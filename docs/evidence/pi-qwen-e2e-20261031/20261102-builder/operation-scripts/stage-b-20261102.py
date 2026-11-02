"""Single Master-bound functional stack, three attempts, stop in finally. Not a GO."""
import os,subprocess,json,time,urllib.request,hashlib,traceback
from pathlib import Path
ROOT=Path.cwd();SHA='444096edccca28155ad60d9c17e2e8d2b7f5fdda';PROJECT='pi-e2e12-1031-b';DEADLINE=int(os.environ['DEADLINE_EPOCH']);OUT=ROOT.parent/'evidence/20261102-run01'
assert os.environ['CUDA_VISIBLE_DEVICES']=='0' and str(ROOT)=='/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/source'
assert time.time()<DEADLINE<=time.time()+900;OUT.mkdir(exist_ok=False)
ENV=dict(os.environ,SOURCE_SHA=SHA,E2E_PROJECT=PROJECT,NODE_ROOT='/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3',PI_MODULES='/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules')
START=time.monotonic_ns();status='failed';serial=0;model_started=False;client=PROJECT+'-client-20261102';created_client=False

def call(args,key=None,check=True,timeout=60):
 global serial
 serial+=1;key=key or 'command-'+str(serial);started=time.time_ns()
 r=subprocess.run(args,env=ENV,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
 (OUT/(key+'.stdout')).write_text(r.stdout);(OUT/(key+'.stderr')).write_text(r.stderr)
 with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps({'command':args,'key':key,'started_ns':started,'ended_ns':time.time_ns(),'exit_code':r.returncode})+'\n')
 if check and r.returncode:raise RuntimeError(key+' failed: '+r.stderr[-1000:])
 return r

def compose(*args,**kwargs):return call(['docker','compose','-p',PROJECT,'-f','service/compose.qwen.yaml',*args],**kwargs)
def health(url):
 with urllib.request.urlopen(url,timeout=3) as r:return json.load(r)
try:
 assert call(['git','rev-parse','HEAD'],'source-head').stdout.strip()==SHA
 assert not call(['git','status','--porcelain'],'source-status').stdout.strip()
 assert hashlib.sha256((ROOT/'service/scripts/pi-qwen-e2e/stage-b.json').read_bytes()).hexdigest()=='12253933a8b29d243d22c838789f8b80ba9f02cc45ed061c81f0e4911b40d991'
 compose('config',key='compose-config')
 (OUT/'execution.json').write_text(json.dumps({'source_sha':SHA,'deadline_epoch':DEADLINE,'started_utc_ns':time.time_ns(),'planned_attempts':3,'warmup':0,'retry':0},indent=2))
 compose('up','-d','pg','model','pi','api',key='compose-up',timeout=120);model_started=True
 while True:
  if time.time()>=DEADLINE-180:raise RuntimeError('insufficient deadline for smoke; stop without attempts')
  try:
   observations={name:health(url) for name,url in [('model','http://127.0.0.1:18181/health'),('pi','http://127.0.0.1:18182/metrics'),('api','http://127.0.0.1:18183/health')]}
   with (OUT/'readiness.jsonl').open('a') as f:f.write(json.dumps({'utc_epoch':time.time(),**observations})+'\n')
   if observations['model']['ready'] and observations['model']['attempts']==0 and observations['model']['max_attempts']==3:break
  except (OSError,ValueError):pass
  time.sleep(2)
 ids=compose('ps','-q',key='compose-ids').stdout.split();call(['docker','inspect',*ids],'stack-inspect')
 call(['python3','service/scripts/pi-qwen-e2e/device_proof.py','--project',PROJECT,'--sha',SHA,'--out',str(OUT/'device-identity')],'device-proof')
 args=['docker','create','--pull','never','--name',client,'--runtime','runc','--network','host','--label','com.docker.compose.project='+PROJECT,'--label','com.docker.compose.service=client','--label','workorder=12','--label','execution-sha='+SHA,'--user','1001:1001','--read-only','--tmpfs','/tmp:size=256m','--cap-drop','ALL','--security-opt','no-new-privileges:true','--cpus','2','--memory','5g','--memory-swap','5g','-v',str(ROOT)+':/source:ro','-v',str(OUT)+':/evidence','-e','PYTHONDONTWRITEBYTECODE=1','-e','CUDA_VISIBLE_DEVICES=0','-w','/source','--entrypoint','python','python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1','service/scripts/pi-qwen-e2e/smoke.py','--prefix','builder20261102','--sha',SHA,'--identity','/evidence/device-identity','--out','/evidence/smoke']
 call(args,'client-create');created_client=True;call(['docker','inspect',client],'client-inspect-before');call(['docker','start','-a',client],'client-smoke',timeout=300)
 ci=json.loads(call(['docker','inspect',client],'client-inspect-after').stdout)[0];assert ci['State']['ExitCode']==0 and not ci['State']['Running']
 bridge=compose('exec','-T','pi','cat','/data/bridge.jsonl',key='bridge');(OUT/'smoke/bridge.jsonl').write_text(bridge.stdout)
 api=compose('logs','--no-color','api',key='api-log');(OUT/'smoke/api.log').write_text(api.stdout+api.stderr)
 rows=[]
 for line in (api.stdout+api.stderr).splitlines():
  if '{' not in line:continue
  try:r=json.loads(line[line.index('{'):])
  except ValueError:continue
  if r.get('clock')=='go-since-claim':rows.append(r)
 (OUT/'smoke/go-trace.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
 pg=compose('exec','-T','pg','psql','-U','pan','-d','pan','-X','-At','-v','ON_ERROR_STOP=1','-c',"SELECT coalesce(json_agg(e ORDER BY id),'[]') FROM events e;",key='pg-events');(OUT/'smoke/pg-events.json').write_text(pg.stdout)
 import sys;sys.path.insert(0,str(ROOT/'service/scripts/pi-qwen-e2e'));from analyze import analyze
 summary=analyze(OUT/'smoke');(OUT/'smoke/summary.json').write_text(json.dumps(summary,indent=2));assert summary['attempts']==3 and summary['success']==3
 status='passed'
except BaseException:
 (OUT/'failure.txt').write_text(traceback.format_exc());raise
finally:
 # Diagnostics are best effort; stop attempts occur regardless of their outcome.
 try:compose('logs','--no-color',key='stack-logs',check=False)
 except Exception:pass
 try:
  if created_client:call(['docker','stop','-t','3',client],'client-stop',check=False);call(['docker','rm',client],'client-remove',check=False)
 finally:compose('down','--timeout','5',key='compose-down',check=False)
 remaining=call(['docker','ps','-q','--filter','label=com.docker.compose.project='+PROJECT],'remaining-owned',check=False).stdout.split()
 if remaining:call(['docker','stop','-t','3',*remaining],'fallback-stop',check=False)
 final=call(['docker','ps','-q','--filter','label=com.docker.compose.project='+PROJECT],'final-owned',check=False).stdout.split()
 call(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],'gpu-after',check=False);call(['ss','-ltn'],'ports-after',check=False)
 lifecycle=(time.monotonic_ns()-START)/1e9
 (OUT/'cleanup.json').write_text(json.dumps({'status':status,'source_sha':SHA,'remaining_owned_running':final,'conservative_stack_invocation_seconds':lifecycle,'model_compose_up_returned':model_started,'historical_attempts':3,'historical_lifetime_seconds':502,'diagnostic_volumes':'retained'},indent=2))
 if final:raise RuntimeError('owned workloads remain')
print(json.dumps({'status':status,'out':str(OUT),'conservative_invocation_seconds':lifecycle}))
