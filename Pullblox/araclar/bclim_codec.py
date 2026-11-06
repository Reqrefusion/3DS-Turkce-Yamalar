#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import struct, math
from PIL import Image

def round8(n): return (n+7)//8*8
def nlpo2(n):
    if n<=1:return 1
    return 1<<(n-1).bit_length()
def morton_d2xy(d):
    x=d; y=x>>1
    x &= 0x55555555; y &= 0x55555555
    x |= x>>1; y |= y>>1
    x &= 0x33333333; y &= 0x33333333
    x |= x>>2; y |= y>>2
    x &= 0x0f0f0f0f; y &= 0x0f0f0f0f
    x |= x>>4; y |= y>>4
    x &= 0x00ff00ff; y &= 0x00ff00ff
    x |= x>>8; y |= y>>8
    x &= 0x0000ffff; y &= 0x0000ffff
    return x,y

def parse_header(b:bytes):
    if len(b)<0x28 or b[-0x28:-0x24]!=b'CLIM': raise ValueError('not BCLIM')
    h=b[-0x28:]
    width,height=struct.unpack_from('<HH',h,0x1c)
    fmt=struct.unpack_from('<I',h,0x20)[0]
    dlen=struct.unpack_from('<I',h,0x24)[0]
    return width,height,fmt,dlen,h

def decode_color(v,fmt):
    if fmt==0: return (v,v,v,255)
    if fmt==1: return (255,255,255,v)
    if fmt==2:
        l=((v>>4)&15)*17; a=(v&15)*17; return (l,l,l,a)
    if fmt==3:
        l=(v>>8)&255; a=v&255; return (l,l,l,a)
    if fmt==4: return ((v>>8)&255,v&255,255,255)
    if fmt==5:
        r=((v>>11)&31)*255//31; g=((v>>5)&63)*255//63; bl=(v&31)*255//31; return (r,g,bl,255)
    if fmt==7:
        r=((v>>11)&31)*255//31; g=((v>>6)&31)*255//31; bl=((v>>1)&31)*255//31; a=255 if v&1 else 0; return (r,g,bl,a)
    if fmt==8:
        r=((v>>12)&15)*17; g=((v>>8)&15)*17; bl=((v>>4)&15)*17; a=(v&15)*17; return (r,g,bl,a)
    if fmt==9:
        r=(v>>24)&255; g=(v>>16)&255; bl=(v>>8)&255; a=v&255; return (r,g,bl,a)
    if fmt==12:
        l=(v&15)*17; return (l,l,l,255)
    if fmt==13:
        a=(v&15)*17; return (255,255,255,a)
    raise NotImplementedError(fmt)

def decode_bclim(b:bytes)->Image.Image:
    width,height,fmt,dlen,hdr=parse_header(b)
    if fmt in (10,11): raise NotImplementedError('ETC1/ETC1A4')
    w=nlpo2(round8(width)); h=nlpo2(round8(height))
    # Special RGBA8 can use non-power-of-two round8 storage.
    bpp={0:1,1:1,2:1,3:2,4:2,5:2,6:3,7:2,8:2,9:4,12:.5,13:.5}[fmt]
    expected=int(w*h*bpp)
    if fmt==9 and expected>dlen:
        w=round8(width); h=round8(height); expected=int(w*h*bpp)
    data=b[:dlen]
    if expected>dlen: raise ValueError(f'data too short expected {expected} got {dlen} {width}x{height} fmt{fmt}')
    img=Image.new('RGBA',(w,h),(0,0,0,0)); px=img.load(); pos=0; i=0; area=w*h
    while i<area:
        x,y=morton_d2xy(i%64); tile=i//64; p=max(1,round8(w)//8); x += (tile%p)*8; y += (tile//p)*8
        if fmt in (0,1,2): v=data[pos]; pos+=1; px[x,y]=decode_color(v,fmt); i+=1
        elif fmt in (3,4,5,7,8): v=struct.unpack_from('<H',data,pos)[0];pos+=2;px[x,y]=decode_color(v,fmt);i+=1
        elif fmt==6:
            bl,g,r=data[pos:pos+3];pos+=3;px[x,y]=(r,g,bl,255);i+=1
        elif fmt==9:
            v=struct.unpack_from('<I',data,pos)[0];pos+=4;px[x,y]=decode_color(v,fmt);i+=1
        elif fmt in (12,13):
            v=data[pos];pos+=1
            px[x,y]=decode_color(v&15,fmt); i+=1
            if i<area:
                x2,y2=morton_d2xy(i%64);tile2=i//64;x2+=(tile2%p)*8;y2+=(tile2//p)*8
                px[x2,y2]=decode_color(v>>4,fmt); i+=1
    return img.crop((0,0,width,height))

def encode_color(c,fmt):
    r,g,b,a=c
    if fmt==0: return int(round(.299*r+.587*g+.114*b))
    if fmt==1: return a
    if fmt==2:
        l=int(round((.299*r+.587*g+.114*b)/17)); return ((max(0,min(15,l))<<4)|(a//17))
    if fmt==3:
        l=int(round(.299*r+.587*g+.114*b)); return (l<<8)|a
    if fmt==4:return (r<<8)|g
    if fmt==5:return ((r*31//255)<<11)|((g*63//255)<<5)|(b*31//255)
    if fmt==7:return ((r*31//255)<<11)|((g*31//255)<<6)|((b*31//255)<<1)|(1 if a>=128 else 0)
    if fmt==8:return ((r//17)<<12)|((g//17)<<8)|((b//17)<<4)|(a//17)
    if fmt==9:return (r<<24)|(g<<16)|(b<<8)|a
    if fmt==12:
        return max(0,min(15,int(round((.299*r+.587*g+.114*b)/17))))
    if fmt==13:return a//17
    raise NotImplementedError(fmt)

def encode_bclim(img:Image.Image, template:bytes)->bytes:
    width,height,fmt,dlen,hdr=parse_header(template)
    if img.size!=(width,height): raise ValueError(f'image must stay {width}x{height}, got {img.size}')
    if fmt in (10,11): raise NotImplementedError('ETC1')
    w=nlpo2(round8(width)); h=nlpo2(round8(height))
    bpp={0:1,1:1,2:1,3:2,4:2,5:2,6:3,7:2,8:2,9:4,12:.5,13:.5}[fmt]
    if fmt==9 and int(w*h*bpp)>dlen: w=round8(width);h=round8(height)
    src=img.convert('RGBA'); sp=src.load(); out=bytearray(); area=w*h; i=0; p=max(1,round8(w)//8)
    def pix_at(i):
        x,y=morton_d2xy(i%64); tile=i//64; x+=(tile%p)*8;y+=(tile//p)*8
        return sp[x,y] if x<width and y<height else (0,86,86,0)
    while i<area:
        if fmt in (12,13):
            v1=encode_color(pix_at(i),fmt);i+=1; v2=encode_color(pix_at(i),fmt) if i<area else 0;i+=1; out.append((v2<<4)|v1)
        else:
            c=pix_at(i);i+=1; v=encode_color(c,fmt)
            if fmt in (0,1,2):out.append(v)
            elif fmt in (3,4,5,7,8):out += struct.pack('<H',v)
            elif fmt==6:
                r,g,b,a=c;out += bytes((b,g,r))
            elif fmt==9:out += struct.pack('<I',v)
    if len(out)>dlen: raise ValueError(f'encoded {len(out)} > template data {dlen}')
    out += template[len(out):dlen]  # preserve any tail padding exactly if any
    rebuilt=bytes(out)+template[dlen:]
    if len(rebuilt)!=len(template):raise AssertionError
    return rebuilt

def main():
 import argparse
 ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest='cmd',required=True)
 p=sp.add_parser('decode');p.add_argument('input');p.add_argument('output')
 p=sp.add_parser('encode');p.add_argument('png');p.add_argument('template');p.add_argument('output')
 a=ap.parse_args()
 if a.cmd=='decode':decode_bclim(Path(a.input).read_bytes()).save(a.output)
 else:Path(a.output).write_bytes(encode_bclim(Image.open(a.png),Path(a.template).read_bytes()))
if __name__=='__main__':main()
