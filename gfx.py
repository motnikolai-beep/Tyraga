"""Загрузка крупных картинок без лишней работы.

Фоны v12 хранятся в 4K. JPEG умеет декодироваться сразу в 1/2, 1/4 или 1/8
размера (Image.draft), поэтому для окна 1600x900 или миниатюры карты игра не
распаковывает все 8 мегапикселей. Картинка всегда остаётся не меньше
запрошенного размера, так что качество после масштабирования не страдает.
"""
from PIL import Image


def open_rgb(path, size=None):
    """Открыть картинку как RGB; size=(w,h) — сколько пикселей реально нужно."""
    im = Image.open(path)
    if size:
        try:
            im.draft('RGB', (max(1, int(size[0])), max(1, int(size[1]))))
        except Exception:
            pass
    return im.convert('RGB')


# Порог «это одна и та же картинка». Замеры на артах игры: одна картинка в другом
# размере или сжатии отличается на 1–17 бит из 256, разные картинки — на 82 и больше.
SAME_PICTURE = 40


def fingerprint(path, n=16):
    """Отпечаток картинки (dHash, n*n бит): почти не меняется от размера и сжатия файла."""
    with Image.open(path) as im:
        try:
            im.draft('L', (n * 8, n * 8))
        except Exception:
            pass
        small = im.convert('L').resize((n + 1, n), Image.Resampling.LANCZOS)
    px = small.tobytes()
    bits = 0
    for y in range(n):
        row = y * (n + 1)
        for x in range(n):
            bits = (bits << 1) | (px[row + x] > px[row + x + 1])
    return bits


def distance(a, b):
    """Сколько бит различается у двух отпечатков: 0 — та же картинка, около половины — разные."""
    return bin(a ^ b).count('1')


def lookalikes(paths):
    """Пары файлов, которые выглядят как одна и та же картинка: [(a, b, расстояние), ...]."""
    marks = [(path, fingerprint(path)) for path in paths]
    found = []
    for i, (a, fa) in enumerate(marks):
        for b, fb in marks[i + 1:]:
            if distance(fa, fb) <= SAME_PICTURE:
                found.append((a, b, distance(fa, fb)))
    return found
