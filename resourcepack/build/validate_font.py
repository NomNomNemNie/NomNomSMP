#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent validator for the NomNom UI font assets.

Deliberately shares no code with build_font.py: it re-reads the shipped files with
plain json / Pillow and re-derives every count, so a bug in the builder cannot make
its own self-check pass.

Checks
  1. every font provider JSON parses with python json, and the default override sits
     at assets/minecraft/font/default.json with the full fallback chain;
  2. atlases exist, are the declared size, and are not empty;
  3. 48 icon glyphs, contiguous U+E000..U+E02F, one non-blank cell each, right edge
     column transparent (so the client advance is 9 px), binary white/black alpha;
  4. >= 300 text codepoints and all 146 precomposed Vietnamese characters present;
  5. icon manifest (work/nn4-icons.json) and ui.json agree codepoint for codepoint;
  6. OFL licence shipped verbatim.

Usage: python work/rp_build/validate_font.py
Exit code 0 = all checks passed.
"""

import json
import sys
import unicodedata
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
RP = WORK / "rp_src"
A = RP / "assets"
DEFAULT_JSON = A / "minecraft" / "font" / "default.json"
ALIAS_JSON = A / "nomnom" / "font" / "default.json"
UI_JSON = A / "nomnom" / "font" / "ui.json"
TEXT_PNG = A / "nomnom" / "textures" / "font" / "vi_text.png"
ICON_PNG = A / "nomnom" / "textures" / "font" / "icons.png"
ICON_DIR = A / "nomnom" / "textures" / "icon"
MANIFEST = WORK / "nn4-icons.json"
OFL = RP / "LICENSE-OFL.txt"
OFL_SRC = HERE / "fonts" / "OFL.txt"

failures = []
notes = []


def check(cond, msg):
    if cond:
        print("  PASS  " + msg)
    else:
        print("  FAIL  " + msg)
        failures.append(msg)


def vietnamese():
    vowels = "aăâeêioôơuưy"
    tones = ["", "\u0300", "\u0301", "\u0303", "\u0309", "\u0323"]
    out = set()
    for v in vowels:
        for t in tones:
            out.add(unicodedata.normalize("NFC", v + t))
            out.add(unicodedata.normalize("NFC", v.upper() + t))
    out |= {"đ", "Đ"}
    return {c for c in out if len(c) == 1}


def main() -> int:
    print("== 1. provider JSON ==")
    docs = {}
    for name, path in (("override", DEFAULT_JSON), ("alias", ALIAS_JSON), ("icons", UI_JSON)):
        try:
            docs[name] = json.loads(path.read_text(encoding="utf-8"))
            check(True, f"{path.relative_to(WORK)} parses as JSON")
        except Exception as e:                                  # noqa: BLE001
            check(False, f"{path.relative_to(WORK)} parses as JSON ({e})")
            return 1

    ov = docs["override"]
    refs = [p.get("id") for p in ov["providers"] if p.get("type") == "reference"]
    check(DEFAULT_JSON.is_file(), "override lives at assets/minecraft/font/default.json")
    check(refs == ["minecraft:include/space", "minecraft:include/default",
                   "nomnom:ui", "minecraft:include/unifont"],
          f"fallback chain is complete and ordered: {refs}")
    check(docs["alias"] == ov, "nomnom:default alias is byte-equal in content to the override")

    print("== 2. text atlas ==")
    text_rows = ov["providers"][0]["chars"]
    check(ov["providers"][0]["type"] == "bitmap"
          and ov["providers"][0]["file"] == "nomnom:font/vi_text.png",
          "first provider is the vi_text bitmap")
    check(ov["providers"][0]["height"] == 16 and ov["providers"][0]["ascent"] == 13,
          "text provider height=16 ascent=13 (ascent <= height)")
    check(len(text_rows) == 25 and all(len(r) == 16 for r in text_rows),
          "chars grid is 25 rows x 16 columns")
    cps = [ord(c) for r in text_rows for c in r if c != "\u0000"]
    check(len(cps) == len(set(cps)), "no duplicated text codepoints")
    check(len(cps) == 385, f"385 text glyphs declared (got {len(cps)})")
    check(len(cps) >= 300, f"at least 300 text glyphs (got {len(cps)})")

    atlas = Image.open(TEXT_PNG).convert("RGBA")
    check(atlas.size == (256, 400), f"vi_text.png is 256x400 (got {atlas.size})")
    alpha = atlas.getchannel("A")
    ink = sum(alpha.histogram()[1:])
    check(ink > 0, f"vi_text.png is not empty ({ink} ink px)")

    cells_empty = []
    for i, cp in enumerate(cps):
        r, c = divmod(i, 16)
        cell = atlas.crop((c * 16, r * 16, c * 16 + 16, r * 16 + 16))
        if cell.getchannel("A").getbbox() is None:
            cells_empty.append(hex(cp))
    check(not cells_empty, f"every declared glyph has ink in its own cell ({len(cells_empty)} empty)")

    vi = vietnamese()
    missing = sorted(c for c in vi if ord(c) not in set(cps))
    check(len(vi) == 146, f"Vietnamese reference set is 146 chars (got {len(vi)})")
    check(not missing, f"all 146 precomposed Vietnamese chars present (missing {''.join(missing) or 'none'})")
    notes.append(f"text glyphs: {len(cps)}, Vietnamese: {len(vi) - len(missing)}/{len(vi)}")

    print("== 3. icon font ==")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    icons = manifest["icons"]
    check(len(icons) == 48, f"nn4-icons.json declares 48 icons (got {len(icons)})")
    man_cps = [int(i["cp"][2:], 16) for i in icons]
    check(man_cps == list(range(0xE000, 0xE030)), "manifest codepoints are contiguous E000..E02F")
    check(len(set(i["id"] for i in icons)) == 48, "manifest icon ids are unique")

    ui = docs["icons"]
    check(len(ui["providers"]) == 1 and ui["providers"][0]["type"] == "bitmap",
          "nomnom:ui has a single bitmap provider")
    check(ui["providers"][0]["height"] == 9 and ui["providers"][0]["ascent"] == 9,
          "icon provider height=9 ascent=9")
    ui_rows = ui["providers"][0]["chars"]
    check(len(ui_rows) == 6 and all(len(r) == 8 for r in ui_rows),
          "icon chars grid is 6 rows x 8 columns")
    ui_cps = [ord(c) for r in ui_rows for c in r]
    check(ui_cps == man_cps, "ui.json order matches nn4-icons.json codepoint for codepoint")

    icon_atlas = Image.open(ICON_PNG).convert("RGBA")
    check(icon_atlas.size == (128, 96), f"icons.png is 128x96 (got {icon_atlas.size})")

    bad = []
    for i, icon in enumerate(icons):
        r, c = divmod(i, 8)
        cell = icon_atlas.crop((c * 16, r * 16, c * 16 + 16, r * 16 + 16))
        colors = {(r_, g_, b_, a_) for _, (r_, g_, b_, a_) in
                  ((n, col) for n, col in (cell.getcolors(maxcolors=64) or []))}
        if len(colors) <= 1:
            bad.append(icon["id"] + ":blank")
            continue
        if not colors <= {(255, 255, 255, 255), (0, 0, 0, 255), (0, 0, 0, 0)}:
            bad.append(icon["id"] + ":colors")
        if any(cell.getpixel((15, y))[3] for y in range(16)):
            bad.append(icon["id"] + ":right-edge")
        if not any(cell.getpixel((x, y))[:3] == (255, 255, 255)
                   for x in range(16) for y in range(16)):
            bad.append(icon["id"] + ":no-white")
    check(not bad, f"all 48 icon cells are white/black, non-blank, right edge clear ({bad[:4]})")

    missing_files = [i["id"] for i in icons if not (ICON_DIR / f"{i['id']}.png").is_file()]
    sizes = {Image.open(ICON_DIR / f"{i['id']}.png").size
             for i in icons if (ICON_DIR / f"{i['id']}.png").is_file()}
    check(not missing_files, f"48 individual icon PNGs exist (missing {missing_files})")
    check(sizes == {(16, 16)}, f"individual icons are 16x16 (got {sizes})")

    print("== 4. licence / attribution ==")
    check(OFL.is_file(), "LICENSE-OFL.txt exists in the pack root")
    if OFL.is_file():
        check(OFL.read_bytes() == OFL_SRC.read_bytes(),
              "LICENSE-OFL.txt is byte-identical to the vendored OFL.txt")

    print()
    for n in notes:
        print("  note: " + n)
    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} checks)")
        return 1
    print("\nRESULT: PASS - all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
