#!/usr/bin/env python3
"""Validate resource pack NomNom UI: zip, JSON, pack.mcmeta, PNG, font, item model.

Chạy:
  python work/rp_build/validate_pack.py --zip work/rp_build/dist/NomNomUI-v1.0.0.zip
  python work/rp_build/validate_pack.py --zip ... --json work/rp_build/validate_report.json

Exit code 0 = PASS, 1 = FAIL. Không sửa zip.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_WEAPONS = PROJECT / "downloads" / "weapons_rp.zip"
EXPECTED_FORMAT = 75  # 1.21.11 resource pack (94 là data pack)

REQUIRED_MAIN = [
    "pack.mcmeta",
    "pack.png",
    "README.md",
    "ATTRIBUTION.md",
    "LICENSE-OFL.txt",
    "assets/nomnom/font/ui.json",
    "assets/nomnom/textures/font/icons.png",
    "assets/nomnom/textures/font/vi_text.png",
]
REQUIRED_HUD = [
    "pack.mcmeta",
    "pack.png",
    "README.md",
    "ATTRIBUTION.md",
    "LICENSE-OFL.txt",
    "HUD-INFO.md",
    "assets/nomnom/font/ui.json",
    "assets/nomnom/font/hud.json",
    "assets/nomnom/textures/font/icons.png",
    "assets/nomnom/textures/font/hud.png",
]
REQUIRED = REQUIRED_MAIN  # đổi theo --preset trong main()

ALLOWED_ROOT = {
    "pack.mcmeta", "pack.png", "README.md", "ATTRIBUTION.md",
    "LICENSE-OFL.txt", "PLACEHOLDERS.txt", "HUD-INFO.md",
}

JUNK_PARTS = {
    "__MACOSX", ".DS_Store", "Thumbs.db", "desktop.ini", "__pycache__",
    ".git", "node_modules", ".idea", ".vscode",
}
JUNK_EXTS = {".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp", ".psd", ".xcf", ".blend"}


def resolve_asset(ref: str) -> str:
    ns, _, path = ref.partition(":")
    if not Path(path).suffix:
        path += ".png"
    return f"assets/{ns}/textures/{path}"


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: dict = {}

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(zip_path: Path, weapons_zip: Path, expect_format: int, res: Result,
             preset: str = "main") -> None:
    if not zip_path.is_file():
        res.err(f"không thấy zip: {zip_path}")
        return
    res.info["zip"] = str(zip_path)
    res.info["bytes"] = zip_path.stat().st_size

    with zipfile.ZipFile(zip_path) as z:
        bad = z.testzip()
        if bad:
            res.err(f"CRC lỗi ở entry: {bad}")
        infos = z.infolist()
        names = [i.filename for i in infos]
        res.info["files"] = len([i for i in infos if not i.is_dir()])
        res.info["directories"] = len([i for i in infos if i.is_dir()])
        res.info["uncompressed_bytes"] = sum(i.file_size for i in infos)

        # --- tên entry
        seen = set()
        for n in names:
            if n in seen:
                res.err(f"entry trùng: {n}")
            seen.add(n)
            if n.startswith("/") or "\\" in n or ".." in n.split("/"):
                res.err(f"đường dẫn không hợp lệ: {n}")
            parts = set(n.split("/"))
            if parts & JUNK_PARTS:
                res.err(f"file rác: {n}")
            if Path(n).suffix.lower() in JUNK_EXTS:
                res.err(f"định dạng rác: {n}")
            if not n.endswith("/") and zipfile.ZipInfo(n).file_size == 0:
                # đọc lại qua zip để chắc chắn
                if z.getinfo(n).file_size == 0 and n != "pack.mcmeta":
                    res.warn(f"file 0 byte: {n}")

        if names.count("pack.mcmeta") != 1:
            res.err("pack.mcmeta phải có đúng 1 ở root")
        if "assets/" not in "".join(names[:1]):
            pass

        # root không mong đợi
        root_files = {n for n in names if "/" not in n and not n.endswith("/")}
        unknown = root_files - ALLOWED_ROOT
        if unknown:
            res.warn(f"file root không nằm trong danh sách chuẩn: {sorted(unknown)}")

        for req in REQUIRED:
            if req not in names:
                res.err(f"thiếu file bắt buộc: {req}")

        # --- pack.mcmeta
        if "pack.mcmeta" in names:
            try:
                meta = json.loads(z.read("pack.mcmeta").decode("utf-8"))
                pack = meta.get("pack", {})
                fmt = pack.get("pack_format")
                res.info["pack_format"] = fmt
                res.info["description"] = pack.get("description")
                if fmt != expect_format:
                    res.err(f"pack_format = {fmt}, cần {expect_format} "
                            f"(resource pack 1.21.11; 94 là data pack)")
                desc = str(pack.get("description", ""))
                if "NomNom" not in desc:
                    res.err("description thiếu 'NomNom'")
                if not any(ord(c) > 127 for c in desc):
                    res.warn("description không có ký tự tiếng Việt")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                res.err(f"pack.mcmeta không parse được: {e}")

        # --- toàn bộ JSON
        json_count = 0
        for n in names:
            if not n.endswith(".json"):
                continue
            json_count += 1
            try:
                json.loads(z.read(n).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                res.err(f"JSON hỏng {n}: {e}")
        res.info["json_files"] = json_count

        # --- PNG: mở/verify + kích thước
        png_count = 0
        dims: dict[str, tuple[int, int]] = {}
        for n in names:
            if not n.endswith(".png"):
                continue
            png_count += 1
            try:
                im = Image.open(io.BytesIO(z.read(n)))
                im.verify()
                im = Image.open(io.BytesIO(z.read(n)))
                dims[n] = im.size
                if im.mode not in ("RGBA", "RGB", "P"):
                    res.warn(f"PNG mode lạ {n}: {im.mode}")
            except Exception as e:  # noqa: BLE001 - báo mọi lỗi ảnh
                res.err(f"PNG hỏng {n}: {e}")
        res.info["png_files"] = png_count

        def expect_dim(name: str, w: int, h: int) -> None:
            if name in dims and dims[name] != (w, h):
                res.err(f"{name} có kích thước {dims[name]}, cần {(w, h)}")

        expect_dim("assets/nomnom/textures/font/icons.png", 128, 112)
        expect_dim("assets/nomnom/textures/font/vi_text.png", 256, 500)
        expect_dim("assets/nomnom/textures/font/hud.png", 128, 64)
        expect_dim("assets/nomnom/textures/gui/panel_primary.png", 48, 48)
        expect_dim("assets/nomnom/textures/gui/panel_inset.png", 48, 48)
        expect_dim("assets/nomnom/textures/gui/panel_raised.png", 48, 48)
        expect_dim("assets/nomnom/textures/gui/titlebar.png", 48, 20)
        expect_dim("assets/nomnom/textures/gui/divider.png", 16, 4)

        for n, (w, h) in dims.items():
            if n.startswith("assets/nomnom/textures/item/ui/") and "/icon/" not in n:
                if (w, h) != (16, 16):
                    res.err(f"{n} kích thước {w}x{h}, cần 16x16")
            if n.startswith("assets/nomnom/textures/item/ui/icon/"):
                if (w, h) != (32, 32):
                    res.err(f"{n} kích thước {w}x{h}, cần 32x32")

        # --- font JSON: bitmap refs + chars khớp atlas
        for n in names:
            if not re.match(r"assets/[^/]+/font/[^/]+\.json$", n):
                continue
            data = json.loads(z.read(n).decode("utf-8"))
            providers = data.get("providers")
            if not isinstance(providers, list) or not providers:
                res.err(f"{n}: providers rỗng/không phải list")
                continue
            has_bitmap = False
            for prov in providers:
                if prov.get("type") != "bitmap":
                    continue
                has_bitmap = True
                ref = prov.get("file", "")
                asset = resolve_asset(ref)
                if "vi_text" in asset:
                    # NN6 A1: the custom text font is dropped from EVERY pack —
                    # vi_text.png may still ship (main pack, unreferenced) but no
                    # font JSON may point at it (20 px boxes overlapped the 9 px
                    # line height by 11 px).
                    res.err(f"{n}: A1 violation — bitmap reference to {asset} "
                            f"(custom text font must not be referenced any more)")
                    continue
                if asset not in names:
                    res.err(f"{n}: bitmap trỏ tới {asset} không có trong zip")
                    continue
                rows = prov.get("chars", [])
                h = prov.get("height")
                ascent = prov.get("ascent")
                if not isinstance(rows, list) or not rows:
                    res.err(f"{n}: chars rỗng")
                    continue
                if not isinstance(h, int) or not isinstance(ascent, int):
                    res.err(f"{n}: height/ascent phải là int")
                elif ascent > h:
                    res.err(f"{n}: ascent {ascent} > height {h}")
                lens = {len(r) for r in rows}
                if len(lens) != 1:
                    res.warn(f"{n}: độ dài các hàng chars khác nhau {sorted(lens)}")
                cols = max(lens)
                w, hpx = dims.get(asset, (0, 0))
                if w and hpx:
                    if w % cols:
                        res.err(f"{n}: atlas rộng {w} không chia hết {cols} cột")
                    elif w // cols != hpx // len(rows):
                        res.warn(f"{n}: cell không vuông ({w // cols}x{hpx // len(rows)})")
                    if hpx % len(rows):
                        res.err(f"{n}: atlas cao {hpx} không chia hết {len(rows)} hàng")
                total = sum(len(r) for r in rows)
                cps = [ord(c) for r in rows for c in r if c != "\0"]
                glyphs = len(cps)
                if glyphs != len(set(cps)):
                    res.err(f"{n}: codepoint trùng trong chars")
                res.info.setdefault("fonts", {})[n] = {
                    "bitmap": has_bitmap, "glyphs": glyphs, "cells": total,
                    "range": f"U+{min(cps):04X}..U+{max(cps):04X}" if cps else None,
                }
            if n == "assets/nomnom/font/ui.json" and has_bitmap:
                if len(cps) != 54:
                    res.err(f"{n}: cần 54 glyph icon, thấy {len(cps)}")
                if cps and (min(cps) != 0xE000 or max(cps) != 0xE035):
                    res.err(f"{n}: dải PUA phải U+E000..U+E035 (48 cũ + 6 mới), thấy "
                            f"U+{min(cps):04X}..U+{max(cps):04X}")
            if n == "assets/nomnom/font/hud.json" and has_bitmap:
                if len(cps) != 30:
                    res.err(f"{n}: cần 30 glyph HUD (10 digits + 6 suffix + 14 ornament), thấy {len(cps)}")
                if cps and (min(cps) != 0xE040 or max(cps) != 0xE05D):
                    res.err(f"{n}: dải PUA HUD phải U+E040..U+E05D, thấy "
                            f"U+{min(cps):04X}..U+{max(cps):04X}")
                if prov.get("height") != 9 or prov.get("ascent") != 9:
                    res.err(f"{n}: HUD font phải height=9 ascent=9 (vanilla scale, NN6 A2)")
                # NN6 A2: the digit group must be right-pinned at atlas column 14
                # (ink_w = 15) so every glyph advances round_half_up(15*9/16)+1 = 9 px.
                hud_atlas = Image.open(io.BytesIO(
                    z.read("assets/nomnom/textures/font/hud.png"))).convert("RGBA")
                bad_pin = []
                for idx in range(16):                       # U+E040..U+E04F
                    row, col = divmod(idx, 8)
                    cc = hud_atlas.crop((col * 16, row * 16, col * 16 + 16, row * 16 + 16))
                    bb = cc.getchannel("A").getbbox()
                    if bb is None or bb[2] != 15:
                        bad_pin.append((f"E{0xE040 + idx:04X}", None if bb is None else bb[2]))
                if bad_pin:
                    res.err(f"{n}: digit group not right-pinned at column 14 "
                            f"(uniform 9 px advance broken): {bad_pin}")
            if n == "assets/minecraft/font/default.json":
                ids = [p.get("id") for p in providers if p.get("type") == "reference"]
                for needed in ("minecraft:include/space", "minecraft:include/default",
                               "nomnom:ui", "minecraft:include/unifont"):
                    if needed not in ids:
                        res.err(f"{n}: thiếu reference {needed} (fallback ký hiệu HUD)")

        # --- item definitions -> model -> texture
        item_defs = [n for n in names if n.startswith("assets/nomnom/items/") and n.endswith(".json")]
        for n in item_defs:
            data = json.loads(z.read(n).decode("utf-8"))
            model = (data.get("model") or {}).get("model")
            if not model:
                res.err(f"{n}: thiếu model.model")
                continue
            ns, _, path = model.partition(":")
            model_path = f"assets/{ns}/models/{path}.json"
            if model_path not in names:
                res.err(f"{n}: trỏ model {model} nhưng thiếu {model_path}")
                continue
            mdata = json.loads(z.read(model_path).decode("utf-8"))
            layer0 = (mdata.get("textures") or {}).get("layer0")
            if layer0:
                tex = resolve_asset(layer0)
                if tex not in names:
                    res.err(f"{model_path}: layer0 {layer0} thiếu texture {tex}")
        res.info["item_definitions"] = len(item_defs)

        # --- weapons merge (chỉ pack chính; pack HUD không chứa weapons)
        if preset == "hud":
            if any(n.startswith("assets/weapons/") for n in names):
                res.err("pack HUD không được chứa assets/weapons/**")
            if "assets/nomnom/textures/font/vi_text.png" in names:
                res.err("pack HUD không được đóng gói font text (vi_text thuộc pack chính)")
            hud_default = json.loads(z.read("assets/minecraft/font/default.json").decode("utf-8"))
            hud_refs = [p.get("id") for p in hud_default["providers"] if p.get("type") == "reference"]
            if "nomnom:hud" not in hud_refs:
                res.err("default.json của pack HUD thiếu reference nomnom:hud")
            if "nomnom:ui" not in hud_refs:
                res.err("default.json của pack HUD thiếu reference nomnom:ui")
        elif weapons_zip.is_file():
            with zipfile.ZipFile(weapons_zip) as wz:
                expect = {i.filename for i in wz.infolist()
                          if not i.is_dir() and i.filename.startswith("assets/weapons/")}
                got = {n for n in names if n.startswith("assets/weapons/")}
                res.info["weapons_files"] = len(got)
                missing = sorted(expect - got)
                extra = sorted(got - expect)
                if missing:
                    res.err(f"thiếu {len(missing)} file weapons: {missing[:5]}")
                if extra:
                    res.warn(f"có {len(extra)} file weapons ngoài nguồn: {extra[:5]}")
                for n in expect & got:
                    if z.read(n) != wz.read(n):
                        res.err(f"weapons file khác byte so với nguồn: {n}")
                if not expect:
                    res.err("nguồn weapons không có assets/weapons/**")
        else:
            res.warn(f"không kiểm merge weapons: thiếu {weapons_zip}")
            if not any(n.startswith("assets/weapons/") for n in names):
                res.err("pack không có assets/weapons/**")

        # --- attribution nội dung (theo preset: HUD không chứa weapons)
        attr_needles = ("CC-BY-4.0", "4pmYLtZ9", "weapons-plus", "jfrost3712",
                        "OFL", "Be Vietnam Pro")
        readme_needles = ("CC-BY-4.0", "4pmYLtZ9", "weapons-plus")
        if preset == "hud":
            attr_needles = ("OFL", "Be Vietnam Pro", "NomNomUI-HUD", "nomnom:hud")
            readme_needles = ("OFL", "Be Vietnam Pro", "NomNomUI-HUD")
        if "ATTRIBUTION.md" in names:
            text = z.read("ATTRIBUTION.md").decode("utf-8", errors="replace")
            for needle in attr_needles:
                if needle not in text:
                    res.err(f"ATTRIBUTION.md thiếu '{needle}'")
        if "README.md" in names:
            readme = z.read("README.md").decode("utf-8", errors="replace")
            for needle in readme_needles:
                if needle not in readme:
                    res.err(f"README.md thiếu ghi công '{needle}'")


def main() -> int:
    global REQUIRED
    ap = argparse.ArgumentParser(description="Validate NomNom UI resource pack")
    ap.add_argument("--zip", default="work/rp_build/dist/NomNomUI-v1.1.0.zip")
    ap.add_argument("--weapons", default=str(DEFAULT_WEAPONS))
    ap.add_argument("--expect-format", type=int, default=EXPECTED_FORMAT)
    ap.add_argument("--preset", choices=("main", "hud"), default="main",
                    help="main = NomNomUI đầy đủ; hud = NomNomUI-HUD (không weapons/vi_text)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    REQUIRED = REQUIRED_HUD if args.preset == "hud" else REQUIRED_MAIN

    res = Result()
    try:
        validate(Path(args.zip), Path(args.weapons), args.expect_format, res, preset=args.preset)
    except Exception as e:  # noqa: BLE001 - validator không được crash im lặng
        res.err(f"validator exception: {type(e).__name__}: {e}")

    status = "PASS" if res.ok else "FAIL"
    print(f"[{status}] {args.zip}")
    print(f"  files={res.info.get('files')} png={res.info.get('png_files')} "
          f"json={res.info.get('json_files')} weapons={res.info.get('weapons_files')} "
          f"format={res.info.get('pack_format')}")
    for k, v in (res.info.get("fonts") or {}).items():
        print(f"  font {k}: glyphs={v['glyphs']} cells={v['cells']} range={v['range']}")
    for w in res.warnings:
        print(f"  WARN  {w}")
    for e in res.errors:
        print(f"  ERROR {e}")
    print(f"  => {status} ({len(res.errors)} lỗi, {len(res.warnings)} cảnh báo)")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"status": status, **res.info,
                                   "errors": res.errors,
                                   "warnings": res.warnings},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  report: {out}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
