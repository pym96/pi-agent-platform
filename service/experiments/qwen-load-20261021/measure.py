"""Opt-in streaming measurement; monotonic timestamps are seconds from run start.

No HTTP-200 shortcut: success requires terminal finish_reason, DONE, valid actual
usage and nonempty generated content. Raw SSE lines remain in every record.
"""
import argparse, asyncio, hashlib, json, math, pathlib, time
import aiohttp


def classify(record):
    events = record.get('events', [])
    first = None
    finish = None
    usage = None
    done = False
    error = record.get('error')
    for event in events:
        if not isinstance(event.get('t'),(int,float)) or not 0<=event['t']<=105:
            error = 'event_outside_run_bound'
            continue
        line = event['line']
        if not line.startswith('data:'):
            continue
        data = line[5:].strip()
        if data == '[DONE]':
            done = True
            continue
        try:
            obj = json.loads(data)
        except (ValueError, TypeError):
            error = 'malformed_sse'
            continue
        if not isinstance(obj,dict) or not isinstance(obj.get('choices',[]),list):
            error = 'malformed_sse_object'
            continue
        if obj.get('error'):
            error = 'backend_error'
        if obj.get('usage') is not None:
            usage = obj['usage']
        for choice in obj.get('choices', []):
            if not isinstance(choice,dict) or not isinstance(choice.get('delta',{}),dict):
                error = 'malformed_sse_choice'
                continue
            content = choice.get('delta', {}).get('content')
            if isinstance(content, str) and content and first is None:
                first = event['t']
            if choice.get('finish_reason') is not None:
                finish = choice['finish_reason']
    valid_usage = isinstance(usage, dict) and all(
        isinstance(usage.get(k), int) and not isinstance(usage.get(k), bool)
        and usage[k] >= 0 for k in ['prompt_tokens', 'completion_tokens', 'total_tokens'])
    if valid_usage:
        valid_usage = (usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
                       and usage['completion_tokens'] > 0)
    success = (record.get('http_status') == 200 and error is None and done
               and isinstance(record.get('done'),(int,float)) and 0<=record['done']<=105
               and isinstance(record.get('send'),(int,float)) and 0<=record['send']<45
               and finish in ['stop', 'length'] and first is not None and valid_usage)
    send = record.get('send')
    return dict(success=success, first=first, finish_reason=finish, usage=usage,
                valid_usage=valid_usage, done=done, error=error,
                ttft_s=(first-send if first is not None and send is not None else None),
                e2e_s=(record['done']-send if success else None))


def nearest(values, p):
    values = sorted(x for x in values if x is not None)
    return values[math.ceil(p*len(values))-1] if values else None


def summarize(run, records):
    classified = [(r, classify(r)) for r in records if r.get('send') is not None]
    success = [(r, c) for r, c in classified if c['success']]
    window = [(r, c) for r, c in success if r['done'] < run['window_s']]
    latencies = {}
    for key in ['ttft_s', 'e2e_s']:
        values = [c[key] for _, c in classified if c[key] is not None]
        latencies[key] = dict(n=len(values), missing=len(classified)-len(values),
                             p50=nearest(values,.5), p95=nearest(values,.95), p99=nearest(values,.99))
    return dict(run=run['id'], mode=run['mode'], load=run['load'], rep=run['rep'],
                window_s=run['window_s'], actual_window_s=run['actual_window_s'],
                valid=abs(run['actual_window_s']-run['window_s'])/run['window_s'] <= .01,
                planned=len(records), sent=len(classified), success=len(success),
                failures=len(classified)-len(success),
                timeout=sum(r.get('error')=='timeout' for r,c in classified),
                partial=sum(c['first'] is not None and not c['success'] for r,c in classified),
                generator_admission_drop=sum(r.get('drop') is not None for r in records),
                unresolved=sum(r.get('done') is None for r in records if r.get('send') is not None),
                window_success=len(window), window_req_s=len(window)/run['window_s'],
                window_output_tokens=sum(c['usage']['completion_tokens'] for r,c in window),
                window_tokens_s=sum(c['usage']['completion_tokens'] for r,c in window)/run['window_s'],
                actual_send_rate=len(classified)/run['window_s'], total_elapsed_s=run['total_elapsed_s'],
                cohort_req_s=len(success)/run['total_elapsed_s'],
                cohort_output_tokens=sum(c['usage']['completion_tokens'] for r,c in success),
                ttft_status_counts=dict(success=sum(c['first'] is not None and c['success'] for r,c in classified),
                    failed=sum(c['first'] is not None and not c['success'] for r,c in classified)),
                latency=latencies)


async def execute(args):
    out=pathlib.Path(args.output); out.mkdir(parents=True,exist_ok=False)
    config=json.loads(pathlib.Path(args.config).read_text())
    corpus=config['corpus']
    run=dict(id=args.run,mode=args.mode,load=args.load,rep=args.rep,window_s=45.,
             timeout_s=60.,max_drain_s=60.,client_cap=64,config_sha256=hashlib.sha256(pathlib.Path(args.config).read_bytes()).hexdigest(),
             code_sha=args.code_sha,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    records=[]; start=time.monotonic(); seq=0; active=set()
    def now(): return time.monotonic()-start
    raw=(out/'requests.jsonl').open('w')
    def save(r):
        records.append(r);raw.write(json.dumps(r,ensure_ascii=False)+'\n');raw.flush()
    timeout=aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout, connector=aiohttp.TCPConnector(limit=64)) as session:
        async def request(planned,ident):
            r=dict(id=f'{args.run}-{ident}',prompt_index=ident%len(corpus),planned=planned,
                   send=now(),events=[],http_status=None,error=None)
            payload=dict(model=config['served_model'],messages=[dict(role='user',content=corpus[ident%len(corpus)])],
                         max_tokens=128,temperature=0,seed=20261021,stream=True,
                         stream_options=dict(include_usage=True),chat_template_kwargs=dict(enable_thinking=False))
            try:
                async with session.post(args.url+'/v1/chat/completions',json=payload) as response:
                    r['http_status']=response.status
                    async for line in response.content:
                        r['events'].append(dict(t=now(),line=line.decode('utf-8',errors='replace').rstrip('\r\n')))
            except asyncio.TimeoutError: r['error']='timeout'
            except asyncio.CancelledError: r['error']='drain_cancelled'
            except Exception as e: r['error']=f'{type(e).__name__}: {e}'
            r['done']=now();save(r)
        async def worker():
            nonlocal seq
            while now()<45:
                ident=seq;seq+=1
                await request(now(),ident)
        if args.mode=='closed':
            active={asyncio.create_task(worker()) for _ in range(int(args.load))}
            await asyncio.sleep(max(0,45-now()))
        else:
            while True:
                planned=seq/args.load
                if planned>=45:break
                await asyncio.sleep(max(0,planned-now()))
                ident=seq;seq+=1
                if now()>=45:
                    save(dict(id=f'{args.run}-{ident}',planned=planned,drop='scheduler_missed_window',done=now(),events=[]));continue
                if len(active)>=64:
                    save(dict(id=f'{args.run}-{ident}',planned=planned,drop='client_cap64',done=now(),events=[]));continue
                task=asyncio.create_task(request(planned,ident));active.add(task);task.add_done_callback(active.discard)
            await asyncio.sleep(max(0,45-now()))
        run['actual_window_s']=now()
        if active:
            _,pending=await asyncio.wait(list(active),timeout=max(0,105-now()))
            for task in pending:task.cancel()
            await asyncio.gather(*pending,return_exceptions=True)
    run['total_elapsed_s']=now();raw.close()
    (out/'run.json').write_text(json.dumps(run,indent=2))
    summary=summarize(run,records)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18171')
    for key in ['config','output','run','code-sha']:p.add_argument('--'+key,required=True)
    p.add_argument('--mode',choices=['closed','open'],required=True);p.add_argument('--load',type=float,required=True);p.add_argument('--rep',type=int,required=True)
    asyncio.run(execute(p.parse_args()))
