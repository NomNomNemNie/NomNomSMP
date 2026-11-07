#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NN6 A2 probe: pick the em for the HUD digit re-render (cell 16x16, height 9, ascent 9).

Client metrics (BitmapProvider#load):
    pixelScale = height / cellHeight = 9 / 16
    advance    = round_half_up(actualGlyphWidth * pixelScale) + 1   (actualGlyphWidth = ink_w)
Uniform advance 9 requires every glyph's rightmost ink column at atlas x=14 (ink_w=15):
    round_half_up(15 * 9/16) + 1 = 8 + 1 = 9
    (ink_w 14 also gives 9: round_half_up(7.875) = 8; ink_w 13 gives 8 — so the box is
     pinned at x=14, never 13.)

Target: ink height 14..16 rows (screen 7.9..9.0 px tall on the 9 px line) with NO
horizontal squash for digits (ink_w <= 15 before pinning), max natural width decides em.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TTF = Path(__file__).resolve().parent / "fonts" / "BeVietnamPro-Regular.ttf"
ALPHA_LOW, ALPHA_HIGH = 36, 210


def alpha_curve(v: int) -> int:
    if v <= ALPHA_LOW:
        return 0
    if v >= ALPHA_HIGH:
        return 255
    return int(ALPHA_LOW + (v - ALPHA_LOW) * (255 - ALPHA_LOW) / (ALPHA_HIGH - ALPHA_LOW))


def render(ch: str, em: int) -> Image.Image:
    img = Image.new("L", (32, 40), 0)  # oversized scratch, baseline at y=32
    ImageDraw.Draw(img).text((4, 32), ch, font=ImageFont.truetype(str(TTF), em),
                             fill=255, anchor="ls")
    return img.point(alpha_curve)


def ink(img: Image.Image):
    bb = img.getbbox()
    return (bb[2] - bb[0], bb[3] - bb[1]) if bb else (0, 0)


CHARS = list("0123456789") + [".", ",", "k", "M", "T", "ms"]

for em in (16, 17, 18, 19, 20, 21, 22, 23, 24):
    rows = []
    maxw, maxh = 0, 0
    for ch in CHARS:
        w, h = ink(render(ch, em))
        maxw, maxh = max(maxw, w), max(maxh, h)
        rows.append(f"{ch}:{w}x{h}")
    print(f"em={em:2d} max_w={maxw:2d} max_h={maxh:2d}  screen_h~{maxh * 9 / 16:.1f}px  " + " ".join(rows))
