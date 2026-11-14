from pathlib import Path
import subprocess,time,json,hashlib,base64
s=Path.home()/'.local/state/pi-agent-platform/vllm24-builder-20261114'
script=r'''
import pathlib,subprocess,time,os,json,hashlib,tarfile,base64
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');assert pathlib.Path.cwd()==root
os.environ['PATH']=str(root/'nvml-normal02-bin')+':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
r={'schema':'pi24-deadline01-closeout/v1','start':time.time(),'commands':[]}
def call(args):
 start=time.time();p=subprocess.run(args,capture_output=True,text=True,timeout=5);r['commands'].append({'command':args,'start':start,'end':time.time(),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});return p
r['B_containers']=call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project=pi-vllm24-b']).stdout.splitlines()
r['B_networks']=call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project=pi-vllm24-b']).stdout.splitlines()
call(['nvidia-smi','-i','0','--query-gpu=uuid','--format=csv,noheader']);call(['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'])
r['retained_network_inspects']=[json.loads(call(['docker','network','inspect',n]).stdout)[0] for n in r['B_networks']]
r['query_prefix']={'bytes':30511,'sha256':hashlib.sha256((root/'NVML-QUERY-RAW-NOV14-V2.jsonl').read_bytes()[:30511]).hexdigest()}
r['nonce_consumed']=(root/'consumed-pi24-b-nov14-deadline01').exists()
for name in ['run-pi24-b-nov14-deadline01/outcome.json','outer-pi24-b-nov14-deadline01/receipt.json']:
 p=root/name;r[name]=json.loads(p.read_text()) if p.exists() else None
r['free_bytes']=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize;r['end']=time.time();(root/'DEADLINE01-NOV14-CLOSEOUT.json').write_text(json.dumps(r,indent=2)+'\n')
names=['run-pi24-b-nov14-deadline01','outer-pi24-b-nov14-deadline01','NVML-QUERY-RAW-NOV14-V2.jsonl','DEADLINE01-NOV14-CLOSEOUT.json','B-GPU-DEADLINE-NOV14-GO01.json','PHASE-CONTRACT.v3.json','gpu_entry_nov14_r3.py','entry_nov14_r3.sh','nvml-normal02-bin/nvidia-smi','REMAINING-PROFILES-CPU-PREP01.json']
def selected(name):return '/data/pg-data' not in name
rows=[]
for name in names:
 p=root/name
 if not p.exists():continue
 files=[p] if p.is_file() else list(p.rglob('*'))
 for f in files:
  rel=str(f.relative_to(root))
  if not selected(rel) or not f.is_file() or f.is_symlink():continue
  rows.append({'path':rel,'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
manifest=root/'DEADLINE01-NOV14-MANIFEST.json';manifest.write_text(json.dumps(rows,indent=2)+'\n');names.append(manifest.name)
archive=root/'deadline01-nov14-raw.tgz'
with tarfile.open(archive,'w:gz') as tar:
 for name in names:
  p=root/name
  if p.exists():tar.add(p,arcname=name,filter=lambda item:item if selected(item.name) else None)
data=archive.read_bytes();print(json.dumps({'archive_sha256':hashlib.sha256(data).hexdigest(),'archive_bytes':len(data),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'manifest_files':len(rows),'closeout':r,'archive_base64':base64.b64encode(data).decode()}))
'''
cmd=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','ConnectTimeout=10','wt@58.199.171.85','cd /media/usv012/pjx && export CUDA_VISIBLE_DEVICES=0 && cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder && exec taskset -c 0,1 python3 -']
start=time.time();p=subprocess.run(cmd,input=script,capture_output=True,text=True,timeout=50);r={'start':start,'end':time.time(),'exit':p.returncode,'stderr':p.stderr,'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'all_SSH_SCP_ended':True}
if p.returncode:r['stdout']=p.stdout
else:
 x=json.loads(p.stdout);data=base64.b64decode(x.pop('archive_base64'));assert hashlib.sha256(data).hexdigest()==x['archive_sha256'];(s/'deadline01-nov14-raw.tgz').write_bytes(data);r['result']=x
(s/'DEADLINE01-RAW-COLLECTION-SSH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='result'},ensure_ascii=False));print(json.dumps({k:v for k,v in r.get('result',{}).items() if k!='closeout'}));raise SystemExit(p.returncode)
