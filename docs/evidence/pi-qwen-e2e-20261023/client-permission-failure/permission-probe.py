import os,json,hashlib
from pathlib import Path
config=Path('/source/service/scripts/pi-qwen-e2e/stage-b.json')
root=Path('/evidence/client-permission-probe')
assert root.exists()
record={'kind':'CPU-only permission probe, no HTTP/model calls','uid':os.getuid(),'gid':os.getgid(),'source_config_sha256':hashlib.sha256(config.read_bytes()).hexdigest()}
p=root/'ledger.jsonl'
with p.open('x') as f:f.write(json.dumps(record)+'\n');f.flush();os.fsync(f.fileno())
record['ledger_uid']=p.stat().st_uid;record['ledger_gid']=p.stat().st_gid;assert record['uid']==record['ledger_uid']==1001 and record['gid']==record['ledger_gid']==1001
print(json.dumps(record))
