"""Calendar, two real residents, opt-in jubilee, non-paid loot and fight equipment."""
import json,shutil,tempfile,types,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
import calendar20,gear20,jubilee19,jubilee20,core
from world import World,save
from fight import FightEngine
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,seed=20)
def set_date(w,m,d,y=2026):w.s['day']=(date(y,m,d)-calendar20.START).days+1

class Calendar(unittest.TestCase):
 def test_fixed_calendar_holidays_birthday_and_old_save(self):
  w=mk();self.assertEqual(calendar20.today(w),calendar20.START)
  for m,d,title in [(10,31,'Хэллоуин'),(11,4,'День народного единства'),(12,25,'Рождество (25 декабря)'),(1,1,'Новый год'),(1,7,'Рождество (7 января)'),(3,8,'8 марта')]:
   y=2027 if m<10 else 2026;set_date(w,m,d,y)
   self.assertTrue(any(x[1]==title for x in calendar20.today_events(w)),title)
  set_date(w,11,2);self.assertIn(('birthday','zv','День рождения: Зоя Заклёпочница'),calendar20.today_events(w))
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'old.json';w.s['core'].pop('calendar20',None);save(w.s,p)
   loaded=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertEqual(calendar20.today(loaded),calendar20.today(w))
   self.assertEqual(calendar20.state(loaded)['celebrated'],[])
   self.assertEqual(loaded.npcs['cal']['portrait'],'cal')

 def test_no_auto_reward_and_event_choices_once_per_year(self):
  w=mk();set_date(w,10,31);name=calendar20.HOLIDAYS[(10,31)][0]
  self.assertEqual(gear20.state(w)['boxes'],0)
  with self.assertRaises(ValueError):calendar20.celebrate(w,'holiday','Новый год','join')
  self.assertEqual(gear20.state(w)['boxes'],0)
  self.assertIn('ящик',calendar20.celebrate(w,'holiday',name,'join'))
  self.assertEqual(gear20.state(w)['boxes'],1)
  self.assertIn('уже',calendar20.celebrate(w,'holiday',name,'observe'))
  self.assertEqual(gear20.state(w)['boxes'],1)
  set_date(w,10,31,2027)
  self.assertIn('ящик',calendar20.celebrate(w,'holiday',name,'join'))
  self.assertEqual(gear20.state(w)['boxes'],2)
  self.assertEqual(w.s['events'][-1]['witnesses'],[])
  feed=len(core.C(w)['feed']);calendar20.notice(w);calendar20.notice(w)
  self.assertEqual(len(core.C(w)['feed']),feed+1)

 def test_birthday_and_collaboration_are_location_and_day_bound(self):
  w=mk();set_date(w,11,2)
  with self.assertRaises(ValueError):calendar20.celebrate(w,'birthday','zv','greet')
  w.s['loc']=6;start=w.s['relations'].get('zv',0);calendar20.celebrate(w,'birthday','zv','gift')
  self.assertEqual(w.s['relations']['zv'],start+5)
  self.assertEqual(w.s['events'][-1]['witnesses'],['zv'])
  self.assertIn('уже',calendar20.celebrate(w,'birthday','zv','greet'))
  calendar20.collaboration(w,'zv');self.assertEqual(gear20.state(w)['scrap'],1)
  self.assertIn('wrap',gear20.state(w)['items'])
  self.assertIn('уже',calendar20.collaboration(w,'zv'))
  set_date(w,11,3);calendar20.collaboration(w,'zv');self.assertEqual(gear20.state(w)['scrap'],2)
  w.s['loc']=10
  with self.assertRaises(ValueError):calendar20.collaboration(w,'cal')
  set_date(w,11,4);calendar20.celebrate(w,'holiday',calendar20.HOLIDAYS[(11,4)][0],'observe')
  calendar20.collaboration(w,'cal');self.assertEqual(gear20.state(w)['boxes'],1)

class Gear(unittest.TestCase):
 def test_rarities_and_boxes_no_real_money_no_duplicate_farming(self):
  w=mk();r=gear20.state(w)
  self.assertEqual([x[1] for x in gear20.RARITIES.values()],[60,28,10,2])
  with self.assertRaises(ValueError):gear20.open_box(w)
  with self.assertRaises(ValueError):gear20.buy_box(w)
  w.s['rub']=25;gear20.buy_box(w);self.assertEqual(w.s['rub'],0)
  out=gear20.open_box(w);self.assertIn('Найдено',out);self.assertEqual(r['boxes'],0)
  self.assertEqual(len(r['items']),1)
  item=next(iter(r['items']));self.assertIn('Дубликат',gear20.give(w,item));self.assertGreater(r['scrap'],0)
  self.assertEqual(len(r['items']),1)
  with self.assertRaises(ValueError):gear20.equip(w,'not_owned')
  self.assertEqual(w.s['events'][-1]['witnesses'],[])

 def test_tenth_box_guarantees_at_least_rare_even_on_common_roll(self):
  w=mk();r=gear20.state(w);r['opened']=9;gear20.award_box(w)
  with patch.object(w.rng,'randrange',side_effect=[0,1]):gear20.open_box(w)
  self.assertEqual(r['opened'],10)
  self.assertEqual({gear20.ITEMS[k][1] for k in r['items']},{'rare'})
  self.assertEqual(core.C(w)['inv']['tea'],1)

 def test_equip_upgrade_really_changes_fight_and_survives_save(self):
  w=mk();base=FightEngine(w,'zub',seed=1);orig=(base.p.base_power,base.p.armor,base.crit_bonus)
  for item in ('master_shiv','keeper','medallion'):gear20.give(w,item);gear20.equip(w,item)
  gear20.state(w)['scrap']=12;w.s['rub']=200
  for _ in range(3):gear20.upgrade(w,'master_shiv')
  with self.assertRaises(ValueError):gear20.upgrade(w,'master_shiv')
  with self.assertRaises(ValueError):gear20.upgrade(w,'not_owned')
  after=FightEngine(w,'zub',seed=1)
  self.assertGreater(after.p.base_power,orig[0]);self.assertGreater(after.p.armor,orig[1]);self.assertGreater(after.crit_bonus,orig[2])
  self.assertLessEqual(gear20.stats(w,__import__('equipment13').stats(w))['damage'],34)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'save.json';save(w.s,p);loaded=World(NP,json.loads(p.read_text(encoding='utf8')))
   self.assertEqual(gear20.state(loaded)['items']['master_shiv'],3)
   self.assertEqual(gear20.state(loaded)['equipped']['weapon'],'master_shiv')
  gear20.unequip(w,'weapon');self.assertEqual(FightEngine(w,'zub',seed=1).p.base_power,orig[0])

class Jubilee(unittest.TestCase):
 def test_opt_in_consent_refusal_and_theme_variants(self):
  for theme in jubilee19.THEMES:
   w=mk();w.s['loc']=10;jubilee19.plan(w,theme)
   with self.assertRaises(ValueError):jubilee20.host(w)
   for loc,k in [(0,'kol'),(4,'steam')]:w.s['loc']=loc;jubilee19.invite(w,k)
   w.s['day']+=1;w.s['loc']=10;jubilee19.rehearse(w)
   with self.assertRaises(ValueError):jubilee20.host(w)
   for loc,k,yes in [(0,'kol',True),(4,'steam',False)]:
    w.s['loc']=loc;jubilee20.consent(w,k,yes)
   self.assertEqual(jubilee20.context(w,'kol')['приглашение_принято'],True)
   self.assertEqual(jubilee20.context(w,'steam')['приглашение_принято'],False)
   w.s['loc']=10;result=jubilee20.host(w)
   self.assertIn('ящик',result);self.assertEqual(gear20.state(w)['boxes'],1)
   if theme=='records':self.assertEqual(len(jubilee20.LINES),20);self.assertIn('20. Последнюю строку',result)
   self.assertIn('уже',jubilee20.host(w));self.assertEqual(gear20.state(w)['boxes'],1)
   self.assertEqual(jubilee20.state(w)['participants'],['kol'])
   self.assertTrue(jubilee19.context(w,'kol')['прошёл_ли_вечер'])
   self.assertIn('состоялся',str(jubilee19.journal(w)))
   self.assertEqual(jubilee20.context(w,'steam')['выступал'],False)
   self.assertIn('состоялся',str(jubilee20.journal(w)))
   self.assertTrue(w.s['events'][-1]['public'])

 def test_ui_calendar_and_wardrobe_and_new_npc_decisions(self):
  from test_ui_stub import Widget,main,env
  original=main.BASE
  with tempfile.TemporaryDirectory() as td,patch.object(main.ImageTk,'PhotoImage',lambda x:object()),patch.object(main.App,'connect',lambda s:None):
   b=Path(td);shutil.copytree(original/'assets',b/'assets');shutil.copy(original/'npcs.json',b/'npcs.json');env(original,b);main.BASE=b
   try:
    app=main.App(Widget());app.new_game('normal');app.menu.hide();set_date(app.world,10,31)
    def walk(item):
     yield item
     for child in item.children:yield from walk(child)
    def press(win,name):next(c for c in walk(win) if c.props.get('text')==name).props['command']()
    app.calendar_window();win=app.root.children[-1];press(win,'Присоединиться · внутриигровой ящик')
    self.assertEqual(gear20.state(app.world)['boxes'],1)
    app.wardrobe();win=app.root.children[-1];press(win,'Открыть ящик')
    self.assertEqual(len(gear20.state(app.world)['items']),1)
    app.world.s['loc']=6;app.refresh();app.select('zv');app.decisions();win=app.root.children[-1]
    press(win,'Совместное дело · ремонт вещей');self.assertIn('wrap',gear20.state(app.world)['items'])
   finally:main.BASE=original

if __name__=='__main__':unittest.main()
