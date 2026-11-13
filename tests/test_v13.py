"""v13: game-owned item icons, real combat upgrades, and two-place comic transitions.

Logical and stub-Tk tests; no claim of a live Windows/GPU render.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import comic_transition,core,equipment13,fight,meta
from world import World
from PIL import Image
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))

def mk(loc=0):
    w=World(NP,meta.new_state(NP),seed=3);w.s['loc']=loc;return w

class Icons(unittest.TestCase):
    def test_distinct_internal_art_for_items_and_weapons(self):
        names=('fist','shiv','armor','bandage','phone','tea','key','letter','parcel','cig','coin','gloves','boots')
        seen=[]
        for name in names:
            path=ROOT/'assets/items'/(name+'.png')
            self.assertTrue(path.is_file(),name)
            with Image.open(path) as im:
                self.assertEqual(im.size,(192,192))
                self.assertEqual(im.mode,'RGBA')
                self.assertGreater(im.getbbox()[2],150)
            seen.append(path.read_bytes())
        self.assertEqual(len(set(seen)),len(names))
        self.assertEqual({r[2] for r in equipment13.offers(mk())}-set(names),set())

class Equipment(unittest.TestCase):
    def test_old_save_uses_previous_damage_and_armor(self):
        w=mk();w.s['gear'].update(weapon='Заточка',damage=28,armor=7)
        self.assertNotIn('combat_upgrades',w.s)
        st=equipment13.stats(w)
        self.assertEqual((st['weapon'],st['damage'],st['armor']),('shiv',28,7))
        self.assertEqual(equipment13.levels(w),{'power':0,'guard':0,'breath':0})

    def test_purchase_deducts_money_once_and_is_capped(self):
        w=mk();w.s['rub']=3000
        for level in range(1,4):
            prev=w.s['rub'];price=equipment13.cost(w,'power')
            self.assertEqual(w.buy('power'),price)
            self.assertEqual(w.s['rub'],prev-price)
            self.assertEqual(equipment13.levels(w)['power'],level)
        self.assertIsNone(equipment13.cost(w,'power'))
        self.assertEqual(next(r for r in equipment13.offers(w) if r[0]=='power')[4],'Предел достигнут')
        with self.assertRaisesRegex(ValueError,'Максимальный'):w.buy('power')
        w.buy('armor');self.assertEqual(w.s['gear']['armor'],7)
        with self.assertRaises(ValueError):w.buy('armor')
        self.assertEqual(len([e for e in w.s['events'] if e['kind']=='purchase']),4)

    def test_price_uses_caste_and_cannot_buy_without_funds(self):
        w=mk();w.s['rub']=0
        with self.assertRaisesRegex(ValueError,'Недостаточно'):w.buy('breath')
        self.assertEqual(equipment13.levels(w)['breath'],0)
        p=equipment13.cost(w,'power')
        core.C(w)['caste']=50
        self.assertLess(equipment13.cost(w,'power'),p)

    def test_weapon_tradeoffs_affect_real_time_fight(self):
        w=mk();base=fight.FightEngine(w,'kol',seed=1)
        w.s['rub']=200
        w.buy('gloves');gloves=fight.FightEngine(w,'kol',seed=1)
        self.assertGreater(gloves.p.speed,base.p.speed)
        self.assertGreater(gloves.crit_bonus,base.crit_bonus)
        w.buy('knife');blade=fight.FightEngine(w,'kol',seed=1)
        self.assertGreater(blade.p.power,gloves.p.power)
        self.assertLess(blade.p.speed,gloves.p.speed)
        self.assertEqual(equipment13.weapon(w),'shiv')
        with self.assertRaises(ValueError):w.buy('knife')

    def test_first_training_unlocks_cooldown_lunge(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight'
        e.press('lunge');self.assertEqual(e.p.state,'idle')  # not bought yet
        w.s['rub']=200;w.buy('power')
        e=fight.FightEngine(w,'kol',seed=1);e.phase='fight'
        before=e.p.x;e.press('lunge')
        self.assertTrue(e.special_ready)
        self.assertEqual(e.p.move,'lunge')
        self.assertGreater(e.p.x,before)
        self.assertEqual(e.special_cd,5)
        e.p.state='idle';e.press('lunge');self.assertEqual(e.special_cd,5)
        for _ in range(300):e.update(1/60);e.think=99
        self.assertLess(e.special_cd,.1)

    def test_training_changes_engine_and_legacy_buy(self):
        w=mk();w.s['rub']=300
        base=fight.FightEngine(w,'kol',seed=1)
        w.buy('power');w.buy('guard');w.buy('breath')
        trained=fight.FightEngine(w,'kol',seed=1)
        self.assertGreater(trained.p.power,base.p.power)
        self.assertEqual(trained.p.armor,base.p.armor+1)
        self.assertGreater(trained.p.regen_bonus,1)
        w.buy('heal');self.assertLess(w.s['rub'],300)

class Travel(unittest.TestCase):
    def test_pair_is_ordered_and_uses_real_backgrounds(self):
        w=mk();a=comic_transition.render(ROOT,w,0,1,(900,510))
        b=comic_transition.render(ROOT,w,1,0,(900,510))
        self.assertEqual(a.size,(900,510))
        self.assertNotEqual(a.tobytes(),b.tobytes())
        self.assertNotEqual(a.getpixel((160,250)),a.getpixel((745,250)))
        for src in range(12):
            for dest in range(12):
                if src==dest:continue
                self.assertTrue(comic_transition.copy(w,src,dest)[0])
                self.assertTrue(comic_transition.copy(w,src,dest)[1])
            panel=comic_transition.render(ROOT,w,src,(src+1)%12,(600,380))
            self.assertEqual(panel.size,(600,380))
        with self.assertRaises(ValueError):comic_transition.render(ROOT,w,0,0)

    def test_past_is_factual_recent_local_event_not_foreign_news(self):
        w=mk();default,_=comic_transition.copy(w,0,1)
        self.assertNotIn('Только что:',default)
        w.event('work','Игрок приготовил паёк.',w.witnesses())
        self.assertIn('Только что: Игрок приготовил паёк.',comic_transition.copy(w,0,1)[0])
        self.assertEqual(w.s['events'][-1]['loc'],0)
        w.s['loc']=2
        w.event('work','Работа на кухне.',w.witnesses())
        self.assertNotIn('кухне',comic_transition.copy(w,0,1)[0])
        w.s['day']+=1
        self.assertEqual(comic_transition.copy(w,0,1)[0],default)

    def test_future_reflects_reign_or_fallen_boss(self):
        w=mk();_,before=comic_transition.copy(w,0,1)
        self.assertIn(NP['polkan']['name'],before)
        core.boss_down(w,'polkan')
        _,after=comic_transition.copy(w,0,1)
        self.assertNotEqual(before,after)
        self.assertIn('Хозяина здесь больше нет',after)
        self.assertEqual(w.s['loc'],0) # preview never actually moves player

if __name__=='__main__':unittest.main()
