"""Build an isolated v12 distribution from the checked-out Tyraga repository.
Original source files, uploaded PNGs and saves are not modified.
Art: stylised 4K masters from art_4k/ ("Borderlands x realism") are used when present,
otherwise the original PNG from "первая половина" is used as before.
Usage: python build_v12.py
"""
from pathlib import Path
import ast,io,json,re,shutil,tokenize,zipfile,hashlib,subprocess,sys
from PIL import Image,ImageOps
import bosscard,gfx
ROOT=Path(__file__).resolve().parent
NPC={
'zub':('02_baykal.png','Байкал','Сдержанный камерный авторитет. Говорит коротко, ценит верность и не терпит подстав.','Защитить своих, проверить новичка.'),
'graf':('10_turnik.png','Турник','Спортивный авторитет жилого блока. Азартен, торгуется за услуги и долги, ценит выдержку.','Укрепить влияние, собрать долги.'),
'buh':('06_bumazhkina.png','Бумажкина','Заведующая библиотечным архивом и неофициальной бухгалтерией зоны. Сухая ирония, точность, любовь к документам.','Свести счета и скрыть двойную бухгалтерию.'),
'gvo':('01_reshotkin.png','Решёткин','Начальник режима. Педантичен, властен, но неожиданно мягок с кошками.','Сохранить порядок и пережить проверку.'),
'str':('05_tsepi.png','Цепи','Каптёрщик оружейной-мастерской: авторитет в золотых цепях, который работает на администрацию. Сигара, трон из армейских ящиков, своя свита. Грубоватый формалист: без пропуска и подписи ничего не выдаёт, боится недостачи и взысканий. Человек, не робот.','Не допустить недостачи на складе и удержать авторитет.'),
'sm':('09_ten.png','Тень','Подземный посредник. Немногословен, подозрителен, знает тайные ходы; бережёт тишину.','Сохранить подземные тайны.'),
'gen':('12_kursant.png','Курсант','Молодая стажёрка-инспектор с планшетом, ведёт первую в жизни проверку. Нервничает, но прячет неопытность за холодной вежливостью и буквальным следованием приказам.','Доказать начальству свою полезность.'),
'serg':('08_bachok.png','Бачок','Заведующий раздачей на кухне. Практичен, устал от очередей; шутит про пайку и котлы.','Накормить смену и избежать драки.'),
'steam':('11_sokrat.png','Сократ','Банный философ. Любит парадоксы и разговоры о смысле жизни, теряет одежду и находит неожиданные ответы.','Найти одежду и достойного собеседника.'),
'cook':('04_analgin.png','Анальгин','Старожил изолятора и самозваный лекарь: халат в пятнах, огромный шприц и поднос таблеток — анальгин от всего. Спокоен и терпелив, как монах, бережёт пайку, помогает без медицинских обещаний.','Пережить изолятор и сберечь людей.'),
'kol':('03_shket.png','Шкет','Нервный молодой сокамерник. Хочет дружбы и защиты, болезненно переживает подставы.','Не остаться без пайки и найти друга.'),
'prach':('07_kulibin.png','Кулибин','Наблюдательный мастер ремонтного участка оружейной. Говорит предметно, замечает мелочи, собирает механизмы из мусора.','Найти пропавшую деталь и закончить заказ.')}
LOCS=['01_cell.png','02_yard_night.png','03_kitchen.png','04_corridor.png','05_shower.png','07_cellblock.png','06_armory.png','08_library.png','09_chapel.png','10_isolation.png','11_theatre.png','12_underpass.png']
# Location names after the text adaptation below (index = location id); checked by validate().
LOC_NAMES=['Камера','Двор','Кухня','Коридор','Душевая','Жилой блок','Оружейная-мастерская','Библиотека','Часовня','Изолятор','Театр','Подземный проход']
# Stylised 4K masters live in art_4k/<kind>/<source name>.jpg and replace the source PNG when present.
ART4K='art_4k';LOC_4K=(3840,2160);LOC_HD=(2560,1440);PORTRAIT=(800,1264)
# Heroes without a source PNG: their own portrait is used as soon as its 4K master exists.
EXTRA_PORTRAITS={'mat':'13_mat.png','zina':'14_zina.png','polkan':'15_polkan.png','hleb':'16_hleborez.png','kip':'17_kipyatok.png','cenz':'18_tsenzor.png'}
LEGACY_PORTRAIT={'mat':'mat','zina':'mat'}
# Bosses invented for v12 ("хозяева локаций"): no source PNG and no legacy picture; npcs.json already holds their final names and roles.
NEW_BOSSES=('polkan','hleb','kip','cenz')
# Background of the main menu: the night yard (location 1).
MENU_BG='02_yard_night.png'
# Borderlands-style boss intro card: one short line under the name.
TAGLINES={
'zub':'Смотрящий камеры. Чифирь, чётки, приговор.',
'graf':'Качает железо. И права.',
'gvo':'Начальник режима. Свисток заряжен.',
'str':'Каптёрщик. Без бумажки ты букашка.',
'sm':'Знает все ходы. Особенно подземные.',
'gen':'Первая проверка. Последние нервы.',
'mat':'Семь кошек. Ноль пощады.',
'cook':'Таблетка от всего. Шприц — от остального.',
'polkan':'Лает сам. Пёс — для солидности.',
'hleb':'Обвешивает честно: всех одинаково.',
'kip':'Горячая — по блату. Холодная — всем.',
'cenz':'Прочёл всё. Вычеркнул главное.'}
# Internal NPC ids, scene ids and save flags deliberately remain unchanged.
REPLACE={
'Подземный Смотритель':'Тень','Подземного Смотрителя':'Тени','Подземному Смотрителю':'Тени',
'Генерал-инспектор':'Курсант','Генерал-инспектора':'Курсанта','Генерал-инспектору':'Курсанту',
'Генерала':'Курсанта','Генералу':'Курсанту','Генерал':'Курсант','генерала':'курсанта',
'Банный Философ':'Сократ','Банного Философа':'Сократа','Банному Философу':'Сократу',
'Зубило':'Байкал','Зубила':'Байкала','Зубилу':'Байкалу',
'Графа':'Турника','Графу':'Турнику','Графом':'Турником','Граф':'Турник',
'Гвоздеву':'Решёткину','Гвоздева':'Решёткина','Гвоздевым':'Решёткиным','Гвоздев':'Решёткин',
'Бухгалтеру':'Бумажкиной','Бухгалтера':'Бумажкиной','Бухгалтер':'Бумажкина',
'Страж-9':'Цепи','Сергеич':'Бачок','Сергеича':'Бачка','Сергеичу':'Бачку',
'Седой':'Анальгин','Седого':'Анальгина','Седому':'Анальгину',
'Коляна':'Шкета','Коляну':'Шкету','Коляном':'Шкетом','Колян':'Шкет',
'Прачечная':'Оружейная-мастерская','прачечная':'оружейная-мастерская','Прачечную':'Оружейную-мастерскую','прачечной':'оружейной-мастерской',
'Мастерская':'Библиотека','мастерской':'библиотеке','Мастерскую':'Библиотеку',
'Столовая':'Кухня','столовой':'кухне','Барак':'Жилой блок','Баня':'Душевая','Храм':'Часовня','ШИЗО':'Изолятор','Клуб':'Театр','Подвалы':'Подземный проход',
'Прач вешает бельё и ведёт счёт':'Кулибин перебирает крепёж и ведёт счёт',
'Прача':'Кулибина','Прачу':'Кулибину','Прач':'Кулибин',
'пропавший носок':'пропавший болт','потерянный носок':'потерянный болт','носков':'болтов','Носков':'Болтов','носки':'болты','Носки':'Болты','носок':'болт','Носок':'Болт',
'Ржавый робот-бюрократ.':'Каптёрщик оружейной в золотых цепях, человек и формалист.',
'робот-бюрократ':'каптёрщик-формалист','робота':'каптёрщика','робот':'каптёрщик',
'Робот':'Каптёрщик',
# Курсант and Бумажкина are women on the art: feminine agreement in the adapted lines.
'Найти несоответствие в его документах':'Найти несоответствие в её документах',
'Генерал сам находит':'Курсант сама находит','Генерал расцвёл':'Курсант расцвела',
'Он сузил глаза':'Она сузила глаза',
'Генерал нашёл у вас лишнее и забрал':'Курсант нашла у вас лишнее и забрала',
'Генерал нашёл':'Курсант нашла','Генерал забыл':'Курсант забыла','Генерал удовлетворён':'Курсант удовлетворена',
'Он тщательно упаковал портфель и уехал':'Она тщательно упаковала портфель и уехала',
'Заглянуть в его бумаги':'Заглянуть в её бумаги',
'Бухгалтер доволен':'Бумажкина довольна','Бухгалтер выписал':'Бумажкина выписала','Бухгалтер что-то записал':'Бумажкина что-то записала',
'Бухгалтер впечатлён':'Бумажкина впечатлена','Бухгалтер уже знал':'Бумажкина уже знала','Бухгалтер закрыл':'Бумажкина закрыла',
'Он вздыхает: «Я не говорил»':'Она вздыхает: «Я не говорила»',
# Location names in the right grammatical case and with the right meaning (the art decides what a place is).
'в Храме':'в Часовне','ойти в Храм':'ойти в Часовню','Храм теперь ваш.':'Часовня теперь ваша.',
'в ШИЗО':'в Изоляторе','В ШИЗО':'В Изоляторе','Подвалы свободны.':'Подземный проход свободен.',
'В столовой':'На кухне','в столовой':'на кухне','из столовой':'с кухни','в бараке':'в жилом блоке',
# Crafting lives in the armory workshop now, not in the library.
'Мастерская: смена':'Оружейная-мастерская: смена','В мастерской полно железа':'В оружейной-мастерской полно железа','в углу мастерской':'в углу оружейной-мастерской',
# The underground keeper is called Тень everywhere, Мать-Смотрительница keeps her name.
'Смотрительниц':'Смотрительниц','Подвальный Смотритель':'Тень','Смотрителя':'Тени','Смотрителю':'Тени','Смотрителем':'Тенью','Смотритель':'Тень',
'совет Философа':'совет Сократа',
# Grammar and leftovers of the old cast: the storekeeper is a man now, the place is the armory.
'Уговорить Бухгалтера':'Уговорить Бумажкину','ПРОПУСК В ПРАЧЕЧНУЮ':'ПРОПУСК В ОРУЖЕЙНУЮ','Страж-9 скрипит':'Цепи цедит','Страж-9 обрабатывает':'Цепи прикидывает',
'завис, пошёл дымом и перешёл в режим энергосбережения':'растерялся, запросил письменное разъяснение и оставил пост',
# Цепи is a man in gold chains, not a robot: his lines lose the machine voice (ALL CAPS, percentages, "the system").
'«ПРЕДЪЯВИТЕ ПРОПУСК В ПРАЧЕЧНУЮ. ЕСЛИ ПРОПУСКА НЕТ — ПРЕДЪЯВИТЕ БУМАГУ ОБ ОТСУТСТВИИ ПРОПУСКА. ЕСЛИ И ЕЁ НЕТ — ЗАПОЛНИТЕ БЛАНК»':'«Пропуск в оружейную покажи. Нет пропуска — неси бумагу, что пропуска нет. Нет и бумаги — садись, пиши бланк»',
'«ВЕРОЯТНОСТЬ ВАШЕЙ ВИНОВНОСТИ СНИЖЕНА НА 12%»':'«Ладно. На жулика ты теперь похож процентов на двенадцать меньше»',
'«ПОПЫТКА ОБМАНА ЗАФИКСИРОВАНА»':'«Лапшу мне на цепи не вешай. Записал»',
'«ПУНКТ 14.3: ЛИЦАМ С ПРОПАВШИМ НОСКОМ ПРОПУСК НЕ ТРЕБУЕТСЯ»':'«Пункт 14.3: кто ищет пропавший болт, тому без пропуска». Цепи морщится: сам писал',
'Страж-9 одобряет. Вы в системе.':'Цепи одобряет. Вы в журнале.',
'«ЭТО НЕ МОЁ»':'«Это не моё»',
'Страж-9 монотонно считает: «ЗАПРЕЩЁННЫЕ ПРЕДМЕТЫ. ПОДГОТОВЬТЕСЬ К ИЗЪЯТИЮ»':'Цепи лениво перечисляет: «Запрещённое — на стол. Изымать буду по списку»',
'«ИНЦИДЕНТ ИСЧЕРПАН»':'«Вопрос закрыт»',
'бухгалтерия':'бухгалтерия', 'Тюряга · Свои люди v9':'Тюряга · Новые лица v12','Свои люди · v9':'Новые лица · v12'}
PAT=re.compile('|'.join(re.escape(k) for k in sorted(REPLACE,key=len,reverse=True)))
def text(s):return PAT.sub(lambda m:REPLACE[m.group()],s)
def transform_source(s):
    out=[]
    for t in tokenize.generate_tokens(io.StringIO(s).readline):
        if t.type==tokenize.STRING:
            changed=text(t.string)
            t=t._replace(string=changed)
        out.append(t)
    result=tokenize.untokenize(out);ast.parse(result);return result

def art_source(root,kind,file):
    """(path, stylised): the 4K master art_4k/<kind>/<stem>.jpg if it exists, else the source PNG."""
    master=Path(root)/ART4K/kind/(Path(file).stem+'.jpg')
    if master.is_file():return master,True
    return Path(root)/'первая половина'/file,False
def save_portrait(source,target):
    """Game portrait 1:1.58 for every existing loader (scene, dialogue, map chips, arena)."""
    with Image.open(source) as im:
        im=ImageOps.exif_transpose(im).convert('RGB')
        ImageOps.fit(im,PORTRAIT,method=Image.Resampling.LANCZOS,centering=(.5,.35)).save(target,quality=94)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build(root=ROOT):
    root=Path(root);src=root/'первая половина'
    needed=set(LOCS)|{v[0] for v in NPC.values()}
    missing=[n for n in sorted(needed) if not (src/n).is_file()]
    if missing:raise RuntimeError('Missing PNG assets: '+', '.join(missing))
    for n in needed:
        with Image.open(src/n) as im:im.verify()
    required=['fight.py','fightui.py','core.py','story10.py','story_data.py','main.py','npcs.json','ai.py']
    for n in required:
        if not (root/n).is_file():raise RuntimeError('Expected v11 file: '+n)
    dest=root/'dist'/'Tyuryaga_v12'
    if dest.exists():shutil.rmtree(dest)
    dest.mkdir(parents=True)
    ignore={'.git','.venv','.venv_build','dist','output','__pycache__','.pytest_cache','saves','logs','первая половина','.github',ART4K,'tools'}
    for p in root.iterdir():
        if p.name in ignore or p.suffix=='.zip' or p.name in('settings.json','achievements.json','.env'):continue
        if p.is_dir():shutil.copytree(p,dest/p.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
        else:shutil.copy2(p,dest/p.name)
    # Safe default configuration: personal .env never enters a public build.
    (dest/'.env').write_text('CHAT_FAST_MODE=true\nGOSSIP_ENABLED=true\n',encoding='utf8')
    for p in dest.glob('*.py'):p.write_text(transform_source(p.read_text(encoding='utf8')),encoding='utf8')
    # The game ships with tests that speak its own language: v12 names, and no test of the art pipeline it does not contain.
    (dest/'tests'/'test_art4k.py').unlink(missing_ok=True)
    for p in (dest/'tests').glob('*.py'):p.write_text(transform_source(p.read_text(encoding='utf8')),encoding='utf8')
    data=json.loads((dest/'npcs.json').read_text(encoding='utf8'))
    report=[]
    def hero(k,file):
        # Full-size art goes to image/characters; a 1:1.58 JPEG serves the existing loaders.
        source,stylised=art_source(root,'characters',file)
        target=dest/'image'/'characters'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        save_portrait(source,dest/'assets'/(k+'.jpg'));data[k]['portrait']=k
        report.append({'id':k,'name':data[k]['name'],'kind':'character','boss':data[k]['boss'],'home':data[k]['home'],'location':LOC_NAMES[data[k]['home']],'file':target.relative_to(dest).as_posix(),'style':'borderlands_4k' if stylised else 'original'})
    for k,(file,name,role,goal) in NPC.items():
        data[k].update(name=name,role=role,goal=goal);hero(k,file)
    for k,file in EXTRA_PORTRAITS.items():
        if art_source(root,'characters',file)[1]:hero(k,file)
        else:
            # No art of their own yet: keep the legacy picture, but as a separate file per hero.
            legacy=root/'assets'/(LEGACY_PORTRAIT.get(k,k)+'.jpg')
            if data[k]['portrait']!=k:shutil.copy2(legacy,dest/'assets'/(k+'.jpg'));data[k]['portrait']=k
            report.append({'id':k,'name':data[k]['name'],'kind':'character','boss':data[k]['boss'],'home':data[k]['home'],'location':LOC_NAMES[data[k]['home']],'file':'assets/%s.jpg'%k,'style':'legacy'})
    for k,line in TAGLINES.items():data[k]['tagline']=line
    (dest/'npcs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    for i,file in enumerate(LOCS):
        source,stylised=art_source(root,'locations',file);target=dest/'assets'/('loc_%d.jpg'%i)
        if stylised:
            with Image.open(source) as im:
                if im.size!=LOC_4K:raise RuntimeError('%s must be %dx%d'%(source.name,*LOC_4K))
            shutil.copy2(source,target)  # byte copy: the 4K master is the game background, no recompression
        else:
            keep=dest/'image'/'locations'/file;keep.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,keep)
            with Image.open(source) as im:
                im=ImageOps.exif_transpose(im).convert('RGB')
                ImageOps.fit(im,LOC_HD,method=Image.Resampling.LANCZOS).save(target,quality=94)
        report.append({'id':i,'name':LOC_NAMES[i],'kind':'location','file':target.relative_to(dest).as_posix(),'source':source.name,'style':'borderlands_4k' if stylised else 'original'})
    shutil.copy2(dest/'assets'/('loc_%d.jpg'%LOCS.index(MENU_BG)),dest/'assets'/'menu_bg.jpg')
    # Pictures of the old cast that nothing loads any more do not belong to the new build.
    for old in ('accountant','general','keeper','mother','robot'):(dest/'assets'/(old+'.jpg')).unlink(missing_ok=True)
    # Boss intro cards as pictures, made by the same renderer the fight window uses.
    cards=dest/'image'/'boss_cards';cards.mkdir(parents=True,exist_ok=True)
    for k,v in data.items():
        if v['boss']:
            with Image.open(dest/'assets'/('loc_%d.jpg'%v['home'])) as scene:
                scene.draft('RGB',(1920,940));bosscard.render(dest,v,LOC_NAMES[v['home']],(1920,940),scene).save(cards/(k+'.jpg'),quality=92)
    # Move crafting to the armory; keep tea accounts in the library.
    p=dest/'core.py';s=p.read_text(encoding='utf8')
    s=re.sub(r"^    if L==6:add\('work_shift'.*\n",'',s,flags=re.M)
    s=s.replace("if L==7:add('work_shift'","if L==6:add('work_shift'")
    s=s.replace("if L==7:add('exchange','Биржа чая',20,'coin');add('order_shiv'","if L==7:add('exchange','Биржа чая',20,'coin')\n    if L==6:add('order_shiv'")
    p.write_text(s,encoding='utf8');ast.parse(s)
    # The shiv is ordered in the armory workshop, so the craftsman is Кулибин, not the librarian.
    p=dest/'story10.py';s=p.read_text(encoding='utf8')
    if s.count("N('buh','Мастер в углу")!=1:raise RuntimeError('order_shiv scene not found')
    s=s.replace("N('buh','Мастер в углу","N('prach','Мастер в углу");p.write_text(s,encoding='utf8');ast.parse(s)
    # Human guard: remove robot-only rendering while keeping his heavy fighting style.
    p=dest/'fightui.py';s=p.read_text(encoding='utf8').replace("robot=f.kind=='enemy' and s.k=='str'","robot=False");p.write_text(s,encoding='utf8')
    (dest/'VERSION.txt').write_text('Tyuryaga v12 / New Faces / Art integration\n',encoding='utf8')
    (dest/'ART_MANIFEST_v12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    done=lambda kind:sum(1 for r in report if r['kind']==kind and r['style']=='borderlands_4k')
    waiting=[r['name'] for r in report if r['style']!='borderlands_4k']
    (dest/'CHANGELOG_v12.md').write_text('# v12 — Новые лица\n'
        'Портреты и фоны подключены ко всем существующим загрузчикам, включая карту, диалоги и арены. Внутренние ID сохранены.\n\n'
        '## Арт «Borderlands × реальность»\n'
        'Стилизованных 4K-фонов: %d из 12 (assets/loc_N.jpg, 3840×2160). Стилизованных портретов: %d из %d (полные версии — image/characters/, игровые 800×1264 — assets/).\n'
        'Это перерисовка исходных картинок с нейросетевым увеличением до 4K, а не нативный 4K-рендер. '%(done('location'),done('character'),len(data))
        +('Ещё в исходном или старом виде: '+', '.join(waiting)+'.\n' if waiting else 'Весь набор стилизован.\n')
        +'У каждого героя свой файл портрета; стилизованные портреты боссов нарисованы на фоне их локаций. Фон меню — ночной двор (assets/menu_bg.jpg). Перед боем с боссом показывается заставка с именем и подписью (bosscard.py).\n\n'
        '## Герои и тексты\n'
        'Новые роли: Решёткин, Байкал, Шкет, Анальгин, Цепи, Бумажкина, Кулибин, Бачок, Тень, Турник, Сократ, Курсант. '
        'Роли Цепей (каптёрщик в золотых цепях), Курсанта (стажёрка-инспектор) и Анальгина (самозваный лекарь изолятора) приведены в соответствие с тем, что нарисовано на картинках; реплики про Курсанта и Бумажкину согласованы в женском роде.\n'
        'Промпты получают новые имена и роли, сюжетные строки адаптированы, ремонт перенесён в оружейную-мастерскую. В старых сохранениях исторические записи не переписываются. Рекомендуется новая игра; перед переносом saves сделайте копию.\n\n'
        '## Двенадцать боссов: хозяева локаций\n'
        'Боссов теперь 12 — по одному на каждую локацию. Четверо новых придуманы для v12, исходных картинок у них не было: '
        'Полкан (двор), Хлеборез (кухня), Кипяток (душевая), Цензор (библиотека). У каждого свой портрет, заставка перед боем, стиль боя и слабость.\n'
        'Пока хозяин у власти, одно местное занятие идёт по его правилам: перекур по свистку, смена на кухне через «долю», горячая вода за сигарету, письма домой через маркер. '
        'После свержения (боем или слабостью) занятие становится обычным, а местный житель рассказывает, как стало без хозяина. '
        'Новое занятие в библиотеке — «Написать письмо домой» (раз в день; ответ приходит примерно через 30 часов, иногда с бандеролью). '
        'В журнале появился раздел «Хозяева локаций», добавлены три достижения. Реплики Цепей больше не написаны «машинными» заглавными буквами.\n'
        'Тексты и баланс новых сцен и боёв — первая редакция: проверены автотестами, живым игроком не пройдены.\n\n'
        'Ограничения: автоматическая текстовая адаптация не заменяет редактуру каждого диалога; Windows, окно Tk, визуальное кадрирование и локальная модель требуют живой проверки.\n',encoding='utf8')
    validate(dest)
    zpath=root/'dist'/'TYURYAGA_v12_FULL.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for p in dest.rglob('*'):
            if p.is_file():z.write(p,'Tyuryaga_Project/'+str(p.relative_to(dest)))
    with zipfile.ZipFile(zpath) as z:
        if z.testzip():raise RuntimeError('ZIP integrity check failed')
    print(json.dumps({'archive':str(zpath),'bytes':zpath.stat().st_size,'sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()},indent=2))
    return dest,zpath

def validate(dest):
    for p in list(dest.glob('*.py'))+list((dest/'tests').glob('*.py')):ast.parse(p.read_text(encoding='utf8'))
    n=json.loads((dest/'npcs.json').read_text(encoding='utf8'))
    assert len(n)==18 and len(NPC)==12 and set(NEW_BOSSES)<=set(n)
    for k,v in n.items():
        assert 0<=v['home']<12
        assert all(c in n for c in v['contacts'])
        assert (dest/'assets'/(v['portrait']+'.jpg')).exists()
    manifest=json.loads((dest/'ART_MANIFEST_v12.json').read_text(encoding='utf8'))
    legacy={r['id'] for r in manifest if r['kind']=='character' and r['style']=='legacy'}
    # Every hero has a portrait file of their own; no two heroes share a picture
    # (heroes still waiting for their art may temporarily show the same legacy picture).
    assert all(v['portrait']==k for k,v in n.items()),'portrait must be named after the hero id'
    faces={k:sha(dest/'assets'/(k+'.jpg')) for k in n if k not in legacy}
    assert len(set(faces.values()))==len(faces),'identical portraits for different heroes'
    # ...and no two heroes look the same either (the same picture saved twice, resized or re-compressed).
    twins=gfx.lookalikes([dest/'assets'/(k+'.jpg') for k in faces])
    assert not twins,'heroes share one picture: '+', '.join('%s=%s'%(a.stem,b.stem) for a,b,_ in twins)
    bosses=[k for k,v in n.items() if v['boss']]
    assert len(bosses)==12 and all(n[k].get('tagline') for k in bosses),'twelve bosses, each with an intro tagline'
    assert sorted(n[k]['home'] for k in bosses)==list(range(12)),'one boss per location'
    for k in faces:
        with Image.open(dest/'assets'/(k+'.jpg')) as im:assert im.size==PORTRAIT,(k,im.size)
    # Twelve different backgrounds, 16:9, 4K when stylised; names match the art.
    views=[]
    for i in range(12):
        with Image.open(dest/'assets'/('loc_%d.jpg'%i)) as im:assert im.size in(LOC_4K,LOC_HD),(i,im.size)
        views.append(sha(dest/'assets'/('loc_%d.jpg'%i)))
    assert len(set(views))==12,'every location needs a unique background'
    twins=gfx.lookalikes([dest/'assets'/('loc_%d.jpg'%i) for i in range(12)])
    assert not twins,'locations share one picture: '+', '.join('%s=%s'%(a.stem,b.stem) for a,b,_ in twins)
    assert (dest/'assets'/'menu_bg.jpg').is_file()
    code="import json,core,world;from story_data import SCENES;n=json.load(open('npcs.json',encoding='utf8'));w=world.World(n);assert n['gvo']['name']=='Решёткин';assert n['str']['name']=='Цепи';assert world.NAMES==%r,world.NAMES;assert len(SCENES)>=110;assert 'сюжет' in __import__('ai').PROMPT;"%(LOC_NAMES,)
    # Twelve bosses are known to every system that lists them, each sits in their own location, and every turf rule has both scenes.
    code+="import fight,story10;bosses={k for k,v in n.items() if v['boss']};assert bosses==set(core.BOSS_LOC)==set(fight.STYLES)==set(story10.WEAK),bosses;assert all(n[k]['home']==l for k,l in core.BOSS_LOC.items());assert all(a in SCENES and a+'_'+b in SCENES and n[b]['home']==l for b,(l,a,_) in core.TURF.items());print('v12 structural smoke test OK')"
    subprocess.run([sys.executable,'-c',code],cwd=dest,check=True)

if __name__=='__main__':build()
