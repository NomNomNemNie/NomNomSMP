# Icon glyph — NomNom UI

Nguồn chuẩn: `resourcepack/icons.json` (manifest **54 icon** — schema `nomnom-ui-icons/2`,
sinh lại từ đợt 5; 48 icon đầu giữ NGUYÊN codepoint/id/ascii so với manifest v1).
Font provider: `nomnom:ui` · dải `U+E000..U+E035` · atlas `16x16` cell, render 9 px (height/ascent = 9/9).

> White fill + 1px black outline, binary alpha. confirm/cancel are aliases of check/cross and do not consume extra code points.
> Đợt 5 (v1.1.0): toàn bộ 48 glyph được vẽ lại theo phong cách NomNom (dáng mạnh 2px, khoảng âm rõ) và thêm 6 icon mới U+E030–E035.
> Item model 32x32 (`nomnom:ui/icon/<id>`) đã ĐỦ cho mọi entry menu + shop: thêm sethome, rp, book, sell, auction, friendly, shop, chat-tag, worldtime, sword.

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
| `U+E013` | `ally` | Hai vòng liên minh móc nhau | `AL` | Ally |
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
| `U+E030` | `book` | Quyển sổ tay mở (nomnom book) | `B` | Book |
| `U+E031` | `sell` | Thẻ giá kèm mũi tên ra (bán) | `S` | Sell |
| `U+E032` | `friendly` | Trái tim kèm hai kiếm gác (đấu tập) | `F` | Friendly |
| `U+E033` | `shop` | Cửa hàng mái sạp kèm cửa | `P` | Shop |
| `U+E034` | `chat-tag` | Bong bóng chat kèm sao (tag) | `C` | Chat tag |
| `U+E035` | `worldtime` | Mặt trời quỹ đạo kèm kim giờ | `W` | World time |

## Font HUD riêng — `nomnom:hud` (pack NomNomUI-HUD v1.0.0, A3)

Dải PUA riêng **U+E040–U+E05D**, không đụng bảng trên. Chi tiết đầy đủ trong
`resourcepack-hud/HUD-INFO.txt` (cũng ship kèm zip HUD).

| CP | ID | Advance | Dùng cho |
|---|---|---|---|
| `U+E040`–`U+E049` | `digit-0`…`digit-9` | 10 px (cố định) | cột số căn phải sidebar/tablist |
| `U+E04A` | `dot` | 10 px (cố định) | dấu chấm thập phân trong số |
| `U+E04B` | `comma` | 10 px (cố định) | dấu phẩy ngăn nghìn |
| `U+E04C` | `k-suffix` | 10 px (cố định) | hậu tố `k` của fmtBounty |
| `U+E04D` | `m-suffix` | 10 px (cố định) | hậu tố `M` của fmtBounty |
| `U+E050`/`E051`/`E052` | `rule-l/m/r` | 16 px | đường kẻ ngang 3 mảnh (title/footer) |
| `U+E053` | `vbar` | 9 px | vạch ngăn cột dọc tablist |
| `U+E054` | `row-bg` | 16 px | nền 1 dòng (tô tối bằng §8/§0) |
| `U+E055` | `spark` | 13 px | sao 4 cánh trang trí |
| `U+E056`–`E058` | `frame-tl/tm/tr` | 16 px | khung cạnh trên |
| `U+E059`/`E05A` | `frame-ml/mr` | 16 px | khung cạnh ngang |
| `U+E05B`–`E05D` | `frame-bl/bm/br` | 16 px | khung cạnh dưới |

Digits/`k`/`M` giữ **đúng hình dạng Be Vietnam Pro em 13 px** như pack chính
(cell 16x20, height 20, ascent 16) nhưng ink bị ép vào hộp 9 px → advance cố định
10 px, căn phải số liệu tuyệt đối kể cả proportional font bên dưới.

