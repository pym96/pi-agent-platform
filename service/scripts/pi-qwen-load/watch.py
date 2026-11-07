"""Foreground #13 exact-ID guard. No scheduling; Master GO required."""
import argparse,json,subprocess,time,shutil,signal
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--deadline',required=True,type=float);p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
assert a.project in ('pi-qwen13-b','pi-qwen13-r') and len(a.sha)==40 and time.time()<a.deadline<=time.time()+900
root=Path(a.root).resolve();assert str(root).startswith('/media/usv012/pjx/pi-agent-platform/experiments/13-qwen-load-20261107/')
assert not Path(a.out).exists();gpu='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead';known={}
def cmd(args):return subprocess.check_output(args,text=True,timeout=15).strip()
from watch_cleanup import discover_owned,cleanup_known,inspect_exact
def owned():return discover_owned(a.project,a.sha,known)
def record(value):
    with Path(a.out).open('a') as f:f.write(json.dumps({'utc_epoch':time.time(),**value})+'\n')
def interrupted(*_):raise RuntimeError('watch interrupted; stop owned objects')
signal.signal(signal.SIGTERM,interrupted)
try:
    seen=False
    while True:
        rows=owned();running=[r for r in rows if r['State']['Running']];seen=seen or bool(running)
        if seen and not running:record({'event':'owned_stack_stopped'});break
        reason=None
        if time.time()>=a.deadline:reason='deadline'
        pids=set()
        for row in running:
            try:pids.update(int(x.strip()) for x in cmd(['docker','top',row['Id'],'-eo','pid']).splitlines()[1:])
            except subprocess.CalledProcessError:
                current=inspect_exact(row['Id'],a.project,a.sha,[])
                if current is not None and current['State']['Running']:raise
                # The exact ID settled/disappeared during this monitoring read.

        others=[]
        for line in cmd(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']).splitlines():
            fields=[x.strip() for x in line.split(',')]
            if fields[0]==gpu and int(fields[1]) not in pids:others.append(int(fields[1]))
        if others:reason='foreign_gpu_process'
        if shutil.disk_usage(root).free<20*2**30:reason='disk_pressure'
        sizes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
        if sizes>2*2**30:reason='owned_disk_budget'
        available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
        if available<40*2**30:reason='host_memory_pressure'
        gpu_snapshot=cmd(['nvidia-smi','--id='+gpu,'--query-gpu=uuid,memory.used,utilization.gpu,clocks.sm,power.draw','--format=csv,noheader,nounits'])
        record({'gpu_snapshot':gpu_snapshot,'event':'sample','running':[r['Id'] for r in running],'foreign_pids':others,'owned_bytes':sizes,'available_memory':available,'stop_reason':reason})
        if reason:break
        time.sleep(1)
finally:
    refresh_error=None
    try:owned()
    except Exception as error:refresh_error=repr(error)
    result=cleanup_known(a.project,a.sha,list(known))
    record({'event':'cleanup',**result,'refresh_error':refresh_error})
    if refresh_error or not result['success']:raise RuntimeError('owned cleanup unknown/incomplete; inspect receipts')
