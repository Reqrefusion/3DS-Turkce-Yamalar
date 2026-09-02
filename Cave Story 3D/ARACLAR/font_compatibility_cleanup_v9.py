#!/usr/bin/env python3
"""Replace unsupported CP1254 smart punctuation in visible SJS text.
0x80-0x9F is absent from the game's BMFont. head.sjs is excluded because it contains binary/technical payload bytes.
"""
from pathlib import Path
import argparse
MAP={0x92:0x27,0x93:0x22,0x94:0x22}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--data',default=str(Path(__file__).resolve().parents[1]/'000400000004D200/romfs/data')); a=ap.parse_args()
 root=Path(a.data); changed=0; repl=0
 for p in root.rglob('*.sjs'):
  if p.name in {'head.sjs','credit.sjs'}: continue
  b=p.read_bytes(); out=bytearray(b); n=0
  for i,x in enumerate(out):
   if x in MAP: out[i]=MAP[x]; n+=1
  if n:
   p.write_bytes(out); changed+=1; repl+=n; print(f'{p.relative_to(root)}\t{n}')
 print(f'changed_files={changed} replacements={repl}')
if __name__=='__main__': main()
