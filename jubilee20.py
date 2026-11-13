"""Opt-in v20 finale of the fictional in-world anniversary preparations."""
import core,jubilee19

LINES=(
    '1. У ворот всегда слышен первый замок.',
    '2. В камере легко считать чужие шаги.',
    '3. Имя важнее номера койки.',
    '4. Пайка не становится больше от громких слов.',
    '5. У воды есть очередь.',
    '6. В мастерской чинят не только ткань.',
    '7. Чужое письмо не стоит читать вслух.',
    '8. Отказ тоже бывает честным ответом.',
    '9. Дежурный помнит смены, люди — помощь.',
    '10. На сцене можно молчать.',
    '11. Ни один авторитет не владеет будущим.',
    '12. Работу можно делать без показной награды.',
    '13. Никто не обязан праздновать по команде.',
    '14. Памятная дата не возвращает потерянное.',
    '15. Но иногда помогает найти слова.',
    '16. Ключ не всегда открывает дверь.',
    '17. Сосед может попросить время подумать.',
    '18. Дорога после ворот ещё не пройдена.',
    '19. В черновике есть место для поправки.',
    '20. Последнюю строку каждый пишет сам.',
)

def state(w):return core.C(w).setdefault('jubilee20',{'decisions':{},'held':False})

def consent(w,k,yes):
    if type(yes) is not bool or k not in jubilee19.GUESTS:raise ValueError('Нет такого выбора')
    prep=jubilee19.state(w);r=state(w)
    if not prep['rehearsed'] or k not in prep['invited'] or w.s['loc']!=w.npcs[k]['home'] or k not in w.witnesses():raise ValueError('Сначала пригласите жителя и подготовьте площадку')
    if r['held']:raise ValueError('Вечер уже прошёл')
    if k in r['decisions']:return 'Этот человек уже принял решение.'
    core.advance(w,10);r['decisions'][k]=yes
    w.event('jubilee20_consent',w.npcs[k]['name']+(' добровольно согласился участвовать в вечере.' if yes else ' отказался участвовать; его решение уважено.'),[k])
    return w.npcs[k]['name']+(' согласился участвовать.' if yes else ' решил не участвовать. Его место останется свободным.')

def host(w):
    p=jubilee19.state(w);r=state(w)
    if w.s['loc']!=10 or not p['rehearsed']:raise ValueError('Для вечера нужно добровольно подготовить сцену в клубе')
    if r['held']:return 'Юбилейный вечер уже состоялся.'
    if any(k not in r['decisions'] for k in p['invited']):raise ValueError('Сначала спросите каждого приглашённого, хочет ли он участвовать')
    core.advance(w,40);r['held']=True;r['theme']=p['theme'];r['participants']=[k for k in p['invited'] if r['decisions'][k]]
    lines={'voices':'Звучат истории только тех, кто сам вызвался говорить.',
           'records':'Вы читаете двадцать коротких строк из черновика истории зоны. Пропуски в нём честнее официального отчёта.',
           'quiet':'В зале можно просто посидеть рядом без обязательных речей.'}
    text=lines[p['theme']]+' '+('Согласились участвовать: '+', '.join(w.npcs[k]['name'] for k in r['participants'])+'.' if r['participants'] else 'Остальные предпочли не выходить на сцену; вы ведёте вечер сами.')
    if p['theme']=='records':text+='\n\n'+'\n'.join(LINES)
    import gear20
    gear20.award_box(w)
    w.event('jubilee20_evening','Состоялся вымышленный юбилейный вечер зоны: '+jubilee19.THEMES[p['theme']][0]+'.',w.witnesses(),public=True)
    return text+' В благодарность за подготовку получен один внутриигровой ящик.'

def context(w,k):
    r=state(w)
    if k in r['decisions']:
        return {'приглашение_принято':r['decisions'][k], 'вечер_состоялся':r['held'],
                'выступал':r['held'] and k in r.get('participants',[])}
    if r['held']:return {'вечер_состоялся':True,'выступал':False}
    return {}

def journal(w):
    p=jubilee19.state(w);r=state(w)
    if not p['rehearsed']:return []
    if r['held']:return ['Юбилейный вечер состоялся: '+jubilee19.THEMES[r['theme']][0]+'. Участие было добровольным.']
    undecided=[w.npcs[k]['name'] for k in p['invited'] if k not in r['decisions']]
    return ['Сцена готова. '+('Спросите приглашённых об участии: '+', '.join(undecided)+'.' if undecided else 'Решения получены; можно провести вечер у сцены клуба или не проводить его.')]
