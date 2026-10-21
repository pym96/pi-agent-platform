"""CPU-only cache hashing, tokenizer/template and deterministic corpus freeze."""
import hashlib,importlib.metadata,json,pathlib


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()


if __name__=='__main__':
    base=pathlib.Path('/experiment');model=pathlib.Path('/model')
    files=[dict(path=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(model.iterdir()) if p.is_file()]
    (base/'model-files.json').write_text(json.dumps(files,indent=2))
    upstream=json.loads((model/'download-manifest.json').read_text())
    index=json.loads((model/'model.safetensors.index.json').read_text())
    required=set(index['weight_map'].values()) | {'config.json','tokenizer.json','tokenizer_config.json','model.safetensors.index.json'}
    missing=sorted(required-set(x['path'] for x in files))
    if missing:raise RuntimeError('Missing required cache files: '+str(missing))
    checks=[]
    for sibling in upstream['siblings']:
        if sibling.get('lfs'):
            if not (model/sibling['rfilename']).exists():raise RuntimeError('missing expected LFS file '+sibling['rfilename'])
            found=next(x for x in files if x['path']==sibling['rfilename'])
            checks.append(dict(path=found['path'],match=found['sha256']==sibling['lfs']['sha256']))
    if not set(index['weight_map'].values()) <= set(c['path'] for c in checks) or not all(c['match'] for c in checks):
        raise RuntimeError('model cached LFS hash mismatch/required shard coverage')
    (base/'model-upstream-checks.json').write_text(json.dumps(dict(revision=upstream['sha'],required=sorted(required),missing=missing,checks=checks),indent=2))
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained('/model',local_files_only=True)
    corpus=[];counts=[]
    for i in range(32):
        text=f'Case {i:02d}. Explain the following service behavior in plain English. '
        text+=('A client submits a generation request. The service records its state, waits for an available worker, '
               'streams generated text, and records completion. Queue time, first content latency, output token count, '
               'and failures should be measured separately. Describe the likely bottleneck and one useful observation. ')*8
        ids=tokenizer.encode(text,add_special_tokens=False)[:230]
        text=tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
        corpus.append(text)
        counts.append(len(tokenizer.apply_chat_template([dict(role='user',content=text)],tokenize=True,
                         add_generation_prompt=True,enable_thinking=False)))
    config=dict(served_model='Qwen3-8B',model_id='Qwen/Qwen3-8B',revision=upstream['sha'],dtype='bfloat16',
        max_context=1024,max_output=128,temperature=0,seed=20261021,enable_thinking=False,prefix_cache=False,
        corpus=corpus,prompt_token_counts=counts,model_files_sha256=digest(base/'model-files.json'),
        chat_template_sha256=hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        sampling='greedy',closed_loads=[1,2,4,8,16,32],reps=2,window_s=45,drain_max_s=60,request_timeout_s=60,
        environment={d.metadata['Name']:importlib.metadata.version(d.metadata['Name']) for d in importlib.metadata.distributions()})
    (base/'config-pre-gate.json').write_text(json.dumps(config,ensure_ascii=False,indent=2))
    print(json.dumps(dict(model_hashes=len(files),upstream_checks=checks,prompt_token_counts=counts)),flush=True)
