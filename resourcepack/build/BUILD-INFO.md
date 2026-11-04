# BUILD-INFO — NomNomUI v1.0.0

| Trường | Giá trị |
|---|---|
| Ngày build | 2026-11-05 |
| Nguồn | `resourcepack/assets/**` (202 file UI) + `assets/weapons/**` (22 file) |
| Số file zip | 229 |
| PNG / JSON | 135 / 87 |
| Kích thước | 124.462 bytes |
| `pack_format` | 75 (resource pack 1.21.11) |
| SHA-1 | `6ad6cec5ef03ccd4709c22f0e20e3621d1ba0045` |
| SHA-256 | `00d13fea7089b1742e430d8a71a869c13e68f97c7a930f53dfb6389674137e86` |
| Placeholder | 0 |
| Item definition phải sửa | 0 |

## Tái lập

```bash
cd resourcepack
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.0.0.zip
# sha1 phải bằng 6ad6cec5ef03ccd4709c22f0e20e3621d1ba0045
```

Đã kiểm: build trong repo và build từ workspace phát triển (merge weapons trực tiếp từ
`downloads/weapons_rp.zip`) cho **cùng SHA-1**. Chạy 2 lần cùng nguồn cũng cho cùng hash.

## Nội dung đã kiểm

- 229 entry, không entry trùng/path traversal/file rác; CRC OK.
- `pack.mcmeta` format 75, description tiếng Việt.
- 87 JSON parse OK; 135 PNG mở được và đúng kích thước quy định.
- Font: 385 glyph text (U+0021..U+1EF9), 48 glyph icon (U+E000..U+E02F), 146/146 tiếng Việt.
- 35 item definition resolve 35 model resolve 35 texture.
- 22 file `assets/weapons/**` khớp **nguyên byte** với `weapons_rp.zip` (đã so trong workspace).
