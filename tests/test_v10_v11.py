import sys,unittest,random,json,tempfile,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,meta,lore,sound,fight
from world import World
from story_data import SCENES,available
NP=json.loads((Path(__file__).resolve().parents[1]/'npcs.json').read_text(encoding='utf8'))
def mk(d='normal'):return World(NP,meta.new_state(NP,d),seed=3)
def pick(sid,i,w,game=True,rng=None):
    return core.resolve_choice(w,SCENES[sid]['nodes']['start']['ch'][i],game_ok=game,rng=rng or random.Random(1))
def offered(w,act):
    # Локация, где доступно действие: в v11 заточку заказывают в мастерской, в сборке v12 — в оружейной-мастерской.
    for loc in range(len(core.NAMES)):
        w.s['loc']=loc
        if act in [a['id'] for a in core.activities(w)]:return loc
    raise AssertionError(act+' is not offered in any location')
class V10(unittest.TestCase):
    def test_lore_reaches_ai_context(self):
        w=mk();core.apply(w,{'flag':['framed_kol','side_graf','cats_friend']});core.boss_down(w,'zub')
        kol=' '.join(w.context('kol')['lore']);zub=' '.join(w.context('zub')['lore']);gvo=' '.join(w.context('gvo')['lore'])
        self.assertIn('подставили',kol);self.assertIn('Графа',zub);self.assertIn('кошку',gvo);self.assertNotIn('подставили',gvo);self.assertIn('тон',w.context('kol')['player'])
        import ai;self.assertIn('сюжет',ai.PROMPT)
    def test_on_chat_friend_enemy(self):
        w=mk();w.s['relations']['kol']=45;core.on_chat(w,'kol');self.assertTrue(core.has(w,'friend_kol'));w.s['relations']['zub']=-50;core.on_chat(w,'zub');self.assertTrue(core.has(w,'enemy_zub'))
    def test_daily_and_timers(self):
        w=mk();core.C(w)['abs']=23*60;w.s['day']=3;core.sleep(w);c=core.C(w);self.assertTrue(c['timers']);n=len(c['pending']);core.advance(w,c['timers'][0]['at']-c['abs']+1,quiet=True);self.assertGreater(len(core.C(w)['pending']),n)
        for e in core.DAILY:self.assertIn(e[0],SCENES)
    def test_prices_and_variants(self):
        w=mk();c=core.C(w);vals=[]
        for cs in(-80,-40,0,40,80):
            c['caste']=cs;c['ousted']=['zub','graf'] if cs==80 else [];vals.append(core.price(w,100))
        self.assertEqual(vals,sorted(vals,reverse=True));self.assertEqual(core.scene_for(w,'meal'),'meal_high');c['caste']=-80;self.assertEqual(core.scene_for(w,'meal'),'meal_low')
    def test_reactions_by_tier(self):
        w=mk();c=core.C(w)
        def seen_at(cs):
            c['caste']=cs;s=set()
            for i in range(400):
                w.s['turn']+=10;c['pending']=[];core.random_event(w,'travel',force=True);s|={p['id'] for p in c['pending']}
            return s
        a=seen_at(-50);self.assertIn('extort',a);self.assertNotIn('tribute',a);b=seen_at(50);self.assertIn('tribute',b);self.assertNotIn('extort',b)
    def test_exchange_order_parcel(self):
        w=mk();w.s['loc']=7;ids=[a['id'] for a in core.activities(w)];self.assertIn('exchange',ids);offered(w,'order_shiv')
        w.s['cig']=10;pick('order_shiv',0,w);self.assertTrue(core.has(w,'shiv_ordered'));core.advance(w,49*60,quiet=True);self.assertIn('shiv_ready',[p['id'] for p in core.C(w)['pending']])
        w2=mk();core.apply(w2,{'item':{'tea':2}});pick('parcel',0,w2);core.advance(w2,31*60,quiet=True);self.assertIn('parcel_back',[p['id'] for p in core.C(w2)['pending']])
    def test_weakness_flow(self):
        w=mk();w.s['loc']=0;self.assertEqual(core.boss_here(w),'zub');w.s['cig']=5;pick('scout_zub',1,w);self.assertTrue(core.weak_known(w,'zub'))
        r=random.Random(0)
        for _ in range(40):
            if 'zub' in core.C(w)['ousted']:break
            pick('weak_zub',0,w,rng=r)
        self.assertIn('zub',core.C(w)['ousted']);self.assertNotIn('zub',w.witnesses())
    def test_hidden_endings(self):
        w=mk();w.s['day']=12;w.s['loc']=11;self.assertNotIn('shaw_final',list(available(w)));core.apply(w,{'flag':['shaw_hammer','shaw_poster','shaw_ledger','storm_tonight']});w.s['dig']=6;self.assertIn('shaw_final',list(available(w)))
        w.s['loc']=8;core.apply(w,{'flag':['cats_friend','cats_fed'],'rel':{'mat':35}});self.assertIn('c9_cats',list(available(w)))
        w.s['loc']=3;w.s['karma']['honor']=8;core.apply(w,{'flag':'amnesty_hope'});self.assertIn('c9_amnesty',list(available(w)));core.apply(w,{'flag':'framed_kol'});self.assertNotIn('c9_amnesty',list(available(w)))
        w2=mk();core.resolve_choice(w2,SCENES['shaw_final']['nodes']['crawl']['ch'][0],game_ok=True);self.assertEqual(core.C(w2)['ending'],'shaw')
    def test_matryoshka_chain(self):
        w=mk();w.s['day']=4;core.finish_scene(w,'c2_zina');w.s['loc']=1;self.assertIn('m1',list(available(w)))
        for a,b,loc in[('m1','m2',5),('m2','m3',7),('m3','m4',8)]:core.finish_scene(w,a);w.s['loc']=loc;self.assertIn(b,list(available(w)))
    def test_journal_stats_achievements(self):
        w=mk();self.assertGreaterEqual(len(core.journal(w)),5);core.apply(w,{'flag':['framed_kol'],'counter':{'chk_ok':3},'learn_weak':'zub'});st=core.stats(w,10);self.assertIn('Подставили Коляна',st['Ваши выборы'])
        with tempfile.TemporaryDirectory() as d:
            ids={x[0] for x in meta.check_achievements(w,d)};self.assertIn('weak1',ids)
        self.assertGreaterEqual(len(meta.ACH),40)
    def test_sound_generation(self):
        with tempfile.TemporaryDirectory() as d:
            for n in['step','horn','clang','ach','hit','whoosh','block','ko']:
                p=d+'/%s.wav'%n;sound.write_wav(p,sound.make_effect(n));self.assertGreater(wave.open(p).getnframes(),400)
            amb=sound.make_ambient(1,2);self.assertLess(abs(amb[0]-amb[-1]),.25)
class V11Fight(unittest.TestCase):
    def run_fight(self,k,seed,script,limit=240):
        w=mk();e=fight.FightEngine(w,k,seed=seed);r=random.Random(seed);dt=1/60;t=0
        while e.phase!='over' and t<limit:
            t+=dt
            if e.phase=='fight':script(e,r,dt)
            e.update(dt)
        return w,e
    def bot(self,e,r,dt):
        p=e.p;p.dir=0;dist=abs(e.e.x-p.x)
        if dist>88:p.dir=p.face
        elif r.random()<.09:e.press(r.choice(['jab','hook','lowkick','highkick']))
    def test_parts_and_damage(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';e.p.x=300;e.e.x=370
        e.e.parts['arm_l']=e.e.parts['arm_r']=0;self.assertLess(e.e.power,e.e.base_power*.6);e.e.parts['leg_l']=e.e.parts['leg_r']=0;self.assertLess(e.e.speed,e.e.base_speed*.5)
        e.think=99;e.p.attack('highkick')
        for _ in range(60):e.update(1/60)
        self.assertLess(e.e.parts['head'],e.e.pmax['head'])
    def test_ko_and_settle(self):
        w,e=self.run_fight('kol',2,self.bot);self.assertEqual(e.phase,'over');res=e.finish();self.assertEqual(res,e.result);self.assertEqual(e.finish(),res)
        self.assertTrue(any(ev['kind']=='combat' for ev in w.s['events']))
        if res=='Победа':self.assertEqual(w.s['npc_health']['kol'],0)
    def test_block_and_parry(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';e.p.x=300;e.e.x=370;e.p.set_block(True);e.p.block_t=1.0;e.e.attack('hook');hp=e.p.frac()
        for _ in range(40):e.update(1/60);e.think=99
        self.assertLessEqual(hp-e.p.frac(),.03)
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';e.p.x=300;e.e.x=370;e.e.attack('jab');e.p.set_block(True);evs=[]
        for _ in range(20):evs+=e.update(1/60);e.think=99
        self.assertIn('parry',[x['type'] for x in evs]);self.assertGreater(e.e.stun,0);self.assertEqual(e.n_parry,1)
    def test_roll_and_crouch_avoid(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';e.p.x=300;e.e.x=370;e.think=99;e.p.crouch=True;e.e.attack('highkick');h0=e.p.frac()
        for _ in range(60):e.update(1/60);e.think=99
        self.assertEqual(e.p.frac(),h0)
        e.p.crouch=False;e.p.stam=100;self.assertTrue(e.p.roll());self.assertGreater(e.p.inv,0)
    def test_combo_bonus(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';a,d=e.p,e.e;a.x=300;d.x=360;e.think=99;a.combo=['jab','jab'];a.combo_t=0;a.attack('hook');evs=[]
        for _ in range(40):evs+=e.update(1/60);e.think=99
        self.assertIn('combo',[x['type'] for x in evs]);self.assertGreaterEqual(e.n_combo,1)
    def test_cigarette_restores_stamina(self):
        w=mk();w.s['cig']=3;e=fight.FightEngine(w,'kol',seed=1);e.phase='fight';e.p.stam=10;e.press('smoke')
        for _ in range(70):e.update(1/60);e.think=99
        self.assertGreater(e.p.stam,40);self.assertEqual(e.cigs,2);e.finish();self.assertEqual(w.s['cig'],2)
    def test_boss_styles_and_weak_boost(self):
        self.assertEqual(set(fight.STYLES),{'zub','graf','gvo','str','sm','gen','mat','cook'})
        self.assertGreater(fight.STYLES['str']['hp'],fight.STYLES['graf']['hp']);self.assertGreater(fight.STYLES['graf']['dodge'],fight.STYLES['zub']['dodge'])
        def dealt(weak):
            tot=0
            for sd in range(1,25):
                w=mk()
                if weak:core.C(w)['weak'].append('kol')
                e=fight.FightEngine(w,'kol',seed=sd);e.phase='fight';e.p.x=300;e.e.x=370;e.think=99;e.p.attack('hook')
                for _ in range(40):e.update(1/60);e.think=99
                tot+=1-e.e.frac()
            return tot
        self.assertGreater(dealt(True),dealt(False))
    def test_boss_win_ousts_boss(self):
        w=mk();e=fight.FightEngine(w,'zub',seed=1);e.e.parts['head']=0;e.e.ko=True;e.finish_fight('Победа','Нокаут');e.finish();self.assertIn('zub',core.C(w)['ousted'])
    def test_outcomes_vary_and_counters(self):
        res=[self.run_fight('zub',s,self.bot)[1].result for s in range(16)];self.assertTrue(set(res)>={'Победа','Поражение'})
    def test_time_limit(self):
        w=mk();e=fight.FightEngine(w,'kol',seed=1,time_limit=3)
        for _ in range(60*6):e.update(1/60)
        self.assertEqual(e.phase,'over')
if __name__=='__main__':unittest.main()
