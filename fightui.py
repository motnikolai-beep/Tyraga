
"""Окно боя v11: вид сбоку, векторные бойцы с суставами и анимацией, эффекты ударов, минималистичный HUD."""
import tkinter as tk,time,math,random
from PIL import Image,ImageTk,ImageOps,ImageEnhance
import fight as F
from fight import FightEngine,MOVES,PARTS,PART_NAME,W_ARENA,GROUND
BG='#05080c';PANEL='#101720';FG='#e6edf4';MUTED='#8799ac';GOLD='#e5b767';RED='#c45867';GREEN='#6fcf97'
H_ARENA=470
VK={65:'left',68:'right',83:'crouch',37:'left',39:'right',40:'crouch',74:'jab',75:'hook',85:'lowkick',73:'highkick',76:'block',16:'block',79:'dodge',80:'roll',32:'roll',67:'smoke',81:'retreat',72:'help',27:'pause',13:'enter'}
SYM={'a':'left','d':'right','s':'crouch','left':'left','right':'right','down':'crouch','j':'jab','k':'hook','u':'lowkick','i':'highkick','l':'block','shift_l':'block','o':'dodge','p':'roll','space':'roll','c':'smoke','q':'retreat','h':'help','escape':'pause','return':'enter',
 'cyrillic_ef':'left','cyrillic_ve':'right','cyrillic_yeru':'crouch','cyrillic_o':'jab','cyrillic_el':'hook','cyrillic_ghe':'lowkick','cyrillic_sha':'highkick','cyrillic_de':'block','cyrillic_shcha':'dodge','cyrillic_ze':'roll','cyrillic_es':'smoke','cyrillic_shorti':'retreat','cyrillic_er':'help'}
ENEMY_COL={'zub':'#7a3f3f','graf':'#5f4d86','gvo':'#40633f','str':'#8a9098','sm':'#3b4252','gen':'#505068','mat':'#7a523d','cook':'#b9b9b0','kol':'#5d6a50','zina':'#8a4f6a','buh':'#4d4a42','serg':'#55603f','steam':'#6a7a86','prach':'#6a5d3f'}
SK='#d1a883'
def key_name(e):
    n=VK.get(getattr(e,'keycode',0))
    if n:return n
    return SYM.get(str(getattr(e,'keysym','')).lower())
def lerp(a,b,t):return a+(b-a)*t
def clamp(v,a=0.0,b=1.0):return max(a,min(b,v))
def ease(t):t=clamp(t);return t*t*(3-2*t)
TORSO=62;UA=32;FA=30;TH=38;SH=36;HEAD=13
def F_COL(k):return ENEMY_COL.get(k,'#5a4a3a')

def pose(f,now):
    p={'lean':0.0,'crouch':0.0,'af':(52,150),'ab':(32,132),'lf':(20,6),'lb':(-22,-12),'rot':0.0,'bob':math.sin(now*4+(2 if f.kind=='enemy' else 0))*1.2}
    st=f.state
    if st=='walk':
        sw=math.sin(f.walk_t*11);p['lf']=(20+30*sw,6+16*max(0,-sw));p['lb']=(-22-30*sw,-12-16*max(0,sw));p['bob']=abs(sw)*2
    if f.crouch and st in('idle','walk'):p['crouch']=.65;p['lf']=(55,-15);p['lb']=(-30,-50)
    if st=='attack':
        m=F.MOVES[f.move];su,ac,re=m['startup'],m['active'],m['rec'];t=f.t
        w0=-.2 if su<.15 else -.45
        if t<su:e=w0*ease(t/su)
        elif t<su+ac:e=lerp(w0,1.0,ease((t-su)/ac))
        else:e=1.0-ease((t-su-ac)/re)
        if f.move=='jab':p['af']=(lerp(52,92,e),lerp(150,92,e));p['lean']=10*e
        elif f.move=='hook':p['af']=(lerp(52,112,e),lerp(150,108,e));p['ab']=(lerp(32,10,e),lerp(132,90,e));p['lean']=18*e
        elif f.move=='lowkick':p['lf']=(lerp(20,58,e),lerp(6,64,e));p['lean']=-6*e;p['lb']=(-22,-14)
        elif f.move=='highkick':p['lf']=(lerp(20,118,e),lerp(6,116,e));p['lean']=-24*e;p['af']=(lerp(52,20,e),lerp(150,60,e))
    elif f.blocking:p['af']=(72,172);p['ab']=(55,160);p['lean']=6;p['crouch']=max(p['crouch'],.2)
    elif st=='hit':p['lean']=-22;p['af']=(12,40);p['ab']=(2,24);p['lf']=(30,10);p['lb']=(-30,-20)
    elif st=='ko':
        k=ease(f.t/.55);p['rot']=-85*k;p['af']=(150,160);p['ab']=(120,140);p['lf']=(10,5);p['lb']=(-10,-5)
    elif st=='roll':
        p['rot']=360*clamp(f.t/.55);p['crouch']=.9;p['af']=(100,160);p['ab']=(90,160);p['lf']=(80,-70);p['lb']=(60,-80)
    elif st=='dodge':p['lean']=-22;p['lf']=(35,15);p['lb']=(-35,-25)
    elif st=='smoke':p['af']=(60,176)
    if f.broken('arm_l' if f.face==1 else 'arm_r'):p['af']=(6,12)
    if f.broken('arm_r' if f.face==1 else 'arm_l'):p['ab']=(-4,6)
    if f.broken('leg_l') or f.broken('leg_r'):p['crouch']=max(p['crouch'],.3);p['lb']=(-40,-70)
    if f.dizzy and st in('idle','walk'):p['lean']+=math.sin(now*7)*5
    return p

def skeleton(f,now,gy=GROUND):
    p=pose(f,now);sg=f.face
    def d(a):r=math.radians(a);return (math.sin(r)*sg,math.cos(r))
    c=p['crouch'];lean=math.radians(p['lean']);legs={}
    for nm,(t_a,s_a) in(('lf',p['lf']),('lb',p['lb'])):
        t_a=t_a+45*c;s_a=s_a-40*c
        kx,ky=d(t_a);kx*=TH;ky*=TH;sx,sy=d(s_a);fx=kx+sx*SH;fy=ky+sy*SH;legs[nm]=((0,0),(kx,ky),(fx,fy))
    chest=(math.sin(lean)*sg*TORSO,-math.cos(lean)*TORSO)
    head=(chest[0]+math.sin(lean)*sg*(HEAD+3),chest[1]-math.cos(lean)*(HEAD+3)+p['bob'])
    arms={}
    for nm,(u_a,l_a) in(('af',p['af']),('ab',p['ab'])):
        ux,uy=d(u_a);ex=chest[0]+ux*UA;ey=chest[1]+4+uy*UA;lx,ly=d(l_a);arms[nm]=((chest[0],chest[1]+4),(ex,ey),(ex+lx*FA,ey+ly*FA))
    rot=math.radians(p['rot']*(1 if sg==1 else -1));cx,cy=0,-TORSO*.5
    def R(q):
        if not rot:return q
        x,y=q[0]-cx,q[1]-cy;return (cx+x*math.cos(rot)-y*math.sin(rot),cy+x*math.sin(rot)+y*math.cos(rot))
    legs={k:tuple(R(q) for q in v) for k,v in legs.items()};arms={k:tuple(R(q) for q in v) for k,v in arms.items()}
    chest,head,hip=R(chest),R(head),R((0,0))
    allp=[q for L in list(legs.values())+list(arms.values()) for q in L]+[chest,head,hip]
    off_y=gy-max(q[1] for q in allp)
    def T(q):return (f.x+q[0],q[1]+off_y)
    return {'legs':{k:tuple(T(q) for q in v) for k,v in legs.items()},'arms':{k:tuple(T(q) for q in v) for k,v in arms.items()},'chest':T(chest),'head':T(head),'hip':T(hip)}

class FightWindow:
    HELP=('A/D — ходьба   S — присесть   J — быстрый удар   K — тяжёлый хук   U — быстрый пинок   I — тяжёлый пинок\n'
          'L или Shift — блок (в момент удара = парирование)   O — уклон назад   Пробел/P — кувырок   C — сигарета (выносливость)   Q Q — отступить   Esc — пауза   H — подсказка')
    def __init__(s,app,k,ambush=False):
        s.a=app;s.k=k;s.eng=FightEngine(app.world,k,ambush);app.battle=s.eng;app.battle_window=s
        s.name=app.npcs[k]['name'];s.closed=False;s.paused=False;s.last=time.monotonic();s.now=0.0;s.over_t=0.0;s.help_t=9.0;s.sparks=[];s.texts=[];s.shake=0.0;s.trail=[];s.combo_txt=('',0.0);s.retreat_armed=0.0;s.held=set();s.refs={}
        s.top=app.window('Бой · '+s.name,W_ARENA+24,H_ARENA+24);s.top.configure(bg=BG);s.top.transient(app.root);s.top.grab_set();s.top.protocol('WM_DELETE_WINDOW',s.try_close)
        s.c=tk.Canvas(s.top,width=W_ARENA,height=H_ARENA,bg=BG,highlightthickness=0);s.c.pack(padx=12,pady=12)
        s.top.bind('<KeyPress>',s.on_down);s.top.bind('<KeyRelease>',s.on_up);s.c.bind('<Button-1>',lambda e:s.on_click())
        try:s.top.focus_force()
        except Exception:pass
        s._bg();s.tick()
    def _bg(s):
        try:
            loc=s.a.world.s['loc'];im=Image.open(s.a.base/('assets/loc_%d.jpg'%loc)).convert('RGB');im=ImageOps.fit(im,(W_ARENA,H_ARENA));im=ImageEnhance.Brightness(im).enhance(.32*s.a.settings.get('brightness',1.0));s.refs['bg']=ImageTk.PhotoImage(im)
        except Exception:s.refs['bg']=None
        try:
            im=Image.open(s.a.base/('assets/%s.jpg'%s.a.npcs[s.k]['portrait'])).convert('RGB');im=ImageOps.fit(im,(44,44),centering=(.5,.2));s.refs['pe']=ImageTk.PhotoImage(im)
        except Exception:s.refs['pe']=None
    def on_down(s,e):
        n=key_name(e)
        if not n:return
        if n=='pause':s.paused=not s.paused;return
        if n=='help':s.help_t=9.0 if s.help_t<=0 else 0;return
        if n=='enter' or (n=='roll' and s.eng.phase=='over'):
            if s.eng.phase=='over' and s.over_t>.9:s.close()
            return
        if s.paused:return
        if n in('left','right','crouch','block'):
            s.held.add(n);s.eng.hold(n,True);return
        if n=='retreat':
            if s.retreat_armed>0:s.eng.press('retreat')
            else:s.retreat_armed=1.5;s.texts.append({'x':W_ARENA/2,'y':140,'t':1.5,'text':'Нажмите Q ещё раз, чтобы отступить','color':MUTED,'big':False})
            return
        s.eng.press(n)
    def on_up(s,e):
        n=key_name(e)
        if n in('left','right','crouch','block'):s.held.discard(n);s.eng.hold(n,False)
    def on_click(s):
        if s.eng.phase=='over' and s.over_t>.9:s.close()
    def tick(s,dt=None):
        if s.closed:return
        t=time.monotonic()
        if dt is None:dt=min(.05,t-s.last)
        s.last=t
        if not s.paused:
            s.now+=dt;ev=s.eng.update(dt);s.fx(ev,dt)
            if s.eng.phase=='over':s.over_t+=dt
        s.retreat_armed=max(0,s.retreat_armed-dt);s.help_t=max(0,s.help_t-dt)
        s.draw()
        if not s.closed:s.top.after(16,s.tick)
    def fx(s,events,dt):
        a=s.a;sp=s.sparks
        for ev in events:
            ty=ev['type']
            if ty=='hit':
                y=GROUND-{'head':150,'torso':100,'arm_l':100,'arm_r':100,'leg_l':35,'leg_r':35}[ev['part']]
                col=RED if ev['who']=='player' else GOLD
                for _ in range(10 if ev['heavy'] or ev['crit'] else 6):
                    ang=random.uniform(0,6.28);v=random.uniform(80,260);sp.append({'x':ev['x'],'y':y,'vx':math.cos(ang)*v,'vy':math.sin(ang)*v-60,'t':.35,'c':col})
                s.texts.append({'x':ev['x'],'y':y-20,'t':.9,'text':('КРИТ! ' if ev['crit'] else '')+str(int(round(ev['dmg']))),'color':'#ffd37a' if ev['who']=='enemy' else '#ff7b8c','big':ev['heavy'] or ev['crit']})
                s.shake=max(s.shake,.25 if ev['heavy'] or ev['crit'] else .1);a.sound.play('hit')
            elif ty=='whiff':a.sound.play('whoosh')
            elif ty in('block','parry','guardbreak'):
                s.texts.append({'x':ev['x'],'y':GROUND-130,'t':.8,'text':{'block':'БЛОК','parry':'ПАРИРОВАНИЕ!','guardbreak':'ГАРД ПРОБИТ'}[ty],'color':'#9ad1ff' if ty!='guardbreak' else '#ff9a7a','big':ty!='block'});a.sound.play('block');s.shake=max(s.shake,.08)
            elif ty=='combo' and ev['who']=='player':s.combo_txt=(ev['text']+'!',1.4)
            elif ty=='broken':s.texts.append({'x':ev['x'],'y':GROUND-170,'t':1.3,'text':PART_NAME[ev['part']].upper()+' ВЫВЕДЕНА','color':'#ff9a7a','big':True})
            elif ty=='text':s.texts.append({'x':ev['x'],'y':GROUND-170,'t':.9,'text':ev['text'],'color':ev.get('color',FG),'big':False})
        if s.eng.phase=='over' and s.eng.result and not getattr(s,'_ko_snd',False):
            s._ko_snd=True;a.sound.play('ko')
        for q in sp:q['x']+=q['vx']*dt;q['y']+=q['vy']*dt;q['vy']+=500*dt;q['t']-=dt
        s.sparks=[q for q in sp if q['t']>0]
        for q in s.texts:q['y']-=28*dt;q['t']-=dt
        s.texts=[q for q in s.texts if q['t']>0];s.shake=max(0,s.shake-dt);s.combo_txt=(s.combo_txt[0],max(0,s.combo_txt[1]-dt))
        for f in(s.eng.p,s.eng.e):
            if f.state=='roll':s.trail.append({'x':f.x,'t':.25})
        for q in s.trail:q['t']-=dt
        s.trail=[q for q in s.trail if q['t']>0][-8:]
    def draw(s):
        c=s.c;c.delete('all');e=s.eng;ox=oy=0
        if s.shake>0:ox=random.uniform(-5,5)*s.shake*4;oy=random.uniform(-3,3)*s.shake*4
        if s.refs.get('bg'):c.create_image(0,0,anchor='nw',image=s.refs['bg'])
        else:c.create_rectangle(0,0,W_ARENA,H_ARENA,fill='#0b121a',outline='')
        c.create_rectangle(0,GROUND+4,W_ARENA,H_ARENA,fill='#0a0e13',outline='');c.create_line(0,GROUND+4,W_ARENA,GROUND+4,fill='#2a3d52',width=2)
        for i in range(0,W_ARENA,60):c.create_line(i,GROUND+4,i-60+(i%120),H_ARENA,fill='#10181f')
        for q in s.trail:
            r=4+q['t']*30;c.create_oval(q['x']+ox-r,GROUND-30-r,q['x']+ox+r,GROUND-30+r,fill='#1a2a38',outline='')
        for f in sorted((e.p,e.e),key=lambda f:f.x if f.state!='ko' else -9999):s.fighter(f,ox,oy)
        for q in s.sparks:r=2+q['t']*6;c.create_oval(q['x']+ox-r,q['y']+oy-r,q['x']+ox+r,q['y']+oy+r,fill=q['c'],outline='')
        for q in s.texts:c.create_text(q['x']+ox,q['y']+oy,text=q['text'],fill=q['color'],font=('Segoe UI',18 if q['big'] else 12,'bold'))
        s.hud()
        if e.phase=='intro':c.create_text(W_ARENA/2,150,text=s.name.upper()+'  против  ВАС',fill=GOLD,font=('Segoe UI',26,'bold'))
        elif e.banner=='БОЙ!' and e.time<.9:c.create_text(W_ARENA/2,150,text='БОЙ!',fill=GOLD,font=('Segoe UI',34,'bold'))
        if s.combo_txt[1]>0:c.create_text(W_ARENA/2,110,text=s.combo_txt[0],fill='#ffd37a',font=('Segoe UI',20,'bold'))
        if e.phase=='over':
            win=e.result=='Победа'
            c.create_rectangle(0,170,W_ARENA,300,fill='#05080c',stipple='gray50',outline='')
            c.create_text(W_ARENA/2,205,text=('ПОБЕДА' if win else 'ПОРАЖЕНИЕ' if e.result=='Поражение' else e.result.upper()),fill=GREEN if win else RED if e.result=='Поражение' else GOLD,font=('Segoe UI',34,'bold'))
            c.create_text(W_ARENA/2,255,text=e.reason,fill=FG,font=('Segoe UI',14))
            if s.over_t>.9:c.create_text(W_ARENA/2,285,text='Enter / клик — продолжить',fill=MUTED,font=('Segoe UI',11))
        if s.paused:
            c.create_rectangle(0,0,W_ARENA,H_ARENA,fill='#05080c',stipple='gray50',outline='');c.create_text(W_ARENA/2,200,text='ПАУЗА',fill=GOLD,font=('Segoe UI',34,'bold'));c.create_text(W_ARENA/2,250,text='Esc — продолжить   ·   Q Q — отступить',fill=FG,font=('Segoe UI',12))
        if s.help_t>0:c.create_text(W_ARENA/2,H_ARENA-30,text=s.HELP,fill='#9fb2c6',font=('Segoe UI',9),width=W_ARENA-40,justify='center')
        elif e.phase=='fight':c.create_text(W_ARENA-10,H_ARENA-10,anchor='se',text='H — управление',fill='#3e5368',font=('Segoe UI',9))
    def fighter(s,f,ox,oy):
        c=s.c;sk=skeleton(f,s.now);flash=f.flash>0;base='#e9eef4' if f.kind=='player' else F_COL(s.k)
        def limb_color(p):
            if f.broken(p):return '#4a4f55'
            return '#ffffff' if flash else base
        c.create_oval(f.x+ox-46,GROUND-2+oy,f.x+ox+46,GROUND+12+oy,fill='#06090c',outline='')
        sgn=f.face
        side={'af':'arm_l' if sgn==1 else 'arm_r','ab':'arm_r' if sgn==1 else 'arm_l','lf':'leg_l' if sgn==1 else 'leg_r','lb':'leg_r' if sgn==1 else 'leg_l'}
        def seg(pts,color,w):
            xy=[]
            for q in pts:xy+=[q[0]+ox,q[1]+oy]
            c.create_line(*xy,fill='#06090c',width=w+4,capstyle='round',joinstyle='round');c.create_line(*xy,fill=color,width=w,capstyle='round',joinstyle='round')
        seg(sk['arms']['ab'],limb_color(side['ab']),9);seg(sk['legs']['lb'],limb_color(side['lb']),11)
        hx,hy=sk['hip'];cx,cy=sk['chest']
        seg([sk['hip'],sk['chest']],'#ffffff' if flash else (base if not f.broken('torso') else '#4a4f55'),18)
        if f.kind=='player':
            for i in (.25,.5,.75):
                px=hx+(cx-hx)*i;py=hy+(cy-hy)*i;c.create_line(px+ox-9,py+oy,px+ox+9,py+oy,fill='#37424e',width=2)
        else:c.create_line(hx+ox-8,hy+oy-2,hx+ox+8,hy+oy-2,fill=GOLD,width=2)
        seg(sk['legs']['lf'],limb_color(side['lf']),11);seg(sk['arms']['af'],limb_color(side['af']),9)
        gx,gy=sk['head'];robot=f.kind=='enemy' and s.k=='str'
        hc='#ffffff' if flash else ('#9aa1a8' if robot else SK)
        if robot:
            c.create_rectangle(gx+ox-13,gy+oy-12,gx+ox+13,gy+oy+12,fill=hc,outline='#06090c',width=2);c.create_oval(gx+ox+sgn*4-5,gy+oy-5,gx+ox+sgn*4+5,gy+oy+5,fill='#ff4040' if not f.ko else '#552222',outline='')
        else:
            c.create_oval(gx+ox-HEAD,gy+oy-HEAD,gx+ox+HEAD,gy+oy+HEAD,fill=hc,outline='#06090c',width=2)
            if not f.ko:c.create_oval(gx+ox+sgn*6-2,gy+oy-3,gx+ox+sgn*6+2,gy+oy+1,fill='#111')
            else:c.create_text(gx+ox+sgn*5,gy+oy,text='×',fill='#111',font=('Segoe UI',10,'bold'))
            if f.kind=='player':c.create_arc(gx+ox-HEAD,gy+oy-HEAD,gx+ox+HEAD,gy+oy+HEAD,start=0,extent=180,fill='#2a2f36',outline='')
        if f.state=='attack' and f.t>MOVES[f.move]['startup']*.6 and f.t<MOVES[f.move]['startup']+MOVES[f.move]['active']+.05:
            tip=sk['arms']['af'][2] if f.move in('jab','hook') else sk['legs']['lf'][2]
            for i in range(3):c.create_line(tip[0]+ox-sgn*(30+i*16),tip[1]+oy+(i-1)*6,tip[0]+ox-sgn*(8+i*8),tip[1]+oy+(i-1)*3,fill='#cfd8e3',width=2)
        if f.blocking:
            c.create_arc(f.x+ox+sgn*20-34,GROUND-150+oy,f.x+ox+sgn*20+34,GROUND-40+oy,start=-60 if sgn==1 else 120,extent=120,style='arc',outline='#9ad1ff',width=3)
    def hud(s):
        c=s.c;e=s.eng
        def body(x,y,f):
            def pc(p):
                v=f.pct(p);return '#4a4f55' if v<=0 else '#6fcf97' if v>.66 else '#e5b767' if v>.33 else '#c45867'
            c.create_oval(x+26,y,x+38,y+12,fill=pc('head'),outline='')
            c.create_rectangle(x+24,y+14,x+40,y+38,fill=pc('torso'),outline='')
            c.create_rectangle(x+14,y+14,x+22,y+36,fill=pc('arm_l'),outline='');c.create_rectangle(x+42,y+14,x+50,y+36,fill=pc('arm_r'),outline='')
            c.create_rectangle(x+24,y+40,x+31,y+64,fill=pc('leg_l'),outline='');c.create_rectangle(x+33,y+40,x+40,y+64,fill=pc('leg_r'),outline='')
        def bar(x,w,frac,col,flip,name,f):
            c.create_rectangle(x,14,x+w,34,fill='#0b121a',outline='#2a3d52');fw=w*clamp(frac)
            if flip:c.create_rectangle(x+w-fw,14,x+w,34,fill=col,outline='')
            else:c.create_rectangle(x,14,x+fw,34,fill=col,outline='')
            c.create_text(x+(w-8 if flip else 8),24,anchor='e' if flip else 'w',text=name,fill=FG,font=('Segoe UI',10,'bold'))
            sw=w*clamp(f.stam/f.stam_max);c.create_rectangle(x,38,x+w,43,fill='#0b121a',outline='')
            if flip:c.create_rectangle(x+w-sw,38,x+w,43,fill='#5aa0d8',outline='')
            else:c.create_rectangle(x,38,x+sw,43,fill='#5aa0d8',outline='')
            body(x+(w-70 if flip else 0),50,f)
        bar(14,380,e.p.frac(),'#6fcf97' if e.p.frac()>.35 else RED,False,'ВЫ',e.p)
        bar(W_ARENA-394,380,e.e.frac(),'#e5b767' if e.e.frac()>.35 else RED,True,s.name.upper(),e.e)
        c.create_text(W_ARENA/2,24,text=str(max(0,int(e.limit-e.time))),fill=MUTED,font=('Segoe UI',18,'bold'))
        c.create_text(14,H_ARENA-12,anchor='sw',text='сигарет: %d'%e.cigs,fill='#6d8196',font=('Segoe UI',9))
        if s.refs.get('pe'):c.create_image(W_ARENA-14-380-48,14,anchor='nw',image=s.refs['pe'])
    def try_close(s):
        if s.eng.phase=='over' and s.over_t>.4:s.close()
    def close(s):
        if s.closed:return
        s.closed=True;a=s.a;res=s.eng.finish();a.battle=None
        try:s.top.grab_release();s.top.destroy()
        except tk.TclError:pass
        a.persist();a.refresh()
        a.status.config(text={'Победа':'Победа над %s.'%s.name,'Поражение':'Вы проиграли бой.','Ничья':'Бой закончился вничью.','Отступление':'Вы отступили.'}.get(res,res))
        a.initiative('combat_finished')
