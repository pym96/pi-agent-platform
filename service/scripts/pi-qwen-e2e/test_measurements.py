"""Independent-style mutation probes of the public measurement entry."""
import json,shutil,tempfile,unittest
from pathlib import Path
from analyze import analyze
SOURCE=Path(__file__).resolve().parents[3]/'docs/evidence/pi-qwen-e2e-20261023/cpu/cpu-ready'
class MeasurementEvidenceTests(unittest.TestCase):
    def probe(self,mutation):
        with tempfile.TemporaryDirectory(prefix='pi-e2e12-measure-') as scratch:
            root=Path(scratch)
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','fixture.jsonl']:
                shutil.copyfile(SOURCE/name,root/name)
            analyze(root)
            rows=[json.loads(x) for x in (root/'bridge.jsonl').read_text().splitlines()]
            row=next(r for r in rows if r['event']=='settled');mutation(row)
            (root/'bridge.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            with self.assertRaises((AssertionError,ValueError,KeyError,TypeError)):analyze(root)
    def test_cpu_fixture_cannot_be_relabelled_gpu(self):
        with tempfile.TemporaryDirectory(prefix='pi-e2e12-kind-') as scratch:
            root=Path(scratch)
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','fixture.jsonl']:
                shutil.copyfile(SOURCE/name,root/name)
            analyze(root)
            run=json.loads((root/'run.json').read_text());run['kind']='qwen-functional';(root/'run.json').write_text(json.dumps(run))
            with self.assertRaises(AssertionError):analyze(root)
    def test_failure_cannot_disappear_from_denominator(self):
        with tempfile.TemporaryDirectory(prefix='pi-e2e12-inventory-') as scratch:
            root=Path(scratch)
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','fixture.jsonl']:
                shutil.copyfile(SOURCE/name,root/name)
            clients=[json.loads(x) for x in (root/'client.jsonl').read_text().splitlines()]
            omitted=next(x['task'] for x in clients if x['status']=='interrupted')
            (root/'client.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in clients if x['task']!=omitted))
            bridge=[json.loads(x) for x in (root/'bridge.jsonl').read_text().splitlines()]
            (root/'bridge.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in bridge if not (x['task']==omitted and x['event']=='settled')))
            with self.assertRaises(AssertionError):analyze(root)
    def test_settled_call_must_match_runtime_result(self):self.probe(lambda r:r.update(id='wrong-model-call'))
    def test_first_content_requires_raw_content_frame(self):self.probe(lambda r:r.update(firstContent=r['start']))
    def test_frame_cannot_occur_after_settled(self):self.probe(lambda r:r['frames'][-1].update(at=r['settled']+10000))
if __name__=='__main__':unittest.main()
