"""Exact GO-bound stack; every collection failure still enters exact-owned cleanup."""
import threading
import argparse,subprocess,json,os,time,hashlib,urllib.request,traceback,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--go',required=True);a=p.parse_args();go=json.loads(Path(a.go).read_text());project=go['project'];deadline=go['deadline_epoch'];out=Path(go['out']);root=Path.cwd();source=root/'source';out.mkdir(parents=True,exist_ok=False)
 assert str(root).startswith('/media/usv012/pjx/pi-agent-platform/experiments/13-qwen-load-20261107/') and os.environ['CUDA_VISIBLE_DEVICES']=='0'
 assert project in ('pi-qwen13-b','pi-qwen13-r') and time.time()<deadline<=time.time()+900 and go['stage'] in ('pilot','formal')
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()==go['source_sha'] and not subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip()
 assert sha(source/'service/compose.qwen-load.yaml')==go['config_sha256'] and sha(source/'service/bin/service')==go['binary_sha256'] and sha(source/'service/scripts/pi-qwen-load/launch.py')==go['launcher_sha256'] and sha(source/'service/scripts/pi-qwen-load/watch.py')==go['watch_sha256']
 assert go['max_attempts']==(6 if go['stage']=='pilot' else 240)
 env=dict(os.environ,SOURCE_SHA=go['source_sha'],LOAD_PROJECT=project,LOAD_OUT=str(out),LOAD_PI_DATA=str(root/'pi-data'),LOAD_PROFILE='/evidence/profile.json' if go['stage']=='pilot' else '',MAX_ATTEMPTS=str(go['max_attempts']),DEADLINE_EPOCH=str(deadline),NODE_ROOT='/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3',PI_MODULES='/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules')
 (root/'pi-data').mkdir(exist_ok=True);started=time.monotonic();serial=0;status='failed';sampling_stop=threading.Event();sampler=None;watch_guard=None;watch_lost=threading.Event();client=project+'-client';client_created=False;client_id=None;startup_attempted=False;known_ids={}
 def call(args,key=None,check=True,timeout=60):
  nonlocal serial
  serial+=1;key=key or str(serial);s=time.time();r=subprocess.run(args,cwd=source,env=env,text=True,capture_output=True,timeout=timeout)
  (out/(key+'.json')).write_text(json.dumps({'command':args,'start_epoch':s,'end_epoch':time.time(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
  if check and r.returncode:raise RuntimeError('command failed:'+key)
  return r
 def compose(*args,**kw):return call(['docker','compose','-p',project,'-f','service/compose.qwen-load.yaml',*args],**kw)
 def watch_live():
  from watch_monitor import verify_watch
  return verify_watch(go)
 def guard():
  from watch_monitor import guard_watch
  guard_watch(go,sampling_stop,watch_lost,known_ids,out/'watch-loss.jsonl')

 try:
  # Two fresh empty snapshots, at least ten seconds apart. A foreign task is never stopped.
  for i in range(2):
   r=call(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],'gpu-empty-'+str(i))
   if any(line.split(',')[0].strip()==go['gpu_uuid'] for line in r.stdout.splitlines() if line.strip()):raise RuntimeError('foreign GPU0 process')
   if i==0:time.sleep(10)
  existing=call(['docker','ps','-a','-q','--filter','label=com.docker.compose.project='+project],'preexisting').stdout.split()
  assert not existing,'preexisting project objects; no takeover'
  watch_live()
  if go['stage']=='formal':assert sha(go['plan_host_path'])==go['plan_sha256']
  compose('config',key='compose-config');startup_attempted=True;watch_guard=threading.Thread(target=guard);watch_guard.start();compose('up','-d','pg','model','pi','api',key='compose-up',timeout=120)
  while time.time()<deadline-180:
   if watch_lost.is_set():raise RuntimeError('watch lost during startup')
   watch_live()
   try:
    observations={}
    for name,port,path in [('model',18181,'health'),('pi',18182,'metrics'),('api',18183,'health')]:
     with urllib.request.urlopen(f'http://127.0.0.1:{port}/{path}',timeout=2) as r:observations[name]=json.load(r)
    if observations['model']['ready'] and observations['model']['attempts']==0:break
   except (OSError,ValueError):pass
   time.sleep(1)
  else:raise RuntimeError('readiness/deadline')
  (out/'ready.json').write_text(json.dumps(observations,indent=2));ids=compose('ps','-q',key='stack-ids').stdout.split();call(['docker','inspect',*ids],'stack-inspect')
  def sample():
   while not sampling_stop.is_set():
    row={'utc_epoch':time.time(),'clock':'sampler-wall-epoch'}
    if watch_lost.is_set():break
    for name,port,path in [('model',18181,'health'),('pi',18182,'metrics'),('api',18183,'metrics')]:
     try:
      with urllib.request.urlopen(f'http://127.0.0.1:{port}/{path}',timeout=1) as response:row[name]=json.load(response)
     except Exception as e:row[name]={'error':repr(e)}
    try:row['docker_stats']=subprocess.check_output(['docker','stats','--no-stream','--format','{{json .}}',*ids],text=True,timeout=5)
    except Exception as e:row['stats_error']=repr(e)
    with (out/'resource-samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    sampling_stop.wait(1)
  sampler=threading.Thread(target=sample);sampler.start()
  command=['docker','create','--pull','never','--name',client,'--runtime','runc','--network','host','--label','com.docker.compose.project='+project,'--label','workorder=13','--label','execution-sha='+go['source_sha'],'--user','1001:1001','--read-only','--tmpfs','/tmp:size=256m','--cap-drop','ALL','--security-opt','no-new-privileges:true','--cpus','2','--memory','5g','--memory-swap','5g','-v',str(source)+':/source:ro','-v',str(out)+':/evidence','-v',str(root/'pi-data')+':/pi-data:ro','-v',str(root)+':/owned:ro','-e','PYTHONDONTWRITEBYTECODE=1','-e','CUDA_VISIBLE_DEVICES=0','-w','/source','--entrypoint','python','python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1','service/scripts/pi-qwen-load/campaign.py','--stage',go['stage'],'--out','/evidence/campaign','--bridge','/pi-data/bridge.jsonl','--deadline',str(deadline)]
  if go['stage']=='formal':command+=['--pilot',go['pilot_container_path'],'--plan',go['plan_container_path']]
  client_id=call(command,'client-create').stdout.strip();assert len(client_id)==64;client_created=True;call(['docker','inspect',client_id],'client-inspect');client_result=call(['docker','start','-a',client_id],'client-run',check=False,timeout=max(1,deadline-time.time()-20))
  state=json.loads(call(['docker','inspect',client_id],'client-state').stdout)[0]['State']
  if go['stage']=='formal':
   result=json.loads((out/'campaign/campaign-status.json').read_text());status=result['status'];assert status in ('complete','stopped')
  else:result={'status':'complete' if client_result.returncode==0 else 'failed'};status=result['status']
  (out/'campaign-result.json').write_text(json.dumps({'stage':go['stage'],'campaign':result,'client_exit':client_result.returncode,'client_state_exit':state['ExitCode'],'client_running':state['Running']},indent=2))
  if client_result.returncode or state['ExitCode'] or state['Running'] or status!='complete':raise RuntimeError('campaign did not complete:'+str(result))
 except BaseException:
  (out/'failure.txt').write_text(traceback.format_exc());raise
 finally:
  sampling_stop.set()
  if sampler is not None:sampler.join(8)
  if watch_guard is not None:watch_guard.join(20)
  for args,key in ([(['logs','--no-color'],'stack-logs'),(['exec','-T','pg','psql','-U','pan','-d','pan','-X','-At','-v','ON_ERROR_STOP=1','-c',"SELECT coalesce(json_agg(e ORDER BY id),'[]') FROM events e;"],'pg-events')] if startup_attempted else []):
   try:compose(*args,key=key,check=False,timeout=15)
   except Exception as e:(out/(key+'-error.txt')).write_text(repr(e))
  try:
   if client_created:
    sys.path.insert(0,str(HERE));from watch_cleanup import cleanup_known
    result=cleanup_known(project,go['source_sha'],[client_id]);(out/'client-stop.json').write_text(json.dumps(result,indent=2))
    if result['success']:call(['docker','rm',client_id],'client-rm',False)
  finally:
   try:
    if startup_attempted:
     sys.path.insert(0,str(HERE));from watch_cleanup import reconcile_owned
     result=reconcile_owned(project,go['source_sha'],known_ids);(out/'exact-stop.json').write_text(json.dumps(result,indent=2))
     if not result['success']:raise RuntimeError('owned stop incomplete')
     if known_ids:call(['docker','rm',*known_ids],'exact-remove',False)
   finally:
    ids=call(['docker','ps','-q','--no-trunc','--filter','label=com.docker.compose.project='+project],'remaining',check=False).stdout.split()
    sys.path.insert(0,str(HERE));from watch_cleanup import reconcile_owned
    cleanup=reconcile_owned(project,go['source_sha'],known_ids) if startup_attempted else {'success':True,'containers':{},'errors':[],'note':'startup not attempted; preexisting objects untouched'};(out/'cleanup.json').write_text(json.dumps({'status':status,'campaign_status':status,'cleanup_status':'succeeded' if cleanup['success'] else 'unknown_or_failed','lifecycle_seconds':time.monotonic()-started,**cleanup},indent=2))
    if not cleanup['success']:raise RuntimeError('cleanup unknown')
if __name__=='__main__':main()
