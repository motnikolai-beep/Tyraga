"""v12 «Бывшие»: свергнутый босс остаётся в зоне, помнит обиду и может прийти за реваншем.

Только логика, без окна. Тест работает и в исходниках, и в готовой сборке, поэтому героев называет по id.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cast
import core
import fight
import former
import lore
import meta
from story_data import SCENES, available
from world import World

NP = json.loads((ROOT / 'npcs.json').read_text(encoding='utf8'))
BOSSES = sorted(k for k, v in NP.items() if v['boss'])
ACH = {row[0]: row[3] for row in meta.ACH}


class Dice:
    """Кубик, который всегда выпадает одной гранью: 20 — успех, 1 — провал."""
    def __init__(self, value):
        self.value = value

    def randint(self, a, b):
        return self.value


def mk(day=3, loc=0):
    w = World(NP, meta.new_state(NP, 'normal'), seed=3)
    w.s['day'] = day
    w.s['loc'] = loc
    core.C(w)['abs'] = day * 1440 + 10 * 60
    return w


def pick(w, sid, index, ok=True):
    choice = SCENES[sid]['nodes']['start']['ch'][index]
    return core.resolve_choice(w, choice, game_ok=ok, rng=Dice(20 if ok else 1))


def night(w):
    """Дожить до отбоя и проснуться утром следующего дня."""
    core.C(w)['abs'] = w.s['day'] * 1440 + 23 * 60
    core.sleep(w)


def fall(boss, day=3, will=True):
    """Мир, где босс свергнут, а игрок стоит в его локации; will — затаил ли он обиду."""
    w = mk(day, NP[boss]['home'])
    core.boss_down(w, boss)
    former.rec(w, boss).update(will=will, at=day + 1)
    core.C(w)['pending'].clear()
    core.C(w)['feed'].clear()
    return w


def call_out(boss):
    """Мир, где бывший уже позвал на разборку, а игрок стоит в его локации."""
    w = fall(boss)
    night(w)
    return w


class Data(unittest.TestCase):
    def test_every_boss_has_a_life_after_the_fall(self):
        self.assertEqual(sorted(former.EX), BOSSES)
        for boss, entry in former.EX.items():
            for field in ('was', 'took', 'role', 'line', 'peace', 'mock', 'tell', 'call'):
                self.assertTrue(entry[field].strip(), (boss, field))
            self.assertGreaterEqual(len(entry['role']), 80, boss)
            self.assertIn(cast.sex(boss), 'mf')
            self.assertIn(former.word(boss), ('бывший', 'бывшая'))
            self.assertIn(entry['was'], former.label(boss))

    def test_each_weakness_is_known_by_exactly_one_other_boss(self):
        self.assertEqual(sorted(former.KNOWS), BOSSES)
        self.assertEqual(sorted(former.KNOWS.values()), BOSSES)
        self.assertTrue(all(a != b for a, b in former.KNOWS.items()))

    def test_scenes_are_well_formed(self):
        effects = {'cig', 'rel', 'karma', 'caste', 'rep', 'peace', 'mock', 'learn_weak', 'duel', 'duel_ambush', 'revenge_off'}
        for boss in BOSSES:
            for sid in ('ex_' + boss, 'revenge_' + boss):
                scene = SCENES[sid]
                self.assertNotEqual(scene['title'], sid)
                node = scene['nodes']['start']
                self.assertEqual(node['who'], boss, sid)
                self.assertGreaterEqual(len(node['text']), 80, sid)
                self.assertEqual(len(node['ch']), 4, sid)
                for choice in node['ch']:
                    self.assertTrue(set(choice['req']) <= {'cig', 'weak'}, sid)
                    for result in (choice['ok'], choice['fail']):
                        self.assertIsNone(result['goto'])
                        self.assertTrue(set(result['fx']) <= effects, (sid, set(result['fx']) - effects))
                        self.assertTrue(all(k in NP for k in result['fx'].get('rel', {})), sid)
                        for key in ('peace', 'mock', 'duel', 'duel_ambush', 'revenge_off'):
                            self.assertIn(result['fx'].get(key, boss), (boss,), (sid, key))
            self.assertTrue(SCENES['ex_' + boss]['story'])
            self.assertEqual(SCENES['ex_' + boss]['trig'], {'loc': NP[boss]['home'], 'ousted': boss})
            self.assertFalse(SCENES['revenge_' + boss]['story'])
            self.assertTrue(SCENES['revenge_' + boss]['rep'])

    def test_names_in_texts_match_the_built_game(self):
        """В готовой сборке имена из таблицы падежей совпадают с именами героев; в исходниках старый состав ещё зовут по-старому."""
        self.assertEqual(sorted(cast.FORMS), sorted(NP))
        for key, row in cast.FORMS.items():
            self.assertEqual(len(row), 6, key)
            self.assertTrue(all(row), key)
        if (ROOT / 'ART_MANIFEST_v12.json').is_file():
            for key in NP:
                self.assertEqual(cast.nom(key), NP[key]['name'], key)
        self.assertEqual(len(cast.PLACES), 12)


class Stays(unittest.TestCase):
    def test_fallen_boss_stays_in_his_place_without_power(self):
        for boss in BOSSES:
            w = mk(loc=NP[boss]['home'])
            self.assertTrue(core.in_power(w, boss))
            self.assertEqual(core.max_hp(w, boss), 120)
            self.assertEqual(core.badge(w, boss), '')
            self.assertEqual(former.role(w, boss), NP[boss]['role'])
            core.boss_down(w, boss)
            self.assertIn(boss, w.witnesses())
            self.assertTrue(core.is_former(w, boss))
            self.assertFalse(core.in_power(w, boss))
            self.assertIsNone(core.boss_here(w))
            self.assertEqual(core.max_hp(w, boss), 90)
            self.assertEqual(core.badge(w, boss), former.word(boss))
            self.assertTrue(core.shown_name(w, boss).startswith(NP[boss]['name']))
            # ИИ получает прежний характер и то, кем герой стал
            role = former.role(w, boss)
            self.assertTrue(role.startswith(NP[boss]['role']))
            self.assertIn(former.EX[boss]['role'], role)
            self.assertFalse(any(a['id'] in ('scout_' + boss, 'weak_' + boss) for a in core.activities(w)))

    def test_ordinary_residents_are_never_former(self):
        w = mk()
        for key in NP:
            if key not in BOSSES:
                self.assertFalse(core.in_power(w, key))
                self.assertFalse(core.is_former(w, key))
                self.assertEqual(core.max_hp(w, key), 90)
                self.assertEqual(former.role(w, key), NP[key]['role'])

    def test_scene_after_the_fall_waits_in_his_place(self):
        for boss in BOSSES:
            w = mk(loc=NP[boss]['home'])
            self.assertNotIn('ex_' + boss, list(available(w)))
            core.boss_down(w, boss)
            self.assertIn('ex_' + boss, list(available(w)))
            other = (NP[boss]['home'] + 1) % 12
            self.assertNotIn('ex_' + boss, list(available(w, loc=other)))

    def test_journal_and_zone_know(self):
        w = fall('hleb', will=False)
        rows = dict(core.journal(w))['Бывшие боссы']
        self.assertEqual(len(rows), 1)
        self.assertIn(NP['hleb']['name'], rows[0])
        self.assertIn(former.label('hleb'), rows[0])
        self.assertTrue(any(NP['hleb']['name'] in line for line in lore.npc_lore(w, 'serg')))
        empty = dict(core.journal(mk()))['Бывшие боссы']
        self.assertEqual(len(empty), 1)   # подсказка, пока никто не свергнут

    def test_old_save_without_records_still_works(self):
        """Сохранение до v12: босс в списке свергнутых, записи о нём нет. Он появляется в зоне бывшим, без обиды."""
        w = mk(loc=0)
        core.C(w)['ousted'] = ['zub', 'graf']
        self.assertEqual(core.C(w)['ex'], {})
        self.assertIn('zub', w.witnesses())
        self.assertTrue(former.journal(w))
        self.assertTrue(former.role(w, 'zub'))
        self.assertIsInstance(lore.npc_lore(w, 'zub'), list)
        night(w)
        self.assertEqual(sorted(core.C(w)['ousted']), ['graf', 'zub'])
        self.assertFalse(former.due(w))
        self.assertFalse(former.rec(w, 'zub')['will'])


class AfterTheFall(unittest.TestCase):
    def test_peace(self):
        w = fall('kip')
        before = w.s['relations'].get('kip', 0)
        result = pick(w, 'ex_kip', 0, ok=True)
        self.assertTrue(result['ok'])
        rec = former.rec(w, 'kip')
        self.assertTrue(rec['peace'])
        self.assertFalse(rec['will'])
        self.assertGreater(w.s['relations']['kip'], before)
        self.assertTrue(ACH['ex_peace'](w))
        self.assertTrue(any('помирились' in line for line in lore.npc_lore(w, 'kip')))
        for _ in range(8):
            night(w)
        self.assertTrue(core.is_former(w, 'kip'))       # помирились — реванша не будет
        self.assertFalse(former.due(w))

    def test_failed_peace_changes_nothing(self):
        w = fall('kip')
        pick(w, 'ex_kip', 0, ok=False)
        self.assertFalse(former.rec(w, 'kip')['peace'])
        self.assertFalse(ACH['ex_peace'](w))

    def test_mockery_brings_revenge_closer(self):
        w = fall('cenz', will=False)
        former.rec(w, 'cenz')['at'] = w.s['day'] + 5
        caste = core.C(w)['caste']
        pick(w, 'ex_cenz', 1)
        rec = former.rec(w, 'cenz')
        self.assertTrue(rec['mock'])
        self.assertTrue(rec['will'])
        self.assertLessEqual(rec['at'], w.s['day'] + 2)
        self.assertEqual(core.C(w)['caste'], caste + 2)
        self.assertTrue(any('унизил' in line for line in lore.npc_lore(w, 'cenz')))

    def test_former_boss_tells_another_weakness(self):
        for boss in BOSSES:
            w = fall(boss)
            w.s['cig'] = 5
            other = former.KNOWS[boss]
            self.assertFalse(core.weak_known(w, other))
            result = pick(w, 'ex_' + boss, 2)
            self.assertTrue(core.weak_known(w, other), boss)
            self.assertEqual(w.s['cig'], 3)
            self.assertTrue(any('Слабость' in line for line in result['lines']), boss)
        w = fall('zub')
        w.s['cig'] = 1
        self.assertFalse(core.req_ok(w, SCENES['ex_zub']['nodes']['start']['ch'][2]['req']))


class Revenge(unittest.TestCase):
    def test_call_comes_in_the_morning_and_scene_starts_in_his_place(self):
        w = fall('polkan')                              # игрок во дворе, там же Полкан
        night(w)
        rec = former.rec(w, 'polkan')
        self.assertEqual(rec['revenge'], 'due')
        self.assertEqual(former.due(w), ['polkan'])
        self.assertIn('revenge_polkan', [p['id'] for p in core.C(w)['pending']])
        self.assertTrue(any('⚔' in line for line in core.C(w)['feed']))
        self.assertTrue(any(e['kind'] == 'revenge' and e['public'] for e in w.s['events']))
        self.assertTrue(any('⚔' in row for row in dict(core.journal(w))['Бывшие боссы']))
        self.assertTrue(any('разборку' in line for line in lore.npc_lore(w, 'polkan')))

    def test_scene_waits_until_the_player_comes(self):
        w = fall('polkan')
        w.s['loc'] = 0                                   # игрок ночует в камере
        night(w)
        self.assertEqual(former.rec(w, 'polkan')['revenge'], 'due')
        self.assertNotIn('revenge_polkan', [p['id'] for p in core.C(w)['pending']])
        core.C(w)['pending'].clear()
        core.travel(w, 1)
        self.assertIn('revenge_polkan', [p['id'] for p in core.C(w)['pending']])
        core.travel(w, 0)
        core.travel(w, 1)                                # второй раз сцена в очередь не встаёт
        self.assertEqual([p['id'] for p in core.C(w)['pending']].count('revenge_polkan'), 1)

    def test_only_one_call_a_day(self):
        w = fall('polkan')
        core.boss_down(w, 'hleb')
        former.rec(w, 'hleb').update(will=True, at=w.s['day'] + 1)
        night(w)
        self.assertEqual(len(former.due(w)), 1)

    def test_no_show_gives_the_power_back(self):
        w = fall('polkan')
        core.flag(w, 'yard_free')
        w.s['loc'] = 0
        night(w)                                         # утро: вызов
        caste = core.C(w)['caste']
        self.assertIsNone(core.turf_boss(w, 'smoke_break', 1))
        night(w)                                         # не пришли до отбоя
        self.assertTrue(core.in_power(w, 'polkan'))
        self.assertNotIn('polkan', core.C(w)['ousted'])
        self.assertEqual(core.C(w)['caste'], caste - 8)
        self.assertEqual(core.turf_boss(w, 'smoke_break', 1), 'polkan')     # его правила вернулись
        self.assertFalse(core.has(w, 'yard_free'))
        self.assertTrue(ACH['boss_back'](w))
        self.assertTrue(any(e['kind'] == 'boss_back' for e in w.s['events']))
        self.assertFalse(any(p['id'] == 'revenge_polkan' for p in core.C(w)['pending']))
        self.assertTrue(any(NP['polkan']['name'] in row for row in dict(core.journal(w))['Бывшие боссы']))
        self.assertTrue(any('власть' in line for line in lore.npc_lore(w, 'zina')))
        self.assertEqual(core.badge(w, 'polkan'), '')

    def test_accepted_fight_is_a_boss_fight(self):
        w = call_out('graf')
        result = pick(w, 'revenge_graf', 0)
        self.assertTrue(result['lines'])
        first = core.C(w)['pending'][0]
        self.assertEqual((first['t'], first['k'], first['ambush']), ('fight', 'graf', False))
        self.assertTrue(former.revenge_now(w, 'graf'))
        engine = fight.FightEngine(w, 'graf', seed=1)
        self.assertTrue(engine.boss)
        self.assertTrue(engine.revenge)
        self.assertEqual(engine.mx, 120)

    def test_won_revenge_breaks_him_for_good(self):
        w = call_out('graf')
        pick(w, 'revenge_graf', 0)
        caste = core.C(w)['caste']
        engine = fight.FightEngine(w, 'graf', seed=1)
        engine.finish_fight('Победа', 'Нокаут')
        engine.finish()
        rec = former.rec(w, 'graf')
        self.assertEqual(rec['revenge'], 'won')
        self.assertTrue(core.is_former(w, 'graf'))
        self.assertEqual(core.C(w)['caste'], caste + 6)
        self.assertTrue(ACH['revenge_won'](w))
        self.assertFalse(former.revenge_now(w, 'graf'))
        for _ in range(6):
            night(w)
        self.assertTrue(core.is_former(w, 'graf'))
        self.assertEqual(former.rec(w, 'graf')['revenge'], 'won')

    def test_lost_revenge_gives_the_power_back(self):
        for outcome in ('Поражение', 'Ничья', 'Отступление'):
            w = call_out('graf')
            pick(w, 'revenge_graf', 0)
            engine = fight.FightEngine(w, 'graf', seed=1)
            engine.finish_fight(outcome, '')
            engine.finish()
            self.assertTrue(core.in_power(w, 'graf'), outcome)
            self.assertEqual(former.rec(w, 'graf')['revenge'], 'back')

    def test_talking_it_out(self):
        w = call_out('mat')
        result = pick(w, 'revenge_mat', 1, ok=True)
        self.assertTrue(result['ok'])
        rec = former.rec(w, 'mat')
        self.assertTrue(rec['peace'])
        self.assertEqual(rec['revenge'], 'off')
        night(w)
        self.assertTrue(core.is_former(w, 'mat'))
        # слова не помогли — он бьёт первым
        w = call_out('mat')
        pick(w, 'revenge_mat', 1, ok=False)
        first = core.C(w)['pending'][0]
        self.assertEqual((first['t'], first['k'], first['ambush']), ('fight', 'mat', True))

    def test_buying_off_and_the_weak_spot(self):
        w = call_out('str')
        w.s['cig'] = 10
        caste = core.C(w)['caste']
        pick(w, 'revenge_str', 2)
        self.assertEqual(w.s['cig'], 4)
        self.assertEqual(core.C(w)['caste'], caste - 3)
        self.assertEqual(former.rec(w, 'str')['revenge'], 'off')
        night(w)
        self.assertTrue(core.is_former(w, 'str'))
        # слабое место: вариант доступен, только если слабость известна
        w = call_out('str')
        option = SCENES['revenge_str']['nodes']['start']['ch'][3]
        self.assertFalse(core.req_ok(w, option['req']))
        self.assertIn('слабость', core.req_text(option['req']))
        core.C(w)['weak'].append('str')
        self.assertTrue(core.req_ok(w, option['req']))
        pick(w, 'revenge_str', 3)
        self.assertEqual(former.rec(w, 'str')['revenge'], 'off')

    def test_second_fall_is_final(self):
        w = fall('kip')
        core.C(w)['done'].append('p12_kip_free')
        w.s['loc'] = 0
        night(w)
        night(w)                                         # не пришли: Кипяток снова у вентиля
        self.assertTrue(core.in_power(w, 'kip'))
        w.s['loc'] = 4
        self.assertEqual(core.scene_for(w, 'wash'), 'wash_kip')
        self.assertTrue(core.boss_down(w, 'kip'))
        rec = former.rec(w, 'kip')
        self.assertEqual(rec['falls'], 2)
        self.assertEqual(rec['revenge'], 'never')
        self.assertFalse(rec['will'])
        self.assertTrue(core.has(w, 'shower_free'))      # сцена «после» уже сыграна: флаг ставится сразу
        for _ in range(8):
            night(w)
        self.assertTrue(core.is_former(w, 'kip'))


class Beating(unittest.TestCase):
    def test_former_boss_fights_as_an_ordinary_man(self):
        w = fall('zub', will=False)
        engine = fight.FightEngine(w, 'zub', seed=1)
        self.assertFalse(engine.boss)
        self.assertFalse(engine.revenge)
        self.assertEqual(engine.mx, 90)

    def test_beating_the_fallen_earns_no_respect(self):
        w = fall('zub', will=False)
        caste, honor, rel = core.C(w)['caste'], w.s['karma']['honor'], w.s['relations'].get('zub', 0)
        engine = fight.FightEngine(w, 'zub', seed=1)
        engine.finish_fight('Победа', 'Нокаут')
        engine.finish()
        self.assertEqual(core.C(w)['caste'], caste)
        self.assertEqual(w.s['karma']['honor'], honor - 2)
        self.assertEqual(w.s['relations']['zub'], rel - 10)
        self.assertTrue(former.rec(w, 'zub')['will'])
        self.assertTrue(core.is_former(w, 'zub'))        # второй раз «свергнуть» нельзя
        self.assertEqual(core.C(w)['ousted'].count('zub'), 1)

    def test_losing_to_the_fallen_costs_status(self):
        w = fall('zub', will=False)
        caste = core.C(w)['caste']
        engine = fight.FightEngine(w, 'zub', seed=1)
        engine.finish_fight('Поражение', 'Нокаут')
        engine.finish()
        self.assertEqual(core.C(w)['caste'], caste - 8)
        self.assertTrue(former.rec(w, 'zub')['will'])
        self.assertTrue(core.is_former(w, 'zub'))

    def test_breaking_the_peace(self):
        w = fall('zub')
        pick(w, 'ex_zub', 0, ok=True)
        self.assertTrue(former.rec(w, 'zub')['peace'])
        engine = fight.FightEngine(w, 'zub', seed=1)
        engine.finish_fight('Победа', 'Нокаут')
        engine.finish()
        rec = former.rec(w, 'zub')
        self.assertFalse(rec['peace'])
        self.assertTrue(rec['will'])


if __name__ == '__main__':
    unittest.main()
