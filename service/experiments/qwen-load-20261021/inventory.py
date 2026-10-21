"""SHA256 inventory; invoke inside the bounded CPU-only experiment container."""
import argparse,hashlib,json,pathlib


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base');p.add_argument('output');a=p.parse_args()
    base=pathlib.Path(a.base);out=pathlib.Path(a.output)
    rows=[dict(path=str(x.relative_to(base)),bytes=x.stat().st_size,sha256=digest(x))
          for x in sorted(base.rglob('*')) if x.is_file() and x.resolve()!=out.resolve() and '__pycache__' not in x.parts]
    out.write_text(json.dumps(rows,indent=2));print(json.dumps(dict(files=len(rows),bytes=sum(r['bytes'] for r in rows))))
