#!/usr/bin/env python3
"""Public sealed-raw recomputation; external manifest SHA256 is mandatory."""
import argparse,json,sys
from pathlib import Path
from measurement import IntegrityError,report

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--expected-manifest-sha256',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.out).resolve()
    if out.is_relative_to(root):p.error('output must be outside the sealed input tree')
    try:data=report(root,expected_manifest_sha256=a.expected_manifest_sha256)
    except IntegrityError as e:
        print(json.dumps({'integrity_verified':False,'phase':'integrity','error':str(e)}),file=sys.stderr);return 1
    except (OSError,ValueError,KeyError) as e:
        print(json.dumps({'integrity_verified':False,'phase':'statistics','error':str(e)}),file=sys.stderr);return 1
    out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'integrity_verified':True,'manifest_sha256':data['manifest_sha256'],'files_verified':data['files_verified'],'out':str(out)}));return 0
if __name__=='__main__':raise SystemExit(main())
