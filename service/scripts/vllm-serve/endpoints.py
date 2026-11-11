"""Resolve only exact-owned containers on one pre-recorded internal network."""
import argparse,hashlib,ipaddress,json,pathlib
from owned import OwnedDocker
PORTS={'model':8082,'pi':8081,'api':8080}
def network(docker,ident):
 if len(ident)!=64 or any(c not in 'abcdef0123456789' for c in ident):raise ValueError('full expected network ID required')
 r=docker.command(['network','inspect',ident])
 if r.returncode:raise RuntimeError('network inspect unknown')
 rows=json.loads(r.stdout)
 if len(rows)!=1 or rows[0]['Id']!=ident:raise ValueError('network identity')
 row=rows[0]
 if row['Internal'] is not True or any(row.get('Labels',{}).get(k)!=v for k,v in docker.labels.items()):raise ValueError('network ownership/internal mismatch')
 return row

def resolve(docker,cids,network_id):
 net=network(docker,network_id);endpoints={}
 for cid in cids:
  row=docker.inspect(cid)
  if row is None or not row['State']['Running']:raise ValueError('endpoint container not running')
  service=row['Config']['Labels'].get('com.docker.compose.service')
  if service not in PORTS:continue
  if service in endpoints:raise ValueError('duplicate endpoint role')
  if row['HostConfig'].get('PortBindings') or any(row['NetworkSettings'].get('Ports',{}).values()):raise ValueError('published ports forbidden')
  nets=list(row['NetworkSettings']['Networks'].values())
  if len(nets)!=1 or nets[0]['NetworkID']!=network_id:raise ValueError('endpoint network mismatch')
  ip=nets[0]['IPAddress'];address=ipaddress.ip_address(ip)
  if address.version!=4 or not address.is_private or address.is_loopback or address.is_unspecified:raise ValueError('private IPv4 required')
  member=net['Containers'].get(cid)
  if member is None or member['IPv4Address'].split('/')[0]!=ip:raise ValueError('network membership/IP mismatch')
  endpoints[service]={'cid':cid,'ip':ip,'port':PORTS[service]}
 if 'model' not in endpoints:raise ValueError('model endpoint missing')
 return {'project':docker.project,'source_sha':docker.labels['execution-sha'],'nonce':docker.labels['pi24.nonce'],'network_id':network_id,'network_name':net['Name'],'endpoints':endpoints}

def verify_file(docker,path,digest):
 raw=pathlib.Path(path).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('endpoint map hash mismatch')
 value=json.loads(raw)
 actual=resolve(docker,[r['cid'] for r in value['endpoints'].values()],value['network_id'])
 if actual!=value:raise ValueError('endpoint map differs from exact live ownership')
 return value

def prepare(docker):
 name=docker.project+'-'+docker.labels['pi24.nonce']
 args=['network','create','--internal']
 for k,v in docker.labels.items():args+=['--label',k+'='+v]
 result=docker.command([*args,name])
 if result.returncode:raise RuntimeError('new internal network creation failed')
 ident=result.stdout.strip();row=network(docker,ident)
 return {'network_id':ident,'network_name':row['Name'],'labels':row['Labels'],'internal':row['Internal'],'receipts':docker.receipts}

def remove(docker,network_id):
 row=network(docker,network_id)
 if row['Containers']:raise RuntimeError('owned network still has containers')
 r=docker.command(['network','rm',network_id])
 if r.returncode:raise RuntimeError('owned network remove failed')
 inventory=docker.command(['network','ls','-q','--no-trunc'])
 if inventory.returncode or network_id in inventory.stdout.splitlines():raise RuntimeError('network removal unknown')
 return {'success':True,'network_id':network_id,'state':'removed'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--project',choices=['pi-vllm24-b','pi-vllm24-r'],required=True);p.add_argument('--sha',required=True);p.add_argument('--nonce',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 out=pathlib.Path(a.out)
 if out.exists():raise ValueError('new receipt required')
 d=OwnedDocker(a.project,a.sha,a.nonce);out.write_text(json.dumps(prepare(d),indent=2))
if __name__=='__main__':main()
