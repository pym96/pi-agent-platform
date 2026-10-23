"""Recompute local-clock spans and identity conservation. Synthetic CPU times only."""
import json,math
from pathlib import Path

def analyze(root):
    root=Path(root);run=json.loads((root/'run.json').read_text());clients=[json.loads(x) for x in (root/'client.jsonl').read_text().splitlines()];bridge=[json.loads(x) for x in (root/'bridge.jsonl').read_text().splitlines()]
    assert run['kind'] in ('synthetic','qwen-functional') and len(run['commit'])==40
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
    assert len(settled)==len(tasks) and len({b['id'] for b in settled})==len(settled)
    for b in settled:
        assert b['task'] in tasks and b['session']==tasks[b['task']]['session'] and b['clock']=='pi-performance.now'
        assert b['start']<=b.get('firstContent',b['settled'])<=b['settled']
        assert all(a['at']<=c['at'] for a,c in zip(b.get('frames',[]),b.get('frames',[])[1:]));assert b['start']<=min([x['at'] for x in b.get('frames',[])] or [b['settled']])
        sample=next(s for s in samples if s['task']==b['task']);sample['pi_model_first_content_ms']=b.get('firstContent')-b['start'] if b.get('firstContent') is not None else None;sample['pi_model_settled_ms']=b['settled']-b['start']
        if b['ok']:assert tasks[b['task']]['status']=='completed'
        else:assert tasks[b['task']]['status']=='interrupted'
    go=[json.loads(x) for x in (root/'go-trace.jsonl').read_text().splitlines()]
    for task,c in tasks.items():
        observations=[g for g in go if g['task']==task];assert observations and observations[0]['phase']=='pi_request_start' and observations[-1]['phase']=='durable_terminal' and observations[-1]['status']==c['status']
        assert all(g['session']==c['session'] and g['clock']=='go-since-claim' and g['sinceClaimNs']>=0 for g in observations)
        assert all(x['sinceClaimNs']<=y['sinceClaimNs'] for x,y in zip(observations,observations[1:]))
    pg=json.loads((root/'pg-events.json').read_text())
    from datetime import datetime
    for task,c in tasks.items():
        rows=[e for e in pg if e['task']==task];assert rows and rows[-1]['kind']==c['status']
        queued=next(e for e in rows if e['kind']=='queued');running=next(e for e in rows if e['kind']=='running')
        q=(datetime.fromisoformat(running['created_at'])-datetime.fromisoformat(queued['created_at'])).total_seconds();assert q>=0
        next(s for s in samples if s['task']==task)['pg_queue_seconds']=q
    return {'kind':run['kind'],'commit':run['commit'],'attempts':len(settled),'success':sum(c['status']=='completed' for c in clients),'failure':sum(c['status']!='completed' for c in clients),'samples':samples,'warning':'local spans only; no subtraction across clock domains; fixture is not GPU latency'}
if __name__=='__main__':
    import sys
    result=analyze(sys.argv[1]);Path(sys.argv[1],'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
