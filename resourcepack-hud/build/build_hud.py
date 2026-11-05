#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomNomUI-HUD — build the HUD-only font (nomnom:hud) for sidebar + tablist.

NN5 A3: pack RIÊNG cho scoreboard/tablist, tách khỏi pack chính. Font
`nomnom:hud` chứa ĐÚNG những thứ HUD cần:

  * Digits fixed-width U+E040..U+E04D  — 0-9 . , k M — mọi glyph đều advance 10 px
    (ink nén/căn giữa vào hộp 9 px) để HUD căn phải cột số liệu TUYỆT ĐỐI,
    không phụ thuộc advance proportional của Be Vietnam Pro.
  * Ornament + khung U+E050..U+E05D    — rule 3-mảnh (rule-l/m/r), vbar ngăn cột,
    row-bg (nền dòng), spark (sao 4 cánh), khung 8-mảnh (tl/tm/tr/ml/mr/bl/bm/br).

Geometrie KHỚP font text của pack chính: cell 16x20, height 20, ascent 16,
em 13 render trực tiếp (hinted) — digit/ornament đứng cạnh chữ chính là cùng cỡ.

Khác với pack chính, pack này KHÔNG đóng gói atlas vi_text; override
minecraft:default của nó tham chiếu CHÉO nomnom:font/vi_text.png (pack chính
cung cấp) + copy byte-identical của nomnom:ui để icon chạy độc lập thứ tự pack.
Thiếu pack chính => chữ rơi về fallback vanilla (include/default), không vỡ.

Outputs (work/rp_build/hud_src — nguồn đóng gói của build_hud_pack.py):
  assets/minecraft/font/default.json     # override có thêm reference nomnom:hud
  assets/nomnom/font/hud.json            # font id nomnom:hud (PUA U+E040..U+E05D)
  assets/nomnom/font/ui.json             # copy byte-identical từ rp_src
  assets/nomnom/textures/font/hud.png    # 128x80, 8x4 cells of 16x20
  assets/nomnom/textures/font/icons.png  # copy byte-identical từ rp_src
  HUD-INFO.txt                           # bảng glyph + hướng dẫn dùng cho HUD agent
  preview_hud_font.png                   # (không ship) — xem nhanh

Usage: python work/rp_build/build_hud.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent          # work/rp_build
WORK = HERE.parent
RP = HERE.parents[1] / "resourcepack" if (HERE.parents[1] / "resourcepack").is_dir() else WORK / "rp_src"  # repo vs workspace
if (HERE.parent / "HUD-INFO.txt").is_file():
    OUT = HERE.parent                                   # repo layout: resourcepack-hud/
else:
    OUT = HERE / "hud_src"                              # workspace: work/rp_build/hud_src
FONT_DIR = HERE / "fonts"
if not (FONT_DIR / "BeVietnamPro-Regular.ttf").is_file():
    FONT_DIR = HERE.parents[1] / "resourcepack" / "build" / "fonts"   # repo layout
TTF = FONT_DIR / "BeVietnamPro-Regular.ttf"

# ==== cùng geometry với build_font.py (pack chính) ==========================
CELL_W, CELL_H = 16, 20
EM_PX = 13
BASELINE = 16
ALPHA_LOW, ALPHA_HIGH = 36, 210

COLS, ROWS = 8, 4                                # 32 cells -> atlas 128x80

# ==== glyph registry ========================================================
# (cp, id, painter). PUA nhánh HUD: E040..E05D. E000..E03F đã thuộc pack chính.
DIGITS = "0123456789"
DIGIT_EXTRA = {".": "dot", ",": "comma", "k": "k-suffix", "M": "m-suffix"}
FIXED_INK = 9                                    # hộp ink ngang — advance = FIXED_INK + 1


def alpha_curve(v: int) -> int:
    if v <= ALPHA_LOW:
        return 0
    if v >= ALPHA_HIGH:
        return 255
    return int(ALPHA_LOW + (v - ALPHA_LOW) * (255 - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW))


def render_char(ch: str, font) -> Image.Image:
    img = Image.new("L", (CELL_W, CELL_H), 0)
    ImageDraw.Draw(img).text((0, BASELINE), ch, font=font, fill=255, anchor="ls")
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    cell.putalpha(img.point(alpha_curve))
    return cell


def render_fixed(ch: str, font) -> tuple[Image.Image, int]:
    """Render chữ rồi ép ink vào đúng hộp FIXED_INK px => advance cố định.

    ink rộng hơn hộp -> nén ngang (BOX); hẹp hơn -> căn giữa. Luôn đặt cột mực
    phải nhất ở x = FIXED_INK-1 nên advance = FIXED_INK + 1 với MỌI glyph.
    """
    src = render_char(ch, font)
    bb = src.getchannel("A").getbbox()
    if bb is None:
        raise SystemExit(f"fixed glyph {ch!r} rendered empty")
    ink = src.crop(bb)
    w, h = ink.size
    if w > FIXED_INK:
        ink = ink.resize((FIXED_INK, h), Image.BOX)
        w = FIXED_INK
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    # căn giữa trong hộp, nhưng chốt cột phải tại FIXED_INK-1
    x0 = (FIXED_INK - w) // 2
    cell.alpha_composite(ink, (x0, bb[1]))
    return cell, FIXED_INK + 1


# ---- ornament painters (trên cell 16x20, trả (cell, advance)) --------------

def px_img(fn) -> tuple[Image.Image, int]:
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    adv = fn(cell.load())
    return cell, adv


def p_rule_l(px):
    # đầu trái bo: 3px cao ở mép, thân 2px
    for y in (13, 14, 15):
        px[0, y] = (255, 255, 255, 255)
    for x in range(1, 16):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)
    return 16


def p_rule_m(px):
    for x in range(16):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)
    return 16


def p_rule_r(px):
    for y in (13, 14, 15):
        px[15, y] = (255, 255, 255, 255)
    for x in range(15):
        for y in (13, 14):
            px[x, y] = (255, 255, 255, 255)
    return 16


def p_vbar(px):
    for y in range(0, 20):
        for x in (7, 8):
            px[x, y] = (255, 255, 255, 255)
    return 9


def p_row_bg(px):
    for y in range(20):
        for x in range(16):
            px[x, y] = (255, 255, 255, 255)
    return 16


def p_spark(px):
    cx, cy, ro, ri = 7.5, 9.5, 6.0, 1.9
    pts = []
    for i in range(8):
        r = ro if i % 2 == 0 else ri
        a = math.radians(-90 + i * 45.0)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    for y in range(CELL_H):
        for x in range(CELL_W):
            if _in_poly(x + 0.5, y + 0.5, pts):
                px[x, y] = (255, 255, 255, 255)
    return 13


def _in_poly(px_, py_, pts) -> bool:
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > py_) != (yj > py_):
            xc = xi + (py_ - yi) * (xj - xi) / (yj - yi)
            if px_ < xc:
                inside = not inside
        j = i
    return inside


def _frame(side: str):
    def draw(px):
        if "t" in side:
            for x in range(16):
                px[x, 0] = (255, 255, 255, 255)
        if "b" in side:
            for x in range(16):
                px[x, 19] = (255, 255, 255, 255)
        if "l" in side:
            for y in range(20):
                px[0, y] = (255, 255, 255, 255)
        if "r" in side:
            for y in range(20):
                px[15, y] = (255, 255, 255, 255)
        return 16
    return draw


ORNAMENTS = [
    (0xE050, "rule-l", p_rule_l),
    (0xE051, "rule-m", p_rule_m),
    (0xE052, "rule-r", p_rule_r),
    (0xE053, "vbar", p_vbar),
    (0xE054, "row-bg", p_row_bg),
    (0xE055, "spark", p_spark),
    (0xE056, "frame-tl", _frame("tl")),
    (0xE057, "frame-tm", _frame("tm")),
    (0xE058, "frame-tr", _frame("tr")),
    (0xE059, "frame-ml", _frame("ml")),
    (0xE05A, "frame-mr", _frame("mr")),
    (0xE05B, "frame-bl", _frame("bl")),
    (0xE05C, "frame-bm", _frame("bm")),
    (0xE05D, "frame-br", _frame("br")),
]


def main() -> int:
    if not OUT.exists():
        OUT.mkdir(parents=True)
    (OUT / "assets/minecraft/font").mkdir(parents=True, exist_ok=True)
    (OUT / "assets/nomnom/font").mkdir(parents=True, exist_ok=True)
    (OUT / "assets/nomnom/textures/font").mkdir(parents=True, exist_ok=True)

    font = ImageFont.truetype(str(TTF), EM_PX)

    # ---- digits + punctuation (fixed width) ------------------------------
    cells: list[tuple[int, str, Image.Image, int]] = []
    for i, ch in enumerate(DIGITS):
        cell, adv = render_fixed(ch, font)
        cells.append((0xE040 + i, f"digit-{ch}", cell, adv))
    for ch, gid in DIGIT_EXTRA.items():
        cell, adv = render_fixed(ch, font)
        cells.append((0xE04A + list(DIGIT_EXTRA).index(ch), gid, cell, adv))

    # ---- ornaments --------------------------------------------------------
    for cp, gid, fn in ORNAMENTS:
        cell, adv = px_img(fn)
        cells.append((cp, gid, cell, adv))

    cells.sort(key=lambda c: c[0])
    cps = [c[0] for c in cells]
    assert cps == sorted(set(cps)), "duplicate HUD codepoints"
    assert cps[0] == 0xE040 and cps[-1] == 0xE05D, "HUD range drifted"

    # ---- atlas + json -----------------------------------------------------
    atlas = Image.new("RGBA", (COLS * CELL_W, ROWS * CELL_H), (255, 255, 255, 0))
    rows_grid: list[list[str]] = [["\u0000"] * COLS for _ in range(ROWS)]
    info_rows: list[str] = []
    for cp, gid, cell, adv in cells:
        idx = cp - 0xE040
        row, col = divmod(idx, COLS)
        atlas.alpha_composite(cell, (col * CELL_W, row * CELL_H))
        rows_grid[row][col] = chr(cp)
        info_rows.append(f"U+{cp:04X}  {gid:11} advance={adv:2d}px")
    atlas.save(OUT / "assets/nomnom/textures/font/hud.png")

    chars_rows = ["".join(r) for r in rows_grid]
    hud_json = {
        "providers": [
            {"type": "bitmap", "file": "nomnom:font/hud.png",
             "height": CELL_H, "ascent": BASELINE, "chars": chars_rows}
        ]
    }
    (OUT / "assets/nomnom/font/hud.json").write_text(
        json.dumps(hud_json, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    # ---- default.json override (superset của pack chính + nomnom:hud) ----
    main_default = json.loads((RP / "assets/minecraft/font/default.json").read_text(encoding="utf-8"))
    hud_default = {"providers": list(main_default["providers"])}
    # chèn reference nomnom:hud NGAY TRƯỚC include/unifont (PUA phải thắng unifont)
    ids = [p.get("id") for p in hud_default["providers"] if p.get("type") == "reference"]
    assert ids == ["minecraft:include/space", "minecraft:include/default",
                   "nomnom:ui", "minecraft:include/unifont"], ids
    hud_default["providers"].insert(4, {"type": "reference", "id": "nomnom:hud"})
    (OUT / "assets/minecraft/font/default.json").write_text(
        json.dumps(hud_default, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")

    # ---- copy byte-identical của bộ icon (độc lập thứ tự pack) ------------
    for name in ("ui.json",):
        src = RP / f"assets/nomnom/font/{name}"
        (OUT / f"assets/nomnom/font/{name}").write_bytes(src.read_bytes())
    for name in ("icons.png",):
        src = RP / f"assets/nomnom/textures/font/{name}"
        (OUT / f"assets/nomnom/textures/font/{name}").write_bytes(src.read_bytes())

    # ---- HUD-INFO.txt ------------------------------------------------------
    info = f"""NomNomUI-HUD — font nomnom:hud (A3, đợt 5)
==========================================
Phạm vi        : CHỈ glyph cho sidebar + tablist. Không chứa font text tiếng Việt
                 (atlas vi_text thuộc pack chính NomNomUI; override bên dưới tham
                 chiếu chéo và rơi về fallback vanilla nếu pack chính vắng mặt).
Geometrie      : cell 16x20, height 20, ascent {BASELINE}, em {EM_PX} px render trực tiếp có hint
                 — KHỚP hoàn toàn cỡ chữ của pack chính nên digit/ornament đứng cạnh
                 chữ thường là cùng cỡ, cùng baseline.
Atlas          : assets/nomnom/textures/font/hud.png ({COLS*CELL_W}x{ROWS*CELL_H}, {COLS}x{ROWS} cells)
Dải PUA        : U+E040..U+E05D (không đụng U+E000..U+E035 của pack chính)

== Cột số căn phải (fixed-width) ==
{chr(10).join(info_rows[:14])}

Mọi glyph trong nhóm này đều advance = {FIXED_INK + 1} px (ink ép vào hộp {FIXED_INK} px).
Cách dùng trong HUD plugin (F1-F3):
  1. Định dạng số -> chuỗi digits '.' ',' 'k' 'M' (HudFormat.fmtBounty đã đúng bộ này).
  2. padLeft chuỗi bằng space (4px) tới độ rộng cột, rồi map TỪNG ký tự:
     '0'-'9' -> (char)(0xE040 + d), '.' -> 0xE04A, ',' -> 0xE04B, 'k' -> 0xE04C, 'M' -> 0xE04D.
  3. Bedrock / use-glyphs=false -> giữ nguyên ASCII (fallback có sẵn).

== Ornament + khung ==
U+E050 rule-l  : mũ trái đường kẻ (advance 16, thân ở y13-14)
U+E051 rule-m  : đoạn giữa — ghép N lần để kéo dài
U+E052 rule-r  : mũ phải
U+E053 vbar    : vạch ngăn cột dọc (advance 9)
U+E054 row-bg  : nền 1 dòng (đầy cell) — tô màu tối bằng §8/§0, ghép ngang
U+E055 spark   : sao 4 cánh trang trí (advance 13)
U+E056..E058   : khung cạnh trên  frame-tl / frame-tm / frame-tr
U+E059..E05A   : khung cạnh ngang  frame-ml / frame-mr
U+E05B..E05D   : khung cạnh dưới  frame-bl / frame-bm / frame-br
Khung 1 hàng:  [tl][tm]…[tr] / [ml] + text + [mr] / [bl][bm]…[br] — viền 1px, góc vuông.

== Override minecraft:default (assets/minecraft/font/default.json) ==
Provider chain: vi_text (chéo pack chính) -> include/space -> include/default ->
nomnom:ui -> nomnom:hud -> include/unifont. Pack này và pack chính CÙNG cài:
default.json của pack thêm Sau (addResourcePack sau cùng) thắng và đã chứa ĐỦ
provider của pack chính, nên không mất chữ tiếng Việt.
Đã kèm bản copy byte-identical của nomnom:ui (ui.json + icons.png) để icon
chạy đúng kể cả khi chỉ cài pack HUD.

Generated by work/rp_build/build_hud.py - do not hand edit.
"""
    (OUT / "HUD-INFO.txt").write_text(info, encoding="utf-8", newline="\n")

    # ---- preview -----------------------------------------------------------
    sheet = Image.new("RGB", (COLS * (CELL_W * 6 + 8) + 8, ROWS * (CELL_H * 6 + 26) + 8), (18, 24, 33))
    d = ImageDraw.Draw(sheet)
    lab = ImageFont.truetype(str(TTF), 11)
    for i, (cp, gid, cell, adv) in enumerate(cells):
        row, col = divmod(i, COLS)
        x = 8 + col * (CELL_W * 6 + 8)
        y = 8 + row * (CELL_H * 6 + 26)
        big = cell.resize((CELL_W * 6, CELL_H * 6), Image.NEAREST)
        bg = Image.new("RGBA", big.size, (24, 32, 44, 255))
        bg.alpha_composite(big)
        sheet.paste(bg.convert("RGB"), (x, y))
        d.text((x, y + CELL_H * 6 + 2), f"U+{cp:04X} {gid} a={adv}", font=lab, fill=(154, 164, 178))
    sheet.save(HERE / "preview_hud_font.png")

    print("== NomNomUI-HUD font build ==")
    print(f"  glyphs      : {len(cells)} (U+E040..U+E05D)")
    print(f"  fixed digits: {len(DIGITS) + len(DIGIT_EXTRA)} advance={FIXED_INK + 1}px")
    print(f"  ornaments   : {len(ORNAMENTS)}")
    print(f"  atlas       : [{COLS * CELL_W}, {ROWS * CELL_H}]")
    print(f"  out         : {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
