"""Responsive layout checks without claiming a real Windows/Tk screenshot."""
import shutil,tempfile,unittest,types
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import ui_layout,hotspots16,gear20,core

SCREENS=((800,600),(1024,768),(1366,768),(1920,1080))

class Geometry(unittest.TestCase):
 def test_every_window_stays_inside_varied_displays(self):
  for sw,sh in SCREENS:
   main=ui_layout.main_size((sw,sh))
   self.assertLessEqual(main[0],sw-32);self.assertLessEqual(main[1],sh-72)
   self.assertGreaterEqual(main[0],760);self.assertGreaterEqual(main[1],520)
   for requested in ((520,305),(680,720),(840,860),(900,680),(1220,755),(984,494)):
    w,h=ui_layout.window_size(*requested,(sw,sh))
    self.assertGreater(w,0);self.assertGreater(h,0)
    self.assertLessEqual(w,sw-32);self.assertLessEqual(h,sh-72)
    self.assertLessEqual(w,requested[0]);self.assertLessEqual(h,requested[1])
    vw,vh,scale=ui_layout.fight_viewport(w,h)
    self.assertLessEqual(vw+24,w);self.assertLessEqual(vh+24,h)
    self.assertGreater(scale,0);self.assertLessEqual(scale,1)
   self.assertLessEqual(ui_layout.card_count(sw-40),7)
   self.assertLessEqual(ui_layout.menu_chars(sw,1.8),60)
   self.assertLessEqual(ui_layout.text_wrap(sw,130),sw-130)

 def test_silhouette_click_mapping_survives_resizing_and_letterbox(self):
  for sw,sh in SCREENS:
   for cover in (True,False):
    for variant in ('master','legacy'):
     for loc in range(12):
      id,title,poly=hotspots16.objects(loc,variant)[0]
      size=(3840,2160) if variant=='master' else (2560,1440)
      pts=hotspots16.transform(poly,(sw-40,max(220,sh-240)),size,cover)
      x=sum(p[0] for p in pts)/len(pts);y=sum(p[1] for p in pts)/len(pts)
      self.assertEqual(hotspots16.hit(x,y,[(id,title,pts)]),(id,title))

 def test_scaled_combat_text_and_shapes(self):
  class Canvas:
   def __init__(self):self.changed=[]
   def scale(self,*args):self.changed.append(('scale',args))
   def find_all(self):return (1,2)
   def type(self,item):return 'text' if item==1 else 'rectangle'
   def itemcget(self,item,key):return {'font':'Segoe UI 20 bold','width':'500'}[key]
   def itemconfigure(self,item,**kwargs):self.changed.append((item,kwargs))
  c=Canvas();ui_layout.scale_canvas(c,.6)
  self.assertIn((1,{'font':('Segoe UI',12,'bold')}),c.changed)
  self.assertIn((1,{'width':300}),c.changed)

class StubWindows(unittest.TestCase):
 def test_all_major_windows_and_long_texts_at_small_screen_high_ui_scale(self):
  from test_ui_stub import Widget,main,env
  from story_data import SCENES
  from uikit import EventWindow
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None),patch.object(Widget,'winfo_screenwidth',lambda s:800,create=True),patch.object(Widget,'winfo_screenheight',lambda s:600,create=True):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    root=Widget();app=main.App(root);app.settings['ui_scale']=1.8;app.apply_settings()
    app.new_game('normal');app.menu.hide()
    self.assertEqual(app._window_width,768)
    coords=[];app.hud.grid=lambda **kw:coords.append(kw);app.reflow_header(768)
    self.assertEqual(coords[-1]['row'],1)
    for screen in ('main','new','slots','howto','authors','stats','settings','ach'):
     app.menu.show(screen)
     self.assertTrue(hasattr(app.menu,'scroll'))
     app.menu.hide()
    for tab in ('gfx','snd','ai','game'):
     app.menu.show('settings');app.menu.go('settings',tab=tab);app.menu.hide()
    app.wardrobe();w=root.children[-1]
    self.assertTrue(any(c.__class__ is Widget for c in w.children))
    app.calendar_window();app.equipment();app.decisions();app.stash_window();app.journal_window()
    sid=next(k for k,s in SCENES.items() if len(s['nodes']['start']['ch'])>=3)
    ev=EventWindow(app,sid);self.assertIsNotNone(ev.opts_outer)
    self.assertTrue(all(c.props.get('wraplength',0)<=ui_layout.text_wrap(768-290,32) for c in ev.opts.children if c.props.get('text')))
    ev.resize(types.SimpleNamespace(widget=ev.top,width=760,height=520))
    self.assertEqual(ev.choice_wrap,ui_layout.text_wrap(760-290,32))
    ev.finish()
    self.assertIsNone(app.modal)
   finally:main.BASE=original

class ScreenMatrix(unittest.TestCase):
 def test_card_overflow_and_popup_geometry_across_screens_and_ui_scales(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    for sw,sh in SCREENS:
     with patch.object(Widget,'winfo_screenwidth',lambda s,w=sw:w,create=True),patch.object(Widget,'winfo_screenheight',lambda s,h=sh:h,create=True):
      app=main.App(Widget());app.new_game('normal');app.menu.hide()
      for scale in (.8,1.0,1.4,1.8):
       app.settings['ui_scale']=scale;app.apply_settings()
       with patch.object(app.actrow,'winfo_width',lambda width=sw-40:width,create=True):app.render_cards()
       shown=min(len(app.acts),ui_layout.card_count(sw-40))
       self.assertEqual(app._card_columns,shown)
       self.assertEqual(len(app.actrow.children),shown+1)
       pop=app.window('Проверка русской длинной строки',1220,860)
       self.assertLessEqual(pop._layout_size[0],sw-32)
       self.assertLessEqual(pop._layout_size[1],sh-72)
       pop.destroy()
   finally:main.BASE=original

class CopyAudit(unittest.TestCase):
 def test_every_scene_node_and_choice_has_renderable_text(self):
  from story_data import SCENES
  import re
  vars={'case':'личное дело','letter_intro':'сосед помнит','letter_end_intro':'лист рядом',
        'friend':'товарищ','enemy':'недруг','slot':'Обед','key':'завтрак'}
  checked=0
  for sid,sc in SCENES.items():
   self.assertTrue(sc['title'].strip(),sid)
   for node in sc['nodes'].values():
    texts=[node['text']]+[choice['t'] for choice in node['ch']]
    texts += [result['text'] for choice in node['ch'] for result in (choice['ok'],choice['fail'])]
    for text in texts:
     self.assertIsInstance(text,str);self.assertTrue(text.strip(),sid)
     rendered=core.render_text(text,vars)
     self.assertFalse(re.search(r'\{[a-zA-Z_][a-zA-Z_0-9]*\}',rendered),(sid,rendered))
     checked+=1
  self.assertGreater(checked,750)

 def test_every_npc_and_local_background_asset_is_readable(self):
  import json
  root=Path(__file__).resolve().parents[1]
  npcs=json.loads((root/'npcs.json').read_text(encoding='utf8'))
  self.assertEqual(len(npcs),20)
  for npc in npcs.values():
   with Image.open(root/'assets'/(npc['portrait']+'.jpg')) as im:
    self.assertGreaterEqual(im.width,200);self.assertGreaterEqual(im.height,200)
  for loc in range(12):
   with Image.open(root/'assets'/('loc_%d.jpg'%loc)) as im:
    self.assertGreaterEqual(im.width,1200)

if __name__=='__main__':unittest.main()
