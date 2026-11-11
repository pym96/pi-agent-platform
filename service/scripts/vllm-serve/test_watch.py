"""Watch loop exercises real owned OS children through an exact Docker transport fixture."""
import json,os,pathlib,signal,subprocess,sys,tempfile,time,unittest,uuid
from types import SimpleNamespace as NS
from unittest.mock import patch
import watch
from owned import OwnedDocker
CID='d'*64
class WatchTests(unittest.TestCase):
 def exercise(self,kind):
  evidence=os.environ.get('G2_TEST_EVIDENCE');temp=None
  if evidence:
   root=pathlib.Path(evidence)/('watch-'+kind+'-'+uuid.uuid4().hex);root.mkdir(parents=True)
  else:temp=tempfile.TemporaryDirectory();root=pathlib.Path(temp.name)
  child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);foreign=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
  state={'exists':True,'discover':0};labels={'workorder':'24','execution-sha':'e'*40,'com.docker.compose.project':'pi-vllm24-b','pi24.nonce':'test'}
  def runner(args):
   if args[0]=='ps':
    if '--filter' in args:
     state['discover']+=1
     if kind=='unknown' and state['discover']>1:return NS(returncode=1,stdout='',stderr='inventory unavailable')
    return NS(returncode=0,stdout=CID+'\n' if state['exists'] else '',stderr='')
   if args[0]=='inspect':
    if not state['exists']:return NS(returncode=1,stdout='',stderr='not found')
    return NS(returncode=0,stdout=json.dumps([{'Id':CID,'Config':{'Labels':labels},'State':{'Running':child.poll() is None}}]),stderr='')
   if args[0]=='top':return NS(returncode=0,stdout='PID\n'+str(child.pid)+'\n',stderr='')
   if args[0]=='stop':child.terminate();child.wait(timeout=2)
   elif args[0]=='rm':state['exists']=False
   else:raise AssertionError(args)
   return NS(returncode=0,stdout=CID+'\n',stderr='')
  docker=OwnedDocker('pi-vllm24-b','e'*40,'test',runner)
  a=NS(root=str(root),project='pi-vllm24-b',sha='e'*40,nonce='test',deadline=time.time()+.15,out=str(root/'watch.jsonl'),ready=str(root/'ready'),stop_file=str(root/'stop'),gpu=kind=='foreign')
  fake_gpu=lambda *args,**kwargs:NS(returncode=0,stdout=f'{foreign.pid}, {watch.GPU}\n',stderr='')
  try:
   with patch.object(watch,'OwnedDocker',return_value=docker):
    if kind=='foreign':
     with patch.object(watch.subprocess,'run',side_effect=fake_gpu):watch.run(a)
    elif kind=='unknown':
     with self.assertRaisesRegex(RuntimeError,'cleanup unknown'):watch.run(a)
    else:watch.run(a)
   self.assertIsNotNone(child.poll());self.assertIsNone(foreign.poll())
   rows=[json.loads(x) for x in pathlib.Path(a.out).read_text().splitlines()];cleanup=rows[-1]
   self.assertTrue(cleanup['success']);self.assertEqual(cleanup['containers'],{CID:'removed'})
   if kind=='unknown':self.assertIsNotNone(cleanup['inventory_error'])
   else:self.assertIn('foreign_gpu_process' if kind=='foreign' else 'deadline',[r.get('reason') for r in rows])
  finally:
   for proc in [child,foreign]:
    if proc.poll() is None:proc.kill()
    proc.wait(timeout=2)
   if temp is not None:temp.cleanup()
 def test_deadline_stops_owned_child_and_keeps_foreign(self):self.exercise('deadline')
 def test_foreign_gpu_fixture_stops_only_owned_child(self):self.exercise('foreign')
 def test_unknown_inventory_keeps_failure_but_cleans_known_child(self):self.exercise('unknown')
if __name__=='__main__':unittest.main()
