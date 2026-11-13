"""Optional aftermath of the duty-list rumour, with no knowledge at a distance.

Zoya and Timofey only learn what the player tells them in person. A later correction
travels by the existing gossip network; it never erases the original claim.
"""
import core
import thread22

KEY='after_list23'
STAGES={'zoya':(6,8*60,16*60),'tim':(10,16*60,21*60),'zina':(1,9*60,17*60)}
PREVIOUS={'zoya':'final','tim':'zoya','zina':'tim'}
NEXT={'zoya':'tim','tim':'zina','zina':'done'}
OPTIONS={'zoya':('check','step_back'),'tim':('tell','listen','uncertain'),
         'zina':('correct','hold','retract')}

def state(w):
    return core.C(w).setdefault(KEY,{'stage':'zoya','days':{},'choices':{},'fact':False,
                                     'told_tim':False,'outcome':None})

def ready(w,stage,branch=None,loc=None):
    r=state(w);previous=thread22.state(w)
    if previous['stage']!='done' or stage not in STAGES or r['stage']!=stage:return False
    if stage=='zoya' and not r['choices'] and previous['evidence']:
        r['fact']=True  # a verified record does not become unknown after a quiet visit
    place,start,end=STAGES[stage]
    if (w.s['loc'] if loc is None else loc)!=place:return False
    prior=previous['days'].get('final') if stage=='zoya' else r['days'].get(PREVIOUS[stage])
    if prior is None or w.s['day']<prior+1 or not start<=core.tod(w)<end:return False
    known=previous['evidence'] if stage=='zoya' else r['fact']
    if branch is not None and branch!=('fact' if known else 'uncertain'):return False
    return True

def _rel(w,k,delta):
    w.s['relations'][k]=max(-100,min(100,w.s['relations'].get(k,0)+delta))

def _local(w,kind,text,k):
    # No global public event: only the person physically in the room learns it.
    return w.event(kind,text,[k] if k in w.witnesses() else [],public=False)

def choose(w,stage,option):
    if option not in OPTIONS.get(stage,()) or not ready(w,stage):
        raise ValueError('Эта глава доступна лишь на встрече в указанное время')
    r=state(w)
    if stage=='tim' and option=='tell' and not r['fact']:raise ValueError('Сначала проверьте запись')
    if stage=='tim' and option=='uncertain' and r['fact']:raise ValueError('Вы уже сверили запись')
    if stage=='zina' and option=='correct' and not r['fact']:raise ValueError('Нет подтверждённой записи')
    if stage=='zina' and option=='retract' and r['fact']:raise ValueError('Запись уже сверена')
    r['choices'][stage]=option;r['days'][stage]=w.s['day']
    if stage=='zoya':
        if option=='check':
            r['fact']=True;_rel(w,'zv',6)
            _local(w,'after23_checked','Зоя вместе с игроком ещё раз сверила ведомость. Перепутаны строки; кража не доказана.','zv')
        else:
            _rel(w,'zv',-2)
            _local(w,'after23_declined','Игрок отказался снова разбирать ведомость с Зоей.','zv')
    elif stage=='tim':
        if option=='tell':
            r['told_tim']=True;_rel(w,'cal',5)
            _local(w,'after23_told','Игрок лично рассказал Тимофею о проверенной с Зоей ошибке в ведомости.','cal')
        elif option=='listen':
            _rel(w,'cal',3)
            _local(w,'after23_listen','Тимофей предложил игроку дать людям сказать самим за себя, не повторяя слух.','cal')
        else:
            _local(w,'after23_uncertain','Игрок честно сказал Тимофею, что не проверил ведомость.','cal')
    else:
        r['outcome']=option
        if option=='correct':
            _rel(w,'zina',5)
            e=_local(w,'after23_correct','Игрок показал Зинаиде запись, проверенную вместе с Зоей. Ошибка подтверждена, кража — нет.','zina')
            # Only contacts who received Zina's earlier rumour can receive this correction.
            rumours={x['id'] for x in w.s['events'] if x['kind'] in ('duty22_rumour','duty22_repeat')}
            heard={g['to'] for g in w.s['gossip'] if g['root'] in rumours}
            if heard:thread22._queue(w,e,sorted(heard))
        elif option=='retract':
            _rel(w,'zina',2)
            _local(w,'after23_retract','Игрок отозвал своё подозрение перед Зинаидой: проверить запись он не смог.','zina')
        else:
            _rel(w,'zina',-2)
            _local(w,'after23_hold','Игрок решил не возвращаться к публичному разговору о ведомости.','zina')
    r['stage']=NEXT[stage]
    core.say(w,'После слуха: '+journal(w)[0])
    return []

def journal(w):
    prev=thread22.state(w);r=state(w)
    if prev['stage']!='done':return ['Сначала завершите историю «Чужая строка».']
    if r['stage']=='done':
        return [{'correct':'Вы показали Зинаиде проверенную запись. Старый слух не исчез мгновенно.',
                 'retract':'Вы честно отозвали подозрение, не притворяясь, будто проверили ведомость.',
                 'hold':'Вы оставили разговор без продолжения.'}[r['outcome']]]
    stage=r['stage'];loc,start,end=STAGES[stage]
    day=(prev['days']['final'] if stage=='zoya' else r['days'][PREVIOUS[stage]])+1
    who={'zoya':'Зоей','tim':'Тимофеем','zina':'Зинаидой'}[stage]
    return ['С дня %d поговорите с %s в локации «%s» с %02d:00 до %02d:00; пропущенная встреча доступна позже.'%
            (day,who,core.NAMES[loc],start//60,end//60)]

def context(w,k):
    r=state(w);choices=r['choices']
    if k=='zv' and 'zoya' in choices:return {'лично_сверила_ведомость':choices['zoya']=='check'}
    if k=='cal' and 'tim' in choices:return {'лично_обсудил':choices['tim']}
    if k=='zina' and 'zina' in choices:return {'ответ_игрока':r['outcome']}
    return {}
