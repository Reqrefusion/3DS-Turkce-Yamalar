#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, struct

def parse(p):
    b=Path(p).read_bytes(); _,_,n=struct.unpack_from('<III',b,0); o=12+n
    s=struct.unpack_from('<I',b,o)[0]; o+=4+s; c=struct.unpack_from('<I',b,o)[0]; o+=4
    m={}
    for _ in range(c): cp,idx=struct.unpack_from('<II',b,o);o+=8;m[cp]=idx
    return b,m

def show(cp):
    try: ch=chr(cp)
    except: ch='?'
    return f'U+{cp:04X} {repr(ch)}'

def main():
    ap=argparse.ArgumentParser(description='İki VLR fontunun karakter tablosu ve binary fark özeti')
    ap.add_argument('a');ap.add_argument('b');a=ap.parse_args()
    ba,ma=parse(a.a); bb,mb=parse(a.b)
    print('A',Path(a.a).name,len(ba),hashlib.sha256(ba).hexdigest())
    print('B',Path(a.b).name,len(bb),hashlib.sha256(bb).hexdigest())
    print('Boyut farkı:',len(bb)-len(ba))
    onlya=sorted(set(ma)-set(mb)); onlyb=sorted(set(mb)-set(ma))
    moved=sorted(cp for cp in set(ma)&set(mb) if ma[cp]!=mb[cp])
    print('\nSadece A:',len(onlya)); [print(' ',show(x),'idx',ma[x]) for x in onlya[:100]]
    print('\nSadece B:',len(onlyb)); [print(' ',show(x),'idx',mb[x]) for x in onlyb[:100]]
    print('\nIndex değişen ortak CP:',len(moved)); [print(' ',show(x),ma[x],'->',mb[x]) for x in moved[:100]]
    n=min(len(ba),len(bb)); positions=[i for i in range(n) if ba[i]!=bb[i]]
    print('\nİlk ortak bölümde farklı byte:',len(positions))
    if positions: print('İlk/son fark offset:',positions[0],positions[-1])

if __name__=='__main__':main()
