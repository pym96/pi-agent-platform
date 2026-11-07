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
    def pg_span(self,queued,running):
        with tempfile.TemporaryDirectory(prefix='pi-e2e12-pg-time-') as scratch:
            root=Path(scratch)
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','fixture.jsonl']:
                shutil.copyfile(SOURCE/name,root/name)
            rows=json.loads((root/'pg-events.json').read_text())
            task=next(e['task'] for e in rows if e['kind']=='queued')
            for row in rows:
                if row['task']==task and row['kind']=='queued':row['created_at']=queued
                if row['task']==task and row['kind']=='running':row['created_at']=running
            (root/'pg-events.json').write_text(json.dumps(rows))
            result=analyze(root)
            return next(s['pg_queue_seconds'] for s in result['samples'] if s['task']==task)
    def test_pg_five_digit_fraction_preserves_queue_span(self):
        self.assertEqual(self.pg_span('2026-11-07T01:20:47.25993+00:00','2026-11-07T01:20:48.25993+00:00'),1.0)
    def test_pg_fraction_precision_and_timezone_preserve_instants(self):
        for precision in range(7):
            fraction='123456'[:precision]
            suffix='.'+fraction if fraction else ''
            expected=1+int(fraction.ljust(6,'0'))/1_000_000
            for timestamp in ('2026-11-07T01:20:48'+suffix+'Z',
                              '2026-11-07T01:20:48'+suffix+'+00:00',
                              '2026-11-07T06:50:48'+suffix+'+05:30',
                              '2026-11-06 21:50:48'+suffix+'-03:30'):
                with self.subTest(precision=precision,timestamp=timestamp):
                    self.assertEqual(self.pg_span('2026-11-07T01:20:47+00:00',timestamp),expected)
    def test_pg_invalid_or_naive_timestamps_fail_closed(self):
        invalid=[None,123,'','not-a-date','2026-11-07','2026-11-07T01:20:48',
                 '2026-11-07T01:20:48.123456','2026-11-07T01:20:48.+00:00',
                 '2026-11-07T01:20:48.1234567+00:00','2026-11-07T01:20:48.12x+00:00',
                 '2026-11-07T01:20:48+24:00','2026-11-07T01:20:48+00:99',
                 '2026-02-30T01:20:48+00:00','2026-11-07T25:20:48+00:00',
                 '2026-11-07T01:20:48+00:00junk','2026-11-07T01:20:48+00:00\n']
        for value in invalid:
            for queued,running in ((value,'2026-11-07T01:20:48Z'),('2026-11-07T01:20:47Z',value)):
                with self.subTest(queued=queued,running=running):
                    with self.assertRaises(ValueError):self.pg_span(queued,running)
        with self.assertRaises(ValueError):self.pg_span('2026-11-07T01:20:47','2026-11-07T01:20:48')
    def test_pg_negative_queue_interval_is_not_clamped(self):
        with self.assertRaises(AssertionError):
            self.pg_span('2026-11-07T01:20:48.25993+00:00','2026-11-07T01:20:48.25992+00:00')
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
    def test_historical_gpu3_cannot_be_relabelled_current_gpu0(self):
        source=SOURCE.parents[1]/'real-functional/smoke'
        with tempfile.TemporaryDirectory(prefix='pi-e2e12-gpu-') as scratch:
            root=Path(scratch)
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','health-before.json','health-after.json']:
                shutil.copyfile(source/name,root/name)
            run=json.loads((root/'run.json').read_text())
            run['resources']['gpu_uuid']='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead';run['config_sha256']='0'*64
            (root/'run.json').write_text(json.dumps(run))
            with self.assertRaises((AssertionError,ValueError,KeyError,TypeError,OSError)):analyze(root)
if __name__=='__main__':unittest.main()
