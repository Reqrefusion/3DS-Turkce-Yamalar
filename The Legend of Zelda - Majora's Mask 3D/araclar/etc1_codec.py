from __future__ import annotations
from PIL import Image
import math
MODS=[
[2,8,-2,-8],[5,17,-5,-17],[9,29,-9,-29],[13,42,-13,-42],
[18,60,-18,-60],[24,80,-24,-80],[33,106,-33,-106],[47,183,-47,-183]]
def clamp(x): return 0 if x<0 else 255 if x>255 else x
def sx3(v): return v-8 if v&4 else v

def decode_block(block:bytes):
    w=int.from_bytes(block,'little')
    diff=(w>>33)&1; flip=(w>>32)&1; t1=(w>>37)&7;t2=(w>>34)&7
    if not diff:
        r1=((w>>60)&15)*17;r2=((w>>56)&15)*17;g1=((w>>52)&15)*17;g2=((w>>48)&15)*17;b1=((w>>44)&15)*17;b2=((w>>40)&15)*17
    else:
        r1v=(w>>59)&31;r2v=r1v+sx3((w>>56)&7);g1v=(w>>51)&31;g2v=g1v+sx3((w>>48)&7);b1v=(w>>43)&31;b2v=b1v+sx3((w>>40)&7)
        # valid ETC1 differential blocks must keep second bases in [0,31]
        r2v=max(0,min(31,r2v));g2v=max(0,min(31,g2v));b2v=max(0,min(31,b2v))
        ex=lambda v:(v<<3)|(v>>2)
        r1,r2,g1,g2,b1,b2=map(ex,(r1v,r2v,g1v,g2v,b1v,b2v))
    out=[[None]*4 for _ in range(4)]
    for y in range(4):
        for x in range(4):
            k=x*4+y
            sel=(((w>>(16+k))&1)<<1)|((w>>k)&1)
            first=(x<2 if flip==0 else y<2)
            base=(r1,g1,b1) if first else (r2,g2,b2); table=t1 if first else t2
            d=MODS[table][sel]
            out[y][x]=(clamp(base[0]+d),clamp(base[1]+d),clamp(base[2]+d),255)
    return out

def _fit_subblock(pixels):
    # pixels: [(x,y,(r,g,b,a)), ...]
    n=len(pixels); means=[sum(p[2][c] for p in pixels)/n for c in range(3)]
    q0=[max(0,min(15,round(v/17))) for v in means]
    best=None
    # Search a modest cube around the average; ETC1 individual mode is robust for UI textures.
    cand=[]
    for c,q in enumerate(q0): cand.append(range(max(0,q-2),min(15,q+2)+1))
    for rn in cand[0]:
      r=rn*17
      for gn in cand[1]:
       g=gn*17
       for bn in cand[2]:
        b=bn*17
        for tab in range(8):
            err=0; sels=[]
            mods=MODS[tab]
            for _,_,rgba in pixels:
                pr,pg,pb=rgba[:3]
                e_best=None;s_best=0
                for s,d in enumerate(mods):
                    rr,gg,bb=clamp(r+d),clamp(g+d),clamp(b+d)
                    e=(pr-rr)**2+(pg-gg)**2+(pb-bb)**2
                    if e_best is None or e<e_best:e_best=e;s_best=s
                err+=e_best;sels.append(s_best)
                if best is not None and err>=best[0]:break
            if best is None or err<best[0]:best=(err,(rn,gn,bn),tab,sels)
    return best

def encode_block(pix4):
    # pix4[y][x] rgba. Use individual mode and evaluate both ETC1 split directions.
    best=None
    for flip in (0,1):
        subs=[[],[]]
        for y in range(4):
            for x in range(4):
                first=(x<2 if flip==0 else y<2)
                subs[0 if first else 1].append((x,y,pix4[y][x]))
        a=_fit_subblock(subs[0]);b=_fit_subblock(subs[1]);err=a[0]+b[0]
        if best is None or err<best[0]:best=(err,flip,a,b,subs)
    _,flip,a,b,subs=best
    (e1,(r1,g1,b1),t1,s1)=a;(e2,(r2,g2,b2),t2,s2)=b
    w=0
    w|=(r1&15)<<60;w|=(r2&15)<<56;w|=(g1&15)<<52;w|=(g2&15)<<48;w|=(b1&15)<<44;w|=(b2&15)<<40
    w|=(t1&7)<<37;w|=(t2&7)<<34;w|=0<<33;w|=(flip&1)<<32
    # selectors correspond to pixels list order for each subblock
    selmap={}
    for sub,sels in zip(subs,(s1,s2)):
        for (entry,sel) in zip(sub,sels): selmap[(entry[0],entry[1])]=sel
    for y in range(4):
        for x in range(4):
            s=selmap[(x,y)];k=x*4+y
            if s&1:w|=1<<k
            if s&2:w|=1<<(16+k)
    return w.to_bytes(8,'little')

def decode_image(data:bytes,width:int,height:int,has_alpha=False):
    out=Image.new('RGBA',(width,height));px=out.load();off=0
    for ty in range(0,height,8):
      for tx in range(0,width,8):
       for dx,dy in ((0,0),(4,0),(0,4),(4,4)):
        alpha=None
        if has_alpha:
            alpha=int.from_bytes(data[off:off+8],'little');off+=8
        block=data[off:off+8];off+=8
        p=decode_block(block)
        for y in range(4):
         for x in range(4):
          a=255
          if alpha is not None:
            # Try standard x-major ETC1A4 nibble order; validated visually on UI atlases.
            k=x*4+y;a=((alpha>>(k*4))&0xF)*17
          r,g,b,_=p[y][x];px[tx+dx+x,ty+dy+y]=(r,g,b,a)
    return out

def encode_image(im:Image.Image,has_alpha=False):
    im=im.convert('RGBA');w,h=im.size;px=im.load();out=bytearray()
    if w%8 or h%8:raise ValueError('ETC1 dimensions must be multiples of 8')
    for ty in range(0,h,8):
      for tx in range(0,w,8):
       for dx,dy in ((0,0),(4,0),(0,4),(4,4)):
        p=[[px[tx+dx+x,ty+dy+y] for x in range(4)] for y in range(4)]
        if has_alpha:
            aw=0
            for y in range(4):
             for x in range(4):
              k=x*4+y;q=max(0,min(15,round(p[y][x][3]/17)));aw|=(q&15)<<(k*4)
            out+=aw.to_bytes(8,'little')
        out+=encode_block(p)
    return bytes(out)
