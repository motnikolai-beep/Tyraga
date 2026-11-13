"""Tour contract and headless integration, not a real screenshot or Windows event test."""
import unittest,sys,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_ui_stub  # register headless Tk before importing the coach
import meta,mentor14
from PIL import Image

class Geometry(unittest.TestCase):
    def test_cutout_is_never_covered_by_four_scrims(self):
        for rect in ((40,80,300,180),(0,0,1200,45),(700,400,1200,600)):
            rect=mentor14.clamp_rect(rect,1200,600)
            self.assertTrue(0<=rect[0]<rect[2]<=1200)
            self.assertTrue(0<=rect[1]<rect[3]<=600)
            for left,top,right,bottom in mentor14.shades(rect,1200,600):
                self.assertFalse(left<rect[2] and right>rect[0] and top<rect[3] and bottom>rect[1])

    def test_steps_cover_entry_map_boss_actions_and_replay(self):
        ids=[step[0] for step in mentor14.STEPS]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue({'chat','chat_send','map','boss','map_room','more','menu','portrait','hud','actions'}<=set(ids))
        with Image.open(Path(__file__).resolve().parents[1]/'assets/mentor_v14.jpg') as im:
            self.assertGreaterEqual(im.width,400)
            self.assertGreaterEqual(im.height,600)
        with Image.open(Path(__file__).resolve().parents[1]/'assets/tutorial_hand.png') as im:self.assertEqual(im.mode,'RGBA')

class StubUI(unittest.TestCase):
    def test_interactive_first_run_skip_and_replay_do_not_spend_time(self):
        from test_ui_stub import Widget,main,env
        import core
        original=main.BASE
        def origin(widget):return 0
        with tempfile.TemporaryDirectory() as td,patch.object(Widget,'winfo_rootx',origin,create=True),patch.object(Widget,'winfo_rooty',origin,create=True),patch.object(main.ImageTk,'PhotoImage',lambda im:object()),patch.object(main.App,'connect',lambda self:None):
            b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
            try:
                app=main.App(Widget());app.new_game('normal');app.menu.hide()
                start=core.C(app.world)['abs'];app.maybe_tutorial();t=app.mentor
                self.assertIsNotNone(t);self.assertEqual(t.step[0],'welcome')
                self.assertTrue(app.blocked());app.menu.show();self.assertFalse(app.menu.visible)
                for key in ('welcome','hud','actions','portrait','chat','chat_send','map','boss','map_room','more','menu','done'):
                    self.assertEqual(t.step[0],key)
                    if key=='portrait':app.open_chat()
                    if key=='map':app.toggle_map()
                    if key=='map_room':app.travel(app.world.s['loc'])
                    t.next()
                self.assertIsNone(app.mentor)
                self.assertTrue(meta.load_settings(b)['tutorial_v14_done'])
                self.assertEqual(core.C(app.world)['abs'],start)
                app.maybe_tutorial();self.assertIsNone(app.mentor)
                app.settings['hints']=False;app.maybe_tutorial(force=True)
                self.assertIsNotNone(app.mentor);app.mentor.skip()
                self.assertFalse(meta.load_settings(b)['hints'])
                self.assertEqual(core.C(app.world)['abs'],start)
            finally:main.BASE=original

if __name__=='__main__':unittest.main()
