# NomNomUI-HUD — resource pack cho sidebar + tablist

Pack phụ của **NomNom SMP** (Paper 1.21.11), tách khỏi pack chính **NomNomUI**:
chỉ chứa glyph/ornament/khung căn cột cho scoreboard (sidebar) + tablist.

- Phiên bản: **1.0.0**
- `pack_format`: **75** (resource pack, Minecraft 1.21.11)
- Font riêng `nomnom:hud` — PUA **U+E040–U+E05D**:
  - **Digits fixed-width** `0-9 . , k M` (U+E040–U+E04D) — mọi glyph advance 10 px
    => cột số liệu căn phải TUYỆT ĐỐI (map từng ký tự sau khi padLeft).
  - Ornament + khung (U+E050–U+E05D): rule 3-mảnh, vbar, row-bg, spark, khung 8-mảnh.
- Copy byte-identical của font icon `nomnom:ui` (U+E000–U+E035) để icon chạy đúng
  kể cả khi chỉ cài pack này.
- Override `minecraft:default` tham chiếu chéo `nomnom:font/vi_text.png` của pack
  chính — không chứa font text; thiếu pack chính thì chữ rơi về fallback vanilla.
- Cài cùng lúc cả hai pack: gửi **NomNomUI trước, NomNomUI-HUD sau**
  (`Player#addResourcePack`) — override của HUD đã chứa ĐỦ provider của pack chính.
- Chi tiết bảng glyph + cách dùng: `HUD-INFO.txt` trong pack.

## Ghi công (bắt buộc)
- **Be Vietnam Pro** — SIL Open Font License 1.1, xem `LICENSE-OFL.txt`
  (digits 'k' 'M' và phần cơ cấu font HUD phái sinh từ bản raster hoá).
- Phần glyph/ornament tự thiết kế: © NomNom SMP 2026.
