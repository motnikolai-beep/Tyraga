"""The duty-list story: local witnesses, an optional rumour, and a recoverable timetable.

Only an explicit player choice changes state. A rumour is hearsay, not a verified theft;
private letters, Shket's note and NPC memory are never used as evidence.
"""
import core

KEY='duty_list22'
# Map scene ids to the actual places and visiting hours. If missed, try again next day.
STAGES={'intro':(1,9*60,17*60),'evidence':(6,8*60,16*60),
        'meeting':(10,16*60,21*60),'final':(1,9*60,17*60)}
NEXT={'intro':'evidence','evidence':'meeting','meeting':'final'}
CHOICES={'intro':('quiet','spread'),'evidence':('inspect','guess'),
         'meeting':('listen','announce'),'final':('correct','conceal','repeat')}

def state(w):
    r=core.C(w).setdefault(KEY,{'stage':'intro','days':{},'choices':{},
                                 'evidence':False,'rumour_id':None,'outcome':None,'pending':[]})
    r.setdefault('pending',[])  # old saves from earlier versions of this optional quest
    return r

def ready(w,stage,branch=None,loc=None):
    r=state(w)
    location=w.s['loc'] if loc is None else loc
    if stage not in STAGES or r['stage']!=stage or location!=STAGES[stage][0]:return False
    if w.s['day']<(3 if stage=='intro' else r['days'].get({'evidence':'intro','meeting':'evidence','final':'meeting'}[stage],10**9)+1):return False
    minute=core.tod(w);_,start,end=STAGES[stage]
    if not start<=minute<end:return False
    if branch is not None and r['evidence']!=branch:return False
    return True

def _rel(w,k,delta):
    w.s['relations'][k]=max(-100,min(100,w.s['relations'].get(k,0)+delta))

def _event(w,kind,text,witnesses):
    witnesses=[k for k in witnesses if k in w.witnesses()]
    return w.event(kind,text,witnesses,public=False)


def _queue(w,e,recipients):
    # Remote contacts learn no sooner than tomorrow. A corrected claim is a
    # new message, never an automatic deletion of the old, disputed rumour.
    state(w)['pending'].append({'day':w.s['day']+1,'id':e['id'],
                                'text':e['text'],'to':list(recipients)})


def morning(w):
    r=state(w);due=[x for x in r['pending'] if x['day']<=w.s['day']]
    r['pending']=[x for x in r['pending'] if x['day']>w.s['day']]
    for x in due:
        for dst in x['to']:
            if dst in w.npcs['zina'].get('contacts',[]) and dst in w.npcs:
                w.gossip('zina',dst,x['text'],x['id'],75,0,'пересказ Зинаиды',[])

def choose(w,stage,option):
    if option not in CHOICES.get(stage,()) or not ready(w,stage):
        raise ValueError('Этот разговор доступен только в указанное время и месте')
    r=state(w)
    if stage=='final' and option=='correct' and not r['evidence']:
        raise ValueError('Нельзя подтвердить то, что вы не проверили')
    r['choices'][stage]=option;r['days'][stage]=w.s['day']
    if stage=='intro':
        _rel(w,'zina',3 if option=='quiet' else 6)
        if option=='spread':
            e=_event(w,'duty22_rumour','Игрок повторил неподтверждённый слух о пропаже из списка дежурств. Это не установленная кража.',w.witnesses())
            r['rumour_id']=e['id'];_queue(w,e,('hleb','cenz','prach'))
        else:_event(w,'duty22_private','Зинаида попросила игрока проверить расхождение в списке дежурств; обвинений пока нет.',['zina'])
    elif stage=='evidence':
        r['evidence']=option=='inspect'
        _rel(w,'zv',7 if r['evidence'] else -2)
        if r['evidence']:
            _event(w,'duty22_fact','Зоя вместе с игроком нашла перепутанные строки в списке дежурств. Доказательств кражи нет.',['zv'])
        else:_event(w,'duty22_uncertain','Игрок ушёл, не сверив список дежурств с Зоей. Факты пока неизвестны.',['zv'])
    elif stage=='meeting':
        _rel(w,'cal',5 if option=='listen' else -2)
        if option=='listen':
            _event(w,'duty22_meeting','Тимофей выслушал игрока без публичных имён и попросил не выдавать догадки за факты.',['cal'])
        else:
            # At the club, only local witnesses hear the announcement. This does not
            # teleport Zina's earlier rumour or disclose a private letter.
            _event(w,'duty22_announcement','Игрок публично предложил обсудить список дежурств; причина расхождения ещё обсуждается.',w.witnesses())
    else:
        r['outcome']=option
        if option=='correct':
            _rel(w,'zina',4)  # Zoya and Timofey are not in the yard to hear this
            e=_event(w,'duty22_correction','Игрок показал Зинаиде проверенную Зоей ошибку в списке. Слух о краже не подтверждён.',w.witnesses())
            if r['rumour_id']:
                heard={g['to'] for g in w.s['gossip'] if g['root']==r['rumour_id']}
                _queue(w,e,sorted(heard))
        elif option=='conceal':
            _rel(w,'zina',-3)
            _event(w,'duty22_silence',('Игрок оставил проверенную ошибку в списке без объяснения.' if r['evidence'] else 'Игрок честно признал Зинаиде, что не проверил список.'),['zina'])
        else:
            _rel(w,'zina',5)  # distant residents cannot react before hearing the rumour
            e=_event(w,'duty22_repeat','Игрок повторил подозрение о списке дежурств, не предъявив подтверждения кражи.',w.witnesses())
            _queue(w,e,('hleb','cenz','prach'))
    r['stage']=NEXT.get(stage,'done')
    core.say(w,'Список дежурств: '+journal(w)[0])
    return []

def journal(w):
    r=state(w);stage=r['stage']
    if stage=='done':
        outcome={'correct':'Ошибка в списке исправлена; прежний слух не исчез сам собой.',
                 'conceal':'Вы оставили вопрос без публичного ответа.',
                 'repeat':'Вы поддержали неподтверждённый слух; он может дойти до других жителей позже.'}
        rows=[outcome[r['outcome']]]
    else:
        loc,start,end=STAGES[stage]
        day=3 if stage=='intro' else r['days'][{'evidence':'intro','meeting':'evidence','final':'meeting'}[stage]]+1
        npc={'intro':'Зинаидой','evidence':'Зоей','meeting':'Тимофеем','final':'Зинаидой'}[stage]
        rows=['С дня %d поговорите с %s в локации «%s» с %02d:00 до %02d:00. Если не успели, приходите в другой день.'%
              (day,npc,core.NAMES[loc],start//60,end//60)]
    if r['rumour_id']:
        heard=len({g['to'] for g in w.s['gossip'] if g['root']==r['rumour_id']})
        rows.append('Неподтверждённый слух: %s'%('дошёл до %d знакомых Зинаиды; пересказ не доказательство.'%heard if heard else 'пока не покинул двор.'))
    return rows

def context(w,k):
    r=state(w);done=r['choices']
    if k=='zina' and 'intro' in done:
        return {'знает_о_несоответствии':True,'проверена_ошибка_в_записи':r['outcome']=='correct'}
    if k=='zv' and 'evidence' in done:
        return {'лично_сверила_список':r['evidence']}
    if k=='cal' and 'meeting' in done:
        return {'встреча':done['meeting']}
    return {}
