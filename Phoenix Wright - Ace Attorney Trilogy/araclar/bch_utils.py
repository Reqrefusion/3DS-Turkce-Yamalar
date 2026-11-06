import struct, math
from PIL import Image

MODS=[(2,8,-2,-8),(5,17,-5,-17),(9,29,-9,-29),(13,42,-13,-42),(18,60,-18,-60),(24,80,-24,-80),(33,106,-33,-106),(47,183,-47,-183)]

def _clamp(x): return 0 if x<0 else 255 if x>255 else x

def parse_bch_textures(b):
    if b[:4]!=b'BCH\0': return []
    sec0=struct.unpack_from('<I',b,8)[0]
    if sec0 in (56,60): nsec,nsizes=5,7
    elif sec0==64: nsec,nsizes=6,8
    else:
        # observed variants; infer type0 when first content starts <=0x3c
        nsec,nsizes=(5,7) if sec0<=60 else (6,8)
    offs=list(struct.unpack_from('<'+'I'*nsec,b,8))
    sizes=list(struct.unpack_from('<'+'I'*nsizes,b,8+4*nsec))
    content,string,command,raw=offs[:4]
    if not (0<=content<len(b) and content+48<=len(b)): return []
    # Patricia map type Texture = 3, 12 bytes each
    pm=content+3*12
    elements,numdata,pad,nodes=struct.unpack_from('<IHHI',b,pm)
    out=[]
    for ti in range(numdata):
        q=content+elements+4*ti
        if q+4>len(b): break
        tco=struct.unpack_from('<I',b,q)[0]
        tc=content+tco
        if tc+32>len(b): continue
        cmds=[struct.unpack_from('<II',b,tc+8*j) for j in range(3)]
        fmt=b[tc+24]; mip=b[tc+25]
        nameoff=struct.unpack_from('<I',b,tc+28)[0]
        np=string+nameoff
        if 0<=np<len(b):
            ne=b.find(b'\0',np,min(len(b),np+256)); ne=len(b) if ne<0 else ne
            name=b[np:ne].decode('ascii','replace')
        else:name=f'tex{ti}'
        infos=[]; seen=set()
        for elem,count in cmds:
            if not count: continue
            cp=command+elem; k=0; W=H=0; cf=None; addrs=[]
            while k<count and cp+4*(k+1)<len(b):
                val,cmd=struct.unpack_from('<II',b,cp+4*k)
                addr=cmd&0xffff; sz=((cmd>>20)&0xff)+1
                if addr in (0x82,0x92,0x9a): W=(val>>16)&0xffff; H=val&0xffff
                elif addr in (0x85,0x86,0x87,0x88,0x89,0x8a,0x95,0x9d):
                    if val not in seen: seen.add(val); addrs.append(val)
                elif addr in (0x8e,0x96,0x9e): cf=val
                k += ((sz+1)+1)&~1
            for a in addrs:
                if W and H and cf is not None:
                    infos.append({'width':W,'height':H,'format':cf,'offset':a,'abs_offset':raw+a})
        # often format byte is authoritative
        for x in infos: x['format']=fmt if fmt in range(14) else x['format']
        out.append({'index':ti,'name':name,'format':fmt,'mipmap':mip,'content_offset':tc,'textures':infos,'raw_section':raw})
    return out

def _etc_decode_block(bb):
    x=int.from_bytes(bb,'big'); diff=(x>>33)&1; flip=(x>>32)&1; t1=(x>>37)&7; t2=(x>>34)&7
    if diff:
        r1=(x>>59)&31; g1=(x>>51)&31; b1=(x>>43)&31
        sd=lambda z:z-8 if z&4 else z
        r2=r1+sd((x>>56)&7);g2=g1+sd((x>>48)&7);b2=b1+sd((x>>40)&7)
        ex=lambda v:(v<<3)|(v>>2)
        c1=(ex(r1),ex(g1),ex(b1));c2=(ex(max(0,min(31,r2))),ex(max(0,min(31,g2))),ex(max(0,min(31,b2))))
    else:
        ex=lambda v:(v<<4)|v
        c1=(ex((x>>60)&15),ex((x>>52)&15),ex((x>>44)&15))
        c2=(ex((x>>56)&15),ex((x>>48)&15),ex((x>>40)&15))
    lo=x&0xffffffff; pix=[]
    for y in range(4):
      row=[]
      for xx in range(4):
        k=xx*4+y; idx=((lo>>(k+16))&1)*2+((lo>>k)&1)
        second=(y>=2) if flip else (xx>=2); base=c2 if second else c1; tab=t2 if second else t1; m=MODS[tab][idx]
        row.append(tuple(_clamp(v+m) for v in base))
      pix.append(row)
    return pix

def decode_texture(b,info):
    w,h,fmt,off=info['width'],info['height'],info['format'],info['abs_offset']
    if fmt not in (12,13): raise NotImplementedError(fmt)
    size=w*h*(1 if fmt==13 else .5); raw=b[off:off+int(size)]
    rgba=[[(0,0,0,255) for _ in range(w)] for __ in range(h)]
    # 8x8 macrotiles, 4 ETC blocks each; format13 interleaves alpha+color for each 4x4 block
    p=0
    for my in range(0,h,8):
      for mx in range(0,w,8):
        for by,bx in ((0,0),(0,4),(4,0),(4,4)):
          if fmt==13:
            ab=raw[p:p+8]; cb=raw[p+8:p+16]; p+=16
          else: ab=None;cb=raw[p:p+8];p+=8
          # 3DS stores each standard ETC block byte-reversed
          col=_etc_decode_block(cb[::-1])
          alpha=[255]*16
          if ab is not None:
            # ordering within alpha bytes matches bchtool's 4x4 packing
            vals=[]
            for j in range(4): vals.append((ab[j*2]&15)*17)
            for j in range(4): vals.append(((ab[j*2]>>4)&15)*17)
            for j in range(4): vals.append((ab[j*2+1]&15)*17)
            for j in range(4): vals.append(((ab[j*2+1]>>4)&15)*17)
            alpha=vals
          for yy in range(4):
            for xx in range(4):
              y=my+by+yy;x=mx+bx+xx
              if y<h and x<w:
                r,g,bl=col[yy][xx];rgba[y][x]=(r,g,bl,alpha[yy*4+xx])
    im=Image.new('RGBA',(w,h)); im.putdata([v for row in rgba for v in row]); return im

def _q4(v): return max(0,min(15,int(round(v/17))))
def _encode_subblock(pixels):
    # Fast ETC1 encoder tuned for flat 3DS UI textures. Quantize the mean base
    # once, then select the best modifier table/index per pixel. This avoids the
    # expensive 3x3x3 local-base search and is visually adequate for text/UI.
    mean=[sum(p[2+c] for p in pixels)/len(pixels) for c in range(3)]
    qq=[_q4(v) for v in mean]; base=[z*17 for z in qq]
    best=None
    for t,mods in enumerate(MODS):
        err=0; inds={}
        for x,y,r,g,b in pixels:
            be=None
            for idx,m in enumerate(mods):
                cc=[_clamp(v+m) for v in base]; e=(r-cc[0])**2+(g-cc[1])**2+(b-cc[2])**2
                if be is None or e<be[0]:be=(e,idx)
            err+=be[0];inds[(x,y)]=be[1]
        if best is None or err<best[0]:best=(err,qq,t,inds)
    return best

def _etc_encode_block(pix):
    bestall=None
    for flip in (0,1):
      p1=[];p2=[]
      for y in range(4):
       for x in range(4):
        r,g,b=pix[y][x][:3]; (p2 if ((y>=2) if flip else (x>=2)) else p1).append((x,y,r,g,b))
      a=_encode_subblock(p1);c=_encode_subblock(p2);err=a[0]+c[0]
      if bestall is None or err<bestall[0]:bestall=(err,flip,a,c)
    _,flip,a,c=bestall; q1,t1,ind1=a[1],a[2],a[3];q2,t2,ind2=c[1],c[2],c[3]
    hi=(q1[0]<<28)|(q2[0]<<24)|(q1[1]<<20)|(q2[1]<<16)|(q1[2]<<12)|(q2[2]<<8)|(t1<<5)|(t2<<2)|(0<<1)|flip
    lo=0
    inds={**ind1,**ind2}
    for y in range(4):
      for x in range(4):
       idx=inds[(x,y)];k=x*4+y;lo|=(idx&1)<<k;lo|=((idx>>1)&1)<<(k+16)
    return ((hi<<32)|lo).to_bytes(8,'big')

def encode_texture(im,fmt):
    im=im.convert('RGBA');w,h=im.size; px=im.load();out=bytearray()
    if fmt not in (12,13):raise NotImplementedError(fmt)
    for my in range(0,h,8):
      for mx in range(0,w,8):
       for by,bx in ((0,0),(0,4),(4,0),(4,4)):
        block=[]; al=[]
        for yy in range(4):
         row=[]
         for xx in range(4):
          r,g,b,a=px[min(w-1,mx+bx+xx),min(h-1,my+by+yy)];row.append((r,g,b,a));al.append(a)
         block.append(row)
        cb=_etc_encode_block(block)[::-1]
        if fmt==13:
         aa=[max(0,min(15,int(round(v/17)))) for v in al];ab=bytearray(8)
         for j in range(4):
          ab[j*2]=(aa[j]&15)|((aa[j+4]&15)<<4)
          ab[j*2+1]=(aa[j+8]&15)|((aa[j+12]&15)<<4)
         out.extend(ab);out.extend(cb)
        else:out.extend(cb)
    return bytes(out)

def replace_texture(b,info,im):
    enc=encode_texture(im,info['format']); off=info['abs_offset']; expected=info['width']*info['height']*(1 if info['format']==13 else 1)//(1 if info['format']==13 else 2)
    if len(enc)!=expected:raise ValueError((len(enc),expected))
    out=bytearray(b);out[off:off+len(enc)]=enc;return bytes(out)
