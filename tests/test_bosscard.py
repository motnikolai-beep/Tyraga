"""Заставка босса и быстрая загрузка фонов. Работает и в исходниках, и в готовой сборке v12.

Tk здесь не запускается: проверяется логика и картинки, собранные Pillow.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PIL import Image

import bosscard
import gfx
import world

NPCS = json.loads((ROOT / 'npcs.json').read_text(encoding='utf8'))
BOSSES = [k for k, v in NPCS.items() if v['boss']]


class BossCard(unittest.TestCase):
    def test_bundled_font_has_cyrillic(self):
        self.assertTrue((ROOT / bosscard.FONT).is_file())
        self.assertTrue((ROOT / 'assets' / 'fonts' / 'OFL.txt').is_file())
        font = bosscard._font(ROOT, 40)
        self.assertEqual(font.getname()[0], 'Oswald')
        self.assertGreater(bosscard._width(font, 'РЕШЁТКИН'), 100)

    def test_card_is_rendered_for_every_boss(self):
        for boss in BOSSES:
            npc = NPCS[boss]
            with Image.open(ROOT / 'assets' / ('loc_%d.jpg' % npc['home'])) as backdrop:
                card = bosscard.render(ROOT, npc, world.NAMES[npc['home']], bosscard.SIZE, backdrop)
            self.assertEqual(card.size, bosscard.SIZE)
            self.assertEqual(card.mode, 'RGB')
            colours = card.resize((48, 24)).getcolors(48 * 24)
            self.assertGreater(len(colours), 40, 'заставка %s выглядит пустой' % boss)
            yellow = sum(count for count, (r, g, b) in card.getcolors(card.width * card.height) if r > 220 and 170 < g < 215 and b < 70)
            self.assertGreater(yellow, 1500, 'нет фирменного жёлтого на заставке %s' % boss)

    def test_card_survives_missing_backdrop_and_long_names(self):
        npc = dict(NPCS['mat'], name='Мать-Смотрительница Всех Кошек Зоны', tagline='')
        card = bosscard.render(ROOT, npc, 'Очень длинное название локации', (640, 313), None)
        self.assertEqual(card.size, (640, 313))

    def test_tagline_falls_back_to_the_first_phrase_of_the_role(self):
        self.assertEqual(bosscard.tagline({'tagline': ' Семь кошек. '}), 'Семь кошек.')
        self.assertEqual(bosscard.tagline({'role': 'Прямой немногословный силач. Ценит верность.'}), 'Прямой немногословный силач.')
        self.assertEqual(bosscard.tagline({}), '')

    def test_fight_window_shows_the_card_only_for_bosses(self):
        import test_ui_stub as stub  # подменяет tkinter заглушкой до импорта main
        main = stub.main
        original = main.BASE
        with tempfile.TemporaryDirectory() as td, patch.object(main.ImageTk, 'PhotoImage', lambda image: image), \
                patch.object(main.App, 'connect', lambda s: None):
            base = Path(td)
            shutil.copytree(ROOT / 'assets', base / 'assets')
            shutil.copy(ROOT / 'npcs.json', base / 'npcs.json')
            (base / '.env').write_text('CHAT_FAST_MODE=true\nGOSSIP_ENABLED=true\n', encoding='utf8')
            main.BASE = base
            try:
                app = main.App(stub.Widget())
                app.new_game('normal')
                app.menu.hide()
                app.go(0)
                app.fight('zub')
                window = app.battle_window
                self.assertEqual(window.refs['intro'].size, (960, 470))
                self.assertGreaterEqual(window.eng.intro, bosscard.INTRO_SECONDS - .2)
                window.draw()
                for _ in range(80):
                    window.tick(1 / 30)
                self.assertEqual(window.eng.phase, 'fight')
                window.close()
                app.fight('kol')
                window = app.battle_window
                self.assertIsNone(window.refs['intro'])
                self.assertLess(window.eng.intro, 2.0)
                window.close()
            finally:
                main.BASE = original


class Gfx(unittest.TestCase):
    def test_4k_background_is_decoded_reduced_but_never_too_small(self):
        with tempfile.TemporaryDirectory() as td:
            master = Path(td) / 'loc.jpg'
            Image.linear_gradient('L').resize((3840, 2160)).convert('RGB').save(master, quality=90)
            full = gfx.open_rgb(master)
            self.assertEqual(full.size, (3840, 2160))
            for want in ((1600, 900), (960, 470), (228, 150)):
                image = gfx.open_rgb(master, want)
                self.assertEqual(image.mode, 'RGB')
                self.assertGreaterEqual(image.width, want[0])
                self.assertGreaterEqual(image.height, want[1])
                self.assertLess(image.width, 3840)

    def test_every_location_background_opens(self):
        for index in range(len(world.NAMES)):
            image = gfx.open_rgb(ROOT / 'assets' / ('loc_%d.jpg' % index), (1600, 900))
            self.assertGreaterEqual(image.width, 1600, world.NAMES[index])
            self.assertAlmostEqual(image.width / image.height, 16 / 9, places=2)

    def test_fingerprint_sees_the_picture_not_the_file(self):
        backgrounds = [ROOT / 'assets' / ('loc_%d.jpg' % index) for index in range(len(world.NAMES))]
        self.assertEqual(gfx.lookalikes(backgrounds), [], 'у двух локаций один и тот же фон')
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / 'copy.jpg'
            with Image.open(backgrounds[0]) as im:
                im.convert('RGB').resize((640, 360)).save(copy, quality=55)
            self.assertLessEqual(gfx.distance(gfx.fingerprint(backgrounds[0]), gfx.fingerprint(copy)), gfx.SAME_PICTURE)
            self.assertEqual(len(gfx.lookalikes([backgrounds[0], backgrounds[1], copy])), 1)

    def test_every_hero_has_a_face_of_their_own(self):
        """Портреты героев не повторяются (кроме тех, кто в исходниках v11 ещё делит картинку)."""
        files = sorted({ROOT / 'assets' / (npc['portrait'] + '.jpg') for npc in NPCS.values()})
        self.assertEqual(gfx.lookalikes(files), [])

    def test_png_and_missing_size_are_fine(self):
        self.assertEqual(gfx.open_rgb(ROOT / 'assets' / 'player_avatar.png', (10, 10)).mode, 'RGB')


if __name__ == '__main__':
    unittest.main()
