import pathlib,json,hashlib,base64,subprocess,time,datetime,math
state=pathlib.Path.home()/'.local/state/pi-agent-platform/vllm24-builder-20261114'
old=pathlib.Path.home()/'.local/state/pi-agent-platform/vllm24-builder-20261111'
files={n:base64.b64encode((state/n).read_bytes()).decode() for n in ['source-nov14-9ea.bundle','PHASE-CONTRACT.v3.json','gpu_entry_nov14_r3.py','entry_nov14_r3.sh']}
plans={n:hashlib.sha256((old/n).read_bytes()).hexdigest() for n in ['plan-normal.json','plan-deadline.json','plan-recovery.json','plan-fallback.json']}
remote=r'''
import pathlib,json,hashlib,base64,subprocess,sys,os,time,traceback,resource
ROOT=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder')
SOURCE='9ea36d3221d024a6d8330322d330809fa9e283a6'
PROJECT='pi-vllm24-b';NONCE='pi24-b-nov14-normal01'
PHASE='82f15dcf6523c8bbea36bd79741fc8c9745fd838024004ad592979ad2b6830ec'
r={'schema':'pi24-nov14-B-CPU-preparation/v1','start':time.time(),'GPU_started':False,'model_calls':0,'records':[],'failure':None}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def call(args,check=True,timeout=8,cwd=None):
 start=time.time();x=subprocess.run(args,capture_output=True,text=True,timeout=timeout,cwd=cwd)
 r['records'].append({'command':args,'start':start,'end':time.time(),'exit':x.returncode,'stdout':x.stdout,'stderr':x.stderr})
 if check and x.returncode:raise RuntimeError('failed '+repr(args))
 return x.stdout.strip()
try:
 assert pathlib.Path.cwd()==ROOT and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
 r['affinity']=sorted(os.sched_getaffinity(0));assert r['affinity']==[0,1]
 assert r['start']<1794624900
 src=ROOT/'source';r['prior_source']=call(['git','rev-parse','HEAD'],cwd=src)
 assert r['prior_source']=='471a317ef687a168306608b1bece931f9b3a2b63'
 assert not call(['git','status','--porcelain'],cwd=src)
 assert not call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT])
 assert not call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT])
 r['staged']={}
 for name,data in FILES.items():
  p=ROOT/name;b=base64.b64decode(data)
  if p.exists() or p.is_symlink():assert not p.is_symlink() and p.read_bytes()==b
  else:p.write_bytes(b)
  if name.endswith('.sh'):p.chmod(0o755)
  r['staged'][name]={'sha256':sha(p),'bytes':len(b)}
 assert sha(ROOT/'PHASE-CONTRACT.v3.json')==PHASE
 assert sha(ROOT/'gpu_entry_nov14_r3.py')=='95af5de69016a7cf027d390395f7c1fefd0fbc96c053aaa000ef452bdb6e497a'
 call(['git','bundle','verify',str(ROOT/'source-nov14-9ea.bundle')],cwd=src)
 call(['git','fetch',str(ROOT/'source-nov14-9ea.bundle'),'workorder/24-candidate'],cwd=src)
 call(['git','merge','--ff-only',SOURCE],cwd=src)
 r['source_sha']=call(['git','rev-parse','HEAD'],cwd=src);assert r['source_sha']==SOURCE
 assert not call(['git','status','--porcelain'],cwd=src)
 r['source_clean']=True;r['bindings']={}
 expected={'source/service/scripts/vllm-serve/launch.py':'d5e07f695b3680a7239d0dcc30a1735120148c2fc57ef4a42b3ce7ecddffec7d','source/service/scripts/vllm-serve/watch.py':'d8a069ac818bf41149853f86a2b2031656abfe82d4919b825eaa656a3bfb36f4','source/service/scripts/vllm-compat/driver.py':'2f8780f46df52208050d359889f58939a215b61cd6c37d5dc67056009484b607','source/service/scripts/vllm-compat/native.py':'691f5f862d0191e51ff7062e07da0bd999dc983a0a334e0012a7458e1e437062','source/service/compose.vllm.yaml':'1e7de456ab4c8e278775bacef257be1be402b4b605efe2a8015382b27cd4d799','asset-inventory.json':'7a9a7e728bbf92411371ac497a896c47ce5bee1f86a9cfea6fbd9a690a78cd54','sdk-files.json':'fac12b65a96b8a7614bc17376b92e03de8a100060978758c65d2134c8b6cd7d3',**PLANS}
 for name,digest in expected.items():
  f=ROOT/name;actual=sha(f);assert actual==digest,(name,actual,digest)
  r['bindings'][name]={'path':str(f),'sha256':actual,'bytes':f.stat().st_size}
 r['asset_inventory']=json.loads((ROOT/'asset-inventory.json').read_text())
 # This is an OS-only affinity/RSS probe: --cpu-probe returns before launcher import.
 probe=call(['sh',str(ROOT/'entry_nov14_r3.sh'),'--cpu-probe'])
 r['cpu_probe']=json.loads(probe);assert r['cpu_probe']['cpu_only'] and not r['cpu_probe']['model_started']
 assert r['cpu_probe']['sample']['affinity']==[0,1] and r['cpu_probe']['sample']['rss_bytes']<1073741824
 name=PROJECT+'-'+NONCE
 labels={'com.docker.compose.project':PROJECT,'execution-sha':SOURCE,'pi24.nonce':NONCE,'workorder':'24','pi24.phase-contract-sha256':PHASE}
 args=['docker','network','create','--internal','--ipv6=false']
 for key,value in labels.items():args+=['--label',key+'='+value]
 nid=call(args+[name]);r['network_id']=nid
 r['network']=json.loads(call(['docker','network','inspect',nid]))[0]
 net=r['network'];assert net['Id']==nid and net['Internal'] is True and net['EnableIPv6'] is False and not net['Containers']
 assert all(net['Labels'].get(k)==v for k,v in labels.items())
 r['containers']=call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT]).splitlines();assert not r['containers']
 r['networks']=call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT]).splitlines();assert r['networks']==[nid]
 r['free_bytes']=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize;assert r['free_bytes']>=21474836480
 r['new_staged_bytes']=sum(x['bytes'] for x in r['staged'].values())
 r['disk_basis']='R actual complete B+R apparent486552798B/allocated500457472B snapshot plus this new staged/sourceGit/raw delta; no claim full current exact PG recount'
 r['shallow_root_files']=[{'name':x.name,'bytes':x.stat().st_size,'blocks':x.stat().st_blocks} for x in ROOT.iterdir() if x.is_file() and not x.is_symlink()]
 r['host_maxrss_KiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 r['other_role_network']='R c61d7fd94ae102b909dfcf55d2cece73f97a6ec379f334eaef1b7d39333a37cd untouched'
except BaseException as e:
 r['failure']=repr(e);r['traceback']=traceback.format_exc()
finally:
 r['end']=time.time();r['elapsed_s']=r['end']-r['start'];r['retained_network_explicit']=r.get('network_id');r['release_compute']=True
 r['success']=r['failure'] is None
 target=ROOT/'CPU-PREP-NOV14-02.json'
 assert not target.exists()
 target.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r))
if not r['success']:raise SystemExit(3)
'''
script='FILES='+repr(files)+'\nPLANS='+repr(plans)+'\n'+remote
(state/'CPU-PREP02-remote-script.py').write_text(script)
cmd=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','wt@58.199.171.85','cd /media/usv012/pjx && export CUDA_VISIBLE_DEVICES=0 && cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder && exec taskset -c 0,1 python3 -']
start=time.time();assert start<datetime.datetime.fromisoformat('2026-11-14T02:53:00+00:00').timestamp()
r=subprocess.run(cmd,input=script,capture_output=True,text=True,timeout=115)
receipt={'command':cmd,'start':start,'end':time.time(),'elapsed_s':time.time()-start,'script_sha256':hashlib.sha256(script.encode()).hexdigest(),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'all_SSH_SCP_ended':True}
(state/'CPU-PREP02-SSH.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'exit':r.returncode,'elapsed_s':receipt['elapsed_s'],'stderr':r.stderr,'stdout':r.stdout},ensure_ascii=False))
raise SystemExit(r.returncode)
