from pathlib import Path
import struct, importlib.util
from PIL import Image
spec=importlib.util.spec_from_file_location('x','/mnt/data/xfsa_extract.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def parse_xi(path):
 b=Path(path).read_bytes()
 magic=b[:8]; assert magic.startswith(b'IMGC00')
 entryOff=struct.unpack_from('<h',b,8)[0]; fmt=b[10]; count=b[12]; bitDepth=b[13]; bpt=struct.unpack_from('<h',b,14)[0]; width,height=struct.unpack_from('<hh',b,16); imgOff,imgCnt=struct.unpack_from('<HH',b,24); dataOff=struct.unpack_from('<i',b,28)[0]
 vals=struct.unpack_from('<iiii',b,imgOff); tileOff,tileSize,dOff,dSize=vals
 tiles=m.level5_dec(b,dataOff+tileOff); data=m.level5_dec(b,dataOff+dOff)
 tileByteDepth=64*bitDepth//8
 entries=[struct.unpack_from('<h',tiles,i)[0] for i in range(0,len(tiles),2)]
 raw=bytearray(len(entries)*tileByteDepth)
 for i,e in enumerate(entries):
  if e<0: continue
  raw[i*tileByteDepth:(i+1)*tileByteDepth]=data[e*tileByteDepth:(e+1)*tileByteDepth]
 W=(width+7)&~7; H=(height+7)&~7
 assert len(raw)>=W*H*bitDepth//8,(len(raw),W,H)
 # unswizzle CTR: storage linear samples use Morton within each 8x8 tile, tiles raster order
 linear=bytearray(W*H*2)
 for p in range(W*H):
  tile=p//64; q=p%64
  xloc=((q>>1)&1) | (((q>>3)&1)<<1) | (((q>>5)&1)<<2)
  yloc=(q&1) | (((q>>2)&1)<<1) | (((q>>4)&1)<<2)
  tx=(tile%(W//8))*8; ty=(tile//(W//8))*8
  x=tx+xloc; y=ty+yloc
  linear[(y*W+x)*2:(y*W+x+1)*2]=raw[p*2:p*2+2]
 # Decode RGBA5551 assuming little endian bits R5 G5 B5 A1 in MSB->LSB? Try common 3DS: R bits 11-15 G6-10 B1-5 A0
 im=Image.new('RGBA',(W,H)); pix=im.load()
 for y in range(H):
  for x in range(W):
   v=struct.unpack_from('<H',linear,(y*W+x)*2)[0]
   r=((v>>11)&31)*255//31; g=((v>>6)&31)*255//31; bb=((v>>1)&31)*255//31; a=255 if (v&1) else 0
   pix[x,y]=(r,g,bb,a)
 return im.crop((0,0,width,height)), linear, (fmt,width,height,W,H,b,entries,data)

if __name__=='__main__':
 import sys
 for p in sys.argv[1:]:
  im,raw,meta=parse_xi(p); out=str(Path(p).with_suffix('.png')); im.save(out); print(out,im.size)
