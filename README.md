# NomNom SMP — Resource Pack & UI Kit

Bộ resource pack chính thức của **NomNom SMP** (Paper **1.21.11**): font tiếng Việt,
**54 icon glyph**, texture GUI market / cash / land / casino / mini, item model cho
menu/GUI và **pack phụ riêng cho sidebar + tablist**.

## Phát hành (v1.1.0 — đợt 5)

| | NomNomUI v1.1.0 (pack chính) | NomNomUI-HUD v1.0.0 (pack phụ) |
|---|---|---|
| Asset | [`NomNomUI-v1.1.0.zip`](https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.1.0/NomNomUI-v1.1.0.zip) | [`NomNomUI-HUD-v1.0.0.zip`](https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.1.0/NomNomUI-HUD-v1.0.0.zip) |
| Kích thước | 138.392 bytes · 275 file | 12.422 bytes · 11 file |
| SHA-1 | `d964fee394ba840c92ea86464589436da38cfae9` | `e5ba4876cf7c68bfc52a858ac8650df2b28bfb41` |
| Nội dung | font VI nét cao cấp (em 13, cell 16x20), 54 icon, 21 item icon, weapons | digits fixed-width + ornament/khung sidebar/tablist (`nomnom:hud`) |
| Release | https://github.com/NomNomNemNie/NomNomSMP/releases/tag/v1.1.0 | cùng release v1.1.0 |

`pack_format` **75** (resource pack 1.21.11; 94 là data pack) cho cả hai.
Gửi pack cho player: **NomNomUI trước, NomNomUI-HUD sau** (`Player#addResourcePack`).

Chi tiết build, cấu trúc pack, kết quả validate và hướng dẫn phân phối:
**[`docs/pack.md`](docs/pack.md)**.

## Nội dung

- `resourcepack/` — nguồn pack chính canonical (assets + `pack.mcmeta` + `pack.png`)
  - `resourcepack/build/` — script sinh font/GUI/đóng gói/validate (chạy được trong repo)
  - `resourcepack/icons.json` — manifest 54 icon (codepoint, ASCII fallback)
- `resourcepack-hud/` — nguồn pack HUD canonical (font `nomnom:hud`, digits fixed-width,
  ornament/khung; `HUD-INFO.txt` liệt kê bảng glyph + cách căn phải cột số)
- `docs/design-tokens.md` — palette, kích thước, quy chuẩn panel/nút/icon
- `docs/icons.md` — bảng 54 glyph `nomnom:ui` + bảng glyph `nomnom:hud` + fallback ASCII
- `docs/ATTRIBUTION.md` — ghi công CC-BY-4.0 (weapons-plus) + OFL (Be Vietnam Pro)
- `docs/pack.md` — phát hành, cấu trúc, build/validate, phân phối

## Build & validate

Chạy từ thư mục `resourcepack/`:

```bash
python build/build_font.py            # font + 54 glyph icon (hoặc --verify-only)
python build/build_gui.py --check     # 187 file texture/model/definition
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.1.0.zip
python build/validate_font.py
python build/validate_pack.py --zip dist/NomNomUI-v1.1.0.zip
```

Pack HUD (từ `resourcepack-hud/`):

```bash
python build/build_hud.py
python build/build_hud_pack.py --out dist/NomNomUI-HUD-v1.0.0.zip
python ../resourcepack/build/validate_pack.py --preset hud --zip dist/NomNomUI-HUD-v1.0.0.zip
```

Build deterministic (cùng nguồn → cùng SHA-1, đã đối chiếu rebuild workspace ↔ repo).
Kết quả v1.1.0: **275 file**, `pack_format 75`, font **385 glyph** (146/146 tiếng Việt,
render trực tiếp em 13 có hinting), **54 icon** U+E000–E035 (48 đầu giữ codepoint v1.0),
**21 item icon 32x32**, **22 file weapons** giữ nguyên byte so với pack nguồn.
HUD v1.0.0: **11 file**, 28 glyph U+E040–E05D (digits advance cố định 10 px).

## Ghi công (bắt buộc — CC-BY-4.0)

- **weapons-plus** — tác giả **jfrost3712**, Modrinth project
  [`4pmYLtZ9`](https://modrinth.com/project/4pmYLtZ9), giấy phép
  [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
  Pack phân phối lại `assets/weapons/**` nguyên byte, giữ nguyên đường dẫn.
  Chi tiết & phạm vi: [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md).
- **Be Vietnam Pro** — SIL Open Font License 1.1,
  Copyright 2021 The Be Vietnam Pro Project Authors; xem `LICENSE-OFL.txt`.
- Phần UI tự thiết kế (palette, panel, button, badge, icon, layout): © NomNom SMP.

Không xoá các file ghi công khi phát hành lại.
