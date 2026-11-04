# Icon glyph — NomNom UI

Nguồn chuẩn: `resourcepack/icons.json` (manifest 48 icon, sinh bởi design brief đợt 4).
Font provider: `nomnom:ui` · dải `U+E000..U+E02F` · atlas `16x16` cell, render 9 px (height/ascent = 9/9).

> White fill + 1px black outline, binary alpha. confirm/cancel are aliases of check/cross and do not consume extra code points.

| CP | ID | Mô tả | ASCII inline | ASCII label |
|---|---|---|---|---|
| `U+E000` | `tps` | Đồng hồ đo tốc độ, kim chỉ vạch 20 | `T` | TPS |
| `U+E001` | `ping` | Ba vạch sóng tăng dần | `P` | Ping |
| `U+E002` | `online` | Hai đầu người cạnh nhau | `O` | Online |
| `U+E003` | `bounty` | Túi tiền có ngôi sao | `B` | Bounty |
| `U+E004` | `cash` | Tờ tiền có ký hiệu ₫ | `$` | Cash |
| `U+E005` | `coin` | Đồng xu tròn có rãnh | `c` | Coin |
| `U+E006` | `sword` | Kiếm chéo 45 độ | `S` | Sword |
| `U+E007` | `shield` | Khiên đứng có biểu tượng | `D` | Shield |
| `U+E008` | `land` | Mảnh đất có cột mốc | `L` | Land |
| `U+E009` | `market` | Giỏ hàng có mái che | `M` | Market |
| `U+E00A` | `auction` | Búa đấu giá | `A` | Auction |
| `U+E00B` | `casino` | Hai xúc xắc | `C` | Casino |
| `U+E00C` | `mini` | Tay cầm game | `m` | Mini |
| `U+E00D` | `menu` | Ba gạch ngang | `=` | Menu |
| `U+E00E` | `home` | Ngôi nhà mái nhọn | `H` | Home |
| `U+E00F` | `sethome` | Ngôi nhà kèm dấu cộng | `+H` | Set home |
| `U+E010` | `spawn` | Beacon tỏa sáng | `SP` | Spawn |
| `U+E011` | `rp` | La bàn bốn hướng | `R` | Wild TP |
| `U+E012` | `mail` | Phong bì thư | `@` | Mail |
| `U+E013` | `ally` | Hai bàn tay bắt nhau | `AL` | Ally |
| `U+E014` | `kill` | Đầu lâu | `K` | Kill |
| `U+E015` | `back` | Mũi tên cong quay lui | `<` | Back |
| `U+E016` | `bag` | Ba lô | `B` | Bag |
| `U+E017` | `bed` | Giường | `BD` | Bed |
| `U+E018` | `chest` | Rương gỗ | `CH` | Chest |
| `U+E019` | `heart` | Trái tim | `HT` | Heart |
| `U+E01A` | `star` | Ngôi sao năm cánh | `*` | Star |
| `U+E01B` | `fire` | Ngọn lửa | `F` | Fire |
| `U+E01C` | `clock` | Mặt đồng hồ | `T` | Clock |
| `U+E01D` | `lock` | Ổ khóa đóng | `L` | Lock |
| `U+E01E` | `mail-verify` | Phong bì kèm dấu check | `V` | Verify |
| `U+E01F` | `warn` | Tam giác chấm than | `!` | Warn |
| `U+E020` | `check` | Dấu check | `OK` | Check |
| `U+E021` | `cross` | Dấu X | `X` | Cancel |
| `U+E022` | `arrow-l` | Mũi tên trái thẳng | `<` | Left |
| `U+E023` | `arrow-r` | Mũi tên phải thẳng | `>` | Right |
| `U+E024` | `page-prev` | Mũi tên trái kèm vạch trang | `<<` | Prev |
| `U+E025` | `page-next` | Mũi tên phải kèm vạch trang | `>>` | Next |
| `U+E026` | `search` | Kính lúp | `?` | Search |
| `U+E027` | `sort` | Hai mũi tên lên xuống | `^` | Sort |
| `U+E028` | `plus` | Dấu cộng | `+` | Plus |
| `U+E029` | `minus` | Dấu trừ | `-` | Minus |
| `U+E02A` | `crown` | Vương miện | `W` | Crown |
| `U+E02B` | `tier1` | Huy hiệu hạng I | `1` | Tier 1 |
| `U+E02C` | `tier2` | Huy hiệu hạng II | `2` | Tier 2 |
| `U+E02D` | `tier3` | Huy hiệu hạng III | `3` | Tier 3 |
| `U+E02E` | `tier4` | Huy hiệu hạng IV | `4` | Tier 4 |
| `U+E02F` | `tier5` | Huy hiệu hạng V kèm vương miện | `5` | Tier 5 |

## Alias

| Tên | Trỏ tới |
|---|---|
| `confirm` | `check` |
| `cancel` | `cross` |

## Quy ước dùng

- Java: dùng ký tự PUA tương ứng (U+E000–U+E02F) trong component/legacy text.
- Bedrock/Geyser hoặc `use-glyphs: false`: dùng cột **ASCII inline** (HUD) hoặc **ASCII label** (menu/tooltip). Không dùng emoji.
- Sau glyph luôn thêm một dấu cách khi ghép chuỗi; advance icon không monospace.
- Icon master trắng + viền đen, alpha nhị phân; client tự tint theo màu text.
