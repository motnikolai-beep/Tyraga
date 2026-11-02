# -*- coding: utf-8 -*-
"""Мини-игры (чистая логика, без pygame): сапёр в каше, покер, шахматы с Лемом, подкоп, танцы, фейк-завод.
Каждая игра: update(dt), key(имя), свои методы действий; по завершении done=True, результат применяет settle()."""

ARROWS = ["←", "↑", "↓", "→"]
KEYMAP = {"left": 0, "up": 1, "down": 2, "right": 3}


def num(key, n):
    return "%s%s%d" % (key, "+" if n >= 0 else "-", abs(n))


class MiniGame:
    title = ""
    kind = ""

    def __init__(self, g, cfg=None):
        self.g, self.cfg, self.rng = g, cfg or {}, g.rng
        self.done = False
        self.result = ""
        self.settled = False

    def update(self, dt):
        pass

    def key(self, name):
        pass

    def finish(self, text):
        self.done = True
        self.result = text

    def _settle(self):
        pass

    def settle(self):
        if not self.settled:
            self.settled = True
            self._settle()
            self.g.say(self.title + ": " + self.result)


class Porridge(MiniGame):
    title, kind = "Сапёр в каше", "porridge"
    N = 6
    ITEMS = ["гайка", "чей-то зуб", "ключ от кассы", "записка", "монета"]

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.pos = set()
        while len(self.pos) < 5:
            self.pos.add(self.rng.randrange(self.N * self.N))
        self.order = sorted(self.pos)
        self.opened, self.clicks, self.found, self.reward = set(), 16, 0, 0

    def count(self, i):
        x, y = i % self.N, i // self.N
        c = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                a, b = x + dx, y + dy
                if (dx or dy) and 0 <= a < self.N and 0 <= b < self.N and b * self.N + a in self.pos:
                    c += 1
        return c

    def open(self, i):
        if self.done or i in self.opened or self.clicks <= 0:
            return
        self.opened.add(i)
        self.clicks -= 1
        if i in self.pos:
            self.found += 1
            self.g.say("Найдено в каше: " + self.ITEMS[self.order.index(i)])
        if self.found >= 5:
            self.reward = self.clicks + 3
            self.finish("Все предметы найдены! +%d🚬" % self.reward)
        elif self.clicks <= 0:
            self.reward = self.found
            self.finish("Клики закончились. Найдено %d/5, +%d🚬" % (self.found, self.reward))

    def _settle(self):
        self.g.apply(num("cig", self.reward))


class Poker(MiniGame):
    title, kind = "Покер на сигаретах", "poker"

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.my, self.op = self.rng.randint(1, 13), self.rng.randint(1, 13)
        self.delta, self.rep = 0, 0

    def act(self, m):
        """0 — честно (ставка 2), 1 — блеф (ставка 5), 2 — подставная карта, 3 — сброс."""
        if self.done:
            return
        pre = ""
        if m == 3:
            self.delta = -1
            return self.finish("Вы сбросили. -1🚬.")
        if m == 2:
            if self.rng.random() < 0.4:
                self.delta, self.rep = -4, -10
                return self.finish("Вас поймали на подставной карте! -10 репутации, -4🚬.")
            self.my = 13
            pre = "Подставная карта прошла. "
        if m == 1 and self.rng.random() < max(0.1, min(0.7, (8 - self.op) / 14)):
            self.delta = 2
            return self.finish("Соперник испугался блефа и сбросил. +2🚬")
        st = 5 if m == 1 else 2
        if self.my >= self.op:
            self.delta = st
            self.finish("%sКарта соперника %d. Вы выиграли +%d🚬" % (pre, self.op, st))
        else:
            self.delta = -st
            self.finish("%sКарта соперника %d. Вы проиграли -%d🚬" % (pre, self.op, st))

    def _settle(self):
        self.g.apply(num("cig", self.delta))
        if self.rep:
            self.g.apply(num("rep", self.rep))


class LemChess(MiniGame):
    title, kind = "Шахматы с профессором Лемом", "chess"
    MOVES = ["Атака", "Защита", "Хитрость"]
    BEAT = {0: 2, 2: 1, 1: 0}

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.r = self.w = self.l = 0
        self.last = "Профессор играет по правилам 1950-х и считает вас шпионом."

    def play(self, i):
        if self.done:
            return
        lem = self.rng.randint(0, 2)
        m = "Лем выбрал «%s». " % self.MOVES[lem]
        if self.BEAT[i] == lem:
            self.w += 1
            m += "Вы выиграли раунд!"
        elif self.BEAT[lem] == i:
            self.l += 1
            m += "Профессор выиграл. «Шпион!»"
        else:
            m += "Ничья."
        self.r += 1
        self.last = m
        if self.r >= 3:
            self.finish(m + (" Профессор: «Допустим, вы не шпион». +1 знание, +3 репутации." if self.w > self.l else " Профессор подозревает вас всё сильнее."))

    def _settle(self):
        if self.w > self.l:
            self.g.apply(["know+1", "rep+3", "rumor:Профессор Лем:60-85"])
        else:
            self.g.apply("pred+1")


class Tunnel(MiniGame):
    title, kind = "Подкоп", "tunnel"
    W, H = 8, 5

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.grid = [[2 if self.rng.random() < 0.25 else 1 for _ in range(self.W)] for _ in range(self.H)]
        self.grid[2][0] = 1
        self.x, self.y, self.spoon, self.noise = 0, 2, 16, 0
        self.fx = []

    def move(self, dx, dy):
        if self.done:
            return
        nx, ny = self.x + dx, self.y + dy
        if not (0 <= nx < self.W and 0 <= ny < self.H):
            return
        c = self.grid[ny][nx]
        if self.spoon < c:
            return self.finish("Ложка сломалась. Подкоп остановлен.")
        self.spoon -= c
        self.noise += c
        self.grid[ny][nx] = 0
        self.x, self.y = nx, ny
        if nx == self.W - 1:
            if self.noise >= 15:
                self.fx = ["hp-10"]
                self.finish("Дошли, но шум услышал Сергеич. -10 ❤, подкоп засыпали.")
            else:
                self.fx = ["dig+1"]
                self.finish("Участок готов! Подкоп %d/6." % (self.g.s["dig"] + 1))

    def key(self, name):
        d = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.get(name)
        if d:
            self.move(*d)

    def _settle(self):
        self.g.apply(self.fx)
        if self.g.s["dig"] >= 6:
            self.g.events.append(("ending", "run"))


class Dance(MiniGame):
    title, kind = "Баня: танцевальный баттл", "dance"
    N, WINDOW = 12, 1.0

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.i = self.sc = 0
        self.cur, self.t, self.fb = -1, 0.0, ""
        self.next_arrow()

    def next_arrow(self):
        if self.i >= self.N:
            self.finish("Очков: %d/%d. Репутация +%d, сигареты +%d" % (self.sc, self.N, self.sc // 3, self.sc // 4))
            self.cur = -1
            return
        self.cur = self.rng.randint(0, 3)
        self.i += 1
        self.t = 0.0

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        if self.t >= self.WINDOW:
            self.fb = "Мимо"
            self.next_arrow()

    def press(self, j):
        if self.done or self.cur < 0:
            return
        if j == self.cur:
            self.sc += 1
            self.fb = "Есть!"
        else:
            self.fb = "Не туда"
        self.next_arrow()

    def key(self, name):
        if name in KEYMAP:
            self.press(KEYMAP[name])

    def _settle(self):
        self.g.apply([num("rep", self.sc // 3), num("cig", self.sc // 4)])


class FakeFactory(MiniGame):
    title, kind = "Фейк-завод", "factory"
    TARGETS = ["Зубило", "Сергеич", "Профессор Лем", "Гвоздев"]
    TEMPLATES = ["воровал чай", "боится крыс", "тайно пишет стихи", "ходит на исповедь с лопатой"]

    def __init__(self, g, cfg=None):
        super().__init__(g, cfg)
        self.stage, self.target, self.txt, self.fx = 0, None, "", []

    def pick_target(self, i):
        if self.stage == 0:
            self.target, self.stage = self.TARGETS[i], 1

    def pick_template(self, j):
        if self.stage != 1:
            return
        self.stage = 2
        pl = self.rng.randint(10, 60) + self.g.s["rep"] // 2
        self.txt = "%s %s" % (self.target, self.TEMPLATES[j])
        if pl >= 70:
            self.fx = ["rub+12", "rep+2"]
            self.finish("Слух «%s» разошёлся как масло (правдоподобие %d). +12₽, +2 репутации." % (self.txt, pl))
        elif pl >= 45:
            self.fx = ["rub+5"]
            self.finish("Слух «%s» разошёлся наполовину (%d). +5₽." % (self.txt, pl))
        else:
            self.fx = ["rep-3"]
            self.finish("«%s» — никто не поверил (%d). Вас назвали сочинителем. -3 репутации." % (self.txt, pl))

    def _settle(self):
        self.g.s["echo"] = self.txt
        self.g.apply(self.fx)


KINDS = {c.kind: c for c in (Porridge, Poker, LemChess, Tunnel, Dance, FakeFactory)}


def create(kind, g, cfg=None):
    return KINDS[kind](g, cfg)
