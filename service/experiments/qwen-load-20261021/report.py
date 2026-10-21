"""Recompute all summaries directly from raw request/SSE records and plot all reps."""
import argparse,csv,json,pathlib
from measure import summarize,classify


def main():
    p=argparse.ArgumentParser();p.add_argument('raw');p.add_argument('output');p.add_argument('--title',required=True)
    a=p.parse_args();raw=pathlib.Path(a.raw);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True)
    summaries=[];request_rows=[]
    for runfile in sorted(raw.glob('*/run.json')):
        run=json.loads(runfile.read_text());records=[json.loads(x) for x in (runfile.parent/'requests.jsonl').read_text().splitlines()]
        summaries.append(summarize(run,records))
        for r in records:
            c=classify(r) if r.get('send') is not None else {}
            usage=c.get('usage') if isinstance(c.get('usage'),dict) else {}
            row={k:r.get(k) for k in ['id','planned','send','done','http_status','error','drop','prompt_index']}
            row.update(run=run['id'],success=c.get('success',False),first=c.get('first'),ttft_s=c.get('ttft_s'),
                       e2e_s=c.get('e2e_s'),finish_reason=c.get('finish_reason'),valid_usage=c.get('valid_usage'),
                       semantic_error=c.get('error'),
                       prompt_tokens=usage.get('prompt_tokens'),output_tokens=usage.get('completion_tokens'))
            request_rows.append(row)
    (out/'summary.json').write_text(json.dumps(summaries,indent=2))
    flat=[]
    for s in summaries:
        row={k:(json.dumps(v,sort_keys=True) if isinstance(v,dict) else v) for k,v in s.items() if k!='latency'}
        for metric,vals in s['latency'].items():
            for stat,value in vals.items():row[f'{metric}_{stat}']=value
        flat.append(row)
    if flat:
        with (out/'summary.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    if request_rows:
        with (out/'requests.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(request_rows[0]));w.writeheader();w.writerows(request_rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for mode in ['closed','open']:
        items=[s for s in summaries if s['mode']==mode and s['valid']]
        if not items:continue
        fig,axes=plt.subplots(3,2,figsize=(14,13),layout='constrained')
        for rep in [1,2]:
            ss=sorted([s for s in items if s['rep']==rep],key=lambda s:s['load']);xx=[s['load'] for s in ss]
            for ax,key,label in [(axes[0,0],'window_req_s','Complete requests/s'),(axes[0,1],'window_tokens_s','Actual output tokens/s')]:
                ax.plot(xx,[s[key] for s in ss],'o-',label=f'rep {rep}');ax.set_ylabel(label)
            for ax,metric in [(axes[1,0],'ttft_s'),(axes[1,1],'e2e_s')]:
                for stat,style in [('p50','o-'),('p95','s--')]:
                    ax.plot(xx,[s['latency'][metric][stat] for s in ss],style,label=f'rep {rep} {stat.upper()}')
                ax.set_ylabel('TTFT (s), all valid first content\nincluding later failures' if metric=='ttft_s'
                              else 'E2E (s), complete success only')
            for key,style in [('failures','o-'),('timeout','s--'),('generator_admission_drop','x:')]:
                axes[2,0].plot(xx,[s[key] for s in ss],style,label=f'rep {rep} {key}')
            axes[2,0].set_ylabel('Request counts')
            for key,style in [('actual_send_rate','o-'),('window_req_s','s--')]:
                axes[2,1].plot(xx,[s[key] for s in ss],style,label=f'rep {rep} {key}')
            axes[2,1].set_ylabel('Requests/s')
        for ax in axes.flat:
            ax.set_xlabel('Closed-loop client concurrency' if mode=='closed' else 'Open-loop offered requests/s')
            ax.grid(alpha=.3);ax.legend(fontsize=8)
        fig.suptitle(a.title+'\n45 s launch window; completions in window for throughput; <=60 s drain; max output128\nAll repetitions; failures retained. Tail sample counts and P99 in CSV.',fontsize=12)
        fig.savefig(out/f'{mode}-curves.png',dpi=150);fig.savefig(out/f'{mode}-curves.svg');plt.close(fig)
    print(json.dumps({'runs':len(summaries),'valid':sum(s['valid'] for s in summaries)}))


if __name__=='__main__':main()
