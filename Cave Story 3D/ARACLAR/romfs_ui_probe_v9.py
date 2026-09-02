#!/usr/bin/env python3
"""Search a supplied ROMFS for UI strings that users still see at runtime."""
from pathlib import Path
import argparse
TERMS=['Start Game','START GAME','Game Start','LOADING','Loading','Start Point','First Cave']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('romfs',nargs='?',default='/mnt/data/v9_work/orig');a=ap.parse_args();root=Path(a.romfs)
 for term in TERMS:
  hits=[]
  probes=[('ASCII',term.encode('ascii')),('UTF16LE',term.encode('utf-16le'))]
  for p in root.rglob('*'):
   if not p.is_file():continue
   try:b=p.read_bytes()
   except:continue
   for enc,q in probes:
    n=b.count(q)
    if n:hits.append((str(p.relative_to(root)),enc,n))
  print(term,'hits=',hits)
if __name__=='__main__':main()
