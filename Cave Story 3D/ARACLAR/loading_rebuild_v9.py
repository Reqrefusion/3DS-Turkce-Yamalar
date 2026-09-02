#!/usr/bin/env python3
"""Rebuild loading.pbm from the original 1-bpp BMP container with a compact Turkish label."""
from pathlib import Path
import argparse,struct
from PIL import Image
FONT={
'Y':["1001","1001","0110","0010","0010","0010","0010"],
'Ü':["1001","0000","1001","1001","1001","1001","0110"],
'K':["1001","1010","1100","1100","1010","1001","1001"],
'L':["1000","1000","1000","1000","1000","1000","1111"],
'E':["1111","1000","1000","1110","1000","1000","1111"],
'N':["1001","1101","1101","1011","1011","1001","1001"],
'İ':["0010","1111","0110","0110","0110","0110","1111"],
'O':["0110","1001","1001","1001","1001","1001","0110"],
'R':["1110","1001","1001","1110","1010","1001","1001"],
}
def read(path):
 raw=bytearray(path.read_bytes()); off=struct.unpack_from('<I',raw,10)[0];w=struct.unpack_from('<i',raw,18)[0];h=struct.unpack_from('<i',raw,22)[0];bpp=struct.unpack_from('<H',raw,28)[0];H=abs(h);rb=((w*bpp+31)//32)*4
 return raw,off,w,h,bpp,H,rb
def main():
 ap=argparse.ArgumentParser();base=Path(__file__).resolve().parents[1]
 ap.add_argument('--original',default='/mnt/data/v9_work/orig/data/loading.pbm'); ap.add_argument('--target',default=str(base/'000400000004D200/romfs/data/loading.pbm')); ap.add_argument('--preview',default=str(base/'ONIZLEMELER/loading_v9_preview.png'));a=ap.parse_args()
 raw,off,w,h,bpp,H,rb=read(Path(a.original)); assert (w,H,bpp)==(64,8,1)
 # clear bitmap rows only; preserve headers and palette byte-for-byte
 for yy in range(H):
  dsty=H-1-yy if h>0 else yy
  raw[off+dsty*rb:off+(dsty+1)*rb]=bytes(rb)
 text='YÜKLENİYOR'; total=len(text)*4+(len(text)-1); x0=(w-total)//2
 for ci,ch in enumerate(text):
  x=x0+ci*5
  for y,row in enumerate(FONT[ch]):
   for xx,v in enumerate(row):
    if v=='1':
     dsty=H-1-y if h>0 else y; px=x+xx; pos=off+dsty*rb+px//8; raw[pos]|=1<<(7-(px%8))
 target=Path(a.target);target.write_bytes(raw)
 im=Image.open(target).convert('RGB'); Path(a.preview).parent.mkdir(parents=True,exist_ok=True);im.resize((640,80),Image.Resampling.NEAREST).save(a.preview)
 print(f'loading rebuilt: {w}x{H} {bpp}-bpp bytes={len(raw)}')
if __name__=='__main__':main()
