"""Issue24 foreground entry. A frozen exact Master GO is required before GPU use."""
import argparse,datetime,hashlib,json,math,os,pathlib,subprocess,sys,time
UUID='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
ROOT=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111')
# Frozen Master P2 allocation; hashes identify bytes, not signatures or authority.
HUMAN_GLOBAL_END=1794420671.0
PHASE={'schema': 'pi24-phase-window/v1',
 'id': 'pi24-nov11-p2',
 'contract_sha256': '06b694ed12c3aebb62cd2bc870e13148998817b2dc96a30f373165665300d9f8',
 'start_epoch': 1794411000.0,
 'builder_latest_start_epoch': 1794414900.0,
 'regulator_latest_start_epoch': 1794415800.0,
 'all_owned_stop_epoch': 1794416400.0,
 'end_epoch': 1794417600.0,
 'global_end_epoch': 1794420671.0}
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def epoch(text):return datetime.datetime.fromisoformat(text.replace('Z','+00:00')).timestamp()
def validate(path,digest):
 if sha(path)!=digest:raise ValueError('GO hash mismatch')
 g=json.loads(pathlib.Path(path).read_text());now=time.time()
 if g.get('issue')!=24 or g.get('role') not in ('builder','regulator'):raise ValueError('GO identity')
 phase=g.get('phase')
 if type(phase) is not dict or phase!=PHASE:raise ValueError('fixed P2 phase identity/bounds required')
 for value in [now,g.get('deadline_epoch'),g.get('max_duration_s'),*[phase[k] for k in phase if k.endswith('_epoch')]]:
  if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('finite phase/GO time required')
 if not (phase['start_epoch']<=phase['builder_latest_start_epoch']<=phase['regulator_latest_start_epoch']<=phase['all_owned_stop_epoch']<=phase['end_epoch']<=phase['global_end_epoch']==HUMAN_GLOBAL_END):raise ValueError('phase ordering/global boundary')
 role=g['role'];latest=phase[role+'_latest_start_epoch'];cap=900 if role=='builder' else 300
 if not phase['start_epoch']<=now<=latest or not 30<g['deadline_epoch']-now<=g['max_duration_s']<=cap or g['deadline_epoch']>phase['all_owned_stop_epoch']:raise ValueError('GO expired or over budget')
 if g['gpu_uuid']!=UUID or g['mode'] not in ('vllm','transformers'):raise ValueError('GO device/backend')
 if not g['nonce'] or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in g['nonce']):raise ValueError('GO nonce')
 if not 1<=g['max_attempts']<=(64 if role=='builder' else 16):raise ValueError('attempt cap')
 for key in ('source_sha','network_id','runtime_manifest_sha256','model_manifest_sha256','entry_sha256','watch_sha256','plan_sha256','driver_sha256','native_sha256','compose_sha256','assets_sha256'):
  value=g[key]
  if len(value)!=(40 if key=='source_sha' else 64) or any(c not in '0123456789abcdef' for c in value):raise ValueError('bad '+key)
 if sha(__file__)!=g['entry_sha256']:raise ValueError('entry changed')
 return g

def execute(g,path,digest):
 from owned import OwnedDocker
 import socket,urllib.request
 root=ROOT/g['role'];source=root/'source';here=source/'service/scripts/vllm-serve'
 if pathlib.Path.cwd().resolve()!=root or os.environ.get('CUDA_VISIBLE_DEVICES')!='0':raise ValueError('role root/CUDA mapping')
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=g['source_sha'] or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():raise ValueError('source identity/dirty')
 bindings={'entry_sha256':here/'launch.py','watch_sha256':here/'watch.py','compose_sha256':source/'service/compose.vllm.yaml','driver_sha256':source/'service/scripts/vllm-compat/driver.py','native_sha256':source/'service/scripts/vllm-compat/native.py','plan_sha256':root/g['plan_file'],'assets_sha256':root/'asset-inventory.json'}
 for key,file in bindings.items():
  if sha(file)!=g[key]:raise ValueError('changed '+key)
 runtime_root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111/builder')
 manifest=runtime_root/'runtime-manifest.json'
 if sha(manifest)!=g['runtime_manifest_sha256']:raise ValueError('runtime manifest changed')
 for row in json.loads(manifest.read_text())['files']:
  if sha(runtime_root/row['path'])!=row['sha256']:raise ValueError('runtime bytes changed')
 model_manifest=source/'docs/evidence/qwen-load-20261021/model-files.json'
 if sha(model_manifest)!=g['model_manifest_sha256']:raise ValueError('model manifest changed')
 for row in json.loads(model_manifest.read_text()):
  if row['path'].startswith(('.cache/','._')):continue
  f=pathlib.Path('/media/usv012/pjx/agent/Qwen3-8B')/row['path']
  if f.stat().st_size!=row['bytes'] or sha(f)!=row['sha256']:raise ValueError('model bytes changed')
 assets=json.loads((root/'asset-inventory.json').read_text())
 for item in assets['files'].values():
  if sha(item['path'])!=item['sha256']:raise ValueError('cached asset changed')
 if sha(root/'sdk-files.json')!=assets['sdk']['manifest_sha256']:raise ValueError('SDK manifest changed')
 for row in json.loads((root/'sdk-files.json').read_text()):
  if sha(pathlib.Path(assets['sdk']['path'])/row['path'])!=row['sha256']:raise ValueError('SDK bytes changed')
 if g['mode']=='transformers':
  original=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021')
  dep_manifest=original/'deps-manifest.json'
  if sha(dep_manifest)!='0daa116e06671a31c9b57f69a7664aa30c5e33d04898eda18f08451bfa93a1e3':raise ValueError('original fallback dependency manifest changed')
  for row in json.loads(dep_manifest.read_text()):
   file=original/'deps'/row['path']
   if file.stat().st_size!=row['bytes'] or sha(file)!=row['sha256']:raise ValueError('original fallback dependency bytes changed')
 role=g['role'];project='pi-vllm24-'+('b' if role=='builder' else 'r');offset=0 if role=='builder' else 10
 docker=OwnedDocker(project,g['source_sha'],g['nonce']);known={}
 if docker.discover(known):raise ValueError('preexisting task containers')
 from endpoints import network,resolve
 net=network(docker,g['network_id'])
 snapshots=[]
 for i in range(2):
  uuid=subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=uuid','--format=csv,noheader'],text=True,timeout=5).strip()
  pids=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True,timeout=5).strip()
  snapshots.append({'epoch':time.time(),'uuid':uuid,'pids':pids})
  if uuid!=UUID or pids:raise ValueError('GPU0 busy/identity unknown')
  if i==0:time.sleep(10)
 if validate(path,digest)!=g:raise ValueError('GO changed')
 (root/('consumed-'+g['nonce'])).touch(exist_ok=False)
 out=root/('run-'+g['nonce']);out.mkdir();(out/'preflight.json').write_text(json.dumps(snapshots,indent=2));(out/'plan.json').write_bytes((root/g['plan_file']).read_bytes())
 # Docker cannot create a nested SDK mount target in a read-only source mount.
 (source/'service/pi/node_modules').mkdir(exist_ok=True)
 data=out/'data';data.mkdir();(data/'pg-data').mkdir(mode=0o777);(data/'pg-data').chmod(0o777);(data/'pi-data').mkdir()
 env=dict(os.environ,PYTHONPATH=str(source),GOMAXPROCS='1',G2_PROJECT=project,G2_ROOT=str(root),G2_DATA_ROOT=str(data),SOURCE_SHA=g['source_sha'],G2_NONCE=g['nonce'],G2_RUNTIME=str(runtime_root/'env'),G2_OUT=str(out),DEADLINE_EPOCH=str(g['deadline_epoch']),GENERATION_TIMEOUT=str(g['generation_timeout']),MAX_ATTEMPTS=str(g['max_attempts']),NODE_ROOT=str(pathlib.Path(assets['files']['node']['path']).parents[1]),PI_MODULES=assets['sdk']['path'],G2_API=assets['files']['api']['path'],G2_NETWORK=net['Name'])
 compose=['docker','compose','-p',project,'-f',str(source/'service/compose.vllm.yaml')]
 if g['mode']=='transformers':
  override={'services':{'model':{'image':'sha256:7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2','entrypoint':['python','/source/service/scripts/vllm-compat/native.py','--deadline',str(g['deadline_epoch']),'--receipt','/evidence/native-budget.json','--','python','-m','service.inference','--backend','transformers','--host','0.0.0.0','--port','8082','--generation-timeout',str(g['generation_timeout']),'--max-attempts',str(g['max_attempts']),'--deadline-epoch',str(g['deadline_epoch'])],'environment':{'PYTHONPATH':'/source:/deps','OMP_NUM_THREADS':'6'},'volumes':['/media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021/deps:/deps:ro']}}}
  (out/'fallback.json').write_text(json.dumps(override));compose+=['-f',str(out/'fallback.json')]
 watch=None;client=None;serial=0;failure=None;stop=out/'stop-watch'
 def call(args,key,check=True,timeout=60):
  start=time.time();r=subprocess.run(args,cwd=source,env=env,capture_output=True,text=True,timeout=timeout)
  (out/(key+'.json')).write_text(json.dumps({'command':args,'start':start,'end':time.time(),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
  if check and r.returncode:raise RuntimeError('command failed: '+key)
  return r
 try:
  watch_log=(out/'watch-stdout.log').open('w')
  watch=subprocess.Popen([sys.executable,str(here/'watch.py'),'--project',project,'--sha',g['source_sha'],'--nonce',g['nonce'],'--root',str(root),'--deadline',str(g['deadline_epoch']-15),'--out',str(out/'watch.jsonl'),'--ready',str(out/'watch-ready'),'--stop-file',str(stop),'--gpu'],stdout=watch_log,stderr=subprocess.STDOUT,env=env)
  until=min(g['deadline_epoch']-25,time.time()+5)
  while not (out/'watch-ready').exists() and time.time()<until and watch.poll() is None:time.sleep(.05)
  if not (out/'watch-ready').exists() or watch.poll() is not None:raise RuntimeError('independent watch unavailable')
  call([*compose,'config'],'compose-config')
  plan=json.loads((out/'plan.json').read_text());full=any(s['action'] in ('platform','sse_disconnect','restart') for s in plan['steps'])
  services=['pg','model','pi','api'] if full else ['model']
  call([*compose,'up','--pull','never','--no-build','-d',*services],'compose-up',timeout=min(120,max(1,g['deadline_epoch']-time.time()-25)))
  docker.discover(known);api_cid=next((cid for cid,row in known.items() if row['Config']['Labels'].get('com.docker.compose.service')=='api'),None)
  mapping=resolve(docker,list(known),g['network_id']);(out/'endpoint-map.json').write_text(json.dumps(mapping,indent=2))
  model_url='http://'+mapping['endpoints']['model']['ip']+':8082'
  api_url='' if not full else 'http://'+mapping['endpoints']['api']['ip']+':8080'
  while time.time()<g['deadline_epoch']-25:
   if watch.poll() is not None:raise RuntimeError('watch lost during startup')
   try:
    with urllib.request.urlopen(model_url+'/health',timeout=1) as r:h=json.load(r)
    if h['ready']:
     if full:
      with urllib.request.urlopen(api_url+'/health',timeout=1) as r:assert r.status==200
     (out/'ready.json').write_text(json.dumps(h));break
   except (OSError,ValueError):pass
   time.sleep(.2)
  else:raise RuntimeError('readiness deadline')
  args=[sys.executable,str(here/'client.py'),'--plan',str(out/'plan.json'),'--out',str(out/'client'),'--endpoints',str(out/'endpoint-map.json'),'--endpoints-sha256',sha(out/'endpoint-map.json'),'--deadline',str(g['deadline_epoch']-20),'--project',project,'--sha',g['source_sha'],'--nonce',g['nonce']]
  if api_cid:args+=['--api-cid',api_cid]
  with (out/'client.log').open('w') as log:
   client=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,cwd=source,env=env)
   while client.poll() is None:
    if time.time()>=g['deadline_epoch']-15 or watch.poll() is not None:raise RuntimeError('client deadline/watch lost')
    time.sleep(.05)
   if client.returncode:raise RuntimeError('matrix failed')
 except BaseException as e:failure=repr(e)
 finally:
  if client is not None and client.poll() is None:
   client.terminate()
   try:client.wait(timeout=2)
   except subprocess.TimeoutExpired:client.kill();client.wait(timeout=2)
  try:
   docker.discover(known)
   for cid,row in known.items():
    call(['docker','logs',cid],'logs-'+cid[:12],False,8)
    if row['Config']['Labels'].get('com.docker.compose.service')=='pg' and row['State']['Running']:
     for table in ['tasks','events','sessions']:
      call(['docker','exec',cid,'psql','-U','pan','-d','pan','-X','-At','-v','ON_ERROR_STOP=1','-c',"SELECT coalesce(json_agg(t),'[]') FROM "+table+' t;'],'pg-'+table,False,8)
     call(['docker','exec',cid,'du','-sb','/var/lib/postgresql/data'],'pg-disk',False,8)
  except Exception as e:failure=failure or repr(e)
  stop.touch()
  if watch is not None:
   try:watch.wait(timeout=30)
   except Exception as e:failure=failure or repr(e)
   if watch.poll()!=0:failure=failure or 'watch cleanup failed'
  refresh_error=None
  try:docker.discover(known)
  except Exception as e:refresh_error=repr(e)
  result=docker.cleanup(known)
  network_cleanup=None
  if result['success'] and not refresh_error:
   try:
    from endpoints import remove
    network_cleanup=remove(docker,g['network_id'])
   except Exception as e:refresh_error=repr(e)
  cleanup_success=result['success'] and not refresh_error
  value={'overall_success':not failure and cleanup_success,'cleanup_success':cleanup_success,'network_cleanup':network_cleanup,'failure':failure,'inventory_error':refresh_error,'client_exit':None if client is None else client.poll(),'watch_exit':None if watch is None else watch.poll(),**result}
  (out/'outcome.json').write_text(json.dumps(value,indent=2))
  if failure or refresh_error or not result['success']:raise RuntimeError('execution or cleanup failed/unknown')

def main():
 p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True);a=p.parse_args()
 try:g=validate(a.go,a.go_sha256)
 except Exception as e:print('GO rejected: '+str(e),file=sys.stderr);return 2
 try:execute(g,a.go,a.go_sha256)
 except Exception as e:print('Execution failed: '+repr(e),file=sys.stderr);return 3
 return 0
if __name__=='__main__':raise SystemExit(main())
