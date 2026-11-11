"""Opt-in issue21 launcher. Invalid GO exits before invoking Docker or CUDA tools."""
import argparse,hashlib,json,pathlib,sys,time,subprocess,os,math
UUID='GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead'
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def validate(path,digest,now=None):
 if sha(path)!=digest:raise ValueError('GO hash mismatch')
 g=json.loads(pathlib.Path(path).read_text());now=time.time() if now is None else now
 if g['issue']!=21 or g['role'] not in ['builder','regulator'] or g['gpu_uuid']!=UUID:raise ValueError('GO identity mismatch')
 cap=300 if g['role']=='builder' else 180
 latest=1794418271 if g['role']=='builder' else 1794418871
 if now>latest:raise ValueError('last new GPU start elapsed')
 if g['deadline_epoch']>1794419471 or not 0<g['deadline_epoch']-now<=g['max_duration_s']<=cap:raise ValueError('GO expired or over budget')
 if g['model_revision']!='b968826d9c46dd6066d109eabc6255188de91218':raise ValueError('model mismatch')
 for k in ['source_sha','probe_sha256','runtime_manifest_sha256','launcher_sha256','watch_sha256','model_manifest_sha256']:
  if len(g[k])!=(40 if k=='source_sha' else 64) or any(c not in '0123456789abcdef' for c in g[k]):raise ValueError('bad '+k)
 if g['launcher_sha256']!=sha(__file__):raise ValueError('launcher hash mismatch')
 if not g['nonce'] or '/' in g['nonce']:raise ValueError('nonce mismatch')
 return g
def execute(g,go_path,go_digest):
 root=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111')/g['role']
 if pathlib.Path.cwd().resolve()!=root:raise ValueError('wrong role root')
 source=root/'source';manifest=root/'runtime-manifest.json';probe=source/'service/scripts/vllm-compat/smoke.py'
 if sha(manifest)!=g['runtime_manifest_sha256'] or sha(probe)!=g['probe_sha256']:raise ValueError('runtime/probe mismatch')
 if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=g['source_sha'] or subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():raise ValueError('source mismatch or dirty')
 if sha(pathlib.Path(__file__).with_name('watch.py'))!=g['watch_sha256']:raise ValueError('watch mismatch')
 files=json.loads(manifest.read_text())['files']
 if not files:raise ValueError('empty runtime manifest')
 expected={str(f.relative_to(root)) for f in (root/'env').rglob('*') if f.is_file() and not f.is_symlink()}
 if {r['path'] for r in files}!=expected or len(files)!=len(expected):raise ValueError('runtime manifest incomplete')
 for row in files:
  f=(root/row['path']).resolve()
  if not f.is_relative_to((root/'env').resolve()) or sha(f)!=row['sha256']:raise ValueError('installed runtime mismatch')
 model=pathlib.Path(g['model_path']).resolve()
 if model!=pathlib.Path('/media/usv012/pjx/agent/Qwen3-8B') or not model.is_dir():raise ValueError('model snapshot mismatch')
 model_manifest=source/'docs/evidence/qwen-load-20261021/model-files.json'
 if sha(model_manifest)!=g['model_manifest_sha256']:raise ValueError('model manifest mismatch')
 model_files=json.loads(model_manifest.read_text())
 if not any(r['path'].endswith('.safetensors') for r in model_files):raise ValueError('model manifest missing weights')
 for row in model_files:
  name=row['path']
  if name.startswith('.cache/') or name.startswith('._'):continue
  f=(model/name).resolve()
  if not f.is_relative_to(model) or f.stat().st_size!=row['bytes'] or sha(f)!=row['sha256']:raise ValueError('model bytes mismatch')
 if g['image']!='sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229' or subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',g['image']],text=True).strip()!=g['image']:raise ValueError('cached image mismatch')
 project='pi-vllm21-n11-'+('b' if g['role']=='builder' else 'r')
 if subprocess.check_output(['docker','ps','-aq','--filter','label=com.docker.compose.project='+project],text=True).strip():raise ValueError('owned containers already present')
 def snapshot():
  ids=subprocess.check_output(['nvidia-smi','-i','0','--query-gpu=uuid','--format=csv,noheader'],text=True).strip()
  pids=subprocess.check_output(['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'],text=True).strip()
  if ids!=UUID or pids:raise ValueError('GPU busy or unknown identity')
  return {'epoch':time.time(),'uuid':ids,'pids':pids}
 first=snapshot();time.sleep(10);second=snapshot()
 # Revalidate absolute deadline after all potentially expensive preflight checks.
 if validate(go_path,go_digest)!=g:raise ValueError('GO changed')
 nonce=root/('consumed-'+g['nonce']);nonce.touch(exist_ok=False)
 out=root/('run-'+g['nonce']);out.mkdir();(out/'preflight.json').write_text(json.dumps([first,second]))
 remain=math.floor(g['deadline_epoch']-time.time())
 if remain<=0:raise ValueError('deadline elapsed')
 args=['docker','create','--cidfile',str(out/'cid'),'--name',project+'-smoke','--label','com.docker.compose.project='+project,'--label','pi21.nonce='+g['nonce'],'--gpus','device='+UUID,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--init','--cpus','8','--memory','24g','--pids-limit','1024','--user',str(os.getuid())+':'+str(os.getgid()),'--tmpfs','/tmp:size=1073741824','--shm-size','1g','--env','CUDA_VISIBLE_DEVICES=0','--env','HF_HUB_OFFLINE=1','--env','HF_HOME=/tmp/hf','--env','VLLM_CACHE_ROOT=/tmp/vllm','--mount','type=bind,src='+str(root/'env')+',dst=/venv,readonly','--mount','type=bind,src='+str(model)+',dst=/model,readonly','--mount','type=bind,src='+str(probe.parent)+',dst=/probe,readonly','--mount','type=bind,src='+str(out)+',dst=/evidence','--entrypoint','timeout',g['image'],'--signal=TERM','--kill-after=2s',str(remain)+'s','/venv/bin/python','/probe/smoke.py']
 stop=out/'stop-watch';ready=out/'watch-ready';watch=None;cid=None
 result={'status':'unknown','start_epoch':time.time(),'cid':None}
 def watch_args():return [sys.executable,str(pathlib.Path(__file__).with_name('watch.py')),'--cid',cid,'--nonce',g['nonce'],'--deadline',str(g['deadline_epoch']),'--stop-file',str(stop),'--out',str(out/'watch.jsonl'),'--ready',str(ready)]
 try:
  created=time.time()
  try:creation=subprocess.run(args,capture_output=True,text=True,timeout=20)
  except subprocess.TimeoutExpired as e:
   (out/'create.json').write_text(json.dumps({'command':args,'start_epoch':created,'end_epoch':time.time(),'timeout':True,'stdout':str(e.stdout),'stderr':str(e.stderr)},indent=2));raise
  (out/'create.json').write_text(json.dumps({'command':args,'start_epoch':created,'end_epoch':time.time(),'exit':creation.returncode,'stdout':creation.stdout,'stderr':creation.stderr},indent=2))
  creation.check_returncode()
  cid=(out/'cid').read_text().strip();result['cid']=cid
  if len(cid)!=64 or any(c not in '0123456789abcdef' for c in cid):raise ValueError('unknown CID')
  watch=subprocess.Popen(watch_args())
  ready_deadline=min(g['deadline_epoch'],time.time()+3)
  while not ready.exists() and time.time()<ready_deadline and watch.poll() is None:time.sleep(.05)
  if not ready.exists() or watch.poll() is not None:raise RuntimeError('independent watch unavailable')
  with (out/'native.log').open('w') as f:
   p=subprocess.run(['docker','start','-a',cid],stdout=f,stderr=subprocess.STDOUT,timeout=max(.001,g['deadline_epoch']-time.time()+2))
  result.update(status='complete' if p.returncode==0 and (out/'completed.json').exists() else 'failed',exit=p.returncode)
 except Exception as e:result.update(error=repr(e))
 finally:
  stop.touch()
  try:
   if watch is not None:watchcode=watch.wait(timeout=25)
   elif (out/'cid').exists():
    cid=(out/'cid').read_text().strip();watchcode=subprocess.run(watch_args(),timeout=25).returncode
   else:watchcode=2
   result['watch_exit']=watchcode
  except Exception as e:result.update(cleanup_error=repr(e),watch_exit=2)
  result['end_epoch']=time.time();(out/'outcome.json').write_text(json.dumps(result,indent=2))
 if result['status']!='complete' or result['watch_exit']!=0:raise RuntimeError('native failed or cleanup unknown')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True);a=p.parse_args()
 try:g=validate(a.go,a.go_sha256)
 except Exception as e:print('GO rejected: '+str(e),file=sys.stderr);sys.exit(2)
 try:execute(g,a.go,a.go_sha256)
 except Exception as e:print('Run failed: '+repr(e),file=sys.stderr);sys.exit(3)
