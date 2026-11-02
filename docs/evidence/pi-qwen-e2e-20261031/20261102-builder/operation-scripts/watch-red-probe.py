import subprocess,time,json,os
from pathlib import Path
root=Path.cwd();out=root.parent/'evidence/20261102-watch-red';out.mkdir();sha='444096edccca28155ad60d9c17e2e8d2b7f5fdda';p='pi-e2e12-1031-b';cid=None;watch=None
cmd=['docker','run','-d','--pull','never','--name',p+'-watch-red-probe','--runtime','runc','--network','none','--label','com.docker.compose.project='+p,'--label','workorder=12','--label','execution-sha='+sha,'--cpus','1','--memory','512m','--user','1001:1001','--read-only','--tmpfs','/tmp:size=32m','--cap-drop','ALL','--security-opt','no-new-privileges:true','--entrypoint','python','python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1','-c','import time;time.sleep(45)']
try:
 cid=subprocess.check_output(cmd,text=True).strip();assert len(cid)==64;(out/'create.json').write_text(json.dumps({'command':cmd,'id':cid}))
 args=['python3','service/scripts/pi-qwen-e2e/watch.py','--project',p,'--sha',sha,'--deadline',str(time.time()+45),'--root',str(root.parent),'--out',str(out/'watch.jsonl')]
 with (out/'stdout.log').open('w') as log:
  watch=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
  until=time.time()+20
  while time.time()<until:
   if watch.poll() is not None:raise RuntimeError('watch exited before deletion')
   if (out/'watch.jsonl').exists() and any(cid in x.get('running',[]) for x in [json.loads(l) for l in (out/'watch.jsonl').read_text().splitlines()]):break
   time.sleep(.2)
  else:raise RuntimeError('no watch running receipt')
  subprocess.run(['docker','rm','-f',cid],check=True,capture_output=True);code=watch.wait(20)
  (out/'result.json').write_text(json.dumps({'watch_command':args,'watch_exit_code':code,'expected_repaired_exit_code':0,'actual_removed_id':cid,'red_observed':code!=0},indent=2))
  assert code!=0,'old cleanup defect did not reproduce'
finally:
 if cid:subprocess.run(['docker','rm','-f',cid],capture_output=True)
 if watch is not None and watch.poll() is None:watch.terminate();watch.wait(20)
print((out/'result.json').read_text())
