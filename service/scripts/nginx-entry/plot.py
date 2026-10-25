"""Optional standalone report artifact; requires matplotlib, never used by HTTP service."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('summary');p.add_argument('out');a=p.parse_args()
data=json.loads(Path(a.summary).read_text());runs=data['runs'];fig,axes=plt.subplots(2,2,figsize=(10,7))
for col,tool in enumerate(['hey','vegeta']):
    for path,color in [('direct','#2878b5'),('proxy','#d45b32')]:
        points=sorted((r for r in runs if r['tool']==tool and r['path']==path),key=lambda r:r['level'])
        axes[0,col].plot([r['level'] for r in points],[r['observed_completion_rps'] for r in points],marker='o',label=path,color=color)
        axes[1,col].plot([r['level'] for r in points],[r['p95_ns']/1e6 if r['p95_ns'] is not None else float('nan') for r in points],marker='o',label=path,color=color)
    axes[0,col].set_title('hey fixed concurrency' if tool=='hey' else 'Vegeta fixed arrival rate')
    for row in range(2):
        axes[row,col].set_xlabel('Concurrent workers' if tool=='hey' else 'Offered requests / second');axes[row,col].grid(alpha=.25);axes[row,col].legend()
axes[0,0].set_ylabel('Observed completion requests / second');axes[1,0].set_ylabel('Successful HTTP P95 (ms, nearest rank)')
fig.suptitle('CPU synthetic platform /health: one exploratory repetition\nSame-host generator; not model TTFT or Qwen throughput',fontsize=11)
fig.tight_layout(rect=[0,0,1,.93]);fig.savefig(a.out)
