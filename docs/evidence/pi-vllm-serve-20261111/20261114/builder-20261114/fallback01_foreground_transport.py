"""Frozen one-shot foreground transport. Only Master GO path/hash are runtime inputs."""
import argparse,hashlib,json,pathlib,subprocess,shlex,time,selectors,os,base64
STATE=pathlib.Path(__file__).resolve().parent
ROOT='/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder'
REMOTE_GO=ROOT+'/B-GPU-FALLBACK-NOV14-GO01.json'
SOURCE='9ea36d3221d024a6d8330322d330809fa9e283a6'
NONCE='pi24-b-nov14-fallback01'
PATH=ROOT+'/nvml-normal02-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
SSH=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=58.199.168.63','-o','ConnectTimeout=10','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','wt@58.199.171.85']
PREFIX='cd /media/usv012/pjx && export CUDA_VISIBLE_DEVICES=0 && cd '+ROOT+' && exec taskset -c 0,1 python3 -c '
STAGE="""import pathlib,sys,hashlib,json,time
p=pathlib.Path(sys.argv[1]);data=sys.stdin.buffer.read();h=hashlib.sha256(data).hexdigest()
assert h==sys.argv[2] and not p.exists() and not p.is_symlink()
with p.open('xb') as f:f.write(data)
print(json.dumps({'event':'GO_staged','epoch':time.time(),'path':str(p),'sha256':h}),flush=True)
"""
LAUNCH="""import pathlib,sys,hashlib,os,json,time
root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder')
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
assert sha(sys.argv[1])==sys.argv[2]
assert sha(root/'nvml-normal02-bin/nvidia-smi')=='917f97350b53c3b2ddcbd0f105900b32a6b786434ce7ca3c971a8a43c6d2dc4e'
assert sha('/usr/bin/nvidia-smi')=='2da08a20450594c3cdf1e677c1d2e46101a0b2d45ee5d3d6b67b87ae50522af2'
os.environ['PATH']='/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/nvml-normal02-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
print(json.dumps({'event':'foreground_outer_exec','pid':os.getpid(),'epoch':time.time(),'go_sha256':sys.argv[2],'PATH':os.environ['PATH']}),flush=True)
os.execv('/bin/sh',['sh',str(root/'entry_nov14_r3.sh'),'--go',sys.argv[1],'--go-sha256',sys.argv[2]])
"""
def command(code,digest):return [*SSH,PREFIX+shlex.quote(code)+' '+shlex.quote(REMOTE_GO)+' '+shlex.quote(digest)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True);a=p.parse_args()
 data=pathlib.Path(a.go).read_bytes();assert hashlib.sha256(data).hexdigest()==a.go_sha256
 g=json.loads(data);assert g['issue']==24 and g['role']=='builder' and g['nonce']==NONCE and g['source_sha']==SOURCE
 assert g['network_id']=='cf97a390694df09401f1b2eeee04f7451fbb3d0c7c2e6b65e07ac63df00000c4' and g['phase_contract_sha256']=='82f15dcf6523c8bbea36bd79741fc8c9745fd838024004ad592979ad2b6830ec'
 deadline=g['deadline_epoch'];assert time.time()<deadline-30
 marker=STATE/'fallback01-transport-once-consumed';marker.touch(exist_ok=False)
 started=time.time();stage=subprocess.run(command(STAGE,a.go_sha256),input=data,capture_output=True,timeout=min(20,max(1,deadline-time.time())))
 (STATE/'FALLBACK01-GO-STAGE-TRANSPORT.json').write_text(json.dumps({'start':started,'end':time.time(),'command':command(STAGE,a.go_sha256),'exit':stage.returncode,'stdout_base64':base64.b64encode(stage.stdout).decode(),'stderr_base64':base64.b64encode(stage.stderr).decode()},indent=2)+'\n')
 if stage.returncode:raise RuntimeError('GO stage failed; no automatic retry')
 os.write(1,stage.stdout);os.write(2,stage.stderr)
 cmd=command(LAUNCH,a.go_sha256);proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
 start=time.time();sel=selectors.DefaultSelector();sel.register(proc.stdout,selectors.EVENT_READ,'stdout');sel.register(proc.stderr,selectors.EVENT_READ,'stderr');unknown=None
 with (STATE/'FALLBACK01-FOREGROUND-RAW.jsonl').open('x') as raw:
  while sel.get_map():
   remain=deadline-time.time()
   if remain<=0:unknown='transport absolute deadline; remote source hard-stop remains independently required';proc.kill();proc.wait(timeout=2);break
   for key,_ in sel.select(min(.5,remain)):
    chunk=os.read(key.fileobj.fileno(),65536)
    if not chunk:sel.unregister(key.fileobj);continue
    raw.write(json.dumps({'epoch':time.time(),'stream':key.data,'base64':base64.b64encode(chunk).decode()})+'\n');raw.flush();os.write(1 if key.data=='stdout' else 2,chunk)
 code=proc.wait(timeout=2);report={'command':cmd,'GO_sha256':a.go_sha256,'start':start,'end':time.time(),'exit':code,'unknown':unknown,'all_foreground_SSH_ended':True,'no_retry':True}
 (STATE/'FALLBACK01-FOREGROUND-TRANSPORT-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 return code if code>=0 else 3
if __name__=='__main__':raise SystemExit(main())
