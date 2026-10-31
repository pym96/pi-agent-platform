"""Seal producer receipts once; publish this digest outside the receipt tree."""
import argparse,hashlib,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--receipt-out',required=True);a=p.parse_args()
    root=Path(a.root).resolve();out=Path(a.receipt_out).resolve()
    if not root.is_dir() or out.is_relative_to(root) or (root/'manifest.json').exists():p.error('new manifest, existing root and external receipt required')
    paths=sorted(root.rglob('*'))
    if any(x.is_symlink() for x in paths):p.error('cannot seal symlinks')
    manifest={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths if f.is_file()}
    if not manifest:p.error('empty receipts')
    raw=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();(root/'manifest.json').write_bytes(raw)
    receipt={'manifest_sha256':hashlib.sha256(raw).hexdigest(),'files':len(manifest),'input':str(root),'note':'producer seal; pin this digest in Handoff before independent recomputation'}
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
