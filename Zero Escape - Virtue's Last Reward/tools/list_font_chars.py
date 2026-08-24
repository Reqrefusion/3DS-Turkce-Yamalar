#!/usr/bin/env python3
from pathlib import Path
import struct, sys

def parse_map(data):
    _,_,nlen=struct.unpack_from('<III',data,0); o=12+nlen
    slen=struct.unpack_from('<I',data,o)[0]; o+=4+slen
    count=struct.unpack_from('<I',data,o)[0]; o+=4
    out=[]
    for _ in range(count):
        cp,idx=struct.unpack_from('<II',data,o); o+=8; out.append((idx,cp))
    return sorted(out)

def main():
    if len(sys.argv)<2:
        print('Kullanım: python list_font_chars.py FONT.dat [cikti.txt]'); return 2
    p=Path(sys.argv[1]); rows=parse_map(p.read_bytes())
    lines=[]
    for idx,cp in rows:
        try: ch=chr(cp)
        except ValueError: ch='�'
        shown={'\n':'\\n','\r':'\\r','\t':'\\t'}.get(ch,ch)
        lines.append(f'{idx:5}  U+{cp:04X}  {shown}')
    text='\n'.join(lines)+'\n'
    if len(sys.argv)>=3: Path(sys.argv[2]).write_text(text,encoding='utf-8')
    else: print(text,end='')
    return 0
if __name__=='__main__': raise SystemExit(main())
