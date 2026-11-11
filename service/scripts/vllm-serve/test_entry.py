"""The actual entry rejects forged/expired GO before touching Docker or CUDA."""
import json,hashlib,pathlib,subprocess,sys,tempfile,time,unittest
HERE=pathlib.Path(__file__).resolve().parent
class EntryTests(unittest.TestCase):
 def test_invalid_go_never_reaches_external_tools(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);go=d/'go.json';go.write_text(json.dumps({'issue':24,'deadline_epoch':1}))
   digest=hashlib.sha256(go.read_bytes()).hexdigest()
   r=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(go),'--go-sha256',digest],capture_output=True,text=True,timeout=5)
   self.assertEqual(r.returncode,2);self.assertIn('GO rejected',r.stderr)
   self.assertNotIn('docker',r.stderr.lower());self.assertNotIn('nvidia-smi',r.stderr.lower())
if __name__=='__main__':unittest.main()

class ClientEntryTests(unittest.TestCase):
 def test_client_cli_imports_from_its_source_with_clean_host_environment(self):
  import os
  env=dict(os.environ);env.pop('PYTHONPATH',None)
  with tempfile.TemporaryDirectory() as cwd:
   r=subprocess.run([sys.executable,str(HERE/'client.py'),'--help'],cwd=cwd,env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('--endpoints-sha256',r.stdout)
  self.assertNotIn('--model ',r.stdout);self.assertNotIn('--api ',r.stdout)


# Exact values from Master PHASE2-CONTRACT.v1.json, hash06b694..., not the implementation.
TEST_PHASE={'schema': 'pi24-phase-window/v1', 'id': 'pi24-nov11-p2', 'contract_sha256': '06b694ed12c3aebb62cd2bc870e13148998817b2dc96a30f373165665300d9f8', 'start_epoch': 1794411000.0, 'builder_latest_start_epoch': 1794414900.0, 'regulator_latest_start_epoch': 1794415800.0, 'all_owned_stop_epoch': 1794416400.0, 'end_epoch': 1794417600.0, 'global_end_epoch': 1794420671.0}
class PhaseWindowTests(unittest.TestCase):
 def load_entry(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('pi24_phase_entry',HERE/'launch.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def go(self,module,now,role='builder'):
  g={'issue':24,'role':role,'phase':dict(TEST_PHASE),'deadline_epoch':now+120,'max_duration_s':180,
     'gpu_uuid':module.UUID,'mode':'vllm','nonce':'cpu-phase-test','max_attempts':8}
  for key in ('source_sha','network_id','runtime_manifest_sha256','model_manifest_sha256','entry_sha256','watch_sha256','plan_sha256','driver_sha256','native_sha256','compose_sha256','assets_sha256'):
   g[key]='a'*(40 if key=='source_sha' else 64)
  g['entry_sha256']=module.sha(HERE/'launch.py');return g
 def validate(self,module,g,now):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'go.json';p.write_text(json.dumps(g));digest=module.sha(p)
   with patch.object(module.time,'time',return_value=now):return module.validate(p,digest)
 def test_fixed_P2_entry_accepts_each_role_after_retired_P1_cutoff(self):
  module=self.load_entry();now=TEST_PHASE['start_epoch']+1860
  for role in ['builder','regulator']:
   with self.subTest(role=role):
    g=self.go(module,now,role);self.assertEqual(self.validate(module,g,now),g)
 def test_phase_identity_and_every_bound_are_exact(self):
  module=self.load_entry();now=TEST_PHASE['start_epoch']+60
  for key in TEST_PHASE:
   with self.subTest(field=key):
    g=self.go(module,now,'regulator');value=g['phase'][key]
    g['phase'][key]=value+'x' if isinstance(value,str) else value+1
    with self.assertRaises(ValueError):self.validate(module,g,now)
  for phase in [None,{}, {'id':'pi24-nov11-p1'}, {**TEST_PHASE,'extra':True}]:
   g=self.go(module,now,'regulator');g['phase']=phase
   with self.assertRaises(ValueError):self.validate(module,g,now)
  g=self.go(module,now,'regulator');del g['phase']
  with self.assertRaises(ValueError):self.validate(module,g,now)
 def test_time_role_duration_and_nonfinite_inputs_reject(self):
  module=self.load_entry();start=TEST_PHASE['start_epoch'];stop=TEST_PHASE['all_owned_stop_epoch']
  cases=[]
  for role in ['builder','regulator']:
   now=TEST_PHASE[role+'_latest_start_epoch']+1;cases.append((self.go(module,now,role),now))
   now=start+60;g=self.go(module,now,role);g['max_duration_s']=901 if role=='builder' else 301;g['deadline_epoch']=now+g['max_duration_s'];cases.append((g,now))
  cases.append((self.go(module,start-1),start-1))
  cases.append((self.go(module,TEST_PHASE['end_epoch']+1),TEST_PHASE['end_epoch']+1))
  now=TEST_PHASE['regulator_latest_start_epoch'];g=self.go(module,now,'regulator');g['deadline_epoch']=stop+1;cases.append((g,now))
  now=start+60;g=self.go(module,now);g['deadline_epoch']=now-1;cases.append((g,now))
  for value in [float('nan'),float('inf'),float('-inf'),True]:
   g=self.go(module,now);g['deadline_epoch']=value;cases.append((g,now))
   g=self.go(module,now);g['phase']['all_owned_stop_epoch']=value;cases.append((g,now))
   g=self.go(module,now);g['max_duration_s']=value;cases.append((g,now))
  for clock in [float('nan'),float('inf'),float('-inf'),True]:cases.append((self.go(module,now),clock))
  for g,clock in cases:
   with self.subTest(role=g['role'],clock=clock,deadline=g['deadline_epoch']):
    with self.assertRaises(ValueError):self.validate(module,g,clock)
 def test_actual_cli_rejects_tampered_phase_without_tool_execution(self):
  module=self.load_entry();now=TEST_PHASE['start_epoch']+60;g=self.go(module,now);g['phase']['end_epoch']=TEST_PHASE['global_end_epoch']+1
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'go.json';p.write_text(json.dumps(g))
   r=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(p),'--go-sha256',module.sha(p)],capture_output=True,text=True,timeout=5)
  self.assertEqual(r.returncode,2);self.assertIn('GO rejected',r.stderr)
  self.assertNotIn('Execution failed',r.stderr)
 def test_wrong_go_digest_and_old_P1_go_reject(self):
  module=self.load_entry();now=TEST_PHASE['start_epoch']+60;g=self.go(module,now)
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'go.json';p.write_text(json.dumps(g))
   with self.assertRaises(ValueError):module.validate(p,'f'*64)
  old=self.go(module,now);del old['phase'];old['deadline_epoch']=1794408345.331222
  with self.assertRaises(ValueError):self.validate(module,old,now)
