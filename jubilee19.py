"""Optional preparation for a fictional twentieth-anniversary evening in the prison club.

This is a v19 foundation for the v20 event, not a claim about the real project's age.
No NPC is conscripted: an invitation records only a willingness to discuss a role.
"""
import core

GUESTS={'kol':'Шкет','steam':'Сократ','cenz':'Цензор'}
THEMES={
 'voices':('голоса жителей','Здесь будет место для рассказов жителей, если они сами захотят говорить.'),
 'records':('двадцать строк истории','Замысел — двадцать коротких строк о зоне: не все из них должны быть официальными.'),
 'quiet':('тихий вечер','Вы предложили спокойный вечер без обязательных речей и показательных выступлений.'),
}

def state(w):
    return core.C(w).setdefault('jubilee19',{'theme':None,'planned_day':None,'invited':[],'rehearsed':False})

def plan(w,theme):
    if theme not in THEMES:raise ValueError('Нет такого варианта вечера')
    if w.s['loc']!=10:raise ValueError('Подготовка ведётся у сцены клуба')
    r=state(w)
    if r['theme'] is not None:return 'План уже выбран; изменить его можно будет только на отдельном собрании.'
    core.advance(w,20)
    r.update(theme=theme,planned_day=w.s['day'])
    # This is the player's own proposal, not a public announcement or NPC consent.
    w.event('jubilee19_plan','Игрок набросал частный план юбилейного вечера: '+THEMES[theme][0]+'.',[])
    return THEMES[theme][1]+' В журнале записан план, но никого ещё не приглашали.'

def invite(w,k):
    if k not in GUESTS:raise ValueError('Неизвестный собеседник')
    r=state(w)
    if r['theme'] is None:raise ValueError('Сначала выберите замысел вечера у сцены в клубе')
    if k not in w.witnesses():raise ValueError('Поговорите с человеком в его локации')
    if k in r['invited']:return GUESTS[k]+' уже слышал приглашение.'
    core.advance(w,10)
    r['invited'].append(k)
    # Only the addressee hears an invitation. Earlier private quests stay private.
    w.event('jubilee19_invite','Игрок спросил '+GUESTS[k]+', интересно ли тому обсудить участие в юбилейном вечере; тот согласился подумать.',[k])
    return GUESTS[k]+' согласился обсудить участие, но не обещал выступить.'

def ready(w):
    r=state(w)
    return r['theme'] is not None and len(r['invited'])>=2 and w.s['day']>r['planned_day'] and not r['rehearsed']

def rehearse(w):
    r=state(w)
    if w.s['loc']!=10:raise ValueError('Осмотреть площадку можно только у сцены клуба')
    if r['theme'] is None:raise ValueError('Сначала предложите замысел вечера')
    if len(r['invited'])<2:raise ValueError('Сначала поговорите хотя бы с двумя жителями о возможном участии')
    if w.s['day']<=r['planned_day']:raise ValueError('Дайте людям подумать до следующего дня')
    if r['rehearsed']:return 'Площадка уже проверена. Сам вечер ещё впереди.'
    core.advance(w,30)
    r['rehearsed']=True
    w.event('jubilee19_rehearsal','Игрок проверил свет и проход у сцены для предстоящего юбилейного вечера; участники не назначены.',[])
    return 'Свет и проход проверены. Приглашённые сами решат, участвовать ли; юбилейный вечер ещё не состоялся.'

def context(w,k):
    r=state(w)
    if k not in r['invited']:return {}
    return {'событие':'Игрок спросил об участии в будущем юбилейном вечере в клубе.',
            'ответ':'Согласился обсудить, не обещал выступить.',
            'тема':THEMES[r['theme']][0] if r['theme'] else None,
            'прошёл_ли_вечер':__import__('jubilee20').state(w)['held']}

def journal(w):
    r=state(w)
    if r['theme'] is None:return ['В клубе есть сцена: можно предложить подготовку к вымышленному двадцатилетнему юбилею зоны. Это необязательно.']
    who=', '.join(GUESTS[k] for k in r['invited']) or 'никого'
    out=['Замысел: '+THEMES[r['theme']][0]+'. Приглашены обсудить участие: '+who+'.']
    if r['rehearsed']:out.append('Свет и проход у сцены проверены. '+('Вечер уже состоялся.' if __import__('jubilee20').state(w)['held'] else 'Сам вечер ещё не состоялся.'))
    elif len(r['invited'])<2:out.append('Поговорите хотя бы с двумя жителями в их локациях; это приглашение, не принуждение.')
    elif w.s['day']<=r['planned_day']:out.append('Вернитесь к сцене на следующий день: приглашённым нужно время подумать.')
    else:out.append('Вернитесь к сцене в клубе, чтобы проверить площадку.')
    return out
