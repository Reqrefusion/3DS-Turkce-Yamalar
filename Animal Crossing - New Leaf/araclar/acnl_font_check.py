#!/usr/bin/env python3
from __future__ import annotations
import argparse, struct
from pathlib import Path

REQUIRED = "çÇğĞıİöÖşŞüÜ"

def parse_mapping(path: Path):
    b=path.read_bytes()
    if b[:4] not in (b'CFNT', b'CFNU'):
        raise ValueError('CFNT/CFNU başlığı yok')
    if struct.unpack_from('<H',b,4)[0] != 0xFEFF:
        raise ValueError('Bu araç little-endian BCFNT v3 bekliyor')
    ver=struct.unpack_from('<I',b,8)[0]
    if ver != 0x03000000:
        raise ValueError(f'Desteklenmeyen BCFNT sürümü: 0x{ver:08X}')
    hs=struct.unpack_from('<H',b,6)[0]
    if b[hs:hs+4] != b'FINF': raise ValueError('FINF yok')
    cmap_off=struct.unpack_from('<I',b,hs+0x18)[0]
    mapping={}; seen=set(); off=cmap_off
    while off and off not in seen:
        seen.add(off); pos=off-8
        if b[pos:pos+4]!=b'CMAP': raise ValueError(f'CMAP yok @0x{pos:X}')
        sec_size=struct.unpack_from('<I',b,pos+4)[0]
        start,end,typ,_=struct.unpack_from('<4H',b,pos+8)
        nxt=struct.unpack_from('<I',b,pos+0x10)[0]
        dp=pos+0x14
        if typ==0:
            idx=struct.unpack_from('<H',b,dp)[0]
            for code in range(start,end+1): mapping[code]=idx+(code-start)
        elif typ==1:
            count=end-start+1
            for i in range(count):
                idx=struct.unpack_from('<H',b,dp+2*i)[0]
                if idx != 0xFFFF: mapping[start+i]=idx
        elif typ==2:
            count=struct.unpack_from('<H',b,dp)[0]
            for i in range(count):
                code,idx=struct.unpack_from('<2H',b,dp+2+4*i)
                mapping[code]=idx
        else: raise ValueError(f'Bilinmeyen CMAP yöntemi {typ}')
        off=nxt
    return mapping

def main():
    ap=argparse.ArgumentParser(description='ACNL BCFNT Türkçe glyph kontrolü')
    ap.add_argument('font',type=Path)
    args=ap.parse_args()
    m=parse_mapping(args.font)
    missing=[ch for ch in REQUIRED if ord(ch) not in m]
    print(f'Font: {args.font}')
    print(f'CMAP karakter sayısı: {len(m)}')
    for ch in REQUIRED:
        print(f'U+{ord(ch):04X} {ch}: ' + (f'glyph #{m[ord(ch)]}' if ord(ch) in m else 'YOK'))
    if missing:
        print('Eksik:', ''.join(missing))
        return 2
    print('OK: Türkçe için gereken temel Latin glyphlerinin tamamı mevcut.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
