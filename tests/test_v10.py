import sys,unittest,random,json,tempfile,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,meta,lore,sound
from world import World
from story_data import SCENES,available
NP=json.loads((Path(__file__).resolve().parents[1]/'npcs.json').read_text(encoding='utf8'))
def mk(d='normal'):return World(NP,meta.new_state(NP,d),seed=3)
def pick(sid,i,w,game=True,rng=None):
    ch=SCENES[sid]['nodes']['start']['ch'][i];return core.resolve_choice(w,ch,game_ok=game,rng=rng or random.Random(1))
def offered(w,act):
    # Локация, где доступно действие: в v11 заточку заказывают в мастерской, в сборке v12 — в оружейной-мастерской.
    for loc in range(len(core.NAMES)):
        w.s['loc']=loc
        if act in [a['id'] for a in core.activities(w)]:return loc
    raise AssertionError(act+' is not offered in any location')
class T(unittest.TestCase):
    def test_lore_reaches_ai_context(self):
        w=mk();core.apply(w,{'flag':['framed_kol','side_graf','cats_friend']});core.boss_down(w,'zub')
        kol=' '.join(w.context('kol')['lore']);zub=' '.join(w.context('zub')['lore']);gvo=' '.join(w.context('gvo')['lore'])
        self.assertIn('подставили',kol);self.assertIn('Графа',zub);self.assertIn('кошку',gvo);self.assertIn('Зубило',gvo)
        self.assertNotIn('подставили',gvo)
        self.assertIn('тон',w.context('kol')['player']);self.assertEqual(lore.npc_lore(mk(),'kol'),[])
    def test_lore_in_prompt(self):
        import ai
        self.assertIn('сюжет',ai.PROMPT)
    def test_on_chat_friend_enemy(self):
        w=mk();w.s['relations']['kol']=45;core.on_chat(w,'kol');self.assertTrue(core.has(w,'friend_kol'));self.assertIn('друзья',' '.join(lore.npc_lore(w,'kol')))
        w.s['relations']['zub']=-50;core.on_chat(w,'zub');self.assertTrue(core.has(w,'enemy_zub'))
    def test_daily_schedule_and_timers(self):
        w=mk();core.C(w)['abs']=23*60;w.s['day']=3;core.sleep(w);c=core.C(w);self.assertTrue(c['timers'] or c['events_done'])
        before=len(c['pending']);t=c['timers'][0]['at'] if c['timers'] else c['abs']+1;core.advance(w,t-c['abs']+1,quiet=True)
        self.assertGreater(len(core.C(w)['pending']),before)
    def test_each_daily_event_exists_and_once(self):
        for e in core.DAILY:self.assertIn(e[0],SCENES)
        w=mk()
        for d in range(2,15):
            w.s['day']=d;core.schedule_day(w)
        self.assertEqual(len(set(core.C(w)['events_done'])),len(core.C(w)['events_done']))
    def test_prices_by_tier(self):
        w=mk();c=core.C(w);vals=[]
        for cs in(-80,-40,0,40,80):
            c['caste']=cs;c['ousted']=['zub','graf'] if cs==80 else [];vals.append(core.price(w,100))
        self.assertEqual(vals,sorted(vals,reverse=True));self.assertEqual(core.scene_for(w,'meal'),'meal_high')
        c['caste']=-80;self.assertEqual(core.scene_for(w,'meal'),'meal_low');self.assertEqual(core.scene_for(w,'trade'),'trade_low')
    def test_reaction_events_by_tier(self):
        w=mk();c=core.C(w);c['caste']=-50;seen=set()
        for i in range(400):
            w.s['turn']+=10;c['pending']=[];core.random_event(w,'travel',force=True)
            for p in c['pending']:seen.add(p['id'])
        self.assertIn('extort',seen);self.assertNotIn('tribute',seen)
        c['caste']=50;seen=set()
        for i in range(400):
            w.s['turn']+=10;c['pending']=[];core.random_event(w,'travel',force=True)
            for p in c['pending']:seen.add(p['id'])
        self.assertIn('tribute',seen);self.assertNotIn('extort',seen)
    def test_exchange_and_order(self):
        w=mk();self.assertIn(core.scene_for(w,'exchange'),SCENES);w.s['loc']=7;ids=[a['id'] for a in core.activities(w)];self.assertIn('exchange',ids);offered(w,'order_shiv')
        w.s['cig']=10;r=pick('order_shiv',0,w);self.assertTrue(core.has(w,'shiv_ordered'));self.assertEqual(w.s['cig'],6)
        core.advance(w,49*60,quiet=True);ids=[p['id'] for p in core.C(w)['pending']];self.assertIn('shiv_ready',ids)
    def test_parcel_roundtrip(self):
        w=mk();core.apply(w,{'item':{'tea':2}});pick('parcel',0,w);self.assertEqual(core.C(w)['inv']['tea'],0);core.advance(w,31*60,quiet=True);self.assertIn('parcel_back',[p['id'] for p in core.C(w)['pending']])
    def test_weakness_flow(self):
        w=mk();w.s['loc']=0;self.assertEqual(core.boss_here(w),'zub');self.assertTrue(any(a['id']=='scout_zub' for a in core.activities(w)))
        w.s['cig']=5;pick('scout_zub',1,w);self.assertTrue(core.weak_known(w,'zub'));self.assertTrue(any(a['id']=='weak_zub' for a in core.activities(w)))
        pick('weak_zub',0,w,rng=random.Random(2));
        r=random.Random(0);
        for _ in range(30):
            if 'zub' in core.C(w)['ousted']:break
            pick('weak_zub',0,w,rng=r)
        self.assertIn('zub',core.C(w)['ousted']);self.assertIn('zub',w.witnesses());self.assertTrue(core.is_former(w,'zub'))
    def test_weakness_boosts_duel(self):
        from world import Duel
        w1,w2=mk(),mk();core.apply(w2,{'learn_weak':'zub'})
        def total(w):
            s=0
            for sd in range(1,25):
                w.s['npc_health']={};w.s['stamina']=100;d=Duel(w,'zub',seed=sd);d.strike(1,1,'attack');s+=120-d.enemy
            return s
        self.assertGreater(total(w2),total(w1))
    def test_hidden_endings_gated(self):
        w=mk();w.s['day']=12;w.s['loc']=11;self.assertNotIn('shaw_final',list(available(w)))
        core.apply(w,{'flag':['shaw_hammer','shaw_poster','shaw_ledger','storm_tonight']});w.s['dig']=6;self.assertIn('shaw_final',list(available(w)))
        w.s['loc']=8;self.assertNotIn('c9_cats',list(available(w)));core.apply(w,{'flag':['cats_friend','cats_fed'],'rel':{'mat':35}});self.assertIn('c9_cats',list(available(w)))
        w.s['loc']=3;self.assertNotIn('c9_amnesty',list(available(w)));w.s['karma']['honor']=8;core.apply(w,{'flag':'amnesty_hope'});self.assertIn('c9_amnesty',list(available(w)));core.apply(w,{'flag':'framed_kol'});self.assertNotIn('c9_amnesty',list(available(w)))
    def test_endings_set_flags(self):
        for sid,end in[('c9_cats','END_cats'),('c9_amnesty','END_amnesty')]:
            w=mk();r=pick(sid,0,w,rng=random.Random(9))
            if r['ok']:self.assertTrue(core.has(w,end));self.assertEqual(r['res']['goto'][:3],'end')
    def test_shaw_final_path(self):
        w=mk();r=core.resolve_choice(w,SCENES['shaw_final']['nodes']['crawl']['ch'][0],game_ok=True);self.assertTrue(core.has(w,'END_shaw'));self.assertEqual(core.C(w)['ending'],'shaw')
    def test_matryoshka_chain(self):
        w=mk();w.s['day']=4;core.finish_scene(w,'c2_zina');w.s['loc']=1;self.assertIn('m1',list(available(w)))
        for a,b,loc in[('m1','m2',5),('m2','m3',7),('m3','m4',8)]:
            core.finish_scene(w,a);w.s['loc']=loc;self.assertIn(b,list(available(w)))
    def test_journal_and_stats(self):
        w=mk();j=core.journal(w);self.assertGreaterEqual(len(j),5);core.apply(w,{'flag':['framed_kol'],'counter':{'chk_ok':3}});st=core.stats(w,10)
        self.assertIn('Подставили Коляна',st['Ваши выборы']);self.assertIn('3 из 3',st['Проверок пройдено'])
    def test_new_achievements(self):
        with tempfile.TemporaryDirectory() as d:
            w=mk();core.apply(w,{'learn_weak':'zub','flag':['END_shaw','kol_bday_done']});ids={x[0] for x in meta.check_achievements(w,d)};self.assertTrue({'weak1','end_shaw','bday'}<=ids)
        self.assertGreaterEqual(len(meta.ACH),40)
    def test_counters_on_checks(self):
        w=mk();rng=random.Random(1)
        for _ in range(10):core.resolve_choice(w,SCENES['c1_intro']['nodes']['start']['ch'][0],rng=rng)
        cn=core.C(w)['counters'];self.assertEqual(cn.get('chk_ok',0)+cn.get('chk_fail',0),10)
    def test_sound_generation(self):
        with tempfile.TemporaryDirectory() as d:
            for n in['step','horn','clang','ach']:
                p=d+'/%s.wav'%n;sound.write_wav(p,sound.make_effect(n));self.assertGreater(wave.open(p).getnframes(),500)
            p=d+'/a.wav';sound.write_wav(p,sound.make_ambient(2,2));self.assertEqual(wave.open(p).getframerate(),sound.RATE)
            amb=sound.make_ambient(1,2);self.assertLess(abs(amb[0]-amb[-1]),.25)
            self.assertFalse(sound.Sound(d).ok or False) if sys.platform!='win32' else None
if __name__=='__main__':unittest.main()
