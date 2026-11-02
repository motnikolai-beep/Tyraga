# -*- coding: utf-8 -*-
"""Нарезка присланного коллажа иконок на отдельные PNG.

Сетка: 8 колонок × 4 ряда (1402×1122). Режется равномерно по колонкам и по
найденным тёмным дорожкам между рядами, затем каждая плитка обрезается до
квадрата, получает скруглённые углы и сохраняется в assets/icons/.

Запуск: python tools/slice_icons.py [путь_к_коллажу]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "assets", "icons")
COLS, ROWS = 8, 4

# имена по порядку слева направо, сверху вниз
NAMES = [
    "heart", "cap", "star", "coin", "cig", "clock", "lock", "radiation",
    "book", "barbell", "bunk", "zone", "soup", "pot", "water", "papers",
    "sock", "candle", "bars", "money", "skull", "medal", "boot", "gloves",
    "knife", "jacket", "magnifier", "ear", "rat", "firstaid", "radio", "chess",
]
# дополнительные иконки, нарисованные отдельно (в коллаже их не было)
EXTRA = ["bread", "phone", "cross"]

# центры рядов (по анализу яркости коллажа)
ROW_CENTERS = [133, 396, 660, 941]


def rounded(im, radius_frac=0.13):
    im = im.convert("RGB")
    size = im.size[0]
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * radius_frac), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    out.putalpha(mask)
    return out


def main(path=None):
    path = path or sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        raise SystemExit("укажите путь к коллажу иконок")
    src = Image.open(path).convert("RGB")
    W, H = src.size
    os.makedirs(OUT, exist_ok=True)
    pitch = W / COLS
    gray = np.asarray(src.convert("L"), dtype=float)
    k = 0
    made = []
    for r in range(ROWS):
        yc = ROW_CENTERS[r]
        for c in range(COLS):
            x0, x1 = int(c * pitch) + 7, int((c + 1) * pitch) - 7
            y0, y1 = max(0, yc - 104), min(H, yc + 104)
            sub = gray[y0:y1, x0:x1]
            mask = sub > 35
            if mask.sum() > 40:
                ys, xs = np.nonzero(mask)
                cx, cy = x0 + xs.mean(), y0 + ys.mean()
                span = max(xs.max() - xs.min(), ys.max() - ys.min())
            else:
                cx, cy, span = (x0 + x1) / 2, yc, 150
            side = int(min(162, x1 - x0, y1 - y0, max(140, span * 1.12)))
            left = int(min(max(x0, cx - side / 2), x1 - side))
            top = int(min(max(y0, cy - side / 2), y1 - side))
            tile = src.crop((left, top, left + side, top + side))
            inset = int(tile.width * 0.06)
            tile = tile.crop((inset, inset, tile.width - inset, tile.height - inset))
            tile = tile.resize((240, 240), Image.Resampling.LANCZOS)
            name = NAMES[k] if k < len(NAMES) else "icon_%02d" % k
            rounded(tile).save(os.path.join(OUT, name + ".png"))
            made.append(name)
            k += 1
    made += [n for n in EXTRA if os.path.isfile(os.path.join(OUT, n + ".png"))]
    rows = (len(made) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (COLS * 128 + 20, rows * 128 + 46), (11, 17, 24, 255))
    sd = ImageDraw.Draw(sheet)
    try:
        from PIL import ImageFont
        tf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
        lf = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    except OSError:
        tf = lf = None
    sd.text((10, 10), "ТЮРЯГА · иконки предметов", font=tf, fill=(229, 183, 103, 255))
    for i, name in enumerate(made):
        im = Image.open(os.path.join(OUT, name + ".png")).resize((118, 118), Image.Resampling.LANCZOS)
        x, y = 10 + (i % COLS) * 128, 40 + (i // COLS) * 128
        sheet.alpha_composite(im, (x, y))
        sd.text((x + 59, y + 118), name, font=lf, fill=(135, 153, 172, 255), anchor="ma")
    sheet.save(os.path.join(BASE, "assets", "icon_sheet.png"))
    print("saved %d icons into assets/icons + icon_sheet.png" % len(made))
    return made


if __name__ == "__main__":
    main()
