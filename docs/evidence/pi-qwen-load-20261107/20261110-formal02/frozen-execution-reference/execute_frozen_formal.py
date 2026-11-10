"""Foreground entry only: no wait, scheduler, retry, renewal, or default GO path."""
import base64,datetime,hashlib,json,shlex,subprocess,sys,time
from pathlib import Path
S=Path(__file__).resolve().parent
ROOT='/media/usv012/pjx/pi-agent-platform/experiments/13-qwen-load-20261107/builder'
REPO=Path('/Users/panyiming/Desktop/todo/面试/career-planning/60-项目/pi-agent-platform-load13-restoration-candidate')
SSH=['ssh','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','BatchMode=yes','-o','ConnectTimeout=10','wt@58.199.171.85']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clock():return {'epoch':time.time(),'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def fresh(g):
 now=time.time()
 assert g['earliest_start_epoch']<=now and now+30<g['latest_start_epoch'],'insufficient unchanged native startup runway; no nonce/watch/model'
 return now
def execution_outcome(coordinator_exit,launch,watch_rows,fresh_epoch,expected_command):
 errors=[];native_exit=None
 if coordinator_exit!=0:errors.append('coordinator_nonzero')
 if not isinstance(launch,dict):errors.append('fresh_native_result_unknown')
 else:
  native_exit=launch.get('exit')
  if type(native_exit) is not int or native_exit!=0:errors.append('native_nonzero_or_unknown')
  if not isinstance(launch.get('start_epoch'),(int,float)) or not isinstance(launch.get('end_epoch'),(int,float)) or not fresh_epoch<=launch['start_epoch']<=launch['end_epoch']:errors.append('native_result_not_fresh')
  if not isinstance(launch.get('command'),list) or not launch['command'] or launch['command'][-1]!=expected_command:errors.append('native_command_binding_unknown')
 if len(watch_rows)!=1 or type(watch_rows[0].get('watch_exit')) is not int or watch_rows[0]['watch_exit']!=0 or not isinstance(watch_rows[0].get('ended_epoch'),(int,float)) or watch_rows[0]['ended_epoch']<fresh_epoch:errors.append('fresh_watch_stop_nonzero_or_unknown')
 code=0 if not errors else native_exit if type(native_exit) is int and native_exit!=0 else coordinator_exit if coordinator_exit!=0 else 1
 return {'complete':not errors,'exit_code':code,'coordinator_exit':coordinator_exit,'native_exit':native_exit,'watch_rows':watch_rows,'errors':errors}
assert len(sys.argv)==2,'one explicit Master envelope path required'
envelope=Path(sys.argv[1]);g=json.loads(envelope.read_text());key=Path(g['out']).name
pre={'phase':'before_checks','clock':clock(),'envelope_sha256':sha(envelope),'nonce':g['nonce'],'literal_already_exists':(S/(key+'-go.json')).exists()}
(S/(key+'-entry-precheck-'+str(time.time_ns())+'.json')).write_text(json.dumps(pre,indent=2));print(json.dumps(pre),flush=True)
assert not pre['literal_already_exists'],'nonce/out already consumed; no retry'
assert g.get('phase')=='phase5' and g['nonce']!='pi13-nov10-formal02-once','retired phase4 GO cannot be revived'
assert (g['earliest_start_epoch'],g['latest_start_epoch'],g['outer_stop_epoch'])==(1794317213,1794322613,1794323513),'exact new phase5 window required'
fresh(g)
assert g['source_sha']=='260831db022021289e5e29776292385f81cd8078' and g['stage']=='formal' and g['max_attempts']==240
if 'entrypoint_sha256' in g:assert sha(__file__)==g['entrypoint_sha256']
assert g['required_CI_run']==42822018807 and sha(S/'ci6-original.zip')=='61667d3fcc1fbfcf232aa0311101906a1497f6f796fcde39b55ee92b1bce1dd9'
summary=json.loads((S/'ci6-original/load13/summary.json').read_text());assert summary['tests']==26 and summary['skipped']==0 and summary['success'] and not summary['errors'] and not summary['failures']
assert sha(S/'interrupt6-terminal-HANDOFF.json')=='6998bfb347276cdff662c5c45bd885013f06d2854f3b70d68f2f0298917bee5f'
assert subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()==g['source_sha']
assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain'],text=True).strip()
for keyname,name in {'config':'service/compose.qwen-load.yaml','launcher':'service/scripts/pi-qwen-load/launch.py','watch':'service/scripts/pi-qwen-load/watch.py','monitor':'service/scripts/pi-qwen-load/watch_monitor.py','sample':'service/scripts/pi-qwen-load/watch_sample.py','cleanup':'service/scripts/pi-qwen-load/watch_cleanup.py','load':'service/scripts/pi-qwen-load/load.py','campaign':'service/scripts/pi-qwen-load/campaign.py','pairs':'service/scripts/pi-qwen-load/pairs.py','recover':'service/scripts/pi-qwen-load/recover.py'}.items():assert sha(REPO/name)==g[keyname+'_sha256'],keyname
coordinator=S/'execute_pilot.py';assert sha(coordinator)==g['coordinator_sha256']
plan_dir=S/Path(g['plan_host_path']).parent.name
for keyname,name in [('plan','frozen-plan.json'),('arrival_traces','arrival-traces.json'),('identity_proof','identity-proof.json')]:assert sha(plan_dir/name)==g[keyname+'_sha256'],keyname
assert Path(g['plan_host_path']).parent.parent==Path(ROOT) and g['project']=='pi-qwen13-b'
files={p.name:{'b64':base64.b64encode(p.read_bytes()).decode(),'sha256':sha(p)} for p in plan_dir.iterdir() if p.is_file()}
remote="""import json,sys,hashlib,base64,time,subprocess,shutil
from pathlib import Path
data=json.load(sys.stdin);v=data['files'];go=data['go'];source=Path('source')
def command(args):return subprocess.check_output(args,text=True,timeout=10)
assert command(['git','-C','source','rev-parse','HEAD']).strip()==go['source_sha'] and not command(['git','-C','source','status','--porcelain']).strip()
for key,name in {'config':'service/compose.qwen-load.yaml','binary':'service/bin/service','launcher':'service/scripts/pi-qwen-load/launch.py','watch':'service/scripts/pi-qwen-load/watch.py','monitor':'service/scripts/pi-qwen-load/watch_monitor.py','sample':'service/scripts/pi-qwen-load/watch_sample.py','cleanup':'service/scripts/pi-qwen-load/watch_cleanup.py','load':'service/scripts/pi-qwen-load/load.py','campaign':'service/scripts/pi-qwen-load/campaign.py','pairs':'service/scripts/pi-qwen-load/pairs.py','recover':'service/scripts/pi-qwen-load/recover.py'}.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==go[key+'_sha256'],key
assert not Path(go['out']).exists() and not Path(go['watch_receipt']).exists() and not Path(Path(go['out']).name+'-go.json').exists(),'prior execution path exists; no takeover'
owned={project:command(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+project]) for project in ['pi-qwen13-b','pi-qwen13-r']};print(json.dumps({'preflight_owned':owned,'epoch':time.time()}),flush=True);assert not any(x.strip() for x in owned.values()),'owned slot not empty'
sizes={role:sum(p.stat().st_size for p in (Path.cwd().parent/role).rglob('*') if p.is_file()) for role in ['builder','regulator']};free=shutil.disk_usage('.').free
available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
print(json.dumps({'preflight_resource':{'root_sizes':sizes,'disk_free':free,'available_memory':available},'epoch':time.time()}),flush=True);assert sum(sizes.values())<2*2**30 and free>20*2**30 and available>=40*2**30,'resource preflight rejected'
samples=[]
for index in range(2):
 at=time.monotonic();apps=command(['nvidia-smi','-i','0','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']);gpu=command(['nvidia-smi','-i','0','--query-gpu=index,uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'])
 samples.append({'epoch':time.time(),'monotonic':at,'gpu':gpu,'compute_apps':apps});print(json.dumps({'preflight_GPU_sample':samples[-1]}),flush=True);assert not apps.strip(),'GPU busy; no nonce/watch/model';assert 'GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead' in gpu
 if index==0:time.sleep(10)
assert samples[1]['monotonic']-samples[0]['monotonic']>=10
r=Path(PLAN_DIR);r.mkdir(exist_ok=True);proof={}
for name,item in v.items():
 assert Path(name).name==name
 p=r/name
 if not p.exists():
  with p.open('xb') as out:out.write(base64.b64decode(item['b64']))
 proof[name]=hashlib.sha256(p.read_bytes()).hexdigest();assert proof[name]==item['sha256']
print(json.dumps({'epoch':time.time(),'fresh_GPU_samples':samples,'owned':owned,'root_sizes':sizes,'disk_free':free,'available_memory':available,'files':proof}))
""".replace('PLAN_DIR',repr(plan_dir.name))
fresh(g)
r=subprocess.run(SSH+['cd '+ROOT+' && export CUDA_VISIBLE_DEVICES=0 && python3 -c '+shlex.quote(remote)],input=json.dumps({'files':files,'go':g}),capture_output=True,text=True,timeout=50)
proof={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr};(S/(key+'-plan-upload-and-GPU.json')).write_text(json.dumps(proof,indent=2));assert r.returncode==0,proof
now=fresh(g);g['deadline_epoch']=min(int(now)+900,g['outer_stop_epoch']);assert 200<=g['deadline_epoch']-now<=900
assert g['cumulative_B_before_seconds']+g['deadline_epoch']-now<=1500 and g['cumulative_B_before_modelHTTP']+240<=g['cumulative_B_modelHTTP_cap']
g['envelope_sha256']=sha(envelope);literal=S/(key+'-go.json')
with literal.open('x') as out:json.dump(g,out,indent=2)
receipt={'fresh_epoch':now,'fresh_UTC':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat(),'literal_deadline_epoch':g['deadline_epoch'],'literal_go_sha256':sha(literal),'envelope_sha256':sha(envelope),'entrypoint_sha256':sha(__file__),'nonce':g['nonce'],'source_sha':g['source_sha'],'R_source_StageA_archive_sha256':'9a7aa480597b01f24082cb85902a0cf6c93e70a9621dd38f98816d08421b02f0','CI6_actual_artifact_sha256':sha(S/'ci6-original.zip')}
(S/(key+'-clock.json')).write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
stdout_path=S/(key+'-coordinator.stdout');stderr_path=S/(key+'-coordinator.stderr');watch_rows=[]
with stdout_path.open('x') as capture,stderr_path.open('x') as errors:
 process=subprocess.Popen([sys.executable,str(coordinator),str(literal)],stdout=subprocess.PIPE,stderr=errors,text=True)
 for line in process.stdout:
  capture.write(line);capture.flush();print(line,end='',flush=True)
  try:
   event=json.loads(line)
   if isinstance(event,dict) and 'watch_exit' in event:watch_rows.append(event)
  except ValueError:pass
 coordinator_exit=process.wait()
launch_file=S/(key+'-launch.json');launch=None;read_error=None
try:launch=json.loads(launch_file.read_text())
except (OSError,ValueError) as error:read_error=repr(error)
expected='cd '+ROOT+' && export CUDA_VISIBLE_DEVICES=0 && python3 source/service/scripts/pi-qwen-load/launch.py --go '+ROOT+'/'+key+'-go.json'
outcome=execution_outcome(coordinator_exit,launch,watch_rows,now,expected);outcome.update(native_result_read_error=read_error,coordinator_stdout_sha256=sha(stdout_path),coordinator_stderr_sha256=sha(stderr_path),native_result_sha256=sha(launch_file) if launch_file.exists() else None)
(S/(key+'-entry-outcome.json')).write_text(json.dumps(outcome,indent=2));print(json.dumps(outcome),flush=True)
raise SystemExit(outcome['exit_code'])
