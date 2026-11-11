"""Finite functional matrix client. All requests/partial streams survive assertion failure."""
import argparse,json,pathlib,time,urllib.request,urllib.error,uuid
from service.inference.oracle import inspect_stream
from owned import OwnedDocker
TERMINAL={'completed','interrupted','cancelled'}
class Client:
 def __init__(self,plan,out,model,api,deadline,owner=None,api_cid=None):
  self.plan=plan;self.out=pathlib.Path(out);self.out.mkdir(exist_ok=False)
  self.model=model;self.api=api;self.deadline=deadline;self.rows=[];self.serial=0;self.owner=owner;self.api_cid=api_cid
 def timeout(self):
  remain=self.deadline-time.time()
  if remain<=0:raise TimeoutError('matrix deadline')
  return min(30,remain)
 def write(self,name,value):(self.out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False))
 def call(self,method,url,payload=None,headers=None):
  self.serial+=1;ident=f'{self.serial:03d}';data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode()
  row={'id':ident,'method':method,'url':url,'payload':payload,'start_epoch':time.time(),'start_monotonic':time.monotonic(),'state':'sent'};self.rows.append(row);self.write('requests.json',self.rows)
  try:r=urllib.request.urlopen(urllib.request.Request(url,data=data,method=method,headers={'Content-Type':'application/json',**(headers or {})}),timeout=self.timeout())
  except urllib.error.HTTPError as e:r=e
  row.update(status=r.status,headers=dict(r.headers));self.write('requests.json',self.rows)
  return ident,row,r
 def json(self,method,url,payload=None):
  ident,row,r=self.call(method,url,payload)
  try:
   b=r.read();(self.out/(ident+'.body')).write_bytes(b)
   row.update(state='received',end_epoch=time.time(),body_file=ident+'.body');self.write('requests.json',self.rows)
   try:decoded=json.loads(b)
   except ValueError:decoded={'raw':b.decode(errors='replace')}
   return row['status'],decoded
  finally:r.close()
 def health(self):return self.json('GET',self.model+'/health')[1]
 def idle(self):
  end=min(self.deadline,time.time()+10)
  while time.time()<end:
   h=self.health()
   if h['active_generation']==0 and h['queued']==0 and h['ready']:return h
   time.sleep(.05)
  raise AssertionError('native settlement/ready not observed')
 def direct(self,spec):
  payload={'model':'Qwen3-8B','stream':True,'messages':[{'role':'user','content':spec['prompt']}],'max_tokens':spec['budget']}
  ident,row,r=self.call('POST',self.model+'/v1/chat/completions',payload);chunks=[];content=False
  try:
   while True:
    line=r.readline()
    if not line:break
    chunks.append(line);(self.out/(ident+'.body')).write_bytes(b''.join(chunks))
    if line.startswith(b'data: ') and line.strip()!=b'data: [DONE]':
     event=json.loads(line[6:]);text=event.get('choices',[{}])[0].get('delta',{}).get('content','')
     if text:content=True
    if spec['action']=='disconnect' and content:break
  finally:r.close();row.update(end_epoch=time.time(),state='disconnected' if spec['action']=='disconnect' and content else 'received',body_file=ident+'.body');self.write('requests.json',self.rows)
  body=b''.join(chunks).decode();result=inspect_stream(row['status'],body,spec['budget'])
  if spec['action']=='disconnect':assert content and not result['success']
  elif spec['action']=='deadline':assert not result['success'] and 'generation_deadline' in body
  else:assert result['success'] and result['content'].strip()
  h=self.idle();self.write(spec['id']+'.json',{'spec':spec,'request':ident,'result':result,'post_idle':h})
 def submit(self,session,key,prompt):
  status,task=self.json('POST',self.api+'/sessions/'+session+'/tasks',{'key':key,'prompt':prompt});assert status==202
  return task
 def history(self,session):
  status,history=self.json('GET',self.api+'/sessions/'+session+'/tasks');assert status==200;return history
 def task_done(self,session,ident):
  while time.time()<self.deadline:
   rows=self.history(session);task=next(x for x in rows if x['id']==ident)
   if task['status'] in TERMINAL:return task
   time.sleep(.05)
  raise AssertionError('PG-backed task not terminal')
 def events(self,session,task,cursor=0,disconnect=False):
  ident,row,r=self.call('GET',self.api+'/sessions/'+session+'/events',headers={'Last-Event-ID':str(cursor)})
  chunks=[];events=[];data=[];got_content=False
  try:
   while True:
    line=r.readline()
    if not line:raise AssertionError('SSE ended before expected event')
    chunks.append(line);(self.out/(ident+'.body')).write_bytes(b''.join(chunks))
    text=line.decode().strip()
    if text.startswith('data: '):data.append(text[6:])
    if not text and data:
     e=json.loads('\n'.join(data));data=[];assert e['id']>cursor;cursor=e['id'];events.append(e)
     if e['task']==task:
      if e['kind']=='text':got_content=True
      if disconnect and got_content:break
      if e['kind'] in TERMINAL:break
  finally:r.close();row.update(state='disconnected' if disconnect else 'received',end_epoch=time.time(),body_file=ident+'.body');self.write('requests.json',self.rows)
  return events,cursor
 def platform(self,spec):
  session=spec['session'];initial=self.health()['calls'];task=self.submit(session,spec['id'],spec['prompt']);events,cursor=self.events(session,task['id'],disconnect=spec['action']=='sse_disconnect')
  terminal=self.task_done(session,task['id']);assert terminal['status']=='completed'
  replay=[]
  if spec['action']=='sse_disconnect':
   replay,last=self.events(session,task['id'],cursor)
   assert replay and replay[-1]['kind']=='completed' and all(x['id']>cursor for x in replay)
   assert self.health()['calls']==initial+1
  assert self.health()['calls']==initial+1
  self.write(spec['id']+'.json',{'spec':spec,'task':task,'terminal':terminal,'events':events,'replay':replay})
  self.idle()
 def restart(self,spec):
  before=self.health();session=spec['session'];task=self.submit(session,spec['id'],spec['prompt'])
  # Poll native active state; do not infer model execution merely from API ACK.
  native_witness=None
  while time.time()<self.deadline:
   path=self.out.parent/'native-trace.jsonl'
   if path.exists():
    rows=[json.loads(line) for line in path.read_text().splitlines() if line]
    starts=[r for r in rows if r['event']=='native_start']
    if starts:
     native_id=starts[-1]['native_id']
     outputs=[r for r in rows if r.get('native_id')==native_id and r['event']=='native_output' and not r['finished']]
     if outputs and self.health()['active_generation']==1:native_witness=outputs[-1];break
   time.sleep(.005)
  assert native_witness is not None,'native streaming execution never observed'
  queued=self.submit(session,spec['id']+'-queued',spec['queued_prompt']);history=self.history(session)
  assert next(x for x in history if x['id']==task['id'])['status']=='running'
  assert next(x for x in history if x['id']==queued['id'])['status']=='queued'
  native_at_restart=self.health();assert native_at_restart['active_generation']==1
  owner=self.owner;assert owner is not None and owner.inspect(self.api_cid)['State']['Running']
  killed=owner.command(['kill','--signal','KILL',self.api_cid]);assert killed.returncode==0
  started=owner.command(['start',self.api_cid]);assert started.returncode==0
  self.write(spec['id']+'-restart.json',{'native_before':before,'native_at_restart':native_at_restart,'native_witness':native_witness,'task':task,'queued':queued,'pre_restart_history':history,'receipts':owner.receipts})
  while True:
   try:
    status,_=self.json('GET',self.api+'/health')
    if status==200:break
   except (OSError,ValueError):pass
   time.sleep(.05)
  first=self.task_done(session,task['id']);second=self.task_done(session,queued['id'])
  assert first['status']=='interrupted' and second['status']=='cancelled'
  status,_=self.json('POST',self.api+'/sessions/'+session+'/tasks',{'key':'blocked','prompt':spec['prompt']});assert status==429
  self.idle();h=self.health();time.sleep(.3);later=self.health();assert h['calls']==later['calls']==before['calls']+1
  self.write(spec['id']+'.json',{'spec':spec,'task':first,'queued':second,'no_resend_before':h,'no_resend_after':later})
 def run(self):
  planned=self.plan['steps'];results=[]
  try:
   for spec in planned:
    if spec['action'] in ('direct','disconnect','deadline'):self.direct(spec)
    elif spec['action'] in ('platform','sse_disconnect'):self.platform(spec)
    elif spec['action']=='restart':self.restart(spec)
    else:raise ValueError('unknown action')
    results.append(spec['id']);self.write('progress.json',{'planned':[x['id'] for x in planned],'completed':results})
  finally:self.write('progress.json',{'planned':[x['id'] for x in planned],'completed':results,'not_completed':[x['id'] for x in planned if x['id'] not in results]})

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--model',required=True);p.add_argument('--api',required=True);p.add_argument('--deadline',type=float,required=True);p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--nonce',required=True);p.add_argument('--api-cid');a=p.parse_args()
 owner=OwnedDocker(a.project,a.sha,a.nonce)
 Client(json.loads(pathlib.Path(a.plan).read_text()),a.out,a.model,a.api,a.deadline,owner,a.api_cid).run()
if __name__=='__main__':main()
