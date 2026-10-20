#!/usr/bin/env python3
"""Owned Linux experiment driver. Run from service; no global changes or paid endpoint."""
import datetime, hashlib, json, os, pathlib, subprocess, time, urllib.request

ROOT = pathlib.Path(os.environ['RUN_ROOT'])
OUT = ROOT / 'evidence'
PROJECT = os.environ.get('HV_PROJECT', 'pi-hv3')
IMAGE = 'python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1'
BASE = 'http://127.0.0.1:18151'
SOURCE = os.environ['SOURCE_SHA']
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(name, value): (OUT/name).write_text(json.dumps(value, indent=2)+'\n')
def cmd(args, check=True):
    p=subprocess.run(args, capture_output=True, text=True)
    if check and p.returncode: raise RuntimeError((args,p.returncode,p.stderr))
    return p
def request(path, body=None):
    req=urllib.request.Request(BASE+path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:return r.status,r.read()
def compose(*args):return cmd(['docker','compose','-p',PROJECT,*args])
def snapshot(name):
    record={'utc':utc()}
    for target,base in [('api',BASE),('pi','http://127.0.0.1:18152')]:
        try:
            with urllib.request.urlopen(base+'/metrics',timeout=5) as r:record[target]=json.load(r)
        except Exception as e:record[target]={'error':str(e)}
    names=[f'{PROJECT}-{x}-1' for x in ['api','pi','pg']]+[f'{PROJECT}-generator',f'{PROJECT}-c10k']
    record['dockerStats']=cmd(['docker','stats','--no-stream','--format','{{json .}}',*names],False).stdout
    record['process']={}
    for name2 in names:
        proc=cmd(['docker','exec',name2,'sh','-c','echo fds=$(ls /proc/1/fd | wc -l); cat /proc/1/status /proc/1/stat /proc/1/limits'],False)
        record['process'][name2]={'stdout':proc.stdout,'stderr':proc.stderr,'exitCode':proc.returncode}
    write(name+'.resources.json',record)
def execute(run):
    rid=run['id']; run.update(sourceSHA=SOURCE,started=utc())
    snapshot(rid+'.before')
    files=[]; start=time.monotonic()
    if run['tool']=='hey':
        args=['/tools/hey','-n',str(run['expected']),'-c',str(run['load']),'-t','5','-cpus','1','-disable-redirects','-o','csv',run['target']]
        stdout=OUT/(rid+'.csv'); stderr=OUT/(rid+'.stderr')
        with stdout.open('wb') as out,stderr.open('wb') as err:
            p=subprocess.run(['docker','exec',f'{PROJECT}-generator',*args],stdout=out,stderr=err,timeout=180)
        files=[stdout,stderr]
    else:
        target=OUT/(rid+'.targets'); target.write_text('GET '+run['target']+'\n')
        args=['/tools/vegeta','attack','-targets','/evidence/'+target.name,'-rate',str(run['load'])+'/s','-duration',str(run['duration'])+'s','-timeout','5s','-http2=false','-keepalive=true','-redirects=0','-workers=10','-max-workers=100','-output','/evidence/'+rid+'.bin']
        stderr=OUT/(rid+'.stderr')
        with stderr.open('wb') as err:p=subprocess.run(['docker','exec',f'{PROJECT}-generator',*args],stdout=err,stderr=err,timeout=90)
        files=[target,stderr,OUT/(rid+'.bin')]
        for suffix,extra in [('.report.json',['report','-type=json']),('.results.jsonl',['encode','-to=json'])]:
            f=OUT/(rid+suffix)
            with f.open('wb') as output:subprocess.run(['docker','exec',f'{PROJECT}-generator','/tools/vegeta',*extra,'/evidence/'+rid+'.bin'],stdout=output,check=True)
            files.append(f)
    run.update(command=args,exitCode=p.returncode,wallSeconds=time.monotonic()-start,ended=utc())
    snapshot(rid+'.after')
    files += [OUT/(rid+'.before.resources.json'),OUT/(rid+'.after.resources.json')]
    run['artifacts']={x.name:digest(x) for x in files}
    with (OUT/'runs.jsonl').open('a') as f:f.write(json.dumps(run)+'\n')
    print(rid,p.returncode,flush=True)

OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'runs.jsonl').exists():raise SystemExit('Refusing to overwrite/repeat an existing run campaign')
write('source-identity.json',{'sourceSHA':SOURCE,'utc':utc(),'files':{p:digest(p) for p in ['bin/service','bin/load','pi/server.mjs','pi/model.mjs','pi/package-lock.json','compose.yaml']},'tools':{p:digest(ROOT/'tools'/p) for p in ['hey','vegeta']},'protocol':'HTTP/1.1 cleartext; keepalive enabled; redirects disabled; no proxy','project':PROJECT})
try:
    os.environ['SSE_TAIL_CACHE']='0'; compose('up','-d','pg','pi','api')
    for _ in range(60):
        try:
            if request('/health')[0]==200:break
        except Exception:time.sleep(1)
    cmd(['docker','run','-d','--name',PROJECT+'-generator','--network',PROJECT+'_default','--cpus','1','--memory','1g','--ulimit','nofile=32768:32768','-e','GOMAXPROCS=1','-v',str(ROOT/'tools')+':/tools:ro','-v',str(OUT)+':/evidence','--entrypoint','sleep',IMAGE,'infinity'])
    session='hv3-fixed'; path='/sessions/'+session+'/tasks'
    for n in [1,2]:
        request(path,{'key':'turn'+str(n),'prompt':'fixed synthetic turn '+str(n)})
        for _ in range(200):
            tasks=json.loads(request(path)[1])
            if len(tasks)==n and all(t['status']=='completed' for t in tasks):break
            time.sleep(.1)
        else:raise RuntimeError('fixed session did not complete')
    status,body=request(path)
    (OUT/'frozen-history.json').write_bytes(body)
    write('frozen-expectation.json',{'path':path,'status':status,'sha256':hashlib.sha256(body).hexdigest(),'tasks':2,'model':'actual Pi1.3.0 + deterministic streaming fixture','utc':utc()})
    for cache in [0,1]:
        os.environ['SSE_TAIL_CACHE']=str(cache); compose('up','-d','--force-recreate','api');time.sleep(2)
        snapshot('cache'+str(cache)+'.idle')
        inspected=cmd(['docker','inspect',*[f'{PROJECT}-{x}-1' for x in ['api','pi','pg']],PROJECT+'-generator'])
        # Config.Env is disposable stack-only; never read external credentials.
        write('cache'+str(cache)+'.containers.json',json.loads(inspected.stdout))
        assert request(path)[1]==body, 'history changed before comparison'
        for endpoint,urlpath in [('health','/health'),('history',path)]:
            for concurrency in [1,10,100]:
                for rep in [1,2,3]:execute({'id':f'hey-cache{cache}-{endpoint}-c{concurrency}-r{rep}','tool':'hey','cache':cache,'endpoint':endpoint,'load':concurrency,'rep':rep,'expected':1000,'target':'http://api:8080'+urlpath})
        for rate in [10,100,500]:
            for rep in [1,2,3]:execute({'id':f'vegeta-cache{cache}-history-q{rate}-r{rep}','tool':'vegeta','cache':cache,'endpoint':'history','load':rate,'rep':rep,'duration':10,'expected':rate*10,'target':'http://api:8080'+path})
        assert request(path)[1]==body, 'history changed after comparison'
    # Existing dedicated generator, separate from both HTTP tool matrices.
    snapshot('c10k.before')
    name=PROJECT+'-c10k'
    args=['docker','compose','-p',PROJECT,'run','--rm','--name',name,'load','-connections','10000','-hold','120s','-session','hv3-c10k','-out','/evidence/c10k.json']
    # Stop idle HTTP generator first: only one 1CPU/1GiB generator slot exists.
    cmd(['docker','stop',PROJECT+'-generator']);cmd(['docker','rm',PROJECT+'-generator'])
    with (OUT/'c10k.log').open('wb') as log:
        p=subprocess.Popen(args,stdout=log,stderr=log)
        began=time.monotonic()
        while p.poll() is None:
            snapshot('c10k.sample'+str(int(time.time())))
            time.sleep(5)
            if time.monotonic()-began>240:
                cmd(['docker','stop',name],False)
                break
        write('c10k-exit.json',{'command':args,'exitCode':p.returncode,'utc':utc()})
    snapshot('c10k.after')
finally:
    # Exact owned names only; preserve volumes and every raw artifact.
    stopped=cmd(['docker','stop',PROJECT+'-generator',PROJECT+'-c10k'],False)
    removed=cmd(['docker','rm',PROJECT+'-generator'],False)
    down=cmd(['docker','compose','-p',PROJECT,'down'],False)
    state=cmd(['docker','ps','-a','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.Names}} {{.Status}}'])
    write('stop.json',{'utc':utc(),'stop':stopped.stdout,'stopStderr':stopped.stderr,'down':down.stdout,'downStderr':down.stderr,'downExit':down.returncode,'remainingOwnedCompose':state.stdout,'volumesPreserved':True})
