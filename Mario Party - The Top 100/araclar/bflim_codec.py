from __future__ import annotations
import math, struct
from PIL import Image

FMT_NAMES={0:'L8',1:'A8',2:'LA4',3:'LA8',4:'HILO8',5:'RGB565',6:'RGB8',7:'RGBA5551',8:'RGBA4',9:'RGBA8',10:'ETC1',11:'ETC1A4',12:'L4',13:'A4',19:'ETC1'}
PIXEL_SIZE={0:1,1:1,2:1,3:2,4:2,5:2,6:3,7:2,8:2,9:4}
ETC1_MODIFIERS=((2,8),(5,17),(9,29),(13,42),(18,60),(24,80),(33,106),(47,183))

def _pow2ceil(n): return 1 if n<=1 else 1<<(n-1).bit_length()

def info(data:bytes):
    if len(data)<40 or data[-40:-36]!=b'FLIM' or data[-20:-16]!=b'imag':
        raise ValueError('not BFLIM')
    e='<' if data[-36:-34]==b'\xff\xfe' else '>'
    magic,bom,hs,ver,flen,sects,pad=struct.unpack_from(e+'4sHHIIHH',data,len(data)-40)
    imag,isz,w,h,align,fmt,swiz,dlen=struct.unpack_from(e+'4sIHHHBBI',data,len(data)-20)
    return {'endian':e,'version':ver,'filelen':flen,'width':w,'height':h,'align':align,'format':fmt,'format_name':FMT_NAMES.get(fmt,str(fmt)),'swizzle':swiz,'data_len':dlen}

def _pix_un(data, pos, fmt, little=True):
    if fmt==0: v=data[pos]; return (v,v,v,255)
    if fmt==1: a=data[pos]; return (255,255,255,a)
    if fmt==2:
        b=data[pos]; v=((b>>4)&15)*17; a=(b&15)*17; return (v,v,v,a)
    if fmt==3:
        if little: a,l=data[pos],data[pos+1]
        else: l,a=data[pos],data[pos+1]
        return (l,l,l,a)
    if fmt==5:
        if little: val=data[pos]|data[pos+1]<<8
        else: val=data[pos]<<8|data[pos+1]
        r=((val>>11)&31)*255//31; g=((val>>5)&63)*255//63; b=(val&31)*255//31
        return (r,g,b,255)
    if fmt==6:
        if little: b,g,r=data[pos:pos+3]
        else: r,g,b=data[pos:pos+3]
        return (r,g,b,255)
    if fmt==7:
        if little: val=data[pos]|data[pos+1]<<8
        else: val=data[pos]<<8|data[pos+1]
        r=((val>>11)&31)*255//31; g=((val>>6)&31)*255//31; b=((val>>1)&31)*255//31; a=255 if val&1 else 0
        return (r,g,b,a)
    if fmt==8:
        if little:
            lo,hi=data[pos],data[pos+1]; r=(hi>>4)*17; g=(hi&15)*17; b=(lo>>4)*17; a=(lo&15)*17
        else:
            hi,lo=data[pos],data[pos+1]; r=(hi>>4)*17; g=(hi&15)*17; b=(lo>>4)*17; a=(lo&15)*17
        return (r,g,b,a)
    if fmt==9:
        r,g,b,a=data[pos:pos+4]; return (r,g,b,a)
    raise ValueError(fmt)

def _decode_tiled(raw:bytes,w:int,h:int,fmt:int,little=True):
    out=Image.new('RGBA',(w,h),(0,0,0,0)); px=out.load()
    tilesx=math.ceil(w/8); tilesy=math.ceil(h/8); totalx=math.ceil(_pow2ceil(w)/8)
    if fmt in (12,13):
        for yt in range(tilesy):
          for xt in range(tilesx):
           for ys in range(2):
            for xs in range(2):
             for yb in range(2):
              for xb in range(2):
               for yp in range(2):
                inpos=yt*totalx*32+xt*32+ys*16+xs*8+yb*4+xb*2+yp
                byte=raw[inpos]
                for xp in range(2):
                 x=xt*8+xs*4+xb*2+xp; y=yt*8+ys*4+yb*2+yp
                 if x>=w or y>=h: continue
                 v=((byte>>(xp*4))&15)*17
                 px[x,y]=(v,v,v,255) if fmt==12 else (255,255,255,v)
        return out
    psize=PIXEL_SIZE[fmt]
    for yt in range(tilesy):
      for xt in range(tilesx):
       for ys in range(2):
        for xs in range(2):
         for yb in range(2):
          for xb in range(2):
           for yp in range(2):
            for xp in range(2):
             x=xt*8+xs*4+xb*2+xp; y=yt*8+ys*4+yb*2+yp
             if x>=w or y>=h: continue
             pindex=yt*totalx*64+xt*64+ys*32+xs*16+yb*8+xb*4+yp*2+xp
             pos=pindex*psize
             px[x,y]=_pix_un(raw,pos,fmt,little)
    return out

def _etc_comp(v,bits): return v if (v>>(bits-1))==0 else v-(1<<bits)
def _decode_etc1(raw,w,h,fmt):
    out=Image.new('RGBA',(w,h),(0,0,0,0)); px=out.load(); p=0
    tilew=_pow2ceil(math.ceil(w/8)); tileh=_pow2ceil(math.ceil(h/8)); hasalpha=(fmt==11)
    for yt in range(tileh):
      for xt in range(tilew):
       for yb in range(2):
        for xb in range(2):
         alphas=(1<<64)-1
         if hasalpha:
          alphas=int.from_bytes(raw[p:p+8],'little'); p+=8
         pixels=int.from_bytes(raw[p:p+8],'little'); p+=8
         diff=(pixels>>33)&1; horiz=(pixels>>32)&1
         t1=ETC1_MODIFIERS[(pixels>>37)&7]; t2=ETC1_MODIFIERS[(pixels>>34)&7]
         if diff:
          r=(pixels>>59)&31; g=(pixels>>51)&31; b=(pixels>>43)&31
          c1=((r<<3)|(r>>2),(g<<3)|(g>>2),(b<<3)|(b>>2))
          r=(r+_etc_comp((pixels>>56)&7,3))&31; g=(g+_etc_comp((pixels>>48)&7,3))&31; b=(b+_etc_comp((pixels>>40)&7,3))&31
          c2=((r<<3)|(r>>2),(g<<3)|(g>>2),(b<<3)|(b>>2))
         else:
          c1=(((pixels>>60)&15)*17,((pixels>>52)&15)*17,((pixels>>44)&15)*17)
          c2=(((pixels>>56)&15)*17,((pixels>>48)&15)*17,((pixels>>40)&15)*17)
         amounts=pixels&0xffff; signs=(pixels>>16)&0xffff
         for yp in range(4):
          for xp in range(4):
           x=xp+xb*4+xt*8; y=yp+yb*4+yt*8
           if x>=w or y>=h: continue
           off=xp*4+yp
           if horiz: table=t1 if yp<2 else t2; col=c1 if yp<2 else c2
           else: table=t1 if xp<2 else t2; col=c1 if xp<2 else c2
           amt=table[(amounts>>off)&1]; amt=-amt if ((signs>>off)&1) else amt
           a=((alphas>>(off*4))&15)*17 if hasalpha else 255
           px[x,y]=(max(0,min(255,col[0]+amt)),max(0,min(255,col[1]+amt)),max(0,min(255,col[2]+amt)),a)
    return out

def decode(data:bytes):
    inf=info(data); w,h=inf['width'],inf['height']; sw=inf['swizzle']; ver=inf['version']; fmt=inf['format']; raw=data[:inf['data_len']]
    tw,th=w,h
    if sw in (4,8) and ver==0x07020100: tw,th=h,w
    if fmt in (10,11,19): img=_decode_etc1(raw,tw,th,11 if fmt==11 else 10)
    else: img=_decode_tiled(raw,tw,th,fmt,inf['endian']=='<')
    if sw==4: img=img.transpose(Image.Transpose.ROTATE_90)
    elif sw==8: img=img.transpose(Image.Transpose.ROTATE_90).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return img

def _swizzle_for_pack(img, sw):
    if sw==4:
        r=img.rotate(-90,expand=True); return r.crop((0,0,img.height,img.width))
    if sw==8:
        r=img.transpose(Image.Transpose.FLIP_TOP_BOTTOM).rotate(-90,expand=True); return r.crop((0,0,img.height,img.width))
    return img

def encode_rgba8(img:Image.Image, swizzle=4, align=0x80, version=0x07020100, endian='<'):
    img=img.convert('RGBA'); width,height=img.size; swimg=_swizzle_for_pack(img,swizzle); w,h=swimg.size
    dataw=_pow2ceil(w); datah=_pow2ceil(h); tilesx=math.ceil(dataw/8); tilesy=math.ceil(datah/8)
    raw=bytearray(dataw*datah*4); pix=swimg.load()
    for yt in range(tilesy):
      for xt in range(tilesx):
       for ys in range(2):
        for xs in range(2):
         for yb in range(2):
          for xb in range(2):
           for yp in range(2):
            for xp in range(2):
             y=yt*8+ys*4+yb*2+yp; x=xt*8+xs*4+xb*2+xp
             if x>=w or y>=h: continue
             rgba=pix[x,y]
             finalx=xp+xb*4+xs*16+xt*64
             finaly=yp*2+yb*8+ys*32+yt*tilesx*64
             pos=(finalx+finaly)*4
             raw[pos:pos+4]=bytes(rgba)
    pad=(-len(raw))%align
    body=bytes(raw)+b'\0'*pad
    filelen=len(body)+40
    hdr=struct.pack(endian+'4sHHIIHH',b'FLIM',0xfeff,0x14,version,filelen,1,0)
    imag=struct.pack(endian+'4sIHHHBBI',b'imag',0x10,width,height,align,9,swizzle,len(raw))
    return body+hdr+imag
