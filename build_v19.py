"""Package optional v19 jubilee preparations atop the complete v18 build."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v18
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v18.build(root)
    dest=root/'dist'/'Tyuryaga_v19'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v19 / Подготовка юбилея\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v19.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v19.md').write_text((root/'CHANGELOG_v19.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'TEST_REPORT.md').write_text('# Проверка v19\n`python -m unittest discover -s tests`: сюжетные состояния, приватность, старые сейвы и Tk-заглушки. Это не проверка реального Windows GUI, звука или модели.\n',encoding='utf8')
    for n in ('jubilee19.py','tests/test_v19.py','route18.py','note17.py'):
        if not (dest/n).is_file():raise RuntimeError('Нет файла v19: '+n)
    archive=root/'dist'/'TYURYAGA_v19_FULL.zip'
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
