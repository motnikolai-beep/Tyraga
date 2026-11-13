"""Optional bunk note: provenance, choice, privacy, delayed scene and UI wiring."""
import json,shutil,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
import core,note17,hotspots16
from story_data import SCENES,available
from world import World,save
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=17)

class Note(unittest.TestCase):
 def test_optional_discovery_and_invalid_actions_are_inert(self):
  w=mk();c=core.C(w);before=c['abs'];self.assertNotIn('note17',c['inv'])
  self.assertFalse(note17.state(w)['found']);self.assertEqual(before,c['abs'])
  with self.assertRaises(ValueError):note17.act(w,'show')
  with self.assertRaises(ValueError):note17.act(w,'invent')
  w.s['loc']=1
  with self.assertRaises(ValueError):note17.find(w)
  self.assertFalse(note17.state(w)['found']);w.s['loc']=0
  note17.find(w);self.assertEqual(c['abs'],before+10);self.assertEqual(c['inv']['note17'],1)
  self.assertIn('больше нет',note17.find(w));self.assertEqual(c['abs'],before+10)
  self.assertEqual(w.s['events'][-1]['witnesses'],[])
  self.assertTrue(all(not note17.context(w,k) for k in NP))
  self.assertNotIn('note17_after',list(available(w)))
  self.assertNotIn('note17',c.get('life15',{}).get('letters',{}))

 def test_hide_take_and_only_shket_hears_a_voluntary_show(self):
  w=mk();note17.find(w);note17.act(w,'hide');self.assertFalse(note17.held(w));self.assertTrue(note17.hidden(w))
  with self.assertRaises(ValueError):note17.act(w,'show')
  w.s['loc']=1
  with self.assertRaises(ValueError):note17.act(w,'take')
  w.s['loc']=0;note17.act(w,'take');self.assertTrue(note17.held(w));self.assertFalse(note17.hidden(w))
  before=w.s['relations'].get('kol',0);note17.act(w,'show')
  self.assertEqual(w.s['relations']['kol'],before+5)
  self.assertEqual(note17.act(w,'show'),'Шкет уже видел эту записку.')
  self.assertEqual(w.s['relations']['kol'],before+5)
  self.assertIn('сестры',note17.context(w,'kol')['что_прочёл'])
  self.assertFalse(any(note17.context(w,k) for k in NP if k!='kol'))
  self.assertEqual(w.s['events'][-1]['witnesses'],['kol'])
  self.assertTrue(w.context('kol')['записка_Шкета'])
  self.assertTrue(all(not w.context(k)['записка_Шкета'] for k in NP if k!='kol'))
  for k in NP:
   if k!='kol':self.assertFalse(any(e['kind'].startswith('note17') for e in w.known(k)),k)

 def test_delivery_followup_next_day_only_and_persistence_old_saves(self):
  w=mk();note17.find(w);note17.act(w,'give');d=w.s['day'];self.assertFalse(note17.held(w))
  self.assertEqual(note17.state(w)['given_day'],d)
  self.assertFalse(note17.followup_ready(w));self.assertNotIn('note17_after',list(available(w)))
  with self.assertRaises(ValueError):note17.act(w,'take')
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'save.json';save(w.s,path);loaded=World(NP,json.loads(path.read_text(encoding='utf8')))
   self.assertEqual(note17.state(loaded)['given_day'],d)
   loaded.s['day']+=1
   self.assertTrue(note17.followup_ready(loaded))
   self.assertIn('note17_after',list(available(loaded)))
   self.assertEqual(SCENES['note17_after']['trig']['loc'],0)
   core.finish_scene(loaded,'note17_after');self.assertFalse(note17.followup_ready(loaded))
   old=mk();old.s['core'].pop('note17',None)
   save(old.s,path);restored=World(NP,json.loads(path.read_text(encoding='utf8')))
   self.assertFalse(note17.state(restored)['found']);self.assertFalse(note17.followup_ready(restored))

 def test_real_background_dialog_offers_independent_search_and_choices(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide()
    bed=next(poly for id,_,poly in app.env_shapes if id=='bed')
    x=sum(a for a,_ in bed)/len(bed);y=sum(a for _,a in bed)/len(bed)
    def walk(widget):
     yield widget
     for child in widget.children:yield from walk(child)
    def press(win,label):
     btn=next(c for c in walk(win) if c.props.get('text')==label)
     btn.props['command']()
    app.click(types.SimpleNamespace(x=x,y=y));win=app.env_window
    self.assertFalse(note17.state(app.world)['found']);press(win,'Назад')
    self.assertFalse(note17.state(app.world)['found'])
    app.click(types.SimpleNamespace(x=x,y=y));press(app.env_window,'Проверить край матраса')
    self.assertTrue(note17.held(app.world));self.assertIsNone(app.env_window)
    app.stash_window();win=app.root.children[-1];press(win,'Спрятать записку')
    self.assertTrue(note17.hidden(app.world));press(win,'Забрать записку');self.assertTrue(note17.held(app.world))
    app.npc='kol';app.decisions();win=app.root.children[-1]
    self.assertTrue(any(c.props.get('text')=='Показать чужую записку Шкету' for c in walk(win)))
    press(win,'Передать чужую записку Шкету')
    self.assertFalse(note17.held(app.world));self.assertEqual(note17.state(app.world)['given_day'],app.world.s['day'])
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
