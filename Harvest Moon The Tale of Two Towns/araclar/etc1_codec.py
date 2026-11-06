from PIL import Image
from pathlib import Path
import struct, math
MOD=[[2,8],[5,17],[9,29],[13,42],[18,60],[24,80],[33,106],[47,183]]

def comp(v,bits): return v if v>>(bits-1)==0 else v-(1<<bits)
def clamp(v): return max(0,min(255,int(v)))

def decode_etc1a4(raw,w,h):
    out=Image.new('RGBA',(w,h),(0,0,0,0)); px=out.load(); pos=0
    tilew=1
    while tilew < (w+7)//8: tilew*=2
    tileh=1
    while tileh < (h+7)//8: tileh*=2
    for ty in range(tileh):
      for tx in range(tilew):
       for by in range(2):
        for bx in range(2):
         blk=raw[pos:pos+16]; pos+=16
         if len(blk)<16: continue
         alphas=int.from_bytes(blk[:8],'little')
         pixels=int.from_bytes(blk[8:],'little')
         diff=((pixels>>33)&1)!=0; horiz=((pixels>>32)&1)!=0
         t1=MOD[(pixels>>37)&7]; t2=MOD[(pixels>>34)&7]
         if diff:
          r=(pixels>>59)&31; g=(pixels>>51)&31; b=(pixels>>43)&31
          c1=[(r<<3)|((r>>2)&7),(g<<3)|((g>>2)&7),(b<<3)|((b>>2)&7)]
          r+=comp((pixels>>56)&7,3); g+=comp((pixels>>48)&7,3); b+=comp((pixels>>40)&7,3)
          c2=[(r<<3)|((r>>2)&7),(g<<3)|((g>>2)&7),(b<<3)|((b>>2)&7)]
         else:
          c1=[((pixels>>60)&15)*17,((pixels>>52)&15)*17,((pixels>>44)&15)*17]
          c2=[((pixels>>56)&15)*17,((pixels>>48)&15)*17,((pixels>>40)&15)*17]
         amounts=pixels & 0xffff; signs=(pixels>>16)&0xffff
         for py in range(4):
          for pxi in range(4):
           off=pxi*4+py
           tab,c=(t1,c1) if ((py<2) if horiz else (pxi<2)) else (t2,c2)
           amt=tab[(amounts>>off)&1]
           if (signs>>off)&1: amt=-amt
           rr,gg,bb=[clamp(q+amt) for q in c]
           aa=((alphas>>(off*4))&15)*17
           x=tx*8+bx*4+pxi; y=ty*8+by*4+py
           if x<w and y<h: px[x,y]=(rr,gg,bb,aa)
    return out

def _subbest(pixels, coords, alpha_weight=True):
    # pixels list 16 tuples RGBA, coords list indices into 4x4 row-major
    vis=[pixels[i] for i in coords if pixels[i][3]>0]
    src=vis if vis else [pixels[i] for i in coords]
    if not src: src=[(0,0,0,0)]
    avg=[sum(p[k] for p in src)/len(src) for k in range(3)]
    q0=[int(round(v/17)) for v in avg]
    best=None
    # Most HM UI labels are grayscale. Searching one base channel is ~50x faster and exact for them.
    is_gray=all(max(abs(p[0]-p[1]),abs(p[1]-p[2]),abs(p[0]-p[2])) <= 8 for p in src)
    if is_gray:
        bases=[(q,q,q) for q in range(16)]
    else:
        bases=[(qr,qg,qb)
               for qr in range(max(0,q0[0]-2),min(15,q0[0]+2)+1)
               for qg in range(max(0,q0[1]-2),min(15,q0[1]+2)+1)
               for qb in range(max(0,q0[2]-2),min(15,q0[2]+2)+1)]
    for qr,qg,qb in bases:
       base=(qr*17,qg*17,qb*17)
       for ti,(m0,m1) in enumerate(MOD):
        err=0.0; choices={}
        opts=[(m0,0,0),(m1,1,0),(-m0,0,1),(-m1,1,1)] # modifier, amountbit, signbit
        for idx in coords:
         r,g,b,a=pixels[idx]
         # visible pixels dominate; transparent RGB is irrelevant.
         weight=max(a/255.0, 0.02 if a else 0.0)
         if weight==0: choices[idx]=(0,0); continue
         be=None
         for mod,ab,sb in opts:
          rr,gg,bb=(clamp(base[0]+mod),clamp(base[1]+mod),clamp(base[2]+mod))
          e=((r-rr)**2+(g-gg)**2+(b-bb)**2)*weight
          if be is None or e<be[0]: be=(e,ab,sb)
         err+=be[0]; choices[idx]=(be[1],be[2])
        if best is None or err<best[0]: best=(err,(qr,qg,qb),ti,choices)
    return best

def encode_etc1_block(pixels):
    # pixels: 16 RGBA tuples row-major, top-to-bottom.
    best=None
    for horiz in (0,1):
      if horiz:
        c1=[y*4+x for y in range(2) for x in range(4)]
        c2=[y*4+x for y in range(2,4) for x in range(4)]
      else:
        c1=[y*4+x for y in range(4) for x in range(2)]
        c2=[y*4+x for y in range(4) for x in range(2,4)]
      b1=_subbest(pixels,c1); b2=_subbest(pixels,c2)
      err=b1[0]+b2[0]
      if best is None or err<best[0]: best=(err,horiz,b1,b2)
    _,horiz,b1,b2=best
    (_,q1,t1,ch1)=b1; (_,q2,t2,ch2)=b2
    p=0
    p|=(q1[0]&15)<<60; p|=(q2[0]&15)<<56
    p|=(q1[1]&15)<<52; p|=(q2[1]&15)<<48
    p|=(q1[2]&15)<<44; p|=(q2[2]&15)<<40
    p|=(t1&7)<<37; p|=(t2&7)<<34
    # diff bit stays 0; orientation/horizontal bit
    p|=(horiz&1)<<32
    amounts=0; signs=0
    for idx,(r,g,b,a) in enumerate(pixels):
      x=idx%4; y=idx//4; off=x*4+y
      ab,sb=(ch1 if ((y<2) if horiz else (x<2)) else ch2)[idx]
      amounts |= (ab&1)<<off; signs |= (sb&1)<<off
    p|=amounts; p|=signs<<16
    alpha=0
    for idx,rgba in enumerate(pixels):
      x=idx%4; y=idx//4; off=x*4+y
      an=max(0,min(15,int(round(rgba[3]/17))))
      alpha |= an<<(off*4)
    return alpha.to_bytes(8,'little') + p.to_bytes(8,'little')

def encode_etc1a4(im):
    im=im.convert('RGBA'); w,h=im.size; pix=im.load(); out=bytearray()
    tilew=1
    while tilew < (w+7)//8: tilew*=2
    tileh=1
    while tileh < (h+7)//8: tileh*=2
    for ty in range(tileh):
      for tx in range(tilew):
       for by in range(2):
        for bx in range(2):
         ps=[]
         for y in range(4):
          for x in range(4):
           xx=tx*8+bx*4+x; yy=ty*8+by*4+y
           ps.append(pix[xx,yy] if xx<w and yy<h else (0,0,0,0))
         out += encode_etc1_block(ps)
    return bytes(out)

def decode_rgba4(raw,w,h):
    # 3DS uncompressed tiled order, 8x8 Morton, same orientation as file
    def morton(x,y):
      r=0
      for i in range(3): r|=((x>>i)&1)<<(2*i); r|=((y>>i)&1)<<(2*i+1)
      return r
    im=Image.new('RGBA',(w,h),(0,0,0,0)); px=im.load(); p=0
    for ty in range(0,h,8):
      for tx in range(0,w,8):
       tile=raw[p:p+128]; p+=128
       for y in range(8):
        for x in range(8):
         idx=morton(x,y)*2; v=tile[idx]|(tile[idx+1]<<8)
         r=((v>>12)&15)*17; g=((v>>8)&15)*17; b=((v>>4)&15)*17; a=(v&15)*17
         if tx+x<w and ty+y<h: px[tx+x,ty+y]=(r,g,b,a)
    return im
