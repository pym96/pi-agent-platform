import pathlib,subprocess,time,json,sys
R=pathlib.Path('/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261110/builder');assert pathlib.Path.cwd()==R
CID='017e942802cc605f57d4dce11c53aae7c1e19bc6cf41e9e6494942bc45f132f5';log=R/'preserve.jsonl'
def call(args,timeout=15):
 t=time.time();p=subprocess.run(args,capture_output=True,text=True,timeout=timeout);log.open('a').write(json.dumps({'epoch':t,'end':time.time(),'args':args,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr})+'\n');return p
r=call(['docker','inspect',CID]);v=json.loads(r.stdout)[0];assert v['Id']==CID and v['Config']['Labels']['com.docker.compose.project']=='pi-vllm21-b'
# Remain on the single current request. Stop conservatively before pip can advance to Torch.
while time.time()<1794323850:
 r=call(['docker','exec',CID,'python3','-c',"import os,json;print(json.dumps([{'path':os.path.join(d,f),'bytes':os.stat(os.path.join(d,f)).st_size} for d,_,fs in os.walk('/tmp') for f in fs if f.endswith('.whl')]))"])
 if r.returncode:break
 rows=json.loads(r.stdout);size=max([x['bytes'] for x in rows]+[0])
 if size>=213619284-2097152:break
 time.sleep(1)
p=call(['docker','pause',CID]);p.check_returncode()
try:
 p=call(['docker','cp',CID+':/tmp',str(R/'failed-partials')],timeout=35);p.check_returncode()
 call(['docker','inspect',CID])
finally:
 call(['docker','rm','-f',CID],timeout=15)
call(['docker','ps','-aq','--filter','label=com.docker.compose.project=pi-vllm21-b'])
call(['du','-sb',str(R)])
call(['df','-B1',str(R)])
