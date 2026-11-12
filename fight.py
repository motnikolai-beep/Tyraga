
"""Боевой движок v11: реальное время, вид сбоку, здоровье по частям тела, быстрые/тяжёлые удары, блок, парирование,
контратаки, перекат, комбо. Без tkinter — полностью тестируется отдельно."""
import random
import core
W_ARENA=960;GROUND=400
PARTS=['head','torso','arm_l','arm_r','leg_l','leg_r']
PMAX={'head':56.0,'torso':140.0,'arm_l':56.0,'arm_r':56.0,'leg_l':70.0,'leg_r':70.0}
WEIGHT={'head':.25,'torso':.40,'arm_l':.075,'arm_r':.075,'leg_l':.10,'leg_r':.10}
PART_NAME={'head':'голова','torso':'корпус','arm_l':'левая рука','arm_r':'правая рука','leg_l':'левая нога','leg_r':'правая нога'}
PART_MULT={'head':1.4,'torso':1.0,'arm_l':.7,'arm_r':.7,'leg_l':.8,'leg_r':.8}
MOVES={
 'jab':{'key':'J','name':'Быстрый удар рукой','h':'high','startup':.07,'active':.08,'rec':.14,'reach':82,'dmg':6,'stam':6,'parts':[('head',.6),('torso',.4)],'kb':10,'stun':.26},
 'hook':{'key':'K','name':'Тяжёлый хук','h':'mid','startup':.30,'active':.10,'rec':.34,'reach':92,'dmg':16,'stam':16,'parts':[('torso',.65),('arm_l',.175),('arm_r',.175)],'kb':34,'stun':.45},
 'lowkick':{'key':'U','name':'Быстрый удар ногой','h':'low','startup':.12,'active':.09,'rec':.20,'reach':100,'dmg':8,'stam':9,'parts':[('leg_l',.5),('leg_r',.5)],'kb':14,'stun':.30},
 'highkick':{'key':'I','name':'Тяжёлый пинок в голову','h':'high','startup':.38,'active':.12,'rec':.42,'reach':112,'dmg':20,'stam':20,'parts':[('head',1.0)],'kb':40,'stun':.55},
}
COMBOS={('jab','jab','hook'):('Двойка-хук',1.25),('lowkick','lowkick','highkick'):('Подсечка-вертушка',1.35),('jab','hook','highkick'):('Лестница',1.30),('hook','highkick'):('Разрушитель',1.20),('jab','jab','jab'):('Серия',1.15)}
STYLES={
 'zub':dict(aggr=.62,heavy=.6,block=.30,dodge=.04,roll=.0,pref=85,think=.22,speed=.85,hp=1.3,power=1.15,armor=2,kite=0),
 'graf':dict(aggr=.5,heavy=.2,block=.25,dodge=.45,roll=.25,pref=95,think=.12,speed=1.15,hp=1.1,power=1.0,armor=0,kite=.4),
 'gvo':dict(aggr=.5,heavy=.35,block=.5,dodge=.1,roll=.0,pref=85,think=.18,speed=1.0,hp=1.2,power=1.0,armor=3,kite=0),
 'str':dict(aggr=.45,heavy=.75,block=.45,dodge=0,roll=0,pref=80,think=.30,speed=.7,hp=1.6,power=1.3,armor=5,kite=0),
 'sm':dict(aggr=.55,heavy=.15,block=.2,dodge=.35,roll=.15,pref=105,think=.11,speed=1.25,hp=1.1,power=1.0,armor=0,kite=.5),
 'gen':dict(aggr=.35,heavy=.3,block=.7,dodge=.1,roll=0,pref=90,think=.16,speed=1.0,hp=1.15,power=1.05,armor=2,kite=.1),
 'mat':dict(aggr=.5,heavy=.4,block=.4,dodge=.1,roll=0,pref=93,think=.2,speed=.95,hp=1.2,power=1.1,armor=1,kite=.1),
 'cook':dict(aggr=.25,heavy=.5,block=.75,dodge=.05,roll=0,pref=85,think=.25,speed=.8,hp=1.1,power=1.2,armor=1,kite=0),
 # v12, хозяева локаций. Полкан — тяжёлый служака в ватнике; Хлеборез — медленный, бьёт редко и больно, закрывается;
 # Кипяток — голый напор: быстрые серии, много здоровья, никакой защиты; Цензор — уходит от ударов и держит дистанцию.
 'polkan':dict(aggr=.58,heavy=.5,block=.4,dodge=.05,roll=0,pref=88,think=.2,speed=.9,hp=1.3,power=1.1,armor=3,kite=0),
 'hleb':dict(aggr=.4,heavy=.7,block=.55,dodge=.05,roll=0,pref=82,think=.26,speed=.78,hp=1.35,power=1.25,armor=2,kite=0),
 'kip':dict(aggr=.7,heavy=.15,block=.15,dodge=.2,roll=.1,pref=90,think=.12,speed=1.2,hp=1.45,power=.95,armor=0,kite=.1),
 'cenz':dict(aggr=.55,heavy=.2,block=.3,dodge=.45,roll=.2,pref=100,think=.13,speed=1.15,hp=1.15,power=1.1,armor=0,kite=.45),
}
DEFAULT_STYLE=dict(aggr=.5,heavy=.3,block=.3,dodge=.15,roll=.05,pref=85,think=.2,speed=1.0,hp=1.0,power=.9,armor=0,kite=.1)

class Fighter:
    def __init__(s,kind,x,face,hpfrac=1.0,stamina=100,power=1.0,armor=0,speed=1.0,hpmult=1.0):
        s.kind=kind;s.x=float(x);s.face=face;s.state='idle';s.t=0.0;s.move=None;s.hit_done=False;s.blocking=False;s.block_t=9.0;s.crouch=False
        s.hpmult=hpmult;s.parts={p:PMAX[p]*hpmult*max(.02,hpfrac) for p in PARTS};s.pmax={p:PMAX[p]*hpmult for p in PARTS}
        s.stam_max=float(max(60,stamina));s.stam=float(stamina);s.base_power=power;s.armor=armor;s.base_speed=speed;s.stun=0.0;s.inv=0.0;s.counter=0.0
        s.stun_len=.3;s.combo=[];s.combo_t=9.0;s.dir=0;s.vx=0.0;s.flash=0.0;s.ko=False;s.roll_dir=1;s.walk_t=0.0;s.cigs_used=0
    def pct(s,p):return max(0.0,s.parts[p]/s.pmax[p])
    def frac(s):return sum(WEIGHT[p]*s.pct(p) for p in PARTS)
    def broken(s,p):return s.parts[p]<=0
    @property
    def power(s):
        arms=(s.pct('arm_l')+s.pct('arm_r'))/2;return s.base_power*(.55+.45*arms)
    @property
    def speed(s):
        legs=(s.pct('leg_l')+s.pct('leg_r'))/2;return s.base_speed*(.45+.55*legs)
    @property
    def regen(s):return 16*(.5+.5*s.pct('torso'))
    @property
    def dizzy(s):return s.pct('head')<.35
    def busy(s):return s.state not in('idle','walk')
    def attack(s,name):
        m=MOVES[name]
        if s.busy() or s.ko or s.stam<m['stam']*.4:return False
        s.state='attack';s.move=name;s.t=0.0;s.hit_done=False;s.blocking=False;s.stam=max(0.0,s.stam-m['stam']);return True
    def set_block(s,on):
        if s.ko:return
        if on and not s.blocking and not s.busy():s.blocking=True;s.block_t=0.0
        elif not on:s.blocking=False
    def dodge(s,away):
        if s.busy() or s.ko or s.stam<10:return False
        s.state='dodge';s.t=0.0;s.stam-=10;s.inv=.22;s.vx=-s.face*260*(1 if away else -.5);s.blocking=False;return True
    def roll(s):
        if s.busy() or s.ko or s.stam<22:return False
        s.state='roll';s.t=0.0;s.stam-=22;s.inv=.42;s.blocking=False;s.roll_dir=s.face;return True
    def smoke(s):
        if s.busy() or s.ko:return False
        s.state='smoke';s.t=0.0;s.blocking=False;return True

class FightEngine:
    def __init__(s,w,k,ambush=False,seed=None,time_limit=90.0):
        s.w=w;s.k=k;s.rng=random.Random(seed);S=w.s;s.settled=False;g=S['gear']
        style=STYLES.get(k,DEFAULT_STYLE);s.style=style;boss=w.npcs[k].get('boss',False)
        mx=120 if boss else 90;ef=max(.02,min(1.0,S['npc_health'].get(k,mx)/mx));pf=max(.02,min(1.0,S['hp']/100))
        s.p=Fighter('player',W_ARENA*.32,1,pf,min(S['stamina'],S['stamina_max']),g['damage']/16.0,g['armor'],1.0,1.0)
        s.e=Fighter('enemy',W_ARENA*.68,-1,ef,70+20*boss,style['power'],style['armor'],style['speed'],style['hp']*(1.15 if boss else .9))
        s.weak=core.weak_known(w,k);s.cigs=S['cig'];s.time=0.0;s.limit=time_limit;s.phase='intro';s.intro=1.6;s.events=[];s.result=None;s.reason='';s.hitstop=0.0
        s.think=0.0;s.block_hold=0.0;s.banner='';s.n_parry=0;s.n_combo=0;s.n_limb=0
        if ambush:s._damage(s.p,'torso',12,s.e,silent=True)
    def press(s,name):
        if s.phase!='fight' or s.p.ko:return
        p=s.p
        if name in MOVES:p.attack(name)
        elif name=='roll':p.roll()
        elif name=='dodge':p.dodge(True)
        elif name=='smoke':
            if s.cigs>0 and p.smoke():s.cigs-=1;p.cigs_used+=1
        elif name=='retreat':s.finish_fight('Отступление','Вы отступили')
    def hold(s,name,on):
        if name=='block':s.p.set_block(on)
        elif name=='crouch':s.p.crouch=bool(on)
        elif name=='left':s.p.dir=-1 if on else (0 if s.p.dir==-1 else s.p.dir)
        elif name=='right':s.p.dir=1 if on else (0 if s.p.dir==1 else s.p.dir)
    def update(s,dt):
        s.events=[]
        if s.phase=='intro':
            s.intro-=dt
            if s.intro<=0:s.phase='fight';s.banner='БОЙ!'
            return s.events
        if s.phase!='fight':
            for f in(s.p,s.e):s._tick_fighter(f,dt)
            return s.events
        if s.hitstop>0:s.hitstop-=dt;return s.events
        s.time+=dt
        s._ai(dt)
        for f,o in((s.p,s.e),(s.e,s.p)):s._tick_fighter(f,dt,o)
        if s.time>=s.limit and s.phase=='fight':
            pf,ef=s.p.frac(),s.e.frac()
            if abs(pf-ef)<.08:s.finish_fight('Ничья','Время вышло: ничья')
            else:s.finish_fight('Победа' if pf>ef else 'Поражение','Время вышло: победа по очкам' if pf>ef else 'Время вышло: поражение по очкам')
        return s.events
    def _tick_fighter(s,f,dt,o=None):
        f.t+=dt;f.block_t+=dt;f.combo_t+=dt;f.flash=max(0,f.flash-dt);f.stun=max(0,f.stun-dt);f.inv=max(0,f.inv-dt);f.counter=max(0,f.counter-dt)
        if f.combo_t>.95:f.combo=[]
        if f.ko:f.vx*=.9;f.x+=f.vx*dt;f.x=max(40,min(W_ARENA-40,f.x));return
        if f.state in('idle','walk'):
            f.stam=min(f.stam_max,f.stam+(f.regen*(.55 if f.blocking else 1))*dt)
        if o is not None and f.state not in('roll',):f.face=1 if o.x>f.x else -1
        f.x+=f.vx*dt;f.vx*=max(0,1-7*dt)
        if f.state in('idle','walk'):
            if f.dir and not f.blocking and not f.crouch and f.stun<=0:
                sp=190*f.speed*(1.0 if f.dir==f.face else .75);f.x+=f.dir*sp*dt;f.state='walk';f.walk_t+=dt
            else:f.state='idle'
        elif f.state=='attack':
            m=MOVES[f.move]
            if not f.hit_done and f.t>=m['startup']:
                f.hit_done=True;s._resolve(f,o,m)
            if f.state=='attack' and f.t>=m['startup']+m['active']+m['rec']:f.state='idle'
        elif f.state=='dodge':
            if f.t>=.3:f.state='idle'
        elif f.state=='roll':
            f.x+=f.roll_dir*430*dt
            if f.t>=.55:f.state='idle';f.face=1 if (o and o.x>f.x) else -1
        elif f.state=='hit':
            if f.t>=f.stun_len:f.state='idle'
        elif f.state=='smoke':
            if f.t>=.8:
                f.state='idle';f.stam=min(f.stam_max,f.stam+45);s.events.append({'type':'text','x':f.x,'text':'+выносливость','color':'#e5b767'})
        if o is not None and f.state!='roll' and o.state!='roll':
            gap=abs(o.x-f.x)
            if gap<54:
                push=(54-gap)/2;sg=1 if f.x<=o.x else -1;f.x-=sg*push;o.x+=sg*push
        f.x=max(40,min(W_ARENA-40,f.x))
    def _resolve(s,a,d,m):
        reach=m['reach']*(0.7 if a.dizzy and s.rng.random()<.25 else 1.0)
        dist=abs(d.x-a.x)
        if d.ko or d.inv>0 or d.state=='roll' or dist>reach:
            s.events.append({'type':'whiff','x':a.x,'who':a.kind});return
        if d.crouch and m['h']=='high':
            s.events.append({'type':'text','x':d.x,'text':'присел','color':'#8799ac'});return
        a.combo.append(a.move);a.combo=a.combo[-4:];a.combo_t=0.0
        mult=1.0;cname=None
        for pat,(nm,mu) in COMBOS.items():
            if tuple(a.combo[-len(pat):])==pat:mult=max(mult,mu);cname=nm
        if cname:
            s.events.append({'type':'combo','who':a.kind,'text':cname})
            if a.kind=='player':s.n_combo+=1
        if d.blocking and d.state in('idle','walk'):
            if d.block_t<=.16:
                a.state='hit';a.t=0;a.stun_len=.6;a.stun=.6;d.counter=1.1;a.combo=[]
                if d.kind=='player':s.n_parry+=1
                s.events.append({'type':'parry','x':d.x,'who':d.kind});return
            cost=m['dmg']*1.1
            if d.stam>=cost:
                d.stam-=cost;d.vx=a.face*m['kb']*3;s.events.append({'type':'block','x':d.x,'who':d.kind})
                part=s._pick(m);s._damage(d,part,m['dmg']*a.power*.18,a,silent=True);return
            d.stam=0;d.blocking=False;d.state='hit';d.t=0;d.stun_len=.7;d.stun=.7;s.events.append({'type':'guardbreak','x':d.x,'who':d.kind});mult*=.8
        part=s._pick(m);dmg=m['dmg']*a.power*mult
        if a.counter>0:dmg*=1.5;a.counter=0;s.events.append({'type':'text','x':a.x,'text':'КОНТРАТАКА','color':'#e5b767'})
        if a.kind=='player' and s.weak:dmg*=1.35
        crit=s.rng.random()<.08
        if crit:dmg*=1.5
        s._damage(d,part,dmg,a,m,crit)
    def _pick(s,m):
        r=s.rng.random();acc=0
        for p,wt in m['parts']:
            acc+=wt
            if r<=acc:return p
        return m['parts'][-1][0]
    def _damage(s,d,part,dmg,a,m=None,crit=False,silent=False):
        dmg=dmg*PART_MULT[part]*(1-min(.5,d.armor*.04))
        before=d.parts[part];d.parts[part]=before-dmg;d.flash=.12
        if not silent:
            d.state='hit';d.t=0;d.stun_len=(m['stun']*(1.3 if part=='head' else 1.0)) if m else .3;d.stun=d.stun_len;d.vx=a.face*(m['kb'] if m else 10)*6;d.blocking=False
            s.hitstop=.045 if not crit else .08
            s.events.append({'type':'hit','x':d.x,'part':part,'dmg':round(dmg,1),'who':d.kind,'crit':crit,'heavy':bool(m and m['dmg']>=15)})
        if before>0 and d.parts[part]<=0:
            s.events.append({'type':'broken','x':d.x,'part':part,'who':d.kind})
            if d.kind=='enemy':s.n_limb+=1
        if d.parts['head']<=0 or d.parts['torso']<=0 or d.frac()<=.1:
            d.ko=True;d.state='ko';d.t=0;d.vx=-d.face*160
            s.finish_fight('Победа' if d is s.e else 'Поражение','Нокаут' if (d.parts['head']<=0 or d.parts['torso']<=0) else 'Технический нокаут')
    def _ai(s,dt):
        e,p,st=s.e,s.p,s.style
        if e.ko or e.stun>0 or e.busy():return
        s.think-=dt
        if s.block_hold>0:
            s.block_hold-=dt
            if s.block_hold<=0:e.set_block(False)
        e.dir=0
        if s.think>0:return
        s.think=st['think']*s.rng.uniform(.8,1.3)
        dist=abs(p.x-e.x);rng=s.rng.random
        threat=p.state=='attack' and dist<=MOVES[p.move]['reach']+30
        if threat and not e.blocking:
            r=rng()
            if r<st['block']:e.set_block(True);s.block_hold=.45;return
            if r<st['block']+st['dodge']:e.dodge(True);return
            if r<st['block']+st['dodge']+st['roll']:e.roll();return
        if e.stam<22:
            e.set_block(True);s.block_hold=.6;e.dir=-e.face if dist<90 else 0;return
        if e.counter>0 or (p.state=='attack' and p.t>MOVES[p.move]['startup']+MOVES[p.move]['active']) or p.state=='hit':
            if dist<=MOVES['hook']['reach']-4:e.attack('jab' if rng()>.4 else 'hook');return
        pref=st['pref']
        if dist>pref+10:e.dir=e.face;return
        if dist<pref-35 and rng()<st['kite']+.15:e.dir=-e.face;return
        if rng()<st['aggr']:
            r=rng()
            if r<st['heavy']:name='highkick' if rng()<.35 else 'hook'
            elif p.crouch:name='lowkick'
            else:name=s.rng.choice(['jab','jab','lowkick'])
            if dist>MOVES[name]['reach']-6:e.dir=e.face;s.think=.05;return
            e.attack(name)
        elif rng()<.25 and not e.blocking:e.set_block(True);s.block_hold=.35
    def finish_fight(s,res,reason=''):
        if s.phase=='over':return
        s.phase='over';s.result=res;s.reason=reason;s.banner=reason or res;s.p.blocking=False;s.e.blocking=False
    def finish(s):
        if s.settled:return s.result
        if s.phase!='over':s.finish_fight('Отступление','Вы отступили')
        s.settled=True;w=s.w;S=w.s;k=s.k;res=s.result
        S['hp']=max(1,int(round(s.p.frac()*100)));S['stamina']=max(0,int(min(S['stamina_max'],s.p.stam)));S['cig']=max(0,S['cig']-s.p.cigs_used)
        mx=120 if w.npcs[k].get('boss') else 90
        S['npc_health'][k]=0 if res=='Победа' else max(1,int(round(s.e.frac()*mx)))
        if res=='Поражение':S['rub']=max(0,S['rub']-15)
        if res=='Победа':
            if k not in S['defeated']:S['rub']+=40;S['defeated'].append(k)
            else:S['rub']+=5
        cn=core.C(w)['counters'];cn['parry']=cn.get('parry',0)+s.n_parry;cn['combo']=cn.get('combo',0)+s.n_combo;cn['limb_broken']=cn.get('limb_broken',0)+s.n_limb
        S['turn']+=1;w.event('combat','Бой с '+w.npcs[k]['name']+': '+res,[k]);core.on_duel(w,k,res)
        return res
