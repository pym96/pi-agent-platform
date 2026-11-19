import json,os,shutil,signal,subprocess,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import watch
from authority import GPU
from watch import compute_processes

class WatchTests(unittest.TestCase):
    def monitor(self,rss_bytes,failure=None):
        """Run the real monitor loop with controlled OS/Docker query transport."""
        self.addCleanup(signal.signal,signal.SIGTERM,signal.getsignal(signal.SIGTERM))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();out=root/'builder/run-stage/pilotA';out.mkdir(parents=True)
            (out/'foreground-lease').touch()
            model={'id':'pilotA','nonce':'model-A','deadline_epoch':time.time()+120}
            go={'role':'builder','source_sha':'a'*40,'nonce':'stage','models':[model]}
            args=SimpleNamespace(go='go',go_sha256='g',phase_contract='phase',phase_contract_sha256='p',model_index=0,out=str(out))
            cleanup=[]
            class Docker:
                def __init__(self,*unused):pass
                def discover(self,known):return []
                def cleanup(self,known):cleanup.append(True);return {'success':failure!='cleanup'}
            def query(argv,**kwargs):
                if argv[0]=='ps':
                    code=1 if failure=='collector' else 0
                    return subprocess.CompletedProcess(argv,code,'PID PPID %CPU RSS\n'+f'{os.getpid()} {os.getppid()} 0 {rss_bytes//1024}\n','deliberate ps failure' if code else '')
                if '--query-compute-apps=pid,gpu_uuid' in argv:
                    raw='999999, '+GPU+'\n' if failure=='foreign' else ''
                elif '--query-gpu=uuid,memory.used,utilization.gpu' in argv:raw=GPU+', 0, 0\n'
                else:raise AssertionError('unexpected tool: '+repr(argv))
                return subprocess.CompletedProcess(argv,0,raw,'')
            def tick(unused):(out/'watch-stop').touch()
            error=None
            with patch.object(watch,'ROOT',root),patch.object(watch,'validate',return_value=go),\
                 patch.object(watch,'verify_entries'),patch.object(watch,'OwnedDocker',Docker),\
                 patch.object(watch.subprocess,'run',side_effect=query),patch.object(watch.time,'sleep',side_effect=tick),\
                 patch.object(watch.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(40*2**30,0,(19 if failure=='disk' else 40)*2**30)):
                try:watch.run(args)
                except RuntimeError as exc:error=exc
            rows=[json.loads(line) for line in (out/'watch.jsonl').read_text().splitlines()]
            evidence=os.environ.get('PI28_TEST_EVIDENCE')
            if evidence:
                target=Path(evidence)/('watch-rss-'+str(rss_bytes)+'-'+str(failure));target.mkdir(parents=True,exist_ok=False)
                for file in out.iterdir():
                    if file.is_file():shutil.copyfile(file,target/file.name)
            return error,rows,cleanup

    def test_real_monitor_records_rss_without_stopping_at_or_above_old_limit(self):
        for value in [0,2**30,2**30+1024,5*2**30]:
            with self.subTest(rss_bytes=value):
                error,rows,cleanup=self.monitor(value)
                self.assertIsNone(error)
                self.assertEqual([r['host_descendant_RSS_bytes'] for r in rows if r['event']=='sample'],[value])
                self.assertFalse(any(r['event']=='watch_error' for r in rows))
                self.assertEqual(cleanup,[True])
                self.assertTrue(rows[-1]['success'])

    def test_high_rss_does_not_hide_independent_monitor_failures(self):
        for failure in ['foreign','collector','disk','cleanup']:
            with self.subTest(failure=failure):
                error,rows,cleanup=self.monitor(5*2**30,failure)
                self.assertIsInstance(error,RuntimeError)
                self.assertEqual(cleanup,[True])
                if failure=='collector':
                    self.assertTrue(any(r.get('stderr')=='deliberate ps failure' and r.get('exit')==1 for r in rows))
                    self.assertFalse(any(r['event']=='sample' for r in rows))
                else:
                    self.assertEqual([r['host_descendant_RSS_bytes'] for r in rows if r['event']=='sample'],[5*2**30])
                if failure=='cleanup':self.assertFalse(rows[-1]['success'])
                else:self.assertTrue(any(r['event']=='watch_error' for r in rows))

    def test_gpu_inventory_cannot_hide_foreign_or_unknown(self):
        self.assertEqual(compute_processes('42, '+GPU+'\n',{42}),[])
        self.assertEqual(compute_processes('43, '+GPU+'\n',{42}),[43])
        for raw in ['unknown','1, wrong-uuid','N/A, '+GPU]:
            with self.subTest(raw=raw),self.assertRaises(ValueError):compute_processes(raw,{42})

if __name__=='__main__':unittest.main()
