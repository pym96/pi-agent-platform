import os,sys,json,time,urllib.request,hashlib,subprocess,pathlib,zipfile,email
R=pathlib.Path('/stage'); W=R/'wheels';W.mkdir(exist_ok=True)
def run(args):
 t=time.time(); p=subprocess.run(args,timeout=max(1,1794324216-time.time()),stdout=(R/'download.log').open('a'),stderr=subprocess.STDOUT); (R/'commands.jsonl').open('a').write(json.dumps({'args':args,'start':t,'end':time.time(),'exit':p.returncode})+'\n');p.check_returncode()
# Official bootstrap, fully hashed before use. No CUDA device exposed.
j=json.load(urllib.request.urlopen('https://pypi.org/pypi/pip/25.0.1/json',timeout=20)); a=next(x for x in j['urls'] if x['filename'].endswith('.whl'));b=urllib.request.urlopen(a['url'],timeout=30).read();assert hashlib.sha256(b).hexdigest()==a['digests']['sha256'];(R/a['filename']).write_bytes(b);(R/'pip-bootstrap.json').write_text(json.dumps(a,indent=2))
run([sys.executable,'-m','venv','--without-pip',str(R/'env')]); p=str(R/'env/bin/python');os.environ['PYTHONPATH']=str(R/a['filename']);os.environ['PIP_DISABLE_PIP_VERSION_CHECK']='1';os.environ['PIP_RETRIES']='0';os.environ['PIP_NO_CACHE_DIR']='1';os.environ['PIP_DEFAULT_TIMEOUT']='30'
v='https://github.com/vllm-project/vllm/releases/download/v0.8.5.post1/vllm-0.8.5.post1%2Bcu118-cp38-abi3-manylinux1_x86_64.whl'
args=[p,'-m','pip','download','--only-binary=:all:','--dest',str(W),'--index-url','https://pypi.org/simple','--extra-index-url','https://download.pytorch.org/whl/cu118','torch==2.6.0+cu118','torchvision==0.21.0+cu118','torchaudio==2.6.0+cu118','xformers==0.0.29.post2','transformers==4.51.3','tokenizers==0.21.1','numpy==1.26.4',v]
run(args)
rows=[]
for f in sorted(W.glob('*.whl')):
 h=hashlib.sha256(f.read_bytes()).hexdigest()
 with zipfile.ZipFile(f) as z:m=email.message_from_bytes(z.read(next(n for n in z.namelist() if n.endswith('.dist-info/METADATA'))))
 rows.append({'filename':f.name,'name':m['Name'],'version':m['Version'],'size':f.stat().st_size,'sha256':h,'requires':m.get_all('Requires-Dist',[])})
assert sum(x['size'] for x in rows)<=8*1024**3
(R/'closure.json').write_text(json.dumps(rows,indent=2));(R/'requirements.lock').write_text(''.join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in rows))
# Full closure is sealed before first dependency install.
run([p,'-m','pip','install','--no-index','--find-links',str(W),'--require-hashes','-r',str(R/'requirements.lock')]);run([p,'-m','pip','check'])
