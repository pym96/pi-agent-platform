"""Rebuild frozen slots from original request/SSE/native/drain receipts; export CSV/SVG.

Never trust the producer's completed classification, metrics or derived plot.
"""
import argparse,base64,copy,csv,hashlib,json,sys
from pathlib import Path
from client import load_lines,reconcile,dump
from measurement import inspect_exchange,summarize
from plan import validate_frozen_plan
from authority import sha

def verify_planned_rows(rows,slots):
    if len(rows)!=len(slots) or [r['id'] for r in rows]!=[s['id'] for s in slots]:raise ValueError('frozen planned slot membership/order/count')
    for row,slot in zip(rows,slots):
        if row['payload']!=slot['payload']:raise ValueError('frozen slot payload changed')
        if 'expected_input_ids' in slot and row.get('expected_input_ids')!=slot['expected_input_ids']:raise ValueError('expected IDs changed')

def rebuild_request(folder,slot):
    raw=folder/(slot['id']+'.jsonl');drop=folder/(slot['id']+'.drop.json')
    if raw.exists()==drop.exists():raise ValueError('exactly one raw exchange or local drop required')
    if drop.exists():
        row=json.loads(drop.read_text())
        if row['classification']!='generator_drop' or row['sent_ns'] is not None:raise ValueError('local drop shape')
        return row
    events=load_lines(raw);planned=[r for r in events if r['event']=='planned'];terminal=[r for r in events if r['event']=='terminal']
    if len(planned)!=1 or planned[0]['slot']!=slot or len(terminal)!=1 or events[-1]['event']!='terminal':raise ValueError('raw slot plan/terminal identity')
    sends=[r for r in events if r['event']=='send'];headers=[r for r in events if r['event']=='headers'];eof=[r for r in events if r['event']=='eof'];errors=[r for r in events if r['event']=='transport_failure']
    if len(sends)>1 or len(headers)>1 or len(eof)>1 or len(errors)>1:raise ValueError('duplicate raw protocol receipt')
    final=terminal[0]['row'];sent=final['sent_ns']
    if eof and final['terminal_ns']!=eof[0]['at_ns']:raise ValueError('latency terminal must be actual observed EOF')
    if sent is None:
        if sends or headers or eof or errors or final['classification']!='generator_drop':raise ValueError('unsent drop contains sent protocol')
        return final
    if sends and sends[0]['at_ns']!=sent:raise ValueError('send timestamp mismatch')
    if not sends and not errors:raise ValueError('missing invocation receipt')
    chunks=[{'at_ns':r['at_ns'],'data_b64':r['data_b64']} for r in events if r['event']=='chunk']
    status=headers[0]['status'] if headers else None
    row={'id':slot['id'],'payload':slot['payload'],'expected_input_ids':slot['expected_input_ids'],
         'planned_ns':final['planned_ns'],'sent_ns':sent,'terminal_ns':final['terminal_ns'],'status':status,'chunks':chunks,'eof':bool(eof),
         'send_lateness_ns':max(0,sent-final['planned_ns']),'not_prepared_reason':None,'not_invoked_reason':None,
         **inspect_exchange(status,chunks,bool(eof),slot['expected_input_ids'],None)}
    if errors:row.update(classification=errors[0]['kind'],reason=errors[0].get('detail',errors[0]['kind']))
    if status!=200:
        try:row['http_error']=json.loads(b''.join(base64.b64decode(c['data_b64']) for c in chunks))
        except (ValueError,TypeError):row['http_error']=None
    return row

def verify_schedule(result,point):
    rows=result['rows'];start=result['start_ns']
    for index,row in enumerate(rows):
        planned=start+point['offset_ns'][index] if point['mode']=='open' else row['planned_ns']
        if row['planned_ns']!=planned:raise ValueError('open offset changed')
        sent=row['sent_ns']
        if sent is not None:
            if sent<planned:raise ValueError('sent before frozen offer')
            inflight=sum(r['sent_ns'] is not None and r['sent_ns']<=sent<r['terminal_ns'] for r in rows)
            cap=point['max_inflight'] if point['mode']=='open' else point['concurrency']
            if inflight>cap:raise ValueError('inflight/concurrency cap')
            if point['mode']=='closed' and any(r['sent_ns'] is not None and r['sent_ns']>sent for r in rows[:index]):raise ValueError('closed slot order')
        elif row['reason']=='max_inflight':
            if point['mode']!='open':raise ValueError('closed generator drop has invalid reason')
            at=row['terminal_ns'];active=sum(r['sent_ns'] is not None and r['sent_ns']<=at<r['terminal_ns'] for r in rows)
            if active<point['max_inflight']:raise ValueError('unjustified max_inflight drop')
        elif row['reason']!='absolute_deadline':raise ValueError('unregistered local drop reason')

def rebuild_point(model_root,point,arm,attempt_start):
    folder=model_root/point['name'];producer=json.loads((folder/'ledger.json').read_text())
    original=json.loads((folder/'response-ledger.json').read_text())
    if original['point']!=point or producer['point']!=point:raise ValueError('original point differs from frozen plan')
    start=original['start_ns'];end=original['offer_end_ns']
    if type(start) is not int or start<0 or type(end) is not int:raise ValueError('original clock type')
    expected_end=start+point['offer_end_ns'] if point['mode']=='open' else start
    if end!=expected_end or producer['start_ns']!=start or producer['offer_end_ns']!=end:raise ValueError('original clock/window differs from derived ledger or frozen mode')
    result={'point':point,'start_ns':start,'offer_end_ns':end,
            'rows':[rebuild_request(folder,s) for s in point['slots']]}
    verify_planned_rows(original['rows'],point['slots'])
    for row,receipt in zip(result['rows'],original['rows']):
        if any(row.get(k)!=receipt.get(k) for k in ('planned_ns','sent_ns','terminal_ns','status','chunks','eof')):raise ValueError('original response differs from request receipts')
        if row['planned_ns']<start or row['terminal_ns']<start:raise ValueError('original clock order')
    verify_planned_rows(result['rows'],point['slots']);verify_schedule(result,point)
    drain=json.loads((folder/'drain.json').read_text())
    last=drain[-1];health=last['health']
    if last['status']!=200 or json.loads(base64.b64decode(last['body_b64']))!=health:raise ValueError('drain health differs from raw query')
    attempt_end=attempt_start+sum(r['sent_ns'] is not None for r in result['rows'])
    if producer['attempt_start']!=attempt_start or producer['attempt_end']!=attempt_end or health['attempts']!=attempt_end:raise ValueError('independent attempt count/cost reconciliation')
    if health['ready'] is not True or health['active_generation']!=0 or health['queued']!=0 or not set(last['acquired'])<=set(last['settled']):raise ValueError('drain not settled')
    app=load_lines(model_root/'model-trace.jsonl');native=load_lines(model_root/('tf-trace.jsonl' if arm=='A' else 'native-trace.jsonl'))
    acquired={r['attempt'] for r in app if r['event']=='slot_acquired' and r['attempt']<=attempt_end}
    settled={r['attempt'] for r in app if r['event']=='settled' and r['attempt']<=attempt_end}
    if acquired!=set(last['acquired']) or settled!=set(last['settled']):raise ValueError('drain trace association differs')
    reconcile(result,app,native,arm,attempt_start,attempt_end)
    summary=summarize(result['rows'],result['start_ns'],result['offer_end_ns'],last['at_ns'])
    if summary!=producer['summary']:raise ValueError('producer metrics differ from independent raw reconstruction')
    result['summary']=summary;return result

def rebuild(plan,stage_root):
    validate_frozen_plan(plan,require_expected=True);stage_root=Path(stage_root)
    stage=json.loads((stage_root/'stage.json').read_text());expected=[b['id'] for b in plan['blocks']]
    if not stage['complete'] or [m['id'] for m in stage['models']]!=expected:raise ValueError('partial or changed stage lifecycle ledger')
    results=[];nonformal=[]
    for block in plan['blocks']:
        root=stage_root/block['id'];report=json.loads((root/'block-report.json').read_text())
        if not report['complete'] or report['id']!=block['id'] or report['arm']!=block['arm']:raise ValueError('block identity/completeness')
        points=[{'name':'warmup','mode':'closed','concurrency':1,'total_limit_ns':600*10**9,'slots':block['warmup']}]
        for p in block['points']:
            points.append(p);points.append({'name':p['name']+'-recovery','mode':'closed','concurrency':1,'total_limit_ns':90*10**9,'slots':[block['recovery_slot']]})
        attempts=0
        for point in points:
            value=rebuild_point(root,point,block['arm'],attempts);attempts+=value['summary']['Nsent']
            value.update(block=block['id'],arm=block['arm'],repeat=block.get('repeat'))
            (results if point['name'] in [p['name'] for p in block['points']] and plan['stage']!='pilot' else nonformal).append(value)
        if report['completion_POST']!=attempts:raise ValueError('block POST cost does not match raw')
    if plan['stage']=='formal' and (len(results)!=24 or sum(len(p['rows']) for p in results)!=480):raise ValueError('formal frozen denominator incomplete')
    return {'stage':plan['stage'],'points':results,'nonformal':nonformal,'ITL':'unmeasured','inference':'whole-implementation comparison; two paired repeats exploratory only'}

def export(result,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);dump(out/'recomputed.json',result)
    rows=[{'block':p['block'],'arm':p['arm'],'repeat':p['repeat'],'point':p['point']['name'],**p['summary']} for p in result['points']]
    if rows:
        with (out/'points.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    slots=[{'block':p['block'],'point':p['point']['name'],'slot':r['id'],'classification':r['classification'],
            'sent_ns':r['sent_ns'],'terminal_ns':r['terminal_ns'],'actual_output_tokens':None if r.get('actual_output_ids') is None else len(r['actual_output_ids'])}
           for p in [*result['points'],*result['nonformal']] for r in p['rows']]
    with (out/'slots.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(slots[0]));writer.writeheader();writer.writerows(slots)
    if result['stage']=='formal':
        comparisons=[]
        for point in dict.fromkeys(r['point'] for r in rows):
            for metric in ['requests_per_s','output_tokens_per_s','completion_p95_ns','ttft_p95_ns']:
                pairs=[]
                for repeat in (1,2):
                    arms={r['arm']:r[metric] for r in rows if r['point']==point and r['repeat']==repeat}
                    a,b=arms['A'],arms['B'];pairs.append({'repeat':repeat,'A':a,'B':b,'B_minus_A':None if a is None or b is None else b-a,'B_over_A':None if a in (None,0) or b is None else b/a})
                differences=[p['B_minus_A'] for p in pairs if p['B_minus_A'] is not None];ratios=[p['B_over_A'] for p in pairs if p['B_over_A'] is not None]
                comparisons.append({'point':point,'metric':metric,'pairs':pairs,'difference_range':None if not differences else [min(differences),max(differences)],'ratio_range':None if not ratios else [min(ratios),max(ratios)],'exploratory_two_pairs_no_CI_or_SLA':True})
        dump(out/'paired-comparisons.json',comparisons)
    return rows

def plots(rows,out,stage_root=None):
    from plot import plots as draw
    draw(rows,out,stage_root)

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--stage-root',required=True);p.add_argument('--out',required=True);p.add_argument('--plots',action='store_true');a=p.parse_args()
    if sha(a.plan)!=a.plan_sha256:raise ValueError('plan SHA mismatch')
    result=rebuild(json.loads(Path(a.plan).read_text()),a.stage_root);rows=export(result,a.out)
    if a.plots:plots(rows,a.out,a.stage_root)
    files=[{'path':str(f.relative_to(Path(a.out))),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(Path(a.out).rglob('*')) if f.is_file()]
    dump(Path(a.out)/'manifest.json',files)
    return 0

if __name__=='__main__':raise SystemExit(main())
