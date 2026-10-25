#!/usr/bin/env python3
"""Required unittest CLI: machine result counts, never success-text matching."""
import argparse,json,sys,unittest
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--start-dir',required=True);p.add_argument('--pattern',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    suite=unittest.defaultTestLoader.discover(a.start_dir,pattern=a.pattern)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'tests':result.testsRun,'skipped':len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses)}
    summary['success']=summary['tests']>0 and result.wasSuccessful() and not any(summary[k] for k in ['skipped','expected_failures','unexpected_successes'])
    Path(a.out).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));return 0 if summary['success'] else 1
if __name__=='__main__':raise SystemExit(main())
