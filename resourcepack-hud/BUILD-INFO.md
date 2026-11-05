# BUILD-INFO — NomNomUI-HUD v1.0.0 (đợt 5, A3)

| Trường | Giá trị |
|---|---|
| Ngày build | 2026-11-06 |
| Nguồn | `resourcepack-hud/assets/**` (6 file) + HUD-INFO.txt |
| Số file zip | 11 |
| PNG / JSON | 3 / 3 |
| Kích thước | 12.422 bytes |
| `pack_format` | 75 (resource pack 1.21.11) |
| SHA-1 | `e5ba4876cf7c68bfc52a858ac8650df2b28bfb41` |
| SHA-256 | `87e22c1e6c5da67e8f88088dd0fe26b743f5cb229707b9b971e9efd319e44348` |

## Nội dung

- Font `nomnom:hud` (atlas `hud.png` 128x80, 28 glyph PUA U+E040–U+E05D):
  digits fixed-width `0-9 . , k M` (advance 10 px) + ornament/khung (rule, vbar,
  row-bg, spark, frame 8 mảnh).
- Copy byte-identical `nomnom:ui` (ui.json + icons.png) — icon chạy độc lập thứ tự pack.
- Override `minecraft:default` superset: tham chiếu chéo `nomnom:font/vi_text.png`
  của pack chính + thêm `nomnom:hud` trước `include/unifont`.
- KHÔNG chứa vi_text.png / gui textures / item models / weapons (validator chặn).

## Tái lập

```bash
cd resourcepack-hud
python build/build_hud.py           # font HUD (cần TTF ở resourcepack/build/fonts)
python build/build_hud_pack.py --out dist/NomNomUI-HUD-v1.0.0.zip
python ../resourcepack/build/validate_pack.py --preset hud --zip dist/NomNomUI-HUD-v1.0.0.zip
```

Build deterministic: workspace và repo cho **cùng SHA-1** `e5ba4876…` (đã đối chiếu).
