"""Required-entry plugin: native xfail/XPASS are not completed passing evidence."""
import json,os
from pathlib import Path
reports=[]
def pytest_runtest_logreport(report):
    if hasattr(report,'wasxfail'):reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'reason':str(report.wasxfail)})
def pytest_sessionfinish(session,exitstatus):
    target=os.environ.get('REQUIRED_PYTEST_RECEIPT')
    if target:Path(target).write_text(json.dumps({'xfail_reports':reports},indent=2))
    if reports:session.exitstatus=1
