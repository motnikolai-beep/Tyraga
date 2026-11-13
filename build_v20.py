"""Standalone v20 package on the complete v19 art and gameplay pipeline."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v19
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v19.build(root)
    dest=root/'dist'/'Tyuryaga_v20'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v20 / Календарь и снаряжение\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v20.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v20.md').write_text((root/'CHANGELOG_v20.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v20\n`python -m unittest discover -s tests`: календарь, бой, новые NPC и Tk-заглушки. Это не ручная проверка Windows GUI, звука или модели.\n',encoding='utf8')
    for n in ('calendar20.py','gear20.py','jubilee20.py','story20.py','tests/test_v20.py','assets/cal.jpg','assets/zv.jpg'):
        if not (dest/n).is_file():raise RuntimeError('Нет файла v20: '+n)
    npc=json.loads((dest/'npcs.json').read_text(encoding='utf8'))
    if not {'cal','zv'}<=npc.keys():raise RuntimeError('Новые жители отсутствуют в сборке')
    archive=root/'dist'/'TYURYAGA_v20_FULL.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts:
                z.write(p,'Tyuryaga_Project/'+str(p.relative_to(dest)))
    with zipfile.ZipFile(archive) as z:
        broken=z.testzip()
        if broken:raise RuntimeError('Повреждён ZIP: '+broken)
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
    return dest,archive
if __name__=='__main__':build()
