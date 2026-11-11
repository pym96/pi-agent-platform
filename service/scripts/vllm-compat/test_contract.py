import unittest,subprocess,sys,pathlib,tempfile,json,time,hashlib
HERE=pathlib.Path(__file__).resolve().parent
class Contract(unittest.TestCase):
 def test_missing_go_never_executes(self):
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',d+'/missing','--go-sha256','0'*64],capture_output=True,text=True,timeout=3)
   self.assertNotEqual(p.returncode,0);self.assertIn('GO rejected',p.stderr)
 def test_go_rejections_before_gpu_commands(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('launcher',HERE/'launch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  good=dict(issue=21,role='builder',gpu_uuid=m.UUID,deadline_epoch=time.time()+30,max_duration_s=300,model_revision='b968826d9c46dd6066d109eabc6255188de91218',source_sha='a'*40,probe_sha256='b'*64,runtime_manifest_sha256='c'*64,launcher_sha256=m.sha(HERE/'launch.py'),watch_sha256=m.sha(HERE/'watch.py'),driver_sha256=m.sha(HERE/'driver.py'),model_manifest_sha256='f'*64,nonce='cpu-probe')
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'go.json'
   for patch in [{'deadline_epoch':time.time()-1},{'deadline_epoch':time.time()+10},{'issue':13},{'role':'master'},{'gpu_uuid':'GPU-other'},{'max_duration_s':301},{'launcher_sha256':'d'*64},{'model_revision':'latest'},{'source_sha':'z'*40}]:
    g={**good,**patch};f.write_text(json.dumps(g));p=subprocess.run([sys.executable,str(HERE/'launch.py'),'--go',str(f),'--go-sha256',m.sha(f)],capture_output=True,text=True,timeout=3)
    self.assertEqual(p.returncode,2,(patch,p.stdout,p.stderr));self.assertIn('GO rejected',p.stderr)
   f.write_text(json.dumps(good));self.assertEqual(m.validate(f,m.sha(f))['issue'],21)
   with self.assertRaises(ValueError):m.validate(f,'0'*64)


 def test_role_caps_and_absolute_window(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('launcher_window',HERE/'launch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as d:
   f=pathlib.Path(d)/'go.json'
   base=dict(issue=21,role='builder',gpu_uuid=m.UUID,deadline_epoch=1794385400,max_duration_s=300,model_revision='b968826d9c46dd6066d109eabc6255188de91218',source_sha='a'*40,probe_sha256='b'*64,runtime_manifest_sha256='c'*64,launcher_sha256=m.sha(HERE/'launch.py'),watch_sha256=m.sha(HERE/'watch.py'),driver_sha256=m.sha(HERE/'driver.py'),model_manifest_sha256='f'*64,nonce='window-probe')
   for role,cap,last in [('builder',300,1794418271),('regulator',180,1794418871)]:
    good={**base,'role':role,'max_duration_s':cap,'deadline_epoch':1794385200+cap};f.write_text(json.dumps(good));self.assertEqual(m.validate(f,m.sha(f),now=1794385200)['role'],role)
    for patch,now in [({'max_duration_s':cap+1},1794385200),({'deadline_epoch':1794419472},1794419300),({'deadline_epoch':last+2},last+1),({'deadline_epoch':1794325116},1794385200)]:
     f.write_text(json.dumps({**good,**patch}))
     with self.assertRaises(ValueError):m.validate(f,m.sha(f),now=now)
 def test_probe_import_has_no_runtime_or_model_side_effect(self):
  # Spawn/forkserver may import __main__: importing the probe must not construct LLM.
  import importlib.util
  spec=importlib.util.spec_from_file_location('isolated_smoke_import',HERE/'smoke.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  self.assertTrue(callable(module.main));self.assertFalse(hasattr(module,'llm'));self.assertFalse(hasattr(module,'OUT'))

class WatchContract(unittest.TestCase):
 def exercise(self,foreign=False):
  import os
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
   try:
    state=root/'state.json';state.write_text(json.dumps({'pid':child.pid,'nonce':'foreign' if foreign else 'cpu-test','cid':'c'*64}))
    docker=root/'docker';docker.write_text('''#!/usr/bin/env python3
import json,os,sys,signal,pathlib
s=json.loads(pathlib.Path(os.environ['CPU_DOCKER_STATE']).read_text())
if sys.argv[1]=='inspect':print(json.dumps([{'Id':s['cid'],'Config':{'Labels':{'pi21.nonce':s['nonce']}}}]))
elif sys.argv[1]=='stop':os.kill(s['pid'],signal.SIGTERM)
elif sys.argv[1]=='rm':pathlib.Path(os.environ['CPU_DOCKER_STATE']+'.removed').write_text('exact-owned')
else:sys.exit(7)
''');docker.chmod(0o755)
    env={**os.environ,'PATH':d+os.pathsep+os.environ['PATH'],'CPU_DOCKER_STATE':str(state)}
    args=[sys.executable,str(HERE/'watch.py'),'--cid','c'*64,'--nonce','cpu-test','--deadline',str(time.time()+.4),'--stop-file',d+'/stop','--out',d+'/events','--ready',d+'/ready']
    p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=4)
    if foreign:
     self.assertEqual(p.returncode,3);self.assertIsNone(child.poll());self.assertFalse(pathlib.Path(d+'/ready').exists());self.assertFalse(pathlib.Path(str(state)+'.removed').exists())
    else:
     self.assertEqual(p.returncode,0,p.stderr);child.wait(timeout=2);self.assertNotEqual(child.returncode,0);self.assertTrue(pathlib.Path(str(state)+'.removed').exists());self.assertIn('owned_cleanup_complete',pathlib.Path(d+'/events').read_text())
   finally:
    if child.poll() is None:child.terminate();child.wait(timeout=2)
 def test_deadline_stops_exact_owned_cpu_process(self):self.exercise()
 def test_mismatched_ownership_preserves_foreign_process(self):self.exercise(True)


class WheelContract(unittest.TestCase):
 def test_root_distribution_metadata_ignores_vendored_metadata(self):
  import importlib.util,zipfile
  spec=importlib.util.spec_from_file_location('wheel_lock_nested',HERE/'lock.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);w=root/'w';w.mkdir();rows=[]
   for name,version in m.PINNED.items():
    f=w/(name+'-fixture.whl')
    with zipfile.ZipFile(f,'w') as z:
     z.writestr(name+'.dist-info/METADATA','Name: '+name+'\nVersion: '+version+'\n')
     z.writestr(name+'/thirdparty_files/vendor.dist-info/METADATA','Name: vendor\nVersion: 1\nRequires-Dist: vendor-private-missing==1\n')
    rows.append(dict(name=name,version=version,filename=f.name,size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),url=m.XFORMERS if name=='xformers' else 'https://files.pythonhosted.org/'+f.name))
   lock=root/'lock';lock.write_text(json.dumps(rows));self.assertEqual(m.validate(lock,w)['artifacts'],len(m.PINNED))
   target=w/rows[0]['filename']
   with zipfile.ZipFile(target,'a') as z:z.writestr('other.dist-info/METADATA','Name: other\nVersion: 1\n')
   rows[0].update(size=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest());lock.write_text(json.dumps(rows))
   with self.assertRaisesRegex(ValueError,'metadata ambiguous'):m.validate(lock,w)

 def test_sealed_wheel_closure_rejects_corruption_and_source_drift(self):
  import importlib.util,zipfile
  spec=importlib.util.spec_from_file_location('wheel_lock',HERE/'lock.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);w=root/'w';w.mkdir();rows=[]
   for name,version in m.PINNED.items():
    f=w/(name+'-fixture.whl')
    with zipfile.ZipFile(f,'w') as z:z.writestr(name+'.dist-info/METADATA','Name: '+name+'\nVersion: '+version+'\n')
    rows.append(dict(name=name,version=version,filename=f.name,size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),url=m.XFORMERS if name=='xformers' else 'https://files.pythonhosted.org/'+f.name))
   lock=root/'lock';lock.write_text(json.dumps(rows));self.assertEqual(m.validate(lock,w)['artifacts'],len(m.PINNED))
   next(r for r in rows if r['name']=='triton')['url']='https://download-r2.pytorch.org/whl/triton-fixture.whl';lock.write_text(json.dumps(rows));self.assertEqual(m.validate(lock,w)['artifacts'],len(m.PINNED))
   target=w/rows[0]['filename'];original=target.read_bytes();target.write_bytes(original+b'bad')
   with self.assertRaisesRegex(ValueError,'bytes mismatch'):m.validate(lock,w)
   target.write_bytes(original);rows[0]['url']='https://untrusted.invalid/wheel';lock.write_text(json.dumps(rows))
   with self.assertRaisesRegex(ValueError,'untrusted'):m.validate(lock,w)
   rows[0]['url']='https://files.pythonhosted.org/'+rows[0]['filename']
   with zipfile.ZipFile(target,'w') as z:z.writestr('vllm.dist-info/METADATA','Name: vllm\nVersion: '+m.PINNED['vllm']+'\nRequires-Dist: deliberately-missing-transitive==1.0\n')
   rows[0].update(size=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest());lock.write_text(json.dumps(rows))
   with self.assertRaisesRegex(ValueError,'transitive'):m.validate(lock,w)
   lock.write_text('[]')
   with self.assertRaisesRegex(ValueError,'empty'):m.validate(lock,w)


class NativeDeadlineContract(unittest.TestCase):
 def test_absolute_native_timeout_terminates_actual_cpu_child(self):
  with tempfile.TemporaryDirectory() as d:
   receipt=pathlib.Path(d)/'receipt.json';pidfile=pathlib.Path(d)/'pid'
   command=[sys.executable,'-c','import os,pathlib,time;pathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid()));time.sleep(10)']
   start=time.time();p=subprocess.run([sys.executable,str(HERE/'native.py'),'--deadline',str(start+15.25),'--receipt',str(receipt),'--',*command],capture_output=True,text=True,timeout=4)
   self.assertEqual(p.returncode,124,p.stderr);self.assertLess(time.time()-start,3)
   data=json.loads(receipt.read_text());self.assertEqual(data['cleanup_reserve_s'],15);self.assertGreater(data['native_limit_s'],0);self.assertLess(data['native_limit_s'],.3)
   import os
   with self.assertRaises(ProcessLookupError):os.kill(int(pidfile.read_text()),0)
 def test_expired_native_deadline_never_executes_command(self):
  with tempfile.TemporaryDirectory() as d:
   marker=pathlib.Path(d)/'must-not-exist';p=subprocess.run([sys.executable,str(HERE/'native.py'),'--deadline',str(time.time()+14),'--receipt',d+'/receipt','--',sys.executable,'-c','open('+repr(str(marker))+',"w").write("executed")'],capture_output=True,text=True,timeout=3)
   self.assertEqual(p.returncode,2);self.assertFalse(marker.exists());self.assertIn('deadline rejected',p.stderr)

class LauncherModelPreflight(unittest.TestCase):
 def test_valid_model_manifest_reaches_cached_image_check(self):
  import importlib.util
  from unittest.mock import Mock,patch
  spec=importlib.util.spec_from_file_location('model_preflight',HERE/'launch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);RealPath=pathlib.Path
  with tempfile.TemporaryDirectory() as d:
   base=RealPath(d).resolve();root=base/'builder';source=root/'source';env=root/'env';env.mkdir(parents=True);(env/'one').write_bytes(b'env');probe=source/'service/scripts/vllm-compat/smoke.py';probe.parent.mkdir(parents=True);probe.write_bytes(b'probe');model=base/'model';model.mkdir();(model/'weights.safetensors').write_bytes(b'weights');manifest=source/'docs/evidence/qwen-load-20261021/model-files.json';manifest.parent.mkdir(parents=True);manifest.write_text(json.dumps([{'path':'weights.safetensors','bytes':7,'sha256':m.sha(model/'weights.safetensors')} ]));runtime=root/'runtime-manifest.json';runtime.write_text(json.dumps({'files':[{'path':'env/one','sha256':m.sha(env/'one')}]}));g={'role':'builder','runtime_manifest_sha256':m.sha(runtime),'probe_sha256':m.sha(probe),'source_sha':'a'*40,'watch_sha256':m.sha(HERE/'watch.py'),'driver_sha256':m.sha(HERE/'driver.py'),'model_path':'/media/usv012/pjx/agent/Qwen3-8B','model_manifest_sha256':m.sha(manifest),'image':'sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229'}
   def path(v):
    if str(v)=='/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111':return base
    if str(v)=='/media/usv012/pjx/agent/Qwen3-8B':return model
    return RealPath(v)
   P=Mock(side_effect=path);P.cwd.return_value=root
   def output(a,**kw):
    if a[0]=='git':return 'a'*40 if 'rev-parse' in a else ''
    raise RuntimeError('model identity passed before cached image')
   with patch.object(m.pathlib,'Path',P),patch.object(m.subprocess,'check_output',side_effect=output):
    with self.assertRaisesRegex(RuntimeError,'model identity passed'):m.execute(g,'unused','unused')

class DriverSelectionContract(unittest.TestCase):
 def module(self):
  import importlib.util
  s=importlib.util.spec_from_file_location('native_driver_selection',HERE/'driver.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def fixture(self,d):
  root=pathlib.Path(d).resolve();f=root/'libcuda.so.535.fixture';f.write_bytes(b'native535fixture');return root,f,hashlib.sha256(f.read_bytes()).hexdigest()
 def test_private_links_and_fresh_child_environment(self):
  import os,stat
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   root,f,h=self.fixture(d);private=root/'private';env=m.prepare(private,f,h,{'LD_LIBRARY_PATH':'original-path'})
   self.assertEqual((private/'libcuda.so.1').resolve(),f);self.assertEqual(stat.S_IMODE(private.stat().st_mode),0o700)
   p=subprocess.run([sys.executable,'-c','import os;print(os.environ["LD_LIBRARY_PATH"])'],env={**os.environ,**env},capture_output=True,text=True,timeout=3)
   self.assertEqual(p.returncode,0);self.assertEqual(p.stdout.strip(),str(private)+os.pathsep+'original-path')
 def test_missing_wrong_hash_and_preload_fail_before_directory(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   root,f,h=self.fixture(d)
   for path,digest,env in [(root/'missing',h,{}),(f,'0'*64,{}),(f,h,{'LD_PRELOAD':'foreign.so'})]:
    with self.assertRaises((ValueError,FileNotFoundError)):m.prepare(root/'private',path,digest,env)
    self.assertFalse((root/'private').exists())
 def test_unsafe_existing_private_directory_and_symlink_preserved(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   root,f,h=self.fixture(d);foreign=root/'foreign';foreign.mkdir();marker=foreign/'keep';marker.write_text('unchanged');link=root/'private';link.symlink_to(foreign,target_is_directory=True)
   for path in [foreign,link]:
    with self.assertRaises((ValueError,FileExistsError)):m.prepare(path,f,h,{})
   self.assertEqual(marker.read_text(),'unchanged');self.assertEqual(link.resolve(),foreign)
 def test_actual_mapping_requires_native_path_and_current_hash(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   root,f,h=self.fixture(d);maps='000-fff r-xp 0 0 0 '+str(f)+'\n';self.assertEqual(m.verify_mapping(maps,f,h)[0]['sha256'],h)
   wrong=root/'libcuda.so.550.fixture';wrong.write_bytes(f.read_bytes())
   for text in ['',maps.replace(str(f),str(wrong)),maps+'000-fff r-xp 0 0 0 '+str(wrong)+' (deleted)\n']:
    with self.assertRaises(ValueError):m.verify_mapping(text,f,h)
   f.write_bytes(b'tamperednative')
   with self.assertRaises(ValueError):m.verify_mapping(maps,f,h)
 def test_import_has_no_library_or_model_load(self):
  import ctypes
  from unittest.mock import patch
  with patch.object(ctypes,'CDLL',side_effect=AssertionError('loadduringimport')):self.assertTrue(callable(self.module().main))

if __name__=='__main__':unittest.main()
