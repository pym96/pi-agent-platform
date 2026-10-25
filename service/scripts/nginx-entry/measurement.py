"""Strict raw-receipt analysis; HTTP success cohort is separate from all attempts."""
import csv,json,math,datetime,re
from pathlib import Path

def summarize_rows(rows,planned):
    if planned<=0 or len(rows)>planned:raise ValueError('invalid attempt denominator')
    ok=[int(r['latency_ns']) for r in rows if 200<=int(r['code'])<300 and not r.get('error')]
    if any(x<0 for x in ok):raise ValueError('negative latency')
    ok.sort()
    q=lambda p:ok[math.ceil(p*len(ok))-1] if ok else None
    return {'planned':planned,'observed':len(rows),'missing':planned-len(rows),'success':len(ok),'error':planned-len(ok),'p50_ns':q(.5),'p95_ns':q(.95),'cohort':'observed HTTP 2xx, no transport error','quantile':'nearest-rank','rejected_http_429':sum(int(r['code'])==429 for r in rows),'http_error':sum(int(r['code'])>=300 for r in rows),'transport_error_observed':sum(int(r['code'])==0 or bool(r.get('error')) for r in rows),'timeout_observed':sum('timeout' in str(r.get('error','')).lower() or 'deadline' in str(r.get('error','')).lower() for r in rows)}

def timestamp_ns(value):
    match=re.search(r'\.(\d+)',value)
    frac=int((match.group(1)+'000000000')[:9]) if match else 0
    whole=re.sub(r'\.\d+','',value).replace('Z','+00:00')
    return int(datetime.datetime.fromisoformat(whole).timestamp())*10**9+frac

def analyze_run(directory):
    p=Path(directory);meta=json.loads((p/'run.json').read_text())
    if meta['tool']=='hey':
        with (p/'raw.csv').open() as f:
            data=list(csv.DictReader(f))
        rows=[{'code':int(r['status-code']),'latency_ns':round(float(r['response-time'])*1e9),'offset_s':float(r['offset'])} for r in data]
        end=max((r['offset_s']+r['latency_ns']/1e9 for r in rows),default=0)
        start=min((r['offset_s'] for r in rows),default=0)
        send_end=max((r['offset_s'] for r in rows),default=0)
    else:
        data=[json.loads(x) for x in (p/'decoded.jsonl').read_text().splitlines() if x.strip()]
        rows=[{'code':int(r['code']),'latency_ns':int(r['latency']),'error':r.get('error','')} for r in data]
        seq=[r['seq'] for r in data]
        if len(seq)!=len(set(seq)):raise ValueError('duplicate Vegeta sequence')
        sends=[timestamp_ns(r['timestamp']) for r in data]
        start=min(sends,default=0)/1e9;send_end=max(sends,default=0)/1e9
        end=max((t+int(r['latency']) for t,r in zip(sends,data)),default=0)/1e9
    result=summarize_rows(rows,meta['expected_scheduled']);result.update(meta)
    result['completion_fraction_scheduled']=result['success']/meta['expected_scheduled']
    result['completion_fraction_configured_intent']=result['success']/meta['configured_intent']
    result['completion_window_s']=max(0,end-start)
    result['observed_send_window_s']=max(0,send_end-start)
    result['observed_send_rps']=len(rows)/(send_end-start) if send_end>start else None
    result['sent_count']=len(rows) if meta['tool']=='vegeta' else None
    result['sent_boundary']='Vegeta decoded results; hey does not expose sent transport failures, planned/observed/missing retained'
    result['completed_receipts']=len(rows)
    result['observed_completion_rps']=len(rows)/(end-start) if end>start else None
    result['source_receipt']=str(p.name)
    if meta['exit_code']!=0:result['invalid']='tool nonzero exit'
    return result

def report(root):
    p=Path(root);config=json.loads((p/'measurement-config.json').read_text());runs=[]
    for i in range(12):
        d=p/f'point-{i:02d}'
        if not d.is_dir():raise ValueError(f'missing point {i}')
        r=analyze_run(d)
        if r['index']!=i:raise ValueError('duplicate/misplaced point identity')
        expected=config['points'][i]
        if r['source_sha']!=config['source_sha']:raise ValueError('source SHA mismatch')
        if any(r[k]!=expected[k] for k in ('tool','path','level','planned','configured_intent','expected_scheduled','generator_not_scheduled')):raise ValueError('matrix differs from frozen config')
        runs.append(r)
    if any(r.get('invalid') or r['missing'] for r in runs):raise ValueError('scheduled attempt receipts missing or invalid')
    (p/'measurement-summary.json').write_text(json.dumps({'config':config,'runs':runs,'boundary':'CPU synthetic platform HTTP health only; no Qwen/model throughput; one repetition exploratory'},indent=2))
    return runs

def summarize_go(events):
    tests=[e for e in events if e.get('Test') and e.get('Action') in ['pass','skip','fail']]
    if not tests or any(e['Action']!='pass' for e in tests):raise ValueError('empty, failed or skipped required Go tests')
    if not any(e['Test']=='TestDurableAdmissionAndRecovery' for e in tests):raise ValueError('required real PostgreSQL test absent')
    return {'tests':len(tests),'skipped':0,'no_test_packages':[e['Package'] for e in events if e.get('Action')=='skip' and not e.get('Test')]}

def scheduled_budget(tool,intent,level):
    if intent<=0 or level<=0:raise ValueError('positive frozen parameters required')
    expected=(intent//level)*level if tool=='hey' else intent
    return {'configured_intent':intent,'expected_scheduled':expected,'generator_not_scheduled':intent-expected}
