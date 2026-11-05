#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đóng gói NomNomUI-HUD resource pack (Paper 1.21.11) — pack RIÊNG sidebar/tablist.

NN5 A3: pack thứ hai, tách khỏi NomNomUI. Chỉ chứa:
  - font nomnom:hud (digits fixed-width + ornament + khung, PUA U+E040..U+E05D)
  - bản copy byte-identical của nomnom:ui (ui.json + icons.png) để icon chạy
    độc lập với thứ tự cài pack
  - override minecraft:default có thêm reference nomnom:hud (superset của pack
    chính — tham chiếu chéo nomnom:font/vi_text.png, thiếu pack chính thì chữ
    rơi về fallback vanilla, không vỡ)
KHÔNG chứa: vi_text.png, gui textures, item models, weapons.

Zip deterministic: sort tên, timestamp cố định, compresslevel 9.

Chạy:
  python work/rp_build/build_hud_pack.py
  python work/rp_build/build_hud_pack.py --version 1.0.0 --out work/rp_build/dist/NomNomUI-HUD-v1.0.0.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
SRC = BUILD_DIR / "hud_src"
if not SRC.is_dir():
    SRC = BUILD_DIR.parent                 # repo layout: resourcepack-hud/
DIST = BUILD_DIR / "dist"
PACK_FORMAT = 75
ZIP_DATE = (2026, 1, 1, 0, 0, 0)


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_pack_png() -> bytes:
    """pack.png HUD: nền ink + 3 thanh vàng kiểu sidebar + ô số."""
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (64, 64), (11, 15, 20, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 61, 61], outline=(232, 180, 80, 255), width=2)
    d.rectangle([4, 4, 59, 59], fill=(18, 24, 33, 255))
    # 3 thanh "sidebar" + cột số căn phải
    rows = [(10, 40, 30), (22, 46, 14), (34, 40, 22)]
    for y, label_w, val_w in rows:
        d.rectangle([8, y, 8 + label_w, y + 8], fill=(232, 180, 80, 255))
        d.rectangle([56 - val_w, y, 56, y + 8], fill=(246, 217, 138, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=9)
    return buf.getvalue()


README = """# NomNomUI-HUD — resource pack cho sidebar + tablist

Pack phụ của **NomNom SMP** (Paper 1.21.11), tách khỏi pack chính **NomNomUI**:
chỉ chứa glyph/ornament/khung căn cột cho scoreboard (sidebar) + tablist.

- Phiên bản: **{version}**
- `pack_format`: **{pack_format}** (resource pack, Minecraft 1.21.11)
- Font riêng `nomnom:hud` — PUA **U+E040–U+E05D**:
  - **Digits fixed-width** `0-9 . , k M` (U+E040–U+E04D) — mọi glyph advance 10 px
    => cột số liệu căn phải TUYỆT ĐỐI (map từng ký tự sau khi padLeft).
  - Ornament + khung (U+E050–U+E05D): rule 3-mảnh, vbar, row-bg, spark, khung 8-mảnh.
- Copy byte-identical của font icon `nomnom:ui` (U+E000–U+E035) để icon chạy đúng
  kể cả khi chỉ cài pack này.
- Override `minecraft:default` tham chiếu chéo `nomnom:font/vi_text.png` của pack
  chính — không chứa font text; thiếu pack chính thì chữ rơi về fallback vanilla.
- Cài cùng lúc cả hai pack: gửi **NomNomUI trước, NomNomUI-HUD sau**
  (`Player#addResourcePack`) — override của HUD đã chứa ĐỦ provider của pack chính.
- Chi tiết bảng glyph + cách dùng: `HUD-INFO.txt` trong pack.

## Ghi công (bắt buộc)
- **Be Vietnam Pro** — SIL Open Font License 1.1, xem `LICENSE-OFL.txt`
  (digits 'k' 'M' và phần cơ cấu font HUD phái sinh từ bản raster hoá).
- Phần glyph/ornament tự thiết kế: © NomNom SMP 2026.
"""

ATTRIBUTION = """# Ghi công & giấy phép — NomNomUI-HUD

## 1. Font Be Vietnam Pro

| Trường | Giá trị |
|---|---|
| Tên font | **Be Vietnam Pro** (Regular 400) |
| Tác giả | The Be Vietnam Pro Project Authors, Copyright 2021 |
| Giấy phép | **SIL Open Font License 1.1 (OFL-1.1)** |
| Nguồn | Google Fonts — `ofl/bevietnampro` |
| Văn bản giấy phép | `LICENSE-OFL.txt` (kèm trong pack) |

Bộ digits fixed-width của pack này là dẫn xuất raster hoá từ Be Vietnam Pro
(ký tự được ép vào hộp 9 px để đồng nhất advance) trong font id `nomnom:hud`.
OFL cho phép nhúng/phân phối bản raster hoá trong resource pack; không được
bán font riêng lẻ.

## 2. Phần tự thiết kế

Ornament, khung căn cột, bố cục glyph HUD và toàn bộ script đóng gói:
**© NomNom SMP 2026**. Phát hành kèm server NomNom SMP.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Đóng gói NomNomUI-HUD resource pack")
    ap.add_argument("--version", default="1.0.0")
    ap.add_argument("--out", default=str(DIST / "NomNomUI-HUD-v1.0.0.zip"))
    args = ap.parse_args()

    if not (SRC / "assets/nomnom/font/hud.json").is_file():
        raise SystemExit("thiếu hud_src — chạy build_hud.py trước")
    ui_src = SRC / "assets/nomnom/font/ui.json"
    _here = Path(__file__).resolve()
    # tìm ui.json của pack chính: workspace (work/rp_src) hoặc repo (resourcepack/)
    ui_main = None
    for base in (_here.parents[1], *_here.parents[1:-1]):
        for cand in (base / "resourcepack" / "assets/nomnom/font/ui.json",
                     base / "rp_src" / "assets/nomnom/font/ui.json"):
            if cand.is_file():
                ui_main = cand
                break
        if ui_main:
            break
    if ui_main is None:
        raise SystemExit("không tìm thấy assets/nomnom/font/ui.json của pack chính")
    if ui_src.read_bytes() != ui_main.read_bytes():
        raise SystemExit("ui.json copy lệch với pack chính — chạy lại build_font.py + build_hud.py")

    out_zip = Path(args.out)
    out_zip.parent.mkdir(parents=True, exist_ok=True)

    files: list[tuple[str, bytes]] = []
    for p in sorted(SRC.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(SRC).as_posix().replace("\\", "/")
        top = rel.split("/")[0]
        # chỉ nhận nội dung pack: assets/** + HUD-INFO.txt. Các file meta
        # (pack.mcmeta, README, ATTRIBUTION, LICENSE, pack.png) LUÔN sinh lại ở
        # dưới — loại trừ build/, dist/… khỏi nguồn.
        if top == "assets" or rel == "HUD-INFO.txt":
            files.append((rel, p.read_bytes()))

    # pack.png sinh tại chỗ (đưa vào trước khi sort — sort theo tên)
    files.append(("pack.png", make_pack_png()))

    mcmeta = {
        "pack": {
            "pack_format": PACK_FORMAT,
            "description": f"§6NomNom UI HUD §8• §7Sidebar & tablist căn cột §8• §7v{args.version}",
        }
    }
    files.append(("pack.mcmeta",
                  (json.dumps(mcmeta, ensure_ascii=False, indent=2) + "\n").encode("utf-8")))
    files.append(("README.md", README.format(version=args.version, pack_format=PACK_FORMAT).encode("utf-8")))
    files.append(("ATTRIBUTION.md", ATTRIBUTION.encode("utf-8")))
    ofl = BUILD_DIR / "fonts" / "OFL.txt"
    if not ofl.is_file():
        for base in (BUILD_DIR.parents[0], *BUILD_DIR.parents[1:]):
            cand = base / "resourcepack" / "build" / "fonts" / "OFL.txt"
            if cand.is_file():
                ofl = cand
                break
    files.append(("LICENSE-OFL.txt", ofl.read_bytes()))

    files.sort(key=lambda t: t[0])
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, data in files:
            info = zipfile.ZipInfo(rel, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    report = {
        "pack": "NomNomUI-HUD",
        "version": args.version,
        "pack_format": PACK_FORMAT,
        "build_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output": str(out_zip),
        "files": len(files),
        "bytes": out_zip.stat().st_size,
        "sha1": sha1_file(out_zip),
        "sha256": sha256_file(out_zip),
    }
    (BUILD_DIR / "build_hud_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=" * 64)
    print(f"NomNomUI-HUD v{args.version}")
    print(f"  output      : {out_zip}")
    print(f"  files       : {len(files)}")
    print(f"  bytes       : {report['bytes']}")
    print(f"  pack_format : {PACK_FORMAT} (resource pack 1.21.11)")
    print(f"  sha1        : {report['sha1']}")
    print(f"  sha256      : {report['sha256']}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
