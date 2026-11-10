"""One control thread owns heartbeat and hard deadline; diagnostics run separately."""
import json,os,signal,subprocess,sys,time,shlex
from pathlib import Path
from watch_cleanup import discover_owned,cleanup_known
HERE=Path(__file__).resolve().parent

def process_birth(pid):
    proc=Path('/proc/'+str(pid)+'/stat')
    if Path('/proc/self/stat').exists():return proc.read_text().split()[21]
    # CPU fixtures on macOS still bind to a real OS process; server uses Linux ticks.
    value=subprocess.check_output(['ps','-p',str(pid),'-o','lstart='],text=True).strip()
    if not value:raise ProcessLookupError(pid)
    return value

def process_arguments(pid):
    if Path('/proc/self/stat').exists():return [x.decode() for x in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\0') if x]
    return shlex.split(subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True).strip())

def verify_watch(go):
    entries=[]
    for line in Path(go['watch_receipt']).read_text().splitlines():
        try:entries.append(json.loads(line))
        except ValueError:pass
    beats=[x for x in entries if x.get('event')=='heartbeat']
    if not beats:raise RuntimeError('watch heartbeat absent')
    beat=beats[-1];pid=beat['watch_pid']
    assert beat['project']==go['project'] and beat['source_sha']==go['source_sha'] and beat['deadline_epoch']==go['deadline_epoch'] and beat.get('monitor_version')==2,'watch binding'
    assert 0<=time.time()-beat['utc_epoch']<=5 and time.time()<beat['deadline_epoch'],'watch heartbeat stale/expired'
    os.kill(pid,0);assert process_birth(pid)==beat['watch_start_ticks'],'watch PID reuse'
    args=process_arguments(pid);assert '--sha' in args and '--project' in args and go['source_sha'] in args and go['project'] in args and any(x.endswith('service/scripts/pi-qwen-load/watch.py') for x in args),'watch process identity'
    return beat

def guard_watch(go,stop,lost,known,out):
    while not stop.wait(1):
        try:verify_watch(go)
        except Exception as error:
            lost.set()
            try:discover_owned(go['project'],go['source_sha'],known)
            except Exception:pass
            result=cleanup_known(go['project'],go['source_sha'],list(known))
            with Path(out).open('a') as f:f.write(json.dumps({'error':repr(error),'cleanup':result,'utc_epoch':time.time()})+'\n')
            return

def run_monitor(project,sha,deadline,root,out,sample_command=None):
    root=Path(root);out=Path(out);assert not out.exists();known={};sample=None;cycle=0;seen=False;latest=None;cycle_started=None;stopping=False
    identity={'project':project,'source_sha':sha,'deadline_epoch':deadline,'watch_pid':os.getpid(),'watch_start_ticks':process_birth(os.getpid()),'monitor_version':2}
    def record(value):
        with out.open('a') as f:f.write(json.dumps({**identity,'utc_epoch':time.time(),**value})+'\n')
    def interrupted(*_):raise RuntimeError('watch interrupted; stop owned objects')
    previous={s:signal.signal(s,interrupted) for s in (signal.SIGTERM,signal.SIGINT)}
    try:
        while True:
            now=time.time()
            if now>=deadline:record({'event':'stop','reason':'deadline'});break
            if sample is not None and sample.poll() is not None:
                result_path=Path(str(out)+'.cycle-'+str(cycle)+'.json');latest=json.loads(result_path.read_text());record({'event':'diagnostic','cycle':cycle,**latest});sample.wait();sample=None
                if latest['status']!='complete':record({'event':'stop','reason':'diagnostic_unknown'});break
                known.update({ident:None for ident in latest['known_ids']});seen=seen or bool(latest['running'])
                if latest.get('stop_reason'):record({'event':'stop','reason':latest['stop_reason']});break
                if seen and not latest['running']:record({'event':'owned_stack_stopped'});break
            if sample is not None and time.monotonic()-cycle_started>=30:
                record({'event':'stop','reason':'diagnostic_cycle_timeout','resource_status':'unknown'});break
            if sample is None:
                cycle+=1;cycle_started=time.monotonic();result_path=Path(str(out)+'.cycle-'+str(cycle)+'.json');command=(sample_command or [sys.executable,str(HERE/'watch_sample.py')])+['--project',project,'--sha',sha,'--root',str(root),'--out',str(result_path),'--commands',str(out)+'.commands.jsonl'];sample=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                record({'event':'diagnostic_start','cycle':cycle,'sampler_pid':sample.pid,'started_epoch':time.time()})
            observed=latest.get('gpu_observed_epoch') if latest else None;fresh=observed is not None and now-observed<=2
            record({'event':'heartbeat','control':'deadline_checked','diagnostic_status':'in_progress','cycle':cycle,'sampler_pid':sample.pid,'resource_status':'fresh' if fresh else 'unknown','resource_observed_epoch':observed,'gpu_snapshot':latest.get('gpu_snapshot') if fresh else None})
            time.sleep(min(1,max(0,deadline-time.time())))
    finally:
        # Stop the complete private sampling process group before Docker reconciliation.
        if sample is not None and sample.poll() is None:
            
            try:os.killpg(sample.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            sample.wait(timeout=5);record({'event':'diagnostic_cancelled','cycle':cycle,'sampler_pid':sample.pid,'resource_status':'unknown'})
        record({'event':'cleanup_start','known_ids':list(known)})
        refresh_error=None
        try:discover_owned(project,sha,known)
        except Exception as error:refresh_error=repr(error)
        record({'event':'cleanup_discovery','known_ids':list(known),'refresh_error':refresh_error})
        result=cleanup_known(project,sha,list(known));record({'event':'cleanup',**result,'refresh_error':refresh_error})
        for sig,handler in previous.items():signal.signal(sig,handler)
        if refresh_error or not result['success']:raise RuntimeError('owned cleanup unknown/incomplete; inspect')
