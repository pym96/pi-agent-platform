"""Independent foreground child watchdog, acts only on its exact recorded CID."""
import argparse,json,pathlib,subprocess,time,sys
p=argparse.ArgumentParser();p.add_argument('--cid',required=True);p.add_argument('--nonce',required=True);p.add_argument('--deadline',type=float,required=True);p.add_argument('--stop-file',required=True);p.add_argument('--out',required=True);p.add_argument('--ready',required=True);a=p.parse_args()
def cmd(args):return subprocess.run(args,capture_output=True,text=True,timeout=8)
def record(v):
 with open(a.out,'a') as f:f.write(json.dumps({'epoch':time.time(),**v})+'\n')
initial=cmd(['docker','inspect',a.cid]);record({'event':'initial-inspect','exit':initial.returncode,'stdout':initial.stdout,'stderr':initial.stderr})
if initial.returncode:sys.exit(2)
v=json.loads(initial.stdout)[0]
if v['Id']!=a.cid or v['Config']['Labels'].get('pi21.nonce')!=a.nonce:sys.exit(3)
pathlib.Path(a.ready).write_text(str(time.time()))
while not pathlib.Path(a.stop_file).exists() and time.time()<a.deadline:time.sleep(min(.2,max(.001,a.deadline-time.time())))
r=cmd(['docker','inspect',a.cid]);record({'event':'inspect','exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
if r.returncode:sys.exit(2)
v=json.loads(r.stdout)[0]
if v['Id']!=a.cid or v['Config']['Labels'].get('pi21.nonce')!=a.nonce:record({'event':'ownership_unknown'});sys.exit(3)
for op,args in [('stop',['docker','stop','--time','2',a.cid]),('rm',['docker','rm','-f',a.cid])]:
 r=cmd(args);record({'event':op,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 if r.returncode:sys.exit(4)
record({'event':'owned_cleanup_complete'})
