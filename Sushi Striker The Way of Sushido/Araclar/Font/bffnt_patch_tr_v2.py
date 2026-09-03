#!/usr/bin/env python3
from pathlib import Path
import struct, statistics
from PIL import Image, ImageDraw, ImageChops

TR_TARGETS=['Ğ','ğ','İ','ı','Ş','ş']
BASE_FOR={'Ğ':'G','ğ':'g','İ':'I','ı':'i','Ş':'S','ş':'s'}
# These are present in the sparse CMAP of the European embedded fonts, but are
# absent from all 243 localization CSVs. They are used only as fixed-size slots.
SACRIFICE=[0x2020,0x2021,0x2030,0x2039,0x203A,0x201A]


def morton8(x,y):
    return ((x&1)|((y&1)<<1)|((x&2)<<1)|((y&2)<<2)|((x&4)<<2)|((y&4)<<3))

def nib_index(x,y,w):
    return ((y//8)*(w//8)+(x//8))*64 + morton8(x&7,y&7)

def parse(data):
    if data[:4] != b'FFNT':
        raise ValueError('not FFNT')
    e = '<' if data[4:6] == b'\xff\xfe' else '>'
    finf = struct.unpack_from(e+'4sI4B2H4B3I', data, 20)
    tpos,wpos,cpos = finf[-3]-8, finf[-2]-8, finf[-1]-8
    t = struct.unpack_from(e+'4sI4BI6HI', data, tpos)
    _,_,cw,ch,ns,maxw,ss,baseline,fmt,cols,rows,sw,sh,dataoff=t
    mapping={}; sparse=[]; pos=cpos
    while pos:
        magic,size,start,end,method,res,nxt=struct.unpack_from(e+'4sI4HI',data,pos); q=pos+20
        if magic != b'CMAP': raise ValueError('invalid CMAP')
        if method==0:
            idx=struct.unpack_from(e+'H',data,q)[0]
            for cp in range(start,end+1): mapping[cp]=idx+cp-start
        elif method==1:
            vals=struct.unpack_from(e+f'{end-start+1}H',data,q)
            for i,v in enumerate(vals):
                if v!=0xffff: mapping[start+i]=v
        elif method==2:
            cnt=struct.unpack_from(e+'H',data,q)[0]; q+=2
            for i in range(cnt):
                ep=q+i*4; cp,idx=struct.unpack_from(e+'HH',data,ep)
                mapping[cp]=idx; sparse.append((cp,idx,ep))
        pos=nxt-8 if nxt else 0
    widths={}; widthpos={}; pos=wpos
    while pos:
        magic,size,start,end,nxt=struct.unpack_from(e+'4sI2HI',data,pos); q=pos+16
        if magic != b'CWDH': raise ValueError('invalid CWDH')
        for idx in range(start,end+1):
            pp=q+(idx-start)*3
            widths[idx]=struct.unpack_from('bbb',data,pp); widthpos[idx]=pp
        pos=nxt-8 if nxt else 0
    return {
        'e':e,'cw':cw,'ch':ch,'ns':ns,'maxw':maxw,'ss':ss,'baseline':baseline,
        'fmt':fmt,'cols':cols,'rows':rows,'sw':sw,'sh':sh,'dataoff':dataoff,
        'mapping':mapping,'sparse':sparse,'widths':widths,'widthpos':widthpos
    }

def glyph_origin(info,idx):
    per=info['cols']*info['rows']; si=idx//per; j=idx%per
    return si,(j%info['cols'])*(info['cw']+1),(j//info['cols'])*(info['ch']+1)

def extract_glyph(data,info,idx):
    si,ox,oy=glyph_origin(info,idx)
    im=Image.new('L',(info['cw'],info['ch']),0); p=im.load(); base=info['dataoff']+si*info['ss']
    for y in range(info['ch']):
        for x in range(info['cw']):
            ni=nib_index(ox+x,oy+y,info['sw']); bb=data[base+ni//2]
            v=(bb&15) if ni%2==0 else (bb>>4); p[x,y]=v*17
    return im

def write_glyph(out,info,idx,im):
    si,ox,oy=glyph_origin(info,idx); p=im.load(); base=info['dataoff']+si*info['ss']
    for y in range(info['ch']):
        for x in range(info['cw']):
            ni=nib_index(ox+x,oy+y,info['sw']); bi=base+ni//2
            v=max(0,min(15,int(round(p[x,y]/17))))
            if ni%2==0: out[bi]=(out[bi]&0xf0)|v
            else: out[bi]=(out[bi]&0x0f)|(v<<4)

def _bbox_top(im):
    b=im.getbbox(); return b[1] if b else 0

def _xheight_top(imgs):
    vals=[]
    for c in 'aceosuvxznmr':
        if c in imgs and imgs[c].getbbox(): vals.append(imgs[c].getbbox()[1])
    return int(round(statistics.median(vals))) if vals else _bbox_top(imgs['i'])+4

def dotless_i_v2(imgs):
    """Build a real dotless i. The old patch removed disconnected components,
    but these A4 fonts connect the i dot to the stem via anti-aliasing, so the
    dot survived. V2 detects the long lower stem run and removes the upper run."""
    src=imgs['i'].copy(); w,h=src.size
    # Identify high-opacity row runs; the longest lower run is the stem.
    active=[]
    for y in range(h):
        mx=max(src.getpixel((x,y)) for x in range(w))
        active.append(mx>=180)
    runs=[]; s=None
    for y,v in enumerate(active+[False]):
        if v and s is None: s=y
        elif not v and s is not None:
            runs.append((s,y-1)); s=None
    if runs:
        # Prefer the longest run; tie -> lower one.
        stem=max(runs,key=lambda r:(r[1]-r[0]+1,r[0]))
        start=stem[0]
    else:
        start=_xheight_top(imgs)+1
    # Sanity: stem should begin around x-height, never at cap/dot height.
    xt=_xheight_top(imgs)
    start=max(start,xt)
    out=src.copy(); p=out.load()
    for y in range(start):
        for x in range(w): p[x,y]=0
    # Add one soft anti-aliased cap row, matching the stem rather than the dot.
    if start>0:
        for x in range(w): p[x,start-1]=int(p[x,start]*0.45)
    return out

def _components_mask(im,threshold=20):
    w,h=im.size; px=im.load(); seen=set(); res=[]
    for y in range(h):
        for x in range(w):
            if (x,y) in seen or px[x,y]<threshold: continue
            st=[(x,y)]; seen.add((x,y)); pts=[]
            while st:
                a,b=st.pop(); pts.append((a,b))
                for nx,ny in ((a-1,b),(a+1,b),(a,b-1),(a,b+1),(a-1,b-1),(a+1,b-1),(a-1,b+1),(a+1,b+1)):
                    if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and px[nx,ny]>=threshold:
                        seen.add((nx,ny)); st.append((nx,ny))
            res.append(pts)
    return res

def dotted_I_v2(imgs):
    """Use one native umlaut dot from Ä as the dot on capital İ so size,
    anti-aliasing and accent height match the font's own European accents."""
    base=imgs['I'].copy(); w,h=base.size
    if 'Ä' not in imgs or 'A' not in imgs:
        return dotted_I_fallback(base)
    a_top=_bbox_top(imgs['A'])
    accent=imgs['Ä'].copy(); ap=accent.load()
    for y in range(a_top,h):
        for x in range(w): ap[x,y]=0
    # Split the umlaut into left/right halves and take a full-alpha bbox.
    # This preserves faint A4 edge pixels that a connected-component threshold can lose.
    ab=imgs['A'].getbbox() or (0,0,w,h); mid=max(1,min(w-1,(ab[0]+ab[2])//2))
    halves=[]
    for xlo,xhi in ((0,mid),(mid,w)):
        part=accent.crop((xlo,0,xhi,a_top)); pb=part.getbbox()
        if pb:
            crop=part.crop(pb); halves.append((crop,pb[1]))
    if not halves:
        return dotted_I_fallback(base)
    dot,py=min(halves,key=lambda t:t[0].width*t[0].height)
    ib=base.getbbox() or (0,0,w,h); cx=(ib[0]+ib[2]-1)/2
    px=int(round(cx-dot.width/2))
    layer=Image.new('L',(w,h),0); layer.paste(dot,(px,py))
    return ImageChops.lighter(base,layer)

def dotted_I_fallback(base):
    out=base.copy();w,h=out.size;bb=out.getbbox() or(0,0,w,h);x0,y0,x1,y1=bb;cx=(x0+x1-1)/2
    scale=4;lay=Image.new('L',(w*scale,h*scale),0);d=ImageDraw.Draw(lay);r=max(1.0,min(2.0,h/17));cy=max(r+.5,y0-2.2)
    d.ellipse(((cx-r)*scale,(cy-r)*scale,(cx+r)*scale,(cy+r)*scale),fill=255)
    lay=lay.resize((w,h),Image.Resampling.LANCZOS)
    return ImageChops.lighter(out,lay)

def cedilla(accented,base):
    w,h=accented.size;bb=base.getbbox() or (0,0,w,h);cut=max(0,bb[3]-1)
    out=Image.new('L',(w,h),0);a=accented.load();o=out.load()
    for y in range(cut,h):
        for x in range(w):
            if a[x,y]>20:o[x,y]=a[x,y]
    return out

def breve(base, upper_ref=None):
    out=base.copy();w,h=out.size;bb=out.getbbox() or (0,0,w,h);x0,y0,x1,y1=bb;center=(x0+x1-1)/2
    # Match the vertical accent zone of Á/Ä where possible.
    ref_top=_bbox_top(upper_ref) if upper_ref is not None and upper_ref.getbbox() else max(1,y0-4)
    avail=max(3,y0-ref_top)
    bw=max(5,min(w-4,int((x1-x0)*.55))); depth=max(1.2,min(2.4,avail*.45)); scale=4
    lay=Image.new('L',(w*scale,h*scale),0);d=ImageDraw.Draw(lay)
    left=int((center-bw/2)*scale);right=int((center+bw/2)*scale);yy=int((ref_top+0.75)*scale)
    pts=[]
    for i in range(max(2,right-left+1)):
        x=left+i;t=i/max(1,right-left);y=yy+int((1-(2*t-1)**2)*depth*scale);pts.append((x,y))
    d.line(pts,fill=255,width=max(3,int(scale*.9)))
    lay=lay.resize((w,h),Image.Resampling.LANCZOS)
    return ImageChops.lighter(out,lay)

def patch_font(data):
    info=parse(data);m=info['mapping'];missing=[ch for ch in TR_TARGETS if ord(ch) not in m]
    if not missing:return data,{'patched':False,'reason':'complete','missing_before':[]}
    required='GgIiSsCcÇçAaÄä'
    if info['fmt']!=11 or any(ord(c) not in m for c in required):
        return data,{'patched':False,'reason':'unsuitable','missing_before':missing,'fmt':info['fmt']}
    bycp={cp:(idx,pos) for cp,idx,pos in info['sparse']};choices=[cp for cp in SACRIFICE if cp in bycp]
    if len(choices)<len(missing):return data,{'patched':False,'reason':'no safe slots','missing_before':missing}
    want=set(required+'aceosuvxznmr')
    imgs={c:extract_glyph(data,info,m[ord(c)]) for c in want if ord(c) in m}
    made={
        'Ğ':breve(imgs['G'],imgs.get('Á') or imgs.get('Ä')),
        'ğ':breve(imgs['g'],imgs.get('á') or imgs.get('ä')),
        'İ':dotted_I_v2(imgs),
        'ı':dotless_i_v2(imgs),
        'Ş':ImageChops.lighter(imgs['S'],cedilla(imgs['Ç'],imgs['C'])),
        'ş':ImageChops.lighter(imgs['s'],cedilla(imgs['ç'],imgs['c']))
    }
    out=bytearray(data);assigned={}
    for ch,sac in zip(missing,choices):
        idx,ep=bycp[sac]
        struct.pack_into(info['e']+'H',out,ep,ord(ch));write_glyph(out,info,idx,made[ch])
        bidx=m[ord(BASE_FOR[ch])]
        if idx in info['widthpos']:
            struct.pack_into('bbb',out,info['widthpos'][idx],*info['widths'][bidx])
        assigned[ch]={'glyph':idx,'replaced_cp':f'U+{sac:04X}','base':BASE_FOR[ch]}
    ni=parse(bytes(out));still=[ch for ch in TR_TARGETS if ord(ch) not in ni['mapping']]
    if still:raise ValueError('still missing '+''.join(still))
    # The synthetic dotless i must be visually distinct from i.
    if 'ı' in assigned:
        ii=extract_glyph(bytes(out),ni,ni['mapping'][ord('i')]); di=extract_glyph(bytes(out),ni,ni['mapping'][ord('ı')])
        if list(ii.getdata())==list(di.getdata()): raise ValueError('dotless i still equals i')
    return bytes(out),{'patched':True,'missing_before':missing,'assigned':assigned,'cell':[info['cw'],info['ch']],'baseline':info['baseline']}

if __name__=='__main__':
    import sys,json
    src,dst=sys.argv[1:3];p,r=patch_font(Path(src).read_bytes());Path(dst).write_bytes(p);print(json.dumps(r,ensure_ascii=False,indent=2))
