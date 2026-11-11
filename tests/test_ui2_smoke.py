# -*- coding: utf-8 -*-
"""Дымовой тест App2 на заглушке pygame (нужны tests/fake_pygame.py и применённый apply_update.py)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
try:
    import fake_pygame
except ModuleNotFoundError:
    # Тест старого интерфейса на pygame (v7): заглушки fake_pygame в проекте больше нет.
    import unittest
    raise unittest.SkipTest('legacy v7 test: fake_pygame is no longer part of the project')


def run():
    script = []
    pg = fake_pygame.install(script)
    for n, v in (("K_LEFT", 1073741904), ("K_RIGHT", 1073741903), ("K_UP", 1073741906), ("K_DOWN", 1073741905)):
        setattr(pg, n, v)
    from game import ui2
    app = ui2.App2(); g = app.g
    app.new_game(False)
    for aid in ("porr", "poker", "chess", "dig", "dance", "factory"):
        g.s.update(ap=6, cig=30, hp=100, rep=60)
        g.do_act(aid); app.post()
        assert app.mode == "minigame", (aid, app.mode)
        for _ in range(400):
            if app.mgame.done: break
            k = app.mgame.kind
            for r, cb in list(app.buttons):
                pass
            app.buttons = []; app.draw()
            btn = [cb for r, cb in app.buttons if cb]
            if btn: btn[__import__("random").randrange(len(btn))]()
            app.update(0.3)
        app.buttons = []; app.draw()
        assert app.mgame.done, aid
        app.buttons = []; app.draw()
        [cb for r, cb in app.buttons if cb][-1]()
        assert app.mode == "scene", (aid, app.mode)
    print("UI2 smoke OK")

if __name__ == "__main__":
    run()
