#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import struct, math
from PIL import Image

ETC_MODIFIERS=[[2,8],[5,17],[9,29],[13,42],[18,60],[24,80],[33,106],[47,183]]
# BFLIM format ids (CTR)
FMT_L8=0;FMT_A8=1;FMT_LA4=2;FMT_LA8=3;FMT_HILO8=4;FMT_RGB565=5;FMT_RGB8=6;FMT_RGBA5551=7;FMT_RGBA4=8;FMT_RGBA8=9;FMT_ETC1=10;FMT_ETC1A4=11;FMT_L4=12;FMT_A4=13


def npot(n:int)->int:
    return 1 if n<=1 else 1<<(n-1).bit_length()

def parse_header(b:bytes):
    if len(b)<0x28 or b[-0x28:-0x24]!=b'FLIM': raise ValueError('not BFLIM')
    footer=b[-0x28:]
    bom=footer[4:6]
    e='<' if bom==b'\xff\xfe' else '>' if bom==b'\xfe\xff' else None
    if not e: raise ValueError('bad BFLIM BOM')
    if footer[0x14:0x18]!=b'imag': raise ValueError('no imag section')
    # IMAG struct is magic,size,height,width,alignment,format,swizzle,data_size
    height,width,align=struct.unpack_from(e+'HHH',footer,0x1c)
    fmt=footer[0x22]; swizzle=footer[0x23]; dlen=struct.unpack_from(e+'I',footer,0x24)[0]
    return {'stored_width':width,'stored_height':height,'alignment':align,'format':fmt,'swizzle':swizzle,'data_len':dlen,'endian':e,'footer':footer}

def display_size(info):
    w,h=info['stored_width'],info['stored_height']
    return (h,w) if info['swizzle'] in (4,8) else (w,h)

def _complement(v,bits): return v if v>>(bits-1)==0 else v-(1<<bits)

def _decode_etc_block(block:bytes,e:str,alpha:bool):
    if alpha:
        alphas=struct.unpack(e+'Q',block[:8])[0]; block=block[8:]
    else: alphas=0xffffffffffffffff
    px=struct.unpack(e+'Q',block)[0]
    differential=((px>>33)&1)==1; horizontal=((px>>32)&1)==1
    table1=ETC_MODIFIERS[(px>>37)&7]; table2=ETC_MODIFIERS[(px>>34)&7]
    c1=[0,0,0];c2=[0,0,0]
    if differential:
        r=(px>>59)&31;g=(px>>51)&31;b=(px>>43)&31
        c1=[(r<<3)|(r>>2),(g<<3)|(g>>2),(b<<3)|(b>>2)]
        r+=_complement((px>>56)&7,3);g+=_complement((px>>48)&7,3);b+=_complement((px>>40)&7,3)
        r=max(0,min(31,r));g=max(0,min(31,g));b=max(0,min(31,b))
        c2=[(r<<3)|(r>>2),(g<<3)|(g>>2),(b<<3)|(b>>2)]
    else:
        c1=[((px>>60)&15)*17,((px>>52)&15)*17,((px>>44)&15)*17]
        c2=[((px>>56)&15)*17,((px>>48)&15)*17,((px>>40)&15)*17]
    amounts=px&0xffff; signs=(px>>16)&0xffff
    out=[]
    for y in range(4):
        for x in range(4):
            off=x*4+y
            use1=(y<2) if horizontal else (x<2)
            tab=table1 if use1 else table2; col=c1 if use1 else c2
            amt=tab[(amounts>>off)&1];
            if (signs>>off)&1: amt=-amt
            rgb=tuple(max(0,min(255,v+amt)) for v in col)
            a=((alphas>>(off*4))&15)*17
            out.append((*rgb,a))
    return out

def _decode_etc(data:bytes,w:int,h:int,e:str,alpha:bool):
    block_size=16 if alpha else 8
    tile_w=npot(math.ceil(w/8));tile_h=npot(math.ceil(h/8))
    out=[(0,0,0,0)]*(w*h); pos=0
    for ty in range(tile_h):
      for tx in range(tile_w):
       for by in range(2):
        for bx in range(2):
         block=data[pos:pos+block_size];pos+=block_size
         if len(block)<block_size: raise ValueError('ETC data truncated')
         pix=_decode_etc_block(block,e,alpha)
         for py in range(4):
          for px in range(4):
           x=px+bx*4+tx*8;y=py+by*4+ty*8
           if x<w and y<h: out[y*w+x]=pix[py*4+px]
    return out

def _pix_order_positions(w,h):
    # 3DS 8x8 tiled order used by BFLIM non-ETC textures
    tile_w=math.ceil(w/8); tile_h=math.ceil(h/8)
    for ty in range(tile_h):
      for tx in range(tile_w):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8;py=y3+y2*2+y*4+ty*8
             yield px,py

def _storage_dims(w,h,data_len,bpp):
    sw=npot(w);sh=npot(h)
    if int(sw*sh*bpp/8)<=data_len: return sw,sh
    # fallback round 8 dimensions
    sw=(w+7)//8*8; sh=(h+7)//8*8
    return sw,sh

def _decode_nonetc(data:bytes,w:int,h:int,fmt:int,e:str):
    bpp={0:8,1:8,2:8,3:16,4:16,5:16,6:24,7:16,8:16,9:32,12:4,13:4}[fmt]
    sw,sh=_storage_dims(w,h,len(data),bpp)
    out=[(0,0,0,0)]*(sw*sh); pos=0; idx=0
    for x,y in _pix_order_positions(sw,sh):
        if fmt==0: v=data[pos];pos+=1;c=(v,v,v,255)
        elif fmt==1: v=data[pos];pos+=1;c=(255,255,255,v)
        elif fmt==2: v=data[pos];pos+=1;c=(((v>>4)&15)*17,)*3+((v&15)*17,)
        elif fmt==3:
            l,a=data[pos],data[pos+1];pos+=2;c=(l,l,l,a)
        elif fmt==5:
            v=struct.unpack_from(e+'H',data,pos)[0];pos+=2;r=((v>>11)&31)*255//31;g=((v>>5)&63)*255//63;b=(v&31)*255//31;c=(r,g,b,255)
        elif fmt==6:
            r,g,b=data[pos:pos+3];pos+=3;c=(r,g,b,255)
        elif fmt==7:
            v=struct.unpack_from(e+'H',data,pos)[0];pos+=2;r=((v>>11)&31)*255//31;g=((v>>6)&31)*255//31;b=((v>>1)&31)*255//31;a=255 if v&1 else 0;c=(r,g,b,a)
        elif fmt==8:
            # BFLIM RGBA4 byte layout matches nibble sequence r,g,b,a in big-order value
            v=struct.unpack_from(e+'H',data,pos)[0];pos+=2;r=((v>>12)&15)*17;g=((v>>8)&15)*17;b=((v>>4)&15)*17;a=(v&15)*17;c=(r,g,b,a)
        elif fmt==9:
            v=struct.unpack_from(e+'I',data,pos)[0];pos+=4;c=((v>>24)&255,(v>>16)&255,(v>>8)&255,v&255)
        elif fmt in (12,13):
            v=data[pos//2]; nib=(v>>((idx&1)*4))&15; idx+=1
            if idx%2==0: pos+=2 # not used; adjusted below
            c=(nib*17,nib*17,nib*17,255) if fmt==12 else (255,255,255,nib*17)
            # above pos management cumbersome; handled separately below
        else: raise NotImplementedError(fmt)
        if fmt not in (12,13): idx+=1
        if x<sw and y<sh: out[y*sw+x]=c
    if fmt in (12,13):
        # redo 4-bit cleanly using order index
        out=[(0,0,0,0)]*(sw*sh)
        for i,(x,y) in enumerate(_pix_order_positions(sw,sh)):
            v=data[i//2];n=(v>>((i&1)*4))&15
            c=(n*17,n*17,n*17,255) if fmt==12 else (255,255,255,n*17)
            out[y*sw+x]=c
    return out,sw,sh

def _stored_to_display(img:Image.Image,swizzle:int):
    if swizzle==8: return img.transpose(Image.Transpose.TRANSPOSE)
    if swizzle==4: return img.transpose(Image.Transpose.ROTATE_90)
    return img

def _display_to_stored(img:Image.Image,swizzle:int):
    if swizzle==8: return img.transpose(Image.Transpose.TRANSPOSE)
    if swizzle==4: return img.transpose(Image.Transpose.ROTATE_270)
    return img

def decode_bflim(b:bytes)->Image.Image:
    inf=parse_header(b);w=inf['stored_width'];h=inf['stored_height'];fmt=inf['format'];data=b[:inf['data_len']]
    if fmt in (10,11):
        pix=_decode_etc(data,w,h,inf['endian'],fmt==11);stored=Image.new('RGBA',(w,h));stored.putdata(pix)
    else:
        pix,sw,sh=_decode_nonetc(data,w,h,fmt,inf['endian']);stored=Image.new('RGBA',(sw,sh));stored.putdata(pix);stored=stored.crop((0,0,w,h))
    return _stored_to_display(stored,inf['swizzle'])

# --- ETC encoder: individual mode, exhaustive modifier tables, preserves ETC1A4 format ---
def _subblock_best(pixels):
    # Fast deterministic ETC1 individual-mode search. Quantize the sub-block
    # average to RGB4, then evaluate all eight modifier tables. This keeps
    # the exact ETC1/ETC1A4 container format while avoiding an expensive
    # 27-neighbour base-color search.
    av=[sum(p[2][c] for p in pixels)/len(pixels) for c in range(3)]
    q=tuple(max(0,min(15,round(v/17))) for v in av)
    base=[x*17 for x in q]
    candidates=[]
    for ti,tab in enumerate(ETC_MODIFIERS):
        err=0; choices={}
        opts=[(tab[0],0,0),(-tab[0],0,1),(tab[1],1,0),(-tab[1],1,1)]
        for x,y,c in pixels:
            best=None
            for delta,abit,sbit in opts:
                rgb=[max(0,min(255,base[k]+delta)) for k in range(3)]
                e=sum((rgb[k]-c[k])**2 for k in range(3))
                if best is None or e<best[0]: best=(e,abit,sbit)
            err+=best[0];choices[(x,y)]=(best[1],best[2])
        candidates.append((err,q,ti,choices))
    return min(candidates,key=lambda x:x[0])

def _encode_etc_block(rgba16,e:str,alpha:bool):
    # rgba16 indexed row-major 4x4
    best_all=None
    for horizontal in (False,True):
        p1=[];p2=[]
        for y in range(4):
          for x in range(4):
            item=(x,y,rgba16[y*4+x])
            use1=(y<2) if horizontal else (x<2)
            (p1 if use1 else p2).append(item)
        b1=_subblock_best(p1);b2=_subblock_best(p2)
        tot=b1[0]+b2[0]
        if best_all is None or tot<best_all[0]: best_all=(tot,horizontal,b1,b2)
    _,horizontal,b1,b2=best_all
    _,q1,t1,ch1=b1; _,q2,t2,ch2=b2
    v=0
    # individual mode => diff bit 0
    if horizontal: v|=1<<32
    v|=(t1&7)<<37;v|=(t2&7)<<34
    v|=(q1[0]&15)<<60;v|=(q2[0]&15)<<56
    v|=(q1[1]&15)<<52;v|=(q2[1]&15)<<48
    v|=(q1[2]&15)<<44;v|=(q2[2]&15)<<40
    amounts=0;signs=0;alphas=0
    for y in range(4):
      for x in range(4):
        off=x*4+y; use1=(y<2) if horizontal else (x<2); abit,sbit=(ch1 if use1 else ch2)[(x,y)]
        amounts|=(abit&1)<<off;signs|=(sbit&1)<<off
        a=rgba16[y*4+x][3]; an=max(0,min(15,round(a/17)));alphas|=an<<(off*4)
    v|=amounts;v|=signs<<16
    col=struct.pack(e+'Q',v)
    return (struct.pack(e+'Q',alphas)+col) if alpha else col

def _encode_etc(img:Image.Image,w:int,h:int,e:str,alpha:bool):
    src=img.convert('RGBA');p=src.load();tile_w=npot(math.ceil(w/8));tile_h=npot(math.ceil(h/8));out=bytearray()
    for ty in range(tile_h):
      for tx in range(tile_w):
       for by in range(2):
        for bx in range(2):
         pix=[]
         for py in range(4):
          for px in range(4):
           x=px+bx*4+tx*8;y=py+by*4+ty*8
           pix.append(p[x,y] if x<w and y<h else (0,0,0,0))
         out+=_encode_etc_block(pix,e,alpha)
    return bytes(out)

def _enc_color(c,fmt):
    r,g,b,a=c
    if fmt==0:return int(round(.299*r+.587*g+.114*b))
    if fmt==1:return a
    if fmt==2:
        l=max(0,min(15,round((.299*r+.587*g+.114*b)/17)));return (l<<4)|round(a/17)
    if fmt==3:
        l=max(0,min(255,round(.299*r+.587*g+.114*b)));return bytes((l,a))
    if fmt==5:return ((r*31//255)<<11)|((g*63//255)<<5)|(b*31//255)
    if fmt==7:return ((r*31//255)<<11)|((g*31//255)<<6)|((b*31//255)<<1)|(1 if a>=128 else 0)
    if fmt==8:return ((round(r/17)&15)<<12)|((round(g/17)&15)<<8)|((round(b/17)&15)<<4)|(round(a/17)&15)
    if fmt==9:return (r<<24)|(g<<16)|(b<<8)|a
    if fmt==12:return max(0,min(15,round((.299*r+.587*g+.114*b)/17)))
    if fmt==13:return max(0,min(15,round(a/17)))
    raise NotImplementedError(fmt)

def _encode_nonetc(img:Image.Image,w:int,h:int,fmt:int,e:str,dlen:int):
    bpp={0:8,1:8,2:8,3:16,4:16,5:16,6:24,7:16,8:16,9:32,12:4,13:4}[fmt]
    sw,sh=_storage_dims(w,h,dlen,bpp); src=img.convert('RGBA');p=src.load();out=bytearray()
    if fmt in (12,13):
        nibs=[]
        for x,y in _pix_order_positions(sw,sh):
            c=p[x,y] if x<w and y<h else (0,0,0,0);nibs.append(_enc_color(c,fmt))
        for i in range(0,len(nibs),2): out.append(nibs[i]|((nibs[i+1] if i+1<len(nibs) else 0)<<4))
    else:
        for x,y in _pix_order_positions(sw,sh):
            c=p[x,y] if x<w and y<h else (0,0,0,0);v=_enc_color(c,fmt)
            if fmt in (0,1,2):out.append(v)
            elif fmt==3:out+=v
            elif fmt in (5,7,8):out+=struct.pack(e+'H',v)
            elif fmt==6:out+=bytes(c[:3])
            elif fmt==9:out+=struct.pack(e+'I',v)
    if len(out)>dlen: raise ValueError(f'encoded too long {len(out)}>{dlen}')
    return bytes(out)+bytes(dlen-len(out))

def encode_bflim(display_img:Image.Image,template:bytes)->bytes:
    inf=parse_header(template);dw,dh=display_size(inf)
    if display_img.size!=(dw,dh):raise ValueError(f'display image must be {dw}x{dh}, got {display_img.size}')
    stored=_display_to_stored(display_img.convert('RGBA'),inf['swizzle'])
    if stored.size!=(inf['stored_width'],inf['stored_height']):raise ValueError(f'stored transform mismatch {stored.size}')
    if inf['format'] in (10,11): data=_encode_etc(stored,*stored.size,inf['endian'],inf['format']==11)
    else:data=_encode_nonetc(stored,*stored.size,inf['format'],inf['endian'],inf['data_len'])
    if len(data)!=inf['data_len']:raise ValueError(f'data length {len(data)} != {inf["data_len"]}')
    rebuilt=data+template[inf['data_len']:]
    if len(rebuilt)!=len(template) or rebuilt[-0x28:]!=template[-0x28:]:raise AssertionError('metadata changed')
    return rebuilt

def main():
 import argparse
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
 p=sp.add_parser('decode');p.add_argument('input');p.add_argument('output')
 p=sp.add_parser('encode');p.add_argument('png');p.add_argument('template');p.add_argument('output')
 p=sp.add_parser('info');p.add_argument('input')
 a=ap.parse_args()
 if a.cmd=='decode':decode_bflim(Path(a.input).read_bytes()).save(a.output)
 elif a.cmd=='encode':Path(a.output).write_bytes(encode_bflim(Image.open(a.png),Path(a.template).read_bytes()))
 else:print(parse_header(Path(a.input).read_bytes()))
if __name__=='__main__':main()
