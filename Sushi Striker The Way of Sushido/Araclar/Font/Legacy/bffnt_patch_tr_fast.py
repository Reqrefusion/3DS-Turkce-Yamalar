#!/usr/bin/env python3
from pathlib import Path
import struct
from PIL import Image,ImageDraw,ImageChops

TR_TARGETS=['Ğ','ğ','İ','ı','Ş','ş']
BASE_FOR={'Ğ':'G','ğ':'g','İ':'I','ı':'i','Ş':'S','ş':'s'}
SACRIFICE=[0x2020,0x2021,0x2030,0x2039,0x203A,0x201A]  # never used by patch text

def morton8(x,y):
    return ((x&1)|((y&1)<<1)|((x&2)<<1)|((y&2)<<2)|((x&4)<<2)|((y&4)<<3))
def nib_index(x,y,w):
    return ((y//8)*(w//8)+(x//8))*64 + morton8(x&7,y&7)

def parse(data):
    if data[:4]!=b'FFNT': raise ValueError('not FFNT')
    e='<' if data[4:6]==b'\xff\xfe' else '>'
    finf=struct.unpack_from(e+'4sI4B2H4B3I',data,20)
    tpos,wpos,cpos=finf[-3]-8,finf[-2]-8,finf[-1]-8
    t=struct.unpack_from(e+'4sI4BI6HI',data,tpos)
    _,_,cw,ch,ns,maxw,ss,baseline,fmt,cols,rows,sw,sh,dataoff=t
    mapping={}; sparse=[]; pos=cpos
    while pos:
        magic,size,start,end,method,res,nxt=struct.unpack_from(e+'4sI4HI',data,pos);q=pos+20
        if method==0:
            idx=struct.unpack_from(e+'H',data,q)[0]
            for cp in range(start,end+1):mapping[cp]=idx+cp-start
        elif method==1:
            vals=struct.unpack_from(e+f'{end-start+1}H',data,q)
            for i,v in enumerate(vals):
                if v!=0xffff:mapping[start+i]=v
        elif method==2:
            cnt=struct.unpack_from(e+'H',data,q)[0];q+=2
            for i in range(cnt):
                ep=q+i*4;cp,idx=struct.unpack_from(e+'HH',data,ep);mapping[cp]=idx;sparse.append((cp,idx,ep))
        pos=nxt-8 if nxt else 0
    widths={};widthpos={};pos=wpos
    while pos:
        magic,size,start,end,nxt=struct.unpack_from(e+'4sI2HI',data,pos);q=pos+16
        for idx in range(start,end+1):
            pp=q+(idx-start)*3;widths[idx]=struct.unpack_from('bbb',data,pp);widthpos[idx]=pp
        pos=nxt-8 if nxt else 0
    return locals()

def glyph_origin(info,idx):
    per=info['cols']*info['rows'];si=idx//per;j=idx%per
    return si,(j%info['cols'])*(info['cw']+1),(j//info['cols'])*(info['ch']+1)

def extract_glyph(data,info,idx):
    si,ox,oy=glyph_origin(info,idx);im=Image.new('L',(info['cw'],info['ch']),0);p=im.load();base=info['dataoff']+si*info['ss']
    for y in range(info['ch']):
        for x in range(info['cw']):
            ni=nib_index(ox+x,oy+y,info['sw']);bb=data[base+ni//2];v=(bb&15) if ni%2==0 else (bb>>4);p[x,y]=v*17
    return im

def write_glyph(out,info,idx,im):
    si,ox,oy=glyph_origin(info,idx);p=im.load();base=info['dataoff']+si*info['ss']
    for y in range(info['ch']):
        for x in range(info['cw']):
            ni=nib_index(ox+x,oy+y,info['sw']);bi=base+ni//2;v=max(0,min(15,int(round(p[x,y]/17))))
            if ni%2==0:out[bi]=(out[bi]&0xf0)|v
            else:out[bi]=(out[bi]&0x0f)|(v<<4)

def components(im,threshold=40):
    w,h=im.size;px=im.load();seen=set();res=[]
    for y in range(h):
      for x in range(w):
       if (x,y) in seen or px[x,y]<threshold:continue
       st=[(x,y)];seen.add((x,y));pts=[]
       while st:
        a,b=st.pop();pts.append((a,b))
        for nx,ny in ((a-1,b),(a+1,b),(a,b-1),(a,b+1),(a-1,b-1),(a+1,b-1),(a-1,b+1),(a+1,b+1)):
         if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and px[nx,ny]>=threshold:seen.add((nx,ny));st.append((nx,ny))
       res.append(pts)
    return res

def dotless_i(im):
    out=im.copy();cs=components(out);pix=out.load()
    if len(cs)>=2:
      stem=max(cs,key=len);sy=sum(y for x,y in stem)/len(stem)
      for c in cs:
       cy=sum(y for x,y in c)/len(c)
       if cy<sy-2:
        for x,y in c:pix[x,y]=0
    return out

def cedilla(accented,base):
    w,h=accented.size;bb=base.getbbox() or (0,0,w,h);cut=max(0,bb[3]-1);out=Image.new('L',(w,h),0);a=accented.load();o=out.load()
    for y in range(cut,h):
      for x in range(w):
       if a[x,y]>20:o[x,y]=a[x,y]
    return out

def breve(base):
    out=base.copy();w,h=out.size;bb=out.getbbox() or (0,0,w,h);x0,y0,x1,y1=bb;center=(x0+x1-1)/2;bw=max(5,min(w-4,int((x1-x0)*.55)));top=max(1,y0-(4 if h>=28 else 3));scale=4
    lay=Image.new('L',(w*scale,h*scale),0);d=ImageDraw.Draw(lay);left=int((center-bw/2)*scale);right=int((center+bw/2)*scale);yy=int(top*scale);pts=[]
    for i in range(max(2,right-left+1)):
      x=left+i;t=i/max(1,right-left);y=yy+int((1-(2*t-1)**2)*2.0*scale);pts.append((x,y))
    d.line(pts,fill=255,width=max(3,int(scale*.9)));lay=lay.resize((w,h),Image.Resampling.LANCZOS);return ImageChops.lighter(out,lay)

def dotted_I(base):
    out=base.copy();w,h=out.size;bb=out.getbbox() or(0,0,w,h);x0,y0,x1,y1=bb;cx=(x0+x1)//2;scale=4;lay=Image.new('L',(w*scale,h*scale),0);d=ImageDraw.Draw(lay);r=max(1.0,min(2.2,h/16));cy=max(r+.5,y0-2.2);d.ellipse(((cx-r)*scale,(cy-r)*scale,(cx+r)*scale,(cy+r)*scale),fill=255);lay=lay.resize((w,h),Image.Resampling.LANCZOS);return ImageChops.lighter(out,lay)

def patch_font(data):
    info=parse(data);m=info['mapping'];missing=[ch for ch in TR_TARGETS if ord(ch) not in m]
    if not missing:return data,{'patched':False,'reason':'complete'}
    if info['fmt']!=11 or any(ord(c) not in m for c in 'GgIiSsCcÇç'):
      return data,{'patched':False,'reason':'unsuitable','missing':missing,'fmt':info['fmt']}
    bycp={cp:(idx,pos) for cp,idx,pos in info['sparse']};choices=[cp for cp in SACRIFICE if cp in bycp]
    if len(choices)<len(missing):return data,{'patched':False,'reason':'no safe slots','missing':missing}
    imgs={c:extract_glyph(data,info,m[ord(c)]) for c in 'GgIiSsCcÇç'}
    made={'Ğ':breve(imgs['G']),'ğ':breve(imgs['g']),'İ':dotted_I(imgs['I']),'ı':dotless_i(imgs['i']),'Ş':ImageChops.lighter(imgs['S'],cedilla(imgs['Ç'],imgs['C'])),'ş':ImageChops.lighter(imgs['s'],cedilla(imgs['ç'],imgs['c']))}
    out=bytearray(data);assigned={}
    for ch,sac in zip(missing,choices):
      idx,ep=bycp[sac];struct.pack_into(info['e']+'H',out,ep,ord(ch));write_glyph(out,info,idx,made[ch]);bidx=m[ord(BASE_FOR[ch])]
      if idx in info['widthpos']:struct.pack_into('bbb',out,info['widthpos'][idx],*info['widths'][bidx])
      assigned[ch]={'glyph':idx,'replaced_cp':f'U+{sac:04X}'}
    # lightweight validate mapping after patch
    ni=parse(bytes(out));still=[ch for ch in TR_TARGETS if ord(ch) not in ni['mapping']]
    if still:raise ValueError('still missing '+''.join(still))
    return bytes(out),{'patched':True,'missing_before':missing,'assigned':assigned,'cell':[info['cw'],info['ch']],'baseline':info['baseline']}

if __name__=='__main__':
 import sys,json
 src,dst=sys.argv[1:3];p,r=patch_font(Path(src).read_bytes());Path(dst).write_bytes(p);print(json.dumps(r,ensure_ascii=False,indent=2))
