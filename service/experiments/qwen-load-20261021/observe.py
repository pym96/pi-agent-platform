"""Lightweight host observer; only stops exactly named experiment containers.

Run in foreground SSH; model has its own independent deadline guard as well.
"""
import argparse,datetime,json,pathlib,subprocess,time


def command(args):
    p=subprocess.run(args,text=True,capture_output=True,timeout=10)
    return dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--uuid',required=True);p.add_argument('--output',required=True)
    p.add_argument('--stop-file',required=True);a=p.parse_args()
    end=datetime.datetime(2026,10,21,9,20,tzinfo=datetime.timezone.utc)
    with pathlib.Path(a.output).open('w') as f:
        while not pathlib.Path(a.stop_file).exists():
            row=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=time.monotonic())
            row['gpu']=command(['nvidia-smi','-i',a.uuid,'--query-gpu=uuid,memory.used,memory.total,utilization.gpu,power.draw','--format=csv,noheader,nounits'])
            row['apps']=command(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader,nounits'])
            row['model_inspect']=command(['docker','inspect','pi-qwen7-model','--format','{{.State.Pid}}'])
            row['stats']=command(['docker','stats','--no-stream','--format','{{json .}}','pi-qwen7-model','pi-qwen7-generator'])
            pid=row['model_inspect']['stdout'].strip()
            foreign=[]
            if row['apps']['returncode']==0:
                for line in row['apps']['stdout'].splitlines():
                    cols=[x.strip() for x in line.split(',')]
                    if len(cols)>=2 and cols[0]==a.uuid and cols[1]!=pid:foreign.append(line)
            row['foreign_on_selected_uuid']=foreign
            f.write(json.dumps(row)+'\n');f.flush()
            if foreign or datetime.datetime.now(datetime.timezone.utc)>=end:
                for name in ['pi-qwen7-generator','pi-qwen7-model']:
                    result=command(['docker','stop','--time','10',name])
                    f.write(json.dumps(dict(event='stop_owned',name=name,result=result))+'\n');f.flush()
                break
            time.sleep(2)
