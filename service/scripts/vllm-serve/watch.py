"""Independent foreground watchdog for exact issue24 objects; no foreign cleanup."""
import argparse,json,pathlib,shutil,signal,subprocess,time
from owned import OwnedDocker
GPU='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
def main():
 p=argparse.ArgumentParser();p.add_argument('--project',choices=['pi-vllm24-b','pi-vllm24-r'],required=True);p.add_argument('--sha',required=True);p.add_argument('--nonce',required=True);p.add_argument('--root',required=True);p.add_argument('--deadline',type=float,required=True);p.add_argument('--out',required=True);p.add_argument('--ready',required=True);p.add_argument('--stop-file',required=True);p.add_argument('--gpu',action='store_true');a=p.parse_args()
 root=pathlib.Path(a.root).resolve()
 if root not in [pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111')/r for r in ('builder','regulator')]:raise ValueError('wrong root')
 run(a)

def run(a):
 root=pathlib.Path(a.root).resolve()
 if not time.time()<a.deadline<=time.time()+900:raise ValueError('watch deadline')
 out=pathlib.Path(a.out)
 if out.exists() or pathlib.Path(a.ready).exists():raise ValueError('new watch receipts required')
 docker=OwnedDocker(a.project,a.sha,a.nonce);known={};failure=None
 def record(v):
  with out.open('a') as f:f.write(json.dumps({'epoch':time.time(),**v})+'\n')
 def interrupt(*_):raise RuntimeError('watch interrupted')
 signal.signal(signal.SIGTERM,interrupt)
 try:
  docker.discover(known);pathlib.Path(a.ready).write_text(str(time.time()))
  while not pathlib.Path(a.stop_file).exists():
   rows=docker.discover(known);reason='deadline' if time.time()>=a.deadline else None
   if shutil.disk_usage(root).free<20*2**30:reason='disk_pressure'
   if a.gpu:
    pids=set()
    for row in rows:
     if not row['State']['Running']:continue
     top=docker.command(['top',row['Id'],'-eo','pid'])
     if top.returncode:
      now=docker.inspect(row['Id'])
      if now is not None and now['State']['Running']:raise RuntimeError('owned process inventory unknown')
     else:pids.update(int(x.strip()) for x in top.stdout.splitlines()[1:])
    r=subprocess.run(['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
    if r.returncode:raise RuntimeError('GPU0 inventory unknown')
    foreign=[]
    for line in r.stdout.splitlines():
     pid,uuid=[x.strip() for x in line.split(',')]
     if uuid!=GPU:raise RuntimeError('GPU0 identity mismatch')
     if int(pid) not in pids:foreign.append(int(pid))
    if foreign:reason='foreign_gpu_process'
   else:foreign=[]
   record({'event':'sample','running':[r['Id'] for r in rows if r['State']['Running']],'foreign':foreign,'reason':reason})
   if reason:break
   time.sleep(.5)
 except BaseException as e:failure=repr(e);record({'event':'watch_error','error':failure})
 finally:
  try:docker.discover(known)
  except Exception as e:failure=repr(e)
  ordered=sorted(known,key=lambda cid:known[cid]['Config']['Labels'].get('com.docker.compose.service')!='model')
  result=docker.cleanup(ordered);record({'event':'cleanup','inventory_error':failure,**result})
  if failure or not result['success']:raise RuntimeError('cleanup unknown/failed')
if __name__=='__main__':main()
