"""The second half of the three-resident story: branch, time, privacy and saves."""
import json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import core,story_data,thread22,follow23
from world import World,save
ROOT=Path(__file__).resolve().parents[1]
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))

def world():return World(NP,seed=23)
def at(w,loc,day,hour):
 w.s.update(loc=loc,day=day);core.C(w)['abs']=day*1440+hour*60

def pick(w,sid,choice):
 ch=next(c for c in story_data.SCENES[sid]['nodes']['start']['ch'] if c['ok']['fx'][('follow23' if sid.startswith('v23_') else 'thread22')][1]==choice)
 out=core.resolve_choice(w,ch);core.finish_scene(w,sid);return out

def earlier(w,rumour='quiet',fact=True,final='conceal'):
 at(w,1,3,10);pick(w,'v22_list_start',rumour)
 at(w,6,4,10);thread22.morning(w);pick(w,'v22_list_evidence','inspect' if fact else 'guess')
 at(w,10,5,17);pick(w,'v22_list_meeting','listen')
 at(w,1,6,10);pick(w,'v22_list_final_checked' if fact else 'v22_list_final_uncertain',final)

class Aftermath(unittest.TestCase):
 def test_quest_waits_for_prior_outcome_and_recovers_after_missed_hours(self):
  w=world();at(w,6,7,9)
  self.assertFalse(any(s.startswith('v23_') for s in story_data.available(w)))
  earlier(w)
  at(w,6,7,7);self.assertNotIn('v23_zoya_known',story_data.available(w))
  at(w,0,7,9);self.assertIn('v23_zoya_known',story_data.available(w,6))
  at(w,6,8,16);self.assertNotIn('v23_zoya_known',story_data.available(w))
  at(w,6,9,9);self.assertIn('v23_zoya_known',story_data.available(w))
  self.assertNotIn('v23_zoya_unknown',story_data.available(w))
  pick(w,'v23_zoya_known','check')
  at(w,10,9,17);self.assertNotIn('v23_tim_fact',story_data.available(w))
  at(w,10,10,17);self.assertIn('v23_tim_fact',story_data.available(w))
  pick(w,'v23_tim_fact','tell')
  at(w,1,11,10);self.assertIn('v23_zina_fact',story_data.available(w))
  pick(w,'v23_zina_fact','correct')
  self.assertEqual(follow23.state(w)['stage'],'done')
  self.assertEqual(follow23.state(w)['outcome'],'correct')
  self.assertFalse(any(s.startswith('v23_') for s in story_data.available(w)))

 def test_existing_evidence_survives_quiet_return_to_zoya(self):
  w=world();earlier(w,'quiet',True,'conceal')
  at(w,6,7,10);pick(w,'v23_zoya_known','step_back')
  self.assertTrue(follow23.state(w)['fact'])
  at(w,10,8,17);self.assertIn('v23_tim_fact',story_data.available(w))
  self.assertNotIn('v23_tim_uncertain',story_data.available(w))

 def test_delayed_correction_and_local_knowledge_only(self):
  w=world();earlier(w,'spread',True,'conceal')
  root=thread22.state(w)['rumour_id'];self.assertTrue(any(g['root']==root for g in w.heard('cenz')))
  at(w,6,7,10);pick(w,'v23_zoya_known','check')
  self.assertEqual(w.s['events'][-1]['witnesses'],['zv'])
  self.assertEqual(follow23.context(w,'cal'),{})
  self.assertTrue(w.context('zv')['после_слуха']['лично_сверила_ведомость'])
  at(w,10,8,17);pick(w,'v23_tim_fact','tell')
  self.assertEqual(w.s['events'][-1]['witnesses'],['cal'])
  at(w,1,9,10);pick(w,'v23_zina_fact','correct')
  correction=w.s['events'][-1]
  self.assertEqual(correction['witnesses'],['zina'])
  self.assertFalse(correction['public'])
  self.assertFalse(any(g['root']==correction['id'] for g in w.heard('cenz')))
  at(w,0,10,8);thread22.morning(w)
  self.assertTrue(any(g['root']==correction['id'] for g in w.heard('cenz')))
  self.assertTrue(any(g['root']==root for g in w.heard('cenz')))
  self.assertEqual(w.context('kol')['после_слуха'],{})
  self.assertFalse(any('записка' in e['text'] or 'сестра' in e['text'] for e in w.s['events'] if e['kind'].startswith('after23_')))

 def test_second_chance_after_unverified_story_and_repeated_claim(self):
  w=world();earlier(w,'quiet',False,'repeat')
  at(w,6,7,10);thread22.morning(w)
  self.assertIn('v23_zoya_unknown',story_data.available(w))
  pick(w,'v23_zoya_unknown','check')
  self.assertTrue(follow23.state(w)['fact'])
  at(w,10,8,17);self.assertIn('v23_tim_fact',story_data.available(w))
  pick(w,'v23_tim_fact','listen')
  at(w,1,9,10);pick(w,'v23_zina_fact','correct')
  prior={e['id'] for e in w.s['events'] if e['kind']=='duty22_repeat'}
  self.assertTrue(any(g['root'] in prior for g in w.s['gossip']))
  at(w,0,10,8);thread22.morning(w)
  self.assertTrue(any(g['root']==w.s['events'][-1]['id'] for g in w.heard('cenz')))

 def test_decline_path_does_not_claim_evidence_and_old_saves_resume(self):
  w=world();earlier(w,'quiet',False,'conceal')
  core.C(w).pop(follow23.KEY,None)
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'old.json';save(w.s,path)
   loaded=World(NP,json.loads(path.read_text(encoding='utf8')))
   self.assertEqual(follow23.state(loaded)['stage'],'zoya')
   w=loaded
   at(w,6,7,9);pick(w,'v23_zoya_unknown','step_back')
   at(w,10,8,17);self.assertIn('v23_tim_uncertain',story_data.available(w))
   before=dict(follow23.state(w)['choices'])
   with self.assertRaises(ValueError):follow23.choose(w,'tim','tell')
   self.assertEqual(follow23.state(w)['choices'],before)
   pick(w,'v23_tim_uncertain','uncertain')
   at(w,1,9,10);self.assertIn('v23_zina_uncertain',story_data.available(w))
   with self.assertRaises(ValueError):follow23.choose(w,'zina','correct')
   pick(w,'v23_zina_uncertain','retract')
   self.assertFalse(any(e['kind']=='after23_correct' for e in w.s['events']))
   self.assertFalse(w.s['gossip'])
   save(w.s,path);reloaded=World(NP,json.loads(path.read_text(encoding='utf8')))
   self.assertEqual(follow23.state(reloaded)['outcome'],'retract')
   self.assertIn('отозвали',follow23.journal(reloaded)[0])

 def test_ui_existing_event_window_and_journal(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   base=Path(td);shutil.copytree(original/'assets',base/'assets');shutil.copy(original/'npcs.json',base/'npcs.json');env(original,base);main.BASE=base
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide()
    w=app.world;earlier(w);at(w,6,7,10);core.C(w)['pending'].clear()
    app.open_scene('v23_zoya_known');self.assertEqual(app.modal.sid,'v23_zoya_known')
    app.modal.pick(app.modal.cur['ch'][0]);app.modal.finish()
    self.assertEqual(follow23.state(w)['stage'],'tim')
    self.assertIn('После слуха',dict(core.journal(w)))
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
