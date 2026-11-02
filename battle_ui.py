import tkinter as tk
import random
import time

BG = '#101720'
FG = '#e6edf4'
GOLD = '#e5b767'


def bar(c, value, maximum, color, label):
    c.delete('all')
    w = max(80, c.winfo_width())
    h = max(18, c.winfo_height())
    v = max(0, min(1, value / max(1, maximum)))
    c.create_rectangle(0, 0, w, h, fill='#090f17', outline='')
    c.create_rectangle(0, 0, w * v, h, fill=color, outline='')
    c.create_text(w / 2, h / 2, text=label, fill='white', font=('Segoe UI', 10, 'bold'))


class BattleWindow:
    """Дуэль: ручной ход, автобой и пауза. Таймер внизу, как в тактических RPG."""

    def __init__(self, app, k, ambush=False):
        from world import Duel
        self.a = app
        self.k = k
        self.b = Duel(app.world, k, ambush)
        app.battle = self.b
        self.closed = False
        self.timer = None
        self.auto = False
        self.rng = random.Random()
        self.interval = 1.2
        self.next_at = time.monotonic()
        boss = ' · БОСС' if getattr(self.b, 'is_boss', False) else ''
        self.w = app.window('Дуэль · ' + app.npcs[k]['name'] + boss, 980, 760)
        self.w.transient(app.root)
        self.w.grab_set()
        self.w.protocol('WM_DELETE_WINDOW', self.close)
        self.title = app.label(self.w, '', 16, True, color=GOLD)
        self.title.pack(pady=(12, 6))
        row = tk.Frame(self.w, bg=BG)
        row.pack(fill='x', padx=18)
        self.hp = tk.Canvas(row, height=26, highlightthickness=0)
        self.hp.pack(side='left', fill='x', expand=True, padx=4)
        self.foe = tk.Canvas(row, height=26, highlightthickness=0)
        self.foe.pack(side='right', fill='x', expand=True, padx=4)
        self.sp = tk.Canvas(self.w, height=22, highlightthickness=0)
        self.sp.pack(fill='x', padx=22, pady=6)
        self.aim = tk.IntVar(value=1)
        self.move = tk.IntVar(value=1)
        self.stance = tk.StringVar(value='attack')
        self.policy = tk.StringVar(value='balanced')
        for name, var, opts in [
                ('Куда атаковать', self.aim, [(0, 'Влево'), (1, 'В центр'), (2, 'Вправо')]),
                ('Ваше смещение', self.move, [(0, 'Влево'), (1, 'На месте'), (2, 'Вправо')]),
                ('Стойка', self.stance, [('attack', 'Атака'), ('guard', 'Защита / отдышаться'), ('aim', 'Прицел')]),
                ('Автобой', self.policy, [('balanced', 'Баланс'), ('aggressive', 'Агрессивно'), ('defensive', 'Осторожно')])]:
            f = tk.LabelFrame(self.w, text=name, bg=BG, fg=FG)
            f.pack(fill='x', padx=20, pady=3)
            for v, t in opts:
                tk.Radiobutton(f, text=t, value=v, variable=var, bg=BG, fg=FG, selectcolor='#243449',
                               activebackground=BG, activeforeground=FG).pack(side='left', padx=18, pady=3)
        self.log = tk.Text(self.w, height=9, wrap='word', bg='#0b1119', fg=FG, relief='flat',
                           font=('Segoe UI', 11))
        self.log.pack(fill='both', expand=True, padx=20, pady=6)
        row = tk.Frame(self.w, bg=BG)
        row.pack(fill='x', padx=20)
        self.manual = app.button(row, 'Сделать ход', self.manual_turn, True)
        self.manual.pack(side='left', fill='x', expand=True, padx=3)
        self.autob = app.button(row, 'Включить автобой', self.toggle)
        self.autob.pack(side='left', fill='x', expand=True, padx=3)
        self.exitb = app.button(row, 'Отступить', self.close)
        self.exitb.pack(side='left', fill='x', expand=True, padx=3)
        self.progress = tk.Canvas(self.w, height=25, highlightthickness=0)
        self.progress.pack(fill='x', padx=22, pady=10)
        self.draw()
        self.tick()

    def toggle(self):
        if self.b.done:
            return
        self.auto = not self.auto
        self.autob.config(text='Пауза автобоя' if self.auto else 'Включить автобой')
        self.next_at = time.monotonic() + self.interval

    def turn(self, aim, move, stance):
        if self.b.done:
            return
        self.b.strike(aim, move, stance)
        self.a.sound.play('hit')
        self.next_at = time.monotonic() + self.interval
        self.a.persist()
        self.draw()

    def manual_turn(self):
        if not self.auto and time.monotonic() >= self.next_at:
            self.turn(self.aim.get(), self.move.get(), self.stance.get())

    def auto_turn(self):
        sp = self.a.world.s['stamina']
        p = self.policy.get()
        stance = ('guard' if sp < 22 or (p == 'defensive' and self.b.hp < 55)
                  else 'attack' if p == 'aggressive' else self.rng.choice(['aim', 'attack', 'guard']))
        self.turn(self.rng.randrange(3), self.rng.randrange(3), stance)

    def tick(self):
        if self.closed:
            return
        now = time.monotonic()
        if self.auto and not self.b.done and now >= self.next_at:
            self.auto_turn()
        v = max(0, min(1, 1 - (self.next_at - now) / self.interval))
        bar(self.progress, v, 1, '#426f94',
            'Бой завершён' if self.b.done else 'До следующего раунда' if self.auto
            else 'Ход готов' if v >= 1 else 'Подготовка хода')
        self.manual.config(state='disabled' if self.auto or self.b.done or v < 1 else 'normal')
        self.timer = self.w.after(70, self.tick)

    def draw(self):
        b = self.b
        s = self.a.world.s
        self.title.config(text='%s · %s · раунд %d' % (s['gear']['weapon'], self.a.npcs[self.k]['name'], b.round))
        bar(self.hp, b.hp, s['hp_max'], '#b14c54', 'Вы %d/%d HP' % (b.hp, s['hp_max']))
        bar(self.foe, b.enemy, b.max_enemy, '#b14c54', 'Враг %d/%d HP' % (b.enemy, b.max_enemy))
        bar(self.sp, s['stamina'], s['stamina_max'], '#aa8747', 'Силы %d/%d' % (s['stamina'], s['stamina_max']))
        self.log.config(state='normal')
        self.log.delete('1.0', 'end')
        self.log.insert('1.0', '\n'.join(b.log[-40:]))
        self.log.config(state='disabled')
        self.log.see('end')
        if b.done:
            self.auto = False
            self.autob.config(state='disabled')
            self.exitb.config(text='Завершить · ' + b.result)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.timer:
            try:
                self.w.after_cancel(self.timer)
            except tk.TclError:
                pass
        self.b.finish()
        self.a.battle = None
        self.a.persist()
        self.a.after_time([])
        self.a.refresh()
        try:
            self.w.grab_release()
        except tk.TclError:
            pass
        self.w.destroy()
