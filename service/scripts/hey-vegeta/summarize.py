#!/usr/bin/env python3
"""Verify per-run artifacts and recompute nearest-rank measurements. Never fill missing samples."""
import argparse, collections, csv, datetime, hashlib, io, json, math, pathlib, re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quantiles(xs):
    xs=sorted(xs)
    return {f'p{int(q*100)}Ms':xs[math.ceil(q*len(xs))-1] if xs else None for q in [.5,.95,.99]}
def resources(root,rid):
    data=[json.loads((root/(rid+'.'+side+'.resources.json')).read_text()) for side in ['before','after']]
    elapsed=(datetime.datetime.fromisoformat(data[1]['utc'])-datetime.datetime.fromisoformat(data[0]['utc'])).total_seconds()
    ticks=json.loads((root/'host-system.json').read_text())['clockTicks'] if (root/'host-system.json').exists() else None
    output={'sampleIntervalSeconds':elapsed,'apiGoroutines':[d.get('api',{}).get('goroutines') for d in data],'apiHeapBytes':[d.get('api',{}).get('heapBytes') for d in data],'processes':{}}
    for name in data[0]['process']:
        samples=[]
        for d in data:
            raw=d['process'][name]['stdout'];stat=None
            for line in raw.splitlines():
                if line.startswith('1 ('):
                    rest=line.split(') ',1)[1].split();stat=int(rest[11])+int(rest[12])
            rss=re.search(r'^VmRSS:\s+(\d+)',raw,re.M);fd=re.search(r'^fds=(\d+)',raw,re.M)
            samples.append({'rssKiB':int(rss[1]) if rss else None,'fds':int(fd[1]) if fd else None,'cpuTicks':stat})
        before,after=samples
        cpu=(after['cpuTicks']-before['cpuTicks'])/ticks/elapsed*100 if ticks and elapsed>0 and before['cpuTicks'] is not None and after['cpuTicks'] is not None else None
        output['processes'][name]={'before':before,'after':after,'pid1CpuPercentOverInterval':cpu}
    return output
def summarize(root, require_matrix=True):
    root=pathlib.Path(root)
    runs=[json.loads(x) for x in (root/'runs.jsonl').read_text().splitlines() if x]
    seen=set(); primary=set(); result=[]; artifacts=set()
    for r in runs:
        rid=r['id']
        if rid in seen:raise ValueError('duplicate run identity: '+rid)
        seen.add(rid)
        for name,expected in r['artifacts'].items():
            if pathlib.Path(name).name != name:raise ValueError('nonlocal artifact')
            if name in artifacts:raise ValueError('reused artifact: '+name)
            artifacts.add(name)
            if not (root/name).is_file() or sha(root/name)!=expected:raise ValueError('missing or hash-mismatched artifact: '+name)
        rawname=rid+('.csv' if r['tool']=='hey' else '.bin')
        if rawname not in r['artifacts']:raise ValueError('unbound primary raw')
        if r['artifacts'][rawname] in primary:raise ValueError('duplicated primary raw bytes')
        primary.add(r['artifacts'][rawname])
        errors=[]
        if r['tool']=='hey':
            rows=list(csv.DictReader(io.StringIO((root/rawname).read_text())))
            codes=[int(x['status-code']) for x in rows]
            lat=[float(x['response-time'])*1000 for x in rows]
            duration=max((float(x['offset'])+float(x['response-time']) for x in rows),default=0)
            actual_send_rate=None # CSV suppresses transport-error rows; no invented send timestamps.
            native=None
        elif r['tool']=='vegeta':
            rows=[json.loads(x) for x in (root/(rid+'.results.jsonl')).read_text().splitlines() if x]
            seq=[x['seq'] for x in rows]
            if len(seq)!=len(set(seq)):raise ValueError('duplicate Vegeta request sequence')
            codes=[int(x['code']) for x in rows]
            lat=[x['latency']/1e6 for x in rows]
            errors=[x['error'] for x in rows if x.get('error')]
            native=json.loads((root/(rid+'.report.json')).read_text())
            if native['requests']!=len(rows):raise ValueError('native/raw request denominator differs')
            duration=(native['duration']+native['wait'])/1e9
            actual_send_rate=native['rate']
        else:raise ValueError('unknown tool')
        if len(rows)>r['expected']:raise ValueError('extra/duplicate request rows')
        missing=r['expected']-len(rows)
        successful=sum(200<=c<300 for c in codes)
        failures=len(rows)-successful+missing
        if any(not math.isfinite(x) or x<0 for x in lat):raise ValueError('invalid latency')
        result.append({**{k:r[k] for k in ['id','tool','cache','endpoint','load','rep','expected','exitCode','sourceSHA','started','ended','wallSeconds']},'observed':len(rows),'successful':successful,'failedOrUnobserved':failures,'unobserved':missing,'statusCounts':dict(collections.Counter(codes)),'transportErrors':dict(collections.Counter(errors)),'normalSuccess':r['exitCode']==0 and failures==0,'latencyDenominator':len(lat),'durationSeconds':duration,'observedCompletionRate':len(rows)/duration if duration else 0,'successfulThroughput':successful/duration if duration else 0,'offeredRate':r['load'] if r['tool']=='vegeta' else None,'actualSendRate':actual_send_rate,**quantiles(lat),'nativeReport':native,'resources':resources(root,rid)})
    if require_matrix:
        expected={('hey',c,e,l,r) for c in [0,1] for e in ['health','history'] for l in [1,10,100] for r in [1,2,3]}|{('vegeta',c,'history',l,r) for c in [0,1] for l in [10,100,500] for r in [1,2,3]}
        keys=[(r['tool'],r['cache'],r['endpoint'],r['load'],r['rep']) for r in runs]
        if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('matrix missing/extra/duplicate cells')
    pairs=[]
    bykey={(r['tool'],r['cache'],r['endpoint'],r['load'],r['rep']):r for r in result}
    for r in result:
        if r['cache']!=0:continue
        other=bykey.get((r['tool'],1,r['endpoint'],r['load'],r['rep']))
        if other:pairs.append({'baseline':r['id'],'cache1':other['id'],'p95DeltaMs':other['p95Ms']-r['p95Ms'] if other['p95Ms'] is not None and r['p95Ms'] is not None else None,'throughputDelta':other['successfulThroughput']-r['successfulThroughput']})
    return {'quantileAlgorithm':'ascending observed per-request latency; nearest rank ceil(p*n), milliseconds','heyPrecision':'upstream CSV rounds seconds to four decimal places; transport-error rows omitted; unobserved expected requests counted as failedOrUnobserved','throughputAlgorithm':'hey observed count / max(offset+response-time); Vegeta completed count / (native duration+wait); docker invocation wall time separate','resourceAlgorithm':'before/after process1 CPU ticks divided by SC_CLK_TCK and snapshot UTC interval; includes sampling overhead; PG PID1 excludes backend processes, whole-container CPU remains raw Docker stats; RSS/FD/goroutines are snapshots, not peaks','matrixRequired':require_matrix,'runCount':len(result),'expectedRequests':sum(r['expected'] for r in result),'observedRequests':sum(r['observed'] for r in result),'successfulRequests':sum(r['successful'] for r in result),'runs':result,'cachePairs':pairs}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('--allow-partial',action='store_true');args=p.parse_args()
    try:print(json.dumps(summarize(args.root,not args.allow_partial),indent=2))
    except (ValueError,KeyError,OSError,TypeError) as e:raise SystemExit('INVALID EVIDENCE: '+str(e))
