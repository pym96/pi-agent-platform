#!/usr/bin/python3
"""Owned transparent stdout/stderr receipt; never substitutes an NVML result."""
import os,sys,json,time,subprocess,signal,base64
REAL='/usr/bin/nvidia-smi'
LOG='/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/NVML-QUERY-RAW-NOV14-V2.jsonl'
def record(row):
 data=(json.dumps(row,separators=(',',':'))+'\n').encode()
 fd=os.open(LOG,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
 try:os.write(fd,data)
 finally:os.close(fd)
start=time.time();args=[REAL,*sys.argv[1:]]
record({'event':'start','pid':os.getpid(),'epoch':start,'command':args})
try:r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=4.0)
except subprocess.TimeoutExpired as e:
 # subprocess.run kills and waits for its child before raising TimeoutExpired.
 out=e.stdout or b'';err=e.stderr or b''
 record({'event':'wrapper_timeout','pid':os.getpid(),'start':start,'end':time.time(),'command':args,'result':'unknown','exit':None,'wrapper_exit':124,'stdout_base64':base64.b64encode(out).decode(),'stderr_base64':base64.b64encode(err).decode()})
 os.write(1,out);os.write(2,err+b'NVML query wrapper timeout; result unknown\n');raise SystemExit(124)
record({'event':'complete','pid':os.getpid(),'start':start,'end':time.time(),'command':args,'exit':r.returncode,'stdout_base64':base64.b64encode(r.stdout).decode(),'stderr_base64':base64.b64encode(r.stderr).decode(),'stdout':r.stdout.decode('utf-8',errors='backslashreplace'),'stderr':r.stderr.decode('utf-8',errors='backslashreplace')})
os.write(1,r.stdout);os.write(2,r.stderr)
if r.returncode<0:os.kill(os.getpid(),-r.returncode)
raise SystemExit(r.returncode)
