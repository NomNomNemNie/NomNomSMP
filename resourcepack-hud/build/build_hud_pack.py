#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pack NomNomUI-HUD resource pack (Paper 1.21.11) — separate sidebar/tablist pack.

NN6 A2: second pack, split from NomNomUI. Contains ONLY:
  - font nomnom:hud (fixed-width digits 0-9 . , k M T + ms at U+E040..U+E04F,
    uniform 9 px advance, cell 16x16 height 9 / ascent 9; ornaments + frames
    U+E050..U+E05D; atlas 128x64)
  - byte-identical copy of nomnom:ui (ui.json + icons.png) so icons work
    regardless of pack install order
  - minecraft:default override = the NN6 A1 chain plus a reference nomnom:hud
    ([space, include/default(uniform=false), nomnom:ui, nomnom:hud, unifont]).
    NO vi_text reference anywhere (A1 dropped the custom text font).
Contains NO: vi_text.png, gui textures, item models, weapons.

Zip is deterministic: sorted names, fixed timestamp, compresslevel 9.

Usage:
  python work/rp_build/build_hud_pack.py
  python work/rp_build/build_hud_pack.py --version 1.1.0 --out work/rp_build/dist/NomNomUI-HUD-v1.1.0.zip
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


README = """# NomNomUI-HUD — resource pack for the sidebar + tablist

Companion pack of **NomNom SMP** (Paper 1.21.11), separate from the main pack
**NomNomUI**: contains only the column-alignment glyphs/ornaments/frames for the
scoreboard (sidebar) and tablist.

- Version: **{version}**
- `pack_format`: **{pack_format}** (resource pack, Minecraft 1.21.11)
- Own font `nomnom:hud` — PUA **U+E040–U+E05D**:
  - **Fixed-width digits** `0-9 . , k M T` + `ms` ligature (U+E040–U+E04F) —
    EVERY glyph advances exactly **9 px** (ink forced into a 15 px box, right
    edge pinned at atlas column 14) => numeric columns right-align perfectly.
    Cell **16x16, height 9 / ascent 9** (vanilla scale — one 9 px text line per
    glyph, no row overlap; the old 20 px cells overlapped by 11 px).
  - Ornaments + frames (U+E050–U+E05D): 3-piece rule, vbar, row-bg, spark,
    8-piece one-row frame.
- Byte-identical copy of the icon font `nomnom:ui` (U+E000–U+E035) so icons work
  even if only this pack is installed.
- The `minecraft:default` override is the wave-6 A1 chain — the custom Vietnamese
  text font (`vi_text`) was dropped from BOTH packs; this pack adds only
  `nomnom:hud` before `minecraft:include/unifont`.
- Install both packs together: send **NomNomUI FIRST, NomNomUI-HUD SECOND**
  (`Player#addResourcePack`) — the HUD override already contains every provider
  of the main chain, so nothing is lost.
- Glyph table + number->PUA mapping recipe: `HUD-INFO.md` in this pack.

## Attribution (required)
- **Be Vietnam Pro** — SIL Open Font License 1.1, see `LICENSE-OFL.txt`
  (the `k`/`M`/`T`/`ms` glyphs are raster derivatives of that typeface).
- Glyph/ornament design: © NomNom SMP 2026.
"""

ATTRIBUTION = """# Attribution & licences — NomNomUI-HUD

## 1. Font Be Vietnam Pro

| Field | Value |
|---|---|
| Font | **Be Vietnam Pro** (Regular 400) |
| Author | The Be Vietnam Pro Project Authors, Copyright 2021 |
| Licence | **SIL Open Font License 1.1 (OFL-1.1)** |
| Source | Google Fonts — `ofl/bevietnampro` |
| Licence text | `LICENSE-OFL.txt` (shipped in this pack) |

The fixed-width digit set of this pack is a raster derivative of Be Vietnam Pro
(characters forced into a 15 px-wide box for a uniform advance) in font id
`nomnom:hud`. OFL allows embedding/redistribution of rasterized fonts inside a
resource pack; the font itself must not be sold separately.

## 2. Original design

Ornaments, column-alignment frames, HUD glyph layout and the packaging script:
**© NomNom SMP 2026**. Released with the NomNom SMP server.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Pack NomNomUI-HUD resource pack")
    ap.add_argument("--version", default="1.1.0")
    ap.add_argument("--out", default=str(DIST / "NomNomUI-HUD-v1.1.0.zip"))
    args = ap.parse_args()

    if not (SRC / "assets/nomnom/font/hud.json").is_file():
        raise SystemExit("missing hud_src — run build_hud.py first")
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
        # only pack content: assets/** + HUD-INFO.md. Meta files (pack.mcmeta,
        # README, ATTRIBUTION, LICENSE, pack.png) are ALWAYS regenerated below —
        # build/, dist/... are excluded from the source scan.
        if top == "assets" or rel == "HUD-INFO.md":
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
