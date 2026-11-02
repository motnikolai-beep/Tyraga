# -*- coding: utf-8 -*-
"""Логика v8: время, распорядок, каста, боссы, храм, схроны и полный проход сюжета."""
import json
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import world as W
from data import LOC_INDEX, MEALS
from story import ENDINGS, SCENES, Story

BASE = Path(__file__).resolve().parents[1]
NPCS = json.loads((BASE / "npcs.json").read_text(encoding="utf8"))


def make(seed=0):
    return W.World(NPCS, seed=seed)


class TimeTests(unittest.TestCase):
    def test_starts_at_wake_and_clock(self):
        w = make()
        self.assertEqual(w.clock(), "07:00")
        self.assertEqual(w.phase(), "утро")

    def test_advance_crosses_meal(self):
        w = make()
        notes = w.advance(90)
        self.assertEqual(w.clock(), "08:30")
        self.assertEqual(notes[0]["kind"], "meal")
        self.assertEqual(notes[0]["meal"], "завтрак")

    def test_actions_spend_time(self):
        w = make()
        start = w.s["time"]
        w.work("kitchen") if w.s["loc"] == LOC_INDEX["mess"] else w.go(LOC_INDEX["mess"])
        w.work("kitchen")
        self.assertGreater(w.s["time"], start)

    def test_eat_only_in_window_and_once(self):
        w = make()
        w.s["loc"] = LOC_INDEX["mess"]
        w.s["time"] = 12 * 60 + 10
        w.eat()
        self.assertIn("обед", w.s["meals"]["eaten"])
        with self.assertRaises(ValueError):
            w.eat()
        w.s["time"] = 15 * 60
        with self.assertRaises(ValueError):
            w.eat()

    def test_sleep_only_at_night_and_in_cell(self):
        w = make()
        with self.assertRaises(ValueError):
            w.sleep()
        w.go(LOC_INDEX["mess"])
        w.s["time"] = 22 * 60
        with self.assertRaises(ValueError):
            w.sleep()
        w.s["loc"] = LOC_INDEX["cam"]
        w.sleep()
        self.assertEqual(w.s["day"], 2)
        self.assertEqual(w.s["time"], W.WAKE)

    def test_new_day_resets_meals_and_health(self):
        w = make()
        w.s["meals"]["eaten"].append("завтрак")
        w.s["npc_hp"]["zub"] = 3
        w.s["time"] = 23 * 60
        w.advance(120)
        self.assertEqual(w.s["day"], 2)
        self.assertEqual(w.s["meals"]["eaten"], [])
        self.assertFalse(w.s["npc_hp"])

    def test_npc_hours_hide_people(self):
        w = make()
        w.s["time"] = 3 * 60
        self.assertEqual(w.witnesses(LOC_INDEX["visit"]), [])
        w.s["time"] = 12 * 60
        self.assertTrue(w.witnesses(LOC_INDEX["visit"]))


class CasteTests(unittest.TestCase):
    def test_start_rank_muzhik(self):
        w = make()
        self.assertEqual(w.rank_key(), "muzhik")

    def test_rise_and_pahan(self):
        w = make()
        w.rise(60, "тест")
        self.assertIn(w.rank_key(), ("blatnoy", "pahan"))

    def test_humiliation_drops(self):
        w = make()
        w.humiliate("сдал своих", strong=True)
        self.assertTrue(w.s["dropped"])
        self.assertIn(w.rank_key(), ("petukh", "opush"))

    def test_redeem(self):
        w = make()
        w.humiliate("тест", strong=True)
        w.s["humiliations"] = 1
        w.redeem("подвиг", 30)
        self.assertFalse(w.s["dropped"])

    def test_stats_grow(self):
        w = make()
        before = w.stats()["wis"]
        w.train_stat("wis")
        self.assertGreater(w.stats()["wis"], before)

    def test_boss_defeat_public_and_drop(self):
        w = make()
        w.boss_defeat("zub")
        self.assertIn("zub", w.s["defeated"])
        self.assertIn("star", w.s["relics"])
        self.assertTrue(any(e["kind"] == "boss_down" for e in w.s["events"]))
        rel = w.s["relations"].get("kol", 0)
        self.assertGreater(rel, 0)
        self.assertGreater(w.s["respect"], 34)


class WorldTests(unittest.TestCase):
    def test_stash_search_returns_items_or_none(self):
        w = make(seed=5)
        found = 0
        for _ in range(30):
            w.s["stamina"] = 100
            if w.search():
                found += 1
        self.assertGreater(found, 0)

    def test_prayer_cleans_bad_karma(self):
        w = make()
        w.s["loc"] = LOC_INDEX["temple"]
        w.s["karma"]["honor"] = -20
        clean = w.pray()
        self.assertGreater(clean, 0)
        self.assertGreater(w.s["karma"]["honor"], -20)

    def test_prayer_limit_per_day(self):
        w = make()
        w.s["loc"] = LOC_INDEX["temple"]
        w.pray()
        w.pray()
        with self.assertRaises(ValueError):
            w.pray()

    def test_purchase_and_gear(self):
        w = make()
        w.s["rub"] = 100
        w.buy("knife")
        self.assertEqual(w.s["gear"]["weapon"], "Заточка")
        self.assertTrue(w.has("knife"))
        self.assertEqual(w.s["rub"], 60)

    def test_visit_only_working_hours(self):
        w = make()
        w.s["time"] = 5 * 60
        with self.assertRaises(ValueError):
            w.go(LOC_INDEX["visit"])
        w.s["time"] = 12 * 60
        w.go(LOC_INDEX["visit"])
        w.visit_start()
        with self.assertRaises(ValueError):
            w.visit_start()

    def test_kicha_locked_until_story(self):
        w = make()
        with self.assertRaises(ValueError):
            w.go(LOC_INDEX["kicha"])
        w.s["flags"]["kicha_open"] = True
        w.go(LOC_INDEX["kicha"])
        self.assertEqual(w.s["loc"], LOC_INDEX["kicha"])

    def test_shmon_can_take_contraband(self):
        w = make(seed=2)
        w.s["inv"]["phone"] = 3
        hits = 0
        for _ in range(40):
            w.s["inv"]["phone"] = 3
            if w.maybe_shmon("тест"):
                hits += 1
        self.assertGreater(hits, 0)


class DuelTests(unittest.TestCase):
    def test_duel_ends_and_boss(self):
        for seed in range(30):
            w = make(seed=seed)
            b = W.Duel(w, "girya", seed % 2 == 0, seed)
            r = random.Random(seed)
            for _ in range(60):
                b.strike(r.randrange(3), r.randrange(3), r.choice(["attack", "guard", "aim"]))
            self.assertTrue(b.done or b.round > 30)
            b.finish()
            self.assertTrue(b.finished)
        w = make(seed=1)
        b = W.Duel(w, "girya", False, 7)
        b.enemy = 0
        b.check()
        b.finish()
        if b.result == "Победа":
            self.assertIn("girya", w.s["defeated"])


class SaveMigrationTests(unittest.TestCase):
    def test_v7_save_loads(self):
        old = {"version": 7, "day": 4, "turn": 12, "ap": 3, "food": 50, "hp": 70,
               "stamina": 40, "rub": 15, "cig": 9, "loc": 0,
               "karma": {"empathy": 1, "honor": 2, "cunning": 0},
               "relations": {"zub": 5}, "history": {"zub": [{"role": "user", "content": "привет"}]}}
        w = W.World(NPCS, old)
        self.assertEqual(w.inv("cig"), 9)
        self.assertEqual(w.s["day"], 4)
        self.assertNotIn("ap", w.s)
        self.assertEqual(w.s["relations"]["zub"], 5)
        self.assertTrue(w.s["story"]["scene"])

    def test_save_roundtrip(self):
        import tempfile
        w = make()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "s.json"
            W.save(w.s, p)
            loaded = W.World(NPCS, json.loads(p.read_text(encoding="utf8")))
            self.assertEqual(loaded.s, w.s)


class StoryTests(unittest.TestCase):
    def test_all_scenes_reachable_and_endings(self):
        seen = set()
        endings = set()
        for seed in range(50):
            w = make(seed=seed)
            st = Story(w)
            r = random.Random(seed)
            for _ in range(300):
                scn = st.scene()
                if not scn or st.finished():
                    break
                st.enter()
                seen.add(scn["id"])
                choices = st.available()
                self.assertTrue(choices, scn["id"])
                where = scn.get("where")
                if where is not None:
                    w.s["loc"] = LOC_INDEX[where]
                    w.s["time"] = 12 * 60
                w.s["visit"] = {"day": w.s["day"], "used": False}
                st.choose(r.randrange(len(choices)))
            self.assertTrue(st.finished(), "seed %d застрял на %s" % (seed, st.s["scene"]))
            endings.add(st.s["ending"])
        self.assertTrue(set(SCENES) <= seen, set(SCENES) - seen)
        self.assertTrue(len(endings) >= 3)

    def test_checks_use_stats(self):
        w = make()
        st = Story(w)
        ok, text, info = st.roll("wis", 10)
        self.assertIn("d20", text)
        self.assertEqual(info["dc"], 10)

    def test_scene_requires_location(self):
        w = make()
        st = Story(w)
        st.goto("first_meal")
        w.s["loc"] = LOC_INDEX["cam"]
        self.assertFalse(st.here())
        w.s["loc"] = LOC_INDEX["mess"]
        self.assertTrue(st.here())

    def test_bunk_only_at_night(self):
        w = make()
        st = Story(w)
        st.goto("first_night")
        w.s["loc"] = LOC_INDEX["cam"]
        w.s["time"] = 10 * 60
        self.assertFalse(st.at_ready())
        w.s["time"] = 22 * 60
        self.assertTrue(st.at_ready())

    def test_effect_item_and_karma(self):
        w = make()
        st = Story(w)
        w.s["inv"]["tea"] = 2
        st.apply({"item": {"tea": -1}, "karma": {"honor": 2}, "respect": 4})
        self.assertEqual(w.inv("tea"), 1)
        self.assertEqual(w.s["karma"]["honor"], 2)


if __name__ == "__main__":
    unittest.main()
