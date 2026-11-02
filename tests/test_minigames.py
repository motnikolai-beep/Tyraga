# -*- coding: utf-8 -*-
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game import minigames as mg

try:
    from game.core import Game
except Exception:  # запасной вариант, если ядро недоступно
    class Game:
        def __init__(self, seed=None):
            self.rng = random.Random(seed); self.events = []; self.log = []
            self.s = {"rep": 50, "dig": 0, "cig": 20, "echo": None}
        def say(self, t): self.log.append(t)
        def apply(self, fx):
            for e in ([fx] if isinstance(fx, str) else fx): self.log.append("fx " + e)


def play_random(kind, seed):
    g = Game(seed)
    m = mg.create(kind, g)
    rng = random.Random(seed)
    for _ in range(3000):
        if m.done: break
        if kind == "porridge": m.open(rng.randrange(36))
        elif kind == "poker": m.act(rng.randrange(4))
        elif kind == "chess": m.play(rng.randrange(3))
        elif kind == "tunnel": m.key(rng.choice(["up", "down", "left", "right", "right", "right"]))
        elif kind == "dance": m.update(0.4); m.key(rng.choice(["left", "up", "down", "right"]))
        elif kind == "factory":
            if m.stage == 0: m.pick_target(rng.randrange(4))
            else: m.pick_template(rng.randrange(4))
    assert m.done, kind
    m.settle(); m.settle()
    return m


def test_all_minigames_finish():
    for kind in mg.KINDS:
        for seed in range(40):
            play_random(kind, seed)


def test_porridge_all_items():
    g = Game(1); m = mg.create("porridge", g)
    for i in sorted(m.pos): m.open(i)
    assert m.done and m.found == 5 and m.reward == 16 - 5 + 3


def test_dance_timeout():
    g = Game(2); m = mg.create("dance", g)
    for _ in range(40): m.update(1.1)
    assert m.done and m.sc == 0


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK", n)
