"""Public pytest entry; required skips/empty collection cannot produce a success summary."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET

def summarize(path,exit_code):
    try:
        suites=list(ET.parse(path).getroot().iter('testsuite'))
        counts={key:sum(int(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
        ok=exit_code==0 and counts['tests']>0 and not any(counts[k] for k in ['failures','errors','skipped'])
        return {'success':ok,'exit_code':exit_code,**counts}
    except (OSError,ET.ParseError,ValueError):return {'success':False,'exit_code':exit_code,'reason':'unusable_junit'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out).resolve();out.mkdir(parents=False,exist_ok=False)
    repo=Path(__file__).resolve().parents[3]
    env=dict(os.environ,INFERENCE_EVIDENCE=str(out/'http'),REQUIRED_PYTEST_RECEIPT=str(out/'required-pytest.json'));start=time.monotonic()
    command=[sys.executable,'-m','pytest','-p','service.inference.scripts.required_pytest','service/inference/tests','-q','--junitxml='+str(out/'junit.xml')]
    with (out/'pytest.log').open('w') as log:
        result=subprocess.run(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    summary=summarize(out/'junit.xml',result.returncode)
    receipt=json.loads((out/'required-pytest.json').read_text()) if (out/'required-pytest.json').exists() else None
    summary['xfail_reports']=receipt['xfail_reports'] if receipt is not None else None
    summary['success']=summary['success'] and receipt is not None and not receipt['xfail_reports']
    summary.update(duration_seconds=time.monotonic()-start,command=command,python=sys.version)
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
    return 0 if summary['success'] else 1
if __name__=='__main__':raise SystemExit(main())
