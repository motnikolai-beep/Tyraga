import sys,unittest,random,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core
from world import World
from story_data import SCENES,available
NP=json.loads((Path(__file__).resolve().parents[1]/'npcs.json').read_text(encoding='utf8'))
def mk():return World(NP,None,seed=1)
class T(unittest.TestCase):
    def test_bed_only_at_night(self):
        w=mk()
        with self.assertRaises(ValueError):core.sleep(w)
        core.C(w)['abs']=23*60;d=w.s['day'];core.sleep(w);self.assertEqual(w.s['day'],d+1);self.assertEqual(core.hhmm(w),'06:00')
    def test_after_midnight_sleep(self):
        w=mk();core.C(w)['abs']=1440+60;core.sleep(w);self.assertEqual(core.hhmm(w),'06:00');self.assertEqual(core.C(w)['abs']//1440,1)
    def test_meal_event_and_talk_time(self):
        w=mk();core.advance(w,90);self.assertTrue(any(p['id']=='meal' for p in core.C(w)['pending']))
        a=core.C(w)['abs'];core.talk(w);core.talk(w);core.talk(w);self.assertGreaterEqual(core.C(w)['abs']-a,7*3+15)
    def test_forced_sleep(self):
        w=mk();core.C(w)['abs']=1440-60;d=w.s['day'];core.advance(w,300);self.assertEqual(w.s['day'],d+1)
    def test_travel_time(self):
        w=mk();a=core.C(w)['abs'];core.travel(w,3);self.assertEqual(core.C(w)['abs']-a,16);self.assertEqual(w.s['loc'],3)
    def test_boss_ousted(self):
        w=mk();b=w.s['relations'].get('graf',0);self.assertIn('zub',w.witnesses());self.assertTrue(core.boss_down(w,'zub'))
        self.assertIn('zub',w.witnesses());self.assertTrue(core.is_former(w,'zub'));self.assertFalse(core.in_power(w,'zub'));self.assertEqual(w.s['relations']['graf']-b,6);self.assertGreater(core.C(w)['caste'],0);self.assertFalse(core.boss_down(w,'zub'))
        self.assertTrue(any(e['kind']=='boss_down' and e['public'] for e in w.s['events']))
    def test_non_boss_not_ousted(self):self.assertFalse(core.boss_down(mk(),'kol'))
    def test_caste_tiers(self):
        w=mk();c=core.C(w);self.assertEqual(core.tier(w)[0],'Мужик')
        c['caste']=-80;self.assertEqual(core.tier(w)[0],'Петух');c['caste']=-40;self.assertEqual(core.tier(w)[0],'Шестёрка')
        c['caste']=80;self.assertEqual(core.tier(w)[0],'Авторитет');c['ousted']=['zub','graf'];self.assertEqual(core.tier(w)[0],'Пахан')
    def test_boost(self):
        w=mk();r=random.Random(5);a=sum(core.check(w,'wis',14,rng=r)['ok'] for _ in range(2000));b=sum(core.check(w,'wis',14,boost=3,rng=r)['ok'] for _ in range(2000));self.assertGreater(b,a)
        self.assertGreater(core.boost_value(w,True,True),core.boost_value(w,False,False))
    def test_temple(self):
        w=mk();w.s['karma']['honor']=-20;core.apply(w,{'cleanse':10});self.assertEqual(w.s['karma']['honor'],-10)
    def test_stash(self):
        w=mk();core.apply(w,{'item':{'shiv':1}});core.stash_move(w,0,'shiv',1);self.assertEqual(core.contraband(w),0)
    def test_story_graph(self):
        for sid,sc in SCENES.items():
            self.assertIn('start',sc['nodes'],sid)
            for nid,n in sc['nodes'].items():
                for ch in n['ch']:
                    for r in (ch['ok'],ch['fail']):
                        if r.get('goto'):self.assertIn(r['goto'],sc['nodes'],sid)
                    if ch.get('chk'):self.assertIn(ch['chk'][0],('wis','cha'))
        for l in range(12):
            w=mk();w.s['loc']=l
            for a in core.activities(w):
                if a['id'] not in('bed','stash') and not a['id'].startswith('mini_'):self.assertIn(core.scene_for(w,a['id']),SCENES)
    def test_everyone_has_scene(self):
        used={n['who'] for sc in SCENES.values() for n in sc['nodes'].values() if n['who']};self.assertEqual(set(NP)-used,set())
        stats={ch['chk'][0] for sc in SCENES.values() for n in sc['nodes'].values() for ch in n['ch'] if ch.get('chk')};self.assertEqual(stats,{'wis','cha'})
        self.assertGreaterEqual(sum(1 for s in SCENES.values() if s['story']),20)
    def test_random_walkthrough(self):
        rng=random.Random(3)
        for sid,sc in SCENES.items():
            for _ in range(20):
                w=mk();w.s['cig']=50;w.s['rub']=200;node='start';n=0
                while node and n<10:
                    chs=sc['nodes'][node]['ch']
                    if not chs:break
                    r=core.resolve_choice(w,rng.choice(chs),game_ok=rng.random()<.5,rng=rng);node=r['res'].get('goto');n+=1
    def test_chain(self):
        w=mk();self.assertEqual(list(available(w)),['c1_intro']);core.finish_scene(w,'c1_intro');self.assertIn('c1_zub_rules',list(available(w)))
    def test_old_save(self):
        w=mk();s=dict(w.s);s.pop('core');self.assertIn('core',World(NP,s).s)
    def test_duel_hook(self):
        from world import Duel
        w=mk();d=Duel(w,'zub',seed=1);d.enemy=0;d.done=True;d.result='Победа';d.finish();self.assertIn('zub',core.C(w)['ousted'])
if __name__=='__main__':unittest.main()
