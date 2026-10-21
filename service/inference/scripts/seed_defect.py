"""Preserve defect and restored pytest executions in a disposable external source copy."""
import argparse,shutil,subprocess,sys,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out).resolve();out.mkdir()
repo=Path(__file__).resolve().parents[3];copy=out/'source';(copy/'service').mkdir(parents=True)
shutil.copytree(repo/'service/inference',copy/'service/inference',ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
app=copy/'service/inference/app.py';original=app.read_text();broken=original.replace("return error(400,'invalid_request')","return error(200,'invalid_request')")
assert broken!=original
rows=[]
for stage,body,want in [('defect',broken,False),('restored',original,True)]:
    app.write_text(body)
    for cache in copy.rglob('__pycache__'):shutil.rmtree(cache)
    with (out/(stage+'.log')).open('w') as log:
        result=subprocess.run([sys.executable,'-m','pytest','service/inference/tests/test_api.py','-k','invalid_request','-q','--junitxml='+str(out/(stage+'.xml'))],cwd=copy,stdout=log,stderr=subprocess.STDOUT,timeout=30)
    rows.append({'stage':stage,'exit_code':result.returncode,'source_sha256':hashlib.sha256(body.encode()).hexdigest()})
    assert (result.returncode==0)==want,rows
(out/'defective-app.py').write_text(broken);(out/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
