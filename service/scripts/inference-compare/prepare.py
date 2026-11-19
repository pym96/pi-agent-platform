"""Read-only CPU preparation. Each server use still needs its distinct stage GO."""
import argparse,hashlib,json,os,shutil,stat,sys
from pathlib import Path
from authority import sha
from plan import pilot_block,formal_blocks,freeze_rates,all_slots

def manifest_files(data):
    from authority import digest
    rows=data['files'] if isinstance(data,dict) else data;result=[];seen=set()
    for row in rows:
        p=Path(row['path']);size=row.get('bytes',row.get('size'))
        if p.is_absolute() or '..' in p.parts or str(p) in seen:raise ValueError('manifest path/duplicate')
        if type(size) is not int or size<0 or ('bytes' in row and 'size' in row and row['bytes']!=row['size']):raise ValueError('manifest size/bytes')
        seen.add(str(p));result.append({'path':str(p),'bytes':size,'sha256':digest(row['sha256'])})
    return result

def inventory(roots):
    rows=[];errors=[];apparent=0;allocated=0
    for root in roots:
        root=Path(root).resolve()
        if not root.exists():errors.append({'path':str(root),'error':'missing root'});continue
        own=root.lstat();apparent+=own.st_size;allocated+=own.st_blocks*512
        rows.append({'path':str(root),'bytes':own.st_size,'allocated_bytes':own.st_blocks*512,'uid':own.st_uid,'mode':stat.S_IMODE(own.st_mode),'symlink':False})
        def error(exc):errors.append({'path':exc.filename,'error':repr(exc)})
        for parent,dirs,files in os.walk(root,onerror=error,followlinks=False):
            for name in [*dirs,*files]:
                path=Path(parent)/name
                try:
                    s=path.lstat();size=s.st_size;blocks=s.st_blocks*512
                    rows.append({'path':str(path),'bytes':size,'allocated_bytes':blocks,'uid':s.st_uid,'mode':stat.S_IMODE(s.st_mode),'symlink':path.is_symlink()})
                    apparent+=size;allocated+=blocks
                except OSError as exc:errors.append({'path':str(path),'error':repr(exc)})
    return {'roots':[str(Path(p).resolve()) for p in roots],'complete':not errors,'apparent_bytes':apparent,'allocated_bytes':allocated,
            'free_bytes':shutil.disk_usage(Path(roots[0]).resolve()).free,'errors':errors,'files':rows}

def entries(source):
    root=Path(source).resolve();files=list((root/'service/scripts/inference-compare').glob('*.py'))+list((root/'service/inference').glob('*.py'))
    files += [root/'service/scripts'/name for name in ['vllm-serve/owned.py','vllm-compat/native.py','vllm-compat/driver.py','nginx-entry/measurement.py']]
    return {str(p.relative_to(root)):sha(p) for p in sorted(files)}

def token_mapping(arm,model):
    from transformers import AutoTokenizer
    import transformers
    tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True)
    plans=[pilot_block('A'),pilot_block('B'),*formal_blocks(freeze_rates([10**9]*6,[10**9]*6))]
    mapping={}
    for block in plans:
        for slot in all_slots(block):
            body=slot['payload'];messages=body['messages']
            if arm=='A':
                prompt=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)
                ids=tokenizer(prompt)['input_ids']
            else:ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False)
            key=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();mapping[key]=ids
    return {'arm':arm,'model':str(Path(model).resolve()),'transformers_version':transformers.__version__,
            'python':sys.version,'executable':str(Path(sys.executable).resolve()),'executable_sha256':sha(Path(sys.executable).resolve()),'expected_only':True,'mapping':mapping}

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    inv=sub.add_parser('inventory');inv.add_argument('--roots',nargs='+',required=True)
    ent=sub.add_parser('entries');ent.add_argument('--source',required=True)
    tok=sub.add_parser('tokens');tok.add_argument('--arm',choices=['A','B'],required=True);tok.add_argument('--model',required=True)
    net=sub.add_parser('network');net.add_argument('--role',choices=['builder','regulator'],required=True);net.add_argument('--source-sha',required=True);net.add_argument('--nonce',required=True)
    for s in (inv,ent,tok,net):s.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='network':
        from owned import OwnedDocker
        docker=OwnedDocker(a.role,a.source_sha,a.nonce);ident=docker.create_network()
        value={'network':docker.network(ident),'receipts':docker.receipts,'permission':'requires separate explicit CPU-stage network-creation GO'}
    else:value=inventory(a.roots) if a.action=='inventory' else entries(a.source) if a.action=='entries' else token_mapping(a.arm,a.model)
    with Path(a.out).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
    return 1 if a.action=='inventory' and not value['complete'] else 0

if __name__=='__main__':raise SystemExit(main())
