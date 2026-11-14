PROFILES={'deadline': {'nonce': 'pi24-b-nov14-deadline01', 'plan_sha256': 'bb123d1270075df14f36efe44528075f25a6e79a8646ab65d980e95c6802095d'}, 'recovery': {'nonce': 'pi24-b-nov14-recovery01', 'plan_sha256': '6740c2f8a53e69f4dba903fdda050624a44bd98b71b1d680d22ee636d7ad7469'}, 'fallback': {'nonce': 'pi24-b-nov14-fallback01', 'plan_sha256': '27ca9074a45acf747b0cf859212901d4f4f52a7d6eafad6153352d465319e8f6'}}
BINDINGS={'source/service/scripts/vllm-serve/launch.py': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/source/service/scripts/vllm-serve/launch.py', 'sha256': 'd5e07f695b3680a7239d0dcc30a1735120148c2fc57ef4a42b3ce7ecddffec7d', 'bytes': 14392}, 'source/service/scripts/vllm-serve/watch.py': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/source/service/scripts/vllm-serve/watch.py', 'sha256': 'd8a069ac818bf41149853f86a2b2031656abfe82d4919b825eaa656a3bfb36f4', 'bytes': 3261}, 'source/service/scripts/vllm-compat/driver.py': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/source/service/scripts/vllm-compat/driver.py', 'sha256': '2f8780f46df52208050d359889f58939a215b61cd6c37d5dc67056009484b607', 'bytes': 4063}, 'source/service/scripts/vllm-compat/native.py': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/source/service/scripts/vllm-compat/native.py', 'sha256': '691f5f862d0191e51ff7062e07da0bd999dc983a0a334e0012a7458e1e437062', 'bytes': 1197}, 'source/service/compose.vllm.yaml': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/source/service/compose.vllm.yaml', 'sha256': '1e7de456ab4c8e278775bacef257be1be402b4b605efe2a8015382b27cd4d799', 'bytes': 4660}, 'asset-inventory.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/asset-inventory.json', 'sha256': '7a9a7e728bbf92411371ac497a896c47ce5bee1f86a9cfea6fbd9a690a78cd54', 'bytes': 1416}, 'sdk-files.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/sdk-files.json', 'sha256': 'fac12b65a96b8a7614bc17376b92e03de8a100060978758c65d2134c8b6cd7d3', 'bytes': 2265484}, 'plan-normal.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/plan-normal.json', 'sha256': 'deb0910ecccedafec8c535dec1d877de560e2cb1cc09800c4e0f4bdf274ea059', 'bytes': 2185}, 'plan-deadline.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/plan-deadline.json', 'sha256': 'bb123d1270075df14f36efe44528075f25a6e79a8646ab65d980e95c6802095d', 'bytes': 331}, 'plan-recovery.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/plan-recovery.json', 'sha256': '6740c2f8a53e69f4dba903fdda050624a44bd98b71b1d680d22ee636d7ad7469', 'bytes': 333}, 'plan-fallback.json': {'path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/plan-fallback.json', 'sha256': '27ca9074a45acf747b0cf859212901d4f4f52a7d6eafad6153352d465319e8f6', 'bytes': 323}}
QUERY={'real_binary': '/usr/bin/nvidia-smi', 'real_resolved': '/usr/bin/nvidia-smi', 'real_binary_sha256': '2da08a20450594c3cdf1e677c1d2e46101a0b2d45ee5d3d6b67b87ae50522af2', 'wrapper_path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/nvml-normal02-bin/nvidia-smi', 'wrapper_sha256': '917f97350b53c3b2ddcbd0f105900b32a6b786434ce7ca3c971a8a43c6d2dc4e', 'wrapper_bytes': 1644, 'original_PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin', 'effective_PATH': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/nvml-normal02-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin', 'log_path': '/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/NVML-QUERY-RAW-NOV14-V2.jsonl', 'log_exists': False}

import pathlib,os,json,subprocess,time,hashlib,traceback
ROOT=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');SOURCE='9ea36d3221d024a6d8330322d330809fa9e283a6';PHASE='82f15dcf6523c8bbea36bd79741fc8c9745fd838024004ad592979ad2b6830ec';PROJECT='pi-vllm24-b'
r={'schema':'pi24-remaining-profiles-CPUprep/v1','start':time.time(),'commands':[],'failure':None,'NVML_queries':0,'model_calls':0,'networks':{},'profiles':PROFILES}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def call(args,cwd=None):
 s=time.time();p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=5);r['commands'].append({'command':args,'start':s,'end':time.time(),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert p.returncode==0,repr(args);return p.stdout.strip()
try:
 assert pathlib.Path.cwd()==ROOT and os.environ['CUDA_VISIBLE_DEVICES']=='0' and sorted(os.sched_getaffinity(0))==[0,1]
 r['source_sha']=call(['git','rev-parse','HEAD'],ROOT/'source');assert r['source_sha']==SOURCE;assert not call(['git','status','--porcelain'],ROOT/'source');r['source_clean']=True
 assert not call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT]);assert not call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT])
 r['markers']={}
 for nonce in ['pi24-b-nov14-normal02']+[v['nonce'] for v in PROFILES.values()]:
  p=ROOT/('consumed-'+nonce)
  try:st=os.lstat(p);r['markers'][nonce]={'exists':True,'mode':st.st_mode,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
  except FileNotFoundError:r['markers'][nonce]={'exists':False}
  assert r['markers'][nonce]['exists']==(nonce=='pi24-b-nov14-normal02')
 r['bindings']={}
 allbind={**BINDINGS,'PHASE-CONTRACT.v3.json':{'sha256':PHASE},'gpu_entry_nov14_r3.py':{'sha256':'95af5de69016a7cf027d390395f7c1fefd0fbc96c053aaa000ef452bdb6e497a'},'entry_nov14_r3.sh':{'sha256':'611e0cc4fbbfaaf618c7caf62c044d9a9966bd24ed2c29e632c11fd7fadee0f9'},'nvml-normal02-bin/nvidia-smi':{'sha256':'917f97350b53c3b2ddcbd0f105900b32a6b786434ce7ca3c971a8a43c6d2dc4e'}}
 for name,ex in allbind.items():
  p=ROOT/name;h=sha(p);assert h==ex['sha256'],name;r['bindings'][name]={'path':str(p),'sha256':h,'bytes':p.stat().st_size}
 assert sha('/usr/bin/nvidia-smi')=='2da08a20450594c3cdf1e677c1d2e46101a0b2d45ee5d3d6b67b87ae50522af2';r['query_binding']=QUERY
 log=pathlib.Path(QUERY['log_path']);r['query_log_preserved_prefix']={'path':str(log),'sha256':sha(log),'bytes':log.stat().st_size,'method':'full existing bytes hashed; no truncate/query invoked'}
 r['cpu_probe']=json.loads(call(['sh',str(ROOT/'entry_nov14_r3.sh'),'--cpu-probe']));assert r['cpu_probe']['cpu_only'] and not r['cpu_probe']['model_started']
 labels={'com.docker.compose.project':PROJECT,'execution-sha':SOURCE,'workorder':'24','pi24.phase-contract-sha256':PHASE}
 r['model_transports']={}
 for profile,v in PROFILES.items():
  assert sha(ROOT/('plan-'+profile+'.json'))==v['plan_sha256']
  args=['docker','network','create','--internal','--ipv6=false']
  for k,val in {**labels,'pi24.nonce':v['nonce']}.items():args+=['--label',k+'='+val]
  nid=call(args+[PROJECT+'-'+v['nonce']]);net=json.loads(call(['docker','network','inspect',nid]))[0];r['networks'][profile]=net
  assert net['Id']==nid and net['Internal'] is True and net['EnableIPv6'] is False and not net['Containers'] and all(net['Labels'].get(k)==val for k,val in {**labels,'pi24.nonce':v['nonce']}.items())
  r['model_transports'][profile]={'command':['sh',str(ROOT/'entry_nov14_r3.sh'),'--go',str(ROOT/('B-GPU-'+profile.upper()+'-NOV14-GO01.json')),'--go-sha256','<Master-exact-GO-hash>'],'PATH':QUERY['effective_PATH'],'cwd':str(ROOT),'CUDA_VISIBLE_DEVICES':'0','host_affinity':[0,1],'network_id':nid,'nonce':v['nonce'],'plan_sha256':v['plan_sha256']}
 assert len(set(x['Id'] for x in r['networks'].values()))==3
 assert not call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT]);r['retained_network_ids']=call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT]).splitlines();assert set(r['retained_network_ids'])==set(x['Id'] for x in r['networks'].values())
 total=allocated=files=0;errors=[];excluded=[]
 def onerror(e):errors.append({'path':e.filename,'error':str(e)})
 for root,dirs,names in os.walk(ROOT,onerror=onerror,followlinks=False):
  for d in list(dirs):
   if d=='pg-data':excluded.append(str(pathlib.Path(root)/d));dirs.remove(d)
  for name in names:
   p=pathlib.Path(root)/name
   try:
    st=p.lstat();total+=st.st_size;allocated+=st.st_blocks*512;files+=1
   except OSError as e:onerror(e)
 r['disk_snapshot']={'scope':'B own readable tree regular/symlink sizes; physical pg-data explicitly excluded, not zero','apparent_bytes':total,'allocated_bytes':allocated,'files':files,'errors':errors,'excluded_physical_PG':excluded,'normal02_last_running_PG_du_bytes':48273926,'normal02_PG_du_source':'run-pi24-b-nov14-normal02/pg-disk.json exit0 at1794624953.007008','prior_R_full_BplusR_apparent_bytes':486552798,'prior_R_full_BplusR_allocated_bytes':500457472,'fresh_full_PG_bytes':'unknown; prior original and normal runtime actual snapshots retained, no container permitted here'}
 r['free_bytes']=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize;assert r['free_bytes']>=21474836480
except BaseException as e:r['failure']=repr(e);r['traceback']=traceback.format_exc()
finally:
 r['end']=time.time();r['elapsed_s']=r['end']-r['start'];r['success']=r['failure'] is None;r['compute_released']=True
 out=ROOT/'REMAINING-PROFILES-CPU-PREP01.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if not r['success']:raise SystemExit(3)
