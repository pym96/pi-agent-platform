import pathlib,tempfile,subprocess,sys,json,os,time,hashlib
state=pathlib.Path.home()/'.local/state/pi-agent-platform/vllm24-builder-20261114';source=(state/'nvidia-smi-raw-wrapper-v2.py').read_text();results=[]
with tempfile.TemporaryDirectory(dir=state,prefix='query-wrapper-test-') as d:
 root=pathlib.Path(d);real=root/'real';log=root/'raw.jsonl';argsfile=root/'args.json';pidfile=root/'pid'
 wrapper=root/'wrapper.py';text=source.replace("REAL='/usr/bin/nvidia-smi'",'REAL='+repr(str(real))).replace("LOG='/media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/NVML-QUERY-RAW-NOV14-V2.jsonl'",'LOG='+repr(str(log)));wrapper.write_text(text)
 args=['-i','0','--query-gpu=uuid','--format=csv,noheader']
 real.write_text('#!'+sys.executable+'\nimport os,sys,pathlib,json\npathlib.Path('+repr(str(argsfile))+').write_text(json.dumps(sys.argv[1:]))\nos.write(1,b"GPU-test\\xff\\n");os.write(2,b"stderr\\xfe");raise SystemExit(7)\n');real.chmod(0o700)
 r=subprocess.run([sys.executable,str(wrapper),*args],capture_output=True,timeout=5);assert r.returncode==7 and r.stdout==b'GPU-test\xff\n' and r.stderr==b'stderr\xfe';assert json.loads(argsfile.read_text())==args
 rows=[json.loads(x) for x in log.read_text().splitlines()];assert rows[-1]['exit']==7;results.append({'kind':'normal-raw-byte-and-argv-exit-transparency','exit':r.returncode,'stdout_hex':r.stdout.hex(),'stderr_hex':r.stderr.hex(),'actual_args':json.loads(argsfile.read_text()),'rows':rows})
 real.write_text('#!'+sys.executable+'\nimport os,time,pathlib\npathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid()))\nos.write(1,b"partial\\n");os.write(2,b"partialerror\\n");time.sleep(10)\n');real.chmod(0o700)
 start=time.time();r=subprocess.run([sys.executable,str(wrapper),*args],capture_output=True,timeout=5);elapsed=time.time()-start;assert r.returncode==124 and r.stdout==b'partial\n' and b'result unknown' in r.stderr and elapsed<5
 pid=int(pidfile.read_text())
 try:os.kill(pid,0)
 except ProcessLookupError:alive=False
 else:alive=True
 assert not alive
 row=json.loads(log.read_text().splitlines()[-1]);assert row['event']=='wrapper_timeout' and row['result']=='unknown' and row['exit'] is None
 results.append({'kind':'actual-timeout-child-kill-wait-unknown','elapsed_s':elapsed,'exit':r.returncode,'child_pid':pid,'child_still_exists':alive,'stdout_hex':r.stdout.hex(),'stderr_hex':r.stderr.hex(),'row':row})
report={'wrapper_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'tests':'actual OS child processes; fixture projects only REAL and LOG constants, no server or NVML/GPU','results':results,'success':True}
f=state/'QUERY-WRAPPER-V2-LOCAL-TESTS.json';f.write_text(json.dumps(report,indent=2)+'\n');print(hashlib.sha256(f.read_bytes()).hexdigest());print(json.dumps({'success':True,'timeout_elapsed_s':results[-1]['elapsed_s']}))
