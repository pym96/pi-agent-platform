"""Recompute local-clock spans and identity conservation. Synthetic CPU times only."""
import json,math,re
from datetime import datetime
from pathlib import Path


def pg_timestamp(value):
    """Read timezone-aware PostgreSQL timestamps consistently on Python 3.10+."""
    if not isinstance(value,str) or not re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}'
        r'(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})',value
    ):
        raise ValueError('expected timezone-aware PostgreSQL timestamp with 0–6 fractional digits')
    # %f accepts PostgreSQL's variable precision on 3.10; fromisoformat does not.
    fmt='%Y-%m-%dT%H:%M:%S'+('.%f' if '.' in value else '')+'%z'
    return datetime.strptime(value.replace(' ','T'),fmt)

def analyze(root):
    root=Path(root);run=json.loads((root/'run.json').read_text());clients=[json.loads(x) for x in (root/'client.jsonl').read_text().splitlines()];bridge=[json.loads(x) for x in (root/'bridge.jsonl').read_text().splitlines()]
    assert run['kind'] in ('synthetic','qwen-functional') and len(run['commit'])==40
    if run['kind']=='synthetic':
        assert run.get('resources',{}).get('GPU') is False and (root/'fixture.jsonl').is_file()
    else:
        assert run.get('resources',{}).get('GPU') is True and not (root/'fixture.jsonl').exists()
        from device_proof import validate
        validate(root,run)
        before=json.loads((root/'health-before.json').read_text());after=json.loads((root/'health-after.json').read_text())
        assert before['ready'] is True and before['backend']=='transformers-serialized/Qwen3-8B' and after['backend']==before['backend']
        assert before['attempts']==0 and after['active_generation']==0 and before['max_attempts']==after['max_attempts']==3
        assert before['max_context']==after['max_context']==1024 and after['ready'] is True
    tasks={};samples=[]
    for c in clients:
        assert c['task'] and c['session'] and c['clock']=='client-monotonic'
        times=[c[k] for k in ('submit','ack','completed')]
        assert all(isinstance(v,(float,int)) and math.isfinite(v) for v in times) and times==sorted(times)
        assert c['status'] in ('completed','interrupted')
        assert c['task'] not in tasks;tasks[c['task']]=c
        events=c['events'];assert events and all(e['task']==c['task'] for e in events)
        assert all(a['id']<b['id'] for a,b in zip(events,events[1:]));assert events[-1]['kind']==c['status']
        result=[e for e in events if e['kind']=='result']
        if c['status']=='completed':assert len(result)==1 and result[0]['data']['verified'] is True
        if result:
            runtime=[e for e in events if e['kind']=='runtime'];assert len(runtime)==1
            assert runtime[0]['data']['task']==c['task'] and runtime[0]['data']['modelCall']==result[0]['data']['modelCall']
            assert runtime[0]['data']['receivedMono']<=result[0]['data']['piResultMono']
        first=[e['clientObserved'] for e in events if e['kind']=='text' and e['data'].get('text')]
        assert all(c['submit']<=e['clientObserved']<=c['completed'] for e in events)
        samples.append({'client_first_content_seconds':min(first)-c['submit'] if first else None,'task':c['task'],'status':c['status'],'ack_seconds':c['ack']-c['submit'],'client_terminal_seconds':c['completed']-c['submit']})
    settled=[b for b in bridge if b['event']=='settled']
    requests=[b for b in bridge if b['event']=='request']
    assert len(settled)==len(tasks)==len(requests) and len({b['id'] for b in settled})==len(settled)
    if run['kind']=='synthetic':
        fixture=[json.loads(x) for x in (root/'fixture.jsonl').read_text().splitlines()]
        assert len(fixture)==len(requests) and [x['call'] for x in fixture]==list(range(1,len(requests)+1))
        assert all(x['request']==y['mapped'] for x,y in zip(fixture,requests))
    else:assert after['attempts']==len(requests)
    def number(v):return type(v) in (int,float) and math.isfinite(v)
    for b in settled:
        c=tasks[b['task']]
        assert b['session']==c['session'] and b['clock']=='pi-performance.now'
        request=[r for r in requests if r['id']==b['id']]
        assert len(request)==1 and all(request[0][k]==b[k] for k in ('task','session','start','sdk','mapped'))
        runtime=[e for e in c['events'] if e['kind']=='runtime'];assert len(runtime)==1
        assert runtime[0]['data']['modelCall']==b['id'] and runtime[0]['data']['task']==b['task']
        assert number(b['start']) and number(b['settled']) and runtime[0]['data']['receivedMono']<=b['start']<=b['settled']
        frames=b.get('frames',[])
        assert all(number(f['at']) and b['start']<=f['at']<=b['settled'] for f in frames)
        assert all(x['at']<=y['at'] for x,y in zip(frames,frames[1:]))
        contents=[];finishes=[];usages=[];done=[]
        for index,frame in enumerate(frames):
            if frame['data']=='[DONE]':done.append(index);continue
            raw=json.loads(frame['data'])
            if 'usage' in raw:usages.append(raw['usage'])
            for choice in raw.get('choices',[]):
                content=choice.get('delta',{}).get('content')
                if content:contents.append((index,frame['at'],content))
                if choice.get('finish_reason') is not None:finishes.append(choice['finish_reason'])
        if contents:
            first_index,first_at,_=contents[0]
            next_at=frames[first_index+1]['at'] if first_index+1<len(frames) else b['settled']
            assert number(b.get('firstContent')) and first_at<=b['firstContent']<=next_at
        else:
            first_at=None;assert 'firstContent' not in b
        result=[e for e in c['events'] if e['kind']=='result']
        if b['ok']:
            assert c['status']=='completed' and len(result)==1 and done==[len(frames)-1] and len(finishes)==1 and len(usages)==1
            value=result[0]['data'];assert value['modelCall']==b['id'] and value['rawUsage']==b['usage']==usages[0] and b['finishReason']==finishes[0]
            assert value['text']==''.join(x[2] for x in contents) and b['settled']<=value['piResultMono']
        else:assert c['status']=='interrupted' and not result
        sample=next(s for s in samples if s['task']==b['task'])
        sample['pi_model_first_content_ms']=first_at-b['start'] if first_at is not None else None
        sample['pi_model_settled_ms']=b['settled']-b['start']
    go=[json.loads(x) for x in (root/'go-trace.jsonl').read_text().splitlines()]
    assert {g['task'] for g in go}==set(tasks)
    for task,c in tasks.items():
        observations=[g for g in go if g['task']==task];assert observations and observations[0]['phase']=='pi_request_start' and observations[-1]['phase']=='durable_terminal' and observations[-1]['status']==c['status']
        assert all(g['session']==c['session'] and g['clock']=='go-since-claim' and g['sinceClaimNs']>=0 for g in observations)
        assert all(x['sinceClaimNs']<=y['sinceClaimNs'] for x,y in zip(observations,observations[1:]))
    pg=json.loads((root/'pg-events.json').read_text())
    assert {e['task'] for e in pg}==set(tasks)
    for task,c in tasks.items():
        rows=[e for e in pg if e['task']==task]
        assert len(rows)==len(c['events']) and all(all(x[k]==y[k] for k in ('id','task','kind','data')) for x,y in zip(rows,c['events']))
        assert rows and rows[-1]['kind']==c['status']
        queued=next(e for e in rows if e['kind']=='queued');running=next(e for e in rows if e['kind']=='running')
        q=(pg_timestamp(running['created_at'])-pg_timestamp(queued['created_at'])).total_seconds();assert q>=0
        next(s for s in samples if s['task']==task)['pg_queue_seconds']=q
    return {'integrity_verified':False,'kind':run['kind'],'commit':run['commit'],'attempts':len(settled),'success':sum(c['status']=='completed' for c in clients),'failure':sum(c['status']!='completed' for c in clients),'samples':samples,'warning':'local spans only; no subtraction across clock domains; fixture is not GPU latency'}
if __name__=='__main__':
    from recompute import main
    raise SystemExit(main())
