#!/usr/bin/python3
"""Owned transparent stdout/stderr receipt; never substitutes an NVML result."""
import os,sys,json,time,subprocess,signal
REAL='/usr/bin/nvidia-smi'
LOG='/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/NVML-NORMAL01-RAW.jsonl'
def record(row):
 data=(json.dumps(row,separators=(',',':'))+'\n').encode()
 fd=os.open(LOG,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
 try:os.write(fd,data)
 finally:os.close(fd)
start=time.time();args=[REAL,*sys.argv[1:]]
record({'event':'start','pid':os.getpid(),'epoch':start,'command':args})
r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
record({'event':'complete','pid':os.getpid(),'start':start,'end':time.time(),'command':args,'exit':r.returncode,'stdout':r.stdout.decode('utf-8',errors='backslashreplace'),'stderr':r.stderr.decode('utf-8',errors='backslashreplace')})
os.write(1,r.stdout);os.write(2,r.stderr)
if r.returncode<0:os.kill(os.getpid(),-r.returncode)
raise SystemExit(r.returncode)
