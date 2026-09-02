#!/usr/bin/env python3
"""Cave Story 3D embedded UI-text texture localizer.

Edits text baked into textbox/caret/minimap sprite sheets while preserving
original dimensions and, for .pbm files, the original BMP bit depth/palette.
"""
from pathlib import Path
from PIL import Image
import struct, argparse, shutil

# Compact 5x7 uppercase bitmap font.  All strings used below are uppercase to
# keep the tiny sprite atlas readable and deterministic.
FONT = {
' ': ["000","000","000","000","000","000","000"],
'A':["01110","10001","10001","11111","10001","10001","10001"],
'B':["11110","10001","10001","11110","10001","10001","11110"],
'C':["01111","10000","10000","10000","10000","10000","01111"],
'Ç':["01111","10000","10000","10000","10000","10000","01111","00100"],
'D':["11110","10001","10001","10001","10001","10001","11110"],
'E':["11111","10000","10000","11110","10000","10000","11111"],
'F':["11111","10000","10000","11110","10000","10000","10000"],
'G':["01111","10000","10000","10111","10001","10001","01111"],
'Ğ':["01010","00100","01111","10000","10111","10001","01111"],
'H':["10001","10001","10001","11111","10001","10001","10001"],
'I':["11111","00100","00100","00100","00100","00100","11111"],
'İ':["00100","00000","11111","00100","00100","00100","11111"],
'J':["00111","00010","00010","00010","10010","10010","01100"],
'K':["10001","10010","10100","11000","10100","10010","10001"],
'L':["10000","10000","10000","10000","10000","10000","11111"],
'M':["10001","11011","10101","10101","10001","10001","10001"],
'N':["10001","11001","10101","10011","10001","10001","10001"],
'O':["01110","10001","10001","10001","10001","10001","01110"],
'Ö':["01010","00000","01110","10001","10001","10001","01110"],
'P':["11110","10001","10001","11110","10000","10000","10000"],
'R':["11110","10001","10001","11110","10100","10010","10001"],
'S':["01111","10000","10000","01110","00001","00001","11110"],
'Ş':["01111","10000","10000","01110","00001","00001","11110","00100"],
'T':["11111","00100","00100","00100","00100","00100","00100"],
'U':["10001","10001","10001","10001","10001","10001","01110"],
'Ü':["01010","00000","10001","10001","10001","10001","01110"],
'V':["10001","10001","10001","10001","10001","01010","00100"],
'X':["10001","10001","01010","00100","01010","10001","10001"],
'Y':["10001","10001","01010","00100","00100","00100","00100"],
'Z':["11111","00001","00010","00100","01000","10000","11111"],
'0':["01110","10001","10011","10101","11001","10001","01110"],
'1':["00100","01100","00100","00100","00100","00100","01110"],
'2':["01110","10001","00001","00010","00100","01000","11111"],
'F':["11111","10000","10000","11110","10000","10000","10000"],
':':["000","010","010","000","010","010","000"],
'.':["000","000","000","000","000","011","011"],
'/':["00001","00010","00100","01000","10000","00000","00000"],
'!':["00100","00100","00100","00100","00100","00000","00100"],
'+':["00000","00100","00100","11111","00100","00100","00000"],
'-':["00000","00000","00000","11111","00000","00000","00000"],
}


def glyph_width(ch):
    return max(len(r) for r in FONT[ch])

def text_width(text, spacing=1):
    if not text: return 0
    return sum(glyph_width(c)+spacing for c in text)-spacing

def draw_text(setpx, text, x, y, color, spacing=1):
    cx=x
    for ch in text:
        if ch not in FONT: raise KeyError(f"Eksik glif: {ch!r}")
        pat=FONT[ch]
        for yy,row in enumerate(pat):
            for xx,v in enumerate(row):
                if v=='1': setpx(cx+xx,y+yy,color)
        cx += glyph_width(ch)+spacing
    return cx-x-spacing

def draw_center(setpx,text,x0,x1,y,color,spacing=1):
    w=text_width(text,spacing)
    draw_text(setpx,text,x0+(x1-x0-w)//2,y,color,spacing)


def read_indexed_bmp(path):
    raw=bytearray(Path(path).read_bytes())
    if raw[:2] != b'BM': raise ValueError(f'BMP değil: {path}')
    off=struct.unpack_from('<I',raw,10)[0]
    w,h=struct.unpack_from('<ii',raw,18)
    bpp=struct.unpack_from('<H',raw,28)[0]
    if bpp not in (1,4): raise ValueError(f'Desteklenmeyen indexed BMP bpp={bpp}: {path}')
    H=abs(h); rowbytes=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        sy=H-1-y if h>0 else y
        row=raw[off+sy*rowbytes:off+(sy+1)*rowbytes]
        if bpp==4:
            for x in range(w): pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
        else:
            for x in range(w): pix[y][x]=(row[x//8]>>(7-x%8))&1
    return [raw,off,w,h,bpp,rowbytes,pix]

def write_indexed_bmp(path,info,pix):
    raw,off,w,h,bpp,rowbytes,_=info; H=abs(h)
    for y in range(H):
        dy=H-1-y if h>0 else y; row=bytearray(rowbytes)
        if bpp==4:
            for x,v in enumerate(pix[y]):
                if x%2==0: row[x//2]|=(v&15)<<4
                else: row[x//2]|=v&15
        else:
            for x,v in enumerate(pix[y]): row[x//8]|=(v&1)<<(7-x%8)
        raw[off+dy*rowbytes:off+(dy+1)*rowbytes]=row
    Path(path).write_bytes(raw)


def clear_rect_rgba(im,box,fill=(0,0,0,0)):
    x0,y0,x1,y1=box
    for y in range(y0,y1):
        for x in range(x0,x1): im.putpixel((x,y),fill)

def clear_rect_idx(pix,box,fill=0):
    x0,y0,x1,y1=box
    for y in range(y0,y1):
        for x in range(x0,x1): pix[y][x]=fill


def textbox_tga(src,dst):
    im=Image.open(src/'textbox.tga').convert('RGBA')
    WHITE=(247,247,234,255); YELLOW=(255,203,0,255); BLUE=(180,205,245,255)
    # transparent-label areas
    for box in [(0,47,25,58),(80,47,145,58),(80,58,145,69),(48,70,72,79),(80,70,112,81),(80,81,94,90),(123,70,146,91)]:
        clear_rect_rgba(im,box)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'ŞEF',1,49,WHITE,1) # compact; 30 px
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SİLAH',81,49,WHITE,1)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'ENVANTER',81,59,WHITE,1)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'EN İYİ',81,70,WHITE,1)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'MAKS',49,71,YELLOW,0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'PUAN',81,71,WHITE,1)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SV',81,82,WHITE,1)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'HAVA',123,71,BLUE,0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'HAVA',123,82,BLUE,0)
    # yes/no button: retain red plate, paint over only interior with sampled red.
    red=im.getpixel((180,62))
    clear_rect_rgba(im,(163,56,225,70),red)
    draw_center(lambda x,y,c: im.putpixel((x,y),c),'EVET / HAYIR',164,224,58,WHITE,0)
    im.save(dst/'textbox.tga',format='TGA')


def textbox_pbm(src,dst):
    info=read_indexed_bmp(src/'textbox.pbm'); pix=info[-1]
    # palette indices: 0 black/transparent-equivalent, 6 white, 11 yellow, 5 pale blue, 8 red
    for box in [(0,47,25,58),(80,47,145,69),(48,70,72,79),(80,70,112,91),(120,70,145,91),(154,78,226,91),(0,130,244,143)]:
        clear_rect_idx(pix,box,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'ŞEF',1,49,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SİLAH',81,49,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'EŞYA',81,59,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'HRT',84,69,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'MAKS',49,71,11,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'PUAN',81,71,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SV',81,82,6,1)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'HAVA',121,71,5,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'HAVA',121,82,5,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SÜRÜM',155,79,6,1)
    # button interior is palette 8; keep decorative frame untouched.
    clear_rect_idx(pix,(163,56,226,70),8)
    draw_center(lambda x,y,c: pix[y].__setitem__(x,c),'EVET / HAYIR',164,225,58,6,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'ESC:ÇIK / F1:DEVAM / F2:SIFIRLA',1,132,6,1)
    write_indexed_bmp(dst/'textbox.pbm',info,pix)


def caret_tga(src,dst):
    im=Image.open(src/'caret.tga').convert('RGBA')
    # fixed text cells, deliberately stop before adjacent effect sprites
    for box in [(0,3,55,17),(0,19,55,30),(0,99,56,110),(0,117,56,128),(107,97,142,110),(107,112,142,124),(0,143,108,155)]:
        clear_rect_rgba(im,box)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SEVİYE+',0,5,(254,254,254,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SEVİYE+',0,20,(100,114,207,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SEVİYE-',0,100,(255,62,37,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'SEVİYE-',0,118,(90,0,0,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'BOŞ!',108,99,(255,226,41,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'BOŞ!',108,113,(255,62,37,255),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'ZIPLAMA TUŞUNA BAS!',0,144,(254,254,254,255),0)
    im.save(dst/'caret.tga',format='TGA')


def caret_pbm(src,dst):
    info=read_indexed_bmp(src/'caret.pbm'); pix=info[-1]
    for box in [(0,3,55,17),(0,19,55,30),(0,99,56,110),(0,117,56,128),(107,97,142,110),(107,112,142,124),(0,143,108,155)]: clear_rect_idx(pix,box,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SEVİYE+',0,5,5,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SEVİYE+',0,20,8,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SEVİYE-',0,100,12,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'SEVİYE-',0,118,14,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'BOŞ!',108,99,10,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'BOŞ!',108,113,12,0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'ZIPLAMA TUŞUNA BAS!',0,144,5,0)
    write_indexed_bmp(dst/'caret.pbm',info,pix)


def minimapframe(src,dst):
    im=Image.open(src/'minimapframe.pbm').convert('RGB')
    # black label area only; preserve the three colored selector bars at x209-217.
    for y in range(18,38):
        for x in range(220,250): im.putpixel((x,y),(0,0,0))
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'HRT',221,20,(255,225,40),0)
    draw_text(lambda x,y,c: im.putpixel((x,y),c),'ENV',221,29,(70,255,45),0)
    im.save(dst/'minimapframe.pbm',format='BMP')



def pixel_signature(src,dst):
    """Localize the tiny 2004.12 Japanese Pixel development-room signature."""
    info=read_indexed_bmp(src/'pixel.bmp'); pix=info[-1]
    # Original uses palette index 1 for the pale-yellow lettering on black.
    # Keep the original date glyphs, replace only the Japanese label.
    clear_rect_idx(pix,(50,0,160,16),0)
    draw_text(lambda x,y,c: pix[y].__setitem__(x,c),'GELİŞTİRME PIXEL',58,4,1,0)
    write_indexed_bmp(dst/'pixel.bmp',info,pix)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source',nargs='?',default='/mnt/data/cs3d_work/patch/data')
    ap.add_argument('dest',nargs='?',default='/mnt/data/cs3d_work/final/000400000004D200/romfs/data')
    a=ap.parse_args(); src=Path(a.source); dst=Path(a.dest); dst.mkdir(parents=True,exist_ok=True)
    textbox_tga(src,dst); textbox_pbm(src,dst); caret_tga(src,dst); caret_pbm(src,dst); minimapframe(src,dst); pixel_signature(src,dst)
    print('UI texture localization complete: textbox x2, caret x2, minimapframe x1, pixel signature x1')
if __name__=='__main__': main()
