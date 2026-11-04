# Build scripts — NomNom UI resource pack

Các script dưới đây chạy trực tiếp trong repo này, với `resourcepack/` là root pack.
Bản gốc được phát triển trong workspace `work/rp_build/`; bản ở đây đã chỉnh đường dẫn
(`RP = resourcepack/`, `ICON_JSON = resourcepack/icons.json`) để tự chứa.

## Yêu cầu

- Python **3.11+** (đã chạy với 3.14.5)
- `Pillow` (12.2.0), `fonttools` (4.63.0)

```bash
pip install pillow fonttools
```

## Lệnh

Chạy từ thư mục `resourcepack/`:

```bash
# 1. Kiểm font + 48 icon khớp asset đã commit (không ghi file)
python build/build_font.py --verify-only

# 2. Kiểm 147 file texture/model/item definition khớp regenerate
python build/build_gui.py --check

# 3. Đóng gói (dùng assets/weapons đã commit)
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.0.0.zip

# 4. Validate zip
python build/validate_pack.py --zip dist/NomNomUI-v1.0.0.zip
```

- `build_font.py` sinh `assets/minecraft/font/default.json`, `assets/nomnom/font/**`,
  `textures/font/*.png`, `textures/icon/*.png`, `LICENSE-OFL.txt`.
- `build_gui.py` sinh `textures/gui/**`, `textures/item/ui/**`, `models/item/ui/**`,
  `items/ui/**` và mirror `textures/gui/items/**`.
- `build_pack.py` ghép toàn bộ `assets/**`, sinh `pack.mcmeta` (format **75**) +
  `README.md`/`ATTRIBUTION.md`/`LICENSE-OFL.txt`, xuất zip deterministic, in SHA-1/SHA-256.
  - `--ui-src DIR` đổi nguồn asset (mặc định `resourcepack/`).
  - `--weapons ZIP` merge `assets/weapons/**` từ pack nguồn (copy nguyên byte).
  - `--no-weapons` dùng weapons đã có trong nguồn.
  - `--no-placeholders` fail nếu thiếu asset thật (mặc định dùng placeholder để pack vẫn hợp lệ).
- `validate_pack.py` kiểm zip/JSON/PNG/font/item model/attribution; nếu có
  `downloads/weapons_rp.zip` thì so byte 22 file weapons với nguồn.
- `validate_font.py` kiểm chi tiết atlas font (30 check của agent font).
- `make_placeholders.py` sinh placeholder khi asset thật chưa có; build sẽ tự thay bằng
  file thật và liệt kê placeholder còn lại trong `PLACEHOLDERS.txt`.

## Font & giấy phép

`build/fonts/` chứa Be Vietnam Pro Regular/Bold + `OFL.txt` (SIL OFL 1.1,
Copyright 2021 The Be Vietnam Pro Project Authors). Các script kiểm SHA-256 của TTF/OFL
trước khi build để tránh tráo nguồn.

## Ghi chú

- Build deterministic: timestamp zip cố định `2026-01-01`, thứ tự entry sort, nén DEFLATE 9.
- `assets/nomnom/textures/gui/items/**` là mirror byte-identical của 35 texture item;
  **không model nào tham chiếu** — canonical là `textures/item/ui/**`.
- Chưa test render trong client Java/Bedrock; `pack_format` đã đối chiếu
  `version.json` của 1.21.11 (`resource_major = 75`).
