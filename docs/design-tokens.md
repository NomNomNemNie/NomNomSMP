# Design tokens — NomNom UI Kit (bản nháp, workflow sẽ hoàn thiện)

## Palette
| Token | Hex | Dùng cho |
|---|---|---|
| ink-900 | #0B0F14 | nền tối |
| ink-800 | #121821 | panel nền |
| ink-700 | #1B2430 | panel nổi |
| gold-400 | #E8B450 | viền/tiêu đề |
| gold-200 | #F6D98A | highlight |
| lime-400 | #7DD957 | thành công / tiền |
| red-400 | #E45757 | cảnh báo |
| text-100 | #F2F4F8 | chữ chính |
| text-500 | #9AA4B2 | chữ phụ |

## Kích thước
- Icon glyph: 16×16 (hiển thị 9–12px), scale 2x cho tiêu đề.
- Panel 9-slice: viền 12px, góc bo 4px, stroke 2px gold + inner 1px ink.
- Nút: cao 20px, chữ 8px, hover sáng +12% luminance.

## Quy chuẩn
- Mọi icon nằm trong font provider `nomnom:ui`, dùng ký tự PUA (U+E000…).
- Fallback ASCII cho Bedrock (glyph không render qua Geyser).
