"""Арт v12 «Borderlands × реальность»: 4K-мастера, правила сборки, уникальность.

Проверяет исходное дерево (art_4k/ и build_v12.py). В готовую сборку этот файл не попадает:
там нет ни мастеров, ни сборщика. Tk здесь не запускается.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if not (ROOT / 'build_v12.py').is_file() or not (ROOT / 'art_4k').is_dir():
    raise unittest.SkipTest('тест конвейера арта: нужен исходный репозиторий с art_4k/ и build_v12.py')
from PIL import Image

import build_v12 as B
import world

ART = ROOT / 'art_4k'
NPCS = json.loads((ROOT / 'npcs.json').read_text(encoding='utf8'))
BOSSES = [k for k, v in NPCS.items() if v['boss']]
# Портрет босса: имя исходника из сборки (включая героев без исходного PNG).
BOSS_ART = {k: (B.NPC[k][0] if k in B.NPC else B.EXTRA_PORTRAITS[k]) for k in BOSSES}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Masters(unittest.TestCase):
    def test_every_location_has_a_unique_4k_master(self):
        seen = {}
        for index, file in enumerate(B.LOCS):
            master = ART / 'locations' / (Path(file).stem + '.jpg')
            self.assertTrue(master.is_file(), 'нет 4K-фона для локации %d «%s»' % (index, B.LOC_NAMES[index]))
            with Image.open(master) as im:
                self.assertEqual(im.size, B.LOC_4K, master.name)
                self.assertEqual(im.mode, 'RGB')
            seen.setdefault(digest(master), []).append(master.name)
        self.assertEqual(len(seen), 12, 'фоны локаций должны быть разными: %s' % [v for v in seen.values() if len(v) > 1])

    def test_masters_are_named_after_known_sources(self):
        known = {Path(f).stem for f in B.LOCS}
        for master in (ART / 'locations').glob('*.jpg'):
            self.assertIn(master.stem, known, master.name)
        known = {Path(v[0]).stem for v in B.NPC.values()} | {Path(f).stem for f in B.EXTRA_PORTRAITS.values()}
        for master in (ART / 'characters').glob('*.jpg'):
            self.assertIn(master.stem, known, master.name)
            with Image.open(master) as im:
                self.assertEqual(im.height, 3840, master.name)
                self.assertGreaterEqual(im.width, 2400, master.name)

    def test_every_boss_has_art_of_their_own(self):
        """8 боссов — 8 разных картинок (стилизованный мастер или, пока он в очереди, исходный PNG)."""
        self.assertEqual(len(BOSSES), 8)
        pictures = {}
        for boss, file in BOSS_ART.items():
            source, _stylised = B.art_source(ROOT, 'characters', file)
            self.assertTrue(source.is_file(), 'у босса %s нет своей картинки: %s' % (boss, file))
            pictures[boss] = digest(source)
        self.assertEqual(len(set(pictures.values())), 8)

    def test_no_two_masters_show_the_same_picture(self):
        import gfx
        for folder in ('locations', 'characters'):
            self.assertEqual(gfx.lookalikes(sorted((ART / folder).glob('*.jpg'))), [], folder)

    def test_location_names_match_the_art(self):
        """После текстовой адаптации имена локаций совпадают со смыслом картинок."""
        self.assertEqual([B.text(name) for name in world.NAMES], B.LOC_NAMES)
        meaning = ['cell', 'yard', 'kitchen', 'corridor', 'shower', 'cellblock', 'armory', 'library', 'chapel', 'isolation', 'theatre', 'underpass']
        for file, word in zip(B.LOCS, meaning):
            self.assertIn(word, file)


class BuildRules(unittest.TestCase):
    def test_art_source_prefers_the_4k_master(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'первая половина').mkdir()
            (root / 'первая половина' / '01_cell.png').write_bytes(b'png')
            self.assertEqual(B.art_source(root, 'locations', '01_cell.png'), (root / 'первая половина' / '01_cell.png', False))
            (root / 'art_4k' / 'locations').mkdir(parents=True)
            (root / 'art_4k' / 'locations' / '01_cell.jpg').write_bytes(b'jpg')
            self.assertEqual(B.art_source(root, 'locations', '01_cell.png'), (root / 'art_4k' / 'locations' / '01_cell.jpg', True))

    def test_portrait_is_cropped_for_the_game_loaders(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'p.jpg'
            B.save_portrait(B.art_source(ROOT, 'characters', B.NPC['zub'][0])[0], target)
            with Image.open(target) as im:
                self.assertEqual(im.size, B.PORTRAIT)
        self.assertAlmostEqual(B.PORTRAIT[1] / B.PORTRAIT[0], 1.58, places=2)  # пропорция портрета в main.draw

    def test_every_boss_has_a_tagline(self):
        self.assertEqual(sorted(B.TAGLINES), sorted(BOSSES))
        for line in B.TAGLINES.values():
            self.assertTrue(4 < len(line) <= 48, line)

    def test_texts_follow_the_pictures(self):
        """На картинках Курсант и Бумажкина — женщины, Цепи — человек в цепях, а не робот."""
        self.assertEqual(B.text('Генерал сам находит у вас три нарушения.'), 'Курсант сама находит у вас три нарушения.')
        self.assertEqual(B.text('Генерал нашёл у вас лишнее и забрал всё запрещённое.'), 'Курсант нашла у вас лишнее и забрала всё запрещённое.')
        self.assertEqual(B.text('Бухгалтер доволен'), 'Бумажкина довольна')
        self.assertEqual(B.text('Убедить робота в своей благонадёжности'), 'Убедить каптёрщика в своей благонадёжности')
        self.assertEqual(B.text('Сдать всех Генерал-инспектору'), 'Сдать всех Курсанту')
        adapted = ''.join(B.transform_source((ROOT / name).read_text(encoding='utf8'))
                          for name in ('story_data.py', 'story10.py', 'lore.py', 'core.py', 'main.py', 'menu.py'))
        for leftover in ('Генерал', 'Бухгалтер', 'робот', 'Страж-9', 'Курсант расцвёл', 'Курсант нашёл', 'Курсант забыл ',
                         'Курсант удовлетворён', 'Бумажкина доволен', 'Бумажкина выписал ', 'Бумажкина закрыл '):
            self.assertFalse(leftover in adapted, leftover)

    def test_texts_follow_the_locations(self):
        """Названия мест стоят в верном падеже, ремесло — в оружейной-мастерской, а не в библиотеке."""
        import re
        adapted = ''.join(B.transform_source((ROOT / name).read_text(encoding='utf8'))
                          for name in ('story_data.py', 'story10.py', 'lore.py', 'core.py', 'main.py', 'menu.py', 'minigames.py'))
        for broken in ('Часовняе', 'в Часовня ', 'в Изолятор ', 'В Изолятор ', 'Библиотека: смена', 'библиотеке полно железа',
                       'углу библиотеке', 'из кухне', 'проход свободны', 'Часовня теперь ваш.', 'ШИЗО', 'Прачечн', 'ПРАЧЕЧН', 'Столовая',
                       'Уговорить Бумажкиной', 'Цепи скрипит', 'Цепи обрабатывает'):
            self.assertFalse(broken in adapted, broken)
        self.assertIsNone(re.search('Смотрител(ь[^н]|я|ю|ем)', adapted), 'старое имя Тени осталось в текстах')
        self.assertIn('Мать-Смотрительница', adapted)
        self.assertIn('Оружейная-мастерская: смена', adapted)

    def test_roles_describe_what_is_drawn(self):
        self.assertIn('стажёрка', B.NPC['gen'][2])
        self.assertIn('цеп', B.NPC['str'][2])
        self.assertIn('шприц', B.NPC['cook'][2])


if __name__ == '__main__':
    unittest.main()
