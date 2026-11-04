# NomNom UI — resource pack

Pack UI chính thức của **NomNom SMP** (Paper 1.21.11): font tiếng Việt, bộ icon glyph
và texture GUI cho market / cash / land / casino / mini.

- Phiên bản: **1.0.0**
- `pack_format`: **75** (resource pack, Minecraft 1.21.11)
- Build: `resourcepack/build/build_pack.py` — zip deterministic, sinh sha1/sha256.
- Cài đặt: chép zip vào `resourcepacks/`, hoặc gửi qua Paper `Player#addResourcePack`.
- Sau khi đổi pack, client cần **F3+T** hoặc reconnect để nạp lại font.

## Nội dung
- `assets/minecraft/font/default.json` — override font mặc định (khi có atlas thật)
- `assets/nomnom/font/ui.json` — font icon `nomnom:ui` (PUA U+E000–U+E02F)
- `assets/nomnom/textures/font/*` — atlas font/icon
- `assets/nomnom/textures/gui/*`, `textures/item/ui/*` — texture kit
- `assets/nomnom/models/item/ui/*`, `items/ui/*` — item model / item definition
- `assets/weapons/**` — texture vũ khí weapons-plus (CC-BY-4.0)

## Ghi công (bắt buộc)
- **weapons-plus** — tác giả **jfrost3712**, Modrinth project
  [`4pmYLtZ9`](https://modrinth.com/project/4pmYLtZ9), giấy phép **CC-BY-4.0**.
  Xem `ATTRIBUTION.md` để biết phạm vi và yêu cầu ghi công.
- **Be Vietnam Pro** — SIL Open Font License 1.1, xem `LICENSE-OFL.txt`.
- Phần UI tự thiết kế: © NomNom SMP.

## Trạng thái build
Đầy đủ asset thật từ `work/rp_src/` (không có placeholder).
