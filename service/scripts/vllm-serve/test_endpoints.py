import copy,json,pathlib,tempfile,unittest
from types import SimpleNamespace as NS
from endpoints import resolve,verify_file
CID='1'*64;NET='2'*64
class FakeDocker:
 project='pi-vllm24-b'
 labels={'workorder':'24','execution-sha':'3'*40,'com.docker.compose.project':project,'pi24.nonce':'test'}
 def __init__(self):
  self.row={'Id':CID,'State':{'Running':True},'Config':{'Labels':{**self.labels,'com.docker.compose.service':'model'}},'HostConfig':{'PortBindings':{}},'NetworkSettings':{'Ports':{},'Networks':{'owned':{'NetworkID':NET,'IPAddress':'172.23.0.2'}}}}
  self.net={'Id':NET,'Name':'owned','Internal':True,'Labels':self.labels.copy(),'Containers':{CID:{'IPv4Address':'172.23.0.2/16'}}}
 def inspect(self,cid):
  if cid!=CID:raise ValueError('wrong full CID')
  if any(self.row['Config']['Labels'].get(k)!=v for k,v in self.labels.items()):raise ValueError('container ownership')
  return self.row
 def command(self,args):
  assert args==['network','inspect',NET]
  return NS(returncode=0,stdout=json.dumps([self.net]),stderr='')
class EndpointTests(unittest.TestCase):
 def test_exact_membership_resolves_fixed_model_port(self):
  d=FakeDocker();m=resolve(d,[CID],NET);self.assertEqual(m['endpoints']['model'],{'cid':CID,'ip':'172.23.0.2','port':8082})
 def test_private_address_alone_never_authorizes_endpoint(self):
  for fault in ['network','membership','published','owner','noninternal']:
   d=FakeDocker()
   if fault=='network':d.row['NetworkSettings']['Networks']['owned']['NetworkID']='4'*64
   elif fault=='membership':d.net['Containers'][CID]['IPv4Address']='172.23.0.99/16'
   elif fault=='published':d.row['HostConfig']['PortBindings']={'8082/tcp':[{'HostIp':'127.0.0.1','HostPort':'18481'}]}
   elif fault=='owner':d.row['Config']['Labels']['pi24.nonce']='foreign'
   elif fault=='noninternal':d.net['Internal']=False
   with self.subTest(fault=fault),self.assertRaises(ValueError):resolve(d,[CID],NET)
 def test_endpoint_map_hash_and_live_identity_both_required(self):
  import hashlib
  d=FakeDocker();value=resolve(d,[CID],NET)
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp)/'map.json';p.write_text(json.dumps(value));digest=hashlib.sha256(p.read_bytes()).hexdigest()
   self.assertEqual(verify_file(d,p,digest),value)
   d.row['NetworkSettings']['Networks']['owned']['IPAddress']='172.23.0.7'
   with self.assertRaises(ValueError):verify_file(d,p,digest)
   with self.assertRaises(ValueError):verify_file(d,p,'0'*64)
if __name__=='__main__':unittest.main()
