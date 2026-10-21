"""Foreground monitor: only the exact owned #9 container may be stopped."""
import argparse,json,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--sha',required=True);p.add_argument('--deadline',type=float,required=True);a=p.parse_args()
name='pi-inference9-model';gpu='GPU-dd5fc05f-7d4d-17f7-8d33-2f474b56b74e'
def cmd(args):return subprocess.check_output(args,text=True).strip()
initial=json.loads(cmd(['docker','inspect',name]))[0];container=initial['Id']
assert initial['Config']['Labels'].get('workorder')=='9' and initial['Config']['Labels'].get('execution-sha')==a.sha
try:
    while True:
        state=json.loads(cmd(['docker','inspect',container]))[0]
        if not state['State']['Running']:
            print(json.dumps({'event':'owned_stopped','container':container,'time':time.time()}),flush=True);break
        reason=None
        if time.time()>=a.deadline:reason='deadline'
        owned={int(line.strip()) for line in cmd(['docker','top',container,'-eo','pid']).splitlines()[1:]}
        others=[]
        for line in cmd(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits']).splitlines():
            fields=[x.strip() for x in line.split(',')]
            if fields[0]==gpu and int(fields[1]) not in owned:others.append(int(fields[1]))
        if others:reason='unrelated_gpu_process'
        if reason:
            print(json.dumps({'event':'stop_requested','reason':reason,'unrelated_pids':others,'container':container}),flush=True)
            subprocess.run(['docker','stop','--time','2',container],check=True,timeout=10)
        else:time.sleep(2)
finally:
    # Any monitor failure/interrupt must not silently leave our GPU process running.
    state=json.loads(cmd(['docker','inspect',container]))[0]
    if state['State']['Running']:
        subprocess.run(['docker','stop','--time','2',container],check=True,timeout=10)
