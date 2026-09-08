#!/usr/bin/env python3
from pathlib import Path
import re, zlib, zipfile, json, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path('/mnt/data')
ORIG=ROOT/'lm2_crash_compare/rom/fe/febundlefonts_res.data'
V3=ROOT/'LM2_TR_CRASHFIX_V3/Luigis_Mansion_2_TR_CRASHFIX_V3_FULL_FONT.zip'
OUTDIR=ROOT/'LM2_TR_FONTFIX_V4'

MIP_DIMS=[256,128,64,32,16]
MIP_SIZES=[d*d for d in MIP_DIMS]
PAGE_SIZE=sum(MIP_SIZES) # 87296
DESC_OFF=152
TEX_OFF=1912
TEX_END=77872

# ETC1 modifier tables
MOD=[
 [2,8,-2,-8],[5,17,-5,-17],[9,29,-9,-29],[13,42,-13,-42],
 [18,60,-18,-60],[24,80,-24,-80],[33,106,-33,-106],[47,183,-47,-183],
]

def clamp(v): return max(0,min(255,int(v)))

def parse_desc(desc,start):
    end=desc.find(b'\0',start)
    if end<0: end=len(desc)
    txt=desc[start:end].decode('latin1')
    ps=int(re.search(r'PageSize (\d+)',txt).group(1))
    pc=int(re.search(r'PageCount (\d+)',txt).group(1))
    rh=int(re.search(r'RenderHeight (\d+)',txt).group(1))
    glyphs=[]
    for line in txt.splitlines():
        if not line.startswith('Glyph '): continue
        m=re.match(r'Glyph (.+?) Width (-?\d+) (-?\d+) (-?\d+)$',line)
        tok=m.group(1)
        cp=int(tok) if tok.isdigit() and len(tok)>=3 else (ord(tok) if len(tok)==1 else int(tok))
        w,rw,xo=map(int,m.groups()[1:])
        glyphs.append([cp,w,rw,xo,line])
    x=y=pg=0; pos={}
    for cp,w,rw,xo,_ in glyphs:
        if x+rw>ps:
            x=0; y+=rh
        if y+rh>ps:
            pg+=1; x=y=0
        pos[cp]=(pg,x,y,w,rw,xo,rh)
        x+=rw
    return dict(start=start,end=end,text=txt,ps=ps,pc=pc,rh=rh,glyphs=glyphs,pos=pos)

def decode_alpha_mip(raw,dim):
    out=np.zeros((dim,dim),dtype=np.uint8)
    blocks=dim//4; tiles_x=dim//8
    for by in range(blocks):
        for bx in range(blocks):
            tx,ty=bx//2,by//2; ix,iy=bx%2,by%2
            bi=(ty*tiles_x+tx)*4 + ix+2*iy
            dat=raw[bi*16:bi*16+8]
            vals=[]
            for b in dat: vals += [b&0xF,b>>4]
            for y in range(4):
                for x in range(4):
                    out[by*4+y,bx*4+x]=vals[x*4+y]*17
    return np.flipud(out)

def encode_alpha_mip_visual(vis):
    dim=vis.shape[0]; raw=np.flipud(vis)
    out=bytearray(dim*dim)
    blocks=dim//4; tiles_x=dim//8
    for by in range(blocks):
        for bx in range(blocks):
            tx,ty=bx//2,by//2; ix,iy=bx%2,by%2
            bi=(ty*tiles_x+tx)*4 + ix+2*iy
            vals=[0]*16
            for y in range(4):
                for x in range(4):
                    vals[x*4+y]=max(0,min(15,int(round(int(raw[by*4+y,bx*4+x])/17))))
            for j in range(0,16,2):
                out[bi*16+j//2]=vals[j] | (vals[j+1]<<4)
    return out

def encode_etc1_gray_block(gray):
    """Simple valid ETC1 individual-mode encoder for a 4x4 grayscale block.
    Pixel selector layout is chosen to match LM2's ETC1 block ordering.
    """
    gray=np.asarray(gray,dtype=np.int16)
    best=None
    for flip in (0,1):
        subs=[]; total=0
        for s in (0,1):
            coords=[]
            for y in range(4):
                for x in range(4):
                    sec=(y>=2) if flip else (x>=2)
                    if int(sec)==s: coords.append((x,y))
            sbest=None
            for q in range(16):
                base=q*17
                for tab in range(8):
                    err=0; inds={}
                    for x,y in coords:
                        tgt=int(gray[y,x]); vals=[clamp(base+m) for m in MOD[tab]]
                        idx=min(range(4),key=lambda i:(vals[i]-tgt)**2)
                        err+=(vals[idx]-tgt)**2; inds[(x,y)]=idx
                    if sbest is None or err<sbest[0]: sbest=(err,q,tab,inds)
            subs.append(sbest); total+=sbest[0]
        if best is None or total<best[0]: best=(total,flip,subs)
    _,flip,subs=best
    q1,tab1,inds1=subs[0][1],subs[0][2],subs[0][3]
    q2,tab2,inds2=subs[1][1],subs[1][2],subs[1][3]
    hi=(q1<<28)|(q2<<24)|(q1<<20)|(q2<<16)|(q1<<12)|(q2<<8)|(tab1<<5)|(tab2<<2)|flip
    lo=0
    inds={**inds1,**inds2}
    for (x,y),idx in inds.items():
        # LM2/PICA selector orientation. Decoder relation was verified against
        # the original atlas' black-glyph/white-background correlation.
        k=x*4+(3-y)
        b0=(idx>>1)&1; b1=idx&1
        lo |= b0<<k
        lo |= b1<<(k+16)
    return hi.to_bytes(4,'big')+lo.to_bytes(4,'big')

def glyph_crop(pages,info,global_offset,cp):
    pg,x,y,w,rw,xo,rh=info['pos'][cp]
    return pages[global_offset+pg][y:y+rh,x:x+rw].copy(), (pg,x,y,w,rw,xo,rh)

def comp_remove_dot(img):
    # dot and stem are separated by at least one blank row in both LM2 fonts.
    rows=np.where((img>0).any(axis=1))[0]
    groups=[]
    if len(rows):
        st=pr=rows[0]
        for r in rows[1:]:
            if r>pr+1: groups.append((st,pr)); st=r
            pr=r
        groups.append((st,pr))
    out=img.copy()
    if len(groups)>=2:
        out[groups[0][0]:groups[0][1]+1,:]=0
    return out

def nonzero_bbox(a):
    yy,xx=np.where(a>0)
    if not len(xx): return None
    return (int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))

def extract_cedilla(pages,info,off,base_cp,ced_cp):
    base,_=glyph_crop(pages,info,off,base_cp)
    ced,_=glyph_crop(pages,info,off,ced_cp)
    bb=nonzero_bbox(base); cutoff=bb[3]
    tmp=ced.copy(); tmp[:cutoff,:]=0
    bb2=nonzero_bbox(tmp)
    return tmp[bb2[1]:bb2[3],bb2[0]:bb2[2]], bb2[0], bb2[1]

def extract_dot(pages,info,off):
    i,_=glyph_crop(pages,info,off,ord('i'))
    rows=np.where((i>0).any(axis=1))[0]
    st=rows[0]; en=st
    for r in rows[1:]:
        if r>en+1: break
        en=r
    part=i[st:en+1]
    bb=nonzero_bbox(part)
    return part[bb[1]:bb[3],bb[0]:bb[2]]

def make_breve(pages,info,off):
    deg,_=glyph_crop(pages,info,off,176)
    bb=nonzero_bbox(deg); cr=deg[bb[1]:bb[3],bb[0]:bb[2]]
    # Use the lower four rows of the game's own degree-ring curve and
    # symmetrise it. This yields a rounded breve using native antialiasing.
    if cr.shape[0]>=6: br=cr[2:6].copy()
    else: br=cr[max(0,cr.shape[0]-4):].copy()
    br=np.maximum(br,np.fliplr(br))
    return br

def place_center(dst,src,y,center_x):
    x=int(round(center_x-(src.shape[1]-1)/2))
    x=max(0,min(dst.shape[1]-src.shape[1],x))
    y=max(0,min(dst.shape[0]-src.shape[0],y))
    h,w=src.shape
    dst[y:y+h,x:x+w]=np.maximum(dst[y:y+h,x:x+w],src)

def build_target(slot_rw,rh,base,kind,pages,info,off):
    dst=np.zeros((rh,slot_rw),dtype=np.uint8)
    # copy as much of the base slot as fits. Visible pixels of S/s fit even
    # in the one-pixel narrower repurposed slots.
    bw=min(slot_rw,base.shape[1])
    dst[:,:bw]=base[:,:bw]
    if kind=='dotless':
        clean=comp_remove_dot(base)
        dst[:]=0; dst[:,:min(slot_rw,clean.shape[1])]=clean[:,:min(slot_rw,clean.shape[1])]
    elif kind=='Idot':
        dot=extract_dot(pages,info,off)
        bb=nonzero_bbox(dst); center=(bb[0]+bb[2]-1)/2
        # Match the accent vertical zone of the original acute-I slot.
        acute,_=glyph_crop(pages,info,off,205)
        baseI,_=glyph_crop(pages,info,off,ord('I'))
        topI=nonzero_bbox(baseI)[1]
        tmp=acute.copy(); tmp[topI:]=0
        ab=nonzero_bbox(tmp)
        y=ab[1] if ab else max(0,topI-dot.shape[0]-1)
        place_center(dst,dot,y,center)
    elif kind in ('Sced','sced'):
        if kind=='Sced': ced,_,_=extract_cedilla(pages,info,off,ord('C'),199)
        else: ced,_,_=extract_cedilla(pages,info,off,ord('c'),231)
        bb=nonzero_bbox(dst); center=(bb[0]+bb[2]-1)/2
        # place immediately below main letter at same native vertical position
        y=bb[3]
        place_center(dst,ced,y,center)
    elif kind in ('Gbreve','gbreve'):
        br=make_breve(pages,info,off)
        bb=nonzero_bbox(dst); center=(bb[0]+bb[2]-1)/2
        y=max(0,bb[1]-br.shape[0]-1)
        place_center(dst,br,y,center)
    return dst

def modify_descriptor(desc):
    out=bytearray(desc)
    replacements={
        # start 288: narrow. Preserve original RenderWidth (3rd number after Width)
        288:{
            161:(305,4,8,1), 205:(304,5,9,1), 211:(286,12,16,1),
            218:(350,11,15,1),224:(351,8,14,1),225:(287,9,14,1),
        },
        # start 4184: Alor. Preserve original RenderWidth exactly.
        4184:{
            161:(305,5,10,1),205:(304,6,11,1),211:(286,16,21,1),
            218:(350,15,19,1),224:(351,11,18,1),225:(287,12,18,0),
        }
    }
    for start,repl in replacements.items():
        info=parse_desc(bytes(out),start)
        region=bytes(out[info['start']:info['end']]).decode('latin1')
        lines=region.splitlines(keepends=True)
        new=[]
        for line in lines:
            bare=line.rstrip('\r\n')
            eol=line[len(bare):]
            if bare.startswith('Glyph '):
                m=re.match(r'Glyph (.+?) Width (-?\d+) (-?\d+) (-?\d+)$',bare)
                tok=m.group(1)
                cp=int(tok) if tok.isdigit() and len(tok)>=3 else (ord(tok) if len(tok)==1 else int(tok))
                if cp in repl:
                    ncp,w,rw,xo=repl[cp]
                    bare=f'Glyph {ncp} Width {w} {rw} {xo}'
            new.append(bare+eol)
        nr=''.join(new).encode('latin1')
        oldlen=info['end']-info['start']
        if len(nr)!=oldlen:
            raise RuntimeError(f'descriptor length changed {start}: {len(nr)} != {oldlen}')
        out[info['start']:info['end']]=nr
    return bytes(out)

def build_font():
    blob=ORIG.read_bytes()
    desc=zlib.decompress(blob[DESC_OFF:])
    tex=zlib.decompress(blob[TEX_OFF:])
    if len(desc)!=8324 or len(tex)!=PAGE_SIZE*5: raise RuntimeError('unexpected font resource')
    narrow=parse_desc(desc,288); alor=parse_desc(desc,4184)
    # Texture page order is Alor (3 pages) then Alor_Narrow_Condensed (2 pages).
    page_offsets={'Alor':0,'Narrow':3}
    infos={'Alor':alor,'Narrow':narrow}
    pages=[]; mip_pages=[]
    for pg in range(5):
        po=pg*PAGE_SIZE; mo=0; arr=[]
        for dim,sz in zip(MIP_DIMS,MIP_SIZES):
            arr.append(decode_alpha_mip(tex[po+mo:po+mo+sz],dim)); mo+=sz
        mip_pages.append(arr); pages.append(arr[0])

    slotmap={305:161,304:205,286:211,350:218,351:224,287:225}
    basecp={305:ord('i'),304:ord('I'),286:ord('G'),350:ord('S'),351:ord('s'),287:ord('g')}
    kind={305:'dotless',304:'Idot',286:'Gbreve',350:'Sced',351:'sced',287:'gbreve'}
    target_rect_masks=[np.zeros((256,256),dtype=np.uint8) for _ in range(5)]
    target_records=[]
    # Start from original top pages.
    newtops=[p.copy() for p in pages]
    for font in ('Alor','Narrow'):
        info=infos[font]; off=page_offsets[font]
        for newcp,slotcp in slotmap.items():
            pg,x,y,wslot,rwslot,xoslot,rh=info['pos'][slotcp]
            base,_=glyph_crop(pages,info,off,basecp[newcp])
            target=build_target(rwslot,rh,base,kind[newcp],pages,info,off)
            gpg=off+pg
            newtops[gpg][y:y+rh,x:x+rwslot]=target
            target_rect_masks[gpg][y:y+rh,x:x+rwslot]=1
            target_records.append(dict(font=font,new_cp=newcp,char=chr(newcp),slot_cp=slotcp,page=gpg,x=x,y=y,rw=rwslot,rh=rh,kind=kind[newcp],bbox=nonzero_bbox(target)))

    # Build new mip alpha arrays. Preserve original mips outside changed glyph influence.
    new_mips=[]; masks_mips=[]
    for pg in range(5):
        parr=[newtops[pg]]; marr=[target_rect_masks[pg]]
        orig_top=Image.fromarray(pages[pg])
        new_top=Image.fromarray(newtops[pg])
        mask_top=Image.fromarray(target_rect_masks[pg]*255)
        for mi,dim in enumerate(MIP_DIMS[1:],1):
            o_pred=np.array(orig_top.resize((dim,dim),Image.Resampling.BOX))
            n_pred=np.array(new_top.resize((dim,dim),Image.Resampling.BOX))
            n_pred=(np.rint(n_pred/17)*17).clip(0,255).astype(np.uint8)
            o_pred=(np.rint(o_pred/17)*17).clip(0,255).astype(np.uint8)
            actual=mip_pages[pg][mi].copy()
            dm=(o_pred!=n_pred)
            actual[dm]=n_pred[dm]
            parr.append(actual)
            mm=np.array(mask_top.resize((dim,dim),Image.Resampling.BOX))>0
            marr.append(mm.astype(np.uint8))
        new_mips.append(parr); masks_mips.append(marr)

    # Build a native ETC1 lookup from the original atlas: for each 4-bit alpha
    # block pattern, retain the most common companion ETC1 block. This lets new
    # Turkish alpha shapes reuse the game's own colour/edge encoding instead of
    # introducing unrelated RGB data from the repurposed source glyph.
    from collections import defaultdict, Counter
    native_map=defaultdict(Counter)
    for pg0 in range(5):
        po0=pg0*PAGE_SIZE; mo0=0
        for dim0,sz0 in zip(MIP_DIMS,MIP_SIZES):
            ch=tex[po0+mo0:po0+mo0+sz0]
            for q in range(0,sz0,16):
                native_map[bytes(ch[q:q+8])][bytes(ch[q+8:q+16])]+=1
            mo0+=sz0
    native_best={k:v.most_common(1)[0][0] for k,v in native_map.items()}
    native_keys=list(native_best.keys())
    def alpha_vec(k):
        vv=[]
        for b in k: vv.extend((b&15,b>>4))
        return np.asarray(vv,dtype=np.int16)
    native_vec=np.stack([alpha_vec(k) for k in native_keys])
    nearest_cache={}
    def native_etc_for(alpha8):
        if alpha8 in native_best: return native_best[alpha8], True
        if alpha8 in nearest_cache: return nearest_cache[alpha8], False
        v=alpha_vec(alpha8)
        idx=int(np.abs(native_vec-v).sum(axis=1).argmin())
        e=native_best[native_keys[idx]]
        nearest_cache[alpha8]=e
        return e, False

    # Rebuild texture stream. Patch A4 exactly; whenever a Turkish edit changes
    # an alpha block, also replace its ETC1 companion with the closest native
    # ETC1 pattern for that alpha shape. Unchanged blocks remain byte-identical.
    tnew=bytearray(tex)
    changed_alpha=changed_rgb=0
    native_exact=native_nearest=0
    for pg in range(5):
        po=pg*PAGE_SIZE; mo=0
        for mi,(dim,sz) in enumerate(zip(MIP_DIMS,MIP_SIZES)):
            vis=new_mips[pg][mi]
            encA=encode_alpha_mip_visual(vis)
            orig_chunk=tex[po+mo:po+mo+sz]
            chunk=bytearray(orig_chunk)
            blocks=dim//4; tiles_x=dim//8
            rawvis=np.flipud(vis)
            rawmask=np.flipud(masks_mips[pg][mi])
            for by in range(blocks):
                for bx in range(blocks):
                    tx,ty=bx//2,by//2; ix,iy=bx%2,by%2
                    bi=(ty*tiles_x+tx)*4 + ix+2*iy
                    aoff=bi*16
                    na=bytes(encA[aoff:aoff+8])
                    olda=bytes(chunk[aoff:aoff+8])
                    if olda!=na:
                        changed_alpha+=sum(a!=b for a,b in zip(olda,na))
                        chunk[aoff:aoff+8]=na
                        ne,exact=native_etc_for(na)
                        if exact: native_exact+=1
                        else: native_nearest+=1
                        if chunk[aoff+8:aoff+16]!=ne:
                            changed_rgb+=sum(a!=b for a,b in zip(chunk[aoff+8:aoff+16],ne))
                            chunk[aoff+8:aoff+16]=ne
            tnew[po+mo:po+mo+sz]=chunk
            mo+=sz

    dnew=modify_descriptor(desc)
    # Verify packing positions (page/x/y) are unchanged index-for-index.
    packing={}
    for nm,start in [('Narrow',288),('Alor',4184)]:
        oi=parse_desc(desc,start); ni=parse_desc(dnew,start)
        op=[]; np2=[]
        # index aligned because only codepoint identifiers changed
        for g in oi['glyphs']:
            op.append(oi['pos'][g[0]][:3] + (g[2],))
        for g in ni['glyphs']:
            np2.append(ni['pos'][g[0]][:3] + (g[2],))
        packing[nm]={'same_positions':all(a[:3]==b[:3] for a,b in zip(op,np2)),
                     'same_renderwidth_sequence':all(a[3]==b[3] for a,b in zip(op,np2)),
                     'count':len(op)}
        if not packing[nm]['same_positions'] or not packing[nm]['same_renderwidth_sequence']:
            raise RuntimeError(f'{nm} packing drift remains')

    cdesc=zlib.compress(dnew,9); ctex=zlib.compress(bytes(tnew),9)
    if len(cdesc)>TEX_OFF-DESC_OFF: raise RuntimeError('descriptor compressed stream overflow')
    if len(ctex)>TEX_END-TEX_OFF: raise RuntimeError(f'texture compressed stream overflow {len(ctex)}')
    out=bytearray(blob)
    out[DESC_OFF:TEX_OFF]=cdesc+b'\0'*((TEX_OFF-DESC_OFF)-len(cdesc))
    out[TEX_OFF:TEX_END]=ctex+b'\0'*((TEX_END-TEX_OFF)-len(ctex))
    # trailing two empty zlib streams untouched
    # Validate all streams.
    val={}
    for off in [0,DESC_OFF,TEX_OFF,77872,77880]:
        try: val[str(off)]=len(zlib.decompress(bytes(out)[off:]))
        except Exception as e: val[str(off)]=f'ERROR {e}'
    # Validate new cps and absent old repurposed cps in both descriptors.
    dchk=zlib.decompress(bytes(out)[DESC_OFF:])
    glyph_checks={}
    for nm,start in [('Narrow',288),('Alor',4184)]:
        inf=parse_desc(dchk,start); cps=set(inf['pos'])
        glyph_checks[nm]={'has_turkish':all(c in cps for c in slotmap),'old_slots_removed':all(c not in cps for c in slotmap.values())}
    meta=dict(format='NLG custom ETC1_A4',page_order=['Alor#0','Alor#1','Alor#2','Alor_Narrow_Condensed#0','Alor_Narrow_Condensed#1'],
              fixes=['preserve original render-width packing','rebuild dotless i','rebuild dotted capital I','cedilla from native C/c','breve from native degree-ring curve','patch A4 alpha','patch ETC1 color plane','regenerate 5 mip levels'],
              desc_compressed=len(cdesc),tex_compressed=len(ctex),allocated_tex=TEX_END-TEX_OFF,
              changed_alpha_bytes=changed_alpha,changed_etc1_bytes=changed_rgb,native_etc_exact_blocks=native_exact,native_etc_nearest_blocks=native_nearest,packing=packing,zlib_validation=val,glyph_checks=glyph_checks,target_records=target_records,
              sha256=hashlib.sha256(out).hexdigest())
    return bytes(out),meta,newtops

def make_previews(tops,meta):
    OUTDIR.mkdir(exist_ok=True)
    # Full atlas pages, upscaled, plus focused Turkish glyph panels.
    for i,a in enumerate(tops):
        Image.fromarray(a).resize((768,768),Image.Resampling.NEAREST).save(OUTDIR/f'font_page{i}_v4.png')
    # Draw bounding boxes and labels for target records on their pages.
    bypage={}
    for r in meta['target_records']: bypage.setdefault(r['page'],[]).append(r)
    for pg,recs in bypage.items():
        im=Image.fromarray(tops[pg]).convert('RGB').resize((1024,1024),Image.Resampling.NEAREST)
        dr=ImageDraw.Draw(im)
        for r in recs:
            x,y,rw,rh=r['x']*4,r['y']*4,r['rw']*4,r['rh']*4
            dr.rectangle([x,y,x+rw-1,y+rh-1],outline=(255,0,0),width=2)
            dr.text((x,max(0,y-12)),f"{r['char']} U+{r['new_cp']:04X}",fill=(255,0,0))
        im.save(OUTDIR/f'turkish_glyphs_page{pg}_v4.png')

def build_zip(font_blob):
    outzip=OUTDIR/'Luigis_Mansion_2_TR_FONTFIX_V4_DUALPLANE.zip'
    with zipfile.ZipFile(V3,'r') as zin, zipfile.ZipFile(outzip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zout:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if info.filename.endswith('/romfs/art/fe/febundlefonts_res.data'):
                data=font_blob
            zout.writestr(info,data)
    with zipfile.ZipFile(outzip) as z:
        bad=z.testzip();
        if bad: raise RuntimeError(f'zip bad {bad}')
        f=z.read('0004000000076500/romfs/art/fe/febundlefonts_res.data')
        if hashlib.sha256(f).hexdigest()!=hashlib.sha256(font_blob).hexdigest(): raise RuntimeError('font zip mismatch')
    return outzip

if __name__=='__main__':
    font,meta,tops=build_font()
    (OUTDIR/'febundlefonts_res_v4.data').write_bytes(font)
    # dict is unchanged from ROM/V3
    with zipfile.ZipFile(V3) as z:
        (OUTDIR/'febundlefonts_res.dict').write_bytes(z.read('0004000000076500/romfs/art/fe/febundlefonts_res.dict'))
    (OUTDIR/'font_fix_v4_meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    make_previews(tops,meta)
    z=build_zip(font)
    print(json.dumps(meta,ensure_ascii=False,indent=2))
    print(z)
