"""Exact-ID Docker reconciliation shared by the live watchdog and its CPU CLI.
A missing inspect is success only after a successful full engine inventory proves absence.
"""
import argparse,json,re,subprocess,time
from pathlib import Path
class UnknownState(RuntimeError):pass
class OwnershipError(RuntimeError):pass

TRACE_PATH=None

def trace(value):
    if TRACE_PATH is not None:
        with Path(TRACE_PATH).open('a') as f:f.write(json.dumps(value)+'\n')

def execute(args,receipts):
    start=time.time_ns();trace({'event':'command_start','command':args,'started_ns':start})
    try:
        result=subprocess.run(args,capture_output=True,text=True,timeout=15)
    except (OSError,subprocess.TimeoutExpired) as error:
        row={'command':args,'started_ns':start,'ended_ns':time.time_ns(),'error':repr(error)}
        receipts.append(row);trace({'event':'command_end',**row})
        raise UnknownState(str(error)) from error
    row={'command':args,'started_ns':start,'ended_ns':time.time_ns(),'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    receipts.append(row);trace({'event':'command_end',**row})
    return result

def command(args,receipts):return execute(['docker',*args],receipts)

def ids(output):
    values=output.splitlines()
    if any(not re.fullmatch('[0-9a-f]{64}',value) for value in values):raise UnknownState('invalid full-ID inventory')
    return set(values)

def inventory(receipts):
    result=command(['ps','-a','-q','--no-trunc'],receipts)
    if result.returncode:raise UnknownState('engine inventory unavailable')
    return ids(result.stdout)

def inspect_exact(ident,project,sha,receipts):
    if not re.fullmatch('[0-9a-f]{64}',ident):raise OwnershipError('full exact ID required')
    result=command(['inspect',ident],receipts)
    if result.returncode:
        if ident not in inventory(receipts):return None
        raise UnknownState('inspect failed for an existing exact ID')
    try:
        rows=json.loads(result.stdout);row=rows[0]
        if len(rows)!=1 or row['Id']!=ident:raise OwnershipError('inspect identity mismatch')
        labels=row['Config']['Labels'] or {}
        if labels.get('com.docker.compose.project')!=project or labels.get('workorder')!='13' or labels.get('execution-sha')!=sha:raise OwnershipError('exact ID is not owned by this execution')
        if type(row['State']['Running']) is not bool:raise UnknownState('invalid running state')
    except (ValueError,KeyError,TypeError,IndexError,AttributeError) as error:raise UnknownState('unusable inspect') from error
    return row

def discover_owned(project,sha,known):
    receipts=[];result=command(['ps','-a','-q','--no-trunc','--filter','label=com.docker.compose.project='+project],receipts)
    if result.returncode:raise UnknownState('project inventory unavailable')
    rows=[]
    for ident in ids(result.stdout):
        row=inspect_exact(ident,project,sha,receipts)
        if row is not None:known[ident]=row;rows.append(row)
    return rows

def cleanup_known(project,sha,known_ids):
    receipts=[];states={};errors=[]
    for ident in known_ids:
        try:
            row=inspect_exact(ident,project,sha,receipts)
            if row is None:states[ident]='removed';continue
            if row['State']['Running']:
                stopped=command(['stop','--time','5',ident],receipts)
                # Even a failed stop can race with removal. Reconcile, never resolve a name.
                row=inspect_exact(ident,project,sha,receipts)
                if row is not None and (stopped.returncode or row['State']['Running']):raise UnknownState('exact ID did not settle after stop')
            states[ident]='removed' if row is None else 'stopped'
        except (UnknownState,OwnershipError) as error:
            states[ident]='unknown';errors.append({'id':ident,'error':str(error)})
    return {'success':not errors and all(x in ('removed','stopped') for x in states.values()),'containers':states,'errors':errors,'receipts':receipts}

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True,choices=['pi-qwen13-b','pi-qwen13-r']);p.add_argument('--sha',required=True);p.add_argument('--known-id',required=True,action='append');p.add_argument('--out',required=True);a=p.parse_args()
    if not re.fullmatch('[0-9a-f]{40}',a.sha):p.error('full source SHA required')
    out=Path(a.out)
    if out.exists():p.error('new receipt required')
    value=cleanup_known(a.project,a.sha,a.known_id);out.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value));return 0 if value['success'] else 1
if __name__=='__main__':raise SystemExit(main())
