#!/usr/bin/env python3
"""Quick discovery scanner for extracted Gravity Falls RomFS/ExeFS."""
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument("root");a=ap.parse_args();root=Path(a.root)
    print("Direct localisation files:")
    for p in root.rglob("*.loc8"): print(" ",p)
    print("\nIPK archives and font/localisation-looking entries:")
    tool=Path(__file__).with_name("ipk_tool.py")
    for p in root.rglob("*.ipk"):
        print(f"\n[{p}]")
        r=subprocess.run([sys.executable,str(tool),"list",str(p)],capture_output=True,text=True)
        if r.returncode:
            print("  parse failed:",r.stderr.strip() or r.stdout.strip());continue
        for line in r.stdout.splitlines():
            low=line.lower()
            if any(k in low for k in ("font",".bcfnt",".tfn","localis",".lng")): print(line)
if __name__=="__main__":main()
