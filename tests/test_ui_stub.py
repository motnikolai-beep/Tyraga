"""Headless UI test; not an actual Tk rendering or GPU test."""
import unittest,sys,tempfile,random,types,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class Widget:
 def __init__(self,*a,**kw):
  self.master=a[0] if a else None;self.props=dict(kw);self.children=[];self.content='';self.value=kw.get('value',0);self.index=0
  if isinstance(self.master,Widget):self.master.children.append(self)
 def __getattr__(self,k):
  if k.startswith('create_'):return lambda *a,**kw:1
  return lambda *a,**kw:None
 def config(self,*a,**kw):self.props.update(kw)
 configure=config
 def cget(self,k):return self.props.get(k,'')
 def winfo_children(self):return self.children[:]
 def winfo_width(self):return 1200
 def winfo_height(self):return 600
 def get(self,*a):return self.content if a else self.value
 def set(self,v):self.value=v
 def insert(self,pos,v,*a):self.content+=v
 def delete(self,*a):self.content=''
 def current(self,i=None):
  if i is not None:self.index=i
  return self.index
 def bbox(self,*a):return (400,90,850,220)
 def after(self,*a):return 'timer'
 def destroy(self):
  if isinstance(self.master,Widget) and self in self.master.children:self.master.children.remove(self)
fake=types.ModuleType('tkinter')
for n in ['Tk','Frame','Label','Button','Canvas','Text','Toplevel','LabelFrame','Radiobutton','IntVar','StringVar','BooleanVar','Scrollbar','Checkbutton','Menu','Menubutton']:setattr(fake,n,Widget)
fake.TclError=RuntimeError;fake.ttk=types.SimpleNamespace(Style=Widget,Combobox=Widget);fake.messagebox=types.SimpleNamespace(showwarning=lambda *a:None,showinfo=lambda *a:None,showerror=lambda *a:None,askyesno=lambda *a:True);sys.modules['tkinter']=fake
import main,ai
from minigames import Mini
class Smoke(unittest.TestCase):
 def test_scenes_bubbles_games_battle_modes(self):
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');shutil.copy(original/'.env',b/'.env');main.BASE=b
   try:
    app=main.App(Widget());self.assertEqual(len(app.navbuttons),12)
    for loc in range(12):app.go(loc);self.assertTrue(app.hits);self.assertEqual('zub' in [k for rect,k in app.hits],loc==0);self.assertIn(app.npc,app.world.witnesses())
    app.toggle_cover();self.assertFalse(app.cover);app.toggle_cover();app.go(0);app.select('zub');app.action('work')
    for kind in ['porridge','poker','chess','tunnel','dance','factory']:
     app.world.s.update(dig=0,cig=30);m=Mini(app,kind);app.mini=m;r=random.Random(8)
     for _ in range(3000):
      if m.done:break
      if kind=='porridge':m.porr(r.randrange(36))
      elif kind=='poker':m.poker(r.randrange(4))
      elif kind=='chess':m.chess(r.randrange(3))
      elif kind=='tunnel':m.move(*r.choice([(0,-1),(0,1),(1,0),(-1,0)]))
      elif kind=='dance':m.dance(r.randrange(4))
      else:m.target('gvo');m.factory('пишет стихи')
     self.assertTrue(m.done,kind);m.close();m.close();self.assertIsNone(app.mini)
    app.fight('zub');bw=app.battle_window;bw.next_at=0;bw.manual_turn();round=bw.b.round;bw.toggle();bw.next_at=0;bw.tick();self.assertGreater(bw.b.round,round);bw.toggle();round=bw.b.round;bw.next_at=0;bw.tick();self.assertEqual(bw.b.round,round);bw.close();self.assertIsNone(app.battle)
    app.world.s['npc_health']={};text='щас порежу тебя';meta={'npc':'zub','text':text,'private':False};o=ai.zero();o.update(reply='Ну попробуй.',_combat_intent={'speaker':'player','target':'npc','evidence':text})
    app.job={'id':'test','kind':'chat','meta':meta};app.liveq.put(('old','zub','wrong'));app.liveq.put(('test','zub','Частичный'));app.q.put(('test',o,None));app.poll();self.assertIsNotNone(app.battle);self.assertTrue(app.bubble_hits);app.battle_window.close();app.chat_combat(meta,o);self.assertIsNone(app.battle)
    self.assertIn('Ну попробуй',app.world.s['history']['zub'][-1]['content']);app.show_history();app.reset_chat();self.assertEqual(app.world.s['history']['zub'],[])
    app.toggle_mode();self.assertEqual(app.engine.cfg['CHAT_FAST_MODE'],'false');app.toggle_mode();self.assertEqual(app.engine.cfg['CHAT_FAST_MODE'],'true');app.journal();app.residents();app.respect_window()
   finally:main.BASE=original
if __name__=='__main__':unittest.main()
