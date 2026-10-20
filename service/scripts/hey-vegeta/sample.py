#!/usr/bin/env python3
"""Optional continuous resource sampler; exact owned project, bounded lifetime."""
import datetime,json,os,pathlib,subprocess,time
root=pathlib.Path(os.environ['RUN_ROOT'])/'evidence'
project=os.environ.get('HV_PROJECT','pi-hv3')
start=time.monotonic()
with (root/'continuous-resources.jsonl').open('a') as out:
    while time.monotonic()-start<900 and not (root/'stop.json').exists():
        names=subprocess.run(['docker','ps','--filter','name='+project+'-','--format','{{.Names}}'],capture_output=True,text=True).stdout.split()
        if names:
            p=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',*names],capture_output=True,text=True)
            out.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'containers':[json.loads(x) for x in p.stdout.splitlines() if x],'exitCode':p.returncode,'stderr':p.stderr})+'\n');out.flush()
        time.sleep(1)
