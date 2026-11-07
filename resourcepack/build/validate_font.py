#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent validator for the NomNom UI font assets (NN6).

Deliberately shares no code with build_font.py: it re-reads the shipped files with
plain json / Pillow and re-derives every count, so a bug in the builder cannot make
its own self-check pass.

Checks (NN6 A1 — custom text font dropped)
  1. every font provider JSON parses with python json, and the default override sits
     at assets/minecraft/font/default.json with the A1 fallback chain
     [include/space, include/default(filter.uniform=false), nomnom:ui, include/unifont];
     the nomnom:default alias is byte-equal in content;
  2. NO font JSON (either namespace) references nomnom:font/vi_text.png any more —
     the 20px text provider was the root cause of the row overlap (wave 6 A1);
  3. the retired text atlas vi_text.png is still shipped on disk (rollback anchor),
     at its NN5 size 256x500, and is not empty;
  4. 54 icon glyphs, contiguous U+E000..U+E035, one non-blank cell each, right edge
     column transparent (so the client advance is 9 px), binary white/black alpha;
     U+E000..U+E02F still match work/nn4-icons.json codepoint for codepoint (v1.0 contract);
  5. icon manifest (work/rp_build/icons-nn5.json) and ui.json agree codepoint for
     codepoint; redrawn glyphs must not change the codepoint/id of the 48 old icons;
  6. OFL licence shipped verbatim.

Usage: python work/rp_build/validate_font.py
Exit code 0 = all checks passed.
"""

import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
RP = HERE.parent if (HERE.parent / "assets").is_dir() else WORK / "rp_src"  # repo: resourcepack/, workspace: work/rp_src
A = RP / "assets"
DEFAULT_JSON = A / "minecraft" / "font" / "default.json"
ALIAS_JSON = A / "nomnom" / "font" / "default.json"
UI_JSON = A / "nomnom" / "font" / "ui.json"
TEXT_PNG = A / "nomnom" / "textures" / "font" / "vi_text.png"   # retired, kept unreferenced
ICON_PNG = A / "nomnom" / "textures" / "font" / "icons.png"
ICON_DIR = A / "nomnom" / "textures" / "icon"
MANIFEST = HERE / "icons-nn5.json"
MANIFEST_V1 = WORK / "nn4-icons.json"
if not MANIFEST_V1.is_file():
    MANIFEST_V1 = HERE.parent / "icons.json"   # repo layout: resourcepack/icons.json
OFL = RP / "LICENSE-OFL.txt"
OFL_SRC = HERE / "fonts" / "OFL.txt"

TEXT_COLS, TEXT_ROWS = 16, 25        # retired atlas geometry (kept for the size check)
ICON_COLS, ICON_ROWS = 8, 7
N_ICONS = 54

failures = []
notes = []


def check(cond, msg):
    if cond:
        print("  PASS  " + msg)
    else:
        print("  FAIL  " + msg)
        failures.append(msg)


def main() -> int:
    print("== 1. provider JSON (A1 chain) ==")
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
    bitmaps = [p.get("file") for p in ov["providers"] if p.get("type") == "bitmap"]
    check(DEFAULT_JSON.is_file(), "override lives at assets/minecraft/font/default.json")
    check(refs == ["minecraft:include/space", "minecraft:include/default",
                   "nomnom:ui", "minecraft:include/unifont"],
          f"A1 fallback chain is complete and ordered: {refs}")
    check(bitmaps == [], f"override carries no bitmap provider of its own (got {bitmaps})")
    dflt = ov["providers"]
    uni = [p for p in dflt if p.get("type") == "reference" and p.get("id") == "minecraft:include/default"]
    check(len(uni) == 1 and uni[0].get("filter", {}).get("uniform") is False,
          "include/default reference keeps filter.uniform=false")
    check(docs["alias"] == ov, "nomnom:default alias is byte-equal in content to the override")

    print("== 2. vi_text must not be referenced anywhere (A1) ==")
    vitext_refs = []
    for font_json in sorted(A.glob("*/font/*.json")):
        data = json.loads(font_json.read_text(encoding="utf-8"))
        for prov in data.get("providers", []):
            if prov.get("type") == "bitmap" and "vi_text" in str(prov.get("file", "")):
                vitext_refs.append(font_json.relative_to(WORK).as_posix())
    check(not vitext_refs,
          f"no font JSON references nomnom:font/vi_text.png (found {vitext_refs or 'none'})")

    print("== 3. retired text atlas still shipped (rollback anchor) ==")
    check(TEXT_PNG.is_file(), "vi_text.png is still shipped on disk (unreferenced)")
    if TEXT_PNG.is_file():
        atlas = Image.open(TEXT_PNG).convert("RGBA")
        check(atlas.size == (TEXT_COLS * 16, TEXT_ROWS * 20),
              f"vi_text.png keeps its NN5 size {TEXT_COLS * 16}x{TEXT_ROWS * 20} (got {atlas.size})")
        ink = sum(atlas.getchannel("A").histogram()[1:])
        check(ink > 0, f"vi_text.png is not empty ({ink} ink px)")

    print("== 4. icon font ==")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    icons = manifest["icons"]
    check(len(icons) == N_ICONS, f"icons-nn5.json declares {N_ICONS} icons (got {len(icons)})")
    man_cps = [int(i["cp"][2:], 16) for i in icons]
    check(man_cps == list(range(0xE000, 0xE000 + N_ICONS)),
          f"manifest codepoints are contiguous E000..E{0xE000 + N_ICONS - 1:04X}")
    check(len(set(i["id"] for i in icons)) == N_ICONS, "manifest icon ids are unique")

    # v1.0 contract: first 48 codepoints + ids must match nn4-icons.json
    v1 = json.loads(MANIFEST_V1.read_text(encoding="utf-8"))
    v1_cps = [int(i["cp"][2:], 16) for i in v1["icons"]]
    check(man_cps[:48] == v1_cps[:48],
          "first 48 codepoints equal the v1 manifest (E000..E02F stable for HUD config)")
    check([i["id"] for i in icons[:48]] == [i["id"] for i in v1["icons"][:48]],
          "first 48 icon ids equal the v1 manifest")

    ui = docs["icons"]
    check(len(ui["providers"]) == 1 and ui["providers"][0]["type"] == "bitmap",
          "nomnom:ui has a single bitmap provider")
    check(ui["providers"][0]["height"] == 9 and ui["providers"][0]["ascent"] == 9,
          "icon provider height=9 ascent=9")
    ui_rows = ui["providers"][0]["chars"]
    check(len(ui_rows) == ICON_ROWS and all(len(r) == ICON_COLS for r in ui_rows),
          f"icon chars grid is {ICON_ROWS} rows x {ICON_COLS} columns")
    ui_cps = [ord(c) for r in ui_rows for c in r if c != "\u0000"]
    check(ui_cps == man_cps, "ui.json order matches icons-nn5.json codepoint for codepoint")

    icon_atlas = Image.open(ICON_PNG).convert("RGBA")
    check(icon_atlas.size == (ICON_COLS * 16, ICON_ROWS * 16),
          f"icons.png is {ICON_COLS * 16}x{ICON_ROWS * 16} (got {icon_atlas.size})")

    bad = []
    for i, icon in enumerate(icons):
        r, c = divmod(i, ICON_COLS)
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
    check(not bad, f"all {N_ICONS} icon cells are white/black, non-blank, right edge clear ({bad[:4]})")

    missing_files = [i["id"] for i in icons if not (ICON_DIR / f"{i['id']}.png").is_file()]
    sizes = {Image.open(ICON_DIR / f"{i['id']}.png").size
             for i in icons if (ICON_DIR / f"{i['id']}.png").is_file()}
    check(not missing_files, f"{N_ICONS} individual icon PNGs exist (missing {missing_files})")
    check(sizes == {(16, 16)}, f"individual icons are 16x16 (got {sizes})")

    print("== 5. licence / attribution ==")
    check(OFL.is_file(), "LICENSE-OFL.txt exists in the pack root")
    if OFL.is_file():
        check(OFL.read_bytes() == OFL_SRC.read_bytes(),
              "LICENSE-OFL.txt is byte-identical to the vendored OFL.txt")

    print()
    notes.append(f"icons: {len(icons)} (U+E000..U+{0xE000 + N_ICONS - 1:04X}), text font: retired (vi_text kept unreferenced)")
    for n in notes:
        print("  note: " + n)
    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} checks)")
        return 1
    print("\nRESULT: PASS - all checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
