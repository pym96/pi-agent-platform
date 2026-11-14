import pathlib,json,hashlib,math,datetime,calendar,collections
from decimal import Decimal
b=pathlib.Path(__file__).parent;r=b/'normal02-nov14-raw';run=r/'run-pi24-b-nov14-normal02';c=run/'client'
j=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]
watch=rows(run/'watch.jsonl');out=j(run/'outcome.json');req=j(c/'requests.json');native=rows(run/'native-trace.jsonl');counts=collections.Counter(x['event'] for x in native)
model=None
for rec in out['receipts']:
 if rec['command'][0]=='inspect' and rec['exit']==0:
  for d in json.loads(rec['stdout']):
   if d.get('Config',{}).get('Labels',{}).get('com.docker.compose.service')=='model':model=d
assert model
rm=[x for x in watch[-1]['receipts'] if x['command']==['rm',model['Id']] and x['exit']==0][0]
created=model['Created'];sec,frac=created.rstrip('Z').split('.');created_decimal=Decimal(calendar.timegm(datetime.datetime.strptime(sec,'%Y-%m-%dT%H:%M:%S').timetuple()))+Decimal('0.'+frac)
device_decimal=Decimal(str(rm['end']))-created_decimal
device_float=rm['end']-float(created_decimal)
intervals=[]
for s in [x for x in native if x['event']=='native_start']:
 rid=s['native_id'];z=[x for x in native if x.get('native_id')==rid];end=[x for x in z if x['event']=='native_settled'];assert len(end)==1
 outputs=[x for x in z if x['event']=='native_output'];last=outputs[-1] if outputs else {};intervals.append({'native_id':rid,'budget':s['budget'],'start':s['at'],'settled':end[0]['at'],'duration_s':end[0]['at']-s['at'],'aborted':end[0]['aborted'],'prompt_tokens':len(s['prompt_token_ids']),'observed_output_token_ids':len(last.get('token_ids',[])),'output_finished':last.get('finished'),'abort_sent':[x['at'] for x in z if x['event']=='abort_sent'],'scheduler_abort_ack':[x['at'] for x in z if x['event']=='scheduler_abort_ack']})
assert len(intervals)==9 and all(a['settled']<=z['start'] for a,z in zip(intervals,intervals[1:]))
pg={name:json.loads(j(run/('pg-'+name+'.json'))['stdout']) for name in ['tasks','events','sessions']}
steps=[]
for name in j(c/'progress.json')['planned']:
 p=c/(name+'.json');v=j(p);d={'id':name,'action':v['spec']['action'],'budget':v['spec']['budget'],'raw_sha256':sha(p)}
 if 'result'in v:d.update(result=v['result'],post_idle=v['post_idle'])
 if 'terminal'in v:d.update(task_id=v['task']['id'],status=v['terminal']['status'],event_count=len(v['events']),replay_count=len(v['replay']))
 if name=='api-restart':d.update(task=v['task'],queued=v['queued'],no_resend_before=v['no_resend_before'],no_resend_after=v['no_resend_after'],restart_witness=j(c/'api-restart-restart.json')['native_witness'])
 steps.append(d)
trans=j(b/'NORMAL02-FOREGROUND-TRANSPORT-RESULT.json');stage=j(b/'NORMAL02-GO-STAGE-TRANSPORT.json');obs=j(b/'NORMAL02-OBSERVE01-SSH.json');coll=j(b/'NORMAL02-RAW-COLLECTION-SSH.json')
cpu=[{'scope':'GO stage plus complete foreground including all preflight/hash and model/cleanup; no separate stage charge','start':stage['start'],'end':trans['end'],'wall_s':trans['end']-stage['start'],'charged_ceil_s':math.ceil(trans['end']-stage['start']),'foreground_only_s':trans['end']-trans['start']},{'scope':'independent read-only observer (overlaps foreground but conservatively charged separately)','start':obs['start'],'end':obs['end'],'wall_s':obs['end']-obs['start'],'charged_ceil_s':math.ceil(obs['end']-obs['start'])},{'scope':'raw collection and fresh closeout','start':coll['start'],'end':coll['end'],'wall_s':coll['end']-coll['start'],'charged_ceil_s':math.ceil(coll['end']-coll['start'])}]
newcpu=sum(x['charged_ceil_s'] for x in cpu);rss=rows(r/'outer-pi24-b-nov14-normal02/rss-affinity.jsonl');pre=j(run/'preflight.json');close=j(r/'NORMAL02-NOV14-CLOSEOUT.json')
report={'schema':'pi24-normal02-local-reconciliation/v1','role':'Working Agent (Builder)','workorder':24,'source':'9ea36d3221d024a6d8330322d330809fa9e283a6','GO_sha256':'8cd96f3b65fdbdfae1083c162e7257300c64aa3ed09362fd8e4745450a351ad1','raw_archive_sha256':sha(b/'normal02-nov14-raw.tgz'),'manifest_sha256':sha(r/'NORMAL02-NOV14-MANIFEST.json'),'archive_regular_files':142,'manifest_bad':0,'result':{'overall_success':out['overall_success'],'cleanup_success':out['cleanup_success'],'client_exit':out['client_exit'],'watch_exit':out['watch_exit'],'completed_steps':len(steps),'completion_POST_attempts':len([x for x in req if x['method']=='POST']),'native_starts':counts['native_start'],'native_settled':counts['native_settled'],'abort_sent':counts['abort_sent'],'scheduler_abort_ack':counts['scheduler_abort_ack'],'PG_tasks':len(pg['tasks']),'PG_statuses':dict(collections.Counter(x['status'] for x in pg['tasks'])),'PG_events':len(pg['events']),'PG_sessions':pg['sessions']},'steps':steps,'native_intervals':intervals,'device_ledger':{'CID':model['Id'],'Created_UTC':created,'Created_epoch_decimal':str(created_decimal),'watch_rm_receipt':rm,'increment_s_float_compatible':device_float,'increment_s_decimal_from_preserved_numeric_text':str(device_decimal),'prior_s':55.169294118881226,'cumulative_s_float_compatible':55.169294118881226+device_float,'cumulative_s_decimal':str(Decimal('55.169294118881226')+device_decimal),'rounding_note':'Float compatible ledger matches R; exact Docker nanoseconds retained; decimal difference is about 0.1 microsecond and no budget threshold is affected.','native_cumulative':9,'POST_cumulative':11,'device_limit_s':1200,'native_limit':32,'POST_limit':64},'CPU_prepare_ledger':{'method':'Conservative full wall charge covers preflight and hash; overlapping observer charged again; local analysis not server CPU. No hidden zero preflight and no separate stage double charge.','prior_s':4253.4357385,'items':cpu,'increment_s':newcpu,'cumulative_s':4253.4357385+newcpu,'limit_s':5400,'new600_remaining_s':573-newcpu},'guards':{'preflight':pre,'idle_gap_s':pre[1]['epoch']-pre[0]['epoch'],'outer_host_RSS_peak_bytes':max(x['rss_bytes'] for x in rss),'outer_affinity_all_0_1':all(x['affinity']==[0,1] for x in rss),'B_containers_after':close['B_containers'],'B_networks_after':close['B_networks'],'nonce_consumed':close['nonce_consumed'],'free_bytes':close['free_bytes'],'network_cleanup':out['network_cleanup']},'limitations':['Builder reconciliation is not final Verdict or performance/C10K/p95 evidence.','Single active generation remains 1; no batching improvement claim.','Physical PG data retained on server; archive includes raw logical PG dumps, excludes data/pg-data; symlinks retained in tar but not materialized on local extraction.','No authorization for another model lifecycle; all SSH/SCP ended.']}
p=b/'NORMAL02-LOCAL-RECONCILIATION.v1.json';assert not p.exists();p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'file':str(p),'sha256':sha(p),'result':report['result'],'device':report['device_ledger'],'CPU':report['CPU_prepare_ledger'],'guards':report['guards']},ensure_ascii=False,indent=2))
