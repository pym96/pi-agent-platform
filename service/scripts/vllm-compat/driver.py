"""Select the already projected native driver in a fresh process before model import."""
import argparse,hashlib,json,os,pathlib,stat,sys,uuid
DRIVER=pathlib.Path('/usr/lib/x86_64-linux-gnu/libcuda.so.535.309.01')
DIGEST='e649879a93439c72083bfc255d87727dcea196413e47152c8ee96ba467935d86'
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def prepare(directory,library,digest,environment):
 directory=pathlib.Path(directory);library=pathlib.Path(library)
 if environment.get('LD_PRELOAD'):raise ValueError('unexpected loader preload')
 if not library.is_file() or library.is_symlink():raise FileNotFoundError('native driver missing or indirect')
 if sha(library)!=digest:raise ValueError('native driver hash mismatch')
 if directory.parent!=directory.parent.resolve():raise ValueError('unsafe private parent')
 directory.mkdir(mode=0o700,exist_ok=False)
 for name in ['libcuda.so','libcuda.so.1']:(directory/name).symlink_to(library.resolve())
 env=dict(environment);env['LD_LIBRARY_PATH']=str(directory)+(os.pathsep+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
 return env
def verify_mapping(maps,library,digest):
 library=pathlib.Path(library).resolve();paths=set()
 for line in maps.splitlines():
  if 'libcuda.so' not in line:continue
  fields=line.split(maxsplit=5)
  if len(fields)!=6 or not fields[5].startswith('/') or fields[5].endswith(' (deleted)'):raise ValueError('ambiguous or deleted driver mapping')
  paths.add(fields[5])
 if not paths or any(pathlib.Path(p).resolve()!=library for p in paths):raise ValueError('native driver mapped path mismatch')
 if sha(library)!=digest:raise ValueError('native driver mapped hash mismatch')
 return [{'path':p,'realpath':str(library),'bytes':library.stat().st_size,'sha256':digest} for p in sorted(paths)]
def main():
 p=argparse.ArgumentParser();p.add_argument('--selected');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();command=a.command[1:] if a.command[:1]==['--'] else a.command
 if not command or not pathlib.Path(command[0]).is_absolute():raise ValueError('absolute child command required')
 if not a.selected:
  private=pathlib.Path('/tmp')/('pi21-driver-'+uuid.uuid4().hex);env=prepare(private,DRIVER,DIGEST,os.environ)
  # The loader reads LD_LIBRARY_PATH at process startup. Changing os.environ in
  # this interpreter cannot establish which library a later dlopen will select.
  os.execvpe(command[0],[command[0],__file__,'--selected',str(private),'--',*command],env)
 else:
  private=pathlib.Path(a.selected);receipt={'status':'failed','CUDA_API_calls':0,'ML_imports':[],'private_dir':str(private),'expected_native_sha256':DIGEST}
  try:
   st=private.lstat()
   if private.parent.resolve()!=pathlib.Path('/tmp').resolve() or not private.name.startswith('pi21-driver-') or not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:raise ValueError('unsafe private driver directory')
   if os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH','').split(os.pathsep)[0]!=str(private):raise ValueError('child loader environment mismatch')
   for name in ['libcuda.so','libcuda.so.1']:
    f=private/name
    if not f.is_symlink() or f.resolve()!=DRIVER:raise ValueError('private native driver link mismatch')
   if sha(DRIVER)!=DIGEST:raise ValueError('native driver changed')
   import ctypes
   handle=ctypes.CDLL('libcuda.so.1')
   maps=pathlib.Path('/proc/self/maps').read_text();receipt.update(mappings=verify_mapping(maps,DRIVER,DIGEST),maps=maps,status='selected',LD_LIBRARY_PATH=os.environ['LD_LIBRARY_PATH'])
  except BaseException as e:receipt['error']=repr(e);raise
  finally:pathlib.Path('/evidence/driver-selection.json').write_text(json.dumps(receipt,indent=2))
  # Exec again: the model starts with the verified selection and no inherited
  # CUDA initialization or Python ML module state from this non-init gate.
  os.execvpe(command[0],command,dict(os.environ))
if __name__=='__main__':main()
