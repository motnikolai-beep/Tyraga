"""Hand-annotated silhouettes of visible props on both shipped background sets.

Coordinates are fractions of the source image, NOT arbitrary screen rectangles. v16
renders the same JPEG that the player sees; cover/letterbox transforms are applied
at runtime. 'legacy' is the repo's 2560px art, 'master' the 3840px distribution.
No object is claimed to exist where the other artwork depicts something else.
"""
from pathlib import Path
from PIL import Image
import core

# (id, label, polygon in normalized source coordinates). Shapes follow actual art,
# with generous borders for mouse accessibility, and are intentionally hand-authored.
LEGACY={
 0:[('bed','Шконка',[(.07,.17),(.19,.14),(.50,.29),(.48,.87),(.09,.98)]),('window','Решётка',[(.55,.05),(.71,.04),(.72,.34),(.54,.35)])],
 1:[('tower','Вышка',[(.30,.08),(.39,.07),(.52,.17),(.50,.60),(.34,.60)]),('fence','Ограждение',[(.01,.40),(.20,.44),(.35,.61),(.36,.83),(.02,.90)])],
 2:[('pots','Котлы',[(.43,.33),(.77,.38),(.80,.65),(.40,.69)]),('counter','Раздача',[(.04,.62),(.68,.59),(.82,.67),(.18,.96),(.01,.99)])],
 3:[('door','Дверь в конце',[(.45,.35),(.58,.34),(.59,.80),(.45,.82)]),('lamp','Лампы',[(.46,.05),(.55,.05),(.57,.34),(.45,.35)])],
 4:[('shower','Душевые',[(.04,.08),(.46,.10),(.46,.48),(.04,.60)]),('bench','Лавки',[(.13,.49),(.43,.52),(.42,.80),(.13,.76)])],
 5:[('bunks','Нары блока',[(.01,.02),(.33,.06),(.35,.94),(.01,.98)]),('aisle','Проход блока',[(.42,.44),(.57,.42),(.85,.99),(.18,.99)])],
 6:[('door','Камерные двери',[(.03,.18),(.30,.13),(.31,.85),(.04,.96)]),('lamp','Лампы коридора',[(.49,.04),(.55,.04),(.56,.44),(.49,.45)])],
 7:[('machine','Швейная машина',[(.14,.54),(.30,.52),(.38,.61),(.35,.90),(.13,.88)]),('table','Рабочий стол',[(.42,.45),(.80,.42),(.84,.74),(.43,.82)])],
 8:[('altar','Алтарь',[(.41,.60),(.59,.60),(.62,.82),(.39,.82)]),('glass','Витраж',[(.41,.02),(.58,.02),(.60,.59),(.39,.59)])],
 9:[('cot','Койка',[(.13,.57),(.45,.55),(.48,.92),(.06,.96)]),('basin','Умывальник',[(.65,.53),(.83,.49),(.85,.85),(.63,.87)])],
 10:[('stage','Сцена',[(.27,.28),(.78,.27),(.79,.72),(.26,.73)]),('seats','Зрительские места',[(.05,.68),(.93,.65),(.99,.99),(.01,.99)])],
 11:[('torch','Факел',[(.08,.24),(.20,.27),(.22,.58),(.10,.55)]),('arch','Арка выхода',[(.34,.14),(.67,.15),(.76,.72),(.27,.74)])],
}
MASTER={
 0:[('bed','Шконка',[(.09,.11),(.29,.10),(.45,.24),(.42,.84),(.10,.83)]),('window','Окно камеры',[(.66,.05),(.81,.07),(.81,.42),(.66,.41)])],
 1:[('tower','Вышка',[(.20,.06),(.31,.05),(.38,.22),(.36,.57),(.22,.55)]),('fence','Ограждение',[(.01,.28),(.20,.31),(.33,.54),(.34,.82),(.01,.90)])],
 2:[('pots','Котлы',[(.48,.30),(.78,.33),(.79,.81),(.47,.81)]),('counter','Рабочий стол',[(.70,.58),(.96,.55),(.99,.82),(.67,.90)])],
 3:[('door','Дверь коридора',[(.15,.32),(.29,.31),(.29,.84),(.13,.88)]),('lamp','Лампы',[(.44,.07),(.57,.08),(.57,.37),(.44,.37)])],
 4:[('shower','Душевые',[(.46,.07),(.84,.08),(.83,.57),(.47,.51)]),('bench','Лавка',[(.12,.53),(.36,.52),(.39,.77),(.09,.78)])],
 5:[('doors','Двери блока',[(.01,.32),(.31,.25),(.34,.80),(.02,.91)]),('rail','Перила',[(.02,.60),(.37,.60),(.55,.90),(.02,.89)])],
 6:[('rack','Стеллаж с инструментами',[(.67,.19),(.99,.10),(.99,.89),(.64,.76)]),('bench','Верстак',[(.40,.61),(.57,.61),(.60,.88),(.35,.88)])],
 7:[('shelves','Книжные полки',[(.70,.13),(.98,.02),(.99,.89),(.67,.79)]),('table','Стол читальни',[(.36,.53),(.72,.52),(.80,.84),(.31,.90)])],
 8:[('altar','Алтарь',[(.42,.53),(.58,.53),(.59,.67),(.41,.67)]),('glass','Витраж',[(.41,.11),(.58,.10),(.60,.58),(.40,.58)])],
 9:[('cot','Койка',[(.17,.70),(.44,.67),(.46,.96),(.11,.96)]),('basin','Умывальник',[(.64,.64),(.79,.62),(.81,.88),(.62,.89)])],
 10:[('stage','Сцена',[(.40,.23),(.76,.21),(.79,.70),(.39,.71)]),('seats','Зрительские места',[(.02,.62),(.60,.60),(.75,.96),(.01,.96)])],
 11:[('torch','Факел',[(.11,.27),(.22,.29),(.23,.64),(.10,.61)]),('arch','Арка прохода',[(.34,.20),(.69,.20),(.77,.77),(.29,.79)])],
}
# Meaning belongs to the prop, not its bounding polygon. The second field is the
# concrete action offered after a short local description, not a free item machine.
LORE={
 'bed':('Место отдыха', 'Нары помнят всех, кто здесь спал. Приглядитесь к краю матраса: возможно, там оставили что-то важное. Днём можно присесть; ночью — лечь до утра.', 'Присесть на нары'),
 'window':('Взгляд наружу', 'За решёткой день идёт своим ходом. Из окна видно свет, но не обещание свободы.', 'Посмотреть в окно'),
 'tower':('Наблюдение', 'Вышка напоминает, что прогулка здесь тоже идёт по расписанию.', 'Проследить за прожектором'),
 'fence':('Граница двора', 'Сетка разделяет двор и чужой путь. Не всякий разговор стоит вести у неё.', 'Оглядеть ограждение'),
 'pots':('Кухонный труд', 'В котлах еда для многих; тем, кто в очереди, важен не только вес пайки.', 'Помочь у котлов'),
 'counter':('Кухонный стол', 'За столом готовят или раздают еду. Очередь напоминает, кому сколько достанется.', 'Осмотреть стол'),
 'door':('Закрытая дверь', 'За дверью слышны шаги. Не всякий замок открывается от нажима.', 'Прислушаться у двери'),
 'lamp':('Свет коридора', 'Лампы горят по режиму. По ним можно заметить смену дежурства, не зная чужих планов.', 'Проверить время по свету'),
 'shower':('Вода по правилам', 'В душе даже горячая вода становится вопросом отношений и порядка.', 'Проверить воду'),
 'bench':('Пауза', 'Скамья и верстак переживают разговоры, споры и короткие передышки.', 'Передохнуть рядом'),
 'bunks':('Общий сон', 'Нары стоят близко: человеку трудно остаться наедине с мыслями.', 'Поправить постель'),
 'aisle':('Общий проход', 'Здесь встречаются соседи, а ночной шум слышно всем.', 'Пройтись по блоку'),
 'doors':('Ряд камер', 'За каждой дверью чей-то день, но его историю нельзя угадать по номеру.', 'Осмотреть двери'),
 'rail':('Перила блока', 'У перил обычно задерживаются перед разговором или проверкой.', 'Остановиться у перил'),
 'rack':('Чужие инструменты', 'Инструменты в учёте; брать их без разрешения — совсем другое действие.', 'Пересчитать инструменты'),
 'machine':('Смена у машины', 'Механизм кормит работой и отнимает часы; детали не появятся сами.', 'Осмотреть машину'),
 'table':('Общий стол', 'За этим столом работают или читают: на нём видно, как проходит день.', 'Осмотреть стол'),
 'shelves':('Книги', 'На полках больше историй, чем в официальных отчётах.', 'Полистать книгу'),
 'altar':('Тихое место', 'Здесь можно остановиться, но никто не обязан менять убеждения.', 'Побыть в тишине'),
 'glass':('Цветной свет', 'Свет проходит через витраж и ложится на пустые скамьи.', 'Посмотреть на витраж'),
 'cot':('Койка изолятора', 'В тесной комнате даже тишина слышится иначе.', 'Прилечь на койку'),
 'basin':('Вода для лица', 'Маленький умывальник — один из немногих привычных ритуалов.', 'Умыться'),
 'stage':('Сцена', 'Когда занавес закрыт, здесь всё равно репетируют слова и роли.', 'Осмотреть сцену'),
 'seats':('Места в зале', 'Зал ждёт зрителей. В одиночестве слышно, как скрипят кресла.', 'Сесть в зале'),
 'torch':('Огонь в проходе', 'Факел освещает мокрый камень, но не объясняет, что за поворотом.', 'Присмотреться к огню'),
 'arch':('Проход', 'Арка ведёт дальше, но путь определяется картой, а не одним нажатием.', 'Оглядеть проход'),
}

def variant(base,loc):
    """Check actual installed artwork, not a global build version or save version."""
    with Image.open(Path(base)/'assets'/f'loc_{loc}.jpg') as image:
        return 'master' if image.width>=3200 else 'legacy'

def objects(loc,kind):return (MASTER if kind=='master' else LEGACY)[loc]

def transform(points,size,source,cover=True):
    """Exact ImageOps.fit(center) / thumbnail(center) mapping used by App.draw."""
    w,h=size;iw,ih=source
    scale=max(w/iw,h/ih) if cover else min(w/iw,h/ih)
    rw,rh=iw*scale,ih*scale;dx=(w-rw)/2;dy=(h-rh)/2
    return [(u*rw+dx,v*rh+dy) for u,v in points]

def inside(x,y,points):
    """Ray-casting works for irregular silhouettes; a bbox would click the wrong prop."""
    yes=False
    for a,b in zip(points,points[1:]+points[:1]):
        x1,y1=a;x2,y2=b
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1:yes=not yes
    return yes

def placed(base,loc,size,cover=True):
    path=Path(base)/'assets'/f'loc_{loc}.jpg'
    with Image.open(path) as im:source=im.size
    return [(id,label,transform(poly,size,source,cover)) for id,label,poly in objects(loc,'master' if source[0]>=3200 else 'legacy')]

def hit(x,y,placed_objects):
    return next(((id,label) for id,label,poly in placed_objects if inside(x,y,poly)),None)

def perform(w,id,art):
    """One verified local action per prop/day. No LLM may grant an item or skip time."""
    if id not in LORE:raise ValueError('Нет такого предмета')
    if art not in ('master','legacy'):raise ValueError('Неизвестное изображение')
    if id not in {obj for obj,_,_ in objects(w.s['loc'],art)}:raise ValueError('Этого предмета на изображении нет')
    if id in ('bed','cot','bunks') and core.is_night(w):
        core.sleep(w)
        seen=core.C(w).setdefault('environment16_seen',[])
        marker=f"{w.s['loc']}:{id}"
        if marker not in seen:seen.append(marker)
        w.event('environment','Игрок лёг на видимую койку и проснулся утром.',w.witnesses())
        return 'Сон до утра. Новый день.'
    record=core.C(w).setdefault('environment16',{})
    key=f"{w.s['day']}:{w.s['loc']}:{id}"
    if key in record:return 'Сегодня вы уже осмотрели это место. Вернитесь завтра.'
    # Optional small benefits, capped per object/day and never compounded for re-clicks.
    minutes=20 if id in ('bed','cot','bench','seats','bunks') else 10
    core.advance(w,minutes)
    if id in ('bed','cot','bench','seats','bunks'):w.s['stamina']=min(w.s['stamina_max'],w.s['stamina']+6)
    if id=='basin':w.s['hp']=min(100,w.s['hp']+2)
    record[key]=True
    seen=core.C(w).setdefault('environment16_seen',[])
    marker=f"{w.s['loc']}:{id}"
    if marker not in seen:seen.append(marker)
    if len(record)>200:
        for old in list(record)[:-120]:record.pop(old,None)
    text='Игрок: '+LORE[id][2].lower()+' в '+core.NAMES[w.s['loc']]+'.'
    w.event('environment',text,w.witnesses())
    return LORE[id][2]+f' · {minutes} мин.'

def journal(w):
    """Only encountered objects, never descriptions of places not actually visited."""
    seen=core.C(w).get('environment16_seen',[])
    rows=[]
    for marker in reversed(seen[-10:]):
        try:loc,id=marker.split(':',1);loc=int(loc)
        except (ValueError,AttributeError):continue
        if 0<=loc<12 and id in LORE:rows.append(core.NAMES[loc]+' · '+LORE[id][0]+': '+LORE[id][1])
    return rows or ['Наведите курсор на очертания предметов в сцене и нажмите на них: окружение помнит ваши действия.']
