"""Build an isolated v12 distribution from the checked-out Tyraga repository.
Original source files, uploaded PNGs and saves are not modified.
Usage: python build_v12.py
"""
from pathlib import Path
import ast,io,json,re,shutil,tokenize,zipfile,hashlib,subprocess,sys
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parent
NPC={
'zub':('02_baykal.png','Байкал','Сдержанный камерный авторитет. Говорит коротко, ценит верность и не терпит подстав.','Защитить своих, проверить новичка.'),
'graf':('10_turnik.png','Турник','Спортивный авторитет жилого блока. Азартен, торгуется за услуги и долги, ценит выдержку.','Укрепить влияние, собрать долги.'),
'buh':('06_bumazhkina.png','Бумажкина','Заведующая библиотечным архивом и неофициальной бухгалтерией зоны. Сухая ирония, точность, любовь к документам.','Свести счета и скрыть двойную бухгалтерию.'),
'gvo':('01_reshotkin.png','Решёткин','Начальник режима. Педантичен, властен, но неожиданно мягок с кошками.','Сохранить порядок и пережить проверку.'),
'str':('05_tsepi.png','Цепи','Человек, охранник оружейной. Грубоватый формалист, требует пропуска, боится служебных взысканий. Не робот.','Не допустить недостачи и не получить выговор.'),
'sm':('09_ten.png','Тень','Подземный посредник. Немногословен, подозрителен, знает тайные ходы; бережёт тишину.','Сохранить подземные тайны.'),
'gen':('12_kursant.png','Курсант','Молодой инспектор-стажёр, ведущий проверку. Компенсирует неопытность холодной вежливостью и буквальным следованием приказам.','Доказать начальству свою полезность.'),
'serg':('08_bachok.png','Бачок','Заведующий раздачей на кухне. Практичен, устал от очередей; шутит про пайку и котлы.','Накормить смену и избежать драки.'),
'steam':('11_sokrat.png','Сократ','Банный философ. Любит парадоксы и разговоры о смысле жизни, теряет одежду и находит неожиданные ответы.','Найти одежду и достойного собеседника.'),
'cook':('04_analgin.png','Анальгин','Опытный заключённый, неформальный санитар изолятора. Спокоен и терпелив, бережёт пайку, помогает без медицинских обещаний.','Пережить изолятор и сберечь людей.'),
'kol':('03_shket.png','Шкет','Нервный молодой сокамерник. Хочет дружбы и защиты, болезненно переживает подставы.','Не остаться без пайки и найти друга.'),
'prach':('07_kulibin.png','Кулибин','Наблюдательный мастер ремонтного участка оружейной. Говорит предметно, замечает мелочи, собирает механизмы из мусора.','Найти пропавшую деталь и закончить заказ.')}
LOCS=['01_cell.png','02_yard_night.png','03_kitchen.png','04_corridor.png','05_shower.png','07_cellblock.png','06_armory.png','08_library.png','09_chapel.png','10_isolation.png','11_theatre.png','12_underpass.png']
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
'Ржавый робот-бюрократ.':'Охранник оружейной, человек и формалист.',
'робот-бюрократ':'охранник-формалист','робота':'охранника','робот':'охранник',
'Робот':'Охранник','завис, пошёл дымом и перешёл в режим энергосбережения':'растерялся, запросил письменное разъяснение и оставил пост',
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
    ignore={'.git','.venv','.venv_build','dist','output','__pycache__','.pytest_cache','saves','logs','первая половина','.github'}
    for p in root.iterdir():
        if p.name in ignore or p.suffix=='.zip' or p.name in('settings.json','achievements.json','.env'):continue
        if p.is_dir():shutil.copytree(p,dest/p.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
        else:shutil.copy2(p,dest/p.name)
    # Safe default configuration: personal .env never enters a public build.
    (dest/'.env').write_text('CHAT_FAST_MODE=true\nGOSSIP_ENABLED=true\n',encoding='utf8')
    for p in dest.glob('*.py'):p.write_text(transform_source(p.read_text(encoding='utf8')),encoding='utf8')
    data=json.loads((dest/'npcs.json').read_text(encoding='utf8'))
    report=[]
    for k,(file,name,role,goal) in NPC.items():
        data[k].update(name=name,role=role,goal=goal,portrait=k)
        # Keep full uploaded PNGs; legacy JPEGs serve existing loaders.
        target=dest/'image'/'characters'/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/file,target)
        with Image.open(src/file) as im:
            im=ImageOps.exif_transpose(im).convert('RGB')
            ImageOps.fit(im,(800,1264),method=Image.Resampling.LANCZOS,centering=(.5,.35)).save(dest/'assets'/(k+'.jpg'),quality=94)
        report.append({'id':k,'name':name,'file':str(target.relative_to(dest)),'home':data[k]['home']})
    (dest/'npcs.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    for i,file in enumerate(LOCS):
        target=dest/'image'/'locations'/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/file,target)
        with Image.open(src/file) as im:
            im=ImageOps.exif_transpose(im).convert('RGB')
            ImageOps.fit(im,(2560,1440),method=Image.Resampling.LANCZOS).save(dest/'assets'/('loc_%d.jpg'%i),quality=94)
    # Move crafting to the armory; keep tea accounts in the library.
    p=dest/'core.py';s=p.read_text(encoding='utf8')
    s=re.sub(r"^    if L==6:add\('work_shift'.*\n",'',s,flags=re.M)
    s=s.replace("if L==7:add('work_shift'","if L==6:add('work_shift'")
    s=s.replace("if L==7:add('exchange','Биржа чая',20,'coin');add('order_shiv'","if L==7:add('exchange','Биржа чая',20,'coin')\n    if L==6:add('order_shiv'")
    p.write_text(s,encoding='utf8');ast.parse(s)
    # Human guard: remove robot-only rendering while keeping his heavy fighting style.
    p=dest/'fightui.py';s=p.read_text(encoding='utf8').replace("robot=f.kind=='enemy' and s.k=='str'","robot=False");p.write_text(s,encoding='utf8')
    (dest/'VERSION.txt').write_text('Tyuryaga v12 / New Faces / Art integration\n',encoding='utf8')
    (dest/'ART_MANIFEST_v12.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    (dest/'CHANGELOG_v12.md').write_text('# v12 — Новые лица\n12 портретов и 12 фонов подключены ко всем существующим загрузчикам, включая карту, диалоги и арены. Исходные PNG — image/, совместимые JPEG — assets/. Внутренние ID сохранены. Два героя (Зинаида и Мать-Смотрительница) сохранены со старой графикой для целостности сюжета. Назначение новых героев — авторская интерпретация по именам файлов, не результат визуального распознавания.\nНовые роли: Решёткин, Байкал, Шкет, Анальгин, Цепи, Бумажкина, Кулибин, Бачок, Тень, Турник, Сократ, Курсант.\nПромпты получают новые имена и роли, сюжетные строки адаптированы, ремонт перенесён в оружейную-мастерскую. В старых сохранениях исторические записи не переписываются. Рекомендуется новая игра; перед переносом saves сделайте копию.\nОграничения: автоматическая текстовая адаптация не заменяет редактуру каждого диалога; Windows, визуальное кадрирование и локальная модель требуют живой проверки.\n',encoding='utf8')
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
    for p in dest.glob('*.py'):ast.parse(p.read_text(encoding='utf8'))
    n=json.loads((dest/'npcs.json').read_text(encoding='utf8'))
    assert len(n)==14 and len(NPC)==12
    for k,v in n.items():
        assert 0<=v['home']<12
        assert all(c in n for c in v['contacts'])
        assert (dest/'assets'/(v['portrait']+'.jpg')).exists()
    for i in range(12):
        with Image.open(dest/'assets'/('loc_%d.jpg'%i)) as im:assert im.size==(2560,1440)
    code="import json,core,world;from story_data import SCENES;n=json.load(open('npcs.json',encoding='utf8'));w=world.World(n);assert n['gvo']['name']=='Решёткин';assert n['str']['name']=='Цепи';assert len(SCENES)>=90;assert 'сюжет' in __import__('ai').PROMPT;print('v12 structural smoke test OK')"
    subprocess.run([sys.executable,'-c',code],cwd=dest,check=True)

if __name__=='__main__':build()
