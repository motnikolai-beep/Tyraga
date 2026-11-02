# -*- coding: utf-8 -*-
"""Расширенное приложение: мини-игры (pygame-интерфейс) и звуки поверх базового App."""
import pygame

from . import minigames as mgm
from .sfx import Sfx
from .ui import App, GOLD, WHITE, GREY, PANEL

KEYNAMES = {}


def _keynames():
    if not KEYNAMES:
        for attr, name in (("K_LEFT", "left"), ("K_RIGHT", "right"), ("K_UP", "up"), ("K_DOWN", "down")):
            if hasattr(pygame, attr):
                KEYNAMES[getattr(pygame, attr)] = name
    return KEYNAMES


class App2(App):
    def __init__(self, hq=False):
        super().__init__(hq)
        self.mgame = None
        self.mg_aid = None
        self.sfx = Sfx()
        orig = self.g.do_tactic

        def wrapped(i):
            orig(i)
            self.sfx.play("hit")
        self.g.do_tactic = wrapped

    # ---------- запуск мини-игры ----------
    def start_mini(self, aid):
        m = self.g.A[aid]["mini"]
        if m.get("type"):
            self.mgame = mgm.create(m["type"], self.g, m)
            self.mg_aid = aid
            self.mode = "minigame"
        else:
            super().start_mini(aid)

    def finish_minigame(self):
        game = self.mgame
        game.settle()
        self.sfx.play("ok")
        self.mgame = None
        self.mode = "scene"
        self.g.check_death()
        self.post()

    # ---------- обновление и ввод ----------
    def update(self, dt):
        super().update(dt)
        if self.mode == "minigame" and self.mgame:
            self.mgame.update(dt)

    def on_key(self, e):
        if self.mode == "minigame" and self.mgame and not self.modal:
            name = _keynames().get(e.key)
            if name:
                self.mgame.key(name)
            return
        super().on_key(e)

    def on_click(self, pos):
        self.sfx.play("click")
        super().on_click(pos)

    def post(self):
        evs = list(self.g.events)
        super().post()
        for e, _ in evs:
            if e in ("ending", "fight_end"):
                self.sfx.play("win")
            elif e == "death":
                self.sfx.play("bad")
            elif e == "radio":
                self.sfx.play("day")

    # ---------- отрисовка ----------
    def draw(self):
        super().draw()
        if self.mode == "minigame" and self.mgame and not self.modal:
            self.draw_minigame()

    def draw_minigame(self):
        m = self.mgame
        self.veil(215)
        cx = self.W // 2
        self.text(m.title, cx, self.s(40), 54, GOLD, True, True)
        if m.done:
            self.text(m.result, cx, self.s(300), 32, WHITE, False, True, maxw=self.s(1300))
            self.button((cx - self.s(220), self.s(560), self.s(440), self.s(80)), "Продолжить", self.finish_minigame, 30)
            return
        getattr(self, "_draw_" + m.kind)(m, cx)

    def _draw_porridge(self, m, cx):
        self.text("Найдите 5 вещей, которых в гречку не клали. Число — сколько вещей в соседних клетках. Кликов: %d · найдено: %d/5" % (m.clicks, m.found), cx, self.s(130), 26, WHITE, False, True, maxw=self.s(1400))
        n, size = m.N, self.s(110)
        x0, y0 = cx - n * size // 2, self.s(220)
        for i in range(n * n):
            x, y = x0 + (i % n) * size, y0 + (i // n) * size
            if i in m.opened:
                label = "✔" if i in m.pos else (str(m.count(i)) if m.count(i) else "·")
                self.button((x, y, size - 6, size - 6), label, None, 34, False)
            else:
                self.button((x, y, size - 6, size - 6), "🌾", (lambda i=i: m.open(i)), 34)

    def _draw_poker(self, m, cx):
        self.text("Ваша карта: %d.  Карта соперника скрыта." % m.my, cx, self.s(160), 44, WHITE, True, True)
        opts = ["Играть честно (ставка 2🚬)", "Блеф: поднять до 5🚬", "Подставная карта (риск попасться)", "Сбросить (-1🚬)"]
        for i, t in enumerate(opts):
            self.button((cx - self.s(420), self.s(260 + 100 * i), self.s(840), self.s(84)), t, (lambda i=i: m.act(i)), 28)

    def _draw_chess(self, m, cx):
        self.text("Раунд %d/3 · счёт %d:%d" % (min(m.r + 1, 3), m.w, m.l), cx, self.s(150), 40, WHITE, True, True)
        self.text(m.last, cx, self.s(220), 28, (230, 220, 180), False, True, maxw=self.s(1300))
        for i, t in enumerate(m.MOVES):
            self.button((cx - self.s(420), self.s(340 + 100 * i), self.s(840), self.s(84)), t, (lambda i=i: m.play(i)), 30)

    def _draw_tunnel(self, m, cx):
        self.text("Дойдите до двери справа. Ложка: %d · Шум: %d · подкопов: %d/6 (стрелки или кнопки)" % (m.spoon, m.noise, self.g.s["dig"]), cx, self.s(130), 26, WHITE, False, True, maxw=self.s(1400))
        size = self.s(100)
        x0, y0 = cx - m.W * size // 2, self.s(220)
        for j in range(m.H):
            for i in range(m.W):
                c = m.grid[j][i]
                col = (30, 30, 36) if c == 0 else (96, 70, 44) if c == 1 else (90, 90, 96)
                pygame.draw.rect(self.screen, col, (x0 + i * size, y0 + j * size, size - 4, size - 4), border_radius=self.s(8))
        pygame.draw.rect(self.screen, GOLD, (x0 + m.x * size, y0 + m.y * size, size - 4, size - 4), self.s(5), border_radius=self.s(8))
        self.text("🚪", x0 + (m.W - 1) * size + self.s(20), y0 + 2 * size + self.s(10), 40)
        by = y0 + m.H * size + self.s(20)
        for t, dx, dy, ox in (("◀", -1, 0, -1), ("▲", 0, -1, 0), ("▼", 0, 1, 1), ("▶", 1, 0, 2)):
            self.button((cx + ox * self.s(110) - self.s(100), by, self.s(100), self.s(80)), t, (lambda dx=dx, dy=dy: m.move(dx, dy)), 36)

    def _draw_dance(self, m, cx):
        self.text("Нажмите нужную стрелку за секунду. Видны только пар и силуэты. Очки: %d/%d" % (m.sc, m.N), cx, self.s(130), 28, WHITE, False, True, maxw=self.s(1400))
        self.text("☁ 🕺 ☁ 💃 ☁ 🕺 ☁", cx, self.s(210), 60, GREY, False, True)
        self.text(mgm.ARROWS[m.cur] if m.cur >= 0 else "?", cx, self.s(330), 200, GOLD, True, True)
        self.text(m.fb, cx, self.s(560), 40, WHITE, True, True)
        pygame.draw.rect(self.screen, (40, 140, 60), (cx - self.s(300), self.s(620), int(self.s(600) * max(0.0, 1 - m.t / m.WINDOW)), self.s(16)), border_radius=8)
        for i, a in enumerate(mgm.ARROWS):
            self.button((cx - self.s(260) + i * self.s(135), self.s(670), self.s(120), self.s(100)), a, (lambda i=i: m.press(i)), 44)

    def _draw_factory(self, m, cx):
        if m.stage == 0:
            self.text("Про кого запустить слух?", cx, self.s(160), 40, WHITE, True, True)
            for i, t in enumerate(m.TARGETS):
                self.button((cx - self.s(420), self.s(250 + 96 * i), self.s(840), self.s(80)), t, (lambda i=i: m.pick_target(i)), 30)
        else:
            self.text("%s... что?" % m.target, cx, self.s(160), 40, WHITE, True, True)
            for j, t in enumerate(m.TEMPLATES):
                self.button((cx - self.s(420), self.s(250 + 96 * j), self.s(840), self.s(80)), t, (lambda j=j: m.pick_template(j)), 30)
