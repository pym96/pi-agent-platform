"""Actual CPU subprocess fixtures. Docker commands below are explicit doubles, not a GPU test."""
import importlib.util,json,os,signal,subprocess,sys,tempfile,threading,time,unittest,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from watch_monitor import verify_watch,guard_watch,process_arguments
SHA='a'*40;IDENT='b'*64;PROJECT='pi-qwen13-b'
class MonitorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.bin=self.root/'bin';self.bin.mkdir();self.state=self.root/'running';self.state.write_text('owned');self.calls=self.root/'docker-calls';self.proc=None;self.guard=None;self.stop=threading.Event();self.lost=threading.Event();self.oldpath=os.environ['PATH'];self.oldenv={k:os.environ.get(k) for k in ['MONITOR_FIXTURE_ROOT','MONITOR_FIXTURE_DELAY']};os.environ['PATH']=str(self.bin)+os.pathsep+self.oldpath;os.environ['MONITOR_FIXTURE_ROOT']=str(self.root);os.environ['MONITOR_FIXTURE_DELAY']='6'
  docker='''#!'''+sys.executable+'''
import os,sys,json
from pathlib import Path
r=Path(os.environ['MONITOR_FIXTURE_ROOT']);a=sys.argv[1:];ident='''+repr(IDENT)+''';running=(r/'running').exists()
with (r/'docker-calls').open('a') as f:f.write(json.dumps(a)+'\\n')
if a[0]=='ps':print(ident)
elif a[0]=='inspect':print(json.dumps([{'Id':ident,'Config':{'Labels':{'com.docker.compose.project':'pi-qwen13-b','workorder':'13','execution-sha':''' +repr(SHA)+'''}},'State':{'Running':running}}]))
elif a[0]=='stop':(r/'running').unlink(missing_ok=True)
else:raise SystemExit(2)
'''
  (self.bin/'docker').write_text(docker);(self.bin/'docker').chmod(0o755)
  sampler=self.root/'sampler.py';sampler.write_text('''import os,time,json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project');p.add_argument('--sha');p.add_argument('--root');p.add_argument('--out');p.add_argument('--commands');a=p.parse_args();start=time.time();Path(a.commands).open('a').write(json.dumps({'event':'command_start','started_ns':time.time_ns(),'command':['CPU-fixture-sleep']})+'\\n');time.sleep(float(os.environ['MONITOR_FIXTURE_DELAY']));Path(a.commands).open('a').write(json.dumps({'event':'command_end','ended_ns':time.time_ns(),'command':['CPU-fixture-sleep']})+'\\n');Path(a.out).write_text(json.dumps({'status':'complete','known_ids':['''+repr(IDENT)+'''],'running':['''+repr(IDENT)+'''] if (Path(a.root)/'running').exists() else [],'foreign_pids':[],'gpu_snapshot':'CPU fixture, not GPU','gpu_observed_epoch':start,'stop_reason':None,'start_epoch':start,'end_epoch':time.time()}))
''')
  self.driver=self.root/'service/scripts/pi-qwen-load/watch.py';self.driver.parent.mkdir(parents=True);self.driver.write_text('''import sys,argparse
from pathlib import Path
sys.path.insert(0,'''+repr(str(HERE))+''')
from watch_monitor import run_monitor
p=argparse.ArgumentParser();p.add_argument('--project');p.add_argument('--sha');p.add_argument('--deadline',type=float);p.add_argument('--root');p.add_argument('--out');a=p.parse_args();run_monitor(a.project,a.sha,a.deadline,a.root,a.out,[sys.executable,'''+repr(str(sampler))+'''])
''')
 def start(self,seconds):
  self.receipt=self.root/'watch.jsonl';self.deadline=time.time()+seconds;self.go={'project':PROJECT,'source_sha':SHA,'deadline_epoch':self.deadline,'watch_receipt':str(self.receipt)};self.proc=subprocess.Popen([sys.executable,str(self.driver),'--project',PROJECT,'--sha',SHA,'--deadline',str(self.deadline),'--root',str(self.root),'--out',str(self.receipt)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  end=time.monotonic()+3
  while time.monotonic()<end:
   if self.receipt.exists() and 'heartbeat' in self.receipt.read_text():return
   if self.proc.poll() is not None:self.fail(self.proc.communicate()[1])
   time.sleep(.05)
  self.fail('no actual heartbeat')
 def rows(self):return [json.loads(x) for x in self.receipt.read_text().splitlines()]
 def begin_guard(self):
  self.guard=threading.Thread(target=guard_watch,args=(self.go,self.stop,self.lost,{},self.root/'loss.jsonl'));self.guard.start()
 def tearDown(self):
  self.stop.set()
  if self.guard:self.guard.join(5)
  if self.proc and self.proc.poll() is None:
   os.kill(self.proc.pid,signal.SIGCONT);self.proc.terminate()
   try:self.proc.communicate(timeout=8)
   except subprocess.TimeoutExpired:self.proc.kill();self.proc.communicate()
  if hasattr(self,'receipt') and self.receipt.exists():
   for pid in {r['sampler_pid'] for r in self.rows() if 'sampler_pid' in r}:
    try:
     if str(self.root/'sampler.py') in process_arguments(pid):os.killpg(pid,signal.SIGKILL)
    except (ProcessLookupError,subprocess.CalledProcessError):pass
  evidence=os.environ.get('MONITOR_TEST_EVIDENCE')
  if evidence:
   target=Path(evidence)/self.id().split('.')[-1];target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.root,target)
  os.environ['PATH']=self.oldpath
  for k,v in self.oldenv.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.tmp.cleanup()
 def test_slow_diagnostics_keep_live_control_and_mark_old_resource_unknown(self):
  self.start(9);self.begin_guard();time.sleep(6.5);beat=verify_watch(self.go);self.assertFalse(self.lost.is_set());self.assertTrue(self.state.exists());self.assertEqual(beat['resource_status'],'unknown');self.assertIsNone(beat['gpu_snapshot']);end=time.monotonic()+2
  while time.monotonic()<end and not any(r.get('event')=='diagnostic' for r in self.rows()):time.sleep(.05)
  self.assertTrue(any(r.get('event')=='diagnostic' for r in self.rows()));self.proc.communicate(timeout=8);self.assertFalse(self.state.exists());self.assertEqual(self.proc.returncode,0)
 def test_deadline_interrupts_blocked_diagnostic_and_cleans_exact_owned(self):
  os.environ['MONITOR_FIXTURE_DELAY']='20';self.start(2.5);self.proc.communicate(timeout=8);rows=self.rows();stop=next(x for x in rows if x.get('event')=='stop');self.assertEqual(stop['reason'],'deadline');self.assertLess(stop['utc_epoch']-self.deadline,.5);self.assertTrue(any(x.get('event')=='diagnostic_cancelled' for x in rows));self.assertFalse(self.state.exists());self.assertTrue(rows[-1]['success']);self.assertEqual(self.proc.returncode,0)
 def test_actual_watcher_death_fails_closed(self):
  self.start(20);self.begin_guard();self.proc.kill();self.proc.communicate(timeout=5);self.assertTrue(self.lost.wait(4));self.guard.join(4);self.assertFalse(self.state.exists());loss=json.loads((self.root/'loss.jsonl').read_text());self.assertTrue(loss['cleanup']['success'])
 def test_wrong_binding_live_process_fails_closed(self):
  self.start(20);os.kill(self.proc.pid,signal.SIGSTOP);rows=self.rows();rows[-1]['source_sha']='c'*40;self.receipt.write_text(''.join(json.dumps(r)+'\n' for r in rows));self.begin_guard();self.assertTrue(self.lost.wait(4));self.guard.join(4);self.assertFalse(self.state.exists());loss=json.loads((self.root/'loss.jsonl').read_text());self.assertIn('watch binding',loss['error'])
 def test_stopped_control_loop_cannot_emit_fresh_heartbeat(self):
  self.start(20);os.kill(self.proc.pid,signal.SIGSTOP);self.begin_guard();self.assertTrue(self.lost.wait(8));self.guard.join(4);self.assertFalse(self.state.exists());loss=json.loads((self.root/'loss.jsonl').read_text());self.assertIn('stale',loss['error'])
if __name__=='__main__':unittest.main()
