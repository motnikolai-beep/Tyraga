"""Local friends/enemies, independent zone news and the saved player dossier. No GUI or model."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import core,meta,profile,social,zone_news
from story_data import SCENES
from world import World
NP=json.loads((ROOT/'npcs.json').read_text(encoding='utf8'))

def mk(loc=0,day=1,origin='paper'):
    w=World(NP,meta.new_state(NP,origin=origin),seed=7)
    w.s['loc']=loc;w.s['day']=day;core.C(w)['abs']=day*1440+12*60
    return w

def choose(w,scene,index,ok=True):
    choice=SCENES[scene]['nodes']['start']['ch'][index]
    rng=type('R',(),{'randint':lambda s,a,b:20 if ok else 1})()
    return core.resolve_choice(w,choice,rng=rng)

class Friend(unittest.TestCase):
    def test_friend_local_only_and_companion_preferred(self):
        w=mk();w.s['relations'].update(zub=42,kol=65)
        self.assertEqual(social.friend(w),'kol')
        w.s['companion']='zub';self.assertEqual(social.friend(w),'zub')
        w.s['loc']=2;self.assertIsNone(social.friend(w))
        w.s['loc']=0;w.s['relations']['zub']=39;self.assertEqual(social.friend(w),'kol')
        w.s['relations']['kol']=0;self.assertIsNone(social.friend(w))

    def test_search_friend_moves_real_items_not_money_and_can_retrieve(self):
        w=mk();w.s['relations']['kol']=40;w.s['companion']='kol'
        core.C(w)['inv'].update(shiv=2,phone=1)
        w.s['cig']=11
        core.C(w)['pending'].append({'t':'scene','id':'shmon'})
        offer=core.pop_pending(w)
        self.assertEqual(offer['id'],'friend_search')
        self.assertEqual(offer['vars']['friend_id'],'kol')
        self.assertEqual(core.C(w)['pending'][0]['id'],'shmon')
        out=choose(w,'friend_search',0)
        self.assertTrue(any('3' in line for line in out['lines']))
        self.assertEqual(core.contraband(w),0)
        self.assertEqual(core.stash_get(w,0)['shiv'],2)
        self.assertEqual(core.stash_get(w,0)['phone'],1)
        self.assertEqual(w.s['cig'],11)
        self.assertFalse(core.C(w)['pending'])
        self.assertTrue(any(e['kind']=='friend_help' for e in w.s['events']))
        core.stash_move(w,0,'shiv',1,put=False)
        self.assertEqual(core.C(w)['inv']['shiv'],1)
        self.assertIn('Свои и чужие',dict(core.journal(w)))

    def test_refusal_gives_normal_search_without_recursion(self):
        w=mk();w.s['relations']['zub']=40
        core.C(w)['pending'].append({'t':'scene','id':'shmon'})
        self.assertEqual(core.pop_pending(w)['id'],'friend_search')
        choose(w,'friend_search',1)
        self.assertEqual(core.pop_pending(w)['id'],'shmon')
        core.C(w)['pending'].append({'t':'scene','id':'shmon'})
        self.assertEqual(core.pop_pending(w)['id'],'shmon') # once/day
        w.s['day']+=1
        core.C(w)['pending'].append({'t':'scene','id':'shmon'})
        self.assertEqual(core.pop_pending(w)['id'],'friend_search')

    def test_no_remote_or_low_relation_protection(self):
        for loc,rel in ((2,45),(0,39)):
            w=mk(loc=loc);w.s['relations']['zub']=rel;w.s['companion']='zub'
            core.C(w)['pending'].append({'t':'scene','id':'shmon'})
            self.assertEqual(core.pop_pending(w)['id'],'shmon')

class Enemy(unittest.TestCase):
    def test_local_enemy_denounces_carried_contraband_once_per_day(self):
        w=mk();w.s['relations']['zub']=-45;core.C(w)['inv']['shiv']=1
        self.assertTrue(social.arrival(w));self.assertFalse(social.arrival(w))
        self.assertEqual(core.C(w)['pending'][0]['id'],'enemy_denunciation')
        self.assertEqual(core.C(w)['pending'][0]['vars']['enemy'],NP['zub']['name'])
        self.assertEqual(w.s['events'][-1]['kind'],'denunciation')
        self.assertFalse(w.s['events'][-1]['public'])
        self.assertEqual(set(w.s['events'][-1]['witnesses']),set(w.witnesses()))
        self.assertEqual(core.pop_pending(w)['id'],'enemy_denunciation')
        choose(w,'enemy_denunciation',3)
        self.assertEqual(core.pop_pending(w)['id'],'shmon')
        self.assertEqual(core.C(w)['inv']['shiv'],1)  # no items silently removed
        w.s['day']+=1;self.assertTrue(social.arrival(w))

    def test_enemy_cannot_report_remote_hidden_or_reconciled(self):
        w=mk();w.s['relations']['zub']=-45;core.C(w)['inv']['shiv']=2
        w.s['loc']=2;self.assertFalse(social.arrival(w))
        w.s['loc']=0;core.stash_move(w,0,'shiv',2)
        self.assertFalse(social.arrival(w))
        core.stash_move(w,0,'shiv',1,False)
        w.s['relations']['zub']=-39;self.assertFalse(social.arrival(w))
        self.assertEqual(len(w.s['events']),0)

    def test_friend_can_foil_a_denunciation_too(self):
        w=mk();w.s['relations'].update(zub=-60,kol=45);w.s['companion']='kol'
        core.C(w)['inv']['shiv']=1
        social.arrival(w);self.assertEqual(core.pop_pending(w)['id'],'enemy_denunciation')
        self.assertTrue(core.req_ok(w,SCENES['enemy_denunciation']['nodes']['start']['ch'][0]['req']))
        choose(w,'enemy_denunciation',0)
        self.assertEqual(core.contraband(w),0)
        self.assertEqual(core.stash_get(w,0)['shiv'],1)
        self.assertFalse(core.C(w)['pending'])

    def test_bribe_or_successful_check_avoids_search(self):
        for index in (1,2):
            w=mk();w.s['relations']['zub']=-60;core.C(w)['inv']['phone']=1
            social.arrival(w);core.C(w)['pending'].clear()
            w.s['cig']=8
            choose(w,'enemy_denunciation',index)
            self.assertFalse(core.C(w)['pending'])
            self.assertEqual(w.s['cig'],4 if index==1 else 8)
            self.assertEqual(core.C(w)['inv']['phone'],1)
        w=mk();choose(w,'enemy_denunciation',2,ok=False)
        self.assertEqual(core.pop_pending(w)['id'],'shmon')

class News(unittest.TestCase):
    def test_daily_news_happens_without_the_player_and_only_once(self):
        w=mk(day=2);w.s['loc']=11
        event=zone_news.morning(w)
        self.assertIsNotNone(event)
        self.assertEqual(event['kind'],'zone_news')
        self.assertFalse(event['public'])
        self.assertEqual(zone_news.morning(w),None)
        self.assertEqual(len(core.C(w)['news']),1)
        self.assertNotIn('Игрок',event['text'])
        self.assertIn('Слухи зоны',dict(core.journal(w)))
        self.assertEqual(len(w.s['chron']),0)  # NPC news must not become the player's deed
        self.assertTrue(core.C(w)['npc_relations'])
        self.assertEqual(len(w.s['history']),0) # requires neither chat nor LLM runtime

    def test_witnesses_know_fact_and_contacts_hear_a_rumor(self):
        w=mk(day=2)
        e=zone_news.morning(w);a,b=core.C(w)['news'][0]['actors']
        self.assertIn(e['id'],[x['id'] for x in w.known(a)])
        self.assertIn(e['id'],[x['id'] for x in w.known(b)])
        outsider=next(k for k in NP if k not in e['witnesses'] and w.heard(k))
        self.assertNotIn(e['id'],[x['id'] for x in w.known(outsider)])
        self.assertTrue(any(g['root']==e['id'] and g['verified'] is False for g in w.heard(outsider)))
        self.assertEqual(w.context(outsider)['known_facts'],[])
        self.assertIn('npc_relations',w.context(a))
        self.assertIn(e['text'],zone_news.journal(w)[0])

    def test_sleep_creates_next_news_and_is_bounded(self):
        w=mk(day=2);w.s['loc']=0
        core.C(w)['abs']=w.s['day']*1440+23*60
        core.sleep(w)
        self.assertEqual(len(core.C(w)['news']),1)
        for _ in range(19):
            core.C(w)['abs']=w.s['day']*1440+23*60
            core.sleep(w)
        self.assertEqual(len(core.C(w)['news']),15)
        self.assertEqual(len(zone_news.journal(w)),7)
        self.assertTrue(all(e['kind']=='zone_news' for e in w.s['events'] if e['kind']=='zone_news'))

class Dossier(unittest.TestCase):
    def test_new_game_saves_backstory_and_player_context(self):
        for origin in profile.ORIGINS:
            w=mk(origin=origin)
            self.assertEqual(w.s['profile']['origin'],origin)
            self.assertEqual(profile.origin(w),profile.ORIGINS[origin])
            self.assertIn(profile.ORIGINS[origin][0],profile.report(w))
            self.assertEqual(w.context('kol')['player']['прошлое'],profile.ORIGINS[origin][2])
            self.assertIn('СЫТОСТЬ',profile.report(w))
            self.assertIn('КАРМА',profile.report(w))
            self.assertIn('ОТНОШЕНИЯ',profile.report(w))
            self.assertIn('ВЕЩИ',profile.report(w))

    def test_legacy_save_has_no_invented_history_and_nickname_changes(self):
        w=mk();del w.s['profile'];w.s['relations']['kol']=50
        self.assertEqual(profile.origin(w)[0],'Дело не указано')
        self.assertIn(NP['kol']['name'],profile.report(w))
        self.assertEqual(profile.nickname(w),'Новенький')
        core.C(w)['counters']['duel_win']=5
        self.assertEqual(profile.nickname(w),'Кулак')
        core.C(w)['flags']['snitch']=True
        self.assertEqual(profile.nickname(w),'Доносчик')

    def test_player_art_exists_and_matches_profile_loader(self):
        from PIL import Image
        with Image.open(ROOT/'assets/player.jpg') as im:self.assertEqual(im.size,(800,1264))
        if (ROOT/'art_4k/characters/19_hero.jpg').exists():
            with Image.open(ROOT/'art_4k/characters/19_hero.jpg') as im:self.assertEqual(im.size,(2880,3840))

if __name__=='__main__':unittest.main()
