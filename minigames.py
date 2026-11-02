import tkinter as tk,random
class Mini:
 def __init__(self,app,kind):
  self.a=app;self.kind=kind;self.r=random.Random();self.done=False;self.reward=[];self.timer=None;self.round=0;self.sc=0;self.closed=False;self.w=app.window('Мини-игра',720,660);self.w.transient(app.root);self.w.grab_set();self.w.protocol('WM_DELETE_WINDOW',self.close);self.info=app.label(self.w,'',12,wraplength=670);self.info.pack(pady=15);self.body=tk.Frame(self.w,bg='#101720');self.body.pack(fill='both',expand=True,padx=15);getattr(self,'start_'+kind)()
 def clear(self):
  for w in self.body.winfo_children():w.destroy()
 def btn(self,t,fn):self.a.button(self.body,t,fn).pack(fill='x',pady=4)
 def finish(self,t,reward=()):
  if self.done:return
  self.done=True;self.reward=list(reward)
  if self.timer:self.w.after_cancel(self.timer);self.timer=None
  self.clear();self.info.config(text=t);self.btn('Принять результат',self.close)
 def close(self):
  if self.closed:return
  self.closed=True
  if self.timer:
   try:self.w.after_cancel(self.timer)
   except tk.TclError:pass
  if self.done:
   for k,v in self.reward:self.a.world.s[k]=max(1 if k=='hp' else 0,self.a.world.s[k]+v)
   self.a.world.event('minigame_result','Завершена мини-игра '+self.kind+'.',self.a.world.witnesses())
   if self.a.world.s['dig']>=6:self.a.text_window('ПОБЕГ','Шесть участков готовы. Песочница продолжается.')
  self.a.mini=None;self.a.persist();self.a.refresh();self.w.grab_release();self.w.destroy()
 def start_porridge(self):
  self.pos=set(self.r.sample(range(36),5));self.opened=set();self.left=16;self.buttons={};self.info.config(text='Сапёр в каше: найдите 5 предметов за 16 открытий. Числа — предметы вокруг.');f=tk.Frame(self.body,bg='#101720');f.pack()
  for i in range(36):
   b=tk.Button(f,text='?',width=5,height=2,bg='#243449',fg='white',command=lambda i=i:self.porr(i));b.grid(row=i//6,column=i%6,padx=2,pady=2);self.buttons[i]=b
 def porr(self,i):
  if self.done or i in self.opened:return
  self.opened.add(i);self.left-=1;x,y=i%6,i//6
  if i in self.pos:self.sc+=1;t='✔'
  else:t=str(sum(abs(j%6-x)<=1 and abs(j//6-y)<=1 for j in self.pos))
  self.buttons[i].config(text=t,state='disabled');self.info.config(text=f'Найдено {self.sc}/5, осталось {self.left} открытий.')
  if self.sc==5:self.finish('Все предметы найдены.',[('cig',self.left+3)])
  elif self.left==0:self.finish('Открытия закончились.',[('cig',self.sc)])
 def start_poker(self):
  self.my=self.r.randint(1,13);self.enemy=self.r.randint(1,13);self.info.config(text=f'Покер на одной карте. У вас {self.my}, чужая скрыта.')
  for i,t in enumerate(['Честно · 2 сиг.','Блеф · 5 сиг.','Подмена · риск','Сброс · -1 сиг.']):self.btn(t,lambda i=i:self.poker(i))
 def poker(self,i):
  if self.done:return
  if i==3:return self.finish('Сброс.',[('cig',-1)])
  if i==2:
   if self.r.random()<.4:return self.finish('Подмену заметили.',[('cig',-4)])
   self.my=13
  if i==1 and self.r.random()<.3:return self.finish('Блеф удался.',[('cig',2)])
  st=5 if i==1 else 2;v=st if self.my>=self.enemy else -st;self.finish(f'Карта противника {self.enemy}, итог {v:+d} сиг.',[('cig',v)])
 def start_chess(self):
  self.info.config(text='Шахматы Лема — абстрактная тактика, не полные шахматы. Атака бьёт хитрость, хитрость — защиту, защита — атаку. 3 раунда.')
  for i,t in enumerate(['Атака','Защита','Хитрость']):self.btn(t,lambda i=i:self.chess(i))
 def chess(self,i):
  if self.done:return
  e=self.r.randrange(3);self.sc+=int({0:2,2:1,1:0}[i]==e);self.round+=1;self.info.config(text=f'Лем выбрал { ["атаку","защиту","хитрость"][e] }. Раунд {self.round}, побед {self.sc}.')
  if self.round==3:self.finish('Лем записал результат.',[('cig',4)] if self.sc>=2 else [])
 def start_tunnel(self):
  self.grid=[[2 if self.r.random()<.25 else 1 for x in range(8)] for y in range(5)];self.x=0;self.y=2;self.spoon=16;self.noise=0;self.tdraw()
  for key,dx,dy in [('Up',0,-1),('Down',0,1),('Left',-1,0),('Right',1,0)]:self.w.bind('<'+key+'>',lambda e,dx=dx,dy=dy:self.move(dx,dy))
  self.w.focus_set()
 def tdraw(self):
  self.clear();self.info.config(text=f'Выход справа. Ложка {self.spoon}, шум {self.noise}.');t='\n'.join(' '.join('●' if (x,y)==(self.x,self.y) else 'Д' if x==7 else '■' if self.grid[y][x]==2 else '·' if self.grid[y][x]==0 else '□' for x in range(8)) for y in range(5));self.a.label(self.body,t,25).pack()
  for t,dx,dy in [('Вверх',0,-1),('Влево',-1,0),('Вниз',0,1),('Вправо',1,0)]:self.btn(t,lambda dx=dx,dy=dy:self.move(dx,dy))
 def move(self,dx,dy):
  if self.done:return
  x,y=self.x+dx,self.y+dy
  if not(0<=x<8 and 0<=y<5):return
  cost=self.grid[y][x]
  if self.spoon<cost:return self.finish('Ложка сломалась.')
  self.spoon-=cost;self.noise+=cost;self.grid[y][x]=0;self.x=x;self.y=y
  if x==7:return self.finish('Шум услышали.' if self.noise>=15 else 'Участок готов.',[('hp',-10)] if self.noise>=15 else [('dig',1)])
  self.tdraw()
 def start_dance(self):
  self.info.config(text='Баня: 12 шагов, на каждый секунда.');self.arrow=self.a.label(self.body,'',64,True);self.arrow.pack(pady=15);f=tk.Frame(self.body,bg='#101720');f.pack()
  for i,t in enumerate(['←','↑','↓','→']):self.a.button(f,t,lambda i=i:self.dance(i)).pack(side='left')
  for key,i in [('Left',0),('Up',1),('Down',2),('Right',3)]:self.w.bind('<'+key+'>',lambda e,i=i:self.dance(i))
  self.w.focus_set();self.next_arrow()
 def next_arrow(self):
  if self.round==12:return self.finish(f'Попаданий {self.sc}/12.',[('cig',self.sc//3)])
  self.round+=1;self.current=self.r.randrange(4);self.arrow.config(text=['←','↑','↓','→'][self.current]);self.timer=self.w.after(1000,self.miss)
 def miss(self):self.timer=None;self.next_arrow()
 def dance(self,i):
  if self.done:return
  if self.timer:self.w.after_cancel(self.timer);self.timer=None
  self.sc+=int(i==self.current);self.next_arrow()
 def start_factory(self):
  self.info.config(text='Про кого пустить слух?')
  for k in ['gvo','zub','graf','buh']:self.btn(self.a.npcs[k]['name'],lambda k=k:self.target(k))
 def target(self,k):
  self.clear();self.k=k
  for t in ['воровал чай','боится крыс','тайно пишет стихи','просит справку о справке']:self.btn(t,lambda t=t:self.factory(t))
 def factory(self,t):
  if self.done:return
  w=self.a.world;e=w.event('rumor_origin','Игрок сочинил слух о '+self.a.npcs[self.k]['name']+'.',w.witnesses())
  for k in w.witnesses():w.gossip(k,k,'Неподтверждённый слух: '+self.a.npcs[self.k]['name']+' '+t+'.',e['id'],45,0,'выдумка игрока',[])
  self.finish('Слух пущен, но не стал фактом.',[('rub',5)])
