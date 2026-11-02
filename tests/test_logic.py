import sys,json,random,tempfile,threading,unittest
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from world import World,Duel,save
from runtime_manager import Engine
import ai
BASE=Path(__file__).resolve().parents[1];NPCS=json.loads((BASE/'npcs.json').read_text(encoding='utf8'))
class Tests(unittest.TestCase):
 def test_fixed_locations(self):
  w=World(NPCS)
  for loc in range(12):
   w.go(loc);w.sleep();self.assertTrue(w.witnesses())
   for k,n in NPCS.items():self.assertEqual(w.s['npc_state'][k]['loc'],n['home'])
   self.assertEqual('zub' in w.witnesses(),loc==0)
 def test_private_and_overhearing(self):
  w=World(NPCS);w.conversation_event('zub','secret','reply',True);w.s['turn']+=1;w.relay();self.assertFalse(w.s['gossip'])
  w.conversation_event('zub','привет','ответ');self.assertTrue(w.heard('kol'));self.assertFalse(w.heard('gen'))
 def test_gossip_chain(self):
  w=World(NPCS,seed=4);w.conversation_event('zub','Гвоздев читает стихи','ага')
  for _ in range(15):w.s['turn']+=1;w.relay()
  self.assertTrue(any(g['hops']>=1 for g in w.s['gossip']));self.assertTrue(all(not g['verified'] and g['hops']<=3 for g in w.s['gossip']))
  ids=[(g['root'],g['to']) for g in w.s['gossip']];self.assertEqual(len(ids),len(set(ids)))
 def test_denial(self):
  w=World(NPCS);w.conversation_event('zub','x','y');g=w.heard('kol')[0];w.deny('kol',g['id']);self.assertTrue(g['disputed'])
 def test_attack_requires_fact(self):
  w=World(NPCS);w.s['relations']['kol']=-100;w.conversation_event('zub','я украл','x');g=w.heard('kol')[0];self.assertEqual(w.initiative('kol',{'action':'attack','reply':'x','evidence':[g['id']]})['action'],'warn')
  w.s['relations']['zub']=-30;e=w.event('theft','caught',['zub']);self.assertEqual(w.initiative('zub',{'action':'attack','reply':'x','evidence':[e['id']]})['action'],'attack');w.go(3);self.assertIsNone(w.initiative('zub',{'action':'talk','reply':'x'}))
 def test_offer_transaction(self):
  w=World(NPCS);o=w.initiative('zub',{'action':'offer_task','reply':'x','task':'help'});w.s['cig']=0
  with self.assertRaises(ValueError):w.resolve(o['id'],True)
  self.assertEqual(o['status'],'pending');w.s['cig']=2;w.resolve(o['id'],True);ap=w.s['ap'];w.resolve(o['id'],True);self.assertEqual(ap,w.s['ap'])
 def test_debt(self):
  w=World(NPCS);w.borrow('zub');self.assertEqual(w.s['rub'],30)
  with self.assertRaises(ValueError):w.borrow('zub')
  w.repay('zub');self.assertEqual(w.s['rub'],20)
 def test_rep(self):
  w=World(NPCS);w.event('help','help',['zub']);w.event('help','again',['zub']);w.reputation('zub');self.assertEqual(w.s['street_rep']['earned'],4);w.reputation('zub');self.assertEqual(w.s['street_rep']['earned'],4)
  w.s['street_rep']['earned']=100;w.s['relations']['zub']=-80;self.assertLessEqual(w.reputation('zub')['score'],-20)
 def test_money(self):
  w=World(NPCS);o={'economy':{'kind':'provocation','success':True,'confidence':95}};t='Зубило расскажи какие новости сегодня ходят по нашему бараку'
  self.assertEqual(w.award_dialogue('zub',t,o),4);self.assertEqual(w.award_dialogue('zub',t+'!!!',o),0);self.assertEqual(w.award_dialogue('gvo',t,o),0)
  for i in range(30):w.award_dialogue('zub',f'Совсем новая история номер {i} содержит другие подробности',o)
  self.assertLessEqual(w.s['dialogue_money']['earned'],6);w.sleep();self.assertEqual(w.s['dialogue_money']['earned'],0)
 def test_karma(self):
  w=World(NPCS);o=ai.assessment({'karma':{'honor':99}},set());o['reply']='Привет'
  for i in range(20):ai.accept(w,'zub',str(i),o,True)
  self.assertEqual(w.s['karma']['honor'],6);self.assertFalse(w.s['gossip'])
 def test_threats(self):
  for t in ['щас порежу тебя','Сейчас тебя ударю!','я щас тебя пырну.']:self.assertTrue(ai.exact_threat(t),t)
  for t in ['я не порежу тебя','он сказал: «щас порежу тебя»','щас порежу хлеб','Что значит щас порежу тебя?']:self.assertFalse(ai.exact_threat(t),t)
  o={'speaker':'player','target':'npc','immediate':True,'confidence':95,'evidence':'сейчас дам тебе в морду'};self.assertTrue(ai.threat_check(o,'сейчас дам тебе в морду','Ну давай'));self.assertIsNone(ai.threat_check(o,'привет','Здорово'))
 def test_fast_and_full(self):
  class E:
   def __init__(self,fast):self.cfg={'CHAT_HISTORY_MESSAGES':'20','CHAT_FAST_MODE':'true' if fast else 'false','CHAT_EVALUATE_KARMA':'true','CHAT_THREAT_AI':'true'};self.calls=[]
   def chat(self,msgs,**kw):
    self.calls.append((msgs,kw))
    if kw.get('json_mode'):raise ValueError('not JSON')
    if kw.get('on_text'):kw['on_text']('Обычный ответ.')
    return 'Обычный ответ.'
  for fast in [True,False]:
   w=World(NPCS);e=E(fast);out=ai.generate_chat(e,w,'zub','щас порежу тебя',lambda t:None,threading.Event());self.assertEqual(out['reply'],'Обычный ответ.');self.assertTrue(out['_combat_intent']);self.assertEqual(out['karma']['honor'],0);self.assertEqual(len(e.calls),1 if fast else 2);self.assertNotIn('max_output',e.calls[0][1])
 def test_parse(self):
  for raw in ['', 'text','[]']:
   with self.assertRaises(ValueError):ai.obj(raw)
  self.assertEqual(ai.plain('<think>hidden</think>Текст'),'Текст')
 def test_duels(self):
  for seed in range(100):
   w=World(NPCS);b=Duel(w,'zub',seed%2==0,seed);r=random.Random(seed)
   for _ in range(40):b.strike(r.randrange(3),r.randrange(3),r.choice(['attack','guard','aim']))
   self.assertTrue(b.done);self.assertGreaterEqual(w.s['stamina'],0);b.finish();rub=w.s['rub'];b.finish();self.assertEqual(rub,w.s['rub'])
 def test_sleep(self):
  w=World(NPCS);w.s['stamina']=0;w.s['npc_health']['zub']=0;w.sleep();self.assertEqual(w.s['stamina'],100);self.assertFalse(w.s['npc_health'])
 def test_save_and_context(self):
  w=World(NPCS);w.event('theft','SECRET',['zub']);self.assertNotIn('SECRET',json.dumps(w.context('gen')))
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'s.json';save(w.s,p);self.assertEqual(World(NPCS,json.loads(p.read_text(encoding='utf8'))).s,w.s)
 def test_http_stream_and_external_server(self):
  bodies=[]
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    data={'status':'ok'} if self.path=='/health' else {'data':[{'id':'mock8b'}]} if self.path=='/v1/models' else {'default_generation_settings':{'n_ctx':8192}};self.send_response(200);self.end_headers();self.wfile.write(json.dumps(data).encode())
   def do_POST(self):
    data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    if self.path=='/apply-template':res={'prompt':'x'}
    elif self.path=='/tokenize':res={'tokens':[1,2,3]}
    else:
     bodies.append(data);assert data['max_tokens']<=8192-259
     if data.get('stream'):
      self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
      for t in ['При','вет']:
       self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':t},'finish_reason':None}]},ensure_ascii=False)+'\n\n').encode());self.wfile.flush()
      self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n');return
     res={'choices':[{'message':{'content':'{"reply":"OK"}'},'finish_reason':'stop'}]}
    self.send_response(200);self.end_headers();self.wfile.write(json.dumps(res).encode())
  server=HTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with tempfile.TemporaryDirectory() as td:
    Path(td,'.env').write_text('SCOUT_PORT='+str(server.server_port));e=Engine(td);e.connect();self.assertTrue(e.external);m=[{'role':'system','content':'s'},{'role':'user','content':'u'}];updates=[]
    self.assertEqual(e.chat(m,on_text=updates.append),'Привет');self.assertEqual(updates,['При','Привет']);self.assertEqual(ai.obj(e.chat(m,json_mode=True,max_output=512))['reply'],'OK');cancel=threading.Event();cancel.set()
    with self.assertRaises(RuntimeError):e.chat(m,cancel=cancel)
    self.assertEqual(len(bodies),2);e.shutdown();self.assertTrue(Engine(td).ready())
  finally:server.shutdown();server.server_close();thread.join()
 def test_random_actions(self):
  for seed in range(15):
   w=World(NPCS,seed=seed);r=random.Random(seed)
   for _ in range(200):
    try:
     c=r.randrange(6)
     if c==0:w.go(r.randrange(12))
     elif c==1:w.work()
     elif c==2:w.eat()
     elif c==3:w.sleep()
     elif c==4:w.decision(r.choice(w.witnesses()),r.choice(['help','theft','betrayal']))
     else:w.conversation_event(r.choice(w.witnesses()),'привет','ответ',r.random()<.2)
     w.relay();w.reputation('zub')
    except ValueError:pass
   self.assertGreaterEqual(w.s['ap'],0);self.assertGreaterEqual(w.s['cig'],0)
if __name__=='__main__':unittest.main()
