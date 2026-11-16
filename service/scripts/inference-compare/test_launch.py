import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from launch import model_command
from authority import GPU,verify_entries

class LaunchTests(unittest.TestCase):
    def test_original_tf_image_uses_verified_python_entry_and_keeps_native_guard(self):
        g={'source_sha':'a'*40,'role':'builder','nonce':'stage','phase_contract_sha256':'f'*64}
        for arm,expected in [('A','/usr/bin/python'),('B','/usr/bin/python3')]:
            model={'id':arm+'1','arm':arm,'nonce':'model-'+arm,'max_attempts':130,'deadline_epoch':1234}
            command=model_command(g,model,0,Path('/role'),Path('/role/run-stage')/model['id'],'n'*64,'g'*64)
            entry=command.index('--entrypoint')
            self.assertEqual(command[entry+1],expected)
            self.assertEqual(command[entry+3],'/source/service/scripts/inference-compare/native.py')
            self.assertEqual(command[entry+4:],['--go','/contract/go.json','--go-sha256','g'*64,
                '--phase-contract','/contract/phase.json','--phase-contract-sha256','f'*64,'--model-index','0'])

    def test_docker_created_nanoseconds_survive_server_python310_parser(self):
        from launch import docker_created_ns
        self.assertEqual(docker_created_ns('2026-11-14T00:00:00.123456789Z')%10**9,123456789)

    def test_native_tf_reuses_selected_interpreter_and_keeps_vllm_guarded_driver(self):
        import native
        from prepare import entries
        from test_authority import fixture,write
        source=Path(__file__).resolve().parents[3]
        real_path=Path
        class ExecObserved(Exception):pass
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);go,ph=fixture(root);go['entry_hashes']=entries(source)
            gh=write(root/'go.json',go)
            def mapped(value):
                path=real_path(value)
                if str(path).startswith('/source/'):return source/path.relative_to('/source')
                if str(path)=='/evidence/native-budget.json':return root/'native-budget.json'
                return path
            for index,arm in enumerate(('A','B')):
                argv=['native.py','--go',str(root/'go.json'),'--go-sha256',gh,
                    '--phase-contract',str(root/'phase.json'),'--phase-contract-sha256',ph,'--model-index',str(index)]
                with patch.object(sys,'argv',argv),patch.object(native,'Path',side_effect=mapped),\
                     patch.object(native,'verify_entries',side_effect=lambda value,unused:verify_entries(value,source)),\
                     patch.object(native.time,'time',return_value=1000),\
                     patch.dict(native.os.environ,{'PI28_MODEL_NONCE':go['models'][index]['nonce'],'CUDA_VISIBLE_DEVICES':'0'}),\
                     patch.object(native.os,'execvp',side_effect=ExecObserved) as execute:
                    with self.assertRaises(ExecObserved):native.main()
                program,command=execute.call_args.args
                self.assertEqual(program,'timeout')
                self.assertEqual(command[:3],['timeout','--signal=TERM','--kill-after=2s'])
                expected=[sys.executable,'-m','service.inference','--backend','transformers'] if arm=='A' else [
                    '/usr/bin/python3','/source/service/scripts/vllm-compat/driver.py','--','/venv/bin/python','-m','service.inference','--backend','vllm']
                self.assertEqual(command[4:4+len(expected)],expected)
                receipt=json.loads((root/'native-budget.json').read_text())
                self.assertEqual(receipt['model'],go['models'][index])
                self.assertEqual(receipt['phase'],ph);self.assertEqual(receipt['cleanup_reserve_s'],15)
                self.assertIn('--queue-timeout',command);self.assertIn('--generation-timeout',command)

    def test_new28_container_binds_native_guard_and_original_backend_limits(self):
        g={'source_sha':'a'*40,'role':'builder','nonce':'stage','phase_contract_sha256':'f'*64}
        model={'id':'A1','arm':'A','nonce':'model','max_attempts':130,'deadline_epoch':1234}
        command=model_command(g,model,0,Path('/role'),Path('/role/run-stage/A1'),'n'*64,'g'*64)
        self.assertNotIn('-p',command);self.assertIn('--read-only',command)
        self.assertIn('--cpus',command);self.assertEqual(command[command.index('--cpus')+1],'6')
        self.assertIn('OMP_NUM_THREADS=6',command);self.assertIn('TF_TOKEN_TRACE=/evidence/tf-trace.jsonl',command)
        self.assertIn('NVIDIA_VISIBLE_DEVICES='+GPU,command)
        self.assertIn('workorder=28',command);self.assertIn('pi28.nonce=model',command)
        self.assertIn('/source/service/scripts/inference-compare/native.py',command)
        self.assertNotIn('/source/service/scripts/vllm-serve/launch.py',command)

if __name__=='__main__':unittest.main()
