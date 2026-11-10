"""Real HTTP/CLI synthetic fixtures for exact per-slot captures and missing denominators."""
import json,sys,subprocess,tempfile,threading,time,unittest,hashlib,os,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from pairs import build,file_hash
from load import PROMPT
class PairTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.bridge=self.root/'bridge.jsonl';self.bridge.write_text('');self.bodies=[];self.arrivals=[];self.reject=False;self.delay=0;self.counter=0;owner=self
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
    if self.path.startswith('/sessions/'):
     session=self.path.split('/')[2]
     if owner.reject and session.endswith('_1'):self.send_response(429);self.end_headers();return
     payload={'model':'Qwen3-8B','messages':[{'role':'system','content':'text only\n<cwd>\n/data/sessions/'+session+'/workspace\n</cwd>'},{'role':'user','content':body['prompt']}],'stream':True,'max_tokens':128};event={'event':'request','id':'model-'+session,'task':session,'session':session,'mapped':payload}
     with owner.bridge.open('a') as f:f.write(json.dumps(event)+'\n')
     self.send_response(202);self.end_headers();self.wfile.write(json.dumps({'id':session}).encode())
    else:
     owner.bodies.append(body);owner.arrivals.append(time.monotonic());self.send_response(200);self.end_headers();time.sleep(owner.delay);self.wfile.write(b'data: {"choices":[{"delta":{"content":"ok"},"finish_reason":null}]}\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":2,"completion_tokens":1,"total_tokens":3}}\n\ndata: [DONE]\n\n')
   def do_GET(self):
    if self.path in ('/health','/metrics'):
     self.send_response(200);self.end_headers();self.wfile.write(b'{"ready":true,"active_generation":0,"queued":0,"active":0}');return
    session=self.path.split('/')[2];self.send_response(200);self.end_headers()
    if self.path.endswith('/tasks'):self.wfile.write(json.dumps([{'id':session,'status':'completed'}]).encode());return
    for i,kind,data in [(1,'text',{'text':'ok'}),(2,'result',{'rawUsage':{'prompt_tokens':2,'completion_tokens':1,'total_tokens':3},'stopReason':'stop','modelCall':'model-'+session}),(3,'completed',{})]:self.wfile.write(('data: '+json.dumps({'id':i,'task':session,'kind':kind,'data':data})+'\n\n').encode())
  self.server=ThreadingHTTPServer(('127.0.0.1',0),H);self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start();self.base='http://127.0.0.1:'+str(self.server.server_port)
 def tearDown(self):
  try:self.server.shutdown();self.thread.join();self.server.server_close()
  finally:
   evidence=os.environ.get('PAIR_TEST_EVIDENCE')
   if evidence:
    out=Path(evidence)/self.id().split('.')[-1];out.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.root,out)
   self.tmp.cleanup()
 def cli(self,path,out,extra):
  command=[sys.executable,str(HERE/'load.py'),'point','--path',path,'--base',self.base,'--count','3','--prefix','p' if path=='platform' else 'd','--out',str(out),*extra];r=subprocess.run(command,capture_output=True,text=True,timeout=12);(self.root/(out.name+'.command.json')).write_text(json.dumps({'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}));return r
 def capture(self):
  r=self.cli('platform',self.root/'platform',['--mode','closed','--concurrency','1']);self.assertEqual(r.returncode,0,r.stderr);return build(self.root/'platform',self.bridge,self.root/'vector','d','cohort0')
 def replay(self,vector,extra=None):return self.cli('direct',self.root/'direct',['--mode','closed','--pairs',str(vector[0]),'--pairs-sha256',vector[1],*(extra or [])])
 def test_complete_payloads_with_distinct_cwd_are_exactly_replayed(self):
  vector=self.capture();r=self.replay(vector);self.assertEqual(r.returncode,0,r.stderr);pairs=json.loads(vector[0].read_text())['slots'];self.assertEqual(self.bodies,[x['payload'] for x in pairs]);self.assertEqual(len({x['payload_core_hash'] for x in pairs}),3);summary=json.loads((self.root/'direct/summary.json').read_text());self.assertEqual(summary['complete'],3);self.assertTrue(all(x['input_tokens_equal'] is True for x in summary['paired_usage']))
 def test_missing_payload_keeps_three_planned_and_explicit_drop(self):
  self.reject=True;vector=self.capture();r=self.replay(vector);self.assertEqual(r.returncode,0,r.stderr);summary=json.loads((self.root/'direct/summary.json').read_text());self.assertEqual((summary['planned'],summary['sent'],summary['generator_drop'],summary['complete']),(3,2,1,2));rows=[json.loads(x) for x in (self.root/'direct/ledger.jsonl').read_text().splitlines()];self.assertEqual(next(x for x in rows if x['id']=='d_1')['reason'],'missing_pair_payload');self.assertEqual(len(self.bodies),2)
 def test_mutated_message_with_resealed_vector_is_rejected_before_send(self):
  vector=self.capture();v=json.loads(vector[0].read_text());v['slots'][0]['payload']['messages'][0]['content']='deleted context';vector[0].write_text(json.dumps(v));r=self.replay((vector[0],file_hash(vector[0])));self.assertNotEqual(r.returncode,0);self.assertEqual(self.bodies,[])
 def test_wrong_pair_mapping_is_rejected_before_send(self):
  vector=self.capture();v=json.loads(vector[0].read_text());v['slots'][0]['platform_id'],v['slots'][1]['platform_id']=v['slots'][1]['platform_id'],v['slots'][0]['platform_id'];vector[0].write_text(json.dumps(v));r=self.replay((vector[0],file_hash(vector[0])));self.assertNotEqual(r.returncode,0);self.assertEqual(self.bodies,[])
 def test_changed_vector_cannot_reuse_pre_send_anchor(self):
  vector=self.capture();v=json.loads(vector[0].read_text());v['slots'][0]['payload']['max_tokens']=1;vector[0].write_text(json.dumps(v));r=self.replay(vector);self.assertNotEqual(r.returncode,0);self.assertEqual(self.bodies,[])
 def test_open_pair_arrivals_do_not_wait_for_slow_responses(self):
  vector=self.capture();self.delay=.2;r=self.cli('direct',self.root/'direct',['--mode','open','--rate','10','--pairs',str(vector[0]),'--pairs-sha256',vector[1]]);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(len(self.bodies),3);self.assertLess(self.arrivals[-1]-self.arrivals[0],.3)
 def test_actual_request_tamper_is_rejected_even_after_resealing(self):
  vector=self.capture();r=self.replay(vector);self.assertEqual(r.returncode,0,r.stderr);path=self.root/'direct/raw/d_0.request.json';v=json.loads(path.read_text());v['payload']['messages'][0]['content']='tampered actual request';path.write_text(json.dumps(v));from load import seal;anchor=seal(self.root/'direct');r=subprocess.run([sys.executable,str(HERE/'load.py'),'recompute','--out',str(self.root/'direct'),'--anchor',anchor],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('actual direct request differs',r.stderr)
 def campaign(self,stage,out,extra=None):
  command=[sys.executable,str(HERE/'campaign.py'),'--stage',stage,'--out',str(out),'--bridge',str(self.bridge),'--deadline',str(time.time()+(180 if stage=='formal' else 45)),'--model-base',self.base,'--platform-base',self.base,'--pi-base',self.base,*(extra or [])];r=subprocess.run(command,capture_output=True,text=True,timeout=50);(self.root/(out.name+'.command.json')).write_text(json.dumps({'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}));return r
 def test_pilot_campaign_captures_then_replays_and_calibrates(self):
  out=self.root/'pilot';r=self.campaign('pilot',out);self.assertEqual(r.returncode,0,r.stderr);cal=json.loads((out/'calibration.json').read_text());self.assertGreater(cal['Rb'],0);self.assertEqual((cal['platform']['complete'],cal['direct']['complete']),(3,3));pairs=json.loads((out/'pairs/pairs.json').read_text());self.assertEqual(self.bodies,[x['payload'] for x in pairs['slots']]);self.assertTrue(all(x['input_tokens_equal'] for x in cal['direct']['paired_usage']))
 def test_offline_whole_plan_freezes_twelve_paired_cohorts(self):
  pilot=self.root/'pilot';pilot.mkdir();(pilot/'calibration.json').write_text(json.dumps({'Rb':1,'pairs_sha256':'a'*64}));out=self.root/'plan';r=self.campaign('freeze',out,['--pilot',str(pilot)]);self.assertEqual(r.returncode,0,r.stderr);plan=json.loads((out/'frozen-plan.json').read_text());self.assertEqual(len(plan['order']),12);self.assertEqual([x['path'] for x in plan['order']],['platform','direct']*6);self.assertEqual([x['value'] for x in plan['order']],[1,1,2,2,4,4,.5,.5,1,1,2,2]);self.assertTrue(all(x['count']==20 and len(x['pair_ids'])==20 for x in plan['order']));self.assertEqual(file_hash(out/'frozen-plan.json'),(out/'frozen-plan.sha256').read_text().strip())
 def test_formal_http_campaign_retains_all_twelve_by_twenty_slots(self):
  pilot=self.root/'pilot';pilot.mkdir();(pilot/'calibration.json').write_text(json.dumps({'Rb':20,'pairs_sha256':'a'*64}));plan=self.root/'plan';r=self.campaign('freeze',plan,['--pilot',str(pilot)]);self.assertEqual(r.returncode,0,r.stderr);out=self.root/'formal';r=self.campaign('formal',out,['--pilot',str(pilot),'--plan',str(plan/'frozen-plan.json')]);self.assertEqual(r.returncode,0,r.stderr);results=json.loads((out/'results.json').read_text());self.assertEqual(len(results),12);self.assertTrue(all(x['planned']==20 for x in results));self.assertTrue(all('paired_usage' in x and len(x['paired_usage'])==20 for x in results if x['path']=='direct'));self.assertTrue((out/'curves.csv').exists());self.assertTrue(all(x.get('reason') is None for x in results))
if __name__=='__main__':unittest.main()
