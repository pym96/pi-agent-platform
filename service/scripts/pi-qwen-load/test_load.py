import unittest,subprocess,sys,json,tempfile,threading,time,os,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
HERE=Path(__file__).resolve().parent
class EvidenceDirectory(tempfile.TemporaryDirectory):
 def cleanup(self):
  target=os.environ.get('LOAD_TEST_EVIDENCE')
  if target and Path(self.name).exists() and not getattr(self,'evidence_saved',False):
   out=Path(target)/Path(self.name).name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.name,out);self.evidence_saved=True
  super().cleanup()
class TestLoad(unittest.TestCase):
 def test_closed_waits_for_terminal(self):
  arrivals=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    arrivals.append(time.monotonic());n=int(self.headers['Content-Length']);self.rfile.read(n)
    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
    self.wfile.write(b'data: {"choices":[{"delta":{"content":""},"finish_reason":null}]}\n\n');self.wfile.flush();time.sleep(.12)
    self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\ndata: [DONE]\n\n')
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever);thread.start()
  try:
   with EvidenceDirectory() as d:
    p=Path(d);(p/'payload.json').write_text(json.dumps({'model':'Qwen3-8B','stream':True,'messages':[{'role':'user','content':'test'}],'max_tokens':128}))
    r=subprocess.run([sys.executable,str(HERE/'load.py'),'point','--path','direct','--mode','closed','--concurrency','1','--count','3','--base','http://127.0.0.1:'+str(server.server_port),'--payload',str(p/'payload.json'),'--out',str(p/'run')],capture_output=True,text=True,timeout=10)
    self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(len(arrivals),3);self.assertTrue(all(b-a>=.1 for a,b in zip(arrivals,arrivals[1:])))
    rows=[json.loads(x) for x in (p/'run/ledger.jsonl').read_text().splitlines()];self.assertTrue(all(x['status']=='complete' and x['first_content']>x['send'] for x in rows))
  finally:server.shutdown();thread.join();server.server_close()
if __name__=='__main__':unittest.main()

class TestMore(unittest.TestCase):
 def test_open_offers_without_waiting_for_responses(self):
  arrivals=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    arrivals.append(time.monotonic());self.rfile.read(int(self.headers['Content-Length']));self.send_response(200);self.end_headers();time.sleep(.25)
    self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\ndata: [DONE]\n\n')
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever);t.start()
  try:
   with EvidenceDirectory() as d:
    p=Path(d);(p/'payload').write_text('{"model":"Qwen3-8B"}');r=subprocess.run([sys.executable,str(HERE/'load.py'),'point','--path','direct','--mode','open','--rate','20','--count','4','--base','http://127.0.0.1:'+str(server.server_port),'--payload',str(p/'payload'),'--out',str(p/'run')],capture_output=True,text=True,timeout=10)
    self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(len(arrivals),4);self.assertLess(arrivals[-1]-arrivals[0],.24)
    summary=json.loads((p/'run/summary.json').read_text());self.assertEqual(summary['complete'],4)
    (p/'run/ledger.jsonl').write_text('bad')
    r=subprocess.run([sys.executable,str(HERE/'load.py'),'recompute','--out',str(p/'run')],capture_output=True);self.assertNotEqual(r.returncode,0)
  finally:server.shutdown();t.join();server.server_close()

class TestPlatform(unittest.TestCase):
 def test_platform_ack_is_not_terminal(self):
  arrivals=[];tasks={}
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    session=self.path.split('/')[2];arrivals.append(time.monotonic());self.rfile.read(int(self.headers['Content-Length']));tasks[session]=session
    self.send_response(202);self.end_headers();self.wfile.write(json.dumps({'id':session}).encode())
   def do_GET(self):
    session=self.path.split('/')[2];self.send_response(200);self.end_headers()
    if self.path.endswith('/tasks'):self.wfile.write(json.dumps([{'id':session,'status':'completed'}]).encode());return
    time.sleep(.12)
    for ident,kind,data in [(1,'text',{'text':'hello'}),(2,'result',{'rawUsage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3},'stopReason':'stop','modelCall':'m-'+session}),(3,'completed',{})]:
     self.wfile.write(('data: '+json.dumps({'id':ident,'task':session,'kind':kind,'data':data})+'\n\n').encode());self.wfile.flush()
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever);t.start()
  try:
   with EvidenceDirectory() as d:
    r=subprocess.run([sys.executable,str(HERE/'load.py'),'point','--path','platform','--mode','closed','--concurrency','1','--count','3','--base','http://127.0.0.1:'+str(server.server_port),'--out',d+'/run'],capture_output=True,text=True,timeout=10)
    self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(len(arrivals),3);self.assertTrue(all(b-a>=.1 for a,b in zip(arrivals,arrivals[1:])))
  finally:server.shutdown();t.join();server.server_close()

class TestNegative(unittest.TestCase):
 def invoke(self,handler,extra=None,count=1):
  server=ThreadingHTTPServer(('127.0.0.1',0),handler);t=threading.Thread(target=server.serve_forever);t.start();tmp=EvidenceDirectory();root=Path(tmp.name);(root/'payload').write_text('{"model":"Qwen3-8B"}')
  try:
   command=[sys.executable,str(HERE/'load.py'),'point','--path','direct','--mode','open','--rate','100','--count',str(count),'--base','http://127.0.0.1:'+str(server.server_port),'--payload',str(root/'payload'),'--out',str(root/'run')]+(extra or [])
   result=subprocess.run(command,capture_output=True,text=True,timeout=10);return tmp,root,result
  finally:server.shutdown();t.join();server.server_close()
 def test_missing_terminal_is_unresolved(self):
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));self.send_response(200);self.end_headers();self.wfile.write(b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":null}]}\n\n')
  tmp,root,r=self.invoke(H)
  try:self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads((root/'run/summary.json').read_text())['unresolved'],1)
  finally:tmp.cleanup()
 def test_inflight_drop_and_resealed_raw_mismatch(self):
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));self.send_response(200);self.end_headers();time.sleep(.15);self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\ndata: [DONE]\n\n')
  tmp,root,r=self.invoke(H,['--max-inflight','2'],3)
  try:
   self.assertEqual(r.returncode,0,r.stderr);s=json.loads((root/'run/summary.json').read_text());self.assertEqual((s['sent'],s['generator_drop'],s['complete']),(2,1,2))
   import importlib.util
   spec=importlib.util.spec_from_file_location('lbload',HERE/'load.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   ledger=root/'run/ledger.jsonl';rows=[json.loads(x) for x in ledger.read_text().splitlines()];row=next(x for x in rows if x['status']=='complete');row['first_content']=row['send'];ledger.write_text(''.join(json.dumps(x)+'\n' for x in rows));anchor=m.seal(root/'run')
   r=subprocess.run([sys.executable,str(HERE/'load.py'),'recompute','--out',str(root/'run'),'--anchor',anchor],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('ledger differs from raw',r.stderr)
  finally:tmp.cleanup()

class TestAbsoluteDeadline(unittest.TestCase):
 def test_trickle_without_newline_stops_at_total_deadline(self):
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    self.rfile.read(int(self.headers['Content-Length']));self.send_response(200);self.end_headers()
    try:
     for _ in range(100):self.wfile.write(b':');self.wfile.flush();time.sleep(.03)
    except (BrokenPipeError,ConnectionResetError):pass
  tmp,root,r=TestNegative.invoke(self,H,['--drain','.2','--rate','1'])
  try:
   self.assertEqual(r.returncode,0,r.stderr);trace=json.loads((root/'run/trace.json').read_text());row=json.loads((root/'run/ledger.jsonl').read_text());self.assertEqual(row['status'],'timeout');self.assertLess(row['end']-trace['deadline'],.2)
  finally:tmp.cleanup()
