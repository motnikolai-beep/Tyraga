
"""Ядро v8: время суток, каста, статы, проверки, схроны, события. Без tkinter — тестируется отдельно."""
import random

NAMES=['Камера','Двор','Столовая','Коридор','Баня','Барак','Прачечная','Мастерская','Храм','ШИЗО','Клуб','Подвалы']
EDGES=[(0,1),(1,2),(2,7),(0,5),(5,9),(1,3),(3,4),(4,6),(6,7),(2,4),(5,3),(3,8),(4,10),(6,11),(9,8),(8,10),(10,11)]
MAPPOS={0:(.12,.2),1:(.37,.2),2:(.63,.2),7:(.88,.2),5:(.12,.5),3:(.37,.5),4:(.63,.5),6:(.88,.5),9:(.12,.8),8:(.37,.8),10:(.63,.8),11:(.88,.8)}
HOP=8
MEALS=[('breakfast','Завтрак',8*60),('lunch','Обед',13*60),('dinner','Ужин',19*60)]
ITEMS={'parcel':'посылка-матрёшка','shiv':'заточка','phone':'мобильник','tea':'пачка чая','key':'ключ от подвала','letter':'письмо с воли'}
TIERS=[(-70,'Петух','самое дно: над вами шутят даже мыши'),(-35,'Шестёрка','на побегушках у всех'),(35,'Мужик','обычный работяга, ни рыба ни мясо'),(70,'Авторитет','с вами здороваются первыми'),(101,'Пахан','слово — закон, а закон — слово')]

DIFFS={
 'easy':{'name':'Мужик','desc':'Для знакомства с зоной: щедрые доходы, мягкие шмоны, проверки на 2 проще, мини-игры на 10% легче. Старт: 25 сигарет, 40 ₽.','dc':-2,'income':1.25,'dmg':.75,'shmon':.6,'game':.10,'cig':25,'rub':40},
 'normal':{'name':'Зона','desc':'Задуманный баланс. Старт: 15 сигарет, 20 ₽.','dc':0,'income':1.0,'dmg':1.0,'shmon':1.0,'game':0.0,'cig':15,'rub':20},
 'hard':{'name':'Строгий режим','desc':'Доходы ниже на 25%, урон выше на 30%, шмоны чаще, проверки на 2 тяжелее, мини-игры на 10% сложнее. Старт: 8 сигарет, 10 ₽.','dc':2,'income':.75,'dmg':1.3,'shmon':1.6,'game':-.10,'cig':8,'rub':10}}
def diff(w):
    return DIFFS.get((w.s.get('meta') or {}).get('diff','normal'),DIFFS['normal'])

def default():
    return {'abs':7*60,'wis':5,'cha':5,'caste':0,'flags':{},'done':[],'stash':{},'inv':{'shiv':0,'phone':0,'tea':0,'key':0,'letter':0,'parcel':0},
            'ousted':[],'timers':[],'events_done':[],'weak':[],'meals':{},'pending':[],'talk':0,'gym':0,'temple_day':0,'ending':None,'feed':[],'counters':{},'last_random':-999,'poverka_day':0,
            'denounced':[],'friend_search_day':0,'news_day':0,'news':[],'npc_relations':{},'ex':{}}  # ex — свергнутые боссы: кто, когда, помирились ли, что с реваншем (former.py)

def C(w):
    c=w.s.setdefault('core',default())
    for k,v in default().items():c.setdefault(k,v)
    return c

def hhmm(w):
    m=C(w)['abs']%1440;return '%02d:%02d'%(m//60,m%60)
def tod(w):return C(w)['abs']%1440
def phase(w):
    m=tod(w)
    return 'Ночь' if (m>=22*60 or m<5*60) else 'Утро' if m<11*60 else 'День' if m<18*60 else 'Вечер'
def is_night(w):
    m=tod(w);return m>=22*60 or m<5*60

def tier(w):
    c=C(w);v=c['caste']
    if v<-70:return TIERS[0][1],TIERS[0][2]
    if v<-35:return TIERS[1][1],TIERS[1][2]
    if v<35:return TIERS[2][1],TIERS[2][2]
    if v<70 or len(c['ousted'])<2:return TIERS[3][1],TIERS[3][2]
    return TIERS[4][1],TIERS[4][2]

def say(w,text):
    f=C(w)['feed'];f.append(text);del f[:-30]

def add_caste(w,d,why=''):
    c=C(w);old=tier(w)[0];c['caste']=max(-100,min(100,c['caste']+d));new=tier(w)[0]
    if d:say(w,'Каста %+d%s'%(d,(' · '+why) if why else ''))
    if new!=old:
        say(w,'★ Ваш статус изменился: %s → %s'%(old,new));w.event('caste','Статус игрока: %s → %s.'%(old,new),list(w.npcs),public=True)

def flag(w,name,val=True):C(w)['flags'][name]=val
def in_power(w,k):
    """Босс у власти: числится боссом и не свергнут. Свергнутый остаётся в своей локации «бывшим»."""
    return bool(w.npcs.get(k,{}).get('boss')) and k not in C(w)['ousted']
def is_former(w,k):return bool(w.npcs.get(k,{}).get('boss')) and k in C(w)['ousted']
def max_hp(w,k):return 120 if in_power(w,k) else 90
def badge(w,k):
    """Короткая пометка к имени героя: кем он стал для игрока (бывший босс…)."""
    import former
    out=[]
    if is_former(w,k):out.append(former.word(k))
    return ' · '.join(out)
def shown_name(w,k):
    b=badge(w,k);return w.npcs[k]['name']+(' · '+b if b else '')
def has(w,name):return bool(C(w)['flags'].get(name))

def mod(w,stat):
    c=C(w);m=c[stat]
    if stat=='cha':
        t=tier(w)[0];m+={'Петух':-3,'Шестёрка':-1,'Мужик':0,'Авторитет':2,'Пахан':4}[t]
    if w.s['stamina']<15:m-=2
    return m

def check(w,stat,dc,boost=0,rng=None):
    dc=dc+diff(w)['dc'];r=(rng or random).randint(1,20);m=mod(w,stat);tot=r+m+boost
    return {'ok':tot>=dc or r==20,'roll':r,'mod':m,'boost':boost,'total':tot,'dc':dc,'stat':stat,'crit':r==20,'fumble':r==1}

def boost_value(w,smoke,focus):
    b=0.0
    if smoke and w.s['cig']>=1:b+=.25
    if focus and w.s['stamina']>=10:b+=.15
    if w.s['stamina']<20:b-=.15
    return b+diff(w)['game']

def apply(w,fx):
    """Применяет эффекты, возвращает список строк для показа игроку."""
    s=w.s;c=C(w);out=[]
    for k,v in fx.items():
        if v==0 and k not in ('flag','unflag'):continue
        d=diff(w)
        if k in('cig','rub') and v>0:v=max(1,int(round(v*d['income'])))
        if k=='hp' and v<0:v=min(-1,int(round(v*d['dmg'])))
        if k=='cig' and v<0:c['counters']['cig_spent']=c['counters'].get('cig_spent',0)-v
        if k=='rub' and v>0:c['counters']['rub_earned']=c['counters'].get('rub_earned',0)+v
        if k=='cig':s['cig']=max(0,s['cig']+v);out.append('Сигареты %+d'%v)
        elif k=='rub':s['rub']=max(0,s['rub']+v);out.append('Рубли %+d'%v)
        elif k=='hp':s['hp']=max(1,min(100,s['hp']+v));out.append('HP %+d'%v)
        elif k=='stamina':s['stamina']=max(0,min(s['stamina_max'],s['stamina']+v));out.append('Силы %+d'%v)
        elif k=='food':s['food']=max(0,min(100,s['food']+v));out.append('Сытость %+d'%v)
        elif k in('wis','cha'):c[k]+=v;out.append(('Мудрость' if k=='wis' else 'Харизма')+' %+d'%v)
        elif k=='caste':add_caste(w,v)
        elif k=='karma':
            for d,n in v.items():s['karma'][d]=max(-100,min(100,s['karma'][d]+n));out.append('Карма(%s) %+d'%({'empathy':'сочувствие','honor':'честь','cunning':'хитрость'}[d],n))
        elif k=='rel':
            for n,d in v.items():
                if n in w.npcs:s['relations'][n]=max(-100,min(100,s['relations'].get(n,0)+d));out.append('%s: отношение %+d'%(w.npcs[n]['name'],d))
        elif k=='rep':s['street_rep']['earned']=max(-100,min(100,s['street_rep']['earned']+v));out.append('Уважуха %+d'%v)
        elif k=='flag':
            for f in ([v] if isinstance(v,str) else v):flag(w,f)
        elif k=='unflag':
            for f in ([v] if isinstance(v,str) else v):c['flags'].pop(f,None)
        elif k=='item':
            for n,d in v.items():c['inv'][n]=max(0,c['inv'].get(n,0)+d);out.append('%s %+d'%(ITEMS.get(n,n).capitalize(),d))
        elif k=='smax':s['stamina_max']=min(140,s['stamina_max']+v);out.append('Макс. силы %+d'%v)
        elif k=='dig':s['dig']=min(6,s['dig']+v);out.append('Подкоп %+d'%v)
        elif k=='gear':s['gear'].update(v);out.append('Снаряжение обновлено')
        elif k=='life_letter':
            import life15
            out+=life15.letter(w,v)
        elif k=='life_routine':
            import life15
            out+=life15.routine(w,v)
        elif k=='cleanse':
            n=0
            for d in s['karma']:
                if s['karma'][d]<0:t=min(-s['karma'][d],v);s['karma'][d]+=t;n+=t
            out.append('Грехи списаны: %d'%n)
        elif k=='note':s['diary'].append('День %d. %s'%(s['day'],v))
        elif k=='ending':c['ending']=v
        elif k=='time':advance(w,v)
        elif k=='ouster':boss_down(w,v,by='сюжет')
        elif k=='timer':c['timers'].append({'at':c['abs']+int(v.get('hours',24)*60),'id':v['id'],'vars':v.get('vars',{})})
        elif k=='learn_weak':
            if v not in c['weak']:c['weak'].append(v);out.append('Слабость найдена: '+w.npcs[v]['name'])
        elif k=='friend_help':
            import social
            friend=social.friend(w)
            if friend:out+=social.use_help(w,friend)
        elif k=='ally_denunciation':
            import social
            ally=social.friend(w)
            if ally:out+=social.hide(w,ally)
        elif k=='queue_shmon':
            c['pending'].insert(0,{'t':'scene','id':'shmon','protected':True})
        elif k=='counter':
            for n_,d_ in v.items():c['counters'][n_]=c['counters'].get(n_,0)+d_
        elif k in('peace','mock','revenge_off','duel','duel_ambush'):
            import former  # бывшие боссы: мир, обида, отказ от реванша, бой за место
            if k=='peace':out+=former.peace(w,v)
            elif k=='mock':out+=former.mock(w,v)
            elif k=='revenge_off':out+=former.off(w,v)
            else:out+=former.start_duel(w,v,k=='duel_ambush')
    return out

# ---- время и события ----
def advance(w,minutes,quiet=False):
    c=C(w);a0=c['abs'];a1=a0+int(minutes);c['abs']=a1;w.s['turn']+=1
    for dayn in range(a0//1440,a1//1440+1):
        for key,name,t in MEALS:
            T=dayn*1440+t;k='%d:%s'%(dayn,key)
            if a0<T<=a1 and k not in c['meals']:
                c['meals'][k]=0;c['pending'].append({'t':'scene','id':scene_for(w,'meal'),'vars':{'slot':name,'key':k}})
        T=dayn*1440+21*60
        if a0<T<=a1 and c['poverka_day']!=dayn:
            c['poverka_day']=dayn;c['pending'].append({'t':'scene','id':'poverka'})
    due=[t for t in c['timers'] if t['at']<=a1]
    if due:
        c['timers']=[t for t in c['timers'] if t['at']>a1]
        for t in due:c['pending'].append({'t':'scene','id':scene_for(w,t['id']),'vars':t.get('vars',{})})
    if not quiet:
        for dayn in range(max(1,a0//1440),a1//1440+1):
            if a0<dayn*1440+180<=a1:force_sleep(w);break
    if len(c['meals'])>60:
        for k in sorted(c['meals'])[:-30]:c['meals'].pop(k)
    if w.rng.random()<.5:w.relay()

def force_sleep(w):
    say(w,'Вы вырубились на ходу. Утром всё болит.');sleep(w,force=True)

def sleep(w,force=False):
    c=C(w)
    if not force and not is_night(w):raise ValueError('Шконка днём для вас закрыта: лечь можно только ночью (с 22:00). Займитесь делом или сходите на кормёжку.')
    import former
    former.night(w)  # кто ждал разборки и не дождался
    w.sleep()
    day_start=((c['abs']//1440)+(1 if c['abs']%1440>=5*60 else 0))*1440+6*60
    c['abs']=day_start;w.s['ap']=99
    if force:w.s['stamina']=int(w.s['stamina_max']*.6);w.s['hp']=max(1,w.s['hp']-8)
    c['flags'].pop('storm_tonight',None);c['flags'].pop('letter_today',None);c['pending'].append({'t':'scene','id':'morning'});schedule_day(w)
    if w.s['day']>=2:c['pending'].append({'t':'scene','id':'life15_round'})
    former.morning(w)
    import zone_news
    zone_news.morning(w)

def hops(a,b):
    if a==b:return 0
    adj={}
    for x,y in EDGES:adj.setdefault(x,[]).append(y);adj.setdefault(y,[]).append(x)
    seen={a};q=[(a,0)]
    while q:
        n,d=q.pop(0)
        for m in adj.get(n,[]):
            if m==b:return d+1
            if m not in seen:seen.add(m);q.append((m,d+1))
    return 99

def travel_minutes(w,dest):return hops(w.s['loc'],dest)*HOP

def travel(w,dest):
    if dest==w.s['loc']:return
    m=travel_minutes(w,dest);w.go(dest);advance(w,m)
    import former
    former.on_enter(w)
    import social
    social.arrival(w)
    random_event(w,'travel')
    story_check(w)

def talk(w):
    c=C(w);c['talk']+=1;m=7
    if c['talk']%3==0:m+=15;say(w,'Долгая болтовня: прошло ещё 15 минут.')
    advance(w,m)
    import social
    social.arrival(w)
    if w.rng.random()<.07:random_event(w,'talk',force=True)

def contraband(w):
    c=C(w);return c['inv'].get('shiv',0)+c['inv'].get('phone',0)

def random_event(w,why,force=False):
    c=C(w);s=w.s
    if s['turn']-c['last_random']<6 and not force:return
    p=0.06+(0.10 if contraband(w) else 0)+(0.04 if has(w,'snitch') else 0)
    if why=='travel' and s['loc'] in (3,9):p+=.08
    p*=diff(w)['shmon']
    if w.rng.random()<p:
        c['last_random']=s['turn']
        t=tier(w)[0]
        pool=[('shmon',3 if contraband(w) else 1),('podstava',1 if s['day']>=3 else 0),('cats',1),('trade',1),('brawl',1 if s['day']>=2 else 0),('extort',3 if t in('Петух','Шестёрка') else 0),('tribute',2 if t in('Авторитет','Пахан') else 0),('orders',2 if t=='Пахан' else 0)]
        ids=[i for i,wt in pool for _ in range(wt)]
        if ids:c['pending'].append({'t':'scene','id':w.rng.choice(ids)})

def boss_down(w,k,by='бой'):
    c=C(w)
    if k in c['ousted'] or not w.npcs.get(k,{}).get('boss'):return False
    c['ousted'].append(k);name=w.npcs[k]['name'];s=w.s
    import former
    former.on_fall(w,k,by)
    w.event('boss_down','Босс «%s» повержен игроком (%s). Зона знает об этом.'%(name,by),list(w.npcs),public=True)
    for n in w.npcs:
        if n!=k:s['relations'][n]=max(-100,min(100,s['relations'].get(n,0)+6))
    s['street_rep']['earned']=min(100,s['street_rep']['earned']+12)
    add_caste(w,15,'босс «%s» повержен'%name)
    say(w,'☠ %s больше не у власти и остаётся в зоне. Остальные теперь относятся к вам с опаской и уважением (+6 к отношению)'%name)
    c['pending'].append({'t':'scene','id':'boss_aftermath','vars':{'boss':k}})
    return True

def on_duel(w,k,result):
    cn=C(w)['counters']
    if result=='Победа':cn['duel_win']=cn.get('duel_win',0)+1
    elif result=='Поражение':cn['duel_lose']=cn.get('duel_lose',0)+1
    import former
    if former.after_duel(w,k,result):pass  # реванш или драка с бывшим боссом: у них свои правила
    elif result=='Победа':
        if in_power(w,k):boss_down(w,k)
        else:add_caste(w,6,'победа над %s'%w.npcs[k]['name'])
    elif result=='Поражение':add_caste(w,-8,'проигрыш в драке')
    advance(w,30,quiet=True)

# ---- схроны ----
def stash_get(w,loc):return C(w)['stash'].setdefault(str(loc),{'cig':0,'shiv':0,'phone':0,'tea':0})
def stash_move(w,loc,item,n,put=True):
    st=stash_get(w,loc);inv=C(w)['inv'];s=w.s
    have=(s['cig'] if item=='cig' else inv.get(item,0)) if put else st.get(item,0)
    n=min(n,have)
    if n<=0:raise ValueError('Нечего перекладывать')
    d=n if put else -n
    st[item]=st.get(item,0)+d
    if item=='cig':s['cig']-=d
    else:inv[item]=inv.get(item,0)-d
    advance(w,5,quiet=True)
def stash_has(w,loc):
    st=C(w)['stash'].get(str(loc),{});return any(st.values())

# ---- сюжет ----
def story_check(w):
    from story_data import available
    c=C(w)
    for sid in available(w):
        if not any(p.get('id')==sid for p in c['pending']):c['pending'].append({'t':'scene','id':sid})
        return

def pop_pending(w):
    c=C(w)
    if not c['pending']:return None
    p=c['pending'].pop(0)
    if p.get('id')=='shmon':
        import social
        return social.prepare_search(w,p)
    return p

def finish_scene(w,sid):
    c=C(w)
    from story_data import SCENES
    if SCENES.get(sid,{}).get('story') and sid not in c['done']:c['done'].append(sid)

def story_available_at(w,loc):
    from story_data import available
    return any(True for _ in available(w,loc=loc))

def caste_report(w):
    c=C(w);n,d=tier(w)
    return {'tier':n,'desc':d,'score':c['caste'],'ousted':[w.npcs[k]['name'] for k in c['ousted']]}

def activities(w):
    """Карточки действий для текущей локации."""
    s=w.s;L=s['loc'];out=[]
    night=is_night(w)
    def add(i,t,m,ic,reason=None):out.append({'id':i,'title':t,'min':m,'icon':ic,'off':reason})
    tired=lambda n:'Нужно %d+ сил'%n if s['stamina']<n else None
    if L==0:add('search_cell','Обыскать камеру',45,'rat');add('stash','Схрон',5,'cig')
    if L==1:add('gym','Тренажёрка',90,'heart',tired(15));add('smoke_break','Перекур',20,'cig','Нет сигарет' if s['cig']<1 else None)
    if L==2:add('work_shift','Кухня: смена',120,'soup',tired(20))
    if L==3:add('patrol','Шнырять по коридору',30,'rat');add('hide','Спрятать вещи',10,'cig')
    if L==4:add('wash','Помыться',30,'heart');add('mini_dance','Танцы на стрелках',40,'star')
    if L==5:add('rest','Отдохнуть на нарах',60,'clock');add('mini_cards','Игра в карты',40,'coin','Нужно 5 сигарет' if s['cig']<5 else None)
    if L==6:add('work_shift','Прачечная: смена',120,'coin',tired(20))
    if L==7:add('work_shift','Мастерская: смена',120,'coin',tired(20));add('shiv_craft','Выточить заточку',90,'rat','Нужно 3 сигареты на материалы' if s['cig']<3 else None)
    if L==8:add('temple_god','Поговорить с Господом',30,'star');add('candle','Поставить свечу',10,'book','Нет сигарет' if s['cig']<1 else None)
    if L==9:add('serve','Отсидеть срок',120,'clock')
    if L==10:add('mini_poker','Покер на одной карте',40,'coin','Нужно 5 сигарет' if s['cig']<5 else None);add('mini_chess','Шахматы Лема',45,'book');add('visit','Комната свиданий',60,'heart','Свидания со 2-го дня' if s['day']<2 else None)
    if L==11:add('mini_tunnel','Копать подкоп',60,'rat',tired(20))
    b=boss_here(w)
    if b:
        if b in C(w)['weak']:add('weak_'+b,'Слабое место: '+w.npcs[b]['name'],30,'star')
        else:add('scout_'+b,'Разведка: слабости '+w.npcs[b]['name'],30,'rat')
    if L==7:add('exchange','Биржа чая',20,'coin');add('order_shiv','Заказать заточку (4 сиг., 2 дня)',10,'rat','Заказ уже в работе' if has(w,'shiv_ordered') else 'Нужно 4 сигареты' if s['cig']<4 else None)
    if L==7:add('letter','Написать письмо домой',40,'book','Сегодня письмо уже ушло' if has(w,'letter_today') else None)
    if L==10:add('parcel','Передать посылку (2 пачки чая)',15,'heart','Нужны 2 пачки чая' if C(w)['inv'].get('tea',0)<2 else 'Посылка уже в пути' if has(w,'parcel_sent') else None)
    add('bed','Лечь на шконку',0,'clock',None if night else 'Только ночью (с 22:00)')
    for a in out:
        b=turf_boss(w,a['id'])
        if b:a['title']+=' · хозяин — '+w.npcs[b]['name']
    return out

# ---- исполнитель сцен (без tk) ----
def req_ok(w,req):
    s=w.s;c=C(w)
    for k,v in req.items():
        if k=='cig' and s['cig']<v:return False
        if k=='rub' and s['rub']<v:return False
        if k=='food' and s['food']<v:return False
        if k=='dig' and s['dig']<v:return False
        if k=='caste' and c['caste']<v:return False
        if k.startswith('item_') and c['inv'].get(k[5:],0)<v:return False
        if k=='weak' and v not in c['weak']:return False
        if k=='friend':
            import social
            if not social.friend(w):return False
    return True

def req_text(req):
    n={'cig':'сиг.','rub':'₽','food':'сытости','dig':'участков подкопа','caste':'каста'}
    return ', '.join('друг рядом (+40)' if k=='friend' else 'известная слабость' if k=='weak' else '%s %s'%(v,n.get(k,k.replace('item_',''))) for k,v in req.items())

def resolve_choice(w,choice,game_ok=None,bonus=0,rng=None):
    info=None;ok=True
    if choice.get('chk'):
        st,dc=choice['chk'];info=check(w,st,dc,bonus,rng);ok=info['ok']
    elif choice.get('game'):
        ok=bool(game_ok)
    cn=C(w)['counters']
    if choice.get('chk'):cn['chk_ok' if ok else 'chk_fail']=cn.get('chk_ok' if ok else 'chk_fail',0)+1
    elif choice.get('game'):cn['game_ok' if ok else 'game_fail']=cn.get('game_ok' if ok else 'game_fail',0)+1
    res=choice['ok'] if ok else choice['fail']
    lines=apply(w,res.get('fx',{}))
    return {'ok':ok,'res':res,'check':info,'lines':lines}

def render_text(text,vars=None):
    try:return text.format_map(type('D',(dict,),{'__missing__':lambda s,k:'{'+k+'}'})(vars or {}))
    except Exception:return text


# ======== v10: цены по касте, сцены по контексту, ежедневные события, слабости, журнал, статистика ========
PRICE={'Петух':1.6,'Шестёрка':1.25,'Мужик':1.0,'Авторитет':.85,'Пахан':.7}
def price_mult(w):return PRICE[tier(w)[0]]
def price(w,base):return max(1,int(round(base*price_mult(w))))
def market_band(w):return ['low','mid','high'][(w.s['day']*7+w.s['day']//3)%3]
MARKET={'low':(8,6),'mid':(12,9),'high':(17,13)}
def scene_for(w,sid):
    t=tier(w)[0]
    if sid=='meal':return 'meal_low' if t=='Петух' else 'meal_high' if t=='Пахан' else 'meal'
    if sid=='trade':return 'trade_'+('low' if t in('Петух','Шестёрка') else 'high' if t in('Авторитет','Пахан') else 'mid')
    if sid=='exchange':return 'exchange_'+market_band(w)
    b=turf_boss(w,sid)
    if b:return sid+'_'+b
    return sid
BOSS_LOC={'zub':0,'graf':5,'gvo':3,'str':6,'sm':11,'gen':10,'mat':8,'cook':9,'polkan':1,'hleb':2,'kip':4,'cenz':7}
# v12 «Хозяева локаций»: пока босс у власти, одно местное занятие идёт по его правилам (сцена «<занятие>_<босс>»).
# босс -> (локация, занятие, как это называется в журнале)
TURF={'polkan':(1,'smoke_break','перекур'),'hleb':(2,'work_shift','смена'),'kip':(4,'wash','горячая вода'),'cenz':(7,'letter','письма')}
def turf_boss(w,act,loc=None):
    """Босс, по чьим правилам сейчас идёт занятие act в локации (None — занятие свободно)."""
    L=w.s['loc'] if loc is None else loc;out=C(w)['ousted']
    return next((b for b,(l,a,_) in TURF.items() if l==L and a==act and b not in out),None)
def weak_known(w,k):return k in C(w)['weak']
def boss_here(w):
    c=C(w);return next((b for b,l in BOSS_LOC.items() if l==w.s['loc'] and b not in c['ousted']),None)
DAILY=[('kol_bday',3,9,18*60),('gen_check',4,12,11*60),('tea_missing',2,10,15*60),('canteen_brawl',3,12,13*60+30),('amnesty',6,11,10*60),('storm',8,14,22*60+30)]
def schedule_day(w):
    c=C(w);d=w.s['day'];day0=(c['abs']//1440)*1440
    elig=[e for e in DAILY if e[1]<=d<=e[2] and e[0] not in c['events_done'] and not any(t['id']==e[0] for t in c['timers']) and not (e[0]=='gen_check' and 'gen' in c['ousted'])]
    if elig:
        e=w.rng.choice(elig);c['events_done'].append(e[0]);c['timers'].append({'at':day0+e[3],'id':e[0],'vars':{}})
def journal(w):
    from story_data import SCENES,available
    c=C(w);s=w.s;out=[];avail=[];seen=set()
    for l in range(12):
        for sid in available(w,loc=l):
            if sid not in seen:seen.add(sid);avail.append('%s — сейчас доступна сюжетная сцена «%s»'%(NAMES[l],SCENES[sid].get('title',sid)))
    out.append(('Сюжет',avail or ['Сейчас новых сюжетных сцен нет. Ходите по зоне, говорите с жителями, ждите следующих дней.']))
    tm=[]
    for t in sorted(c['timers'],key=lambda t:t['at']):
        left=max(0,t['at']-c['abs']);tm.append('%s — через %d ч %02d мин'%(SCENES.get(scene_for(w,t['id']),{}).get('title',t['id']),left//60,left%60))
    out.append(('Ожидается',tm or ['Ничего не запланировано.']))
    d=['%s: долг %d ₽ до дня %d'%(w.npcs[o['npc']]['name'],o['amount'],o['due']) for o in s['obligations'] if o['status']=='active']
    out.append(('Долги',d or ['Долгов нет.']))
    wk=[('✔ %s: слабость известна — «Слабое место» в %s'%(w.npcs[b]['name'],NAMES[BOSS_LOC[b]])) if b in c['weak'] else ('? %s (%s): слабость неизвестна, нужна разведка'%(w.npcs[b]['name'],NAMES[BOSS_LOC[b]])) for b in BOSS_LOC if b not in c['ousted']]
    out.append(('Доска слабостей боссов',wk or ['Все боссы повержены.']))
    tf=[('✔ %s: %s — свободно, %s больше не хозяин'%(NAMES[l],what,w.npcs[b]['name'])) if b in c['ousted'] else ('✘ %s: %s — по правилам хозяина (%s)'%(NAMES[l],what,w.npcs[b]['name'])) for b,(l,a,what) in TURF.items() if b in w.npcs]
    out.append(('Хозяева локаций',tf))
    import social,zone_news
    out.append(('Свои и чужие',social.journal(w)))
    out.append(('Слухи зоны',zone_news.journal(w)))
    import life15,boss15
    out.append(('Повседневная жизнь',life15.journal(w)))
    out.append(('Судьбы хозяев',boss15.journal(w)))
    import former
    out.append(('Бывшие боссы',former.journal(w) or ['Пока никто не свергнут. Свергнутый босс остаётся в зоне: с ним можно помириться, а можно дождаться реванша.']))
    f=c['flags'];pl=[]
    for k,t in [('esc_key','ключ от подвала'),('shaw_hammer','геологический молоточек'),('shaw_poster','плакат'),('shaw_ledger','копия чёрной бухгалтерии')]:
        pl.append(('✔ ' if (f.get(k) or (k=='esc_key' and c['inv'].get('key'))) else '✘ ')+t)
    pl.append('%s подкоп: %d/6 участков'%('✔' if s['dig']>=6 else '✘',s['dig']))
    out.append(('Подготовка побега',pl));return out
def stats(w,playtime_min=0):
    c=C(w);cn=c['counters'];s=w.s
    chk=cn.get('chk_ok',0)+cn.get('chk_fail',0);g=cn.get('game_ok',0)+cn.get('game_fail',0)
    from lore import choices_summary
    return {'Дней в зоне':s['day'],'Статус':'%s (%+d)'%(tier(w)[0],c['caste']),'Концовка':c['ending'] or 'не выбрана','Сюжетных сцен пройдено':len(c['done']),
            'Драк выиграно / проиграно':'%d / %d'%(cn.get('duel_win',0),cn.get('duel_lose',0)),'Боссов повержено':len(c['ousted']),'Слабостей боссов найдено':len(c['weak']),
            'Проверок пройдено':'%d из %d'%(cn.get('chk_ok',0),chk),'Мини-игр выиграно':'%d из %d'%(cn.get('game_ok',0),g),
            'Сигарет потрачено':cn.get('cig_spent',0),'Рублей заработано':cn.get('rub_earned',0),'Сообщений NPC':c['talk'],'Мудрость / харизма':'%d / %d'%(c['wis'],c['cha']),
            'Время в игре, минут':playtime_min,'Ваши выборы':choices_summary(w)}
def on_chat(w,k):
    r=w.s['relations'].get(k,0);c=C(w);cn=c['counters'];cn['talk_'+k]=cn.get('talk_'+k,0)+1
    if r>=40 and not has(w,'friend_'+k):flag(w,'friend_'+k);say(w,'%s теперь считает вас другом.'%w.npcs[k]['name'])
    if r<=-40 and not has(w,'enemy_'+k):flag(w,'enemy_'+k);say(w,'%s вас на дух не переносит.'%w.npcs[k]['name'])
def log_scene(w,sid):
    from story_data import SCENES
    sc=SCENES.get(sid) or {}
    if sc.get('memo'):w.event('daily',sc['memo'],[k for k in sc.get('know',[]) if k in w.npcs],public=not sc.get('know'))
