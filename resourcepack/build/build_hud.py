#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomNomUI-HUD — build the HUD-only font (nomnom:hud) for sidebar + tablist.

NN6 A2 (wave 6): re-render at VANILLA SCALE.
  * Cell 16x16 (atlas 8x4 cells = 128x64), provider height 9 / ascent 9 — the whole
    cell renders as a 9x9 px box, exactly one MC text line, so glyphs can never
    overlap the next row (the old 16x20 cells at height 20 overlapped by 11 px).
  * Fixed-width digit group 0-9 . , k M T + ms at U+E040..U+E04F, EVERY glyph
    advance = 9 px:
      client advance = round_half_up(ink_w * height / cellHeight) + 1   (BitmapProvider#load)
                     = round_half_up(15 * 9 / 16) + 1 = 8 + 1 = 9
    achieved by forcing each glyph's ink into the uniform box: natural ink squashed
    to <= 15 px wide (Image.BOX) when needed, pasted with the RIGHT edge pinned at
    atlas column 14 (column 15 stays transparent) and the BOTTOM pinned at row 15
    (ascent 9 puts the baseline at the glyph bottom edge, like unifont).
    Em 20 was measured (probe_hud_digits_nn6.py): digit ink 15 rows tall
    (screen ~8.4 px), max digit width 12 px <= 15 — only the 'ms' ligature squashes.
  * Ornament + frame glyphs U+E050..U+E05D re-fitted to the 16-row cell (rule
    3-piece, vbar, row-bg, spark, 8-piece frame). Their advances are MEASURED from
    the rendered ink and documented in HUD-INFO.md — nothing is aspirational.
  * The override minecraft:default is the NN6 A1 chain (no vi_text anywhere) plus
    a reference to nomnom:hud before include/unifont:
      [include/space, include/default(uniform=false), nomnom:ui, nomnom:hud, include/unifont]

Outputs (work/rp_build/hud_src — packed by build_hud_pack.py):
  assets/minecraft/font/default.json     # A1 chain + reference nomnom:hud
  assets/nomnom/font/hud.json            # font id nomnom:hud (PUA U+E040..U+E05D)
  assets/nomnom/font/ui.json             # byte-identical copy from rp_src
  assets/nomnom/textures/font/hud.png    # 128x64, 8x4 cells of 16x16
  assets/nomnom/textures/font/icons.png  # byte-identical copy from rp_src
  HUD-INFO.md                            # glyph table + number->PUA recipe (HUD agent)
  preview_hud_font.png                   # (not shipped) — quick look

Usage: python work/rp_build/build_hud.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent          # work/rp_build
WORK = HERE.parent
RP = HERE.parents[1] / "resourcepack" if (HERE.parents[1] / "resourcepack").is_dir() else WORK / "rp_src"  # repo vs workspace
if (HERE.parent / "HUD-INFO.md").is_file() or (HERE.parent / "HUD-INFO.txt").is_file():
    OUT = HERE.parent                                   # repo layout: resourcepack-hud/
else:
    OUT = HERE / "hud_src"                              # workspace: work/rp_build/hud_src
FONT_DIR = HERE / "fonts"
if not (FONT_DIR / "BeVietnamPro-Regular.ttf").is_file():
    FONT_DIR = HERE.parents[1] / "resourcepack" / "build" / "fonts"   # repo layout
TTF = FONT_DIR / "BeVietnamPro-Regular.ttf"

# ==== NN6 geometry: vanilla scale (cell 16x16 -> rendered 9x9) ===============
CELL_W, CELL_H = 16, 16
PROVIDER_HEIGHT = 9
PROVIDER_ASCENT = 9
EM_PX = 20                  # measured: digit ink 15 rows, max digit ink_w 12 (<= INK_BOX_W)
ALPHA_LOW, ALPHA_HIGH = 36, 210

COLS, ROWS = 8, 4            # 32 cells -> atlas 128x64

INK_BOX_W = 15               # ink box width; right edge pinned at column 14
DIGIT_ADVANCE = 9            # round_half_up(INK_BOX_W * PROVIDER_HEIGHT / CELL_H) + 1

# ==== glyph registry ========================================================
# PUA HUD branch: E040..E05D. E000..E03F belong to the main pack (nomnom:ui).
DIGITS = "0123456789"
# order matters: E04A dot, E04B comma, E04C k, E04D M, E04E T, E04F ms
DIGIT_EXTRA = [(".", "dot"), (",", "comma"), ("k", "k-suffix"),
               ("M", "m-suffix"), ("T", "t-suffix"), ("ms", "ms-suffix")]
DIGIT_GROUP_LAST = 0xE04F    # uniform-advance assertion covers E040..E04F


def alpha_curve(v: int) -> int:
    if v <= ALPHA_LOW:
        return 0
    if v >= ALPHA_HIGH:
        return 255
    return int(ALPHA_LOW + (v - ALPHA_LOW) * (255 - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW))


def round_half_up(x: float) -> int:
    """Java's (int)(0.5 + x) for non-negative x."""
    return int(0.5 + x)


def render_ink(ch: str, font) -> Image.Image:
    """Render one glyph on an oversized scratch canvas, return the cropped ink."""
    scratch = Image.new("L", (CELL_W * 3, CELL_H * 3), 0)
    ImageDraw.Draw(scratch).text((CELL_W, CELL_H * 2), ch, font=font, fill=255, anchor="ls")
    inked = scratch.point(alpha_curve)
    bb = inked.getbbox()
    if bb is None:
        raise SystemExit(f"fixed glyph {ch!r} rendered empty")
    return inked.crop(bb)


def render_fixed(ch: str, font) -> Image.Image:
    """Force the ink into the uniform box => advance is the same for every glyph.

    1. render naturally at EM_PX (hinted), measure the ink;
    2. if wider than INK_BOX_W, squash horizontally (Image.BOX);
    3. paste with the RIGHT edge pinned at column 14 (column 15 transparent) and
       the BOTTOM pinned at row 15 — ascent 9 puts the baseline at the glyph's
       bottom edge, so digits sit on the text baseline and never cross rows.
    """
    ink = render_ink(ch, font)
    w, h = ink.size
    if w > INK_BOX_W:
        ink = ink.resize((INK_BOX_W, h), Image.BOX)
        w = INK_BOX_W
    if h > CELL_H:
        raise SystemExit(f"fixed glyph {ch!r} ink {h} rows does not fit cell {CELL_H}")
    glyph = Image.new("RGBA", (w, h), (255, 255, 255, 0))  # white RGB for §-tinting
    glyph.putalpha(ink)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    cell.alpha_composite(glyph, (INK_BOX_W - w, CELL_H - h))
    return cell


def ink_width(cell: Image.Image) -> int:
    """Rightmost non-transparent column + 1 (client's actualGlyphWidth)."""
    bb = cell.getchannel("A").getbbox()
    return bb[2] if bb else 0


def advance_of(cell: Image.Image) -> int:
    iw = ink_width(cell)
    return round_half_up(iw * PROVIDER_HEIGHT / CELL_H) + 1 if iw else 0


# ---- ornament painters (16x16 cells; advances are measured, not declared) ----

def px_img(fn) -> Image.Image:
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    fn(cell.load())
    return cell


def p_rule_l(px):
    # left cap: 3 px tall at the edge, body 2 px
    for y in (13, 14, 15):
        px[0, y] = (255, 255, 255, 255)
    for x in range(1, 16):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)


def p_rule_m(px):
    for x in range(16):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)


def p_rule_r(px):
    for y in (13, 14, 15):
        px[15, y] = (255, 255, 255, 255)
    for x in range(15):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)


def p_vbar(px):
    for y in range(16):
        for x in (7, 8):
            px[x, y] = (255, 255, 255, 255)


def p_row_bg(px):
    for y in range(16):
        for x in range(16):
            px[x, y] = (255, 255, 255, 255)


def p_spark(px):
    cx, cy, ro, ri = 7.5, 7.5, 5.0, 1.7
    pts = []
    for i in range(8):
        r = ro if i % 2 == 0 else ri
        a = math.radians(-90 + i * 45.0)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for y in range(CELL_H):
        for x in range(CELL_W):
            if _in_poly(x + 0.5, y + 0.5, pts):
                px[x, y] = (255, 255, 255, 255)


def _in_poly(px_, py_, pts) -> bool:
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > py_) != (yj > py_):
            xc = xi + (py_ - yi) * (xj - xi) / (yj - yi)
            if px_ < xc:
                inside = not inside
        j = i
    return inside


def _frame(side: str):
    def draw(px):
        if "t" in side:
            for x in range(16):
                px[x, 0] = (255, 255, 255, 255)
        if "b" in side:
            for x in range(16):
                px[x, 15] = (255, 255, 255, 255)
        if "l" in side:
            for y in range(16):
                px[0, y] = (255, 255, 255, 255)
        if "r" in side:
            for y in range(16):
                px[15, y] = (255, 255, 255, 255)
    return draw


ORNAMENTS = [
    (0xE050, "rule-l", p_rule_l),
    (0xE051, "rule-m", p_rule_m),
    (0xE052, "rule-r", p_rule_r),
    (0xE053, "vbar", p_vbar),
    (0xE054, "row-bg", p_row_bg),
    (0xE055, "spark", p_spark),
    (0xE056, "frame-tl", _frame("tl")),
    (0xE057, "frame-tm", _frame("tm")),
    (0xE058, "frame-tr", _frame("tr")),
    (0xE059, "frame-ml", _frame("ml")),
    (0xE05A, "frame-mr", _frame("mr")),
    (0xE05B, "frame-bl", _frame("bl")),
    (0xE05C, "frame-bm", _frame("bm")),
    (0xE05D, "frame-br", _frame("br")),
]


def main() -> int:
    if not OUT.exists():
        OUT.mkdir(parents=True)
    (OUT / "assets/minecraft/font").mkdir(parents=True, exist_ok=True)
    (OUT / "assets/nomnom/font").mkdir(parents=True, exist_ok=True)
    (OUT / "assets/nomnom/textures/font").mkdir(parents=True, exist_ok=True)

    font = ImageFont.truetype(str(TTF), EM_PX)

    # ---- digits + punctuation + suffixes (fixed width) --------------------
    cells: list[tuple[int, str, Image.Image]] = []
    for i, ch in enumerate(DIGITS):
        cells.append((0xE040 + i, f"digit-{ch}", render_fixed(ch, font)))
    for j, (ch, gid) in enumerate(DIGIT_EXTRA):
        cells.append((0xE04A + j, gid, render_fixed(ch, font)))

    # ---- ornaments --------------------------------------------------------
    for cp, gid, fn in ORNAMENTS:
        cells.append((cp, gid, px_img(fn)))

    cells.sort(key=lambda c: c[0])
    cps = [c[0] for c in cells]
    assert cps == sorted(set(cps)), "duplicate HUD codepoints"
    assert cps[0] == 0xE040 and cps[-1] == 0xE05D, "HUD range drifted"
    assert len(cps) == 30, f"expected 30 HUD glyphs (E040..E05F gap-free), got {len(cps)}"

    # ---- measured advances + uniformity assertion (the NN6 contract) ------
    measured = []
    for cp, gid, cell in cells:
        iw = ink_width(cell)
        adv = advance_of(cell)
        measured.append((cp, gid, iw, adv))
    digit_adv = {adv for cp, _gid, _iw, adv in measured if cp <= DIGIT_GROUP_LAST}
    assert digit_adv == {DIGIT_ADVANCE}, (
        f"digits/suffixes must all advance {DIGIT_ADVANCE}px, measured {digit_adv}")
    for cp, gid, iw, adv in measured:
        if cp <= DIGIT_GROUP_LAST and iw != INK_BOX_W:
            raise SystemExit(f"{gid}: ink_w {iw} != {INK_BOX_W} (right edge must sit at column 14)")

    # ---- atlas + json -----------------------------------------------------
    atlas = Image.new("RGBA", (COLS * CELL_W, ROWS * CELL_H), (255, 255, 255, 0))
    rows_grid: list[list[str]] = [["\u0000"] * COLS for _ in range(ROWS)]
    for cp, gid, cell in cells:
        idx = cp - 0xE040
        row, col = divmod(idx, COLS)
        atlas.alpha_composite(cell, (col * CELL_W, row * CELL_H))
        rows_grid[row][col] = chr(cp)
    atlas.save(OUT / "assets/nomnom/textures/font/hud.png")

    chars_rows = ["".join(r) for r in rows_grid]
    hud_json = {
        "providers": [
            {"type": "bitmap", "file": "nomnom:font/hud.png",
             "height": PROVIDER_HEIGHT, "ascent": PROVIDER_ASCENT, "chars": chars_rows}
        ]
    }
    (OUT / "assets/nomnom/font/hud.json").write_text(
        json.dumps(hud_json, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    # ---- default.json override (A1 chain + nomnom:hud before unifont) -----
    main_default = json.loads((RP / "assets/minecraft/font/default.json").read_text(encoding="utf-8"))
    hud_default = {"providers": list(main_default["providers"])}
    ids = [p.get("id") for p in hud_default["providers"] if p.get("type") == "reference"]
    assert ids == ["minecraft:include/space", "minecraft:include/default",
                   "nomnom:ui", "minecraft:include/unifont"], ids
    assert not [p for p in hud_default["providers"] if p.get("type") == "bitmap"], \
        "main chain still carries a bitmap provider (A1 regression?)"
    hud_default["providers"].insert(3, {"type": "reference", "id": "nomnom:hud"})
    (OUT / "assets/minecraft/font/default.json").write_text(
        json.dumps(hud_default, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    # ---- byte-identical icon copy (independent of pack install order) -----
    for name in ("ui.json",):
        src = RP / f"assets/nomnom/font/{name}"
        (OUT / f"assets/nomnom/font/{name}").write_bytes(src.read_bytes())
    for name in ("icons.png",):
        src = RP / f"assets/nomnom/textures/font/{name}"
        (OUT / f"assets/nomnom/textures/font/{name}").write_bytes(src.read_bytes())

    # ---- HUD-INFO.md ------------------------------------------------------
    info_rows = [f"| U+{cp:04X} | `{gid}` | {iw} | **{adv}** |"
                 for cp, gid, iw, adv in measured]
    ornament_shapes = {
        "rule-l": "left cap of the horizontal rule",
        "rule-m": "middle segment of the horizontal rule",
        "rule-r": "right cap of the horizontal rule",
        "vbar": "2 px vertical column separator, full height",
        "row-bg": "full-cell background (chain horizontally)",
        "spark": "4-point star, centred",
        "frame-tl": "frame corner top-left", "frame-tm": "frame edge top-middle",
        "frame-tr": "frame corner top-right", "frame-ml": "frame edge mid-left",
        "frame-mr": "frame edge mid-right", "frame-bl": "frame corner bottom-left",
        "frame-bm": "frame edge bottom-middle", "frame-br": "frame corner bottom-right",
    }
    orn_rows = [f"| U+{cp:04X} | `{gid}` | {advance_of(px_img(fn))} | {ornament_shapes[gid]} |"
                for cp, gid, fn in ORNAMENTS]
    info = f"""NomNomUI-HUD v1.1.0 — font `nomnom:hud` (wave 6, A2)
=============================================

Scope: glyphs for the sidebar + tablist ONLY. No Vietnamese text font is shipped
(the custom text font was dropped from both packs in wave 6 A1 — the old 20 px
glyph boxes overlapped MC's fixed 9 px lines by 11 px).

Geometry (vanilla scale)
------------------------
* Atlas: `assets/nomnom/textures/font/hud.png`, {COLS * CELL_W}x{ROWS * CELL_H} px, {COLS}x{ROWS} cells of **{CELL_W}x{CELL_H}**.
* Provider: `"height": {PROVIDER_HEIGHT}, "ascent": {PROVIDER_ASCENT}` — the client renders every
  16x16 cell as a **9x9 px box** (pixelScale = 9/16), exactly one Minecraft text
  line, so a glyph can never bleed into the next row.
* Baseline: ascent 9 puts the text baseline at the glyph's bottom edge (same
  convention as unifont). All digit ink is bottom-pinned at atlas row 15, so
  numbers sit ON the baseline.
* Ink box: every fixed-width glyph's ink is forced into a **{INK_BOX_W} px wide box** with the
  RIGHT edge pinned at atlas column 14 (column 15 stays transparent).

Uniform advance — the formula
-----------------------------
The client computes `advance = round_half_up(ink_w * height / cellHeight) + 1`
(BitmapProvider#load). With ink_w = {INK_BOX_W}, height 9, cellHeight 16:

    advance = round_half_up(15 * 9 / 16) + 1 = round_half_up(8.4375) + 1 = 8 + 1 = 9

So **every glyph below advances exactly {DIGIT_ADVANCE} px**. Render em is {EM_PX} (measured with
`work/rp_build/probe_hud_digits_nn6.py`: digit ink 15 rows tall -> ~8.4 px on
screen; widest digit '0'/'4' is 12 px <= {INK_BOX_W}, so digits are never distorted; only the
two-letter `ms` ligature is squashed horizontally into the box).

Fixed-width digit group (uniform advance {DIGIT_ADVANCE} px) — number -> PUA mapping
---------------------------------------------------------------
| Codepoint | Glyph id | ink_w (px) | advance (px) |
|---|---|---|---|
{chr(10).join(info_rows[:16])}

Recipe for the HUD plugin (tablist/sidebar numeric columns):

1. **Format the number** into an ASCII string over the alphabet `[0-9 . , k M T]`
   plus the optional suffix `ms` — the exact output shape of
   `HudFormat.fmtBounty` / `fmtCash` (`12.3k`, `1.5M`, `1,250,000`, `34ms`, `2T`).
2. **padLeft** the string with ASCII spaces (`U+0020`, advance 4 px from
   `minecraft:include/space`) to the column width — unchanged from NN5.
3. **Map character by character**:
   * `'0'`..`'9'` -> `(char)(0xE040 + d)`
   * `'.'` -> `U+E04A`, `','` -> `U+E04B`
   * `'k'` -> `U+E04C`, `'M'` -> `U+E04D`, `'T'` -> `U+E04E`
   * the suffix `"ms"` (both chars together) -> the single ligature `U+E04F`
4. **Column width math**: a mapped glyph costs 9 px, an ASCII space 4 px. A right
   aligned column of W px fits `n * 9 + s * 4 <= W`.
5. **Fallback**: Bedrock clients and `use-glyphs=false` keep the plain ASCII
   string (the existing `glyphsFor()` branch). Any character that is NOT in the
   table above (e.g. a `B` for billion) must be left as ASCII — vanilla renders
   it, the column just loses monospacing for that one char. Do NOT invent
   codepoints.

Ornament + frame glyphs (U+E050..U+E05D) — measured advances
------------------------------------------------------------
| Codepoint | Glyph id | advance (px) | Shape (16x16 cell) |
|---|---|---|---|
{chr(10).join(orn_rows)}

* `rule-l/m/r`: 3-piece horizontal rule, body rows 13-14, end caps rows 13-15 —
  chain N x `rule-m` between `rule-l` and `rule-r` to stretch.
* `vbar`: 2 px column separator, full height (advance {advance_of(px_img(p_vbar))} px).
* `row-bg`: full-cell background — tint with a dark colour code and chain
  horizontally to paint a row.
* `spark`: 4-point star, centred.
* `frame-*`: 1 px edges for one-row tablist frames:
  `[tl][tm]...[tr]` / `[ml] + text + [mr]` / `[bl][bm]...[br]`.

Override minecraft:default (assets/minecraft/font/default.json)
---------------------------------------------------------------
Provider chain: `include/space` -> `include/default (uniform=false)` -> `nomnom:ui`
-> **`nomnom:hud`** -> `include/unifont` — the NN6 A1 chain plus this pack's font.
There is **no** `vi_text` reference anywhere (A1). Both packs override the same
file path, so the pack added LAST (second `Player#addResourcePack` call) wins:
send **NomNomUI first, NomNomUI-HUD second** — the HUD override already contains
every provider of the main chain, so no text is lost. `nomnom:ui` (ui.json +
icons.png) ships byte-identical in this pack so icons work even if only the HUD
pack is installed.

Generated by work/rp_build/build_hud.py (NN6) - do not hand edit.
"""
    (OUT / "HUD-INFO.md").write_text(info, encoding="utf-8", newline="\n")
    old_txt = OUT / "HUD-INFO.txt"
    if old_txt.is_file():
        old_txt.unlink()          # replaced by HUD-INFO.md

    # ---- preview -----------------------------------------------------------
    sheet = Image.new("RGB", (COLS * (CELL_W * 6 + 8) + 8, ROWS * (CELL_H * 6 + 26) + 8), (18, 24, 33))
    d = ImageDraw.Draw(sheet)
    lab = ImageFont.truetype(str(TTF), 11)
    for i, (cp, gid, cell) in enumerate(cells):
        row, col = divmod(i, COLS)
        x = 8 + col * (CELL_W * 6 + 8)
        y = 8 + row * (CELL_H * 6 + 26)
        big = cell.resize((CELL_W * 6, CELL_H * 6), Image.NEAREST)
        bg = Image.new("RGBA", big.size, (24, 32, 44, 255))
        bg.alpha_composite(big)
        sheet.paste(bg.convert("RGB"), (x, y))
        adv = advance_of(cell)
        d.text((x, y + CELL_H * 6 + 2), f"U+{cp:04X} {gid} a={adv}", font=lab, fill=(154, 164, 178))
    sheet.save(HERE / "preview_hud_font.png")

    print("== NomNomUI-HUD font build (NN6) ==")
    print(f"  glyphs      : {len(cells)} (U+E040..U+E05D; digits+suffixes E040..E04F)")
    print(f"  geometry    : cell {CELL_W}x{CELL_H}, height {PROVIDER_HEIGHT}, ascent {PROVIDER_ASCENT}, em {EM_PX}")
    print(f"  fixed digits: 16 glyphs advance={DIGIT_ADVANCE}px (ink box {INK_BOX_W}px, right edge col 14)")
    print(f"  ornaments   : {len(ORNAMENTS)} (measured advances)")
    print(f"  atlas       : [{COLS * CELL_W}, {ROWS * CELL_H}]")
    for cp, gid, iw, adv in measured[:16]:
        print(f"    U+{cp:04X} {gid:11} ink_w={iw:2d} adv={adv}px")
    print(f"  out         : {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
