"""Geometry and headless interaction checks; real rendering needs a desktop."""
import unittest,sys,types,tempfile,shutil
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_ui_stub import Widget
from radial25 import sector,geometry,DialogueWheel,actions

class Nearby:
 def __init__(self):self.local=['zub']
 def witnesses(self):return self.local

class Game:
 def __init__(self):
  self.root=Widget();self.world=Nearby();self.npcs={'zub':{'name':'Зуб'}}
  self.calls=[];self.wheel=None;self.npc='zub'
 def window(self,title,w,h):
  obj=Widget(self.root);obj._layout_size=(w,h);return obj
 def open_chat(self):self.calls.append('chat')
 def decisions(self):self.calls.append('decisions')
 def knowledge_window(self):self.calls.append('knowledge')
 def show_history(self):self.calls.append('history')

class WheelTests(unittest.TestCase):
 def test_sector_and_resize(self):
  for size in [(700,500),(300,280),(1024,768)]:
   cx,cy,r,inner=geometry(*size)
   self.assertLess(inner,r)
   for n in (3,4,6):
    for i in range(n):
     import math
     angle=math.radians(90-i*360/n)
     self.assertEqual(sector(cx+round((r-8)*math.cos(angle)),cy-round((r-8)*math.sin(angle)),cx,cy,r,inner,n),i)
    self.assertIsNone(sector(cx,cy,cx,cy,r,inner,n))
    self.assertIsNone(sector(cx+r+1,cy,cx,cy,r,inner,n))
  self.assertIsNone(sector(0,0,0,0,100,25,0))
 def test_actions_are_nearby_only(self):
  app=Game();self.assertEqual([a[0] for a in actions(app,'zub')],['talk','decide','knowledge','history'])
  self.assertEqual(actions(app,'absent'),[])
 def test_real_app_entrypoint_and_modal_guard(self):
  from test_ui_stub import main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();app.select('zub')
    self.assertEqual(app.wheelbtn.props['text'],'Колесо · R')
    app.job={'kind':'chat'};app.open_wheel();self.assertIsNone(app.wheel);app.job=None
    app.modal=object();app.open_wheel();self.assertIsNone(app.wheel);app.modal=None
    app.hot(app.open_wheel,types.SimpleNamespace(widget=app.entry));self.assertIsNone(app.wheel)
    app.open_wheel();self.assertIsNotNone(app.wheel);self.assertTrue(app.blocked())
    previous=app.wheel;app.open_wheel();self.assertIs(app.wheel,previous)
    previous.choose(1);self.assertIsNone(app.wheel)
    app.open_wheel();self.assertIsNotNone(app.wheel);app.close();self.assertIsNone(app.wheel)
   finally:main.BASE=original
 def test_mouse_keys_close_and_no_stale_npc(self):
  app=Game();wheel=DialogueWheel(app,'zub');app.wheel=wheel
  cx,cy,r,inner=wheel.geom
  wheel.motion(types.SimpleNamespace(x=cx,y=cy-r+8))
  self.assertEqual(wheel.selected,0)
  wheel.click(types.SimpleNamespace(x=cx,y=cy-r+8))
  self.assertEqual(app.calls,['chat']);self.assertIsNone(app.wheel)
  wheel=DialogueWheel(app,'zub');app.wheel=wheel
  wheel.rotate(1);wheel.choose(wheel.selected)
  self.assertEqual(app.calls[-1],'decisions')
  wheel=DialogueWheel(app,'zub');app.wheel=wheel
  app.world.local=[];wheel.choose(2)
  self.assertIsNone(app.wheel);self.assertEqual(len(app.calls),2)
  app.world.local=['zub'];wheel=DialogueWheel(app,'zub');app.wheel=wheel
  wheel.click(types.SimpleNamespace(x=wheel.geom[0],y=wheel.geom[1]))
  self.assertIsNone(app.wheel);self.assertEqual(len(app.calls),2)

if __name__=='__main__':unittest.main()
