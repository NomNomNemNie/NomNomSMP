# BUILD-INFO — NomNomUI v1.1.0 (đợt 5, NN5)

| Trường | Giá trị |
|---|---|
| Ngày build | 2026-11-06 |
| Nguồn | `resourcepack/assets/**` (270 file UI) + `assets/weapons/**` (22 file) |
| Số file zip | 275 |
| PNG / JSON | 161 / 107 |
| Kích thước | 138.392 bytes |
| `pack_format` | 75 (resource pack 1.21.11) |
| SHA-1 | `d964fee394ba840c92ea86464589436da38cfae9` |
| SHA-256 | `b9f67c4df05933d17c757a37a26119fb467f424ce9d1cfc68964ee62e2ace177` |
| Placeholder | 0 |
| Item definition phải sửa | 0 |

## Đổi gì so với v1.0.0

- **Font (A1)**: render lại toàn bộ 385 glyph — em 10.31 → **13 px** (glyph to hơn ~26%),
  cell 16x16 → **16x20** (atlas 256x400 → 256x500), provider height 16→20, ascent 13→16.
  Kỹ thuật: render TRỰC TIẾP ở cỡ cuối có hinting FreeType (bỏ supersample 4x + LANCZOS
  của 1.0) + curve alpha 36..210 — nét sạch, hết "480p".
- **Icon (A2)**: 48 glyph vẽ lại + **6 icon mới** U+E030–E035 (book, sell, friendly, shop,
  chat-tag, worldtime); atlas icons.png 128x96 → 128x112.
- **Item model (A2/A5)**: thêm 10 icon 32x32 + model + item definition: sethome, rp, book,
  sell, auction, friendly, shop, chat-tag, worldtime, sword → tổng 21 icon item.
- weapons-plus giữ nguyên byte (22 file, CC-BY-4.0 attribution không đổi).

## Tái lập

```bash
cd resourcepack
python build/build_font.py          # font + 54 glyph icon
python build/build_gui.py           # 187 file texture/model/definition
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.1.0.zip
python build/validate_font.py
python build/validate_pack.py --zip dist/NomNomUI-v1.1.0.zip
```

Build deterministic: rebuild trong workspace phát triển và trong repo cho **cùng SHA-1**
`d964fee…` (đã chạy đối chiếu 2026-11-06).
