"""Build isolated v14 ZIP with v13 art and gameplay plus offline spotlight mentor."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v13
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root)
    previous,_=build_v13.build(root)
    dest=root/'dist'/'Tyuryaga_v14'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v14 / Лис-наставник\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v14.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v14.md').write_text((root/'CHANGELOG_v14.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v14\nЗапуск: `python -m unittest discover -s tests`. Тесты используют заглушки Tk и не являются реальным запуском Windows GUI, звука или модели.\n',encoding='utf8')
    for name in ('mentor14.py','assets/mentor_v14.jpg','assets/tutorial_hand.png'):
        if not (dest/name).is_file():raise RuntimeError('Отсутствует наставник: '+name)
    with zipfile.ZipFile(root/'dist'/'TYURYAGA_v14_FULL.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts:
                z.write(p,'Tyuryaga_Project/'+str(p.relative_to(dest)))
    archive=root/'dist'/'TYURYAGA_v14_FULL.zip'
    with zipfile.ZipFile(archive) as z:
        broken=z.testzip()
        if broken:raise RuntimeError('Повреждён файл архива: '+broken)
    print(json.dumps({'archive':str(archive),'files':len(list(dest.rglob('*'))),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
    return dest,archive

if __name__=='__main__':build()
