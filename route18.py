"""Optional follow-through on a promise made to Shket; not a sister's reply.

Only explicit decisions create facts. An anonymous procedural question does not reveal
Shket's name to the censor. The player cannot submit mail in Shket's name.
"""
import core

KEY='route18'

def state(w):
    return core.C(w).setdefault(KEY,{'route':None,'told':False,'offered':False})

def eligible(w):
    c=core.C(w)
    return 'note17_after' in c['done'] and bool(c['flags'].get('note17_promise')) and __import__('note17').state(w).get('given_day') is not None

def inquire(w,choice):
    if choice not in ('anonymous','open'):raise ValueError('Нет такого вопроса')
    if not eligible(w) or w.s['loc']!=7 or 'cenz' not in w.witnesses():raise ValueError('Сначала поговорите со Шкетом после передачи записки; расспросить о почте можно в библиотеке')
    r=state(w)
    if r['route'] is not None:return 'Вы уже выяснили, куда отнести запрос.'
    core.advance(w,15);r['route']=choice
    if choice=='open':
        w.event('route18_open','Игрок прямо спросил Цензора о процедуре для Шкета. Ответа от сестры ещё нет.',['cenz'])
        w.s['relations']['cenz']=max(-100,w.s['relations'].get('cenz',0)-2)
        return 'Цензор услышал имя Шкета. Нужны его собственные слова и адрес, если он его узнает; ответа от сестры нет.'
    w.event('route18_anonymous','Игрок узнал порядок подачи письма, не назвав адресата и не показывая записку.',[])
    return 'Цензор объяснил порядок: нужен адрес и письмо самого отправителя. Вы не назвали Шкета и не показывали записку.'

def tell(w,choice):
    if choice not in ('explain','offer'):raise ValueError('Нет такого решения')
    r=state(w)
    if not eligible(w) or r['route'] is None or w.s['loc']!=0 or 'kol' not in w.witnesses():
        raise ValueError('Сначала выясните порядок почты в библиотеке, затем поговорите со Шкетом в камере')
    if r['told']:
        if choice=='explain' or r['offered']:return 'Шкет уже знает, как подать запрос; письмо за него вы не отправляли.'
    core.advance(w,10)
    if not r['told']:
        r['told']=True
        w.s['relations']['kol']=min(100,w.s['relations'].get('kol',0)+3)
    if choice=='offer' and not r['offered']:
        r['offered']=True
        w.s['relations']['kol']=min(100,w.s['relations'].get('kol',0)+2)
        import life15
        life15.bond(w,'kol',trust=2)
    w.event('route18_tell','Игрок объяснил Шкету порядок почты'+(' и предложил чистый лист; отправлять ли запрос, решит сам Шкет.' if choice=='offer' else '; отправлять ли запрос, решит сам Шкет.'),['kol'])
    return 'Шкет '+('взял чистый лист, но не стал писать при вас.' if choice=='offer' else 'выслушал и решил подумать сам.')+' Ни адреса, ни ответа от сестры пока нет.'

def context(w,k):
    if not eligible(w):return {}
    r=state(w)
    if k=='kol' and r['told']:
        return {'известно':'Порядок подачи письма: нужен адрес и собственные слова Шкета. Ответа от сестры нет.',
                'предложен_чистый_лист':r['offered']}
    if k=='cenz' and r['route']=='open':
        return {'известно':'Игрок назвал Шкета, спрашивая о порядке подачи письма; содержание чужой записки неизвестно.'}
    return {}

def journal(w):
    if not eligible(w):return []
    r=state(w)
    if r['route'] is None:return ['Вы предложили Шкету помощь: в библиотеке можно спросить Цензора о порядке подачи письма, не показывая записку.']
    if not r['told']:return ['Порядок почты выяснен. Вернитесь к Шкету в камеру; решите, рассказывать ли ему об этом.']
    return ['Шкет знает порядок почты'+(' и получил чистый лист' if r['offered'] else '')+'. Отправлять запрос или нет — его выбор. Ответа сестры пока нет.']
