#!/usr/bin/env python3
"""Sinh placeholder cho các asset UI còn thiếu (font agent / texture agent chưa giao).

Mọi file sinh ra bởi script này được liệt kê trong PLACEHOLDERS.txt ở root pack.
Build script sẽ ưu tiên file thật trong work/rp_src/; placeholder chỉ lấp chỗ trống.
Chạy idempotent: cùng input -> cùng byte PNG/JSON.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- palette (work/nn4-design.md §1.1)
INK_950 = "#070A0E"
INK_900 = "#0B0F14"
INK_800 = "#121821"
INK_700 = "#1B2430"
INK_600 = "#243040"
GOLD_600 = "#B17C17"
GOLD_400 = "#E8B450"
GOLD_200 = "#F6D98A"
LIME_600 = "#479C23"
LIME_400 = "#7DD957"
LIME_200 = "#B7EAA2"
RED_400 = "#E45757"
AQUA_400 = "#4CC9F0"
VIOLET_400 = "#B084F5"
TEXT_100 = "#F2F4F8"
TEXT_500 = "#9AA4B2"
TEXT_700 = "#5F6B7D"

TIERS = [
    ("1", "I", TEXT_500, TEXT_700, "#CED3DA"),
    ("2", "II", LIME_400, LIME_600, LIME_200),
    ("3", "III", AQUA_400, "#1093BC", "#A1E3F7"),
    ("4", "IV", VIOLET_400, "#7A4BC4", "#E7D9FC"),
    ("5", "V", GOLD_400, GOLD_600, GOLD_200),
]

# 48 icon PUA, đúng thứ tự U+E000..U+E02F (work/nn4-icons.json)
ICON_IDS = [
    "tps", "ping", "online", "bounty", "cash", "coin", "sword", "shield",
    "land", "market", "auction", "casino", "mini", "menu", "home", "sethome",
    "spawn", "rp", "mail", "ally", "kill", "back", "bag", "bed",
    "chest", "heart", "star", "fire", "clock", "lock", "mail-verify", "warn",
    "check", "cross", "arrow-l", "arrow-r", "page-prev", "page-next", "search", "sort",
    "plus", "minus", "crown", "tier1", "tier2", "tier3", "tier4", "tier5",
]

ENTRY_ICONS = [
    ("market", "M"), ("cash", "$"), ("land", "L"), ("casino", "C"),
    ("mini", "G"), ("home", "H"), ("spawn", "S"), ("bounty", "B"),
    ("mail", "@"), ("ally", "A"), ("leaderboard", "T"),
]

# 24 item model cơ bản (work/nn4-design.md §4.6)
ITEM_MODELS = [
    "bg", "border",
    "btn_green", "btn_green_hover", "btn_green_disabled",
    "btn_gold", "btn_gold_hover", "btn_gold_disabled",
    "btn_gray", "btn_gray_hover", "btn_gray_disabled",
    "btn_gray_back", "btn_gray_close", "btn_gray_prev", "btn_gray_next",
    "btn_green_confirm", "btn_gold_sell",
    "title", "card",
    "tier_1", "tier_2", "tier_3", "tier_4", "tier_5",
]


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path(__file__).resolve().parent / "fonts" / ("BeVietnamPro-Bold.ttf" if bold else "BeVietnamPro-Regular.ttf"),
        Path("work/nn4_font_probe/BeVietnamPro-Bold.ttf" if bold else "work/nn4_font_probe/BeVietnamPro-Regular.ttf"),
    ]
    here = Path(__file__).resolve().parents[2]
    candidates += [
        here / "work/nn4_font_probe/BeVietnamPro-Bold.ttf" if bold else here / "work/nn4_font_probe/BeVietnamPro-Regular.ttf",
    ]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10
        return ImageFont.load_default()


def _save(img: Image.Image, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGBA").save(path, format="PNG", optimize=True)


def _rounded(size: tuple[int, int], radius: int, fill: str, outline: str | None = None, width: int = 1) -> Image.Image:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=fill,
                        outline=outline, width=width)
    return img


def draw_panel(path: Path, *, fill: str, outer: str, outer_w: int, inner: str,
               bevel_light: str, bevel_dark: str, size: tuple[int, int] = (48, 48),
               radius: int = 4) -> None:
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=outer)
    d.rounded_rectangle([outer_w, outer_w, w - 1 - outer_w, h - 1 - outer_w],
                        radius=max(0, radius - 1), fill=inner)
    inset = outer_w + 1
    d.rounded_rectangle([inset, inset, w - 1 - inset, h - 1 - inset],
                        radius=max(0, radius - 2), fill=fill)
    # bevel 2px trên/trái sáng, dưới/phải tối
    d.line([(inset + 1, inset + 1), (w - inset - 2, inset + 1)], fill=bevel_light, width=2)
    d.line([(inset + 1, inset + 1), (inset + 1, h - inset - 2)], fill=bevel_light, width=2)
    d.line([(inset + 1, h - inset - 2), (w - inset - 2, h - inset - 2)], fill=bevel_dark, width=2)
    d.line([(w - inset - 2, inset + 1), (w - inset - 2, h - inset - 2)], fill=bevel_dark, width=2)
    _save(img, path)


def draw_titlebar(path: Path) -> None:
    w, h = 48, 20
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=4, fill=GOLD_400)
    d.rounded_rectangle([2, 2, w - 3, h - 3], radius=3, fill=INK_900)
    d.rounded_rectangle([3, 3, w - 4, h - 4], radius=2, fill=INK_700)
    d.line([(3, h - 4), (w - 4, h - 4)], fill=GOLD_200, width=1)
    _save(img, path)


def draw_divider(path: Path) -> None:
    img = Image.new("RGBA", (16, 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 15, 3], fill=INK_900)
    d.line([(0, 1), (15, 1)], fill=GOLD_400, width=1)
    _save(img, path)


def draw_plate(path: Path, *, face: str, light: str | None, dark: str | None,
               outline: str = INK_900, size: int = 16) -> None:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=2, fill=outline)
    d.rectangle([1, 1, size - 2, size - 2], fill=face)
    if light:
        d.line([(1, 1), (size - 3, 1)], fill=light, width=2)
        d.line([(1, 1), (1, size - 3)], fill=light, width=2)
    if dark:
        d.line([(1, size - 2), (size - 2, size - 2)], fill=dark, width=2)
        d.line([(size - 2, 1), (size - 2, size - 2)], fill=dark, width=2)
    # corner pixels trong suốt để trông bo nhẹ
    for xy in [(0, 0), (size - 1, 0), (0, size - 1), (size - 1, size - 1)]:
        img.putpixel(xy, (0, 0, 0, 0))
    _save(img, path)


def draw_item_texture(path: Path, name: str) -> None:
    if name == "bg":
        img = Image.new("RGBA", (16, 16), INK_800)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 15, 15], outline=INK_600)
        d.line([(1, 1), (14, 1)], fill=INK_700)
        _save(img, path)
    elif name == "border":
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 15, 15], fill=INK_900)
        d.rectangle([1, 1, 14, 14], fill=GOLD_400)
        d.rectangle([2, 2, 13, 13], fill=INK_900)
        d.rectangle([3, 3, 12, 12], fill=(0, 0, 0, 0))
        _save(img, path)
    elif name.startswith("btn_"):
        rest = name[4:]
        variant, state = rest, ""
        for v in ("green", "gold", "gray"):
            if rest == v:
                variant, state = v, ""
                break
            if rest.startswith(v + "_"):
                variant, state = v, rest[len(v) + 1:]
                break
        faces = {
            "green": (LIME_400, LIME_200, LIME_600),
            "gold": (GOLD_400, GOLD_200, GOLD_600),
            "gray": (INK_700, INK_600, INK_950),
        }
        if state == "disabled":
            draw_plate(path, face=INK_800, light=None, dark=None, outline=INK_600)
        else:
            face, light, dark = faces[variant]
            outline = GOLD_200 if state == "hover" else INK_900
            draw_plate(path, face=face, light=light, dark=dark, outline=outline)
    elif name == "title":
        draw_plate(path, face=GOLD_400, light=GOLD_200, dark=GOLD_600)
    elif name == "card":
        img = Image.new("RGBA", (16, 16), INK_700)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, 15, 15], outline=INK_600)
        d.line([(1, 1), (14, 1)], fill=GOLD_400, width=2)
        _save(img, path)
    elif name.startswith("tier_"):
        idx = int(name.split("_")[1]) - 1
        _num, roman, primary, dark, light = TIERS[idx]
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        shield = [(3, 1), (12, 1), (12, 9), (8, 14), (3, 9)]
        d.polygon(shield, fill=INK_800, outline=primary)
        d.line(shield + [shield[0]], fill=primary, width=2)
        d.polygon([(4, 3), (11, 3), (11, 8), (8, 12), (4, 8)], outline=INK_900)
        if idx == 4:  # crown tier 5
            d.rectangle([5, 0, 10, 1], fill=GOLD_200)
        f = _font(7)
        box = d.textbbox((0, 0), roman, font=f)
        tw, th = box[2] - box[0], box[3] - box[1]
        d.text(((16 - tw) / 2 - box[0], (12 - th) / 2 - box[1]), roman, font=f, fill=primary)
        _save(img, path)
    else:
        raise ValueError(name)


def draw_entry_icon(path: Path, letter: str) -> None:
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, 31, 31], radius=5, fill=GOLD_400)
    d.rounded_rectangle([2, 2, 29, 29], radius=4, fill=INK_900)
    d.rounded_rectangle([3, 3, 28, 28], radius=3, fill=INK_800)
    f = _font(16)
    box = d.textbbox((0, 0), letter, font=f)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(((32 - tw) / 2 - box[0], (32 - th) / 2 - box[1]), letter, font=f, fill=TEXT_100)
    _save(img, path)


def draw_icon_atlas(path: Path) -> None:
    """Atlas 8x6 cell 16px: glyph placeholder = ô vuông gạch chéo.

    Đây KHÔNG phải icon thật — thay bằng atlas của font agent.
    """
    cols, rows, cell = 8, 6, 16
    img = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(len(ICON_IDS)):
        cx, cy = (i % cols) * cell, (i // cols) * cell
        d.rectangle([cx + 2, cy + 2, cx + 13, cy + 13], outline=(255, 255, 255, 255))
        d.line([(cx + 3, cy + 3), (cx + 12, cy + 12)], fill=(255, 255, 255, 255))
        d.line([(cx + 12, cy + 3), (cx + 3, cy + 12)], fill=(255, 255, 255, 255))
    _save(img, path)


def draw_pack_png(path: Path) -> None:
    size = 128
    img = Image.new("RGBA", (size, size), INK_900)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, size - 5, size - 5], radius=8, outline=GOLD_400, width=4)
    f1 = _font(42)
    f2 = _font(18)
    d.text((18, 30), "NN", font=f1, fill=GOLD_400)
    d.text((18, 78), "UI KIT", font=f2, fill=LIME_400)
    d.text((18, 100), "v1.0.0", font=_font(12), fill=TEXT_500)
    _save(img, path)


def write_json(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(out_dir: Path) -> list[str]:
    """Sinh placeholder vào out_dir (assets/...). Trả về danh sách path tương đối."""
    out_dir = Path(out_dir)
    created: list[str] = []

    def rel(p: Path) -> str:
        created.append(p.relative_to(out_dir).as_posix())
        return str(p)

    # --- pack.png
    draw_pack_png(rel(out_dir / "pack.png"))

    # --- font icon (provider nomnom:ui)
    draw_icon_atlas(rel(out_dir / "assets/nomnom/textures/font/icons.png"))
    rows = ["".join(chr(0xE000 + r * 8 + c) for c in range(8)) for r in range(6)]
    write_json(rel(out_dir / "assets/nomnom/font/ui.json"), {
        "providers": [{
            "type": "bitmap",
            "file": "nomnom:font/icons.png",
            "height": 9,
            "ascent": 9,
            "chars": rows,
        }],
    })

    # --- GUI 9-slice
    draw_panel(rel(out_dir / "assets/nomnom/textures/gui/panel_primary.png"),
               fill=INK_800, outer=GOLD_400, outer_w=2, inner=INK_900,
               bevel_light=INK_700, bevel_dark=INK_900)
    draw_panel(rel(out_dir / "assets/nomnom/textures/gui/panel_inset.png"),
               fill=INK_900, outer=INK_600, outer_w=1, inner=INK_900,
               bevel_light=INK_900, bevel_dark=INK_700)
    draw_panel(rel(out_dir / "assets/nomnom/textures/gui/panel_raised.png"),
               fill=INK_700, outer=GOLD_400, outer_w=2, inner=INK_900,
               bevel_light=INK_600, bevel_dark=INK_900)
    draw_titlebar(rel(out_dir / "assets/nomnom/textures/gui/titlebar.png"))
    draw_divider(rel(out_dir / "assets/nomnom/textures/gui/divider.png"))

    # --- item texture + model + item definition
    for name in ITEM_MODELS:
        tex = out_dir / f"assets/nomnom/textures/item/ui/{name}.png"
        draw_item_texture(tex, name)
        rel(tex)
        model_id = f"nomnom:item/ui/{name}"
        write_json(rel(out_dir / f"assets/nomnom/models/item/ui/{name}.json"), {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"nomnom:item/ui/{name}"},
        })
        write_json(rel(out_dir / f"assets/nomnom/items/ui/{name}.json"), {
            "model": {"type": "minecraft:model", "model": model_id},
        })

    for name, letter in ENTRY_ICONS:
        tex = out_dir / f"assets/nomnom/textures/item/ui/icon/{name}.png"
        draw_entry_icon(tex, letter)
        rel(tex)
        write_json(rel(out_dir / f"assets/nomnom/models/item/ui/icon/{name}.json"), {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"nomnom:item/ui/icon/{name}"},
        })
        write_json(rel(out_dir / f"assets/nomnom/items/ui/icon/{name}.json"), {
            "model": {"type": "minecraft:model", "model": f"nomnom:item/ui/icon/{name}"},
        })

    return sorted(created)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh placeholder asset NomNom UI")
    ap.add_argument("--out", default="work/rp_build/placeholders")
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        # xoá sạch để idempotent
        for p in sorted(out.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
    files = build(out)
    print(f"placeholders: {len(files)} file -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
