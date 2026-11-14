import unittest
from pathlib import Path
from launch import model_command
from authority import GPU

class LaunchTests(unittest.TestCase):
    def test_docker_created_nanoseconds_survive_server_python310_parser(self):
        from launch import docker_created_ns
        self.assertEqual(docker_created_ns('2026-11-14T00:00:00.123456789Z')%10**9,123456789)

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
