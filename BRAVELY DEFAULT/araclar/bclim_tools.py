from __future__ import annotations
import struct, math
from PIL import Image

TILE_ORDER=[0,1,8,9,2,3,10,11,16,17,24,25,18,19,26,27,4,5,12,13,6,7,14,15,20,21,28,29,22,23,30,31,32,33,40,41,34,35,42,43,48,49,56,57,50,51,58,59,36,37,44,45,38,39,46,47,52,53,60,61,54,55,62,63]
ETC1_LUT=((2,8,-2,-8),(5,17,-5,-17),(9,29,-9,-29),(13,42,-13,-42),(18,60,-18,-60),(24,80,-24,-80),(33,106,-33,-106),(47,183,-47,-183))

def _next_pow2(x): return 1 if x<=1 else 1 << (x-1).bit_length()

def parse_bclim(b:bytes):
    if len(b)<0x28 or b[-0x28:-0x24] not in (b'CLIM',b'FLIM'):
        raise ValueError('not BCLIM/BFLIM')
    o=len(b)-0x28
    magic=b[o:o+4]
    endian=struct.unpack_from('<H',b,o+4)[0]
    header_len=struct.unpack_from('<I',b,o+6)[0]
    file_len=struct.unpack_from('<I',b,o+0xc)[0]
    imag_magic=b[o+0x14:o+0x18]
    imag_len=struct.unpack_from('<I',b,o+0x18)[0]
    width,height=struct.unpack_from('<HH',b,o+0x1c)
    fmt_raw=struct.unpack_from('<I',b,o+0x20)[0]
    length=struct.unpack_from('<I',b,o+0x24)[0]
    fmt=((fmt_raw>>16)&0xf) if magic==b'FLIM' else fmt_raw
    data_start=len(b)-0x28-length
    return {'magic':magic,'endian':endian,'header_len':header_len,'file_len':file_len,'imag_magic':imag_magic,'imag_len':imag_len,'width':width,'height':height,'format':fmt,'format_raw':fmt_raw,'length':length,'data_start':data_start,'footer_offset':o}

def _signed3(v):
    v &= 7
    return v-8 if v&4 else v

def _clamp(v): return 0 if v<0 else 255 if v>255 else int(v)

def _etc_pixel(r,g,b,x,y,bottom,table):
    index=x*4+y
    msb=(bottom << 1) & 0xffffffff
    if index < 8:
        sel=((bottom >> (index+24)) & 1) + ((msb >> (index+8)) & 2)
    else:
        sel=((bottom >> (index+8)) & 1) + ((msb >> (index-8)) & 2)
    mod=ETC1_LUT[table][sel]
    return (_clamp(r+mod),_clamp(g+mod),_clamp(b+mod),255)

def _etc1_decode_block(data8:bytes):
    top,bottom=struct.unpack_from('<II',data8,0)
    flip=bool(top & 0x01000000)
    diff=bool(top & 0x02000000)
    if diff:
        r1=top&0xf8; g1=(top&0xf800)>>8; b1=(top&0xf80000)>>16
        r2=((r1>>3)+_signed3(top&7))
        g2=((g1>>3)+_signed3((top>>8)&7))
        b2=((b1>>3)+_signed3((top>>16)&7))
        r1|=r1>>5; g1|=g1>>5; b1|=b1>>5
        r2=((r2<<3)|(r2>>2))&0xff; g2=((g2<<3)|(g2>>2))&0xff; b2=((b2<<3)|(b2>>2))&0xff
    else:
        r1=top&0xf0; g1=(top&0xf000)>>8; b1=(top&0xf00000)>>16
        r2=(top&0xf)<<4; g2=(top&0xf00)>>4; b2=(top&0xf0000)>>12
        r1|=r1>>4; g1|=g1>>4; b1|=b1>>4
        r2|=r2>>4; g2|=g2>>4; b2|=b2>>4
    t1=(top>>29)&7; t2=(top>>26)&7
    out=[(0,0,0,255)]*16
    if not flip:
        for y in range(4):
            for x in range(2):
                out[y*4+x]=_etc_pixel(r1,g1,b1,x,y,bottom,t1)
                out[y*4+x+2]=_etc_pixel(r2,g2,b2,x+2,y,bottom,t2)
    else:
        for y in range(2):
            for x in range(4):
                out[y*4+x]=_etc_pixel(r1,g1,b1,x,y,bottom,t1)
                out[(y+2)*4+x]=_etc_pixel(r2,g2,b2,x,y+2,bottom,t2)
    return out

def _etc1_scramble(width,height):
    n=(width//4)*(height//4)
    out=[0]*n
    base_acc=0; row_acc=0; base_num=0; row_num=0
    for tile in range(n):
        if tile % (width//4)==0 and tile>0:
            if row_acc<1:
                row_acc+=1; row_num+=2; base_num=row_num
            else:
                row_acc=0; base_num-=2; row_num=base_num
        out[tile]=base_num
        if base_acc<1:
            base_acc+=1; base_num+=1
        else:
            base_acc=0; base_num+=3
    return out

def _decode_etc(data,width,height,alpha):
    # Exact port of Ohana3DS-Rebirth's ETC1 stage, converted to RGBA.
    decoded=bytearray(width*height*4); off=0
    for by in range(height//4):
        for bx in range(width//4):
            if alpha:
                alpha_block=data[off:off+8]
                color_block=data[off+8:off+16][::-1]
                off+=16
            else:
                alpha_block=b'\xff'*8
                color_block=data[off:off+8][::-1]
                off+=8
            colors=_etc1_decode_block(color_block)
            toggle=False; ao=0
            for tx in range(4):
                for ty in range(4):
                    idx=ty*4+tx
                    r,g,b,_=colors[idx]
                    if alpha:
                        a4=((alpha_block[ao]>>4)&0xf) if toggle else (alpha_block[ao]&0xf)
                        if toggle: ao+=1
                        toggle=not toggle
                        a=a4*17
                    else: a=255
                    pos=((by*4+ty)*width+(bx*4+tx))*4
                    decoded[pos:pos+4]=bytes((r,g,b,a))
    order=_etc1_scramble(width,height)
    out=bytearray(width*height*4); i=0
    for ty in range(height//4):
        for tx in range(width//4):
            TX=order[i]%(width//4); TY=order[i]//(width//4); i+=1
            for y in range(4):
                for x in range(4):
                    sp=((TY*4+y)*width+(TX*4+x))*4
                    dp=((ty*4+y)*width+(tx*4+x))*4
                    out[dp:dp+4]=decoded[sp:sp+4]
    return out

def decode_bclim(b:bytes)->Image.Image:
    m=parse_bclim(b); w=m['width']; h=m['height']; W=_next_pow2(w); H=_next_pow2(h); fmt=m['format']
    data=b[m['data_start']:m['data_start']+m['length']]
    if fmt in (10,11):
        rgba=_decode_etc(data,W,H,fmt==11)
        return Image.frombytes('RGBA',(W,H),bytes(rgba)).crop((0,0,w,h))
    out=bytearray(W*H*4); off=0; toggle=False
    for tY in range(H//8):
        for tX in range(W//8):
            for pixel in range(64):
                x=TILE_ORDER[pixel]%8; y=TILE_ORDER[pixel]//8
                pos=((tY*8+y)*W+(tX*8+x))*4
                if fmt==9: # rgba8 stored A,R/G/B-like according to Ohana output channels; treat byte1,2,3 as RGB
                    a=data[off]; r,g,bl=data[off+1:off+4]; off+=4
                elif fmt==6: r,g,bl=data[off:off+3]; a=255; off+=3
                elif fmt==7:
                    v=data[off]|(data[off+1]<<8); off+=2
                    r=((v>>1)&31); g=((v>>6)&31); bl=((v>>11)&31); a=255 if v&1 else 0
                    r=(r<<3)|(r>>2); g=(g<<3)|(g>>2); bl=(bl<<3)|(bl>>2)
                elif fmt==5:
                    v=data[off]|(data[off+1]<<8); off+=2
                    r=v&31; g=(v>>5)&63; bl=(v>>11)&31; a=255
                    r=(r<<3)|(r>>2); g=(g<<2)|(g>>4); bl=(bl<<3)|(bl>>2)
                elif fmt==8:
                    v=data[off]|(data[off+1]<<8); off+=2
                    r=(v>>4)&15; g=(v>>8)&15; bl=(v>>12)&15; a=v&15
                    r*=17; g*=17; bl*=17; a*=17
                elif fmt in (3,4):
                    l=data[off]; a=data[off+1]; off+=2; r=g=bl=l
                elif fmt==0:
                    l=data[off]; off+=1; r=g=bl=l; a=255
                elif fmt==1:
                    a=data[off]; off+=1; r=g=bl=255
                elif fmt==2:
                    v=data[off]; off+=1; l=v&15; a=(v>>4)&15; r=g=bl=l*17; a*=17
                elif fmt==12:
                    v=data[off//2] if False else 0
                    # Use shared nibble stream below
                    nib=(data[off] & 0xf) if not toggle else ((data[off]>>4)&0xf)
                    if toggle: off+=1
                    toggle=not toggle; r=g=bl=nib*17; a=255
                elif fmt==13:
                    nib=(data[off] & 0xf) if not toggle else ((data[off]>>4)&0xf)
                    if toggle: off+=1
                    toggle=not toggle; r=g=bl=255; a=nib*17
                else: raise NotImplementedError(fmt)
                out[pos:pos+4]=bytes((r,g,bl,a))
    return Image.frombytes('RGBA',(W,H),bytes(out)).crop((0,0,w,h))

def encode_rgba8_bclim(img:Image.Image, template:bytes)->bytes:
    m=parse_bclim(template); w,h=m['width'],m['height']; W=_next_pow2(w); H=_next_pow2(h)
    if img.size!=(w,h): raise ValueError((img.size,(w,h)))
    canvas=Image.new('RGBA',(W,H),(0,0,0,0)); canvas.paste(img,(0,0))
    raw=canvas.tobytes(); out=bytearray()
    for tY in range(H//8):
        for tX in range(W//8):
            for pixel in range(64):
                x=TILE_ORDER[pixel]%8; y=TILE_ORDER[pixel]//8
                pos=((tY*8+y)*W+(tX*8+x))*4
                r,g,b,a=raw[pos:pos+4]
                out += bytes((a,r,g,b))
    footer=bytearray(template[-0x28:])
    # CLIM format field direct; preserve other header values.
    if footer[:4]==b'FLIM':
        old=struct.unpack_from('<I',footer,0x20)[0]
        struct.pack_into('<I',footer,0x20,(old&0x0000ffff)|(9<<16))
    else: struct.pack_into('<I',footer,0x20,9)
    struct.pack_into('<I',footer,0x24,len(out))
    total=len(out)+0x28
    struct.pack_into('<I',footer,0x0c,total)
    return bytes(out)+bytes(footer)
