#!/usr/bin/env python3
import argparse, struct
from pathlib import Path

TR = 'ÇçĞğİıÖöŞşÜü'

def parse_cmap(path):
    b=Path(path).read_bytes()
    if b[:4] not in (b'FFNT',b'FFNU',b'CFNT',b'CFNU'):
        raise ValueError('BFFNT/BCFNT magic bulunamadı')
    e='<' if b[4:6]==b'\xff\xfe' else '>'
    # This tool targets the FFNT layout used by the supplied Sushi Striker fonts.
    if len(b) < 52:
        raise ValueError('Dosya çok küçük')
    finf=struct.unpack_from(e+'4sI4B2H4B3I', b, 20)
    cmap_pos=finf[-1]-8
    mapping={}
    seen=set()
    while cmap_pos and cmap_pos not in seen:
        seen.add(cmap_pos)
        magic,size,start,end,method,res,nextoff=struct.unpack_from(e+'4sI4HI',b,cmap_pos)
        if magic != b'CMAP':
            raise ValueError(f'CMAP bekleniyordu: 0x{cmap_pos:X}')
        data=cmap_pos+20
        if method==0:
            idxoff=struct.unpack_from(e+'H',b,data)[0]
            for cp in range(start,end+1): mapping[cp]=cp-start+idxoff
        elif method==1:
            count=end-start+1
            vals=struct.unpack_from(e+f'{count}H',b,data)
            for i,v in enumerate(vals):
                if v != 0xFFFF: mapping[start+i]=v
        elif method==2:
            count=struct.unpack_from(e+'H',b,data)[0]
            p=data+2
            for _ in range(count):
                cp,idx=struct.unpack_from(e+'2H',b,p); p+=4; mapping[cp]=idx
        cmap_pos=nextoff-8 if nextoff else 0
    return mapping

def main():
    ap=argparse.ArgumentParser(description='Sushi Striker BFFNT Türkçe karakter CMAP kontrolü')
    ap.add_argument('font')
    args=ap.parse_args()
    m=parse_cmap(args.font)
    print(Path(args.font).name)
    print(f'Toplam CMAP karakteri: {len(m)}')
    missing=[]
    for ch in TR:
        ok=ord(ch) in m
        print(f'{ch} U+{ord(ch):04X}: '+(f'VAR (glyph {m[ord(ch)]})' if ok else 'YOK'))
        if not ok: missing.append(ch)
    print('Eksik:', ''.join(missing) if missing else 'yok')

if __name__=='__main__': main()
