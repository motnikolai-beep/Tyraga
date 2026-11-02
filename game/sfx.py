# -*- coding: utf-8 -*-
"""Простые синтезированные звуки (numpy + pygame.mixer). Если звук недоступен — тихо отключается."""


class Sfx:
    def __init__(self):
        self.ok = False
        self.snd = {}
        try:
            import numpy as np
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1)

            def tone(freq, dur, vol=0.25, square=False, slide=0.0):
                n = int(22050 * dur)
                t = np.arange(n) / 22050.0
                ph = 2 * np.pi * (freq * t + slide * t * t / 2)
                w = np.sign(np.sin(ph)) if square else np.sin(ph)
                a = (w * (np.linspace(1, 0, n) ** 1.6) * vol * 32767).astype(np.int16)
                return pygame.sndarray.make_sound(a)

            self.snd = {"click": tone(660, 0.05), "ok": tone(880, 0.18, slide=500), "bad": tone(200, 0.28, square=True, slide=-250),
                        "hit": tone(130, 0.14, 0.3, True), "day": tone(330, 0.5, 0.2, slide=-120), "win": tone(520, 0.6, 0.25, slide=700)}
            self.ok = True
        except Exception:
            self.ok = False

    def play(self, name):
        if self.ok and name in self.snd:
            try:
                self.snd[name].play()
            except Exception:
                pass
