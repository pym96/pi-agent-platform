"""Strict raw-receipt analysis; HTTP success cohort is separate from all attempts."""
import csv,json,math
from pathlib import Path

def summarize_rows(rows,planned):
    if planned<=0 or len(rows)>planned:raise ValueError('invalid attempt denominator')
    ok=[int(r['latency_ns']) for r in rows if 200<=int(r['code'])<300 and not r.get('error')]
    if any(x<0 for x in ok):raise ValueError('negative latency')
    ok.sort()
    q=lambda p:ok[math.ceil(p*len(ok))-1] if ok else None
    return {'planned':planned,'observed':len(rows),'missing':planned-len(rows),'success':len(ok),'error':planned-len(ok),'p50_ns':q(.5),'p95_ns':q(.95),'cohort':'observed HTTP 2xx, no transport error','quantile':'nearest-rank'}

def analyze_run(directory):
    p=Path(directory);meta=json.loads((p/'run.json').read_text())
    if meta['tool']=='hey':
        with (p/'raw.csv').open() as f:
            data=list(csv.DictReader(f))
        rows=[{'code':int(r['status-code']),'latency_ns':round(float(r['response-time'])*1e9),'offset_s':float(r['offset'])} for r in data]
        end=max((r['offset_s']+r['latency_ns']/1e9 for r in rows),default=0)
        start=min((r['offset_s'] for r in rows),default=0)
    else:
        data=[json.loads(x) for x in (p/'decoded.jsonl').read_text().splitlines() if x.strip()]
        rows=[{'code':int(r['code']),'latency_ns':int(r['latency']),'error':r.get('error','')} for r in data]
        # Go timestamps may carry nanoseconds: preserve raw; wall envelope is separately recorded.
        start=0;end=meta['elapsed_s']
    result=summarize_rows(rows,meta['planned']);result.update(meta)
    result['completion_window_s']=max(0,end-start)
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
        if any(r[k]!=expected[k] for k in ('tool','path','level','planned')):raise ValueError('matrix differs from frozen config')
        runs.append(r)
    (p/'measurement-summary.json').write_text(json.dumps({'config':config,'runs':runs,'boundary':'CPU synthetic platform HTTP health only; no Qwen/model throughput; one repetition exploratory'},indent=2))
    return runs
