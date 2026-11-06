#!/usr/bin/env python3
from pathlib import Path
import argparse,struct,hashlib,json
W16=0x15B630; W8=0x1B8288
HOOK_SITE=0x65D00; CAVE=0x65DD0; STORE_SITE=0x65D04
DOTLESS_I_IDX=0x49; DOTTED_I_IDX=0x45
MAP=[('Ç','C',0x4C),('Ğ','G',0x42),('İ','I',0x45),('Ö','O',0x46),('Ş','S',0x4D),('Ü','U',0x4B),
     ('ç','c',0x5A),('ğ','g',0x40),('ı','i',0x49),('ö','o',0x4A),('ş','s',0x5B),('ü','u',0x59)]
GEOM={'Ç':9,'Ğ':9,'İ':5,'Ö':9,'Ş':9,'Ü':8,'ç':8,'ğ':9,'ı':6,'ö':8,'ş':8,'ü':8}
def base_idx(ch): return (0x8A+ord(ch)-65-0x80) if 'A'<=ch<='Z' else (0xA4+ord(ch)-97-0x80)
def arm_b(src,dst):
 d=dst-(src+8)
 if d%4: raise ValueError('unaligned branch')
 imm=d//4
 if not -(1<<23)<=imm<(1<<23): raise ValueError('branch out of range')
 return 0xEA000000|(imm&0xFFFFFF)
def w16(b,i):return struct.unpack_from('<H',b,W16+i*2)[0]
def w8(b,i):return b[W8+i]
def patch(src:bytes,shift=2):
 if len(src)<0x1ED000:raise ValueError('code.bin kısa/compressed görünüyor')
 b=bytearray(src); rows=[]
 for tr,base,idx in MAP:
  bi=base_idx(base);d16=max(w16(src,bi),GEOM[tr]);d8=max(w8(src,bi),GEOM[tr])
  struct.pack_into('<H',b,W16+idx*2,d16);b[W8+idx]=d8
  rows.append({'tr':tr,'base':base,'idx':idx,'w16':d16,'w8':d8})
 # Safe v27 inline hook, same executable page as proven v26.
 # Only normalized 0x45 (İ) or 0x49 (ı) shift left; cursor/advance remains unchanged.
 # Return to the original STRH at 0x65D04 so we fit entirely before the live literal at 0x65DEC.
 struct.pack_into('<I',b,HOOK_SITE,arm_b(HOOK_SITE,CAVE))
 body=[
  0xE1D502B4,                # ldrh r0,[r5,#36]
  0xE1D511B4,                # ldrh r1,[r5,#20]
  0xE3510045,                # cmp r1,#0x45 (İ)
  0x13510049,                # cmpne r1,#0x49 (ı)
  0x02400000|shift,          # subeq r0,r0,#shift
  arm_b(CAVE+20,STORE_SITE), # b original strh at 0x65D04
  0xE320F000,                # nop; 0x65DEC live literal untouched
 ]
 for i,v in enumerate(body):struct.pack_into('<I',b,CAVE+4*i,v)
 return bytes(b),rows

def main():
 ap=argparse.ArgumentParser(description='Ace Attorney Trilogy TR v27 code.bin patcher: İ/ı same origin shift')
 ap.add_argument('input');ap.add_argument('output');ap.add_argument('--shift',type=int,default=2,choices=(1,2,3))
 a=ap.parse_args();src=Path(a.input).read_bytes();out,rows=patch(src,a.shift);Path(a.output).write_bytes(out)
 print(json.dumps({'shift_left_px':a.shift,'indices':{'İ':DOTTED_I_IDX,'ı':DOTLESS_I_IDX},'rows':rows,'sha256':hashlib.sha256(out).hexdigest()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
