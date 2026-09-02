#!/usr/bin/env python3
"""Generate localized pixel-style title/loading/splash assets.
Preserves the game's unusual .pbm-as-BMP bit depth by editing the original BMP bytes.
"""
from pathlib import Path
from PIL import Image
import struct
SRC=Path('/mnt/data/cs3d_work/patch/data')
DST=Path('/mnt/data/cs3d_work/final/000400000004D200/romfs/data')

FONT={
'A':["01110","10001","10001","11111","10001","10001","10001"],
'B':["11110","10001","10001","11110","10001","10001","11110"],
'C':["01111","10000","10000","10000","10000","10000","01111"],
'Ç':["01111","10000","10000","10000","10000","10000","01111","00100"],
'D':["11110","10001","10001","10001","10001","10001","11110"],
'E':["11111","10000","10000","11110","10000","10000","11111"],
'G':["01111","10000","10000","10111","10001","10001","01111"],
'İ':["00100","00000","11111","00100","00100","00100","00100","11111"],
'I':["11111","00100","00100","00100","00100","00100","11111"],
'K':["10001","10010","10100","11000","10100","10010","10001"],
'L':["10000","10000","10000","10000","10000","10000","11111"],
'N':["10001","11001","10101","10011","10001","10001","10001"],
'O':["01110","10001","10001","10001","10001","10001","01110"],
'P':["11110","10001","10001","11110","10000","10000","10000"],
'R':["11110","10001","10001","11110","10100","10010","10001"],
'S':["01111","10000","10000","01110","00001","00001","11110"],
'T':["11111","00100","00100","00100","00100","00100","00100"],
'U':["10001","10001","10001","10001","10001","10001","01110"],
'Ü':["01010","00000","10001","10001","10001","10001","10001","01110"],
'Y':["10001","10001","01010","00100","00100","00100","00100"],
'X':["10001","01010","00100","00100","00100","01010","10001"],
' ':["000","000","000","000","000","000","000"],
'-':["00000","00000","00000","11111","00000","00000","00000"],
}

def draw_pixel_text(setpx, text, x, y, scale=1, spacing=1):
    cx=x
    for ch in text:
        pat=FONT.get(ch)
        if pat is None: raise KeyError(f'no glyph {ch!r}')
        w=max(len(r) for r in pat)
        for yy,row in enumerate(pat):
            for xx,v in enumerate(row):
                if v=='1':
                    for sy in range(scale):
                        for sx in range(scale): setpx(cx+xx*scale+sx,y+yy*scale+sy)
        cx += w*scale + spacing*scale
    return cx-x-spacing*scale

def read_bmp_indices(path):
    raw=bytearray(path.read_bytes())
    off=struct.unpack_from('<I',raw,10)[0]; w=struct.unpack_from('<i',raw,18)[0]; h=struct.unpack_from('<i',raw,22)[0]
    bpp=struct.unpack_from('<H',raw,28)[0]; H=abs(h); rowbytes=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        srcy=H-1-y if h>0 else y; row=raw[off+srcy*rowbytes:off+(srcy+1)*rowbytes]
        if bpp==4:
            for x in range(w): pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
        elif bpp==1:
            for x in range(w): pix[y][x]=(row[x//8]>>(7-(x%8)))&1
        else: raise ValueError(bpp)
    return raw,off,w,h,bpp,rowbytes,pix

def write_bmp_indices(path, info, pix):
    raw,off,w,h,bpp,rowbytes,_=info; H=abs(h)
    for y in range(H):
        dsty=H-1-y if h>0 else y; row=bytearray(rowbytes)
        if bpp==4:
            for x,v in enumerate(pix[y]):
                if x%2==0: row[x//2]|=(v&15)<<4
                else: row[x//2]|=v&15
        else:
            for x,v in enumerate(pix[y]): row[x//8]|=(v&1)<<(7-(x%8))
        raw[off+dsty*rowbytes:off+(dsty+1)*rowbytes]=row
    path.write_bytes(raw)

def make_title():
    # RGBA TGA: clear only the original New/Load pixels and draw compact pixel labels.
    im=Image.open(SRC/'title.tga').convert('RGBA')
    for y in range(2,30):
        for x in range(145,177): im.putpixel((x,y),(0,0,0,0))
    col=(247,247,234,255)
    draw_pixel_text(lambda x,y: im.putpixel((x,y),col),'YENİ',146,4,1,1)
    draw_pixel_text(lambda x,y: im.putpixel((x,y),col),'YÜKLE',146,18,1,1)
    im.save(DST/'title.tga',format='TGA')

    info=read_bmp_indices(SRC/'title.pbm'); pix=info[-1]
    for y in range(2,30):
        for x in range(145,177): pix[y][x]=0
    draw_pixel_text(lambda x,y: pix[y].__setitem__(x,4),'YENİ',146,4,1,1)
    draw_pixel_text(lambda x,y: pix[y].__setitem__(x,4),'YÜKLE',146,18,1,1)
    write_bmp_indices(DST/'title.pbm',info,pix)

def make_loading():
    # Convert the already localized v2 rendering back into the original 1-bpp BMP container.
    current=Image.open(Path('/mnt/data/cs3d_work/out/000400000004D200/romfs/data/loading.pbm')).convert('RGB')
    info=read_bmp_indices(SRC/'loading.pbm'); pix=info[-1]
    for y in range(info[3] if info[3]>0 else -info[3]):
        for x in range(info[2]):
            r,g,b=current.getpixel((x,y)); pix[y][x]=1 if (r+g+b)>80 else 0
    write_bmp_indices(DST/'loading.pbm',info,pix)

def make_splash(srcname, main):
    im=Image.new('RGB',(400,240),(0,0,0))
    white=(255,255,255)
    # 3x main line, 2x status line; centered around the original vertical positions.
    def width(text,scale): return sum(max(len(r) for r in FONT[c])*scale+scale for c in text)-scale
    w=width(main,3); draw_pixel_text(lambda x,y: im.putpixel((x,y),white),main,(400-w)//2,96,3,1)
    sub='-GEÇİCİ-'; w2=width(sub,2); draw_pixel_text(lambda x,y: im.putpixel((x,y),white),sub,(400-w2)//2,137,2,1)
    im.save(DST/srcname,format='TGA')

def main():
    make_title(); make_loading()
    make_splash('splash_legal_01.tga','YASAL BİLGİLER')
    make_splash('splash_pixel_01.tga','PİXEL STÜDYOSU')
    print('localized title/loading/splash assets written')
if __name__=='__main__': main()
