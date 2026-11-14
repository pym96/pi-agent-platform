"""Frozen external envelope; CPU probe never starts the Product launcher."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys,time
ROOT=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder')
SOURCE='9ea36d3221d024a6d8330322d330809fa9e283a6'
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def sample():
 rows={}
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   fields=dict(line.split(':',1) for line in (p/'status').read_text().splitlines() if ':' in line)
   rows[int(p.name)]={'ppid':int(fields['PPid']),'rss_bytes':int(fields.get('VmRSS','0 kB').split()[0])*1024,'allowed':fields['Cpus_allowed_list'].strip()}
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 owned={os.getpid()}
 while True:
  nxt=owned|{pid for pid,row in rows.items() if row['ppid'] in owned}
  if nxt==owned:break
  owned=nxt
 values={str(pid):rows[pid] for pid in owned if pid in rows}
 return {'epoch':time.time(),'pid':os.getpid(),'affinity':sorted(os.sched_getaffinity(0)),'rss_bytes':sum(x['rss_bytes'] for x in values.values()),'descendants':values}
def main():
 p=argparse.ArgumentParser();p.add_argument('--cpu-probe',action='store_true');p.add_argument('--go');p.add_argument('--go-sha256');p.add_argument('--phase-contract');p.add_argument('--phase-contract-sha256');a=p.parse_args()
 assert pathlib.Path.cwd()==ROOT and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
 assert sorted(os.sched_getaffinity(0))==[0,1]
 if a.cpu_probe:print(json.dumps({'cpu_only':True,'model_started':False,'sample':sample()}));return 0
 assert a.go and a.go_sha256 and a.phase_contract and a.phase_contract_sha256 and digest(a.go)==a.go_sha256
 g=json.loads(pathlib.Path(a.go).read_text());assert g['source_sha']==SOURCE and g['role']=='builder'
 assert g['outer_entry_sha256']==digest(__file__)
 assert g['max_host_rss_bytes']==1073741824 and g['host_affinity']==[0,1]
 sys.path.insert(0,str(ROOT/'source/service/scripts/vllm-serve'))
 from launch import validate
 assert validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256)==g
 assert g['outer_absolute_stop_epoch']==g['deadline_epoch']
 out=ROOT/('outer-'+g['nonce']);out.mkdir();child=None;failure=None
 with (out/'rss-affinity.jsonl').open('w',buffering=1) as log:
  command=[sys.executable,str(ROOT/'source/service/scripts/vllm-serve/launch.py'),'--go',a.go,'--go-sha256',a.go_sha256,'--phase-contract',a.phase_contract,'--phase-contract-sha256',a.phase_contract_sha256]
  (out/'command.json').write_text(json.dumps({'command':command,'go_sha256':a.go_sha256,'entry_sha256':digest(__file__),'start':time.time()},indent=2))
  try:
   with (out/'launcher.log').open('w') as target:
    child=subprocess.Popen(command,stdout=target,stderr=subprocess.STDOUT,start_new_session=True)
    while child.poll() is None:
     row=sample();log.write(json.dumps(row)+'\n')
     if row['rss_bytes']>1073741824:raise RuntimeError('host RSS cap')
     if any(v['allowed']!='0-1' for v in row['descendants'].values()):raise RuntimeError('own affinity changed')
     if time.time()>=g['deadline_epoch']:raise TimeoutError('outer absolute deadline')
     time.sleep(.25)
    if child.returncode:failure='launcher exit '+str(child.returncode)
  except BaseException as e:failure=repr(e)
  finally:
   if child is not None and child.poll() is None:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=2)
   # Only exact source/project/nonce objects; inventory failure remains unknown.
   sys.path.insert(0,str(ROOT/'source/service/scripts/vllm-serve'))
   from owned import OwnedDocker
   d=OwnedDocker('pi-vllm24-b',SOURCE,g['nonce']);known={};inventory_error=None
   try:d.discover(known)
   except Exception as e:inventory_error=repr(e)
   cleanup=d.cleanup(known)
   post={}
   for name,cmd in [('uuid',['nvidia-smi','-i','0','--query-gpu=uuid','--format=csv,noheader']),('processes',['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'])]:
    try:
     r=subprocess.run(cmd,capture_output=True,text=True,timeout=5);post[name]={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except Exception as e:post[name]={'error':repr(e)}
   result={'end':time.time(),'launcher_exit':None if child is None else child.returncode,'failure':failure,'inventory_error':inventory_error,'cleanup':cleanup,'post_gpu0':post}
   (out/'receipt.json').write_text(json.dumps(result,indent=2))
 return 0 if not failure and not inventory_error and cleanup['success'] else 3
if __name__=='__main__':raise SystemExit(main())
