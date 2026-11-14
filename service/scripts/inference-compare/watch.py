"""Independent issue28 watcher: exact owned cleanup, GPU/raw/resource receipts.

Loss of the foreground lease stops owned work within 5s + bounded queries/cleanup.
No process restart, foreign kill, or unknown-inventory-to-empty conversion.
"""
import argparse,json,os,resource,shutil,signal,subprocess,time
from pathlib import Path
from authority import validate,verify_entries,ROOT,GPU
from owned import OwnedDocker

def compute_processes(text,owned_pids):
    foreign=[]
    for line in text.splitlines():
        fields=[s.strip() for s in line.split(',')]
        if len(fields)!=2 or fields[1]!=GPU or not fields[0].isdigit():raise ValueError('GPU process inventory unknown/identity')
        pid=int(fields[0])
        if pid not in owned_pids:foreign.append(pid)
    return foreign

def parser():
    p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True)
    p.add_argument('--phase-contract',required=True);p.add_argument('--phase-contract-sha256',required=True)
    p.add_argument('--model-index',required=True,type=int);p.add_argument('--out',required=True);return p

def run(a):
    g=validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256);role_root=ROOT/g['role'];verify_entries(g,role_root/'source')
    if not 0<=a.model_index<len(g['models']):raise ValueError('model index')
    model=g['models'][a.model_index];out=Path(a.out).resolve()
    if out.parent!=role_root/('run-'+g['nonce']) or out.name!=model['id']:raise ValueError('watch exact own output root')
    docker=OwnedDocker(g['role'],g['source_sha'],model['nonce']);known={};failure=None
    target=out/'watch.jsonl'
    if target.exists():raise ValueError('fresh watch receipts required')
    def record(event):
        with target.open('a') as f:f.write(json.dumps({'epoch':time.time(),**event})+'\n')
    def query(args):
        start=time.time()
        try:
            r=subprocess.run(args,capture_output=True,text=True,timeout=5)
            record({'event':'query','argv':args,'start':start,'end':time.time(),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if r.returncode:raise RuntimeError('query failed')
            return r.stdout
        except BaseException as exc:record({'event':'query_failed','argv':args,'error':repr(exc)});raise
    def interrupted(*_):raise RuntimeError('watch interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        docker.discover(known);(out/'watch-ready').write_text(str(time.time()))
        while not (out/'watch-stop').exists():
            tick=time.monotonic();rows=docker.discover(known);pids=set()
            for row in rows:
                if row['State']['Running']:
                    r=docker.command(['top',row['Id'],'-eo','pid'])
                    if r.returncode:raise RuntimeError('owned PIDs unknown')
                    pids.update(int(x.strip()) for x in r.stdout.splitlines()[1:])
            raw=query(['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader,nounits'])
            foreign=compute_processes(raw,pids)
            gpu=query(['nvidia-smi','-i','0','--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'])
            if gpu.split(',')[0].strip()!=GPU:raise RuntimeError('GPU identity unknown')
            record({'event':'sample','running':[r['Id'] for r in rows if r['State']['Running']],
                    'foreign':foreign,'host_load':os.getloadavg(),'watch_cpu_s':time.process_time(),
                    'watch_maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'host_processes':query(['ps','-eo','pid,ppid,pcpu,rss,args'])})
            lease=out/'foreground-lease'
            if not lease.exists() or time.time()-lease.stat().st_mtime>5:raise RuntimeError('foreground transport lease lost')
            if foreign:raise RuntimeError('foreign GPU0 process observed')
            if shutil.disk_usage(role_root).free<20*2**30:raise RuntimeError('free disk pressure')
            if time.time()>=model['deadline_epoch']-15:raise RuntimeError('absolute watch deadline')
            time.sleep(max(0,1-(time.monotonic()-tick)))
    except BaseException as exc:failure=repr(exc);record({'event':'watch_error','error':failure})
    finally:
        try:docker.discover(known)
        except Exception as exc:failure=failure or repr(exc)
        cleanup=docker.cleanup(known);record({'event':'cleanup','inventory_error':failure,**cleanup})
        if failure or not cleanup['success']:raise RuntimeError('watch execution/cleanup failed or unknown')

if __name__=='__main__':
    try:run(parser().parse_args())
    except Exception as e:raise SystemExit('watch rejected/failed: '+repr(e))
