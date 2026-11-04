# NomNom UI resource pack — phát hành & cấu trúc

## 1. Bản phát hành

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
