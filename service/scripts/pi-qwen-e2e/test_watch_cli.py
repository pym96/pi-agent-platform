"""Required actual Docker CLI tests; no daemon startup, fake Docker, or GPU calls."""
import json,os,subprocess,sys,tempfile,time,unittest,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
IMAGE='python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1'
PROJECT='pi-e2e12-1031-b';SHA='a'*40
class WatchCleanupCliTests(unittest.TestCase):
    def setUp(self):
        if not os.environ.get('WATCH_CLI_EVIDENCE'):raise RuntimeError('explicit WATCH_CLI_EVIDENCE root required')
        evidence_root=Path(os.environ['WATCH_CLI_EVIDENCE']).resolve();evidence_root.mkdir(parents=True,exist_ok=True)
        self.scratch=tempfile.TemporaryDirectory(prefix='watch-cleanup-',dir=evidence_root);self.root=Path(self.scratch.name);self.owned=[];self.receipts=[]
        self.evidence=evidence_root/self.id().rsplit('.',1)[-1];self.evidence.mkdir(parents=True,exist_ok=False)
        self.call(['docker','info','--format','{{.ServerVersion}}'])
    def tearDown(self):
        for ident in self.owned:self.call(['docker','rm','-f',ident],check=False)
        (self.evidence/'commands.json').write_text(json.dumps(self.receipts,indent=2)+'\n');self.scratch.cleanup()
    def call(self,args,env=None,check=True):
        start=time.time_ns();r=subprocess.run(args,env=env,capture_output=True,text=True,timeout=30)
        self.receipts.append({'command':args,'started_ns':start,'ended_ns':time.time_ns(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        if check:self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        return r
    def create(self,name=None,sha=SHA):
        name=name or 'pi-e2e12-watch-probe-'+uuid.uuid4().hex[:12]
        result=self.call(['docker','run','-d','--pull','never','--name',name,'--runtime','runc','--network','none','--label','com.docker.compose.project='+PROJECT,'--label','workorder=12','--label','execution-sha='+sha,'--cpus','1','--memory','512m','--read-only','--tmpfs','/tmp:size=32m','--user','1001:1001','--cap-drop','ALL','--security-opt','no-new-privileges:true','--entrypoint','python',IMAGE,'-c','import time;time.sleep(45)'])
        ident=result.stdout.strip();self.assertEqual(len(ident),64);self.owned.append(ident);return ident
    def cleanup(self,ident,env=None,key='result'):
        out=self.evidence/(key+'.json');r=self.call([sys.executable,str(ROOT/'watch_cleanup.py'),'--project',PROJECT,'--sha',SHA,'--known-id',ident,'--out',str(out)],env=env,check=False)
        return r,json.loads(out.read_text())
    def running(self,ident):return json.loads(self.call(['docker','inspect',ident]).stdout)[0]['State']['Running']
    def test_removed_exact_id_and_reused_name_does_not_stop_new_id(self):
        name='pi-e2e12-watch-reuse-'+uuid.uuid4().hex[:12];old=self.create(name);self.call(['docker','rm','-f',old]);new=self.create(name,sha='b'*40)
        result,value=self.cleanup(old);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(value['containers'][old],'removed');self.assertTrue(self.running(new))
        self.assertTrue(any(r['command']==['docker','ps','-a','-q','--no-trunc'] and r['exit_code']==0 for r in value['receipts']))
    def test_live_owned_exact_id_is_stopped(self):
        ident=self.create();result,value=self.cleanup(ident);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(value['containers'][ident],'stopped');self.assertFalse(self.running(ident))
    def test_unreachable_engine_is_unknown_and_leaves_real_object_running(self):
        ident=self.create();env=dict(os.environ,DOCKER_HOST='unix://'+str(self.root/'missing-daemon.sock'));env.pop('DOCKER_CONTEXT',None)
        result,value=self.cleanup(ident,env);self.assertNotEqual(result.returncode,0);self.assertFalse(value['success']);self.assertEqual(value['containers'][ident],'unknown');self.assertTrue(self.running(ident))
    def test_existing_wrong_execution_is_not_stopped(self):
        ident=self.create(sha='b'*40);result,value=self.cleanup(ident);self.assertNotEqual(result.returncode,0);self.assertEqual(value['containers'][ident],'unknown');self.assertTrue(self.running(ident))
if __name__=='__main__':unittest.main()
