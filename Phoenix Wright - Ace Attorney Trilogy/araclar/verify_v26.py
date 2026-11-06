#!/usr/bin/env python3
from pathlib import Path
import argparse,struct,hashlib,json
ap=argparse.ArgumentParser();ap.add_argument('codebin');a=ap.parse_args();b=Path(a.codebin).read_bytes()
def u32(o):return struct.unpack_from('<I',b,o)[0]
assert u32(0x65D00)==0xEA000032
body=[u32(0x65DD0+i*4) for i in range(7)]
assert body[0:3]==[0xE1D502B4,0xE1D511B4,0xE3510049]
assert body[4]==0xE1C40EB6 and body[5]==0xEAFFFFC7
shift=body[3]&0xff
assert body[3]==(0x02400000|shift) and shift in (1,2,3)
assert struct.unpack_from('<H',b,0x15B630+0x49*2)[0]==6
assert b[0x1B8288+0x49]==6
print(json.dumps({'ok':True,'sha256':hashlib.sha256(b).hexdigest(),'dotless_i_shift_left_px':shift,'w16':6,'w8':6,'hook_site':'0x65D00','cave':'0x65DD0'},indent=2))
