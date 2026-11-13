"""Local consequences of friendship and enmity. NPCs do not teleport or see hidden stashes.

Relationships are evaluated *now*, not from sticky friend_/enemy_ flags: reconciliation matters.
A companion is preferred when present, but is not a magical remote bodyguard.
"""
import core

FRIEND=40
ENEMY=-40

def friend(w):
    local=[k for k in w.witnesses() if w.s['relations'].get(k,0)>=FRIEND]
    return w.s.get('companion') if w.s.get('companion') in local else (max(local,key=lambda k:w.s['relations'][k]) if local else None)

def enemy(w):
    local=[k for k in w.witnesses() if w.s['relations'].get(k,0)<=ENEMY]
    return min(local,key=lambda k:w.s['relations'][k]) if local else None

def arrival(w):
    """A local enemy denounces visible contraband once per day, never a stash or a distant player."""
    c=core.C(w);k=enemy(w)
    if not k or not core.contraband(w):return False
    key=f'{w.s["day"]}:{k}'
    if key in c['denounced']:return False
    c['denounced'].append(key);c['denounced']=c['denounced'][-40:]
    w.event('denunciation',w.npcs[k]['name']+' заметил запрещённые вещи у игрока и позвал охрану.',w.witnesses(),public=False)
    c['pending'].append({'t':'scene','id':'enemy_denunciation','vars':{'enemy':w.npcs[k]['name']}})
    core.say(w,'⚠ '+w.npcs[k]['name']+' донёс охране о ваших вещах.')
    return True

def prepare_search(w,p):
    """Offer help before the search, once a day, if an actual friend is locally present.

    Protected searches (refused help / denunciation) must not recurse.
    """
    c=core.C(w)
    if p.get('protected') or c['friend_search_day']==w.s['day']:return p
    k=friend(w)
    if not k:return p
    c['friend_search_day']=w.s['day']
    c['pending'].insert(0,dict(p,protected=True))
    return {'t':'scene','id':'friend_search','vars':{'friend':w.npcs[k]['name'],'friend_id':k}}

def hide(w,k):
    """Friend hides carried contraband in the current room. It remains owned and can be retrieved."""
    if k not in w.witnesses() or w.s['relations'].get(k,0)<FRIEND:return []
    c=core.C(w);inv=c['inv'];st=core.stash_get(w,w.s['loc']);count=0
    for item in ('shiv','phone'):
        n=inv.get(item,0)
        if n:inv[item]=0;st[item]=st.get(item,0)+n;count+=n
    if count:
        w.event('friend_help',w.npcs[k]['name']+' помог спрятать вещи при обыске.',[k])
        return ['Спрятано предметов: %d. Их можно забрать из схрона.'%count]
    return ['Запрещённых вещей при вас нет.']

def use_help(w,k):
    """A decision at the friend-search scene: move contraband then cancel only this search."""
    c=core.C(w)
    if not c['pending'] or c['pending'][0].get('id')!='shmon' or not c['pending'][0].get('protected'):return []
    if k not in w.witnesses() or w.s['relations'].get(k,0)<FRIEND:return []
    out=hide(w,k)
    c['pending'].pop(0)
    return out

def journal(w):
    c=core.C(w)
    rows=['Напарник: %s (помогает только рядом и при отношении ≥ +%d)'%(w.npcs[w.s['companion']]['name'] if w.s.get('companion') in w.npcs else 'не выбран',FRIEND)]
    rows+=['Друг рядом: '+w.npcs[k]['name'] for k in w.witnesses() if w.s['relations'].get(k,0)>=FRIEND]
    rows+=['Враг рядом: '+w.npcs[k]['name']+' (может донести, если увидит запрещённое)' for k in w.witnesses() if w.s['relations'].get(k,0)<=ENEMY]
    return rows
