import tkinter as tk
import random

from data import ITEMS

BG = '#101720'
CARD = '#182331'
FG = '#e6edf4'
MUTED = '#8799ac'
GOLD = '#e5b767'
RED = '#c45867'
GREEN = '#82b080'


class Mini:
    """Всплывающая мини-игра. Окно модальное: без реакции не закроешь.

    kind: porridge, chow, pushups, poker, chess, tunnel, dance, factory.
    """

    def __init__(self, app, kind, on_done=None):
        self.a = app
        self.kind = kind
        self.r = app.world.rng
        self.done = False
        self.reward = []
        self.timer = None
        self.round = 0
        self.sc = 0
        self.closed = False
        self.on_done = on_done
        self.boost = 0
        # сигареты и выносливость повышают шансы
        self.boost = min(3, app.world.inv('cig') // 4) + (1 if app.world.s['stamina'] > 60 else 0)
        self.w = app.window('Мини-игра', 760, 700)
        self.w.transient(app.root)
        self.w.grab_set()
        self.w.protocol('WM_DELETE_WINDOW', self.close)
        self.title = {'porridge': 'Сапёр в каше', 'chow': 'Кормёжка', 'pushups': 'Подходы',
                      'poker': 'Покер на одной карте', 'chess': 'Шахматы Лема',
                      'tunnel': 'Подкоп', 'dance': 'Танцы на стрелках',
                      'factory': 'Фейк-завод'}.get(kind, 'Мини-игра')
        self.a.label(self.w, self.title.upper(), 18, True, color=GOLD).pack(pady=(16, 4))
        self.info = app.label(self.w, '', 11, color=FG, wraplength=700, justify='left')
        self.info.pack(pady=6, padx=16, fill='x')
        self.body = tk.Frame(self.w, bg=BG)
        self.body.pack(fill='both', expand=True, padx=16, pady=8)
        self.note = app.label(self.w, '', 9, color=MUTED)
        self.note.pack(pady=(0, 10))
        getattr(self, 'start_' + kind)()

    # ------------------------------------------------------------- сервис
    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def btn(self, text, fn, primary=False):
        b = self.a.button(self.body, text, fn, primary=primary)
        b.pack(fill='x', pady=4)
        return b

    def finish(self, text, reward=(), note=None):
        if self.done:
            return
        self.done = True
        self.reward = list(reward)
        if self.timer:
            try:
                self.w.after_cancel(self.timer)
            except tk.TclError:
                pass
            self.timer = None
        self.clear()
        self.info.config(text=text, fg=GOLD)
        if note:
            self.note.config(text=note)
        self.btn('Принять результат', self.close, True)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.timer:
            try:
                self.w.after_cancel(self.timer)
            except tk.TclError:
                pass
        world = self.a.world
        for entry in self.reward:
            kind, value = entry[0], entry[1]
            item = entry[2] if len(entry) > 2 else None
            if kind == 'rub':
                world.s['rub'] = max(0, world.s['rub'] + value)
            elif kind == 'item':
                world.add(item, value)
            elif kind in ('hp', 'stamina', 'food'):
                limits = {'hp': (1, world.s['hp_max']), 'stamina': (0, world.s['stamina_max']),
                          'food': (0, 100)}
                lo, hi = limits[kind]
                world.s[kind] = max(lo, min(hi, world.s[kind] + value))
            elif kind == 'dig':
                world.s['flags']['dig'] = world.s['flags'].get('dig', 0) + value
            elif kind == 'respect':
                if value > 0:
                    world.rise(value, 'мини-игра')
                else:
                    world.s['respect'] = max(0, world.s['respect'] + value)
        if self.done:
            world.event('minigame_result', 'Мини-игра: ' + self.title + '.', world.witnesses())
        self.a.mini = None
        try:
            self.w.grab_release()
        except tk.TclError:
            pass
        self.w.destroy()
        if self.on_done:
            try:
                self.on_done(self)
            except Exception:
                pass
        self.a.persist()
        self.a.after_time([])
        self.a.refresh()

    # ------------------------------------------------------------- сапёр в каше
    def start_porridge(self):
        self.pos = set(self.r.sample(range(36), 5))
        self.opened = set()
        self.left = 16
        self.buttons = {}
        self.info.config(text='В баланде пять предметов, которые туда не клали. '
                              'Цифра — сколько предметов в соседних клетках. Открытий: 16.')
        f = tk.Frame(self.body, bg=BG)
        f.pack()
        for i in range(36):
            b = tk.Button(f, text='?', width=5, height=2, bg='#243449', fg='white',
                          relief='flat', font=('Segoe UI', 11, 'bold'),
                          command=lambda i=i: self.porr(i))
            b.grid(row=i // 6, column=i % 6, padx=2, pady=2)
            self.buttons[i] = b
        self.note.config(text='Бонус за сигареты: +%d к награде' % self.boost)

    def porr(self, i):
        if self.done or i in self.opened:
            return
        self.opened.add(i)
        self.left -= 1
        x, y = i % 6, i // 6
        if i in self.pos:
            self.sc += 1
            text = '✔'
            self.buttons[i].config(bg='#3c5a3f')
        else:
            near = sum(abs(j % 6 - x) <= 1 and abs(j // 6 - y) <= 1 for j in self.pos)
            text = str(near) if near else '·'
        self.buttons[i].config(text=text, state='disabled')
        self.info.config(text='Найдено %d/5, открытий осталось %d.' % (self.sc, self.left))
        if self.sc == 5:
            self.finish('Все предметы найдены. Каша подозрительно чистая.',
                        [('item', self.left + 3 + self.boost, 'cig')])
        elif self.left == 0:
            self.finish('Открытия закончились. Кто-то из каши уже поел.',
                        [('item', max(1, self.sc), 'cig')])

    # ------------------------------------------------------------- кормёжка
    def start_chow(self):
        self.target = 5
        self.zone = (40, 60)
        self.pos = 0
        self.dir = 1
        self.speed = 6
        self.info.config(text='Кормёжка — это спорт. Жми «Ложка!», когда ползунок в зелёной зоне. '
                              'Пять подходов, иначе баланда достанется соседу.')
        self.bar = tk.Canvas(self.body, height=44, bg='#0b1119', highlightthickness=0)
        self.bar.pack(fill='x', pady=12)
        self.label_round = self.a.label(self.body, '', 12, True, color=FG)
        self.label_round.pack(pady=6)
        self.btn('ЛОЖКА!', self.chow_click, True)
        self.anim()

    def anim(self):
        if self.done or self.closed:
            return
        self.pos += self.speed * self.dir
        if self.pos > 100:
            self.pos = 100
            self.dir = -1
        if self.pos < 0:
            self.pos = 0
            self.dir = 1
        self.bar.delete('all')
        w = max(100, self.bar.winfo_width())
        self.bar.create_rectangle(0, 12, w, 34, fill='#1b2734', outline='')
        self.bar.create_rectangle(w * self.zone[0] / 100, 12, w * self.zone[1] / 100, 34,
                                  fill='#2f4a34', outline=GREEN)
        self.bar.create_rectangle(w * self.pos / 100 - 3, 6, w * self.pos / 100 + 3, 40, fill=GOLD, outline='')
        self.label_round.config(text='Подход %d из %d · попаданий %d · бонус +%d'
                                     % (min(self.round + 1, self.target), self.target, self.sc, self.boost))
        self.timer = self.w.after(40, self.anim)

    def chow_click(self):
        if self.done:
            return
        hit = self.zone[0] <= self.pos <= self.zone[1]
        self.sc += 1 if hit else 0
        self.round += 1
        self.zone = (self.zone[0] + 6 - self.boost, self.zone[1] - 4 + self.boost)
        self.zone = (max(5, self.zone[0]), min(95, self.zone[1]))
        self.speed += 1
        if self.round >= self.target:
            good = self.sc + self.boost
            if good >= 4:
                self.finish('Ты съел всё и добавку. Сергеич сделал вид, что не заметил.',
                            [('food', 20), ('stamina', 10), ('respect', 1)])
            elif good >= 2:
                self.finish('Поел нормально. Ложку не отобрали.', [('food', 12), ('stamina', 5)])
            else:
                self.finish('Баланда ушла соседу. Ты остался с пустой ложкой.',
                            [('food', 4), ('stamina', -4)])

    # ------------------------------------------------------------- подходы
    def start_pushups(self):
        self.info.config(text='Гиря смотрит. Жми «ЖАТЬ!», когда ползунок силы в зелёной зоне. '
                              'Восемь подходов, иначе позор на всю тренажёрку.')
        self.target = 8
        self.zone = (45, 65)
        self.pos = 0
        self.dir = 1
        self.speed = 9
        self.bar = tk.Canvas(self.body, height=44, bg='#0b1119', highlightthickness=0)
        self.bar.pack(fill='x', pady=12)
        self.label_round = self.a.label(self.body, '', 12, True)
        self.label_round.pack(pady=6)
        self.btn('ЖАТЬ!', self.push_click, True)
        self.anim_push()

    def anim_push(self):
        if self.done or self.closed:
            return
        self.pos += self.speed * self.dir
        if self.pos > 100:
            self.pos, self.dir = 100, -1
        if self.pos < 0:
            self.pos, self.dir = 0, 1
        self.bar.delete('all')
        w = max(100, self.bar.winfo_width())
        self.bar.create_rectangle(0, 12, w, 34, fill='#1b2734', outline='')
        self.bar.create_rectangle(w * self.zone[0] / 100, 12, w * self.zone[1] / 100, 34,
                                  fill='#2f4a34', outline=GREEN)
        self.bar.create_rectangle(w * self.pos / 100 - 3, 6, w * self.pos / 100 + 3, 40, fill=GOLD, outline='')
        self.label_round.config(text='Подход %d/%d · чисто %d · бонус +%d'
                                     % (min(self.round + 1, self.target), self.target, self.sc, self.boost))
        self.timer = self.w.after(40, self.anim_push)

    def push_click(self):
        if self.done:
            return
        hit = self.zone[0] <= self.pos <= self.zone[1]
        self.sc += 1 if hit else 0
        self.round += 1
        self.zone = (max(5, self.zone[0] + 5 - self.boost), min(95, self.zone[1] - 5 + self.boost))
        self.speed += 2
        if self.round >= self.target:
            good = self.sc + self.boost
            if good >= 7:
                self.finish('Гиря кивнул: «Нормально». Это высшая похвала.',
                            [('respect', 4), ('stamina', -10)])
            elif good >= 4:
                self.finish('Подходы сделаны. Руки дрожат, но держат.', [('respect', 1), ('hp', -4)])
            else:
                self.finish('Штанга победила. Гиря молчит — это хуже слов.', [('hp', -10), ('stamina', -10)])

    # ------------------------------------------------------------- покер
    def start_poker(self):
        self.my = self.r.randint(1, 13)
        self.enemy = self.r.randint(1, 13)
        self.info.config(text='Покер на одной карте. У тебя %d, карта соперника скрыта. '
                              'Блеф — это тоже сила (бонус +%d).' % (self.my, self.boost))
        for t, i in [('Честно · 2 сиг.', 0), ('Блеф · 5 сиг.', 1),
                     ('Подмена карты · риск', 2), ('Сброс · -1 сиг.', 3)]:
            self.btn(t, lambda i=i: self.poker(i))

    def poker(self, i):
        if self.done:
            return
        if i == 3:
            return self.finish('Сброс. Умение вовремя уйти — тоже выигрыш.',
                               [('item', -1, 'cig')])
        if i == 2:
            if self.r.random() < 0.35 + 0.08 * self.boost:
                return self.finish('Подмену заметили. Позор и минус сигареты.',
                                   [('item', -4, 'cig'), ('respect', -3)])
            self.my = 13
        if i == 1:
            if self.r.random() < 0.3 + 0.1 * self.boost:
                return self.finish('Блеф удался. Граф хлопнул по столу и рассмеялся.',
                                   [('item', 2, 'cig'), ('respect', 1)])
        stake = 5 if i == 1 else 2
        value = stake if self.my >= self.enemy else -stake
        self.finish('Карта соперника: %d. Итог: %+d сигарет.' % (self.enemy, value),
                    [('item', value, 'cig')])

    # ------------------------------------------------------------- шахматы Лема
    def start_chess(self):
        self.lem = 0
        self.info.config(text='Шахматы Лема — абстрактная тактика: атака бьёт хитрость, '
                              'хитрость — защиту, защита — атаку. Три раунда.')
        for i, t in enumerate(['Атака', 'Защита', 'Хитрость']):
            self.btn(t, lambda i=i: self.chess(i))

    def chess(self, i):
        if self.done:
            return
        e = self.r.randrange(3)
        beats = {0: 2, 2: 1, 1: 0}
        win = beats[i] == e
        self.sc += 1 if win else 0
        self.round += 1
        self.info.config(text='Лем выбрал %s. Раунд %d, побед %d%s.'
                              % (['атаку', 'защиту', 'хитрость'][e], self.round, self.sc,
                                 ' · бонус +%d' % self.boost if self.boost else ''))
        if self.round >= 3:
            if self.sc + self.boost >= 2:
                self.finish('Лем записал результат и кивнул: «Ты играешь лучше, чем выглядишь».',
                            [('item', 4, 'cig'), ('respect', 2)])
            else:
                self.finish('Лем выиграл и вежливо промолчал. Это унизительно.',
                            [('item', 1, 'cig')])

    # ------------------------------------------------------------- подкоп
    def start_tunnel(self):
        self.W, self.H = 8, 5
        self.grid = [[2 if self.r.random() < 0.25 else 1 for _ in range(self.W)] for _ in range(self.H)]
        self.x, self.y = 0, 2
        self.spoon = 14 + self.boost * 2
        self.noise = 0
        self.info.config(text='Выход справа. Ложка тратится на твёрдый грунт, шум — на все подряд. '
                              'Шум 15+ — услышат.')
        for key, dx, dy in [('Up', 0, -1), ('Down', 0, 1), ('Left', -1, 0), ('Right', 1, 0)]:
            self.w.bind('<' + key + '>', lambda e, dx=dx, dy=dy: self.move(dx, dy))
        self.w.focus_set()
        self.tdraw()

    def tdraw(self):
        self.clear()
        self.a.label(self.body, 'Ложка %d · шум %d · готовых участков %d'
                     % (self.spoon, self.noise, self.a.world.s['flags'].get('dig', 0)),
                     11, bold=True).pack(pady=6)
        canvas = tk.Canvas(self.body, width=self.W * 64, height=self.H * 64, bg='#0b1119',
                           highlightthickness=0)
        canvas.pack(pady=8)
        for y in range(self.H):
            for x in range(self.W):
                c = self.grid[y][x]
                col = '#1d2229' if c == 0 else '#54402a' if c == 1 else '#4a4f56'
                canvas.create_rectangle(x * 64 + 2, y * 64 + 2, x * 64 + 62, y * 64 + 60,
                                        fill=col, outline='#2b333d')
        canvas.create_oval(self.x * 64 + 18, self.y * 64 + 16, self.x * 64 + 46, self.y * 64 + 44,
                           fill=GOLD, outline='')
        canvas.create_text((self.W - 1) * 64 + 32, 2 * 64 + 32, text='ВЫХОД', fill=GREEN,
                           font=('Segoe UI', 9, 'bold'))
        row = tk.Frame(self.body, bg=BG)
        row.pack(pady=6)
        for t, dx, dy in [('◀', -1, 0), ('▲', 0, -1), ('▼', 0, 1), ('▶', 1, 0)]:
            self.a.button(row, t, lambda dx=dx, dy=dy: self.move(dx, dy)).pack(side='left', padx=3)

    def move(self, dx, dy):
        if self.done:
            return
        x, y = self.x + dx, self.y + dy
        if not (0 <= x < self.W and 0 <= y < self.H):
            return
        cost = self.grid[y][x]
        if self.spoon < cost:
            return self.finish('Ложка сломалась. Смотритель скажет, что так и было задумано.',
                               [('stamina', -10)])
        self.spoon -= cost
        self.noise += cost
        self.grid[y][x] = 0
        self.x, self.y = x, y
        if x == self.W - 1:
            if self.noise >= 15:
                return self.finish('Шум услышали. Тоннель засыпали, тебя — в кичу.',
                                   [('hp', -10), ('respect', -4)])
            return self.finish('Участок готов. За стеной — воля, но пока только пахнет.',
                               [('dig', 1), ('stamina', -12)])
        self.tdraw()

    # ------------------------------------------------------------- танцы
    def start_dance(self):
        self.N = 10
        self.arrows = ['←', '↑', '↓', '→']
        self.info.config(text='Баня, пар и ритм. На каждый шаг — одна секунда. Бонус за сигареты: +%d.'
                         % self.boost)
        self.arrow_label = self.a.label(self.body, '', 64, True, color=GOLD)
        self.arrow_label.pack(pady=10)
        row = tk.Frame(self.body, bg=BG)
        row.pack()
        for i, t in enumerate(self.arrows):
            self.a.button(row, t, lambda i=i: self.dance(i)).pack(side='left', padx=4)
        for key, i in [('Left', 0), ('Up', 1), ('Down', 2), ('Right', 3)]:
            self.w.bind('<' + key + '>', lambda e, i=i: self.dance(i))
        self.w.focus_set()
        self.next_arrow()

    def next_arrow(self):
        if self.done:
            return
        if self.round >= self.N:
            good = self.sc + self.boost
            if good >= 7:
                return self.finish('Ты танцевал так, что Банный Философ прослезился.',
                                   [('item', 3, 'cig'), ('respect', 2)])
            return self.finish('Потанцевал. Пар скрыл всё, кроме результата.',
                               [('item', max(1, self.sc // 3), 'cig')])
        self.round += 1
        self.current = self.r.randrange(4)
        self.arrow_label.config(text=self.arrows[self.current])
        self.timer = self.w.after(1000, self.miss)

    def miss(self):
        self.timer = None
        self.next_arrow()

    def dance(self, i):
        if self.done:
            return
        if self.timer:
            try:
                self.w.after_cancel(self.timer)
            except tk.TclError:
                pass
            self.timer = None
        self.sc += 1 if i == self.current else 0
        self.next_arrow()

    # ------------------------------------------------------------- фейк-завод
    def start_factory(self):
        self.info.config(text='Про кого пустить слух? Слух станет слухом, а не фактом — как в жизни.')
        for k in ['gvo', 'zub', 'graf', 'buh', 'vertuha']:
            if k in self.a.npcs:
                self.btn(self.a.npcs[k]['name'], lambda k=k: self.target(k))

    def target(self, k):
        self.clear()
        self.k = k
        for t in ['воровал чай', 'боится крыс', 'тайно пишет стихи', 'просит справку о справке']:
            self.btn(t, lambda t=t: self.factory(t))

    def factory(self, t):
        if self.done:
            return
        w = self.a.world
        e = w.event('rumor_origin', 'Игрок сочинил слух о ' + self.a.npcs[self.k]['name'] + '.',
                    w.witnesses())
        for k in w.witnesses():
            w.gossip(k, k, 'Неподтверждённый слух: ' + self.a.npcs[self.k]['name'] + ' ' + t + '.',
                     e['id'], 45 + 5 * self.boost, 0, 'выдумка игрока', [])
        self.finish('Слух пущен. Он не факт, но уже живёт своей жизнью.',
                    [('rub', 5), ('respect', 1)])
