#!/usr/bin/env python3
from pathlib import Path
import struct
root=Path(__file__).resolve().parents[1]
code=(root/'000400000004D200/exefs/code.bin').read_bytes()
checks={0x675b8:0x001e3260,0x675bc:0x001e3228}
bad=0
for off,expected in checks.items():
 got=int.from_bytes(code[off:off+4],'little')
 ok=got==expected; bad+=not ok
 print(hex(off),hex(got),'expected',hex(expected),'OK' if ok else 'HATA')
raise SystemExit(1 if bad else 0)
