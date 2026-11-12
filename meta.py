
"""Мета-слой v9: слоты сохранений, настройки, .env, достижения, новая игра. Без tkinter."""
import json,os,re,time,shutil
from pathlib import Path
import core

SLOTS=['slot1','slot2','slot3']
DEFAULT_SETTINGS={'brightness':1.0,'fullscreen':False,'ui_scale':1.0,'cover':True,'volume':0.7,'music':0.4,'autosave_sec':30,'hints':True,'seen_howto':False}

def sdir(base):
    p=Path(base)/'saves';p.mkdir(parents=True,exist_ok=True);return p
def slot_path(base,sid):
    return Path(base)/'saves'/('autosave.json' if sid=='auto' else 'town_v4.json' if sid=='legacy' else sid+'.json')

# ---------- настройки ----------
def load_settings(base):
    s=dict(DEFAULT_SETTINGS);p=Path(base)/'settings.json'
    try:
        d=json.loads(p.read_text(encoding='utf8'))
        for k,v in d.items():
            if k in s and type(v)==type(s[k]) or (k in s and isinstance(s[k],float) and isinstance(v,int)):s[k]=v
    except Exception:pass
    return clamp_settings(s)
def clamp_settings(s):
    s['brightness']=max(.4,min(1.6,float(s['brightness'])));s['ui_scale']=max(.8,min(1.8,float(s['ui_scale'])));s['volume']=max(0.0,min(1.0,float(s['volume'])));s['music']=max(0.0,min(1.0,float(s['music'])))
    s['autosave_sec']=int(max(10,min(600,s['autosave_sec'])));return s
def save_settings(base,s):
    (Path(base)/'settings.json').write_text(json.dumps(s,ensure_ascii=False,indent=1),encoding='utf8')

def env_set(base,key,val):
    """Меняет KEY=... во всех строках .env (дубли тоже), либо дописывает в конец. Комментарии сохраняются."""
    p=Path(base)/'.env';text=p.read_text(encoding='utf-8-sig') if p.exists() else ''
    pat=re.compile(r'^\s*'+re.escape(key)+r'\s*=.*$',re.M)
    if pat.search(text):text=pat.sub(lambda m:key+'='+str(val),text)
    else:text=text.rstrip('\n')+'\n'+key+'='+str(val)+'\n'
    p.write_text(text if text.endswith('\n') else text+'\n',encoding='utf8')

# ---------- сохранения ----------
def new_state(npcs,diff='normal'):
    from world import World
    w=World(npcs,None);d=core.DIFFS.get(diff,core.DIFFS['normal'])
    w.s['cig']=d['cig'];w.s['rub']=d['rub'];w.s['meta']={'diff':diff if diff in core.DIFFS else 'normal','created':time.time(),'playtime':0,'saved':0}
    return w.s

def write_state(base,sid,state,playtime=0):
    m=state.setdefault('meta',{'diff':'normal','created':time.time(),'playtime':0});m['saved']=time.time();m['playtime']=m.get('playtime',0)+playtime
    p=slot_path(base,sid);sdir(base)
    if sid=='auto' and p.exists():
        try:shutil.copy2(p,p.with_suffix('.bak'))
        except OSError:pass
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(state,ensure_ascii=False,indent=1),encoding='utf8');os.replace(tmp,p)

def read_state(base,sid):
    p=slot_path(base,sid)
    try:d=json.loads(p.read_text(encoding='utf8'))
    except FileNotFoundError:raise ValueError('Слот пуст')
    except Exception as e:raise ValueError('Файл сохранения повреждён: %s'%e)
    if not isinstance(d,dict) or 'day' not in d or 'loc' not in d:raise ValueError('Это не файл сохранения Тюряги')
    return d

def load_any(base):
    """Автозагрузка: автосохранение -> резервная копия -> старое town_v4.json."""
    for sid in ('auto',):
        try:return read_state(base,sid)
        except ValueError:pass
    bak=slot_path(base,'auto').with_suffix('.bak')
    try:
        d=json.loads(bak.read_text(encoding='utf8'))
        if isinstance(d,dict) and 'day' in d:return d
    except Exception:pass
    try:return read_state(base,'legacy')
    except ValueError:return None

def summary(base,sid):
    try:d=read_state(base,sid)
    except ValueError as e:return None if str(e)=='Слот пуст' else {'error':str(e)}
    m=d.get('meta') or {};c=d.get('core') or {};mins=(c.get('abs',420))%1440
    caste=c.get('caste',0)
    t='Петух' if caste<-70 else 'Шестёрка' if caste<-35 else 'Мужик' if caste<35 else 'Авторитет' if caste<70 or len(c.get('ousted',[]))<2 else 'Пахан'
    names=['Камера','Двор','Столовая','Коридор','Баня','Барак','Прачечная','Мастерская','Храм','ШИЗО','Клуб','Подвалы']
    return {'day':d['day'],'time':'%02d:%02d'%(mins//60,mins%60),'tier':t,'loc':names[d['loc']] if 0<=d['loc']<12 else '?','diff':core.DIFFS.get(m.get('diff','normal'),core.DIFFS['normal'])['name'],
            'saved':time.strftime('%d.%m.%Y %H:%M',time.localtime(m['saved'])) if m.get('saved') else 'ранее','playtime':int(m.get('playtime',0)//60),'scenes':len(c.get('done',[]))}

def summary_text(s):
    if s is None:return 'пусто'
    if 'error' in s:return s['error']
    return 'День %d · %s · %s · %s · %s · игра %d мин · %s'%(s['day'],s['time'],s['loc'],s['tier'],s['diff'],s['playtime'],s['saved'])

# ---------- достижения ----------
def _ev(w,kind,tail=None):
    return any(e.get('kind')==kind and (tail is None or e.get('text','').endswith(tail)) for e in w.s['events'])
def _cnt(w,k):return core.C(w)['counters'].get(k,0)
def _fl(w,f):return core.has(w,f)
def _rel5(w):return sum(1 for v in w.s['relations'].values() if v>=50)>=5
ACH=[
 ('first_blood','Первая кровь','Победить в драке.',lambda w:_ev(w,'combat','Победа'),False),
 ('boss1','Свергатель','Свергнуть первого босса.',lambda w:len(core.C(w)['ousted'])>=1,False),
 ('boss3','Гроза начальства','Свергнуть трёх боссов.',lambda w:len(core.C(w)['ousted'])>=3,False),
 ('boss8','Зона без хозяев','Свергнуть всех боссов зоны.',lambda w:len(core.C(w)['ousted'])>=len(core.BOSS_LOC),False),
 ('tier_up','Не последний человек','Стать Авторитетом.',lambda w:core.C(w)['caste']>=35,False),
 ('pahan','Слово — закон','Достичь статуса Пахана.',lambda w:core.tier(w)[0]=='Пахан',False),
 ('six','На побегушках','Опуститься до Шестёрки.',lambda w:core.C(w)['caste']<-35,False),
 ('bottom','Дно пробито','Опуститься до Петуха. Выбраться ещё сложнее.',lambda w:core.C(w)['caste']<=-70,True),
 ('wis10','Голова на плечах','Довести мудрость до 10.',lambda w:core.C(w)['wis']>=10,False),
 ('cha10','Язык без костей','Довести харизму до 10.',lambda w:core.C(w)['cha']>=10,False),
 ('story10','Втянулся','Пройти 10 сюжетных сцен.',lambda w:len(core.C(w)['done'])>=10,False),
 ('story_all','Весь сюжет','Пройти все сюжетные сцены.',lambda w:len(core.C(w)['done'])>=sum(1 for s in __import__('story_data').SCENES.values() if s['story']),False),
 ('ending','Финал','Дойти до любой концовки.',lambda w:bool(core.C(w).get('ending')),False),
 ('end_escape','Свобода','Концовка «Подкоп».',lambda w:_fl(w,'END_escape'),False),
 ('end_pahan','Трон из ящиков','Концовка «Пахан».',lambda w:_fl(w,'END_pahan'),False),
 ('end_zavhoz','Завхоз','Концовка «Завхоз».',lambda w:_fl(w,'END_zavhoz'),False),
 ('end_snitch','Крыса','Концовка «Крыса».',lambda w:_fl(w,'END_snitch'),True),
 ('end_honest','Честный мужик','Концовка «Мужик».',lambda w:_fl(w,'END_honest'),False),
 ('rich','Кубышка','Накопить 200 ₽.',lambda w:w.s['rub']>=200,False),
 ('smoker','Табачный барон','Накопить 50 сигарет.',lambda w:w.s['cig']>=50,False),
 ('stash','Схрон','Спрятать вещи в схроне.',lambda w:any(any(v.values()) for v in core.C(w)['stash'].values()),False),
 ('gym5','Качок','Пять раз сходить в тренажёрку.',lambda w:_cnt(w,'gym')>=5,False),
 ('shift10','Ударник','Отработать 10 смен.',lambda w:_cnt(w,'work_shift')>=10,False),
 ('pray3','Прихожанин','Трижды поговорить с Господом.',lambda w:_cnt(w,'temple_god')>=3,False),
 ('tunnel','Крот','Прокопать все 6 участков подкопа.',lambda w:w.s['dig']>=6,False),
 ('talker','Душа компании','Отправить 50 сообщений NPC.',lambda w:core.C(w)['talk']>=50,False),
 ('friends','Свой в доску','Отношение 50+ у пяти жителей.',_rel5,False),
 ('cats','Кошачий друг','Подружиться с кошками Гвоздева.',lambda w:_fl(w,'cats_friend'),False),
 ('traitor','Подлец','Подставить Коляна.',lambda w:_fl(w,'framed_kol'),True),
 ('week','Старожил','Дожить до 10-го дня.',lambda w:w.s['day']>=10,False),
 ('end_cats','Мур-революция','Концовка «Кошачья революция».',lambda w:_fl(w,'END_cats'),True),
 ('end_amnesty','Чистая совесть','Концовка «Полная амнистия».',lambda w:_fl(w,'END_amnesty'),True),
 ('end_shaw','Побег из Шоушенка','Секретная концовка: ползти через трубу под грозой.',lambda w:_fl(w,'END_shaw'),True),
 ('weak1','Знай врага','Найти слабость первого босса.',lambda w:len(core.C(w)['weak'])>=1,False),
 ('weak_all','Доска слабостей','Узнать слабости всех боссов зоны.',lambda w:len(set(core.C(w)['weak'])|set(core.C(w)['ousted']))>=len(core.BOSS_LOC),False),
 ('weak_win','Мозги, а не кулаки','Свергнуть босса, используя слабость.',lambda w:any(k.startswith('weak_') and k.endswith('_used') and v for k,v in core.C(w)['flags'].items()),False),
 ('matr','Матрёшка','Пройти цепочку посылок до конца.',lambda w:_fl(w,'matr_done'),False),
 ('broker','Биржевой волк','Пять раз поторговать на бирже чая.',lambda w:_cnt(w,'exchange')>=5,False),
 ('shiv_master','Заказчик','Получить заточку мастера.',lambda w:_cnt(w,'order_shiv')>=1,False),
 ('parcel','Связи с волей','Отправить посылку через свидание.',lambda w:_cnt(w,'parcel')>=1,False),
 ('bday','Именинник','Отпраздновать день рождения Коляна.',lambda w:_fl(w,'kol_bday_done'),False),
 ('bff','Друг зоны','Подружиться с жителем зоны.',lambda w:any(k.startswith('friend_') and v for k,v in core.C(w)['flags'].items()),False),
 ('brawler','Бывалый','Выиграть 5 драк.',lambda w:_cnt(w,'duel_win')>=5,False),
 ('parry','Идеальный блок','Парировать удар в бою.',lambda w:_cnt(w,'parry')>=1,False),
 ('combo','Комбо-мастер','Выполнить комбо в бою.',lambda w:_cnt(w,'combo')>=1,False),
 ('limb','Вывел из строя','Вывести из строя часть тела противника.',lambda w:_cnt(w,'limb_broken')>=1,False),
 ('turf1','Без хозяина','Освободить локацию от её хозяина.',lambda w:any(b in core.C(w)['ousted'] for b in core.TURF),False),
 ('turf_all','Ничья земля','Свергнуть всех четырёх хозяев локаций: двор, кухня, душевая и библиотека свободны.',lambda w:all(b in core.C(w)['ousted'] for b in core.TURF),False),
 ('letters5','Пишите письма','Отправить домой пять писем.',lambda w:_cnt(w,'letter')>=5,False),
]
def ach_store(base):
    try:d=json.loads((Path(base)/'achievements.json').read_text(encoding='utf8'))
    except Exception:d={}
    d.setdefault('unlocked',{});return d
def check_achievements(w,base):
    st=ach_store(base);new=[]
    for id,title,desc,fn,hidden in ACH:
        if id in st['unlocked']:continue
        try:ok=bool(fn(w))
        except Exception:ok=False
        if ok:st['unlocked'][id]=time.time();new.append((id,title,desc))
    if new:(Path(base)/'achievements.json').write_text(json.dumps(st,ensure_ascii=False,indent=1),encoding='utf8')
    return new
