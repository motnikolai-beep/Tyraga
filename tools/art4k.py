#!/usr/bin/env python3
"""4K-мастеринг стилизованных артов «Тюряги» (стиль «Borderlands × реализм»).

Что делает
    Берёт уже перерисованный арт (PNG около 1K), увеличивает его в 4 раза
    нейросетью «Upscayl Lite» (upscayl-lite-4x, формат ncnn, работает на CPU)
    и сохраняет мастер-файл в art_4k/:
        art_4k/locations/<имя>.jpg    3840x2160
        art_4k/characters/<имя>.jpg   высота 3840 (обычно 2880x3840)
    Это нейросетевое увеличение перерисовки, а не нативный 4K-рендер.

Зависимости (нужны только этому инструменту, игре и сборке — нет)
    pip install pillow numpy ncnn

Использование
    python tools/art4k.py loc 01_cell     путь/к/перерисовке.png
    python tools/art4k.py chr 02_baykal   путь/к/перерисовке.png
    python tools/art4k.py preview         # пересобрать art_4k/preview/*.jpg
    python tools/art4k.py audit           # таблица: что готово, уникальность
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / 'art_4k'
ORIGINALS = ROOT / 'первая половина'
MODELS = Path(__file__).resolve().parent / '.models'

# Модель «Upscayl Lite» из открытого проекта Upscayl (репозиторий под AGPL-3.0, основан на Real-ESRGAN).
# Веса не хранятся в этом репозитории: скачиваются один раз в tools/.models/ и сверяются по sha256.
MODEL_REPO = 'upscayl/upscayl'
MODEL_REF = 'a00d55fee90e0f9435d5eaa86e76700df8199af8'
MODEL_FILES = {
    'upscayl-lite-4x.param': '22174924330297357434ad21ed0af7f4b820008d2a502b492754d130d4142714',
    'upscayl-lite-4x.bin': '85ee266b632a765a725425ba6a5620c088c8aa2939a03063b2d83b3462724cc1',
}

LOC_SIZE = (3840, 2160)
CHR_HEIGHT = 3840
CHR_SIZE = (2880, CHR_HEIGHT)
FOLDERS = {'loc': 'locations', 'chr': 'characters'}
JPEG = dict(quality=94, subsampling=0, optimize=True)  # 4:4:4 — чёткие цветные контуры


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_model() -> Path:
    """Скачать веса (один раз) и проверить контрольные суммы."""
    MODELS.mkdir(exist_ok=True)
    for name, digest in MODEL_FILES.items():
        target = MODELS / name
        if target.is_file() and _sha256(target) == digest:
            continue
        url = 'https://api.github.com/repos/%s/contents/resources/models/%s?ref=%s' % (MODEL_REPO, name, MODEL_REF)
        headers = {'Accept': 'application/vnd.github.raw', 'User-Agent': 'tyuryaga-art4k'}
        token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        print('Скачиваю', name, '...', flush=True)
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as response:
            target.write_bytes(response.read())
        if _sha256(target) != digest:
            target.unlink()
            raise RuntimeError('Контрольная сумма не совпала: ' + name)
    return MODELS


def upscale_x4(image: Image.Image, tile: int = 256, pad: int = 16, threads: int | None = None) -> Image.Image:
    """Увеличение x4 по плиткам с перекрытием (без швов), только CPU."""
    import ncnn
    import numpy as np

    models = ensure_model()
    net = ncnn.Net()
    net.opt.use_vulkan_compute = False
    net.opt.num_threads = threads or os.cpu_count() or 2
    net.load_param(str(models / 'upscayl-lite-4x.param'))
    net.load_model(str(models / 'upscayl-lite-4x.bin'))

    source = np.asarray(image.convert('RGB'), dtype=np.float32) / 255.0
    height, width, _ = source.shape
    padded = np.pad(source, ((pad, pad), (pad, pad), (0, 0)), mode='reflect')
    result = np.zeros((height * 4, width * 4, 3), dtype=np.uint8)
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            th, tw = min(tile, height - y), min(tile, width - x)
            chunk = np.ascontiguousarray(padded[y:y + th + 2 * pad, x:x + tw + 2 * pad].transpose(2, 0, 1))
            extractor = net.create_extractor()
            extractor.input('data', ncnn.Mat(chunk))
            status, out = extractor.extract('output')
            if status != 0:
                raise RuntimeError('ncnn: ошибка вывода %r' % status)
            out = np.array(out).transpose(1, 2, 0)[pad * 4:(pad + th) * 4, pad * 4:(pad + tw) * 4]
            result[y * 4:(y + th) * 4, x * 4:(x + tw) * 4] = np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(result, 'RGB')


def master(kind: str, name: str, source: Path) -> Path:
    """Перерисовка (~1K) -> мастер 4K в art_4k/."""
    image = Image.open(source).convert('RGB')
    big = upscale_x4(image)
    if kind == 'loc':
        final = ImageOps.fit(big, LOC_SIZE, method=Image.Resampling.LANCZOS)
    else:
        aspect = image.width / image.height
        if abs(aspect - 0.75) < 0.01:
            final = ImageOps.fit(big, CHR_SIZE, method=Image.Resampling.LANCZOS)
        else:  # нестандартный кадр: сохраняем пропорции, высота 3840
            final = big.resize((round(CHR_HEIGHT * aspect / 2) * 2, CHR_HEIGHT), Image.Resampling.LANCZOS)
    target = ART / FOLDERS[kind] / (name + '.jpg')
    target.parent.mkdir(parents=True, exist_ok=True)
    final.save(target, 'JPEG', **JPEG)
    print('%s -> %s %dx%d (%.2f МБ)' % (source, target.relative_to(ROOT), final.width, final.height, target.stat().st_size / 1e6))
    return target


# ---------------------------------------------------------------- отчёты

def _font(size: int):
    for candidate in (str(ROOT / 'assets' / 'fonts' / 'Oswald-Bold.ttf'), 'C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                      '/System/Library/Fonts/Supplemental/Arial Bold.ttf'):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return None


def _catalog():
    """(тип, имя файла, подпись, путь к исходнику или None) — по данным build_v12.py.

    None вместо исходника — у героев, придуманных для v12: «было» у них нет.
    """
    sys.path.insert(0, str(ROOT))
    import build_v12 as b
    names = json.loads((ROOT / 'npcs.json').read_text(encoding='utf8'))
    rows = []
    for index, file in enumerate(b.LOCS):
        rows.append(('loc', Path(file).stem, '%d. %s' % (index, b.LOC_NAMES[index]), ORIGINALS / file))
    for npc, (file, name, _role, _goal) in b.NPC.items():
        boss = ' · босс' if names[npc]['boss'] else ''
        rows.append(('chr', Path(file).stem, name + boss, ORIGINALS / file))
    for npc, file in b.EXTRA_PORTRAITS.items():
        boss = ' · босс' if names[npc]['boss'] else ''
        before = None if npc in b.NEW_BOSSES else ROOT / 'assets' / (b.LEGACY_PORTRAIT.get(npc, npc) + '.jpg')
        rows.append(('chr', Path(file).stem, names[npc]['name'] + boss, before))
    # Герой игрока: не NPC, исходник — его прежний фотопортрет из assets.
    rows.append(('chr', Path(b.HERO_ART).stem, 'Герой игрока', ROOT / 'assets' / b.HERO_SOURCE))
    return rows


def _pair(before: Path | None, after: Path | None, cell, label: str, font):
    """Плитка «было -> стало» с подписью. Без исходника слева стоит пометка «новый герой»."""
    gap, bar = 6, 30
    tile = Image.new('RGB', (cell[0] * 2 + gap, cell[1] + bar), '#0d131b')
    draw = ImageDraw.Draw(tile)
    if before is not None:
        left = ImageOps.fit(Image.open(before).convert('RGB'), cell, method=Image.Resampling.LANCZOS, centering=(.5, .3))
        tile.paste(left, (0, bar))
    else:
        draw.rectangle((0, bar, cell[0] - 1, cell[1] + bar - 1), fill='#161d27', outline='#2b3c50')
        if font:
            draw.text((cell[0] // 2, bar + cell[1] // 2 - 14), 'новый герой', fill='#e6b450', font=font, anchor='mm')
            draw.text((cell[0] // 2, bar + cell[1] // 2 + 14), 'исходника не было', fill='#8fa3b8', font=font, anchor='mm')
    if after and after.is_file():
        with Image.open(after) as im:
            im.draft('RGB', (cell[0] * 2, cell[1] * 2))
            right = ImageOps.fit(im.convert('RGB'), cell, method=Image.Resampling.LANCZOS, centering=(.5, .3))
        tile.paste(right, (cell[0] + gap, bar))
    else:
        draw.rectangle((cell[0] + gap, bar, cell[0] * 2 + gap - 1, cell[1] + bar - 1), fill='#161d27', outline='#2b3c50')
        if font:
            draw.text((cell[0] + gap + cell[0] // 2, bar + cell[1] // 2), 'в очереди', fill='#8fa3b8', font=font, anchor='mm')
    if font:
        draw.text((6, bar // 2), label, fill='#e6b450', font=font, anchor='lm')
    return tile


def _sheet(tiles, columns: int, out: Path):
    width, height = tiles[0].size
    margin = 14
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * (width + margin) + margin, rows * (height + margin) + margin), '#070b10')
    for index, tile in enumerate(tiles):
        sheet.paste(tile, (margin + (index % columns) * (width + margin), margin + (index // columns) * (height + margin)))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, 'JPEG', quality=88, optimize=True)
    print(out.relative_to(ROOT), sheet.size)


def preview():
    """Листы «было -> стало» для быстрой проверки глазами."""
    font = _font(19)
    rows = _catalog()
    locations = [_pair(src, ART / 'locations' / (stem + '.jpg'), (600, 338), label, font)
                 for kind, stem, label, src in rows if kind == 'loc']
    _sheet(locations, 2, ART / 'preview' / 'locations_before_after.jpg')
    characters = [(label, _pair(src, ART / 'characters' / (stem + '.jpg'), (300, 474), label, font))
                  for kind, stem, label, src in rows if kind == 'chr']
    bosses = [tile for label, tile in characters if 'босс' in label]
    others = [tile for label, tile in characters if 'босс' not in label]
    _sheet(bosses, 4, ART / 'preview' / 'bosses_before_after.jpg')
    if others:
        _sheet(others, 3, ART / 'preview' / 'others_before_after.jpg')
    _cast_sheet(ROOT / 'dist' / 'Tyuryaga_v12', ART / 'preview' / 'cast_in_game.jpg')


def _cast_sheet(game: Path, out: Path):
    """Все герои так, как их показывает собранная игра: портрет, имя, локация, стиль."""
    if not (game / 'ART_MANIFEST_v12.json').is_file():
        print('cast_in_game.jpg пропущен: сначала соберите игру (python build_v12.py)')
        return
    rows = [r for r in json.loads((game / 'ART_MANIFEST_v12.json').read_text(encoding='utf8')) if r['kind'] == 'character']
    rows.sort(key=lambda r: not r['boss'])
    styles = {'borderlands_4k': 'новый стиль', 'original': 'оригинал', 'legacy': 'старая картинка'}
    cell, bar, gap, columns = (250, 395), 56, 10, 6  # 12 боссов — два полных ряда, остальные герои — третий
    lines = (len(rows) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * (cell[0] + gap) + gap, lines * (cell[1] + bar + gap) + gap), '#0b1016')
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        x = gap + (index % columns) * (cell[0] + gap)
        y = gap + (index // columns) * (cell[1] + bar + gap)
        with Image.open(game / row['file']) as im:
            sheet.paste(ImageOps.fit(im.convert('RGB'), cell, method=Image.Resampling.LANCZOS), (x, y))
        title = row['name'] + (' · босс' if row['boss'] else '')
        note = '%s · %s' % (row['location'], styles.get(row['style'], row['style']))
        for text, top, colour, size in ((title, 3, '#e6b450', 19), (note, 29, '#9fb2c6' if row['style'] == 'borderlands_4k' else '#ff7a59', 16)):
            font = _font(size)
            while font and size > 9 and draw.textlength(text, font=font) > cell[0]:
                size -= 1
                font = _font(size)
            if font:
                draw.text((x, y + cell[1] + top), text, fill=colour, font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, 'JPEG', quality=88, optimize=True)
    print(out.relative_to(ROOT), sheet.size)


def audit() -> int:
    """Печатает таблицу готовности и проверяет уникальность: и файлов, и самих картинок."""
    sys.path.insert(0, str(ROOT))
    import gfx
    seen, problems, ready, total = {}, [], {}, {}
    for kind, stem, label, _src in _catalog():
        group = 'локации' if kind == 'loc' else 'боссы' if 'босс' in label else 'остальные герои'
        total[group] = total.get(group, 0) + 1
        path = ART / FOLDERS[kind] / (stem + '.jpg')
        if not path.is_file():
            print('  ожидает   %-4s %-16s %s' % (kind, stem, label))
            continue
        ready[group] = ready.get(group, 0) + 1
        with Image.open(path) as im:
            size = im.size
        digest = _sha256(path)
        if digest in seen:
            problems.append('%s дублирует %s' % (path.name, seen[digest]))
        seen[digest] = path.name
        ok = size == LOC_SIZE if kind == 'loc' else size[1] == CHR_HEIGHT
        if not ok:
            problems.append('%s: неверный размер %dx%d' % (path.name, *size))
        print('  готово    %-4s %-16s %-28s %dx%d' % (kind, stem, label, *size))
    for folder in FOLDERS.values():
        for a, b, bits in gfx.lookalikes(sorted((ART / folder).glob('*.jpg'))):
            problems.append('%s и %s — одна и та же картинка (различие %d бит из 256)' % (a.name, b.name, bits))
    print('Итог: ' + ' · '.join('%s %d/%d' % (group, ready.get(group, 0), count) for group, count in total.items()))
    for problem in problems:
        print('ПРОБЛЕМА:', problem)
    if not problems:
        print('Все готовые картинки разные: ни одинаковых файлов, ни одинаковых изображений.')
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='4K-мастеринг артов «Тюряги»')
    sub = parser.add_subparsers(dest='command', required=True)
    for kind in ('loc', 'chr'):
        p = sub.add_parser(kind)
        p.add_argument('name')
        p.add_argument('source', type=Path)
    sub.add_parser('preview')
    sub.add_parser('audit')
    args = parser.parse_args(argv)
    if args.command in ('loc', 'chr'):
        master(args.command, args.name, args.source)
        return 0
    if args.command == 'preview':
        preview()
        return 0
    return audit()


if __name__ == '__main__':
    raise SystemExit(main())
