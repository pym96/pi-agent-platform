import json,os,resource,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from launch import model_command
from authority import GPU,verify_entries

def resource_entry_probe(directory):
    """Real foreground entry with fake Docker transport, no daemon or GPU."""
    import launch
    from owned import OwnedDocker
    from plan import all_slots,pilot_block
    from prepare import entries
    from test_authority import fixture,write
    directory=Path(directory).resolve();role=directory/'builder';role.mkdir()
    source=Path(__file__).resolve().parents[3];(role/'source').symlink_to(source,target_is_directory=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    go,ph=fixture(role);go['source_sha']=head;go['entry_hashes']=entries(source)
    plan={'stage':'pilot','blocks':[pilot_block(arm) for arm in ('A','B')]}
    for block in plan['blocks']:
        for slot in all_slots(block):slot['expected_input_ids']=[4,5]
    go['plan_sha256']=write(role/'plan.json',plan);gh=write(role/'go.json',go)
    observed={'baseline_AS':list(resource.getrlimit(resource.RLIMIT_AS)),'affinity_mode':'actual Linux' if hasattr(os,'sched_setaffinity') else 'call seam only; host has no affinity syscall','affinity_calls':[],'commands':[]}
    actual_affinity=getattr(os,'sched_setaffinity',None)
    def affinity(pid,cpus):
        observed['affinity_calls'].append([pid,sorted(cpus)])
        if actual_affinity:actual_affinity(pid,cpus)
    def runner(args):
        observed['commands'].append(args);number=len(observed['commands'])
        code="""import json,os,resource,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'AS':list(resource.getrlimit(resource.RLIMIT_AS)),'affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None}))
if sys.argv[2]=='1':
 print('deliberate first inventory failure; original stderr',file=sys.stderr)
 raise SystemExit(2)
"""
        return subprocess.run([sys.executable,'-c',code,str(role/('resource-'+str(number)+'.json')),str(number)],capture_output=True,text=True,timeout=5)
    class Docker(OwnedDocker):
        def __init__(self,*args):super().__init__(*args,runner=runner)
    def identity(args,**unused):
        if args==['git','rev-parse','HEAD']:return head+'\n'
        if args==['git','status','--porcelain']:return ''
        raise AssertionError('unexpected identity command')
    previous=Path.cwd()
    try:
        os.chdir(role)
        with patch.object(launch,'ROOT',directory),patch.object(launch,'asset_check',return_value={}),\
             patch.object(launch.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(40*2**30,0,40*2**30)),\
             patch.object(launch.subprocess,'check_output',side_effect=identity),\
             patch.object(launch.os,'sched_setaffinity',side_effect=affinity,create=True),\
             patch.object(launch,'OwnedDocker',Docker),patch.object(launch.time,'time',return_value=1000),\
             patch.object(launch.subprocess,'Popen',wraps=subprocess.Popen) as popen,\
             patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'0'}),\
             patch.object(sys,'argv',['launch.py','--go',str(role/'go.json'),'--go-sha256',gh,'--phase-contract',str(role/'phase.json'),'--phase-contract-sha256',ph]):
            observed['exit']=launch.main()
            observed['spawn_argv']=[call.args[0] for call in popen.call_args_list]
    finally:os.chdir(previous)
    stage=role/'run-test-once/stage.json';observed['stage']=json.loads(stage.read_text()) if stage.exists() else None
    observed['child_resources']=[json.loads(p.read_text()) for p in sorted(role.glob('resource-*.json'))]
    (directory/'probe.json').write_text(json.dumps(observed,indent=2)+'\n')

class LaunchTests(unittest.TestCase):
    def test_real_entry_keeps_child_AS_and_cpu_affinity_and_preserves_failed_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            # Keep the script directory importable after the probe enters its role root,
            # as a real launch.py script entry does, without ambient PYTHONPATH.
            code='import sys;sys.path[0]='+repr(str(Path(__file__).resolve().parent))+';from test_launch import resource_entry_probe;resource_entry_probe('+repr(directory)+')'
            result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).parent,capture_output=True,text=True,timeout=20)
            (root/'child.stdout').write_text(result.stdout);(root/'child.stderr').write_text(result.stderr)
            evidence=os.environ.get('COMPARE_TEST_EVIDENCE')
            if evidence:
                target=Path(evidence)/'launch-resource-entry';target.mkdir(parents=True,exist_ok=False)
                for p in root.rglob('*'):
                    if p.is_file() and not p.is_symlink():
                        dest=target/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
            self.assertEqual(result.returncode,0,result.stderr)
            observed=json.loads((root/'probe.json').read_text())
            self.assertEqual(observed['exit'],2)
            self.assertTrue(observed['child_resources'],'foreground must reach the real child resource boundary')
            self.assertEqual(observed['child_resources'][0]['AS'],observed['baseline_AS'])
            self.assertEqual(observed['affinity_calls'],[[0,[0,1]]])
            if observed['affinity_mode']=='actual Linux':self.assertEqual(observed['child_resources'][0]['affinity'],[0,1])
            self.assertEqual(len(observed['commands']),2)
            self.assertTrue(all(command==['ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project=pi-compare28-b'] for command in observed['commands']))
            self.assertTrue(all(argv[:2]==[sys.executable,'-c'] for argv in observed['spawn_argv']))
            stage=observed['stage'];self.assertFalse(stage['complete']);self.assertTrue(stage['native_count_unknown'])
            model=stage['models'][0]
            self.assertEqual(model['failure'],"RuntimeError('project inventory unknown')")
            self.assertEqual(model['cleanup']['receipts'][0]['exit'],2)
            self.assertIn('deliberate first inventory failure; original stderr',model['cleanup']['receipts'][0]['stderr'])
            self.assertEqual(model['cleanup']['receipts'][1]['exit'],0)
            for key in ['device_s','native','POST']:self.assertIsNone(model[key])
            self.assertNotIn('cid',model)
            self.assertFalse((root/'builder/run-test-once/pilotA/empty-gate.json').exists())
            self.assertFalse((root/'builder/run-test-once/pilotA/watch.jsonl').exists())

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
