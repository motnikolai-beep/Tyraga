# -*- coding: utf-8 -*-
"""Мир «Тюряги» v8: время, распорядок, каста, боссы, схроны, храм, работа.

Ключевые отличия от v7:
- вместо «ходов» — минуты и распорядок дня (кормёжки, отбой, шконка только ночью);
- каста игрока считается из уважения и поступков: мужик → блатной → пахан
  либо мужик → петух → опущенный;
- боссы зоны: победа публична, уважение растёт, иконка босса исчезает;
- схроны, работа, тренажёрка, храм, свиданка, чифирь.
"""
import copy
import hashlib
import json
import os
import random
import re
import uuid
from pathlib import Path

from data import (BOSSES, CAST_TITLES, COSTS, ITEMS, JOBS, LOC_INDEX, LOCATIONS,
                  LIGHTS_OUT, MEALS, NAMES, RANKS, SLEEP_FROM, SLEEP_TO, WAKE)

DIMS = ("empathy", "honor", "cunning")
PRISONERS = {"zub", "graf", "buh", "sm", "kol", "prach", "steam", "cook", "zina", "girya"}
AUTHORITIES = {"gvo", "str", "gen", "serg", "vertuha", "mat"}


def fresh(npcs):
    return {
        "version": 8, "day": 1, "time": WAKE, "loc": 0, "visited": [0],
        "hp": 100, "hp_max": 100, "stamina": 100, "stamina_max": 100, "food": 75,
        "rub": 25, "inv": {"cig": 12, "bread": 1},
        "gear": {"weapon": "Кулаки", "damage": 16, "armor": 2, "accuracy": 0.72},
        "karma": dict.fromkeys(DIMS, 0), "budget": dict.fromkeys(DIMS, 0),
        "relations": {}, "history": {}, "memory": {}, "seen": [], "events": [],
        "knowledge": {}, "gossip": [], "audit": [], "diary": [], "notices": [],
        "chron": [], "chat_fight_tokens": [],
        "npc_state": {k: {"last_turn": -9, "last_topic": "", "discussed_gossip": []} for k in npcs},
        "respect": 34, "dropped": False, "drop_reason": "", "humiliations": 0,
        "training": {"wis": 0, "cha": 0, "str": 0, "cun": 0},
        "defeated": [], "relics": [], "npc_hp": {}, "boss_news": [],
        "stashes": {}, "meals": {"day": 1, "eaten": []},
        "temple": {"day": 1, "prayers": 0, "grace": 0},
        "visit": {"day": 0, "used": False},
        "story": {"scene": "intro", "flags": {}, "act": 1, "log": [], "completed": [],
                  "checks": {"ok": 0, "fail": 0}},
        "toasts": [], "chat_minutes": 0, "chat_npc": "", "day_talk": {},
        "obligations": [], "dialogue_money": {"day": 0, "earned": 0, "seen": []},
        "day_log": [], "flags": {},
    }


def save(s, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf8")
    os.replace(tmp, p)


def clamp(v, lo=-100, hi=100):
    return max(lo, min(hi, v))


def hhmm(minutes):
    minutes = int(minutes) % (24 * 60)
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def in_window(now, start, end):
    """Окно времени с переходом через полночь."""
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def phase_of(minutes):
    minutes %= 1440
    if minutes < 7 * 60:
        return "ночь"
    if minutes < 12 * 60:
        return "утро"
    if minutes < 18 * 60:
        return "день"
    if minutes < 22 * 60:
        return "вечер"
    return "ночь"


class World:
    def __init__(self, npcs, s=None, seed=None):
        self.npcs = npcs
        self.rng = random.Random(seed)
        defaults = fresh(npcs)
        self.s = s if isinstance(s, dict) else defaults
        for k, v in defaults.items():
            self.s.setdefault(k, v)
        self.s["version"] = 8
        for k, n in npcs.items():
            st = self.s["npc_state"].setdefault(k, {"last_turn": -9, "last_topic": ""})
            st.setdefault("discussed_gossip", [])
        # миграция v7 → v8
        if "cig" in self.s:
            self.s["inv"]["cig"] = self.s.pop("cig")
        if "stamina_max" not in self.s:
            self.s["stamina_max"] = 100
        if "ap" in self.s:
            del self.s["ap"]

    # ------------------------------------------------------------ базовое
    def witnesses(self, loc=None):
        loc = self.s["loc"] if loc is None else loc
        now = self.s["time"]
        out = []
        for k, n in self.npcs.items():
            if n.get("home") != loc:
                continue
            h = n.get("hours") or [0, 1440]
            if in_window(now, h[0], h[1]):
                out.append(k)
        return out

    def loc_name(self, i=None):
        return NAMES[self.s["loc"] if i is None else i]

    def clock(self):
        return hhmm(self.s["time"])

    def phase(self):
        return phase_of(self.s["time"])

    def is_night(self):
        return in_window(self.s["time"], SLEEP_FROM, SLEEP_TO)

    def inv(self, item):
        return int(self.s["inv"].get(item, 0))

    def add(self, item, n=1):
        self.s["inv"][item] = max(0, self.inv(item) + n)
        if not self.s["inv"][item]:
            del self.s["inv"][item]

    def take(self, item, n=1):
        if self.inv(item) < n:
            raise ValueError("Нет: " + ITEMS.get(item, {}).get("name", item))
        self.add(item, -n)

    def has(self, item, n=1):
        return self.inv(item) >= n

    def toast(self, text, kind="info"):
        self.s["toasts"].append({"text": text, "kind": kind, "day": self.s["day"], "time": self.s["time"]})
        self.s["toasts"] = self.s["toasts"][-40:]

    # ------------------------------------------------------------ время
    def advance(self, minutes, why=""):
        """Двигает время, списывает голод, помечает пропущенные кормёжки."""
        notes = []
        minutes = int(minutes)
        if minutes <= 0:
            return notes
        before = self.s["time"]
        self.s["time"] = before + minutes
        crossed = []
        for start, end, key, _ in MEALS:
            if self._crossed(before, self.s["time"], start, end) and key not in self.s["meals"]["eaten"]:
                crossed.append(key)
        for m in crossed:
            self.s["food"] = max(0, self.s["food"] - 6)
            notes.append({"kind": "meal", "meal": m,
                          "text": "Прошёл %s. Ты не успел." % m})
        hours = minutes / 60.0
        self.s["food"] = max(0, self.s["food"] - int(hours * 2))
        self.s["stamina"] = max(0, min(self.s["stamina_max"], self.s["stamina"] - int(hours * 1.5)))
        if self.s["food"] <= 0:
            self.s["hp"] = max(1, self.s["hp"] - int(hours))
        while self.s["time"] >= 24 * 60:
            self.s["time"] -= 24 * 60
            self._new_day(forced=True)
            notes.append({"kind": "day", "text": "Наступил день %d. Свет в окне, подъём." % self.s["day"]})
        if why:
            self.s["day_log"].append("%s — %s" % (self.clock(), why))
            self.s["day_log"] = self.s["day_log"][-60:]
        return notes

    @staticmethod
    def _crossed(before, after, start, end):
        """Пересекли ли окно [start,end) при движении before→after."""
        for base in range(0, after // 1440 + 2):
            day = base * 1440
            s0, s1 = day + start, day + end
            if s1 <= before or s0 >= after:
                continue
            if before < s1 and after > s0:
                return True
        return False

    def _new_day(self, forced=False):
        s = self.s
        s["day"] += 1
        s["time"] = WAKE if forced else s["time"]
        s["meals"] = {"day": s["day"], "eaten": []}
        s["budget"] = dict.fromkeys(DIMS, 0)
        s["temple"]["day"] = s["day"]
        s["visit"] = {"day": s["day"], "used": False}
        s["npc_hp"] = {}
        s["day_talk"] = {}
        if s["food"] > 20:
            s["hp"] = min(s["hp_max"], s["hp"] + 6)
        else:
            s["hp"] = max(1, s["hp"] - 8)
        s["stamina"] = s["stamina_max"]
        self._decay_relations()
        self.diary()

    def _decay_relations(self):
        for k, v in list(self.s["relations"].items()):
            if v < 0:
                self.s["relations"][k] = min(0, v + 1)
            elif v > 0:
                self.s["relations"][k] = max(0, v - 1)

    # ------------------------------------------------------------ сон
    def can_sleep(self):
        return self.is_night()

    def sleep(self):
        s = self.s
        if s["loc"] != LOC_INDEX["cam"]:
            raise ValueError("Шконка твоя — в камере. Спать в коридоре не по понятиям.")
        if not self.can_sleep():
            raise ValueError("На шконку ложатся ночью. Сейчас %s — %s." % (self.clock(), self.phase()))
        self._new_day(forced=False)
        s["time"] = WAKE
        s["hp"] = min(s["hp_max"], s["hp"] + 14)
        s["stamina"] = s["stamina_max"]
        s["food"] = max(0, s["food"] - 8)
        self.toast("Подъём. День %d, %s." % (s["day"], self.clock()), "day")
        self.event("sleep", "Игрок лёг на шконку и дожил до утра.", [])

    def diary(self):
        s = self.s
        today = [e["text"] for e in s["events"] if e["day"] == s["day"] and e["kind"] not in ("speech",)]
        line = "День %d (%s). %s" % (s["day"], self.clock(), "; ".join(today[-6:]) or "Ничего не произошло. Тоже результат.")
        s["diary"].append(line)
        s["diary"] = s["diary"][-120:]

    # ------------------------------------------------------------ еда
    def meal_now(self):
        for start, end, key, dish in MEALS:
            if in_window(self.s["time"], start, end):
                return key, dish
        return None, None

    def eat(self):
        s = self.s
        meal, dish = self.meal_now()
        if s["loc"] != LOC_INDEX["mess"]:
            raise ValueError("В столовую иди, там кормят.")
        if not meal:
            raise ValueError("Кормят по часам: 07:00, 12:00 и 18:00. Сейчас %s." % self.clock())
        if meal in s["meals"]["eaten"]:
            raise ValueError("Ты уже поел на %s. Второй раз только за сигареты." % meal)
        s["meals"]["eaten"].append(meal)
        s["food"] = min(100, s["food"] + 28)
        s["stamina"] = min(s["stamina_max"], s["stamina"] + 8)
        self.advance(COSTS["eat"], "приём пищи")
        self.event("meal", "Игрок поел на %s (%s)." % (meal, dish), self.witnesses())
        fun = self.rng.choice([
            "Сергеич налил через край и сделал вид, что так и надо.",
            "В баланде нашлась пуговица. Никто не удивился.",
            "Сосед по столу отобрал горбушку, но вернул соль.",
            "Кто-то прочитал стихи про волю. Все ели быстрее.",
        ])
        self.toast(fun)

    def smoke(self, target=None):
        s = self.s
        if self.inv("cig") < 1:
            raise ValueError("Сигарет нет. Стреляй или зарабатывай.")
        self.add("cig", -1)
        self.advance(COSTS["smoke"], "перекур")
        s["stamina"] = min(s["stamina_max"], s["stamina"] + 6)
        s["food"] = max(0, s["food"] - 1)
        if target and target in self.witnesses():
            s["relations"][target] = clamp(s["relations"].get(target, 0) + 2)
            self.toast("Угостил %s. Отношение +2." % self.npcs[target]["name"])
        self.event("smoke", "Игрок курил" + (" с " + self.npcs[target]["name"] if target else "") + ".", self.witnesses())

    # ------------------------------------------------------------ каста
    def rank_key(self):
        s = self.s
        if s["dropped"]:
            return "opush" if s["humiliations"] >= 3 else "petukh"
        score = s["respect"] + 3 * len([r for r in s["relics"] if r in ("star", "fist")])
        for key, title, _, (lo, hi) in RANKS:
            if key in ("opush", "petukh"):
                continue
            if lo <= score < hi:
                return key
        return "pahan" if score >= 82 else "muzhik"

    def rank(self):
        k = self.rank_key()
        for key, title, note, _ in RANKS:
            if key == k:
                return {"key": key, "title": title, "note": note, "score": self.s["respect"]}
        return {"key": "muzhik", "title": "Мужик", "note": "", "score": self.s["respect"]}

    def rise(self, amount, reason):
        s = self.s
        if s["dropped"] and amount > 0:
            amount = amount // 2 or 1  # из петухов выбираются медленно
        s["respect"] = clamp(s["respect"] + amount, 0, 100)
        if amount:
            s["toasts"].append({"text": "Уважение %+d · %s" % (amount, reason), "kind": "respect",
                                "day": s["day"], "time": s["time"]})

    def humiliate(self, reason, strong=False):
        s = self.s
        s["humiliations"] += 1
        s["respect"] = clamp(s["respect"] - (14 if strong else 8), 0, 100)
        if not s["dropped"] and (strong or s["humiliations"] >= 2):
            s["dropped"] = True
            s["drop_reason"] = reason
            self.event("humiliation", "Игрока опустили: " + reason, self.witnesses(), public=True)
            self.toast("Ты теперь петух. Причина: " + reason, "bad")
        else:
            self.event("humiliation", "Игрока унизили: " + reason, self.witnesses())
            self.toast("Унижение: " + reason, "bad")

    def redeem(self, reason, amount=10):
        s = self.s
        s["respect"] = clamp(s["respect"] + amount, 0, 100)
        if s["dropped"] and s["respect"] >= 40:
            s["dropped"] = False
            s["drop_reason"] = ""
            self.event("redeem", "Игрок поднялся с самого дна: " + reason, self.witnesses(), public=True)
            self.toast("С тебя сняли клеймо. Ты снова мужик.", "good")

    # ------------------------------------------------------------ репутация/знания
    def event(self, kind, text, witnesses=(), public=False):
        s = self.s
        ids = list(dict.fromkeys(k for k in witnesses if k in self.npcs))
        e = {"id": uuid.uuid4().hex, "day": s["day"], "turn": s["time"], "kind": kind,
             "text": text, "witnesses": ids, "public": public}
        s["events"].append(e)
        s["events"] = s["events"][-400:]
        for k in ids:
            s["knowledge"].setdefault(k, []).append({**e, "source": "очевидец", "verified": True})
            s["knowledge"][k] = s["knowledge"][k][-120:]
        honest = kind not in ("theft", "betrayal")
        s["chron"].append({"day": s["day"], "real": text,
                           "his": "Герой скромно трудился на благо зоны." if honest
                           else "Мелкое недоразумение, не требующее проверки."})
        s["chron"] = s["chron"][-100:]
        return e

    def known(self, k):
        s = self.s
        out = list(s["knowledge"].get(k, []))
        ids = {e["id"] for e in out}
        out += [{**e, "source": "публичное событие", "verified": True}
                for e in s["events"] if e.get("public") and e["id"] not in ids]
        return out[-30:]

    def heard(self, k):
        return [g for g in self.s["gossip"] if g["to"] == k][-10:]

    def reputation(self, k=None):
        s = self.s
        ids = [i for i in self.npcs if i in PRISONERS]
        mean = sum(s["relations"].get(i, 0) for i in ids) / max(1, len(ids))
        ka = s["karma"]
        karma = 0.5 * ka["honor"] + 0.3 * ka["cunning"] + 0.2 * ka["empathy"]
        personal = s["relations"].get(k, 0) if k else 0
        public = s["respect"]
        score = 0.55 * public + 0.25 * karma + 0.2 * personal
        if personal <= -25:
            score = min(score, -20)
        return {"public_respect": round(public, 1), "prisoners_average": round(mean, 1),
                "karma": round(karma, 1), "personal": personal, "score": round(score, 1),
                "rank": self.rank()["title"],
                "authority": k not in PRISONERS}

    def context(self, k):
        """Контекст для ИИ: что NPC реально знает и каким видит игрока."""
        s = self.s
        n = self.npcs[k]
        bosses = [BOSSES[b]["title"] for b in s["defeated"] if b in BOSSES]
        return {
            "npc": {"name": n["name"], "role": n["role"], "cast": n.get("cast", "muzhik")},
            "location": self.loc_name(n.get("home", 0)),
            "day": s["day"], "time": self.clock(), "phase": self.phase(),
            "relationship": s["relations"].get(k, 0),
            "respect": self.reputation(k),
            "player": {"rank": self.rank()["title"], "dropped": s["dropped"],
                       "karma": s["karma"], "hp": s["hp"], "food": s["food"],
                       "bosses_beaten": bosses, "relics": s["relics"],
                       "reputation_note": "бойся его" if bosses else "обычный"},
            "known_facts": [{kk: e[kk] for kk in ("day", "kind", "text")} for e in self.known(k)[-6:]],
            "heard_rumors": [{"id": g["id"],
                              "from": ("лично слышал от игрока" if g["from"] == k and g["hops"] == 0
                                       else self.npcs[g["from"]]["name"]),
                              "claim": g["claim"], "confidence": g["confidence"], "hops": g["hops"],
                              "verified": False, "disputed": g.get("disputed", False)}
                             for g in self.heard(k)[-4:]],
            "already_discussed_rumors": s["npc_state"][k]["discussed_gossip"][-15:],
            "obligations": [o for o in s["obligations"] if o["npc"] == k and o["status"] == "active"],
            "memory": s["memory"].get(k, [])[-5:],
            "story": {"act": s["story"].get("act", 1),
                      "objective": s["story"].get("objective", ""),
                      "known_flags": sorted([k for k, v in s["story"].get("flags", {}).items() if v is True])[:12]},
        }

    # ------------------------------------------------------------ слухи
    def conversation_event(self, k, text, reply, private=False):
        s = self.s
        loc = self.npcs[k].get("home", 0)
        listeners = [] if private else [i for i, n in self.npcs.items()
                                        if n.get("home") == loc and i != k]
        e = {"id": uuid.uuid4().hex, "kind": "speech", "day": s["day"], "turn": s["time"],
             "text": text[:1600], "addressed_to": k, "npc_reply": reply[:900],
             "private": private, "observers": listeners}
        s["events"].append(e)
        s["events"] = s["events"][-400:]
        if not private:
            claim = "Игрок сказал %s: «%s»." % (self.npcs[k]["name"], text[:320])
            self.gossip(k, k, claim, e["id"], 100, 0, "участник разговора", [])
            for i in listeners:
                self.gossip(k, i, claim, e["id"], 90, 0, "подслушал в " + NAMES[loc], [])
        return e

    def gossip(self, src, to, claim, root, confidence, hops, channel, chain):
        s = self.s
        if any(g["root"] == root and g["to"] == to for g in s["gossip"]):
            return None
        g = {"id": uuid.uuid4().hex, "root": root, "day": s["day"], "turn": s["time"],
             "from": src, "to": to, "claim": claim[:650], "confidence": confidence,
             "hops": hops, "channel": channel, "chain": chain + [src], "verified": False}
        s["gossip"].append(g)
        s["gossip"] = s["gossip"][-500:]
        return g

    def relay(self):
        s = self.s
        candidates = [g for g in s["gossip"] if g["hops"] < 3 and s["time"] != g["turn"]]
        self.rng.shuffle(candidates)
        out = []
        for g in candidates:
            src = g["to"]
            pool = [i for i in self.npcs[src].get("contacts", [])
                    if i != src and not any(x["root"] == g["root"] and x["to"] == i for x in s["gossip"])]
            if not pool:
                continue
            txt = ("Оспариваемый слух: " if g.get("disputed") else "") + g["claim"]
            txt = ("Говорят, " if g["hops"] == 0 else "Через третьи руки передают: ") + txt[:500]
            n = self.gossip(src, self.rng.choice(pool), txt, g["root"],
                            max(10, g["confidence"] - self.rng.randint(12, 25)),
                            g["hops"] + 1, "записки и пересказы", g["chain"])
            if n:
                out.append(n)
            if len(out) >= 2:
                break
        return out

    def deny(self, k, id):
        g = next((g for g in self.heard(k) if g["id"] == id), None)
        if not g:
            raise ValueError("NPC не слышал этот слух")
        g["disputed"] = True
        self.event("denial", "Игрок оспорил слух: " + g["claim"], [k])
        self.gossip(k, k, "Игрок отрицает: " + g["claim"], uuid.uuid4().hex, 80, 0, "опровержение", [])

    # ------------------------------------------------------------ переходы
    def go(self, loc):
        s = self.s
        if loc not in range(len(LOCATIONS)):
            raise ValueError("Нет такой локации")
        if loc == LOC_INDEX["kicha"] and not s["flags"].get("kicha_open"):
            raise ValueError("Кича закрыта. Туда провожают, а не ходят в гости.")
        if loc == LOC_INDEX["visit"]:
            if not in_window(s["time"], 10 * 60, 17 * 60):
                raise ValueError("Свиданка работает с 10:00 до 17:00. Сейчас %s." % self.clock())
        old = s["loc"]
        s["loc"] = loc
        if loc not in s["visited"]:
            s["visited"].append(loc)
        mins = COSTS["walk"] if LOCATIONS[old]["map"][0] != LOCATIONS[loc]["map"][0] else 5
        self.advance(mins, "переход в " + NAMES[loc])
        self.s["chat_npc"] = ""
        return {"from": old, "to": loc, "notes": []}

    # ------------------------------------------------------------ работа и тренировки
    def work(self, job=None):
        s = self.s
        keys = [k for k, j in JOBS.items() if j["loc"] == s["loc"]]
        if not keys:
            raise ValueError("Здесь не работают. Ищи в столовой, прачечной, мастерской или во дворе.")
        job = job or keys[0]
        if job not in JOBS:
            raise ValueError("Нет такой работы")
        j = JOBS[job]
        if j["loc"] != s["loc"]:
            raise ValueError("Работа не здесь")
        if s["stamina"] < 8:
            raise ValueError("Выносливости нет. Поешь или поспи.")
        s["rub"] += int(j["pay"] * (1 + 0.2 * s["training"]["str"]))
        self.add("cig", j["cig"])
        s["stamina"] = max(0, s["stamina"] + j["stamina"])
        s["food"] = max(0, s["food"] - 5)
        self.advance(j["time"], j["name"])
        self.event("work", j["line"], self.witnesses())
        self.rise(1, "работа")
        self.maybe_shmon("после смены")

    def maybe_shmon(self, when=""):
        """Шмон: вероятность найти контрабанду растёт с числом предметов."""
        s = self.s
        contraband = sum(v for k, v in s["inv"].items() if k in ("phone", "knife", "chifir"))
        if not contraband:
            return
        chance = min(0.55, 0.05 * contraband + (0.15 if s["loc"] == LOC_INDEX["hall"] else 0))
        if self.rng.random() < chance:
            item = "phone" if self.inv("phone") else "knife" if self.inv("knife") else "chifir"
            self.add(item, -1)
            self.humiliate("вертухай нашёл " + ITEMS[item]["name"].lower() + " " + when, strong=False)
            self.advance(30, "шмон")
            return "shmon"
        return None

    def train(self):
        s = self.s
        if s["loc"] != LOC_INDEX["gym"]:
            raise ValueError("Тренажёрка — во дворе у забора, туда иди.")
        if s["stamina"] < 15:
            raise ValueError("Силы кончились. Отдохни, поешь.")
        s["stamina"] -= 18
        s["food"] = max(0, s["food"] - 4)
        s["training"]["str"] = min(20, s["training"]["str"] + 1)
        s["gear"]["damage"] = 16 + 2 * s["training"]["str"] + (8 if s["gear"]["weapon"] == "Заточка" else 0)
        self.advance(COSTS["train"], "тренажёрка")
        self.event("train", "Игрок тянул железо до отказа.", self.witnesses())
        self.rise(1, "спорт")
        return s["training"]["str"]

    def train_stat(self, stat, minutes=20):
        s = self.s
        if stat not in s["training"]:
            raise ValueError("Нет такой характеристики")
        if s["stamina"] < 6:
            raise ValueError("Нет сил")
        s["stamina"] -= 6
        s["training"][stat] = min(10, s["training"][stat] + 1)
        self.advance(minutes, "тренировка " + stat)
        self.toast({"wis": "Мудрость +1", "cha": "Харизма +1", "cun": "Хитрость +1", "str": "Сила +1"}[stat])

    def stats(self):
        s = self.s
        return {
            "wis": 3 + s["training"]["wis"] + s["karma"]["honor"] // 12 - (2 if s["dropped"] else 0),
            "cha": 3 + s["training"]["cha"] + s["karma"]["empathy"] // 12 + (2 if self.rank_key() in ("blatnoy", "pahan") else 0),
            "str": 3 + s["training"]["str"] + (2 if self.has("knife") else 0),
            "cun": 3 + s["training"]["cun"] + s["karma"]["cunning"] // 12,
        }

    # ------------------------------------------------------------ схроны
    def search(self):
        s = self.s
        loc = s["loc"]
        s["stamina"] = max(0, s["stamina"] - 6)
        self.advance(COSTS["search"], "поиск схрона в " + NAMES[loc])
        stash = s["stashes"].setdefault(str(loc), {"found": False, "items": []})
        chance = 0.28 + 0.04 * s["training"]["cun"] + (0.1 if s["flags"].get("knows_stashes") else 0)
        if self.rng.random() < chance:
            stash["found"] = True
            loot = self.rng.choice([
                ("cig", self.rng.randint(2, 6)), ("rub", self.rng.randint(5, 25)),
                ("tea", 1), ("bread", 2), ("phone", 1), ("key", 1), ("cross", 1),
            ])
            if loot[0] == "rub":
                s["rub"] += loot[1]
            else:
                self.add(*loot)
            s["flags"]["knows_stashes"] = True
            self.event("stash", "Игрок нашёл схрон в " + NAMES[loc] + ".", self.witnesses())
            self.toast("Схрон! %s ×%d" % (ITEMS.get(loot[0], {"name": "Рубли"})["name"], loot[1]), "good")
            return loot
        self.toast("Ничего. Только пыль и чужие надежды.")
        return None

    def stash_put(self, item):
        s = self.s
        self.take(item, 1)
        st = s["stashes"].setdefault(str(s["loc"]), {"found": True, "items": []})
        st["found"] = True
        st["items"].append(item)
        self.advance(COSTS["stash"], "закладка в схрон")
        self.toast("Спрятал: " + ITEMS[item]["name"])

    def stash_take(self, item):
        s = self.s
        st = s["stashes"].get(str(s["loc"]), {"items": []})
        if item not in st["items"]:
            raise ValueError("В этом схроне такого нет")
        st["items"].remove(item)
        self.add(item, 1)
        self.advance(COSTS["stash"], "достал из схрона")

    # ------------------------------------------------------------ храм
    def pray(self, sin=None):
        s = self.s
        if s["loc"] != LOC_INDEX["temple"]:
            raise ValueError("Бог — в храме. Или везде, но лучше в храме.")
        t = s["temple"]
        if t["day"] == s["day"] and t["prayers"] >= 2:
            raise ValueError("Бог занят. Приходи завтра.")
        t["prayers"] += 1
        self.advance(COSTS["pray"], "молитва")
        clean = 0
        for d in DIMS:
            if s["karma"][d] < 0:
                step = min(-s["karma"][d], 12)
                s["karma"][d] += step
                clean += step
        if clean:
            s["temple"]["grace"] = s["day"]
            self.event("prayer", "Игрок помолился и отпустил часть грехов.", [])
            self.toast("Карма очищена на %d. Господь всё видел." % clean, "good")
        else:
            self.toast("Господь молчит. Зато свеча горит ровно.")
        if s["dropped"] and clean >= 8:
            s["humiliations"] = max(0, s["humiliations"] - 1)
            self.redeem("прощён в храме", amount=6)
        return clean

    def talk_god(self, mode):
        """Разговор с Господом в храме. mode: признание / вопрос / благодарность."""
        s = self.s
        if s["loc"] != LOC_INDEX["temple"]:
            raise ValueError("Бог — в храме.")
        t = s.setdefault("temple", {"day": s["day"], "prayers": 0, "grace": 0, "talks": 0})
        t.setdefault("talks", 0)
        if t.get("talk_day") != s["day"]:
            t["talk_day"] = s["day"]
            t["talks"] = 0
        if t["talks"] >= 2:
            raise ValueError("На сегодня хватит. Господь тоже занят.")
        t["talks"] += 1
        self.advance(15, "разговор с Господом")
        if mode == "confess":
            cleaned = 0
            for dim in DIMS:
                if s["karma"][dim] < 0:
                    step = min(-s["karma"][dim], 8)
                    s["karma"][dim] += step
                    cleaned += step
            line = ("Ты назвал вслух всё, что давило. Стало тише. Карма очищена на %d." % cleaned
                    if cleaned > 0 else "Нечего было сказать. Или ты просто боишься сказать.")
            return {"text": line, "clean": cleaned,
                    "god": "— Я слышу не слова. Я слышу, как ты врёшь." if cleaned == 0 else
                           "— Иди. И больше не делай так."}
        if mode == "ask":
            s["karma"]["empathy"] = clamp(s["karma"]["empathy"] + 1)
            answer = self.rng.choice([
                "— Вопрос не в том, за что тебе это. Вопрос в том, что ты с этим сделаешь.",
                "— Я не выдаю справок. Я выдаю утро. Пользуйся.",
                "— Ты просишь свободы, а держишь обиду. Освободи сначала её.",
            ])
            return {"text": "Ты спросил: «За что?» И сам понял, что вопрос глупый.",
                    "clean": 0, "god": answer}
        s["karma"]["honor"] = clamp(s["karma"]["honor"] + 1)
        return {"text": "Ты сказал спасибо — за то, что жив, за то, что есть ещё день.",
                "clean": 0, "god": "— Не благодари. Просто не подведи."}

    def confess_line(self):
        s = self.s
        ka = s["karma"]
        worst = min(DIMS, key=lambda d: ka[d])
        if ka[worst] >= 0:
            return "Не в чем каяться. Странно, но приятно."
        return {
            "empathy": "Ты холоден к людям. Даже к тем, кто тебе ничего не сделал.",
            "honor": "Ты обещал и не сделал. Это тяжелее, чем кажется.",
            "cunning": "Ты слишком много врал. Даже себе.",
        }[worst]

    # ------------------------------------------------------------ свиданка
    def visit_start(self):
        s = self.s
        if s["loc"] != LOC_INDEX["visit"]:
            raise ValueError("Свиданка — в комнате за коридором.")
        if s["visit"]["used"]:
            raise ValueError("Одна свиданка в день. Так решил не ты.")
        s["visit"]["used"] = True
        self.advance(COSTS["visit"], "свиданка")
        self.event("visit", "Игрок на свидании.", ["mamka"])

    # ------------------------------------------------------------ боссы
    def boss_alive(self, k):
        return k in BOSSES and k not in self.s["defeated"]

    def boss_defeat(self, k):
        s = self.s
        if k in s["defeated"]:
            return
        s["defeated"].append(k)
        info = BOSSES.get(k, {"title": self.npcs[k]["name"], "line": "Он пал.", "drop": None})
        s["boss_news"].append({"boss": k, "day": s["day"]})
        if info.get("drop"):
            self.add(info["drop"], 1)
            if info["drop"] not in s["relics"]:
                s["relics"].append(info["drop"])
        self.rise(14, "победа над " + info["title"])
        for other in self.npcs:
            if other == k or other in AUTHORITIES:
                continue
            s["relations"][other] = clamp(s["relations"].get(other, 0) + (3 if other in PRISONERS else 1))
        self.event("boss_down", "Игрок победил " + info["title"] + ". Зона это запомнит.", [], public=True)
        self.toast("Босс повержен: %s. Иконка убрана с карты." % info["title"], "good")
        s["story"]["flags"]["boss_" + k] = True

    # ------------------------------------------------------------ экономика разговоров
    def money_reset(self):
        pass

    def award_dialogue(self, k, text, result=None):
        """Небольшой доход за разговор, с защитой от спама."""
        s = self.s
        e = s["dialogue_money"] if "dialogue_money" in s else {"day": 0, "earned": 0, "seen": []}
        s["dialogue_money"] = e
        if e.get("day") != s["day"]:
            e.update(day=s["day"], earned=0, seen=[])
        if k not in PRISONERS or k not in self.witnesses():
            return 0
        tokens = set(re.findall(r"[а-яёa-z0-9]+", text.casefold()))
        if len(text.strip()) < 28 or len(tokens) < 5:
            return 0
        digest = hashlib.sha256(" ".join(sorted(tokens)).encode()).hexdigest()
        if digest in e["seen"]:
            return 0
        e["seen"].append(digest)
        e["seen"] = e["seen"][-200:]
        amount = 2 if e["earned"] < 12 else 0
        if result and isinstance(result.get("economy"), dict) and result["economy"].get("success"):
            amount += 2
        amount = min(amount, 18 - e["earned"])
        if amount > 0:
            s["rub"] += amount
            e["earned"] += amount
        return max(0, amount)

    # ------------------------------------------------------------ покупки
    def buy(self, item):
        s = self.s
        info = ITEMS.get(item)
        if not info:
            raise ValueError("Нет такого товара")
        if not info.get("price"):
            raise ValueError("Не продаётся")
        if s["rub"] < info["price"]:
            raise ValueError("Не хватает рублей")
        s["rub"] -= info["price"]
        if item == "knife":
            s["gear"].update(weapon="Заточка", damage=24 + 2 * s["training"]["str"])
        elif item == "armor":
            s["gear"]["armor"] = 7
        elif item == "shoe":
            s["gear"]["accuracy"] = min(0.92, s["gear"]["accuracy"] + 0.06)
        else:
            self.add(item, 1)
        if item in ("knife", "armor", "shoe"):
            self.add(item, 1)
        self.event("purchase", "Покупка: " + info["name"], self.witnesses())

    # ------------------------------------------------------------ аренда/долги (совместимость)
    def borrow(self, k):
        if k not in self.witnesses():
            raise ValueError("NPC не рядом")
        s = self.s
        if any(o["npc"] == k and o["status"] == "active" for o in s["obligations"]):
            raise ValueError("Сначала верни долг")
        s["rub"] += 10
        s["obligations"].append({"id": uuid.uuid4().hex, "npc": k, "amount": 10,
                                 "due": s["day"] + 1, "status": "active"})
        self.event("debt", "Игрок занял 10 рублей до завтра.", [k])
        self.advance(5, "долг")

    def repay(self, k):
        s = self.s
        o = next((o for o in s["obligations"] if o["npc"] == k and o["status"] == "active"), None)
        if not o or k not in self.witnesses():
            raise ValueError("Нет доступного долга этому NPC")
        if s["rub"] < o["amount"]:
            raise ValueError("Не хватает рублей")
        s["rub"] -= o["amount"]
        o["status"] = "paid"
        s["relations"][k] = clamp(s["relations"].get(k, 0) + 4)
        self.event("debt_paid", "Игрок вернул долг.", [k])
        self.rise(2, "долг закрыт")

    def decision(self, k, kind):
        s = self.s
        if k not in self.witnesses():
            raise ValueError("NPC не рядом")
        if kind == "help" and self.inv("cig") < 2:
            raise ValueError("Нужны 2 сигареты")
        loc = s["loc"]
        if kind in ("help", "theft", "betrayal"):
            self.advance(10, "решение")
        if kind == "help":
            self.add("cig", -2)
            delta, text = 6, "Игрок отдал %s две сигареты." % self.npcs[k]["name"]
        elif kind == "theft":
            s["rub"] += 15
            delta, text = -22, "%s поймал игрока на краже 15 рублей." % self.npcs[k]["name"]
        elif kind == "frame":
            if not any(self.has(i) for i in ("knife", "phone", "chifir")):
                raise ValueError("Подставить можно только вещью: заточка, телефон или чифирь.")
            item = next(i for i in ("phone", "knife", "chifir") if self.has(i))
            self.take(item)
            if self.rng.random() < 0.45 + 0.05 * s["training"]["cun"]:
                st = s["stashes"].setdefault(str(loc), {"found": True, "items": []})
                st["items"].append(item)
                s["relations"][k] = clamp(s["relations"].get(k, 0) - 12)
                s["karma"]["honor"] = clamp(s["karma"]["honor"] - 3)
                for other in PRISONERS:
                    if other != k:
                        s["relations"][other] = clamp(s["relations"].get(other, 0) - 1)
                self.event("frame", "Игрок подставил %s: в заначке нашлась %s."
                           % (self.npcs[k]["name"], ITEMS[item]["name"].lower()), self.witnesses())
                self.rise(3, "подстава удалась")
                self.advance(20, "подстава")
                return "ok"
            self.humiliate("подстава раскрылась", strong=True)
            self.event("frame_fail", "Подстава раскрылась. Игрока опустили.", self.witnesses(), public=True)
            self.advance(30, "провал подставы")
            return "fail"
        elif kind == "betrayal":
            s["rub"] += 25
            delta, text = -26, "Игрок сдал %s охране. Об этом узнали." % self.npcs[k]["name"]
            self.humiliate("стукачество", strong=True)
        else:
            raise ValueError("Нет действия")
        s["relations"][k] = clamp(s["relations"].get(k, 0) + delta)
        self.event(kind, text, self.witnesses(), public=(kind == "betrayal"))
        if kind == "help":
            self.rise(1, "помощь")

    # ------------------------------------------------------------ инициативы NPC
    def candidate(self):
        s = self.s
        if len([n for n in s["notices"] if n["status"] == "pending"]) >= 3:
            return None
        pool = self.witnesses()
        return self.rng.choice(pool) if pool else None

    def initiative(self, k, obj):
        s = self.s
        if k not in self.witnesses():
            return None
        if not isinstance(obj, dict) or not isinstance(obj.get("reply", ""), str):
            raise ValueError("Некорректная инициатива")
        a = obj.get("action", "wait")
        a = a if a in ("wait", "talk", "warn", "offer_task", "attack") else "wait"
        ids = obj.get("evidence", []) if isinstance(obj.get("evidence"), list) else []
        facts = [e for e in self.known(k) if e["id"] in ids and e["kind"] in ("theft", "betrayal", "assault") and e.get("verified")]
        if a == "attack" and (not facts or s["relations"].get(k, 0) > -15):
            a = "warn"
        topic = str(obj.get("topic", ""))[:90] or a
        st = s["npc_state"][k]
        if topic == st.get("last_topic") and s["time"] - st.get("last_turn", -99) < 30:
            return None
        st["last_turn"] = s["time"]
        st["last_topic"] = topic
        o = {"id": uuid.uuid4().hex, "npc": k, "action": a, "reply": obj["reply"][:1800],
             "topic": topic, "day": s["day"], "status": "pending",
             "evidence": ids, "rumors_used": obj.get("rumors_used", []) if isinstance(obj.get("rumors_used"), list) else [],
             "task": obj.get("task", "work")}
        s["notices"].append(o)
        s["notices"] = s["notices"][-60:]
        return o

    def resolve(self, id, accept):
        s = self.s
        o = next(x for x in s["notices"] if x["id"] == id)
        if o["status"] != "pending":
            return None
        if not accept:
            o["status"] = "later"
            return None
        if o["npc"] not in self.witnesses():
            raise ValueError("NPC уже ушёл")
        if o["action"] == "offer_task":
            task = o.get("task", "work")
            if task == "help" and self.inv("cig") < 2:
                raise ValueError("Нужны 2 сигареты")
            self.advance(30, "дело для " + self.npcs[o["npc"]]["name"])
            if task == "help":
                self.add("cig", -2)
            elif task == "work":
                s["rub"] += 6
            else:
                s["training"]["str"] += 1
            s["relations"][o["npc"]] = clamp(s["relations"].get(o["npc"], 0) + 5)
            self.event("task_done", "Игрок выполнил дело: " + task, [o["npc"]])
            self.rise(2, "дело исполнено")
            o["status"] = "accepted"
            return "done"
        o["status"] = "accepted"
        return o["action"]


# ==================================================================== дуэль
class Duel:
    def __init__(self, w, k, ambush=False, seed=None):
        self.w = w
        self.k = k
        self.rng = random.Random(seed)
        self.hp = w.s["hp"]
        self.max_hp = w.s["hp_max"]
        boss = BOSSES.get(k)
        self.max_enemy = boss["hp"] if boss else (120 if w.npcs[k].get("boss") else 90)
        self.enemy = w.s["npc_hp"].get(k, self.max_enemy)
        self.is_boss = bool(boss) and k not in w.s["defeated"]
        self.round = 1
        self.done = False
        self.finished = False
        self.log = []
        self.result = "Отступление"
        self.commit()
        if ambush:
            self.hp = max(0, self.hp - 12)
            self.log.append("Внезапный удар: -12 HP.")
        self.check()

    def commit(self):
        self.emove = self.rng.randrange(3)
        self.eaim = self.rng.randrange(3)
        self.guard = self.rng.random() < 0.25

    def check(self):
        if self.hp <= 0 or self.enemy <= 0:
            self.done = True
            self.result = ("Обоюдное поражение" if self.hp <= 0 and self.enemy <= 0
                           else "Поражение" if self.hp <= 0 else "Победа")

    def strike(self, aim, move, stance):
        if self.done:
            return
        if aim not in range(3) or move not in range(3) or stance not in ("attack", "guard", "aim"):
            raise ValueError("Неверный ход")
        s = self.w.s
        g = s["gear"]
        power = g["damage"] + s["training"]["str"]
        cost = 5 if stance == "guard" else 7 if stance == "aim" else 9
        exhausted = s["stamina"] < cost
        s["stamina"] = max(0, s["stamina"] - cost)
        damage = int(power * 0.55) if exhausted else power
        acc = g["accuracy"] - (0.15 if exhausted else 0) + (0.06 if s["stamina"] > 70 else 0)
        hit = max(0.1, min(0.95, acc + (0.18 if aim == self.emove else -0.18) + (0.1 if stance == "aim" else 0)))
        enemy_block = 6 if self.guard else 2
        dmg = max(1, damage + self.rng.randint(-3, 3) - enemy_block) if self.rng.random() < hit else 0
        shield = g["armor"] + (9 if stance == "guard" else 0)
        taken = max(1, 19 + self.rng.randint(-3, 3) - shield) if self.rng.random() < (0.86 if self.eaim == move else 0.48) else 0
        if stance == "guard":
            s["stamina"] = min(s["stamina_max"], s["stamina"] + 7)
        self.enemy = max(0, self.enemy - dmg)
        self.hp = max(0, self.hp - taken)
        self.log.append("Раунд %d: нанесли %d, получили %d." % (self.round, dmg, taken))
        self.round += 1
        if exhausted:
            self.log.append("Выдохлись: удар слабее. Защита помогает отдышаться.")
        self.check()
        if not self.done and self.round > 30:
            self.done = True
            self.result = "Ничья"
        if not self.done:
            self.commit()
        s["hp"] = max(1, self.hp)
        s["npc_hp"][self.k] = self.enemy

    def finish(self):
        if self.finished:
            return
        self.finished = True
        w = self.w
        s = w.s
        s["hp"] = max(1, self.hp)
        s["npc_hp"][self.k] = self.enemy
        self.w.advance(10, "дуэль")
        if not self.hp:
            s["rub"] = max(0, s["rub"] - 15)
            w.humiliate("проиграл " + w.npcs[self.k]["name"], strong=False)
        won = self.done and self.hp > 0 and self.enemy == 0
        if won:
            s["rub"] += 40
            if self.k not in s["defeated"] and not self.is_boss:
                s["defeated"].append(self.k)
            w.rise(6, "победа в дуэли")
            if self.is_boss:
                w.boss_defeat(self.k)
        w.event("combat", "Бой с %s: %s" % (w.npcs[self.k]["name"], self.result),
                [self.k], public=True)
