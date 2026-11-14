"""Actual cached fallback image + unchanged native.py hard deadline; no CUDA/model."""
import pathlib,subprocess,sys,os,time,json,hashlib
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');source=root/'source';sys.path.insert(0,str(source/'service/scripts/vllm-serve'));from owned import OwnedDocker
assert pathlib.Path.cwd()==root and os.environ['CUDA_VISIBLE_DEVICES']=='0'
nonce='cpu-fallback-native01';out=root/nonce;out.mkdir();sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip();owner=OwnedDocker('pi-vllm24-b',sha,nonce);known={};watch=None;stop=out/'stop-watch';failure=None;epoch=time.time();deadline=epoch+24
try:
 assert not owner.discover(known)
 log=(out/'watch.log').open('w');watch=subprocess.Popen([sys.executable,str(source/'service/scripts/vllm-serve/watch.py'),'--project',owner.project,'--sha',sha,'--nonce',nonce,'--root',str(root),'--deadline',str(epoch+32),'--out',str(out/'watch.jsonl'),'--ready',str(out/'watch-ready'),'--stop-file',str(stop)],stdout=log,stderr=subprocess.STDOUT)
 while not (out/'watch-ready').exists():
  assert watch.poll() is None and time.time()<epoch+5;time.sleep(.02)
 command=['create','--pull','never','--runtime','runc','--network','none','--name',owner.project+'-native01','--label','com.docker.compose.project='+owner.project,'--label','workorder=24','--label','execution-sha='+sha,'--label','pi24.nonce='+nonce,'--label','com.docker.compose.service=model','--user','1001:1001','--cpus','1','--memory','512m','--memory-swap','512m','--pids-limit','512','--read-only','--tmpfs','/tmp:size=32m','--cap-drop','ALL','--security-opt','no-new-privileges:true','-e','NVIDIA_VISIBLE_DEVICES=void','-e','CUDA_VISIBLE_DEVICES=0','-e','PYTHONDONTWRITEBYTECODE=1','-v',str(source)+':/source:ro','-v',str(out)+':/evidence','--entrypoint','python','sha256:7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2','/source/service/scripts/vllm-compat/native.py','--deadline',str(deadline),'--receipt','/evidence/native-budget.json','--','python','-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("uncooperative CPU child",flush=True);time.sleep(60)']
 r=owner.command(command);assert r.returncode==0;cid=r.stdout.strip();known[cid]=owner.inspect(cid);(out/'created-inspect.json').write_text(json.dumps(known[cid],indent=2))
 start=time.time();r=owner.command(['start','-a',cid]);end=time.time();row=owner.inspect(cid);(out/'finished-inspect.json').write_text(json.dumps(row,indent=2))
 result={'kind':'actual-Docker-CPU-no-GPU-no-model','source_sha':sha,'native_sha256':hashlib.sha256((source/'service/scripts/vllm-compat/native.py').read_bytes()).hexdigest(),'outer_deadline':deadline,'start':start,'end':end,'elapsed':end-start,'native_exit':row['State']['ExitCode'],'running':row['State']['Running'],'stdout':r.stdout,'stderr':r.stderr,'no_device_requests':not row['HostConfig']['DeviceRequests'],'runtime':row['HostConfig']['Runtime'],'native_budget':json.loads((out/'native-budget.json').read_text())}
 (out/'result.json').write_text(json.dumps(result,indent=2));assert not row['State']['Running'] and row['State']['ExitCode'] in (124,137) and end<deadline and result['no_device_requests']
except BaseException as e:failure=repr(e)
finally:
 stop.touch()
 if watch is not None:watch.wait(timeout=20)
 refresh=None
 try:owner.discover(known)
 except Exception as e:refresh=repr(e)
 cleanup=owner.cleanup(known);value={'failure':failure,'refresh_error':refresh,'overall_success':not failure and not refresh and cleanup['success'],'cleanup_success':not refresh and cleanup['success'],'watch_exit':None if watch is None else watch.poll(),**cleanup};(out/'outcome.json').write_text(json.dumps(value,indent=2));print(json.dumps({'failure':failure,'cleanup':cleanup['success']}))
 if failure or refresh or not cleanup['success']:raise SystemExit(1)
