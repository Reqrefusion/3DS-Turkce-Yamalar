#!/usr/bin/env python3
"""v3: v2 Turkish glyph synthesis + mandatory sorted Scan-CMAP pairs.
Original NintendoWare FFNT method-2 CMAP lists are sorted by Unicode codepoint.
v2 preserved size by reusing sparse slots but did not restore that ordering.
"""
from pathlib import Path
import sys,struct,json
# import v2 from same directory when packaged; fallback dev path
try:
    from bffnt_patch_tr_v2 import patch_font as patch_font_v2, parse
except ImportError:
    sys.path.insert(0,'/mnt/data/v131x/Araclar/Font')
    from bffnt_patch_tr_v2 import patch_font as patch_font_v2, parse

def sort_scan_cmaps(data: bytes):
    info=parse(data); out=bytearray(data); e=info['e']
    finf=struct.unpack_from(e+'4sI4B2H4B3I',data,20); pos=finf[-1]-8
    sections=changed=0
    while pos:
        magic,size,start,end,method,res,nxt=struct.unpack_from(e+'4sI4HI',data,pos)
        if magic!=b'CMAP': raise ValueError('CMAP bekleniyordu')
        if method==2:
            sections += 1; q=pos+20; cnt=struct.unpack_from(e+'H',data,q)[0]; q+=2
            pairs=[struct.unpack_from(e+'HH',data,q+j*4) for j in range(cnt)]
            ordered=sorted(pairs,key=lambda p:p[0])
            if pairs!=ordered:
                changed += 1
                for j,(cp,idx) in enumerate(ordered): struct.pack_into(e+'HH',out,q+j*4,cp,idx)
        pos=nxt-8 if nxt else 0
    return bytes(out), sections, changed

def patch_font(data: bytes):
    patched,report=patch_font_v2(data)
    patched,sections,reordered=sort_scan_cmaps(patched)
    report=dict(report); report['scan_sections']=sections; report['scan_sections_reordered']=reordered
    # final invariant
    check,_,again=sort_scan_cmaps(patched)
    if again: raise RuntimeError('CMAP scan sırası normalize edilemedi')
    return patched,report

if __name__=='__main__':
    src,dst=sys.argv[1:3]; p,r=patch_font(Path(src).read_bytes()); Path(dst).write_bytes(p); print(json.dumps(r,ensure_ascii=False,indent=2))
