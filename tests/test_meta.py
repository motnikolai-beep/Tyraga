import sys,unittest,random,json,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,meta
from world import World
NP=json.loads((Path(__file__).resolve().parents[1]/'npcs.json').read_text(encoding='utf8'))
def mk(d='normal'):return World(NP,meta.new_state(NP,d),seed=1)
class T(unittest.TestCase):
    def test_env_set_replaces_all_and_keeps_comments(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'.env').write_text('# c\nA=1\nB=2\nA=3\n',encoding='utf8');meta.env_set(d,'A',9);meta.env_set(d,'NEW','x')
            s=Path(d,'.env').read_text(encoding='utf8');self.assertEqual(s.count('A=9'),2);self.assertIn('# c',s);self.assertIn('NEW=x',s)
    def test_settings_clamp_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            s=meta.load_settings(d);self.assertEqual(s['brightness'],1.0);s['brightness']=9;s['autosave_sec']=1;meta.save_settings(d,meta.clamp_settings(s))
            s2=meta.load_settings(d);self.assertEqual(s2['brightness'],1.6);self.assertEqual(s2['autosave_sec'],10)
            Path(d,'settings.json').write_text('{bad',encoding='utf8');self.assertEqual(meta.load_settings(d)['volume'],.7)
    def test_slots(self):
        with tempfile.TemporaryDirectory() as d:
            w=mk('hard');meta.write_state(d,'slot1',w.s,120);sm=meta.summary(d,'slot1');self.assertEqual(sm['diff'],'Строгий режим');self.assertEqual(sm['day'],1);self.assertIsNone(meta.summary(d,'slot2'))
            Path(d,'saves/slot2.json').write_text('oops',encoding='utf8');self.assertIn('error',meta.summary(d,'slot2'))
            with self.assertRaises(ValueError):meta.read_state(d,'slot2')
            meta.write_state(d,'auto',w.s);w.s['day']=5;meta.write_state(d,'auto',w.s);Path(d,'saves/autosave.json').write_text('broken',encoding='utf8');self.assertEqual(meta.load_any(d)['day'],1)
    def test_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(meta.load_any(d));(Path(d)/'saves').mkdir();Path(d,'saves/town_v4.json').write_text(json.dumps({'day':3,'loc':0}),encoding='utf8');self.assertEqual(meta.load_any(d)['day'],3)
    def test_difficulty_effects(self):
        e,n,h=mk('easy'),mk(),mk('hard');self.assertEqual((e.s['cig'],n.s['cig'],h.s['cig']),(25,15,8))
        r=random.Random(1);ok=[sum(core.check(w,'wis',14,rng=r)['ok'] for _ in range(3000)) for w in (e,n,h)];self.assertGreater(ok[0],ok[1]);self.assertGreater(ok[1],ok[2])
        for w in (e,n,h):w.s['rub']=0;core.apply(w,{'rub':20,'hp':-10})
        self.assertGreater(e.s['rub'],n.s['rub']);self.assertGreater(n.s['rub'],h.s['rub']);self.assertGreater(e.s['hp'],h.s['hp'])
        self.assertGreater(core.boost_value(e,False,False),core.boost_value(h,False,False))
    def test_old_save_defaults_normal(self):
        w=World(NP,None);self.assertEqual(core.diff(w)['name'],'Зона')
    def test_achievements_unlock_once(self):
        with tempfile.TemporaryDirectory() as d:
            w=mk();self.assertEqual(meta.check_achievements(w,d),[]);w.s['rub']=300;core.C(w)['ousted']=['zub'];new={x[0] for x in meta.check_achievements(w,d)};self.assertTrue({'rich','boss1'}<=new)
            self.assertEqual(meta.check_achievements(w,d),[]);self.assertIn('rich',meta.ach_store(d)['unlocked'])
            self.assertEqual(len({a[0] for a in meta.ACH}),len(meta.ACH))
    def test_new_state_playable(self):
        w=mk();core.travel(w,3);core.advance(w,60);self.assertGreater(core.C(w)['abs'],420)
if __name__=='__main__':unittest.main()
