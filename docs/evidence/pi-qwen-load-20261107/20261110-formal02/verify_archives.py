"""Verify original archive members without extracting or executing their contents."""
from pathlib import Path
import hashlib,json,tarfile
D=Path(__file__).resolve().parent
for archive,manifest in [('formal02-originals.tar.gz','raw-manifest.json'),('calibration-originals-excluding-profile.tar.gz','calibration-committed-manifest.json')]:
 expected=json.loads((D/manifest).read_text()); seen={}
 with tarfile.open(D/archive) as tf:
  for member in tf:
   if member.isfile():
    assert member.name not in seen,member.name
    seen[member.name]=hashlib.sha256(tf.extractfile(member).read()).hexdigest()
 if archive=='formal02-originals.tar.gz':
  embedded=seen.pop('formal-nov10-02-originals-manifest.json')
  assert embedded==hashlib.sha256((D/manifest).read_bytes()).hexdigest()
 assert seen==expected,(archive,len(seen),len(expected))
 print(archive,len(seen),'files; hash mismatches=0')
