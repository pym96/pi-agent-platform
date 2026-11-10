"""Recover a partial campaign from pinned originals; only a separate copy is recomputed."""
import argparse,hashlib,json,shutil
from pathlib import Path
from campaign import render,validate_plan
from load import recompute,seal

def sha(p):
 d=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):d.update(b)
 return d.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--manifest-sha256',required=True);p.add_argument('--campaign',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 root=Path(a.root).resolve();manifest=Path(a.manifest);out=Path(a.out).resolve();campaign=(root/a.campaign).resolve()
 if not campaign.is_relative_to(root) or out.is_relative_to(campaign):raise ValueError('separate derived output required')
 if sha(manifest)!=a.manifest_sha256:raise ValueError('original manifest anchor mismatch')
 files=json.loads(manifest.read_text())
 def verify_originals():
  for name,want in files.items():
   source=(root/name).resolve()
   if not source.is_relative_to(root) or sha(source)!=want:raise ValueError('original hash mismatch:'+name)
 verify_originals()
 def pinned(path):
  name=str(path.relative_to(root))
  if name not in files:raise ValueError('unanchored recovery input:'+name)
  return {'path':name,'sha256':files[name]}
 pinned(campaign/'frozen-plan.json');pinned(campaign/'results.json');plan=json.loads((campaign/'frozen-plan.json').read_text());validate_plan(plan);reported=json.loads((campaign/'results.json').read_text())
 if len(reported)!=12 or any(r['point']!=i['point'] for r,i in zip(reported,plan['order'])):raise ValueError('original point identity mismatch')
 # No unpinned file may be introduced into the recomputation copy.
 for source in campaign.rglob('*'):
  if source.is_file():pinned(source)
 out.mkdir(parents=True,exist_ok=False);shutil.copytree(campaign,out/'source-copy');(out/'originals-manifest.json').write_bytes(manifest.read_bytes());results=[]
 for item,old in zip(plan['order'],reported):
  original=campaign/item['point']/'summary.json';row=dict(item,planned=20)
  if original.exists():
   provenance=pinned(original);raw=json.loads(original.read_text());computed=recompute(out/'source-copy'/item['point'])
   if raw!=computed or raw['planned']!=20:raise ValueError('original summary differs from verified raw:'+item['point'])
   row.update(raw,summary_provenance=provenance,reason=old.get('reason'),stop_reason=old.get('stop_reason') or old.get('reason'))
  elif old.get('sent')==0 and old.get('generator_drop')==20 and not (campaign/item['point']/'trace.json').exists():
   row.update(sent=0,complete=0,rejected=0,failed=0,timeout=0,unresolved=0,generator_drop=20,n_success=0,reason=old.get('reason'),not_run_provenance=pinned(campaign/'results.json'))
  else:
   row.update({k:None for k in ['sent','complete','rejected','failed','timeout','unresolved','generator_drop','n_success']});row.update(reason=old.get('reason') or 'incomplete original point evidence',unknown_inventory=True,results_provenance=pinned(campaign/'results.json'))
  results.append(row)
 partial=any(r.get('reason') or r.get('unknown_inventory') or not r.get('summary_provenance') for r in results)
 inventory={k:sum(r[k] for r in results) if all(isinstance(r.get(k),int) for r in results) else None for k in ['planned','sent','complete','rejected','failed','timeout','unresolved','generator_drop']}
 status={'analysis_status':'recovered_with_provenance','status':'stopped' if partial else 'complete','original_manifest_sha256':a.manifest_sha256,'analysis_script_sha256':sha(__file__),'summary_source':'immutable originals; recompute only source-copy','original_files_verified':len(files),'unknown_inventory_points':[r['point'] for r in results if r.get('unknown_inventory')],**inventory}
 (out/'results.json').write_text(json.dumps(results,indent=2));(out/'recovery-status.json').write_text(json.dumps(status,indent=2));render(out,results);verify_originals();anchor=seal(out);print(json.dumps({**status,'derived_manifest_sha256':anchor}))

if __name__=='__main__':main()
