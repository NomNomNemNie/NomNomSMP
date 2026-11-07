NomNomUI-HUD v1.1.0 — font `nomnom:hud` (wave 6, A2)
=============================================

Scope: glyphs for the sidebar + tablist ONLY. No Vietnamese text font is shipped
(the custom text font was dropped from both packs in wave 6 A1 — the old 20 px
glyph boxes overlapped MC's fixed 9 px lines by 11 px).

Geometry (vanilla scale)
------------------------
* Atlas: `assets/nomnom/textures/font/hud.png`, 128x64 px, 8x4 cells of **16x16**.
* Provider: `"height": 9, "ascent": 9` — the client renders every
  16x16 cell as a **9x9 px box** (pixelScale = 9/16), exactly one Minecraft text
  line, so a glyph can never bleed into the next row.
* Baseline: ascent 9 puts the text baseline at the glyph's bottom edge (same
  convention as unifont). All digit ink is bottom-pinned at atlas row 15, so
  numbers sit ON the baseline.
* Ink box: every fixed-width glyph's ink is forced into a **15 px wide box** with the
  RIGHT edge pinned at atlas column 14 (column 15 stays transparent).

Uniform advance — the formula
-----------------------------
The client computes `advance = round_half_up(ink_w * height / cellHeight) + 1`
(BitmapProvider#load). With ink_w = 15, height 9, cellHeight 16:

    advance = round_half_up(15 * 9 / 16) + 1 = round_half_up(8.4375) + 1 = 8 + 1 = 9

So **every glyph below advances exactly 9 px**. Render em is 20 (measured with
`work/rp_build/probe_hud_digits_nn6.py`: digit ink 15 rows tall -> ~8.4 px on
screen; widest digit '0'/'4' is 12 px <= 15, so digits are never distorted; only the
two-letter `ms` ligature is squashed horizontally into the box).

Fixed-width digit group (uniform advance 9 px) — number -> PUA mapping
---------------------------------------------------------------
| Codepoint | Glyph id | ink_w (px) | advance (px) |
|---|---|---|---|
| U+E040 | `digit-0` | 15 | **9** |
| U+E041 | `digit-1` | 15 | **9** |
| U+E042 | `digit-2` | 15 | **9** |
| U+E043 | `digit-3` | 15 | **9** |
| U+E044 | `digit-4` | 15 | **9** |
| U+E045 | `digit-5` | 15 | **9** |
| U+E046 | `digit-6` | 15 | **9** |
| U+E047 | `digit-7` | 15 | **9** |
| U+E048 | `digit-8` | 15 | **9** |
| U+E049 | `digit-9` | 15 | **9** |
| U+E04A | `dot` | 15 | **9** |
| U+E04B | `comma` | 15 | **9** |
| U+E04C | `k-suffix` | 15 | **9** |
| U+E04D | `m-suffix` | 15 | **9** |
| U+E04E | `t-suffix` | 15 | **9** |
| U+E04F | `ms-suffix` | 15 | **9** |

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
| U+E050 | `rule-l` | 10 | left cap of the horizontal rule |
| U+E051 | `rule-m` | 10 | middle segment of the horizontal rule |
| U+E052 | `rule-r` | 10 | right cap of the horizontal rule |
| U+E053 | `vbar` | 6 | 2 px vertical column separator, full height |
| U+E054 | `row-bg` | 10 | full-cell background (chain horizontally) |
| U+E055 | `spark` | 8 | 4-point star, centred |
| U+E056 | `frame-tl` | 10 | frame corner top-left |
| U+E057 | `frame-tm` | 10 | frame edge top-middle |
| U+E058 | `frame-tr` | 10 | frame corner top-right |
| U+E059 | `frame-ml` | 2 | frame edge mid-left |
| U+E05A | `frame-mr` | 10 | frame edge mid-right |
| U+E05B | `frame-bl` | 10 | frame corner bottom-left |
| U+E05C | `frame-bm` | 10 | frame edge bottom-middle |
| U+E05D | `frame-br` | 10 | frame corner bottom-right |

* `rule-l/m/r`: 3-piece horizontal rule, body rows 13-14, end caps rows 13-15 —
  chain N x `rule-m` between `rule-l` and `rule-r` to stretch.
* `vbar`: 2 px column separator, full height (advance 6 px).
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
