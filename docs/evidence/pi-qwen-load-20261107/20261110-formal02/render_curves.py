"""Offline figure from sealed results; no requests or runtime configuration changes."""
from pathlib import Path
import hashlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
rows=json.loads((D/'results.json').read_text())
fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
for ri,mode in enumerate(['closed','open']):
 for path,color in [('platform','#b83d42'),('direct','#2169a6')]:
  points=[r for r in rows if r['mode']==mode and r['path']==path]
  xs=list(range(len(points)))
  labels=[str(r['concurrency']) if mode=='closed' else f"{r['rate']:.3f}" for r in points]
  for ci,key in enumerate(['p95_complete_s','cohort_complete_rps','success_rate_planned']):
   ys=[r[key]*(100 if ci==2 else 1) for r in points]
   axes[ri,ci].plot(xs,ys,'o-',color=color,label=path)
   axes[ri,ci].set_xticks(xs,labels)
   axes[ri,ci].grid(alpha=.2)
   axes[ri,ci].set_xlabel('Closed-loop concurrency' if mode=='closed' else 'Configured offered requests/s')
   if ci==0:
    for x,y,r in zip(xs,ys,points):axes[ri,ci].annotate(f"{r['complete']}/20",(x,y),xytext=(2,7 if path=='platform' else -14),textcoords='offset points',color=color,fontsize=8)
  axes[ri,2].set_ylim(0,110)
 for ci,title in enumerate(['Successful-request completion P95 (s)','Completed requests / cohort elapsed (req/s)','Successful / all 20 planned slots (%)']):axes[ri,ci].set_title(title,fontsize=10)
 axes[ri,0].legend()
 for ci in [0,1]:
  ymax=max(max(line.get_ydata()) for line in axes[ri,ci].lines)
  axes[ri,ci].set_ylim(0,ymax*1.18)
fig.suptitle('Formal02: paired platform → direct, 20 slots per point, one run\nNearest-rank P95 among successes; labels show successful n/20; cold first request retained',fontsize=12)
fig.savefig(D/'curves-with-denominators.svg');fig.savefig(D/'curves-with-denominators.png',dpi=130)
(D/'plot-provenance.json').write_text(json.dumps({'input':'results.json','input_sha256':hashlib.sha256((D/'results.json').read_bytes()).hexdigest(),'points':12,'slots_each':20,'warning':'No independent repeats; fixed order. P95 conditional on success. Rejections and failures remain in success-rate denominator.'},indent=2)+'\n')

svg=D/'curves-with-denominators.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
