# BUILD-INFO — NomNomUI v1.2.0 (wave 6, NN6)

| Field | Value |
|---|---|
| Build date | 2026-11-07 |
| Source | `resourcepack/assets/**` (248 UI files incl. the retired vi_text atlas + 22 weapons files) |
| Zip files | 275 |
| PNG / JSON | 161 / 107 |
| Size | 136,884 bytes |
| `pack_format` | 75 (resource pack 1.21.11) |
| SHA-1 | `b46aab6df436d6c463253ecb3b08cf1b3a9b6813` |
| SHA-256 | `7e6845d6cd022c66bf28c9759a9ab55dfa7df803e3b55741a1909af3ae19d2a7` |
| Placeholders | 0 |
| Item definitions normalized | 0 |

## What changed vs v1.1.0 (wave 6 A1 + A3)

- **A1 — custom text font dropped**: `assets/minecraft/font/default.json` (and the
  `nomnom:default` alias) no longer carry the `vi_text` bitmap provider. The
  `minecraft:default` chain is now exactly
  `[minecraft:include/space, minecraft:include/default (filter.uniform=false), nomnom:ui, minecraft:include/unifont]`.
  Root cause: the 20 px text glyph boxes overlapped Minecraft's fixed 9 px line
  height by 11 px (owner sidebar screenshot, wave 6). `vi_text.png` is STILL
  SHIPPED, unreferenced, as a rollback anchor. All text renders with the vanilla
  providers (full Vietnamese coverage via include/default + unifont).
- **A3 — light GUI theme**: panels (`panel_primary/inset/raised`, `titlebar`,
  `divider`), slots (`slot_inset`, `slot_border`) and the item kit (`bg`,
  `border`, `card`, `title`) repainted to a clean paper-white look
  (`bg.png` mean RGB (22,30,40) -> (230,233,238)); **arrows**
  (`btn_gray_prev/next/back/close`) render **black** on the light neutral
  buttons; gold accents unchanged (`btn_gold` mean RGB still (171,136,64)).
  Neutral (gray) buttons + the disabled state flipped to light as part of the theme.
- Icon font `nomnom:ui` (54 glyphs, U+E000–U+E035) unchanged.
- weapons-plus kept byte-identical (22 files, CC-BY-4.0 attribution unchanged).

## Rebuild (deterministic)

From `resourcepack/` (the merged weapons live inside `assets/weapons/**`, so the
repo is self-contained):

```bash
cd resourcepack
python build/build_gui.py --check
python build/validate_font.py
python build/build_pack.py --version 1.2.0 --ui-src . --no-weapons \
    --out dist/NomNomUI-v1.2.0.zip
python build/validate_pack.py --zip dist/NomNomUI-v1.2.0.zip
```

Same source -> same SHA-1 (fixed zip timestamps, sorted entries).
