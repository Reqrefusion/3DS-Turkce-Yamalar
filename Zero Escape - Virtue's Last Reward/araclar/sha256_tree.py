#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib

def main():
    ap=argparse.ArgumentParser(description='Klasördeki tüm dosyalar için SHA-256 listesi')
    ap.add_argument('root');ap.add_argument('-o','--output');a=ap.parse_args();r=Path(a.root)
    rows=[]
    for p in sorted(x for x in r.rglob('*') if x.is_file()):
        h=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(f'{h}  {p.relative_to(r).as_posix()}')
    t='\n'.join(rows)+'\n'
    if a.output:Path(a.output).write_text(t,encoding='utf-8')
    else:print(t,end='')
if __name__=='__main__':main()
