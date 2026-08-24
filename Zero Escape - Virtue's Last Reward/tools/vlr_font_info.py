#!/usr/bin/env python3
from pathlib import Path
import argparse, hashlib, struct

TR='çğıöşüÇĞİÖŞÜ'

def read_header_map(path):
    b=Path(path).read_bytes()
    if len(b)<24: raise ValueError('Dosya çok kısa')
    magic,total,nlen=struct.unpack_from('<III',b,0)
    o=12
    if o+nlen>len(b): raise ValueError('İsim alanı bozuk')
    name=b[o:o+nlen].decode('utf-8','replace'); o+=nlen
    slen=struct.unpack_from('<I',b,o)[0]; o+=4
    style=b[o:o+slen].decode('utf-8','replace'); o+=slen
    count=struct.unpack_from('<I',b,o)[0]; o+=4
    entries=[]
    for _ in range(count):
        if o+8>len(b): raise ValueError('Karakter haritası yarım')
        cp,idx=struct.unpack_from('<II',b,o); o+=8; entries.append((cp,idx))
    return b,magic,total,name,style,entries,o

def main():
    ap=argparse.ArgumentParser(description='VLR .dat font başlık/karakter tablosu inceleyici')
    ap.add_argument('font')
    a=ap.parse_args()
    b,magic,total,name,style,e,post=read_header_map(a.font)
    cps=[cp for cp,_ in e]
    print('Dosya       :',Path(a.font).name)
    print('Boyut       :',len(b))
    print('SHA-256     :',hashlib.sha256(b).hexdigest())
    print('Magic       :',hex(magic))
    print('Total       :',total)
    print('Font adı    :',name)
    print('Stil        :',style)
    print('Map count   :',len(e))
    print('Index aralık:',min(i for _,i in e),'-',max(i for _,i in e))
    print('Map sonu    :',post)
    print('Duplicate CP:',len(cps)-len(set(cps)))
    print('Türkçe      :',' '.join(f'{c}={"VAR" if ord(c) in cps else "YOK"}' for c in TR))

if __name__=='__main__': main()
