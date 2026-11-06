#!/usr/bin/env python3
from pathlib import Path
import argparse
PAT=b'\x5d\x00\x00\x01\x00'

def main():
    ap=argparse.ArgumentParser(description='VLR font içindeki LZMA1 özellik imzası adaylarını tarar')
    ap.add_argument('font');ap.add_argument('-o','--output');a=ap.parse_args()
    b=Path(a.font).read_bytes(); pos=[]; s=0
    while True:
        i=b.find(PAT,s)
        if i<0: break
        pos.append(i);s=i+1
    text='\n'.join(f'{n:4}: 0x{x:08X} ({x})' for n,x in enumerate(pos))+'\n'
    print(f'{Path(a.font).name}: {len(pos)} LZMA imza adayı')
    if a.output: Path(a.output).write_text(text,encoding='utf-8')
    else: print(text,end='')
if __name__=='__main__':main()
