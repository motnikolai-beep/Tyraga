"""A physical note found under the cell bunk: discovery, concealment, conversation, delivery.

It is NOT the player's v15 letter from home or the v12 mail item. Only Shket can
know its words after the player actually shows or gives it to him. All actions are
validated here, never inferred from a free-form model response.
"""
import core

ITEM='note17'
WORDS='«Шкет, если окажешься на воле раньше меня, попроси у сестры адрес. Не оставайся один». Подпись стёрлась.'

def state(w):return core.C(w).setdefault('note17',{'found':False,'shown':False,'given_day':None,'where':None})

def held(w):return core.C(w)['inv'].get(ITEM,0)>0

def hidden(w):return core.stash_get(w,0).get(ITEM,0)>0

def find(w):
    if w.s['loc']!=0:raise ValueError('Нары в другой комнате')
    r=state(w)
    if r['found']:return 'Под матрасом больше нет новой записки.'
    core.advance(w,10);r.update(found=True,where='held')
    core.C(w)['inv'][ITEM]=1
    # Finding is private; other NPCs cannot deduce content from location alone.
    w.event('note17_find','Игрок нашёл под краем койки чужую записку и никому её не показал.',[])
    return 'Под матрасом нашлась чужая записка: '+WORDS+' Она у вас в вещах.'

def act(w,choice):
    if choice not in ('hide','take','show','give'):raise ValueError('Нет такого решения')
    r=state(w)
    if not r['found'] or r.get('given_day') is not None:raise ValueError('Записка больше не у вас')
    if choice=='hide':
        if not held(w) or w.s['loc']!=0:raise ValueError('Спрятать записку можно только у своей койки в камере')
        core.stash_move(w,0,ITEM,1,True);r['where']='hidden'
        w.event('note17_hide','Игрок спрятал чужую записку в схроне камеры.',[])
        return 'Записка в схроне камеры. Её можно забрать позже.'
    if choice=='take':
        if not hidden(w) or w.s['loc']!=0:raise ValueError('Записка не лежит в схроне камеры')
        core.stash_move(w,0,ITEM,1,False);r['where']='held'
        w.event('note17_take','Игрок забрал чужую записку из схрона камеры.',[])
        return 'Записка снова у вас.'
    if not held(w) or w.s['loc']!=0 or 'kol' not in w.witnesses():raise ValueError('Чтобы поговорить с Шкетом, держите записку при себе и вернитесь в камеру')
    if choice=='show':
        if r['shown']:return 'Шкет уже видел эту записку.'
        core.advance(w,10);r['shown']=True
        w.s['relations']['kol']=min(100,w.s['relations'].get('kol',0)+5)
        import life15
        life15.bond(w,'kol',trust=5)
        w.event('note17_show','Игрок показал Шкету записку для него; отправитель неизвестен.', ['kol'])
        return 'Шкет прочёл несколько строк, но не знает, кто их написал. Записка пока у вас.'
    core.advance(w,10);core.C(w)['inv'][ITEM]=0;r.update(given_day=w.s['day'],where='given')
    w.s['relations']['kol']=min(100,w.s['relations'].get('kol',0)+8)
    import life15
    life15.bond(w,'kol',trust=8)
    w.event('note17_give','Игрок передал Шкету записку о сестре и адресе. Отправитель неизвестен.', ['kol'])
    return 'Записка у Шкета. На следующий день поговорите с ним в камере.'

def context(w,k):
    if k!='kol':return {}
    r=state(w)
    if not r.get('shown') and r.get('given_day') is None:return {}
    return {'что_прочёл':WORDS,'отправитель':'неизвестен','записка_у_Шкета':r.get('given_day') is not None,
            'разговор_после_передачи': 'note17_after' in core.C(w)['done']}

def followup_ready(w):
    r=state(w);d=r.get('given_day')
    return d is not None and w.s['day']>d and 'note17_after' not in core.C(w)['done']

def journal(w):
    r=state(w)
    if not r['found']:return ['В камере есть вещи, к которым можно присмотреться внимательнее.']
    if r.get('given_day') is not None:
        return ['Чужая записка передана Шкету. '+('Вы поговорили с ним на следующий день.' if 'note17_after' in core.C(w)['done'] else 'После смены дня вернитесь в камеру и поговорите с ним.')]
    if hidden(w):return ['Чужая записка спрятана в схроне камеры; её можно забрать у своей койки.']
    return ['Чужая записка у вас. '+WORDS+' Покажите её Шкету, передайте ему или спрячьте в камере.']
