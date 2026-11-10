"""Foreground #13 exact-ID guard. No scheduling; Master GO required."""
import argparse,time
from pathlib import Path
from watch_monitor import run_monitor

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',required=True);p.add_argument('--sha',required=True);p.add_argument('--deadline',required=True,type=float);p.add_argument('--root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    assert a.project in ('pi-qwen13-b','pi-qwen13-r') and len(a.sha)==40 and time.time()<a.deadline<=time.time()+900
    root=Path(a.root).resolve();assert str(root).startswith('/media/usv012/pjx/pi-agent-platform/experiments/13-qwen-load-20261107/')
    run_monitor(a.project,a.sha,a.deadline,root,a.out)
if __name__=='__main__':main()
