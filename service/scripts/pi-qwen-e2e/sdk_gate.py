"""Run actual Node tests and require complete, non-skipped SDK JUnit events."""
import argparse,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
REQUIRED={
 'actual SDK explicit-stream wire preserves smaller output budget',
 'actual Pi SDK must not complete missing upstream usage',
 'actual Pi SDK successful stream has verified raw usage and mapped budget',
 'content reaches client before complete upstream terminal',
 *('actual Pi SDK rejects '+name for name in ['missing DONE','inconsistent usage','partial then error','empty content','missing terminal','usage beyond budget','null usage','damaged intermediate usage','data after DONE'])}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('files',nargs='*');a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 command=['node','--test','--test-reporter=junit',*(a.files or ['service/pi/tests/budget.test.mjs','service/pi/tests/wire.test.mjs'])]
 with (out/'junit.xml').open('w') as f:r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.PIPE,text=True,timeout=120)
 (out/'stderr.log').write_text(r.stderr)
 summary={'command':command,'exit_code':r.returncode,'success':False}
 try:
  rows=list(ET.parse(out/'junit.xml').getroot().iter('testcase'));ids=[x.get('name') for x in rows]
  summary.update(tests=len(rows),collected=ids,missing_required=sorted(REQUIRED-set(ids)),failures=sum(len(list(x.iter('failure')))+len(list(x.iter('error'))) for x in rows),skipped=sum(len(list(x.iter('skipped'))) for x in rows))
  summary['success']=r.returncode==0 and bool(rows) and len(ids)==len(set(ids)) and not any(summary[k] for k in ['failures','skipped','missing_required'])
 except (ET.ParseError,OSError,TypeError):summary['reason']='unusable_junit'
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary));return 0 if summary['success'] else 1
if __name__=='__main__':raise SystemExit(main())
