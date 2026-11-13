"""Non-monetized prison gear: four rarities, three slots, safe bounded combat stats.

Boxes use only in-game rubles/earned event rewards. This module never sells real-money
currency or silently equips drops. Old gear and old saves remain authoritative until
players explicitly equip a new item.
"""
import core
RARITIES={'common':('Обычное',60),'rare':('Редкое',28),'epic':('Эпичное',10),'legendary':('Легендарное',2)}
ITEMS={
 'wrap':('Бинты из простыни','common','weapon',3,0,0),
 'shiv':('Заточка с меткой','rare','weapon',8,0,0),
 'pipe':('Гладкая рукоять','epic','weapon',11,0,0),
 'master_shiv':('Заточка мастера','legendary','weapon',14,0,0),
 'patch':('Латаная телогрейка','common','armor',0,1,0),
 'vest':('Плотный ватник','rare','armor',0,2,0),
 'reinforced':('Усиленная подкладка','epic','armor',0,3,0),
 'keeper':('Старая броня мастера','legendary','armor',0,4,0),
 'thread':('Шнурок на память','common','trinket',0,0,.02),
 'token':('Жетон цеха','rare','trinket',0,0,.04),
 'ring':('Кольцо из гайки','epic','trinket',0,0,.06),
 'medallion':('Жетон старожила','legendary','trinket',0,0,.08),
}
SLOTS=('weapon','armor','trinket')

def state(w):return core.C(w).setdefault('gear20',{'items':{},'equipped':{},'scrap':0,'boxes':0,'opened':0})

def give(w,item):
    if item not in ITEMS:raise ValueError('Нет такого предмета')
    r=state(w)
    if item in r['items']:
        amount={'common':1,'rare':2,'epic':3,'legendary':5}[ITEMS[item][1]]
        r['scrap']+=amount
        return 'Дубликат: '+ITEMS[item][0]+' → детали ×'+str(amount)
    r['items'][item]=0
    return 'Найдено: '+ITEMS[item][0]+' ('+RARITIES[ITEMS[item][1]][0]+')'

def award_box(w):state(w)['boxes']+=1

def buy_box(w):
    if w.s['rub']<25:raise ValueError('Нужно 25 игровых рублей; покупок за реальные деньги нет')
    w.s['rub']-=25;award_box(w)
    w.event('gear20_box','Игрок обменял 25 игровых рублей на ящик снаряжения.',[])
    return 'Ящик получен. Откройте его в мастерской снаряжения.'

def open_box(w):
    r=state(w)
    if r['boxes']<1:raise ValueError('Ящиков нет')
    r['boxes']-=1;r['opened']+=1
    # 60/28/10/2 percent per box; every 10th box is at least rare.
    roll=w.rng.randrange(100)
    rarity='common' if roll<60 else 'rare' if roll<88 else 'epic' if roll<98 else 'legendary'
    if r['opened']%10==0 and rarity=='common':rarity='rare'
    pool=[id for id,spec in ITEMS.items() if spec[1]==rarity]
    item=w.rng.choice(pool)
    result=give(w,item)
    bonus=w.rng.randrange(3)
    if bonus==0:
        w.s['cig']+=2;extra='2 сигареты'
    elif bonus==1:
        core.C(w)['inv']['tea']=core.C(w)['inv'].get('tea',0)+1;extra='пачка чая'
    else:
        w.s['hp']=min(100,w.s['hp']+5);extra='перевязка (+5 HP)'
    w.event('gear20_open','Игрок открыл внутриигровой ящик: '+ITEMS[item][0]+', '+extra+'.',[])
    return result+'; дополнительно: '+extra

def equip(w,item):
    r=state(w)
    if item not in r['items']:raise ValueError('Предмета нет у вас')
    slot=ITEMS[item][2]
    if r['equipped'].get(slot)==item:return 'Уже надето: '+ITEMS[item][0]
    r['equipped'][slot]=item
    return 'Надето: '+ITEMS[item][0]

def unequip(w,slot):
    if slot not in SLOTS:raise ValueError('Нет такого слота')
    r=state(w)
    if slot not in r['equipped']:return 'Этот слот уже пуст.'
    r['equipped'].pop(slot)
    return 'Слот освобождён.'

def upgrade(w,item):
    r=state(w)
    if item not in r['items']:raise ValueError('Предмета нет у вас')
    lv=r['items'][item]
    if lv>=3:raise ValueError('Предел улучшения: +3')
    need=lv+1;rub=8*need
    if r['scrap']<need or w.s['rub']<rub:raise ValueError('Нужно %d деталей и %d игровых рублей'%(need,rub))
    r['scrap']-=need;w.s['rub']-=rub;r['items'][item]=lv+1
    w.event('gear20_upgrade','Игрок улучшил '+ITEMS[item][0]+' до +'+str(lv+1)+'.',[])
    return ITEMS[item][0]+' улучшено до +'+str(lv+1)

def stats(w,base):
    """Augment equipment13.stats at the one point consumed by FightEngine."""
    out=base.copy();r=state(w)
    for slot,item in r['equipped'].items():
        if slot not in SLOTS or item not in r['items'] or ITEMS.get(item,('', '',None))[2]!=slot:continue
        name,rarity,_,dmg,armor,accuracy=ITEMS[item];lv=min(3,r['items'][item])
        if slot=='weapon':
            out['damage']=min(34,16+dmg+lv);out['weapon']='gloves' if item=='wrap' else 'shiv'
            out['name']=name+' +'+str(lv) if lv else name
        if slot=='armor':out['armor']=min(12,out['armor']+armor+lv)
        if slot=='trinket':out['accuracy']=min(.90,out['accuracy']+accuracy+lv*.01)
    return out

def journal(w):
    r=state(w);eq=[slot+': '+ITEMS[item][0] for slot,item in r['equipped'].items() if item in ITEMS]
    return ['Вещи: %d · ящики: %d · детали: %d. Надето: %s.'%(len(r['items']),r['boxes'],r['scrap'],', '.join(eq) or 'ничего'),
            'Шансы ящика: обычное 60%%, редкое 28%%, эпичное 10%%, легендарное 2%%; каждый десятый — не ниже редкого. Только игровые рубли и награды.']
