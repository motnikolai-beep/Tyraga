# -*- coding: utf-8 -*-
"""Headless-тест интерфейса: tkinter подменяется заглушкой, картинки — пустышкой.

Это не проверка красоты и не запуск GPU: только что код сцены, карты, действий,
мини-игр, боя и сюжетных окон не падает и меняет состояние мира.
"""
import random
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class Widget:
    def __init__(self, *a, **kw):
        self.master = a[0] if a else None
        self.props = dict(kw)
        self.children = []
        self.content = ''
        self.value = kw.get('value', 0)
        self.index = 0
        if isinstance(self.master, Widget):
            self.master.children.append(self)

    def __getattr__(self, k):
        if k.startswith('create_'):
            return lambda *a, **kw: 1
        if k in ('winfo_width', 'winfo_height'):
            return lambda: 1200 if k.endswith('width') else 640
        return lambda *a, **kw: None

    def config(self, *a, **kw):
        self.props.update(kw)

    configure = config

    def cget(self, k):
        return self.props.get(k, '')

    def winfo_children(self):
        return self.children[:]

    def winfo_exists(self):
        return True

    def winfo_ismapped(self):
        return True

    def grid(self, *a, **kw):
        return None

    def pack(self, *a, **kw):
        return None

    def place(self, *a, **kw):
        return None

    def grid_propagate(self, *a):
        return None

    def grid_columnconfigure(self, *a, **kw):
        return None

    columnconfigure = grid_columnconfigure
    rowconfigure = grid_columnconfigure

    def focus_set(self):
        return None

    def bind(self, *a, **kw):
        return None

    def get(self, *a):
        return self.content if a else self.value

    def set(self, v):
        self.value = v

    def insert(self, pos, v, *a):
        self.content += v

    def delete(self, *a):
        self.content = ''

    def current(self, i=None):
        if i is not None:
            self.index = i
        return self.index

    def bbox(self, *a):
        return (400, 90, 850, 220)

    def after(self, *a):
        return 'timer'

    def after_cancel(self, *a):
        return None

    def grab_set(self):
        return None

    def grab_release(self):
        return None

    def transient(self, *a):
        return None

    def title(self, *a):
        return None

    def geometry(self, *a):
        return None

    def minsize(self, *a):
        return None

    def mainloop(self):
        return None

    def destroy(self):
        if isinstance(self.master, Widget) and self in self.master.children:
            self.master.children.remove(self)


fake = types.ModuleType('tkinter')
for n in ['Tk', 'Frame', 'Label', 'Button', 'Canvas', 'Text', 'Toplevel', 'LabelFrame',
          'Radiobutton', 'IntVar', 'StringVar', 'BooleanVar', 'Scrollbar', 'Checkbutton',
          'Menu', 'Menubutton', 'Listbox']:
    setattr(fake, n, Widget)
fake.TclError = RuntimeError
fake.ttk = types.SimpleNamespace(Style=Widget, Combobox=Widget)
fake.messagebox = types.SimpleNamespace(showwarning=lambda *a, **k: None,
                                        showinfo=lambda *a, **k: None,
                                        showerror=lambda *a, **k: None,
                                        askyesno=lambda *a, **k: True)
sys.modules.setdefault('tkinter', fake)
sys.modules['tkinter'] = fake

import main  # noqa: E402
from minigames import Mini  # noqa: E402
from data import LOC_INDEX  # noqa: E402


class Smoke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = main.BASE
        b = Path(self.tmp.name)
        shutil.copytree(self.original / 'assets', b / 'assets')
        shutil.copy(self.original / 'npcs.json', b / 'npcs.json')
        if (self.original / '.env').exists():
            shutil.copy(self.original / '.env', b / '.env')
        main.BASE = b
        self.patch_img = patch.object(main.ImageTk, 'PhotoImage', lambda x: object())
        self.patch_img.start()
        self.patch_conn = patch.object(main.App, 'connect', lambda s: None)
        self.patch_conn.start()
        self.app = main.App(Widget())

    def tearDown(self):
        self.patch_conn.stop()
        self.patch_img.stop()
        main.BASE = self.original
        self.tmp.cleanup()

    def test_scene_all_locations(self):
        app = self.app
        for loc in range(len(app.world.witnesses.__self__.npcs) and 15):
            app.world.s['time'] = 12 * 60
            try:
                app.world.go(loc)
            except ValueError:
                app.world.s['flags']['kicha_open'] = True
                app.world.go(loc)
            app.world.s['time'] = 12 * 60
            app.refresh()
            self.assertTrue(app.hits is not None)

    def test_hud_and_rank(self):
        app = self.app
        app.refresh()
        app.world.rise(60, 'тест')
        app.refresh_hud()
        self.assertIn(app.world.rank_key(), ('blatnoy', 'pahan'))

    def test_story_window_and_choices(self):
        app = self.app
        app.world.s['loc'] = LOC_INDEX['cam']
        app.open_story()
        for _ in range(60):
            if app.story.finished():
                break
            scn = app.story.scene()
            where = scn.get('where')
            if where:
                app.world.s['loc'] = LOC_INDEX[where]
                app.world.s['time'] = 22 * 60 if scn['id'] == 'first_night' else 12 * 60
            app.world.s['visit'] = {'day': app.world.s['day'], 'used': False}
            app.story_window = app.window('x')
            app.open_story()
            app.choose_story(0)
        self.assertTrue(app.story.finished())
        app.show_ending()

    def test_actions_cards(self):
        app = self.app
        app.world.s['loc'] = LOC_INDEX['cam']
        app.world.s['time'] = 22 * 60
        app.open_actions()
        app.do_action('look')
        app.do_action('smoke')
        app.world.s['loc'] = LOC_INDEX['gym']
        app.do_action('train')
        app.world.s['loc'] = LOC_INDEX['temple']
        app.world.s['karma']['honor'] = -10
        app.do_action('pray')
        self.assertGreater(app.world.s['karma']['honor'], -10)

    def test_meal_minigame(self):
        app = self.app
        app.world.s['loc'] = LOC_INDEX['mess']
        app.world.s['time'] = 7 * 60 + 20
        app.meal_event()
        m = app.mini
        self.assertIsNotNone(m)
        for _ in range(10):
            if m.done:
                break
            m.pos = 50
            m.chow_click()
        self.assertTrue(m.done)
        m.close()
        self.assertIsNone(app.mini)

    def test_other_minigames(self):
        app = self.app
        r = random.Random(4)
        for kind in ('porridge', 'chow', 'pushups', 'poker', 'chess', 'tunnel', 'dance', 'factory'):
            app.world.s['inv']['cig'] = 20
            m = Mini(app, kind)
            app.mini = m
            for _ in range(3000):
                if m.done:
                    break
                if kind == 'porridge':
                    m.porr(r.randrange(36))
                elif kind == 'chow':
                    m.pos = 50
                    m.chow_click()
                elif kind == 'pushups':
                    m.pos = 50
                    m.push_click()
                elif kind == 'poker':
                    m.poker(r.randrange(4))
                elif kind == 'chess':
                    m.chess(r.randrange(3))
                elif kind == 'tunnel':
                    m.move(*r.choice([(0, -1), (0, 1), (1, 0), (-1, 0)]))
                elif kind == 'dance':
                    m.dance(r.randrange(4))
                else:
                    m.target('gvo')
                    m.factory('пишет стихи')
            self.assertTrue(m.done, kind)
            self.assertIsNone(app.mini) if m.closed else None
            m.close()
            self.assertIsNone(app.mini)

    def test_battle(self):
        app = self.app
        app.world.s['loc'] = LOC_INDEX['cellar']
        app.fight('sm')
        bw = app.battle_window
        self.assertIsNotNone(bw)
        bw.next_at = 0
        bw.manual_turn()
        self.assertGreaterEqual(bw.b.round, 2)
        bw.close()
        self.assertIsNone(app.battle)

    def test_map_inventory_journal(self):
        app = self.app
        app.open_map()
        app.open_inventory()
        app.buy('tea')
        app.open_journal()
        app.open_stash()
        app.decisions() if app.npc else None
        app.text_window('t', 'x')
        app.close_overlays()

    def test_chat_accept_and_time(self):
        app = self.app
        app.connected = True
        app.npc = 'zub'
        meta = {'npc': 'zub', 'text': 'Зубило, расскажи, чем тут вообще живут', 'private': False}
        app.job = {'id': 't', 'kind': 'chat', 'meta': meta}
        before = app.world.s['time']
        app.q.put(('t', {'reply': 'Живут по понятиям.', 'karma': {'empathy': 0, 'honor': 0, 'cunning': 0},
                         'relationship': 0, 'reason': '', 'memory': '', 'rumors_used': [],
                         'economy': {}, '_combat_intent': None}, None))
        app.poll()
        self.assertGreaterEqual(app.world.s['time'], before)
        self.assertTrue(app.world.s['history']['zub'])

    def test_pause_and_mode(self):
        app = self.app
        app.toggle_pause()
        self.assertTrue(app.paused)
        app.toggle_pause()
        self.assertFalse(app.paused)
        fast = app.engine.cfg['CHAT_FAST_MODE']
        app.toggle_mode()
        self.assertNotEqual(fast, app.engine.cfg['CHAT_FAST_MODE'])


if __name__ == '__main__':
    unittest.main()
