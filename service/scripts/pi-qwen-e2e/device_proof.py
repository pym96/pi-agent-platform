"""Capture raw host/container mapping; validate the authorized physical GPU identity."""
import argparse,csv,hashlib,io,json,os,subprocess,time
from pathlib import Path
GPU='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
QUERY=['nvidia-smi','--query-gpu=index,uuid,name','--format=csv,noheader,nounits']
FILES=('device-host.json','device-container.json','model-inspect.json','source-identity.json','stage-b.json')
def receipt(command):
    start=time.time_ns();r=subprocess.run(command,capture_output=True,text=True,check=False,timeout=20)
    result={'command':command,'started_utc_ns':start,'ended_utc_ns':time.time_ns(),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    if r.returncode:raise RuntimeError('identity command failed: '+str(result))
    return result

def validate(root,run):
    root=Path(root);config_raw=(root/'stage-b.json').read_bytes();config=json.loads(config_raw)
    assert hashlib.sha256(config_raw).hexdigest()==run['config_sha256']
    assert config['gpu_uuid']==GPU and config['host_gpu_index']==0 and config['cuda_visible_devices']=='0'
    assert run['resources']['gpu_uuid']==GPU and run['resources']['host_gpu_index']==0
    assert config['model_revision']=='b968826d9c46dd6066d109eabc6255188de91218'
    assert config['max_context']==1024 and config['max_output']==128
    source=json.loads((root/'source-identity.json').read_text())
    assert source['source_sha']==run['commit'] and source['config_sha256']==run['config_sha256'] and source['tracked_dirty'] is False
    host=json.loads((root/'device-host.json').read_text());container=json.loads((root/'device-container.json').read_text());inspection=json.loads((root/'model-inspect.json').read_text())
    for r in (host,container,inspection):assert r['exit_code']==0 and type(r['started_utc_ns']) is int and r['ended_utc_ns']>=r['started_utc_ns']
    assert host['command']==QUERY
    host_rows=[[v.strip() for v in row] for row in csv.reader(io.StringIO(host['stdout']))]
    assert [r for r in host_rows if r and r[0]=='0']==[['0',GPU,'NVIDIA GeForce RTX 4090']]
    inspected=json.loads(inspection['stdout']);assert len(inspected)==1;model=inspected[0]
    assert inspection['command']==['docker','inspect',model['Id']]
    assert container['command']==['docker','exec',model['Id'],*QUERY]
    assert [[v.strip() for v in row] for row in csv.reader(io.StringIO(container['stdout']))]==[['0',GPU,'NVIDIA GeForce RTX 4090']]
    argv=model['Config']['Entrypoint']
    assert argv[argv.index('--max-attempts')+1]=='3'
    assert model['Image']==config['image'] and model['State']['Running'] is True
    labels=model['Config']['Labels'];assert labels['execution-sha']==run['commit'] and labels['workorder']=='12' and labels['com.docker.compose.service']=='model'
    assert labels['com.docker.compose.project'] in ('pi-e2e12-1031-b','pi-e2e12-1031-r')
    env=dict(x.split('=',1) for x in model['Config']['Env'] if '=' in x)
    assert env['CUDA_VISIBLE_DEVICES']=='0' and env['NVIDIA_VISIBLE_DEVICES']==GPU
    mounts={m['Destination']:m for m in model['Mounts']}
    assert all(mounts[k]['RW'] is False for k in ('/source','/model','/deps'))
    assert mounts['/model']['Source']==config['model_path'] and mounts['/deps']['Source']==config['dependency_path']
    hostcfg=model['HostConfig'];assert hostcfg['NanoCpus']==6*10**9 and hostcfg['Memory']==28*2**30 and hostcfg['ReadonlyRootfs'] is True
    assert model['Config']['User']=='1001:1001' and 'ALL' in hostcfg['CapDrop']
    return {'host_gpu_index':0,'gpu_uuid':GPU,'container_id':model['Id'],'config_sha256':run['config_sha256']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--project',choices=['pi-e2e12-1031-b','pi-e2e12-1031-r'],required=True);p.add_argument('--sha',required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[3]
    assert str(repo).startswith('/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/') and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==a.sha
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip()
    ids=receipt(['docker','ps','-q','--filter','label=com.docker.compose.project='+a.project,'--filter','label=com.docker.compose.service=model'])['stdout'].splitlines();assert len(ids)==1
    inspect=receipt(['docker','inspect',ids[0]]);model=json.loads(inspect['stdout'])[0]
    # Docker accepts short IDs; save the exact full-ID command used by the validator.
    inspect=receipt(['docker','inspect',model['Id']])
    root=Path(a.out);root.mkdir(parents=True,exist_ok=False)
    for name,value in [('device-host.json',receipt(QUERY)),('device-container.json',receipt(['docker','exec',model['Id'],*QUERY])),('model-inspect.json',inspect)]:
        (root/name).write_text(json.dumps(value,indent=2))
    raw=Path(__file__).with_name('stage-b.json').read_bytes();(root/'stage-b.json').write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest();(root/'source-identity.json').write_text(json.dumps({'source_sha':a.sha,'config_sha256':digest,'tracked_dirty':False},indent=2))
    validate(root,{'commit':a.sha,'config_sha256':digest,'resources':{'gpu_uuid':GPU,'host_gpu_index':0}})
    print(json.dumps({'identity_captured':True,'source_sha':a.sha,'config_sha256':digest}))
if __name__=='__main__':main()
