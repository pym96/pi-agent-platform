import pathlib,os,sys,time,json,subprocess
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');source=root/'source';sys.path.insert(0,str(source/'service/scripts/vllm-serve'));from owned import OwnedDocker
assert pathlib.Path.cwd()==root and os.environ['CUDA_VISIBLE_DEVICES']=='0'
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip();owner=OwnedDocker('pi-vllm24-b',sha,'cpu-disk01');known={};out=root/'cpu-disk01';out.mkdir();error=None
code='''import os,json,pathlib
result={}
for i in range(4):
 root=pathlib.Path('/pg'+str(i));rows=[];errors=[]
 for parent,dirs,names in os.walk(root,onerror=lambda e:errors.append(repr(e))):
  for name in names:
   p=pathlib.Path(parent)/name
   if p.is_symlink():errors.append('unexpected symlink '+str(p))
   elif p.is_file():rows.append(p.stat().st_size)
 result[str(root)]={'files':len(rows),'regular_bytes':sum(rows),'errors':errors}
print(json.dumps(result))
'''
try:
 assert not owner.discover(known)
 cmd=['create','--pull','never','--runtime','runc','--network','none','--name',owner.project+'-disk01','--user','70:70','--read-only','--cpus','.5','--memory','128m','--memory-swap','128m','--pids-limit','64','--cap-drop','ALL','--security-opt','no-new-privileges:true','-e','NVIDIA_VISIBLE_DEVICES=void','-e','CUDA_VISIBLE_DEVICES=0','-e','PYTHONDONTWRITEBYTECODE=1']
 for k,v in owner.labels.items():cmd+=['--label',k+'='+v]
 for i in range(4):cmd+=['-v',str(root/('cpu-fullchain0'+str(i+1))/'data/pg-data')+':/pg'+str(i)+':ro']
 cmd+=['--entrypoint','/usr/bin/python3','sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229','-c',code]
 r=owner.command(cmd);assert r.returncode==0;cid=r.stdout.strip();known[cid]=owner.inspect(cid);start=time.time();r=subprocess.run(['docker','start','-a',cid],capture_output=True,text=True,timeout=15);end=time.time();owner.receipts.append({'command':['start','-a',cid],'start':start,'end':end,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});assert r.returncode==0
 rows=json.loads(r.stdout);assert all(not v['errors'] for v in rows.values());(out/'result.json').write_text(json.dumps({'source_sha':sha,'datasets':rows,'actual_retained_pg_regular_bytes':sum(v['regular_bytes'] for v in rows.values())},indent=2))
except BaseException as e:error=repr(e)
finally:
 try:owner.discover(known)
 except Exception as e:error=error or repr(e)
 cleanup=owner.cleanup(known);(out/'outcome.json').write_text(json.dumps({'error':error,'overall_success':not error and cleanup['success'],'cleanup_success':cleanup['success'],**cleanup},indent=2));print(json.dumps({'error':error,'cleanup':cleanup['success']}))
 if error or not cleanup['success']:raise SystemExit(1)
