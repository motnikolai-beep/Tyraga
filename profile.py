"""Player's personal file. Fictional backstories, saved with each game; no gameplay advantage.

A legacy save without an origin shows 'not specified' rather than inventing one.
Nickname is derived from actions/status, never stored as a stale string.
"""
import core

ORIGINS={
 'paper':('Подделка талонов', 'Три года', 'Подделал пропуска в столовую: очередь стала короче, но начальство сочло это преступлением.'),
 'cat':('Оскорбление начальственного кота', 'Два года', 'Сказал, что кот Решёткина перекормлен. Протокол занял семь страниц.'),
 'escape':('Побег из цирка', 'Четыре года', 'Помог цирковым мышам сбежать из клетки; дело назвали организованной группой.'),
}

def origin(w):
    key=w.s.get('profile',{}).get('origin')
    return ORIGINS.get(key,('Дело не указано','Срок не указан','Старое сохранение: прошлое героя не задано.'))

def nickname(w):
    c=core.C(w);flags=c['flags']
    if len(c['ousted'])>=12:return 'Свергатель'
    if flags.get('framed_kol') or flags.get('snitch'):return 'Доносчик'
    if c['counters'].get('ex_peace',0)>=2:return 'Миротворец'
    if c['counters'].get('duel_win',0)>=5:return 'Кулак'
    if c['counters'].get('letter',0)>=3:return 'Письмо'
    if core.tier(w)[0]=='Пахан':return 'Пахан'
    return 'Новенький'

def ai_context(w):
    case,term,story=origin(w)
    return {'погоняло':nickname(w),'дело':case,'срок':term,'прошлое':story}

def report(w):
    """Plain text for the personal-file UI, testable without Tk or an LLM."""
    s=w.s;c=core.C(w);case,term,story=origin(w)
    items=['%s ×%d'%(core.ITEMS.get(k,k),v) for k,v in c['inv'].items() if v>0]
    relation=[]
    for k,n in w.npcs.items():
        val=s['relations'].get(k,0)
        status=' · бывший' if core.is_former(w,k) else ''
        relation.append('%s: %+d%s'%(n['name'],val,status))
    rel=sorted(relation)
    return ('ПОГОНЯЛО: %s\nДЕЛО: %s · %s\n%s\n\n'
            'ДЕНЬ %d  ·  %s  ·  СТАТУС: %s (%+d)\n'
            'ЗДОРОВЬЕ %d/100  ·  СИЛЫ %d/%d  ·  СЫТОСТЬ %d/100\n'
            'МУДРОСТЬ %d  ·  ХАРИЗМА %d\n'
            'КАРМА: сочувствие %+d · честь %+d · хитрость %+d\n'
            'РЕСУРСЫ: сигареты %d · ₽ %d\n'
            'ОРУЖИЕ: %s · броня %d\n'
            'ВЕЩИ: %s\n\nОТНОШЕНИЯ В ЗОНЕ\n%s')%(
            nickname(w),case,term,story,s['day'],core.hhmm(w),core.tier(w)[0],c['caste'],
            s['hp'],s['stamina'],s['stamina_max'],s['food'],c['wis'],c['cha'],
            s['karma']['empathy'],s['karma']['honor'],s['karma']['cunning'],
            s['cig'],s['rub'],s['gear']['weapon'],s['gear']['armor'],
            ', '.join(items) or 'пусто','\n'.join(rel))
