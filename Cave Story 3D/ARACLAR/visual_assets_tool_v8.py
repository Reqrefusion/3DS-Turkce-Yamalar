#!/usr/bin/env python3
"""V8 final visual pass: remove remaining foreign subtitle text from title assets.
Rewrites title.tga and title.pbm in-place while preserving file format/bit depth.
"""
from pathlib import Path
from PIL import Image
import struct
ROOT=Path(__file__).resolve().parents[1]/'000400000004D200'/'romfs'/'data'
FONT={
'A':["01110","10001","10001","11111","10001","10001","10001"],
'D':["11110","10001","10001","10001","10001","10001","11110"],
'E':["11111","10000","10000","11110","10000","10000","11111"],
'G':["01111","10000","10000","10111","10001","10001","01111"],
'Ğ':["01110","10001","10000","10111","10001","10001","01110","00110","00100"],
'H':["10001","10001","10001","11111","10001","10001","10001"],
'İ':["00100","00000","11111","00100","00100","00100","00100","11111"],
'I':["11111","00100","00100","00100","00100","00100","11111"],
'K':["10001","10010","10100","11000","10100","10010","10001"],
'M':["10001","11011","10101","10101","10001","10001","10001"],
'N':["10001","11001","10101","10011","10001","10001","10001"],
'R':["11110","10001","10001","11110","10100","10010","10001"],
'S':["01111","10000","10000","01110","00001","00001","11110"],
'T':["11111","00100","00100","00100","00100","00100","00100"],
'Y':["10001","10001","01010","00100","00100","00100","00100"],
' ':["000","000","000","000","000","000","000"],
}
def draw_pixel_text(setpx, text, x, y, fg, scale=1, spacing=1):
    cx=x
    for ch in text:
        pat=FONT[ch]
        w=max(len(r) for r in pat)
        for yy,row in enumerate(pat):
            for xx,v in enumerate(row):
                if v=='1':
                    for sy in range(scale):
                        for sx in range(scale): setpx(cx+xx*scale+sx,y+yy*scale+sy,fg)
        cx += w*scale + spacing*scale
def read_bmp_indices(path):
    raw=bytearray(path.read_bytes())
    off=struct.unpack_from('<I',raw,10)[0]; w=struct.unpack_from('<i',raw,18)[0]; h=struct.unpack_from('<i',raw,22)[0]
    bpp=struct.unpack_from('<H',raw,28)[0]; H=abs(h); rowbytes=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        srcy=H-1-y if h>0 else y; row=raw[off+srcy*rowbytes:off+(srcy+1)*rowbytes]
        for x in range(w): pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
    return raw,off,w,h,bpp,rowbytes,pix
def write_bmp_indices(path, info, pix):
    raw,off,w,h,bpp,rowbytes,_=info; H=abs(h)
    for y in range(H):
        dsty=H-1-y if h>0 else y; row=bytearray(rowbytes)
        for x,v in enumerate(pix[y]):
            if x%2==0: row[x//2]|=(v&15)<<4
            else: row[x//2]|=v&15
        raw[off+dsty*rowbytes:off+(dsty+1)*rowbytes]=row
    path.write_bytes(raw)
def apply():
    tga=ROOT/'title.tga'; im=Image.open(tga).convert('RGBA')
    for x0,y0,x1,y1 in [(4,20,170,35),(4,37,180,48),(228,0,320,34)]:
        for y in range(y0,y1):
            for x in range(x0,x1): im.putpixel((x,y),(0,0,0,0))
    col=(247,247,234,255)
    draw_pixel_text(lambda x,y,c: im.putpixel((x,y),c),'MAĞARA HİKAYESİ',10,22,col)
    draw_pixel_text(lambda x,y,c: im.putpixel((x,y),c),'MAĞARA',246,4,col)
    draw_pixel_text(lambda x,y,c: im.putpixel((x,y),c),'HİKAYESİ',237,18,col)
    draw_pixel_text(lambda x,y,c: im.putpixel((x,y),c),'MAGARA HIKAYESI',8,39,col)
    im.save(tga, format='TGA')
    pbm=ROOT/'title.pbm'; info=read_bmp_indices(pbm); pix=info[-1]
    for x0,y0,x1,y1 in [(4,20,170,35),(4,37,180,48),(228,0,320,34)]:
        for y in range(y0,y1):
            for x in range(x0,x1): pix[y][x]=0
    for txt,pos in [('MAĞARA HİKAYESİ',(10,22)),('MAĞARA',(246,4)),('HİKAYESİ',(237,18)),('MAGARA HIKAYESI',(8,39))]:
        draw_pixel_text(lambda x,y,c: pix[y].__setitem__(x,c),txt,pos[0],pos[1],4)
    write_bmp_indices(pbm, info, pix)
    print('title.tga/title.pbm V8 visual pass applied')
if __name__=='__main__':
    apply()
