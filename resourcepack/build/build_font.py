#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomNom UI v1.1 — build the Vietnamese bitmap font atlas + the 54 PUA icon glyphs.

NN5 (2026-11-06) — bản dựng lại theo feedback "font nhìn như 480p":
  * Pipeline MỚI: render TRỰC TIẾP ở cỡ cuối (em 13 px) bằng FreeType CÓ HINTING
    (ttfautohint của Google Fonts), không còn supersample 4x + LANCZOS như 1.0 —
    berkht hint bắt nét chữ vào lưới pixel => nét sạch, không mờ.
  * Glyph TO HƠN: em 10.31 -> 13 px (+26%), nhờ cell cao hơn 16 -> 20 px
    (atlas 256x500). Vẫn render 1:1 (height == cell height) => không méo.
  * Alpha sau render được nắn độ tương phản (curve 36..210) để cắt quầng mờ
    nhưng vẫn giữ một chút khử răng cưa.
  * Hợp đồng giữ nguyên: 385 codepoint (5 block Latin), 146/146 tiếng Việt
    precomposed, fallback chain minecraft:default không đổi.

Outputs (all under work/rp_src, overwritten deterministically -> idempotent):

  assets/minecraft/font/default.json         # the REAL override of minecraft:default
  assets/nomnom/font/default.json            # alias font id nomnom:default (same body)
  assets/nomnom/font/ui.json                 # font id nomnom:ui  (PUA U+E000..U+E035)
  assets/nomnom/font/FONT-INFO.txt           # font provenance / metrics / coverage
  assets/nomnom/font/charset.tsv             # cp,char,row,col,ink_w,advance(20px),advance(9px)
  assets/nomnom/textures/font/vi_text.png    # 256x500 text atlas, 16x25 cells of 16x20
  assets/nomnom/textures/font/icons.png      # 128x112 icon atlas, 8x7 cells of 16x16
  assets/nomnom/textures/icon/<id>.png       # 54 individual 16x16 icons
  LICENSE-OFL.txt                            # verbatim OFL 1.1 of Be Vietnam Pro

Icon manifest: work/rp_build/icons-nn5.json (48 icon U+E000..U+E02F GIỮ codepoint cũ
so với work/nn4-icons.json + 6 icon mới U+E030..U+E035).

Usage:
  python work/rp_build/build_font.py                # build + validate + print tables
  python work/rp_build/build_font.py --verify-only  # validate what is on disk
  python work/rp_build/build_font.py --no-preview   # skip preview PNGs

The client advance formula is copied from BitmapProvider#load:
    pixelScale = height / cellHeight
    advance    = round_half_up(actualGlyphWidth * pixelScale) + 1
where actualGlyphWidth = rightmost non-transparent column + 1 (0 if the cell is empty).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

# --------------------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent            # work/rp_build
WORK = HERE.parent                                # work
RP = HERE.parent if (HERE.parent / "assets").is_dir() else WORK / "rp_src"  # repo: resourcepack/, workspace: work/rp_src
ICON_JSON = HERE / "icons-nn5.json"               # NN5 manifest: source of truth for codepoints
if not ICON_JSON.is_file():
    ICON_JSON = HERE.parent / "icons.json"         # repo layout: resourcepack/icons.json
ICON_JSON_V1 = WORK / "nn4-icons.json"             # v1.0 manifest (compat check, first 48)
if not ICON_JSON_V1.is_file():
    ICON_JSON_V1 = HERE.parent / "icons.json"      # repo layout fallback
FONT_DIR = HERE / "fonts"
TTF_REGULAR = FONT_DIR / "BeVietnamPro-Regular.ttf"
OFL_SRC = FONT_DIR / "OFL.txt"

FONT_ASSETS = RP / "assets" / "nomnom" / "font"
TEX_FONT = RP / "assets" / "nomnom" / "textures" / "font"
TEX_ICON = RP / "assets" / "nomnom" / "textures" / "icon"
MC_FONT = RP / "assets" / "minecraft" / "font"

# Font file hashes were pinned in work/nn4-design.md sec.3.2; refuse to build from
# a different file so the artefact stays reproducible.
SHA_REGULAR = "cd1ef6e9d7db28ad5cdb88a65ccbe693870e60d340b791f349d248342b4fe4c3"
SHA_OFL = "6b7f8f73609a25ea78c891e34cf37b06f8a676b7ea986e941e43b009110f2a85"

# ------------------------------------------------------------------- atlas geometry
# TEXT (NN5): cell 16 wide x 20 tall, em 13 px rendered 1:1 (height == 20).
CELL_W, CELL_H = 16, 20
TEXT_COLS, TEXT_ROWS = 16, 25                    # 400 cells, 385 used -> atlas 256x500
EM_PX = 13                                       # rendered em, direct hinted (no downscale)
BASELINE = 16                                    # baseline from cell top == provider ascent
# Contrast curve on FreeType coverage: below 36 -> transparent (kills halo),
# above 210 -> solid (solidifies stems); between: linear stretch.
ALPHA_LOW, ALPHA_HIGH = 36, 210

# ICONS: unchanged contract from v1.0 (render 9 px, advance 9).
ICELL = 16
ICON_COLS, ICON_ROWS = 8, 7                      # 56 cells, 54 used -> atlas 128x112

ICON_W, ICON_H = 13, 14                # authoring canvas for the *fill* mask
ICON_OFFSET = (1, 1)                   # fill mask placed at (1,1): ring expands to x0..14
ICON_MARGIN_RIGHT = 1                  # px kept transparent on the right edge

# text ranges, in the order used by work/nn4-design.md sec.3.3
TEXT_RANGES = [
    (0x0021, 0x007E, "ASCII"),
    (0x00A1, 0x00FF, "Latin-1"),
    (0x0100, 0x017F, "Latin Ext-A"),
    (0x0180, 0x024F, "Latin Ext-B"),
    (0x1E00, 0x1EFF, "Latin Ext-Additional"),
]

REQUIRED_ICON_NAMES = (
    "tps ping online bounty cash coin sword shield land market auction casino mini menu "
    "home sethome spawn rp mail ally kill back bag bed chest heart star fire clock lock "
    "mail-verify warn check cross arrow-l arrow-r page-prev page-next search sort plus minus "
    "confirm cancel crown tier1 tier2 tier3 tier4 tier5 "
    "book sell friendly shop chat-tag worldtime"
).split()


# ============================================================================= utils
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def round_half_up(x: float) -> int:
    """Java's (int)(0.5 + x) for non-negative x."""
    return int(0.5 + x)


def hex_cp(cp: int) -> str:
    return "U+%04X" % cp


def alpha_curve(v: int) -> int:
    """Contrast stretch of FreeType coverage: cut halo, solidify stems, keep AA."""
    if v <= ALPHA_LOW:
        return 0
    if v >= ALPHA_HIGH:
        return 255
    return int(ALPHA_LOW + (v - ALPHA_LOW) * (255 - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW))


# ========================================================================== text font
def collect_codepoints(cmap: set[int]) -> list[int]:
    cps: list[int] = []
    for a, b, _name in TEXT_RANGES:
        cps.extend(cp for cp in range(a, b + 1) if cp in cmap)
    return cps


def vietnamese_chars() -> list[str]:
    """146 precomposed Vietnamese characters: 12 vowels x 6 tones x 2 cases + đ/Đ."""
    vowels = "aăâeêioôơuưy"
    tones = ["", "\u0300", "\u0301", "\u0303", "\u0309", "\u0323"]
    out: set[str] = set()
    for v in vowels:
        for t in tones:
            out.add(unicodedata.normalize("NFC", v + t))
            out.add(unicodedata.normalize("NFC", v.upper() + t))
    out |= {"đ", "Đ"}
    return sorted(c for c in out if len(c) == 1)


def render_text_cell(ch: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    """Render one glyph DIRECTLY at final size (hinted) into a 16x20 cell.

    Không supersample, không downscale — hinting của FreeType (ttfautohint) bắt
    các nét chính vào lưới pixel nên nét sạch. Alpha sau đó được nắn bằng
    alpha_curve để bỏ quầng mờ mà vẫn giữ khử răng cưa.
    """
    mask = Image.new("L", (CELL_W, CELL_H), 0)
    ImageDraw.Draw(mask).text((0, BASELINE), ch, font=font, fill=255, anchor="ls")
    alpha = mask.point(alpha_curve)
    cell = Image.new("RGBA", (CELL_W, CELL_H), (255, 255, 255, 0))
    cell.putalpha(alpha)
    return cell


def ink_width(cell: Image.Image) -> int:
    """Rightmost non-transparent column + 1 (client's actualGlyphWidth)."""
    alpha = cell.getchannel("A")
    w, h = cell.size
    px = alpha.load()
    for x in range(w - 1, -1, -1):
        for y in range(h):
            if px[x, y]:
                return x + 1
    return 0


def build_text_atlas(log) -> tuple[Image.Image, list[dict], list[int]]:
    cmap = set()
    tt = TTFont(TTF_REGULAR)
    for table in tt["cmap"].tables:
        cmap.update(table.cmap.keys())
    tt.close()

    cps = collect_codepoints(cmap)
    expected = 385
    if len(cps) != expected:
        raise SystemExit(f"charset drift: got {len(cps)} codepoints, design expects {expected}")

    font = ImageFont.truetype(str(TTF_REGULAR), EM_PX)
    used_rows = (len(cps) + TEXT_COLS - 1) // TEXT_COLS
    if used_rows > TEXT_ROWS:
        raise SystemExit(f"atlas overflow: {len(cps)} glyphs need {used_rows} rows > {TEXT_ROWS}")

    atlas = Image.new("RGBA", (TEXT_COLS * CELL_W, TEXT_ROWS * CELL_H), (255, 255, 255, 0))
    glyphs: list[dict] = []
    overflows: list[str] = []

    for i, cp in enumerate(cps):
        ch = chr(cp)
        cell = render_text_cell(ch, font)
        row, col = divmod(i, TEXT_COLS)
        atlas.alpha_composite(cell, (col * CELL_W, row * CELL_H))
        iw = ink_width(cell)
        adv = round_half_up(iw * (CELL_H / CELL_H)) + 1 if iw else 0   # height 20 / cell 20
        glyphs.append({"cp": cp, "char": ch, "row": row, "col": col,
                       "ink_w": iw, "advance": adv})
        # every glyph must fit with >=1px of clearance on the right (design sec.3.4)
        if iw > CELL_W - 1:
            overflows.append(f"{hex_cp(cp)} ink_w={iw}")
        # vertical sanity: ink must stay inside the cell (no clipped diacritics)
        bbox = cell.getchannel("A").getbbox()
        if bbox is None:
            overflows.append(f"{hex_cp(cp)} EMPTY")
        elif bbox[1] < 0 or bbox[3] > CELL_H:
            overflows.append(f"{hex_cp(cp)} vink={bbox}")

    if overflows:
        log.append("WARN text glyphs outside 16x20 budget: " + ", ".join(overflows[:20]))

    return atlas, glyphs, cps


# ================================================================== icon raster core
class Mask:
    """13x14 white-fill mask; the 1px black ring is generated afterwards."""

    def __init__(self) -> None:
        self.px = [[0] * ICON_W for _ in range(ICON_H)]

    # -- low level -----------------------------------------------------------
    def set(self, x: int, y: int, v: int = 1) -> None:
        if 0 <= x < ICON_W and 0 <= y < ICON_H:
            self.px[y][x] = v

    def clear(self, x: int, y: int) -> None:
        self.set(x, y, 0)

    def get(self, x: int, y: int) -> int:
        return self.px[y][x] if (0 <= x < ICON_W and 0 <= y < ICON_H) else 0

    # -- primitives ----------------------------------------------------------
    def hbar(self, y0: int, x0: int, x1: int, w: int = 1) -> None:
        for y in range(y0, y0 + w):
            for x in range(x0, x1 + 1):
                self.set(x, y)

    def vbar(self, x0: int, y0: int, y1: int, w: int = 1) -> None:
        for x in range(x0, x0 + w):
            for y in range(y0, y1 + 1):
                self.set(x, y)

    def rect(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.hbar(y0, x0, x1, y1 - y0 + 1)

    def hole(self, x0: int, y0: int, x1: int, y1: int) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.clear(x, y)

    def line(self, x0: int, y0: int, x1: int, y1: int, w: int = 1) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        off = (w - 1) // 2
        while True:
            for oy in range(w):
                for ox in range(w):
                    self.set(x0 + ox - off, y0 + oy - off)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx: float, cy: float, r: float) -> None:
        for y in range(ICON_H):
            for x in range(ICON_W):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.set(x, y)

    def ring(self, cx: float, cy: float, r: float, w: int = 1) -> None:
        inner = max(0.0, r - w)
        for y in range(ICON_H):
            for x in range(ICON_W):
                d2 = (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2
                if inner * inner < d2 <= r * r:
                    self.set(x, y)

    def arc(self, cx: float, cy: float, r: float, a0: float, a1: float, w: int = 1) -> None:
        """Angles in degrees, 0=east, 90=north (screen y grows down)."""
        steps = max(16, int(abs(a1 - a0) * 2))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            px = cx + r * math.cos(a)
            py = cy - r * math.sin(a)
            x, y = int(math.floor(px)), int(math.floor(py))
            off = (w - 1) // 2
            for oy in range(w):
                for ox in range(w):
                    self.set(x + ox - off, y + oy - off)

    def poly(self, pts: list[tuple[float, float]]) -> None:
        for y in range(ICON_H):
            for x in range(ICON_W):
                if _point_in_poly(x + 0.5, y + 0.5, pts):
                    self.set(x, y)

    def tri(self, a, b, c) -> None:
        self.poly([a, b, c])

    def mirror_lr(self) -> None:
        for y in range(ICON_H):
            for x in range(ICON_W // 2):
                self.px[y][ICON_W - 1 - x] = self.px[y][x]

    def star(self, cx: float, cy: float, r_out: float, r_in: float, rot_deg: float = -90.0) -> None:
        pts = []
        for i in range(10):
            r = r_out if i % 2 == 0 else r_in
            a = math.radians(rot_deg + i * 36.0)
            pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
        self.poly(pts)

    def stamp(self, rows: list[str], ox: int = 0, oy: int = 0) -> None:
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    self.set(x + ox, y + oy)
                elif ch == "o":
                    self.clear(x + ox, y + oy)

    # -- carving (details must be *holes*: white-on-white is invisible) -------
    def carve(self, fn) -> None:
        tmp = Mask()
        fn(tmp)
        for y in range(ICON_H):
            for x in range(ICON_W):
                if tmp.px[y][x]:
                    self.px[y][x] = 0

    def hole_line(self, x0: int, y0: int, x1: int, y1: int, w: int = 1) -> None:
        self.carve(lambda t: t.line(x0, y0, x1, y1, w))

    def hole_star(self, cx: float, cy: float, r_out: float, r_in: float) -> None:
        self.carve(lambda t: t.star(cx, cy, r_out, r_in))


def _point_in_poly(px: float, py: float, pts: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > py) != (yj > py):
            xcross = xi + (py - yi) * (xj - xi) / (yj - yi)
            if px < xcross:
                inside = not inside
        j = i
    return inside


# ---------------------------------------------------------------- icon definitions
# NN5: toàn bộ 54 icon được vẽ lại (phong cách NomNom: fill trắng, viền đen tự sinh,
# dáng mạnh 2px, khoảng lặp lại âm rõ ràng). Mỗi hàm nhận Mask 13x14 (0..12, 0..13).

def i_tps(m: Mask) -> None:
    # speedometer: dial + kim chéo đâm qua vành (vành bị khoét nơi kim đi qua)
    m.ring(6.0, 7.5, 5.6, w=2)
    m.line(6, 7, 10, 2, w=2)
    m.disc(6.0, 7.5, 1.6)
    m.hole(9, 2, 10, 3)
    m.hole(9, 4, 10, 5)
    # hai vạch đo trong mặt số
    m.vbar(3, 10, 11, w=1)
    m.vbar(9, 10, 11, w=1)


def i_ping(m: Mask) -> None:
    # ba cột sóng tăng dần, đáy cùng một hàng
    m.rect(0, 8, 2, 13)
    m.rect(5, 4, 7, 13)
    m.rect(10, 0, 12, 13)


def i_online(m: Mask) -> None:
    # hai người: người sau (phải) rồi người trước (trái) đè lên
    m.disc(9.3, 3.2, 2.1)
    m.poly([(7.5, 13), (12, 13), (11.2, 7), (8.2, 7)])
    m.disc(4.2, 4.6, 2.5)
    m.poly([(0, 13), (8, 13), (6.8, 8), (1.2, 8)])
    # đường phân cách hai thân
    m.hole_line(7, 8, 7, 13, w=1)


def i_bounty(m: Mask) -> None:
    # túi tiền: thân phồng, cổ buộc, ngôi sao khắc xuyên
    m.poly([(1.5, 6), (11.5, 6), (12.6, 9), (10, 13.6), (3, 13.6), (0.4, 9)])
    m.rect(4, 4, 8, 5)
    m.rect(3, 2, 9, 3)
    m.rect(5, 0, 7, 1)
    m.hole_star(6.0, 9.6, 2.7, 1.1)


def i_cash(m: Mask) -> None:
    # tờ tiền: seal tròn rỗng + hai mép bản.lẻ
    m.rect(0, 3, 12, 10)
    m.hole(0, 3, 0, 3)
    m.hole(12, 3, 12, 3)
    m.hole(0, 10, 0, 10)
    m.hole(12, 10, 12, 10)
    m.carve(lambda t: t.ring(6.0, 6.5, 2.7, w=1))


def i_coin(m: Mask) -> None:
    # đồng xu: vành đúc + vệt mint trên đỉnh
    m.disc(6.0, 6.8, 5.4)
    m.carve(lambda t: t.ring(6.0, 6.8, 3.1, w=1))
    m.hole(6, 2, 6, 3)


def i_sword(m: Mask) -> None:
    # kiếm chéo 45°: lưỡi NE, chuôi SW,-guard vuông góc, chuông tròn
    m.line(11, 2, 6, 7, w=2)
    m.set(12, 1)
    m.line(4, 4, 8, 8, w=2)
    m.line(6, 8, 3, 11, w=2)
    m.disc(1.9, 12.0, 1.3)


def i_shield(m: Mask) -> None:
    # khiên: thân nhu mì, chữ thập khắc xuyên
    m.poly([(1.5, 0.5), (11.5, 0.5), (11.5, 5), (9, 9.5), (6.5, 13), (4, 9.5), (1.5, 5)])
    m.hole(6, 3, 6, 9)
    m.hole(3, 5, 9, 5)


def i_land(m: Mask) -> None:
    # lô đất: nền đất dày, cột mốc + cờ bay
    m.hbar(11, 0, 12, w=2)
    m.vbar(3, 1, 10, w=2)
    m.tri((5, 1), (11, 3.4), (5, 6))
    m.vbar(9, 9, 10, w=1)
    m.vbar(11, 8, 10, w=1)


def i_market(m: Mask) -> None:
    # giỏ hàng: quai cung, vành miệng, thân thuôn + nan dọc
    m.arc(6, 7.2, 4.2, 0, 180, w=2)
    m.hbar(7, 0, 12, w=2)
    m.poly([(0.8, 8.5), (12.2, 8.5), (10, 13.6), (3, 13.6)])
    m.hole(4, 10, 4, 13)
    m.hole(8, 10, 8, 13)


def i_auction(m: Mask) -> None:
    # búa đấu giá: đầu búa dày 45°, cán xuôi về tay, đế tạ 2 bậc
    m.line(7, 2, 10, 5, w=3)
    m.line(6, 6, 1, 11, w=2)
    m.disc(0.9, 11.6, 1.2)
    m.hbar(13, 3, 10, w=1)
    m.hbar(12, 3, 9, w=1)


def i_casino(m: Mask) -> None:
    # hai xúc xắc: 3 chéo + 5 chấm
    m.rect(0, 1, 5, 6)
    m.hole(0, 1, 0, 1)
    m.hole(5, 1, 5, 1)
    m.hole(0, 6, 0, 6)
    m.hole(5, 6, 5, 6)
    m.hole(1, 3, 2, 4)
    m.hole(3, 2, 4, 2)
    m.hole(1, 5, 2, 5)
    m.rect(7, 7, 12, 12)
    m.hole(7, 7, 7, 7)
    m.hole(12, 7, 12, 7)
    m.hole(7, 12, 7, 12)
    m.hole(12, 12, 12, 12)
    m.hole(9, 9, 10, 10)
    m.hole(8, 8, 9, 8)
    m.hole(10, 8, 11, 8)
    m.hole(8, 10, 9, 10)
    m.hole(10, 10, 11, 10)


def i_mini(m: Mask) -> None:
    # tay cầm game: thân + hai bám, D-pad và nút khắc
    m.rect(0, 4, 12, 8)
    m.rect(0, 8, 3, 12)
    m.rect(9, 8, 12, 12)
    m.hole(0, 4, 0, 4)
    m.hole(12, 4, 12, 4)
    m.hole(3, 5, 3, 7)
    m.hole(2, 6, 4, 6)
    m.hole(8, 5, 9, 6)
    m.hole(10, 7, 11, 8)


def i_menu(m: Mask) -> None:
    # ba gạch: gạch giữa ngắn hơn một nhịp (menu kiểu mới)
    m.hbar(2, 0, 12, w=2)
    m.hbar(6, 2, 12, w=2)
    m.hbar(10, 0, 12, w=2)


def i_home(m: Mask) -> None:
    # mái nhà tam giác trùm kín + ống khói + cửa vòm
    m.tri((6, 0), (13, 6.5), (-1, 6.5))
    m.rect(9, 1, 10, 3)
    m.rect(1, 7, 11, 12)
    m.hole(1, 7, 11, 7)
    m.hole(5, 9, 7, 12)


def i_sethome(m: Mask) -> None:
    # nhà nhỏ + dấu cộng nổi bên phải, hai khối tách bạch bằng khe ring
    m.tri((3, 0), (8, 4.5), (-2, 4.5))
    m.rect(0, 5, 7, 10)
    m.hole(0, 5, 7, 5)
    m.hole(2, 7, 3, 10)
    m.rect(10, 6, 12, 8)
    m.rect(11, 5, 12, 9)


def i_spawn(m: Mask) -> None:
    # beacon: bệ, trụ, đèn kim cương tỏa sáng
    m.poly([(0, 13), (12, 13), (9.5, 10.5), (2.5, 10.5)])
    m.rect(5, 6, 7, 10)
    m.rect(4, 5, 8, 6)
    m.poly([(6, 0), (9, 2.4), (6, 4.6), (3, 2.4)])


def i_rp(m: Mask) -> None:
    # la bàn: vành + kim kim cương
    m.ring(6.0, 6.8, 5.8, w=2)
    m.poly([(6, 2.2), (7.8, 6.8), (6, 11.4), (4.2, 6.8)])


def i_mail(m: Mask) -> None:
    # phong bì: thân + nắp V khắc mở
    m.rect(0, 3, 12, 10)
    m.hole_line(1, 3, 6, 7)
    m.hole_line(11, 3, 6, 7)


def i_ally(m: Mask) -> None:
    # liên minh: hai vòng móc nhau, vòng sau bị chặn ở hai mặt cắt
    m.ring(4.2, 7.0, 3.5, w=2)
    m.ring(8.8, 7.0, 3.5, w=2)
    m.hole(6, 3, 6, 4)
    m.hole(6, 10, 6, 10)


def i_kill(m: Mask) -> None:
    # đầu lâu: sọ tròn, hàm, hai hốc mắt + răng
    m.disc(6.0, 5.0, 5.4)
    m.rect(3, 9, 9, 12)
    m.hole(3, 12, 3, 12)
    m.hole(9, 12, 9, 12)
    m.hole(2, 4, 3, 5)
    m.hole(7, 4, 8, 5)
    m.hole(6, 6, 6, 7)
    m.hole(5, 10, 5, 12)
    m.hole(7, 10, 7, 12)


def i_back(m: Mask) -> None:
    # mũi tên cong: cung trái, đầu nhọn, đuôi đổ xuống
    m.arc(8, 8.5, 5.0, 90, 180, w=2)
    m.tri((0, 8), (5, 4), (5, 12))
    m.vbar(8, 8, 13, w=2)


def i_bag(m: Mask) -> None:
    # ba lô: quai xách, thân bo góc, nắp và khóa
    m.vbar(3, 0, 3, w=1)
    m.vbar(9, 0, 3, w=1)
    m.rect(1, 3, 11, 12)
    m.hole(1, 3, 1, 3)
    m.hole(11, 3, 11, 3)
    m.hole(1, 12, 1, 12)
    m.hole(11, 12, 11, 12)
    m.hole(1, 6, 11, 6)
    m.rect(5, 5, 7, 8)
    m.hole(6, 6, 6, 7)


def i_bed(m: Mask) -> None:
    # giường: đầu giường cao, nệm, hai chân
    m.rect(0, 2, 2, 11)
    m.rect(2, 7, 12, 9)
    m.rect(3, 5, 6, 6)
    m.rect(2, 10, 3, 12)
    m.rect(10, 10, 11, 12)


def i_chest(m: Mask) -> None:
    # rương: nắp khe hở, thân, khoá giữa
    m.rect(1, 2, 11, 5)
    m.hole(1, 2, 1, 2)
    m.hole(11, 2, 11, 2)
    m.rect(0, 7, 12, 12)
    m.rect(5, 4, 7, 8)
    m.hole(6, 6, 6, 7)


def i_heart(m: Mask) -> None:
    m.stamp([
        "..###...###..",
        ".#####.#####.",
        "#############",
        "#############",
        ".###########.",
        "..#########..",
        "...#######...",
        "....#####....",
        ".....###.....",
        "......#......",
    ], oy=2)


def i_star(m: Mask) -> None:
    m.star(6.0, 6.9, 6.3, 2.2, rot_deg=-90)


def i_fire(m: Mask) -> None:
    m.stamp([
        "......#......",
        ".....#.#.....",
        "....#..#.....",
        "....#.##.....",
        "...##.##.....",
        "...#.#####...",
        "..##.######..",
        "..#########..",
        ".##########..",
        ".##########..",
        "..#########..",
        "...########..",
        "....######...",
        ".....##......",
    ])


def i_clock(m: Mask) -> None:
    m.disc(6.0, 6.8, 5.6)
    m.hole(6, 3, 6, 6)
    m.hole(6, 6, 9, 6)
    m.hole(6, 6, 6, 7)


def i_lock(m: Mask) -> None:
    m.ring(6.0, 4.6, 3.2, w=2)
    m.hole(6, 4, 6, 5)
    m.rect(1, 5, 11, 11)
    m.hole(1, 5, 1, 5)
    m.hole(11, 5, 11, 5)
    m.hole(1, 11, 1, 11)
    m.hole(11, 11, 11, 11)
    m.hole(5, 7, 7, 8)
    m.hole(6, 9, 6, 10)


def i_mail_verify(m: Mask) -> None:
    m.rect(0, 2, 12, 10)
    m.hole_line(1, 2, 5, 6)
    m.hole_line(11, 2, 6, 6)
    m.hole_line(3, 7, 5, 9, w=2)
    m.hole_line(5, 9, 10, 4, w=2)


def i_warn(m: Mask) -> None:
    m.tri((6, 0), (13, 13), (-1, 13))
    m.vbar(5, 4, 8, w=2)
    m.hole(5, 10, 6, 11)


def i_check(m: Mask) -> None:
    m.line(0, 7, 4, 11, w=3)
    m.line(4, 11, 11, 1, w=3)


def i_cross(m: Mask) -> None:
    m.line(1, 2, 11, 12, w=3)
    m.line(11, 2, 1, 12, w=3)


def i_arrow_l(m: Mask) -> None:
    m.rect(3, 5, 12, 7)
    m.tri((0, 6), (5, 1), (5, 12))


def i_arrow_r(m: Mask) -> None:
    i_arrow_l(m)
    m.mirror_lr()


def i_page_prev(m: Mask) -> None:
    m.tri((0, 7), (4, 3), (4, 11))
    m.rect(4, 6, 9, 8)
    m.rect(11, 1, 12, 13)


def i_page_next(m: Mask) -> None:
    i_page_prev(m)
    m.mirror_lr()


def i_search(m: Mask) -> None:
    m.ring(5.0, 5.0, 4.6, w=2)
    m.line(7, 8, 11, 12, w=3)


def i_sort(m: Mask) -> None:
    m.tri((1, 0), (11, 0), (6, 5))
    m.rect(5, 4, 7, 9)
    m.tri((1, 13), (11, 13), (6, 8))


def i_plus(m: Mask) -> None:
    m.rect(0, 5, 12, 7)
    m.rect(5, 1, 7, 12)


def i_minus(m: Mask) -> None:
    m.rect(0, 5, 12, 7)


def i_crown(m: Mask) -> None:
    m.stamp([
        "#...........#",
        "##.........##",
        "###..###..###",
        "#############",
        "#############",
        "##o###o###o##",
        "#############",
        "#############",
    ], oy=3)


def _badge(m: Mask, top: int = 0) -> None:
    m.poly([(6, top), (12, top + 3), (12, 9), (6, 13), (0, 9), (0, top + 3)])


def _numeral(m: Mask, kind: str) -> None:
    """Numerals are holes: the ring pass paints them black inside the badge."""
    if kind == "I":
        m.hole(5, 3, 6, 9)
        m.hole(3, 3, 8, 3)
        m.hole(3, 9, 8, 9)
    elif kind == "II":
        for x in (2, 8):
            m.hole(x, 3, x + 1, 9)
            m.hole(x - 1, 3, x + 2, 3)
            m.hole(x - 1, 9, x + 2, 9)
    elif kind == "III":
        for x in (1, 5, 9):
            m.hole(x, 3, x + 1, 9)
            m.hole(x, 3, x + 1, 3)
    elif kind == "IV":
        m.hole(1, 3, 2, 9)
        m.hole_line(5, 3, 7, 10, w=2)
        m.hole_line(10, 3, 8, 10, w=2)
    elif kind == "V":
        m.hole_line(3, 3, 6, 10, w=2)
        m.hole_line(9, 3, 6, 10, w=2)


def _tier(kind: str, crown: bool = False):
    def draw(m: Mask) -> None:
        if crown:
            m.rect(0, 0, 2, 2)
            m.rect(5, 0, 7, 1)
            m.rect(10, 0, 12, 2)
        _badge(m, top=2 if crown else 0)
        _numeral(m, kind)
    return draw


def i_tier1(m: Mask) -> None: _tier("I")(m)
def i_tier2(m: Mask) -> None: _tier("II")(m)
def i_tier3(m: Mask) -> None: _tier("III")(m)
def i_tier4(m: Mask) -> None: _tier("IV")(m)
def i_tier5(m: Mask) -> None: _tier("V", crown=True)(m)


# ---- 6 icon mới U+E030..U+E035 (NN5) ---------------------------------------

def i_book(m: Mask) -> None:
    # sổ tay mở: hai trang xòe, sống giữa hở, khe trang khắc
    m.poly([(0, 3), (5, 1), (5, 11), (0, 13)])
    m.poly([(12, 3), (7, 1), (7, 11), (12, 13)])
    m.hole(2, 4, 4, 4)
    m.hole(8, 4, 10, 4)
    m.hole(2, 6, 4, 6)
    m.hole(8, 6, 10, 6)
    m.hole(2, 8, 4, 8)
    m.hole(8, 8, 10, 8)


def i_sell(m: Mask) -> None:
    # thẻ giá mũi trái + lỗ dây; hai vạch chuyển động bên phải
    m.poly([(11, 2), (4, 2), (1, 6.5), (4, 11), (11, 11)])
    m.hole(8, 5, 9, 6)
    m.rect(12, 4, 12, 5)
    m.rect(12, 8, 12, 9)


def i_friendly(m: Mask) -> None:
    # hai trái tim chồng mép (đấu tập thân thiện)
    m.stamp([
        ".##.##.",
        "#######",
        "#######",
        ".#####.",
        "..###..",
        "...#...",
    ], ox=0, oy=6)
    m.stamp([
        ".##.##.",
        "#######",
        ".#####.",
        "..###..",
        "...#...",
    ], ox=6, oy=0)


def i_shop(m: Mask) -> None:
    # cửa hàng: mái sạp bao quanh + thân, cửa đi
    m.rect(0, 1, 12, 3)
    m.hole(1, 3, 1, 3)
    m.hole(4, 3, 4, 3)
    m.hole(7, 3, 7, 3)
    m.hole(10, 3, 10, 3)
    m.rect(1, 4, 11, 13)
    m.hole(5, 9, 7, 13)
    m.hole(2, 6, 3, 7)


def i_chat_tag(m: Mask) -> None:
    # bong bóng chat + sao khắc (tag đặc biệt)
    m.rect(0, 2, 12, 9)
    m.hole(0, 2, 0, 2)
    m.hole(12, 2, 12, 2)
    m.hole(0, 9, 0, 9)
    m.poly([(2, 9), (6, 9), (2, 13)])
    m.hole_star(6.0, 5.4, 2.4, 1.0)


def i_worldtime(m: Mask) -> None:
    # mặt trời + kim giờ: quỹ đạo thế giới
    m.disc(6.0, 6.8, 4.2)
    m.hole(6, 4, 6, 6)
    m.hole(6, 6, 8, 6)
    m.vbar(6, 0, 1, w=1)
    m.vbar(6, 13, 13, w=1)
    m.hbar(0, 6, 1, 7)
    m.hbar(11, 6, 12, 7)
    m.set(2, 2)
    m.set(10, 2)
    m.set(2, 11)
    m.set(10, 11)


ICON_DRAW = {
    "tps": i_tps, "ping": i_ping, "online": i_online, "bounty": i_bounty,
    "cash": i_cash, "coin": i_coin, "sword": i_sword, "shield": i_shield,
    "land": i_land, "market": i_market, "auction": i_auction, "casino": i_casino,
    "mini": i_mini, "menu": i_menu, "home": i_home, "sethome": i_sethome,
    "spawn": i_spawn, "rp": i_rp, "mail": i_mail, "ally": i_ally,
    "kill": i_kill, "back": i_back, "bag": i_bag, "bed": i_bed,
    "chest": i_chest, "heart": i_heart, "star": i_star, "fire": i_fire,
    "clock": i_clock, "lock": i_lock, "mail-verify": i_mail_verify, "warn": i_warn,
    "check": i_check, "cross": i_cross, "arrow-l": i_arrow_l, "arrow-r": i_arrow_r,
    "page-prev": i_page_prev, "page-next": i_page_next, "search": i_search,
    "sort": i_sort, "plus": i_plus, "minus": i_minus, "crown": i_crown,
    "tier1": i_tier1, "tier2": i_tier2, "tier3": i_tier3, "tier4": i_tier4,
    "tier5": i_tier5,
    "book": i_book, "sell": i_sell, "friendly": i_friendly, "shop": i_shop,
    "chat-tag": i_chat_tag, "worldtime": i_worldtime,
}


def compose_icon(mask: Mask) -> Image.Image:
    """White fill + 1px black 8-neighbour ring on a 16x16 cell, binary alpha."""
    fill = [[0] * ICELL for _ in range(ICELL)]
    ox, oy = ICON_OFFSET
    for y in range(ICON_H):
        for x in range(ICON_W):
            if mask.px[y][x]:
                fill[y + oy][x + ox] = 1

    img = Image.new("RGBA", (ICELL, ICELL), (0, 0, 0, 0))
    px = img.load()
    for y in range(ICELL):
        for x in range(ICELL):
            if fill[y][x]:
                px[x, y] = (255, 255, 255, 255)
            else:
                ring = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < ICELL and 0 <= xx < ICELL and fill[yy][xx]:
                            ring = True
                if ring:
                    px[x, y] = (0, 0, 0, 255)
    if not any(px[x, y][3] for x in range(ICELL) for y in range(ICELL)):
        raise SystemExit("empty icon mask")
    return img


def build_icon_atlas(icons: list[dict]) -> tuple[Image.Image, dict]:
    atlas = Image.new("RGBA", (ICON_COLS * ICELL, ICON_ROWS * ICELL), (0, 0, 0, 0))
    metrics: dict[str, dict] = {}
    for i, icon in enumerate(icons):
        mask = Mask()
        ICON_DRAW[icon["id"]](mask)
        img = compose_icon(mask)
        row, col = divmod(i, ICON_COLS)
        atlas.alpha_composite(img, (col * ICELL, row * ICELL))
        img.save(TEX_ICON / f"{icon['id']}.png")
        iw = ink_width(img)
        adv = round_half_up(iw * (9.0 / ICELL)) + 1 if iw else 0
        metrics[icon["id"]] = {"ink_w": iw, "advance9": adv, "row": row, "col": col}
    return atlas, metrics


# ============================================================================ json
def chars_grid(cps: list[int], cols: int) -> list[str]:
    rows = []
    for r in range(0, max(len(cps), 1), cols):
        chunk = cps[r:r + cols]
        row = "".join(chr(c) for c in chunk)
        if len(row) < cols:
            row += "\u0000" * (cols - len(row))
        rows.append(row)
    return rows


def bitmap_json(rows: list[str], texture: str, height: int, ascent: int) -> dict:
    return {
        "providers": [
            {
                "type": "bitmap",
                "file": texture,
                "height": height,
                "ascent": ascent,
                "chars": rows,
            }
        ]
    }


def write_json(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def default_font_json(text_rows: list[str]) -> dict:
    return {
        "providers": [
            {"type": "bitmap", "file": "nomnom:font/vi_text.png",
             "height": CELL_H, "ascent": BASELINE, "chars": text_rows},
            {"type": "reference", "id": "minecraft:include/space"},
            {"type": "reference", "id": "minecraft:include/default",
             "filter": {"uniform": False}},
            {"type": "reference", "id": "nomnom:ui"},
            {"type": "reference", "id": "minecraft:include/unifont"},
        ]
    }


# ======================================================================== validate
def verify(log: list[str], expect_icons: list[dict]) -> dict:
    res: dict = {}
    mc = MC_FONT / "default.json"
    alias = FONT_ASSETS / "default.json"
    ui = FONT_ASSETS / "ui.json"

    mc_doc = json.loads(mc.read_text(encoding="utf-8"))
    alias_doc = json.loads(alias.read_text(encoding="utf-8"))
    ui_doc = json.loads(ui.read_text(encoding="utf-8"))

    refs = [p.get("id") for p in mc_doc["providers"] if p.get("type") == "reference"]
    res["default_refs"] = refs
    assert refs == ["minecraft:include/space", "minecraft:include/default",
                    "nomnom:ui", "minecraft:include/unifont"], refs
    assert mc_doc == alias_doc, "nomnom:default alias differs from the override"
    assert len(mc_doc["providers"][0]["chars"]) == TEXT_ROWS
    assert all(len(r) == TEXT_COLS for r in mc_doc["providers"][0]["chars"])
    assert mc_doc["providers"][0]["height"] == CELL_H
    assert mc_doc["providers"][0]["ascent"] == BASELINE
    assert BASELINE <= CELL_H

    # ---- text glyphs
    text_rows = mc_doc["providers"][0]["chars"]
    text_cps = [ord(c) for r in text_rows for c in r if c != "\u0000"]
    res["text_glyphs"] = len(text_cps)
    res["text_duplicates"] = len(text_cps) - len(set(text_cps))
    assert len(text_cps) == len(set(text_cps)), "duplicate text codepoints"
    assert len(text_cps) >= 300, f"only {len(text_cps)} text glyphs"

    vi = vietnamese_chars()
    missing_vi = [c for c in vi if ord(c) not in set(text_cps)]
    res["vi_total"] = len(vi)
    res["vi_missing"] = missing_vi
    assert not missing_vi, f"missing Vietnamese chars: {missing_vi}"

    atlas = Image.open(TEX_FONT / "vi_text.png").convert("RGBA")
    res["text_atlas_size"] = list(atlas.size)
    assert atlas.size == (TEXT_COLS * CELL_W, TEXT_ROWS * CELL_H)
    alpha = atlas.getchannel("A")
    res["text_atlas_ink_px"] = sum(alpha.histogram()[1:])
    assert res["text_atlas_ink_px"] > 0, "text atlas is empty"

    # every codepoint on disk must have ink in its own cell
    empty_cells = []
    for i, cp in enumerate(text_cps):
        row, col = divmod(i, TEXT_COLS)
        cell = atlas.crop((col * CELL_W, row * CELL_H, col * CELL_W + CELL_W, row * CELL_H + CELL_H))
        if cell.getchannel("A").getbbox() is None:
            empty_cells.append(hex_cp(cp))
    res["text_empty_cells"] = empty_cells
    assert not empty_cells, f"empty glyph cells: {empty_cells}"

    # ---- icon font
    icon_rows = ui_doc["providers"][0]["chars"]
    assert ui_doc["providers"][0]["height"] == 9
    assert ui_doc["providers"][0]["ascent"] == 9
    assert len(icon_rows) == ICON_ROWS and all(len(r) == ICON_COLS for r in icon_rows)
    icon_cps = [ord(c) for r in icon_rows for c in r if c != "\u0000"]
    res["icon_codepoints"] = len(icon_cps)
    res["icon_contiguous"] = icon_cps == list(range(0xE000, 0xE000 + len(icon_cps)))
    res["icon_range"] = f"U+E000..U+{0xE000 + len(icon_cps) - 1:04X}"
    assert res["icon_contiguous"]
    assert len(set(icon_cps)) == len(icon_cps)

    # manifest and JSON must agree, codepoint for codepoint
    manifest_cps = [int(x["cp"][2:], 16) for x in expect_icons]
    assert manifest_cps == icon_cps, "icons-nn5.json order != ui.json chars grid"

    # v1.0 compat: first 48 codepoints must match nn4-icons.json exactly
    v1 = json.loads(ICON_JSON_V1.read_text(encoding="utf-8"))
    v1_cps = [int(x["cp"][2:], 16) for x in v1["icons"]]
    v1_ids = [x["id"] for x in v1["icons"]]
    assert manifest_cps[:48] == v1_cps[:48], "v1 codepoints drifted (E000..E02F must stay stable)"
    assert [x["id"] for x in expect_icons][:48] == v1_ids[:48], "v1 icon ids drifted"

    icon_atlas = Image.open(TEX_FONT / "icons.png").convert("RGBA")
    res["icon_atlas_size"] = list(icon_atlas.size)
    assert icon_atlas.size == (ICON_COLS * ICELL, ICON_ROWS * ICELL)
    blank = []
    for i, icon in enumerate(expect_icons):
        row, col = divmod(i, ICON_COLS)
        cell = icon_atlas.crop((col * ICELL, row * ICELL, col * ICELL + ICELL, row * ICELL + ICELL))
        colors = cell.getcolors(maxcolors=32) or []
        if len(colors) <= 1:
            blank.append(icon["id"])
        # right-most column must stay empty so advance == 9 for full-width icons
        right_col = [cell.getpixel((ICELL - 1, y))[3] for y in range(ICELL)]
        if any(right_col):
            blank.append(icon["id"] + "(right-margin)")
    res["icon_blank"] = blank
    assert not blank, f"blank/bad icons: {blank}"

    # individual files
    missing_files = [i["id"] for i in expect_icons if not (TEX_ICON / f"{i['id']}.png").is_file()]
    assert not missing_files, f"missing icon png: {missing_files}"

    # ---- names
    names = set(i["id"] for i in expect_icons) | set(ICON_ALIASES)
    missing_names = [n for n in REQUIRED_ICON_NAMES if n not in names]
    res["names_missing"] = missing_names
    assert not missing_names, f"icon names missing: {missing_names}"

    res["ok"] = True
    return res


ICON_ALIASES = {"confirm": "check", "cancel": "cross"}


def vertical_metrics(atlas: Image.Image, glyphs: list[dict]) -> dict:
    """Ink extents drive the line-height risk documented in nn5-decisions-rp.md."""
    tops, bots, desc = [], [], 0
    for g in glyphs:
        cell = atlas.crop((g["col"] * CELL_W, g["row"] * CELL_H,
                           g["col"] * CELL_W + CELL_W, g["row"] * CELL_H + CELL_H)).getchannel("A")
        bb = cell.getbbox()
        if not bb:
            continue
        tops.append(bb[1])
        bots.append(bb[3])          # exclusive -> last ink row is bb[3]-1
        if bb[3] > BASELINE:
            desc += 1
    top_min, bot_max = min(tops), max(bots)
    return {
        "ink_top_min": top_min,
        "ink_bottom_max": bot_max,
        "descenders": desc,
        "above_cap": sum(1 for t in tops if t < BASELINE - 9),
        "worst_line_overlap_px": bot_max - (top_min + 9),   # client Font.lineHeight = 9
    }


# ======================================================================== manifest
def write_charset_tsv(glyphs: list[dict], icons: list[dict], metrics: dict) -> None:
    lines = ["# cp\tchar\tkind\trow\tcol\tink_w\tadvance_20px\tadvance_9px\tnote"]
    for g in glyphs:
        ch = g["char"]
        lines.append("\t".join([
            hex_cp(g["cp"]), ch, "text", str(g["row"]), str(g["col"]),
            str(g["ink_w"]), str(g["advance"]), "", unicodedata.name(ch, "?"),
        ]))
    for icon in icons:
        cp = int(icon["cp"][2:], 16)
        m = metrics[icon["id"]]
        lines.append("\t".join([
            hex_cp(cp), chr(cp), "icon", str(m["row"]), str(m["col"]),
            str(m["ink_w"]), "", str(m["advance9"]), icon["id"],
        ]))
    (FONT_ASSETS / "charset.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def font_info(res: dict) -> str:
    return f"""NomNom UI Text / NomNom UI Icons (NN5 rebuild)
=============================================
Family          : NomNom UI Text (derived from Be Vietnam Pro)
Upstream        : https://github.com/bettergui/BeVietnamPro
Source file     : BeVietnamPro-Regular.ttf  ({sha256(TTF_REGULAR)})
License         : SIL Open Font License 1.1 - see ../../../LICENSE-OFL.txt (verbatim OFL.txt)
                  Copyright 2021 The Be Vietnam Pro Project Authors.
                  "NomNom UI Text" is a derivative; no Reserved Font Name is claimed by upstream.

TEXT FONT (provider id minecraft:default, override at assets/minecraft/font/default.json)
  Grid          : {TEXT_COLS}x{TEXT_ROWS} cells of {CELL_W}x{CELL_H} px = {TEXT_COLS*CELL_W}x{TEXT_ROWS*CELL_H} px  (nomnom:font/vi_text.png)
  Rasterisation : FreeType via Pillow, rendered DIRECTLY at final size (em {EM_PX} px, hinted —
                  no supersample/downscale like v1.0), baseline {BASELINE} px, then contrast
                  curve alpha {ALPHA_LOW}..{ALPHA_HIGH} -> 0..255 (cuts halo, keeps edge AA).
                  White RGB for text tinting.
  Baseline      : {BASELINE} px from cell top (provider "ascent": {BASELINE}, "height": {CELL_H})
  Codepoints    : {res.get('text_glyphs', 0)} text glyphs
  Vietnamese    : {res.get('vi_total', 0)}/{res.get('vi_total', 0)} precomposed characters
                  (12 vowels x 6 tones, upper+lower, + d/D)
  Space         : not in the atlas - provided by minecraft:include/space (4 px)
  Advances      : computed by the client, advance = round_half_up(ink_w * height / cell_h) + 1
                  (BitmapProvider#load). No advance is stored in the JSON.
  Fallbacks     : minecraft:include/default + minecraft:include/unifont cover everything this
                  atlas omits (U+2014 em dash, U+20AB dong sign, U+2726/U+2694/U+2713 HUD symbols,
                  combining marks, CJK). Do not remove those references.

ICON FONT (provider id nomnom:ui, assets/nomnom/font/ui.json)
  Grid          : {ICON_COLS}x{ICON_ROWS} cells of {ICELL}x{ICELL} px = {ICON_COLS*ICELL}x{ICON_ROWS*ICELL} px  (nomnom:font/icons.png)
  Range         : U+E000..U+E035, {res.get('icon_codepoints', 0)} glyphs, private use area only
                  (U+E000..U+E02F byte-stable vs v1.0; U+E030..U+E035 added in NN5:
                  book, sell, friendly, shop, chat-tag, worldtime)
  Provider      : height 9, ascent 9 -> rendered 9 px tall, proportional advance
  Art           : white #FFFFFF fill + 1 px black #000000 ring, binary alpha, 13x14 fill mask
                  inset 1 px in a 16x16 cell (column 15 stays transparent -> advance 9)
  Referenced by : minecraft:default, so legacy section-sign strings render PUA icons too
  Registry      : work/rp_build/icons-nn5.json (id, codepoint, ASCII fallback);
                  aliases confirm=check, cancel=cross

HUD PACK (NomNomUI-HUD, font id nomnom:hud — see work/rp_build/hud_src/HUD-INFO.txt)
  Pack phụ cho sidebar/tablist: digits fixed-width U+E040.., ornament/khung U+E050..
  Pack này KHÔNG đóng gói font text; override default.json của nó tham chiếu chéo
  nomnom:font/vi_text.png (nếu pack chính vắng mặt, chữ rơi về fallback vanilla).

Generated by work/rp_build/build_font.py (NN5) - do not hand edit.
"""


# ======================================================================== previews
def write_previews(glyphs: list[dict], icons: list[dict], metrics: dict) -> None:
    # icons at 8x with labels
    scale, pad, label_h = 8, 6, 12
    cw = ICELL * scale + pad
    cols = 8
    rows = (len(icons) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw + pad, rows * (cw + label_h) + pad), (18, 24, 33))
    d = ImageDraw.Draw(sheet)
    try:
        fnt_s = ImageFont.truetype(str(TTF_REGULAR), 8)
    except Exception:                                     # pragma: no cover
        fnt_s = ImageFont.load_default()
    for i, icon in enumerate(icons):
        r, c = divmod(i, cols)
        x = pad + c * cw
        y = pad + r * (cw + label_h)
        img = Image.open(TEX_ICON / f"{icon['id']}.png").convert("RGBA")
        big = img.resize((ICELL * scale, ICELL * scale), Image.NEAREST)
        bg = Image.new("RGBA", big.size, (18, 24, 33, 255))
        bg.alpha_composite(big)
        sheet.paste(bg.convert("RGB"), (x, y))
        d.text((x + 2, y + ICELL * scale + 1),
               f"{icon['cp']} {icon['id']} a={metrics[icon['id']]['advance9']}",
               font=fnt_s, fill=(154, 164, 178))
        small = img.resize((9, 9), Image.NEAREST)
        sb = Image.new("RGBA", (9, 9), (18, 24, 33, 255))
        sb.alpha_composite(small)
        sheet.paste(sb.convert("RGB"), (x + ICELL * scale - 11, y + 1))
    sheet.save(HERE / "preview_icons.png")

    # true-size simulation: each icon at the 9 px render height, upscaled 6x,
    # white and gold-400 tints on ink-800 (the black 1 px ring must survive both)
    def tint(img: Image.Image, rgb: tuple[int, int, int]) -> Image.Image:
        out = img.convert("RGBA")
        px = out.load()
        for yy in range(out.height):
            for xx in range(out.width):
                r_, g_, b_, a_ = px[xx, yy]
                if a_ and r_ > 127:
                    px[xx, yy] = (rgb[0], rgb[1], rgb[2], a_)
        return out

    s9, cw9, pad9 = 6, 58, 4
    cols9 = 12
    rows9 = (len(icons) + cols9 - 1) // cols9
    entry_h = s9 * 9 * 2 + 4 + 11
    sheet9 = Image.new("RGB", (cols9 * cw9 + pad9, rows9 * entry_h + pad9), (11, 15, 20))
    d9 = ImageDraw.Draw(sheet9)
    for i, icon in enumerate(icons):
        r, c = divmod(i, cols9)
        x9 = pad9 + c * cw9
        y9 = pad9 + r * entry_h
        src = Image.open(TEX_ICON / f"{icon['id']}.png").convert("RGBA").resize((9, 9), Image.BILINEAR)
        for k, rgb in enumerate([(242, 244, 248), (232, 180, 80)]):
            cell9 = Image.new("RGBA", (9, 9), (18, 24, 33, 255))
            cell9.alpha_composite(tint(src, rgb))
            sheet9.paste(cell9.convert("RGB").resize((s9 * 9, s9 * 9), Image.NEAREST), (x9, y9 + k * s9 * 9))
        d9.text((x9, y9 + 2 * s9 * 9), icon["id"][:10], font=fnt_s, fill=(154, 164, 178))
    sheet9.save(HERE / "preview_icons_9px.png")

    # text line built with the client advance rule, 3x
    atlas = Image.open(TEX_FONT / "vi_text.png").convert("RGBA")
    cells = {}
    for g in glyphs:
        cells[g["cp"]] = (g, atlas.crop((g["col"] * CELL_W, g["row"] * CELL_H,
                                         g["col"] * CELL_W + CELL_W, g["row"] * CELL_H + CELL_H)))
    # only codepoints that live in this atlas; everything else (em dash, ₫, ✦, ⚔)
    # is served by the vanilla fallback providers, see work/nn4-decisions-font.md
    line = "Tiếng Việt: Ế ộ ữ ự ỹ - Nhà bán đất #123, giá 1.250.000 (OK)"
    x = 0
    strip = Image.new("RGBA", (2200, 26), (18, 24, 33, 255))
    for ch in line:
        if ch == " ":
            x += 5
            continue
        if ord(ch) not in cells:
            x += 8
            continue
        g, cell = cells[ord(ch)]
        strip.alpha_composite(cell, (x, 2))
        x += g["advance"]
    strip = strip.crop((0, 0, max(x + 8, 1), 26))
    strip.convert("RGB").resize((strip.width * 3, 78), Image.NEAREST).save(HERE / "preview_text.png")


# ============================================================================ main
def main() -> int:
    if not __debug__:                    # verify() uses assert; -O would silently skip it
        raise SystemExit("refusing to run with python -O: the self-checks are assertions")
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args()

    for p in (FONT_ASSETS, TEX_FONT, TEX_ICON, MC_FONT):
        p.mkdir(parents=True, exist_ok=True)

    log: list[str] = []

    if not args.verify_only:
        # --- guard the inputs
        if sha256(TTF_REGULAR) != SHA_REGULAR:
            raise SystemExit("BeVietnamPro-Regular.ttf hash mismatch - refusing to build")
        if sha256(OFL_SRC) != SHA_OFL:
            raise SystemExit("OFL.txt hash mismatch - refusing to build")
        shutil.copyfile(OFL_SRC, RP / "LICENSE-OFL.txt")

        meta = json.loads(ICON_JSON.read_text(encoding="utf-8"))
        icons = meta["icons"]
        if len(icons) != 54:
            raise SystemExit(f"icons-nn5.json has {len(icons)} icons, expected 54")
        unknown = [i["id"] for i in icons if i["id"] not in ICON_DRAW]
        if unknown:
            raise SystemExit(f"no painter for: {unknown}")
        if set(ICON_DRAW) != {i["id"] for i in icons}:
            raise SystemExit("ICON_DRAW has entries not present in icons-nn5.json")

        # --- text
        text_atlas, glyphs, cps = build_text_atlas(log)
        text_atlas.save(TEX_FONT / "vi_text.png")
        text_rows = chars_grid(cps, TEXT_COLS)

        # --- icons
        icon_atlas, metrics = build_icon_atlas(icons)
        icon_atlas.save(TEX_FONT / "icons.png")
        icon_rows = chars_grid([int(i["cp"][2:], 16) for i in icons], ICON_COLS)

        # --- json
        write_json(MC_FONT / "default.json", default_font_json(text_rows))
        write_json(FONT_ASSETS / "default.json", default_font_json(text_rows))
        write_json(FONT_ASSETS / "ui.json",
                   bitmap_json(icon_rows, "nomnom:font/icons.png", 9, 9))
        write_charset_tsv(glyphs, icons, metrics)
        if not args.no_preview:
            write_previews(glyphs, icons, metrics)
    else:
        meta = json.loads(ICON_JSON.read_text(encoding="utf-8"))
        icons = meta["icons"]

    # --- always verify
    res = verify(log, icons)
    res["text_glyphs"] = res.get("text_glyphs", 0)
    info = {
        "text_glyphs": res["text_glyphs"],
        "text_atlas": res["text_atlas_size"],
        "text_ink_px": res["text_atlas_ink_px"],
        "vietnamese": f"{res['vi_total'] - len(res['vi_missing'])}/{res['vi_total']}",
        "icons": res["icon_codepoints"],
        "icon_atlas": res["icon_atlas_size"],
        "icon_range": res["icon_range"],
        "default_refs": res["default_refs"],
    }

    # FONT-INFO carries the measured coverage, so it is written after verification
    if not args.verify_only:
        (FONT_ASSETS / "FONT-INFO.txt").write_text(font_info(res), encoding="utf-8", newline="\n")

    print("== NomNom font build (NN5) ==")
    for k, v in info.items():
        print(f"  {k:14}: {v}")

    # vertical metrics are design-relevant (line-height 9 px vs a 20 px cell)
    atlas_disk = Image.open(TEX_FONT / "vi_text.png").convert("RGBA")
    cps_disk = [ord(c) for r in json.loads(
        (MC_FONT / "default.json").read_text(encoding="utf-8"))["providers"][0]["chars"]
        for c in r if c != "\u0000"]
    glyphs_disk = [{"cp": cp, "row": i // TEXT_COLS, "col": i % TEXT_COLS}
                   for i, cp in enumerate(cps_disk)]
    vm = vertical_metrics(atlas_disk, glyphs_disk)
    print("  vertical      : " + ", ".join(f"{k}={v}" for k, v in vm.items()))
    if log:
        for line in log:
            print("  " + line)

    # --- char -> icon table (the one the task asks the build to print)
    print("\n== char -> icon (nomnom:ui, U+E000..U+E035) ==")
    print(f"{'CP':7} {'char':5} {'id':12} {'ascii':5} {'label':9} {'ink':>3} {'adv9':>4}")
    meta_by_id = {i["id"]: i for i in icons}
    metrics = {}
    icon_atlas = Image.open(TEX_FONT / "icons.png").convert("RGBA")
    for i, icon in enumerate(icons):
        row, col = divmod(i, ICON_COLS)
        cell = icon_atlas.crop((col * ICELL, row * ICELL, col * ICELL + ICELL, row * ICELL + ICELL))
        iw = ink_width(cell)
        adv = round_half_up(iw * 9.0 / ICELL) + 1 if iw else 0
        metrics[icon["id"]] = adv
        print(f"{icon['cp']:7} {chr(int(icon['cp'][2:], 16)):5} {icon['id']:12} "
              f"{icon['ascii']:5} {icon['label']:9} {iw:3} {adv:4}")
    print(f"\naliases: {json.dumps(ICON_ALIASES)}  ({len(icons)} glyphs, "
          f"{len(icons) + len(ICON_ALIASES)} names)")
    print(f"names required: {len(REQUIRED_ICON_NAMES)} / covered: "
          f"{len(set(REQUIRED_ICON_NAMES) & (set(meta_by_id) | set(ICON_ALIASES)))}")
    print(f"outputs: {RP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
