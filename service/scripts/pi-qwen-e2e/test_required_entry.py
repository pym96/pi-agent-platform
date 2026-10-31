"""Required guards exercised with native test runners, not fabricated counters."""
import json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class RequiredEntryTests(unittest.TestCase):
    def test_real_expected_failure_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='e2e12-required-') as tmp:
            copy=Path(tmp)
            for p in ROOT.glob('*.py'):shutil.copy2(p,copy/p.name)
            # All mandatory IDs collect. One real expectedFailure is still native-green.
            names=['test_settled_call_must_match_runtime_result','test_first_content_requires_raw_content_frame','test_frame_cannot_occur_after_settled','test_failure_cannot_disappear_from_denominator','test_cpu_fixture_cannot_be_relabelled_gpu','test_historical_gpu3_cannot_be_relabelled_current_gpu0']
            source='import unittest\nclass MeasurementEvidenceTests(unittest.TestCase):\n'
            for i,name in enumerate(names):
                source+=('    @unittest.expectedFailure\n' if i==0 else '')+f'    def {name}(self): self.assertTrue({i!=0!r})\n'
            (copy/'test_measurements.py').write_text(source)
            native=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(copy),'-p','test_measurements.py'],capture_output=True,text=True)
            self.assertEqual(native.returncode,0,native.stdout+native.stderr)
            guarded=subprocess.run([sys.executable,str(copy/'measurement_gate.py'),'--out',str(copy/'summary.json')],capture_output=True,text=True)
            self.assertNotEqual(guarded.returncode,0,guarded.stdout+guarded.stderr)
            result=json.loads((copy/'summary.json').read_text())
            self.assertEqual(result['expected_failures'],1)
    def test_actual_node_skip_todo_and_empty_are_rejected(self):
        from sdk_gate import REQUIRED
        with tempfile.TemporaryDirectory(prefix='e2e12-node-required-') as tmp:
            root=Path(tmp)
            for mode in ('normal','skip','todo','zero'):
                src="import test from 'node:test';\n"
                if mode!='zero':
                    for i,name in enumerate(sorted(REQUIRED)):
                        options={mode:True} if i==0 and mode!='normal' else {}
                        src+='test('+json.dumps(name)+','+json.dumps(options)+',()=>{});\n'
                fixture=root/(mode+'.mjs');fixture.write_text(src)
                run=subprocess.run([sys.executable,str(ROOT/'sdk_gate.py'),'--out',str(root/mode),str(fixture)],capture_output=True,text=True)
                self.assertEqual(run.returncode==0,mode=='normal',run.stdout+run.stderr)
                summary=json.loads((root/mode/'summary.json').read_text())
                if mode in ('skip','todo'):self.assertGreater(summary['skipped'],0)
    def test_real_skip_empty_and_unexpected_success_are_rejected(self):
        from measurement_gate import REQUIRED
        with tempfile.TemporaryDirectory(prefix='e2e12-python-required-') as tmp:
            root=Path(tmp)
            for mode in ('normal','skip','zero','unexpected_success'):
                copy=root/mode;copy.mkdir()
                shutil.copy2(ROOT/'measurement_gate.py',copy/'measurement_gate.py')
                source='import unittest\nclass MeasurementEvidenceTests(unittest.TestCase):\n'
                if mode=='zero':source+='    pass\n'
                else:
                    for i,name in enumerate(sorted(REQUIRED)):
                        source+=('    @unittest.skip("required skip")\n' if i==0 and mode=='skip' else '    @unittest.expectedFailure\n' if i==0 and mode=='unexpected_success' else '')
                        source+='    def '+name.rsplit('.',1)[-1]+'(self): self.assertTrue(True)\n'
                (copy/'test_measurements.py').write_text(source)
                run=subprocess.run([sys.executable,str(copy/'measurement_gate.py'),'--out',str(copy/'summary.json')],capture_output=True,text=True)
                self.assertEqual(run.returncode==0,mode=='normal',run.stdout+run.stderr)
    def test_actual_pytest_xpass_is_not_required_success(self):
        with tempfile.TemporaryDirectory(prefix='e2e12-pytest-required-') as tmp:
            root=Path(tmp);runner=root/'service/inference/scripts';runner.mkdir(parents=True)
            original=(ROOT.parents[1]/'inference/scripts/run_tests.py').read_text()
            plugin=ROOT.parents[1]/'inference/scripts/required_pytest.py'
            if plugin.exists():shutil.copy2(plugin,runner/plugin.name)
            for mode in ('normal','xfail','xpass'):
                case=root/('case_'+mode);case.mkdir()
                code='import pytest\n'+('@pytest.mark.xfail(strict=False)\n' if mode!='normal' else '')+'def test_native_case(): assert '+str(mode!='xfail')+'\n'
                (case/'test_case.py').write_text(code)
                (runner/'run_tests.py').write_text(original.replace("'service/inference/tests'",repr(str(case))))
                result=subprocess.run([sys.executable,str(runner/'run_tests.py'),'--out',str(root/('out_'+mode))],capture_output=True,text=True)
                self.assertEqual(result.returncode==0,mode=='normal',result.stdout+result.stderr)
    def test_authoritative_cli_requires_external_anchor_and_inventory(self):
        source=ROOT.parents[2]/'docs/evidence/pi-qwen-e2e-20261023/cpu/cpu-ready'
        with tempfile.TemporaryDirectory(prefix='e2e12-seal-') as tmp:
            root=Path(tmp);sealed=root/'sealed';sealed.mkdir()
            for name in ['run.json','client.jsonl','bridge.jsonl','go-trace.jsonl','pg-events.json','fixture.jsonl']:shutil.copy2(source/name,sealed/name)
            seal=subprocess.run([sys.executable,str(ROOT/'seal.py'),'--root',str(sealed),'--receipt-out',str(root/'receipt.json')],capture_output=True,text=True)
            self.assertEqual(seal.returncode,0,seal.stderr)
            digest=json.loads((root/'receipt.json').read_text())['manifest_sha256']
            command=[sys.executable,str(ROOT/'recompute.py'),'--root',str(sealed),'--out',str(root/'report.json')]
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            good=subprocess.run([*command,'--expected-manifest-sha256',digest],capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertTrue(json.loads((root/'report.json').read_text())['integrity_verified'])
            self.assertNotEqual(subprocess.run([*command,'--expected-manifest-sha256','0'*64],capture_output=True).returncode,0)
            original=(sealed/'run.json').read_bytes();(sealed/'run.json').write_bytes(original+b' ')
            self.assertNotEqual(subprocess.run([*command,'--expected-manifest-sha256',digest],capture_output=True).returncode,0)
            (sealed/'run.json').write_bytes(original);(sealed/'extra').write_text('untrusted')
            self.assertNotEqual(subprocess.run([*command,'--expected-manifest-sha256',digest],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
