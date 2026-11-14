"""Bounded direct-HTTP scheduling, raw streaming receipts and logical drain.

Client monotonic_ns owns latency and interval math. Model traces are correlated by
attempt/call ordering, never subtracted from client timestamps.
"""
import asyncio,base64,hashlib,json,resource,time
from pathlib import Path
import aiohttp
from measurement import inspect_exchange,summarize

def dump(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def load_lines(path):
    p=Path(path)
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def core(payload):return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

async def request(session,url,slot,out,planned_ns,deadline_ns):
    row={'id':slot['id'],'payload':slot['payload'],'expected_input_ids':slot.get('expected_input_ids'),
         'planned_ns':planned_ns,'sent_ns':None,'terminal_ns':None,'status':None,'chunks':[],'eof':False,
         'actual_input_ids':None,'actual_output_ids':None,'usage':None,'not_prepared_reason':None,'not_invoked_reason':None}
    path=out/(slot['id']+'.jsonl')
    def record(event):
        with path.open('a') as f:f.write(json.dumps(event)+'\n')
    record({'event':'planned','slot':slot,'at_ns':time.monotonic_ns()})
    ready=time.monotonic_ns();row['send_lateness_ns']=max(0,ready-planned_ns)
    if ready>=deadline_ns:
        row.update(classification='generator_drop',reason='absolute_deadline',terminal_ns=ready,
                   not_prepared_reason='generator_drop',not_invoked_reason='generator_drop')
        record({'event':'terminal','row':row});return row
    try:
        remaining=(deadline_ns-time.monotonic_ns())/1e9
        if remaining<=0:
            row.update(classification='generator_drop',reason='absolute_deadline',not_prepared_reason='generator_drop',not_invoked_reason='generator_drop')
            return row
        row['sent_ns']=time.monotonic_ns()
        context=session.post(url+'/v1/chat/completions',json=slot['payload'],timeout=aiohttp.ClientTimeout(total=remaining))
        record({'event':'send','at_ns':row['sent_ns']})
        async with context as response:
            row['status']=response.status;record({'event':'headers','at_ns':time.monotonic_ns(),'status':response.status,'headers':dict(response.headers)})
            async for data in response.content.iter_any():
                chunk={'at_ns':time.monotonic_ns(),'data_b64':base64.b64encode(data).decode()};row['chunks'].append(chunk);record({'event':'chunk',**chunk})
            row['eof']=True
            row['terminal_ns']=time.monotonic_ns();record({'event':'eof','at_ns':row['terminal_ns']})
        row.update(inspect_exchange(row['status'],row['chunks'],True,row['expected_input_ids'],None))
        if row['status']!=200:
            try:row['http_error']=json.loads(b''.join(base64.b64decode(c['data_b64']) for c in row['chunks']))
            except (ValueError,TypeError):row['http_error']=None
    except (asyncio.TimeoutError,TimeoutError):
        record({'event':'transport_failure','kind':'timeout','at_ns':time.monotonic_ns()});row.update(classification='timeout',reason='client_deadline')
    except (aiohttp.ClientError,OSError) as exc:
        record({'event':'transport_failure','kind':'unresolved','detail':repr(exc),'at_ns':time.monotonic_ns()});row.update(classification='unresolved',reason=repr(exc))
    finally:
        if row['terminal_ns'] is None:row['terminal_ns']=time.monotonic_ns()
        record({'event':'terminal','row':row})
    return row

async def run_point(session,url,point,out,deadline_ns):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic_ns();cpu_start=time.process_time_ns();rows=[];pending=set()
    offer_end=start+point.get('offer_end_ns',0)
    limit=min(deadline_ns,(offer_end+point.get('drain_limit_ns',0)) if point['mode']=='open' else start+point['total_limit_ns'])
    def drop(slot,planned,reason):
        row={'id':slot['id'],'payload':slot['payload'],'expected_input_ids':slot.get('expected_input_ids'),
             'planned_ns':planned,'sent_ns':None,'terminal_ns':time.monotonic_ns(),'classification':'generator_drop',
             'reason':reason,'actual_input_ids':None,'actual_output_ids':None,'usage':None,
             'not_prepared_reason':'generator_drop','not_invoked_reason':'generator_drop'}
        dump(out/(slot['id']+'.drop.json'),row);rows.append(row)
    async def collect(wait=False):
        nonlocal pending
        if pending:
            done,pending=await asyncio.wait(pending,return_when=asyncio.FIRST_COMPLETED if wait else asyncio.ALL_COMPLETED,
                                            timeout=None if wait else 0)
            rows.extend(t.result() for t in done)
    if point['mode']=='open':
        if len(point['offset_ns'])!=len(point['slots']) or point['offset_ns']!=sorted(point['offset_ns']):raise ValueError('frozen offset cardinality/order')
        for slot,offset in zip(point['slots'],point['offset_ns']):
            planned=start+offset;await asyncio.sleep(max(0,(min(planned,limit)-time.monotonic_ns())/1e9));await collect()
            if time.monotonic_ns()>=limit:drop(slot,planned,'absolute_deadline')
            elif len(pending)>=point['max_inflight']:drop(slot,planned,'max_inflight')
            else:pending.add(asyncio.create_task(request(session,url,slot,out,planned,limit)))
    elif point['mode']=='closed':
        for slot in point['slots']:
            if len(pending)>=point['concurrency']:await collect(wait=True)
            planned=time.monotonic_ns()
            if planned>=limit:drop(slot,planned,'absolute_deadline')
            else:pending.add(asyncio.create_task(request(session,url,slot,out,planned,limit)))
    else:raise ValueError('open/closed mode required')
    if pending:rows.extend(await asyncio.gather(*pending))
    if point['mode']=='open':await asyncio.sleep(max(0,(min(offer_end,limit)-time.monotonic_ns())/1e9))
    order={s['id']:i for i,s in enumerate(point['slots'])};rows.sort(key=lambda r:order[r['id']])
    result={'point':point,'start_ns':start,'offer_end_ns':offer_end,'rows':rows,'client_cpu_ns':time.process_time_ns()-cpu_start,
            'client_maxrss_raw':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'client_platform':__import__('sys').platform}
    dump(out/'response-ledger.json',result)
    return result

def reconcile(result,app,native,arm,attempt_start,attempt_end):
    """Native call ordinal maps to app execution ordinal under immutable single slot."""
    executed=[r['attempt'] for r in app if r['event']=='execute_start']
    prepared=[r['attempt'] for r in app if r['event']=='prepared']
    validations={r['attempt']:r for r in app if r['event']=='validated'}
    traces={}
    if arm=='A':
        inputs=[r for r in native if r['event']=='tf_prepare']
        if len(inputs)!=len(prepared):raise ValueError('TF prepared trace cardinality')
        for attempt,entry in zip(prepared,inputs):traces[attempt]={'input_ids':entry['input_ids']}
        seen_calls=set()
        for entry in native:
            if entry['event']=='tf_settled':
                call=entry['call']
                if call in seen_calls:raise ValueError('duplicate TF settlement')
                seen_calls.add(call)
                if 0<call<=len(executed):traces.setdefault(executed[call-1],{}).update(output_ids=entry['output_ids'],finish_reason=entry['finish_reason'],text=entry['text'])
        if seen_calls!=set(range(1,len(executed)+1)):raise ValueError('TF generation settlement trace missing')
    else:
        if any(r['event']=='native_settlement_unknown' for r in native):raise ValueError('native settlement unknown')
        starts={r['native_id']:r for r in native if r['event']=='native_start'}
        if len(starts)!=len(executed) or len(starts)!=sum(r['event']=='native_start' for r in native):raise ValueError('native/app invocation cardinality')
        for ident,entry in starts.items():
            call=entry['calls']
            if not 0<call<=len(executed):raise ValueError('native/app call ordinal')
            attempt=executed[call-1];traces[attempt]={'input_ids':entry['prompt_token_ids']}
            terminal=[r for r in native if r['event']=='native_output' and r['native_id']==ident and r['finished']]
            if len(terminal)>1:raise ValueError('duplicate native terminal')
            settled=[r for r in native if r['event']=='native_settled' and r['native_id']==ident]
            if len(settled)!=1 or settled[0]['active']!=0:raise ValueError('native logical settlement missing')
            if settled[0]['aborted'] and not all(any(r['event']==event and r['native_id']==ident for r in native) for event in ('abort_sent','scheduler_abort_ack')):raise ValueError('native abort ACK trace missing')
            if terminal:traces[attempt].update(output_ids=terminal[0]['token_ids'],finish_reason=terminal[0]['finish_reason'],text=terminal[0]['text'])
    used=set()
    for row in result['rows']:
        if row['sent_ns'] is None:continue
        matches=[a for a,v in validations.items() if attempt_start<a<=attempt_end and v['core_hash']==core(row['payload'])]
        if len(matches)!=1 or matches[0] in used:raise ValueError('unique payload/attempt correlation missing')
        attempt=matches[0];used.add(attempt);row['app_attempt']=attempt;truth=traces.get(attempt)
        row['actual_input_ids']=None if truth is None else truth.get('input_ids')
        row['actual_output_ids']=None if truth is None else truth.get('output_ids')
        if attempt in prepared and row['actual_input_ids']!=row['expected_input_ids']:raise ValueError('actual prepared IDs missing/different')
        if attempt not in prepared:row['not_prepared_reason']=row.get('http_error',{}).get('error',{}).get('code','not-prepared')
        if attempt not in executed:row['not_invoked_reason']='not-invoked'
        if row.get('status')==200 and row.get('eof'):
            row.update(inspect_exchange(row['status'],row['chunks'],True,row['expected_input_ids'],truth))
    return result

async def drain(session,url,app_path,expected_attempts,deadline_ns,out):
    receipts=[]
    while time.monotonic_ns()<deadline_ns:
        at=time.monotonic_ns()
        try:
            async with session.get(url+'/health',timeout=aiohttp.ClientTimeout(total=1)) as response:
                raw=await response.read();receipt={'at_ns':time.monotonic_ns(),'query_start_ns':at,'status':response.status,'headers':dict(response.headers),'body_b64':base64.b64encode(raw).decode()};receipts.append(receipt);dump(out,receipts)
                if response.status!=200:raise ValueError('health status')
                health=json.loads(raw);receipt['health']=health
                if any(type(health[k]) is not int or health[k]<0 for k in ('attempts','calls','active_generation','queued')):raise RuntimeError('health counter type unknown')
            app=load_lines(app_path)
            acquired={r['attempt'] for r in app if r['event']=='slot_acquired'}
            settled={r['attempt'] for r in app if r['event']=='settled'}
            receipt.update(at_ns=time.monotonic_ns(),acquired=sorted(acquired),settled=sorted(settled));dump(out,receipts)
            if any(r['event']=='settlement_unknown' for r in app):raise RuntimeError('explicit unknown settlement')
            if health['attempts']==expected_attempts and health['active_generation']==0 and health['queued']==0 and health['ready'] is True and acquired<=settled:
                dump(out,receipts);return receipt['at_ns']
        except (aiohttp.ClientError,OSError,ValueError) as exc:receipts.append({'at_ns':time.monotonic_ns(),'error':repr(exc)})
        dump(out,receipts);await asyncio.sleep(.05)
    raise RuntimeError('drain unknown/deadline')

async def run_block(session,url,block,out,deadline_ns):
    out=Path(out);attempts=0;report={'id':block['id'],'arm':block['arm'],'points':[],'nonformal':[],
                                  'complete':False,'completion_POST':0,'native_calls':None}
    async def one(point,formal=False):
        nonlocal attempts
        before=attempts;destination=out/point['name']
        result=await run_point(session,url,point,destination,deadline_ns)
        attempts+=sum(r['sent_ns'] is not None for r in result['rows']);report['completion_POST']=attempts
        report['points' if formal else 'nonformal'].append(result);dump(out/'block-report.json',report)
        settled=await drain(session,url,out/'model-trace.jsonl',attempts,deadline_ns,destination/'drain.json')
        app=load_lines(out/'model-trace.jsonl');native=load_lines(out/('tf-trace.jsonl' if block['arm']=='A' else 'native-trace.jsonl'))
        reconcile(result,app,native,block['arm'],before,attempts)
        result['summary']=summarize(result['rows'],result['start_ns'],result['offer_end_ns'],settled)
        result['attempt_start']=before;result['attempt_end']=attempts
        dump(destination/'ledger.json',result);dump(out/'block-report.json',report)
        if any(r['classification']=='unresolved' for r in result['rows']):raise RuntimeError('unknown exchange; partial preserved')
        if not formal and any(r['classification']!='completed' for r in result['rows']):raise RuntimeError('warmup/calibration/recovery not successful')
        return result
    await one({'name':'warmup','mode':'closed','concurrency':1,'total_limit_ns':600*10**9,'slots':block['warmup']})
    for point in block['points']:
        await one(point,formal=point['name']!='calibration')
        if point['name']=='calibration' and any(r['classification']!='completed' for r in report['nonformal'][-1]['rows']):raise RuntimeError('pilot calibration unsuccessful')
        await one({'name':point['name']+'-recovery','mode':'closed','concurrency':1,'total_limit_ns':90*10**9,'slots':[block['recovery_slot']]})
    async with session.get(url+'/health',timeout=aiohttp.ClientTimeout(total=1)) as response:health=await response.json()
    report.update(complete=True,native_calls=health['calls'],final_health=health)
    dump(out/'block-report.json',report);return report
