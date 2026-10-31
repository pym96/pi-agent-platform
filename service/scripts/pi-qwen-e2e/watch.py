"""External foreground watchdog. Only exact-labelled #12 objects can be stopped."""
import argparse,json,subprocess,time,shutil,signal
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--deadline',required=True,type=float);p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
assert a.project in ('pi-e2e12-1031-b','pi-e2e12-1031-r') and len(a.sha)==40 and time.time()<a.deadline<=time.time()+900
root=Path(a.root).resolve();assert str(root).startswith('/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/')
assert not Path(a.out).exists();gpu='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead';known={}
def cmd(args):return subprocess.check_output(args,text=True,timeout=15).strip()
def owned():
    ids=cmd(['docker','ps','-aq','--filter','label=com.docker.compose.project='+a.project]).splitlines();result=[]
    for ident in ids:
        row=json.loads(cmd(['docker','inspect',ident]))[0];labels=row['Config']['Labels']
        assert labels.get('workorder')=='12' and labels.get('execution-sha')==a.sha
        known[row['Id']]=row;result.append(row)
    return result
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
            pids.update(int(x.strip()) for x in cmd(['docker','top',row['Id'],'-eo','pid']).splitlines()[1:])
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
        record({'event':'sample','running':[r['Id'] for r in running],'foreign_pids':others,'owned_bytes':sizes,'available_memory':available,'stop_reason':reason})
        if reason:break
        time.sleep(2)
finally:
    errors=[]
    # Failure to collect fresh diagnostics must not skip known-owned stop attempts.
    try:owned()
    except Exception as error:errors.append('refresh: '+repr(error))
    for ident in list(known):
        try:subprocess.run(['docker','stop','--time','5',ident],check=True,timeout=20,capture_output=True)
        except Exception as error:errors.append('stop '+ident+': '+repr(error))
    state={}
    for ident in known:
        try:state[ident]=not json.loads(cmd(['docker','inspect',ident]))[0]['State']['Running']
        except Exception as error:state[ident]=None;errors.append('inspect '+ident+': '+repr(error))
    record({'event':'cleanup','containers':state,'errors':errors})
    if errors or any(value is not True for value in state.values()):raise RuntimeError('owned cleanup incomplete; inspect receipts')
