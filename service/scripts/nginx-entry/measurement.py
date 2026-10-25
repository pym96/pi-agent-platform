"""Strict raw-receipt analysis; HTTP success cohort is separate from all attempts."""
import csv,json,math,datetime,re,hashlib
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

def _analyze_run(directory):
    """Internal statistics only; caller controls integrity verification stage."""
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

def _summarize_points(root):
    """Internal statistics; no standalone verified claim without external anchor."""
    p=Path(root);config=json.loads((p/'measurement-config.json').read_text());runs=[]
    for i in range(12):
        d=p/f'point-{i:02d}'
        if not d.is_dir():raise ValueError(f'missing point {i}')
        r=_analyze_run(d)
        if r['index']!=i:raise ValueError('duplicate/misplaced point identity')
        expected=config['points'][i]
        if r['source_sha']!=config['source_sha']:raise ValueError('source SHA mismatch')
        if any(r[k]!=expected[k] for k in ('tool','path','level','planned','configured_intent','expected_scheduled','generator_not_scheduled')):raise ValueError('matrix differs from frozen config')
        runs.append(r)
    if any(r.get('invalid') or r['missing'] for r in runs):raise ValueError('scheduled attempt receipts missing or invalid')
    return {'config':config,'runs':runs,'boundary':'CPU synthetic platform HTTP health only; no Qwen/model throughput; one repetition exploratory'}

def summarize_go(events):
    tests=[e for e in events if e.get('Test') and e.get('Action') in ['pass','skip','fail']]
    if not tests or any(e['Action']!='pass' for e in tests):raise ValueError('empty, failed or skipped required Go tests')
    if not any(e['Test']=='TestDurableAdmissionAndRecovery' for e in tests):raise ValueError('required real PostgreSQL test absent')
    return {'tests':len(tests),'skipped':0,'no_test_packages':[e['Package'] for e in events if e.get('Action')=='skip' and not e.get('Test')]}

def scheduled_budget(tool,intent,level):
    if intent<=0 or level<=0:raise ValueError('positive frozen parameters required')
    expected=(intent//level)*level if tool=='hey' else intent
    return {'configured_intent':intent,'expected_scheduled':expected,'generator_not_scheduled':intent-expected}

class IntegrityError(ValueError):
    pass

def verify_manifest(root,expected_manifest_sha256):
    p=Path(root).resolve()
    if not isinstance(expected_manifest_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',expected_manifest_sha256):
        raise IntegrityError('external expected SHA256 anchor is required')
    manifest_path=p/'manifest.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():raise IntegrityError('missing regular manifest')
    raw=manifest_path.read_bytes()
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected_manifest_sha256:raise IntegrityError('external manifest SHA256 mismatch')
    try:manifest=json.loads(raw)
    except (ValueError,UnicodeError) as e:raise IntegrityError('invalid trusted manifest') from e
    if not isinstance(manifest,dict) or not manifest:raise IntegrityError('empty or invalid trusted manifest')
    for name,digest in manifest.items():
        if not isinstance(name,str) or not isinstance(digest,str) or not re.fullmatch(r'[0-9a-f]{64}',digest):raise IntegrityError('invalid manifest entry')
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or name=='manifest.json':raise IntegrityError('unsafe manifest path')
        path=p/rel
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(p):raise IntegrityError('missing/unsafe receipt '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise IntegrityError('receipt SHA256 mismatch: '+name)
    actual_files=set()
    for path in p.rglob('*'):
        if path.is_symlink():raise IntegrityError('symlink in sealed receipt set')
        if path.is_file() and path!=manifest_path:actual_files.add(str(path.relative_to(p)))
    if actual_files!=set(manifest):raise IntegrityError('sealed file inventory differs from trusted manifest')
    return {'manifest_sha256':actual,'files_verified':len(manifest)}

def report(root,*,expected_manifest_sha256):
    """Authoritative offline entry: external anchor first, then original statistics.

    Does not alter sealed input files. Public callers cannot omit the trust anchor.
    """
    integrity=verify_manifest(root,expected_manifest_sha256)
    return dict(_summarize_points(root),integrity_verified=True,**integrity)

def summarize_live_unsealed(root):
    """Producer intermediate only: not authoritative and not sealed/verified."""
    if (Path(root)/'manifest.json').exists():raise ValueError('sealed inputs require externally anchored offline report')
    data=dict(_summarize_points(root),integrity_verified=False,integrity_stage='live_unsealed_not_authoritative')
    (Path(root)/'measurement-summary.json').write_text(json.dumps(data,indent=2)+'\n')
    return data['runs']

if __name__=='__main__':
    raise SystemExit('Use recompute.py with --expected-manifest-sha256 from the external Handoff/CI binding')
