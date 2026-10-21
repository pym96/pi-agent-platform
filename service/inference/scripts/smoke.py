"""Bounded real-service smoke. No retries; every attempted generation is retained."""
import argparse,json,sys,time,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from service.inference.oracle import inspect_stream
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:18179');p.add_argument('--out',required=True);p.add_argument('--requests',type=int,default=3);a=p.parse_args()
if not 1<=a.requests<=6 or a.url!='http://127.0.0.1:18179':raise ValueError('fixed loopback target and1..6calls required')
out=Path(a.out);out.mkdir(exist_ok=False)
with urllib.request.urlopen(a.url+'/health',timeout=5) as response:health=json.load(response)
(out/'health.json').write_text(json.dumps(health,indent=2));assert health['ready'] and health['backend']=='transformers-serialized/Qwen3-8B'
rows=[]
for index in range(a.requests):
    payload={'model':'Qwen3-8B','stream':True,'messages':[{'role':'user','content':'Reply briefly: what is two plus two?'}],'max_tokens':[16,8,1,16,8,1][index]}
    (out/f'{index}.request.json').write_text(json.dumps(payload));start=time.monotonic()
    # Write intent before sending; interruption never disappears from attempt count.
    (out/f'{index}.attempt.json').write_text(json.dumps({'index':index,'started_epoch':time.time()}))
    status=0;body='';headers={}
    try:
        req=urllib.request.Request(a.url+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=90) as response:
            status=response.status;headers=dict(response.headers);body=response.read().decode()
        verdict=inspect_stream(status,body)
        if not headers.get('Content-Type','').startswith('text/event-stream'):verdict={'success':False,'reason':'content_type'}
        if verdict.get('success') and verdict['usage']['completion_tokens']>payload['max_tokens']:verdict={'success':False,'reason':'generation_budget'}
    except Exception as exc:verdict={'success':False,'reason':type(exc).__name__}
    (out/f'{index}.sse').write_text(body)
    row={'index':index,'status':status,'headers':headers,'duration_seconds':time.monotonic()-start,'verdict':verdict};rows.append(row)
    (out/'summary.json').write_text(json.dumps({'attempts':len(rows),'success':all(r['verdict']['success'] for r in rows),'rows':rows},indent=2))
    if not verdict['success']:break
print(json.dumps({'attempts':len(rows),'success':len(rows)==a.requests and all(r['verdict']['success'] for r in rows)}))
raise SystemExit(0 if len(rows)==a.requests and all(r['verdict']['success'] for r in rows) else 1)
