"""Read-only StageB readiness. Never starts a model or changes shared resources."""
import argparse,hashlib,json,socket,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--out',required=True);a=p.parse_args();config=Path(a.config);c=json.loads(config.read_text());out=Path(a.out)
if out.exists():raise RuntimeError('new receipt required')
receipt={'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'snapshots':[],'ready':False}
def command(args):return subprocess.check_output(args,text=True).strip()
def check_manifest(manifest,root):
    raw=Path(manifest).read_bytes();rows=json.loads(raw);mismatches=[]
    for row in rows:
        path=Path(root)/row['path'];digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        if digest.hexdigest()!=row['sha256'] or path.stat().st_size!=row['bytes']:mismatches.append(row['path'])
    return {'manifest_sha256':hashlib.sha256(raw).hexdigest(),'files':len(rows),'mismatches':mismatches}
try:
    receipt['image']=command(['docker','image','inspect',c['image'],'--format','{{.Id}}'])
    if receipt['image']!=c['image']:raise RuntimeError('image mismatch')
    if c['container'] in command(['docker','ps','-a','--format','{{.Names}}']).splitlines():raise RuntimeError('container collision')
    with socket.socket() as s:s.bind(('127.0.0.1',c['port']))
    for key,manifest,root in [('model',c['model_manifest'],c['model_path']),('dependencies',c['dependency_manifest'],c['dependency_path'])]:
        receipt[key]=check_manifest(manifest,root)
        if receipt[key]['mismatches']:raise RuntimeError(key+' identity mismatch')
    for index in range(2):
        apps=command(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'])
        metrics=command(['nvidia-smi','-i',c['gpu_uuid'],'--query-gpu=uuid,memory.used,utilization.gpu','--format=csv,noheader,nounits'])
        row=metrics.split(',');busy=any(line.split(',')[0].strip()==c['gpu_uuid'] for line in apps.splitlines())
        receipt['snapshots'].append({'utc_epoch':time.time(),'gpu':metrics,'matching_compute':busy})
        if row[0].strip()!=c['gpu_uuid'] or busy or float(row[1])>=1024 or float(row[2])>5:raise RuntimeError('GPU unavailable')
        if index==0:time.sleep(10)
    receipt['ready']=True
except Exception as exc:receipt['error']=str(exc)
finally:out.write_text(json.dumps(receipt,indent=2))
print(json.dumps(receipt));raise SystemExit(0 if receipt['ready'] else 1)
