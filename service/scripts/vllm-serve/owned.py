"""Exact-ID task ownership and reconciled cleanup. Inventory failures stay unknown."""
import json,re,subprocess,time
class OwnedDocker:
 def __init__(self,project,sha,nonce,runner=None):
  self.labels={'workorder':'24','execution-sha':sha,'com.docker.compose.project':project,'pi24.nonce':nonce}
  self.project=project;self.receipts=[]
  self.runner=runner or (lambda args:subprocess.run(['docker',*args],capture_output=True,text=True,timeout=8))
 def command(self,args):
  start=time.time()
  try:r=self.runner(args)
  except Exception as e:self.receipts.append({'command':args,'start':start,'end':time.time(),'error':repr(e)});raise
  self.receipts.append({'command':args,'start':start,'end':time.time(),'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});return r
 def ids(self,text):
  rows=text.splitlines()
  if any(not re.fullmatch('[a-f0-9]{64}',x) for x in rows):raise RuntimeError('invalid exact-ID inventory')
  return set(rows)
 def inspect(self,cid):
  if not re.fullmatch('[a-f0-9]{64}',cid):raise RuntimeError('full CID required')
  r=self.command(['inspect',cid])
  if r.returncode:
   inventory=self.command(['ps','-a','-q','--no-trunc'])
   if inventory.returncode:raise RuntimeError('missing-ID inventory unknown')
   if cid not in self.ids(inventory.stdout):return None
   raise RuntimeError('inspect failed on existing object')
  rows=json.loads(r.stdout)
  if len(rows)!=1 or rows[0]['Id']!=cid:raise RuntimeError('inspect identity mismatch')
  row=rows[0];labels=row['Config']['Labels'] or {}
  if any(labels.get(k)!=v for k,v in self.labels.items()):raise RuntimeError('exact object ownership mismatch')
  if type(row['State']['Running']) is not bool:raise RuntimeError('running state unknown')
  return row
 def discover(self,known):
  r=self.command(['ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+self.project])
  if r.returncode:raise RuntimeError('project inventory unknown')
  rows=[]
  for cid in self.ids(r.stdout):
   row=self.inspect(cid)
   if row is not None:known[cid]=row;rows.append(row)
  return rows
 def cleanup(self,cids):
  states={};errors=[]
  for cid in cids:
   try:
    row=self.inspect(cid)
    if row is not None and row['State']['Running']:
     r=self.command(['stop','--time','2',cid]);row=self.inspect(cid)
     if row is not None and (r.returncode or row['State']['Running']):raise RuntimeError('stop failed/unsettled')
    if row is not None:
     r=self.command(['rm',cid])
     if r.returncode or self.inspect(cid) is not None:raise RuntimeError('remove not confirmed')
    states[cid]='removed'
   except Exception as e:states[cid]='unknown';errors.append({'cid':cid,'error':repr(e)})
  return {'success':not errors,'containers':states,'errors':errors,'receipts':self.receipts}
