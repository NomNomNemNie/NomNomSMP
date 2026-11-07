# NomNomUI-HUD — resource pack for the sidebar + tablist

Companion pack of **NomNom SMP** (Paper 1.21.11), separate from the main pack
**NomNomUI**: contains only the column-alignment glyphs/ornaments/frames for the
scoreboard (sidebar) and tablist.

- Version: **1.1.0**
- `pack_format`: **75** (resource pack, Minecraft 1.21.11)
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
