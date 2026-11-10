"""One bounded diagnostic cycle, isolated from the watchdog's control loop."""
import argparse,json,time,shutil
from pathlib import Path
import watch_cleanup as cleanup

def collect(project,sha,root):
    known={};rows=cleanup.discover_owned(project,sha,known);running=[r for r in rows if r['State']['Running']];pids=set();receipts=[]
    for row in running:
        result=cleanup.command(['top',row['Id'],'-eo','pid'],receipts)
        if result.returncode:
            current=cleanup.inspect_exact(row['Id'],project,sha,receipts)
            if current is not None and current['State']['Running']:raise cleanup.UnknownState('top failed on running exact ID')
        else:pids.update(int(x.strip()) for x in result.stdout.splitlines()[1:])
    gpu='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
    apps=cleanup.execute(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],receipts)
    if apps.returncode:raise cleanup.UnknownState('GPU process inventory unavailable')
    others=[]
    for line in apps.stdout.splitlines():
        fields=[x.strip() for x in line.split(',')]
        if fields[0]==gpu and int(fields[1]) not in pids:others.append(int(fields[1]))
    snapshot=cleanup.execute(['nvidia-smi','--id='+gpu,'--query-gpu=uuid,memory.used,utilization.gpu,clocks.sm,power.draw','--format=csv,noheader,nounits'],receipts)
    if snapshot.returncode:raise cleanup.UnknownState('GPU snapshot unavailable')
    gpu_observed_epoch=time.time();sizes=sum(p.stat().st_size for p in root.rglob('*') if p.is_file());available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    reason='foreign_gpu_process' if others else None
    if shutil.disk_usage(root).free<20*2**30:reason='disk_pressure'
    if sizes>2*2**30:reason='owned_disk_budget'
    if available<40*2**30:reason='host_memory_pressure'
    return {'known_ids':list(known),'running':[r['Id'] for r in running],'foreign_pids':others,'gpu_snapshot':snapshot.stdout.strip(),'gpu_observed_epoch':gpu_observed_epoch,'owned_bytes':sizes,'available_memory':available,'stop_reason':reason}

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--commands',required=True);a=p.parse_args();cleanup.TRACE_PATH=a.commands;started=time.time()
    try:value={'status':'complete',**collect(a.project,a.sha,Path(a.root))}
    except BaseException as error:value={'status':'unknown','error':repr(error)}
    value.update(start_epoch=started,end_epoch=time.time());Path(a.out).write_text(json.dumps(value));return 0 if value['status']=='complete' else 1
if __name__=='__main__':raise SystemExit(main())
