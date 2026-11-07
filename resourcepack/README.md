# NomNom UI — resource pack

The official UI pack of **NomNom SMP** (Paper 1.21.11): PUA icon glyphs, the
light-theme GUI texture kit for market / cash / land / casino / mini, plus the
bundled weapons-plus weapon textures.

- Version: **1.2.0**
- `pack_format`: **75** (resource pack, Minecraft 1.21.11)
- Build: `resourcepack/build/build_pack.py` — deterministic zip, emits sha1/sha256.
- Install: copy the zip into `resourcepacks/`, or send it via Paper
  `Player#addResourcePack`.
- After changing packs the client needs **F3+T** or a reconnect to reload fonts.

## Contents
- `assets/minecraft/font/default.json` — NN6 A1 reference-only chain
  `[include/space, include/default(uniform=false), nomnom:ui, include/unifont]`
  (the custom Vietnamese text font was removed in wave 6; `vi_text.png` ships
  unreferenced as a rollback anchor)
- `assets/nomnom/font/ui.json` — icon font `nomnom:ui` (PUA U+E000–U+E035)
- `assets/nomnom/textures/font/*` — font/icon atlases
- `assets/nomnom/textures/gui/*`, `textures/item/ui/*` — light-theme texture kit
- `assets/nomnom/models/item/ui/*`, `items/ui/*` — item model / item definition
- `assets/weapons/**` — weapons-plus weapon textures (CC-BY-4.0)

## Attribution (required)
- **weapons-plus** — author **jfrost3712**, Modrinth project
  [`4pmYLtZ9`](https://modrinth.com/project/4pmYLtZ9), licence **CC-BY-4.0**.
  See `ATTRIBUTION.md` for scope and attribution requirements.
- **Be Vietnam Pro** — SIL Open Font License 1.1, see `LICENSE-OFL.txt`.
- Original UI design: © NomNom SMP.

## Build status
All real assets from `work/rp_src/` (no placeholders).
