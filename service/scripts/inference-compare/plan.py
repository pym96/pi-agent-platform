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
                       'points':points,'recovery_payload':payload('recovery')})
    return blocks

def pilot_block(arm):
    return {'id':'pilot'+arm,'arm':arm,'max_attempts':16,'warmup':[
        {'id':f'warmup-{k}','payload':payload(f'warmup-{k}')} for k in range(2)],
        'points':[{'name':'calibration','mode':'closed','concurrency':1,'total_limit_ns':600*10**9,
                   'slots':[{'id':f'calibration-{k}','payload':payload(f'calibration-{k}')} for k in range(6)]}],
        'recovery_payload':payload('recovery')}
