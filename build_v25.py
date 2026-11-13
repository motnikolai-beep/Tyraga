"""Complete v25 archive, retaining every asset and earlier release's game files."""
import hashlib,json,shutil,zipfile
from pathlib import Path
import build_v24
ROOT=Path(__file__).resolve().parent

def build(root=ROOT):
    root=Path(root);previous,_=build_v24.build(root)
    dest=root/'dist'/'Tyuryaga_v25'
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(previous,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('main.py','menu.py','radial25.py','tests/test_radial25.py'):
        dst=dest/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/name,dst)
    (dest/'VERSION.txt').write_text('Tyuryaga v25 / Колесо диалогов\n',encoding='utf8')
    (dest/'ПРОЧИТАЙТЕ.txt').write_text((root/'ИГРАТЬ_v25.md').read_text(encoding='utf8'),encoding='utf8')
    (dest/'CHANGELOG_v25.md').write_text((root/'CHANGELOG_v25.md').read_text(encoding='utf8'),encoding='utf8')
    archive=root/'dist'/'TYURYAGA_v25_FULL.zip'
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
