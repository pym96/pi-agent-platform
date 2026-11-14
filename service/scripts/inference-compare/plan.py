"""Deterministic protocol plan; no clock, network or model work."""
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_EVEN

ORDER=['closed1','openlow','closed4','openmid','closed8','openhigh']

def freeze_rates(a_ns,b_ns):
    for values in (a_ns,b_ns):
        if len(values)!=6 or any(type(x) is not int or x<=0 for x in values):
            raise ValueError('six successful positive integer-ns calibration durations required per arm')
    with localcontext() as ctx:
        ctx.prec=50;ctx.rounding=ROUND_HALF_EVEN
        a=Decimal(6_000_000_000)/sum(a_ns);b=Decimal(6_000_000_000)/sum(b_ns)
        rates={'low':min(a,b)*Decimal('.5'),'mid':(a*b).sqrt(),'high':max(a,b)*2}
        return {name:{'rate':str(rate),'offset_ns':[int((Decimal(k)*10**9/rate).to_integral_value(rounding=ROUND_FLOOR)) for k in range(20)],
                      'offer_end_ns':int((Decimal(20)*10**9/rate).to_integral_value(rounding=ROUND_CEILING))}
                for name,rate in rates.items()}

def payload(label):
    return {'model':'Qwen3-8B','stream':True,'max_tokens':128,
            'messages':[{'role':'user','content':'List consecutive positive integers separated by commas. Continue until the output limit. Request '+label+'.'}]}

def formal_blocks(rates):
    blocks=[]
    for ident in ['A1','B1','B2','A2']:
        repeat=int(ident[1]);points=[]
        for name in ORDER if repeat==1 else list(reversed(ORDER)):
            point={'name':name,'mode':'closed' if name.startswith('closed') else 'open',
                   'slots':[{'id':f'r{repeat}-{name}-{k:02d}','payload':payload(f'r{repeat}-{name}-{k:02d}')} for k in range(20)]}
            if point['mode']=='closed':point.update(concurrency=int(name[-1]),total_limit_ns=600*10**9)
            else:point.update(rates[name[4:]],max_inflight=32,drain_limit_ns=90*10**9)
            points.append(point)
        blocks.append({'id':ident,'arm':ident[0],'repeat':repeat,'max_attempts':130,
                       'warmup':[{'id':f'warmup-{k}','payload':payload(f'warmup-{k}')} for k in range(2)],
                       'points':points,'recovery_slot':{'id':'recovery','payload':payload('recovery')}})
    return blocks

def pilot_block(arm):
    return {'id':'pilot'+arm,'arm':arm,'max_attempts':16,'warmup':[
        {'id':f'warmup-{k}','payload':payload(f'warmup-{k}')} for k in range(2)],
        'points':[{'name':'calibration','mode':'closed','concurrency':1,'total_limit_ns':600*10**9,
                   'slots':[{'id':f'calibration-{k}','payload':payload(f'calibration-{k}')} for k in range(6)]}],
        'recovery_slot':{'id':'recovery','payload':payload('recovery')}}

def review_blocks(rates):
    blocks=[]
    base=formal_blocks(rates)[0]
    for arm in ('A','B'):
        import copy
        closed=copy.deepcopy(base['points'][0]);closed['slots']=closed['slots'][:4]
        opened=copy.deepcopy(base['points'][-1]);opened['slots']=opened['slots'][:8];opened['offset_ns']=opened['offset_ns'][:8]
        blocks.append({'id':'review'+arm,'arm':arm,'max_attempts':18,'warmup':copy.deepcopy(base['warmup']),
                       'points':[closed,opened],'recovery_slot':copy.deepcopy(base['recovery_slot'])})
    return blocks

def all_slots(block):
    return [*block['warmup'],*[s for p in block['points'] for s in p['slots']],block['recovery_slot']]

def validate_frozen_plan(plan,require_expected=False):
    import copy
    stage=plan.get('stage')
    if stage=='pilot':expected=[pilot_block(a) for a in ('A','B')]
    elif stage in ('formal','review'):
        calibration=plan['calibration'];rates=freeze_rates(calibration['A_ns'],calibration['B_ns'])
        if rates!=plan.get('rates'):raise ValueError('rates do not derive from frozen six-sample pilot')
        expected=formal_blocks(rates) if stage=='formal' else review_blocks(rates)
    else:raise ValueError('unknown plan stage')
    actual=copy.deepcopy(plan['blocks'])
    for block in actual:
        for slot in all_slots(block):
            ids=slot.pop('expected_input_ids',None)
            if require_expected and (not isinstance(ids,list) or not ids or any(type(x) is not int or x<0 for x in ids) or len(ids)+128>1024):raise ValueError('frozen expected input IDs required')
    if actual!=expected:raise ValueError('frozen payload/slot/order/offset/count contract differs')
    return True

def bind_expected(plan,mapping):
    import hashlib,json
    for block in plan['blocks']:
        for slot in all_slots(block):
            key=hashlib.sha256(json.dumps(slot['payload'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            a=mapping['A'][key];b=mapping['B'][key]
            if a!=b:raise ValueError('expected TF/vLLM template IDs differ')
            slot['expected_input_ids']=a
    validate_frozen_plan(plan,require_expected=True);return plan

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['pilot','formal','review'],required=True)
    p.add_argument('--expected-inputs',required=True);p.add_argument('--calibration');p.add_argument('--out',required=True);a=p.parse_args()
    plan={'stage':a.stage}
    if a.stage=='pilot':plan['blocks']=[pilot_block(x) for x in ('A','B')]
    else:
        calibration=json.loads(Path(a.calibration).read_text());plan.update(calibration=calibration,rates=freeze_rates(calibration['A_ns'],calibration['B_ns']))
        plan['blocks']=formal_blocks(plan['rates']) if a.stage=='formal' else review_blocks(plan['rates'])
    value=bind_expected(plan,json.loads(Path(a.expected_inputs).read_text()))
    with Path(a.out).open('x') as f:f.write(json.dumps(value,indent=2)+'\n')
