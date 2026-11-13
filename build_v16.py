"""Package v16 with 12 art-matched interactive environments and all prior versions' gameplay."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v15
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v15.build(root)
    dest=root/'dist'/'Tyuryaga_v16'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v16 / Окружение ожило\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v16.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v16.md').write_text((root/'CHANGELOG_v16.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v16\nЗапуск: `python -m unittest discover -s tests`. Полигоны проверены на обеих версиях фонов; окна — через заглушки Tk, не через реальный Windows GUI.\n',encoding='utf8')
    if not (dest/'hotspots16.py').is_file() or not (dest/'tests/test_v16.py').is_file():raise RuntimeError('Нет системы окружения v16')
    import hotspots16
    from PIL import Image
    for loc in range(12):
        with Image.open(dest/'assets'/f'loc_{loc}.jpg') as im:im.verify()
        if len(hotspots16.objects(loc,'master'))<2 or len(hotspots16.objects(loc,'legacy'))<2:raise RuntimeError('Пустая локация '+str(loc))
    archive=root/'dist'/'TYURYAGA_v16_FULL.zip'
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
