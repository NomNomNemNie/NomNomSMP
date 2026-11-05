# NomNom UI resource pack — phát hành & cấu trúc

## 0. Bản phát hành v1.1.0 (đợt 5, 2026-11-06) — pack chính + pack HUD

Release: https://github.com/NomNomNemNie/NomNomSMP/releases/tag/v1.1.0

| Trường | NomNomUI v1.1.0 | NomNomUI-HUD v1.0.0 |
|---|---|---|
| Asset URL | `https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.1.0/NomNomUI-v1.1.0.zip` | `https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.1.0/NomNomUI-HUD-v1.0.0.zip` |
| Kích thước | 138.392 bytes | 12.422 bytes |
| Số file | 275 (161 PNG, 107 JSON, 22 weapons) | 11 (3 PNG, 3 JSON) |
| SHA-1 | `d964fee394ba840c92ea86464589436da38cfae9` | `e5ba4876cf7c68bfc52a858ac8650df2b28bfb41` |
| SHA-256 | `b9f67c4df05933d17c757a37a26119fb467f424ce9d1cfc68964ee62e2ace177` | `b93db1fbc60c023ce300127d829f2e261527ef21e021287561ae6934cd0ddd81` |
| `pack_format` | 75 | 75 |

Validate: `validate_font.py` PASS (30 check, 146/146 tiếng Việt), `validate_pack.py`
PASS cả hai preset (`main` 0 lỗi, `hud` 0 lỗi). Build deterministic — rebuild trong
workspace phát triển và trong repo cho cùng SHA-1 từng pack (đã chạy đối chiếu).

Đổi chính v1.1.0 so với v1.0.0 (A1/A2/A3 đợt 5):

1. **A1 — font nét to, sạch**: render TRỰC TIẾP ở cỡ cuối em **13 px** có hinting
   FreeType (bỏ supersample 4x + LANCZOS của 1.0 — nguyên nhân "nhìn như 480p"),
   curve alpha 36..210 cắt quầng; cell 16x16 → **16x20** (atlas 256x400 → 256x500),
   provider `height 20 / ascent 16`. Glyph to hơn ~26% (cap 7.5 → ~9.4 px).
2. **A2 — icon**: 48 glyph vẽ lại (phong cách NomNom, binary trắng + viền đen,
   advance 9 giữ nguyên) + **6 icon mới** `book, sell, friendly, shop, chat-tag,
   worldtime` tại **U+E030–E035** (48 icon đầu giữ nguyên codepoint — HUD config
   không phải đổi). Thêm **10 item icon 32x32** + model + item definition:
   `sethome, rp, book, sell, auction, friendly, shop, chat-tag, worldtime, sword`.
3. **A3 — pack HUD riêng**: `NomNomUI-HUD` chỉ chứa font `nomnom:hud`
   (digits fixed-width `0-9 . , k M` advance **10 px** tại U+E040–E04D + ornament/khung
   U+E050–E05D cho sidebar/tablist) và copy byte-identical của `nomnom:ui`.
   Override `minecraft:default` của pack HUD là superset (tham chiếu chéo
   `nomnom:font/vi_text.png` của pack chính, thêm `nomnom:hud` trước `include/unifont`)
   — cài cả hai pack không mất chữ; thiếu pack chính thì chữ rơi về fallback vanilla.
   Gửi pack: **NomNomUI trước, NomNomUI-HUD sau**. Bảng glyph + cách căn phải:
   `resourcepack-hud/HUD-INFO.txt` (ship kèm zip).

## 1. Bản phát hành v1.0.0 (lịch sử)

| Trường | Giá trị |
|---|---|
| Phiên bản | **v1.0.0** |
| File | `NomNomUI-v1.0.0.zip` |
| Kích thước | **124.462 bytes** (~121,5 KiB) |
| Số file | **229** (135 PNG, 87 JSON, 22 file weapons) |
| `pack_format` | **75** — resource pack cho Minecraft **1.21.11** |
| SHA-1 | `6ad6cec5ef03ccd4709c22f0e20e3621d1ba0045` |
| SHA-256 | `00d13fea7089b1742e430d8a71a869c13e68f97c7a930f53dfb6389674137e86` |
| Release | https://github.com/NomNomNemNie/NomNomSMP/releases/tag/v1.0.0 |
| Asset URL | https://github.com/NomNomNemNie/NomNomSMP/releases/download/v1.0.0/NomNomUI-v1.0.0.zip |

> Hash chỉ đúng cho đúng file đã phát hành; build lại có thể đổi hash nếu asset/doc đổi.
> Build deterministic: chạy lại cùng nguồn cho cùng hash (đã kiểm 2 lần).

### Vì sao `pack_format` là 75, không phải 94

Prompt đóng gói ban đầu ghi 94, nhưng 94 là **data pack format**. Resource pack của
1.21.11 là **75**:

```text
$ unzip -p local_server/cache/mojang_1.21.11.jar version.json
"pack_version": { "resource_major": 75, "resource_minor": 0,
                  "data_major": 94, "data_minor": 1 }
```

Quyết định: dùng **75** (đã xác nhận với chủ workflow). Dùng 94 sẽ khiến client
1.21.11 đánh dấu pack không tương thích.

## 2. Cấu trúc pack

```text
pack.mcmeta                              # pack_format 75, description tiếng Việt
pack.png                                 # icon pack (sinh bởi build_pack.py)
README.md / ATTRIBUTION.md / LICENSE-OFL.txt
assets/
  minecraft/font/default.json            # override THẬT của minecraft:default
  nomnom/
    font/ui.json                         # font icon nomnom:ui (PUA U+E000–E02F)
    font/default.json                    # alias font nomnom:default
    font/FONT-INFO.txt, charset.tsv      # provenance + bảng 385 glyph
    textures/font/vi_text.png            # 256×400, 16×25 cell 16 px
    textures/font/icons.png              # 128×96, 8×6 cell 16 px
    textures/icon/*.png                  # 48 icon rời 16×16 (nguồn)
    textures/gui/*.png                   # panel 9-slice, titlebar, divider, slot
    textures/gui/items/**                # mirror 35 texture item (không model nào trỏ)
    textures/item/ui/**                  # 24 texture item 16×16 + 11 icon 32×32
    models/item/ui/**                    # 35 model (parent item/generated)
    items/ui/**                          # 35 item definition (minecraft:model)
  weapons/**                             # 22 file weapons-plus, giữ nguyên đường dẫn
```

- Font text: **385 glyph**, phủ **146/146** ký tự tiếng Việt precomposed; space lấy từ
  `minecraft:include/space`; fallback `include/default` → `nomnom:ui` → `include/unifont`.
- Icon: **48 codepoint** U+E000–U+E02F, `height/ascent = 9/9`; alias `confirm→check`,
  `cancel→cross`; mọi nơi dùng icon đều có fallback ASCII (Bedrock/Geyser không render custom font).
- Menu dùng item definition ID `nomnom:ui/<name>`; model ID là `nomnom:item/ui/<name>`.
  Ba tầng ID này **không được lẫn** (xem `docs/icons.md`).

## 3. Build & validate

Nguồn canonical nằm trong repo này. Chạy từ thư mục `resourcepack/`:

```bash
python build/build_font.py --verify-only     # font + 48 icon khớp asset đã commit
python build/build_gui.py --check            # 147 file texture/model/definition khớp
python build/build_pack.py --no-weapons --out dist/NomNomUI-v1.0.0.zip
python build/validate_pack.py --zip dist/NomNomUI-v1.0.0.zip
```

- `build_pack.py` ghép `resourcepack/assets/**`, sinh `pack.mcmeta` + docs, xuất zip
  deterministic và in SHA-1/SHA-256.
- `--no-weapons` dùng `assets/weapons/**` đã commit. Khi build từ workspace phát triển,
  bỏ cờ này để merge trực tiếp từ `downloads/weapons_rp.zip` (copy nguyên byte).
- `validate_pack.py` kiểm: zip CRC/entry trùng/path traversal/file rác, `pack.mcmeta`,
  toàn bộ JSON, PNG mở được + đúng kích thước, font provider trỏ đúng atlas, dải PUA
  48 glyph, item definition → model → texture, weapons khớp byte với nguồn (khi có zip nguồn).
- Trong repo không có `downloads/weapons_rp.zip`, nên validator chỉ cảnh báo "không kiểm
  merge weapons"; kiểm byte-for-byte đã chạy trong workspace phát triển (22/22 file khớp).

### Kết quả validate bản v1.0.0

```text
$ python work/rp_build/validate_pack.py --zip work/rp_build/dist/NomNomUI-v1.0.0.zip
[PASS] .../NomNomUI-v1.0.0.zip
  files=229 png=135 json=87 weapons=22 format=75
  font assets/minecraft/font/default.json: glyphs=385 cells=400 range=U+0021..U+1EF9
  font assets/nomnom/font/default.json: glyphs=385 cells=400 range=U+0021..U+1EF9
  font assets/nomnom/font/ui.json: glyphs=48 cells=48 range=U+E000..U+E02F
  => PASS (0 lỗi, 0 cảnh báo)
```

Build lại trong repo cho **cùng SHA-1** `6ad6cec5…` với build từ workspace phát triển.

## 4. Ghi công & giấy phép

- **weapons-plus** — tác giả **jfrost3712**, Modrinth `4pmYLtZ9`, **CC-BY-4.0**.
  Toàn bộ `assets/weapons/**` được phân phối lại, giữ nguyên đường dẫn và byte.
  Xem `docs/ATTRIBUTION.md`.
- **Be Vietnam Pro** — SIL OFL 1.1, Copyright 2021 The Be Vietnam Pro Project Authors;
  `LICENSE-OFL.txt` kèm trong pack và repo.
- Phần UI tự thiết kế: © NomNom SMP.

CC-BY-4.0 yêu cầu giữ tên tác giả, link giấy phép, link nguồn và ghi rõ sửa đổi.
Không xoá `ATTRIBUTION.md`/`README.md` khi phát hành lại.

## 5. Phân phối cho server

- Server Paper gửi pack phụ bằng `Player#addResourcePack(uuid, url, hash, prompt, force)`;
  dùng SHA-1 ở trên cho tham số `hash` (Paper nhận SHA-1 hex).
- Repo hiện là **PRIVATE**. GitHub Releases của repo private yêu cầu xác thực, nên
  client Minecraft **không tải được** asset URL. Để phát hành cho người chơi, chọn một trong:
  1. chủ repo bật **Public** (quyết định của chủ sở hữu, không tự đổi), hoặc
  2. mirror `NomNomUI-v1.0.0.zip` lên URL công khai (CDN/S3/static host) và dùng URL đó,
     giữ nguyên hash.
- Sau khi đổi pack, client cần **F3+T** hoặc reconnect để nạp lại font.
- Chưa test render trong client Java/Bedrock thật (máy DEV không đủ RAM chạy server đầy đủ);
  đây là gate QA trước khi coi là bản cuối cho production.
