import os,json,time,socket,subprocess,threading,urllib.request,urllib.error,re
from pathlib import Path
DEFAULT={'LLAMA_SERVER_PATH':r'runtime\llama.cpp\llama-server.exe','LLAMA_HOST':'127.0.0.1','SCOUT_PORT':'1235','SCOUT_MODEL_PATH':r'models\8B\Qwen3-VL-8B-Instruct-Q4_K_M.gguf','SCOUT_MMPROJ_PATH':r'models\8B\mmproj-Qwen3-VL-8B-Instruct-F16.gguf','LLAMA_GPU_LAYERS':'99','LLAMA_FLASH_ATTENTION':'on','LLAMA_START_TIMEOUT':'180','CHAT_CONTEXT_LENGTH':'16384','CHAT_MAX_OUTPUT_TOKENS':'8192','CHAT_TIMEOUT':'600','CHAT_MAX_INPUT_CHARS':'20000','CHAT_TEMPERATURE':'0.6','CHAT_HISTORY_MESSAGES':'20','CHAT_JSON_MODE':'true','CHAT_FAST_MODE':'true','CHAT_EVALUATE_KARMA':'true','CHAT_THREAT_AI':'true','NPC_INITIATIVE':'true','GOSSIP_ENABLED':'true'}
def config(base):
 c=dict(DEFAULT);p=Path(base)/'.env'
 if p.exists():
  for line in p.read_text(encoding='utf-8-sig').splitlines():
   s=line.strip()
   if s and not s.startswith('#') and '=' in s:
    k,v=s.split('=',1);c[k.strip()]=v.strip().strip('"').strip("'")
 return c
class Engine:
 def __init__(self,base):
  self.base=Path(base);self.cfg=config(base);self.host=self.cfg['LLAMA_HOST'];self.port=int(self.cfg['SCOUT_PORT']);self.url=f'http://{self.host}:{self.port}';self.process=None;self.log=None;self.model=None;self.stop=threading.Event();self.life=threading.Lock();self.serial=threading.Lock();self.external=False
 def path(self,s):
  p=Path(s.replace('\\',os.sep));return p if p.is_absolute() else self.base/p
 def request(self,path,body=None,timeout=4):
  req=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req,timeout=timeout) as r:
    data=r.read(4_000_001)
    if len(data)>4_000_000:raise RuntimeError('Ответ сервера слишком большой')
    return json.loads(data)
  except urllib.error.HTTPError as e:raise RuntimeError('HTTP %s: %s'%(e.code,e.read(1500).decode('utf8','replace'))) from e
 def ready(self):
  try:
   if self.request('/health').get('status')!='ok':return False
   data=self.request('/v1/models').get('data',[])
   if not data:return False
   self.model=data[0]['id'];return True
  except Exception:return False
 def occupied(self):
  try:
   with socket.create_connection((self.host,self.port),timeout=1):return True
  except OSError:return False
 def tail(self):
  try:return (self.base/'logs/llama-server.log').read_text(encoding='utf8',errors='replace')[-8000:]
  except OSError:return ''
 def connect(self):
  with self.life:
   if self.ready():self.external=self.process is None;return self.model
   if not self.occupied():
    if self.host not in ('127.0.0.1','localhost'):raise RuntimeError('Автозапуск разрешён только локально')
    exe=self.path(self.cfg['LLAMA_SERVER_PATH']);model=self.path(self.cfg['SCOUT_MODEL_PATH']);proj=self.path(self.cfg['SCOUT_MMPROJ_PATH'])
    if not exe.is_file():
     found=list((self.base/'runtime').rglob('llama-server.exe'))
     if len(found)==1:exe=found[0]
    missing=[str(p) for p in (exe,model,proj) if not p.is_file()]
    if missing:raise FileNotFoundError('Скопируйте runtime/models или исправьте .env:\n'+'\n'.join(missing))
    args=[str(exe),'-m',str(model),'--mmproj',str(proj),'--host',self.host,'--port',str(self.port),'-c',self.cfg['CHAT_CONTEXT_LENGTH'],'-ngl',self.cfg['LLAMA_GPU_LAYERS'],'--flash-attn',self.cfg['LLAMA_FLASH_ATTENTION']]
    (self.base/'logs').mkdir(exist_ok=True)
    if self.log:self.log.close()
    self.log=open(self.base/'logs/llama-server.log','wb');self.log.write((subprocess.list2cmdline(args)+'\n').encode());self.log.flush();self.process=subprocess.Popen(args,cwd=str(self.base),stdout=self.log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.external=False
   else:self.external=True
   deadline=time.monotonic()+int(self.cfg['LLAMA_START_TIMEOUT'])
   while not self.stop.is_set():
    if self.process and self.process.poll() is not None:raise RuntimeError('Сервер завершился:\n'+self.tail())
    if self.ready():return self.model
    if time.monotonic()>deadline:raise RuntimeError('Таймаут запуска:\n'+self.tail())
    self.stop.wait(1)
   raise RuntimeError('Запуск отменён')
 def count(self,msgs):
  try:
   p=self.request('/apply-template',{'messages':msgs,'add_generation_prompt':True,'chat_template_kwargs':{'enable_thinking':False}},20)['prompt'];return len(self.request('/tokenize',{'content':p,'add_special':False},20)['tokens']),True
  except Exception:return sum(len(m['content'].encode('utf8'))+64 for m in msgs)+128,False
 def chat(self,messages,json_mode=False,max_output=None,on_text=None,cancel=None):
  with self.serial:
   if self.stop.is_set() or (cancel and cancel.is_set()):raise RuntimeError('Запрос отменён')
   if not self.model:raise RuntimeError('ИИ не готов')
   msgs=[dict(m) for m in messages];ctx=int(self.cfg['CHAT_CONTEXT_LENGTH']);wanted=int(self.cfg['CHAT_MAX_OUTPUT_TOKENS'])
   if max_output is not None:wanted=min(wanted,int(max_output))
   if not hasattr(self,'actual_context'):
    try:self.actual_context=self.request('/props').get('default_generation_settings',{}).get('n_ctx')
    except Exception:self.actual_context=None
   if type(self.actual_context) is int and self.actual_context>0:ctx=min(ctx,self.actual_context)
   while True:
    used,exact=self.count(msgs);room=ctx-used-256
    if room>=min(wanted,ctx//2) or len(msgs)<=2:break
    del msgs[1]
    while len(msgs)>2 and msgs[1]['role']!='user':del msgs[1]
   if room<256:raise RuntimeError('Последняя реплика слишком велика для контекста')
   body={'model':self.model,'messages':msgs,'temperature':float(self.cfg['CHAT_TEMPERATURE']),'max_tokens':min(wanted,room),'stream':bool(on_text),'chat_template_kwargs':{'enable_thinking':False}}
   if json_mode and self.cfg['CHAT_JSON_MODE'].lower()=='true':body['response_format']={'type':'json_object'}
   started=time.monotonic();first=None;finish=None
   if not on_text:
    res=self.request('/v1/chat/completions',body,int(self.cfg['CHAT_TIMEOUT']));ch=res['choices'][0];raw=ch['message'].get('content') or '';finish=ch.get('finish_reason')
   else:
    req=urllib.request.Request(self.url+'/v1/chat/completions',data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Accept':'text/event-stream'});parts=[];size=0
    try:
     with urllib.request.urlopen(req,timeout=int(self.cfg['CHAT_TIMEOUT'])) as r:
      for line in r:
       if self.stop.is_set() or (cancel and cancel.is_set()):raise RuntimeError('Запрос отменён')
       size+=len(line)
       if size>4_000_000:raise RuntimeError('Слишком большой поток ответа')
       line=line.decode('utf8',errors='replace').strip()
       if not line.startswith('data:'):continue
       data=line[5:].strip()
       if data=='[DONE]':break
       if not data:continue
       item=json.loads(data)
       if item.get('error'):raise RuntimeError(str(item['error']))
       for ch in item.get('choices',[]):
        finish=ch.get('finish_reason') or finish;token=(ch.get('delta') or {}).get('content')
        if isinstance(token,str) and token:
         if first is None:first=time.monotonic()-started
         parts.append(token);visible=re.sub(r'<think>.*?</think>','', ''.join(parts),flags=re.S|re.I)
         if '<think>' in visible:visible=visible.split('<think>')[0]
         if not visible.lstrip().startswith('{'):on_text(visible)
    except urllib.error.HTTPError as e:raise RuntimeError('HTTP %s: %s'%(e.code,e.read(1500).decode('utf8','replace'))) from e
    raw=''.join(parts)
   if cancel and cancel.is_set():raise RuntimeError('Запрос отменён')
   info={'context':ctx,'prompt_tokens':used,'exact':exact,'max_tokens':body['max_tokens'],'finish':finish,'stream':bool(on_text),'elapsed':round(time.monotonic()-started,3),'first_token_seconds':first}
   (self.base/'logs').mkdir(exist_ok=True);(self.base/'logs/chat_budget.json').write_text(json.dumps(info,indent=1),encoding='utf8')
   if json_mode and finish=='length':
    try:json.loads(raw)
    except ValueError:raise RuntimeError('Служебный JSON обрезан лимитом')
   return raw
 def shutdown(self):
  self.stop.set()
  with self.life:
   if self.process and self.process.poll() is None:
    self.process.terminate()
    try:self.process.wait(timeout=5)
    except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
   if self.log:self.log.close();self.log=None
