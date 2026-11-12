"""v12 «Хозяева локаций»: 12 боссов, правила хозяев, письма домой.

Только логика, без окна: Tk здесь не запускается. Тест работает и в исходниках, и в готовой сборке,
поэтому героев и места называет по внутренним id, а не по именам.
"""
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import core
import fight
import lore
import meta
import story10
import world
from story_data import SCENES, available
from world import World

NP = json.loads((ROOT / 'npcs.json').read_text(encoding='utf8'))
NEW = {'polkan': 1, 'hleb': 2, 'kip': 4, 'cenz': 7}            # новый босс -> его локация
NEIGHBOUR = {'polkan': 'zina', 'hleb': 'serg', 'kip': 'steam', 'cenz': 'buh'}  # кто живёт рядом и рассказывает «после»
FREE_FLAG = {'polkan': 'yard_free', 'hleb': 'kitchen_free', 'kip': 'shower_free', 'cenz': 'letters_free'}
ACH = {row[0]: row[3] for row in meta.ACH}


def mk(day=2, loc=0):
    w = World(NP, meta.new_state(NP, 'normal'), seed=3)
    w.s['day'] = day
    w.s['loc'] = loc
    return w


def choices(sid):
    return SCENES[sid]['nodes']['start']['ch']


def outcomes(sid):
    """Все исходы всех выборов первой реплики сцены."""
    for choice in choices(sid):
        yield choice, choice['ok']
        if choice['fail'] is not choice['ok']:
            yield choice, choice['fail']


def flags_of(result):
    value = result['fx'].get('flag', [])
    return [value] if isinstance(value, str) else list(value)


def offered(w):
    return {a['id']: a for a in core.activities(w)}


def section(w, title):
    return dict(core.journal(w))[title]


class Roster(unittest.TestCase):
    def test_twelve_bosses_one_per_location(self):
        bosses = {k for k, v in NP.items() if v['boss']}
        self.assertEqual(len(NP), 18)
        self.assertEqual(len(bosses), 12)
        self.assertEqual(sorted(NP[k]['home'] for k in bosses), list(range(12)))
        self.assertEqual({k: NP[k]['home'] for k in NEW}, NEW)

    def test_every_system_knows_the_same_bosses(self):
        bosses = {k for k, v in NP.items() if v['boss']}
        self.assertEqual(set(core.BOSS_LOC), bosses)
        self.assertEqual(set(fight.STYLES), bosses)
        self.assertEqual(set(story10.WEAK), bosses)
        for boss, loc in core.BOSS_LOC.items():
            self.assertEqual(NP[boss]['home'], loc, boss)
            self.assertIn('scout_' + boss, SCENES)
            self.assertIn('weak_' + boss, SCENES)

    def test_new_bosses_are_complete_characters(self):
        from PIL import Image
        for boss in NEW:
            hero = NP[boss]
            self.assertEqual(hero['portrait'], boss)
            self.assertGreater(len(hero['role']), 80, boss)
            self.assertTrue(hero['goal'], boss)
            self.assertTrue(all(c in NP for c in hero['contacts']), boss)
            self.assertIn(NEIGHBOUR[boss], hero['contacts'])
            self.assertIn(boss, NP['zina']['contacts'])
            with Image.open(ROOT / 'assets' / (boss + '.jpg')) as im:
                self.assertAlmostEqual(im.height / im.width, 1.58, places=2)

    def test_inmates_and_administration(self):
        """Хлеборез и Кипяток — заключённые, Полкан и Цензор — администрация: от этого зависит уважение зоны."""
        self.assertTrue({'hleb', 'kip'} <= world.PRISONERS)
        self.assertFalse({'polkan', 'cenz'} & world.PRISONERS)

    def test_boss_is_met_where_he_rules(self):
        for boss, loc in NEW.items():
            w = mk(loc=loc)
            self.assertEqual(core.boss_here(w), boss)
            self.assertIn(boss, w.witnesses())
            self.assertIn('scout_' + boss, offered(w))
            core.C(w)['weak'].append(boss)
            self.assertIn('weak_' + boss, offered(w))
            core.boss_down(w, boss)
            self.assertIsNone(core.boss_here(w))
            self.assertIn(boss, w.witnesses())          # свергнутый остаётся в своей локации «бывшим»
            self.assertTrue(core.is_former(w, boss))
            self.assertFalse(core.in_power(w, boss))

    def test_each_new_boss_can_be_beaten_and_can_win(self):
        """Бот, который просто подходит и бьёт наугад, и выигрывает, и проигрывает каждому: ни стены, ни груши."""
        def bot(e, r):
            p = e.p
            p.dir = 0
            if abs(e.e.x - p.x) > 88:
                p.dir = p.face
            elif r.random() < .09:
                e.press(r.choice(['jab', 'hook', 'lowkick', 'highkick']))
        for boss in NEW:
            results = []
            for seed in range(24):
                e = fight.FightEngine(mk(), boss, seed=seed)
                r = random.Random(seed)
                t = 0
                while e.phase != 'over' and t < 240:
                    t += 1 / 60
                    if e.phase == 'fight':
                        bot(e, r)
                    e.update(1 / 60)
                results.append(e.result)
            self.assertGreaterEqual(results.count('Победа'), 3, boss)
            self.assertGreaterEqual(results.count('Поражение'), 3, boss)

    def test_styles_tell_the_bosses_apart(self):
        s = fight.STYLES
        self.assertEqual(max(NEW, key=lambda k: s[k]['armor']), 'polkan')      # ватник и ремни
        self.assertEqual(max(NEW, key=lambda k: s[k]['heavy']), 'hleb')        # бьёт редко и тяжело
        self.assertEqual(max(NEW, key=lambda k: s[k]['hp']), 'kip')            # здоровья больше всех
        self.assertEqual(s['kip']['armor'], 0)                                 # и никакой защиты
        self.assertEqual(max(NEW, key=lambda k: s[k]['dodge']), 'cenz')        # уворачивается
        self.assertEqual(max(NEW, key=lambda k: s[k]['kite']), 'cenz')         # и держит дистанцию


class Turf(unittest.TestCase):
    def test_turf_table_is_consistent(self):
        self.assertEqual(set(core.TURF), set(NEW))
        for boss, (loc, act, what) in core.TURF.items():
            self.assertEqual(loc, NEW[boss])
            self.assertTrue(what)
            self.assertIn(act, SCENES)
            self.assertIn(act + '_' + boss, SCENES)
            self.assertTrue(SCENES[act]['rep'] and SCENES[act + '_' + boss]['rep'])
            self.assertIn(act, offered(mk(loc=loc)), 'занятие должно быть в локации хозяина')

    def test_the_master_speaks_in_his_scene(self):
        for boss, (loc, act, _what) in core.TURF.items():
            node = SCENES[act + '_' + boss]['nodes']['start']
            self.assertEqual(node['who'], boss)
            self.assertGreaterEqual(len(node['ch']), 3)
            # всегда есть выход, который ничего не требует: ни сигарет, ни удачи
            self.assertTrue(any(not c['req'] for c in node['ch']), boss)

    def test_activity_runs_by_the_masters_rules_until_he_falls(self):
        for boss, (loc, act, _what) in core.TURF.items():
            w = mk(loc=loc)
            self.assertEqual(core.turf_boss(w, act), boss)
            self.assertEqual(core.scene_for(w, act), act + '_' + boss)
            self.assertIn(NP[boss]['name'], offered(w)[act]['title'])
            core.boss_down(w, boss)
            self.assertIsNone(core.turf_boss(w, act))
            self.assertEqual(core.scene_for(w, act), act)
            self.assertNotIn(NP[boss]['name'], offered(w)[act]['title'])

    def test_rules_stay_inside_the_masters_place(self):
        for boss, (loc, act, _what) in core.TURF.items():
            for other in range(12):
                if other != loc:
                    w = mk(loc=other)
                    self.assertIsNone(core.turf_boss(w, act), (boss, other))
                    self.assertEqual(core.scene_for(w, act), act)
        # другие сцены правило хозяина не трогает
        w = mk(loc=7)
        for sid in ('letter_reply', 'letter_parcel', 'morning', 'poverka'):
            self.assertEqual(core.scene_for(w, sid), sid)

    def test_the_bread_cutter_takes_his_cut(self):
        free, ruled = choices('work_shift')[0]['ok']['fx'], choices('work_shift_hleb')[0]['ok']['fx']
        self.assertLess(ruled['rub'], free['rub'])
        self.assertLess(ruled['cig'], free['cig'])
        self.assertEqual(ruled['stamina'], free['stamina'])  # работа та же, получка меньше
        best = max(result['fx'].get('rub', 0) for _c, result in outcomes('work_shift_hleb'))
        self.assertLessEqual(best, free['rub'])              # даже отбив обсчёт, больше честной смены не получить

    def test_hot_water_costs_a_cigarette(self):
        free = choices('wash')[0]['ok']['fx']
        hot, cold = choices('wash_kip')[0], choices('wash_kip')[1]
        self.assertEqual(hot['req'], {'cig': 1})
        self.assertEqual(hot['ok']['fx']['cig'], -1)
        self.assertEqual((hot['ok']['fx']['hp'], hot['ok']['fx']['stamina']), (free['hp'], free['stamina']))
        self.assertFalse(cold['req'])
        self.assertNotIn('cig', cold['ok']['fx'])
        self.assertLess(cold['ok']['fx']['hp'] + cold['ok']['fx']['stamina'], free['hp'] + free['stamina'])

    def test_smoking_by_the_whistle(self):
        by_whistle = choices('smoke_break_polkan')[0]
        self.assertEqual(by_whistle['game'], 'timing')
        self.assertGreater(by_whistle['ok']['fx']['stamina'], by_whistle['fail']['fx']['stamina'])
        # сигарета тратится в любом случае: перекур есть перекур
        self.assertEqual(by_whistle['ok']['fx']['cig'], by_whistle['fail']['fx']['cig'], -1)

    def test_journal_lists_the_masters(self):
        w = mk()
        lines = section(w, 'Хозяева локаций')
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(line.startswith('✘') for line in lines))
        for boss in NEW:
            self.assertTrue(any(NP[boss]['name'] in line for line in lines), boss)
        core.boss_down(w, 'kip')
        lines = section(w, 'Хозяева локаций')
        self.assertEqual(sum(line.startswith('✔') for line in lines), 1)
        self.assertTrue(next(line for line in lines if NP['kip']['name'] in line).startswith('✔'))
        # доска слабостей знает всех двенадцать
        self.assertEqual(len(section(mk(), 'Доска слабостей боссов')), 12)


class Letters(unittest.TestCase):
    def test_letters_are_written_in_one_place(self):
        places = [loc for loc in range(12) if 'letter' in offered(mk(loc=loc))]
        self.assertEqual(places, [7])

    def test_one_letter_a_day(self):
        w = mk(loc=7)
        self.assertIsNone(offered(w)['letter']['off'])
        core.apply(w, choices('letter_cenz')[0]['ok']['fx'])
        self.assertTrue(core.has(w, 'letter_today'))
        self.assertTrue(offered(w)['letter']['off'])
        core.sleep(w, force=True)
        self.assertFalse(core.has(w, 'letter_today'))
        self.assertIsNone(offered(w)['letter']['off'])

    def test_no_choice_lets_you_write_twice(self):
        for sid in ('letter', 'letter_cenz'):
            for choice, result in outcomes(sid):
                self.assertIn('letter_today', flags_of(result), (sid, choice['t']))

    def test_reply_comes_in_thirty_hours(self):
        w = mk(loc=7)
        c = core.C(w)
        c['pending'].clear()
        core.apply(w, choices('letter_cenz')[0]['ok']['fx'])
        timer = next(t for t in c['timers'] if t['id'] == 'letter_reply')
        self.assertEqual(timer['at'] - c['abs'], 30 * 60)
        core.advance(w, 29 * 60, quiet=True)
        self.assertNotIn('letter_reply', [p.get('id') for p in c['pending']])
        core.advance(w, 2 * 60, quiet=True)
        self.assertIn('letter_reply', [p.get('id') for p in c['pending']])
        self.assertFalse([t for t in c['timers'] if t['id'] == 'letter_reply'])

    def test_blacked_out_letter_gets_no_reply(self):
        """Если Цензор вымарал письмо, отвечать дома не на что."""
        for index in (1, 2, 3):
            fail = choices('letter_cenz')[index]['fail']
            self.assertIsNot(fail, choices('letter_cenz')[index]['ok'])
            self.assertNotIn('timer', fail['fx'], index)
            self.assertIn('timer', choices('letter_cenz')[index]['ok']['fx'], index)

    def test_parcel_must_be_asked_for(self):
        asked = [result['fx']['timer']['id'] for sid in ('letter', 'letter_cenz') for _c, result in outcomes(sid) if 'timer' in result['fx']]
        self.assertIn('letter_parcel', asked)
        self.assertIn('letter_reply', asked)
        w = mk()
        tea = core.C(w)['inv'].get('tea', 0)
        keep = next(c for c in choices('letter_parcel') if c['ok']['fx'].get('item'))
        core.apply(w, keep['ok']['fx'])
        self.assertEqual(core.C(w)['inv']['tea'], tea + 1)
        # письмо из дома — радость, а не товар: предмета «письмо с воли» за него не дают
        for sid in ('letter_reply', 'letter_parcel'):
            for _c, result in outcomes(sid):
                self.assertNotIn('letter', result['fx'].get('item', {}))

    def test_free_letters_after_the_censor(self):
        w = mk(loc=7)
        self.assertEqual(core.scene_for(w, 'letter'), 'letter_cenz')
        core.boss_down(w, 'cenz')
        self.assertEqual(core.scene_for(w, 'letter'), 'letter')
        self.assertIsNone(SCENES['letter']['nodes']['start']['who'])
        # без Цензора дойдёт любое письмо: вымарывать некому
        for choice in choices('letter')[:3]:
            self.assertIn('timer', choice['ok']['fx'])
            self.assertIs(choice['fail'], choice['ok'])


class Story(unittest.TestCase):
    def test_master_introduces_himself_from_day_two(self):
        for boss, loc in NEW.items():
            sid = 'p12_' + boss
            self.assertTrue(SCENES[sid]['story'])
            self.assertEqual(SCENES[sid]['nodes']['start']['who'], boss)
            self.assertNotIn(sid, list(available(mk(day=1, loc=loc))))
            self.assertIn(sid, list(available(mk(day=2, loc=loc))))
            self.assertNotIn(sid, list(available(mk(day=2, loc=(loc + 1) % 12))))
            w = mk(day=2, loc=loc)
            core.boss_down(w, boss)
            self.assertNotIn(sid, list(available(w)))
            for _choice, result in outcomes(sid):
                self.assertIn(boss + '_met', flags_of(result))

    def test_neighbour_tells_how_it_is_without_the_master(self):
        for boss, loc in NEW.items():
            sid = 'p12_%s_free' % boss
            speaker = SCENES[sid]['nodes']['start']['who']
            self.assertEqual(speaker, NEIGHBOUR[boss])
            self.assertEqual(NP[speaker]['home'], loc)
            self.assertFalse(NP[speaker]['boss'])
            w = mk(day=1, loc=loc)
            self.assertNotIn(sid, list(available(w)))
            core.boss_down(w, boss)
            self.assertIn(sid, list(available(w)))
            for _choice, result in outcomes(sid):
                self.assertIn(FREE_FLAG[boss], flags_of(result))

    def test_story_scene_is_played_once(self):
        w = mk(day=2, loc=1)
        self.assertIn('p12_polkan', list(available(w)))
        core.finish_scene(w, 'p12_polkan')
        self.assertNotIn('p12_polkan', list(available(w)))

    def test_weakness_ousts_without_a_fight(self):
        for boss, loc in NEW.items():
            w = mk(loc=loc)
            scout = choices('scout_' + boss)[0]['ok']
            self.assertEqual(scout['fx']['learn_weak'], boss)
            core.apply(w, scout['fx'])
            self.assertTrue(core.weak_known(w, boss))
            use = choices('weak_' + boss)[0]
            self.assertIn(use['chk'][0], ('wis', 'cha'))
            core.apply(w, use['ok']['fx'])
            self.assertIn(boss, core.C(w)['ousted'])
            self.assertTrue(core.has(w, 'weak_%s_used' % boss))
            self.assertIsNone(core.turf_boss(w, core.TURF[boss][1]))

    def test_a_won_fight_frees_the_place_too(self):
        w = mk(loc=2)
        core.on_duel(w, 'hleb', 'Победа')
        self.assertIn('hleb', core.C(w)['ousted'])
        self.assertEqual(core.scene_for(w, 'work_shift'), 'work_shift')
        self.assertIn('p12_hleb_free', list(available(w)))
        self.assertIn('boss_aftermath', [p.get('id') for p in core.C(w)['pending']])

    def test_scenes_are_well_formed(self):
        effects = {'cig', 'rub', 'hp', 'stamina', 'food', 'wis', 'cha', 'caste', 'karma', 'rel', 'rep', 'flag', 'item', 'time', 'timer'}
        chapter = [s for s in SCENES if s.startswith('p12_') or s.startswith('letter') or s.split('_')[-1] in NEW]
        for sid in [s for s in chapter if not s.startswith(('ex_', 'revenge_'))]:   # сцены бывших боссов проверяет test_former.py
            scene = SCENES[sid]
            self.assertTrue(scene['title'] and scene['title'] != sid, sid)
            for node in scene['nodes'].values():
                self.assertTrue(node['who'] is None or node['who'] in NP, sid)
                self.assertGreaterEqual(len(node['text']), 60, sid)
                for choice in node['ch']:
                    for result in (choice['ok'], choice['fail']):
                        self.assertTrue(result['goto'] is None or result['goto'] in scene['nodes'], sid)
                        if not sid.startswith(('scout_', 'weak_')):
                            self.assertTrue(set(result['fx']) <= effects, (sid, set(result['fx']) - effects))
                        self.assertTrue(all(k in NP for k in result['fx'].get('rel', {})), sid)
                    self.assertTrue(set(choice['req']) <= {'cig'}, sid)
                    if choice['req']:  # цена выбора не меньше того, что он потом спишет
                        self.assertGreaterEqual(choice['req']['cig'], -choice['ok']['fx'].get('cig', 0), (sid, choice['t']))

    def test_the_zone_remembers(self):
        w = mk()
        self.assertFalse(any('Мухтар' in line for line in lore.npc_lore(w, 'polkan')))
        core.flag(w, 'mukhtar_fed')
        self.assertTrue(any('Мухтар' in line for line in lore.npc_lore(w, 'polkan')))
        for boss, flag in FREE_FLAG.items():
            core.flag(w, flag)
            entry = lore.LORE[flag]
            self.assertIn(entry[NEIGHBOUR[boss]], lore.npc_lore(w, NEIGHBOUR[boss]))
            self.assertIn(entry['*'], lore.npc_lore(w, 'kol'))     # остальным — общая новость
            self.assertIn(entry['_'], lore.choices_summary(w))
        for flag in ('mukhtar_fed', 'hleb_debt', 'kip_shiver', 'cenz_notebook', 'cenz_poem'):
            self.assertIn(flag, lore.LORE)
            self.assertTrue(any(flag in flags_of(result) for sid in SCENES for _c, result in outcomes(sid)), flag + ' нигде не ставится')


class Achievements(unittest.TestCase):
    def test_zone_without_masters_needs_all_twelve(self):
        w = mk()
        old_eight = ['zub', 'graf', 'gvo', 'str', 'sm', 'gen', 'mat', 'cook']
        core.C(w)['ousted'] = list(old_eight)
        self.assertFalse(ACH['boss8'](w))
        core.C(w)['ousted'] = old_eight + list(NEW)
        self.assertTrue(ACH['boss8'](w))

    def test_weakness_board_counts_each_boss_once(self):
        w = mk()
        half = ['zub', 'graf', 'gvo', 'str', 'sm', 'gen']
        core.C(w)['weak'] = list(half)
        core.C(w)['ousted'] = list(half)   # те же шестеро: и узнаны, и свергнуты
        self.assertFalse(ACH['weak_all'](w))
        core.C(w)['ousted'] = ['mat', 'cook'] + list(NEW)
        self.assertTrue(ACH['weak_all'](w))

    def test_turf_achievements(self):
        w = mk()
        self.assertFalse(ACH['turf1'](w))
        core.boss_down(w, 'zub')            # не хозяин занятия
        self.assertFalse(ACH['turf1'](w))
        core.boss_down(w, 'polkan')
        self.assertTrue(ACH['turf1'](w))
        self.assertFalse(ACH['turf_all'](w))
        for boss in ('hleb', 'kip', 'cenz'):
            core.boss_down(w, boss)
        self.assertTrue(ACH['turf_all'](w))

    def test_five_letters(self):
        w = mk()
        core.C(w)['counters']['letter'] = 4
        self.assertFalse(ACH['letters5'](w))
        core.C(w)['counters']['letter'] = 5
        self.assertTrue(ACH['letters5'](w))

    def test_achievement_ids_are_unique(self):
        ids = [row[0] for row in meta.ACH]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({'turf1', 'turf_all', 'letters5'} <= set(ids))


if __name__ == '__main__':
    unittest.main()
