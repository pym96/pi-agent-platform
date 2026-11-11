"""Validate frozen official wheel bytes before any isolated installation."""
import argparse,email,hashlib,json,pathlib,urllib.parse,zipfile
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.markers import default_environment
PINNED={'vllm':'0.8.5.post1+cu118','torch':'2.6.0+cu118','torchvision':'0.21.0+cu118','torchaudio':'2.6.0+cu118','xformers':'0.0.29.post2','transformers':'4.51.3','tokenizers':'0.21.1','triton':'3.2.0','numpy':'1.26.4'}
HOSTS={'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com','download.pytorch.org','download-r2.pytorch.org','pypi.org','files.pythonhosted.org'}
XFORMERS='https://download.pytorch.org/whl/cu118/xformers-0.0.29.post2-cp310-cp310-manylinux_2_28_x86_64.whl'
def validate(lock,wheels):
 rows=json.loads(pathlib.Path(lock).read_text());root=pathlib.Path(wheels);names={};files=set();total=0;metadata_by_name={}
 if not rows:raise ValueError('empty closure')
 for row in rows:
  filename=row['filename'];f=root/filename;u=urllib.parse.urlparse(row['url'])
  if f.name!=filename or u.scheme!='https' or u.hostname not in HOSTS:raise ValueError('untrusted artifact URL/path')
  if filename in files or canonicalize_name(row['name']) in names:raise ValueError('duplicate artifact')
  if canonicalize_name(row['name'])=='xformers' and row['url']!=XFORMERS:raise ValueError('xformers CUDA variant ambiguous')
  h=hashlib.sha256()
  with f.open('rb') as b:
   for chunk in iter(lambda:b.read(1024*1024),b''):h.update(chunk)
  if h.hexdigest()!=row['sha256'] or f.stat().st_size!=row['size']:raise ValueError('artifact bytes mismatch')
  with zipfile.ZipFile(f) as z:
   metadata=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
   if len(metadata)!=1:raise ValueError('wheel metadata ambiguous')
   m=email.message_from_bytes(z.read(metadata[0]))
  if (canonicalize_name(m['Name']),m['Version'])!=(canonicalize_name(row['name']),row['version']):raise ValueError('wheel identity mismatch')
  names[canonicalize_name(row['name'])]=row['version'];metadata_by_name[canonicalize_name(row['name'])]=m.get_all('Requires-Dist',[]);files.add(filename);total+=row['size']
 if not {canonicalize_name(k):v for k,v in PINNED.items()}.items()<=names.items():raise ValueError('fixed runtime closure mismatch')
 if files!={f.name for f in root.iterdir() if f.is_file()}:raise ValueError('wheel directory contains unsealed files')
 if total>8*1024**3:raise ValueError('download budget exceeded')
 # Evaluate every installed distribution's active dependencies for the fixed target,
 # including extras requested by transitive requirements. No network or installation.
 env=default_environment();env.update(python_version='3.10',python_full_version='3.10.12',implementation_name='cpython',implementation_version='3.10.12',platform_python_implementation='CPython',sys_platform='linux',platform_system='Linux',platform_machine='x86_64',os_name='posix')
 extras={name:set() for name in names};changed=True
 while changed:
  changed=False
  for name,dependencies in metadata_by_name.items():
   for text in dependencies:
    r=Requirement(text)
    if r.marker and not any(r.marker.evaluate({**env,'extra':extra}) for extra in {'',*extras[name]}):continue
    target=canonicalize_name(r.name)
    if r.url:raise ValueError('unlocked direct dependency URL')
    if target not in names or not r.specifier.contains(names[target],prereleases=True):raise ValueError('missing or incompatible transitive dependency: '+str(r))
    before=len(extras[target]);extras[target].update(r.extras);changed=changed or len(extras[target])!=before
 return {'artifacts':len(rows),'bytes':total,'pinned':PINNED}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('lock');p.add_argument('wheels');a=p.parse_args();print(json.dumps(validate(a.lock,a.wheels),indent=2))
