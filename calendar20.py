"""In-world date, opt-in holidays and inmate birthdays, independent of system clock.

Fixed campaign start makes old saves deterministic. No real-world holiday is treated as
mandatory and no reward is granted merely because the player loaded a save.
"""
from datetime import date,timedelta
import core
START=date(2026,10,25)
HOLIDAYS={
 (10,31):('Хэллоуин','В клубе вырезали бумажные маски. Никого не заставляют надевать их.'),
 (11,4):('День народного единства','В клубе говорят о том, как трудно и важно поддерживать друг друга.'),
 (12,25):('Рождество (25 декабря)','Для тех, кто отмечает эту дату, в клубе оставили тихое место.'),
 (1,1):('Новый год','Столовая выдала тёплый чай. Загадывать желания или нет — личное дело.'),
 (1,7):('Рождество (7 января)','Для тех, кто отмечает эту дату, в клубе оставили тихое место.'),
 (2,23):('23 февраля','Кто-то вспоминает близких и тех, с кем хочет помириться.'),
 (3,8):('8 марта','В мастерской сделали открытки; дарить или не дарить их — выбор каждого.'),
 (5,1):('1 мая','Работники сравнивают планы на свободе, а не нормы выработки.'),
 (5,9):('9 мая','В клубе можно помолчать и вспомнить людей, не требуя одинаковых слов.'),
}
BIRTHDAYS={'cal':(10,29),'zv':(11,2),'steam':(11,11),'zina':(12,3),'prach':(2,15),'cook':(4,7),'buh':(5,20),'graf':(8,18)}

def today(w):return START+timedelta(days=max(0,w.s['day']-1))

def today_events(w):
    d=today(w);out=[]
    if (d.month,d.day) in HOLIDAYS:
        title,text=HOLIDAYS[(d.month,d.day)];out.append(('holiday',title,text))
    for k,md in BIRTHDAYS.items():
        if md==(d.month,d.day) and k in w.npcs:out.append(('birthday',k,'День рождения: '+w.npcs[k]['name']))
    return out

def state(w):return core.C(w).setdefault('calendar20',{'celebrated':[]})

def _mark(w,kind,key):
    d=today(w);return '%d-%02d-%02d:%s:%s'%(d.year,d.month,d.day,kind,key)

def eligible(w,kind,key):
    return any(t==kind and (name==key if kind=='birthday' else name==HOLIDAYS[(today(w).month,today(w).day)][0]) for t,name,_ in today_events(w))

def celebrate(w,kind,key,choice):
    if kind=='holiday':
        if choice not in ('join','observe') or (today(w).month,today(w).day) not in HOLIDAYS or key!=HOLIDAYS[(today(w).month,today(w).day)][0]:raise ValueError('Сегодня такого праздника нет')
    elif kind=='birthday':
        if choice not in ('greet','gift') or key not in BIRTHDAYS or not eligible(w,kind,key):raise ValueError('Сегодня не этот день рождения')
        if w.s['loc']!=w.npcs[key]['home'] or key not in w.witnesses():raise ValueError('Поздравить можно лично в локации именинника')
    else:raise ValueError('Нет такого события')
    stamp=_mark(w,kind,key);r=state(w)
    if stamp in r['celebrated']:return 'Сегодня это уже отмечено.'
    if kind=='birthday' and choice=='gift' and w.s['cig']<1:raise ValueError('Для небольшого подарка нужна 1 сигарета')
    core.advance(w,10)
    r['celebrated'].append(stamp)
    if len(r['celebrated'])>240:r['celebrated']=r['celebrated'][-240:]
    if kind=='holiday':
        if choice=='join':
            import gear20
            gear20.award_box(w)
            text=key+': вы помогли провести вечер. Получен один внутриигровой ящик; откройте его в снаряжении.'
        else:
            w.s['stamina']=min(w.s['stamina_max'],w.s['stamina']+5)
            text=key+': вы просто побыли рядом (+5 сил).'
        w.event('calendar20_holiday','Игрок выбрал участие в празднике «'+key+'»: '+choice+'.',[])
        return text
    if choice=='gift':w.s['cig']-=1
    w.s['relations'][key]=min(100,w.s['relations'].get(key,0)+(5 if choice=='gift' else 2))
    w.event('calendar20_birthday','Игрок лично поздравил '+w.npcs[key]['name']+' с днём рождения'+(' и подарил сигарету.' if choice=='gift' else '.'),[key])
    return 'Вы поздравили '+w.npcs[key]['name']+'. Чужой день рождения не обязан быть общим праздником.'

def collaboration(w,k):
    if k not in ('cal','zv') or k not in w.npcs:raise ValueError('Нет такого совместного дела')
    if w.s['loc']!=w.npcs[k]['home'] or k not in w.witnesses():raise ValueError('Сначала найдите собеседника')
    d=today(w);r=state(w);stamp='%04d-%02d-%02d:collab:%s'%(d.year,d.month,d.day,k)
    if stamp in r['celebrated']:return 'Сегодня вы уже вместе поработали.'
    if k=='cal':
        holiday=HOLIDAYS.get((d.month,d.day))
        if not holiday or _mark(w,'holiday',holiday[0]) not in r['celebrated']:
            raise ValueError('Сначала добровольно отметьте сегодняшний праздник через календарь')
    core.advance(w,20);r['celebrated'].append(stamp)
    import gear20
    if k=='cal':
        gear20.award_box(w);result='Тимофей помог собрать истории дня. Получен один внутриигровой ящик.'
    else:
        gear20.state(w)['scrap']+=1
        result='Зоя показала, как укрепить шов. Получена 1 деталь для улучшений.'
        if not r.get('zoya_first'):
            r['zoya_first']=True;result+=' '+gear20.give(w,'wrap')
    w.event('calendar20_collab','Игрок вместе с '+w.npcs[k]['name']+' поработал над '+('памятными датами.' if k=='cal' else 'починкой вещей.'),[k])
    return result

def notice(w):
    events=today_events(w)
    if not events:return
    r=state(w);stamp=today(w).isoformat()
    if r.get('last_notice')==stamp:return
    r['last_notice']=stamp
    core.C(w)['feed'].append('Календарь: '+', '.join(text for _,_,text in events)+'. Откройте «Календарь» в меню ⋯.')

def context(w,k):
    d=today(w);holiday=HOLIDAYS.get((d.month,d.day))
    return {'дата':'%02d.%02d.%04d'%(d.day,d.month,d.year),
            'праздник_сегодня':holiday[0] if holiday else None,
            'личный_день_рождения':BIRTHDAYS.get(k)==(d.month,d.day)}

def journal(w):
    d=today(w);events=today_events(w)
    return ['Игровая дата: %02d.%02d.%04d. Отсчёт начинается 25.10.2026, не зависит от часов компьютера.'%(d.day,d.month,d.year),
            'Сегодня: '+(', '.join(text for _,_,text in events) or 'обычный день')+'.',
            'Праздники и дни рождения необязательны: откройте «Календарь» в меню действий.']
