"""Terminal-aware closed/open client. stdlib only, no retry, raw frames retained."""
import signal
import shutil
import argparse,concurrent.futures,hashlib,json,math,socket,time,urllib.request,urllib.error,threading
from pathlib import Path
PROMPT='List the integers from 1 through 24, comma-separated, with no other text.'
STOP=threading.Event()
TERMINALS={'completed':'complete','interrupted':'failed','cancelled':'failed'}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def http(url,data=None,timeout=65):
 request=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 started=time.monotonic();response=urllib.request.urlopen(request,timeout=timeout)
 # A read socket timeout resets on every byte; enforce the whole response budget.
 remaining=max(0,timeout-(time.monotonic()-started));original_close=response.close
 def expire():
  try:response.fp.raw._sock.shutdown(socket.SHUT_RDWR)
  except (AttributeError,OSError):pass
 timer=threading.Timer(remaining,expire);timer.daemon=True;timer.start()
 def close():timer.cancel();original_close()
 response.close=close
 return response
def getjson(url,data=None,timeout=65):
 with http(url,data,timeout) as r:return r.status,json.load(r)
def usage_ok(u):return isinstance(u,dict) and set(u)=={'prompt_tokens','completion_tokens','total_tokens'} and all(type(x) is int and x>=0 for x in u.values()) and u['prompt_tokens']+u['completion_tokens']==u['total_tokens']
def attempt(base,path,payload,ident,planned,deadline,raw,pair=None):
 row={'id':ident,'path':path,'clock':'client-monotonic','planned':planned,'send':time.monotonic(),'ack':None,'first_content':None,'end':None,'usage':None,'finish_reason':None,'status':'unresolved','events':[]}
 if row['send']>=deadline:row.update(send=None,status='generator_drop',end=time.monotonic(),reason='deadline_before_send');return row
 try:
  if path=='platform':
   session=ident;code,task=getjson(base+'/sessions/'+session+'/tasks',{'key':ident,'prompt':PROMPT},max(.1,deadline-time.monotonic()));row.update(ack=time.monotonic(),http=code,task=task['id'],session=session)
   if code not in (200,202):raise ValueError('invalid_ack')
   stream=http(base+'/sessions/'+session+'/events',timeout=max(.1,deadline-time.monotonic()))
  else:
   body=json.dumps(payload);request={'observed':time.monotonic(),'body_utf8':body,'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'payload':payload,'payload_core_hash':digest(payload),'pair_id':pair['pair_id'] if pair else None,'platform_id':pair['platform_id'] if pair else None};raw.with_suffix('.request.json').write_text(json.dumps(request,indent=2));row.update(payload_core_hash=digest(payload),pair_id=request['pair_id'],platform_id=request['platform_id']);stream=http(base+'/v1/chat/completions',payload,max(.1,deadline-time.monotonic()));row.update(ack=time.monotonic(),http=stream.status)
  done=False;finish=False;content=False;last_event_id=0
  with stream,raw.open('x') as f:
   for wire in stream:
    now=time.monotonic();line=wire.decode('utf-8').rstrip('\r\n');f.write(json.dumps({'observed':now,'line':line})+'\n');f.flush()
    if now>=deadline:raise TimeoutError('point_drain_deadline')
    if not line.startswith('data: '):continue
    value=line[6:]
    if path=='direct':
     if done:raise ValueError('event_after_DONE')
     if value=='[DONE]':done=True;continue
     ev=json.loads(value);row['events'].append({'at':now,'data':ev})
     if ev.get('error'):raise ValueError('stream_error:'+str(ev['error']))
     if not isinstance(ev.get('choices'),list):raise ValueError('invalid_choices')
     if 'usage' in ev:
      if row['usage'] is not None or not usage_ok(ev['usage']):raise ValueError('invalid_usage')
      row['usage']=ev['usage']
     for choice in ev['choices']:
      delta=choice.get('delta',{}).get('content','')
      if delta:
       if finish or not isinstance(delta,str):raise ValueError('bad_content')
       content=True
       if row['first_content'] is None:row['first_content']=now
      reason=choice.get('finish_reason')
      if reason is not None:
       if finish or reason not in ('stop','length'):raise ValueError('invalid_finish')
       finish=True;row['finish_reason']=reason
    else:
     ev=json.loads(value)
     if ev['task']!=row['task']:raise ValueError('wrong_task_id')
     if ev['id']<=last_event_id:raise ValueError('event_order')
     last_event_id=ev['id'];row['events'].append({'at':now,'data':ev})
     if ev['kind']=='text' and ev.get('data',{}).get('text') and row['first_content'] is None:row['first_content']=now
     if ev['kind']=='result':
      result=ev['data'];row['usage']=result.get('rawUsage');row['finish_reason']=result.get('stopReason');row['model_call']=result.get('modelCall')
     if ev['kind'] in TERMINALS:
      row['status']=TERMINALS[ev['kind']];row['terminal']=ev['kind'];done=True;break
   if path=='direct':
    if not (done and finish and content and usage_ok(row['usage'])):raise EOFError('incomplete_stream')
    row['status']='complete'
   elif not done:raise EOFError('missing_durable_terminal')
   if path=='platform':
    _,history=getjson(base+'/sessions/'+row['session']+'/tasks',timeout=max(.1,deadline-time.monotonic()))
    persisted=next(x for x in history if x['id']==row['task']);row['durable_status']=persisted['status']
    if persisted['status']!=row['terminal']:raise ValueError('durable_terminal_mismatch')
    if row['status']=='complete' and (not usage_ok(row['usage']) or row['first_content'] is None):raise ValueError('missing_usage_or_content')
    f.write(json.dumps({'observed':time.monotonic(),'durable_history':history})+'\n')
   row['end']=time.monotonic();f.write(json.dumps({'observed':row['end'],'eof':True})+'\n')
 except urllib.error.HTTPError as e:
  row.update(http=e.code,status='rejected' if e.code in (429,503) else 'failed',reason='http_'+str(e.code),error_body=e.read().decode(errors='replace'))
 except EOFError as e:row.update(status='timeout' if time.monotonic()>=deadline else 'unresolved',reason=str(e))
 except (TimeoutError,socket.timeout) as e:row.update(status='timeout',reason=str(e))
 except Exception as e:row.update(status='timeout' if time.monotonic()>=deadline else 'failed',reason=repr(e))
 row['end']=row['end'] or time.monotonic();return row

def point(args):
 STOP.clear()
 for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:STOP.set())
 out=Path(args.out);out.mkdir(parents=True,exist_ok=False);payload=json.loads(Path(args.payload).read_text()) if args.payload else None;vector=None
 prefix=args.prefix or 'lb'+str(time.time_ns())
 if args.pairs:
  from pairs import validate
  if args.path!='direct' or args.payload or not args.pairs_sha256:raise ValueError('paired direct requires a frozen vector and no fallback')
  validate(args.pairs,args.pairs_sha256,prefix,args.count);shutil.copytree(Path(args.pairs).parent,out/'pair-source');vector=validate(out/'pair-source/pairs.json',args.pairs_sha256,prefix,args.count)
  (out/'pair-binding.json').write_text(json.dumps({'vector_sha256':args.pairs_sha256,'bound_monotonic':time.monotonic(),'read_epoch':time.time(),'created_epoch':vector['created_epoch']},indent=2))
 if args.path=='direct' and payload is None and vector is None:raise ValueError('direct requires actual captured payload')
 t0=time.monotonic();offer_end=t0+args.count/args.rate if args.mode=='open' else None;deadline=(offer_end if offer_end else t0)+args.drain
 trace={'schema':'lb13-point-v1','path':args.path,'mode':args.mode,'count':args.count,'concurrency':args.concurrency,'rate':args.rate if args.mode=='open' else None,'t0':t0,'offer_end':offer_end,'deadline':deadline,'drain_seconds':args.drain,'max_inflight':args.max_inflight,'clock':'client-monotonic','payload_core_hash':digest(payload) if payload else None,'slots':[{'id':prefix+'_'+str(i),'offset':i/args.rate if args.mode=='open' else None} for i in range(args.count)]}
 if vector is not None:trace['pairs_sha256']=args.pairs_sha256;trace['pair_slots']=[{k:v for k,v in x.items() if k!='payload'} for x in vector['slots']]
 (out/'trace.json').write_text(json.dumps(trace,indent=2));(out/'trace.sha256').write_text(hashlib.sha256((out/'trace.json').read_bytes()).hexdigest()+'\n')
 (out/'raw').mkdir();pending={};rows=[]
 def write(row):
  if vector is not None:
   pair=next(x for x in vector['slots'] if x['direct_id']==row['id'])
   for k in ('pair_id','platform_id','payload_core_hash'):row.setdefault(k,pair[k])
   if row['send'] is None and pair['payload'] is None:row['reason']='missing_pair_payload'
  rows.append(row)
  with (out/'ledger.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 def submit(pool,i,planned):
  ident=trace['slots'][i]['id'];pair=vector['slots'][i] if vector is not None else None;body=pair['payload'] if pair is not None else payload
  if pair is not None and body is None:
   write({'id':ident,'path':args.path,'clock':'client-monotonic','planned':planned,'send':None,'end':time.monotonic(),'status':'generator_drop','reason':'missing_pair_payload','usage':None,'first_content':None,'ack':None,'events':[],'pair_id':pair['pair_id'],'platform_id':pair['platform_id'],'payload_core_hash':None});return
  future=pool.submit(attempt,args.base,args.path,body,ident,planned,deadline,out/'raw'/(ident+'.jsonl'),pair);pending[future]=i
 with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
  if args.mode=='closed':
   i=0
   while i<args.count or pending:
    while i<args.count and len(pending)<args.concurrency and time.monotonic()<deadline and not STOP.is_set():submit(pool,i,time.monotonic());i+=1
    if not pending:break
    done,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
    for future in done:write(future.result());del pending[future]
   for j in range(i,args.count):write({'id':trace['slots'][j]['id'],'path':args.path,'clock':'client-monotonic','planned':None,'send':None,'end':time.monotonic(),'status':'generator_drop','reason':'drain_deadline','usage':None,'first_content':None,'ack':None,'events':[]})
  else:
   for i in range(args.count):
    planned=t0+i/args.rate;STOP.wait(max(0,planned-time.monotonic()))
    for future in list(pending):
     if future.done():write(future.result());del pending[future]
    if vector is not None and vector['slots'][i]['payload'] is None:submit(pool,i,planned)
    elif STOP.is_set() or time.monotonic()>=offer_end or len(pending)>=args.max_inflight:
     write({'id':trace['slots'][i]['id'],'path':args.path,'clock':'client-monotonic','planned':planned,'send':None,'end':time.monotonic(),'status':'generator_drop','reason':'offer_deadline_or_inflight','usage':None,'first_content':None,'ack':None,'events':[]})
    else:submit(pool,i,planned)
   for future in concurrent.futures.as_completed(pending):write(future.result())
 (out/'run.json').write_text(json.dumps({'kind':args.kind,'path':args.path,'mode':args.mode,'ended':time.monotonic(),'clock':'client-monotonic','trace_sha256':hashlib.sha256((out/'trace.json').read_bytes()).hexdigest()},indent=2))
 seal(out);summary=recompute(out);print(json.dumps(summary))

def seal(root):
 files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.name not in ('manifest.json','manifest.sha256','summary.json','summary.csv','curve.svg')}
 (root/'manifest.json').write_text(json.dumps(files,sort_keys=True,indent=2));anchor=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest();(root/'manifest.sha256').write_text(anchor+'\n');return anchor

def verify_raw(row,raw):
 records=[json.loads(x) for x in raw.read_text().splitlines()];first=None;usage=None;reason=None;terminal=None;done=False;last_id=0;result=None
 times=[x['observed'] for x in records]
 if times!=sorted(times) or any(not row['send']<=x<=row['end'] for x in times):raise ValueError('raw clock')
 for record in records:
  line=record.get('line','')
  if not line.startswith('data: '):continue
  value=line[6:]
  if row['path']=='direct':
   if done:raise ValueError('raw after DONE')
   if value=='[DONE]':done=True;continue
   ev=json.loads(value)
   if ev.get('error'):
    if row['status']=='complete':raise ValueError('raw stream error')
    continue
   for c in ev.get('choices',[]):
    content=c.get('delta',{}).get('content')
    if content and first is None:first=record['observed']
    if c.get('finish_reason') is not None:reason=c['finish_reason']
   if 'usage' in ev:usage=ev['usage']
  else:
   ev=json.loads(value)
   if ev.get('task')!=row['task'] or ev['id']<=last_id:raise ValueError('raw task/event id')
   last_id=ev['id']
   if ev['kind']=='text' and ev.get('data',{}).get('text') and first is None:first=record['observed']
   if ev['kind']=='result':result=ev['data'];usage=result.get('rawUsage');reason=result.get('stopReason')
   if ev['kind'] in TERMINALS:terminal=ev['kind']
 if row['first_content']!=first or row['usage']!=usage or row['finish_reason']!=reason:raise ValueError('ledger differs from raw')
 if row['status']=='complete':
  if not usage_ok(usage) or first is None:raise ValueError('raw success evidence')
  if not records[-1].get('eof') or records[-1]['observed']!=row['end']:raise ValueError('raw completion clock')
  if row['path']=='direct' and (not done or reason not in ('stop','length')):raise ValueError('raw terminal')
  if row['path']=='platform':
   histories=[x['durable_history'] for x in records if 'durable_history' in x]
   if terminal!='completed' or not histories or next(x['status'] for x in histories[-1] if x['id']==row['task'])!='completed':raise ValueError('raw durable terminal')

def recompute(root,anchor=None):
 root=Path(root);actual=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest();expected=anchor or (root/'manifest.sha256').read_text().strip()
 if actual!=expected:raise ValueError('manifest anchor mismatch')
 files=json.loads((root/'manifest.json').read_text())
 for name,h in files.items():
  p=root/name
  if not p.resolve().is_relative_to(root.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise ValueError('raw hash mismatch:'+name)
 trace=json.loads((root/'trace.json').read_text());run=json.loads((root/'run.json').read_text());rows=[json.loads(x) for x in (root/'ledger.jsonl').read_text().splitlines()]
 if hashlib.sha256((root/'trace.json').read_bytes()).hexdigest()!=run['trace_sha256']:raise ValueError('trace binding')
 ids=[x['id'] for x in rows]
 if len(ids)!=len(set(ids)) or set(ids)!={x['id'] for x in trace['slots']}:raise ValueError('planned inventory mismatch')
 statuses=['complete','rejected','failed','timeout','unresolved','generator_drop'];counts={s:sum(r['status']==s for r in rows) for s in statuses}
 if sum(counts.values())!=trace['count']:raise ValueError('invalid statuses')
 vector=None;pair_usage=[]
 if trace.get('pairs_sha256'):
  from pairs import validate
  prefix=trace['slots'][0]['id'].rsplit('_',1)[0];vector=validate(root/'pair-source/pairs.json',trace['pairs_sha256'],prefix,trace['count']);binding=json.loads((root/'pair-binding.json').read_text())
  if binding['vector_sha256']!=trace['pairs_sha256'] or binding['bound_monotonic']>trace['t0'] or binding['created_epoch']>binding['read_epoch']:raise ValueError('pair vector was not frozen before direct send')
 latencies=[];ttfts=[];lags=[];tokens=0;unknown_usage=0;stops={};lengths=[]
 for row in rows:
  if row['clock']!='client-monotonic' or row['path']!=trace['path']:raise ValueError('clock/path mismatch')
  sent=row['send'] is not None
  if sent==(row['status']=='generator_drop'):raise ValueError('send/status mismatch')
  if vector is not None:
   i=next(i for i,x in enumerate(trace['slots']) if x['id']==row['id']);pair=vector['slots'][i]
   if row.get('pair_id')!=pair['pair_id'] or row.get('platform_id')!=pair['platform_id'] or row.get('payload_core_hash')!=pair['payload_core_hash']:raise ValueError('ledger pair assignment differs from frozen vector')
   if pair['payload'] is None:
    if sent or row.get('reason')!='missing_pair_payload':raise ValueError('missing pair was sent or hidden')
   elif sent:
    request=json.loads((root/'raw'/(row['id']+'.request.json')).read_text())
    if request['payload']!=pair['payload'] or json.loads(request['body_utf8'])!=pair['payload'] or request['body_sha256']!=hashlib.sha256(request['body_utf8'].encode()).hexdigest() or request['payload_core_hash']!=pair['payload_core_hash'] or row.get('payload_core_hash')!=pair['payload_core_hash'] or request['pair_id']!=pair['pair_id'] or row.get('pair_id')!=pair['pair_id'] or request['platform_id']!=pair['platform_id'] or row.get('platform_id')!=pair['platform_id'] or not row['send']<=request['observed']<=row['end']:raise ValueError('actual direct request differs from its full pair')
   pair_usage.append({'pair_id':pair['pair_id'],'platform_id':pair['platform_id'],'direct_id':row['id'],'platform_usage':pair['platform_usage'],'direct_usage':row.get('usage'),'platform_status':pair['platform_status'],'direct_status':row['status'],'input_tokens_equal':pair['platform_usage']['prompt_tokens']==row['usage']['prompt_tokens'] if usage_ok(pair['platform_usage']) and usage_ok(row.get('usage')) else None,'output_tokens_equal':pair['platform_usage']['completion_tokens']==row['usage']['completion_tokens'] if usage_ok(pair['platform_usage']) and usage_ok(row.get('usage')) else None})
  if not sent:continue
  if row['planned'] is None or row['send']<row['planned'] or row['end']<row['send']:raise ValueError('invalid clock')
  for field in ('ack','first_content'):
   if row[field] is not None and not row['send']<=row[field]<=row['end']:raise ValueError('invalid clock '+field)
  raw=root/'raw'/(row['id']+'.jsonl')
  if not raw.exists() and row.get('http') in (200,202):raise ValueError('raw stream missing')
  if raw.exists():verify_raw(row,raw)
  lags.append(row['send']-row['planned'])
  if row['status']=='complete':
   if not usage_ok(row['usage']) or row['first_content'] is None:raise ValueError('success lacks evidence')
   latencies.append(row['end']-row['send']);ttfts.append(row['first_content']-row['send']);tokens+=row['usage']['completion_tokens'];lengths.append(row['usage']['completion_tokens']);stops[row['finish_reason']]=stops.get(row['finish_reason'],0)+1
  elif row['usage'] is None:unknown_usage+=1
 def p95(xs):return sorted(xs)[math.ceil(.95*len(xs))-1] if xs else None
 sent=trace['count']-counts['generator_drop'];end=max(r['end'] for r in rows);elapsed=end-trace['t0'];offer=trace['offer_end'];offer_duration=offer-trace['t0'] if offer else None
 summary={'kind':run['kind'],'path':trace['path'],'mode':trace['mode'],'concurrency':trace['concurrency'],'rate':trace['rate'],'planned':trace['count'],'sent':sent,**counts,'success_rate_planned':counts['complete']/trace['count'],'n_success':len(latencies),'p95_complete_s':p95(latencies),'p95_ttft_s':p95(ttfts),'p95_send_lag_s':p95(lags),'cohort_seconds':elapsed,'cohort_complete_rps':counts['complete']/elapsed,'cohort_success_output_tokens_per_s':tokens/elapsed,'success_output_tokens':tokens,'unknown_failed_usage':unknown_usage,'output_lengths':lengths,'stop_reasons':stops,'offer_seconds':offer_duration,'send_in_offer':sum(r['send'] is not None and offer is not None and r['send']<offer for r in rows),'complete_in_offer_rps':sum(r['status']=='complete' and offer is not None and r['end']<offer for r in rows)/offer_duration if offer_duration else None,'quantile':'nearest-rank/exploratory/no independent repeats','censored_first_content':sum(r['send'] is not None and r['first_content'] is None for r in rows),'manifest_sha256':actual}
 if vector is not None:summary['paired_usage']=pair_usage;summary['pairs_sha256']=trace['pairs_sha256']
 (root/'summary.json').write_text(json.dumps(summary,indent=2));return summary

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 q=sub.add_parser('point');q.add_argument('--path',choices=['direct','platform'],required=True);q.add_argument('--mode',choices=['closed','open'],required=True);q.add_argument('--base',required=True);q.add_argument('--payload');q.add_argument('--pairs');q.add_argument('--pairs-sha256');q.add_argument('--out',required=True);q.add_argument('--prefix');q.add_argument('--concurrency',type=int,default=1);q.add_argument('--count',type=int,default=20);q.add_argument('--rate',type=float,default=1);q.add_argument('--max-inflight',type=int,default=32);q.add_argument('--drain',type=float,default=90);q.add_argument('--kind',choices=['synthetic','pilot','formal','diagnostic','independent'],default='synthetic')
 r=sub.add_parser('recompute');r.add_argument('--out',required=True);r.add_argument('--anchor')
 args=p.parse_args()
 if args.command=='point':
  if args.kind!='synthetic' and args.max_inflight!=32:p.error('real workloads require max-inflight32')
  if not 1<=args.max_inflight<=32 or not 1<=args.count<=20 or not 1<=args.concurrency<=32 or not 0<args.drain<=90 or not math.isfinite(args.rate) or not args.rate>0 or not args.base.startswith('http://127.0.0.1:'):p.error('bounded loopback point required')
  point(args)
 else:print(json.dumps(recompute(args.out,args.anchor)))
if __name__=='__main__':main()
