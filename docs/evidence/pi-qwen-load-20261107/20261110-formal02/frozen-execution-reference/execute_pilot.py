import subprocess,time,json,sys,os,hashlib
from pathlib import Path
state=Path(__file__).resolve().parent;go_path=Path(sys.argv[1]);go=json.loads(go_path.read_text());root='/media/usv012/pjx/pi-agent-platform/experiments/13-qwen-load-20261107/builder';key=Path(go['out']).name;ssh=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','ConnectTimeout=10','wt@58.199.171.85'];prefix='cd '+root+' && export CUDA_VISIBLE_DEVICES=0 && '
assert time.time()<go['deadline_epoch']-200,'insufficient fresh startup window; no watch/model'
remote_go=root+'/'+key+'-go.json';r=subprocess.run(ssh+[prefix+'cat > '+remote_go],input=go_path.read_bytes(),capture_output=True,timeout=20);assert r.returncode==0,r.stderr
watch_command=prefix+'python3 source/service/scripts/pi-qwen-load/watch.py --project '+go['project']+' --sha '+go['source_sha']+' --deadline '+str(go['deadline_epoch'])+' --root '+root+' --out '+go['watch_receipt'];wf=(state/(key+'-watch-ssh.stdout')).open('w');we=(state/(key+'-watch-ssh.stderr')).open('w');watch=subprocess.Popen(ssh+[watch_command],stdout=wf,stderr=we);print(json.dumps({'watch_ssh_pid':watch.pid,'start_epoch':time.time(),'go_sha256':hashlib.sha256(go_path.read_bytes()).hexdigest()}),flush=True)
try:
 time.sleep(2)
 proof="import sys,json;from pathlib import Path;sys.path.insert(0,'"+root+"/source/service/scripts/pi-qwen-load');from watch_monitor import verify_watch;g=json.loads(Path('"+remote_go+"').read_text());print(json.dumps(verify_watch(g)))"
 check=subprocess.run(ssh+[prefix+"python3 -c "+__import__('shlex').quote(proof)],capture_output=True,text=True,timeout=20);(state/(key+'-watch-proof.json')).write_text(json.dumps({'exit':check.returncode,'stdout':check.stdout,'stderr':check.stderr},indent=2));assert check.returncode==0,check.stderr
 s=time.time();p=subprocess.Popen(ssh+[prefix+'python3 source/service/scripts/pi-qwen-load/launch.py --go '+remote_go],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 out,err=p.communicate(timeout=max(1,go['deadline_epoch']-time.time()+45));(state/(key+'-launch.json')).write_text(json.dumps({'command':p.args,'start_epoch':s,'end_epoch':time.time(),'exit':p.returncode,'stdout':out,'stderr':err},indent=2));print(json.dumps({'launch_exit':p.returncode,'start_epoch':s,'end_epoch':time.time(),'stdout':out,'stderr':err}),flush=True)
finally:
 try:watch.wait(timeout=20)
 except subprocess.TimeoutExpired:
  stop="import json,os,signal;from pathlib import Path;g=json.loads(Path('"+remote_go+"').read_text());r=[json.loads(x) for x in Path(g['watch_receipt']).read_text().splitlines() if json.loads(x).get('event')=='heartbeat'][-1];p=r['watch_pid'];assert r['project']==g['project'] and r['source_sha']==g['source_sha'];assert Path('/proc/'+str(p)+'/stat').read_text().split()[21]==r['watch_start_ticks'];a=Path('/proc/'+str(p)+'/cmdline').read_bytes();assert b'watch.py' in a and g['source_sha'].encode() in a;os.kill(p,signal.SIGTERM)"
  q=subprocess.run(ssh+[prefix+"python3 -c "+__import__('shlex').quote(stop)],capture_output=True,text=True,timeout=20);(state/(key+'-watch-stop.json')).write_text(json.dumps({'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr}));watch.wait(timeout=20)
 wf.close();we.close();print(json.dumps({'watch_exit':watch.returncode,'ended_epoch':time.time()}),flush=True)
