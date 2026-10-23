"""One CPU entry: actual Pi SDK + real dedicated PG + existing regressions.
No real model or GPU is invoked. Every required suite must collect and pass.
"""
import argparse,asyncio,json,os,re,shutil,socket,subprocess,sys,time,hashlib
from pathlib import Path
import aiohttp
import psycopg
from psycopg.conninfo import conninfo_to_dict
from analyze import analyze
REPO=Path(__file__).resolve().parents[3]

def execute(command,out,env=None,timeout=180):
    with out.open('w') as log:
        r=subprocess.run(command,cwd=REPO,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    if r.returncode:raise RuntimeError(f'command failed ({r.returncode}): {command}; see {out}')

def freeport():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

async def wait_ready(url,process):
    async with aiohttp.ClientSession() as c:
        for _ in range(200):
            if process.poll() is not None:raise RuntimeError('child exited before readiness')
            try:
                async with c.get(url) as r:
                    if r.status==200:return
            except aiohttp.ClientError:pass
            await asyncio.sleep(.1)
    raise RuntimeError('readiness deadline')

async def exercise(base,out):
    records=[]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as c:
        async def run(session,key,prompt,disconnect=False):
            start=time.monotonic()
            async with c.post(base+f'/sessions/{session}/tasks',json={'key':key,'prompt':prompt}) as r:
                assert r.status==202;task=await r.json()
            ack=time.monotonic();events=[];cursor=0
            async def read(stop_early=False):
                nonlocal cursor
                async with c.get(base+f'/sessions/{session}/events',headers={'Last-Event-ID':str(cursor)}) as r:
                    assert r.status==200;data=[]
                    async for line in r.content:
                        line=line.decode().strip()
                        if line.startswith('data: '):data.append(line[6:])
                        if not line and data:
                            e=json.loads('\n'.join(data));data=[]
                            assert e['id']>cursor;cursor=e['id']
                            if e['task']!=task['id']:continue
                            e['clientObserved']=time.monotonic();events.append(e)
                            if e['kind'] in ('completed','interrupted','cancelled'):return e['kind']
                            if stop_early and e['kind']=='text':return None
                raise AssertionError('SSE ended without terminal')
            status=await read(disconnect)
            if disconnect:
                assert status is None
                await asyncio.sleep(.7)
                status=await read()
            end=time.monotonic()
            async with c.get(base+f'/sessions/{session}/tasks') as r:history=await r.json()
            assert next(x for x in history if x['id']==task['id'])['status']==status
            # Durable idempotency: replay submit returns original identity, no new task.
            async with c.post(base+f'/sessions/{session}/tasks',json={'key':key,'prompt':prompt}) as r:
                again=await r.json();assert r.status==200 and again['id']==task['id']
            record={'task':task['id'],'session':session,'clock':'client-monotonic','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'submit':start,'ack':ack,'completed':end,'status':status,'events':events,'disconnected_and_replayed':disconnect}
            records.append(record)
            with (out/'client.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            return status
        assert await run('context','one','Say hello')=='completed'
        assert await run('context','two','What was my last request?')=='completed'
        assert await run('independent','one','SLOW reply',True)=='completed'
        assert await run('failure','one','STREAM_ERROR')=='interrupted'
        assert await run('limit','one','CONTEXT_LIMIT')=='interrupted'
    return records

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,GOMAXPROCS='2');children=[];logs=[];pg_started=False
    pgdata=out/'pgdata';pgport=freeport()
    try:
        for command in ['go','node','psql']:
            if not shutil.which(command):raise RuntimeError('missing required tool '+command)
        url=os.environ.get('TEST_DATABASE_URL')
        if not url:
            for command in ['initdb','pg_ctl','createdb']:
                if not shutil.which(command):raise RuntimeError('need TEST_DATABASE_URL or local '+command)
            execute(['initdb','-D',str(pgdata),'-A','trust','--no-locale','--encoding=UTF8'],out/'initdb.log',env)
            execute(['pg_ctl','-D',str(pgdata),'-l',str(out/'pg.log'),'-o',f'-h 127.0.0.1 -p {pgport} -k /tmp -c max_connections=32 -c shared_buffers=32MB','start'],out/'pg-start.log',env)
            pg_started=True
            execute(['createdb','-h','127.0.0.1','-p',str(pgport),'e2e12'],out/'createdb.log',env)
            url=f'postgresql://{os.environ.get("USER","postgres")}@127.0.0.1:{pgport}/e2e12?sslmode=disable'
        info=conninfo_to_dict(url)
        if not info.get('dbname','').startswith('e2e12'):raise RuntimeError('dedicated database name must begin e2e12')
        env['TEST_DATABASE_URL']=url
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        with psycopg.connect(url) as conn:
            version=conn.execute('select version()').fetchone()[0]
            tables=conn.execute("select count(*) from information_schema.tables where table_schema='public'").fetchone()[0]
            if tables:raise RuntimeError('dedicated database must start empty')
        paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard'],cwd=REPO,text=True).splitlines()
        source={p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in paths if p.startswith('service/') and (REPO/p).is_file()}
        (out/'source-manifest.json').write_text(json.dumps(source,indent=2,sort_keys=True))
        (out/'run.json').write_text(json.dumps({'kind':'synthetic','commit':commit,'worktree_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)),'source_manifest_sha256':hashlib.sha256((out/'source-manifest.json').read_bytes()).hexdigest(),'workload':{'sessions':4,'tasks':5,'success':3,'errors':2,'output_budget':128,'actual_model':'synthetic protocol fixture'},'resources':{'GOMAXPROCS':2,'GPU':False},'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'postgres':version,'node':subprocess.check_output(['node','--version'],text=True).strip(),'go':subprocess.check_output(['go','version'],text=True).strip()},indent=2))
        with (out/'go-tests.jsonl').open('w') as f:
            r=subprocess.run(['go','test','-race','-json','./...'],cwd=REPO/'service',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
        go=[json.loads(x) for x in (out/'go-tests.jsonl').read_text().splitlines() if x.startswith('{')]
        assert r.returncode==0 and any(x.get('Action')=='pass' and x.get('Test') for x in go) and not any(x.get('Action')=='fail' or (x.get('Action')=='skip' and x.get('Test')) for x in go)
        for package in ['cmd/load','internal/api','internal/store','internal/executor']:
            assert any(x.get('Action')=='pass' and x.get('Test') and x.get('Package','').endswith('/'+package) for x in go)
        execute(['node','--test','--test-reporter=tap','service/pi/tests/wire.test.mjs'],out/'sdk-tests.log',env)
        tap=(out/'sdk-tests.log').read_text();assert re.search(r'# tests [1-9]',tap) and '# fail 0' in tap and '# skipped 0' in tap
        execute([sys.executable,'service/inference/scripts/run_tests.py','--out',str(out/'inference')],out/'inference-tests.log',env)
        with (out/'build.log').open('w') as f:
            subprocess.run(['go','build','-o',str(out/'api'),'./cmd/service'],cwd=REPO/'service',env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
        with psycopg.connect(url) as conn:conn.execute('TRUNCATE events,tasks,sessions CASCADE')
        mp,pp,ap=freeport(),freeport(),freeport()
        def start(command,name,extra):
            f=(out/(name+'.log')).open('w');logs.append(f);proc=subprocess.Popen(command,cwd=REPO,env=dict(env,**extra),stdout=f,stderr=subprocess.STDOUT);children.append(proc);return proc
        model=start(['node','service/scripts/pi-qwen-e2e/fixture.mjs'],'fixture',{'FIXTURE_PORT':str(mp),'FIXTURE_TRACE':str(out/'fixture.jsonl')})
        asyncio.run(wait_ready(f'http://127.0.0.1:{mp}/health',model))
        pi=start(['node','service/pi/server.mjs'],'pi',{'PI_DATA':str(out/'pi-data'),'PI_PORT':str(pp),'PI_HOST':'127.0.0.1','PI_TRACE':str(out/'bridge.jsonl'),'MODEL_URL':f'http://127.0.0.1:{mp}/v1','MODEL_ID':'Qwen3-8B','MODEL_KIND':'qwen'})
        asyncio.run(wait_ready(f'http://127.0.0.1:{pp}/metrics',pi))
        api=start([str(out/'api')],'api',{'DATABASE_URL':url,'PI_URL':f'http://127.0.0.1:{pp}','MODEL_KIND':'qwen','API_ADDR':f'127.0.0.1:{ap}'})
        asyncio.run(wait_ready(f'http://127.0.0.1:{ap}/health',api))
        records=asyncio.run(exercise(f'http://127.0.0.1:{ap}',out))
        fixture=[json.loads(x) for x in (out/'fixture.jsonl').read_text().splitlines()]
        assert len(fixture)==5
        assert [m['role'] for m in fixture[1]['request']['messages']]==['system','user','assistant','user']
        assert len(fixture[2]['request']['messages'])==2
        with psycopg.connect(url) as conn:
            rows=conn.execute('select row_to_json(e) from events e order by id').fetchall()
            (out/'pg-events.json').write_text(json.dumps([x[0] for x in rows],indent=2))
        go_trace=[]
        for line in (out/'api.log').read_text().splitlines():
            if '{' in line:
                try:row=json.loads(line[line.index('{'):])
                except ValueError:continue
                if row.get('clock')=='go-since-claim':go_trace.append(row)
        (out/'go-trace.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in go_trace))
        summary=analyze(out);(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
        # Required negative measurement oracle: damaging a local monotonic timestamp must fail.
        original=(out/'client.jsonl').read_text();bad=json.loads(original.splitlines()[0]);bad['ack']=bad['submit']-1
        (out/'client.jsonl').write_text(json.dumps(bad)+'\n'+'\n'.join(original.splitlines()[1:])+'\n')
        rejected=False
        try:analyze(out)
        except AssertionError:rejected=True
        finally:(out/'client.jsonl').write_text(original)
        assert rejected
        (out/'measurement-negative.json').write_text(json.dumps({'negative_timestamp_rejected':True}))
        (out/'PASS').write_text('all required CPU suites and actual SDK / PG chain passed; synthetic only\n')
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:child.wait(10)
                except subprocess.TimeoutExpired:child.kill();child.wait()
        for f in logs:f.close()
        if pg_started:execute(['pg_ctl','-D',str(pgdata),'-m','fast','stop'],out/'pg-stop.log',env)
        (out/'cleanup.json').write_text(json.dumps({'owned_processes_stopped':all(c.poll() is not None for c in children),'owned_pg_stopped':not pg_started or not (pgdata/'postmaster.pid').exists()}))
if __name__=='__main__':main()
