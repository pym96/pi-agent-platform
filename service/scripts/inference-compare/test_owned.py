import json,unittest
from types import SimpleNamespace as NS
from owned import OwnedDocker

class OwnedTests(unittest.TestCase):
    def test_exact28_identity_cannot_clean_old24_or_foreign_objects(self):
        calls=[];cid='c'*64
        def runner(args):
            calls.append(args)
            return NS(returncode=0,stderr='',stdout=json.dumps([{'Id':cid,'Config':{'Labels':{'workorder':'24'}},'State':{'Running':True}}]))
        docker=OwnedDocker('builder','a'*40,'new28',runner=runner)
        self.assertEqual(docker.labels['workorder'],'28')
        self.assertEqual(docker.labels['pi28.nonce'],'new28')
        result=docker.cleanup([cid])
        self.assertFalse(result['success'])
        self.assertEqual(calls,[['inspect',cid]])

if __name__=='__main__':unittest.main()
