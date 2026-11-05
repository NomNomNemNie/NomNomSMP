#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NomNom UI Kit -- GUI texture + item model generator (resource pack, 1.21.11).

Deterministic, idempotent, pixel-art only (binary alpha, no anti-aliasing).

Usage (run from anywhere):
    python work/rp_build/build_gui.py            # generate textures + JSON
    python work/rp_build/build_gui.py --check    # verify on-disk == regenerated
    python work/rp_build/build_gui.py --preview  # also write QA preview sheets

Outputs:
    work/rp_src/assets/nomnom/textures/gui/**            (9-slice, slots)
    work/rp_src/assets/nomnom/textures/item/ui/**         (16x16 UI items, 32x32 icons)
    work/rp_src/assets/nomnom/textures/gui/items/**       (byte-identical mirror)
    work/rp_src/assets/nomnom/models/item/ui/**           (model JSON)
    work/rp_src/assets/nomnom/items/ui/**                 (item_model definitions)
    work/rp_build/gui_manifest.json                       (build manifest + hashes)

Design source: work/nn4-design.md sections 1.3-1.6, 4.6; decisions D10-D12/D16.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
RP = HERE.parent if (HERE.parent / "assets").is_dir() else WORK / "rp_src"  # repo: resourcepack/, workspace: work/rp_src
ASSETS = RP / "assets" / "nomnom"
TEX = ASSETS / "textures"
MODELS = ASSETS / "models" / "item" / "ui"
ITEMS = ASSETS / "items" / "ui"
MANIFEST = HERE / "gui_manifest.json"

# ---------------------------------------------------------------------------
# Palette (work/nn4-design.md 1.1 + 1.5; no colours outside this table)
# ---------------------------------------------------------------------------

INK_950 = (0x07, 0x0A, 0x0E, 255)
INK_900 = (0x0B, 0x0F, 0x14, 255)
INK_800 = (0x12, 0x18, 0x21, 255)
INK_700 = (0x1B, 0x24, 0x30, 255)
INK_600 = (0x24, 0x30, 0x40, 255)
GOLD_600 = (0xB1, 0x7C, 0x17, 255)
GOLD_400 = (0xE8, 0xB4, 0x50, 255)
GOLD_200 = (0xF6, 0xD9, 0x8A, 255)
LIME_600 = (0x47, 0x9C, 0x23, 255)
LIME_400 = (0x7D, 0xD9, 0x57, 255)
LIME_200 = (0xB7, 0xEA, 0xA2, 255)
RED_600 = (0xA8, 0x2F, 0x2F, 255)
RED_400 = (0xE4, 0x57, 0x57, 255)
RED_300 = (0xF0, 0x7A, 0x7A, 255)
AQUA_400 = (0x4C, 0xC9, 0xF0, 255)
AQUA_600 = (0x10, 0x93, 0xBC, 255)
AQUA_200 = (0xA1, 0xE3, 0xF7, 255)
VIOLET_400 = (0xB0, 0x84, 0xF5, 255)
VIOLET_600 = (0x7A, 0x4B, 0xC4, 255)
VIOLET_200 = (0xE7, 0xD9, 0xFC, 255)
TEXT_100 = (0xF2, 0xF4, 0xF8, 255)
TEXT_500 = (0x9A, 0xA4, 0xB2, 255)
TEXT_700 = (0x5F, 0x6B, 0x7D, 255)
SILVER_200 = (0xCE, 0xD3, 0xDA, 255)
TRANSPARENT = (0, 0, 0, 0)

# Button hover faces are the +12 L values given in design 1.4.
GREEN_HOVER = (0xA4, 0xE4, 0x89, 255)
GREEN_HOVER_LIGHT = (0xD7, 0xF3, 0xCB, 255)
GREEN_HOVER_DARK = (0x71, 0xD5, 0x47, 255)
GOLD_HOVER = (0xEF, 0xCB, 0x86, 255)
GOLD_HOVER_LIGHT = (0xF9, 0xEA, 0xCE, 255)
GOLD_HOVER_DARK = (0xE5, 0xAC, 0x3E, 255)
GRAY_HOVER = (0x31, 0x41, 0x57, 255)
GRAY_HOVER_LIGHT = (0x4E, 0x68, 0x8B, 255)
GRAY_HOVER_DARK = (0x14, 0x1A, 0x23, 255)


# ---------------------------------------------------------------------------
# Pixel canvas
# ---------------------------------------------------------------------------

class Canvas:
    """Tiny RGBA pixel canvas; every write is opaque or fully transparent."""

    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.px = [[TRANSPARENT for _ in range(w)] for _ in range(h)]

    # -- basics -------------------------------------------------------------
    def get(self, x: int, y: int):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return TRANSPARENT

    def set(self, x: int, y: int, c) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def rect(self, x: int, y: int, w: int, h: int, c) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def hline(self, x: int, y: int, w: int, c) -> None:
        self.rect(x, y, w, 1, c)

    def vline(self, x: int, y: int, h: int, c) -> None:
        self.rect(x, y, 1, h, c)

    def frame(self, x: int, y: int, w: int, h: int, c) -> None:
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def line(self, x0: int, y0: int, x1: int, y1: int, c, width: int = 1) -> None:
        """Bresenham with a square brush (width px)."""
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = width // 2
        while True:
            self.rect(x0 - r, y0 - r, width, width, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def polygon(self, pts, c) -> None:
        ys = [p[1] for p in pts]
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if y1 == y2:
                    continue
                if min(y1, y2) <= y < max(y1, y2):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i])), int(math.floor(xs[i + 1])) + 1):
                    self.set(x, y, c)

    def disc(self, cx: float, cy: float, r: float, c) -> None:
        for y in range(int(math.floor(cy - r)), int(math.ceil(cy + r)) + 1):
            for x in range(int(math.floor(cx - r)), int(math.ceil(cx + r)) + 1):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r * r:
                    self.set(x, y, c)

    def star(self, cx: float, cy: float, ro: float, ri: float, c) -> None:
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = ro if i % 2 == 0 else ri
            pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        self.polygon(pts, c)

    # -- masks --------------------------------------------------------------
    def fill_mask(self, mask, c, ox: int = 0, oy: int = 0) -> None:
        for y, row in enumerate(mask):
            for x, on in enumerate(row):
                if on:
                    self.set(x + ox, y + oy, c)

    def outline8(self, c=INK_950) -> None:
        """Add a 1 px outer outline around every opaque silhouette."""
        add = set()
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x][3] == 0:
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.w and 0 <= ny < self.h:
                            if self.px[ny][nx][3] == 0:
                                add.add((nx, ny))
        for x, y in add:
            self.set(x, y, c)

    def shade_band(self, y0: int, y1: int, c) -> None:
        for y in range(y0, min(y1, self.h)):
            for x in range(self.w):
                if self.px[y][x][3] != 0:
                    self.px[y][x] = c

    # -- io -----------------------------------------------------------------
    def flat_bytes(self) -> bytes:
        out = bytearray()
        for row in self.px:
            for p in row:
                out += bytes(p)
        return bytes(out)

    def image(self) -> Image.Image:
        return Image.frombytes("RGBA", (self.w, self.h), self.flat_bytes())

    def png_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.image().save(buf, format="PNG", compress_level=9)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Mask helpers
# ---------------------------------------------------------------------------

def rounded_mask(w: int, h: int, r: int):
    if r <= 0:
        return [[True] * w for _ in range(h)]
    mask = [[True] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            cx = min(x, w - 1 - x)
            cy = min(y, h - 1 - y)
            if cx < r and cy < r:
                dx = (r - 1) - cx
                dy = (r - 1) - cy
                if dx * dx + dy * dy > (r - 0.6) ** 2:
                    mask[y][x] = False
    return mask


def erode(mask, n: int):
    cur = [row[:] for row in mask]
    for _ in range(n):
        h = len(cur)
        w = len(cur[0])
        nxt = [[False] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                if not cur[y][x]:
                    continue
                ok = True
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= nx < w and 0 <= ny < h:
                            ok = ok and cur[ny][nx]
                        else:
                            ok = False
                nxt[y][x] = ok
        cur = nxt
    return cur


# ---------------------------------------------------------------------------
# 9-slice panels
# ---------------------------------------------------------------------------

def make_panel(w, h, radius, outer, outer_w, inner, fill,
               bevel_light=None, bevel_dark=None, bevel_px=2) -> Canvas:
    c = Canvas(w, h)
    c.fill_mask(rounded_mask(w, h, radius), outer)

    iw, ih = w - 2 * outer_w, h - 2 * outer_w
    c.fill_mask(rounded_mask(iw, ih, max(1, radius - outer_w)), inner, outer_w, outer_w)

    fw, fh = w - 2 * (outer_w + 1), h - 2 * (outer_w + 1)
    frad = max(1, radius - outer_w - 1)
    fmask = rounded_mask(fw, fh, frad)
    c.fill_mask(fmask, fill, outer_w + 1, outer_w + 1)

    if bevel_light or bevel_dark:
        for ly in range(fh):
            for lx in range(fw):
                if not fmask[ly][lx]:
                    continue
                col = None
                if bevel_light and (ly < bevel_px or lx < bevel_px):
                    col = bevel_light
                elif bevel_dark and (ly >= fh - bevel_px or lx >= fw - bevel_px):
                    col = bevel_dark
                if col is not None:
                    c.set(lx + outer_w + 1, ly + outer_w + 1, col)
    return c


def tex_panel_primary() -> Canvas:
    return make_panel(48, 48, 4, GOLD_400, 2, INK_900, INK_800, INK_700, INK_900)


def tex_panel_inset() -> Canvas:
    return make_panel(48, 48, 4, INK_600, 1, INK_900, INK_900, INK_900, INK_700, 2)


def tex_panel_raised() -> Canvas:
    return make_panel(48, 48, 4, GOLD_400, 2, INK_900, INK_700, INK_600, INK_900)


def tex_titlebar() -> Canvas:
    c = make_panel(48, 20, 4, GOLD_400, 2, INK_900, INK_700, INK_600, INK_900, 2)
    # gold-200 underline sits inside the fill, above the dark bottom bevel
    c.hline(3, 13, 42, GOLD_200)
    return c


def tex_divider() -> Canvas:
    c = Canvas(16, 4)
    c.hline(0, 1, 16, GOLD_400)
    c.hline(0, 2, 16, INK_900)
    return c


# ---------------------------------------------------------------------------
# Slot tiles (16x16) + item textures
# ---------------------------------------------------------------------------

def tex_slot_inset() -> Canvas:
    """Plain slot background tile: ui/bg (square so a grid tiles seamlessly)."""
    c = Canvas(16, 16)
    c.rect(0, 0, 16, 16, INK_800)
    c.frame(0, 0, 16, 16, INK_600)
    c.hline(1, 1, 14, INK_900)
    c.vline(1, 1, 14, INK_900)
    c.hline(1, 14, 14, INK_700)
    c.vline(14, 1, 14, INK_700)
    return c


def tex_slot_border() -> Canvas:
    """Slot frame tile: ui/border (square; gold 1 px + ink 1 px)."""
    c = Canvas(16, 16)
    c.rect(0, 0, 16, 16, GOLD_400)
    c.frame(1, 1, 14, 14, INK_900)
    c.rect(2, 2, 12, 12, INK_800)
    c.hline(2, 2, 12, INK_900)
    c.vline(2, 2, 12, INK_900)
    c.hline(2, 13, 12, INK_700)
    c.vline(13, 2, 12, INK_700)
    return c


def tex_card() -> Canvas:
    """Raised card frame tile: ui/card."""
    return make_panel(16, 16, 2, GOLD_400, 1, INK_900, INK_700, INK_600, INK_900, 1)


def tex_title() -> Canvas:
    """Single-slot titlebar tile: ui/title."""
    c = make_panel(16, 16, 2, GOLD_400, 1, INK_900, INK_700, INK_600, INK_900, 1)
    c.hline(3, 12, 10, GOLD_200)
    return c


# ---------------------------------------------------------------------------
# Buttons (16x16, 3 variants x 3 states; label never baked)
# ---------------------------------------------------------------------------

BUTTON_SPEC = {
    ("green", "normal"): dict(face=LIME_400, light=LIME_200, dark=LIME_600, outline=INK_900),
    ("green", "hover"): dict(face=GREEN_HOVER, light=GREEN_HOVER_LIGHT, dark=GREEN_HOVER_DARK, outline=GOLD_200),
    ("gold", "normal"): dict(face=GOLD_400, light=GOLD_200, dark=GOLD_600, outline=INK_900),
    ("gold", "hover"): dict(face=GOLD_HOVER, light=GOLD_HOVER_LIGHT, dark=GOLD_HOVER_DARK, outline=GOLD_200),
    ("gray", "normal"): dict(face=INK_700, light=INK_600, dark=INK_950, outline=INK_900),
    ("gray", "hover"): dict(face=GRAY_HOVER, light=GRAY_HOVER_LIGHT, dark=GRAY_HOVER_DARK, outline=TEXT_100),
}


def make_button(kind: str, state: str, glyph: str | None = None, icon_color=None) -> Canvas:
    c = Canvas(16, 16)
    if state == "disabled":
        c.rect(0, 0, 16, 16, INK_600)
        c.rect(1, 1, 14, 14, INK_800)
        # flat: no bevel, no icon (binary alpha preserved)
        return c

    spec = BUTTON_SPEC[(kind, state)]
    c.rect(0, 0, 16, 16, spec["outline"])
    c.rect(1, 1, 14, 14, spec["face"])
    c.rect(1, 1, 14, 2, spec["light"])       # top bevel
    c.rect(1, 1, 2, 14, spec["light"])       # left bevel
    c.rect(1, 13, 14, 2, spec["dark"])       # bottom bevel
    c.rect(13, 1, 2, 14, spec["dark"])       # right bevel

    if glyph:
        if icon_color is None:
            icon_color = TEXT_100 if kind == "gray" else INK_900
        draw_glyph_9(c, glyph, 3, 3, icon_color, spec["face"])
    return c


# -- 9x9 button glyphs ------------------------------------------------------

def draw_glyph_9(c: Canvas, name: str, ox: int, oy: int, col, face) -> None:
    def px(x, y):
        c.set(ox + x, oy + y, col)

    def line(x0, y0, x1, y1, width=2):
        tmp = Canvas(9, 9)
        tmp.line(x0, y0, x1, y1, col, width)
        for y in range(9):
            for x in range(9):
                if tmp.px[y][x][3]:
                    px(x, y)

    if name in ("check", "confirm"):
        line(1, 4, 3, 7)
        line(3, 7, 8, 1)
    elif name in ("cross", "close"):
        line(1, 1, 7, 7)
        line(7, 1, 1, 7)
    elif name == "back":
        line(7, 4, 2, 4)
        line(2, 4, 4, 2)
        line(2, 4, 4, 6)
    elif name == "prev":
        line(6, 4, 1, 4)
        line(1, 4, 3, 2)
        line(1, 4, 3, 6)
        c.rect(ox + 7, oy + 1, 2, 7, col)
    elif name == "next":
        line(2, 4, 7, 4)
        line(7, 4, 5, 2)
        line(7, 4, 5, 6)
        c.rect(ox + 0, oy + 1, 2, 7, col)
    elif name in ("coin", "sell"):
        tmp = Canvas(9, 9)
        tmp.disc(4.5, 4.5, 4.0, col)
        tmp.disc(4.5, 4.5, 2.5, face)
        tmp.disc(4.5, 4.5, 1.1, col)
        for y in range(9):
            for x in range(9):
                if tmp.px[y][x][3]:
                    px(x, y)
    else:
        raise ValueError(f"unknown glyph {name}")


# ---------------------------------------------------------------------------
# Tier badges 1..5 (16x16 shield, 2 px primary rim, 1 px ink rim)
# ---------------------------------------------------------------------------

TIER_COLORS = {
    1: (TEXT_500, SILVER_200),
    2: (LIME_400, LIME_200),
    3: (AQUA_400, AQUA_200),
    4: (VIOLET_400, VIOLET_200),
    5: (GOLD_400, GOLD_200),
}

ROMAN = {
    "I": ["#", "#", "#", "#", "#"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
}


def rows_mask(rows):
    m = [[False] * 16 for _ in range(16)]
    for y, (x0, x1) in rows.items():
        for x in range(x0, x1 + 1):
            m[y][x] = True
    return m


def shield_mask():
    """13 px tall shield (y=3..15); y=0..4 is reserved for the tier-5 crown."""
    return rows_mask({
        3: (4, 11),
        4: (3, 12),
        5: (1, 14),
        6: (1, 14),
        7: (1, 14),
        8: (1, 14),
        9: (1, 14),
        10: (1, 14),
        11: (2, 13),
        12: (3, 12),
        13: (4, 11),
        14: (5, 10),
        15: (6, 9),
    })


def shield_inner_mask():
    """Inset silhouette: leaves a 2 px primary rim + 1 px ink ring."""
    return rows_mask({
        5: (6, 9),
        6: (3, 12),
        7: (3, 12),
        8: (3, 12),
        9: (3, 12),
        10: (3, 12),
        11: (4, 11),
        12: (5, 10),
        13: (6, 9),
    })


def shield_fill_mask():
    return rows_mask({
        6: (7, 8),
        7: (4, 11),
        8: (4, 11),
        9: (4, 11),
        10: (4, 11),
        11: (5, 10),
        12: (6, 9),
    })


def tex_tier(n: int) -> Canvas:
    primary, _light = TIER_COLORS[n]
    c = Canvas(16, 16)
    c.fill_mask(shield_mask(), primary)
    c.fill_mask(shield_inner_mask(), INK_900)
    c.fill_mask(shield_fill_mask(), INK_800)

    label = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}[n]
    glyphs = [ROMAN[ch] for ch in label]
    width = sum(len(g[0]) for g in glyphs) + max(0, len(glyphs) - 1)
    x0 = 8 - width // 2
    y0 = 7
    cx = x0
    for g in glyphs:
        for gy, row in enumerate(g):
            for gx, ch in enumerate(row):
                if ch == "#":
                    c.set(cx + gx, y0 + gy, primary)
        cx += len(g[0]) + 1

    if n == 5:
        # 7x4 three-point crown above the shield, dark keyline against the gold rim
        crown = ["#..#..#", "#..#..#", "#######", ".#####."]
        pts = set()
        for y, row in enumerate(crown):
            for x, ch in enumerate(row):
                if ch == "#":
                    pts.add((4 + x, y))
        for x, y in pts:
            c.set(x, y, GOLD_200)
        for x, y in pts:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) not in pts and c.get(nx, ny)[3] == 0:
                        c.set(nx, ny, INK_950)

    return c


# ---------------------------------------------------------------------------
# 32x32 menu icons (NN5: vẽ lại toàn bộ + 10 icon mới)
# ---------------------------------------------------------------------------

def icon_market() -> Canvas:
    c = Canvas(32, 32)
    # awning rail + striped canopy (v2: sọc dày hơn, thêmhighlight gold-200)
    c.rect(3, 2, 26, 1, GOLD_600)
    c.rect(4, 3, 24, 6, GOLD_400)
    for x in range(8, 28, 8):
        c.rect(x, 3, 4, 6, RED_600)
    for x in range(4, 28, 8):
        c.rect(x, 3, 2, 2, GOLD_200)
    for i, x in enumerate(range(4, 28, 4)):
        col = GOLD_400 if i % 2 == 0 else RED_600
        c.rect(x, 9, 4, 1, col)
        c.rect(x + 1, 10, 2, 1, col)
    # produce above the rim
    c.rect(12, 9, 1, 3, GOLD_600)
    c.rect(13, 9, 3, 1, LIME_400)
    c.disc(12.5, 13, 2.4, RED_400)
    c.disc(13, 12, 1.0, RED_300)
    c.disc(19.5, 12.5, 2.4, LIME_400)
    c.disc(23.5, 13, 2.0, GOLD_200)
    # basket (v2: thân có vành sáng + nan dọc đậm)
    c.polygon([(7, 15), (24, 15), (22, 27), (9, 27)], GOLD_400)
    c.rect(6, 14, 20, 2, GOLD_600)
    c.hline(7, 15, 18, GOLD_200)
    for y in range(18, 27, 3):
        c.hline(9, y, 13, GOLD_600)
    for x in range(11, 22, 4):
        c.vline(x, 16, 11, GOLD_600)
    c.outline8()
    return c


def icon_cash() -> Canvas:
    c = Canvas(32, 32)
    # note behind
    c.rect(3, 7, 22, 14, GOLD_600)
    c.frame(3, 7, 22, 14, GOLD_400)
    # front note (v2: thêm khung trong + góc sáng)
    c.rect(6, 10, 22, 14, GOLD_200)
    c.frame(6, 10, 22, 14, GOLD_400)
    c.frame(7, 11, 20, 12, GOLD_600)
    c.rect(7, 11, 2, 2, TEXT_100)
    # money circle
    c.disc(17, 17, 6.0, GOLD_400)
    c.disc(17, 17, 5.0, GOLD_200)
    # dong sign: lowercase d with the ascender stroke (reads at 16 px)
    c.rect(13, 10, 2, 12, INK_950)       # stem
    c.rect(13, 14, 7, 2, INK_950)        # bowl top
    c.rect(13, 20, 7, 2, INK_950)        # bowl bottom
    c.rect(19, 14, 2, 8, INK_950)        # bowl right
    c.rect(11, 12, 10, 2, INK_950)       # stroke across the ascender
    c.outline8()
    return c


def icon_land() -> Canvas:
    c = Canvas(32, 32)
    # isometric grass block (v2: đỉnh cỏ sáng hơn, thêm cột mốc vàng)
    c.polygon([(16, 7), (28, 13), (17, 19), (5, 13)], LIME_400)
    c.polygon([(16, 7), (20, 9), (12, 12), (9, 11)], LIME_200)
    c.polygon([(5, 13), (17, 19), (17, 29), (5, 23)], GOLD_600)
    c.polygon([(28, 13), (17, 19), (17, 29), (28, 23)], INK_700)
    c.line(5, 13, 16, 19, LIME_600, 2)
    c.line(28, 13, 17, 19, LIME_600, 2)
    # marker pole + flag
    c.rect(22, 2, 2, 14, TEXT_500)
    c.polygon([(24, 2), (30, 4), (24, 8)], RED_400)
    c.rect(22, 2, 2, 1, GOLD_200)
    c.outline8()
    return c


def die(c: Canvas, x: int, y: int, pips) -> None:
    c.rect(x, y, 13, 13, TEXT_100)
    c.frame(x, y, 13, 13, INK_950)
    for px, py in pips:
        c.rect(x + px, y + py, 2, 2, INK_950)


def icon_casino() -> Canvas:
    c = Canvas(32, 32)
    die(c, 3, 4, [(3, 3), (9, 3), (3, 9), (9, 9)])
    die(c, 16, 15, [(3, 3), (9, 3), (6, 6), (3, 9), (9, 9)])
    # sparkle (v2: chấm sáng 4 cánh)
    c.rect(26, 3, 1, 5, GOLD_200)
    c.rect(24, 5, 5, 1, GOLD_200)
    c.set(26, 2, GOLD_200)
    c.outline8()
    return c


def icon_mini() -> Canvas:
    c = Canvas(32, 32)
    # body + grips (v2: thêm viền sáng trên thân)
    c.rect(7, 9, 18, 13, VIOLET_400)
    c.disc(9, 21, 5, VIOLET_400)
    c.disc(23, 21, 5, VIOLET_400)
    for y in range(18, 27):
        for x in range(32):
            if c.get(x, y)[3] and c.get(x, y) == VIOLET_400 and y >= 20:
                c.set(x, y, VIOLET_600)
    c.hline(8, 10, 16, VIOLET_200)
    # dpad
    c.rect(9, 14, 7, 2, INK_900)
    c.rect(11, 12, 2, 7, INK_900)
    # face buttons
    c.disc(20.5, 14.5, 2.2, LIME_400)
    c.disc(24.5, 18.5, 2.2, RED_400)
    # center pills
    c.rect(14, 18, 3, 2, TEXT_500)
    c.rect(18, 18, 3, 2, TEXT_500)
    c.outline8()
    return c


def icon_home() -> Canvas:
    c = Canvas(32, 32)
    # chimney behind the roof (tall enough to read above the ridge)
    c.rect(22, 1, 5, 12, RED_600)
    c.rect(21, 0, 7, 2, TEXT_500)
    # roof (v2: chóp sáng gold-200)
    c.polygon([(16, 1), (31, 14), (1, 14)], GOLD_400)
    c.polygon([(16, 1), (22, 6), (16, 8), (10, 6)], GOLD_200)
    c.line(2, 13, 16, 2, GOLD_600, 1)
    c.line(30, 13, 16, 2, GOLD_600, 1)
    # walls
    c.rect(5, 14, 22, 15, GOLD_600)
    c.hline(5, 14, 22, GOLD_400)
    # door + window
    c.rect(13, 19, 7, 10, INK_900)
    c.rect(17, 23, 1, 2, GOLD_200)
    c.rect(7, 17, 5, 5, AQUA_400)
    c.frame(7, 17, 5, 5, INK_950)
    c.vline(9, 17, 5, INK_950)
    c.hline(7, 19, 5, INK_950)
    c.outline8()
    return c


def icon_sethome() -> Canvas:
    """NN5 mới: ngôi nhà + huy hiệu dấu cộng vàng góc phải dưới."""
    c = Canvas(32, 32)
    # house (nhỏ hơn icon home, dịch trái-lên)
    c.polygon([(13, 2), (25, 12), (1, 12)], GOLD_400)
    c.polygon([(13, 2), (18, 6), (13, 9), (8, 6)], GOLD_200)
    c.rect(4, 12, 18, 12, GOLD_600)
    c.hline(4, 12, 18, GOLD_400)
    c.rect(9, 16, 5, 8, INK_900)
    c.rect(5, 14, 4, 4, AQUA_400)
    c.frame(5, 14, 4, 4, INK_950)
    # plus badge (góc phải dưới: đĩa ink + cộng gold-200)
    c.disc(24.5, 24.5, 7.0, INK_950)
    c.disc(24.5, 24.5, 6.0, GOLD_400)
    c.disc(24.5, 24.5, 5.0, INK_900)
    c.rect(19, 23, 11, 3, GOLD_200)
    c.rect(23, 19, 3, 11, GOLD_200)
    c.outline8()
    return c


def icon_spawn() -> Canvas:
    c = Canvas(32, 32)
    # beam
    c.rect(13, 1, 6, 19, AQUA_600)
    c.rect(14, 1, 4, 19, AQUA_400)
    c.rect(15, 1, 2, 19, TEXT_100)
    # platform
    c.rect(3, 26, 26, 3, INK_700)
    c.rect(6, 23, 20, 3, INK_600)
    c.rect(9, 21, 14, 2, AQUA_600)
    c.rect(12, 19, 8, 2, AQUA_400)
    # sparkles
    for sx, sy in ((21, 6), (8, 10), (23, 15)):
        c.rect(sx, sy, 1, 3, GOLD_200)
        c.rect(sx - 1, sy + 1, 3, 1, GOLD_200)
    c.outline8()
    return c


def icon_rp() -> Canvas:
    """NN5 mới: la bàn vàng-khói, kim hai màu bắc nam."""
    c = Canvas(32, 32)
    # vành ngoài
    c.disc(16, 16, 13.5, INK_950)
    c.disc(16, 16, 12.5, GOLD_400)
    c.disc(16, 16, 10.5, INK_900)
    c.disc(16, 16, 9.5, INK_800)
    # vạch hướng (N/E/S/W)
    c.rect(15, 4, 2, 3, TEXT_500)
    c.rect(15, 25, 2, 3, TEXT_500)
    c.rect(4, 15, 3, 2, TEXT_500)
    c.rect(25, 15, 3, 2, TEXT_500)
    # kim: nửa bắc gold-200, nửa nam text-500
    c.polygon([(16, 6), (19, 16), (16, 16)], GOLD_200)
    c.polygon([(16, 6), (13, 16), (16, 16)], TEXT_100)
    c.polygon([(16, 26), (19, 16), (16, 16)], TEXT_500)
    c.polygon([(16, 26), (13, 16), (16, 16)], TEXT_700)
    # chốt
    c.disc(16, 16, 2.0, GOLD_400)
    c.disc(16, 16, 1.0, GOLD_200)
    c.outline8()
    return c


def icon_book() -> Canvas:
    """NN5 mới: quyển sổ mở, trang trắng kèm dòng chữ, bìa nâu-vàng."""
    c = Canvas(32, 32)
    # bìa dưới
    c.polygon([(3, 8), (16, 5), (29, 8), (29, 26), (16, 29), (3, 26)], GOLD_600)
    # hai trang mở
    c.polygon([(5, 9), (16, 6), (16, 26), (5, 23)], TEXT_100)
    c.polygon([(27, 9), (16, 6), (16, 26), (27, 23)], SILVER_200)
    # sống giữa
    c.line(16, 6, 16, 26, TEXT_500, 1)
    # dòng chữ khắc ink
    for y in (11, 14, 17, 20):
        c.hline(7, y, 6, INK_700)
        c.hline(19, y - 1, 6, INK_700)
    # thẻ bookmark (đỏ, cài trên trang phải)
    c.rect(21, 3, 4, 6, RED_400)
    c.rect(21, 3, 4, 1, RED_300)
    c.outline8()
    return c


def icon_sell() -> Canvas:
    """NN5 mới: thẻ giá vàng kèm mũi tên ra ngoài (bán hàng)."""
    c = Canvas(32, 32)
    # thẻ giá quay trái
    c.polygon([(24, 5), (10, 5), (3, 16), (10, 27), (24, 27)], GOLD_400)
    c.polygon([(24, 5), (10, 5), (8, 8), (22, 8)], GOLD_200)
    c.rect(22, 5, 2, 22, GOLD_600)
    # lỗ dây
    c.disc(9, 16, 2.6, INK_950)
    c.disc(9, 16, 1.4, INK_800)
    # dòng giá khắc
    c.rect(14, 14, 7, 2, INK_900)
    c.rect(14, 18, 7, 2, INK_900)
    # mũi tên bay ra (lime, góc phải trên, tách khỏi thẻ)
    c.rect(24, 9, 5, 3, LIME_400)
    c.polygon([(29, 7), (31, 10.5), (29, 14)], LIME_400)
    c.polygon([(24, 9), (26, 10.5), (24, 12)], LIME_200)
    c.outline8()
    return c


def icon_auction() -> Canvas:
    """NN5 mới: búa đấu giá gỗ vàng, cán ink, đế tạ."""
    c = Canvas(32, 32)
    # đầu búa (khối vuông xoay 45°, hai Band gold)
    c.line(20, 4, 27, 11, GOLD_600, 8)
    c.line(20, 4, 27, 11, GOLD_400, 6)
    c.line(19, 3, 28, 12, GOLD_200, 1)
    # cán búa
    c.line(17, 13, 6, 24, GOLD_600, 4)
    c.line(17, 13, 6, 24, GOLD_400, 2)
    c.disc(5, 25, 2.5, GOLD_200)
    # đế tạ 2 bậc
    c.rect(18, 24, 12, 3, INK_700)
    c.rect(16, 27, 16, 3, INK_900)
    c.hline(18, 24, 12, TEXT_500)
    c.outline8()
    return c


def icon_friendly() -> Canvas:
    """NN5 mới: hai trái tim riêng biệt (tim đỏ nhỏ trên phải, tim vàng dưới trái)."""
    c = Canvas(32, 32)
    # tim nhỏ đỏ — trên phải
    c.disc(17.5, 7.5, 3.8, RED_400)
    c.disc(23.5, 7.5, 3.8, RED_400)
    c.polygon([(14, 9), (27, 9), (20.5, 18)], RED_400)
    c.polygon([(16, 7), (20, 7), (18, 10)], RED_300)
    # tim lớn vàng — dưới trái
    c.disc(9.0, 16.0, 5.6, GOLD_400)
    c.disc(16.0, 16.0, 5.6, GOLD_400)
    c.polygon([(4, 19), (21, 19), (12.5, 30)], GOLD_400)
    c.polygon([(6, 14), (11, 14), (8.5, 18)], GOLD_200)
    c.outline8()
    return c


def icon_shop() -> Canvas:
    """NN5 mới: cửa hàng — mái sạp sọc vàng/đỏ + thân, cửa và cửa sổ."""
    c = Canvas(32, 32)
    # mái sạp
    c.rect(2, 3, 28, 2, GOLD_600)
    for i, x in enumerate(range(2, 30, 4)):
        c.rect(x, 5, 4, 5, GOLD_400 if i % 2 == 0 else RED_600)
        c.rect(x, 10, 4, 2, GOLD_400 if i % 2 == 0 else RED_600)
        c.rect(x + 1, 12, 2, 1, GOLD_400 if i % 2 == 0 else RED_600)
    # thân nhà
    c.rect(4, 13, 24, 16, INK_800)
    c.frame(4, 13, 24, 16, INK_900)
    # cửa
    c.rect(13, 19, 7, 10, INK_950)
    c.rect(18, 24, 1, 2, GOLD_200)
    # cửa sổ
    c.rect(6, 17, 5, 5, AQUA_400)
    c.frame(6, 17, 5, 5, INK_950)
    # biển hiệu
    c.rect(21, 17, 6, 5, GOLD_400)
    c.rect(22, 19, 4, 1, GOLD_200)
    c.outline8()
    return c


def icon_chat_tag() -> Canvas:
    """NN5 mới: bong bóng chat tối viền vàng kèm sao gold, đuôi rõ."""
    c = Canvas(32, 32)
    # bóng chat (bo tròn hai đầu)
    c.disc(9, 10, 6.0, INK_900)
    c.disc(23, 10, 6.0, INK_900)
    c.rect(4, 4, 24, 13, INK_900)
    c.frame(4, 4, 24, 13, GOLD_400)
    c.frame(5, 5, 22, 11, GOLD_600)
    # đuôi bong bóng (tam giác đậm dưới trái)
    c.polygon([(7, 16), (16, 16), (7, 27)], INK_900)
    c.line(7, 16, 7, 26, GOLD_400, 1)
    c.line(7, 26, 12, 18, GOLD_600, 1)
    # sao tag giữa bóng
    c.star(16, 10, 5.5, 2.3, GOLD_200)
    c.star(16, 10, 2.2, 1.0, GOLD_400)
    c.outline8()
    return c


def icon_worldtime() -> Canvas:
    """NN5 mới: mặt trời đồng hồ — quỹ đạo vàng, kim giờ tối."""
    c = Canvas(32, 32)
    # tia nắng 8 hướng
    for dx, dy in ((0, -12), (0, 12), (-12, 0), (12, 0),
                   (-9, -9), (9, -9), (-9, 9), (9, 9)):
        cx, cy = 16 + dx, 16 + dy
        c.rect(cx - 1, cy - 1, 3, 3, GOLD_200)
    # đĩa mặt trời / mặt đồng hồ
    c.disc(16, 16, 10.0, GOLD_600)
    c.disc(16, 16, 9.0, GOLD_400)
    c.disc(16, 16, 7.0, GOLD_200)
    c.disc(16, 16, 6.0, GOLD_400)
    # kim giờ + phút
    c.rect(15, 10, 2, 7, INK_950)
    c.rect(15, 15, 6, 2, INK_950)
    c.disc(16, 16, 1.5, INK_950)
    c.outline8()
    return c


def icon_sword() -> Canvas:
    """NN5 mới: kiếm bạc lưỡi sáng, chắn vàng, chuôi quấn."""
    c = Canvas(32, 32)
    # lưỡi kiếm (2 tông bạc, sống tối)
    c.line(25, 4, 12, 17, SILVER_200, 5)
    c.line(26, 5, 14, 17, TEXT_100, 3)
    c.line(25, 4, 12, 17, TEXT_500, 1)
    tip = [(27, 2), (29, 4), (26, 6)]
    c.polygon(tip, SILVER_200)
    # chắn ngang vàng
    c.line(8, 14, 16, 22, GOLD_600, 6)
    c.line(8, 14, 16, 22, GOLD_400, 4)
    c.line(9, 15, 15, 21, GOLD_200, 1)
    # chuôi quấn
    c.line(7, 23, 3, 27, GOLD_600, 4)
    for i, (x, y) in enumerate(((7, 23), (5, 25), (3, 27))):
        c.rect(x - 1, y - 1, 3, 1, INK_900)
    # chuôi nút
    c.disc(2.5, 28.5, 2.2, GOLD_400)
    c.outline8()
    return c


def icon_bounty() -> Canvas:
    c = Canvas(32, 32)
    # bag body
    c.disc(16, 21, 9, GOLD_600)
    c.rect(7, 21, 18, 6, GOLD_600)
    c.disc(13, 19, 5, GOLD_400)
    # neck + tie
    c.polygon([(11, 8), (21, 8), (19, 14), (13, 14)], GOLD_400)
    c.rect(10, 7, 12, 2, GOLD_600)
    c.rect(11, 12, 10, 2, INK_900)
    # star (v2: thêm chấm sáng giữa sao)
    c.star(16, 20, 6.5, 2.8, GOLD_200)
    c.star(16, 20, 2.4, 1.0, GOLD_400)
    c.outline8()
    return c


def icon_mail() -> Canvas:
    c = Canvas(32, 32)
    c.rect(3, 8, 26, 17, TEXT_100)
    c.frame(3, 8, 26, 17, INK_900)
    # flap
    c.line(5, 9, 16, 18, GOLD_400, 2)
    c.line(27, 9, 16, 18, GOLD_400, 2)
    c.line(4, 24, 12, 18, GOLD_600, 1)
    c.line(27, 24, 20, 18, GOLD_600, 1)
    # wax seal
    c.disc(16, 20, 3.2, RED_400)
    c.disc(16, 20, 1.2, RED_300)
    # stamp
    c.rect(23, 10, 5, 5, GOLD_400)
    c.rect(24, 11, 3, 3, GOLD_200)
    c.outline8()
    return c


def icon_ally() -> Canvas:
    c = Canvas(32, 32)
    # sleeves angled toward the clasp
    c.polygon([(0, 17), (9, 17), (11, 24), (0, 24)], LIME_400)
    c.polygon([(31, 17), (22, 17), (20, 24), (31, 24)], AQUA_400)
    c.rect(8, 17, 3, 7, LIME_600)
    c.rect(21, 17, 3, 7, AQUA_600)
    # left hand base
    c.rect(8, 12, 10, 11, TEXT_100)
    # right palm
    c.rect(16, 13, 8, 11, GOLD_200)
    # right-hand fingers wrap left over the left hand
    for yy in (15, 18, 21):
        c.rect(11, yy, 6, 2, GOLD_200)
        c.rect(11, yy + 2, 6, 1, GOLD_600)
    # thumbs
    c.rect(9, 9, 3, 4, TEXT_100)
    c.rect(21, 10, 3, 4, GOLD_200)
    # left-hand finger grooves
    for yy in (14, 17, 20):
        c.hline(9, yy, 3, INK_700)
    c.outline8()
    return c


LEADER_DIGITS = {
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["##.", "..#", ".#.", "#..", "###"],
    "3": ["##.", "..#", ".#.", "..#", "##."],
}


def icon_leaderboard() -> Canvas:
    c = Canvas(32, 32)
    # podium bars: 2nd, 1st, 3rd
    c.rect(3, 17, 9, 11, TEXT_500)
    c.rect(3, 17, 9, 2, TEXT_100)
    c.rect(12, 10, 9, 18, GOLD_400)
    c.rect(12, 10, 9, 2, GOLD_200)
    c.rect(21, 21, 9, 7, GOLD_600)
    c.rect(21, 21, 9, 2, GOLD_400)
    c.rect(2, 28, 28, 2, INK_700)
    # place numbers
    for x, y, n in ((6, 21, "2"), (15, 14, "1"), (24, 23, "3")):
        for gy, row in enumerate(LEADER_DIGITS[n]):
            for gx, ch in enumerate(row):
                if ch == "#":
                    c.set(x + gx, y + gy, INK_950)
    # crown above first place
    crown = ["#..#..#", "#..#..#", "#######", ".#####."]
    pts = {(12 + x, 3 + y) for y, row in enumerate(crown) for x, ch in enumerate(row) if ch == "#"}
    for x, y in pts:
        c.set(x, y, GOLD_200)
    for x, y in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (nx, ny) not in pts and c.get(nx, ny)[3] == 0:
                    c.set(nx, ny, INK_950)
    c.outline8()
    return c


# ---------------------------------------------------------------------------
# Asset spec
# ---------------------------------------------------------------------------

# name -> (draw fn, width, height)
GUI_TEXTURES = {
    "gui/panel_primary": (tex_panel_primary, 48, 48),
    "gui/panel_inset": (tex_panel_inset, 48, 48),
    "gui/panel_raised": (tex_panel_raised, 48, 48),
    "gui/titlebar": (tex_titlebar, 48, 20),
    "gui/divider": (tex_divider, 16, 4),
    "gui/slot_inset": (tex_slot_inset, 16, 16),
    "gui/slot_border": (tex_slot_border, 16, 16),
}

# Nine-slice parameters of the GUI panels (design 1.3). Kept in the manifest so a
# pack/GUI agent can emit .mcmeta later without re-deriving them.
SLICES = {
    "textures/gui/panel_primary.png": {"slice": 12, "corner": 4},
    "textures/gui/panel_inset.png": {"slice": 12, "corner": 4},
    "textures/gui/panel_raised.png": {"slice": 12, "corner": 4},
    "textures/gui/titlebar.png": {"slice_x": 12, "slice_y": 8, "corner": 4},
    "textures/gui/divider.png": {"tile": [16, 4]},
}

# name -> (draw fn, width, height); also gets a model + item definition
ITEM_TEXTURES = {
    "bg": (tex_slot_inset, 16, 16),
    "border": (tex_slot_border, 16, 16),
    "title": (tex_title, 16, 16),
    "card": (tex_card, 16, 16),
    "btn_green": (lambda: make_button("green", "normal"), 16, 16),
    "btn_green_hover": (lambda: make_button("green", "hover"), 16, 16),
    "btn_green_disabled": (lambda: make_button("green", "disabled"), 16, 16),
    "btn_gold": (lambda: make_button("gold", "normal"), 16, 16),
    "btn_gold_hover": (lambda: make_button("gold", "hover"), 16, 16),
    "btn_gold_disabled": (lambda: make_button("gold", "disabled"), 16, 16),
    "btn_gray": (lambda: make_button("gray", "normal"), 16, 16),
    "btn_gray_hover": (lambda: make_button("gray", "hover"), 16, 16),
    "btn_gray_disabled": (lambda: make_button("gray", "disabled"), 16, 16),
    "btn_gray_back": (lambda: make_button("gray", "normal", "back"), 16, 16),
    "btn_gray_close": (lambda: make_button("gray", "normal", "cross"), 16, 16),
    "btn_gray_prev": (lambda: make_button("gray", "normal", "prev"), 16, 16),
    "btn_gray_next": (lambda: make_button("gray", "normal", "next"), 16, 16),
    "btn_green_confirm": (lambda: make_button("green", "normal", "check"), 16, 16),
    "btn_gold_sell": (lambda: make_button("gold", "normal", "sell"), 16, 16),
    "tier_1": (lambda: tex_tier(1), 16, 16),
    "tier_2": (lambda: tex_tier(2), 16, 16),
    "tier_3": (lambda: tex_tier(3), 16, 16),
    "tier_4": (lambda: tex_tier(4), 16, 16),
    "tier_5": (lambda: tex_tier(5), 16, 16),
    "icon/market": (icon_market, 32, 32),
    "icon/cash": (icon_cash, 32, 32),
    "icon/land": (icon_land, 32, 32),
    "icon/casino": (icon_casino, 32, 32),
    "icon/mini": (icon_mini, 32, 32),
    "icon/home": (icon_home, 32, 32),
    "icon/spawn": (icon_spawn, 32, 32),
    "icon/bounty": (icon_bounty, 32, 32),
    "icon/mail": (icon_mail, 32, 32),
    "icon/ally": (icon_ally, 32, 32),
    "icon/leaderboard": (icon_leaderboard, 32, 32),
    # NN5 (A2): 10 icon item_model còn thiếu cho menu/shop/scoreboard
    "icon/sethome": (icon_sethome, 32, 32),
    "icon/rp": (icon_rp, 32, 32),
    "icon/book": (icon_book, 32, 32),
    "icon/sell": (icon_sell, 32, 32),
    "icon/auction": (icon_auction, 32, 32),
    "icon/friendly": (icon_friendly, 32, 32),
    "icon/shop": (icon_shop, 32, 32),
    "icon/chat-tag": (icon_chat_tag, 32, 32),
    "icon/worldtime": (icon_worldtime, 32, 32),
    "icon/sword": (icon_sword, 32, 32),
}


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def texture_id(rel: str) -> str:
    assert rel.startswith("textures/") and rel.endswith(".png")
    return "nomnom:" + rel[len("textures/"):-len(".png")]


def model_id(name: str) -> str:
    """Model ID (resolves to models/<path>.json). The item definition ID used by
    ItemMeta#setItemModel is `nomnom:ui/<name>` and lives at items/ui/<name>.json."""
    return "nomnom:item/ui/" + name


def model_json(texture: str) -> bytes:
    obj = {
        "parent": "minecraft:item/generated",
        "textures": {"layer0": texture},
    }
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def item_json(name: str) -> bytes:
    obj = {"model": {"type": "minecraft:model", "model": model_id(name)}}
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


# Contract with the menu agent: these model IDs must always exist.
REQUIRED_MODELS = {
    "bg", "border", "title", "card",
    "btn_green", "btn_gold", "btn_gray",
    "btn_green_hover", "btn_green_disabled",
    "btn_gold_hover", "btn_gold_disabled",
    "btn_gray_hover", "btn_gray_disabled",
    "btn_gray_back", "btn_gray_close", "btn_gray_prev", "btn_gray_next",
    "btn_green_confirm", "btn_gold_sell",
    "tier_1", "tier_2", "tier_3", "tier_4", "tier_5",
    "icon/market", "icon/cash", "icon/land", "icon/casino", "icon/mini",
    "icon/home", "icon/spawn", "icon/bounty", "icon/mail", "icon/ally",
    "icon/leaderboard",
    # NN5 (A2/A5): đủ icon item_model cho mọi entry menu + shop/scoreboard
    "icon/sethome", "icon/rp", "icon/book", "icon/sell", "icon/auction",
    "icon/friendly", "icon/shop", "icon/chat-tag", "icon/worldtime",
    "icon/sword",
}


def build_records():
    """Return list of dicts: rel, kind, bytes, w, h (w/h only for png)."""
    missing = REQUIRED_MODELS - set(ITEM_TEXTURES)
    if missing:
        raise SystemExit(f"required item models missing from spec: {sorted(missing)}")
    recs = []

    for name, (fn, w, h) in GUI_TEXTURES.items():
        c = fn()
        assert (c.w, c.h) == (w, h), f"{name}: canvas {c.w}x{c.h} != {w}x{h}"
        recs.append(dict(rel=f"textures/{name}.png", kind="texture", bytes=c.png_bytes(), w=w, h=h))

    for name, (fn, w, h) in ITEM_TEXTURES.items():
        c = fn()
        assert (c.w, c.h) == (w, h), f"{name}: canvas {c.w}x{c.h} != {w}x{h}"
        png = c.png_bytes()
        rel = f"textures/item/ui/{name}.png"
        recs.append(dict(rel=rel, kind="texture", bytes=png, w=w, h=h))
        # Mirror under textures/gui/items/ so the task's textures/gui/** tree is complete.
        recs.append(dict(rel=f"textures/gui/items/{name}.png", kind="texture_mirror",
                         bytes=png, w=w, h=h))

        tex_id = texture_id(rel)
        recs.append(dict(rel=f"models/item/ui/{name}.json", kind="model",
                         bytes=model_json(tex_id), w=None, h=None))
        recs.append(dict(rel=f"items/ui/{name}.json", kind="item",
                         bytes=item_json(name), w=None, h=None))

    return recs


def write_records(recs) -> None:
    for r in recs:
        p = ASSETS / r["rel"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r["bytes"])


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_manifest(recs) -> None:
    tex = {r["rel"]: {"w": r["w"], "h": r["h"], "sha256": sha(r["bytes"])}
           for r in recs if r["kind"] in ("texture", "texture_mirror")}
    models = {r["rel"]: sha(r["bytes"]) for r in recs if r["kind"] == "model"}
    items = {r["rel"]: sha(r["bytes"]) for r in recs if r["kind"] == "item"}
    obj = {
        "schema": "nomnom-ui-textures/1",
        "generator": "work/rp_build/build_gui.py",
        "design": "work/nn4-design.md 1.3-1.6, 4.6",
        "counts": {
            "textures": len([r for r in recs if r["kind"] == "texture"]),
            "texture_mirrors": len([r for r in recs if r["kind"] == "texture_mirror"]),
            "models": len(models),
            "items": len(items),
        },
        "slices": SLICES,
        "textures": dict(sorted(tex.items())),
        "models": dict(sorted(models.items())),
        "items": dict(sorted(items.items())),
    }
    MANIFEST.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def check(recs) -> list[str]:
    errors = []
    for r in recs:
        p = ASSETS / r["rel"]
        if not p.exists():
            errors.append(f"MISSING {r['rel']}")
            continue
        disk = p.read_bytes()
        if disk != r["bytes"]:
            errors.append(f"STALE   {r['rel']} (on disk != regenerated; run build)")
            continue
        if r["kind"] in ("texture", "texture_mirror"):
            try:
                img = Image.open(io.BytesIO(disk))
                img.load()
            except Exception as e:  # pragma: no cover
                errors.append(f"BADPNG  {r['rel']}: {e}")
                continue
            if img.mode != "RGBA":
                errors.append(f"MODE    {r['rel']}: {img.mode} != RGBA")
            if img.size != (r["w"], r["h"]):
                errors.append(f"SIZE    {r['rel']}: {img.size} != {(r['w'], r['h'])}")
            # Only item textures must be a multiple of 16; the 9-slice titlebar
            # (48x20) and divider (16x4) have their own sizes in design 1.3.
            item_tex = (r["rel"].startswith("textures/item/ui/")
                        or r["rel"].startswith("textures/gui/items/"))
            if item_tex and (r["w"] % 16 or r["h"] % 16):
                errors.append(f"MULT16  {r['rel']}: {r['w']}x{r['h']} not a multiple of 16")
            raw = img.tobytes()
            alpha = set(raw[3::4])
            opaque = sum(1 for a in raw[3::4] if a == 255)
            if not alpha <= {0, 255}:
                errors.append(f"ALPHA   {r['rel']}: partial alpha {sorted(alpha)}")
            if opaque == 0:
                errors.append(f"EMPTY   {r['rel']}: no opaque pixels")
        else:
            try:
                json.loads(disk.decode("utf-8"))
            except Exception as e:  # pragma: no cover
                errors.append(f"JSON    {r['rel']}: {e}")
    return errors


def resolve_refs(recs) -> list[str]:
    """Every model layer0 and item model target must exist in this build."""
    errors = []
    textures = {texture_id(r["rel"]) for r in recs if r["kind"] == "texture"}
    models = {model_id(r["rel"].split("models/item/ui/")[1][:-5])
              for r in recs if r["kind"] == "model"}
    for r in recs:
        if r["kind"] == "model":
            obj = json.loads(r["bytes"])
            tex = obj["textures"]["layer0"]
            if tex not in textures:
                errors.append(f"REF     {r['rel']}: texture {tex} missing")
        elif r["kind"] == "item":
            obj = json.loads(r["bytes"])
            mid = obj["model"]["model"]
            if mid not in models:
                errors.append(f"REF     {r['rel']}: model {mid} missing")
    return errors


# ---------------------------------------------------------------------------
# QA preview sheets (not pack assets)
# ---------------------------------------------------------------------------

def upscale(img: Image.Image, k: int) -> Image.Image:
    return img.resize((img.width * k, img.height * k), Image.Resampling.NEAREST)


def as_image(t) -> Image.Image:
    return t.image() if isinstance(t, Canvas) else t


def compose(bg, tiles, cols, k, pad=8):
    """tiles: list of (Canvas|Image, label). Returns sheet."""
    tw = max(as_image(t).width for t, _ in tiles) * k
    th = max(as_image(t).height for t, _ in tiles) * k
    rows = math.ceil(len(tiles) / cols)
    W = cols * tw + (cols + 1) * pad
    H = rows * th + (rows + 1) * pad
    sheet = Image.new("RGBA", (W, H), bg)
    for i, (img, _) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + pad)
        sheet.alpha_composite(upscale(as_image(img), k), (x, y))
    return sheet


def slice9(img: Image.Image, W: int, H: int, bx: int, by: int | None = None) -> Image.Image:
    """QA-only: stretch a 9-slice source to WxH (corners copied, edges/centre stretched)."""
    by = bx if by is None else by
    w, h = img.size
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for sx, sy, dx, dy in (
        (0, 0, 0, 0), (w - bx, 0, W - bx, 0),
        (0, h - by, 0, H - by), (w - bx, h - by, W - bx, H - by),
    ):
        out.paste(img.crop((sx, sy, sx + bx, sy + by)), (dx, dy))
    out.paste(img.crop((bx, 0, w - bx, by)).resize((W - 2 * bx, by), Image.Resampling.NEAREST), (bx, 0))
    out.paste(img.crop((bx, h - by, w - bx, h)).resize((W - 2 * bx, by), Image.Resampling.NEAREST), (bx, H - by))
    out.paste(img.crop((0, by, bx, h - by)).resize((bx, H - 2 * by), Image.Resampling.NEAREST), (0, by))
    out.paste(img.crop((w - bx, by, w, h - by)).resize((bx, H - 2 * by), Image.Resampling.NEAREST), (W - bx, by))
    out.paste(img.crop((bx, by, w - bx, h - by)).resize((W - 2 * bx, H - 2 * by), Image.Resampling.NEAREST), (bx, by))
    return out


def write_previews():
    bg = (0x0B, 0x0F, 0x14, 255)
    panels = [tex_panel_primary(), tex_panel_inset(), tex_panel_raised(),
              tex_titlebar(), tex_divider()]
    sheet = compose(bg, [(p, "") for p in panels], 3, 4, 12)
    sheet.save(HERE / "preview_panels.png")

    buttons = [make_button(v, s) for v in ("green", "gold", "gray")
               for s in ("normal", "hover", "disabled")]
    buttons += [make_button("gray", "normal", g) for g in ("back", "close", "prev", "next")]
    buttons += [make_button("green", "normal", "check"), make_button("gold", "normal", "sell")]
    sheet = compose(bg, [(b, "") for b in buttons], 5, 6, 10)
    sheet.save(HERE / "preview_buttons.png")

    tiers = [tex_tier(i) for i in range(1, 6)]
    tiers += [tex_slot_inset(), tex_slot_border(), tex_card(), tex_title()]
    sheet = compose(bg, [(t, "") for t in tiers], 5, 7, 10)
    sheet.save(HERE / "preview_tiles.png")

    icons = [fn() for fn, _, _ in ITEM_TEXTURES.values() if fn.__name__.startswith("icon_")]
    sheet = compose(bg, [(i, "") for i in icons], 4, 5, 12)
    sheet.save(HERE / "preview_icons.png")

    # Chest mock: 9x6 at 4x, S54 + S27 land strip.
    def mock(rows):
        tiles = []
        for y in range(rows):
            for x in range(9):
                tiles.append(tex_slot_inset())
        return tiles

    def place(tiles, idx, img):
        # An item texture renders inside a 16x16 slot; 32x32 icons are downscaled
        # by the client, so the mock must do the same to be honest.
        im = as_image(img)
        if (im.width, im.height) != (16, 16):
            im = im.resize((16, 16), Image.Resampling.LANCZOS)
        tiles[idx] = im

    m = mock(6)
    # border ring on rows 0 and 5, bg elsewhere
    for x in range(9):
        m[x] = tex_slot_border()
        m[45 + x] = tex_slot_border()
    for x in range(9):
        m[9 + x] = tex_slot_border() if x in (0, 8) else tex_slot_inset()
        m[18 + x] = tex_slot_border() if x in (0, 8) else tex_slot_inset()
        m[27 + x] = tex_slot_border() if x in (0, 8) else tex_slot_inset()
        m[36 + x] = tex_slot_border() if x in (0, 8) else tex_slot_inset()
    place(m, 10, icon_market())
    place(m, 12, icon_cash())
    place(m, 14, icon_land())
    place(m, 16, icon_casino())
    place(m, 20, icon_mini())
    place(m, 22, icon_home())
    place(m, 24, icon_spawn())
    place(m, 28, icon_bounty())
    place(m, 30, icon_mail())
    place(m, 32, icon_ally())
    place(m, 34, icon_leaderboard())
    # NN5: entry menu mới — đủ icon chuẩn như A5 yêu cầu
    place(m, 11, icon_sethome())
    place(m, 13, icon_rp())
    place(m, 15, icon_book())
    place(m, 19, icon_sell())
    place(m, 21, icon_auction())
    place(m, 23, icon_friendly())
    place(m, 25, icon_shop())
    place(m, 29, icon_chat_tag())
    place(m, 31, icon_worldtime())
    place(m, 33, icon_sword())
    place(m, 45, make_button("gray", "normal", "back"))
    place(m, 46, tex_card())
    place(m, 48, make_button("gray", "normal", "prev"))
    place(m, 49, tex_card())
    place(m, 50, make_button("gray", "normal", "next"))
    place(m, 52, make_button("gray", "normal"))
    place(m, 53, make_button("gray", "normal", "close"))
    place(m, 43, make_button("green", "normal", "check"))
    place(m, 44, make_button("gold", "normal", "sell"))

    W, H = 9 * 16 * 4 + 16, 6 * 16 * 4 + 16
    sheet = Image.new("RGBA", (W, H), bg)
    for i, t in enumerate(m):
        r, c = divmod(i, 9)
        sheet.alpha_composite(upscale(as_image(t), 4), (8 + c * 64, 8 + r * 64))
    sheet.save(HERE / "preview_gui_mock.png")

    # zoomed tier badges (14x, nearest)
    sheet = compose(bg, [(tex_tier(i), "") for i in range(1, 6)], 5, 14, 8)
    sheet.save(HERE / "preview_tier_zoom.png")

    # 9-slice stretch test
    tiles = [
        slice9(tex_panel_primary().image(), 180, 110, 12),
        slice9(tex_panel_raised().image(), 150, 90, 12),
        slice9(tex_panel_inset().image(), 140, 70, 12),
        slice9(tex_titlebar().image(), 220, 40, 12, 8),
    ]
    div = Image.new("RGBA", (220, 4), (0, 0, 0, 0))
    d = tex_divider().image()
    for x in range(0, 220, 16):
        div.alpha_composite(d, (x, 0))
    tiles.append(div)
    W = max(t.width for t in tiles) + 20
    H = sum(t.height for t in tiles) + 10 * (len(tiles) + 1)
    sheet = Image.new("RGBA", (W, H), bg)
    y = 10
    for t in tiles:
        sheet.alpha_composite(t, (10, y))
        y += t.height + 10
    upscale(sheet, 2).save(HERE / "preview_slice9.png")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify on-disk files, write nothing")
    ap.add_argument("--preview", action="store_true", help="write QA preview sheets")
    args = ap.parse_args(argv)

    recs = build_records()
    refs = resolve_refs(recs)
    if refs:
        for e in refs:
            print("FAIL", e)
        return 1

    if args.check:
        errs = check(recs)
        if errs:
            for e in errs:
                print("FAIL", e)
            return 1
        print(f"PASS check: {len(recs)} files match regenerated bytes, "
              f"{sum(1 for r in recs if r['kind']=='texture')} textures, "
              f"{sum(1 for r in recs if r['kind']=='model')} models, "
              f"{sum(1 for r in recs if r['kind']=='item')} item definitions")
        return 0

    write_records(recs)
    write_manifest(recs)
    if args.preview:
        write_previews()

    ntex = sum(1 for r in recs if r["kind"] == "texture")
    nmir = sum(1 for r in recs if r["kind"] == "texture_mirror")
    nmod = sum(1 for r in recs if r["kind"] == "model")
    nitm = sum(1 for r in recs if r["kind"] == "item")
    print(f"OK wrote {ntex} textures (+{nmir} mirrors), {nmod} models, {nitm} item definitions")
    print(f"manifest: {MANIFEST.relative_to(WORK)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
