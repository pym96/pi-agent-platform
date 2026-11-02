import subprocess,json,os,hashlib,time,shutil,socket
from pathlib import Path
root=Path.cwd();source=root/'source';out=root/'evidence/20261102-prep';sha='444096edccca28155ad60d9c17e2e8d2b7f5fdda';project='pi-e2e12-1031-b';name=project+'-client-probe-20261102'
def call(args,key,check=True,timeout=30):
 s=time.time_ns();r=subprocess.run(args,text=True,capture_output=True,timeout=timeout,cwd=source)
 value={'command':args,'started_ns':s,'ended_ns':time.time_ns(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr};(out/(key+'.json')).write_text(json.dumps(value,indent=2))
 if check and r.returncode:raise RuntimeError(key+': '+r.stderr)
 return value
assert os.environ['CUDA_VISIBLE_DEVICES']=='0' and str(root)=='/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder'
assert call(['git','rev-parse','HEAD'],'source-head')['stdout'].strip()==sha
assert not call(['git','status','--porcelain'],'source-status')['stdout'].strip()
for key,p in [('node','/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3'),('sdk','/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules')]:assert Path(p).is_dir(),key
node='/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3/bin/node';sdk=Path('/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules')
call([node,'--version'],'node-version');package=sdk/'@earendil-works/pi-coding-agent/package.json';assert json.loads(package.read_text())['version']=='1.3.0'
config_path=source/'service/scripts/pi-qwen-e2e/stage-b.json';raw=config_path.read_bytes();base=json.loads(raw);assert hashlib.sha256(raw).hexdigest()=='12253933a8b29d243d22c838789f8b80ba9f02cc45ed061c81f0e4911b40d991'
derived=dict(base,container=project+'-model-1',port=18181);guard=out/'derived-guard.json';guard.write_text(json.dumps(derived,indent=2)+'\n')
(out/'config-binding.json').write_text(json.dumps({'source_sha':sha,'base_config_sha256':hashlib.sha256(raw).hexdigest(),'derived_guard_sha256':hashlib.sha256(guard.read_bytes()).hexdigest(),'added_fields':{k:derived[k] for k in ['container','port']},'remaining_equal':{k:v for k,v in derived.items() if k not in ['container','port']}==base,'sdk_package_sha256':hashlib.sha256(package.read_bytes()).hexdigest()},indent=2))
images=[base['image'],'python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1','postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24','nginx@sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284']
call(['docker','image','inspect',*images],'image-identities')
ports=call(['ss','-ltn'],'ports')['stdout'];assert not any(':'+str(p)+' ' in ports for p in [18181,18182,18183,18201,18202,18203,18204,18205,18206,18207,18208,18209])
for port in [18181,18182,18183]:
 with socket.socket() as s:s.bind(('127.0.0.1',port))
assert shutil.disk_usage(root).free>=20*2**30
available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;assert available>=40*2**30
paths=['/media/usv012/pjx/pi-agent-platform/experiments/15-nginx-entry-20261025/regulator/deps','/media/usv012/pjx/pi-agent-platform/experiments/15-nginx-entry-20261025/builder/deps','/media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021/deps']
(out/'environment.json').write_text(json.dumps({'cwd':str(root),'uid':os.getuid(),'gid':os.getgid(),'available_memory_bytes':available,'disk_free':shutil.disk_usage(root).free,'new_root_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),'host_commands':{x:shutil.which(x) for x in ['go','gcc','node','psql','initdb','pg_ctl']},'deps_paths':{p:Path(p).is_dir() for p in paths}},indent=2))
call(['python3','-c',"import importlib.util,json;print(json.dumps({x:importlib.util.find_spec(x) is not None for x in ['aiohttp','psycopg']}))"],'host-python-deps')
probe=out/'client-permission-probe';probe.mkdir()
code="import os,json,hashlib;from pathlib import Path;p=Path('/evidence/client-permission-probe/ledger.jsonl');r={'uid':os.getuid(),'gid':os.getgid(),'config_sha256':hashlib.sha256(Path('/source/service/scripts/pi-qwen-e2e/stage-b.json').read_bytes()).hexdigest()};f=p.open('x');f.write(json.dumps(r)+'\\n');f.flush();os.fsync(f.fileno());f.close();assert r['uid']==r['gid']==p.stat().st_uid==p.stat().st_gid==1001;print(json.dumps(r))"
args=['docker','create','--pull','never','--name',name,'--label','com.docker.compose.project='+project,'--label','workorder=12','--label','execution-sha='+sha,'--runtime','runc','--network','host','--user','1001:1001','--read-only','--tmpfs','/tmp:size=256m','--cap-drop','ALL','--security-opt','no-new-privileges:true','--cpus','2','--memory','5g','--memory-swap','5g','-v',str(source)+':/source:ro','-v',str(out)+':/evidence','-e','PYTHONDONTWRITEBYTECODE=1','-e','CUDA_VISIBLE_DEVICES=0','-w','/source','--entrypoint','python',images[1],'-c',code]
created=False
try:
 call(args,'probe-create');created=True;inspect=call(['docker','inspect',name],'probe-inspect-before');c=json.loads(inspect['stdout'])[0];h=c['HostConfig'];assert h['NanoCpus']==2*10**9 and h['Memory']==5*2**30 and h['ReadonlyRootfs'] and c['Config']['User']=='1001:1001' and h['Runtime']=='runc';assert not h.get('Devices')
 call(['docker','start','-a',name],'probe-run');after=call(['docker','inspect',name],'probe-inspect-after');state=json.loads(after['stdout'])[0]['State'];assert not state['Running'] and state['ExitCode']==0
finally:
 if created:call(['docker','stop','-t','3',name],'probe-stop',False);call(['docker','rm',name],'probe-remove',False)
print(json.dumps({'stage_a_probe_passed':True,'source_sha':sha,'config_sha256':hashlib.sha256(raw).hexdigest(),'derived_guard_sha256':hashlib.sha256(guard.read_bytes()).hexdigest(),'available_memory_bytes':available,'new_root_bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file())}))
