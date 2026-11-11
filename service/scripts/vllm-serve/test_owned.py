import importlib.util,pathlib,json,unittest
from types import SimpleNamespace as NS
spec=importlib.util.spec_from_file_location('owned',pathlib.Path(__file__).with_name('owned.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CID='a'*64
class OwnedTests(unittest.TestCase):
 def test_label_mismatch_never_stops_object(self):
  calls=[]
  def run(args):
   calls.append(args)
   return NS(returncode=0,stdout=json.dumps([{'Id':CID,'Config':{'Labels':{'workorder':'24','execution-sha':'b'*40,'com.docker.compose.project':'pi-vllm24-b','pi24.nonce':'FOREIGN'}},'State':{'Running':True}}]),stderr='')
  docker=m.OwnedDocker('pi-vllm24-b','b'*40,'ours',run)
  result=docker.cleanup([CID])
  self.assertFalse(result['success']);self.assertEqual(result['containers'][CID],'unknown')
  self.assertTrue(all(x[0]=='inspect' for x in calls))
 def test_failed_inventory_is_unknown_not_empty_cleanup_success(self):
  def run(args):return NS(returncode=1,stdout='',stderr='engine unavailable')
  docker=m.OwnedDocker('pi-vllm24-b','b'*40,'ours',run)
  with self.assertRaises(RuntimeError):docker.discover({})
if __name__=='__main__':unittest.main()

class ReconciliationTests(unittest.TestCase):
 def test_multicid_cleanup_attempts_known_other_after_first_unknown(self):
  other='c'*64;states={other:True};calls=[]
  def run(args):
   calls.append(args)
   if args[0]=='inspect':
    if args[1]==CID:return NS(returncode=1,stdout='',stderr='inspect unavailable')
    if other in states:
     return NS(returncode=0,stdout=json.dumps([{'Id':other,'Config':{'Labels':{'workorder':'24','execution-sha':'b'*40,'com.docker.compose.project':'pi-vllm24-b','pi24.nonce':'ours'}},'State':{'Running':states[other]}}]),stderr='')
    return NS(returncode=1,stdout='',stderr='missing')
   if args[0]=='ps':return NS(returncode=0,stdout=CID+'\n'+(other+'\n' if other in states else ''),stderr='')
   if args[0]=='stop':states[other]=False
   if args[0]=='rm':states.pop(other)
   return NS(returncode=0,stdout='',stderr='')
  docker=m.OwnedDocker('pi-vllm24-b','b'*40,'ours',run)
  r=docker.cleanup([CID,other]);self.assertFalse(r['success']);self.assertEqual(r['containers'],{CID:'unknown',other:'removed'})
  self.assertIn(['stop','--time','2',other],calls)
  self.assertNotIn(['stop','--time','2',CID],calls)
