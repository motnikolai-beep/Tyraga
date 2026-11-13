
"""Главное / пауза-меню v9: новая игра, слоты, настройки (графика, звук, ИИ), достижения, авторы."""
import tkinter as tk
from tkinter import messagebox
from PIL import Image,ImageTk,ImageOps,ImageEnhance
from gfx import open_rgb
import core,meta
BG='#090d12';PANEL='#101720';CARD='#182331';FG='#e6edf4';MUTED='#8799ac';GOLD='#e5b767';GREEN='#6fcf97';RED='#c45867'
HOWTO="""УПРАВЛЕНИЕ
• Esc — меню, M — карта зоны, F11 — полный экран, Ctrl+S — быстрое сохранение, F2 — история разговора.
• Alt+1…7 — быстрые действия из карточек внизу.
• Enter — отправить реплику NPC, Shift+Enter — перенос строки.

КАК ИГРАТЬ
• Наводите курсор на пунктирные контуры предметов в сцене и нажимайте на подсвеченный силуэт: нары, окно и другие вещи дают действия и местный смысл. В J — журнал «Следы мест».
• Со второго дня в камере начинается история «Письмо из дома»; её три части идут в разные дни. В J — распорядок, судьбы встреченных хозяев и подготовка к жизни после зоны.
• При первом продолжении старый заключённый Дед Мирон ведёт по подсвеченным кнопкам. Пропуск и отключение — на его панели; для повтора откройте главное меню → «Обучение с Дедом Мироном — заново».
• Кликните по портрету, чтобы выбрать собеседника, и пишите ему своими словами.
• Время идёт от всего: переходы, работа, разговоры. Лечь на шконку можно только с 22:00.
• Кормёжка в 08:00, 13:00 и 19:00: успейте прийти, иначе останетесь голодным.
• Проверки мудрости и харизмы — бросок d20 + ваш стат. Сигарета и силы повышают шанс, мини-игры тоже.
• На карте переход в другую локацию показывает комикс-экран: что осталось позади и что может ждать впереди.
• Оружие и тренировки — в «Снаряжении» в меню ⋯. Три ветки по три уровня.
• Сюжетные сцены ждут в локациях с золотой «!» на карте.
• Свергнутый босс остаётся в зоне без власти. С ним можно помириться; обиженный однажды позовёт на разборку — не придёте до отбоя или проиграете, и он снова хозяин.
• В меню «⋯» → «Личное дело» видны ваше прошлое, сытость, карма, вещи и отношения.
• Статус растёт и падает от ваших поступков: Петух → Шестёрка → Мужик → Авторитет → Пахан.
• Господь в Храме списывает часть грехов, но статус возвращается только делом.
• Бой идёт в реальном времени (меню «⋯» → Дуэль): J/K — удары руками, U/I — ногами, L — блок, O — уклон, Пробел — кувырок, C — сигарета. Подробности — по клавише H в бою.
• «Разведка» открывает слабость босса: затем «Слабое место» свергает босса без драки, а в бою даёт +35% урона.
• Клавиша J — задания, Enter — разговор, Esc — меню."""
class Menu:
    def __init__(s,app):
        s.a=app;s.visible=False;s.cache={};s.inner=None;s.vars={};s.tab='gfx'
        s.f=tk.Frame(app.root,bg=BG);s.c=tk.Canvas(s.f,bg=BG,highlightthickness=0);s.c.pack(fill='both',expand=True)
        s.inner=tk.Frame(s.c,bg='#0d1520');s.c.bind('<Configure>',lambda e:s.paint())
    # ---- показ ----
    def show(s,screen='main'):
        if getattr(s.a,'mentor',None):return
        s.visible=True;s.a.menu_open=True;s.f.place(x=0,y=0,relwidth=1,relheight=1);s.f.lift();s.go(screen)
    def hide(s):
        if not s.a.has_game:return
        s.visible=False;s.a.menu_open=False;s.f.place_forget();s.a.refresh();s.a.root.after(0,s.a.maybe_tutorial)
    def toggle(s):
        if s.visible:s.hide()
        elif not s.a.modal and not s.a.battle and not s.a.mini and not s.a.mentor:s.show()
    def paint(s):
        c=s.c;w=max(300,c.winfo_width());h=max(300,c.winfo_height());br=s.a.settings.get('brightness',1.0);key=(w,h,br)
        if key not in s.cache:
            bg=s.a.base/'assets/menu_bg.jpg'  # отдельный фон меню, если он есть в сборке; иначе камера
            if not bg.is_file():bg=s.a.base/'assets/loc_0.jpg'
            s.cache.clear();im=ImageOps.fit(open_rgb(bg,(w,h)),(w,h));s.cache[key]=ImageTk.PhotoImage(ImageEnhance.Brightness(im).enhance(.32*br))
        c.delete('all');c.create_image(0,0,anchor='nw',image=s.cache[key]);c.create_window(w//2,h//2,window=s.inner,anchor='center')
    def go(s,screen,**kw):
        for x in s.inner.winfo_children():x.destroy()
        s.screen=screen;getattr(s,'screen_'+screen)(**kw);s.paint()
    # ---- элементы ----
    def title(s,t,size=26,color=GOLD):tk.Label(s.inner,text=t,bg=s.inner.cget('bg'),fg=color,font=('Segoe UI',size,'bold')).pack(padx=40,pady=(26,6))
    def note(s,t,color=MUTED,size=10,wrap=620,anchor='center'):tk.Label(s.inner,text=t,bg=s.inner.cget('bg'),fg=color,font=('Segoe UI',size),wraplength=wrap,justify='left' if anchor=='w' else 'center').pack(padx=30,pady=3,anchor=anchor)
    def btn(s,t,fn,primary=False,state='normal',width=34,parent=None):
        b=tk.Button(parent or s.inner,text=t,command=fn,bg=GOLD if primary else CARD,fg='#111821' if primary else FG,activebackground='#e9c88f' if primary else '#24364a',disabledforeground='#4b5a6b',relief='flat',bd=0,font=('Segoe UI',12,'bold'),width=width,pady=9,cursor='hand2',state=state)
        if parent is None:b.pack(pady=4,padx=60)
        return b
    # ---- экраны ----
    def screen_main(s):
        a=s.a;s.title('ТЮРЯГА',40);s.note('Почтовый вопрос · v18',MUTED,11)
        if a.has_game:s.note('Текущая игра: день %d · %s · %s'%(a.world.s['day'],core.hhmm(a.world),core.diff(a.world)['name']),GOLD,10)
        if a.has_game:s.btn('▶  Продолжить',s.hide,True)
        s.btn('Новая игра',lambda:s.go('new'),not a.has_game)
        s.btn('Загрузить игру',lambda:s.go('slots',mode='load'))
        s.btn('Сохранить игру',lambda:s.go('slots',mode='save'),state='normal' if a.has_game else 'disabled')
        s.btn('Статистика и выборы',lambda:s.go('stats'),state='normal' if a.has_game else 'disabled')
        s.btn('Настройки',lambda:s.go('settings'))
        got=len(meta.ach_store(a.base_data)['unlocked']);s.btn('Достижения  (%d/%d)'%(got,len(meta.ACH)),lambda:s.go('ach'))
        if a.has_game:s.btn('Обучение с Дедом Мироном — заново',lambda:(s.hide(),a.root.after(50,lambda:a.maybe_tutorial(force=True))))
        s.btn('Как играть',lambda:s.go('howto'));s.btn('Авторы',lambda:s.go('authors'));s.btn('Выход',a.close)
        s.note('',MUTED,4)
    def screen_new(s):
        s.title('Новая игра',24);s.note('Выберите сложность. Её нельзя сменить в уже начатой игре.')
        s.diffvar=tk.StringVar(value='normal')
        for k,d in core.DIFFS.items():
            r=tk.Radiobutton(s.inner,text='%s\n%s'%(d['name'],d['desc']),variable=s.diffvar,value=k,bg=CARD,fg=FG,selectcolor='#2c4058',activebackground='#24364a',activeforeground=GOLD,justify='left',anchor='w',font=('Segoe UI',11),wraplength=560,padx=14,pady=8,indicatoron=0,width=60)
            r.pack(pady=4,padx=30)
        import profile
        s.note('Прошлое героя — сюжетная деталь, бонусов не даёт.',GOLD,10)
        s.originvar=tk.StringVar(value='paper')
        for key,(case,term,_story) in profile.ORIGINS.items():
            tk.Radiobutton(s.inner,text=case+' · '+term,variable=s.originvar,value=key,bg=CARD,fg=FG,selectcolor='#2c4058',activebackground='#24364a',activeforeground=GOLD,indicatoron=0,width=60).pack(pady=2,padx=30)
        s.btn('Начать игру',s.start_new,True);s.btn('Назад',lambda:s.go('main'))
    def start_new(s):
        a=s.a
        if a.has_game and not messagebox.askyesno('Новая игра','Текущее автосохранение будет заменено новой игрой (копия сохранится в saves/before_newgame.json). Продолжить?'):return
        a.new_game(s.diffvar.get(),s.originvar.get());s.hide()
    def screen_slots(s,mode='load'):
        a=s.a;s.title('Загрузка' if mode=='load' else 'Сохранение',24)
        ids=(['auto','legacy'] if mode=='load' else [])+meta.SLOTS
        names={'auto':'Автосохранение','legacy':'Прошлая игра (v7)','slot1':'Слот 1','slot2':'Слот 2','slot3':'Слот 3'}
        for sid in ids:
            sm=meta.summary(a.base_data,sid)
            if sid=='legacy' and sm is None:continue
            row=tk.Frame(s.inner,bg=PANEL);row.pack(fill='x',padx=30,pady=4)
            tk.Label(row,text=names[sid],bg=PANEL,fg=GOLD,font=('Segoe UI',11,'bold'),width=20,anchor='w').pack(side='left',padx=8)
            tk.Label(row,text=meta.summary_text(sm),bg=PANEL,fg=FG if sm and 'error' not in sm else MUTED,font=('Segoe UI',10),wraplength=520,justify='left',anchor='w',width=62).pack(side='left',padx=6,pady=6)
            if mode=='load':s.btn('Загрузить',lambda sid=sid:s.do_load(sid),state='normal' if sm and 'error' not in sm else 'disabled',width=12,parent=row).pack(side='right',padx=6)
            else:s.btn('Сохранить',lambda sid=sid:s.do_save(sid),width=12,parent=row).pack(side='right',padx=6)
            if sid in meta.SLOTS and sm:s.btn('✕',lambda sid=sid,mode=mode:s.do_del(sid,mode),width=3,parent=row).pack(side='right')
        s.btn('Назад',lambda:s.go('main'))
    def do_load(s,sid):
        a=s.a
        if a.has_game and not messagebox.askyesno('Загрузка','Несохранённый прогресс будет потерян. Загрузить?'):return
        try:a.load_slot(sid)
        except ValueError as e:return messagebox.showerror('Загрузка',str(e))
        s.hide()
    def do_save(s,sid):
        a=s.a
        if meta.summary(a.base_data,sid) and not messagebox.askyesno('Сохранение','Слот занят. Перезаписать?'):return
        try:a.save_slot(sid);s.go('slots',mode='save')
        except Exception as e:messagebox.showerror('Сохранение',str(e))
    def do_del(s,sid,mode):
        if messagebox.askyesno('Удаление','Удалить сохранение?'):
            try:meta.slot_path(s.a.base_data,sid).unlink()
            except OSError:pass
            s.go('slots',mode=mode)
    # ---- настройки ----
    AI_BOOL=[('CHAT_FAST_MODE','Быстрый режим (один запрос, без оценок и инициатив)'),('GOSSIP_ENABLED','Слухи и сплетни между NPC'),('NPC_INITIATIVE','Инициатива NPC (только в полном режиме)'),('CHAT_JSON_MODE','JSON-режим ответов'),('CHAT_EVALUATE_KARMA','ИИ-оценка кармы (полный режим)'),('CHAT_THREAT_AI','ИИ-проверка угроз (полный режим)')]
    AI_NUM=[('CHAT_MAX_OUTPUT_TOKENS','Макс. длина ответа, токенов',64,16384),('CHAT_HISTORY_MESSAGES','Сообщений истории в контексте',0,100),('CHAT_MAX_INPUT_CHARS','Макс. длина вашей реплики, символов',100,50000),('CHAT_CONTEXT_LENGTH','Контекст модели, токенов (нужен перезапуск ИИ)',2048,65536),('LLAMA_GPU_LAYERS','Слоёв на GPU (нужен перезапуск ИИ)',0,200),('SCOUT_PORT','Порт сервера (нужен перезапуск ИИ)',1024,65535)]
    AI_STR=[('SCOUT_MODEL_PATH','Файл модели .gguf'),('SCOUT_MMPROJ_PATH','Файл mmproj .gguf'),('LLAMA_SERVER_PATH','llama-server.exe')]
    def screen_settings(s,tab=None):
        a=s.a;s.tab=tab or s.tab;s.title('Настройки',24);bar=tk.Frame(s.inner,bg=s.inner.cget('bg'));bar.pack(pady=4)
        for k,t in [('gfx','Графика'),('snd','Звук'),('ai','ИИ-модель'),('game','Игра')]:
            s.btn(t,lambda k=k:s.go('settings',tab=k),primary=(k==s.tab),width=14,parent=bar).pack(side='left',padx=3)
        box=tk.Frame(s.inner,bg=PANEL);box.pack(fill='x',padx=30,pady=8);s.vars={};st=a.settings
        def scale(label,key,lo,hi,step,val):
            r=tk.Frame(box,bg=PANEL);r.pack(fill='x',padx=12,pady=5);tk.Label(r,text=label,bg=PANEL,fg=FG,font=('Segoe UI',11),width=34,anchor='w').pack(side='left')
            v=tk.DoubleVar(value=val);s.vars[key]=v;tk.Scale(r,from_=lo,to=hi,resolution=step,orient='horizontal',variable=v,length=320,bg=PANEL,fg=FG,troughcolor=CARD,highlightthickness=0).pack(side='left')
        def check(label,key,val,store=None):
            v=tk.BooleanVar(value=val);(store or s.vars)[key]=v;tk.Checkbutton(box,text=label,variable=v,bg=PANEL,fg=FG,selectcolor=CARD,activebackground=PANEL,activeforeground=GOLD,font=('Segoe UI',11),anchor='w').pack(fill='x',padx=12,pady=3)
        def entry(label,key,val,width=12):
            r=tk.Frame(box,bg=PANEL);r.pack(fill='x',padx=12,pady=4);tk.Label(r,text=label,bg=PANEL,fg=FG,font=('Segoe UI',11),width=46,anchor='w').pack(side='left')
            v=tk.StringVar(value=str(val));s.vars[key]=v;tk.Entry(r,textvariable=v,width=width,bg=CARD,fg=FG,insertbackground=GOLD,relief='flat',font=('Segoe UI',11)).pack(side='left',padx=4,ipady=4)
        if s.tab=='gfx':
            scale('Яркость','brightness',.4,1.6,.05,st['brightness']);scale('Масштаб интерфейса','ui_scale',.8,1.8,.1,st['ui_scale'])
            check('Полный экран (F11)','fullscreen',st['fullscreen']);check('Фон сцены: заполнять окно целиком','cover',st['cover'])
        elif s.tab=='snd':
            scale('Громкость эффектов','volume',0,1,.05,st['volume']);scale('Громкость фоновой музыки','music',0,1,.05,st['music']);s.note('Фон — тихий процедурный амбиент для каждой локации. Звук проверяется на Windows.',MUTED,9)
        elif s.tab=='ai':
            cfg=a.engine.cfg
            for k,t in s.AI_BOOL:check(t,k,str(cfg.get(k,'false')).lower()=='true')
            r=tk.Frame(box,bg=PANEL);r.pack(fill='x',padx=12,pady=5);tk.Label(r,text='Температура (креативность ответов)',bg=PANEL,fg=FG,font=('Segoe UI',11),width=34,anchor='w').pack(side='left')
            v=tk.DoubleVar(value=float(cfg.get('CHAT_TEMPERATURE',.6)));s.vars['CHAT_TEMPERATURE']=v;tk.Scale(r,from_=0,to=1.5,resolution=.05,orient='horizontal',variable=v,length=320,bg=PANEL,fg=FG,troughcolor=CARD,highlightthickness=0).pack(side='left')
            for k,t,lo,hi in s.AI_NUM:entry(t,k,cfg.get(k,''))
            for k,t in s.AI_STR:entry(t,k,cfg.get(k,''),width=52)
        else:
            sec=st['autosave_sec'];entry('Автосохранение каждые N секунд (10–600)','autosave_sec',sec);check('Пошаговое обучение при первом запуске','hints',st['hints'])
            d=core.diff(a.world) if a.has_game else core.DIFFS['normal']
            tk.Label(box,text='Сложность текущей игры: %s'%d['name'],bg=PANEL,fg=GOLD,font=('Segoe UI',11,'bold')).pack(anchor='w',padx=12,pady=6)
        s.msg=tk.Label(s.inner,text='',bg=s.inner.cget('bg'),fg=GREEN,font=('Segoe UI',10),wraplength=620);s.msg.pack()
        row=tk.Frame(s.inner,bg=s.inner.cget('bg'));row.pack(pady=6)
        s.btn('Применить',s.apply_settings,True,width=16,parent=row).pack(side='left',padx=4)
        if s.tab=='ai':
            s.btn('Проверить файлы',s.check_files,width=16,parent=row).pack(side='left',padx=4);s.btn('Перезапустить ИИ',s.restart_ai,width=18,parent=row).pack(side='left',padx=4)
        s.btn('Назад',lambda:s.go('main'),width=12,parent=row).pack(side='left',padx=4)
    def apply_settings(s):
        a=s.a;v=s.vars;errs=[]
        try:
            for k in ('brightness','ui_scale','volume','music'):
                if k in v:a.settings[k]=float(v[k].get())
            for k in ('fullscreen','cover','hints'):
                if k in v:a.settings[k]=bool(v[k].get())
            if 'autosave_sec' in v:a.settings['autosave_sec']=int(float(v['autosave_sec'].get()))
            meta.clamp_settings(a.settings);meta.save_settings(a.base_data,a.settings);a.apply_settings()
            if s.tab=='ai':
                for k,t in s.AI_BOOL:
                    val='true' if v[k].get() else 'false';a.engine.cfg[k]=val;meta.env_set(a.base_data,k,val)
                t=round(max(0,min(1.5,float(v['CHAT_TEMPERATURE'].get()))),2);a.engine.cfg['CHAT_TEMPERATURE']=str(t);meta.env_set(a.base_data,'CHAT_TEMPERATURE',t)
                for k,t_,lo,hi in s.AI_NUM:
                    try:n=int(float(v[k].get()))
                    except ValueError:errs.append(t_);continue
                    n=max(lo,min(hi,n));a.engine.cfg[k]=str(n);meta.env_set(a.base_data,k,n)
                for k,t_ in s.AI_STR:
                    val=v[k].get().strip()
                    if val:a.engine.cfg[k]=val;meta.env_set(a.base_data,k,val)
        except Exception as e:errs.append(str(e))
        s.msg.config(text=('Не применено: '+', '.join(errs)) if errs else 'Применено и сохранено.',fg=RED if errs else GREEN);a.refresh_light()
    def check_files(s):
        e=s.a.engine;rows=[]
        for k,t in s.AI_STR:
            p=e.path(s.vars[k].get().strip() or e.cfg.get(k,''));rows.append(('✔ ' if p.exists() else '✘ ')+t+': '+str(p))
        s.msg.config(text='\n'.join(rows),fg=FG,justify='left')
    def restart_ai(s):
        s.apply_settings();s.a.restart_ai();s.msg.config(text='ИИ перезапускается… Статус внизу окна игры.',fg=GREEN)
    # ---- прочее ----
    def screen_ach(s):
        a=s.a;st=meta.ach_store(a.base_data)['unlocked'];s.title('Достижения  %d/%d'%(len(st),len(meta.ACH)),24)
        fr=tk.Frame(s.inner,bg=PANEL);fr.pack(padx=30,pady=6);t=tk.Text(fr,width=84,height=18,bg='#0b1119',fg=FG,relief='flat',font=('Segoe UI',11),wrap='word',padx=12,pady=8);sb=tk.Scrollbar(fr,command=t.yview);t.config(yscrollcommand=sb.set);t.pack(side='left');sb.pack(side='right',fill='y')
        t.tag_config('ok',foreground=GOLD,font=('Segoe UI',11,'bold'));t.tag_config('lock',foreground=MUTED)
        for id,title,desc,fn,hidden in meta.ACH:
            if id in st:t.insert('end','★ '+title+'\n','ok');t.insert('end','   '+desc+'\n\n')
            elif hidden:t.insert('end','☆ ???\n','lock');t.insert('end','   Скрытое достижение\n\n','lock')
            else:t.insert('end','☆ '+title+'\n','lock');t.insert('end','   '+desc+'\n\n','lock')
        t.config(state='disabled');s.btn('Назад',lambda:s.go('main'))
    def screen_howto(s):
        s.title('Как играть',24);s.note(HOWTO,FG,11,700,'w');s.btn('Назад',lambda:s.go('main'))
    def screen_authors(s):
        s.title('Авторы',28);s.note('Мотырев',GOLD,22);s.note('Кивокурцев',GOLD,22)
        s.note('\nТюряга · Свои люди\nСатирическая RPG с ИИ-персонажами\nPython · Tkinter · Pillow · llama.cpp · Qwen3-VL',MUTED,11);s.btn('Назад',lambda:s.go('main'))

    def screen_stats(s):
        a=s.a;s.title('Статистика',24);minutes=int(((a.world.s.get('meta') or {}).get('playtime',0)+(__import__('time').time()-a.started))//60);st=core.stats(a.world,minutes)
        fr=tk.Frame(s.inner,bg=PANEL);fr.pack(padx=30,pady=6);t=tk.Text(fr,width=84,height=19,bg='#0b1119',fg=FG,relief='flat',font=('Segoe UI',11),wrap='word',padx=12,pady=8);sb=tk.Scrollbar(fr,command=t.yview);t.config(yscrollcommand=sb.set);t.pack(side='left');sb.pack(side='right',fill='y')
        t.tag_config('k',foreground=GOLD,font=('Segoe UI',11,'bold'))
        for k,v in st.items():
            if k=='Ваши выборы':
                t.insert('end','\n'+k+':\n','k')
                for x in v:t.insert('end','  • '+x+'\n')
            else:t.insert('end',k+': ','k');t.insert('end',str(v)+'\n')
        t.config(state='disabled');s.btn('Назад',lambda:s.go('main'))
