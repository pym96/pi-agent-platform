"""A frozen two-path campaign; pilot capture precedes direct replay. No stack startup."""
import argparse,json,hashlib,subprocess,sys,time,urllib.request,csv,html,re
from pathlib import Path
from load import PROMPT,digest,recompute,seal,getjson
HERE=Path(__file__).resolve().parent
BASES={'direct':'http://127.0.0.1:18181','platform':'http://127.0.0.1:18183','pi':'http://127.0.0.1:18182'}
ORDER=[(p,'closed',c) for c in (1,2,4) for p in ('platform','direct')]+[(p,'open',m) for m in (.5,1,2) for p in ('platform','direct')]
def run_point(out,path,mode,value,payload=None,count=20,kind='formal',prefix=None,pairs=None):
 command=[sys.executable,str(HERE/'load.py'),'point','--path',path,'--mode',mode,'--base',BASES[path],'--out',str(out),'--count',str(count),'--kind',kind,'--prefix',prefix or 'lb'+str(time.time_ns())]
 if path=='direct':
  if pairs:command+=['--pairs',str(pairs[0]),'--pairs-sha256',pairs[1]]
  else:command+=['--payload',str(payload)]
 command+=['--concurrency' if mode=='closed' else '--rate',str(value)]
 r=subprocess.run(command,capture_output=True,text=True,timeout=400);(out.parent/(out.name+'.command.json')).write_text(json.dumps({'command':command,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr},indent=2))
 if r.returncode:raise RuntimeError('point failed:'+str(out))
 return json.loads((out/'summary.json').read_text())
def idle(deadline,platform=None):
 sessions=[]
 if platform is not None:sessions=[x['id'] for x in json.loads((Path(platform)/'trace.json').read_text())['slots']]
 while time.time()<deadline:
  _,h=getjson(BASES['direct']+'/health',timeout=3);_,pi=getjson(BASES['pi']+'/metrics',timeout=3);histories={}
  for session in sessions:
   _,tasks=getjson(BASES['platform']+'/sessions/'+session+'/tasks',timeout=3);histories[session]=tasks
   if not isinstance(tasks,list) or any(x.get('status') not in ('queued','running','completed','interrupted','cancelled') for x in tasks):raise RuntimeError('unknown durable Go inventory')
  queued=sum(x['status']=='queued' for tasks in histories.values() for x in tasks);running=sum(x['status']=='running' for tasks in histories.values() for x in tasks)
  if platform is not None:
   with (Path(platform).parent/'idle-checks.jsonl').open('a') as f:f.write(json.dumps({'utc_epoch':time.time(),'clock':'client-idle-wall','model':h,'pi':pi,'durable_task_histories':histories,'go_queued':queued,'go_running':running})+'\n')
  if h['active_generation']==0 and h['queued']==0 and pi['active']==0 and queued==0 and running==0:return h
  time.sleep(1)
 raise RuntimeError('carry-in unresolved')
def render(out,results):
 keys=['point','path','mode','concurrency','rate','planned','sent','complete','rejected','failed','timeout','unresolved','generator_drop','n_success','success_rate_planned','p95_complete_s','p95_ttft_s','p95_send_lag_s','cohort_complete_rps','cohort_success_output_tokens_per_s','reason','stop_reason']
 with (out/'curves.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(results)
 # Points/lines only express measured points. Missing points stay in CSV and are not drawn.
 partial=any(r.get('reason') or r.get('stop_reason') for r in results)
 colors={'direct':'#2563eb','platform':'#dc2626'};svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="650"><rect width="1600" height="650" fill="white"/><text x="30" y="30">'+('PARTIAL: ' if partial else '')+'Exploratory terminal latency / throughput: planned20 per point; no SLO claim</text>']
 for metric,y,label in [('p95_complete_s',80,'P95 completion (seconds)'),('cohort_complete_rps',350,'Cohort completion requests/second')]:
  values=[r[metric] for r in results if isinstance(r.get(metric),(int,float))];scale=max(values,default=1) or 1
  svg.append(f'<text x="30" y="{y}">{label}</text>')
  for i,r in enumerate(results):
   if not isinstance(r.get(metric),(int,float)):continue
   x=60+i*125;py=y+190-r[metric]/scale*160
   annotation=f'n={r.get("n_success","unknown")}/{r["planned"]} fail={r.get("failed","unknown")} reject={r.get("rejected","unknown")}'
   if r.get('stop_reason'):annotation+=' interrupted'
   svg.append(f'<circle cx="{x}" cy="{py}" r="5" fill="{colors[r["path"]]}"/><text x="{x}" y="{y+210}" font-size="10">{html.escape(r["point"])}</text><text x="{x}" y="{y+225}" font-size="9">{html.escape(annotation)}</text><text x="{x}" y="{py-8}" font-size="10">{r[metric]:.3g}</text>')
 svg.append('</svg>');(out/'curves.svg').write_text(''.join(svg))
def validate_plan(plan):
 namespace=plan.get('id_prefix','')
 if not isinstance(namespace,str) or not re.fullmatch(r'[A-Za-z0-9_-]{0,40}',namespace):raise ValueError('invalid frozen ID namespace')
 if len(plan['order'])!=12 or plan['drain']!=90 or plan['max_inflight']!=32 or plan['kind']!='formal' or plan['independent_repeats']!=0 or not 0<plan['Rb']<float('inf'):raise ValueError('invalid frozen campaign envelope')
 for i,((path,mode,value),item) in enumerate(zip(ORDER,plan['order'])):
  expected=value if mode=='closed' else value*plan['Rb'];offsets=[j/expected for j in range(20)] if mode=='open' else [None]*20
  if item['path']!=path or item['mode']!=mode or item['value']!=expected or item['count']!=20 or item['ids']!=[f'{namespace}p{i}_{j}' for j in range(20)] or item['pair_ids']!=[f'cohort{i//2}:{j}' for j in range(20)] or item['cohort_id']!=f'cohort{i//2}' or item['offsets']!=offsets:raise ValueError('frozen cohort/slot/arrival mismatch')

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['pilot','freeze','formal'],required=True);p.add_argument('--out',required=True);p.add_argument('--bridge',required=True);p.add_argument('--pilot');p.add_argument('--plan');p.add_argument('--id-prefix',default='');p.add_argument('--deadline',type=float,required=True);p.add_argument('--model-base',default=BASES['direct']);p.add_argument('--platform-base',default=BASES['platform']);p.add_argument('--pi-base',default=BASES['pi']);a=p.parse_args();
 from urllib.parse import urlsplit
 for key,value in [('direct',a.model_base),('platform',a.platform_base),('pi',a.pi_base)]:
  parsed=urlsplit(value)
  if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or parsed.port is None or parsed.path not in ('','/'):raise ValueError('bounded loopback campaign required')
  BASES[key]=value.rstrip('/')
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 if a.stage=='pilot':
  from pairs import build
  prefix='pilot'+str(time.time_ns());first=run_point(out/'platform','platform','closed',1,count=3,kind='pilot',prefix=prefix+'p');idle(a.deadline,out/'platform')
  vector=build(out/'platform',Path(a.bridge),out/'pairs',prefix+'d','pilot')
  direct=run_point(out/'direct','direct','closed',1,count=3,kind='pilot',prefix=prefix+'d',pairs=vector);idle(a.deadline,out/'platform')
  rows=[json.loads(x) for x in (out/'direct/ledger.jsonl').read_text().splitlines()]
  if len(rows)!=3 or any(r['status']!='complete' for r in rows) or first['complete']!=3:raise RuntimeError('pilot incomplete; no formal GO')
  rows.sort(key=lambda r:r['send']);rb=2/sum(r['end']-r['send'] for r in rows[-2:]);(out/'calibration.json').write_text(json.dumps({'Rb':rb,'algorithm':'2 / sum(last two paired direct send-to-valid-terminal seconds)','pairs_sha256':vector[1],'platform':first,'direct':direct,'first_request_cold':True,'pilot_excluded_formal':True,'all_inputs':'full-field actual platform mapped payload per slot; no normalization'},indent=2));print((out/'calibration.json').read_text())
 elif a.stage=='freeze':
  pilot=Path(a.pilot);cal=json.loads((pilot/'calibration.json').read_text());plan={'order':[{'point':f'{path}_{mode}_{v}','path':path,'mode':mode,'value':v if mode=='closed' else v*cal['Rb'],'count':20,'cohort_id':f'cohort{i//2}','pair_ids':[f'cohort{i//2}:{j}' for j in range(20)],'ids':[f'{a.id_prefix}p{i}_{j}' for j in range(20)],'offsets':[j/(v*cal['Rb']) for j in range(20)] if mode=='open' else [None]*20} for i,(path,mode,v) in enumerate(ORDER)],'id_prefix':a.id_prefix,'Rb':cal['Rb'],'capture_algorithm':'each complete platform planned cohort -> exact session/task/modelCall request matching -> freeze full vector+original source raw -> direct same20slots; missing actual payload stays generator_drop; no replacement/normalization','drain':90,'max_inflight':32,'independent_repeats':0,'kind':'formal','pilot_pairs_sha256':cal['pairs_sha256']}
  validate_plan(plan)
  (out/'frozen-plan.json').write_text(json.dumps(plan,indent=2));(out/'frozen-plan.sha256').write_text(hashlib.sha256((out/'frozen-plan.json').read_bytes()).hexdigest()+'\n');print(json.dumps({'plan_sha256':hashlib.sha256((out/'frozen-plan.json').read_bytes()).hexdigest()}));return
 else:
  pilot=Path(a.pilot);cal=json.loads((pilot/'calibration.json').read_text());plan=json.loads(Path(a.plan).read_text());validate_plan(plan);(out/'frozen-plan.json').write_bytes(Path(a.plan).read_bytes());results=[];reason=None
  from pairs import build
  last_platform=None
  for index,item in enumerate(plan['order']):
   required_offer=item['count']/item['value'] if item['mode']=='open' else 30
   if reason or time.time()+90+required_offer>=a.deadline:
    reason=reason or 'insufficient_deadline_for_offer_and_drain';results.append(dict(item,planned=20,sent=0,complete=0,generator_drop=20,reason=reason));continue
   measured=None;point_invoked=False
   try:
    h=idle(a.deadline,out/last_platform['point'] if last_platform else None);prefix=item['ids'][0].rsplit('_',1)[0];vector=None
    if item['path']=='direct':
     if last_platform is None:raise RuntimeError('missing preceding platform cohort')
     vector=build(out/last_platform['point'],Path(a.bridge),out/('pairs-'+str(index)),prefix,'cohort'+str(index//2))
    point_invoked=True;s=run_point(out/item['point'],item['path'],item['mode'],item['value'],prefix=prefix,pairs=vector);measured=dict(s,point=item['point']);results.append(measured)
    if item['path']=='platform':last_platform=item
    if s['timeout'] or s['unresolved']:reason='uncertain task settlement; stop subsequent points'
    idle(a.deadline,out/item['point'] if item['path']=='platform' else out/last_platform['point'])
   except Exception as e:
    reason=reason or repr(e)
    if measured is not None:measured.update(stop_reason=reason,reason=reason)
    else:
     summary=out/item['point']/'summary.json'
     if summary.exists():
      measured=json.loads(summary.read_text());measured.update(point=item['point'],stop_reason=reason,reason=reason,summary_provenance={'path':str(summary.relative_to(out)),'sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'cli_completed_successfully':False});results.append(measured)
     else:results.append(dict(item,planned=20,sent=None if point_invoked else 0,complete=None if point_invoked else 0,generator_drop=None if point_invoked else 20,reason=reason))
  (out/'results.json').write_text(json.dumps(results,indent=2));render(out,results)
  inventory={k:sum(r[k] for r in results) if all(isinstance(r.get(k),int) for r in results) else None for k in ['planned','sent','complete','generator_drop']}
  campaign_status={'schema':'lb13-campaign-status-v1','status':'stopped' if reason else 'complete','stopped_reason':reason,'points_planned':12,'points_with_summary':sum((out/r['point']/'summary.json').exists() for r in results),**inventory};(out/'campaign-status.json').write_text(json.dumps(campaign_status,indent=2));print(json.dumps(campaign_status))
 anchor=seal(out);print(json.dumps({'manifest_sha256':anchor}))
 if a.stage=='formal' and reason:raise SystemExit(2)
if __name__=='__main__':main()
