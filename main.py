import tkinter as tk,json,queue,threading,uuid,copy,traceback,hashlib,re
from tkinter import ttk,messagebox
from pathlib import Path
from PIL import Image,ImageTk,ImageOps
from runtime_manager import Engine
from world import World,NAMES,save
from battle_ui import BattleWindow
from minigames import Mini
from sound import Sound
import ai
BASE=Path(__file__).resolve().parent
BG='#090d12';PANEL='#101720';CARD='#182331';FG='#e6edf4';MUTED='#8799ac';GOLD='#e5b767'
class App:
 def __init__(self,root):
  self.root=root;root.title('Тюряга · Свои люди v7');root.geometry('1540x980');root.minsize(1120,800);root.configure(bg=BG);root.columnconfigure(0,weight=1);root.rowconfigure(2,weight=1)
  self.npcs=json.loads((BASE/'npcs.json').read_text(encoding='utf8'));self.path=BASE/'saves/town_v4.json';state=None
  if self.path.exists():
   try:state=json.loads(self.path.read_text(encoding='utf8'))
   except Exception as e:messagebox.showwarning('Сохранение',str(e))
  self.world=World(self.npcs,state);self.engine=Engine(BASE);self.sound=Sound(BASE);self.q=queue.Queue();self.liveq=queue.Queue();self.job=None;self.cancel_event=None;self.connected=False;self.closed=False;self.npc=None;self.hover=None;self.hits=[];self.bubble_hits=[];self.cache={};self.navrefs={};self.cover=True;self.battle=None;self.battle_window=None;self.mini=None;self.stream_text={};self.draft_speech={}
  st=ttk.Style(root)
  try:st.theme_use('clam')
  except tk.TclError:pass
  st.configure('Dark.TCombobox',fieldbackground=CARD,background=CARD,foreground=FG,arrowcolor=GOLD,padding=7);st.map('Dark.TCombobox',fieldbackground=[('readonly',CARD)],foreground=[('readonly',FG)])
  self.build_header();self.build_nav();self.build_scene();self.select_default();root.protocol('WM_DELETE_WINDOW',self.close);root.bind('<Control-s>',lambda e:self.persist());root.bind('<F2>',lambda e:self.show_history());root.after(80,self.poll);root.after(30000,self.autosave);self.refresh();self.connect()
 def label(self,parent,text='',size=11,bold=False,color=None,**kw):return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color or FG,font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)
 def button(self,parent,text,fn,primary=False):return tk.Button(parent,text=text,command=fn,bg=GOLD if primary else CARD,fg='#111821' if primary else FG,activebackground='#e9c88f' if primary else '#24364a',activeforeground='#111821' if primary else FG,relief='flat',bd=0,font=('Segoe UI',10,'bold'),padx=12,pady=8,cursor='hand2')
 def window(self,title,w=900,h=650):
  p=tk.Toplevel(self.root);p.title(title);p.geometry(f'{w}x{h}');p.configure(bg=PANEL);return p
 def build_header(self):
  f=tk.Frame(self.root,bg=BG);f.grid(row=0,column=0,sticky='ew',padx=14,pady=(10,6));f.columnconfigure(1,weight=1)
  self.label(f,'ТЮРЯГА',18,True,color=GOLD).grid(row=0,column=0,padx=(0,20));self.hud=self.label(f,size=11,color=MUTED);self.hud.grid(row=0,column=1,sticky='w')
  self.modebutton=self.button(f,'Быстрый режим',self.toggle_mode);self.modebutton.grid(row=0,column=2,padx=3);self.button(f,'Сохранить',self.persist).grid(row=0,column=3,padx=3)
  mb=tk.Menubutton(f,text='Система ▾',bg=CARD,fg=FG,relief='flat',font=('Segoe UI',10),padx=12,pady=8);m=tk.Menu(mb,tearoff=0,bg=PANEL,fg=FG)
  for t,fn in [('Подключить ИИ',self.connect),('История разговора · F2',self.show_history),('Новый разговор с NPC',self.reset_chat),('Журналы мира',self.journal),('Уважуха',self.respect_window),('Постоянные жители',self.residents),('Настройки',lambda:self.text_window('Настройки',json.dumps(self.engine.cfg,ensure_ascii=False,indent=1))),('Лог сервера',lambda:self.text_window('llama-server',self.engine.tail()))]:m.add_command(label=t,command=fn)
  mb.config(menu=m);mb.grid(row=0,column=4,padx=3)
 def build_nav(self):
  f=tk.Frame(self.root,bg=BG);f.grid(row=1,column=0,sticky='ew',padx=12);f.columnconfigure(0,weight=1);c=tk.Canvas(f,height=74,bg=BG,highlightthickness=0);c.grid(row=0,column=0,sticky='ew');sb=tk.Scrollbar(f,orient='horizontal',command=c.xview);sb.grid(row=1,column=0,sticky='ew');c.config(xscrollcommand=sb.set);frame=tk.Frame(c,bg=BG);c.create_window((0,0),window=frame,anchor='nw');self.navbuttons={}
  for i,name in enumerate(NAMES):
   self.navrefs[i]=ImageTk.PhotoImage(ImageOps.fit(Image.open(BASE/f'assets/loc_{i}.jpg'),(94,40),method=Image.Resampling.LANCZOS));b=tk.Button(frame,text=name.upper(),image=self.navrefs[i],compound='top',command=lambda i=i:self.go(i),bg=CARD,fg=FG,activebackground='#24364a',activeforeground=GOLD,relief='flat',font=('Segoe UI',8,'bold'),padx=5,pady=4,width=104);b.grid(row=0,column=i,padx=3);self.navbuttons[i]=b
  frame.bind('<Configure>',lambda e:c.config(scrollregion=c.bbox('all')))
 def build_scene(self):
  f=self.scene=tk.Frame(self.root,bg=PANEL);f.grid(row=2,column=0,sticky='nsew',padx=12,pady=8);f.columnconfigure(0,weight=1);f.rowconfigure(1,weight=1)
  h=tk.Frame(f,bg=PANEL);h.grid(row=0,column=0,sticky='ew',padx=14,pady=(10,6));h.columnconfigure(0,weight=1);self.title=self.label(h,size=18,bold=True);self.title.grid(row=0,column=0,sticky='w');self.hint=self.label(h,size=9,color=MUTED);self.hint.grid(row=1,column=0,sticky='w',pady=3);self.coverbtn=self.button(h,'Фон: заполнить',self.toggle_cover);self.coverbtn.grid(row=0,column=1,rowspan=2)
  self.canvas=tk.Canvas(f,bg='#070b10',highlightthickness=0);self.canvas.grid(row=1,column=0,sticky='nsew',padx=8);self.canvas.bind('<Configure>',lambda e:self.draw());self.canvas.bind('<Motion>',self.motion);self.canvas.bind('<Button-1>',self.click)
  self.notice=tk.Frame(f,bg='#17232c');self.notice.grid(row=2,column=0,sticky='ew',padx=8,pady=4)
  row=tk.Frame(f,bg=PANEL);row.grid(row=3,column=0,sticky='ew',padx=8,pady=4)
  actions=[('Дуэль',self.fight),('Решения',self.decisions),('Снаряжение',self.equipment),('Работа',lambda:self.action('work')),('Паёк · 2 сиг.',lambda:self.action('eat')),('Отбой',lambda:self.action('sleep')),('Мини-игры',self.games),('Журнал',self.journal)]
  for i,(t,fn) in enumerate(actions):row.columnconfigure(i,weight=1);self.button(row,t,fn).grid(row=0,column=i,sticky='ew',padx=2)
  row=tk.Frame(f,bg=PANEL);row.grid(row=4,column=0,sticky='ew',padx=10,pady=5);row.columnconfigure(1,weight=1)
  self.who=self.label(row,size=12,bold=True);self.who.grid(row=0,column=0,sticky='w',padx=(0,12));self.npcbox=ttk.Combobox(row,state='readonly',style='Dark.TCombobox',width=24);self.npcbox.grid(row=1,column=0,sticky='ew',padx=(0,12));self.npcbox.bind('<<ComboboxSelected>>',lambda e:self.pick_npc());self.relation=self.label(row,size=9,color=MUTED);self.relation.grid(row=2,column=0,sticky='w')
  self.entry=tk.Text(row,height=3,wrap='word',bg=CARD,fg=FG,insertbackground=GOLD,font=('Segoe UI',12),relief='flat',padx=12,pady=10);self.entry.grid(row=0,column=1,rowspan=3,sticky='ew',padx=(0,10));self.entry.bind('<Return>',self.enter);self.entry.bind('<Shift-Return>',self.newline);self.entry.bind('<Control-Return>',self.enter)
  self.sendbutton=self.button(row,'СКАЗАТЬ ↵',self.send,True);self.sendbutton.grid(row=0,column=2,sticky='ew');self.button(row,'Отмена',self.cancel).grid(row=1,column=2,sticky='ew',pady=3);self.button(row,'История · F2',self.show_history).grid(row=2,column=2,sticky='ew')
  status=tk.Frame(f,bg=PANEL);status.grid(row=5,column=0,sticky='ew',padx=10,pady=(0,8));status.columnconfigure(1,weight=1);self.private=tk.BooleanVar(value=False);tk.Checkbutton(status,text='Наедине',variable=self.private,bg=PANEL,fg=MUTED,selectcolor=CARD,activebackground=PANEL).grid(row=0,column=0)
  self.status=self.label(status,size=9,color=MUTED,wraplength=1100,justify='left');self.status.grid(row=0,column=1,sticky='w',padx=10)
 def blocked(self):return bool(self.job or self.battle or self.mini)
 def persist(self):
  try:save(self.world.s,self.path)
  except Exception as e:messagebox.showerror('Сохранение',str(e))
 def autosave(self):
  if not self.closed:self.persist();self.root.after(30000,self.autosave)
 def close(self):
  self.closed=True
  if self.cancel_event:self.cancel_event.set()
  self.job=None
  if self.battle:self.battle.finish()
  self.persist();self.root.destroy()
 def launch(self,kind,fn,meta=None):
  if self.job:return False
  id=uuid.uuid4().hex;cancel=threading.Event();self.cancel_event=cancel;self.job={'id':id,'kind':kind,'meta':meta};self.status.config(text={'start':'Загрузка модели…','chat':'NPC отвечает…','initiative':'NPC обдумывает свои дела…'}[kind])
  def worker():
   try:self.q.put((id,fn(id,cancel),None))
   except Exception as e:self.q.put((id,None,str(e)))
  threading.Thread(target=worker,daemon=True).start();return True
 def connect(self):
  if not self.blocked():self.launch('start',lambda id,cancel:self.engine.connect())
 def cancel(self):
  if self.job and self.job['kind']=='start':return self.status.config(text='Дождитесь запуска или закройте игру.')
  if self.cancel_event:self.cancel_event.set()
  self.job=None;self.stream_text.clear();self.draft_speech.clear();self.draw();self.status.config(text='Отменено. Поздний ответ не применяется; сервер может ещё вычислять его.')
 def enter(self,e=None):self.send();return 'break'
 def newline(self,e=None):self.entry.insert('insert','\n');return 'break'
 def send(self):
  if self.blocked():return
  if not self.connected:return self.status.config(text='ИИ не подключён.')
  if not self.npc or self.npc not in self.world.witnesses():return
  text=self.entry.get('1.0','end').strip()
  if not text:return
  if len(text)>int(self.engine.cfg['CHAT_MAX_INPUT_CHARS']):return self.status.config(text='Превышен технический CHAT_MAX_INPUT_CHARS.')
  k=self.npc;private=self.private.get() or self.engine.cfg['GOSSIP_ENABLED'].lower()!='true';snap=World(self.npcs,copy.deepcopy(self.world.s));self.draft_speech[k]=text;self.stream_text[k]='…';self.draw()
  self.launch('chat',lambda id,cancel:ai.generate_chat(self.engine,snap,k,text,lambda partial:self.liveq.put((id,k,partial)),cancel),{'npc':k,'text':text,'private':private})
 def initiative(self,trigger):
  if self.blocked() or not self.connected or self.engine.cfg['CHAT_FAST_MODE'].lower()=='true' or self.engine.cfg['NPC_INITIATIVE'].lower()!='true' or self.entry.get('1.0','end').strip():return
  k=self.world.candidate()
  if not k:return
  snap=World(self.npcs,copy.deepcopy(self.world.s));self.launch('initiative',lambda id,cancel:ai.generate_initiative(self.engine,snap,k,trigger,cancel),{'npc':k})
 def propagate(self):return self.world.relay() if self.engine.cfg['GOSSIP_ENABLED'].lower()=='true' else []
 def poll(self):
  if self.closed:return
  latest={}
  try:
   while True:
    id,k,text=self.liveq.get_nowait()
    if self.job and id==self.job['id']:latest[k]=text
  except queue.Empty:pass
  if latest:self.stream_text.update(latest);self.draw()
  try:
   while True:
    id,result,error=self.q.get_nowait()
    if not self.job or id!=self.job['id']:continue
    job=self.job;self.job=None;self.stream_text.clear();self.draft_speech.clear()
    if error:
     self.status.config(text='Ошибка: '+error[:600]);self.draw()
     if job['kind']=='start':self.connected=False;self.text_window('Ошибка запуска',error)
     continue
    if job['kind']=='start':self.connected=True;self.status.config(text='ИИ готов. Выберите персонажа и говорите.')
    elif job['kind']=='chat':
     m=job['meta'];ai.accept(self.world,m['npc'],m['text'],result,m['private']);self.entry.delete('1.0','end');self.sound.play('ok');self.status.config(text='Ответ получен. История — по кнопке F2.');self.persist();self.refresh();self.chat_combat(m,result)
    else:
     try:self.world.initiative(job['meta']['npc'],result);self.persist();self.refresh();self.status.config(text='NPC продолжает свои дела.')
     except Exception as e:self.status.config(text='Инициатива не применена: '+str(e))
  except queue.Empty:pass
  self.sendbutton.config(state='disabled' if self.blocked() or not self.connected else 'normal');self.root.after(80,self.poll)
 def chat_combat(self,m,result):
  intent=result.get('_combat_intent');k=m['npc']
  if not intent or k not in self.world.witnesses() or self.battle or self.mini:return
  id=hashlib.sha256((str(self.world.s['day'])+k+m['text']+result['reply']).encode()).hexdigest();tokens=self.world.s['chat_fight_tokens']
  if id in tokens:return
  tokens.append(id);self.world.s['chat_fight_tokens']=tokens[-100:];self.world.event('chat_threat',('Игрок угрожал '+self.npcs[k]['name'] if intent['speaker']=='player' else self.npcs[k]['name']+' угрожал игроку')+': '+intent['evidence'],[k] if m['private'] else self.world.witnesses());self.persist();self.fight(k,False)
 def toggle_mode(self):
  if self.blocked():return self.status.config(text='Сначала завершите текущий запрос или бой.')
  fast=self.engine.cfg['CHAT_FAST_MODE'].lower()!='true';self.engine.cfg['CHAT_FAST_MODE']='true' if fast else 'false'
  p=BASE/'.env';text=p.read_text(encoding='utf-8-sig') if p.exists() else '';key='CHAT_FAST_MODE='+self.engine.cfg['CHAT_FAST_MODE']
  text=re.sub(r'^CHAT_FAST_MODE=.*$',key,text,flags=re.M) if re.search(r'^CHAT_FAST_MODE=',text,re.M) else text+'\n'+key;p.write_text(text+'\n',encoding='utf8');self.refresh();self.status.config(text='Быстро: один запрос, без оценок и инициатив.' if fast else 'Полно: добавлены оценки кармы/угроз/дохода и инициативы. Это медленнее.')
 def select_default(self):
  self.local_ids=self.world.witnesses();self.npc=self.local_ids[0] if self.local_ids else None;self.npcbox.config(values=[self.npcs[k]['name'] for k in self.local_ids])
  if self.local_ids:self.npcbox.current(0)
 def pick_npc(self):
  if self.blocked():return
  i=self.npcbox.current()
  if 0<=i<len(self.local_ids):self.select(self.local_ids[i])
 def select(self,k):
  if self.blocked() or k not in self.world.witnesses():return
  self.npc=k;self.npcbox.current(self.local_ids.index(k));self.refresh();self.entry.focus_set()
 def go(self,i):
  if self.blocked():return self.status.config(text='Завершите действие или отмените запрос перед переходом.')
  self.world.go(i);self.propagate();self.hover=None;self.stream_text.clear();self.draft_speech.clear();self.select_default();self.persist();self.refresh();self.initiative('player_entered')
 def toggle_cover(self):self.cover=not self.cover;self.coverbtn.config(text='Фон: заполнить' if self.cover else 'Фон: целиком');self.draw()
 def draw(self):
  c=self.canvas;c.delete('all');w=max(1,c.winfo_width());h=max(1,c.winfo_height())
  if w<20 or h<20:return
  loc=self.world.s['loc'];key=(loc,w,h,self.cover)
  if key not in self.cache:
   if len(self.cache)>35:self.cache.clear()
   im=Image.open(BASE/f'assets/loc_{loc}.jpg').convert('RGB')
   if self.cover:im=ImageOps.fit(im,(w,h),method=Image.Resampling.LANCZOS)
   else:im.thumbnail((w,h),Image.Resampling.LANCZOS);bg=Image.new('RGB',(w,h),'#070b10');bg.paste(im,((w-im.width)//2,(h-im.height)//2));im=bg
   self.cache[key]=ImageTk.PhotoImage(im)
  self.bgref=self.cache[key];c.create_image(0,0,anchor='nw',image=self.bgref);self.hits=[];self.bubble_hits=[];present=self.world.witnesses();pw=max(75,min(170,int(w*.18),int(h*.44/1.58)));ph=int(pw*1.58);gap=40;start=(w-len(present)*pw-max(0,len(present)-1)*gap)//2
  c.create_rectangle(0,0,w,44,fill='#0b1420',stipple='gray50',outline='');c.create_text(14,15,text=NAMES[loc].upper(),anchor='w',fill=GOLD,font=('Segoe UI',10,'bold'))
  for i,k in enumerate(present):
   x=start+i*(pw+gap);y=max(40,h-ph-65);key=('npc',k,pw,ph)
   if key not in self.cache:self.cache[key]=ImageTk.PhotoImage(Image.open(BASE/f'assets/{self.npcs[k]["portrait"]}.jpg').resize((pw,ph),Image.Resampling.LANCZOS))
   active=k==self.npc or k==self.hover;c.create_rectangle(x-4,y-4,x+pw+4,y+ph+27,fill='#141b24',outline=GOLD if active else '#2b3c50',width=2);c.create_image(x,y,anchor='nw',image=self.cache[key]);c.create_text(x+pw/2,y+ph+14,text=self.npcs[k]['name'],fill=GOLD if active else FG,font=('Segoe UI',10,'bold'))
   maximum=120 if self.npcs[k]['boss'] else 90;hp=self.world.s['npc_health'].get(k,maximum);c.create_rectangle(x,y-23,x+pw,y-8,fill='#211218',outline='');c.create_rectangle(x,y-23,x+pw*max(0,hp)/maximum,y-8,fill='#c45867',outline='');c.create_text(x+pw/2,y-16,text=f'{hp}/{maximum} HP',fill='white',font=('Segoe UI',9,'bold'));self.hits.append(((x-4,y-4,x+pw+4,y+ph+27),k))
  if self.npc:
   hist=self.world.s['history'].get(self.npc,[]);speech=self.stream_text.get(self.npc)
   if speech is None:speech=next((m['content'] for m in reversed(hist) if m['role']=='assistant'),'')
   user=self.draft_speech.get(self.npc) or next((m['content'] for m in reversed(hist) if m['role']=='user'),'');hit=next((rect for rect,k in self.hits if k==self.npc),None)
   if speech and hit:self.bubble(speech,hit,self.npcs[self.npc]['name'])
   if user:c.create_rectangle(12,h-34,min(w-12,1100),h-7,fill='#152532',outline='#34536a');c.create_text(24,h-21,anchor='w',text='ВЫ  '+(user if len(user)<130 else user[:127]+'…'),fill='#8fc5ec',font=('Segoe UI',11))
 def bubble(self,text,hit,name):
  c=self.canvas;cw=c.winfo_width();x0,y0,x1,y1=hit;maxw=min(650,max(280,cw-40));cx=(x0+x1)/2;display=text.strip()
  if len(display)>460:display=display[:457]+'…\n[Нажмите, чтобы прочитать целиком]'
  x=max(14,min(cw-maxw-14,cx-maxw/2));item=c.create_text(x+14,max(70,y0-32),anchor='sw',text=display,width=maxw-28,fill=FG,font=('Segoe UI',12),justify='left');box=c.bbox(item)
  if not box:return
  if box[1]<52:c.move(item,0,52-box[1]);box=c.bbox(item)
  rect=(box[0]-12,box[1]-10,box[2]+12,box[3]+10);bg=c.create_rectangle(*rect,fill='#101b26',outline=GOLD,width=2);c.tag_lower(bg,item);tip=c.create_polygon(cx-7,rect[3],cx+7,rect[3],cx,rect[3]+9,fill='#101b26',outline=GOLD);c.tag_lower(tip,item);self.bubble_hits.append((rect,text,name))
 def motion(self,e):
  k=next((k for (x,y,r,b),k in self.hits if x<=e.x<=r and y<=e.y<=b),None)
  if k!=self.hover:self.hover=k;self.canvas.config(cursor='hand2' if k else '');self.draw()
 def click(self,e):
  for (x,y,r,b),text,name in self.bubble_hits:
   if x<=e.x<=r and y<=e.y<=b:return self.text_window(name,text)
  self.motion(e)
  if self.hover and not self.blocked():self.sound.play('click');self.select(self.hover)
 def refresh(self):
  s=self.world.s;rep=self.world.reputation(self.npc or 'zub')['public_respect'];self.hud.config(text=f"Д{s['day']} · Ходы {s['ap']}/6 · HP {s['hp']} · Силы {s['stamina']} · ₽{s['rub']} · Сиг. {s['cig']} · Уваж. {rep:+.1f}");self.title.config(text=NAMES[s['loc']]);self.hint.config(text='Местные: '+', '.join(self.npcs[k]['name'] for k in self.world.witnesses()))
  for i,b in self.navbuttons.items():b.config(bg='#5c4831' if i==s['loc'] else CARD,fg=GOLD if i==s['loc'] else FG)
  if self.npc:self.who.config(text=self.npcs[self.npc]['name']);self.relation.config(text=f"Отношение {s['relations'].get(self.npc,0):+d}")
  self.modebutton.config(text='Быстро · 1 запрос' if self.engine.cfg['CHAT_FAST_MODE'].lower()=='true' else 'Полный режим');self.draw();self.render_notices()
 def show_history(self):
  if not self.npc:return
  text='\n\n'.join(('Вы' if m['role']=='user' else self.npcs[self.npc]['name'])+': '+m['content'] for m in self.world.s['history'].get(self.npc,[]));self.text_window('История · '+self.npcs[self.npc]['name'],text or 'Переписка пуста.')
 def reset_chat(self):
  if self.blocked() or not self.npc:return
  if not messagebox.askyesno('Новый разговор','Архивировать старую переписку и заметки? События, отношения и карма сохранятся.'):return
  s=self.world.s;k=self.npc;s.setdefault('dialogue_archives',[]).append({'npc':k,'day':s['day'],'history':s['history'].get(k,[]),'memory':s['memory'].get(k,[])});s['dialogue_archives']=s['dialogue_archives'][-30:];s['history'][k]=[];s['memory'][k]=[];self.stream_text.clear();self.draft_speech.clear();self.persist();self.refresh()
 def render_notices(self):
  for w in self.notice.winfo_children():w.destroy()
  pending=[o for o in self.world.s['notices'] if o['status']=='pending' and o['npc'] in self.world.witnesses()]
  if not pending:self.label(self.notice,'● Рядом спокойно',9,color=MUTED).pack(anchor='w',padx=10,pady=7);return
  o=pending[0];self.label(self.notice,self.npcs[o['npc']]['name']+' · '+o['action'],10,True,color=GOLD).pack(anchor='w',padx=10,pady=(7,2));self.label(self.notice,o['reply'],10,wraplength=1200,justify='left').pack(fill='x',padx=10);row=tk.Frame(self.notice,bg='#17232c');row.pack(fill='x',padx=8,pady=6);self.button(row,'Ответить / принять',lambda:self.resolve(o['id'],True),True).pack(side='left',padx=3);self.button(row,'Позже',lambda:self.resolve(o['id'],False)).pack(side='left',padx=3)
 def resolve(self,id,accept):
  if self.blocked():return
  o=next(x for x in self.world.s['notices'] if x['id']==id)
  try:
   result=self.world.resolve(id,accept)
   if accept:
    ai.mark_rumors(self.world,o['npc'],o.get('rumors_used',[]))
    if result in ('talk','warn'):self.world.s['history'].setdefault(o['npc'],[]).append({'role':'assistant','content':o['reply']});self.select(o['npc'])
   self.persist();self.refresh()
   if result=='attack':self.fight(o['npc'],True)
   elif result=='done':self.text_window('Дело выполнено','Результат записан в мир. Отношение улучшилось.')
  except ValueError as e:self.status.config(text=str(e))
 def action(self,name):
  if self.blocked():return
  if name=='sleep' and self.world.s['ap']>0 and not messagebox.askyesno('Закончить день',f"Осталось {self.world.s['ap']} действий. Перейти к следующему дню?"):return
  try:getattr(self.world,name)();self.propagate();self.persist();self.refresh();self.initiative('end_day' if name=='sleep' else 'player_action')
  except ValueError as e:self.status.config(text=str(e))
 def text_window(self,title,text):
  w=self.window(title);self.label(w,title,16,True).pack(anchor='w',padx=16,pady=14);frame=tk.Frame(w,bg=PANEL);frame.pack(fill='both',expand=True,padx=12,pady=(0,12));t=tk.Text(frame,wrap='word',bg='#0b1119',fg=FG,relief='flat',font=('Segoe UI',11),padx=12,pady=12);t.pack(side='left',fill='both',expand=True);sb=tk.Scrollbar(frame,command=t.yview);sb.pack(side='right',fill='y');t.config(yscrollcommand=sb.set);t.insert('1.0',text);t.config(state='disabled')
 def journal(self):
  w=self.window('Журналы мира · отладка',1100,700);row=tk.Frame(w,bg=PANEL);row.pack(fill='x');t=tk.Text(w,wrap='word',bg='#0b1119',fg=FG,relief='flat',font=('Segoe UI',11));t.pack(fill='both',expand=True)
  def show(k):t.delete('1.0','end');t.insert('1.0',json.dumps(self.world.s[k],ensure_ascii=False,indent=1))
  for title,k in [('События','events'),('Знания','knowledge'),('Сплетни','gossip'),('Карма','audit'),('Дневник','diary'),('Хроника','chron'),('Долги','obligations'),('Доход','dialogue_money')]:self.button(row,title,lambda k=k:show(k)).pack(side='left',padx=2)
  show('events')
 def respect_window(self):self.text_window('Уважуха',json.dumps({'context':self.world.reputation(self.npc or 'zub'),'events':self.world.s['street_rep']['audit']},ensure_ascii=False,indent=1))
 def residents(self):self.text_window('Местные жители','\n\n'.join(NAMES[i]+': '+', '.join(n['name'] for n in self.npcs.values() if n['home']==i) for i in range(12)))
 def decisions(self):
  if self.blocked() or not self.npc:return
  k=self.npc;w=self.window('Решения · '+self.npcs[k]['name'],680,500)
  def do(fn):
   try:fn();self.propagate();self.persist();self.refresh();w.destroy();self.initiative('decision')
   except ValueError as e:messagebox.showinfo('Решение',str(e))
  for t,kind in [('Помочь · 2 сигареты','help'),('Украсть · +15₽, NPC заметит','theft'),('Сдать охране · +25₽','betrayal')]:self.button(w,t,lambda kind=kind:do(lambda:self.world.decision(k,kind))).pack(fill='x',padx=15,pady=4)
  def companion():self.world.s['companion']=k
  self.button(w,'Назначить напарником (остаётся здесь)',lambda:do(companion)).pack(fill='x',padx=15,pady=4);self.button(w,'Занять 10₽ до завтра',lambda:do(lambda:self.world.borrow(k))).pack(fill='x',padx=15,pady=4);self.button(w,'Вернуть долг',lambda:do(lambda:self.world.repay(k))).pack(fill='x',padx=15,pady=4)
  def deny():
   pop=self.window('Оспорить слух',750,500)
   for g in self.world.heard(k):self.button(pop,g['claim'][:100],lambda id=g['id']:(do(lambda:self.world.deny(k,id)),pop.destroy())).pack(fill='x',padx=10,pady=3)
  self.button(w,'Оспорить услышанный NPC слух',deny).pack(fill='x',padx=15,pady=4)
 def equipment(self):
  if self.blocked():return
  w=self.window('Экипировка',650,390);self.label(w,json.dumps(self.world.s['gear'],ensure_ascii=False),11,wraplength=600).pack(pady=15)
  def buy(k):
   try:self.world.buy(k);self.persist();self.refresh();w.destroy()
   except ValueError as e:messagebox.showinfo('Ресурсы',str(e))
  for t,k in [('Заточка · урон 24 · 40₽','knife'),('Телогрейка · броня 7 · 35₽','armor'),('Перевязка · +35 HP · 10₽','heal')]:self.button(w,t,lambda k=k:buy(k)).pack(fill='x',padx=15,pady=5)
 def fight(self,k=None,ambush=False):
  if self.blocked():return
  manual=k is None;k=k or self.npc
  if not k or k not in self.world.witnesses():return
  if self.world.s['npc_health'].get(k,1)<=0:return self.status.config(text='Противник уже побеждён. Новый бой после отбоя.')
  if manual and not messagebox.askyesno('Дуэль','Начать бой с '+self.npcs[k]['name']+'?'):return
  self.battle_window=BattleWindow(self,k,ambush)
 def games(self):
  if self.blocked():return
  choices={0:[('Фейк-завод','factory')],2:[('Сапёр в каше','porridge')],4:[('Танцы на стрелках','dance')],10:[('Покер на одной карте','poker'),('Шахматы Лема (тактика)','chess')],11:[('Подкоп','tunnel')]};opts=choices.get(self.world.s['loc'])
  if not opts:return self.text_window('Мини-игры','Камера — фейки. Столовая — сапёр. Баня — танцы. Клуб — покер/тактика. Подвалы — подкоп.')
  w=self.window('Мини-игры',650,350)
  def start(kind):
   try:
    if kind=='poker' and self.world.s['cig']<5:raise ValueError('Нужны 5 сигарет')
    self.world.spend();self.world.event('minigame','Игрок начал '+kind,self.world.witnesses());w.destroy();self.mini=Mini(self,kind);self.persist();self.refresh()
   except ValueError as e:messagebox.showinfo('Мини-игра',str(e))
  for t,k in opts:self.button(w,t+' · 1 ход',lambda k=k:start(k)).pack(fill='x',padx=15,pady=6)
def run():
 app=None
 try:root=tk.Tk();app=App(root);root.mainloop()
 except Exception:
  (BASE/'logs').mkdir(exist_ok=True);(BASE/'logs/startup_error.log').write_text(traceback.format_exc(),encoding='utf8');raise
 finally:
  if app:app.engine.shutdown()
if __name__=='__main__':run()
