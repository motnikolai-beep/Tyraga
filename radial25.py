"""Original Tk dialogue wheel: geometry and interaction independent of FiveM code.

Keyboard shortcuts and a plain-button strip remain usable when circular targeting is
awkward. The caller supplies actual game callbacks, not strings or runtime evaluation.
"""
import math

BG='#090d12';PANEL='#101720';CARD='#182331';FG='#e6edf4';GOLD='#e5b767';MUTED='#8799ac'


def sector(x,y,cx,cy,outer,inner,count):
    """Index clockwise from twelve o'clock, or None for hub/outside."""
    if count<=0:return None
    distance=math.hypot(x-cx,y-cy)
    if distance<inner or distance>outer:return None
    angle=math.degrees(math.atan2(cy-y,x-cx))
    step=360/count
    return int(((90-angle+step/2)%360)//step)


def geometry(width,height):
    """Always leave room for labels and the central cancel button."""
    w=max(280,int(width));h=max(280,int(height))
    outer=max(112,min((w-55)//2,(h-25)//2,235))
    return w//2,h//2,outer,max(36,round(outer*.24))


def actions(app,k):
    """Only actual nearby, currently possible actions; no fabricated dialog choices."""
    if k not in app.world.witnesses():return []
    return [('talk','Говорить',app.open_chat),
            ('decide','Решения',app.decisions),
            ('knowledge','Кто что знает',app.knowledge_window),
            ('history','История беседы',app.show_history)]


class DialogueWheel:
    def __init__(self,app,k):
        import tkinter as tk
        self.tk=tk;self.app=app;self.k=k;self.items=actions(app,k);self.selected=0;self.closed=False
        if not self.items:raise ValueError('В этой локации нет выбранного собеседника')
        self.top=app.window('Колесо диалога · '+app.npcs[k]['name'],700,620)
        self.top.transient(app.root);self.top.protocol('WM_DELETE_WINDOW',self.close)
        self.top.configure(bg=BG)
        width,height=self.top._layout_size
        tk.Label(self.top,text=app.npcs[k]['name']+' · выберите действие',bg=BG,fg=GOLD,font=('Segoe UI',13,'bold'),
                 wraplength=max(200,width-40)).pack(side='top',pady=6)
        footer=tk.Frame(self.top,bg=BG);footer.pack(side='bottom',fill='x',padx=8,pady=(2,8))
        for i,(_,title,_) in enumerate(self.items):
            tk.Button(footer,text=f'{i+1} · {title}',command=lambda i=i:self.choose(i),
                      bg=CARD,fg=FG,relief='flat',font=('Segoe UI',9),
                      wraplength=max(65,(width-32)//len(self.items)-16),padx=3,pady=5).grid(row=0,column=i,sticky='nsew',padx=2)
            footer.columnconfigure(i,weight=1)
        self.canvas=tk.Canvas(self.top,bg=BG,highlightthickness=0)
        self.canvas.pack(side='top',fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw(e.width,e.height))
        self.canvas.bind('<Motion>',self.motion)
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<Leave>',lambda e:self.highlight(None))
        self.top.bind('<Escape>',lambda e:self.close())
        self.top.bind('<Return>',lambda e:self.choose(self.selected))
        self.top.bind('<Left>',lambda e:self.rotate(-1))
        self.top.bind('<Right>',lambda e:self.rotate(1))
        self.top.bind('<Tab>',lambda e:(self.rotate(1),'break')[1])
        for i in range(len(self.items)):
            self.top.bind(f'<Key-{i+1}>',lambda e,i=i:self.choose(i))
        self.top.grab_set()
        try:self.top.focus_force()
        except tk.TclError:pass
        self.draw(width,max(280,height-110))
    def draw(self,width=None,height=None):
        if self.closed:return
        c=self.canvas
        w=max(280,int(width if width is not None else c.winfo_width()))
        h=max(280,int(height if height is not None else c.winfo_height()))
        cx,cy,outer,inner=geometry(w,h);self.geom=(cx,cy,outer,inner)
        c.delete('all');step=360/len(self.items)
        for i,(_,title,_) in enumerate(self.items):
            angle=90-i*step
            chosen=i==self.selected
            c.create_arc(cx-outer,cy-outer,cx+outer,cy+outer,start=angle-step/2,extent=step,
                         style='pieslice',fill='#36506a' if chosen else CARD,outline=GOLD if chosen else '#405468',width=3)
            r=(outer+inner)*.54
            x=cx+r*math.cos(math.radians(angle));y=cy-r*math.sin(math.radians(angle))
            c.create_text(x,y,text=f'{i+1}\n{title}',fill=GOLD if chosen else FG,
                          font=('Segoe UI',10,'bold' if chosen else 'normal'),width=max(75,round(outer*.53)),justify='center')
        c.create_oval(cx-inner,cy-inner,cx+inner,cy+inner,fill=PANEL,outline=GOLD,width=3)
        c.create_text(cx,cy,text='НАЗАД\nEsc',fill=GOLD,font=('Segoe UI',9,'bold'),justify='center')
    def highlight(self,index):
        if index is not None and not 0<=index<len(self.items):return
        if self.selected!=index:self.selected=index;self.draw()
    def motion(self,event):
        cx,cy,outer,inner=self.geom
        self.highlight(sector(event.x,event.y,cx,cy,outer,inner,len(self.items)))
    def click(self,event):
        cx,cy,outer,inner=self.geom
        index=sector(event.x,event.y,cx,cy,outer,inner,len(self.items))
        if index is None:self.close()
        else:self.choose(index)
    def rotate(self,step):
        self.selected=((self.selected if self.selected is not None else 0)+step)%len(self.items)
        self.draw()
    def choose(self,index):
        if self.closed or not isinstance(index,int) or not 0<=index<len(self.items):return
        action=self.items[index][2]
        if self.k not in self.app.world.witnesses() or self.app.npc!=self.k:return self.close()
        self.close();action()
    def close(self):
        if self.closed:return
        self.closed=True
        try:self.top.grab_release();self.top.destroy()
        except self.tk.TclError:pass
        self.app.wheel=None
