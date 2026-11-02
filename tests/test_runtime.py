import sys,tempfile,unittest,threading,json
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_manager import Engine
import ai
class Tests(unittest.TestCase):
 def test_paths(self):
  with tempfile.TemporaryDirectory() as d:
   Path(d,'.env').write_text('SCOUT_PORT=1235\nSCOUT_MODEL_PATH=models\\4B\\x.gguf')
   e=Engine(d);self.assertEqual(e.port,1235);self.assertEqual(e.path(e.cfg['SCOUT_MODEL_PATH']),Path(d)/'models/4B/x.gguf')
   with self.assertRaises(FileNotFoundError):e.resolve_files()
 def test_external(self):
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'status':'ok'} if self.path=='/health' else {'data':[{'id':'test'}]}).encode())
  s=HTTPServer(('127.0.0.1',0),H);t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
  try:
   with tempfile.TemporaryDirectory() as d:
    Path(d,'.env').write_text('SCOUT_PORT='+str(s.server_port));e=Engine(d);e.connect();self.assertTrue(e.external);e.shutdown();self.assertTrue(Engine(d).ready())
  finally:s.shutdown();s.server_close();t.join()
 def test_karma(self):
  s=ai.fresh();r=ai.parse('{"reply":"Да","karma":{"honor":999}}')
  self.assertEqual(r['karma']['honor'],2)
  for i in range(20):ai.accept(s,'zub',str(i),r)
  self.assertEqual(s['karma']['honor'],6)
if __name__=='__main__':unittest.main()
