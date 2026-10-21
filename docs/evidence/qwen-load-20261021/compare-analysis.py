"""Post-run-only audit: retain execution source and compare every original record.

Never edits raw records, original per-run summaries, or the original open-rate plan.
"""
import argparse,hashlib,importlib.util,json,pathlib


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['old-source','new-source','raw','output','execution-sha','analysis-sha','matrix-source']:
        p.add_argument('--'+name,required=True)
    a=p.parse_args();old=module(a.old_source,'frozen_execution_measure');new=module(a.new_source,'postrun_measure')
    rates_module=module(a.matrix_source,'rate_reference');root=pathlib.Path(a.raw)
    changes=[];summary_changes=[];rows=[];total=0
    for runfile in sorted(root.glob('*/run.json')):
        run=json.loads(runfile.read_text());records=[json.loads(x) for x in (runfile.parent/'requests.jsonl').read_text().splitlines()]
        original=json.loads((runfile.parent/'summary.json').read_text())
        for r in records:
            if r.get('send') is None:continue
            total+=1;before=old.classify(r);after=new.classify(r)
            if before!=after:changes.append(dict(run=run['id'],id=r['id'],old=before,new=after))
        before=old.summarize(run,records);after=new.summarize(run,records)
        if before!=after or before!=original:
            summary_changes.append(dict(run=run['id'],original=original,old_recomputed=before,new_recomputed=after))
        rows.append(after)
    lock=json.loads((root/'open-rates-lock.json').read_text())
    count=max(s['window_success'] for s in rows if s['mode']=='closed' and s['valid'])
    rates=rates_module.derive_rates(count)
    equal_rates=(count==lock['max_window_completed_count'] and count/45==lock['reference_rb'] and rates==lock['rates'])
    receipt=dict(execution_sha=a.execution_sha,analysis_sha=a.analysis_sha,
        execution_source_sha256=hashlib.sha256(pathlib.Path(a.old_source).read_bytes()).hexdigest(),
        analysis_source_sha256=hashlib.sha256(pathlib.Path(a.new_source).read_bytes()).hexdigest(),
        runs=len(rows),actual_sent_records=total,classification_changes=changes,summary_changes=summary_changes,
        original_open_rate_lock=lock,new_reference_max_window_count=count,new_rates=rates,open_rate_plan_unchanged=equal_rates,
        all_actual_unchanged=not changes and not summary_changes and equal_rates)
    pathlib.Path(a.output).write_text(json.dumps(receipt,indent=2))
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['original_open_rate_lock','classification_changes','summary_changes']}))
    if not receipt['all_actual_unchanged']:raise SystemExit(2)
