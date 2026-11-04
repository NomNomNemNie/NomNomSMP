# NomNom SMP — Resource Pack & UI Kit

Bộ resource pack chính thức của **NomNom SMP** (Paper **1.21.11**): font tiếng Việt,
48 icon glyph, texture GUI market / cash / land / casino / mini và item model cho
tablist/scoreboard.

## Phát hành

| | |
|---|---|
| Phiên bản | **v1.0.0** |
| Asset | [`NomNomUI-v1.0.0.zip`](https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.0.0/NomNomUI-v1.0.0.zip) |
| Kích thước | 124.462 bytes · 229 file |
| SHA-1 | `6ad6cec5ef03ccd4709c22f0e20e3621d1ba0045` |
| SHA-256 | `00d13fea7089b1742e430d8a71a869c13e68f97c7a930f53dfb6389674137e86` |
| `pack_format` | **75** (resource pack 1.21.11; 94 là data pack) |
| Release | https://github.com/NomNomNemNie/NomNomSMP/releases/tag/v1.0.0 |

Chi tiết build, cấu trúc pack, kết quả validate và hướng dẫn phân phối:
**[`docs/pack.md`](docs/pack.md)**.

> Repo hiện là **private**: asset GitHub Releases yêu cầu xác thực nên client Minecraft
> không tải được. Cần bật Public hoặc mirror zip ra URL công khai trước khi gửi cho player
> (xem `docs/pack.md` §5). Không tự đổi visibility.

## Nội dung

- `resourcepack/` — nguồn pack canonical (assets + `pack.mcmeta` + `pack.png`)
  - `resourcepack/build/` — script sinh font/GUI/đóng gói/validate (chạy được trong repo)
  - `resourcepack/icons.json` — manifest 48 icon (codepoint, ASCII fallback)
- `docs/design-tokens.md` — palette, kích thước, quy chuẩn panel/nút/icon
- `docs/icons.md` — bảng 48 glyph `nomnom:ui` + fallback ASCII
- `docs/ATTRIBUTION.md` — ghi công CC-BY-4.0 (weapons-plus) + OFL (Be Vietnam Pro)
- `docs/pack.md` — phát hành, cấu trúc, build/validate, phân phối

## Build & validate

Chạy từ thư mục `resourcepack/`:

```bash
python build/build_font.py --verify-only
python build/build_gui.py --check
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.0.0.zip
python build/validate_pack.py --zip dist/NomNomUI-v1.0.0.zip
```

Build deterministic (cùng nguồn → cùng SHA-1). Kết quả v1.0.0: **229 file**,
`pack_format 75`, font **385 glyph** (146/146 tiếng Việt), **48 icon** U+E000–E02F,
**22 file weapons** giữ nguyên byte so với pack nguồn.

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
