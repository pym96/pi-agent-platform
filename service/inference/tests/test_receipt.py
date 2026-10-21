import pytest
from service.inference.scripts.run_tests import summarize
@pytest.mark.parametrize('attrs,exit_code,want',[
 ('tests="1" failures="0" errors="0" skipped="0"',0,True),
 ('tests="0"',0,False),('tests="1" skipped="1"',0,False),
 ('tests="1" failures="1"',1,False),('tests="1"',1,False)])
def test_receipt_rejects_missing_or_skipped_evidence(tmp_path,attrs,exit_code,want):
    path=tmp_path/'junit.xml';path.write_text('<testsuites><testsuite '+attrs+'/></testsuites>')
    assert summarize(path,exit_code)['success'] is want
