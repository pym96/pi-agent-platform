"""Real process contracts for required-suite and sealed measurement entry points."""
import csv,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SEALED=ROOT/'docs/evidence/nginx-entry-20261025/raw/run-08'
ANCHOR='35d43915ecfab8e4224ff17a3d692481610a11680327bb899167fbc555c3210d'

def record_process(case,command,result,out):
    if os.environ.get('NG_EVIDENCE'):
        root=Path(os.environ['NG_EVIDENCE']);root.mkdir(parents=True,exist_ok=True)
        receipt=json.loads(out.read_text()) if out.exists() else None
        with (root/'required-cli-processes.jsonl').open('a') as f:f.write(json.dumps({'case':case,'command':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'receipt':receipt})+'\n')

class RequiredSuiteCLI(unittest.TestCase):
    def invoke(self,code):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'test_case.py').write_text(code);out=p/'receipt.json'
            command=[sys.executable,str(HERE/'strict_suite.py'),'--start-dir',str(p),'--pattern','test_case.py','--out',str(out)]
            r=subprocess.run(command,capture_output=True,text=True,timeout=10);record_process(self.id(),command,r,out)
            return r,json.loads(out.read_text()) if out.exists() else None
    def test_real_success_process(self):
        r,s=self.invoke('import unittest\nclass T(unittest.TestCase):\n def test_one(self):self.assertTrue(True)\n')
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(s['tests'],1);self.assertEqual(s['skipped'],0)
    def test_real_skipped_test_process_fails_required_entry(self):
        r,s=self.invoke('import unittest\nclass T(unittest.TestCase):\n @unittest.skip("seeded required skip")\n def test_one(self):pass\n')
        self.assertEqual(r.returncode,1,r.stderr);self.assertIn('skipped=1',r.stderr);self.assertEqual(s['skipped'],1)
    def test_real_empty_process_fails_required_entry(self):
        r,s=self.invoke('import unittest\n')
        self.assertEqual(r.returncode,1,r.stderr);self.assertEqual(s['tests'],0)

class SealedMeasurementCLI(unittest.TestCase):
    def invoke(self,root,out,anchor=ANCHOR):
        args=[sys.executable,str(HERE/'recompute.py'),'--root',str(root),'--out',str(out)]
        if anchor is not None:args+=['--expected-manifest-sha256',anchor]
        result=subprocess.run(args,capture_output=True,text=True,timeout=15);record_process(self.id(),args,result,Path(out));return result
    def test_original_natural_equal_rows_are_preserved(self):
        with (SEALED/'point-01/raw.csv').open() as f:rows=list(csv.reader(f))[1:]
        self.assertGreater(len(rows),len(set(map(tuple,rows))),'fixture must exercise legitimate rounded equal rows')
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out.json';r=self.invoke(SEALED,out)
            self.assertEqual(r.returncode,0,r.stderr);d=json.loads(out.read_text());self.assertTrue(d['integrity_verified']);self.assertEqual(sum(x['observed'] for x in d['runs']),3468)
    def test_missing_or_wrong_external_anchor_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            for anchor in [None,'0'*64]:
                out=Path(td)/'out.json';r=self.invoke(SEALED,out,anchor)
                self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists())
    def test_same_count_replacement_fails_before_statistics(self):
        import shutil
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);shutil.copytree(SEALED,p/'sealed');f=p/'sealed/point-01/raw.csv';lines=f.read_text().splitlines();lines[1]=lines[2];f.write_text('\n'.join(lines)+'\n')
            out=p/'out.json';r=self.invoke(p/'sealed',out)
            self.assertNotEqual(r.returncode,0);self.assertFalse(out.exists());self.assertEqual(json.loads(r.stderr)['phase'],'integrity')
    def test_changed_manifest_cannot_replace_external_anchor(self):
        import shutil
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);shutil.copytree(SEALED,p/'sealed');m=p/'sealed/manifest.json';m.write_text(m.read_text()+'\n');r=self.invoke(p/'sealed',p/'out.json')
            self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stderr)['phase'],'integrity')

    def test_appended_or_missing_receipt_is_not_excused_by_rounding(self):
        import shutil
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for delta in ['append','delete']:
                target=p/delta;shutil.copytree(SEALED,target);f=target/'point-01/raw.csv';lines=f.read_text().splitlines()
                lines=lines+[lines[-1]] if delta=='append' else lines[:-1]
                f.write_text('\n'.join(lines)+'\n');r=self.invoke(target,p/(delta+'.json'))
                self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads(r.stderr)['phase'],'integrity')

class LiveProducerSemantics(unittest.TestCase):
    def test_live_summary_is_explicitly_unverified_and_cannot_rewrite_sealed_tree(self):
        import shutil
        from measurement import summarize_live_unsealed
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'input';shutil.copytree(SEALED,p)
            with self.assertRaises(ValueError):summarize_live_unsealed(p)
            (p/'manifest.json').unlink();summarize_live_unsealed(p)
            d=json.loads((p/'measurement-summary.json').read_text());self.assertFalse(d['integrity_verified']);self.assertEqual(d['integrity_stage'],'live_unsealed_not_authoritative')
