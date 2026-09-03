#!/usr/bin/env python3
from pathlib import Path
import sys,struct
sys.path.insert(0,'/mnt/data/v131x/Araclar/Font')
from lz11_codec import decompress
from bffnt_patch_tr_v2 import parse

def compress_literals(data: bytes) -> bytes:
    n=len(data)
    if n<0x1000000: out=bytearray([0x11,n&255,(n>>8)&255,(n>>16)&255])
    else: out=bytearray([0x11,0,0,0])+n.to_bytes(4,'little')
    pos=0
    while pos<n:
        out.append(0) # 8 literal tokens
        chunk=data[pos:pos+8]; out.extend(chunk); pos+=len(chunk)
    return bytes(out)

def sort_scan_cmaps(font: bytes):
    info=parse(font); out=bytearray(font); e=info['e']; finf=struct.unpack_from(e+'4sI4B2H4B3I',font,20); pos=finf[-1]-8
    sections=changed=0
    while pos:
        magic,size,start,end,method,res,nxt=struct.unpack_from(e+'4sI4HI',font,pos)
        if magic!=b'CMAP': raise ValueError('CMAP expected')
        if method==2:
            sections+=1; q=pos+20; cnt=struct.unpack_from(e+'H',font,q)[0]; q+=2
            pairs=[struct.unpack_from(e+'HH',font,q+j*4) for j in range(cnt)]; sp=sorted(pairs,key=lambda x:x[0])
            if pairs!=sp:
                changed+=1
                for j,(cp,idx) in enumerate(sp):struct.pack_into(e+'HH',out,q+j*4,cp,idx)
        pos=nxt-8 if nxt else 0
    return bytes(out),sections,changed

def patch_carc(src,dst):
    raw=Path(src).read_bytes(); dec=bytearray(decompress(raw)); e='<' if dec[6:8]==b'\xff\xfe' else '>'
    hdr=struct.unpack_from(e+'H',dec,4)[0]; hsz,nodes,m=struct.unpack_from(e+'HHI',dec,hdr+4); no=hdr+hsz; do=struct.unpack_from(e+'I',dec,12)[0]
    fonts=sections=changed=0
    for i in range(nodes):
        h,a,st,en=struct.unpack_from(e+'IIII',dec,no+i*16);A,B=do+st,do+en;dat=bytes(dec[A:B])
        if dat[:4]!=b'FFNT':continue
        fonts+=1;new,s,c=sort_scan_cmaps(dat);sections+=s;changed+=c
        if c:dec[A:B]=new
    comp=compress_literals(bytes(dec));
    if decompress(comp)!=bytes(dec):raise RuntimeError('roundtrip')
    dst=Path(dst);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(comp)
    return fonts,sections,changed,len(raw),len(comp)
