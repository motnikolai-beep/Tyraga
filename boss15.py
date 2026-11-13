"""Human reasons behind all twelve rulers. Traits are not rewards or objective truths.

Only a boss gets their own private motive in the LLM prompt. Other NPCs see local facts,
public falls and their own known contacts; no remote mind-reading or spoilers.
"""
import core

# (need, fear, life after losing power). Independent from the existing public role and
# former.py's mechanical revenge/peace flags: a grudge does not erase the person.
MOTIVES={
 'zub':('Боишься, что без привычных правил камера развалится и пострадает Шкет. Контроль заменяет тебе доверие.','Остаться одному без уважения.','Учишься помогать без приказа; вначале получается неловко.'),
 'graf':('Долги и тренировки дают тебе чувство, что ты всё ещё нужен другим.','Оказаться никому не нужным, когда долги закроют.','Снова тренируешь людей, но без права требовать плату за внимание.'),
 'gvo':('Режим кажется тебе единственным способом уберечь людей и кошек от хаоса.','Признать, что твой порядок тоже причинял боль.','Учишься слушать жалобу до конца, не записывая её как нарушение.'),
 'str':('Учёт и подписи защищают тебя от обвинения в недостаче.','Потерять работу из-за одной чужой ошибки.','Чинишь вещи без ведомости; рука всё ещё ищет графу для подписи.'),
 'sm':('Тишина в проходе — твой способ удержать память о тех, кто не вернулся.','Что скрытые ходы станут чужой добычей.','Показываешь безопасный путь лишь тем, кому действительно доверяешь.'),
 'gen':('Проверка — твой первый шанс доказать начальству, что тебе можно доверить решение.','Ошибиться публично и подвести тех, кого проверяешь.','Учишься спрашивать, а не только сверять с приказом.'),
 'mat':('Хочешь, чтобы о слабых и о кошках кто-то заботился, даже если приходится говорить жёстко.','Остаться без тех, за кого отвечаешь.','Помогаешь без необходимости решать за другого.'),
 'cook':('Роль лекаря давала тебе право выслушивать людей, которых иначе не слушали.','Что без халата никто не придёт поговорить.','Продолжаешь слушать без обещаний исцелить всех.'),
 'polkan':('Строй и свисток напоминают тебе, что хотя бы двор можно удержать в порядке.','Что без команды никто не заметит твоего присутствия.','Учишься делить двор с другими и гулять с Мухтаром без строя.'),
 'hleb':('Контроль над хлебом — твой способ не оказаться первым в пустой очереди.','Снова остаться голодным и зависеть от чужой милости.','Пробуешь отрезать ровно, хотя рука по привычке тянется к весам.'),
 'kip':('Горячая вода была редкой вещью, которой ты мог распоряжаться сам.','Остаться невидимым, когда вентиль станет общим.','Помогаешь чинить душевую, а не решать, кому мыться.'),
 'cenz':('Чужие письма позволяют тебе выбирать слова, которых ты боишься в собственных стихах.','Что кто-то прочитает твои стихи и высмеет тебя.','Пишешь свои строки открыто и стараешься не вымарывать чужие.'),
}

def context(w,k):
    """Bounded, perspective-aware prompt data; names and statuses from the save, not prophecy."""
    if k not in w.npcs:return {}
    n=w.npcs[k];c=core.C(w);out={}
    if k in MOTIVES:
        need,fear,after=MOTIVES[k]
        out['личный_мотив']=need;out['личный_страх']=fear
        out['сейчас']='у власти' if core.in_power(w,k) else 'после потери власти'
        if core.is_former(w,k):out['возможный_путь']=after
    # Contact values refer to a relationship between two residents, not their opinion of player.
    rel=c['npc_relations']
    ties=[]
    for other in n.get('contacts',[]):
        key=':'.join(sorted((k,other)))
        if other in w.npcs and key in rel:
            ties.append({'имя':w.npcs[other]['name'],'отношение':rel[key]})
    if ties:out['знакомые']=ties[:5]
    if k in MOTIVES and core.is_former(w,k):
        ex=c['ex'].get(k,{})
        out['память_о_падении']={'примирились':bool(ex.get('peace')),'обида':bool(ex.get('mock')),'претензия_на_реванш':ex.get('revenge') in ('due','fight')}
    return out

def journal(w):
    """Only people whom the player has met; no omniscient biography board."""
    c=core.C(w);rows=[]
    for k in MOTIVES:
        if k not in w.npcs:continue
        met=k in c['weak'] or k in c['ousted'] or bool(w.s.get('history',{}).get(k)) or w.s['loc']==w.npcs[k]['home']
        # A scripted encounter also counts as meeting; avoid leaking motives for unseen rooms.
        met=met or any(sid in c['done'] for sid in ('p12_'+k,'ex_'+k))
        if not met:continue
        status='у власти' if core.in_power(w,k) else 'бывший хозяин'
        text=MOTIVES[k][0] if core.in_power(w,k) else MOTIVES[k][2]
        ties=context(w,k).get('знакомые',[])
        if ties:text+=' Связь: '+', '.join(x['имя']+' (%+d)'%x['отношение'] for x in ties[:2])+'.'
        import life15
        bond=life15.state(w)['bonds'].get(k)
        if bond:text+=' Ваши поступки: доверие %+d, опасение %d.'%(bond['trust'],bond['fear'])
        rows.append(w.npcs[k]['name']+' · '+status+': '+text)
    return rows or ['Познакомьтесь с хозяевами мест: на карте они отмечены золотом. Их причины станут яснее в разговоре.']
