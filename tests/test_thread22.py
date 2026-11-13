"""Four-day quest: schedule, distinct outcomes, witnessed gossip, saves and Tk path."""
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import core,story_data,thread22
from world import World,save

ROOT=Path(__file__).resolve().parents[1]
NPCS=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
IDS=('v22_list_start','v22_list_evidence','v22_list_meeting',
     'v22_list_final_checked','v22_list_final_uncertain')

def world():return World(NPCS,seed=22)
def visit(w,loc,day,hour):
 w.s['loc']=loc;w.s['day']=day;core.C(w)['abs']=day*1440+hour*60

def pick(w,sid,index):
 scene=story_data.SCENES[sid];choice=scene['nodes']['start']['ch'][index]
 result=core.resolve_choice(w,choice);core.finish_scene(w,sid)
 return result

class Script(unittest.TestCase):
 def test_all_stages_window_and_recovery_after_missed_day(self):
  w=world();visit(w,1,2,10);self.assertNotIn(IDS[0],story_data.available(w,1))
  visit(w,1,3,8);self.assertNotIn(IDS[0],story_data.available(w,1))
  visit(w,0,3,10);self.assertIn(IDS[0],story_data.available(w,1)) # map marker
  self.assertNotIn(IDS[0],story_data.available(w,0))
  visit(w,1,5,17);self.assertNotIn(IDS[0],story_data.available(w))
  visit(w,1,6,9);self.assertIn(IDS[0],story_data.available(w))
  pick(w,IDS[0],0)
  self.assertNotIn(IDS[1],story_data.available(w,6))
  visit(w,6,7,16);self.assertNotIn(IDS[1],story_data.available(w))
  visit(w,6,9,8);self.assertIn(IDS[1],story_data.available(w))
  pick(w,IDS[1],0)
  visit(w,10,10,15);self.assertNotIn(IDS[2],story_data.available(w))
  visit(w,10,10,16);self.assertIn(IDS[2],story_data.available(w))
  pick(w,IDS[2],0)
  visit(w,1,11,10);self.assertIn(IDS[3],story_data.available(w));self.assertNotIn(IDS[4],story_data.available(w))
  self.assertIn('Зинаидой',thread22.journal(w)[0])
  pick(w,IDS[3],0);self.assertEqual(thread22.state(w)['stage'],'done')
  self.assertFalse(set(IDS)&set(story_data.available(w)))
  self.assertIn('исправлена',thread22.journal(w)[0])

 def test_verified_correction_recalls_only_real_rumour_and_contacts(self):
  w=world();visit(w,1,3,10);pick(w,IDS[0],1)
  r=thread22.state(w);self.assertEqual(r['choices']['intro'],'spread')
  self.assertTrue(r['rumour_id']);self.assertFalse(w.s['events'][-1]['public'])
  self.assertEqual(w.s['events'][-1]['loc'],1)
  self.assertEqual(w.context('zv')['история_ведомости'],{})
  self.assertEqual(w.context('cal')['история_ведомости'],{})
  self.assertFalse(w.heard('cenz')) # distant contacts cannot hear the same instant
  visit(w,6,4,10);thread22.morning(w)
  self.assertTrue(any(g['root']==r['rumour_id'] and not g['verified'] for g in w.heard('cenz')))
  pick(w,IDS[1],0)
  self.assertTrue(w.context('zv')['история_ведомости']['лично_сверила_список'])
  self.assertEqual(w.s['events'][-1]['witnesses'],['zv'])
  self.assertEqual(w.context('cal')['история_ведомости'],{})
  visit(w,10,5,17);pick(w,IDS[2],0)
  self.assertEqual(w.s['events'][-1]['witnesses'],['cal'])
  visit(w,1,6,10);pick(w,IDS[3],0)
  self.assertEqual(r['outcome'],'correct');self.assertGreater(w.s['relations']['zv'],0)
  corrections=[e for e in w.s['events'] if e['kind']=='duty22_correction']
  self.assertEqual(len(corrections),1)
  self.assertEqual(corrections[0]['loc'],1)
  self.assertFalse(any(g['root']==corrections[0]['id'] for g in w.heard('cenz')))
  visit(w,0,7,8);thread22.morning(w);thread22.morning(w) # delivery once
  self.assertEqual(sum(g['root']==corrections[0]['id'] for g in w.heard('cenz')),1)
  self.assertTrue(any(g['root']==r['rumour_id'] for g in w.heard('cenz'))) # old gossip remains hearsay
  self.assertFalse(any('записк' in str(e).lower() or 'сестр' in str(e).lower() for e in w.s['events'] if e['kind'].startswith('duty22_')))
  self.assertEqual(w.context('kol')['история_ведомости'],{})

 def test_unverified_branch_has_no_fake_correction_and_has_consequences(self):
  w=world();visit(w,1,3,10);pick(w,IDS[0],0)
  self.assertFalse(w.s['gossip']);self.assertEqual(w.s['events'][-1]['witnesses'],['zina'])
  visit(w,6,4,10);pick(w,IDS[1],1)
  self.assertFalse(thread22.state(w)['evidence'])
  visit(w,10,5,17);pick(w,IDS[2],1)
  self.assertEqual(w.s['events'][-1]['loc'],10)
  self.assertNotIn('zina',w.s['events'][-1]['witnesses'])
  visit(w,1,6,10)
  self.assertIn(IDS[4],story_data.available(w));self.assertNotIn(IDS[3],story_data.available(w))
  before=dict(thread22.state(w)['choices'])
  with self.assertRaises(ValueError):thread22.choose(w,'final','correct')
  self.assertEqual(thread22.state(w)['choices'],before)
  pick(w,IDS[4],1)
  self.assertEqual(thread22.state(w)['outcome'],'repeat')
  self.assertLess(w.s['relations']['zv'],0);self.assertLess(w.s['relations']['cal'],0)
  self.assertFalse(w.s['gossip'])
  visit(w,0,7,8);thread22.morning(w)
  self.assertTrue(any(g['root']==w.s['events'][-1]['id'] for g in w.s['gossip']))
  self.assertFalse(any(e['kind']=='duty22_correction' for e in w.s['events']))
  self.assertIn('неподтверждённый',thread22.journal(w)[0])
  with self.assertRaises(ValueError):thread22.choose(w,'final','repeat')

 def test_sleep_delivers_delayed_rumour_once(self):
  w=world();visit(w,1,3,10);pick(w,IDS[0],1)
  root=thread22.state(w)['rumour_id']
  self.assertFalse(w.heard('cenz'))
  core.C(w)['abs']=3*1440+22*60;core.sleep(w)
  self.assertEqual(w.s['day'],4)
  self.assertEqual(sum(g['root']==root for g in w.heard('cenz')),1)
  thread22.morning(w)
  self.assertEqual(sum(g['root']==root for g in w.heard('cenz')),1)

 def test_alternative_silence_and_old_save(self):
  w=world();core.C(w).pop(thread22.KEY,None)
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'old.json';save(w.s,path)
   loaded=World(NPCS,json.loads(path.read_text(encoding='utf8')))
   self.assertEqual(thread22.state(loaded)['stage'],'intro')
  visit(w,1,3,10);pick(w,IDS[0],0)
  visit(w,6,4,9);pick(w,IDS[1],0)
  visit(w,10,5,17);pick(w,IDS[2],0)
  visit(w,1,6,9);pick(w,IDS[3],1)
  self.assertEqual(thread22.state(w)['outcome'],'conceal')
  self.assertFalse(w.s['gossip'])
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'slot.json';save(w.s,path)
   loaded=World(NPCS,json.loads(path.read_text(encoding='utf8')))
   self.assertEqual(thread22.state(loaded)['outcome'],'conceal')
   self.assertEqual(loaded.s['relations'],w.s['relations'])

 def test_finishing_another_local_scene_queues_timed_chapter(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   base=Path(td);shutil.copytree(original/'assets',base/'assets');shutil.copy(original/'npcs.json',base/'npcs.json');env(original,base);main.BASE=base
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide()
    w=app.world;visit(w,6,4,9);r=thread22.state(w)
    r['stage']='evidence';r['days']['intro']=3
    core.C(w)['pending'].clear()
    core.C(w)['done']=[sid for sid,sc in story_data.SCENES.items() if sc['story'] and not sid.startswith('v22_')]
    app.open_scene('v20_craftswoman');app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish()
    self.assertEqual([p['id'] for p in core.C(w)['pending']],[IDS[1]])
    app.pump();self.assertEqual(app.modal.sid,IDS[1]);app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish()
   finally:main.BASE=original

 def test_ui_scene_uses_existing_choices_and_journal(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   base=Path(td);shutil.copytree(original/'assets',base/'assets');shutil.copy(original/'npcs.json',base/'npcs.json');env(original,base);main.BASE=base
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide()
    visit(app.world,1,3,10);core.C(app.world)['pending'].clear()
    self.assertIn(IDS[0],story_data.available(app.world))
    app.open_scene(IDS[0]);self.assertEqual(app.modal.sid,IDS[0])
    app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish()
    self.assertEqual(thread22.state(app.world)['stage'],'evidence')
    self.assertTrue(any(h=='Чужая строка' for h,_ in core.journal(app.world)))
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
