from pathlib import Path
import base64,subprocess,time,json,hashlib,datetime
s=Path.home()/'.local/state/pi-agent-platform/vllm24-builder-20261114';wrapper=(s/'nvidia-smi-raw-wrapper-v2.py').read_bytes();expected=json.loads((s/'CPU-PREP03-HANDOFF-RELEASE.v1.json').read_text())['bindings']
script='WRAPPER='+repr(base64.b64encode(wrapper).decode())+'\nBINDINGS='+repr(expected)+'\n'+r'''
import pathlib,base64,subprocess,time,os,json,hashlib,traceback
ROOT=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder');SOURCE='9ea36d3221d024a6d8330322d330809fa9e283a6';PHASE='82f15dcf6523c8bbea36bd79741fc8c9745fd838024004ad592979ad2b6830ec';OLD='pi24-b-nov14-normal01';NEW='pi24-b-nov14-normal02';PROJECT='pi-vllm24-b';OLDNET='ebbd890f95f601066d7dbcf66d2189f574f5cbb3e49e7482c0dac1decb213486'
r={'schema':'pi24-normal02-CPUfreeze-receipt/v1','start':time.time(),'records':[],'failure':None,'model_calls':0,'NVML_queries':0}
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def call(args,timeout=5,cwd=None):
 start=time.time();p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,cwd=cwd);r['records'].append({'command':args,'start':start,'end':time.time(),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 if p.returncode:raise RuntimeError('commandfailed '+repr(args))
 return p.stdout.strip()
try:
 assert pathlib.Path.cwd()==ROOT and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
 r['affinity']=sorted(os.sched_getaffinity(0));assert r['affinity']==[0,1]
 src=ROOT/'source';r['source_sha']=call(['git','rev-parse','HEAD'],cwd=src);assert r['source_sha']==SOURCE
 assert not call(['git','status','--porcelain'],cwd=src);r['source_clean']=True
 r['markers']={}
 for nonce in [OLD,NEW]:
  marker=ROOT/('consumed-'+nonce)
  try:os.lstat(marker)
  except FileNotFoundError:r['markers'][str(marker)]={'exists':False,'method':'actual os.lstat FileNotFoundError'}
  else:raise RuntimeError('unexpected consumedmarker '+str(marker))
 r['bindings']={}
 for name,expected in BINDINGS.items():
  p=ROOT/name;actual=sha(p);assert actual==expected['sha256'],name;r['bindings'][name]={'path':str(p),'sha256':actual,'bytes':p.stat().st_size}
 for name,h in [('PHASE-CONTRACT.v3.json',PHASE),('gpu_entry_nov14_r3.py','95af5de69016a7cf027d390395f7c1fefd0fbc96c053aaa000ef452bdb6e497a'),('entry_nov14_r3.sh','611e0cc4fbbfaaf618c7caf62c044d9a9966bd24ed2c29e632c11fd7fadee0f9')]:
  assert sha(ROOT/name)==h;r['bindings'][name]={'path':str(ROOT/name),'sha256':h,'bytes':(ROOT/name).stat().st_size}
 assert not call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT])
 before=call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT]).splitlines();assert before==[OLDNET]
 net=json.loads(call(['docker','network','inspect',OLDNET]))[0]
 labels={'com.docker.compose.project':PROJECT,'execution-sha':SOURCE,'workorder':'24','pi24.phase-contract-sha256':PHASE}
 assert net['Id']==OLDNET and net['Internal'] is True and net['EnableIPv6'] is False and not net['Containers']
 assert all(net['Labels'].get(k)==v for k,v in {**labels,'pi24.nonce':OLD}.items());r['retired_network_before']=net
 real=call(['which','nvidia-smi']);assert pathlib.Path(real).resolve()==pathlib.Path('/usr/bin/nvidia-smi').resolve();realhash=sha(real);assert realhash=='2da08a20450594c3cdf1e677c1d2e46101a0b2d45ee5d3d6b67b87ae50522af2'
 directory=ROOT/'nvml-normal02-bin';directory.mkdir(exist_ok=False);w=directory/'nvidia-smi';w.write_bytes(base64.b64decode(WRAPPER));w.chmod(0o700);assert sha(w)=='917f97350b53c3b2ddcbd0f105900b32a6b786434ce7ca3c971a8a43c6d2dc4e'
 log=ROOT/'NVML-QUERY-RAW-NOV14-V2.jsonl';assert not log.exists() and not log.is_symlink()
 r['query_binding']={'real_binary':real,'real_resolved':str(pathlib.Path(real).resolve()),'real_binary_sha256':realhash,'wrapper_path':str(w),'wrapper_sha256':sha(w),'wrapper_bytes':w.stat().st_size,'original_PATH':os.environ['PATH'],'effective_PATH':str(directory)+os.pathsep+os.environ['PATH'],'log_path':str(log),'log_exists':False}
 r['cpu_probe']=json.loads(call(['sh',str(ROOT/'entry_nov14_r3.sh'),'--cpu-probe']));assert r['cpu_probe']['cpu_only'] and not r['cpu_probe']['model_started'];assert r['cpu_probe']['sample']['affinity']==[0,1] and r['cpu_probe']['sample']['rss_bytes']<1073741824
 call(['docker','network','rm',OLDNET]);r['old_network_removed']=True
 args=['docker','network','create','--internal','--ipv6=false']
 for k,v in {**labels,'pi24.nonce':NEW}.items():args+=['--label',k+'='+v]
 nid=call(args+[PROJECT+'-'+NEW]);r['network_id']=nid;newnet=json.loads(call(['docker','network','inspect',nid]))[0];assert newnet['Id']==nid and newnet['Internal'] is True and newnet['EnableIPv6'] is False and not newnet['Containers'];assert all(newnet['Labels'].get(k)==v for k,v in {**labels,'pi24.nonce':NEW}.items());r['network']=newnet
 assert not call(['docker','ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+PROJECT]);assert call(['docker','network','ls','--no-trunc','-q','--filter','label=com.docker.compose.project='+PROJECT])==nid
 r['free_bytes']=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize;assert r['free_bytes']>=21474836480
 r['model_transport']={'shell':str(ROOT/'entry_nov14_r3.sh'),'outer':str(ROOT/'gpu_entry_nov14_r3.py'),'phase_file':str(ROOT/'PHASE-CONTRACT.v3.json'),'future_GO_file':str(ROOT/'B-GPU-NORMAL-NOV14-GO02.json'),'command':['sh',str(ROOT/'entry_nov14_r3.sh'),'--go',str(ROOT/'B-GPU-NORMAL-NOV14-GO02.json'),'--go-sha256','<Master-exact-GO-hash>'],'PATH':r['query_binding']['effective_PATH'],'cwd':str(ROOT),'CUDA_VISIBLE_DEVICES':'0','host_affinity':[0,1]}
except BaseException as e:r['failure']=repr(e);r['traceback']=traceback.format_exc()
finally:
 r['end']=time.time();r['elapsed_s']=r['end']-r['start'];r['success']=r['failure'] is None;r['compute_released']=True
 out=ROOT/'NORMAL02-CPU-FREEZE01.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if not r['success']:raise SystemExit(3)
'''
(s/'NORMAL02-CPU-freeze-remote-script.py').write_text(script)
cmd=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','wt@58.199.171.85','cd /media/usv012/pjx && export CUDA_VISIBLE_DEVICES=0 && cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder && exec taskset -c 0,1 python3 -']
start=time.time();assert start<datetime.datetime.fromisoformat('2026-11-14T03:04:00+00:00').timestamp()
p=subprocess.run(cmd,input=script,capture_output=True,text=True,timeout=55)
r={'command':cmd,'start':start,'end':time.time(),'wall_s':time.time()-start,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'remote_script_sha256':hashlib.sha256(script.encode()).hexdigest(),'all_SSH_SCP_ended':True};(s/'NORMAL02-CPU-FREEZE01-SSH.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(p.returncode)
