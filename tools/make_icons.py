# -*- coding: utf-8 -*-
"""Генератор иконок предметов и коллажа icon_sheet.png.

Иконки рисуются кодом, поэтому их легко править и они не «нарезаны» из чужих
картинок: один стиль, один палитровый набор, прозрачный фон.
Запуск: python tools/make_icons.py
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE, "assets")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

AMBER = (229, 183, 103, 255)
AMBER_D = (150, 110, 52, 255)
TEAL = (143, 197, 236, 255)
GREY = (170, 180, 190, 255)
RED = (196, 88, 103, 255)
GREEN = (130, 176, 128, 255)
WHITE = (235, 240, 246, 255)


def canvas(size=128):
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def rr(d, box, r, fill=None, outline=None, width=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def plate(size=128, tint=None):
    im = canvas(size)
    d = ImageDraw.Draw(im)
    rr(d, (4, 4, size - 4, size - 4), 24, fill=(19, 27, 36, 255), outline=tint or (58, 78, 98, 255), width=3)
    rr(d, (12, 12, size - 12, size - 12), 17, outline=(255, 255, 255, 16), width=2)
    return im, d


# ---------------- отдельные предметы ----------------
def i_cig(c):
    im, d = plate()
    # пачка и одна сигарета рядом
    d.rounded_rectangle((28, 40, 72, 104), radius=6, fill=(228, 226, 220, 255), outline=(120, 120, 120, 255), width=2)
    d.rectangle((28, 40, 72, 58), fill=AMBER)
    d.text((50, 82), "Я", font=ImageFont.truetype(FONT, 26), fill=(90, 70, 50, 255), anchor="mm")
    d.rounded_rectangle((84, 34, 100, 96), radius=5, fill=WHITE, outline=(170, 170, 170, 255), width=2)
    d.rectangle((84, 34, 100, 52), fill=(200, 150, 90, 255))
    d.ellipse((88, 26, 98, 38), fill=(70, 70, 70, 200))
    d.arc((86, 14, 96, 28), 250, 290, fill=(200, 200, 200, 130), width=2)
    return im


def i_coin(c):
    im, d = plate()
    d.ellipse((24, 24, 104, 104), fill=(52, 46, 28, 255), outline=AMBER, width=4)
    d.ellipse((34, 34, 94, 94), outline=AMBER_D, width=3)
    f = ImageFont.truetype(FONT, 46)
    d.text((64, 66), "₽", font=f, fill=AMBER, anchor="mm")
    return im


def i_knife(c):
    im, d = plate()
    d.polygon([(52, 30), (78, 34), (96, 92), (66, 98)], fill=(212, 222, 232, 255), outline=(110, 124, 138, 255))
    d.polygon([(52, 30), (66, 78), (66, 98)], fill=(240, 246, 252, 255))
    d.rounded_rectangle((60, 92, 82, 108), radius=4, fill=AMBER, outline=AMBER_D, width=2)
    return im


def i_tea(c):
    im, d = plate()
    d.rounded_rectangle((34, 48, 92, 96), radius=10, fill=(64, 44, 34, 255), outline=AMBER, width=4)
    d.ellipse((34, 42, 92, 60), fill=(120, 78, 48, 255), outline=AMBER, width=3)
    d.arc((92, 56, 116, 86), 300, 60, fill=AMBER, width=5)
    for x in (50, 64, 78):
        d.arc((x - 8, 18, x + 8, 40), 250, 290, fill=(220, 220, 220, 140), width=3)
    return im


def i_soup(c):
    im, d = plate()
    d.pieslice((22, 40, 106, 112), 0, 180, fill=(66, 86, 92, 255), outline=AMBER, width=4)
    d.line((22, 76, 106, 76), fill=AMBER, width=4)
    d.ellipse((46, 56, 62, 66), fill=GREEN)
    d.ellipse((70, 52, 84, 62), fill=(196, 150, 96, 255))
    d.arc((52, 20, 76, 48), 250, 290, fill=(220, 220, 220, 120), width=3)
    return im


def i_book(c):
    im, d = plate()
    d.rounded_rectangle((30, 26, 98, 104), radius=6, fill=(30, 44, 58, 255), outline=AMBER, width=4)
    d.line((44, 26, 44, 104), fill=AMBER_D, width=4)
    for y in (48, 62, 76, 90):
        d.line((54, y, 88, y), fill=(160, 175, 190, 200), width=3)
    return im


def i_clock(c):
    im, d = plate()
    d.ellipse((26, 26, 102, 102), outline=AMBER, width=5, fill=(20, 26, 34, 255))
    d.line((64, 64, 64, 44), fill=WHITE, width=5)
    d.line((64, 64, 82, 74), fill=TEAL, width=5)
    d.ellipse((60, 60, 68, 68), fill=AMBER)
    return im


def i_heart(c):
    im, d = plate(tint=(120, 52, 62, 255))
    d.ellipse((28, 34, 68, 74), fill=RED)
    d.ellipse((60, 34, 100, 74), fill=RED)
    d.polygon([(30, 62), (98, 62), (64, 104)], fill=RED)
    d.ellipse((44, 44, 56, 54), fill=(240, 170, 170, 190))
    return im


def i_fist(c):
    im, d = plate()
    d.rounded_rectangle((28, 46, 100, 96), radius=16, fill=(168, 132, 104, 255), outline=AMBER_D, width=3)
    for x in (40, 56, 72, 88):
        d.rounded_rectangle((x - 9, 34, x + 9, 60), radius=8, fill=(186, 148, 118, 255), outline=AMBER_D, width=2)
    d.line((52, 74, 80, 74), fill=(110, 84, 66, 255), width=3)
    return im


def i_rat(c):
    im, d = plate()
    d.ellipse((30, 60, 86, 96), fill=(120, 122, 130, 255))
    d.ellipse((66, 50, 96, 80), fill=(140, 142, 150, 255))
    d.ellipse((74, 42, 90, 58), fill=(160, 162, 170, 255))
    d.ellipse((92, 58, 100, 66), fill=(240, 160, 170, 255))
    d.arc((18, 62, 54, 98), 90, 300, fill=(160, 162, 170, 255), width=5)
    d.ellipse((82, 60, 88, 66), fill=(20, 20, 20, 255))
    return im


def i_star(c):
    im, d = plate()
    cx, cy, R, r = 64, 64, 40, 17
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    d.polygon(pts, fill=AMBER, outline=(255, 232, 180, 255))
    return im


def i_key(c):
    im, d = plate()
    d.ellipse((26, 34, 66, 74), outline=AMBER, width=7)
    d.line((60, 68, 98, 104), fill=AMBER, width=8)
    d.line((84, 90, 96, 78), fill=AMBER, width=7)
    d.line((74, 100, 86, 88), fill=AMBER, width=7)
    return im


def i_cross(c):
    im, d = plate(tint=(90, 110, 140, 255))
    d.line((64, 22, 64, 106), fill=AMBER, width=11)
    d.line((40, 50, 88, 50), fill=AMBER, width=11)
    d.ellipse((56, 96, 72, 112), fill=AMBER)
    return im


def i_phone(c):
    im, d = plate()
    d.rounded_rectangle((30, 24, 98, 104), radius=12, fill=(28, 38, 50, 255), outline=AMBER, width=4)
    d.rectangle((40, 38, 88, 70), fill=(16, 22, 30, 255), outline=(70, 90, 110, 255))
    for y in (80, 90):
        for x in (42, 56, 70, 84):
            d.ellipse((x, y, x + 8, y + 8), fill=AMBER_D)
    return im


def i_sack(c):
    im, d = plate()
    d.polygon([(44, 30), (84, 30), (96, 100), (32, 100)], fill=(96, 88, 70, 255), outline=AMBER_D, width=3)
    d.line((44, 30, 84, 30), fill=AMBER, width=8)
    d.text((64, 68), "П", font=ImageFont.truetype(FONT, 34), fill=AMBER, anchor="mm")
    return im


def i_shield(c):
    im, d = plate()
    d.polygon([(64, 24), (100, 40), (94, 84), (64, 106), (34, 84), (28, 40)], fill=(34, 56, 74, 255), outline=AMBER, width=4)
    d.line((44, 48, 84, 88), fill=AMBER, width=5)
    d.line((84, 48, 44, 88), fill=AMBER, width=5)
    return im


def i_shoe(c):
    im, d = plate()
    d.polygon([(26, 92), (30, 58), (60, 34), (74, 40), (66, 62), (102, 78), (102, 94)], fill=(58, 48, 40, 255), outline=AMBER, width=4)
    d.line((26, 92, 102, 94), fill=(30, 24, 20, 255), width=6)
    for y, x0, x1 in ((48, 40, 58), (58, 44, 66), (68, 50, 74)):
        d.line((x0, y, x1, y + 8), fill=WHITE, width=3)
    return im


def i_cards(c):
    im, d = plate()
    for off in (0, 10, 20):
        d.rounded_rectangle((30 + off, 34, 78 + off, 96), radius=6, fill=(22, 30, 40, 255), outline=AMBER, width=3)
    d.text((78, 64), "A", font=ImageFont.truetype(FONT, 30), fill=RED, anchor="mm")
    return im


def i_wall(c):
    im, d = plate()
    for y in (34, 62, 90):
        d.line((26, y, 102, y), fill=(110, 118, 126, 255), width=3)
    for y, xs in ((34, (26, 48, 70, 92)), (62, (38, 60, 82)), (90, (26, 48, 70, 92))):
        for x in xs:
            d.line((x, y, x, y + 28), fill=(90, 98, 106, 255), width=3)
    return im


def i_fire(c):
    im, d = plate(tint=(120, 70, 40, 255))
    d.polygon([(64, 22), (86, 62), (78, 62), (94, 92), (64, 78), (34, 92), (50, 62), (42, 62)],
              fill=(232, 150, 70, 255), outline=AMBER)
    d.polygon([(64, 48), (76, 76), (64, 90), (52, 76)], fill=(250, 214, 130, 255))
    return im


ICONS = {"cig": i_cig, "coin": i_coin, "knife": i_knife, "tea": i_tea, "soup": i_soup,
         "book": i_book, "clock": i_clock, "heart": i_heart, "fist": i_fist, "rat": i_rat,
         "star": i_star, "key": i_key, "cross": i_cross, "phone": i_phone, "sack": i_sack,
         "shield": i_shield, "shoe": i_shoe, "cards": i_cards, "wall": i_wall, "fire": i_fire}


def main():
    os.makedirs(ASSETS, exist_ok=True)
    names = list(ICONS)
    for n in names:
        ICONS[n](None).save(os.path.join(ASSETS, "item_%s.png" % n))
    cols = 7
    rows = (len(names) + cols - 1) // cols
    cell, pad = 132, 10
    sheet = Image.new("RGBA", (cols * cell + pad * 2, rows * cell + pad * 2 + 40), (11, 17, 24, 255))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 15)
    for i, n in enumerate(names):
        x, y = pad + (i % cols) * cell, pad + 40 + (i // cols) * cell
        sheet.alpha_composite(ICONS[n](None), (x, y))
        d.text((x + cell // 2, y + cell - 2), n, font=f, fill=(150, 165, 180, 255), anchor="mm")
    d.text((pad, 16), "ТЮРЯГА · иконки предметов v8", font=ImageFont.truetype(FONT, 20), fill=(229, 183, 103, 255))
    sheet.save(os.path.join(ASSETS, "icon_sheet.png"))
    print("icons:", len(names))


if __name__ == "__main__":
    main()
