"""Behavioral contract tests against real HTTP endpoints, not mocked Nginx."""
import http.client,json,os,time,unittest,uuid,urllib.parse
from pathlib import Path
MODE=os.environ.get('NG_TEST_MODE','platform');OUT=Path(os.environ['NG_EVIDENCE']);OUT.mkdir(parents=True,exist_ok=True)
DIRECT='http://127.0.0.1:18201';PROXY='http://127.0.0.1:18202';LAB='http://127.0.0.1:18205'
def record(kind,**data):
    with (OUT/'client.jsonl').open('a') as f:f.write(json.dumps({'kind':kind,'at_ns':time.time_ns(),**data})+'\n');f.flush();os.fsync(f.fileno())
def request(base,path,body=None,headers=None,method=None):
    u=urllib.parse.urlsplit(base);c=http.client.HTTPConnection(u.hostname,u.port,timeout=10)
    raw=None if body is None else json.dumps(body).encode();h={'Content-Type':'application/json',**(headers or {})}
    c.request(method or ('POST' if body is not None else 'GET'),path,body=raw,headers=h);r=c.getresponse();data=r.read();status=r.status;c.close()
    try:value=json.loads(data)
    except ValueError:value=data.decode(errors='replace')
    record('http',base=base,path=path,method=method or ('POST' if body is not None else 'GET'),request=body,request_headers=h,status=status,response=value)
    return status,value

def wait_task(base,session,status='completed'):
    until=time.monotonic()+30
    while time.monotonic()<until:
        code,tasks=request(base,'/sessions/'+session+'/tasks')
        if code==200 and tasks and tasks[-1]['status']==status:return tasks
        time.sleep(.05)
    raise AssertionError(('task timeout',status,tasks))

def open_stream(base,path,headers=None,timeout=4):
    u=urllib.parse.urlsplit(base);c=http.client.HTTPConnection(u.hostname,u.port,timeout=timeout);c.request('GET',path,headers=headers or {});r=c.getresponse()
    if r.status!=200:raise AssertionError(('stream status',r.status,r.read()))
    return c,r

def event(r):
    fields={}
    while True:
        raw=r.readline()
        if not raw:raise EOFError('stream ended before expected event')
        line=raw.decode().rstrip('\r\n')
        if not line:
            if fields:return fields
            continue
        if line.startswith(':'):continue
        key,_,value=line.partition(':');fields[key]=value.lstrip(' ')

def retained(base,session,end,cursor=0):
    c,r=open_stream(base,'/sessions/'+session+'/events',{'Last-Event-ID':str(cursor)});items=[]
    try:
        while True:
            item=event(r);payload=json.loads(item['data']);items.append(payload)
            if payload['id']==end:break
    finally:c.close()
    record('sse',base=base,session=session,cursor=cursor,end=end,events=items)
    return items

class PlatformTests(unittest.TestCase):
    def test_01_actual_sdk_identity_idempotency_and_replay(self):
        session='ng-'+uuid.uuid4().hex[:12];p='/sessions/'+session+'/tasks';body={'key':'one','prompt':'hello'}
        before=request('http://127.0.0.1:18203','/metrics')[1]['requests']
        code,task=request(PROXY,p,body);self.assertEqual(code,202)
        duplicate_code,duplicate=request(DIRECT,p,body);self.assertEqual(duplicate_code,200);self.assertEqual(duplicate['id'],task['id'])
        self.assertEqual(request(PROXY,p,dict(body,prompt='different'))[0],409)
        tasks=wait_task(PROXY,session);self.assertEqual(tasks,request(DIRECT,p)[1])
        self.assertEqual(request('http://127.0.0.1:18203','/metrics')[1]['requests'],before+1)
        c,r=open_stream(PROXY,'/sessions/'+session+'/events');items=[]
        try:
            while True:
                payload=json.loads(event(r)['data']);items.append(payload)
                if payload['kind']=='completed':break
        finally:c.close()
        end=items[-1]['id'];self.assertEqual(items,retained(DIRECT,session,end));cursor=items[len(items)//2]['id']
        self.assertEqual(retained(PROXY,session,end,cursor),[x for x in items if x['id']>cursor])
        record('platform-retained',session=session,task=tasks[0],events=items)
        result=next(x for x in items if x['kind']=='result');self.assertIn('Synthetic reply',result['data']['text'])
        self.assertEqual(request(PROXY,p,{'key':'two','prompt':'second turn'})[0],202)
        tasks=wait_task(PROXY,session);self.assertEqual(len(tasks),2)
        record('platform-context',session=session,tasks=tasks)
    def test_02_input_boundaries_match_direct(self):
        s='boundary-'+uuid.uuid4().hex[:8]
        for body in ({'key':'x','prompt':''},{'key':'x','prompt':'x'*8193},{'key':'x','prompt':'x'*40000},{'key':'!','prompt':'x'},{'key':'x','prompt':'x','unknown':True}):
            statuses=[request(b,'/sessions/'+s+'/tasks',body)[0] for b in [DIRECT,PROXY]];self.assertEqual(statuses,[400,400])
        for cursor in ['-1','bad']:
            self.assertEqual([request(b,'/sessions/'+s+'/events',headers={'Last-Event-ID':cursor})[0] for b in [DIRECT,PROXY]],[400,400])
    def test_03_disconnect_preserves_durable_task_and_failure(self):
        s='detach-'+uuid.uuid4().hex[:8];p='/sessions/'+s+'/tasks'
        self.assertEqual(request(PROXY,p,{'key':'one','prompt':'SLOW_MODEL hello'})[0],202)
        c,r=open_stream(PROXY,'/sessions/'+s+'/events');event(r);c.close();record('client-disconnect',session=s)
        self.assertEqual(wait_task(PROXY,s)[0]['status'],'completed')
        fault='fault-'+uuid.uuid4().hex[:8];p='/sessions/'+fault+'/tasks'
        self.assertEqual(request(PROXY,p,{'key':'one','prompt':'FAIL_MODEL'})[0],202)
        self.assertEqual(wait_task(PROXY,fault,'interrupted')[0]['status'],'interrupted')
        self.assertEqual(request(PROXY,p,{'key':'two','prompt':'hello'})[0],429)

class LabTests(unittest.TestCase):
    def test_01_round_robin_with_request_receipts(self):
        ids=[];backends=[]
        for _ in range(12):
            rid='rr-'+uuid.uuid4().hex;ids.append(rid);code,data=request(LAB,'/echo',headers={'X-Request-ID':rid});self.assertEqual(code,200);self.assertEqual(data['id'],rid);backends.append(data['backend'])
        self.assertEqual(set(backends),{'A','B'});self.assertTrue(all(a!=b for a,b in zip(backends,backends[1:])))
        logs=sum([request('http://127.0.0.1:'+str(p),'/control/ledger')[1] for p in [18206,18207]],[])
        for rid,b in zip(ids,backends):self.assertEqual([(x['id'],x['backend']) for x in logs if x['id']==rid and x['kind']=='received'],[(rid,b)])
        record('round-robin',ids=ids,backends=backends)
    def test_02_marker_precedes_independent_release(self):
        rid='gate-'+uuid.uuid4().hex;c,r=open_stream(LAB,'/stream?id='+rid,{'X-Request-ID':rid},timeout=3)
        try:
            marker=event(r);self.assertEqual(marker['event'],'marker');data=json.loads(marker['data']);self.assertEqual(data['id'],rid)
            record('marker-observed-before-release',id=rid,backend=data['backend'])
            port=18206 if data['backend']=='A' else 18207
            self.assertEqual(request('http://127.0.0.1:'+str(port),'/control/release?id='+rid)[0],200)
            terminal=event(r);self.assertEqual(terminal['event'],'terminal');self.assertEqual(json.loads(terminal['data'])['id'],rid)
            record('terminal-observed',id=rid)
        finally:c.close()
        logs=request('http://127.0.0.1:'+str(port),'/control/ledger')[1];seq=[x['kind'] for x in logs if x['id']==rid];self.assertEqual(seq,['received','marker','release','terminal'])
    def test_03_received_post_drop_is_not_retried(self):
        rid='drop-'+uuid.uuid4().hex;code,data=request(LAB,'/drop',{'synthetic':'non-idempotent'},headers={'X-Request-ID':rid})
        self.assertEqual(code,502)
        logs=sum([request('http://127.0.0.1:'+str(p),'/control/ledger')[1] for p in [18206,18207]],[])
        self.assertEqual(len([x for x in logs if x['id']==rid and x['kind']=='received']),1)
    def test_04_failure_recovery_and_truncation(self):
        self.assertEqual(request('http://127.0.0.1:18206','/control/fail?enabled=1')[0],200)
        statuses=[request(LAB,'/echo',headers={'X-Request-ID':'fault-'+uuid.uuid4().hex})[0] for _ in range(4)]
        self.assertEqual(sorted(statuses),[200,200,503,503])
        self.assertEqual(request('http://127.0.0.1:18206','/control/fail?enabled=0')[0],200)
        self.assertEqual([request(LAB,'/echo',headers={'X-Request-ID':'recover-'+uuid.uuid4().hex})[0] for _ in range(4)],[200]*4)
        c,r=open_stream(LAB,'/truncate')
        with self.assertRaises((http.client.IncompleteRead,ConnectionError)):r.read()
        c.close();record('truncated-stream-detected')

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PlatformTests if MODE=='platform' else LabTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'mode':MODE,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    (OUT/(MODE+'-tests.json')).write_text(json.dumps(summary,indent=2));raise SystemExit(0 if result.wasSuccessful() and result.testsRun>0 and not result.skipped else 1)
