"""Боссовая заставка в духе Borderlands: стоп-кадр, крупное имя и колкая подпись.

Картинка целиком собирается в Pillow (без Tk), поэтому её можно проверить вне игры:
    python bosscard.py          # сохранит заставки всех боссов в boss_cards/
Окно боя показывает её, пока идёт вступление (fightui.FightWindow).
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

BASE = Path(__file__).resolve().parent
FONT = 'assets/fonts/Oswald-Bold.ttf'
FALLBACK_FONTS = ('C:/Windows/Fonts/impact.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                  '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
YELLOW = (245, 197, 24)
INK = (7, 9, 12)
PAPER = (243, 239, 230)
SIZE = (960, 470)
INTRO_SECONDS = 2.2  # сколько держится заставка перед боем с боссом


def _font(base, size):
    for candidate in (Path(base) / FONT,) + tuple(Path(p) for p in FALLBACK_FONTS):
        try:
            return ImageFont.truetype(str(candidate), size)
        except Exception:
            continue
    return ImageFont.load_default()


def tagline(npc):
    """Подпись под именем: поле tagline или первая фраза роли."""
    line = (npc.get('tagline') or '').strip()
    if line:
        return line
    role = (npc.get('role') or '').strip()
    return role.split('. ')[0].rstrip('.') + '.' if role else ''


def _width(font, text):
    box = font.getbbox(text)
    return box[2] - box[0]


def _name_lines(name):
    """Имя целиком и варианты переноса по пробелу или дефису."""
    name = name.upper()
    options = [[name]]
    for index, char in enumerate(name):
        if char in ' -' and 0 < index < len(name) - 1:
            options.append([name[:index + 1].strip(), name[index + 1:].strip()])
    return options


def _fit_name(base, name, max_width, max_height):
    """Самый крупный кегль, при котором имя помещается (в одну или две строки)."""
    best = None
    for lines in _name_lines(name):
        size = 150
        while size > 26:
            font = _font(base, size)
            if max(_width(font, line) for line in lines) <= max_width and len(lines) * size * 1.08 <= max_height:
                break
            size -= 4
        if best is None or size > best[0]:
            best = (size, lines)
    return best


def _wrap(font, text, max_width, max_lines=3):
    lines, current = [], ''
    for word in text.split():
        trial = (current + ' ' + word).strip()
        if current and _width(font, trial) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines[:max_lines]


def _backdrop(size, backdrop):
    width, height = size
    if backdrop is None:
        card = Image.new('RGB', size, (11, 18, 26))
    else:
        card = ImageOps.fit(backdrop.convert('RGB'), size, method=Image.Resampling.BILINEAR)
        card = ImageEnhance.Color(card).enhance(.55)
        card = ImageEnhance.Brightness(card).enhance(.34).filter(ImageFilter.GaussianBlur(2))
    return card


def _text_block(base, npc, place, width, height, indent=0):
    """Прозрачный слой с плашкой «БОСС», именем, мазком и подписью.

    indent — сдвиг верхней плашки вправо, чтобы она не задевала наклонный край портрета.
    """
    scale = height / 470.0
    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    pad = int(14 * scale)
    y = pad
    # плашка
    tag_font = _font(base, int(30 * scale))
    tag = 'БОСС'
    tag_w = _width(tag_font, tag) + int(22 * scale)
    tag_h = int(42 * scale)
    left = pad + indent
    draw.rectangle((left, y, left + tag_w, y + tag_h), fill=YELLOW + (255,))
    draw.text((left + tag_w // 2, y + tag_h // 2), tag, font=tag_font, fill=INK + (255,), anchor='mm')
    if place:
        draw.text((left + tag_w + int(14 * scale), y + tag_h // 2), place.upper(), font=tag_font, fill=YELLOW + (255,),
                  anchor='lm', stroke_width=max(2, int(3 * scale)), stroke_fill=INK + (255,))
    y += tag_h + int(10 * scale)
    # имя
    line_text = tagline(npc)
    sub_font = _font(base, int(31 * scale))
    sub_lines = _wrap(sub_font, line_text, width - 2 * pad)
    sub_height = len(sub_lines) * int(38 * scale)
    size, lines = _fit_name(base, npc['name'], width - 2 * pad - int(10 * scale), height - y - sub_height - int(46 * scale))
    font = _font(base, size)
    stroke = max(4, size // 13)
    shift = max(3, size // 16)
    for line in lines:
        draw.text((pad + shift, y + shift), line, font=font, fill=YELLOW + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
        draw.text((pad, y), line, font=font, fill=PAPER + (255,), stroke_width=stroke, stroke_fill=INK + (255,))
        y += int(size * 1.08)
    # мазок под именем
    y += int(12 * scale)
    stroke_w = min(width - 2 * pad, max(_width(font, line) for line in lines) + int(24 * scale))
    thick = int(14 * scale)
    draw.polygon([(pad - 4, y + 3), (pad + stroke_w * .32, y), (pad + stroke_w * .7, y + 2), (pad + stroke_w, y - 2),
                  (pad + stroke_w - 9, y + thick - 3), (pad + stroke_w * .55, y + thick), (pad + stroke_w * .2, y + thick - 2),
                  (pad + 2, y + thick + 2)], fill=YELLOW + (255,), outline=INK + (255,))
    y += thick + int(12 * scale)
    # подпись
    for line in sub_lines:
        draw.text((pad, y), line, font=sub_font, fill=PAPER + (255,), stroke_width=max(2, int(3 * scale)), stroke_fill=INK + (255,))
        y += int(38 * scale)
    return layer


def render(base, npc, place='', size=SIZE, backdrop=None):
    """Собрать заставку босса. base — папка игры, npc — запись из npcs.json."""
    width, height = size
    card = _backdrop(size, backdrop)
    top, bottom = int(width * .47), int(width * .39)  # наклонный правый край портрета
    # портрет (верх кадра: лицо и плечи), маска со сглаженным наклонным краем
    with Image.open(Path(base) / 'assets' / (npc['portrait'] + '.jpg')) as source:
        face = ImageOps.fit(source.convert('RGB'), (top, height), method=Image.Resampling.LANCZOS, centering=(.5, .15))
    face = ImageEnhance.Contrast(face).enhance(1.06)
    mask = Image.new('L', (top * 2, height * 2), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (top * 2, 0), (bottom * 2, height * 2), (0, height * 2)], fill=255)
    mask = mask.resize((top, height), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(card)
    edge = max(6, width // 110)
    draw.polygon([(top + edge, 0), (top + edge * 3, 0), (bottom + edge * 3, height), (bottom + edge, height)], fill=YELLOW)
    card.paste(face, (0, 0), mask)
    draw.line([(top, -4), (bottom, height + 4)], fill=INK, width=edge + 4)
    # текст справа, слегка наклонён
    block_w = width - bottom - int(width * .085)
    block = _text_block(base, npc, place, block_w, int(height * .86), indent=int(width * .028))
    block = block.rotate(3.5, resample=Image.Resampling.BICUBIC, expand=True)
    x = width - block.width - int(width * .006)
    y = (height - block.height) // 2 + int(height * .02)
    card.paste(block, (x, y), block)
    # киношные полосы стоп-кадра
    bar = max(10, height // 30)
    draw.rectangle((0, 0, width, bar), fill=INK)
    draw.rectangle((0, height - bar, width, height), fill=INK)
    return card


def main():
    """Сохранить заставки всех боссов в boss_cards/ (для проверки глазами)."""
    npcs = json.loads((BASE / 'npcs.json').read_text(encoding='utf8'))
    try:
        from world import NAMES
    except Exception:
        NAMES = [''] * 12
    out = BASE / 'boss_cards'
    out.mkdir(exist_ok=True)
    for key, npc in npcs.items():
        if not npc.get('boss'):
            continue
        location = BASE / 'assets' / ('loc_%d.jpg' % npc['home'])
        backdrop = Image.open(location) if location.is_file() else None
        render(BASE, npc, NAMES[npc['home']], SIZE, backdrop).save(out / (key + '.jpg'), quality=92)
        print(out / (key + '.jpg'))


if __name__ == '__main__':
    main()
