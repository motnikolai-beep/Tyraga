# Exact installed-project collector; stdlib only. Does not alter game source.
import argparse,hashlib,json,os,re,zipfile,datetime
from pathlib import Path
import xml.etree.ElementTree as ET
TEXT={'.py','.pyi','.json','.yaml','.yml','.toml','.ini','.cfg','.md','.txt','.bat','.cmd','.ps1','.html','.css','.js','.csv','.spec','.sh','.sql','.xml','.ts','.tsx','.jsx','.vue','.c','.cpp','.h','.hpp','.rs','.go','.cs','.lua','.svg','.ipynb','.lock'}
SKIP={'.venv','venv','__pycache__','.git','.cache','node_modules','logs','output','dist','build','_TRANSFER','.pytest_cache','.mypy_cache'}
STORED={'.jpg','.jpeg','.png','.webp','.pdf','.docx','.zip','.gguf','.dll','.exe','.mp3','.wav'}
SECRET=re.compile(r'(?:^|_)(?:API_KEY|API_TOKEN|ACCESS_TOKEN|AUTH_TOKEN|SECRET|PASSWORD|PASSWD|BEARER_TOKEN|PRIVATE_KEY)$',re.I)
def hash_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def decode(data):
 for enc in ('utf-8-sig','cp1251'):
  try:return data.decode(enc)
  except UnicodeDecodeError:pass
 return None
def config_clean(rel,data):
 text=decode(data)
 if text is None:return data
 if rel.name.startswith('.env'):
  lines=[]
  for line in text.splitlines():
   if '=' in line and not line.lstrip().startswith('#'):
    key,value=line.split('=',1)
    if SECRET.search(key.strip()):line=key+'=REDACTED'
   lines.append(line)
  return ('\n'.join(lines)+'\n').encode('utf8')
 if rel.suffix.casefold()=='.json':
  try:o=json.loads(text)
  except ValueError:return data
  changed=[False]
  def walk(v):
   if isinstance(v,dict):
    out={}
    for k,x in v.items():
     if SECRET.search(k) or k.casefold() in ('api_key','apikey','password','secret','access_token','auth_token'):out[k]='REDACTED';changed[0]=True
     else:out[k]=walk(x)
    return out
   if isinstance(v,list):return [walk(x) for x in v]
   return v
  result=walk(o)
  if changed[0]:return (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 return data
def excluded_file(p):
 n=p.name.casefold()
 return n.endswith(('.pyc','.pyo','.bak','.tmp','.log','.zip','.7z','.rar')) or '.before_' in n or '.before.' in n or n in ('project_handoff.md','all_source_code.md','manifest_sha256.json') or n.startswith('start.before')
def collect_paths(root,saves=False,runtime=False):
 ignored=set(SKIP)
 if not saves:ignored.add('saves')
 if not runtime:ignored.update({'models','runtime'})
 out=[]
 for current,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=[d for d in dirs if d not in ignored and not (Path(current)/d).is_symlink()]
  for n in files:
   p=Path(current)/n
   if not p.is_symlink() and not excluded_file(p):out.append(p)
 return sorted(out,key=lambda p:str(p.relative_to(root)).casefold())
def docx_text(data):
 try:
  from io import BytesIO
  with zipfile.ZipFile(BytesIO(data)) as z:tree=ET.fromstring(z.read('word/document.xml'))
  ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
  return '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in tree.findall('.//w:p',ns))
 except Exception:return None
def build(root,include_saves=False,include_runtime=False):
 root=Path(root).resolve()
 if not (root/'main.py').is_file() or not (root/'world.py').is_file():raise RuntimeError('Положите сборщик в корень Python-игры рядом с main.py/world.py.')
 paths=collect_paths(root,include_saves,include_runtime);out=root/'_TRANSFER';out.mkdir(exist_ok=True)
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f');archive=out/('TYURYAGA_ACTUAL_PROJECT_'+stamp+'.zip');bundle=out/('PROJECT_HANDOFF_'+stamp+'.md')
 note=root/'NEW_CHAT_CONTEXT.md';summary=note.read_text(encoding='utf-8-sig') if note.exists() else '# Project handoff\n'
 header='\n\n---\n# Снимок реальной папки проекта\n\nЭто контекст для нового чата, не обучение весов модели. Исходники ниже собраны из фактических файлов. Реализацию подтверждать по коду, описание намерений не заменяет проверку.\n\n'
 header+='Создан: '+datetime.datetime.now().isoformat(timespec='seconds')+'\n\nRuntime/модели в ZIP: '+str(include_runtime)+'; сохранения: '+str(include_saves)+'.\n'
 header+='Здесь полный текст исходников/конфигов/инструкций, без base64 изображений и весов. Двоичные ассеты и исходные DOCX/PDF находятся в ZIP.\n'
 header+='Типовые секреты в .env/JSON скрыты. Перед отправкой всё равно проверьте исходники на личные данные и вшитые в код ключи.\n\n'
 manifest=[];sources=[];extracts=[]
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
  for path in paths:
   rel=path.relative_to(root);suffix=path.suffix.casefold();is_text=suffix in TEXT or path.name.startswith('.env') or path.name.casefold() in ('readme','license','dockerfile','makefile')
   if is_text:
    data=config_clean(rel,path.read_bytes());sha=hashlib.sha256(data).hexdigest();size=len(data);z.writestr('Tyuryaga_Project/'+rel.as_posix(),data);body=decode(data)
    if body is not None and 'saves' not in rel.parts and path.name!='NEW_CHAT_CONTEXT.md':
     lang={'py':'python','bat':'bat','json':'json','yaml':'yaml','yml':'yaml','md':'markdown'}.get(suffix.lstrip('.'),'text');fence='`'*(max([len(x) for x in re.findall(r'`+',body)]+[2])+1)
     sources.append('\n## FILE: '+rel.as_posix()+'\n\nSHA256: `'+sha+'`\n\n'+fence+lang+'\n'+body+('' if body.endswith('\n') else '\n')+fence+'\n')
   else:
    sha=hash_file(path);size=path.stat().st_size;z.write(path,'Tyuryaga_Project/'+rel.as_posix(),compress_type=zipfile.ZIP_STORED if suffix in STORED else zipfile.ZIP_DEFLATED)
    if suffix=='.docx' and 'docs' in rel.parts:
     extracted=docx_text(path.read_bytes())
     if extracted:extracts.append('\n## DOCUMENT TEXT: '+rel.as_posix()+'\n\n'+extracted+'\n')
   manifest.append({'path':rel.as_posix(),'bytes':size,'sha256':sha,'included_as_text':is_text and 'saves' not in rel.parts})
  listing='\n'.join('- `'+m['path']+'` — '+str(m['bytes'])+' bytes' for m in manifest)
  content=summary+header+'# Состав проекта\n\n'+listing+'\n\n# Полные текстовые исходники\n'+''.join(sources)
  if extracts:content+='\n# Документация из DOCX\n'+''.join(extracts)
  content+='\n# Правило продолжения\n\nПроверьте ZIP и код как актуальную реализацию. Не восстанавливайте отсутствующие функции по обещаниям из переписки. Начните с main.py, world.py, runtime_manager.py, ai.py и tests.\n'
  bundle.write_text(content,encoding='utf8');z.writestr('Tyuryaga_Project/PROJECT_HANDOFF.md',content.encode('utf8'))
  z.writestr('Tyuryaga_Project/TRANSFER_MANIFEST.json',json.dumps({'generated':stamp,'files':manifest,'source_files':len(sources),'include_saves':include_saves,'include_runtime_models':include_runtime},ensure_ascii=False,indent=1).encode('utf8'))
  starter='Прочитай PROJECT_HANDOFF.md и ZIP как актуальный источник реализации. Сначала перечисли архитектуру и реальное состояние, отличая сделанное от планов. Сохраняй UI с пузырями над NPC, быстрый SSE-режим и локальную 8B. Не возвращай длинные стилевые промпты и несовместимые патчи. Перед правками проверь код и тесты. Не утверждай, что запускал Windows/GPU, если не запускал. Модели/runtime могут быть исключены из ZIP. Следующую задачу напишу после ознакомления.\n'
  z.writestr('Tyuryaga_Project/START_NEW_CHAT.txt',starter.encode('utf8'))
 with zipfile.ZipFile(archive) as z:
  bad=z.testzip()
  if bad:raise RuntimeError('Повреждён архив: '+bad)
 print('ГОТОВО:\nZIP:',archive,'\nФайл для нового чата:',bundle,'\nФайлов:',len(manifest),'| полных текстовых исходников:',len(sources),'| размер ZIP:',archive.stat().st_size)
 print('Исходная игра не изменялась. Папка _TRANSFER исключена из последующих сборок.')
 return archive,bundle,manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parent));p.add_argument('--include-saves',action='store_true');p.add_argument('--include-runtime-models',action='store_true');a=p.parse_args()
 try:build(a.root,a.include_saves,a.include_runtime_models)
 except Exception as e:print('ОШИБКА:',e);raise SystemExit(1)
