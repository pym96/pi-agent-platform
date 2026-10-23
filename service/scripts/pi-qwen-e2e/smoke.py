"""Exactly three sequential durable tasks against a separately activated real stack.
stdlib only; no retries. All provider calls are also capped by the model server.
"""
import argparse,json,time,urllib.request,hashlib,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',default='http://127.0.0.1:18183');p.add_argument('--model',default='http://127.0.0.1:18181');p.add_argument('--out',required=True);p.add_argument('--prefix',required=True);p.add_argument('--sha',required=True);a=p.parse_args()
assert len(a.sha)==40 and a.base.startswith('http://127.0.0.1:') and a.model.startswith('http://127.0.0.1:')
out=Path(a.out);out.mkdir(exist_ok=False,parents=True)
def request(path,data=None):
    body=json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(urllib.request.Request(path,data=body,headers={'Content-Type':'application/json'}),timeout=90) as r:return r.status,json.load(r)
_,health=request(a.model+'/health');assert health['ready'] and health['attempts']==0
(out/'health-before.json').write_text(json.dumps(health,indent=2))
config=Path(__file__).with_name('stage-b.json')
(out/'run.json').write_text(json.dumps({'kind':'qwen-functional','commit':a.sha,'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'workload':'3 sequential tasks, same-session 2 turns and independent session; no throughput/P95 claim','resource':'one authorized GPU3, fixed model/config'},indent=2))
for session,key,prompt in [(a.prefix+'_context','one','Remember the codeword LANTERN. Reply with OK only.'),(a.prefix+'_context','two','What was the codeword? Reply with that word only.'),(a.prefix+'_independent','one','Reply with hello only.')]:
    start=time.monotonic();code,task=request(a.base+f'/sessions/{session}/tasks',{'key':key,'prompt':prompt});assert code==202;ack=time.monotonic();events=[]
    with urllib.request.urlopen(a.base+f'/sessions/{session}/events',timeout=90) as stream:
        for raw in stream:
            line=raw.decode().strip()
            if not line.startswith('data: '):continue
            event=json.loads(line[6:]);
            if event['task']!=task['id']:continue
            event['clientObserved']=time.monotonic();events.append(event)
            if event['kind'] in ('completed','interrupted','cancelled'):break
        else:raise RuntimeError('missing durable terminal')
    end=time.monotonic();_,history=request(a.base+f'/sessions/{session}/tasks');status=next(t['status'] for t in history if t['id']==task['id']);assert status==events[-1]['kind']
    record={'task':task['id'],'session':session,'clock':'client-monotonic','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'submit':start,'ack':ack,'completed':end,'status':status,'events':events}
    with (out/'client.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
    if status!='completed':raise RuntimeError('real task did not complete; do not retry automatically')
    code,again=request(a.base+f'/sessions/{session}/tasks',{'key':key,'prompt':prompt});assert code==200 and again['id']==task['id']
_,health=request(a.model+'/health');(out/'health-after.json').write_text(json.dumps(health,indent=2));assert health['attempts']==3 and health['active_generation']==0
print(json.dumps({'tasks':3,'completed':3,'attempts':health['attempts'],'kind':'qwen-functional'}))
