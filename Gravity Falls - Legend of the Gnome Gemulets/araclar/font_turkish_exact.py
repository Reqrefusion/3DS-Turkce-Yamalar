#!/usr/bin/env python3
from __future__ import annotations
import argparse, struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

TR = "ÇĞİÖŞÜçğıöşü"
TARGETS = {
    'Ğ': ('G', 0x0192),
    'ğ': ('g', 0x02C6),
    'İ': ('I', 0x02DC),
    'ı': ('i', 0x2030),
    'Ş': ('S', 0x2039),
    'ş': ('s', 0x203A),
}

# ---------- shared drawing helpers ----------
def overlay(dst: Image.Image, src: Image.Image, xy=(0,0)) -> None:
    tmp = Image.new('L', dst.size, 0)
    tmp.paste(src, xy)
    dst.paste(ImageChops.lighter(dst, tmp))

def aa_arc(size, box, start, end, width=1, scale=4):
    hi = Image.new('L', (size[0]*scale, size[1]*scale), 0)
    d = ImageDraw.Draw(hi)
    b = tuple(int(v*scale) for v in box)
    d.arc(b, start=start, end=end, fill=255, width=max(1,int(width*scale)))
    return hi.resize(size, Image.Resampling.LANCZOS)

def aa_ellipse(size, box, scale=4):
    hi = Image.new('L', (size[0]*scale, size[1]*scale), 0)
    d = ImageDraw.Draw(hi)
    b = tuple(int(v*scale) for v in box)
    d.ellipse(b, fill=255)
    return hi.resize(size, Image.Resampling.LANCZOS)

# ---------- BCFNT ----------
def endian_bcfnt(data: bytes) -> str:
    if data[:4] not in (b'CFNT', b'TNFC', b'CFNU'):
        raise ValueError('Not CFNT/BCFNT')
    if data[4:6] == b'\xff\xfe': return '<'
    if data[4:6] == b'\xfe\xff': return '>'
    raise ValueError('Unknown BCFNT byte order')

def cmap_blocks(data: bytes, order: str):
    finf=data.find(b'FINF')
    ptr=struct.unpack_from(order+'I',data,finf+0x18)[0]
    off=ptr-8; seen=set(); out=[]
    while off and off not in seen:
        seen.add(off)
        vals=struct.unpack_from(order+'4sIHHHHI',data,off)
        if vals[0]!=b'CMAP': raise ValueError('Bad CMAP')
        out.append((off,*vals[1:]))
        off=vals[-1]-8 if vals[-1] else 0
    return out

def parse_bcfnt_mapping(data: bytes):
    order=endian_bcfnt(data); mapping={}; blocks=cmap_blocks(data,order)
    for off,size,begin,end,method,reserved,nxt in blocks:
        p=off+20
        if method==0:
            idx0=struct.unpack_from(order+'H',data,p)[0]
            for cp in range(begin,end+1): mapping[cp]=idx0+cp-begin
        elif method==1:
            vals=struct.unpack_from(order+'H'*(end-begin+1),data,p)
            for cp,idx in zip(range(begin,end+1),vals):
                if idx!=0xFFFF: mapping[cp]=idx
        elif method==2:
            count=struct.unpack_from(order+'H',data,p)[0]; p+=2
            for _ in range(count):
                cp,idx=struct.unpack_from(order+'HH',data,p);p+=4;mapping[cp]=idx
        else: raise ValueError('Unknown CMAP method')
    return order,mapping,blocks

def morton8(x,y):
    r=0
    for b in range(3):
        r|=((x>>b)&1)<<(2*b); r|=((y>>b)&1)<<(2*b+1)
    return r

def bcfnt_decode_sheet(src: bytes,w:int,h:int)->Image.Image:
    out=bytearray(w*h)
    for y in range(h):
        for x in range(w):
            idx=((y//8)*(w//8)+(x//8))*64+morton8(x&7,y&7)
            out[y*w+x]=src[idx]
    return Image.frombytes('L',(w,h),bytes(out))

def bcfnt_encode_sheet(im:Image.Image)->bytes:
    w,h=im.size; src=im.tobytes(); out=bytearray(w*h)
    for y in range(h):
        for x in range(w):
            idx=((y//8)*(w//8)+(x//8))*64+morton8(x&7,y&7)
            out[idx]=src[y*w+x]
    return bytes(out)

def build_bcfnt_cell(char, getcell, cw, ch):
    base_char=TARGETS[char][0]
    base=getcell(base_char).copy()
    out=base.copy()
    bb=base.getbbox() or (0,0,cw,ch)
    cx=(bb[0]+bb[2])/2
    if char in ('Ğ','ğ'):
        y0 = 1 if char=='Ğ' else 3
        markw = 7 if char=='Ğ' else 6
        markh = 4 if char=='Ğ' else 4
        mark=aa_arc((cw,ch),(cx-markw/2,y0,cx+markw/2,y0+markh),0,180,width=1.1)
        overlay(out,mark)
    elif char=='İ':
        mark=aa_ellipse((cw,ch),(cx-1.25,1.5,cx+1.25,4.0))
        overlay(out,mark)
    elif char=='ı':
        # Remove the lowercase-i dot while keeping its stem.
        out.paste(0,(0,0,cw,8))
    elif char in ('Ş','ş'):
        # Tiny comma-like cedilla; drawn at high resolution so the 19px BCFNT cell keeps a readable hook.
        hi=Image.new('L',(cw*6,ch*6),0); d=ImageDraw.Draw(hi); c=int(cx*6)
        pts=[(c,int(15.6*6)),(c-4,int(16.8*6)),(c+1,int(17.7*6)),(c-5,int(18.6*6))]
        d.line(pts,fill=255,width=5)
        overlay(out,hi.resize((cw,ch),Image.Resampling.LANCZOS))
    return out

def patch_bcfnt(inp:Path,outp:Path,preview:Path|None=None):
    data=bytearray(inp.read_bytes()); order,mapping,blocks=parse_bcfnt_mapping(data)
    t=data.find(b'TGLP')
    vals=struct.unpack_from(order+'4sI4BI6HI',data,t)
    _,secsize,cw,ch,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,W,H,dataoff=vals
    if fmt!=8: raise ValueError(f'Expected A8 BCFNT, got format {fmt}')
    sheets=[]
    for si in range(sheetcount):
        raw=data[dataoff+si*sheetsize:dataoff+(si+1)*sheetsize]
        sheets.append(bcfnt_decode_sheet(raw,W,H))
    per=cols*rows
    def cellpos(idx):
        si=idx//per;j=idx%per;x=(j%cols)*(cw+1);y=(j//cols)*(ch+1);return si,x,y
    def getcell(c):
        idx=mapping[ord(c)];si,x,y=cellpos(idx);return sheets[si].crop((x,y,x+cw,y+ch))
    def putcell(idx,im):
        si,x,y=cellpos(idx);sheets[si].paste(im,(x,y))
    donor_idx={}
    for c,(base,donor_cp) in TARGETS.items():
        if donor_cp not in mapping: raise ValueError(f'Donor U+{donor_cp:04X} missing')
        di=mapping[donor_cp]; donor_idx[ord(c)]=di
        putcell(di,build_bcfnt_cell(c,getcell,cw,ch))
    # Copy base glyph widths to donor glyph slots.
    cwdoff=data.find(b'CWDH')
    if cwdoff<0: raise ValueError('CWDH missing')
    _,cwdsize,beg,end,nxt=struct.unpack_from(order+'4sIHHI',data,cwdoff)
    for c,(base,_) in TARGETS.items():
        bi=mapping[ord(base)];di=donor_idx[ord(c)]
        if not (beg<=bi<=end and beg<=di<=end): raise ValueError('Glyph index outside CWDH')
        src=cwdoff+16+(bi-beg)*3; dst=cwdoff+16+(di-beg)*3
        data[dst:dst+3]=data[src:src+3]
    # Write edited A8 sheets.
    for si,im in enumerate(sheets):
        enc=bcfnt_encode_sheet(im)
        data[dataoff+si*sheetsize:dataoff+(si+1)*sheetsize]=enc
    # Add exact Unicode -> donor glyph mappings in terminal scan CMAP.
    last=blocks[-1]; off,size,begin,end,method,reserved,nxt=last
    if method!=2 or nxt!=0 or off+size!=len(data): raise ValueError('Terminal scan CMAP layout not expected')
    p=off+20; count=struct.unpack_from(order+'H',data,p)[0];p+=2
    pairs=[struct.unpack_from(order+'HH',data,p+i*4) for i in range(count)]
    dd=dict(pairs);dd.update(donor_idx);pairs=sorted(dd.items())
    body=bytearray(struct.pack(order+'H',len(pairs)))
    for cp,idx in pairs: body+=struct.pack(order+'HH',cp,idx)
    new_size=20+len(body); body+=b'\0'*((4-new_size%4)%4); new_size=20+len(body)
    block=bytearray(struct.pack(order+'4sIHHHHI',b'CMAP',new_size,begin,end,method,reserved,0))+body
    data=data[:off]+block;struct.pack_into(order+'I',data,0x0C,len(data))
    outp.write_bytes(data)
    _,m2,_=parse_bcfnt_mapping(data)
    miss=[c for c in TR if ord(c) not in m2]
    if miss: raise ValueError('BCFNT verification failed: '+''.join(miss))
    if preview:
        # Show the six constructed donor cells.
        imgs=[]
        # Re-decode from final in-memory sheets (already edited)
        for c in TARGETS:
            di=donor_idx[ord(c)];si,x,y=cellpos(di);imgs.append((c,sheets[si].crop((x,y,x+cw,y+ch))))
        scale=6; canvas=Image.new('L',(len(imgs)*cw*scale,ch*scale),0)
        for i,(c,im) in enumerate(imgs): canvas.paste(im.resize((cw*scale,ch*scale),Image.Resampling.NEAREST),(i*cw*scale,0))
        canvas.save(preview)
    return donor_idx

# ---------- UbiArt TFN + ETC1A4 alpha atlas ----------
MARK=struct.pack('>II',15,40); REC_SIZE=44

def tfn_records(data:bytes):
    out={};pos=0
    while True:
        i=data.find(MARK,pos)
        if i<0: break
        if i+REC_SIZE<=len(data):
            vals=struct.unpack_from('>11I',data,i);out[vals[2]]=(i,vals)
        pos=i+REC_SIZE
    if len(out)<100: raise ValueError('Unrecognized TFN')
    return out

def tex_dims(data:bytes):
    if data[4:8]!=b'TEX\0': raise ValueError('Unrecognized UbiArt TEX')
    w=struct.unpack_from('>H',data,0x10)[0];h=struct.unpack_from('>H',data,0x12)[0]
    payload_off=len(data)-w*h
    if payload_off<32 or len(data)-payload_off!=w*h: raise ValueError('Unexpected ETC1A4 payload size')
    return w,h,payload_off

def decode_tga_alpha(data:bytes):
    W,H,off=tex_dims(data);p=data[off:];im=Image.new('L',(W,H),0);px=im.load();pos=0
    bcoords=[(0,0),(1,0),(0,1),(1,1)]
    for ty in range(0,H,8):
        for tx in range(0,W,8):
            for bx,by in bcoords:
                a=p[pos:pos+8];pos+=16
                vals=[]
                for byte in a: vals.extend((byte&15,byte>>4))
                for j,v in enumerate(vals):
                    x=j//4;y=j%4;px[tx+bx*4+x,ty+by*4+y]=v*17
    return im.transpose(Image.Transpose.FLIP_TOP_BOTTOM),off

def encode_tga_alpha(original:bytes, flipped:Image.Image, off:int):
    W,H=flipped.size; raw=flipped.transpose(Image.Transpose.FLIP_TOP_BOTTOM);pix=raw.load();out=bytearray(original);pos=off
    bcoords=[(0,0),(1,0),(0,1),(1,1)]
    for ty in range(0,H,8):
        for tx in range(0,W,8):
            for bx,by in bcoords:
                vals=[]
                for j in range(16):
                    x=j//4;y=j%4;v=pix[tx+bx*4+x,ty+by*4+y]
                    vals.append(max(0,min(15,int(round(v/17)))))
                a=bytearray(8)
                for k in range(8): a[k]=vals[2*k] | (vals[2*k+1]<<4)
                out[pos:pos+8]=a;pos+=16
    return bytes(out)

def make_tfn_target(c, base_im:Image.Image, base_vals, source_records, atlas):
    _,_,cp,bx,by,bw,bh,xoff,yoff,adv,last=base_vals
    if c in ('Ğ','ğ'):
        extra=8; w=bw;h=bh+extra;out=Image.new('L',(w,h),0);out.paste(base_im,(0,extra));bb=base_im.getbbox() or (0,0,w,bh);cx=(bb[0]+bb[2])/2
        markw=11 if c=='Ğ' else 9;markh=6 if c=='Ğ' else 5
        overlay(out,aa_arc((w,h),(cx-markw/2,1,cx+markw/2,1+markh),0,180,width=2.0))
        return out,xoff,max(0,yoff-extra),adv
    if c=='İ':
        extra=6;w=bw;h=bh+extra;out=Image.new('L',(w,h),0);out.paste(base_im,(0,extra));bb=base_im.getbbox() or (0,0,w,bh);cx=(bb[0]+bb[2])/2
        overlay(out,aa_ellipse((w,h),(cx-2,1,cx+2,5)))
        return out,xoff,max(0,yoff-extra),adv
    if c=='ı':
        out=base_im.copy(); # remove dot: keep the stem/lower component only
        # Find horizontal rows with content; lowercase i has a gap between dot and stem.
        # Clearing the upper third is safe for this game's handwritten font.
        out.paste(0,(0,0,bw,max(8,bh//3)))
        return out,xoff,yoff,adv
    if c in ('Ş','ş'):
        extra=9;w=bw;h=bh+extra;out=Image.new('L',(w,h),0);out.paste(base_im,(0,0));bb=base_im.getbbox() or (0,0,w,bh);cx=(bb[0]+bb[2])/2
        # Hand-drawn cedilla hook, anti-aliased to the atlas' 4-bit alpha.
        hi=Image.new('L',(w*4,h*4),0);d=ImageDraw.Draw(hi);cx4=int(cx*4);y0=(bh-1)*4
        d.line([(cx4,y0),(cx4-4,y0+10),(cx4+4,y0+18),(cx4,y0+26),(cx4-5,y0+30)],fill=255,width=5)
        mark=hi.resize((w,h),Image.Resampling.LANCZOS);overlay(out,mark)
        return out,xoff,yoff,adv
    raise ValueError(c)

def patch_tfn(tfn_in:Path,tga_in:Path,tfn_out:Path,tga_out:Path,preview:Path|None=None):
    tfn=bytearray(tfn_in.read_bytes()); recs=tfn_records(tfn); tex=tga_in.read_bytes(); atlas,off=decode_tga_alpha(tex)
    # deterministic unused strip; all stock records stay above this area except tiny punctuation at x<64 in font66.
    x=80;y=456
    built=[]
    for c,(base,donor_cp) in TARGETS.items():
        if ord(base) not in recs or donor_cp not in recs: raise ValueError('Required TFN base/donor missing')
        boff,bvals=recs[ord(base)]; _,_,_,bx,by,bw,bh,*_=bvals;base_im=atlas.crop((bx,by,bx+bw,by+bh))
        target,xoff,yoff,adv=make_tfn_target(c,base_im,bvals,recs,atlas)
        tw,th=target.size
        x=(x+3)&~3
        if x+tw>512: x=80;y=((y+56+3)//4)*4
        if y+th>512: raise ValueError('No room for Turkish TFN glyphs')
        # Ensure target storage is blank before writing.
        if atlas.crop((x,y,x+tw,y+th)).getbbox(): raise ValueError(f'Target atlas area not blank for {c} at {x},{y}')
        atlas.paste(target,(x,y))
        doff,dvals=recs[donor_cp]
        newvals=(15,40,ord(c),x,y,tw,th,xoff,yoff,adv,0)
        struct.pack_into('>11I',tfn,doff,*newvals)
        built.append((c,x,y,tw,th))
        x += ((tw+7)//4)*4
    tga=encode_tga_alpha(tex,atlas,off)
    tfn_out.write_bytes(tfn);tga_out.write_bytes(tga)
    r2=tfn_records(tfn); miss=[c for c in TR if ord(c) not in r2]
    if miss: raise ValueError('TFN verification failed: '+''.join(miss))
    # Round-trip decoder verification at new rectangles.
    atlas2,_=decode_tga_alpha(tga)
    for c,x,y,w,h in built:
        if not atlas2.crop((x,y,x+w,y+h)).getbbox(): raise ValueError(f'Encoded glyph vanished: {c}')
    if preview:
        scale=2; gap=8; widths=[w*scale for _,_,_,w,_ in built]; maxh=max(h for *_,h in built)*scale
        canvas=Image.new('L',(sum(widths)+gap*(len(built)-1),maxh),0);xx=0
        for c,x,y,w,h in built:
            im=atlas2.crop((x,y,x+w,y+h)).resize((w*scale,h*scale),Image.Resampling.NEAREST);canvas.paste(im,(xx,0));xx+=w*scale+gap
        canvas.save(preview)
    return built

def main():
    ap=argparse.ArgumentParser(description='Create real Turkish glyphs for Gravity Falls 3DS fonts')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('bcfnt');p.add_argument('input');p.add_argument('output');p.add_argument('--preview')
    p=sp.add_parser('tfn');p.add_argument('tfn_input');p.add_argument('tga_input');p.add_argument('tfn_output');p.add_argument('tga_output');p.add_argument('--preview')
    a=ap.parse_args()
    if a.cmd=='bcfnt': patch_bcfnt(Path(a.input),Path(a.output),Path(a.preview) if a.preview else None)
    else: patch_tfn(Path(a.tfn_input),Path(a.tga_input),Path(a.tfn_output),Path(a.tga_output),Path(a.preview) if a.preview else None)
if __name__=='__main__': main()
