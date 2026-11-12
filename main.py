import tkinter as tk,json,queue,threading,uuid,copy,traceback,hashlib,re,time,shutil
from tkinter import ttk,messagebox
from pathlib import Path
from PIL import Image,ImageTk,ImageOps,ImageEnhance
from runtime_manager import Engine
from world import World,NAMES,save
from fightui import FightWindow
from minigames import Mini
from sound import Sound
import ai
import core,meta
from menu import Menu
from gfx import open_rgb
from uikit import Tutorial
from uikit import EventWindow,MapView
from story_data import SCENES
BASE=Path(__file__).resolve().parent
BG='#090d12';PANEL='#101720';CARD='#182331';FG='#e6edf4';MUTED='#8799ac';GOLD='#e5b767'
class _Null:
 def config(self,*a,**k):pass
 configure=config
class Status:
 def __init__(self,app,label):self.app=app;self.l=label;self.job=None
 def config(self,**kw):
  t=kw.get('text')
  if t is None:return
  self.l.config(text=t)
  if self.job:
   try:self.app.root.after_cancel(self.job)
   except Exception:pass
   self.job=None
  if t:
   self.l.grid();self.job=self.app.root.after(7000,lambda:self.config(text=''))
  else:self.l.grid_remove()
class App:
 def __init__(self,root):
  self.root=root;root.title('Тюряга · Свои люди v9');root.geometry('1540x980');root.minsize(1120,800);root.configure(bg=BG);root.columnconfigure(0,weight=1);root.rowconfigure(1,weight=1)
  self.npcs=json.loads((BASE/'npcs.json').read_text(encoding='utf8'));self.base=BASE;self.base_data=BASE;self.settings=meta.load_settings(BASE);self.path=meta.slot_path(BASE,'auto');state=meta.load_any(BASE);self.has_game=state is not None;self.menu_open=False;self.started=time.time();self.cover=self.settings['cover']
  self.world=World(self.npcs,state);self.engine=Engine(BASE);self.sound=Sound(BASE,self.settings['volume'],self.settings['music']);self.q=queue.Queue();self.liveq=queue.Queue();self.job=None;self.cancel_event=None;self.connected=False;self.closed=False;self.npc=None;self.hover=None;self.hits=[];self.bubble_hits=[];self.cache={};self.navrefs={};self.battle=None;self.battle_window=None;self.mini=None;self.modal=None;self.view='scene';self.cardrefs={};self.acts=[];self.stream_text={};self.draft_speech={}
  st=ttk.Style(root)
  try:st.theme_use('clam')
  except tk.TclError:pass
  st.configure('Dark.TCombobox',fieldbackground=CARD,background=CARD,foreground=FG,arrowcolor=GOLD,padding=7);st.map('Dark.TCombobox',fieldbackground=[('readonly',CARD)],foreground=[('readonly',FG)])
  self.chat_open=False;self.build_header();self.build_nav();self.build_scene();self.select_default();root.protocol('WM_DELETE_WINDOW',self.close);root.bind('<Control-s>',lambda e:self.quick_save());root.bind('<Escape>',lambda e:(self.close_chat() or self.menu.toggle()));root.bind('<F11>',lambda e:self.toggle_fullscreen());root.bind('<F2>',lambda e:self.show_history());root.after(80,self.poll);root.bind('<KeyPress-m>',lambda e:self.hot(self.toggle_map,e));root.bind('<KeyPress-j>',lambda e:self.hot(self.journal_window,e));root.bind('<KeyPress-t>',lambda e:self.hot(self.open_chat,e));root.bind('<Return>',lambda e:self.hot(self.open_chat,e));[root.bind('<Alt-Key-%d>'%i,lambda e,i=i:self.card_key(i)) for i in range(1,8)];root.after(400,lambda:core.story_check(self.world));root.after(self.settings['autosave_sec']*1000,self.autosave);self.menu=Menu(self);self.apply_settings();self.refresh();self.connect();self.menu.show()
 def label(self,parent,text='',size=11,bold=False,color=None,**kw):return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color or FG,font=('Segoe UI',size,'bold' if bold else 'normal'),**kw)
 def button(self,parent,text,fn,primary=False):return tk.Button(parent,text=text,command=fn,bg=GOLD if primary else CARD,fg='#111821' if primary else FG,activebackground='#e9c88f' if primary else '#24364a',activeforeground='#111821' if primary else FG,relief='flat',bd=0,font=('Segoe UI',10,'bold'),padx=12,pady=8,cursor='hand2')
 def window(self,title,w=900,h=650):
  p=tk.Toplevel(self.root);p.title(title);p.geometry(f'{w}x{h}');p.configure(bg=PANEL);return p
 def build_header(self):
  f=tk.Frame(self.root,bg=BG);f.grid(row=0,column=0,sticky='ew',padx=12,pady=(8,2));f.columnconfigure(3,weight=1)
  self.title=self.hint=self.modebutton=self.coverbtn=self.caste_lbl=_Null();self.navbuttons={}
  self.button(f,'☰',lambda:self.menu.show()).grid(row=0,column=0,padx=(0,6))
  self.mapbtn=self.button(f,'Карта · M',self.toggle_map,True);self.mapbtn.grid(row=0,column=1,padx=3)
  self.clock=self.label(f,size=13,bold=True,color=GOLD);self.clock.grid(row=0,column=2,sticky='w',padx=14)
  self.hud=self.label(f,size=11,color=MUTED);self.hud.grid(row=0,column=4,sticky='e')
 def build_nav(self):pass
 def build_scene(self):
  f=self.scene=tk.Frame(self.root,bg=PANEL);f.grid(row=1,column=0,sticky='nsew',padx=12,pady=(2,8));f.columnconfigure(0,weight=1);f.rowconfigure(0,weight=1)
  self.canvas=tk.Canvas(f,bg='#070b10',highlightthickness=0);self.canvas.grid(row=0,column=0,sticky='nsew',padx=4,pady=4);self.canvas.bind('<Configure>',lambda e:self.draw());self.canvas.bind('<Motion>',self.motion);self.canvas.bind('<Button-1>',self.click);self.map=MapView(self,f);self.map.c.grid(row=0,column=0,sticky='nsew',padx=4,pady=4);self.map.c.grid_remove()
  self.notice=tk.Frame(f,bg='#17232c');self.notice.grid(row=1,column=0,sticky='ew',padx=4,pady=2);self.notice.grid_remove()
  self.actrow=tk.Frame(f,bg=PANEL);self.actrow.grid(row=2,column=0,sticky='ew',padx=4,pady=2)
  self.chat=row=tk.Frame(f,bg=PANEL);row.grid(row=3,column=0,sticky='ew',padx=6,pady=4);row.columnconfigure(1,weight=1)
  self.who=self.label(row,size=12,bold=True);self.who.grid(row=0,column=0,sticky='w',padx=(0,12));self.npcbox=ttk.Combobox(row,state='readonly',style='Dark.TCombobox',width=22);self.npcbox.grid(row=1,column=0,sticky='ew',padx=(0,12));self.npcbox.bind('<<ComboboxSelected>>',lambda e:self.pick_npc());self.relation=self.label(row,size=9,color=MUTED);self.relation.grid(row=2,column=0,sticky='w')
  self.entry=tk.Text(row,height=2,wrap='word',bg=CARD,fg=FG,insertbackground=GOLD,font=('Segoe UI',12),relief='flat',padx=12,pady=8);self.entry.grid(row=0,column=1,rowspan=3,sticky='ew',padx=(0,10));self.entry.bind('<Return>',self.enter);self.entry.bind('<Shift-Return>',self.newline);self.entry.bind('<Control-Return>',self.enter);self.entry.bind('<Escape>',lambda e:(self.close_chat(True),'break')[1])
  self.sendbutton=self.button(row,'Сказать ↵',self.send,True);self.sendbutton.grid(row=0,column=2,sticky='ew');self.button(row,'Закрыть',lambda:self.close_chat(True)).grid(row=1,column=2,sticky='ew',pady=3)
  self.private=tk.BooleanVar(value=False);tk.Checkbutton(row,text='Наедине',variable=self.private,bg=PANEL,fg=MUTED,selectcolor=CARD,activebackground=PANEL).grid(row=2,column=2)
  self.chat.grid_remove()
  self.status_l=self.label(f,size=9,color=MUTED,wraplength=1100,justify='left');self.status_l.grid(row=4,column=0,sticky='w',padx=10);self.status_l.grid_remove();self.status=Status(self,self.status_l)
 def hot(self,fn,e):
  if e.widget is self.entry or self.blocked() or not self.has_game:return
  fn()
 def open_chat(self):
  if not self.has_game or self.modal or self.battle or self.mini or self.menu_open:return
  if not self.world.witnesses():return self.status.config(text='Здесь не с кем говорить.')
  if not self.npc or self.npc not in self.world.witnesses():self.select_default()
  self.chat_open=True;self.chat.grid();self.refresh_light()
  try:self.entry.focus_set()
  except Exception:pass
 def close_chat(self,force=False):
  if not self.chat_open:return False
  if self.job and not force:return False
  self.chat_open=False;self.chat.grid_remove()
  try:self.root.focus_set()
  except Exception:pass
  return True
 def blocked(self):return bool(self.job or self.battle or self.mini or self.modal or self.menu_open)
 def persist(self):
  if not self.has_game:return
  try:
   now=time.time();meta.write_state(BASE,'auto',self.world.s,now-self.started);self.started=now
  except Exception as e:messagebox.showerror('Сохранение',str(e))
 def quick_save(self):
  if self.has_game:self.persist();self.toast('Игра сохранена','Автосохранение обновлено')
 def autosave(self):
  if not self.closed:self.persist();self.root.after(int(self.settings['autosave_sec'])*1000,self.autosave)
 def apply_settings(self):
  s=self.settings;self.cover=s['cover']
  try:self.root.attributes('-fullscreen',bool(s['fullscreen']))
  except Exception:pass
  try:self.root.tk.call('tk','scaling',self.root.winfo_fpixels('1i')/72*float(s['ui_scale']))
  except Exception:pass
  try:self.sound.set_volume(s['volume']);self.sound.set_music(s['music'])
  except Exception:pass
  self.cache.clear()
  if hasattr(self,'coverbtn'):self.coverbtn.config(text='Фон: заполнить' if self.cover else 'Фон: целиком')
  if hasattr(self,'map'):self.map.cache.clear()
  if getattr(self,'menu',None):self.menu.cache.clear()
  if self.has_game:self.draw()
 def toggle_fullscreen(self):
  self.settings['fullscreen']=not self.settings['fullscreen'];meta.save_settings(BASE,self.settings);self.apply_settings()
 def new_game(self,diff):
  if self.job:
   if self.cancel_event:self.cancel_event.set()
   self.job=None
  p=self.path
  if p.exists():
   try:shutil.copy2(p,p.with_name('before_newgame.json'))
   except OSError:pass
  self._swap(meta.new_state(self.npcs,diff));self.has_game=True;self.started=time.time();self.persist();core.story_check(self.world);self.refresh();self.toast('Новая игра','Сложность: '+core.diff(self.world)['name'])
 def load_slot(self,sid):
  st=meta.read_state(BASE,sid)
  if self.job:
   if self.cancel_event:self.cancel_event.set()
   self.job=None
  self._swap(st);self.has_game=True;self.started=time.time();self.persist();self.refresh();self.toast('Игра загружена','День %d'%self.world.s['day'])
 def save_slot(self,sid):
  meta.write_state(BASE,sid,self.world.s,0);self.toast('Сохранено','Слот: '+sid)
 def _swap(self,state):
  self.world=World(self.npcs,state);self.npc=None;self.hover=None;self.stream_text.clear();self.draft_speech.clear();self.cache.clear();self.select_default()
 def restart_ai(self):
  if self.battle or self.mini:return
  try:self.engine.shutdown()
  except Exception:pass
  self.engine=Engine(BASE);self.connected=False;self.job=None;self.status.config(text='Перезапуск ИИ…');self.connect()
 def journal_window(self):
  if not self.has_game:return
  t='\n\n'.join('■ '+h+'\n'+'\n'.join('  • '+x for x in rows) for h,rows in core.journal(self.world))
  self.text_window('Задания и дела',t)
 def show_stats(self):
  if self.has_game:self.menu.show('stats')
 def maybe_tutorial(self):
  if self.has_game and self.settings.get('hints',True) and not self.settings.get('seen_howto') and not self.menu_open and not self.modal:Tutorial(self)
 def check_achievements(self):
  if not self.has_game:return
  for id,title,desc in meta.check_achievements(self.world,BASE):self.sound.play('ach');self.toast('★ Достижение: '+title,desc)
 def toast(self,title,text=''):
  try:
   t=tk.Toplevel(self.root);t.overrideredirect(True);t.attributes('-topmost',True);t.configure(bg=GOLD)
   inner=tk.Frame(t,bg=PANEL);inner.pack(padx=2,pady=2);tk.Label(inner,text=title,bg=PANEL,fg=GOLD,font=('Segoe UI',12,'bold'),wraplength=380,justify='left').pack(padx=16,pady=(10,2),anchor='w');tk.Label(inner,text=text,bg=PANEL,fg=FG,font=('Segoe UI',10),wraplength=320,justify='left').pack(padx=16,pady=(0,10),anchor='w')
   t.update_idletasks();x=self.root.winfo_rootx()+self.root.winfo_width()-t.winfo_reqwidth()-24;y=self.root.winfo_rooty()+self.root.winfo_height()-t.winfo_reqheight()-60-40*len(getattr(self,'_toasts',[]));t.geometry(f'+{max(0,x)}+{max(0,y)}')
   self._toasts=getattr(self,'_toasts',[])+[t]
   def gone():
    try:t.destroy()
    except Exception:pass
    self._toasts=[x for x in getattr(self,'_toasts',[]) if x is not t]
   self.root.after(4200,gone)
  except Exception:pass
 def close(self):
  self.closed=True
  try:self.sound.close()
  except Exception:pass
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
  if not (self.job or self.battle or self.mini or self.modal):self.launch('start',lambda id,cancel:self.engine.connect())
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
     m=job['meta'];ai.accept(self.world,m['npc'],m['text'],result,m['private']);self.entry.delete('1.0','end');core.talk(self.world);core.on_chat(self.world,m['npc']);self.sound.play('ok');self.status.config(text='Ответ получен. История — по кнопке F2.');self.persist();self.refresh();self.chat_combat(m,result)
    else:
     try:self.world.initiative(job['meta']['npc'],result);self.persist();self.refresh();self.status.config(text='NPC продолжает свои дела.')
     except Exception as e:self.status.config(text='Инициатива не применена: '+str(e))
  except queue.Empty:pass
  self.pump();self.sendbutton.config(state='disabled' if self.blocked() or not self.connected else 'normal');self.root.after(80,self.poll)
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
  self.npc=k;self.npcbox.current(self.local_ids.index(k));self.refresh();self.open_chat()
 def toggle_map(self):
  if self.view=='scene':self.view='map';self.canvas.grid_remove();self.map.c.grid();self.map.draw();self.mapbtn.config(text='К сцене · M')
  else:self.show_scene()
 def show_scene(self):
  self.view='scene';self.map.c.grid_remove();self.canvas.grid();self.mapbtn.config(text='Карта · M');self.draw()
 def travel(self,i):
  if i==self.world.s['loc']:return self.show_scene()
  if self.blocked():return self.status.config(text='Завершите действие перед переходом.')
  self.go(i);self.show_scene()
 def go(self,i):
  if self.blocked():return self.status.config(text='Завершите действие или отмените запрос перед переходом.')
  self.sound.play('step');core.travel(self.world,i);self.propagate();self.hover=None;self.stream_text.clear();self.draft_speech.clear();self.select_default();self.persist();self.refresh();self.initiative('player_entered')
 def toggle_cover(self):self.cover=not self.cover;self.coverbtn.config(text='Фон: заполнить' if self.cover else 'Фон: целиком');self.draw()
 def draw(self):
  c=self.canvas;c.delete('all');w=max(1,c.winfo_width());h=max(1,c.winfo_height())
  if w<20 or h<20:return
  loc=self.world.s['loc'];key=(loc,w,h,self.cover,self.settings['brightness'])
  if key not in self.cache:
   if len(self.cache)>35:self.cache.clear()
   im=open_rgb(BASE/f'assets/loc_{loc}.jpg',(w,h))
   if self.settings['brightness']!=1:im=ImageEnhance.Brightness(im).enhance(self.settings['brightness'])
   if self.cover:im=ImageOps.fit(im,(w,h),method=Image.Resampling.LANCZOS)
   else:im.thumbnail((w,h),Image.Resampling.LANCZOS);bg=Image.new('RGB',(w,h),'#070b10');bg.paste(im,((w-im.width)//2,(h-im.height)//2));im=bg
   self.cache[key]=ImageTk.PhotoImage(im)
  self.bgref=self.cache[key];c.create_image(0,0,anchor='nw',image=self.bgref);self.hits=[];self.bubble_hits=[];present=self.world.witnesses();pw=max(75,min(170,int(w*.18),int(h*.44/1.58)));ph=int(pw*1.58);gap=40;start=(w-len(present)*pw-max(0,len(present)-1)*gap)//2
  c.create_rectangle(0,0,w,44,fill='#0b1420',stipple='gray50',outline='');c.create_text(14,15,text=NAMES[loc].upper(),anchor='w',fill=GOLD,font=('Segoe UI',10,'bold'))
  for i,k in enumerate(present):
   x=start+i*(pw+gap);y=max(40,h-ph-65);key=('npc',k,pw,ph)
   if key not in self.cache:self.cache[key]=ImageTk.PhotoImage(Image.open(BASE/f'assets/{self.npcs[k]["portrait"]}.jpg').resize((pw,ph),Image.Resampling.LANCZOS))
   active=k==self.npc or k==self.hover;c.create_rectangle(x-4,y-4,x+pw+4,y+ph+27,fill='#141b24',outline=GOLD if active else '#2b3c50',width=2);c.create_image(x,y,anchor='nw',image=self.cache[key]);c.create_text(x+pw/2,y+ph+14,text=core.shown_name(self.world,k),fill=GOLD if active else FG,font=('Segoe UI',10,'bold'))
   maximum=core.max_hp(self.world,k);hp=min(maximum,self.world.s['npc_health'].get(k,maximum));c.create_rectangle(x,y-23,x+pw,y-8,fill='#211218',outline='');c.create_rectangle(x,y-23,x+pw*max(0,hp)/maximum,y-8,fill='#c45867',outline='');c.create_text(x+pw/2,y-16,text=f'{hp}/{maximum} HP',fill='white',font=('Segoe UI',9,'bold'));self.hits.append(((x-4,y-4,x+pw+4,y+ph+27),k))
  if self.npc:
   hist=self.world.s['history'].get(self.npc,[]);speech=self.stream_text.get(self.npc)
   if speech is None:speech=next((m['content'] for m in reversed(hist) if m['role']=='assistant'),'')
   user=self.draft_speech.get(self.npc) or next((m['content'] for m in reversed(hist) if m['role']=='user'),'');hit=next((rect for rect,k in self.hits if k==self.npc),None)
   if speech and hit:self.bubble(speech,hit,self.npcs[self.npc]['name'])
   if user:c.create_rectangle(12,h-34,min(w-12,1100),h-7,fill='#152532',outline='#34536a');c.create_text(24,h-21,anchor='w',text='ВЫ  '+(user if len(user)<130 else user[:127]+'…'),fill='#8fc5ec',font=('Segoe UI',11))
 def bubble(self,text,hit,name):
  c=self.canvas;cw=c.winfo_width();x0,y0,x1,y1=hit;maxw=min(650,max(280,cw-40));cx=(x0+x1)/2;top=54;bottom=y0-32;avail=max(60,bottom-top);display=text.strip();item=None;box=None;fits=False
  for size in (12,11,10,9):
   while True:
    if item:c.delete(item)
    shown=display
    if len(display)>460:shown=display[:457]+'…\n[Нажмите, чтобы прочитать целиком]'
    item=c.create_text(0,0,anchor='nw',text=shown,width=maxw-28,fill=FG,font=('Segoe UI',size),justify='left');box=c.bbox(item)
    fits=bool(box) and box[3]-box[1]+20<=avail
    if fits or size>9 or len(display)<60:break
    display=display[:int(len(display)*.85)].rstrip()+'…'
   if fits:break
  if not box:return
  bw=box[2]-box[0]+24;bh=box[3]-box[1]+20;left=max(14,min(cw-bw-14,cx-bw/2));topy=max(top,bottom-bh)
  c.move(item,left+12-box[0],topy+10-box[1]);rect=(left,topy,left+bw,topy+bh);bg=c.create_rectangle(*rect,fill='#101b26',outline=GOLD,width=2);c.tag_lower(bg,item)
  tx=max(left+14,min(left+bw-14,cx));tip=c.create_polygon(tx-7,rect[3],tx+7,rect[3],tx,rect[3]+9,fill='#101b26',outline=GOLD);c.tag_lower(tip,item);self.bubble_hits.append((rect,text,name))
 def motion(self,e):
  k=next((k for (x,y,r,b),k in self.hits if x<=e.x<=r and y<=e.y<=b),None)
  if k!=self.hover:self.hover=k;self.canvas.config(cursor='hand2' if k else '');self.draw()
 def click(self,e):
  for (x,y,r,b),text,name in self.bubble_hits:
   if x<=e.x<=r and y<=e.y<=b:return self.text_window(name,text)
  self.motion(e)
  if self.hover and not self.blocked():self.sound.play('click');self.select(self.hover)
 def refresh(self):
  s=self.world.s;rep=self.world.reputation(self.npc or 'zub')['public_respect'];t=core.tier(self.world)[0];c=core.C(self.world)
  self.hud.config(text=f"♥ {s['hp']}   ⚡ {s['stamina']}   ● {s['cig']}   ₽ {s['rub']}   ·   {t}")
  self.clock.config(text=f"День {s['day']} · {core.hhmm(self.world)} {core.phase(self.world)}")
  self.title.config(text=NAMES[s['loc']]);self.hint.config(text='Местные: '+(', '.join(self.npcs[k]['name'] for k in self.world.witnesses()) or 'никого'))
  present=self.world.witnesses()
  if not self.npc or self.npc not in present:self.select_default()
  # Список собеседников — те, кто сейчас в локации (свергнутый босс остаётся в ней «бывшим»).
  elif self.local_ids!=present:self.local_ids=present;self.npcbox.config(values=[self.npcs[k]['name'] for k in present]);self.npcbox.current(present.index(self.npc))
  if self.npc:self.who.config(text=self.npcs[self.npc]['name']);self.relation.config(text=f"Отношение {s['relations'].get(self.npc,0):+d}")
  else:self.who.config(text='—');self.relation.config(text='')
  self.modebutton.config(text='Быстро · 1 запрос' if self.engine.cfg['CHAT_FAST_MODE'].lower()=='true' else 'Полный режим');self.draw();self.render_notices();self.render_cards()
  if self.view=='map':self.map.draw()
  self.check_achievements()
  if self.has_game:self.sound.music(s['loc'])
 def refresh_light(self):
  try:self.refresh()
  except Exception:pass
 def render_cards(self):
  for w in self.actrow.winfo_children():w.destroy()
  self.acts=core.activities(self.world);n=len(self.acts)
  for i,a in enumerate(self.acts):
   self.actrow.columnconfigure(i,weight=1);key='ic_'+a['icon']
   if key not in self.cardrefs:self.cardrefs[key]=ImageTk.PhotoImage(Image.open(BASE/f"assets/icon_{a['icon']}.png").convert('RGBA').resize((22,22)))
   off=a['off'];txt=a['title']+('\n'+off if off else (f"\n{a['min']} мин" if a['min'] else ''))
   b=tk.Button(self.actrow,text=txt,image=self.cardrefs[key],compound='left',command=lambda id=a['id']:self.do_activity(id),bg='#1d2b3c' if not off else '#121a24',fg=FG if not off else MUTED,activebackground='#2c4058',relief='flat',bd=0,font=('Segoe UI',9,'bold'),padx=8,pady=4,cursor='hand2' if not off else 'arrow',wraplength=150,justify='left')
   b.grid(row=0,column=i,sticky='ew',padx=2)
  mb=tk.Menubutton(self.actrow,text='⋯',bg=CARD,fg=FG,relief='flat',font=('Segoe UI',14,'bold'),padx=14,pady=4,cursor='hand2');m=tk.Menu(mb,tearoff=0,bg=PANEL,fg=FG)
  for t,fn in [('Говорить · Enter',self.open_chat),('Решения',self.decisions),('Снаряжение',self.equipment),('Дуэль',self.fight),('Схрон',self.stash_window),('Задания · J',self.journal_window),('Статус и каста',self.caste_window),('История разговора · F2',self.show_history),('Новый разговор с NPC',self.reset_chat),('Уважуха',self.respect_window),('Постоянные жители',self.residents),('Подключить ИИ',self.connect),('Журналы мира (отладка)',self.journal),('Лог сервера',lambda:self.text_window('llama-server',self.engine.tail()))]:m.add_command(label=t,command=fn)
  mb.config(menu=m);mb.grid(row=0,column=n,padx=(6,0))
 def card_key(self,i):
  if 1<=i<=len(self.acts):self.do_activity(self.acts[i-1]['id'])
 def pump(self):
  if self.closed or self.modal or self.battle or self.mini or self.menu_open or not self.has_game:return
  p=core.pop_pending(self.world)
  if p and p.get('t')=='scene' and p['id'] in SCENES:self.open_scene(p['id'],p.get('vars'))
  elif p and p.get('t')=='fight':self.fight(p['k'],bool(p.get('ambush')))  # реванш: бой начинается без вопроса «начать?»
 def open_scene(self,sid,vars=None):
  if self.view=='map':self.show_scene()
  if sid.startswith('meal'):self.sound.play('horn')
  elif sid in('shmon','extort','brawl'):self.sound.play('clang')
  EventWindow(self,sid,vars)
 def do_activity(self,id):
  if self.blocked():return self.status.config(text='Сначала завершите текущее действие.')
  a=next((x for x in core.activities(self.world) if x['id']==id),None)
  if not a:return
  if a['off']:return self.status.config(text=a['off'])
  w=self.world
  try:
   if id=='bed':
    core.sleep(w);self.persist();self.refresh();return self.status.config(text='Вы проспали до утра. Новый день.')
   if id=='stash':return self.stash_window()
   if id.startswith('mini_'):
    kind={'mini_dance':'dance','mini_cards':'poker','mini_poker':'poker','mini_chess':'chess','mini_tunnel':'tunnel'}[id]
    w.spend();w.event('minigame','Игрок начал '+kind,w.witnesses());core.advance(w,a['min']);self.mini=Mini(self,kind);self.persist();self.refresh();return
   if id=='temple_god':
    c=core.C(w)
    if c['temple_day']==w.s['day']:return self.status.config(text='Господь сегодня уже вас выслушал. Приходите завтра.')
    c['temple_day']=w.s['day']
   core.advance(w,a['min']);cn=core.C(w)['counters'];cn[id]=cn.get(id,0)+1
   if id in('work_shift','gym','shiv_craft'):w.event('work' if id=='work_shift' else 'activity','Игрок: '+a['title'],w.witnesses())
   self.propagate();self.persist();self.refresh();self.open_scene(core.scene_for(w,id))
  except ValueError as e:self.status.config(text=str(e))
 def stash_window(self):
  if self.blocked():return
  w=self.world;L=w.s['loc'];win=self.window('Схрон · '+NAMES[L],620,470);box=tk.Frame(win,bg=PANEL);box.pack(fill='both',expand=True,padx=14,pady=10)
  def draw():
   for x in box.winfo_children():x.destroy()
   st=core.stash_get(w,L);inv=core.C(w)['inv']
   self.label(box,'Схрон в локации «%s»'%NAMES[L],12,True,color=GOLD).pack(anchor='w',pady=6)
   for it,name in [('cig','Сигареты'),('shiv','Заточка'),('phone','Мобильник'),('tea','Пачка чая')]:
    have=w.s['cig'] if it=='cig' else inv.get(it,0);r=tk.Frame(box,bg=PANEL);r.pack(fill='x',pady=3);self.label(r,'%s · при себе %d · в схроне %d'%(name,have,st.get(it,0)),11).pack(side='left')
    def mv(it=it,put=True):
     try:core.stash_move(w,L,it,1,put);self.persist();self.refresh();draw()
     except ValueError as e:self.status.config(text=str(e))
    self.button(r,'Взять',lambda it=it:mv(it,False)).pack(side='right',padx=3);self.button(r,'Спрятать',lambda it=it:mv(it,True)).pack(side='right',padx=3)
   self.label(box,'При шмоне забирают заточки и мобильники, что при вас. Спрятанное шмон не находит.',9,color=MUTED).pack(anchor='w',pady=10)
  draw()
 def caste_window(self):
  r=core.caste_report(self.world);c=core.C(self.world)
  txt=f"СТАТУС: {r['tier']} ({r['score']:+d})\n{r['desc']}\n\nМудрость {c['wis']} · Харизма {c['cha']}\nПоверженные боссы: {', '.join(r['ousted']) or 'нет'}\n\nШкала: Петух ≤ −70 → Шестёрка → Мужик → Авторитет ≥ 35 → Пахан ≥ 70 (и минимум 2 поверженных босса).\n\nПодъём: победы в драках, свержение боссов, успешные проверки, помощь.\nПадение: крысятничество, кражи, проигрыши, подставы.\nГосподь в Храме списывает часть грехов (карму), но не статус — его возвращает только дело.\n\nСюжетных сцен пройдено: {len(c['done'])}/{sum(1 for s in SCENES.values() if s['story'])}\nКонцовка: {c['ending'] or 'ещё не выбрана'}"
  self.text_window('Статус и каста',txt)
 def show_history(self):
  if not self.npc:return
  text='\n\n'.join(('Вы' if m['role']=='user' else self.npcs[self.npc]['name'])+': '+m['content'] for m in self.world.s['history'].get(self.npc,[]));self.text_window('История · '+self.npcs[self.npc]['name'],text or 'Переписка пуста.')
 def reset_chat(self):
  if self.blocked() or not self.npc:return
  if not messagebox.askyesno('Новый разговор','Архивировать старую переписку и заметки? События, отношения и карма сохранятся.'):return
  s=self.world.s;k=self.npc;s.setdefault('dialogue_archives',[]).append({'npc':k,'day':s['day'],'history':s['history'].get(k,[]),'memory':s['memory'].get(k,[])});s['dialogue_archives']=s['dialogue_archives'][-30:];s['history'][k]=[];s['memory'][k]=[];self.stream_text.clear();self.draft_speech.clear();self.persist();self.refresh()
 def render_notices(self):
  for w in self.notice.winfo_children():w.destroy()
  fd=core.C(self.world)['feed']
  if fd:
   for msg in fd[-3:]:self.toast(msg)
   fd.clear()
  pending=[o for o in self.world.s['notices'] if o['status']=='pending' and o['npc'] in self.world.witnesses()]
  if not pending:self.notice.grid_remove();return
  self.notice.grid()
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
  self.close_chat(True);self.battle_window=FightWindow(self,k,ambush)
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
