import os,time,json,pathlib,subprocess,datetime
start=time.time();assert pathlib.Path.cwd()==pathlib.Path('/media/usv012/pjx') and os.environ.get('CUDA_VISIBLE_DEVICES')=='0'
stop=datetime.datetime.fromisoformat('2026-11-11T15:20:09.454973+00:00').timestamp();assert start+31<stop
rows=[]
for offset in [0,15,30]:
 remain=start+offset-time.time()
 if remain>0:time.sleep(remain)
 row={'offset_s':offset,'epoch':time.time(),'queries':{}}
 for name,args in [('uuid',['nvidia-smi','-i','0','--query-gpu=uuid','--format=csv,noheader']),('compute',['nvidia-smi','-i','0','--query-compute-apps=pid,gpu_uuid','--format=csv,noheader'])]:
  try:
   r=subprocess.run(args,capture_output=True,text=True,timeout=5);row['queries'][name]={'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
  except Exception as e:row['queries'][name]={'error':repr(e)}
 rows.append(row)
 assert time.time()<stop
v={'start':start,'end':time.time(),'samples':rows,'device_query_index':0,'CUDA_VISIBLE_DEVICES':'0','model_calls':0,'container_started':False,'PID_introspection':False,'release':True}
assert v['end']-start<=45
path=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/GPU0-OBSERVE02.json');assert not path.exists();path.write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2))
