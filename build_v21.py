"""Full v21 game ZIP with responsive UI checks and audit notes."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v20
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v20.build(root)
    dest=root/'dist'/'Tyuryaga_v21'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v21 / Масштабирование и проверка интерфейса\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v21.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v21.md').write_text((root/'CHANGELOG_v21.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'UI_AUDIT_v21.md').write_text((root/'UI_AUDIT_v21.md').read_text(encoding='utf8'),encoding='utf8')
    for n in ('ui_layout.py','tests/test_layout21.py','assets/cal.jpg','assets/zv.jpg'):
        if not (dest/n).is_file():raise RuntimeError('Нет файла проверки v21: '+n)
    archive=root/'dist'/'TYURYAGA_v21_FULL.zip'
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
