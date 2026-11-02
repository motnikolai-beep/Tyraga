# -*- coding: utf-8 -*-
"""Рендер сцены и карты зоны (Pillow). Никакого tkinter — можно тестировать headless.

Сцена: фон локации, «сцена» с карточками NPC внизу, карточка игрока и панель
диалога отдельной полосой — поэтому реплики физически не могут наехать на аватарки.
Карта: схематичный план зоны с корпусами, дорожками и отметками, а не нарезка картинок.
"""
import math
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from data import BOSSES, ITEMS, LOCATIONS

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")

BG = (9, 13, 18)
PANEL = (16, 23, 32)
CARD = (24, 35, 49)
CARD_HI = (38, 54, 74)
FG = (230, 237, 244)
MUTED = (135, 153, 172)
GOLD = (229, 183, 103)
GOLD_D = (150, 116, 60)
RED = (196, 88, 103)
GREEN = (130, 176, 128)
BLUE = (143, 197, 236)
DARK = (10, 15, 21)

_FONT_CACHE = {}
_FONT_PATHS = [
    ("segoeui", r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
    ("dejavu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def font(size, bold=False):
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    f = None
    for name, regular, b in _FONT_PATHS:
        path = b if bold else regular
        if os.path.isfile(path):
            try:
                f = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
    if f is None:
        f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def text_w(d, s, f):
    try:
        return d.textlength(s, font=f)
    except Exception:
        return len(s) * (f.size * 0.55)


def wrap(s, f, maxw, d=None):
    """Перенос по словам; поддерживает явные \n."""
    lines = []
    for para in str(s).split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if d is not None and text_w(d, trial, f) <= maxw:
                cur = trial
            elif d is None and len(trial) * f.size * 0.55 <= maxw:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def truncate_lines(d, s, f, maxw, max_lines):
    lines = wrap(s, f, maxw, d)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    last = lines[-1]
    while last and text_w(d, last + "…", f) > maxw:
        last = last[:-1]
    lines[-1] = last + "…"
    return lines


def rr(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def shadow(img, box, radius=14, blur=8, alpha=110):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.alpha_composite(layer)


def cover(img, size):
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS)


class SceneRenderer:
    """Кеширует фоны и портреты, чтобы интерфейс не тормозил при перерисовке."""

    def __init__(self, npcs):
        self.npcs = npcs
        self.cache = {}

    def _bg(self, loc, size):
        key = ("bg", loc, size)
        if key in self.cache:
            return self.cache[key]
        path = os.path.join(ASSETS, "loc_%d.jpg" % loc)
        im = Image.open(path).convert("RGB")
        im = cover(im, size)
        im = ImageEnhance.Brightness(im).enhance(0.62)
        im = ImageEnhance.Color(im).enhance(0.9)
        # затемнение снизу и сверху под интерфейс
        grad = Image.new("L", (1, size[1]), 0)
        for y in range(size[1]):
            t = y / max(1, size[1] - 1)
            v = int(150 * max(0.0, (t - 0.35) / 0.65) ** 1.4)
            grad.putpixel((0, y), v)
        dark = Image.new("RGB", size, DARK)
        im = Image.composite(dark, im, grad.resize(size)).convert("RGB")
        self.cache[key] = im
        return im

    def _portrait(self, key, size):
        k = ("p", key, size)
        if k in self.cache:
            return self.cache[k]
        path = os.path.join(ASSETS, (self.npcs[key]["portrait"] + ".jpg"))
        im = Image.open(path).convert("RGB")
        im = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.35))
        im = ImageEnhance.Brightness(im).enhance(0.95)
        self.cache[k] = im
        return im

    def _player(self, size, rank_key, dropped):
        k = ("player", size, rank_key, dropped)
        if k in self.cache:
            return self.cache[k]
        path = os.path.join(ASSETS, "player_avatar.png")
        im = Image.open(path).convert("RGB")
        im = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.3))
        if dropped:
            im = ImageEnhance.Color(im).enhance(0.35)
        self.cache[k] = im
        return im

    # ------------------------------------------------------------ сцена
    def scene(self, size, world, ui):
        """ui: {'npc': выбранный, 'text': реплика, 'who': имя, 'hover': ключ,
        'toasts': [...], 'objective': str, 'story_ready': bool, 'bubbles': bool}"""
        W, H = size
        img = self._bg(world.s["loc"], size).convert("RGBA")
        d = ImageDraw.Draw(img)
        loc = LOCATIONS[world.s["loc"]]

        # верхняя плашка
        top = 58
        rr(d, (16, 12, 340, 12 + top), 12, fill=(11, 18, 26, 232), outline=(50, 70, 92, 255))
        d.text((34, 24), loc["name"].upper(), font=font(22, True), fill=GOLD)
        d.text((34, 50), loc["hint"], font=font(12), fill=(150, 168, 186))
        # часы
        rr(d, (W - 250, 12, W - 16, 12 + top), 12, fill=(11, 18, 26, 232), outline=(50, 70, 92, 255))
        phase = world.phase()
        icon = {"утро": "☀", "день": "☼", "вечер": "◐", "ночь": "☾"}.get(phase, "•")
        d.text((W - 232, 24), world.clock(), font=font(24, True), fill=FG)
        d.text((W - 232, 54), "%s %s · день %d" % (icon, phase, world.s["day"]),
               font=font(12), fill=MUTED)
        if world.is_night():
            d.text((W - 120, 24), "ОТБОЙ", font=font(14, True), fill=BLUE)

        # карточки NPC в «сцене»
        present = world.witnesses()
        selected = ui.get("npc")
        n = max(1, len(present))
        card_w = min(196, int((W - 260) / max(1, n)) - 12)
        card_w = max(96, card_w)
        card_h = int(card_w * 1.42)
        gap = 12
        total = n * card_w + (n - 1) * gap
        start = max(300, (W - total) // 2)
        base_y = H - 168 - card_h
        hits = []
        for i, k in enumerate(present):
            x = start + i * (card_w + gap)
            y = base_y
            active = k == selected
            hover = k == ui.get("hover")
            self._npc_card(img, d, k, (x, y, x + card_w, y + card_h), world, active, hover)
            hits.append((k, (x, y, x + card_w, y + card_h)))
        if not present:
            d.text((W // 2, base_y + card_h // 2), "Здесь пусто. Только эхо и твои мысли.",
                   font=font(16), fill=MUTED, anchor="mm")

        # карточка игрока слева
        pw, ph = 118, 168
        px, py = 26, 92
        self._player_card(img, d, (px, py, px + pw, py + ph), world)

        # панель диалога — отдельная полоса, ничего не перекрывает
        bar_top = H - 150
        rr(d, (16, bar_top, W - 16, H - 14), 14, fill=(9, 15, 22, 242), outline=(58, 80, 104, 255), width=2)
        accent = RED if world.rank_key() in ("petukh", "opush") else GOLD
        d.rectangle((16, bar_top, 22, H - 14), fill=accent)
        who = ui.get("who") or "Тишина"
        d.text((40, bar_top + 12), who.upper(), font=font(15, True), fill=GOLD)
        body = ui.get("text") or "Выбери, с кем говорить, или займись делом."
        lines = truncate_lines(d, body, font(15), W - 120, 4)
        for j, line in enumerate(lines):
            d.text((40, bar_top + 38 + j * 22), line, font=font(15), fill=FG)
        hint = ui.get("hint") or "Enter — сказать · F2 — история · Q — сюжет · M — карта"
        d.text((40, bar_top + 126), hint, font=font(11), fill=MUTED)

        # цель по сюжету
        obj = ui.get("objective")
        if obj:
            f = font(12, True)
            tw = text_w(d, obj, f)
            x0 = W - tw - 60
            rr(d, (x0, 86, W - 16, 122), 10, fill=(12, 19, 27, 225), outline=(GOLD_D[0], GOLD_D[1], GOLD_D[2], 255))
            d.text((x0 + 12, 92), "ЦЕЛЬ", font=font(10, True), fill=GOLD)
            d.text((x0 + 12, 104), obj, font=f, fill=(232, 238, 245))
            if ui.get("story_ready"):
                d.ellipse((x0 - 12, 96, x0 - 2, 106), fill=GOLD)

        # тосты — стопкой слева снизу, над панелью диалога
        blocks = []
        for t in (ui.get("toasts") or [])[-4:]:
            blocks.append(t)
        y = bar_top - 14
        for t in reversed(blocks):
            col = {"good": GREEN, "bad": RED, "respect": GOLD, "story": BLUE,
                   "day": GOLD}.get(t.get("kind"), MUTED)
            lines = truncate_lines(d, t["text"], font(12), 430, 2)
            h = 14 + 17 * len(lines)
            wmax = max(text_w(d, l, font(12)) for l in lines) + 48
            y -= h
            rr(d, (22, y, 22 + wmax, y + h), 8, fill=(10, 16, 23, 232), outline=col)
            for j, l in enumerate(lines):
                d.text((34, y + 7 + j * 17), l, font=font(12), fill=col)
            y -= 6
        return img.convert("RGB"), hits

    def _npc_card(self, img, d, k, box, world, active, hover):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        shadow(img, (x0 + 3, y0 + 5, x1 + 3, y1 + 5), radius=12, blur=7)
        portrait = self._portrait(k, (w, h))
        img.paste(portrait, (x0, y0))
        # затемнение под подписи
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle((0, h - 44, w, h), fill=(8, 13, 19, 205))
        img.alpha_composite(ov, (x0, y0))
        border = GOLD if active else (BLUE if hover else (44, 62, 82))
        d.rounded_rectangle(box, radius=10, outline=border, width=3 if active else 2)
        name = world.npcs[k]["name"]
        d.text((x0 + 8, y0 + h - 34), name, font=font(13, True), fill=FG)
        boss = BOSSES.get(k)
        dead = k in world.s["defeated"]
        if boss and not dead:
            d.text((x0 + w - 26, y0 + 6), "★", font=font(18, True), fill=GOLD)
        if dead:
            d.line((x0 + 6, y0 + 6, x1 - 6, y1 - 50), fill=RED, width=3)
        # HP
        mx = 130 if boss else 100
        hp = world.s["npc_hp"].get(k, mx)
        bw = w - 16
        d.rectangle((x0 + 8, y0 + h - 14, x0 + 8 + bw, y0 + h - 6), fill=(30, 16, 20, 230))
        frac = max(0.0, min(1.0, hp / mx))
        d.rectangle((x0 + 8, y0 + h - 14, x0 + 8 + bw * frac, y0 + h - 6), fill=RED)
        cast = world.npcs[k].get("cast", "muzhik")
        mark = {"authority": "охрана", "blatnoy": "блатной", "civil": "гражданка"}.get(cast, "мужик")
        d.text((x1 - 8, y0 + 6), mark, font=font(9), fill=MUTED, anchor="ra")

    def _player_card(self, img, d, box, world):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        rank = world.rank()
        dropped = world.rank_key() in ("petukh", "opush")
        self.cache_ready = True
        portrait = self._player((w, h - 34), world.rank_key(), dropped)
        shadow(img, (x0 + 3, y0 + 5, x1 + 3, y1 + 5), radius=12, blur=7)
        img.paste(portrait, (x0, y0))
        ov = Image.new("RGBA", (w, h - 34), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rectangle((0, h - 34 - 26, w, h - 34), fill=(8, 13, 19, 200))
        img.alpha_composite(ov, (x0, y0))
        d.rounded_rectangle((x0, y0, x1, y1), radius=10, outline=(GOLD if not dropped else RED), width=2)
        d.text((x0 + w / 2, y0 + h - 44), "ВЫ", font=font(12, True), fill=FG, anchor="mm")
        rank_col = RED if dropped else (GOLD if rank["key"] in ("blatnoy", "pahan") else BLUE)
        rr(d, (x0, y1 - 32, x1, y1), 8, fill=(12, 19, 27, 235), outline=rank_col)
        d.text((x0 + w / 2, y1 - 16), rank["title"], font=font(12, True), fill=rank_col, anchor="mm")
        # хп-полоска снизу карточки
        frac = max(0.0, min(1.0, world.s["hp"] / world.s["hp_max"]))
        d.rectangle((x0, y0 - 8, x1, y0 - 3), fill=(30, 16, 20, 230))
        d.rectangle((x0, y0 - 8, x0 + w * frac, y0 - 3), fill=RED)

    # ------------------------------------------------------------ карта
    def map(self, size, world):
        W, H = size
        img = Image.new("RGBA", size, (12, 18, 25, 255))
        d = ImageDraw.Draw(img)
        # сетка-миллиметровка
        for x in range(0, W, 40):
            d.line((x, 0, x, H), fill=(18, 26, 35, 255))
        for y in range(0, H, 40):
            d.line((0, y, W, y), fill=(18, 26, 35, 255))
        d.text((28, 20), "ПЛАН ЗОНЫ", font=font(24, True), fill=GOLD)
        d.text((28, 52), "Щёлкни по объекту, чтобы перейти. ★ — босс, ✕ — уже повержен.",
               font=font(12), fill=MUTED)

        sx = (W - 60) / 1000.0
        sy = (H - 130) / 640.0
        ox, oy = 30, 100

        def T(x, y):
            return ox + x * sx, oy + y * sy

        # периметр
        p = [T(20, 20), T(980, 20), T(980, 620), T(20, 620)]
        d.line(p + [p[0]], fill=(96, 120, 146, 255), width=6)
        for i in range(0, 1000, 60):
            x1, y1 = T(i, 20)
            d.line((x1, y1, x1 - 8, y1 + 16), fill=(70, 88, 108, 255), width=3)
            x2, y2 = T(i, 620)
            d.line((x2, y2, x2 - 8, y2 - 16), fill=(70, 88, 108, 255), width=3)
        # КПП
        gx, gy = T(940, 240)
        d.rectangle((gx - 4, gy - 20, gx + 8, gy + 20), fill=(96, 122, 146, 255))
        d.text((gx + 10, gy), "КПП", font=font(10), fill=MUTED, anchor="lm")
        # вышка
        tx, ty = T(470, 40)
        d.polygon([(tx - 14, ty + 22), (tx, ty - 16), (tx + 14, ty + 22)], outline=(120, 140, 160, 255), width=3)
        d.text((tx, ty + 26), "вышка", font=font(10), fill=MUTED, anchor="ma")
        # дорожки
        paths = [((230, 180), (260, 180)), ((460, 180), (490, 180)), ((360, 220), (360, 250)),
                 ((230, 310), (260, 310)), ((230, 420), (260, 420)), ((230, 525), (260, 525)),
                 ((360, 430), (360, 455)), ((460, 340), (490, 340)),
                 ((660, 280), (690, 280)), ((660, 385), (690, 385)), ((765, 240), (765, 260)),
                 ((765, 330), (765, 350)), ((765, 430), (765, 455)), ((660, 180), (690, 180)),
                 ((660, 500), (690, 500)), ((900, 240), (940, 240))]
        for a, b in paths:
            d.line([T(*a), T(*b)], fill=(70, 92, 112, 255), width=10)
            d.line([T(*a), T(*b)], fill=(96, 122, 146, 255), width=3)

        hits = []
        for i, loc in enumerate(LOCATIONS):
            x, y, w, h = loc["map"]
            x0, y0 = T(x, y)
            x1, y1 = T(x + w, y + h)
            cur = world.s["loc"] == i
            fill = (44, 62, 78, 255) if not cur else (74, 60, 34, 255)
            d.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=fill,
                                outline=GOLD if cur else (78, 100, 122, 255), width=3 if cur else 2)
            # лёгкие «крыши»
            d.line((x0 + 8, y0 + 8, x1 - 8, y0 + 8), fill=(120, 144, 166, 120), width=2)
            d.text((x0 + 10, y0 + 12), str(i + 1), font=font(11, True), fill=MUTED)
            name = loc["name"]
            nf = font(13, True) if (x1 - x0) > 110 else font(11, True)
            d.text(((x0 + x1) / 2, (y0 + y1) / 2 + 4), name, font=nf,
                   fill=FG if not cur else GOLD, anchor="mm")
            alive = [k for k in BOSSES if LOCATIONS[BOSSES[k]["loc"]]["key"] == loc["key"]
                     and k not in world.s["defeated"]]
            dead = [k for k in BOSSES if LOCATIONS[BOSSES[k]["loc"]]["key"] == loc["key"]
                    and k in world.s["defeated"]]
            bx = x1 - 16
            for k in alive[:3]:
                d.text((bx, y0 + 10), "★", font=font(14, True), fill=GOLD)
                bx -= 16
            for k in dead[:3]:
                d.text((bx, y0 + 10), "✕", font=font(13, True), fill=RED)
                bx -= 16
            if cur:
                cx, cy = (x0 + x1) / 2, y0 - 14
                d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=GOLD)
                d.text((cx, cy - 22), "ВЫ", font=font(11, True), fill=GOLD, anchor="ma")
            hits.append((loc["key"], i, (x0, y0, x1, y1)))
        # легенда
        legend_y = H - 24
        d.text((30, legend_y - 6), "★ босс на объекте   ✕ босс повержен   ○ вы здесь   "
                                   "Кича откроется по сюжету",
               font=font(11), fill=MUTED)
        return img.convert("RGB"), hits

    # ------------------------------------------------------------ инвентарь-иконки
    def icon(self, name, size=56):
        key = ("icon", name, size)
        if key in self.cache:
            return self.cache[key]
        path = os.path.join(ASSETS, "item_%s.png" % name)
        if not os.path.isfile(path):
            return None
        im = Image.open(path).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        self.cache[key] = im
        return im


def placeholder_scene(size=(1200, 620)):
    """Заглушка для тестов без мира."""
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    d.text((30, 30), "ТЮРЯГА v8", font=font(28, True), fill=GOLD)
    return img
