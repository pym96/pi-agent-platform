"""Standalone standard-matplotlib SVG export; no HTTP or model dependency.

The existing macOS system Python3.9/matplotlib installation can run this separately
from the Python3.10+ receipt reconstructor. Set a new task-owned MPLCONFIGDIR.
"""
import argparse,csv,json
from pathlib import Path

def resources(stage_root):
    rows=[]
    for file in sorted(Path(stage_root).glob('*/watch.jsonl')):
        first=None;latest=None
        for line in file.read_text().splitlines():
            row=json.loads(line)
            if first is None:first=row['epoch']
            if row['event']=='query' and '--query-gpu=uuid,memory.used,utilization.gpu' in row['argv']:
                values=[s.strip() for s in row['stdout'].split(',')]
                latest={'block':file.parent.name,'watch_elapsed_s':row['epoch']-first,'query_start_epoch':row['start'],'query_end_epoch':row['end'],
                        'GPU_memory_MiB':None,'GPU_util_percent':None,'host_RSS_bytes':None,'model_RSS_KiB':None,'host_ps_CPU_percent':None,
                        'status':'unknown' if row['exit'] else 'observed'}
                if row['exit']==0:
                    try:latest.update(GPU_memory_MiB=float(values[1]),GPU_util_percent=float(values[2]))
                    except (ValueError,IndexError):latest['status']='unknown'
                rows.append(latest)
            elif row['event']=='sample' and latest is not None:
                latest['host_RSS_bytes']=row['host_descendant_RSS_bytes']
                latest['model_RSS_KiB']=sum(float(p[3]) for p in row['owned_model_processes'])
                process_rows=[x.split() for x in row['host_processes'].splitlines()[1:]]
                latest['host_ps_CPU_percent']=sum(float(p[2]) for p in process_rows if int(p[0]) in row['host_descendants'])
            elif row['event'] in ('query_failed','watch_error'):
                rows.append({'block':file.parent.name,'watch_elapsed_s':row['epoch']-first,'query_start_epoch':None,'query_end_epoch':None,
                             'GPU_memory_MiB':None,'GPU_util_percent':None,'host_RSS_bytes':None,'model_RSS_KiB':None,'host_ps_CPU_percent':None,'status':'unknown'})
    return rows

def plots(rows,out,stage_root=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=Path(out)
    for metric,label in [('requests_per_s','Completed requests/s (includes drain)'),('output_tokens_per_s','Actual completed output tokens/s (includes drain)'),('completion_p95_ns','Success completion P95 (ns); n <=20, exploratory')]:
        fig,ax=plt.subplots(figsize=(11,4))
        for block in dict.fromkeys(r['block'] for r in rows):
            selected=[r for r in rows if r['block']==block]
            ax.plot([r['point'] for r in selected],[r[metric] for r in selected],marker='o',label=block)
        ax.set_ylabel(label);ax.set_xlabel('Frozen point; each line is one independent block/repeat');ax.legend();fig.tight_layout();fig.savefig(out/(metric+'.svg'));plt.close(fig)
    fig,ax=plt.subplots(figsize=(13,5));bottom=[0]*len(rows)
    for kind in ['completed','rejected','failed','timeout','unresolved','generator_drop']:
        values=[r[kind] for r in rows];ax.bar(range(len(rows)),values,bottom=bottom,label=kind);bottom=[a+b for a,b in zip(bottom,values)]
    ax.set_xticks(range(len(rows)));ax.set_xticklabels([r['block']+'/'+r['point'] for r in rows],rotation=75,fontsize=7)
    ax.set_ylabel('All frozen planned slots (20/point); latency uses completed subset only');ax.legend();fig.tight_layout();fig.savefig(out/'denominators.svg');plt.close(fig)
    if stage_root:
        samples=resources(stage_root)
        if not samples:raise ValueError('no actual resource receipts; cannot create resource curve')
        with (out/'resources.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
        for block in dict.fromkeys(r['block'] for r in samples):
            selected=[r for r in samples if r['block']==block];fig,axes=plt.subplots(4,1,figsize=(10,9),sharex=True)
            for axis,(metric,label) in zip(axes,[('GPU_memory_MiB','GPU0 memory (MiB)'),('GPU_util_percent','GPU0 utilization (%)'),('host_RSS_bytes','Owned host descendants RSS (bytes)'),('host_ps_CPU_percent','Owned host ps %CPU (lifetime average)')]):
                axis.plot([r['watch_elapsed_s'] for r in selected],[r[metric] for r in selected],marker='.',label=block);axis.set_ylabel(label);axis.legend()
            axes[-1].set_xlabel('Seconds since first query in this watchdog clock; missing/failed samples are gaps')
            fig.tight_layout();fig.savefig(out/('resources-'+block+'.svg'));plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--recomputed',required=True);p.add_argument('--out',required=True);p.add_argument('--stage-root',required=True);a=p.parse_args()
    value=json.loads(Path(a.recomputed).read_text());out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    rows=[{'block':point['block'],'point':point['point']['name'],**point['summary']} for point in value['points']]
    plots(rows,out,a.stage_root)
    from hashlib import sha256
    manifest=[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha256(f.read_bytes()).hexdigest()} for f in sorted(out.iterdir()) if f.is_file()]
    (out/'manifest.json').write_text(json.dumps({'plot_python':__import__('sys').version,'files':manifest},indent=2)+'\n')
    return 0

if __name__=='__main__':raise SystemExit(main())
