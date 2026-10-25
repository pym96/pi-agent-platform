#!/usr/bin/env python3
"""Single bounded CPU entry point. Owns only its explicit project; retains volumes."""
import argparse,csv,hashlib,json,os,signal,subprocess,sys,threading,time,urllib.request
from pathlib import Path
from measurement import report
ROOT=Path(__file__).resolve().parents[3];PYTHON='python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1'
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--measure',action='store_true');p.add_argument('--build-host',action='store_true');a=p.parse_args()
OUT=Path(a.out).resolve();OUT.mkdir(parents=True,exist_ok=False);PROJECT=os.environ.get('NG_PROJECT','pi-ng15-b');OWNER=os.environ.get('NG_OWNER','builder')
assert PROJECT.startswith('pi-ng15-') and OWNER in ['builder','regulator','ci']
ENV=dict(os.environ,NG_EVIDENCE=str(OUT),NG_PROJECT=PROJECT,NG_OWNER=OWNER)
SHA=os.environ['SOURCE_SHA'];assert len(SHA)==40
serial=0;stop_sampling=threading.Event();sample_thread=None

def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')
def command(args,name=None,check=True,timeout=180,input=None,env=None,cwd=None):
    global serial
    serial+=1;name=name or f'command-{serial:03d}';started=time.time_ns()
    r=subprocess.run(args,cwd=cwd or ROOT,env=env or ENV,input=input,text=True,capture_output=True,timeout=timeout)
    (OUT/(name+'.stdout')).write_text(r.stdout);(OUT/(name+'.stderr')).write_text(r.stderr)
    with (OUT/'commands.jsonl').open('a') as f:f.write(json.dumps({'name':name,'command':args,'started_ns':started,'ended_ns':time.time_ns(),'exit_code':r.returncode})+'\n')
    if check and r.returncode:raise RuntimeError(f'{name} exit {r.returncode}: {r.stderr[-1200:]} {r.stdout[-1200:]}')
    return r

def compose(*args,**kw):return command(['docker','compose','-p',PROJECT,'-f','service/compose.nginx.yaml',*args],**kw)
def container(args,name,network='host',image=PYTHON,extra=(),check=True,timeout=180):
    return command(['docker','run','--rm','--name',PROJECT+'-'+name,'--label','ng.project='+PROJECT,'--label','workorder=15','--label','owner='+OWNER,'--label','source-sha='+SHA,'--cpus','1','--memory','2g','--network',network,'--read-only','--tmpfs','/tmp:size=256m','-v',str(ROOT)+':/source:ro','-v',str(OUT)+':/evidence','-v',str(Path(os.environ['NG_DEPS']).resolve())+':/deps:ro','-e','PYTHONPATH=/deps:/source','-e','PYTHONDONTWRITEBYTECODE=1','-e','NG_EVIDENCE=/evidence','-w','/source',*extra,'--entrypoint','timeout',image,'180',*args],name=name,check=check,timeout=timeout)

def ready(url):
    for _ in range(60):
        try:
            with urllib.request.urlopen(url,timeout=1) as r:
                if r.status==200:return
        except Exception:time.sleep(.5)
    raise RuntimeError('not ready '+url)

def pg(query,name):return compose('exec','-T','pg','psql','-U','pan','-d','pan','-X','-v','ON_ERROR_STOP=1','-At','-c',query,name=name)
def capture_db(name):
    return pg("SELECT json_build_object('sessions',(SELECT coalesce(json_agg(s ORDER BY id),'[]') FROM sessions s),'tasks',(SELECT coalesce(json_agg(t ORDER BY id),'[]') FROM tasks t),'events',(SELECT coalesce(json_agg(e ORDER BY id),'[]') FROM events e));",name).stdout

def sample():
    while not stop_sampling.is_set():
        r=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}'],capture_output=True,text=True,timeout=10)
        rows=[json.loads(x) for x in r.stdout.splitlines() if x.strip()];rows=[x for x in rows if x['Name'].startswith(PROJECT+'-')]
        with (OUT/'resources.jsonl').open('a') as f:f.write(json.dumps({'at_ns':time.time_ns(),'containers':rows})+'\n')
        stop_sampling.wait(1)

def measurements():
    cfg=json.loads((ROOT/'service/scripts/nginx-entry/config.json').read_text());points=[]
    for tool,levels in [('hey',cfg['hey_concurrency']),('vegeta',cfg['vegeta_rates'])]:
        for path in ['direct','proxy']:
            for level in levels:points.append({'index':len(points),'tool':tool,'path':path,'level':level,'planned':cfg['hey_requests'] if tool=='hey' else level*cfg['vegeta_seconds']})
    cfg['points']=points;cfg['source_sha']=SHA;save('measurement-config.json',cfg)
    toolroot=Path(os.environ['NG_TOOLS']).resolve()
    for path,base in cfg['paths'].items():
        rows=[]
        for i in range(cfg['warmup_per_path']):
            with urllib.request.urlopen(base+cfg['endpoint'],timeout=5) as r:rows.append({'index':i,'status':r.status,'body':r.read().decode()})
        save('warmup-'+path+'.json',rows)
    for point in points:
        d=OUT/f"point-{point['index']:02d}";d.mkdir();url=cfg['paths'][point['path']]+cfg['endpoint'];t=time.monotonic();started=time.time_ns()
        if point['tool']=='hey':
            args=['/tools/hey','-n',str(point['planned']),'-c',str(point['level']),'-t','5','-cpus','1','-disable-redirects','-o','csv',url]
            r=container(args,'point-'+str(point['index']),extra=['-v',str(toolroot)+':/tools:ro'],check=False);(d/'raw.csv').write_text(r.stdout)
        else:
            (d/'targets.txt').write_text('GET '+url+'\n');rel='/evidence/'+d.name
            args=['/tools/vegeta','attack','-targets',rel+'/targets.txt','-rate',str(point['level'])+'/s','-duration','10s','-timeout','5s','-http2=false','-keepalive=true','-redirects','0','-workers','1','-max-workers','32','-output',rel+'/raw.bin']
            r=container(args,'point-'+str(point['index']),extra=['-v',str(toolroot)+':/tools:ro'],check=False)
        ended=time.time_ns();elapsed=time.monotonic()-t
        (d/'stderr.txt').write_text(r.stderr)
        meta=dict(point,command=args,exit_code=r.returncode,started_ns=started,ended_ns=ended,elapsed_s=elapsed,source_sha=SHA)
        (d/'run.json').write_text(json.dumps(meta,indent=2))
        if point['tool']=='vegeta':
            for suffix,args2 in [('decoded.jsonl',['encode','-to=json']),('native-report.json',['report','-type=json'])]:
                rr=container(['/tools/vegeta',*args2,'/evidence/'+d.name+'/raw.bin'],'decode-'+str(point['index'])+'-'+suffix.split('.')[0],extra=['-v',str(toolroot)+':/tools:ro']);(d/suffix).write_text(rr.stdout)
        print('measurement',point,flush=True);time.sleep(cfg['idle_seconds'])
    runs=report(OUT)
    if any(x.get('invalid') or x['missing'] for x in runs):raise RuntimeError('invalid/missing measurement receipts')

def timeout_handler(*_):raise TimeoutError('full CPU invocation exceeded 15 minutes')
signal.signal(signal.SIGALRM,timeout_handler);signal.alarm(900)
signal.signal(signal.SIGTERM,timeout_handler)
status='failed'
try:
    for key in ['NODE_ROOT','PI_MODULES','NG_DEPS']:assert Path(os.environ[key]).is_dir(),key
    ports=command(['ss','-ltn'],name='ports-before').stdout
    if any(':'+str(port)+' ' in ports for port in range(18201,18210)):raise RuntimeError('owned port conflict')
    disk=os.statvfs(OUT);assert disk.f_bavail*disk.f_frsize>=20*1024**3,'less than 20GiB free'
    save('identity.json',{'source_sha':SHA,'config_sha256':hashlib.sha256((ROOT/'service/scripts/nginx-entry/config.json').read_bytes()).hexdigest(),'project':PROJECT,'owner':OWNER,'started_ns':time.time_ns(),'gpu_calls':0,'model':'synthetic fixture through actual Pi1.3.0','cpu_limit':6,'memory_limit_gib':10,'max_containers':6})
    command(['git','status','--porcelain'],name='source-status');command(['git','rev-parse','HEAD'],name='source-sha');command(['docker','images','--digests'],name='images-before')
    assert command(['git','rev-parse','HEAD']).stdout.strip()==SHA
    assert not command(['git','status','--porcelain','--untracked-files=no']).stdout.strip(),'tracked source dirty'
    # Docker cannot create a nested bind target beneath a read-only source bind.
    (ROOT/'service/pi/node_modules').mkdir(exist_ok=True)
    sdk=json.loads((Path(os.environ['PI_MODULES'])/'@earendil-works/pi-coding-agent/package.json').read_text());assert sdk['version']=='1.3.0','SDK version mismatch'
    save('dependency-identity.json',{'sdk_version':sdk['version'],'sdk_package_sha256':hashlib.sha256((Path(os.environ['PI_MODULES'])/'@earendil-works/pi-coding-agent/package.json').read_bytes()).hexdigest(),'lock_sha256':hashlib.sha256((ROOT/'service/pi/package-lock.json').read_bytes()).hexdigest(),'node_root':os.environ['NODE_ROOT']})
    compose('config',name='compose-config')
    command(['docker','image','inspect',PYTHON,'postgres@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24','nginx@sha256:30f1c0d78e0ad60901648be663a710bdadf19e4c10ac6782c235200619158284'],name='image-identities')
    if a.build_host:
        command(['go','build','-trimpath','-o','bin/service','./cmd/service'],name='build',env=dict(ENV,CGO_ENABLED='0',GOMAXPROCS='1'),cwd=ROOT/'service')
    else:
        args=['docker','run','--rm','--name',PROJECT+'-build','--label','ng.project='+PROJECT,'--label','workorder=15','--cpus','1','--memory','2g','--network','none','-v',str(ROOT)+':/source','-v',os.environ['GO_ROOT']+':/go:ro','-v',os.environ['GO_MOD_CACHE']+':/mod:ro','-v',os.environ['NG_BUILD_CACHE']+':/cache','-w','/source/service','-e','GOROOT=/go','-e','GOMODCACHE=/mod','-e','GOCACHE=/cache','-e','GOTOOLCHAIN=local','-e','GOENV=off','-e','GOMAXPROCS=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory','-e','GIT_CONFIG_VALUE_0=/source','--entrypoint','/bin/sh',os.environ['NG_BUILD_IMAGE'],'-c','CGO_ENABLED=0 /go/bin/go build -p 1 -trimpath -o bin/service ./cmd/service']
        command(args,name='build',timeout=180)
    compose('--profile','platform','up','-d',name='platform-start');ready('http://127.0.0.1:18202/health')
    compose('exec','-T','nginx','nginx','-v',name='nginx-version')
    compose('exec','-T','nginx','nginx','-t',name='nginx-test');compose('exec','-T','nginx','nginx','-T',name='nginx-effective')
    ids=compose('ps','-q').stdout.split();command(['docker','inspect',*ids],name='platform-inspect')
    pg('CREATE DATABASE ng_test','test-database-create')
    if a.build_host:
        hostenv=dict(ENV,TEST_DATABASE_URL=os.environ['NG_HOST_TEST_DATABASE_URL']);command(['go','test','-race','-count=1','-json','./...'],name='go-tests',env=hostenv,timeout=180,cwd=ROOT/'service') # CI host variant uses service cwd below
    else:
        testargs=args.copy();testargs[testargs.index('none')]=PROJECT+'_default';testargs[-1]='TEST_DATABASE_URL=postgres://pan:isolated-cpu-only@pg:5432/ng_test?sslmode=disable /go/bin/go test -p 1 -race -count=1 -json ./...'
        testargs[testargs.index(PROJECT+'-build')]=PROJECT+'-gotests';command(testargs,name='go-tests',timeout=240)
    gotest=(OUT/'go-tests.stdout').read_text();events=[json.loads(x) for x in gotest.splitlines() if x.startswith('{')];assert not any(x.get('Action')=='skip' for x in events),'required Go skip';assert any(x.get('Action')=='pass' and x.get('Test') for x in events),'zero Go tests'
    container(['python','service/inference/scripts/run_tests.py','--out','/evidence/inference'],'inference',timeout=180)
    unit=container(['python','-m','unittest','discover','-s','service/scripts/nginx-entry','-p','test_measurement.py'],'measurement-tests')
    assert 'Ran 0 tests' not in unit.stderr and 'Ran ' in unit.stderr and 'OK' in unit.stderr,'empty required measurement suite'
    container(['python','service/scripts/nginx-entry/test_entry.py'],'platform-tests',extra=['-e','NG_TEST_MODE=platform'])
    before=capture_db('database-before-singleton')
    probe=compose('run','--rm','--no-deps','--name',PROJECT+'-singleton','api',name='singleton-rejected',check=False)
    assert probe.returncode!=0 and 'another control-plane instance' in probe.stderr+probe.stdout
    after=capture_db('database-after-singleton');assert before==after,'singleton changed durable records';ready('http://127.0.0.1:18202/health')
    if a.measure:
        sample_thread=threading.Thread(target=sample,daemon=True);sample_thread.start();measurements();stop_sampling.set();sample_thread.join(timeout=12)
    capture_db('database-final')
    compose('logs','--no-color',name='platform-logs');compose('--profile','platform','stop',name='platform-stop')
    compose('--profile','lab','up','-d',name='lab-start');ready('http://127.0.0.1:18206/echo');ready('http://127.0.0.1:18207/echo')
    compose('exec','-T','nginx-lab','nginx','-T',name='lab-effective')
    container(['python','service/scripts/nginx-entry/test_entry.py'],'lab-tests',extra=['-e','NG_TEST_MODE=lab'])
    ids=compose('--profile','lab','ps','-q').stdout.split();command(['docker','inspect',*ids],name='lab-inspect')
    status='passed'
finally:
    signal.alarm(0);stop_sampling.set()
    if sample_thread:sample_thread.join(timeout=12)
    compose('--profile','platform','--profile','lab','logs','--no-color',name='all-logs',check=False)
    compose('--profile','platform','--profile','lab','down','--timeout','5',name='cleanup',check=False)
    owned=command(['docker','ps','-aq','--filter','label=ng.project='+PROJECT],name='extra-owned',check=False).stdout.split()
    if owned:command(['docker','stop','-t','3',*owned],name='extra-stop',check=False)
    remaining=command(['docker','ps','--filter','label=com.docker.compose.project='+PROJECT,'--format','{{.Names}}'],name='remaining-compose',check=False).stdout.strip()
    extra=command(['docker','ps','--filter','label=ng.project='+PROJECT,'--format','{{.Names}}'],name='remaining-extra',check=False).stdout.strip()
    save('summary.json',{'status':status,'source_sha':SHA,'remaining_owned_running':remaining.splitlines()+extra.splitlines(),'volumes':'preserved for diagnostics','gpu_calls':0,'measurement':a.measure})
    manifest={str(f.relative_to(OUT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.rglob('*')) if f.is_file() and f.name!='manifest.json'};save('manifest.json',manifest)
    if remaining or extra:raise RuntimeError('owned running resources remain')
