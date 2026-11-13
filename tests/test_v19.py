"""Opt-in club preparations for fictional anniversary, with private invitations."""
import json,shutil,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
import core,jubilee19,hotspots16
from world import World,save
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=19)

class Jubilee(unittest.TestCase):
 def test_stage_is_opt_in_and_old_saves_work(self):
  w=mk();self.assertIsNone(jubilee19.state(w)['theme']);self.assertEqual(jubilee19.context(w,'kol'),{})
  with self.assertRaises(ValueError):jubilee19.plan(w,'voices')
  w.s['loc']=10;before=core.C(w)['abs']
  hotspots16.perform(w,'stage','legacy')
  self.assertIsNone(jubilee19.state(w)['theme'])
  self.assertGreater(core.C(w)['abs'],before)
  with self.assertRaises(ValueError):jubilee19.plan(w,'invented')
  self.assertIsNone(jubilee19.state(w)['theme'])
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'slot.json';w.s['core'].pop('jubilee19',None);save(w.s,p)
   restored=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertIsNone(jubilee19.state(restored)['theme'])

 def test_three_themes_repeat_no_farm_and_prepare_next_day_only(self):
  for theme in jubilee19.THEMES:
   w=mk();w.s['loc']=10;a=core.C(w)['abs'];day=w.s['day']
   self.assertIn('журнал',jubilee19.plan(w,theme))
   self.assertEqual(core.C(w)['abs']-a,20)
   self.assertEqual(jubilee19.state(w)['planned_day'],day)
   self.assertIn('уже выбран',jubilee19.plan(w,'quiet'))
   self.assertEqual(jubilee19.state(w)['theme'],theme)
   self.assertEqual(core.C(w)['abs']-a,20)
   with self.assertRaises(ValueError):jubilee19.rehearse(w)
   for loc,k in [(0,'kol'),(4,'steam')]:
    w.s['loc']=loc;jubilee19.invite(w,k)
   w.s['loc']=10
   with self.assertRaises(ValueError):jubilee19.rehearse(w)
   self.assertFalse(jubilee19.ready(w));w.s['day']+=1;self.assertTrue(jubilee19.ready(w))
   self.assertIn('ещё не состоялся',jubilee19.rehearse(w))
   self.assertFalse(jubilee19.ready(w));self.assertIn('уже проверена',jubilee19.rehearse(w))
   self.assertTrue(jubilee19.state(w)['rehearsed'])
   self.assertEqual(w.s['events'][-1]['witnesses'],[])
   self.assertIn('не состоялся',str(jubilee19.journal(w)))

 def test_invitations_only_known_to_addressee_and_do_not_leak_note(self):
  w=mk();w.s['loc']=10;jubilee19.plan(w,'voices')
  with self.assertRaises(ValueError):jubilee19.invite(w,'ghost')
  with self.assertRaises(ValueError):jubilee19.invite(w,'kol')
  w.s['loc']=0;before=core.C(w)['abs'];jubilee19.invite(w,'kol')
  self.assertEqual(w.s['events'][-1]['witnesses'],['kol'])
  self.assertEqual(core.C(w)['abs']-before,10)
  self.assertIn('уже',jubilee19.invite(w,'kol'))
  self.assertEqual(core.C(w)['abs']-before,10)
  self.assertEqual(jubilee19.context(w,'cenz'),{})
  self.assertIn('обсудить',jubilee19.context(w,'kol')['ответ'])
  for k in NP:
   if k!='kol':self.assertEqual(w.context(k)['юбилейный_вечер'],{})
  self.assertEqual(w.context('kol')['записка_Шкета'],{})
  self.assertFalse(any('записку' in e['text'] for e in w.s['events'] if e['kind'].startswith('jubilee19')))
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'slot.json';save(w.s,p);loaded=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertEqual(jubilee19.state(loaded)['invited'],['kol'])
   self.assertTrue(loaded.context('kol')['юбилейный_вечер'])

 def test_click_stage_for_three_real_ui_choices_and_invite_decisions(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();app.world.s['loc']=10;app.refresh();app.draw()
    def walk(item):
     yield item
     for child in item.children:yield from walk(child)
    def press(win,text):
     next(c for c in walk(win) if c.props.get('text')==text).props['command']()
    stage=next(poly for id,_,poly in app.env_shapes if id=='stage')
    x=sum(q[0] for q in stage)/len(stage);y=min(q[1] for q in stage)+55  # above the NPC portrait
    app.click(types.SimpleNamespace(x=x,y=y));win=app.env_window
    self.assertIsNone(jubilee19.state(app.world)['theme'])
    for title in ('Голоса жителей','Двадцать строк истории','Тихий вечер'):
     self.assertTrue(any(c.props.get('text')==title for c in walk(win)))
    press(win,'Назад');self.assertIsNone(jubilee19.state(app.world)['theme'])
    app.click(types.SimpleNamespace(x=x,y=y));press(app.env_window,'Тихий вечер')
    self.assertEqual(jubilee19.state(app.world)['theme'],'quiet')
    app.world.s['loc']=0;app.refresh();app.select('kol');app.decisions();win=app.root.children[-1]
    press(win,'Пригласить обсудить юбилейный вечер')
    self.assertEqual(jubilee19.state(app.world)['invited'],['kol'])
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
