"""Player-facing evidence ledger and one-off local reactions; not a real GUI screenshot."""
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import core,knowledge24,thread22
from world import World,save
ROOT=Path(__file__).resolve().parents[1]
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=24)

class Knowledge(unittest.TestCase):
 def test_actual_witness_is_distinct_from_delivered_rumour(self):
  w=mk();w.s['loc']=1;w.s['day']=3;core.C(w)['abs']=3*1440+10*60
  thread22.choose(w,'intro','spread')
  event=w.s['events'][-1]
  zina=knowledge24.knowledge(w,'zina')
  self.assertEqual(zina[-1]['id'],event['id']);self.assertTrue(zina[-1]['firsthand'])
  self.assertFalse(knowledge24.knowledge(w,'cenz'))
  self.assertIn('видел сам',knowledge24.report(w))
  self.assertIn('нет подтверждённых',knowledge24.report(w))
  w.s['day']=4;thread22.morning(w)
  heard=knowledge24.knowledge(w,'cenz')[-1]
  self.assertEqual(heard['id'],event['id']);self.assertFalse(heard['firsthand'])
  self.assertEqual(heard['source'],'слышал пересказ')
  self.assertIsNone(knowledge24.offer(w,'cenz')) # still remote
  w.s['loc']=7;self.assertEqual(knowledge24.offer(w,'cenz')['id'],event['id'])
  self.assertIn('не был',knowledge24.prompt(w,'cenz',heard))
  self.assertNotIn('записк',knowledge24.report(w).lower())
  self.assertNotIn('сестр',knowledge24.report(w).lower())

 def test_one_reaction_per_event_requires_local_and_saves_its_result(self):
  w=mk();w.s['loc']=6;w.s['day']=4;core.C(w)['abs']=4*1440+10*60
  e=w.event('duty22_fact','Ведомость сверена вместе с Зоей.', ['zv'])
  info=knowledge24.offer(w,'zv');self.assertEqual(info['id'],e['id'])
  old=core.C(w)['abs'];rel=w.s['relations'].get('zv',0)
  result=knowledge24.respond(w,'zv',e['id'],'clarify')
  self.assertIn('Зоя',result);self.assertEqual(core.C(w)['abs']-old,5)
  self.assertEqual(w.s['relations']['zv'],rel+1)
  self.assertIsNone(knowledge24.offer(w,'zv'))
  with self.assertRaises(ValueError):knowledge24.respond(w,'zv',e['id'],'listen')
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'save.json';save(w.s,path)
   loaded=World(NP,json.loads(path.read_text(encoding='utf8')))
   self.assertIsNone(knowledge24.offer(loaded,'zv'))
   self.assertEqual(knowledge24.state(loaded)['seen']['zv'],[e['id']])

 def test_private_mail_and_unrelated_speech_never_enter_the_ledger(self):
  w=mk();w.s['loc']=0
  w.event('note17_secret','Приватная записка Шкета: секретный адрес.',['kol'])
  w.event('route18_open','Шкет спросил о сестре.', ['kol'])
  w.conversation_event('kol','Приватные слова','Ответ',private=True)
  self.assertIsNone(knowledge24.offer(w,'kol'))
  dossier=knowledge24.report(w)
  self.assertNotIn('секретный адрес',dossier)
  self.assertNotIn('Приватные слова',dossier)
  self.assertFalse(knowledge24.knowledge(w,'cenz'))
  # Legacy save without a reactions field loads without changing the originals.
  core.C(w).pop(knowledge24.KEY,None)
  self.assertEqual(knowledge24.state(w)['seen'],{})

 def test_correction_is_new_hearsay_not_retroactive_truth(self):
  w=mk();w.s.update(loc=1,day=3);core.C(w)['abs']=3*1440+10*60
  thread22.choose(w,'intro','spread');old=w.s['events'][-1]
  w.s['day']=4;thread22.morning(w)
  w.s['loc']=6;w.s['day']=5;core.C(w)['abs']=5*1440+10*60
  thread22.state(w)['days']['intro']=3
  thread22.choose(w,'evidence','inspect')
  w.s['loc']=10;w.s['day']=6;core.C(w)['abs']=6*1440+17*60
  thread22.choose(w,'meeting','listen')
  w.s['loc']=1;w.s['day']=7;core.C(w)['abs']=7*1440+10*60
  thread22.choose(w,'final','correct');correction=w.s['events'][-1]
  w.s['day']=8;thread22.morning(w)
  cenz=knowledge24.knowledge(w,'cenz')
  self.assertEqual([e['id'] for e in cenz],[old['id'],correction['id']])
  self.assertTrue(all(not e['firsthand'] for e in cenz))

 def test_decisions_dialogue_and_journal_are_reachable_in_stub_ui(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();app.world.s['loc']=1
    app.refresh();app.select('zina');e=app.world.event('duty22_rumour','Неподтверждённый слух.', ['zina'])
    app.decisions()
    def walk(x):
     yield x
     for child in x.children:yield from walk(child)
    top=app.root.children[-1]
    talk=next(c for c in walk(top) if str(c.props.get('text','')).startswith('Обсудить:'))
    talk.props['command']();pop=app.root.children[-1]
    button=next(c for c in walk(pop) if c.props.get('text')=='Уточнить, что видел сам')
    button.props['command']()
    self.assertIsNone(knowledge24.offer(app.world,'zina'))
    app.knowledge_window();self.assertIn('Кто что знает',str([x.props for x in walk(app.root)]))
    self.assertIn('Кто что знает',dict(core.journal(app.world)))
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
