"""Visible consequences of witnessed facts and hearsay, without revealing private mail.

The dossier only covers deliberately whitelisted public-facing interactions. It never
reads a private conversation, a hidden stash, Shket's note, or letters. A reported fact
remains *hearsay* to its recipient even when the underlying event was verified.
"""
import core

# Text is written for the player, not taken from unchecked AI/chat/gossip payloads.
TOPICS={
 'duty22_private':'расхождение в списке дежурств',
 'duty22_rumour':'неподтверждённое подозрение о ведомости',
 'duty22_repeat':'повторённое подозрение о ведомости',
 'duty22_fact':'проверка ведомости: ошибка в строках, не доказательство кражи',
 'duty22_uncertain':'разговор о непроверенной ведомости',
 'duty22_meeting':'разговор о ведомости без обвинений',
 'duty22_announcement':'открытое обсуждение ведомости',
 'duty22_correction':'поправка к подозрению после проверки',
 'duty22_silence':'незавершённый разговор о ведомости',
 'after23_checked':'повторная проверка ведомости',
 'after23_declined':'отказ от повторной проверки',
 'after23_told':'рассказ Тимофею о проверенной записи',
 'after23_listen':'тихий разговор с Тимофеем',
 'after23_uncertain':'признание, что запись не проверена',
 'after23_correct':'проверенная поправка к подозрению',
 'after23_retract':'отзыв неподтверждённого подозрения',
 'after23_hold':'разговор о ведомости оставлен без продолжения',
 'help':'помощь соседу',
 'theft':'кража в локации',
 'betrayal':'донос охране',
}
KEY='reactions24'

def state(w):
    return core.C(w).setdefault(KEY,{'seen':{}})

def knowledge(w,k):
    """Only events the NPC witnessed/publicly knows, or actual delivered gossip."""
    if k not in w.npcs:return []
    events={e['id']:e for e in w.s['events'] if e.get('id') and e.get('kind') in TOPICS}
    facts={e['id'] for e in w.s['knowledge'].get(k,[]) if e.get('id') in events and k in e.get('witnesses',[])}
    heard={g['root']:g for g in w.s['gossip'] if g.get('to')==k and g.get('root') in events}
    out=[]
    for event in events.values():
        root=event['id']
        if root not in facts and root not in heard:continue
        g=heard.get(root)
        out.append({'id':root,'kind':event['kind'],'topic':TOPICS[event['kind']],
                    'day':event.get('day',0),'source':'видел сам' if root in facts else 'слышал пересказ',
                    'firsthand':root in facts,'disputed':bool(g and g.get('disputed')) if root not in facts else False})
    return out

def offer(w,k):
    """Most recent unaddressed event. Only a physically present resident may react."""
    if k not in w.witnesses():return None
    seen=set(state(w)['seen'].get(k,[]))
    return next((e for e in reversed(knowledge(w,k)) if e['id'] not in seen),None)

def prompt(w,k,item):
    if not item or item['id'] not in {e['id'] for e in knowledge(w,k)}:raise ValueError('Нет события для разговора')
    name=w.npcs[k]['name'];topic=item['topic']
    if item['firsthand']:
        return '%s помнит, что лично видел: %s. «Я был рядом. Хочу услышать, что ты сам об этом скажешь». '%(name,topic)
    return '%s говорит: «Мне пересказали про %s. Я при этом не был и не стану выдавать чужие слова за доказательство». '%(name,topic)

def respond(w,k,event_id,choice):
    item=offer(w,k)
    if item is None or item['id']!=event_id or choice not in ('listen','clarify','leave'):
        raise ValueError('Этот разговор уже состоялся или житель не рядом')
    # A reaction is opt-in and once per resident/event, not a daily relationship farm.
    delta={'listen':2,'clarify':1,'leave':-1}[choice]
    old=w.s['relations'].get(k,0);w.s['relations'][k]=max(-100,min(100,old+delta))
    state(w)['seen'].setdefault(k,[]).append(event_id)
    core.advance(w,5)
    endings={
        'listen':'Вы выслушали ответ и не стали додумывать за собеседника.',
        'clarify':'Вы отделили то, что житель видел сам, от того, что ему только пересказали.',
        'leave':'Вы оборвали разговор. Невысказанное осталось между вами.'}
    w.event('reaction24','Игрок обсудил событие с '+w.npcs[k]['name']+'; источник: '+item['source']+'.',[k])
    return prompt(w,k,item)+endings[choice]

def rows(w):
    out=['Сводка основана на событиях и доставленных пересказах игры. «Слышал пересказ» не означает «знает правду». Содержание личных писем и тайников здесь не показывается.']
    for k in w.npcs:
        info=knowledge(w,k)
        if not info:
            out.append(w.npcs[k]['name']+': нет подтверждённых свидетельств или доставленных пересказов из этой сводки.')
            continue
        out.append(w.npcs[k]['name']+':')
        for e in info[-4:]:
            suffix=' · оспаривает пересказ' if e['disputed'] else ''
            out.append('  День %d · %s · %s%s'%(e['day'],e['source'],e['topic'],suffix))
    return out

def report(w):return '\n'.join(rows(w))
