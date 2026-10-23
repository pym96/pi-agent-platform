"""Required unittest gate: native success alone does not exclude skips/zero tests."""
import argparse,json,sys,unittest
from pathlib import Path
REQUIRED={
 'test_measurements.MeasurementEvidenceTests.test_settled_call_must_match_runtime_result',
 'test_measurements.MeasurementEvidenceTests.test_first_content_requires_raw_content_frame',
 'test_measurements.MeasurementEvidenceTests.test_frame_cannot_occur_after_settled',
 'test_measurements.MeasurementEvidenceTests.test_failure_cannot_disappear_from_denominator',
 'test_measurements.MeasurementEvidenceTests.test_cpu_fixture_cannot_be_relabelled_gpu',
}
def flatten(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from flatten(item)
        else:yield item.id()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent),pattern='test_measurements.py')
    names=set(flatten(suite));result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'missing_required':sorted(REQUIRED-names),'collected':sorted(names)}
    summary['success']=result.wasSuccessful() and result.testsRun>0 and not summary['skipped'] and not summary['missing_required']
    Path(a.out).write_text(json.dumps(summary,indent=2));return 0 if summary['success'] else 1
if __name__=='__main__':raise SystemExit(main())
