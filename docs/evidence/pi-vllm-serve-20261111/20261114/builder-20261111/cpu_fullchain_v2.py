import os,sys,time,json,pathlib,subprocess,urllib.request,traceback
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');source=root/'source';sys.path.insert(0,str(source/'service/scripts/vllm-serve'));from owned import OwnedDocker
from endpoints import prepare,resolve,remove
assert pathlib.Path.cwd()==root and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
nonce=sys.argv[1];out=root/nonce;out.mkdir();data=out/'data';data.mkdir();(data/'pg-data').mkdir(mode=0o777);(data/'pg-data').chmod(0o777);(data/'pi-data').mkdir();(out/'empty-model').mkdir()
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip();deadline=time.time()+180;project='pi-vllm24-b';assets=json.loads((root/'asset-inventory.json').read_text())
env=dict(os.environ,GOMAXPROCS='1',PYTHONPATH=str(source),G2_PROJECT=project,G2_ROOT=str(root),G2_DATA_ROOT=str(data),SOURCE_SHA=sha,G2_NONCE=nonce,G2_RUNTIME='/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111/builder/env',G2_OUT=str(out),DEADLINE_EPOCH=str(deadline),MAX_ATTEMPTS='32',MODEL_PORT='18481',PI_PORT='18482',API_PORT='18483',NODE_ROOT='/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3',PI_MODULES=assets['sdk']['path'],G2_API=assets['files']['api']['path'])
override={'services':{'model':{'runtime':'runc','entrypoint':['/venv/bin/python','/fixture.py'],'environment':{'NVIDIA_VISIBLE_DEVICES':'void','NVIDIA_DRIVER_CAPABILITIES':''},'volumes':[str(root/'cpu_fixture.py')+':/fixture.py:ro',str(out/'empty-model')+':/model:ro'],'cpus':2,'mem_limit':'2g','memswap_limit':'2g'}}}
(out/'override.json').write_text(json.dumps(override));compose=['docker','compose','-p',project,'-f',str(source/'service/compose.vllm.yaml'),'-f',str(out/'override.json')]
owner=OwnedDocker(project,sha,nonce);known={};stop=out/'stop-watch';failure=None;watch=None;network_id=None
plan=json.loads((root/'plan-normal.json').read_text());plan['kind']='synthetic-CPU-no-model';plan['steps']=[{**s,**({'session':'cpu-'+s['session']} if 'session' in s else {})} for s in plan['steps']];(out/'plan.json').write_text(json.dumps(plan,indent=2))
def call(args,key,timeout=60,check=True):
 start=time.time();r=subprocess.run(args,cwd=source,env=env,capture_output=True,text=True,timeout=timeout);(out/(key+'.json')).write_text(json.dumps({'command':args,'start':start,'end':time.time(),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
 if check and r.returncode:raise RuntimeError('failed '+key)
 return r
try:
 assert not owner.discover(known),'preexisting owned project'
 prepared=prepare(owner);network_id=prepared['network_id'];env['G2_NETWORK']=prepared['network_name'];(out/'network-prepare.json').write_text(json.dumps(prepared,indent=2))
 log=(out/'watch-stdout.log').open('w');watch=subprocess.Popen([sys.executable,str(source/'service/scripts/vllm-serve/watch.py'),'--project',project,'--sha',sha,'--nonce',nonce,'--root',str(root),'--deadline',str(deadline-10),'--out',str(out/'watch.jsonl'),'--ready',str(out/'watch-ready'),'--stop-file',str(stop)],stdout=log,stderr=subprocess.STDOUT,env=env)
 while not (out/'watch-ready').exists():
  assert watch.poll() is None
  if time.time()>deadline-30:raise TimeoutError('watch ready')
  time.sleep(.05)
 call([*compose,'config'],'config');call([*compose,'up','--pull','never','--no-build','-d','pg','model','pi','api'],'up')
 owner.discover(known);model=next(cid for cid,row in known.items() if row['Config']['Labels'].get('com.docker.compose.service')=='model');api=next(cid for cid,row in known.items() if row['Config']['Labels'].get('com.docker.compose.service')=='api')
 call(['docker','inspect',model],'cpu-model-inspect');call(['docker','exec',model,'/venv/bin/python','-c','import glob,json; print(json.dumps(glob.glob("/dev/nvidia*")))'],'cpu-no-devices')
 mapping=resolve(owner,list(known),network_id);(out/'endpoint-map.json').write_text(json.dumps(mapping,indent=2))
 model_url='http://'+mapping['endpoints']['model']['ip']+':8082';api_url='http://'+mapping['endpoints']['api']['ip']+':8080'
 while time.time()<deadline-30:
  try:
   for base in [model_url,api_url]:
    with urllib.request.urlopen(base+'/health',timeout=1) as r:assert r.status==200
   break
  except (OSError,ValueError):time.sleep(.1)
 else:raise TimeoutError('CPU fullchain readiness')
 call([sys.executable,str(source/'service/scripts/vllm-serve/client.py'),'--plan',str(out/'plan.json'),'--out',str(out/'client'),'--endpoints',str(out/'endpoint-map.json'),'--endpoints-sha256',__import__('hashlib').sha256((out/'endpoint-map.json').read_bytes()).hexdigest(),'--deadline',str(deadline-20),'--project',project,'--sha',sha,'--nonce',nonce,'--api-cid',api],'client',timeout=120)
except BaseException as e:failure=repr(e);(out/'failure.txt').write_text(traceback.format_exc())
finally:
 try:
  owner.discover(known)
  for cid,row in known.items():
   call(['docker','logs',cid],'logs-'+cid[:12],check=False,timeout=8)
   if row['Config']['Labels'].get('com.docker.compose.service')=='pg' and row['State']['Running']:
    for table in ['tasks','events','sessions']:
     call(['docker','exec',cid,'psql','-U','pan','-d','pan','-X','-At','-c',"SELECT coalesce(json_agg(t),'[]') FROM "+table+' t;'],'pg-'+table,check=False,timeout=8)
    call(['docker','exec',cid,'du','-sb','/var/lib/postgresql/data'],'pg-disk',check=False,timeout=8)
 except Exception as e:failure=failure or repr(e)
 stop.touch()
 if watch is not None:
  try:watch.wait(timeout=30)
  except Exception as e:failure=failure or repr(e)
 refresh=None
 try:owner.discover(known)
 except Exception as e:refresh=repr(e)
 cleanup=owner.cleanup(known)
 network_cleanup=None
 if cleanup['success'] and network_id:
  try:network_cleanup=remove(owner,network_id)
  except Exception as e:refresh=repr(e)
 (out/'outcome.json').write_text(json.dumps({'kind':'synthetic-CPU-no-model','source_sha':sha,'overall_success':not failure and not refresh and cleanup['success'],'cleanup_success':not refresh and cleanup['success'],'network_cleanup':network_cleanup,'failure':failure,'refresh_error':refresh,'watch_exit':None if watch is None else watch.poll(),**cleanup},indent=2))
 print(json.dumps({'out':str(out),'failure':failure,'cleanup':cleanup['success']}))
 if failure or refresh or not cleanup['success']:raise SystemExit(1)
