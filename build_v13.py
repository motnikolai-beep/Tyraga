"""Build an isolated v13 distribution from the validated v12 pipeline.

Use: python build_v13.py. Intermediate v12 output is kept under dist/ (ignored by Git).
The v13 game contains all 4K art, the 12 bosses, new gear, drawn item icons and live comic travel.
"""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import build_v12

ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root)
    old,_=build_v12.build(root)
    dest=root/'dist'/'Tyuryaga_v13'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(old,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Only the v13 copy is changed. The historical v12 build is left intact.
    (dest/'VERSION.txt').write_text('Tyuryaga v13 / Снаряжение и комикс-переходы\n',encoding='utf8')
    guide=(root/'ИГРАТЬ_v13.md').read_text(encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text(guide,encoding='utf8')
    (dest/'CHANGELOG_v13.md').write_text((root/'CHANGELOG_v13.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v13\nЗапуск: `python -m unittest discover -s tests`. Проверки использовали заглушки Tk и движок без локальной модели; реальный Windows GUI, GPU и скорость на машине игрока нужно проверить отдельно.\n',encoding='utf8')
    # v13 titles are visible in the window and main menu, not only in the ZIP filename.
    for name in ('main.py','menu.py'):
        p=dest/name;s=p.read_text(encoding='utf8')
        s=s.replace('Тюряга · Новые лица v12','Тюряга · Комикс и бой v13')
        s=s.replace('Новые лица · v12','Комикс и бой · v13')
        p.write_text(s,encoding='utf8')
    icons={'fist','shiv','armor','bandage','phone','tea','key','letter','parcel','cig','coin','gloves','boots'}
    assert {p.stem for p in (dest/'assets/items').glob('*.png')}==icons
    assert (dest/'assets/player.jpg').is_file()
    build_v12.validate(dest)
    zpath=root/'dist'/'TYURYAGA_v13_FULL.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':
                z.write(p,'Tyuryaga_Project/'+str(p.relative_to(dest)))
    with zipfile.ZipFile(zpath) as z:
        if z.testzip():raise RuntimeError('ZIP integrity check failed')
    print(json.dumps({'archive':str(zpath),'bytes':zpath.stat().st_size,'sha256':hashlib.sha256(zpath.read_bytes()).hexdigest()},indent=2))
    return dest,zpath

if __name__=='__main__':build()
