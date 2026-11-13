"""A promise can lead to a procedural question, never an invented reply."""
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
import core,note17,route18
from world import World,save
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=18)
def promised(w):
 note17.find(w);note17.act(w,'give');w.s['day']+=1
 core.C(w)['done'].append('note17_after');core.C(w)['flags']['note17_promise']=True

class Route(unittest.TestCase):
 def test_no_quest_without_explicit_promise_or_after_show_only(self):
  w=mk();self.assertFalse(route18.eligible(w));self.assertEqual(route18.journal(w),[])
  w.s['loc']=7
  for choice in ('anonymous','open'):
   with self.assertRaises(ValueError):route18.inquire(w,choice)
  with self.assertRaises(ValueError):route18.tell(w,'explain')
  w.s['loc']=0;note17.find(w);note17.act(w,'show')
  core.C(w)['flags']['note17_promise']=True;core.C(w)['done'].append('note17_after')
  self.assertFalse(route18.eligible(w))
  with self.assertRaises(ValueError):route18.inquire(w,'bad')
  with self.assertRaises(ValueError):route18.tell(w,'bad')
  self.assertFalse(route18.state(w)['route'])

 def test_anonymous_question_preserves_privacy_and_return_is_optional(self):
  w=mk();promised(w);w.s['loc']=7
  start=core.C(w)['abs'];route18.inquire(w,'anonymous')
  self.assertEqual(core.C(w)['abs']-start,15)
  self.assertEqual(w.s['events'][-1]['witnesses'],[])
  self.assertEqual(route18.context(w,'cenz'),{})
  self.assertEqual(route18.context(w,'kol'),{})
  self.assertTrue(all(not w.context(k)['почтовый_вопрос'] for k in NP))
  self.assertIn('порядок',route18.journal(w)[0].lower())
  self.assertIn('уже',route18.inquire(w,'open'))
  self.assertEqual(core.C(w)['abs']-start,15)
  with self.assertRaises(ValueError):route18.tell(w,'explain')
  w.s['loc']=0;start=core.C(w)['abs'];rel=w.s['relations'].get('kol',0)
  route18.tell(w,'explain');self.assertTrue(route18.state(w)['told'])
  self.assertEqual(core.C(w)['abs']-start,10)
  self.assertEqual(w.s['relations']['kol'],rel+3)
  self.assertEqual(route18.context(w,'cenz'),{})
  self.assertTrue(route18.context(w,'kol'))
  self.assertEqual(route18.tell(w,'explain'),'Шкет уже знает, как подать запрос; письмо за него вы не отправляли.')
  route18.tell(w,'offer');self.assertTrue(route18.state(w)['offered'])
  self.assertEqual(w.s['relations']['kol'],rel+5)
  self.assertEqual(core.C(w)['abs']-start,20)
  self.assertEqual(w.s['events'][-1]['witnesses'],['kol'])
  self.assertFalse(any(route18.context(w,k) for k in NP if k!='kol'))
  self.assertTrue(all('сестра ответила' not in str(e) for e in w.s['events']))

 def test_open_question_reveals_name_to_censor_but_not_contents_or_reply(self):
  w=mk();promised(w);w.s['loc']=7
  route18.inquire(w,'open');self.assertEqual(w.s['events'][-1]['witnesses'],['cenz'])
  self.assertIn('Шкета',str(w.context('cenz')['почтовый_вопрос']))
  self.assertEqual(w.context('cenz')['записка_Шкета'],{})
  self.assertNotIn('сестры',str(w.context('cenz')['почтовый_вопрос']))
  for k in NP:
   if k!='cenz':self.assertFalse(w.context(k)['почтовый_вопрос'])
  w.s['loc']=0;route18.tell(w,'offer')
  self.assertEqual(w.s['events'][-1]['witnesses'],['kol'])
  self.assertIn('чистый',route18.journal(w)[0])
  self.assertEqual(w.context('kol')['почтовый_вопрос']['предложен_чистый_лист'],True)

 def test_save_roundtrip_and_old_save_compatibility(self):
  w=mk();promised(w);w.s['loc']=7;route18.inquire(w,'anonymous')
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'slot.json';save(w.s,p);loaded=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertEqual(route18.state(loaded)['route'],'anonymous');self.assertTrue(route18.eligible(loaded))
   old=mk();save(old.s,p);restored=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertFalse(route18.eligible(restored));self.assertIsNone(route18.state(restored)['route'])

 def test_decisions_are_reachable_from_actual_npc_dialogs(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();promised(app.world)
    def walk(item):
     yield item
     for child in item.children:yield from walk(child)
    def choices():
     app.decisions();win=app.root.children[-1]
     return win,{c.props.get('text'):c for c in walk(win) if c.props.get('command')}
    app.world.s['loc']=7;app.refresh();app.select('cenz')
    win,buttons=choices();self.assertIn('Узнать порядок письма, не называя Шкета',buttons)
    buttons['Узнать порядок письма, не называя Шкета'].props['command']()
    self.assertEqual(route18.state(app.world)['route'],'anonymous')
    app.world.s['loc']=0;app.refresh();app.select('kol');win,buttons=choices()
    self.assertIn('Предложить Шкету чистый лист',buttons)
    buttons['Предложить Шкету чистый лист'].props['command']()
    self.assertTrue(route18.state(app.world)['offered'])
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
