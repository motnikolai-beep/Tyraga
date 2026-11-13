"""v13 equipment and combat training. All prices/effects are engine-owned; the LLM cannot grant upgrades.

Compatible with old saves: existing gear.damage / armor remain authoritative; optional upgrades
are lazily initialized. A weapon is not a consumable inventory shiv (those can be hidden at a search).
"""
import core

WEAPONS={
 'fist':{'name':'Кулаки','damage':16,'accuracy':.72,'speed':1.00,'icon':'fist'},
 'gloves':{'name':'Бинты бойца','damage':18,'accuracy':.79,'speed':1.10,'icon':'gloves'},
 'shiv':{'name':'Заточка','damage':24,'accuracy':.72,'speed':.96,'icon':'shiv'},
}
UPGRADES={
 'power':('Техника удара','gloves',18,'+5% силы удара за уровень; F — рывок'),
 'guard':('Крепкая стойка','armor',16,'+1 к броне за уровень'),
 'breath':('Дыхание','boots',16,'+8% восстановления сил за уровень'),
}
MAX_LEVEL=3

def weapon(w):
    g=w.s['gear'];kind=g.get('weapon_type')
    if kind in WEAPONS:return kind
    # Old save: it may already contain a bought shiv or a crafted weapon with custom damage.
    if g.get('damage',16)>20 or g.get('weapon')=='Заточка':return 'shiv'
    if g.get('weapon')=='Бинты бойца':return 'gloves'
    return 'fist'

def levels(w):return w.s.setdefault('combat_upgrades',{'power':0,'guard':0,'breath':0})

def stats(w):
    g=w.s['gear'];kind=weapon(w);lv=levels(w)
    return {'weapon':kind,'name':g.get('weapon',WEAPONS[kind]['name']),
            'damage':g.get('damage',WEAPONS[kind]['damage']),
            'armor':min(12,g.get('armor',2)+lv.get('guard',0)),
            'speed':max(.8,min(1.2,g.get('speed',WEAPONS[kind]['speed']))),
            'power':1.0+min(MAX_LEVEL,lv.get('power',0))*.05,
            'regen':1.0+min(MAX_LEVEL,lv.get('breath',0))*.08,
            'accuracy':g.get('accuracy',WEAPONS[kind]['accuracy'])}

def cost(w,kind):
    if kind in UPGRADES:
        level=levels(w).get(kind,0)
        if level>=MAX_LEVEL:return None
        return core.price(w,UPGRADES[kind][2]*(level+1))
    return core.price(w,{'knife':40,'gloves':28,'armor':35,'heal':10}[kind])

def buy(w,kind):
    if kind not in (*UPGRADES,'knife','gloves','armor','heal'):raise ValueError('Нет такого улучшения')
    if kind=='armor' and w.s['gear'].get('armor',2)>=7:raise ValueError('Телогрейка уже куплена')
    if kind in ('knife','gloves') and weapon(w)==('shiv' if kind=='knife' else 'gloves'):raise ValueError('Это оружие уже в руках')
    price=cost(w,kind)
    if price is None:raise ValueError('Максимальный уровень тренировки достигнут')
    if w.s['rub']<price:raise ValueError('Недостаточно рублей: нужно %d ₽'%price)
    w.s['rub']-=price
    if kind in UPGRADES:levels(w)[kind]=levels(w).get(kind,0)+1
    elif kind in ('knife','gloves'):
        spec=WEAPONS['shiv' if kind=='knife' else 'gloves']
        w.s['gear'].update(weapon=spec['name'],weapon_type=spec['icon'],damage=spec['damage'],accuracy=spec['accuracy'],speed=spec['speed'])
    elif kind=='armor':w.s['gear']['armor']=7
    elif kind=='heal':w.s['hp']=min(100,w.s['hp']+35)
    w.event('purchase','Покупка: '+kind,w.witnesses())
    return price

def offers(w):
    """(id, label, icon, price, reason) for the equipment window."""
    rows=[]
    for kind,label,icon in [('knife','Заточка · урон 24','shiv'),('gloves','Бинты бойца · точнее и быстрее','gloves'),('armor','Телогрейка · броня 7','armor'),('heal','Перевязка · +35 HP','bandage')]:
        try:
            p=cost(w,kind);reason='Уже куплено' if (kind=='armor' and w.s['gear'].get('armor',2)>=7) or (kind=='knife' and weapon(w)=='shiv') or (kind=='gloves' and weapon(w)=='gloves') else ''
        except (ValueError,KeyError):p=None;reason='Недоступно'
        rows.append((kind,label,icon,p,reason or ('Недостаточно ₽' if p is not None and w.s['rub']<p else '')))
    for kind,(label,icon,_base,benefit) in UPGRADES.items():
        level=levels(w).get(kind,0);p=cost(w,kind)
        rows.append((kind,'%s %d/%d · %s'%(label,level,MAX_LEVEL,benefit),icon,p,
                     'Предел достигнут' if p is None else 'Недостаточно ₽' if p is not None and w.s['rub']<p else ''))
    return rows
