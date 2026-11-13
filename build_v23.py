"""Full v23 package with the complete art/gameplay chain and the new epilogue."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v22
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v22.build(root)
    dest=root/'dist'/'Tyuryaga_v23'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'VERSION.txt').write_text('Tyuryaga v23 / После слуха\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v23.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v23.md').write_text((root/'CHANGELOG_v23.md').read_text(encoding='utf8'),encoding='utf8')
    for n in ('follow23.py','story23.py','tests/test_follow23.py','thread22.py','story22.py'):
        if not (dest/n).is_file():raise RuntimeError('Нет файла v23: '+n)
    archive=root/'dist'/'TYURYAGA_v23_FULL.zip'
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
