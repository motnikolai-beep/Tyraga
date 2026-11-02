import sys,tempfile,unittest,threading,json
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_manager import Engine
class Tests(unittest.TestCase):
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
if __name__=='__main__':unittest.main()
