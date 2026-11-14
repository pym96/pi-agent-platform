"""The actual entry rejects forged/expired GO before touching Docker or CUDA."""
import json,hashlib,pathlib,subprocess,sys,tempfile,time,unittest
HERE=pathlib.Path(__file__).resolve().parent
class EntryTests(unittest.TestCase):
 def test_invalid_go_never_reaches_external_tools(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);go=d/'go.json';go.write_text(json.dumps({'issue':24,'deadline_epoch':1}))
   digest=hashlib.sha256(go.read_bytes()).hexdigest()
   r=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(go),'--go-sha256',digest,'--phase-contract',str(go),'--phase-contract-sha256',digest],capture_output=True,text=True,timeout=5)
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


class IndependentPhaseTests(unittest.TestCase):
 def load_entry(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('pi24_independent_phase',HERE/'launch.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 def phase(self,start=2000000000):
  import datetime
  phase={'schema':'pi24-master-phase-contract/v2','id':'simulation-'+str(start),'issue':24}
  for name,offset in [('start',0),('builder_latest_start',600),('regulator_latest_start',900),('all_owned_stop',1200),('end',1500),('global_end',1800)]:
   value=start+offset;phase[name+'_epoch']=value
   phase[name]=datetime.datetime.fromtimestamp(value,datetime.timezone.utc).isoformat().replace('+00:00','Z')
  return phase
 def go(self,module,phase,phase_hash,now,role='builder'):
  g={'issue':24,'role':role,'phase':phase,'phase_contract_sha256':phase_hash,'deadline_epoch':now+120,'max_duration_s':180,'gpu_uuid':module.UUID,'mode':'vllm','nonce':'cpu-independent-phase','max_attempts':8}
  for key in ('source_sha','network_id','runtime_manifest_sha256','model_manifest_sha256','entry_sha256','watch_sha256','plan_sha256','driver_sha256','native_sha256','compose_sha256','assets_sha256'):
   g[key]='a'*(40 if key=='source_sha' else 64)
  g['entry_sha256']=module.sha(HERE/'launch.py');return g
 def validate(self,module,phase,now,change_go=None,change_phase=None,expected_hash=None):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   pp=pathlib.Path(d)/'phase.json';pp.write_text(json.dumps(phase));ph=module.sha(pp)
   g=self.go(module,phase,ph,now)
   if change_go:change_go(g)
   gp=pathlib.Path(d)/'go.json';gp.write_text(json.dumps(g))
   if change_phase:change_phase(pp)
   with patch.object(module.time,'time',return_value=now):return module.validate(gp,module.sha(gp),pp,expected_hash or ph),g
 def test_same_source_accepts_two_independently_bound_phase_files(self):
  module=self.load_entry();before=module.sha(HERE/'launch.py')
  for start in [2000000000,2100000000]:
   phase=self.phase(start);actual,g=self.validate(module,phase,start+60);self.assertEqual(actual,g)
  self.assertEqual(module.sha(HERE/'launch.py'),before)

 def test_phase_hash_and_go_binding_cannot_be_changed_by_go_caller(self):
  module=self.load_entry();phase=self.phase();now=phase['start_epoch']+60
  changes=[lambda g:g.pop('phase_contract_sha256'),lambda g:g.update(phase_contract_sha256='f'*64),lambda g:g.pop('phase'),lambda g:g['phase'].update(id='retired-phase'),lambda g:g['phase'].update(end_epoch=phase['global_end_epoch']+1)]
  for change in changes:
   with self.subTest(change=change):
    # Each GO has its own deep copy so mutations cannot change the frozen input.
    frozen=json.loads(json.dumps(phase))
    with self.assertRaises(ValueError):self.validate(module,frozen,now,change_go=change)
  with self.assertRaises(ValueError):self.validate(module,phase,now,expected_hash='f'*64)
  with self.assertRaises(ValueError):self.validate(module,phase,now,change_phase=lambda p:p.write_text('{}'))
 def test_each_role_uses_its_own_last_start_and_original_duration_cap(self):
  module=self.load_entry();phase=self.phase();start=phase['start_epoch']
  for role in ['builder','regulator']:
   now=phase[role+'_latest_start_epoch']
   actual,g=self.validate(module,phase,now,change_go=lambda g:g.update(role=role));self.assertEqual(actual,g)
   with self.assertRaises(ValueError):self.validate(module,phase,now+1,change_go=lambda g:g.update(role=role))
   with self.assertRaises(ValueError):self.validate(module,phase,start+1,change_go=lambda g:g.update(role=role,max_duration_s=901 if role=='builder' else 301))

 def test_independent_phase_schema_order_utc_and_finite_times(self):
  module=self.load_entry();baseline=self.phase();now=baseline['start_epoch']+60
  changes=[lambda p:p.pop('schema'),lambda p:p.update(schema='unknown'),lambda p:p.pop('id'),lambda p:p.update(issue=25),lambda p:p.update(start='2033-05-18T03:33:20+00:00'),lambda p:p.update(start_epoch=p['start_epoch']+1),lambda p:p.update(global_end_epoch=p['end_epoch']-1)]
  for field in ['start','builder_latest_start','regulator_latest_start','all_owned_stop','end','global_end']:
   changes.append(lambda p,field=field:p.pop(field+'_epoch'))
   for value in [True,float('nan'),float('inf'),float('-inf'),'123']:
    changes.append(lambda p,field=field,value=value:p.update({field+'_epoch':value}))
  for change in changes:
   phase=json.loads(json.dumps(baseline));change(phase)
   with self.subTest(phase=phase):
    with self.assertRaises((ValueError,KeyError)):self.validate(module,phase,now)
 def test_early_expired_deadline_and_nonfinite_go_are_rejected(self):
  module=self.load_entry();phase=self.phase();start=phase['start_epoch'];now=start+60
  for clock in [start-1,phase['end_epoch']+1,True,float('nan'),float('inf'),float('-inf')]:
   with self.subTest(clock=clock):
    with self.assertRaises(ValueError):self.validate(module,phase,clock)
  for field in ['deadline_epoch','max_duration_s']:
   for value in [True,float('nan'),float('inf'),float('-inf'),'123']:
    with self.subTest(field=field,value=value):
     with self.assertRaises(ValueError):self.validate(module,phase,now,change_go=lambda g:g.update({field:value}))
  for deadline in [now-1,now+30,now+181,phase['all_owned_stop_epoch']+1]:
   with self.subTest(deadline=deadline):
    with self.assertRaises(ValueError):self.validate(module,phase,now,change_go=lambda g:g.update(deadline_epoch=deadline))
 def test_actual_cli_rejects_changed_go_phase_and_retired_go_before_tools(self):
  import os
  module=self.load_entry();phase=self.phase(int(time.time())-60)
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);pp=root/'phase.json';pp.write_text(json.dumps(phase));ph=module.sha(pp)
   marker=root/'external-tool-called'
   for name in ['docker','nvidia-smi']:
    tool=root/name;tool.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nPath('+repr(str(marker))+').touch()\n');tool.chmod(0o755)
   baseline=self.go(module,phase,ph,time.time())
   changed=json.loads(json.dumps(baseline));changed['phase']['end_epoch']+=1
   retired=json.loads(json.dumps(baseline));retired['phase']={'schema':'pi24-phase-window/v1','id':'pi24-nov11-p2'};retired.pop('phase_contract_sha256')
   for g in [changed,retired]:
    gp=root/'go.json';gp.write_text(json.dumps(g));env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ.get('PATH',''))
    result=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(gp),'--go-sha256',module.sha(gp),'--phase-contract',str(pp),'--phase-contract-sha256',ph],capture_output=True,text=True,env=env,timeout=5)
    self.assertEqual(result.returncode,2,result.stderr);self.assertIn('GO rejected',result.stderr);self.assertNotIn('Execution failed',result.stderr)
    self.assertFalse(marker.exists())
