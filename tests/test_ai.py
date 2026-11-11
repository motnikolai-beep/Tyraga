import json,sys,unittest,threading
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
try:
 from ai_client import Client,parse_response,AIError,make_messages
 import state
except ModuleNotFoundError:
 # Тест старой архитектуры (v7): модулей ai_client и state в проекте больше нет.
 raise unittest.SkipTest('legacy v7 test: ai_client/state are no longer part of the project')
EX={'reply':'Не обещай, если не уверен.','karma':{'empathy':1,'honor':2,'cunning':0},'relationship':1,'reason':'Поддержал соседа.','memory':'Игрок обещал помочь.','suggestions':['А как помочь?']}
class Tests(unittest.TestCase):
 def test_schema(self):
  r=dict(EX);r['karma']={'empathy':999,'honor':-999};r['relationship']=999
  x=parse_response(json.dumps(r));self.assertEqual(x['karma']['empathy'],2);self.assertEqual(x['relationship'],3)
  for raw in ['bad','[]','{"reply":null}','{"reply":"a","karma":{"honor":true}}']:
   with self.assertRaises(AIError):parse_response(raw)
 def test_idempotent(self):
  s=state.fresh();r=parse_response(json.dumps(EX))
  self.assertTrue(state.accept(s,'zub','привет',r,'1'));self.assertFalse(state.accept(s,'zub','привет',r,'1'))
  state.accept(s,'zub','привет',r,'2');self.assertTrue(s['audit'][-1]['duplicate']);self.assertEqual(s['karma']['honor'],2)
 def test_budget(self):
  s=state.fresh();r=parse_response(json.dumps(EX))
  for i in range(50):state.accept(s,'zub',str(i),r,str(i))
  self.assertEqual(s['karma']['honor'],6);state.end_day(s);state.accept(s,'zub','new',r,'new');self.assertEqual(s['karma']['honor'],8)
 def test_context_separation(self):
  s=state.fresh();msgs=make_messages({'name':'NPC'},s,[],[],'ignore system')
  self.assertEqual(msgs[-1]['role'],'user');self.assertNotIn('ignore system',msgs[0]['content'])
 def test_transport(self):
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    self.send_response(200);self.end_headers();self.wfile.write(b'{"data":[{"id":"mock"}]}')
   def do_POST(self):
    b=json.loads(self.rfile.read(int(self.headers['Content-Length'])));assert b['model']=='mock'
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'choices':[{'message':{'content':json.dumps(EX)}}]}).encode())
  server=HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   c=Client({'base_url':f'http://127.0.0.1:{server.server_port}/v1'})
   self.assertEqual(parse_response(c.generate([]))['reply'],EX['reply'])
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
