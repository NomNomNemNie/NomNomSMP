# BUILD-INFO — NomNomUI-HUD v1.1.0 (wave 6, NN6 A2)

| Field | Value |
|---|---|
| Build date | 2026-11-07 |
| Source | `resourcepack-hud/assets/**` (5 files) + `HUD-INFO.md` |
| Zip files | 11 |
| PNG / JSON | 3 / 3 |
| Size | 13,441 bytes |
| `pack_format` | 75 (resource pack 1.21.11) |
| SHA-1 | `2e5f2e4152ef6392d77f8b5df4a55cba6bf99b46` |
| SHA-256 | `63fb53a832bec34471845938aea2377db5385245e44bb5ba30283b1a233625e9` |

## What changed vs v1.0.0 (wave 6 A2)

- **Re-render at vanilla scale**: cell 16x20 / height 20 / ascent 16 ->
  **cell 16x16, height 9 / ascent 9** (atlas 128x80 -> 128x64). Each glyph now
  renders as exactly one 9 px text line — the old 20 px boxes overlapped the
  next row by 11 px.
- **Digit set extended**: `0-9 . , k M` (U+E040–E04D) -> `0-9 . , k M T` + the
  `ms` ligature (**U+E040–U+E04F**, 16 glyphs). Ornament/frame glyphs stay at
  U+E050–E05D, re-fitted to the 16-row cell.
- **Uniform advance, measured not declared**: every digit-group glyph's ink is
  forced into a 15 px box with the right edge pinned at atlas column 14 =>
  client advance = `round_half_up(15 * 9 / 16) + 1 = 9` px for ALL 16 glyphs.
  (`validate_pack.py` now measures this from the shipped atlas.)
- **No vi_text anywhere**: the override `minecraft:default` is the wave-6 A1
  chain `[include/space, include/default(uniform=false), nomnom:ui, nomnom:hud,
  include/unifont]` — the v1.0.0 cross-reference to the main pack's text atlas
  is gone (A1 removed that font from both packs).
- `HUD-INFO.txt` replaced by **`HUD-INFO.md`** (shipped in the zip): glyph
  table, the advance formula, and the number -> PUA mapping recipe for the HUD
  agent (map `0-9` -> U+E040+d, `.` -> E04A, `,` -> E04B, `k` -> E04C,
  `M` -> E04D, `T` -> E04E, suffix `ms` -> E04F; pad with ASCII spaces, 9 px
  per glyph, 4 px per space; Bedrock / use-glyphs=false keeps ASCII).

## Rebuild (deterministic, self-contained)

```bash
cd resourcepack-hud
python build/build_hud.py
python build/build_hud_pack.py --version 1.1.0 --out dist/NomNomUI-HUD-v1.1.0.zip
```

Same source -> same SHA-1 `2e5f2e41…` (verified 2026-11-07, rebuild inside this
repo).
