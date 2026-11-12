import json,uuid,random,os,hashlib,re
from pathlib import Path
import core,lore
NAMES=['Камера','Двор','Столовая','Коридор','Баня','Барак','Прачечная','Мастерская','Храм','ШИЗО','Клуб','Подвалы']
DIMS=('empathy','honor','cunning');PRISONERS={'zub','graf','buh','sm','kol','prach','steam','cook','zina','hleb','kip'}
def fresh(npcs):
 return {'core':core.default(),'version':7,'day':1,'turn':0,'ap':6,'food':80,'hp':100,'stamina':100,'stamina_max':100,'rub':20,'cig':15,'loc':0,'companion':'zub','karma':dict.fromkeys(DIMS,0),'budget':dict.fromkeys(DIMS,0),'relations':{},'history':{},'memory':{},'seen':[],'events':[],'knowledge':{},'gossip':[],'audit':[],'diary':[],'notices':[],'npc_state':{k:{'loc':v['home'],'last_turn':-9,'last_topic':'','discussed_gossip':[]} for k,v in npcs.items()},'day_interruptions':0,'obligations':[],'gear':{'weapon':'Кулаки','damage':16,'armor':2,'accuracy':.72},'npc_health':{},'dig':0,'mice':0,'chron':[],'defeated':[],'chat_fight_tokens':[],'street_rep':{'earned':0,'processed_events':[],'rewarded_victories':[],'daily':{},'audit':[]},'dialogue_money':{'day':1,'earned':0,'npcs':{},'seen':[],'audit':[]}}
def save(s,path):
 p=Path(path);p.parent.mkdir(exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(s,ensure_ascii=False,indent=1),encoding='utf8');os.replace(tmp,p)
def clamp(v):return max(-100,min(100,v))
class World:
 def __init__(self,npcs,s=None,seed=None):
  self.npcs=npcs;self.rng=random.Random(seed);defaults=fresh(npcs);self.s=s if isinstance(s,dict) else defaults
  for k,v in defaults.items():self.s.setdefault(k,v)
  self.s['version']=7
  for k,n in npcs.items():self.s['npc_state'].setdefault(k,{'last_turn':-9,'last_topic':''})['loc']=n['home'];self.s['npc_state'][k].setdefault('discussed_gossip',[])
 def witnesses(self):
  out=core.C(self).get('ousted',[]);return [k for k,n in self.npcs.items() if n['home']==self.s['loc'] and k not in out]
 def event(self,kind,text,witnesses=(),public=False):
  s=self.s;ids=list(dict.fromkeys(k for k in witnesses if k in self.npcs));e={'id':uuid.uuid4().hex,'day':s['day'],'turn':s['turn'],'kind':kind,'text':text,'witnesses':ids,'public':public};s['events'].append(e);s['events']=s['events'][-300:]
  for k in ids:s['knowledge'].setdefault(k,[]).append({**e,'source':'очевидец','verified':True});s['knowledge'][k]=s['knowledge'][k][-100:]
  s['chron'].append({'day':s['day'],'real':text,'his':'Герой скромно трудился на благо зоны.' if kind not in ('theft','betrayal') else 'Мелкое недоразумение, не требующее проверки.'});s['chron']=s['chron'][-80:];return e
 def known(self,k):
  out=list(self.s['knowledge'].get(k,[]));ids={e['id'] for e in out};out += [{**e,'source':'публичное событие','verified':True} for e in self.s['events'] if e.get('public') and e['id'] not in ids];return out[-30:]
 def heard(self,k):return [g for g in self.s['gossip'] if g['to']==k][-10:]
 def reputation(self,k):
  s=self.s;r=s['street_rep'];seen=set(r['processed_events'])
  for e in s['events']:
   if e['id'] in seen:continue
   seen.add(e['id']);r['processed_events'].append(e['id'])
   if not any(x in PRISONERS for x in e.get('witnesses',[])):continue
   kind=e['kind'];delta={'help':4,'theft':-7,'betrayal':-12,'debt_paid':4,'task_done':3,'work':1}.get(kind,0)
   if kind=='combat' and e['text'].endswith(': Победа'):
    target=e['text'].split(':',1)[0]
    if target not in r['rewarded_victories']:delta=5;r['rewarded_victories'].append(target)
   key=str(e['day'])+':'+kind
   if not delta or key in r['daily']:continue
   r['daily'][key]=True;before=r['earned'];r['earned']=clamp(before+delta);r['audit'].append({'day':e['day'],'event':e['id'],'delta':r['earned']-before,'why':e['text']})
  r['processed_events']=r['processed_events'][-1000:];r['audit']=r['audit'][-200:]
  if len(r['daily'])>300:r['daily']={k:v for k,v in r['daily'].items() if int(k.split(':')[0])>=s['day']-30}
  ids=[i for i in self.npcs if i in PRISONERS];mean=sum(s['relations'].get(i,0) for i in ids)/max(1,len(ids));public=.7*r['earned']+.3*mean;ka=s['karma'];karma=.6*ka['honor']+.3*ka['cunning']+.1*ka['empathy'];personal=s['relations'].get(k,0);score=.45*public+.2*karma+.35*personal+.15*core.C(self)['caste']
  if personal<=-25:score=min(score,-20)
  return {'public_respect':round(public,1),'earned':r['earned'],'prisoners_average':round(mean,1),'karma':round(karma,1),'personal':personal,'score':round(score,1),'authority':k not in PRISONERS}
 def context(self,k):
  s=self.s
  return {'npc':self.npcs[k],'location':NAMES[self.npcs[k]['home']],'day':s['day'],'relationship':s['relations'].get(k,0),'respect':self.reputation(k),'known_facts':self.known(k)[-6:],'heard_rumors':[{'id':g['id'],'from':('лично слышал от игрока' if g['from']==k and g['hops']==0 else self.npcs[g['from']]['name']),'claim':g['claim'],'confidence':g['confidence'],'hops':g['hops'],'verified':False,'disputed':g.get('disputed',False)} for g in self.heard(k)[-4:]],'already_discussed_rumors':s['npc_state'][k]['discussed_gossip'][-15:],'obligations':[o for o in s['obligations'] if o['npc']==k and o['status']=='active'],'memory':s['memory'].get(k,[])[-5:],'lore':lore.npc_lore(self,k),'player':{'тон':lore.TIER_TONE[core.tier(self)[0]],'caste':core.tier(self)[0],'caste_score':core.C(self)['caste'],'time':core.hhmm(self)+' '+core.phase(self),'defeated_bosses':[self.npcs[x]['name'] for x in core.C(self)['ousted']]}}
 def conversation_event(self,k,text,reply,private=False):
  s=self.s;loc=self.npcs[k]['home'];listeners=[] if private else [i for i,n in self.npcs.items() if n['home']==loc and i!=k]
  e={'id':uuid.uuid4().hex,'kind':'speech','day':s['day'],'turn':s['turn'],'text':text[:1600],'addressed_to':k,'npc_reply':reply[:900],'private':private,'observers':listeners};s['events'].append(e);s['events']=s['events'][-300:]
  if not private:
   claim='Игрок сказал '+self.npcs[k]['name']+': «'+text[:320]+'».';self.gossip(k,k,claim,e['id'],100,0,'участник разговора',[])
   for i in listeners:self.gossip(k,i,claim,e['id'],90,0,'подслушал в '+NAMES[loc],[])
  return e
 def gossip(self,src,to,claim,root,confidence,hops,channel,chain):
  if any(g['root']==root and g['to']==to for g in self.s['gossip']):return None
  g={'id':uuid.uuid4().hex,'root':root,'day':self.s['day'],'turn':self.s['turn'],'from':src,'to':to,'claim':claim[:650],'confidence':confidence,'hops':hops,'channel':channel,'chain':chain+[src],'verified':False};self.s['gossip'].append(g);self.s['gossip']=self.s['gossip'][-400:];return g
 def relay(self):
  candidates=[g for g in self.s['gossip'] if g['hops']<3 and self.s['turn']>g['turn']];self.rng.shuffle(candidates);out=[]
  for g in candidates:
   src=g['to'];pool=[i for i in self.npcs[src]['contacts'] if i!=src and not any(x['root']==g['root'] and x['to']==i for x in self.s['gossip'])]
   if not pool:continue
   txt=('Оспариваемый слух: ' if g.get('disputed') else '')+g['claim'];txt=('Говорят, ' if g['hops']==0 else 'Через третьи руки передают: ')+txt[:500]
   n=self.gossip(src,self.rng.choice(pool),txt,g['root'],max(10,g['confidence']-self.rng.randint(12,25)),g['hops']+1,'записки и пересказы',g['chain'])
   if n:out.append(n)
   if len(out)>=2:break
  return out
 def deny(self,k,id):
  g=next((g for g in self.heard(k) if g['id']==id),None)
  if not g:raise ValueError('NPC не слышал этот слух')
  g['disputed']=True;self.event('denial','Игрок оспорил слух: '+g['claim'],[k]);self.gossip(k,k,'Игрок отрицает: '+g['claim'],uuid.uuid4().hex,80,0,'опровержение',[])
 def spend(self,n=1):
  self.s['turn']+=1
 def go(self,loc):
  if loc not in range(12):raise ValueError('Нет локации')
  self.s['loc']=loc;self.s['turn']+=1
 def work(self):
  self.spend();s=self.s;s['rub']+=8;s['cig']+=2;s['food']=max(0,s['food']-4);s['stamina']=max(0,s['stamina']-8);self.event('work','Игрок отработал смену в '+NAMES[s['loc']]+'.',self.witnesses())
 def eat(self):
  if self.s['cig']<2:raise ValueError('Нужны 2 сигареты')
  s=self.s;s['cig']-=2;s['food']=min(100,s['food']+25);s['stamina']=min(s['stamina_max'],s['stamina']+12);s['turn']+=1;self.event('meal','Игрок поел.',self.witnesses())
 def sleep(self):
  s=self.s;s['diary'].append('День %d. '%s['day']+'; '.join(e['text'] for e in s['events'] if e['day']==s['day'] and e['kind']!='speech')[-1500:]);s['day']+=1;s['turn']+=1;s['ap']=6;s['food']=max(0,s['food']-10);s['hp']=max(1,s['hp']-10) if not s['food'] else min(100,s['hp']+4);s['stamina']=s['stamina_max'];s['npc_health']={};s['budget']=dict.fromkeys(DIMS,0);s['day_interruptions']=0;self.money_reset()
 def decision(self,k,kind):
  if k not in self.witnesses():raise ValueError('NPC не рядом')
  if kind=='help' and self.s['cig']<2:raise ValueError('Нужны 2 сигареты')
  if kind not in ('help','theft','betrayal'):raise ValueError('Нет действия')
  self.spend();s=self.s
  if kind=='help':s['cig']-=2;delta=6;text='Игрок отдал '+self.npcs[k]['name']+' две сигареты.'
  elif kind=='theft':s['rub']+=15;delta=-20;text=self.npcs[k]['name']+' поймал игрока на краже 15 рублей.'
  else:s['rub']+=25;delta=-25;text='Игрок сдал '+self.npcs[k]['name']+' охране. NPC достоверно узнал об этом.'
  s['relations'][k]=clamp(s['relations'].get(k,0)+delta);self.event(kind,text,self.witnesses());core.add_caste(self,{'help':3,'theft':-5,'betrayal':-15}[kind],{'help':'помощь','theft':'кража','betrayal':'донос'}[kind])
 def buy(self,kind):
  s=self.s;cost=core.price(self,{'knife':40,'armor':35,'heal':10}[kind])
  if s['rub']<cost:raise ValueError('Недостаточно рублей')
  s['rub']-=cost
  if kind=='knife':s['gear'].update(weapon='Заточка',damage=24)
  elif kind=='armor':s['gear']['armor']=7
  else:s['hp']=min(100,s['hp']+35)
  self.event('purchase','Покупка: '+kind,self.witnesses())
 def borrow(self,k):
  if k not in self.witnesses():raise ValueError('NPC не рядом')
  s=self.s
  if any(o['npc']==k and o['status']=='active' for o in s['obligations']):raise ValueError('Сначала верните долг')
  s['rub']+=10;s['obligations'].append({'id':uuid.uuid4().hex,'npc':k,'amount':10,'due':s['day']+1,'status':'active'});self.event('debt','Игрок занял 10 рублей до завтра.',[k])
 def repay(self,k):
  s=self.s;o=next((o for o in s['obligations'] if o['npc']==k and o['status']=='active'),None)
  if not o or k not in self.witnesses():raise ValueError('Нет доступного долга этому NPC')
  if s['rub']<o['amount']:raise ValueError('Не хватает рублей')
  s['rub']-=o['amount'];o['status']='paid';s['relations'][k]=clamp(s['relations'].get(k,0)+4);self.event('debt_paid','Игрок вернул долг.',[k])
 def candidate(self):
  s=self.s
  if s['day_interruptions']>=3:return None
  pool=[k for k in self.witnesses() if s['turn']-s['npc_state'][k]['last_turn']>=3]
  def score(k):return sum(2 for g in self.heard(k) if g['id'] not in s['npc_state'][k]['discussed_gossip'])+sum(8 for o in s['obligations'] if o['npc']==k and o['status']=='active' and o['due']<=s['day'])
  return max(pool,key=score) if pool else None
 def initiative(self,k,obj):
  if k not in self.witnesses() or self.s['day_interruptions']>=3:return None
  if not isinstance(obj,dict) or not isinstance(obj.get('reply',''),str):raise ValueError('Некорректная инициатива')
  s=self.s;n=s['npc_state'][k];a=obj.get('action','wait');a=a if a in ('wait','talk','warn','offer_task','attack') else 'wait';ids=obj.get('evidence',[]);ids=ids if isinstance(ids,list) else []
  facts=[e for e in self.known(k) if e['id'] in ids and e['kind'] in ('theft','betrayal','assault') and e.get('verified')]
  if a=='attack' and (not facts or s['relations'].get(k,0)>-15):a='warn'
  topic=str(obj.get('topic',''))[:90] or a
  if topic==n['last_topic'] and s['turn']-n['last_turn']<6:return None
  n['last_turn']=s['turn'];n['last_topic']=topic
  if a=='wait':return None
  task=obj.get('task','work');task=task if task in ('work','help','train') else 'work';used=obj.get('rumors_used',[])
  o={'id':uuid.uuid4().hex,'npc':k,'action':a,'reply':obj['reply'][:1800],'task':task,'status':'pending','topic':topic,'day':s['day'],'evidence':ids,'rumors_used':used if isinstance(used,list) else []};s['notices'].append(o);s['notices']=s['notices'][-60:];s['day_interruptions']+=1;return o
 def resolve(self,id,accept):
  s=self.s;o=next(x for x in s['notices'] if x['id']==id)
  if o['status']!='pending':return None
  if not accept:o['status']='later';return None
  if o['npc'] not in self.witnesses():raise ValueError('NPC в другой локации')
  if o['action']=='offer_task':
   if o['task']=='help' and s['cig']<2:raise ValueError('Нужны 2 сигареты')
   self.spend()
   if o['task']=='help':s['cig']-=2
   elif o['task']=='work':s['rub']+=6
   else:s['mice']=min(10,s['mice']+1)
   s['relations'][o['npc']]=clamp(s['relations'].get(o['npc'],0)+5);self.event('task_done','Игрок выполнил дело: '+o['task'],[o['npc']]);o['status']='accepted';return 'done'
  o['status']='accepted';return o['action']
 def money_reset(self):
  e=self.s['dialogue_money']
  if e['day']!=self.s['day']:e.update(day=self.s['day'],earned=0,npcs={},seen=[])
 def award_dialogue(self,k,text,result):
  self.money_reset();s=self.s;e=s['dialogue_money']
  if k not in PRISONERS or k not in self.witnesses():return 0
  tokens=set(re.findall(r'[а-яёa-z0-9]+',text.casefold()))
  if len(text.strip())<28 or len(tokens)<5 or re.search(r'\b(дай|выдай|начисли|добавь)\b.*\b(денег|деньги|рублей|рубли|монет)\b',text.casefold()):return 0
  n=e['npcs'].setdefault(k,{'paid':0,'base_count':0,'texts':[]})
  if any(len(tokens&set(t))/max(1,len(tokens|set(t)))>=.8 for t in n['texts']):return 0
  digest=hashlib.sha256(' '.join(sorted(tokens)).encode()).hexdigest()
  if digest in e['seen']:return 0
  e['seen'].append(digest);n['texts'].append(sorted(tokens));n['texts']=n['texts'][-30:];amount=1 if n['base_count']<2 else 0;kind='conversation';q=result.get('economy',{})
  if isinstance(q,dict) and q.get('success') is True and type(q.get('confidence')) is int and q['confidence']>=85 and q.get('kind') in ('information','deal','provocation'):kind=q['kind'];amount+=3 if kind=='provocation' else 2
  amount=max(0,min(amount,6-n['paid'],20-e['earned']))
  if amount:s['rub']+=amount;n['paid']+=amount;n['base_count']+=1;e['earned']+=amount;e['audit'].append({'day':s['day'],'npc':k,'amount':amount,'kind':kind,'text':text[:300]});e['audit']=e['audit'][-100:]
  return amount
class Duel:
 def __init__(self,w,k,ambush=False,seed=None):
  self.w=w;self.k=k;self.rng=random.Random(seed);self.hp=w.s['hp'];self.max_enemy=120 if w.npcs[k]['boss'] else 90;self.enemy=w.s['npc_health'].get(k,self.max_enemy);self.round=1;self.done=False;self.finished=False;self.log=[];self.result='Отступление';self.commit()
  if ambush:self.hp=max(0,self.hp-12);self.log.append('Внезапный удар: -12 HP.')
  self.check()
 def commit(self):self.emove=self.rng.randrange(3);self.eaim=self.rng.randrange(3);self.guard=self.rng.random()<.25
 def check(self):
  if self.hp<=0 or self.enemy<=0:self.done=True;self.result='Обоюдное поражение' if self.hp<=0 and self.enemy<=0 else 'Поражение' if self.hp<=0 else 'Победа'
 def strike(self,aim,move,stance):
  if self.done:return
  if aim not in range(3) or move not in range(3) or stance not in ('attack','guard','aim'):raise ValueError('Неверный ход')
  s=self.w.s;g=s['gear'];cost=5 if stance=='guard' else 7 if stance=='aim' else 9;exhausted=s['stamina']<cost;s['stamina']=max(0,s['stamina']-cost);damage=int(g['damage']*.55) if exhausted else g['damage'];damage=int(damage*(1.35 if core.weak_known(self.w,self.k) else 1));acc=g['accuracy']-(.15 if exhausted else 0)
  hit=max(.1,min(.95,acc+(.18 if aim==self.emove else -.18)+(.1 if stance=='aim' else 0)))
  d=max(1,damage+self.rng.randint(-3,3)-(6 if self.guard else 2)) if self.rng.random()<hit else 0
  t=max(1,19+self.rng.randint(-3,3)-g['armor']-(9 if stance=='guard' else 0)) if self.rng.random()<(.86 if self.eaim==move else .48) else 0
  if t:t=max(1,int(round(t*core.diff(self.w)['dmg'])))
  if stance=='guard':s['stamina']=min(s['stamina_max'],s['stamina']+7)
  self.enemy=max(0,self.enemy-d);self.hp=max(0,self.hp-t);self.log.append(f'Раунд {self.round}: нанесли {d}, получили {t}.');self.round+=1
  if exhausted:self.log.append('Выдохлись: урон и точность ниже. Защита помогает отдышаться.')
  self.check()
  if not self.done and self.round>30:self.done=True;self.result='Ничья'
  if not self.done:self.commit()
  s['hp']=max(1,self.hp);s['npc_health'][self.k]=self.enemy
 def finish(self):
  if self.finished:return
  self.finished=True;s=self.w.s;s['hp']=max(1,self.hp);s['npc_health'][self.k]=self.enemy
  if not self.hp:s['rub']=max(0,s['rub']-15)
  if self.done and self.hp>0 and self.enemy==0:
   if self.k not in s['defeated']:s['rub']+=40;s['defeated'].append(self.k)
   else:s['rub']+=5
  s['turn']+=1;self.w.event('combat','Бой с '+self.w.npcs[self.k]['name']+': '+self.result,[self.k]);core.on_duel(self.w,self.k,self.result)
