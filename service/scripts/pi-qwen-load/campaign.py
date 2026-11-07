"""A frozen two-path campaign; pilot capture precedes direct replay. No stack startup."""
import argparse,json,hashlib,subprocess,sys,time,urllib.request,csv,html
from pathlib import Path
from load import PROMPT,digest,recompute,seal,getjson
HERE=Path(__file__).resolve().parent
ORDER=[(p,'closed',c) for c in (1,2,4) for p in ('direct','platform')]+[(p,'open',m) for m in (.5,1,2) for p in ('direct','platform')]
def run_point(out,path,mode,value,payload,count=20,kind='formal',prefix=None):
 command=[sys.executable,str(HERE/'load.py'),'point','--path',path,'--mode',mode,'--base','http://127.0.0.1:'+('18181' if path=='direct' else '18183'),'--out',str(out),'--count',str(count),'--kind',kind,'--prefix',prefix or 'lb'+str(time.time_ns())]
 if path=='direct':command+=['--payload',str(payload)]
 command+=['--concurrency' if mode=='closed' else '--rate',str(value)]
 r=subprocess.run(command,capture_output=True,text=True,timeout=400);(out.parent/(out.name+'.command.json')).write_text(json.dumps({'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
 if r.returncode:raise RuntimeError('point failed:'+str(out))
 return json.loads((out/'summary.json').read_text())
def idle(deadline):
 while time.time()<deadline:
  _,h=getjson('http://127.0.0.1:18181/health',timeout=3);_,pi=getjson('http://127.0.0.1:18182/metrics',timeout=3)
  if h['active_generation']==0 and h['queued']==0 and pi['active']==0:return h
  time.sleep(1)
 raise RuntimeError('carry-in unresolved')
def render(out,results):
 keys=['point','path','mode','concurrency','rate','planned','sent','complete','rejected','failed','timeout','unresolved','generator_drop','n_success','success_rate_planned','p95_complete_s','p95_ttft_s','p95_send_lag_s','cohort_complete_rps','cohort_success_output_tokens_per_s','reason']
 with (out/'curves.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(results)
 # Points/lines only express measured points. Missing points stay in CSV and are not drawn.
 colors={'direct':'#2563eb','platform':'#dc2626'};svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="650"><rect width="1000" height="650" fill="white"/><text x="30" y="30">Exploratory terminal latency / throughput: n=20 planned per point; no SLO claim</text>']
 for metric,y,label in [('p95_complete_s',80,'P95 completion (seconds)'),('cohort_complete_rps',350,'Cohort completion requests/second')]:
  values=[r[metric] for r in results if isinstance(r.get(metric),(int,float))];scale=max(values,default=1) or 1
  svg.append(f'<text x="30" y="{y}">{label}</text>')
  for i,r in enumerate(results):
   if not isinstance(r.get(metric),(int,float)):continue
   x=60+i*75;py=y+190-r[metric]/scale*160
   svg.append(f'<circle cx="{x}" cy="{py}" r="5" fill="{colors[r["path"]]}"/><text x="{x}" y="{y+210}" font-size="10">{html.escape(r["point"])}</text><text x="{x}" y="{py-8}" font-size="10">{r[metric]:.3g}</text>')
 svg.append('</svg>');(out/'curves.svg').write_text(''.join(svg))
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['pilot','freeze','formal'],required=True);p.add_argument('--out',required=True);p.add_argument('--bridge',required=True);p.add_argument('--pilot');p.add_argument('--plan');p.add_argument('--deadline',type=float,required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 if a.stage=='pilot':
  first=run_point(out/'platform','platform','closed',1,None,3,'pilot');idle(a.deadline)
  bridge=[json.loads(x) for x in Path(a.bridge).read_text().splitlines()];requests=[x for x in bridge if x.get('event')=='request'];cores=[x['mapped'] for x in requests]
  if len(cores)!=3 or len({digest(x) for x in cores})!=1:raise RuntimeError('pilot payload identity unclear')
  payload=out/'payload.json';payload.write_text(json.dumps(cores[0],indent=2));direct=run_point(out/'direct','direct','closed',1,payload,3,'pilot');idle(a.deadline)
  rows=[json.loads(x) for x in (out/'direct/ledger.jsonl').read_text().splitlines()]
  if len(rows)!=3 or any(r['status']!='complete' for r in rows) or first['complete']!=3:raise RuntimeError('pilot incomplete; no formal GO')
  rows.sort(key=lambda r:r['send']);rb=2/sum(r['end']-r['send'] for r in rows[-2:]);(out/'calibration.json').write_text(json.dumps({'Rb':rb,'algorithm':'2 / sum(last two direct send-to-valid-terminal seconds)','payload_core_hash':digest(cores[0]),'platform':first,'direct':direct,'first_request_cold':True,'pilot_excluded_formal':True},indent=2));print((out/'calibration.json').read_text())
 elif a.stage=='freeze':
  pilot=Path(a.pilot);cal=json.loads((pilot/'calibration.json').read_text());payload=pilot/'payload.json';plan={'order':[{'point':f'{path}_{mode}_{v}','path':path,'mode':mode,'value':v if mode=='closed' else v*cal['Rb'],'count':20,'ids':[f'p{i}_{j}' for j in range(20)],'offsets':[j/(v*cal['Rb']) for j in range(20)] if mode=='open' else [None]*20} for i,(path,mode,v) in enumerate(ORDER)],'Rb':cal['Rb'],'payload_core_hash':cal['payload_core_hash'],'drain':90,'max_inflight':32,'independent_repeats':0,'kind':'formal'}
  (out/'frozen-plan.json').write_text(json.dumps(plan,indent=2));(out/'frozen-plan.sha256').write_text(hashlib.sha256((out/'frozen-plan.json').read_bytes()).hexdigest()+'\n');print(json.dumps({'plan_sha256':hashlib.sha256((out/'frozen-plan.json').read_bytes()).hexdigest()}));return
 else:
  pilot=Path(a.pilot);cal=json.loads((pilot/'calibration.json').read_text());payload=pilot/'payload.json';plan=json.loads(Path(a.plan).read_text());(out/'frozen-plan.json').write_bytes(Path(a.plan).read_bytes());results=[];reason=None
  for item in plan['order']:
   required_offer=item['count']/item['value'] if item['mode']=='open' else 30
   if reason or time.time()+90+required_offer>=a.deadline:
    reason=reason or 'insufficient_deadline_for_offer_and_drain';results.append(dict(item,planned=20,sent=0,complete=0,generator_drop=20,reason=reason));continue
   try:
    h=idle(a.deadline);s=run_point(out/item['point'],item['path'],item['mode'],item['value'],payload,prefix=item['ids'][0].rsplit('_',1)[0]);idle(a.deadline)
    # All formal platform requests must match captured semantics (no past history).
    bridge=[json.loads(x) for x in Path(a.bridge).read_text().splitlines()]
    if any(digest(x['mapped'])!=cal['payload_core_hash'] for x in bridge if x.get('event')=='request'):raise RuntimeError('platform semantic drift')
    results.append(dict(s,point=item['point']))
    if s['timeout'] or s['unresolved']:reason='uncertain task settlement; stop subsequent points'
   except Exception as e:reason=repr(e);results.append(dict(item,planned=20,reason=reason))
  (out/'results.json').write_text(json.dumps(results,indent=2));render(out,results);print(json.dumps({'results':len(results),'stopped_reason':reason}))
 anchor=seal(out);print(json.dumps({'manifest_sha256':anchor}))
if __name__=='__main__':main()
