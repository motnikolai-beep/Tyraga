import tkinter as tk, json, queue, threading, uuid, copy, traceback, hashlib, re, time
from tkinter import ttk, messagebox
from pathlib import Path
from PIL import Image, ImageTk
from runtime_manager import Engine
from world import World, NAMES, save, hhmm
from data import ITEMS, JOBS, LOCATIONS, LOC_INDEX, MEALS, RECIPES
from story import Story, ENDINGS
from battle_ui import BattleWindow
from minigames import Mini
from sound import Sound
import ai

BASE = Path(__file__).resolve().parent
BG = '#090d12'; PANEL = '#101720'; CARD = '#182331'; FG = '#e6edf4'; MUTED = '#8799ac'; GOLD = '#e5b767'
RED = '#c45867'; GREEN = '#82b080'; BLUE = '#8fc5ec'

IDLE_MINUTES = 1        # сколько игровых минут идёт за тик
IDLE_TICK_MS = 3000     # длительность тика ожидания


def fmt_time(m):
    return hhmm(m)


class Card(tk.Frame):
    """Карточка действия: иконка, название, цена по времени."""

    def __init__(self, parent, app, title, subtitle, icon, command, disabled=False, note=''):
        super().__init__(parent, bg=CARD, highlightbackground='#2b3c50', highlightthickness=1)
        self.app = app
        self.command = command
        self.photo = None
        if icon:
            im = app.renderer.icon(icon, 44)
            if im is not None:
                self.photo = ImageTk.PhotoImage(im)
                tk.Label(self, image=self.photo, bg=CARD).grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=10)
        text = tk.Frame(self, bg=CARD)
        text.grid(row=0, column=1, sticky='w', padx=(0, 10), pady=(8, 2))
        tk.Label(text, text=title, bg=CARD, fg=GOLD if not disabled else MUTED,
                 font=('Segoe UI', 11, 'bold'), anchor='w').pack(anchor='w')
        tk.Label(text, text=subtitle, bg=CARD, fg=MUTED, font=('Segoe UI', 9),
                 anchor='w', justify='left', wraplength=330).pack(anchor='w')
        if note:
            tk.Label(self, text=note, bg=CARD, fg=BLUE, font=('Segoe UI', 9, 'bold')).grid(
                row=1, column=2, padx=(0, 10), sticky='e')
        self.columnconfigure(1, weight=1)
        if disabled:
            self.config(highlightbackground='#1d2836')
        else:
            for w in (self, text) + tuple(text.winfo_children()):
                w.bind('<Button-1>', lambda e: self.command())
                w.bind('<Enter>', lambda e: self._hover(True))
                w.bind('<Leave>', lambda e: self._hover(False))
        self.grid_propagate(False)

    def _hover(self, on):
        col = '#24364a' if on else CARD
        self.config(bg=col)
        for w in self.winfo_children():
            if isinstance(w, tk.Frame):
                w.config(bg=col)
                for c in w.winfo_children():
                    c.config(bg=col)


class App:
    def __init__(self, root):
        self.root = root
        root.title('Тюряга · Свои люди v8')
        root.geometry('1500x940')
        root.minsize(1180, 780)
        root.configure(bg=BG)
        self.npcs = json.loads((BASE / 'npcs.json').read_text(encoding='utf8'))
        self.path = BASE / 'saves/town_v4.json'
        state = None
        if self.path.exists():
            try:
                state = json.loads(self.path.read_text(encoding='utf8'))
            except Exception as e:
                messagebox.showwarning('Сохранение', str(e))
        self.world = World(self.npcs, state)
        self.story = Story(self.world)
        self.engine = Engine(BASE)
        self.sound = Sound(BASE)
        self.q = queue.Queue()
        self.liveq = queue.Queue()
        self.job = None
        self.cancel_event = None
        self.connected = False
        self.closed = False
        self.npc = None
        self.hover = None
        self.hits = []
        self.map_hits = []
        self.battle = None
        self.battle_window = None
        self.mini = None
        self.stream_text = {}
        self.draft_speech = {}
        self.last_click = 0
        self.paused = False
        from render import SceneRenderer
        self.renderer = SceneRenderer(self.npcs)
        self.scene_photo = None
        self.map_photo = None
        self.pending_scene = None
        self.story_window = None
        self.build()
        self.select_default()
        self.story.enter()
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        for key, cmd in [('<Control-s>', self.persist), ('<F2>', self.show_history),
                         ('<Key-m>', self.open_map), ('<Key-q>', self.open_story),
                         ('<Key-i>', self.open_inventory), ('<Key-j>', self.open_journal),
                         ('<Key-a>', self.open_actions), ('<Escape>', self.close_overlays)]:
            root.bind(key, lambda e, c=cmd: (c(), 'break')[1])
        root.after(120, self.poll)
        root.after(1000, self.tick)
        root.after(30000, self.autosave)
        self.connect()
        self.maybe_open_story_on_start()

    # ------------------------------------------------------------ построение
    def label(self, parent, text='', size=11, bold=False, color=None, **kw):
        return tk.Label(parent, text=text, bg=parent.cget('bg'), fg=color or FG,
                        font=('Segoe UI', size, 'bold' if bold else 'normal'), **kw)

    def button(self, parent, text, fn, primary=False, small=False):
        return tk.Button(parent, text=text, command=fn,
                         bg=GOLD if primary else CARD, fg='#111821' if primary else FG,
                         activebackground='#e9c88f' if primary else '#24364a',
                         activeforeground='#111821' if primary else FG,
                         relief='flat', bd=0, font=('Segoe UI', 10 if not small else 9,
                                                    'bold' if primary else 'normal'),
                         padx=12 if not small else 8, pady=8 if not small else 5, cursor='hand2')

    def window(self, title, w=900, h=650):
        p = tk.Toplevel(self.root)
        p.title(title)
        p.geometry('%dx%d' % (w, h))
        p.configure(bg=PANEL)
        p.transient(self.root)
        return p

    def build(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        # HUD
        head = tk.Frame(root, bg=BG)
        head.grid(row=0, column=0, sticky='ew', padx=14, pady=(8, 4))
        head.columnconfigure(1, weight=1)
        self.logo = self.label(head, 'ТЮРЯГА', 18, True, color=GOLD)
        self.logo.grid(row=0, column=0, padx=(0, 16))
        self.hud = self.label(head, size=10, color=MUTED)
        self.hud.grid(row=0, column=1, sticky='w')
        self.rank_label = self.label(head, size=10, bold=True, color=GOLD)
        self.rank_label.grid(row=0, column=2, padx=8)
        self.modebutton = self.button(head, 'Быстрый режим', self.toggle_mode, small=True)
        self.modebutton.grid(row=0, column=3, padx=3)
        self.pausebutton = self.button(head, '⏸ Время', self.toggle_pause, small=True)
        self.pausebutton.grid(row=0, column=4, padx=3)
        mb = tk.Menubutton(head, text='Система ▾', bg=CARD, fg=FG, relief='flat',
                           font=('Segoe UI', 10), padx=12, pady=6)
        menu = tk.Menu(mb, tearoff=0, bg=PANEL, fg=FG)
        for t, fn in [('Подключить ИИ', self.connect),
                      ('История разговора · F2', self.show_history),
                      ('Новый разговор с NPC', self.reset_chat),
                      ('Карта зоны · M', self.open_map),
                      ('Сюжет · Q', self.open_story),
                      ('Журналы мира', self.open_journal),
                      ('Иконки предметов', self.open_icons),
                      ('Настройки', lambda: self.text_window('Настройки', json.dumps(self.engine.cfg, ensure_ascii=False, indent=1))),
                      ('Лог сервера', lambda: self.text_window('llama-server', self.engine.tail()))]:
            menu.add_command(label=t, command=fn)
        mb.config(menu=menu)
        mb.grid(row=0, column=5, padx=3)

        # сцена
        self.canvas = tk.Canvas(root, bg='#070b10', highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky='nsew', padx=12)
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        self.canvas.bind('<Button-1>', self.on_click)
        self.canvas.bind('<Motion>', self.on_motion)

        # нижняя панель управления
        bar = tk.Frame(root, bg=BG)
        bar.grid(row=2, column=0, sticky='ew', padx=12, pady=(6, 10))
        bar.columnconfigure(1, weight=1)
        left = tk.Frame(bar, bg=BG)
        left.grid(row=0, column=0, sticky='w')
        self.actbutton = self.button(left, 'Действия · A', self.open_actions, small=True)
        self.actbutton.pack(side='left', padx=2)
        self.button(left, 'Сюжет · Q', self.open_story, small=True).pack(side='left', padx=2)
        self.button(left, 'Карта · M', self.open_map, small=True).pack(side='left', padx=2)
        self.button(left, 'Сумка · I', self.open_inventory, small=True).pack(side='left', padx=2)
        self.button(left, 'Журнал · J', self.open_journal, small=True).pack(side='left', padx=2)
        mid = tk.Frame(bar, bg=BG)
        mid.grid(row=0, column=1, sticky='ew', padx=10)
        mid.columnconfigure(1, weight=1)
        self.who = self.label(mid, 'Собеседник', 10, True)
        self.who.grid(row=0, column=0, sticky='w', padx=(0, 8))
        self.npcbox = ttk.Combobox(mid, state='readonly', width=18)
        self.npcbox.grid(row=0, column=2, rowspan=2, sticky='e', padx=(6, 0))
        self.npcbox.bind('<<ComboboxSelected>>', lambda e: self.pick_npc())
        self.entry = tk.Text(mid, height=2, wrap='word', bg=CARD, fg=FG, insertbackground=GOLD,
                             font=('Segoe UI', 12), relief='flat', padx=10, pady=8)
        self.entry.grid(row=0, column=1, rowspan=2, sticky='ew')
        self.entry.bind('<Return>', self.enter)
        self.entry.bind('<Shift-Return>', self.newline)
        self.private = tk.BooleanVar(value=False)
        self.privbox = tk.Checkbutton(bar, text='Наедине', variable=self.private, bg=BG, fg=MUTED,
                                      selectcolor=CARD, activebackground=BG, activeforeground=FG,
                                      font=('Segoe UI', 9))
        self.privbox.grid(row=0, column=2, padx=(0, 6))
        self.sendbutton = self.button(bar, 'СКАЗАТЬ ↵', self.send, True)
        self.sendbutton.grid(row=0, column=3, padx=2)
        self.status = self.label(bar, size=9, color=MUTED)
        self.status.grid(row=1, column=0, columnspan=4, sticky='w', pady=(4, 0))

    # ------------------------------------------------------------ утилиты
    def blocked(self):
        return bool(self.job or self.battle or self.mini)

    def overlay_open(self):
        for w in self.root.winfo_children():
            if isinstance(w, tk.Toplevel) and w.winfo_exists():
                return True
        return False

    def close_overlays(self):
        for w in list(self.root.winfo_children()):
            if isinstance(w, tk.Toplevel):
                try:
                    w.grab_release()
                except tk.TclError:
                    pass
                w.destroy()

    def persist(self):
        try:
            save(self.world.s, self.path)
        except Exception as e:
            messagebox.showerror('Сохранение', str(e))

    def autosave(self):
        if not self.closed:
            self.persist()
            self.root.after(30000, self.autosave)

    def close(self):
        self.closed = True
        if self.cancel_event:
            self.cancel_event.set()
        self.job = None
        if self.battle:
            self.battle.finish()
        self.persist()
        self.root.destroy()

    def toast(self, text, kind='info'):
        self.world.toast(text, kind)

    # ------------------------------------------------------------ время
    def toggle_pause(self):
        self.paused = not self.paused
        self.pausebutton.config(text='▶ Время' if self.paused else '⏸ Время',
                                bg=CARD if self.paused else '#5c4831')
        self.status.config(text='Время остановлено.' if self.paused else 'Время идёт.')

    def tick(self):
        if self.closed:
            return
        if not self.paused and not self.blocked() and not self.overlay_open():
            notes = self.world.advance(IDLE_MINUTES, '')
            if notes:
                self.after_time(notes)
        self.refresh_hud()
        self.redraw()
        self.root.after(IDLE_TICK_MS, self.tick)

    def after_time(self, notes=None):
        """Последствия течения времени: кормёжки, сюжет, смена локации NPC."""
        for n in notes or []:
            if n.get('kind') == 'meal':
                self.toast('Прошёл %s. Опоздал — значит, не голоден.' % n.get('meal', ''), 'bad')
            elif n.get('kind') == 'day':
                self.toast(n.get('text', 'Новый день'), 'day')
        self.sync_npc()
        self.check_story_trigger()
        self.persist()
        self.redraw()

    def sync_npc(self):
        present = self.world.witnesses()
        if present and (self.npc not in present):
            self.npc = present[0]

    # ------------------------------------------------------------ ИИ
    def launch(self, kind, fn, meta=None):
        if self.job:
            return False
        id = uuid.uuid4().hex
        cancel = threading.Event()
        self.cancel_event = cancel
        self.job = {'id': id, 'kind': kind, 'meta': meta}
        self.status.config(text={'start': 'Загрузка модели…', 'chat': 'NPC отвечает…',
                                 'initiative': 'NPC обдумывает свои дела…'}[kind])

        def worker():
            try:
                self.q.put((id, fn(id, cancel), None))
            except Exception as e:
                self.q.put((id, None, str(e)))
        threading.Thread(target=worker, daemon=True).start()
        return True

    def connect(self):
        if not self.blocked():
            self.launch('start', lambda id, cancel: self.engine.connect())

    def poll(self):
        if self.closed:
            return
        latest = {}
        try:
            while True:
                id, k, text = self.liveq.get_nowait()
                if self.job and id == self.job['id']:
                    latest[k] = text
        except queue.Empty:
            pass
        if latest:
            self.stream_text.update(latest)
            self.redraw()
        try:
            while True:
                id, result, error = self.q.get_nowait()
                if not self.job or id != self.job['id']:
                    continue
                job = self.job
                self.job = None
                self.stream_text.clear()
                self.draft_speech.clear()
                if error:
                    self.status.config(text='Ошибка: ' + error[:500])
                    if job['kind'] == 'start':
                        self.connected = False
                    continue
                if job['kind'] == 'start':
                    self.connected = True
                    self.status.config(text='ИИ готов. Говорите или действуйте.')
                elif job['kind'] == 'chat':
                    self.after_chat(job['meta'], result)
                else:
                    try:
                        self.world.initiative(job['meta']['npc'], result)
                        self.persist()
                        self.redraw()
                    except Exception as e:
                        self.status.config(text='Инициатива не применена: ' + str(e))
        except queue.Empty:
            pass
        self.sendbutton.config(state='disabled' if self.blocked() or not self.connected else 'normal')
        self.root.after(120, self.poll)

    def send(self):
        if self.blocked():
            return
        if not self.connected:
            self.status.config(text='ИИ не подключён. Сюжет и дела работают и без него.')
            return
        if not self.npc or self.npc not in self.world.witnesses():
            self.status.config(text='Рядом никого нет. Сначала перейди к людям.')
            return
        text = self.entry.get('1.0', 'end').strip()
        if not text:
            return
        if len(text) > int(self.engine.cfg['CHAT_MAX_INPUT_CHARS']):
            self.status.config(text='Слишком длинная реплика.')
            return
        k = self.npc
        private = self.private.get() or self.engine.cfg['GOSSIP_ENABLED'].lower() != 'true'
        snap = World(self.npcs, copy.deepcopy(self.world.s))
        self.draft_speech[k] = text
        self.stream_text[k] = '…'
        self.redraw()
        self.launch('chat', lambda id, cancel: ai.generate_chat(
            self.engine, snap, k, text, lambda partial: self.liveq.put((id, k, partial)), cancel),
            {'npc': k, 'text': text, 'private': private})

    def after_chat(self, meta, result):
        k = meta['npc']
        text = meta['text']
        ai.accept(self.world, k, text, result, meta['private'])
        self.entry.delete('1.0', 'end')
        # болтовня съедает время: чем длиннее реплика, тем больше минут
        spent = min(35, 3 + len(text) // 45 + len(result.get('reply', '')) // 60)
        self.world.advance(spent, 'разговор с ' + self.npcs[k]['name'])
        self.world.s['chat_npc'] = k
        self.world.s['chat_minutes'] = self.world.s.get('chat_minutes', 0) + spent
        talk_key = '%d:%s' % (self.world.s['day'], k)
        self.world.s['day_talk'][talk_key] = self.world.s['day_talk'].get(talk_key, 0) + 1
        self.sound.play('ok')
        self.status.config(text='Ответ получен. Разговор занял %d минут. История — F2.' % spent)
        self.persist()
        self.after_time([])
        self.chat_combat(meta, result)
        self.maybe_shmon_after_talk(k)

    def maybe_shmon_after_talk(self, k):
        if self.world.inv('phone') and self.world.rng.random() < 0.12:
            self.world.maybe_shmon('во время разговора')
            self.after_time([])

    def chat_combat(self, m, result):
        intent = result.get('_combat_intent')
        k = m['npc']
        if not intent or k not in self.world.witnesses() or self.battle or self.mini:
            return
        id = hashlib.sha256((str(self.world.s['day']) + k + m['text'] + result['reply']).encode()).hexdigest()
        tokens = self.world.s['chat_fight_tokens']
        if id in tokens:
            return
        tokens.append(id)
        self.world.s['chat_fight_tokens'] = tokens[-100:]
        self.world.event('chat_threat', ('Игрок угрожал ' + self.npcs[k]['name']
                                         if intent['speaker'] == 'player'
                                         else self.npcs[k]['name'] + ' угрожал игроку') + ': ' + intent['evidence'],
                         [k] if m['private'] else self.world.witnesses())
        self.persist()
        self.fight(k, False)

    def toggle_mode(self):
        if self.blocked():
            return self.status.config(text='Сначала завершите запрос или бой.')
        fast = self.engine.cfg['CHAT_FAST_MODE'].lower() != 'true'
        self.engine.cfg['CHAT_FAST_MODE'] = 'true' if fast else 'false'
        p = BASE / '.env'
        text = p.read_text(encoding='utf-8-sig') if p.exists() else ''
        key = 'CHAT_FAST_MODE=' + self.engine.cfg['CHAT_FAST_MODE']
        text = re.sub(r'^CHAT_FAST_MODE=.*$', key, text, flags=re.M) if re.search(r'^CHAT_FAST_MODE=', text, re.M) else text + '\n' + key
        try:
            p.write_text(text + '\n', encoding='utf8')
        except OSError:
            pass
        self.refresh_hud()
        self.status.config(text='Быстрый режим: один запрос на реплику.' if fast else 'Полный режим: оценки кармы/угроз.')

    # ------------------------------------------------------------ NPC / сцена
    def select_default(self):
        self.local_ids = self.world.witnesses()
        self.npc = self.local_ids[0] if self.local_ids else None
        if hasattr(self, 'npcbox'):
            self.npcbox.config(values=[self.npcs[k]['name'] for k in self.local_ids])
            if self.local_ids:
                self.npcbox.current(0)

    def pick_npc(self):
        if self.blocked():
            return
        i = self.npcbox.current()
        if 0 <= i < len(self.local_ids):
            self.select(self.local_ids[i])

    def select(self, k):
        if self.blocked() or k not in self.world.witnesses():
            return
        self.npc = k
        self.refresh()
        self.entry.focus_set()

    def on_motion(self, e):
        k = None
        for key, (x0, y0, x1, y1) in self.hits:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                k = key
                break
        if k != self.hover:
            self.hover = k
            self.canvas.config(cursor='hand2' if k else '')
            self.redraw()

    def on_click(self, e):
        now = time.monotonic()
        if now - self.last_click < 0.12:
            return
        self.last_click = now
        for key, (x0, y0, x1, y1) in self.hits:
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                if not self.blocked():
                    self.sound.play('click')
                    self.select(key)
                return
        # клик по панели диалога — полная реплика
        h = self.canvas.winfo_height()
        if e.y > h - 150:
            self.show_history()

    def redraw(self):
        if self.closed:
            return
        c = self.canvas
        w, h = c.winfo_width(), c.winfo_height()
        if w < 60 or h < 60:
            return
        scn = self.story.scene() if not self.story.finished() else None
        ready = self.story.at_ready()
        text, who = None, None
        if self.stream_text.get(self.npc):
            text = self.stream_text[self.npc]
            who = self.npcs[self.npc]['name']
        elif ready and scn and (scn.get('npc') == self.npc or scn.get('npc') is None):
            text = ' '.join(scn.get('text', [])[:2])
            who = scn.get('title')
        elif self.npc:
            hist = self.world.s['history'].get(self.npc, [])
            text = next((m['content'] for m in reversed(hist) if m['role'] == 'assistant'), '')
            who = self.npcs[self.npc]['name']
        ui = {'npc': self.npc, 'text': text, 'who': who,
              'hover': self.hover,
              'toasts': self.world.s['toasts'][-4:],
              'objective': self.world.s['story'].get('objective', ''),
              'story_ready': ready}
        img, hits = self.renderer.scene((w, h), self.world, ui)
        self.scene_photo = ImageTk.PhotoImage(img)
        c.delete('all')
        c.create_image(0, 0, anchor='nw', image=self.scene_photo)
        self.hits = hits
        # маркер сюжета
        if ready:
            c.create_rectangle(w - 190, h - 208, w - 16, h - 160, fill='#1b2a1f', outline=GREEN, width=2)
            c.create_text(w - 103, h - 184, text='СЮЖЕТ · Q', fill=GREEN, font=('Segoe UI', 11, 'bold'))

    def refresh_hud(self):
        s = self.world.s
        rank = self.world.rank()
        self.hud.config(text='%s · день %d · HP %d/%d · Силы %d · Еда %d · ₽%d · Сиг. %d'
                             % (self.world.clock(), s['day'], s['hp'], s['hp_max'], s['stamina'],
                                s['food'], s['rub'], self.world.inv('cig')))
        self.rank_label.config(text='%s · Уважение %d' % (rank['title'], s['respect']),
                               fg=RED if self.world.rank_key() in ('petukh', 'opush') else GOLD)

    def refresh(self):
        self.refresh_hud()
        present = self.world.witnesses()
        if self.npc not in present:
            self.npc = present[0] if present else None
        self.local_ids = present
        if hasattr(self, 'npcbox'):
            self.npcbox.config(values=[self.npcs[k]['name'] for k in present])
            if self.npc in present:
                self.npcbox.current(present.index(self.npc))
        if self.npc:
            self.who.config(text=self.npcs[self.npc]['name'])
        else:
            self.who.config(text='Рядом никого')
        self.modebutton.config(text='Быстро' if self.engine.cfg['CHAT_FAST_MODE'].lower() == 'true' else 'Полный')
        self.redraw()

    # ------------------------------------------------------------ сюжет
    def check_story_trigger(self):
        if self.story.finished():
            if self.pending_scene != 'ending':
                self.pending_scene = 'ending'
                self.status.config(text='История завершена. Q — финал.')
            return
        if self.story.at_ready():
            if self.pending_scene != self.story.s['scene']:
                self.pending_scene = self.story.s['scene']
                self.status.config(text='Новая сцена сюжета. Нажми Q.')
                self.toast('Сюжет: ' + (self.story.scene().get('title') or ''), 'story')

    def maybe_open_story_on_start(self):
        self.root.after(600, self.check_story_trigger)

    def open_story(self):
        if self.blocked():
            return
        if self.story.finished():
            return self.show_ending()
        scn = self.story.scene()
        if not scn:
            return
        wh = self.story.where()
        if wh is not None and LOC_INDEX[wh] != self.world.s['loc']:
            loc = LOCATIONS[LOC_INDEX[wh]]['name']
            return messagebox.showinfo('Сюжет', 'Эта сцена происходит в локации «%s». Иди туда.' % loc)
        if scn['id'] == 'first_night' and not self.world.is_night():
            return messagebox.showinfo('Сюжет', 'Сейчас %s. Лечь на шконку можно только ночью (после 21:00).\n'
                                                'Пока займись делами — время идёт само.' % self.world.clock())
        if scn['id'] == 'visit_mama' and self.world.s['visit'].get('used'):
            return messagebox.showinfo('Сюжет', 'Свиданка уже была сегодня.')
        self.story.enter()
        self.story_window = self.window('Сюжет · ' + (scn.get('title') or ''), 980, 760)
        self.story_window.grab_set()
        self.render_story_window(scn)

    def render_story_window(self, scn):
        w = self.story_window
        for c in w.winfo_children():
            c.destroy()
        self.label(w, 'АКТ %d · %s' % (scn.get('act', 1), scn.get('title', '').upper()),
                   13, True, color=GOLD).pack(anchor='w', padx=20, pady=(16, 4))
        if scn.get('objective'):
            self.label(w, 'Цель: ' + scn['objective'], 10, color=MUTED).pack(anchor='w', padx=20)
        box = tk.Frame(w, bg=PANEL)
        box.pack(fill='both', expand=True, padx=16, pady=10)
        txt = tk.Text(box, wrap='word', bg='#0b1119', fg=FG, relief='flat',
                      font=('Segoe UI', 12), padx=14, pady=12, height=10)
        sb = tk.Scrollbar(box, command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        txt.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        txt.insert('1.0', '\n\n'.join(scn.get('text', [])))
        txt.config(state='disabled')
        for i, ch in enumerate(self.story.available(scn)):
            check = ch.get('check')
            mark = ''
            if check:
                key, dc = check
                names = {'wis': 'Мудрость', 'cha': 'Харизма', 'cun': 'Хитрость',
                         'str': 'Сила', 'hon': 'Честность'}
                mark = '   [%s %d]' % (names.get(key, key), dc)
            b = tk.Button(w, text='%d. %s%s' % (i + 1, ch['text'], mark), anchor='w',
                          bg=CARD, fg=FG, activebackground='#24364a', relief='flat',
                          font=('Segoe UI', 11), padx=14, pady=10, cursor='hand2',
                          command=lambda i=i: self.choose_story(i))
            b.pack(fill='x', padx=16, pady=3)
        self.label(w, 'Проверки: %d успехов, %d провалов · шанс зависит от характеристик и касты'
                  % (self.story.s['checks']['ok'], self.story.s['checks']['fail']),
                   9, color=MUTED).pack(anchor='w', padx=20, pady=(6, 12))

    def choose_story(self, i):
        try:
            res = self.story.choose(i)
        except ValueError as e:
            return messagebox.showinfo('Сюжет', str(e))
        self.persist()
        self.refresh()
        msg = []
        if res.get('check'):
            msg.append(res['check'])
        if res.get('effects'):
            msg.append(' · '.join(res['effects']))
        if self.story.s.get('ending'):
            for c in self.story_window.winfo_children():
                c.destroy()
            self.story_window.destroy()
            self.show_ending()
            return
        self.render_story_window(self.story.scene())
        self.status.config(text=' | '.join(msg)[:900] if msg else '')

    def show_ending(self):
        e = self.story.ending_text() or {'title': 'Финал', 'body': 'История завершена.'}
        w = self.window('Финал · ' + e['title'], 760, 460)
        w.grab_set()
        self.label(w, 'ФИНАЛ: ' + e['title'].upper(), 20, True, color=GOLD).pack(pady=(24, 10))
        self.label(w, e['body'], 12, wraplength=680, justify='left').pack(padx=24, pady=10)
        rank = self.world.rank()['title']
        self.label(w, 'Итоговая каста: %s · уважение %d' % (rank, self.world.s['respect']),
                   11, color=BLUE).pack(pady=8)
        self.button(w, 'Закрыть', w.destroy, True).pack(pady=14)

    # ------------------------------------------------------------ действия
    def open_actions(self):
        if self.blocked():
            return
        w = self.window('Действия · ' + NAMES[self.world.s['loc']], 820, 760)
        w.grab_set()
        s = self.world.s
        head = tk.Frame(w, bg=PANEL)
        head.pack(fill='x', padx=16, pady=(14, 4))
        self.label(head, 'ДЕЛА', 15, True, color=GOLD).pack(side='left')
        self.label(head, 'сейчас %s · %s · дел не осталось — иди спать'
                   % (self.world.clock(), self.world.phase()), 10, color=MUTED).pack(side='left', padx=12)
        grid = tk.Frame(w, bg=PANEL)
        grid.pack(fill='both', expand=True, padx=12, pady=6)
        for col in range(2):
            grid.columnconfigure(col, weight=1, uniform='c')
        cards = []

        def add(title, subtitle, icon, fn, note='', allowed=True, why=''):
            cards.append((title, subtitle, icon, fn, note, allowed))

        loc = LOCATIONS[s['loc']]['key']
        add('Осмотреться', 'Оглядеться, найти мелочь или зацепку', 'magnifier',
            lambda: self.do_action('look'), '10 мин')
        add('Поискать схрон', 'Схроны, нычки и чужие секреты', 'rat',
            lambda: self.do_action('search'), '30 мин')
        add('Перекур', 'Сигарета, разговор, минута покоя', 'cig', lambda: self.do_action('smoke'), '5 мин')
        job = next((j for j in JOBS.values() if j['loc'] == s['loc']), None)
        if job:
            add('Работать', job['name'] + ' · +%d₽' % job['pay'], 'medal',
                lambda: self.do_action('work'), '%d мин' % job['time'])
        if loc == 'mess':
            meal, dish = self.world.meal_now()
            add('Поесть', (dish or 'сейчас не кормят') + ' · кормят 07:00, 12:00, 18:00', 'soup',
                lambda: self.do_action('eat'), '20 мин', bool(meal), 'время')
        if loc == 'gym':
            add('Тренажёрка', 'Тянуть железо и качать силу', 'barbell', lambda: self.do_action('train'), '60 мин')
            add('Помериться силой', 'Мини-игра: подходы', 'gloves', lambda: self.minigame('pushups'), '30 мин')
        if loc == 'temple':
            add('Помолиться', 'Господь всё слышит, карму чистит', 'candle', lambda: self.do_action('pray'), '20 мин')
            add('Поговорить с Господом', 'Признание, вопрос или благодарность', 'cross',
                self.talk_god, '15 мин')
        if loc == 'visit':
            add('Свиданка', 'Поговорить с матерью, взять передачку', 'ear',
                lambda: self.do_action('visit'), '60 мин', not s['visit'].get('used'))
        if loc == 'cam':
            add('Сварить чифирь', 'Из чая — напиток для взрослых', 'pot',
                lambda: self.do_action('cook'), '25 мин', self.world.has('tea'))
            add('Лечь на шконку', 'Только ночью, после 21:00', 'bunk',
                lambda: self.do_action('sleep'), 'до утра', self.world.can_sleep(),
                'только ночью' if not self.world.can_sleep() else '')
            add('Спрятать вещь в схрон', 'Убрать из сумки то, что ищет шмон', 'lock',
                lambda: self.open_stash(), '10 мин')
        if loc == 'cellar':
            add('Копать тоннель', 'Мини-игра «Подкоп» — шесть участков', 'bars',
                lambda: self.minigame('tunnel'), '30 мин')
        if loc == 'club':
            add('Покер', 'Одна карта, большой блеф', 'chess',
                lambda: self.minigame('poker'), '20 мин', self.world.inv('cig') >= 5)
            add('Шахматы Лема', 'Тактика на троих', 'chess', lambda: self.minigame('chess'), '20 мин')
        if loc == 'bath':
            add('Танцы на стрелках', 'Баня, пар и ритм', 'radio', lambda: self.minigame('dance'), '20 мин')
        if loc == 'mess':
            add('Сапёр в каше', 'Найти в баланде то, что не съедобно', 'soup',
                lambda: self.minigame('porridge'), '15 мин')
        if loc == 'laundry':
            add('Фейк-завод', 'Запустить слух о ком надо', 'radio',
                lambda: self.minigame('factory'), '20 мин')
        add('Встретиться с NPC', 'Решения: помочь, украсть, подставить, сдать', 'magnifier',
            self.decisions, '10 мин', bool(self.npc))
        add('Бросить вызов', 'Дуэль или босс-испытание', 'gloves',
            lambda: self.fight(None), '10 мин', bool(self.npc))
        add('Поговорить с NPC', 'Открыть диалог снизу', 'book',
            self.focus_entry, '', bool(self.npc))
        for i, (title, subtitle, icon, fn, note, allowed) in enumerate(cards):
            c = Card(grid, self, title, subtitle, icon, fn, disabled=not allowed, note=note)
            c.grid(row=i // 2, column=i % 2, sticky='nsew', padx=4, pady=4)
            c.config(height=74)
        self.button(w, 'Закрыть', w.destroy).pack(pady=8)

    def focus_entry(self):
        self.close_overlays()
        self.entry.focus_set()

    def do_action(self, kind):
        self.close_overlays()
        w = self.world
        try:
            if kind == 'look':
                w.advance(10, 'осмотрелся')
                spot = w.rng.choice(LOCATIONS[w.s['loc']]['spot'])
                txt = {
                    'look': 'Ты осмотрелся: %s. %s' % (spot, w.rng.choice([
                        'Ничего нового, но спокойнее.', 'Кто-то оставил след. Свежий.',
                        'Пахнет сыростью и чужими надеждами.', 'Всё как всегда. Значит, скоро что-то будет.']))
                }['look']
                if w.rng.random() < 0.25:
                    item = w.rng.choice(['cig', 'bread', 'tea', 'rub'])
                    if item == 'rub':
                        w.s['rub'] += w.rng.randint(2, 8)
                        txt += ' На полу — мелочь. Теперь твоя.'
                    else:
                        w.add(item, 1)
                        txt += ' Нашёл: %s.' % ITEMS[item]['name']
                    w.event('find', 'Игрок нашёл ' + ITEMS.get(item, {'name': 'мелочь'})['name'], w.witnesses())
                self.toast(txt)
            elif kind == 'search':
                w.search()
            elif kind == 'smoke':
                if self.npc and w.rng.random() < 0.5:
                    w.smoke(self.npc)
                else:
                    w.smoke()
            elif kind == 'work':
                w.work()
            elif kind == 'eat':
                self.meal_event()
                return
            elif kind == 'train':
                lvl = w.train()
                self.toast('Сила: %d. Урон растёт.' % lvl, 'good')
                if lvl % 3 == 0:
                    self.minigame('pushups')
                    return
            elif kind == 'pray':
                clean = w.pray()
                self.toast('Исповедь: ' + w.confess_line(), 'story')
                self.status.config(text='Карма очищена на %d.' % clean if clean else 'Господь молчит.')
            elif kind == 'visit':
                w.visit_start()
                self.open_story_force('visit_mama')
            elif kind == 'cook':
                self.cook_menu()
                return
            elif kind == 'sleep':
                self.sleep()
                return
        except ValueError as e:
            return self.status.config(text=str(e))
        self.persist()
        self.after_time([])
        self.refresh()

    def open_story_force(self, scene_id):
        self.story.s['scene'] = scene_id
        self.story.enter()
        if not self.story_window or not self.story_window.winfo_exists():
            scn = self.story.scene()
            self.story_window = self.window('Сюжет · ' + (scn.get('title') or ''), 980, 760)
            self.story_window.grab_set()
        self.render_story_window(self.story.scene())

    def talk_god(self):
        self.close_overlays()
        w = self.window('Храм · разговор', 720, 560)
        w.grab_set()
        self.label(w, 'ГОСПОДЬ ВСЁ СЛЫШИТ', 16, True, color=GOLD).pack(anchor='w', padx=18, pady=(16, 4))
        self.label(w, 'Свечи горят. Икона молчит так, что слышно собственные мысли.',
                   10, color=MUTED).pack(anchor='w', padx=18)
        out = self.label(w, '', 12, color=FG, wraplength=660, justify='left')
        out.pack(anchor='w', padx=18, pady=12, fill='x')

        def say(mode):
            try:
                r = self.world.talk_god(mode)
            except ValueError as e:
                return out.config(text=str(e))
            out.config(text=r['text'] + '\n\n' + r['god'])
            self.persist()
            self.after_time([])
            self.refresh()
        for t, mode in [('Признаться в плохом', 'confess'), ('Спросить: «За что?»', 'ask'),
                        ('Сказать спасибо', 'thanks')]:
            self.button(w, t, lambda mode=mode: say(mode)).pack(fill='x', padx=18, pady=4)
        self.button(w, 'Выйти из храма', w.destroy).pack(fill='x', padx=18, pady=(12, 14))

    def sleep(self):
        try:
            self.world.sleep()
        except ValueError as e:
            messagebox.showinfo('Шконка', str(e))
            return
        self.persist()
        self.after_time([])
        self.refresh()
        self.status.config(text='Новый день. Зарядка, баланда, всё по расписанию.')

    def cook_menu(self):
        w = self.window('Готовка', 680, 520)
        w.grab_set()
        self.label(w, 'ЧТО ГОТОВИМ', 14, True, color=GOLD).pack(anchor='w', padx=16, pady=12)
        for r in RECIPES:
            need = ', '.join('%s×%d' % (ITEMS[k]['name'], v) for k, v in r['need'].items())
            ok = all(self.world.has(k, v) for k, v in r['need'].items())
            b = self.button(w, '%s · %s · %d мин' % (r['name'], need, r['time']),
                            lambda r=r: self.cook(r), primary=ok)
            b.config(state='normal' if ok else 'disabled')
            b.pack(fill='x', padx=16, pady=4)
        self.button(w, 'Закрыть', w.destroy).pack(pady=10)

    def cook(self, r):
        self.close_overlays()
        for k, v in r['need'].items():
            if not self.world.has(k, v):
                return self.status.config(text='Нет ингредиентов')
        ok, text, info = self.story.roll('cun', r['dc'])
        if ok:
            for k, v in r['need'].items():
                self.world.take(k, v)
            self.world.add(r['out'], 1)
            self.toast(r['win'], 'good')
        else:
            for k, v in r['need'].items():
                self.world.take(k, v)
            self.toast(r['fail'], 'bad')
        self.world.advance(r['time'], 'готовка')
        self.world.event('cook', 'Готовка: ' + r['name'], self.world.witnesses())
        self.status.config(text=text)
        self.persist()
        self.after_time([])
        self.refresh()

    # ------------------------------------------------------------ кормёжка
    def meal_event(self):
        self.close_overlays()
        self.world.eat()
        self.persist()
        self.refresh()
        self.after_time([])
        self.minigame('chow')

    # ------------------------------------------------------------ карта
    def open_map(self):
        if self.blocked():
            return
        w = self.window('Карта зоны · M', 1180, 780)
        w.grab_set()
        w.columnconfigure(0, weight=1)
        w.rowconfigure(0, weight=1)
        c = tk.Canvas(w, bg='#0c1219', highlightthickness=0)
        c.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        self.map_hits = []

        def draw():
            img, hits = self.renderer.map((c.winfo_width() or 1100, c.winfo_height() or 660), self.world)
            self.map_photo = ImageTk.PhotoImage(img)
            c.delete('all')
            c.create_image(0, 0, anchor='nw', image=self.map_photo)
            self.map_hits = [(key, (x0, y0, x1, y1)) for key, i, (x0, y0, x1, y1) in hits]

        def click(e):
            for key, (x0, y0, x1, y1) in self.map_hits:
                if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                    w.grab_release()
                    w.destroy()
                    self.go(LOC_INDEX[key])
                    return
        c.bind('<Configure>', lambda e: draw())
        c.bind('<Button-1>', click)
        self.button(w, 'Закрыть', lambda: (w.grab_release(), w.destroy())).grid(row=1, column=0, pady=6)
        w.after(60, draw)

    def go(self, loc):
        if self.blocked():
            return self.status.config(text='Завершите действие или отмените запрос перед переходом.')
        try:
            self.world.go(loc)
        except ValueError as e:
            return self.status.config(text=str(e))
        self.world.relay()
        self.hover = None
        self.stream_text.clear()
        self.draft_speech.clear()
        self.select_default()
        self.persist()
        self.after_time([])
        self.refresh()
        self.status.config(text='Прибыл: %s · %s' % (NAMES[loc], self.world.clock()))
        self.maybe_random_scene()

    def maybe_random_scene(self):
        w = self.world
        if w.rng.random() > 0.3 or self.blocked():
            return
        loc = LOCATIONS[w.s['loc']]['key']
        if loc == 'hall' and w.inv('phone'):
            w.maybe_shmon('у поста')
            if w.s['toasts']:
                self.status.config(text=w.s['toasts'][-1]['text'])
            self.refresh()
        elif loc == 'mess' and not w.s['meals']['eaten']:
            self.toast('Пахнет баландой. Если сейчас приём пищи — жми «Поесть».')

    # ------------------------------------------------------------ инвентарь
    def open_inventory(self):
        if self.blocked():
            return
        w = self.window('Сумка и снаряжение · I', 900, 640)
        w.grab_set()
        self.label(w, 'СУМКА', 15, True, color=GOLD).pack(anchor='w', padx=18, pady=(14, 2))
        gear = self.world.s['gear']
        self.label(w, 'Оружие: %s (урон %d) · Броня %d · Точность %d%%'
                   % (gear['weapon'], gear['damage'], gear['armor'], int(gear['accuracy'] * 100)),
                   10, color=MUTED).pack(anchor='w', padx=18)
        grid = tk.Frame(w, bg=PANEL)
        grid.pack(fill='both', expand=True, padx=12, pady=8)
        items = self.world.s['inv']
        if not items:
            self.label(grid, 'Пусто. Даже мыло не своё.', 11, color=MUTED).pack(pady=20)
        for i, (key, n) in enumerate(sorted(items.items())):
            info = ITEMS.get(key, {'name': key, 'desc': '', 'icon': 'rub'})
            cell = tk.Frame(grid, bg=CARD, highlightbackground='#2b3c50', highlightthickness=1)
            cell.grid(row=i // 4, column=i % 4, padx=5, pady=5, sticky='nsew')
            im = self.renderer.icon(info.get('icon', 'coin'), 56)
            if im is not None:
                ph = ImageTk.PhotoImage(im)
                lbl = tk.Label(cell, image=ph, bg=CARD)
                lbl.image = ph
                lbl.pack(pady=(8, 2))
            tk.Label(cell, text='%s ×%d' % (info['name'], n), bg=CARD, fg=FG,
                     font=('Segoe UI', 10, 'bold')).pack()
            tk.Label(cell, text=info.get('desc', ''), bg=CARD, fg=MUTED, font=('Segoe UI', 8),
                     wraplength=170, justify='left').pack(padx=6, pady=(0, 6))
        for c in range(4):
            grid.columnconfigure(c, weight=1, uniform='i')
        shop = tk.Frame(w, bg=PANEL)
        shop.pack(fill='x', padx=14, pady=(0, 10))
        self.label(shop, 'Купить:', 10, color=MUTED).pack(side='left')
        for key in ('cig', 'tea', 'bread', 'knife', 'armor', 'shoe', 'cards', 'cross'):
            info = ITEMS[key]
            price = info.get('price') or 3
            self.button(shop, '%s · %d₽' % (info['name'], price),
                        lambda key=key: self.buy(key), small=True).pack(side='left', padx=2)

    def buy(self, key):
        try:
            self.world.buy(key)
            self.toast('Куплено: ' + ITEMS[key]['name'])
            self.persist()
        except ValueError as e:
            self.status.config(text=str(e))

    def open_stash(self):
        w = self.window('Схрон', 640, 460)
        w.grab_set()
        st = self.world.s['stashes'].get(str(self.world.s['loc']), {'found': False, 'items': []})
        self.label(w, 'СХРОН НА ОБЪЕКТЕ', 14, True, color=GOLD).pack(anchor='w', padx=16, pady=12)
        if st['items']:
            for it in list(st['items']):
                self.button(w, 'Достать: ' + ITEMS[it]['name'],
                            lambda it=it: (self.world.stash_take(it), self.persist(), w.destroy())).pack(fill='x', padx=16, pady=3)
        else:
            self.label(w, 'Пусто. Или ты ещё не нашёл.', 11, color=MUTED).pack(anchor='w', padx=16)
        self.label(w, 'Спрятать из сумки:', 10, color=MUTED).pack(anchor='w', padx=16, pady=(12, 2))
        for it in list(self.world.s['inv']):
            self.button(w, ITEMS[it]['name'],
                        lambda it=it: (self.world.stash_put(it), self.persist(), w.destroy())).pack(fill='x', padx=16, pady=2)

    # ------------------------------------------------------------ журнал
    def open_journal(self):
        if self.blocked():
            return
        w = self.window('Журнал · J', 1000, 700)
        w.grab_set()
        row = tk.Frame(w, bg=PANEL)
        row.pack(fill='x', padx=12, pady=10)
        txt = tk.Text(w, wrap='word', bg='#0b1119', fg=FG, relief='flat', font=('Segoe UI', 11))
        txt.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        s = self.world.s

        def show(key):
            txt.config(state='normal')
            txt.delete('1.0', 'end')
            if key == 'story':
                st = self.story
                lines = ['АКТ %d · цель: %s' % (st.s.get('act', 1), st.s.get('objective', '')), '']
                for e in st.s['log'][-25:]:
                    lines.append('%sСцена %s: %s' % ('✔ ' if e['ok'] else '✘ ', e['scene'], e.get('choice', '')))
                    if e.get('check'):
                        lines.append('   ' + e['check'])
                for f, v in (st.s['flags'] or {}).items():
                    if v is True:
                        lines.append('Флаг: ' + f)
                txt.insert('1.0', '\n'.join(lines))
            elif key == 'cast':
                r = self.world.rank()
                txt.insert('1.0', 'Каста: %s\n%s\nУважение: %d\nУнижений: %d\n%s'
                           % (r['title'], r['note'], s['respect'], s['humiliations'],
                              ('Клеймо: ' + s['drop_reason']) if s['dropped'] else 'Клейма нет.'))
            elif key == 'diary':
                txt.insert('1.0', '\n\n'.join(s['diary'][-20:]) or 'Дневник пуст.')
            elif key == 'gossip':
                txt.insert('1.0', '\n'.join('%s → %s: %s (доверие %d%%)'
                                            % (self.npcs.get(g['from'], {}).get('name', '?'),
                                               self.npcs.get(g['to'], {}).get('name', '?'),
                                               g['claim'][:220], g['confidence'])
                                            for g in s['gossip'][-30:]) or 'Слухов нет.')
            else:
                txt.insert('1.0', json.dumps(s.get(key, {}), ensure_ascii=False, indent=1)[:60000])
            txt.config(state='disabled')
        for title, key in [('Сюжет', 'story'), ('Каста', 'cast'), ('Дневник', 'diary'),
                           ('Слухи', 'gossip'), ('События', 'events'), ('Знания', 'knowledge'),
                           ('Долги', 'obligations'), ('Хроника', 'chron')]:
            self.button(row, title, lambda key=key: show(key), small=True).pack(side='left', padx=2)
        self.button(row, 'Закрыть', w.destroy, small=True).pack(side='right')
        show('story')

    # ------------------------------------------------------------ разговоры
    def decisions(self):
        if self.blocked() or not self.npc:
            return
        k = self.npc
        w = self.window('Решения · ' + self.npcs[k]['name'], 700, 560)
        w.grab_set()

        def do(fn):
            try:
                fn()
                self.world.advance(10, 'решение')
                self.persist()
                self.after_time([])
                self.refresh()
                w.destroy()
            except ValueError as e:
                messagebox.showinfo('Решение', str(e))
        for t, kind in [('Помочь · 2 сигареты', 'help'),
                        ('Украсть · +15₽, NPC заметит', 'theft'),
                        ('Подставить вещь · заточка/телефон/чифирь', 'frame'),
                        ('Сдать охране · +25₽ и клеймо', 'betrayal')]:
            self.button(w, t, lambda kind=kind: do(lambda: self.world.decision(k, kind))).pack(fill='x', padx=16, pady=4)
        self.button(w, 'Занять 10₽ до завтра', lambda: do(lambda: self.world.borrow(k))).pack(fill='x', padx=16, pady=4)
        self.button(w, 'Вернуть долг', lambda: do(lambda: self.world.repay(k))).pack(fill='x', padx=16, pady=4)

        def deny():
            pop = self.window('Оспорить слух', 760, 520)
            pop.grab_set()
            heard = self.world.heard(k)
            if not heard:
                self.label(pop, 'Он ничего не слышал.', 11, color=MUTED).pack(pady=20)
            for g in heard:
                self.button(pop, g['claim'][:110],
                            lambda id=g['id']: (self.world.deny(k, id), self.persist(), pop.destroy())).pack(fill='x', padx=12, pady=3)
        self.button(w, 'Оспорить слух', deny).pack(fill='x', padx=16, pady=4)

    def show_history(self):
        if not self.npc:
            return
        hist = self.world.s['history'].get(self.npc, [])
        text = '\n\n'.join(('Вы' if m['role'] == 'user' else self.npcs[self.npc]['name']) + ': ' + m['content']
                           for m in hist)
        self.text_window('История · ' + self.npcs[self.npc]['name'], text or 'Переписка пуста.')

    def reset_chat(self):
        if self.blocked() or not self.npc:
            return
        if not messagebox.askyesno('Новый разговор', 'Архивировать старую переписку? События и карма сохранятся.'):
            return
        s = self.world.s
        k = self.npc
        s.setdefault('dialogue_archives', []).append({'npc': k, 'day': s['day'],
                                                     'history': s['history'].get(k, []),
                                                     'memory': s['memory'].get(k, [])})
        s['dialogue_archives'] = s['dialogue_archives'][-30:]
        s['history'][k] = []
        s['memory'][k] = []
        self.persist()
        self.refresh()

    def enter(self, e=None):
        self.send()
        return 'break'

    def newline(self, e=None):
        self.entry.insert('insert', '\n')
        return 'break'

    # ------------------------------------------------------------ бой и мини-игры
    def fight(self, k=None, ambush=False):
        if self.blocked():
            return
        manual = k is None
        k = k or self.npc
        if not k or k not in self.world.witnesses():
            return self.status.config(text='Рядом никого.')
        if self.world.s['npc_hp'].get(k, 1) <= 0:
            return self.status.config(text='Противник уже повержен. Новый бой после отбоя.')
        if manual and not messagebox.askyesno('Дуэль', 'Начать бой с ' + self.npcs[k]['name'] + '?'):
            return
        self.close_overlays()
        self.battle_window = BattleWindow(self, k, ambush)

    def minigame(self, kind):
        if self.blocked():
            return
        self.close_overlays()
        self.mini = Mini(self, kind)

    def games(self):
        self.open_actions()

    # ------------------------------------------------------------ сервис
    def open_icons(self):
        """Коллаж иконок предметов (assets/icon_sheet.png)."""
        from PIL import Image
        w = self.window('Иконки предметов', 960, 560)
        path = BASE / 'assets/icon_sheet.png'
        try:
            im = Image.open(path).convert('RGB')
        except OSError:
            return self.text_window('Иконки', 'Нет assets/icon_sheet.png')
        k = min(1.0, 920 / im.width, 500 / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.Resampling.LANCZOS)
        self.icon_sheet_photo = ImageTk.PhotoImage(im)
        c = tk.Canvas(w, width=im.width, height=im.height, bg=PANEL, highlightthickness=0)
        c.pack(pady=12)
        c.create_image(0, 0, anchor='nw', image=self.icon_sheet_photo)
        self.label(w, 'Иконки нарисованы кодом (tools/make_icons.py) — единый стиль, без нарезки.',
                   9, color=MUTED).pack()

    def text_window(self, title, text):
        w = self.window(title, 900, 650)
        self.label(w, title, 16, True).pack(anchor='w', padx=16, pady=14)
        frame = tk.Frame(w, bg=PANEL)
        frame.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        t = tk.Text(frame, wrap='word', bg='#0b1119', fg=FG, relief='flat', font=('Segoe UI', 11),
                    padx=12, pady=12)
        sb = tk.Scrollbar(frame, command=t.yview)
        t.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        t.config(yscrollcommand=sb.set)
        t.insert('1.0', text)
        t.config(state='disabled')


def run():
    app = None
    try:
        root = tk.Tk()
        app = App(root)
        root.mainloop()
    except Exception:
        (BASE / 'logs').mkdir(exist_ok=True)
        (BASE / 'logs/startup_error.log').write_text(traceback.format_exc(), encoding='utf8')
        raise
    finally:
        if app:
            app.engine.shutdown()


if __name__ == '__main__':
    run()


def main():
    run()
