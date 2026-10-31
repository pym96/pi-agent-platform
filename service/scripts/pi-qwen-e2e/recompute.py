"""Authoritative offline recomputation requires an external SHA256 manifest anchor."""
import argparse,importlib.util,json,sys
from pathlib import Path
from analyze import analyze
# Reuse the accepted NG1.2 integrity module unchanged.
spec=importlib.util.spec_from_file_location('pi_ng12_integrity',Path(__file__).parents[1]/'nginx-entry/measurement.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--expected-manifest-sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.out).resolve()
    if out.is_relative_to(root):p.error('output must be outside sealed inputs')
    try:
        integrity=module.verify_manifest(root,a.expected_manifest_sha256)
        summary=analyze(root);summary.update(integrity,integrity_verified=True)
    except (AssertionError,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'integrity_verified':False,'error':str(error)}),file=sys.stderr);return 1
    out.write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));return 0
if __name__=='__main__':raise SystemExit(main())
