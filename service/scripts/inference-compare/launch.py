"""Issue28-only foreground chain. No implicit stages, retry, pull or installation."""
import argparse,asyncio,base64,json,math,os,resource,shutil,signal,subprocess,sys,threading,time,urllib.request
from pathlib import Path
from authority import ROOT,GPU,validate,verify_entries,sha,consume,local_file
from owned import OwnedDocker
from plan import validate_frozen_plan

VLLM_ROOT=Path('/media/usv012/pjx/pi-agent-platform/experiments/21-vllm-compat-20261111/builder')
TF_ROOT=Path('/media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021')
MODEL_ROOT=Path('/media/usv012/pjx/agent/Qwen3-8B')
IMAGES={'A':'sha256:7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2',
        'B':'sha256:08619d6d884b3b456661f883a4e4420bd85a81aee560a86f7f26021b75dd6229'}

def docker_created_ns(value):
    import importlib.util
    file=Path(__file__).resolve().parents[1]/'nginx-entry/measurement.py'
    spec=importlib.util.spec_from_file_location('_pi28_docker_timestamp',file);parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
    return parser.timestamp_ns(value)

def model_command(g,model,index,root,out,network_id,go_digest):
    arm=model['arm'];project='pi-compare28-'+('b' if g['role']=='builder' else 'r')
    command=['create','--name',project+'-'+model['nonce'],'--network',network_id,'--runtime','nvidia','--user','1001:1001',
             '--workdir','/source','--cpus','6','--memory','28g','--memory-swap','28g','--pids-limit','512','--read-only',
             '--tmpfs','/tmp:rw,size=1g','--shm-size','1g','--cap-drop','ALL','--security-opt','no-new-privileges:true']
    labels={'workorder':'28','execution-sha':g['source_sha'],'com.docker.compose.project':project,'pi28.nonce':model['nonce']}
    for k,v in labels.items():command+=['--label',k+'='+v]
    mounts=[(root/'source','/source','ro'),(MODEL_ROOT,'/model','ro'),(out,'/evidence','rw'),(root/'contracts'/g['nonce'],'/contract','ro')]
    mounts.append((VLLM_ROOT/'env','/venv','ro') if arm=='B' else (TF_ROOT/'deps','/deps','ro'))
    for host,target,mode in mounts:command+=['--volume',str(host)+':'+target+':'+mode]
    env={'NVIDIA_VISIBLE_DEVICES':GPU,'NVIDIA_DRIVER_CAPABILITIES':'compute,utility','CUDA_VISIBLE_DEVICES':'0',
         'VLLM_USE_V1':'1','VLLM_WORKER_MULTIPROC_METHOD':'spawn','PYTHONDONTWRITEBYTECODE':'1',
         'PYTHONPATH':'/source' if arm=='B' else '/source:/deps','HOME':'/tmp','HF_HUB_OFFLINE':'1','HF_HOME':'/tmp/hf',
         'VLLM_CACHE_ROOT':'/tmp/vllm','TRITON_CACHE_DIR':'/tmp/triton','TORCHINDUCTOR_CACHE_DIR':'/tmp/torchinductor','XDG_CACHE_HOME':'/tmp/cache',
         'OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OMP_NUM_THREADS':'4' if arm=='B' else '6','TOKENIZERS_PARALLELISM':'false',
         'LOAD_TRACE':'/evidence/model-trace.jsonl','NATIVE_TRACE':'/evidence/native-trace.jsonl','TF_TOKEN_TRACE':'/evidence/tf-trace.jsonl',
         'INFERENCE_IDENTITY_RECEIPT':'/evidence/backend-identity.json','PI28_MODEL_NONCE':model['nonce']}
    for k,v in env.items():command+=['--env',k+'='+v]
    command+=['--entrypoint','/usr/bin/python3' if arm=='B' else '/usr/local/bin/python',IMAGES[arm],
              '/source/service/scripts/inference-compare/native.py','--go','/contract/go.json','--go-sha256',go_digest,
              '--phase-contract','/contract/phase.json','--phase-contract-sha256',g['phase_contract_sha256'],'--model-index',str(index)]
    return command

def asset_check(g,root):
    path=local_file(root,g['assets_file'])
    if sha(path)!=g['assets_sha256']:raise ValueError('asset inventory binding')
    assets=json.loads(path.read_text());expected={
        'model':(MODEL_ROOT,'4380c0c2174d1ba6a4698f37d06d05cfb01d3652a19fccdeeb414a96b573a1a8'),
        'vllm':(VLLM_ROOT,'8399994fa82aac42c3cd82a0f3e697bb46f70e16d4ba62969a13ce3a76fc8820'),
        'transformers':(TF_ROOT/'deps','0daa116e06671a31c9b57f69a7664aa30c5e33d04898eda18f08451bfa93a1e3')}
    if set(assets['manifests'])!=set(expected):raise ValueError('complete both-runtime/model assets required')
    for name,(base,digest) in expected.items():
        manifest=assets['manifests'][name]
        if manifest['root']!=str(base) or manifest['sha256']!=digest or sha(manifest['path'])!=digest:raise ValueError('cached manifest identity '+name)
        from prepare import manifest_files
        rows=manifest_files(json.loads(Path(manifest['path']).read_text()))
        expected_files=set()
        for row in rows:
            # Original model manifest includes download metadata; retained but not model runtime inputs.
            if name=='model' and row['path'].startswith(('.cache/','._')):continue
            p=Path(row['path'])
            if p.is_absolute() or '..' in p.parts:raise ValueError('asset closure path')
            file=base/p
            expected_files.add(str(p))
            if file.stat().st_size!=row['bytes'] or sha(file)!=row['sha256']:raise ValueError('cached asset bytes '+str(file))
        scan=base/'env' if name=='vllm' else base
        actual_files=set()
        def unreadable(error):raise RuntimeError('cached closure inventory unknown: '+repr(error))
        for parent,dirs,files in os.walk(scan,onerror=unreadable,followlinks=False):
            for leaf in files:
                p=Path(parent)/leaf;relative=str(p.relative_to(base))
                if not p.is_symlink() and not (name=='model' and relative.startswith(('.cache/','._'))):actual_files.add(relative)
        if actual_files!=expected_files:raise ValueError('cached complete regular-file closure differs '+name)
    return assets

def execute(a,g):
    started=time.time()
    root=ROOT/g['role'];source=root/'source';here=source/'service/scripts/inference-compare'
    if Path.cwd().resolve()!=root or os.environ.get('CUDA_VISIBLE_DEVICES')!='0':raise ValueError('role root/CUDA mapping')
    verify_entries(g,source)
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()!=g['source_sha'] or subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True).strip():raise ValueError('clean exact source required')
    plan=json.loads(local_file(root,g['plan_file']).read_text());validate_frozen_plan(plan,require_expected=True)
    if plan['stage']!=g['stage']:raise ValueError('frozen stage identity')
    asset_check(g,root)
    if (root/('consumed-'+g['nonce'])).exists():raise ValueError('stage nonce already consumed')
    if shutil.disk_usage(root).free<20*2**30:raise ValueError('free disk')
    os.sched_setaffinity(0,{0,1});resource.setrlimit(resource.RLIMIT_AS,(2**30,2**30))
    out=root/('run-'+g['nonce']);out.mkdir(exist_ok=False)
    contract=root/'contracts'/g['nonce'];contract.mkdir(parents=True,exist_ok=False)
    for input_path in [Path(a.go),Path(a.phase_contract),local_file(root,g['plan_file']),local_file(root,g['ledger_file'])]:
        target=contract/('go.json' if input_path==Path(a.go) else 'phase.json' if input_path==Path(a.phase_contract) else input_path.relative_to(root))
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(input_path,target)
    device_total=0;post_total=0;native_total=0
    from client import dump,run_block
    stage={'issue':28,'source_sha':g['source_sha'],'phase_sha256':g['phase_contract_sha256'],'go_sha256':a.go_sha256,
           'start':started,'spent_before':g['spent'],'models':[],'complete':False}
    for index,(model,block) in enumerate(zip(g['models'],plan['blocks'])):
        validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256)
        verify_entries(g,source)
        if time.time()+40>=model['deadline_epoch'] or model['deadline_epoch']-time.time()>1800:raise ValueError('model fresh bounded deadline')
        if (root/('consumed-'+model['nonce'])).exists():raise ValueError('model nonce already consumed before tools')
        if time.time()-started>=g['allocated_device_s']:raise RuntimeError('stage budget exhausted')
        model_out=out/model['id'];model_out.mkdir();docker=OwnedDocker(g['role'],g['source_sha'],model['nonce']);known={};network=None;watch=None;cid=None;created=None;failure=None;stop_lease=threading.Event();lease_thread=None
        receipt={'id':model['id'],'arm':model['arm'],'nonce':model['nonce'],'complete':False,'device_s':None,'POST':None,'native':None}
        stage['models'].append(receipt);dump(out/'stage.json',stage)
        def record_command(args):
            r=docker.command(args);dump(model_out/'docker-receipts.json',docker.receipts)
            if r.returncode:raise RuntimeError('Docker command failed')
            return r
        def lease():
            while not stop_lease.is_set():(model_out/'foreground-lease').touch();stop_lease.wait(.5)
        try:
            if docker.discover(known):raise ValueError('preexisting owned objects')
            snapshots=[]
            for n in range(2):
                for query in ['--query-gpu=uuid','--query-compute-apps=pid,gpu_uuid']:
                    at=time.time();r=subprocess.run(['nvidia-smi','-i','0',query,'--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
                    snapshots.append({'epoch':at,'end':time.time(),'query':query,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr});dump(model_out/'empty-gate.json',snapshots)
                    if r.returncode or (r.stdout.strip()!=GPU if query=='--query-gpu=uuid' else bool(r.stdout.strip())):raise ValueError('GPU0 busy/unknown/identity')
                if n==0:time.sleep(10)
            validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256)
            verify_entries(g,source)
            if time.time()+40>=model['deadline_epoch']:raise ValueError('selected model deadline expired during preflight before Docker')
            consume(root/('consumed-'+model['nonce']))
            network=docker.create_network();dump(model_out/'network.json',docker.network(network))
            lease_thread=threading.Thread(target=lease,daemon=True);lease_thread.start()
            watch_log=(model_out/'watch.log').open('w')
            watch=subprocess.Popen([sys.executable,str(here/'watch.py'),'--go',a.go,'--go-sha256',a.go_sha256,
                                    '--phase-contract',a.phase_contract,'--phase-contract-sha256',a.phase_contract_sha256,'--model-index',str(index),'--out',str(model_out)],
                                   stdout=watch_log,stderr=subprocess.STDOUT,start_new_session=True)
            until=min(model['deadline_epoch']-25,time.time()+5)
            while not (model_out/'watch-ready').exists() and time.time()<until and watch.poll() is None:time.sleep(.05)
            if not (model_out/'watch-ready').exists() or watch.poll() is not None:raise RuntimeError('watch not ready')
            for image in IMAGES.values():record_command(['image','inspect',image])
            command=model_command(g,model,index,root,model_out,network,a.go_sha256)
            result=record_command(command);cid=result.stdout.strip();row=docker.inspect(cid)
            if row is None:raise RuntimeError('created model missing')
            created_ns=docker_created_ns(row['Created']);created=created_ns/1e9;receipt.update(cid=cid,created_text=row['Created'],created_epoch=created,created_epoch_ns=created_ns)
            record_command(['start',cid]);url=docker.endpoint(cid,network);dump(model_out/'endpoint.json',{'cid':cid,'network_id':network,'url':url,'labels':docker.labels})
            while time.time()<model['deadline_epoch']-25:
                if watch.poll() is not None:raise RuntimeError('watch failed')
                query_start=time.time();query_receipt={'start':query_start,'url':url+'/health'}
                try:
                    with urllib.request.urlopen(url+'/health',timeout=1) as response:
                        raw=response.read();query_receipt.update(end=time.time(),status=response.status,headers=dict(response.headers),body_b64=base64.b64encode(raw).decode())
                    with (model_out/'readiness.jsonl').open('a') as log:log.write(json.dumps(query_receipt)+'\n')
                    health=json.loads(raw)
                    if health['ready'] is True:
                        expected_backend='transformers-serialized/Qwen3-8B' if model['arm']=='A' else 'vllm-0.8.5.post1+cu118/V1-uni/Qwen3-8B'
                        if health['backend']!=expected_backend or health['model']!='Qwen3-8B' or health['max_context']!=1024 or health['max_active_generation']!=1 or health['max_attempts']!=model['max_attempts']:raise RuntimeError('actual model health identity/configuration')
                        if health['calls'] or health['attempts'] or health['active_generation'] or health['queued']:raise ValueError('fresh model counters')
                        receipt['ready_epoch']=time.time();dump(model_out/'ready.json',health);break
                except (OSError,ValueError) as exc:
                    query_receipt.update(end=time.time(),error=repr(exc))
                    with (model_out/'readiness.jsonl').open('a') as log:log.write(json.dumps(query_receipt)+'\n')
                time.sleep(.2)
            else:raise RuntimeError('readiness timeout')
            async def client():
                import aiohttp
                deadline_ns=time.monotonic_ns()+int((model['deadline_epoch']-time.time()-20)*1e9)
                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0),trust_env=False) as session:
                    return await run_block(session,url,block,model_out,deadline_ns)
            report=asyncio.run(client());receipt.update(complete=report['complete'],POST=report['completion_POST'],native=report['native_calls'])
            if watch.poll() is not None:raise RuntimeError('watch failed during client')
        except BaseException as exc:failure=repr(exc)
        finally:
            try:
                docker.discover(known)
                if cid:
                    logs=docker.command(['logs',cid]);dump(model_out/'model-logs.json',{'exit':logs.returncode,'stdout':logs.stdout,'stderr':logs.stderr})
            except BaseException as exc:failure=failure or repr(exc)
            (model_out/'watch-stop').touch()
            if watch is not None:
                try:watch.wait(timeout=30)
                except subprocess.TimeoutExpired:failure=failure or 'watch cleanup timeout'
                if watch.poll()!=0:failure=failure or 'watch failed'
            cleanup=docker.cleanup(known)
            if network and cleanup['success']:
                try:receipt['network_cleanup']=docker.remove_network(network)
                except Exception as exc:failure=failure or repr(exc)
            stop_lease.set()
            if lease_thread:lease_thread.join(timeout=2)
            if created is not None:
                from client import load_lines
                command_receipts=[*docker.receipts,*[r for row in load_lines(model_out/'watch.jsonl') if row.get('event')=='cleanup' for r in row.get('receipts',[])]]
                removals=[r for r in command_receipts if r.get('command')==['rm',cid] and r.get('exit')==0]
                if removals:
                    removal=min(removals,key=lambda r:r['end']);receipt['rm_command_start_epoch']=removal['start'];receipt['removed_epoch']=removal['end']
                    receipt['device_s']=receipt['removed_epoch']-created;device_total+=receipt['device_s']
                else:failure=failure or 'actual model removal time unknown'
            if (model_out/'block-report.json').exists():
                partial=json.loads((model_out/'block-report.json').read_text());receipt['POST']=partial['completion_POST'];receipt['native']=partial.get('native_calls')
            post_total+=receipt['POST'] or 0
            if receipt['native'] is not None:native_total+=receipt['native']
            else:stage['native_count_unknown']=True
            receipt.update(cleanup=cleanup,failure=failure)
            stage.update(device_s=device_total,POST=post_total,native=native_total,server_wall_s=math.ceil(time.time()-started),end=time.time())
            dump(out/'stage.json',stage)
        if failure or not cleanup['success'] or stage.get('native_count_unknown'):raise RuntimeError('model partial/cleanup/usage unknown; stop stage')
        if device_total>g['allocated_device_s'] or post_total>g['allocated_POST'] or native_total>g['allocated_native']:raise RuntimeError('stage cost exceeded')
    consume(root/('consumed-'+g['nonce']));stage['complete']=True;dump(out/'stage.json',stage)
    return stage

def main():
    p=argparse.ArgumentParser();p.add_argument('--go',required=True);p.add_argument('--go-sha256',required=True)
    p.add_argument('--phase-contract',required=True);p.add_argument('--phase-contract-sha256',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    try:
        g=validate(a.go,a.go_sha256,a.phase_contract,a.phase_contract_sha256)
        if a.validate_only:print(json.dumps({'valid':True,'issue':28,'stage':g['stage']}));return 0
        def expired(*_):raise RuntimeError('foreground absolute stage deadline')
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,max(.001,min(g['deadline_epoch']-15-time.time(),g['allocated_server_wall_s'])))
        execute(a,g);return 0
    except Exception as exc:print('Pi28 rejected/failed: '+repr(exc),file=sys.stderr);return 2
    finally:signal.setitimer(signal.ITIMER_REAL,0)

if __name__=='__main__':raise SystemExit(main())
