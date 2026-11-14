"""Issue28 authorization identity; pure-file rejection precedes every tool call.

The independently supplied phase digest is authority input, not a GO field's claim.
Hash binding is byte identity, not protection against an operator replacing authority.
"""
import datetime,hashlib,json,math,re,time
from pathlib import Path

ROOT=Path('/media/usv012/pjx/pi-agent-platform/experiments/28-engine-compare-20261114')
GPU='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
TIME_KEYS=['start','builder_latest_model_start','regulator_latest_model_start','all_server_owned_stop',
           'final_candidate_push_latest','final_Verdict_target','Master_main_push_latest','end']

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def number(x):
    if type(x) not in (int,float) or not math.isfinite(x) or x<0:raise ValueError('finite nonnegative number required')
    return x

def digest(x,n=64):
    if not isinstance(x,str) or not re.fullmatch('[0-9a-f]{'+str(n)+'}',x):raise ValueError('hex digest required')
    return x

def nonce(x):
    if not isinstance(x,str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',x):raise ValueError('safe unique nonce required')
    return x

def local_file(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:raise ValueError('relative contract path required')
    path=root.resolve()/p
    if path.resolve()!=path.absolute():raise ValueError('symlink contract path')
    return path

def validate(path,go_digest,phase_path,phase_digest,now=None):
    path=Path(path);root=path.parent
    if sha(path)!=digest(go_digest) or sha(phase_path)!=digest(phase_digest):raise ValueError('GO/independent phase hash mismatch')
    g=json.loads(path.read_text());phase=json.loads(Path(phase_path).read_text())
    if g.get('schema')!='pi28-stage-go/v1' or type(g.get('issue')) is not int or g['issue']!=28:raise ValueError('GO schema/issue')
    if phase.get('schema')!='pi28-master-phase-contract/v1' or type(phase.get('issue')) is not int or phase['issue']!=28 or not phase.get('id'):raise ValueError('phase schema/issue')
    if g.get('phase_contract_sha256')!=phase_digest:raise ValueError('independent phase binding')
    if phase.get('server_root')!=str(ROOT) or phase.get('physical_GPU_UUID')!=GPU or g.get('gpu_uuid')!=GPU:raise ValueError('phase root/device identity')
    times=[]
    for key in TIME_KEYS:
        value=phase.get(key)
        if not isinstance(value,str) or not value.endswith('Z'):raise ValueError('UTC Z phase required')
        times.append(number(datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()))
    if times!=sorted(times):raise ValueError('phase ordering')
    role=g.get('role');stage=g.get('stage')
    if role not in ('builder','regulator') or stage not in (('pilot','formal') if role=='builder' else ('review',)):raise ValueError('role/stage')
    now=number(time.time() if now is None else now);end=number(g.get('deadline_epoch'))
    if not times[0]<=now<=times[1 if role=='builder' else 2] or not now+30<end<=times[3]:raise ValueError('expired/stage boundary')
    digest(g.get('source_sha'),40);nonce(g.get('nonce'))
    ledger=local_file(root,g['ledger_file'])
    if sha(ledger)!=digest(g['ledger_sha256']):raise ValueError('ledger bytes changed')
    spent=json.loads(ledger.read_text())
    if spent!=g.get('spent') or set(spent)!={'device_s','native','POST','server_wall_s'}:raise ValueError('full prior stage ledger binding')
    prefix='B' if role=='builder' else 'R'
    for budget,field in [('device_Created_to_removed_s','device_s'),('native_generations','native'),('completion_POST','POST')]:
        limit=number(phase['budgets'][prefix+'_'+budget]);used=number(spent[field]);allocation=number(g['allocated_'+field])
        if allocation<=0 or used+allocation>limit:raise ValueError('stage allocation exceeds remaining '+field)
        if field!='device_s' and (type(used) is not int or type(allocation) is not int):raise ValueError('integer call accounting')
    if number(spent['server_wall_s'])+number(g['allocated_server_wall_s'])>number(phase['budgets']['server_conservative_wall_CPU_total_s']):raise ValueError('server cumulative wall budget')
    if type(spent['server_wall_s']) is not int or type(g['allocated_server_wall_s']) is not int:raise ValueError('conservative integer wall seconds required')
    if end-now>g['allocated_device_s'] or g['allocated_server_wall_s']<g['allocated_device_s']:raise ValueError('stage wall/device bound')
    plan_path=local_file(root,g['plan_file'])
    if sha(plan_path)!=digest(g['plan_sha256']):raise ValueError('plan bytes changed')
    plan=json.loads(plan_path.read_text())
    expected=['pilotA','pilotB'] if stage=='pilot' else ['A1','B1','B2','A2'] if stage=='formal' else ['reviewA','reviewB']
    models=g.get('models',[])
    if [m.get('id') for m in models]!=expected or [b.get('id') for b in plan.get('blocks',[])]!=expected:raise ValueError('pre-registered exact lifecycle sequence')
    cap=16 if stage=='pilot' else 130 if stage=='formal' else 18
    lower=times[0];nonces={g['nonce']}
    for ident,model,block in zip(expected,models,plan['blocks']):
        expected_arm=ident[-1] if stage in ('pilot','review') else ident[0]
        if model.get('arm')!=expected_arm or block.get('arm')!=expected_arm:raise ValueError('named lifecycle arm identity')
        if type(model.get('max_attempts')) is not int or model['max_attempts']!=cap or block.get('max_attempts')!=cap:raise ValueError('model attempt cap')
        nonce(model.get('nonce'))
        if model['nonce'] in nonces:raise ValueError('duplicate model nonce')
        nonces.add(model['nonce']);deadline=number(model.get('deadline_epoch'))
        if not lower+15<deadline<=end:raise ValueError('ordered finite model deadline')
        lower=deadline
    required=18 if stage=='pilot' else 512 if stage=='formal' else 32
    if g['allocated_native']<required or g['allocated_POST']<required:raise ValueError('insufficient planned stage allocation')
    entries=g.get('entry_hashes')
    if not isinstance(entries,dict) or not entries:raise ValueError('entry file closure required')
    for name,value in entries.items():local_file(Path('/source'),name);digest(value)
    return g

def verify_entries(go,source):
    source=Path(source)
    expected={str(p.relative_to(source)) for p in (list((source/'service/scripts/inference-compare').glob('*.py'))+list((source/'service/inference').glob('*.py')))}
    expected.update('service/scripts/'+name for name in ['vllm-serve/owned.py','vllm-compat/native.py','vllm-compat/driver.py','nginx-entry/measurement.py'])
    if set(go['entry_hashes'])!=expected:raise ValueError('complete executing source file closure required')
    for name,value in go['entry_hashes'].items():
        if sha(local_file(Path(source),name))!=value:raise ValueError('entry bytes changed: '+name)

def consume(path):
    with Path(path).open('x') as f:f.write(str(time.time()))
