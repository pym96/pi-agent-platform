"""Compute the absolute native time limit inside the container, before engine import."""
import argparse,json,math,os,pathlib,sys,time

def budget(deadline,now):
 if not math.isfinite(deadline):raise ValueError('nonfinite deadline')
 remaining=deadline-now-15
 if remaining<=0:raise ValueError('insufficient cleanup reserve')
 return remaining

def main():
 p=argparse.ArgumentParser();p.add_argument('--deadline',type=float,required=True);p.add_argument('--receipt',required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
 command=a.command[1:] if a.command[:1]==['--'] else a.command
 if not command:raise ValueError('empty native command')
 now=time.time();remaining=budget(a.deadline,now)
 pathlib.Path(a.receipt).write_text(json.dumps({'epoch':now,'absolute_deadline':a.deadline,'cleanup_reserve_s':15,'native_limit_s':remaining,'command':command},indent=2))
 # GNU timeout sends TERM to its process group, then KILL two seconds later.
 os.execvp('timeout',['timeout','--signal=TERM','--kill-after=2s',str(remaining)+'s',*command])

if __name__=='__main__':
 try:main()
 except Exception as e:print('Native deadline rejected: '+repr(e),file=sys.stderr);sys.exit(2)
