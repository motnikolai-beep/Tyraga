"""Daily NPC-to-NPC news independent of player dialogue, AI runtime or current location.

An event is a witnessed fact only for people in that room. Contacts elsewhere receive a
rumor with source/confidence; other NPCs are NOT globally told it happened. The player
sees the prison grapevine as a journal headline, not as a verified fact about the player.
"""
import core

# Actor pairs live in the same room; two variants per pair avoid a fixed daily script.
NEWS=(
 ('zub','kol',('Байкал заметил, что Шкет тайком кормит мышь, и пригрозил отобрать пайку.',-6),('Байкал поделился с Шкетом чифиром после тяжёлого дня.',6)),
 ('polkan','zina',('Полкан прогнал Зинаиду с лавки за торговлю во время построения.',-7),('Зинаида обменяла семечки на старый свисток Полкана; оба остались довольны.',5)),
 ('hleb','serg',('Хлеборез спорил с Бачком из-за веса пайки; очередь слышала их ругань.',-7),('Хлеборез уступил Бачку лишний ломоть хлеба для вечерней раздачи.',5)),
 ('kip','steam',('Кипяток и Сократ поссорились из-за вентиля горячей воды.',-6),('Сократ помог Кипятку починить протекающий вентиль.',6)),
 ('str','prach',('Цепи обвинил Кулибина в недостаче гайки; оба обыскали склад.',-5),('Кулибин помог Цепи пересчитать ящики; недостача оказалась ошибкой.',7)),
 ('cenz','buh',('Цензор задержал письмо Бумажкиной из-за помарки; она потребовала расписку.',-6),('Бумажкина нашла Цензору чистую бумагу для стихов.',6)),
)

def morning(w):
    c=core.C(w);d=w.s['day']
    if c['news_day']==d:return None
    c['news_day']=d
    a,b,*variants=NEWS[(d-2)%len(NEWS)]
    if a not in w.npcs or b not in w.npcs:return None
    text,delta=variants[w.rng.randrange(len(variants))]
    loc=w.npcs[a]['home']
    witnesses=[k for k,n in w.npcs.items() if n['home']==loc]
    e=w.event('zone_news',text,witnesses,public=False)
    # Prisoners' relationships with each other, separate from their opinion of the player.
    rel=c['npc_relations'];key=':'.join(sorted((a,b)))
    rel[key]=max(-100,min(100,rel.get(key,0)+delta))
    for src in (a,b):
        for dst in w.npcs[src].get('contacts',[]):
            if dst in w.npcs and dst not in witnesses:
                w.gossip(src,dst,text,e['id'],75,0,'новости из '+w.npcs[src]['name'],[])
    c['news'].append({'day':d,'id':e['id'],'text':text,'actors':[a,b],'location':loc})
    c['news']=c['news'][-15:]
    core.say(w,'Новости зоны: '+text)
    return e

def journal(w):
    rows=['День %d · %s'%(row['day'],row['text']) for row in reversed(core.C(w)['news'][-7:])]
    return rows or ['Пока новостей нет. Они появляются утром, даже если игрок ни с кем не говорил.']

def npc_relations(w,k):
    """The NPC's own relationship to known acquaintances, as context rather than player reputation."""
    rel=core.C(w)['npc_relations']
    return {w.npcs[other]['name']:rel.get(':'.join(sorted((k,other))),0)
            for other in w.npcs[k].get('contacts',[]) if other in w.npcs and ':'.join(sorted((k,other))) in rel}
