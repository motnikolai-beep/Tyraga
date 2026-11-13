"""Build the complete v15 standalone ZIP from the tested v14 pipeline."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v14
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);old,_=build_v14.build(root)
    dest=root/'dist'/'Tyuryaga_v15'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(old,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v15 / Письмо, быт и судьбы хозяев\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v15.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v15.md').write_text((root/'CHANGELOG_v15.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v15\nЗапуск: `python -m unittest discover -s tests`. Автотесты используют заглушки Tk; реальный Windows GUI, модель и звук нужно проверить отдельно.\n',encoding='utf8')
    for n in ('boss15.py','life15.py','story15.py','tests/test_v15.py','assets/mentor_v14.jpg'):
        if not (dest/n).is_file():raise RuntimeError('Не хватает файла v15: '+n)
    from PIL import Image
    for n in ('assets/mentor_v14.jpg','assets/loc_0.jpg'):
        with Image.open(dest/n) as im:im.verify()
    with zipfile.ZipFile(root/'dist'/'TYURYAGA_v15_FULL.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts:
                z.write(p,'Tyuryaga_Project/'+str(p.relative_to(dest)))
    archive=root/'dist'/'TYURYAGA_v15_FULL.zip'
    with zipfile.ZipFile(archive) as z:
        broken=z.testzip()
        if broken:raise RuntimeError('Повреждён ZIP: '+broken)
    print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
    return dest,archive
if __name__=='__main__':build()
