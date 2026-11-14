import os,sys,time,json,pathlib,subprocess,urllib.request,ipaddress
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');source=root/'source';sys.path.insert(0,str(source/'service/scripts/vllm-serve'));from owned import OwnedDocker
assert pathlib.Path.cwd()==root and os.environ['CUDA_VISIBLE_DEVICES']=='0'
nonce='cpu-private-ip03';out=root/nonce;out.mkdir();sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip();project='pi-vllm24-b';owner=OwnedDocker(project,sha,nonce);known={};stop=out/'stop-watch';deadline=time.time()+45;watch=None;failure=None
try:
 assert not owner.discover(known)
 with (out/'watch.log').open('w') as log:watch=subprocess.Popen([sys.executable,str(source/'service/scripts/vllm-serve/watch.py'),'--project',project,'--sha',sha,'--nonce',nonce,'--root',str(root),'--deadline',str(deadline-5),'--out',str(out/'watch.jsonl'),'--ready',str(out/'watch-ready'),'--stop-file',str(stop)],stdout=log,stderr=subprocess.STDOUT)
 while not (out/'watch-ready').exists():
  assert watch.poll() is None and time.time()<deadline-10;time.sleep(.02)
 cmd=['create','--pull','never','--runtime','runc','--network','pi-vllm24-b_default','--name',project+'-ip03','--label','com.docker.compose.project='+project,'--label','workorder=24','--label','execution-sha='+sha,'--label','pi24.nonce='+nonce,'--label','com.docker.compose.service=model','--user','1001:1001','--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','512','--read-only','--tmpfs','/tmp:size=64m','--cap-drop','ALL','--security-opt','no-new-privileges:true','-e','NVIDIA_VISIBLE_DEVICES=void','-e','CUDA_VISIBLE_DEVICES=0','-e','PYTHONDONTWRITEBYTECODE=1','-e','PYTHONPATH=/source','-e','NATIVE_TRACE=/evidence/native-trace.jsonl','-v',str(source)+':/source:ro','-v','/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111/builder/env:/venv:ro','-v',str(root/'cpu_fixture.py')+':/fixture.py:ro','-v',str(out)+':/evidence','--entrypoint','/venv/bin/python','sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229','/fixture.py']
 r=owner.command(cmd);assert r.returncode==0;cid=r.stdout.strip();owner.command(['start',cid]);row=owner.inspect(cid);known[cid]=row
 network=row['NetworkSettings']['Networks']['pi-vllm24-b_default'];ip=network['IPAddress'];assert ipaddress.ip_address(ip).is_private
 r=owner.command(['network','inspect',network['NetworkID']]);n=json.loads(r.stdout)[0];assert n['Id']==network['NetworkID'] and n['Internal'] and n['Labels']['com.docker.compose.project']==project
 result={'container':row,'network':n,'target':'http://'+ip+':8082/health','private_http':None}
 while time.time()<deadline-10:
  try:
   with urllib.request.urlopen(result['target'],timeout=1) as q:result['private_http']={'status':q.status,'body':q.read().decode()}
   break
  except Exception as e:result['last_error']=repr(e);time.sleep(.1)
 (out/'result.json').write_text(json.dumps(result,indent=2));assert result['private_http'] and result['private_http']['status']==200
except BaseException as e:failure=repr(e)
finally:
 stop.touch()
 if watch is not None:watch.wait(timeout=20)
 refresh=None
 try:owner.discover(known)
 except Exception as e:refresh=repr(e)
 result=owner.cleanup(known);value={'failure':failure,'refresh_error':refresh,'watch_exit':None if watch is None else watch.poll(),**result};(out/'outcome.json').write_text(json.dumps(value,indent=2));print(json.dumps({'failure':failure,'cleanup':result['success'],'result':json.loads((out/'result.json').read_text())['private_http'] if (out/'result.json').exists() else None}))
 if failure or refresh or not result['success']:raise SystemExit(1)
