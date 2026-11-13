
"""Окна v8: сюжетные сцены, всплывающие мини-игры, карта зоны."""
import tkinter as tk,random
from PIL import Image,ImageTk,ImageOps,ImageDraw,ImageEnhance
from gfx import open_rgb
import core,ui_layout
from story_data import SCENES
BG='#090d12';PANEL='#101720';CARD='#182331';FG='#e6edf4';MUTED='#8799ac';GOLD='#e5b767';RED='#c45867';GREEN='#6fcf97'
STATN={'wis':'МУДР','cha':'ХАР'}

def chance(w,st,dc,bonus=0):
    need=dc+core.diff(w)['dc']-core.mod(w,st)-bonus;return max(.05,min(1.0,(21-need)/20))

class EventWindow:
    def __init__(s,app,sid,vars=None):
        s.a=app;s.w=app.world;s.sid=sid;s.sc=SCENES[sid];s.vars=vars or {};s.done=False;s.cur=None
        app.modal=s;s.top=app.window(s.sc.get('title',sid),900,680);s.top.transient(app.root);s.top.grab_set();s.top.protocol('WM_DELETE_WINDOW',lambda:None)
        s.top.columnconfigure(1,weight=1);s.top.rowconfigure(0,weight=1)
        s.left=tk.Frame(s.top,bg=PANEL,width=250);s.left.grid(row=0,column=0,sticky='ns',padx=(12,0),pady=12)
        s.portrait=tk.Label(s.left,bg=PANEL);s.portrait.pack(padx=8,pady=8);s.who=tk.Label(s.left,bg=PANEL,fg=GOLD,font=('Segoe UI',13,'bold'));s.who.pack()
        s.stats=tk.Label(s.left,bg=PANEL,fg=MUTED,font=('Segoe UI',9),justify='left');s.stats.pack(pady=12,padx=8,anchor='w')
        s.right=tk.Frame(s.top,bg=PANEL);s.right.grid(row=0,column=1,sticky='nsew',padx=12,pady=12);s.right.columnconfigure(0,weight=1);s.right.rowconfigure(0,weight=1);s.right.rowconfigure(2,weight=1)
        s.text=tk.Text(s.right,wrap='word',bg='#0b1119',fg=FG,relief='flat',font=('Segoe UI',12),padx=14,pady=12,height=2);s.text.grid(row=0,column=0,sticky='nsew')
        text_bar=tk.Scrollbar(s.right,command=s.text.yview);text_bar.grid(row=0,column=1,sticky='ns');s.text.config(yscrollcommand=text_bar.set)
        width,height=getattr(s.top,'_layout_size',(900,680));s.choice_wrap=ui_layout.text_wrap(width-290,32)
        s.res_outer=tk.Frame(s.right,bg=PANEL);s.res_outer.grid(row=1,column=0,sticky='ew',pady=4)
        results,s.res_body=ui_layout.scroll_frame(s.res_outer,PANEL,height=72);results.pack(fill='both',expand=True)
        s.res=tk.Label(s.res_body,bg=PANEL,fg=GREEN,font=('Segoe UI',10),justify='left',wraplength=s.choice_wrap,anchor='w');s.res.pack(fill='x')
        s.opts_outer=tk.Frame(s.right,bg=PANEL);s.opts_outer.grid(row=2,column=0,sticky='nsew')
        scroll,s.opts=ui_layout.scroll_frame(s.opts_outer,PANEL,height=max(110,min(220,height//3)));scroll.pack(fill='both',expand=True)
        s.top.bind('<Configure>',s.resize)
        s.boostrow=tk.Frame(s.right,bg=PANEL);s.boostrow.grid(row=3,column=0,sticky='ew',pady=4)
        s.smoke=tk.BooleanVar(value=False);s.focus=tk.BooleanVar(value=False)
        tk.Checkbutton(s.boostrow,text='Закурить перед проверкой (−1 сиг., +2)',variable=s.smoke,bg=PANEL,fg=MUTED,selectcolor=CARD,activebackground=PANEL,command=s.redraw).pack(anchor='w')
        tk.Checkbutton(s.boostrow,text='Собраться (−8 сил, +1)',variable=s.focus,bg=PANEL,fg=MUTED,selectcolor=CARD,activebackground=PANEL,command=s.redraw).pack(anchor='w')
        s.refs={};s.show('start')
    def resize(s,e):
        if e.widget is not s.top:return
        s.choice_wrap=ui_layout.text_wrap(e.width-290,32)
        s.res.config(wraplength=s.choice_wrap)
        for child in s.opts.winfo_children():child.config(wraplength=s.choice_wrap)

    def bonus(s):
        b=0
        if s.smoke.get() and s.w.s['cig']>=1:b+=2
        if s.focus.get() and s.w.s['stamina']>=8:b+=1
        return b
    def setport(s,who):
        if who and who in s.a.npcs:
            im=Image.open(s.a.base/('assets/%s.jpg'%s.a.npcs[who]['portrait'])).resize((220,347),Image.Resampling.LANCZOS);s.refs['p']=ImageTk.PhotoImage(im);s.portrait.config(image=s.refs['p']);s.who.config(text=core.shown_name(s.w,who))
        else:
            try:
                im=Image.open(s.a.base/('assets/player.jpg' if (s.a.base/'assets/player.jpg').is_file() else 'assets/player_avatar.png')).resize((200,200));s.refs['p']=ImageTk.PhotoImage(im);s.portrait.config(image=s.refs['p'])
            except Exception:pass
            s.who.config(text='Ваш герой' if (s.a.base/'assets/player.jpg').is_file() else 'Рассказчик')
    def show(s,node):
        n=s.sc['nodes'][node];s.cur=n;s.setport(n.get('who'));s.res.config(text='')
        s.text.config(state='normal');s.text.delete('1.0','end');s.text.insert('1.0',core.render_text(n['text'],s.vars));s.text.config(state='disabled');s.redraw()
    def redraw(s):
        for x in s.opts.winfo_children():x.destroy()
        n=s.cur;w=s.w;c=core.C(w);st=w.s
        s.stats.config(text='Мудрость %d · Харизма %d\nСтатус: %s (%+d)\nСигареты %d · Силы %d'%(core.mod(w,'wis'),core.mod(w,'cha'),core.tier(w)[0],c['caste'],st['cig'],st['stamina']))
        if not n['ch']:
            s.btn('Закрыть',s.finish,True);return
        for ch in n['ch']:
            tag=''
            if ch.get('chk'):
                stn,dc=ch['chk'];tag='[%s %d · %d%%] '%(STATN[stn],dc,int(chance(w,stn,dc,s.bonus())*100))
            elif ch.get('game'):tag='[МИНИ-ИГРА] '
            if ch.get('req'):tag+='(нужно: %s) '%core.req_text(ch['req'])
            b=s.btn(tag+ch['t'],lambda ch=ch:s.pick(ch),False)
            if not core.req_ok(w,ch.get('req',{})):b.config(state='disabled')
    def btn(s,t,fn,primary=False):
        b=tk.Button(s.opts,text=t,command=fn,bg=GOLD if primary else CARD,fg='#111821' if primary else FG,activebackground='#24364a',relief='flat',bd=0,font=('Segoe UI',11,'bold'),padx=12,pady=9,anchor='w',justify='left',wraplength=s.choice_wrap,cursor='hand2');b.pack(fill='x',pady=3);return b
    def pick(s,ch):
        if ch.get('game'):
            for x in s.opts.winfo_children():x.destroy()
            QuickGame(s.a,ch['game'],lambda ok:s.resolve(ch,ok,0),parent=s.top)
        else:
            b=0
            if ch.get('chk'):
                if s.smoke.get() and s.w.s['cig']>=1:s.w.s['cig']-=1;b+=2
                if s.focus.get() and s.w.s['stamina']>=8:s.w.s['stamina']-=8;b+=1
                s.smoke.set(False);s.focus.set(False)
            s.resolve(ch,None,b)
    def resolve(s,ch,game_ok,bonus):
        r=core.resolve_choice(s.w,ch,game_ok=game_ok,bonus=bonus);res=r['res'];info=r['check']
        for x in s.opts.winfo_children():x.destroy()
        line=''
        if info:line='🎲 %s: d20(%d)%+d%s = %d против сложности %d — %s\n'%(STATN[info['stat']],info['roll'],info['mod'],('%+d'%info['boost']) if info['boost'] else '',info['total'],info['dc'],'УСПЕХ' if r['ok'] else 'ПРОВАЛ')
        elif ch.get('game'):line=('🎮 Мини-игра пройдена\n' if r['ok'] else '🎮 Мини-игра провалена\n')
        s.text.config(state='normal');s.text.insert('end','\n\n'+line+res['text']);s.text.see('end');s.text.config(state='disabled')
        s.res.config(text=' · '.join(r['lines']),fg=GREEN if r['ok'] else RED)
        goto=res.get('goto')
        s.btn('Дальше ▶' if goto else 'Готово',(lambda:s.show(goto)) if goto else s.finish,True)
        s.a.refresh_light()
    def finish(s):
        if s.done:return
        s.done=True;had=core.C(s.w).get('ending');core.finish_scene(s.w,s.sid);core.log_scene(s.w,s.sid);s.a.modal=None
        try:s.top.grab_release();s.top.destroy()
        except tk.TclError:pass
        s.a.persist();s.a.refresh();s.a.propagate()
        if core.C(s.w).get('ending') and not had:s.a.status.config(text='Концовка пройдена. Песочница продолжается: можно играть дальше.');s.a.root.after(300,s.a.show_stats)
        s.a.root.after(0,s.a.maybe_tutorial)

class QuickGame:
    DESC={'timing':('Поймай момент','Нажимай СТОП (или Пробел), когда маркер в зелёной зоне. Нужно 2 попадания из 3.'),
          'mash':('Давка у раздачи','Жми ЖМИ (или Пробел) как можно быстрее, пока не кончилось время.'),
          'cups':('Стаканчики','Запомни, где вещь. Выбери правильный стаканчик после перемешивания.')}
    def __init__(s,app,kind,cb,parent=None):
        s.a=app;s.kind=kind;s.cb=cb;s.done=False;s.after=None;s.prev=app.modal;app.modal=s
        s.top=app.window(s.DESC[kind][0],720,440);s.top.transient(parent or app.root);s.top.grab_set();s.top.protocol('WM_DELETE_WINDOW',lambda:None)
        s.track=min(640,max(300,getattr(s.top,'_layout_size',(720,440))[0]-80))
        tk.Label(s.top,text=s.DESC[kind][0],bg=PANEL,fg=GOLD,font=('Segoe UI',18,'bold')).pack(pady=(14,4))
        s.info=tk.Label(s.top,text=s.DESC[kind][1],bg=PANEL,fg=FG,font=('Segoe UI',11),wraplength=s.track);s.info.pack(pady=4)
        s.body=tk.Frame(s.top,bg=PANEL);s.body.pack(fill='both',expand=True,padx=16,pady=8)
        w=app.world;s.smoke=tk.BooleanVar(value=False);s.focus=tk.BooleanVar(value=False)
        s.pre=tk.Frame(s.body,bg=PANEL);s.pre.pack(pady=6)
        tk.Label(s.pre,text='Подготовка повышает шанс на победу:',bg=PANEL,fg=MUTED).pack()
        cs=tk.Checkbutton(s.pre,text='Закурить (−1 сиг.): +25%% (у вас %d)'%w.s['cig'],variable=s.smoke,bg=PANEL,fg=FG,selectcolor=CARD,activebackground=PANEL);cs.pack(anchor='w')
        cf=tk.Checkbutton(s.pre,text='Собраться с силами (−10 сил): +15%% (у вас %d)'%w.s['stamina'],variable=s.focus,bg=PANEL,fg=FG,selectcolor=CARD,activebackground=PANEL);cf.pack(anchor='w')
        if w.s['cig']<1:cs.config(state='disabled')
        if w.s['stamina']<10:cf.config(state='disabled')
        if w.s['stamina']<20:tk.Label(s.pre,text='Вы выдохлись: шанс снижен на 15%',bg=PANEL,fg=RED).pack()
        tk.Button(s.pre,text='НАЧАТЬ ▶',command=s.start,bg=GOLD,fg='#111821',relief='flat',font=('Segoe UI',12,'bold'),padx=20,pady=8).pack(pady=10)
    def start(s):
        w=s.a.world;sm=s.smoke.get() and w.s['cig']>=1;fo=s.focus.get() and w.s['stamina']>=10
        s.boost=core.boost_value(w,sm,fo)
        if sm:w.s['cig']-=1
        if fo:w.s['stamina']-=10
        s.pre.destroy();s.rng=random.Random();getattr(s,'g_'+s.kind)()
    def end(s,ok):
        if s.done:return
        s.done=True
        if s.after:
            try:s.top.after_cancel(s.after)
            except tk.TclError:pass
        for x in s.body.winfo_children():x.destroy()
        tk.Label(s.body,text='ПОБЕДА!' if ok else 'ПРОВАЛ…',bg=PANEL,fg=GREEN if ok else RED,font=('Segoe UI',26,'bold')).pack(expand=True)
        s.top.after(900,lambda:s.close(ok))
    def close(s,ok):
        s.a.modal=s.prev
        try:s.top.grab_release();s.top.destroy()
        except tk.TclError:pass
        if s.prev is not None and hasattr(s.prev,'top'):
            try:s.prev.top.grab_set()
            except tk.TclError:pass
        s.cb(ok)
    def g_timing(s):
        s.c=tk.Canvas(s.body,width=s.track,height=90,bg='#0b1119',highlightthickness=0);s.c.pack(pady=14);s.x=20;s.dx=9;s.round=0;s.hits=0
        s.lab=tk.Label(s.body,text='',bg=PANEL,fg=FG,font=('Segoe UI',12));s.lab.pack()
        tk.Button(s.body,text='СТОП',command=s.stop,bg=GOLD,fg='#111821',relief='flat',font=('Segoe UI',14,'bold'),padx=30,pady=8).pack(pady=8);s.top.bind('<space>',lambda e:s.stop())
        s.newzone();s.tick()
    def newzone(s):
        wd=max(40,min(260,int(100*(1+s.boost))));cx=s.rng.randint(60+wd//2,580-wd//2);s.zone=(cx-wd//2,cx+wd//2);s.lab.config(text='Попытка %d/3 · попаданий %d'%(s.round+1,s.hits))
    def tick(s):
        if s.done:return
        s.x+=s.dx
        if s.x>=620 or s.x<=20:s.dx=-s.dx
        c=s.c;c.delete('all');c.create_rectangle(10,35,630,55,fill='#243449',outline='');c.create_rectangle(s.zone[0],28,s.zone[1],62,fill='#2f6b4a',outline=GREEN);c.create_rectangle(s.x-4,15,s.x+4,75,fill=GOLD,outline='');c.scale('all',0,0,s.track/640,1)
        s.after=s.top.after(16,s.tick)
    def stop(s):
        if s.done:return
        if s.zone[0]<=s.x<=s.zone[1]:s.hits+=1
        s.round+=1
        if s.round>=3:return s.end(s.hits>=2)
        s.dx=s.dx*1.12;s.newzone()
    def g_mash(s):
        s.need=max(8,int(34*(1-s.boost)));s.n=0;s.t=6.0
        s.c=tk.Canvas(s.body,width=s.track,height=40,bg='#0b1119',highlightthickness=0);s.c.pack(pady=14)
        s.lab=tk.Label(s.body,text='',bg=PANEL,fg=FG,font=('Segoe UI',12));s.lab.pack()
        tk.Button(s.body,text='ЖМИ!',command=s.hit,bg=GOLD,fg='#111821',relief='flat',font=('Segoe UI',20,'bold'),padx=60,pady=14).pack(pady=8);s.top.bind('<space>',lambda e:s.hit());s.mtick()
    def hit(s):
        if s.done:return
        s.n+=1
        if s.n>=s.need:s.end(True)
    def mtick(s):
        if s.done:return
        s.t-=.05;s.c.delete('all');s.c.create_rectangle(0,0,s.track*min(1,s.n/s.need),40,fill=GOLD,outline='');s.lab.config(text='Нажатий %d/%d · осталось %.1f с'%(s.n,s.need,max(0,s.t)))
        if s.t<=0:return s.end(False)
        s.after=s.top.after(50,s.mtick)
    def g_cups(s):
        n=4 if s.boost<0 else 3;s.n=n;s.ball=s.rng.randrange(n);s.order=list(range(n));s.moves=0;s.picked=False
        s.row=tk.Frame(s.body,bg=PANEL);s.row.pack(pady=20);s.btns=[]
        for i in range(n):
            b=tk.Button(s.row,text='🥤',font=('Segoe UI',34),width=3,bg=CARD,fg=FG,relief='flat',state='disabled',command=lambda i=i:s.choose(i));b.grid(row=0,column=i,padx=10);s.btns.append(b)
        s.btns[s.ball].config(text='📦');s.lab=tk.Label(s.body,text='Запоминайте!',bg=PANEL,fg=FG,font=('Segoe UI',12));s.lab.pack()
        s.after=s.top.after(1300,s.shuffle)
    def shuffle(s):
        if s.done:return
        for b in s.btns:b.config(text='🥤')
        s.lab.config(text='Перемешиваю…')
        if s.moves<9:
            a,b=s.rng.sample(range(s.n),2);s.order[a],s.order[b]=s.order[b],s.order[a]
            if s.ball==a:s.ball=b
            elif s.ball==b:s.ball=a
            for pos,i in enumerate(s.order):s.btns[i].grid(row=0,column=pos)
            s.moves+=1;s.after=s.top.after(260,s.shuffle)
        else:
            for b in s.btns:b.config(state='normal')
            s.lab.config(text='Где вещь?')
            if s.boost>0:
                wrong=[i for i in range(s.n) if i!=s.ball]
                for i in s.rng.sample(wrong,min(len(wrong)-1,1 if s.boost<.35 else 2)):s.btns[i].config(state='disabled',text='✖')
                s.lab.config(text='Где вещь? (подготовка убрала лишний стаканчик)')
    def choose(s,i):
        if s.picked:return
        s.picked=True;s.btns[s.ball].config(text='📦');s.end(i==s.ball)

class MapView:
    def __init__(s,app,parent):
        s.a=app;s.c=tk.Canvas(parent,bg='#070b10',highlightthickness=0);s.cache={};s.hover=None;s.rects={}
        s.c.bind('<Configure>',lambda e:s.draw());s.c.bind('<Motion>',s.motion);s.c.bind('<Button-1>',s.click);s.c.bind('<Leave>',lambda e:s.sethover(None))
    def geom(s):
        w=max(300,s.c.winfo_width());h=max(200,s.c.winfo_height());rw=int(w*.19);rh=int(h*.25)
        return w,h,rw,rh,{k:(int(x*w),int(y*h)) for k,(x,y) in core.MAPPOS.items()}
    def chip(s,k,size):
        key=('chip',k,size)
        if key not in s.cache:
            a=s.a;im=Image.open(a.base/('assets/%s.jpg'%a.npcs[k]['portrait'])).convert('RGB');im=ImageOps.fit(im,(size,size),centering=(.5,.2));m=Image.new('L',(size,size),0);ImageDraw.Draw(m).ellipse((0,0,size-1,size-1),fill=255);im.putalpha(m);s.cache[key]=ImageTk.PhotoImage(im)
        return s.cache[key]
    def icon(s,name,size):
        key=('ic',name,size)
        if key not in s.cache:s.cache[key]=ImageTk.PhotoImage(Image.open(s.a.base/('assets/icon_%s.png'%name)).convert('RGBA').resize((size,size)))
        return s.cache[key]
    def room(s,i,rw,rh,cur):
        br=s.a.settings.get('brightness',1.0);key=('room',i,rw,rh,cur,br)
        if key not in s.cache:
            im=ImageOps.fit(open_rgb(s.a.base/('assets/loc_%d.jpg'%i),(rw*2,rh*2)),(rw,rh),method=Image.Resampling.LANCZOS)
            im=ImageEnhance.Brightness(im).enhance((1.0 if cur else .55)*br);s.cache[key]=ImageTk.PhotoImage(im)
        return s.cache[key]
    def draw(s):
        c=s.c;a=s.a;w,h,rw,rh,pos=s.geom();c.delete('all');s.rects={}
        if len(s.cache)>120:s.cache.clear()
        for x in range(0,w,40):c.create_line(x,0,x,h,fill='#0b141d')
        for y in range(0,h,40):c.create_line(0,y,w,y,fill='#0b141d')
        for a1,b1 in core.EDGES:
            (x1,y1),(x2,y2)=pos[a1],pos[b1];c.create_line(x1,y1,x2,y2,fill='#162231',width=16);c.create_line(x1,y1,x2,y2,fill='#2a3d52',width=2,dash=(6,4))
        cur=a.world.s['loc']
        for i,(x,y) in pos.items():
            x0,y0,x1,y1=x-rw//2,y-rh//2,x+rw//2,y+rh//2;s.rects[i]=(x0,y0,x1,y1);act=i==cur;hov=i==s.hover
            c.create_rectangle(x0-4,y0-4,x1+4,y1+4,fill='#141b24',outline=GOLD if act else '#5c4831' if hov else '#2b3c50',width=3 if act else 2)
            c.create_image(x0,y0,anchor='nw',image=s.room(i,rw,rh,act or hov))
            c.create_rectangle(x0,y1-24,x1,y1,fill='#0b1420',stipple='gray50',outline='');c.create_text(x0+8,y1-12,anchor='w',text=core.NAMES[i].upper(),fill=GOLD if act else FG,font=('Segoe UI',10,'bold'))
            if not act:c.create_text(x1-8,y1-12,anchor='e',text='%d мин'%core.travel_minutes(a.world,i),fill=MUTED,font=('Segoe UI',9))
            else:c.create_text(x1-8,y1-12,anchor='e',text='ВЫ ЗДЕСЬ',fill=GOLD,font=('Segoe UI',9,'bold'))
            present=[k for k,n in a.npcs.items() if n['home']==i];cs=max(26,min(40,rh//3))
            for j,k in enumerate(present):
                cx=x0+8+j*(cs+4);cy=y0+8;boss=core.in_power(a.world,k)  # золотое кольцо — только у босса при власти
                c.create_oval(cx-2,cy-2,cx+cs+2,cy+cs+2,fill='#e5b767' if boss else '#2b3c50',outline='')
                c.create_image(cx,cy,anchor='nw',image=s.chip(k,cs))
            if core.stash_has(a.world,i):c.create_image(x1-22,y0+16,image=s.icon('cig',24))
            if core.story_available_at(a.world,i):
                c.create_oval(x1-24,y0+34,x1-4,y0+54,fill='#e5b767',outline='');c.create_text(x1-14,y0+44,text='!',fill='#111821',font=('Segoe UI',12,'bold'))
        if s.hover is not None:
            i=s.hover;who=[core.shown_name(a.world,k) for k,n in a.npcs.items() if n['home']==i]
            t='%s · %s · %s'%(core.NAMES[i],'вы здесь' if i==cur else 'идти %d мин'%core.travel_minutes(a.world,i),', '.join(who) or 'никого')
            c.create_rectangle(10,h-34,w-10,h-8,fill='#0b1420',outline='#34536a');c.create_text(20,h-21,anchor='w',text=t,fill=FG,font=('Segoe UI',11))
        else:c.create_text(w//2,h-20,text='Кликните по локации, чтобы пойти. Золотое кольцо у портрета — босс. «!» — доступна сюжетная сцена. Пачка — ваш схрон.',fill=MUTED,font=('Segoe UI',10))
    def at(s,x,y):
        return next((i for i,(a,b,c_,d) in s.rects.items() if a<=x<=c_ and b<=y<=d),None)
    def sethover(s,i):
        if i!=s.hover:s.hover=i;s.c.config(cursor='hand2' if i is not None else '');s.draw()
    def motion(s,e):s.sethover(s.at(e.x,e.y))
    def click(s,e):
        tour=getattr(s.a,'mentor',None)
        if tour and tour.step[0]=='boss':return
        i=s.at(e.x,e.y)
        if i is not None:s.a.travel(i)


class Tutorial:
    STEPS=[('Добро пожаловать в зону','Ваша цель — выжить, заслужить уважение и выбрать свою концовку. Время идёт: переходы, работа и разговоры двигают часы.'),
           ('Карта (M)','Кнопка «Карта» открывает план зоны. Кликните по комнате, чтобы пойти туда. Золотое кольцо у портрета — босс, «!» — сюжетная сцена, пачка — ваш схрон.'),
           ('Действия','Внизу — действия текущей локации. Остальное (бой, решения, схрон, задания) — в меню «⋯». Спать можно только ночью, кормёжка в 8:00, 13:00 и 19:00.'),
           ('Разговоры и проверки','Кликните по портрету или нажмите Enter, чтобы написать реплику. В сценах проверки идут по d20; сигарета и силы повышают шанс, процент виден на кнопке.'),
           ('Статус, задания, меню','Статус растёт от поступков: Петух → Шестёрка → Мужик → Авторитет → Пахан. Клавиша J покажет задания, Esc откроет меню и сохранения. Удачи!')]
    def __init__(s,app):
        s.a=app;s.i=0;s.top=app.window('Обучение',620,330);s.top.transient(app.root)
        s.title=tk.Label(s.top,bg=PANEL,fg=GOLD,font=('Segoe UI',16,'bold'));s.title.pack(pady=(18,6))
        s.body=tk.Label(s.top,bg=PANEL,fg=FG,font=('Segoe UI',12),wraplength=560,justify='left');s.body.pack(padx=24,pady=6)
        s.dots=tk.Label(s.top,bg=PANEL,fg=MUTED,font=('Segoe UI',10));s.dots.pack(pady=4)
        row=tk.Frame(s.top,bg=PANEL);row.pack(pady=14)
        s.next=tk.Button(row,text='Дальше ▶',command=s.step,bg=GOLD,fg='#111821',relief='flat',font=('Segoe UI',11,'bold'),padx=18,pady=7);s.next.pack(side='left',padx=6)
        tk.Button(row,text='Пропустить',command=s.close,bg=CARD,fg=FG,relief='flat',font=('Segoe UI',11),padx=18,pady=7).pack(side='left',padx=6)
        s.top.protocol('WM_DELETE_WINDOW',s.close);s.show()
    def show(s):
        t,b=s.STEPS[s.i];s.title.config(text=t);s.body.config(text=b);s.dots.config(text='●'*(s.i+1)+'○'*(len(s.STEPS)-s.i-1))
        s.next.config(text='Начать игру' if s.i==len(s.STEPS)-1 else 'Дальше ▶')
    def step(s):
        if s.i>=len(s.STEPS)-1:return s.close()
        s.i+=1;s.show()
    def close(s):
        import meta
        s.a.settings['seen_howto']=True;meta.save_settings(s.a.base_data,s.a.settings)
        try:s.top.destroy()
        except tk.TclError:pass
