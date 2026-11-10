"""Full-field platform captures, immutable per-slot replay; never normalize model input."""
import hashlib,json,shutil,time
from pathlib import Path

def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_rows(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]
def build(platform,bridge,out,direct_prefix,pair_prefix):
    from load import recompute,digest
    platform=Path(platform);bridge=Path(bridge);out=Path(out);assert not out.exists();anchor=(platform/'manifest.sha256').read_text().strip();recompute(platform,anchor);out.mkdir(parents=True);shutil.copytree(platform,out/'platform-source');shutil.copyfile(bridge,out/'bridge.jsonl')
    trace=json.loads((platform/'trace.json').read_text());rows={x['id']:x for x in read_rows(platform/'ledger.jsonl')};requests=[x for x in read_rows(bridge) if x.get('event')=='request'];slots=[]
    for i,item in enumerate(trace['slots']):
        ident=item['id'];matches=[x for x in requests if x.get('session')==ident]
        if len(matches)>1:raise ValueError('multiple actual requests for one platform slot')
        source=rows[ident];request=matches[0] if matches else None
        if request is not None:
            if source.get('task') is not None and request['task']!=source['task']:raise ValueError('bridge task mismatch')
            if source.get('model_call') is not None and request['id']!=source['model_call']:raise ValueError('bridge model call mismatch')
        payload=request['mapped'] if request is not None else None
        slots.append({'pair_id':pair_prefix+':'+str(i),'platform_id':ident,'direct_id':direct_prefix+'_'+str(i),'platform_status':source['status'],'platform_usage':source.get('usage'),'payload':payload,'payload_core_hash':digest(payload) if payload is not None else None,'missing_reason':'missing_pair_payload' if payload is None else None})
    value={'schema':'lb13-pairs-v1','created_epoch':time.time(),'platform_manifest_sha256':anchor,'bridge_sha256':file_hash(out/'bridge.jsonl'),'direct_prefix':direct_prefix,'pair_prefix':pair_prefix,'slots':slots};p=out/'pairs.json';p.write_text(json.dumps(value,indent=2));h=file_hash(p);(out/'pairs.sha256').write_text(h+'\n');validate(p,h,direct_prefix,len(slots));return p,h

def validate(path,anchor,prefix,count):
    from load import recompute,digest
    path=Path(path)
    if file_hash(path)!=anchor:raise ValueError('pair vector anchor mismatch')
    value=json.loads(path.read_text());root=path.parent
    if value['schema']!='lb13-pairs-v1' or value['direct_prefix']!=prefix or len(value['slots'])!=count:raise ValueError('pair vector shape/identity mismatch')
    recompute(root/'platform-source',value['platform_manifest_sha256'])
    trace=json.loads((root/'platform-source/trace.json').read_text());rows={x['id']:x for x in read_rows(root/'platform-source/ledger.jsonl')}
    if trace['path']!='platform' or len(trace['slots'])!=count:raise ValueError('pair source is not the full platform cohort')
    if file_hash(root/'bridge.jsonl')!=value['bridge_sha256']:raise ValueError('pair bridge snapshot mismatch')
    requests=[x for x in read_rows(root/'bridge.jsonl') if x.get('event')=='request'];pair_ids=[]
    for i,slot in enumerate(value['slots']):
        ident=trace['slots'][i]['id'];source=rows[ident];pair_ids.append(slot['pair_id'])
        if slot['pair_id']!=value['pair_prefix']+':'+str(i) or slot['platform_id']!=ident or slot['direct_id']!=prefix+'_'+str(i):raise ValueError('wrong pair/slot')
        if slot['platform_status']!=source['status'] or slot['platform_usage']!=source.get('usage'):raise ValueError('pair source ledger mismatch')
        matches=[x for x in requests if x.get('session')==ident]
        if len(matches)>1:raise ValueError('ambiguous actual pair payload')
        if not matches:
            if slot['payload'] is not None or slot['payload_core_hash'] is not None or slot['missing_reason']!='missing_pair_payload':raise ValueError('missing pair cannot have fallback payload')
            continue
        request=matches[0]
        if source.get('task') is not None and request['task']!=source['task']:raise ValueError('pair task mismatch')
        if source.get('model_call') is not None and request['id']!=source['model_call']:raise ValueError('pair model call mismatch')
        if slot['payload']!=request['mapped'] or slot['payload_core_hash']!=digest(request['mapped']) or slot['missing_reason'] is not None:raise ValueError('pair payload differs from actual full bridge input')
    if len(set(pair_ids))!=count:raise ValueError('duplicate pair IDs')
    return value
