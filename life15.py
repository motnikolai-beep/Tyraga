"""v15 prison life: small, bounded consequences, a three-day letter, and social memory.

Scripts decide effects; the LLM receives only a perspective-aware summary. All state is
lazy so v12-v14 saves continue unchanged. No visit, meal or release is guaranteed.
"""
import core

CHOICES={
 'share':('Вы разделили письмо с человеком рядом; это услышали в камере.',4,0),
 'quiet':('Вы оставили письмо при себе: чужой отклик пока не нужен.',0,0),
 'help':('Вы помогли соседу составить ответ домой, не требуя ничего взамен.',5,0),
}

def state(w):
    st=core.C(w).setdefault('life15',{'bonds':{},'letters':{},'routine':[]})
    st.setdefault('bonds',{});st.setdefault('letters',{});st.setdefault('routine',[])
    st.setdefault('outside',{'contact':0,'skill_days':[],'mutual':0})
    return st

def bond(w,k,trust=0,fear=0):
    if k not in w.npcs:return
    b=state(w)['bonds'].setdefault(k,{'trust':0,'fear':0})
    b['trust']=max(-100,min(100,b['trust']+trust));b['fear']=max(0,min(100,b['fear']+fear))

def observe(w,k,kind):
    # Actual decisions only, never dialogue claims or inferred emotional states.
    if kind=='help':bond(w,k,trust=5,fear=-1)
    elif kind=='theft':bond(w,k,trust=-10,fear=5)
    elif kind=='betrayal':bond(w,k,trust=-18,fear=10)

def routine(w,choice):
    if choice not in ('share','keep','listen'):raise ValueError('Нет такого решения')
    st=state(w)
    if any(x['day']==w.s['day'] for x in st['routine']):return ['Сегодняшний распорядок уже выбран.']
    if choice=='share' and w.s['food']<6:return ['Пайки недостаточно, чтобы поделиться.']
    text={'share':'Игрок поделился частью пайки во время раздачи.',
          'keep':'Игрок сохранил свою пайку и отдохнул после раздачи.',
          'listen':'Игрок выслушал чужую историю после раздачи.'}[choice]
    ids=w.witnesses() if choice!='keep' else []
    w.event('life_routine',text,ids)
    if choice=='share':
        w.s['food']=max(0,w.s['food']-6)
        for k in ids:bond(w,k,trust=2)
    elif choice=='keep':w.s['stamina']=min(w.s['stamina_max'],w.s['stamina']+5)
    else:
        for k in ids:bond(w,k,trust=1)
    st['routine'].append({'day':w.s['day'],'choice':choice});st['routine']=st['routine'][-30:]
    return [text]

def letter(w,choice):
    """Stage transitions are idempotent, timed by actual days; unrelated v12 mail is untouched."""
    st=state(w);r=st['letters'];d=w.s['day']
    if choice in ('share','quiet','help'):
        if r:return ['Письмо уже прочитано.']
        r.update(start_day=d,choice=choice,stage=1,reply=None,ending=None)
        text=CHOICES[choice][0];ids=['kol'] if choice!='quiet' and 'kol' in w.npcs else []
        w.event('life_letter',text,ids)
        if choice=='share' and 'kol' in w.npcs:bond(w,'kol',trust=4)
        if choice=='help' and 'kol' in w.npcs:bond(w,'kol',trust=5)
        return [text]
    if choice in ('honest','polite','postpone'):
        if r.get('stage')!=1 or d<=r['start_day']:return ['Ответ ещё не готов.']
        r.update(stage=2,reply=choice,middle_day=d)
        text={'honest':'Игрок написал честный ответ, не скрывая трудного дня.',
              'polite':'Игрок ответил коротко, чтобы не тревожить близких.',
              'postpone':'Игрок пока не решился отправить ответ и оставил письмо у себя.'}[choice]
        w.event('life_letter',text,['cenz'] if choice!='postpone' and 'cenz' in w.npcs else [])
        if choice=='honest' and 'cenz' in w.npcs:bond(w,'cenz',trust=2)
        return [text]
    if choice in ('keep_link','support_neighbor','close'):
        if r.get('stage')!=2 or d<=r['middle_day']:return ['Нужен ещё один день.']
        r.update(stage=3,ending=choice,end_day=d)
        outside=st.setdefault('outside',{'contact':0,'skill_days':[],'mutual':0})
        if choice=='keep_link':outside['contact']=1
        if choice=='support_neighbor':outside['mutual']=1
        text={'keep_link':'Игрок решил сохранить связь с домом без обещания скорой встречи.',
              'support_neighbor':'Игрок помог соседу написать письмо, помня о своём доме.',
              'close':'Игрок убрал письмо: пока говорить об этом слишком трудно.'}[choice]
        ids=['kol'] if choice=='support_neighbor' and 'kol' in w.npcs else []
        w.event('life_letter',text,ids)
        if choice=='support_neighbor' and 'kol' in w.npcs:bond(w,'kol',trust=6)
        return [text]
    raise ValueError('Неизвестный выбор письма')

def letter_intro(w):
    r=state(w)['letters'];choice=r.get('choice')
    return {'share':'Сосед помнит, что вы показали письмо. Он не лезет с советами, только молча оставляет место за столом.',
            'quiet':'Письмо всё ещё при вас. Никто не требует рассказывать, что в нём было.',
            'help':'Сосед, которому вы помогли, сам принёс вам чистый лист для ответа.'}.get(choice,'Письмо лежит рядом с чистым листом.')

def letter_end_intro(w):
    r=state(w)['letters'];reply=r.get('reply')
    return {'honest':'Честный ответ отправлен. Вы не знаете, когда он дойдёт и будет ли ответ.',
            'polite':'Короткий ответ отправлен. Сказать главное оказалось труднее всего.',
            'postpone':'Лист остался у вас. Ни письмо, ни молчание не делают выбор за вас.'}.get(reply,'Снова перед вами письмо и тишина.')

def work(w):
    """One useful workday per day, not a guaranteed job on release."""
    days=state(w)['outside']['skill_days']
    if w.s['day'] not in days:days.append(w.s['day']);del days[:-30]

def context(w,k):
    st=state(w);b=st['bonds'].get(k,{'trust':0,'fear':0});r=st['letters'];out={'доверие_по_поступкам':b['trust'],'опасение_по_поступкам':b['fear']}
    # A private letter is NOT public knowledge. Only addressed witnesses see the event.
    if any(e.get('kind')=='life_letter' and k in e.get('witnesses',[]) for e in w.known(k)):
        out['письмо']={'что_известно':'Игрок затронул тему дома; содержание письма и мысли семьи неизвестны.',
                      'выбор_игрока':r.get('choice') if k=='kol' and r.get('choice')!='quiet' else None,'ответ':r.get('reply') if r.get('reply') in ('honest','polite') and k=='cenz' else None}
    return out

def journal(w):
    st=state(w);r=st['letters'];out=[]
    if r:
        out.append('Письмо из дома: '+('связь осмыслена; исход зависит от выбора игрока' if r.get('stage')==3 else
                   'ответ написан; вернитесь в камеру на следующий день' if r.get('stage')==2 else
                   'письмо прочитано; вернитесь в камеру на следующий день'))
    else:out.append('Письмо из дома: история откроется в камере со второго дня.')
    out.append('Распорядок: после ночного сна — новый день, раздача и возможность поделиться или сохранить пайку.')
    if st['routine']:
        names={'share':'поделились','keep':'сохранили пайку','listen':'выслушали человека'}
        out.append('Последний день %d: %s.'%(st['routine'][-1]['day'],names[st['routine'][-1]['choice']]))
    ahead=st['outside'];out.append('После зоны — не обещание освобождения: связь с домом %s; дней полезной работы %d; взаимопомощь %s.'%('сохранена' if ahead['contact'] else 'пока не налажена',len(ahead['skill_days']),'есть' if ahead['mutual'] else 'пока нет'))
    return out
