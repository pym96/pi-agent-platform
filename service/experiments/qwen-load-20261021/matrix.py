"""Serial preregistered matrix; open rates are frozen after all closed points."""
import argparse,datetime,json,pathlib,subprocess,sys,time
from fractions import Fraction


def derive_rates(count):
    result=[]
    for factor in [Fraction(1,2),Fraction(1),Fraction(3,2)]:
        value=Fraction(count,45)*factor*1000
        units=(2*value.numerator+value.denominator)//(2*value.denominator)
        result.append(max(10,units)/1000)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True)
    p.add_argument('--code-sha',required=True);p.add_argument('--url',default='http://127.0.0.1:18171')
    a=p.parse_args();out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=False)
    summaries=[]
    def point(mode,load,rep):
        if datetime.datetime.now(datetime.timezone.utc)>=datetime.datetime(2026,10,21,9,18,tzinfo=datetime.timezone.utc):
            raise RuntimeError('No new point: Builder deadline guard09:18Z (<=105s point)')
        ident=f'{mode}-{load:g}-r{rep}'
        cmd=[sys.executable,str(pathlib.Path(__file__).with_name('measure.py')),
             '--config',a.config,'--output',str(out/ident),'--code-sha',a.code_sha,
             '--mode',mode,'--load',str(load),'--rep',str(rep),'--run',ident,'--url',a.url]
        subprocess.run(cmd,check=True,timeout=110)
        summary=json.loads((out/ident/'summary.json').read_text());summaries.append(summary)
        (out/'progress.json').write_text(json.dumps(summaries,indent=2))
        time.sleep(2)  # explicit inter-run pause, never overlapping run launch windows/drains
    for load in [1,2,4,8,16,32]:
        for rep in [1,2]:point('closed',load,rep)
    count=max(s['window_success'] for s in summaries if s['valid'])
    rb=count/45
    rates=derive_rates(count) if rb>0 else []
    (out/'open-rates-lock.json').write_text(json.dumps(dict(reference_rb=rb,rates=rates,
        max_window_completed_count=count,formula='max(0.01,half-up((max_window_completed_count/45)*factor,3)), factors0.5,1.0,1.5',
        frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2))
    for load in rates:
        for rep in [1,2]:point('open',load,rep)


if __name__=='__main__':main()
