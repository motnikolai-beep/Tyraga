"""First-run, opt-out spotlight tour. No game clock, resources or NPC messages are changed.

Four opaque scrims surround a genuine live widget: unlike a screenshot of the UI, the
highlighted area remains clickable. Buttons/canvas are observed, never invoked twice.
The coach is scripted and offline; it is not an NPC or an AI conversation.
"""
import tkinter as tk
from PIL import Image, ImageTk
import meta

INK='#060b12'; PANEL='#111c2a'; GOLD='#e5b767'; FG='#f2efe7'
# action='tap' requires an actual click on the highlighted widget. 'read' advances
# only by the coach's button. No compulsory spending, travel, or chat submission.
STEPS=(
 ('welcome','Знакомься, новичок', 'Я Мирон. На зоне зовут Дедом. Ты здесь по делу из личного дела; я давно научился читать людей и местные правила. Впереди — работа, соседи, двенадцать хозяев мест и твои решения. Покажу кнопки, не потратив твои деньги и не отправив слов в ИИ.', 'scene','read'),
 ('hud','Следи за собой', 'Здесь здоровье, силы, сигареты, рубли и статус. Работа и переходы тратят время; раздача еды бывает утром, днём и вечером.', 'hud','read'),
 ('actions','Дела на месте', 'Внизу действия именно этой локации. У недоступных действий написана причина. За золотым знаком «!» на карте прячутся сюжетные сцены и проверки d20.', 'actions','read'),
 ('portrait','Кто здесь живёт?', 'Нажми на портрет соседа. Так ты выберешь собеседника и откроешь окно разговора. Отношения меняются из-за поступков; друг может помочь, враг — донести.', 'portrait','tap'),
 ('chat','Свои слова', 'Вот поле реплики. Можно говорить свободно с выбранным персонажем. Щёлкни по полю, чтобы найти место для своей реплики. После экскурсии напечатай её: Enter или «Сказать» отправит текст, только если локальная ИИ-модель подключена.', 'entry','tap'),
 ('chat_send','Разговор и приватность', '«Наедине» скрывает слова от других свидетелей; слухи могут разойтись иначе. Нажать «Сказать» можно после обучения: без установленной модели игра честно сообщит, что ИИ не подключён. Сейчас не отправляем ничего за тебя.', 'send','read'),
 ('map','Открой карту', 'Нажми «Карта». Узлы — комнаты зоны, линии — пути; переход тратит игровое время и открывает комикс о двух локациях.', 'mapbtn','tap'),
 ('boss','Кто здесь главный?', 'Золотая рамка у круглого портрета на карте — действующий босс. Сцены разведки открывают слабое место; после свержения бывший хозяин остаётся в зоне и может искать реванш. «!» — доступный сюжет, пачка — схрон.', 'boss','read'),
 ('map_room','Вернись в комнату', 'Нажми на комнату с надписью «ВЫ ЗДЕСЬ» — это вернёт к сцене без траты времени. Чтобы пойти дальше, после обучения нажми ДРУГУЮ комнату.', 'room','tap'),
 ('more','Больше возможностей', 'Кнопка «⋯» открывает снаряжение, дуэль, схрон, задания и статус. Оружие и три ветки тренировок улучшают бой; в бою H покажет управление.', 'more','read'),
 ('menu','Записи и сохранения', 'Через ☰ доступны личное дело, настройки, слоты и справка. M — карта, J — задания, F2 — история чата, Ctrl+S — сохранение. Обучение можно отключить или запустить заново в настройках «Игра».', 'menu','read'),
 ('done','Теперь твой ход', 'Я не выбираю за тебя: начни с местных и изучи карту. Часы и последствия настоящие, но эту экскурсию всегда можно повторить. Удачи, новичок!', 'scene','read'),
)


def clamp_rect(rect,width,height,pad=7):
    """Clamp highlight to the actual viewport; keep a visible, clickable hole."""
    x0,y0,x1,y1=rect
    return (max(0,min(width-1,int(x0-pad))),max(0,min(height-1,int(y0-pad))),
            max(1,min(width,int(x1+pad))),max(1,min(height,int(y1+pad))))


def shades(rect,width,height):
    """Four nonoverlapping dark regions; nothing is placed over the highlighted UI."""
    x0,y0,x1,y1=rect
    return ((0,0,width,y0),(0,y1,width,height),(0,y0,x0,y1),(x1,y0,width,y1))

class MentorTour:
    def __init__(self,app):
        self.app=app;self.index=0;self.active=True;self.parts=[];self.bound=None;self.resize=None;self.pending=None;self.disabled=None
        app.mentor=self
        self.resize=app.root.bind('<Configure>',self._resize,add='+')
        self.paint()

    @property
    def step(self):return STEPS[self.index]

    def _resize(self,event):
        if not self.active or event.widget is not self.app.root:return
        if self.pending:return
        self.pending=self.app.root.after(80,self._repaint)

    def _repaint(self):
        self.pending=None
        if self.active:self.paint()

    def _rect(self,target):
        a=self.app
        widget={'scene':a.canvas,'hud':a.hud,'actions':a.actrow,'portrait':a.canvas,
                'entry':a.entry,'send':a.sendbutton,'mapbtn':a.mapbtn,
                'boss':a.map.c,'room':a.map.c,'more':a.morebtn,'menu':a.menubtn}[target]
        if target=='portrait':
            area=next((rect for rect,k in a.hits if k==a.npc),None)
            if not area:area=a.hits[0][0] if a.hits else None
        elif target in ('boss','room'):
            if target=='room':idx=a.world.s['loc']
            else:
                import core
                idx=next((n['home'] for k,n in a.npcs.items() if n['boss'] and core.in_power(a.world,k)),a.world.s['loc'])
            area=a.map.rects.get(idx)
        else:area=None
        if area is None:area=(0,0,widget.winfo_width(),widget.winfo_height())
        x=widget.winfo_rootx()-a.root.winfo_rootx();y=widget.winfo_rooty()-a.root.winfo_rooty()
        return widget,(x+area[0],y+area[1],x+area[2],y+area[3]),area

    def _clear(self):
        if self.bound:
            widget,sequence,bid=self.bound
            if bid:
                try:widget.unbind(sequence,bid)
                except tk.TclError:pass
            self.bound=None
        if self.disabled:
            try:self.disabled.config(state='normal')
            except tk.TclError:pass
            self.disabled=None
        for p in self.parts:
            try:p.destroy()
            except tk.TclError:pass
        self.parts.clear()

    def _place(self,widget,x,y,w,h):
        if w<=0 or h<=0:return
        widget.place(x=int(x),y=int(y),width=int(w),height=int(h));widget.lift()
        self.parts.append(widget)

    def paint(self):
        if not self.active:return
        self._clear();a=self.app;root=a.root
        width=max(1,root.winfo_width());height=max(1,root.winfo_height())
        if self.step[0]=='portrait' and not a.hits:self.index=6  # an empty room has nobody to talk to
        key,title,text,target,mode=self.step
        widget,raw,local=self._rect(target)
        if key=='more':
            widget.config(state='disabled');self.disabled=widget
        rect=clamp_rect(raw,width,height)
        for l,t,r,b in shades(rect,width,height):
            if r>l and b>t:self._place(tk.Frame(root,bg=INK,cursor='arrow'),l,t,r-l,b-t)
        x0,y0,x1,y1=rect
        # Four slim outlines do not intercept clicks inside the target area.
        for l,t,r,b in ((x0,y0,x1,y0+3),(x0,y1-3,x1,y1),(x0,y0,x0+3,y1),(x1-3,y0,x1,y1)):
            self._place(tk.Frame(root,bg=GOLD),l,t,r-l,b-t)
        side='right' if width-x1>=340 else 'left' if x0>=340 else 'bottom'
        pw,ph=310,335
        if side=='right':px=min(width-pw-8,x1+14);py=max(8,min(height-ph-8,(y0+y1-ph)//2))
        elif side=='left':px=max(8,x0-pw-14);py=max(8,min(height-ph-8,(y0+y1-ph)//2))
        else:px=max(8,(width-pw)//2);py=max(8,min(height-ph-8,y1+10 if height-y1>=ph+12 else y0-ph-10))
        card=tk.Frame(root,bg=PANEL,highlightbackground=GOLD,highlightthickness=2)
        self._place(card,px,py,pw,ph)
        face=a.base/'assets/mentor_v14.jpg'
        if face.is_file():
            with Image.open(face) as im:
                im=im.convert('RGB').resize((82,110),Image.Resampling.LANCZOS)
                self.photo=ImageTk.PhotoImage(im)
            tk.Label(card,image=self.photo,bg=PANEL).place(x=12,y=10)
        tk.Label(card,text='ДЕД МИРОН · НАСТАВНИК',fg=GOLD,bg=PANEL,font=('Segoe UI',12,'bold')).place(x=105,y=14)
        tk.Label(card,text=f'{self.index+1}/{len(STEPS)}  {title}',fg=FG,bg=PANEL,font=('Segoe UI',10,'bold'),wraplength=195,justify='left').place(x=105,y=43)
        if key=='welcome':
            import profile
            case,term,_=profile.origin(a.world)
            text+=' Твоё дело: '+case.lower()+'; срок: '+term.lower()+'.'
        if key=='boss':
            import core
            boss=next((k for k in a.npcs if a.npcs[k]['boss'] and core.in_power(a.world,k)),None)
            text+=(' Первый действующий хозяин: '+a.npcs[boss]['name']+'.' if boss else ' Сейчас действующих хозяев не осталось.')
        tk.Label(card,text=text,fg=FG,bg=PANEL,font=('Segoe UI',10),wraplength=280,justify='left',anchor='nw').place(x=13,y=122,width=284,height=171)
        if mode=='read':tk.Button(card,text='Дальше ▶',command=self.next,bg=GOLD,fg=INK,relief='flat').place(x=13,y=300,width=110,height=26)
        else:tk.Label(card,text='☝ Нажми на подсвеченное',fg=GOLD,bg=PANEL,font=('Segoe UI',9,'bold')).place(x=13,y=301)
        tk.Button(card,text='Отключить' if self.index<2 else 'Пропустить',command=self.skip,bg='#28374a',fg=FG,relief='flat').place(x=200,y=300,width=98,height=26)
        # Finger pointer, always outside the cutout. Decorative; does not steal clicks.
        hand=a.base/'assets/tutorial_hand.png'
        if hand.is_file():
            with Image.open(hand) as im:self.hand=ImageTk.PhotoImage(im.convert('RGBA'))
            if side=='right':hx=min(width-54,x1+4);hy=max(0,min(height-70,(y0+y1)//2-34))
            elif side=='left':hx=max(0,x0-55);hy=max(0,min(height-70,(y0+y1)//2-34))
            else:hx=max(0,min(width-54,(x0+x1)//2));hy=max(0,y0-72)
            pointer=tk.Label(root,image=self.hand,bg=INK,bd=0)
            self._place(pointer,hx,hy,54,70)
        if mode=='tap':
            seq='<ButtonRelease-1>' if target=='mapbtn' else '<Button-1>'
            step=self.index
            def touched(e):
                if not self.active or self.index!=step:return
                if local[0]<=e.x<=local[2] and local[1]<=e.y<=local[3]:root.after(100,self._after_tap)
            self.bound=(widget,seq,widget.bind(seq,touched,add='+'))

    def _after_tap(self):
        if self.active:self.next()

    def next(self):
        if not self.active:return
        if self.index==len(STEPS)-1:return self.finish()
        key=self.step[0]
        if key=='portrait' and not self.app.chat_open:self.app.open_chat()
        if key=='chat_send':self.app.close_chat(True)
        if key=='map' and self.app.view!='map':self.app.toggle_map()
        if key=='map_room' and self.app.view!='scene':self.app.show_scene()
        self.index+=1;self.paint()

    def skip(self):self.finish(disable=True)

    def finish(self,disable=False):
        if not self.active:return
        self.active=False;self._clear()
        if self.pending:
            try:self.app.root.after_cancel(self.pending)
            except tk.TclError:pass
        if self.resize:
            try:self.app.root.unbind('<Configure>',self.resize)
            except tk.TclError:pass
        self.app.mentor=None
        self.app.settings['tutorial_v14_done']=True
        if disable:self.app.settings['hints']=False
        meta.save_settings(self.app.base_data,self.app.settings)
        # Allow queued story scenes to resume once the tour is gone.
        self.app.root.after(100,self.app.pump)
