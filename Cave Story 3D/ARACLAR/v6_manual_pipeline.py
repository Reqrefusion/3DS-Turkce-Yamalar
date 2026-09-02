#!/usr/bin/env python3
"""Cave Story 3D TR v6 manuel kalite geçişini tek komutla uygular."""
from pathlib import Path
import argparse, subprocess, sys

def run(script,*args):
    cmd=[sys.executable,str(script),*map(str,args)]
    print('+',' '.join(cmd))
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('data_root',help='000400000004D200/romfs/data klasörü')
    a=ap.parse_args(); here=Path(__file__).resolve().parent; root=Path(a.data_root)
    run(here/'manual_review_v6.py',root)
    run(here/'manual_credits_review_v6.py',root)
    print('V6 manuel kalite geçişi tamamlandı.')
if __name__=='__main__': main()
