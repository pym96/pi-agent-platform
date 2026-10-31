"""Synthetic metadata fixtures validate the identity reader; no NVIDIA calls here."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from device_proof import GPU,QUERY,validate
class DeviceProofTests(unittest.TestCase):
    def fixture(self,root):
        raw=Path(__file__).with_name('stage-b.json').read_bytes();config=json.loads(raw);digest=hashlib.sha256(raw).hexdigest();sha='a'*40
        model={'Id':'f'*64,'Image':config['image'],'State':{'Running':True},'Config':{'Entrypoint':['python','--max-attempts','3'],'User':'1001:1001','Labels':{'execution-sha':sha,'workorder':'12','com.docker.compose.service':'model','com.docker.compose.project':'pi-e2e12-1031-b'},'Env':['CUDA_VISIBLE_DEVICES=0','NVIDIA_VISIBLE_DEVICES='+GPU]},'Mounts':[{'Destination':a,'Source':b,'RW':False} for a,b in [('/source','/authorized/source'),('/model',config['model_path']),('/deps',config['dependency_path'])]],'HostConfig':{'NanoCpus':6*10**9,'Memory':28*2**30,'ReadonlyRootfs':True,'CapDrop':['ALL']}}
        receipt=lambda cmd,stdout:{'command':cmd,'started_utc_ns':1,'ended_utc_ns':2,'exit_code':0,'stdout':stdout,'stderr':''}
        rows={'stage-b.json':config,'source-identity.json':{'source_sha':sha,'config_sha256':digest,'tracked_dirty':False},'device-host.json':receipt(QUERY,'0, '+GPU+', NVIDIA GeForce RTX 4090\n'),'device-container.json':receipt(['docker','exec',model['Id'],*QUERY],'0, '+GPU+', NVIDIA GeForce RTX 4090\n'),'model-inspect.json':receipt(['docker','inspect',model['Id']],json.dumps([model]))}
        for name,value in rows.items():(root/name).write_text(json.dumps(value))
        (root/'stage-b.json').write_bytes(raw)
        return {'commit':sha,'config_sha256':digest,'resources':{'gpu_uuid':GPU,'host_gpu_index':0}},rows,model
    def test_consistent_mapping_and_mismatches(self):
        with tempfile.TemporaryDirectory(prefix='e2e12-device-reader-') as temp:
            root=Path(temp);run,rows,model=self.fixture(root);validate(root,run)
            for field in ('device-host.json','device-container.json'):
                original=(root/field).read_text();bad=copy.deepcopy(rows[field]);bad['stdout']=bad['stdout'].replace(GPU,'GPU-foreign')
                (root/field).write_text(json.dumps(bad))
                with self.assertRaises(AssertionError):validate(root,run)
                (root/field).write_text(original)
            for mutation in [lambda m:m['Config']['Env'].append('CUDA_VISIBLE_DEVICES=3'),lambda m:m['Config']['Labels'].update({'execution-sha':'b'*40}),lambda m:m['HostConfig'].update(Memory=0),lambda m:m['Mounts'][0].update(RW=True)]:
                bad=copy.deepcopy(model);mutation(bad);receipt=copy.deepcopy(rows['model-inspect.json']);receipt['stdout']=json.dumps([bad]);(root/'model-inspect.json').write_text(json.dumps(receipt))
                with self.assertRaises(AssertionError):validate(root,run)
                (root/'model-inspect.json').write_text(json.dumps(rows['model-inspect.json']))
            run['config_sha256']='0'*64
            with self.assertRaises(AssertionError):validate(root,run)
if __name__=='__main__':unittest.main()
