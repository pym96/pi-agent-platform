"""External foreground watchdog. Only exact-labelled #12 objects can be stopped."""
import argparse,json,subprocess,time,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--deadline',required=True,type=float);p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
assert a.project in ('pi-e2e12-builder','pi-e2e12-regulator') and len(a.sha)==40 and time.time()<a.deadline<=time.time()+1800
root=Path(a.root).resolve();assert str(root).startswith('/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261023/')
assert not Path(a.out).exists();gpu='GPU-dd5fc05f-7d4d-17f7-8d33-2f474b56b74e';known={}
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
    for row in owned():
        if row['State']['Running']:subprocess.run(['docker','stop','--time','5',row['Id']],check=True,timeout=20)
    record({'event':'cleanup','containers':{i:not json.loads(cmd(['docker','inspect',i]))[0]['State']['Running'] for i in known}})
