#!/usr/bin/env python3
from pathlib import Path
import sys, shutil, json, struct, hashlib, zipfile, re, math
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

BASE=Path('/mnt/data/build_v310/BravelyDefault_TR_Progress_v3.10_2026-08-22')
OUTROOT=Path('/mnt/data/build_v311')
OUT=OUTROOT/'BravelyDefault_TR_Progress_v3.11_2026-08-22'
SRCG=Path('/mnt/data/fix_font_v34/src/di#U011fer #U015feyler/Graphics')
if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUTROOT.mkdir(parents=True)
shutil.copytree(BASE,OUT)
TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'; ROMFS=OUT/'romfs'; TRROOT=ROMFS/'Graphics/UI_en'
sys.path.insert(0,str(TOOLS))
import repack_bravely as rb
from bravely_ui_tools import DarcArchive, cfnt_char_map, _sheet_to_bitmap_la4, _bitmap_to_sheet_la4, _alpha, bclyt_entries, make_text_width_fn
from bclim_tools import decode_bclim, encode_rgba8_bclim
from raster_patch_tools import inpaint_language_area, pick_font
from turkish_compat_encoding_v36 import DECODE

report={'version':'v3.11','font':{},'buttons':{},'raster':{},'technical':{}}
def sha(b): return hashlib.sha256(b).hexdigest()
def dec(s): return ''.join(DECODE.get(c,c) for c in s)

# ---------------- common archive helpers ----------------
def member_map(root:Path):
    m={}
    if not root.exists(): return m
    for idx in root.rglob('index.fs'):
        cp=idx.with_name('crowd.fs')
        if not cp.is_file(): continue
        frel=str(idx.parent.relative_to(root)).replace('\\','/')
        try: es=rb.parse_index(idx.read_bytes())
        except: continue
        for e in es:
            crel=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
            m[crel]=(frel,e['name'])
    return m

def extract_component(root:Path, mm:dict, crel:str):
    p=root/crel
    if p.is_file(): return p.read_bytes()
    z=mm.get(crel)
    if not z: return None
    frel,name=z; ip=root/frel/'index.fs'; cp=root/frel/'crowd.fs'
    if not ip.is_file() or not cp.is_file(): return None
    ib=ip.read_bytes(); cb=cp.read_bytes()
    for e in rb.parse_index(ib):
        if e['name']==name: return cb[e['offset']:e['offset']+e['size']]
    return None

def rebuild_crowd(root:Path,frel:str,repl:dict):
    ip=root/frel/'index.fs'; cp=root/frel/'crowd.fs'; ib=ip.read_bytes(); old=cp.read_bytes(); oi=bytearray(ib); oc=bytearray()
    for e in rb.parse_index(ib):
        while len(oc)%4: oc.append(0)
        off=len(oc); b=repl.get(e['name'],old[e['offset']:e['offset']+e['size']]); oc+=b
        struct.pack_into('<I',oi,e['pos']+4,off); struct.pack_into('<I',oi,e['pos']+8,len(b))
    while len(oc)%4: oc.append(0)
    ip.write_bytes(oi); cp.write_bytes(oc)

# ---------------- font quality patch ----------------
def cfnt_sections(d:bytes):
    hs=struct.unpack_from('<H',d,6)[0]; off=hs; out=[]
    while off+8<=len(d):
        mg=d[off:off+4]; sz=struct.unpack_from('<I',d,off+4)[0]
        if sz<8 or off+sz>len(d): break
        out.append((mg,off,sz)); off+=sz
    return out

def patch_cfnt_quality(cfnt:bytes):
    d=bytearray(cfnt); cmap=cfnt_char_map(cfnt)
    required=['g','G','i','ğ','Ğ','ı','ð','Ð','þ']
    miss=[c for c in required if c not in cmap]
    if miss: raise ValueError('font missing '+repr(miss))
    secs=cfnt_sections(cfnt); t=next(o for m,o,s in secs if m==b'TGLP')
    cw,ch,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,t+8)
    if fmt!=9: raise ValueError('expected LA4')
    cache={}
    def bitmap(si):
        if si not in cache:
            st=sheetoff+si*sheetsize; cache[si]=_sheet_to_bitmap_la4(bytes(d[st:st+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cw+1); y0=(rem//cols)*(ch+1); b=bitmap(si)
        return [[b[(y0+y)*sw+x0+x] for x in range(cw)] for y in range(ch)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cw+1); y0=(rem//cols)*(ch+1); b=bitmap(si)
        for y in range(ch):
            for x in range(cw): b[(y0+y)*sw+x0+x]=c[y][x]
    def bbox(c):
        pts=[(x,y) for y,row in enumerate(c) for x,v in enumerate(row) if _alpha(v)>0]
        return (min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)) if pts else (0,0,cw-1,ch-1)
    def full(v): return (v & 0xf0) | 0x0f if _alpha(v)>0 else v
    # Exact dotless i: copy base i and clear ONLY the detached top component.
    ii=getcell(cmap['i']); rows_on=[any(_alpha(v)>0 for v in row) for row in ii]; groups=[]; st=None
    for y,on in enumerate(rows_on+[False]):
        if on and st is None: st=y
        elif not on and st is not None: groups.append((st,y-1)); st=None
    if len(groups)<2: raise ValueError('i does not have detached dot')
    ds,de=groups[0]; dotless=[r[:] for r in ii]
    for y in range(ds,de+1):
        for x in range(cw): dotless[y][x]=0xf0
    for c in ('ı','þ'): setcell(cmap[c],dotless)
    # Strong, readable breve + reinforced g descender. Start from untouched G/g every time.
    def make_breve(basech, lower=False):
        c=[r[:] for r in getcell(cmap[basech])]; x0,y0,x1,y1=bbox(c); cx=(x0+x1)//2
        # Reinforce existing descender pixels so the lower loop survives 3DS scaling.
        if lower:
            for y in range(baseline+1,ch):
                for x in range(cw):
                    if _alpha(c[y][x])>0: c[y][x]=full(c[y][x])
            # Small 14px font clips the g loop at the texture bottom; close the hook on final row.
            if ch<=14 and ch-1>baseline:
                xs=[x for x in range(cw) if _alpha(c[ch-1][x])>0]
                if len(xs)>=2:
                    lo,hi=min(xs),max(xs)
                    for x in range(lo+1,hi): c[ch-1][x]=0xff
        # Three-row U-shaped breve, with a one-row gap when space permits.
        end=max(2,y0-1)
        if y0>=7: end=y0-2
        r2=end; r1=max(0,r2-1); r0=max(0,r1-1)
        half=3 if cw>=14 else 2
        lx=max(0,cx-half); rx=min(cw-1,cx+half)
        # top arms
        c[r0][lx]=0xff; c[r0][rx]=0xff
        # vertical/inward arms
        c[r1][lx]=0xff; c[r1][rx]=0xff
        # broad rounded bottom
        for x in range(max(0,lx+1),min(cw,rx)): c[r2][x]=0xff
        return c,{'base_top':y0,'breve_rows':[r0,r1,r2],'center':cx,'descender_reinforced':bool(lower)}
    G,gi=make_breve('G',False); g,ggi=make_breve('g',True)
    for c in ('Ğ','Ð'): setcell(cmap[c],G)
    for c in ('ğ','ð'): setcell(cmap[c],g)
    # Widths exactly follow source base glyphs.
    wpos={}
    for mg,co,sz in secs:
        if mg!=b'CWDH': continue
        a,b,nxt=struct.unpack_from('<HHI',d,co+8)
        for idx in range(a,b+1):
            p=co+0x10+(idx-a)*3
            if p+3<=co+sz: wpos[idx]=p
    for target,src in [('ı','i'),('þ','i'),('ğ','g'),('ð','g'),('Ğ','G'),('Ð','G')]:
        if cmap[target] in wpos and cmap[src] in wpos:
            d[wpos[cmap[target]]:wpos[cmap[target]]+3]=d[wpos[cmap[src]]:wpos[cmap[src]]+3]
    for si,bm in cache.items():
        st=sheetoff+si*sheetsize; d[st:st+sheetsize]=_bitmap_to_sheet_la4(bm,sw,sh)
    return bytes(d),{'cell':[cw,ch],'baseline':baseline,'i_dot_rows':[ds,de],'g':ggi,'G':gi,'map':{c:cmap[c] for c in ['ı','þ','ğ','ð','Ğ','Ð']}}

font_infos=[]
for rel in ['Graphics/UI/Font/Font','Graphics/UI_en/Font/Font']:
    p=ROMFS/rel; arc=DarcArchive(p.read_bytes()); repl={}
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,info=patch_cfnt_quality(b); repl[ip]=nb; info.update({'archive':rel,'inner':ip,'sha256':sha(nb)}); font_infos.append(info)
    if repl: p.write_bytes(arc.rebuild(repl))
report['font']['patched']=font_infos

# font preview
def font_preview(path:Path,out:Path,label:str):
    arc=DarcArchive(path.read_bytes()); cf=next(b for _,b in arc.files() if b[:4]==b'CFNT'); cmap=cfnt_char_map(cf); secs=cfnt_sections(cf); t=next(o for m,o,s in secs if m==b'TGLP')
    cw,ch,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',cf,t+8); cache={}
    def cell(c):
        gi=cmap[c];si=gi//(cols*rows);rem=gi%(cols*rows);x0=(rem%cols)*(cw+1);y0=(rem//cols)*(ch+1)
        if si not in cache:
            st=sheetoff+si*sheetsize;cache[si]=_sheet_to_bitmap_la4(cf[st:st+sheetsize],sw,sh)
        bm=cache[si]; return [[_alpha(bm[(y0+y)*sw+x0+x]) for x in range(cw)] for y in range(ch)]
    chars=['i','ı','þ','g','ğ','ð','G','Ğ','Ð']; scale=12; cellW=cw*scale+24; H=ch*scale+55
    im=Image.new('RGB',(cellW*len(chars),H),'white'); dr=ImageDraw.Draw(im)
    for j,c in enumerate(chars):
        ox=j*cellW; dr.text((ox+2,2),c,fill='black')
        a=cell(c)
        for y,row in enumerate(a):
            for x,v in enumerate(row):
                if v:
                    q=255-int(v/15*255);dr.rectangle((ox+x*scale,30+y*scale,ox+(x+1)*scale-1,30+(y+1)*scale-1),fill=(q,q,q))
        dr.line((ox,30+baseline*scale,ox+cw*scale,30+baseline*scale),fill='red')
    im.save(out)
font_preview(ROMFS/'Graphics/UI/Font/Font',REPORTS/'FONT_GLYPHS_COMMON_v311.png','common')
font_preview(ROMFS/'Graphics/UI_en/Font/Font',REPORTS/'FONT_GLYPHS_UI_EN_v311.png','en')

# ---------------- BCLYT button fit against official localizations ----------------
langs=['en','de','fr','es','it']
trmm=member_map(TRROOT); smm={l:member_map(SRCG/f'UI_{l}') for l in langs}
wfn={}
for l in langs:
    a=DarcArchive((SRCG/f'UI_{l}/Font/Font').read_bytes()); cf=next(b for _,b in a.files() if b[:4]==b'CFNT'); wfn[l]=make_text_width_fn(cf)
a=DarcArchive((TRROOT/'Font/Font').read_bytes()); cf=next(b for _,b in a.files() if b[:4]==b'CFNT'); trw=make_text_width_fn(cf)
button_re=re.compile(r'(btn|button|select|cmnd|cmd|choice|yes|no|ok|cancel|close|back|return|next|prev|on|off|wifi|tab|guide|decide|confirm)',re.I)
stage=defaultdict(dict); bchanges=[]; bcandidates=[]
def patch_fontx(data,pane,ordinal,newfx):
    out=bytearray(data)
    for e in bclyt_entries(data):
        if e['pane']==pane and e['ordinal']==ordinal:
            struct.pack_into('<f',out,e['section_offset']+0x64,float(newfx)); return bytes(out),True
    return data,False
for crel in sorted(trmm):
    if not (crel.startswith('Layout/') or crel.startswith('Common/')): continue
    tc=extract_component(TRROOT,trmm,crel)
    if not tc or tc[:4]!=b'darc': continue
    try: ta=DarcArchive(tc); tf=dict(ta.files())
    except: continue
    donors={}
    for l in langs:
        c=extract_component(SRCG/f'UI_{l}',smm[l],crel)
        if c and c[:4]==b'darc':
            try: donors[l]=dict(DarcArchive(c).files())
            except: pass
    repl={}
    for ip,tb0 in tf.items():
        if tb0[:4]!=b'CLYT': continue
        tb=tb0
        for e0 in bclyt_entries(tb0):
            txt=dec(e0['text']).strip()
            if not txt or '\n' in txt or len(txt)>35 or e0['width']<=0 or e0['font_x']<=0: continue
            key=(e0['pane'],e0['ordinal']); ds=[]
            for l,files in donors.items():
                b=files.get(ip)
                if not b or b[:4]!=b'CLYT': continue
                d=next((x for x in bclyt_entries(b) if (x['pane'],x['ordinal'])==key),None)
                if not d or not d['text']: continue
                ds.append({'lang':l,'text':d['text'],'rendered':wfn[l](d['text'])*(d['font_x']/14.0),'font_x':d['font_x'],'pane_w':d['width']})
            if len(ds)<3: continue
            cur=next(x for x in bclyt_entries(tb) if (x['pane'],x['ordinal'])==key)
            trr=trw(cur['text'])*(cur['font_x']/14.0); mx=max(ds,key=lambda x:x['rendered']); ratio=trr/max(mx['rendered'],.001)
            fname=(crel+' '+ip+' '+cur['pane']).lower(); score=3 if button_re.search(fname) else 0
            if cur['width']<=90: score+=1
            if len(txt)<=16: score+=1
            if any(x['text'].strip().lower() in ['yes','no','ok','cancel','back','close','next','on','off','buy','sell','use','equip','save','load','start','quit','confirm'] for x in ds): score+=3
            if ratio>1.05 and score>=4:
                bcandidates.append({'archive':crel,'inner':ip,'pane':cur['pane'],'ordinal':cur['ordinal'],'text':txt,'ratio':ratio,'tr_width':trr,'official_max':mx['rendered'],'donor':mx,'old_font_x':cur['font_x']})
                newfx=cur['font_x']*(mx['rendered']*0.98/trr)
                newfx=max(8.0,min(cur['font_x'],newfx))
                if newfx<cur['font_x']-0.01:
                    tb,ok=patch_fontx(tb,cur['pane'],cur['ordinal'],newfx)
                    if ok: bchanges.append({'archive':crel,'inner':ip,'pane':cur['pane'],'ordinal':cur['ordinal'],'text':txt,'old_font_x':cur['font_x'],'new_font_x':newfx,'before':trr,'target':mx['rendered']})
        if tb!=tb0: repl[ip]=tb
    if repl:
        nc=ta.rebuild(repl); frel,name=trmm[crel]; stage[frel][name]=nc
for frel,repl in stage.items(): rebuild_crowd(TRROOT,frel,repl)
report['buttons']['bclyt_candidates']=bcandidates; report['buttons']['bclyt_changes']=bchanges

# ---------------- raster button/title refinement ----------------
# Current map refreshed after BCLYT crowd rebuild (same component membership).
trmm=member_map(TRROOT)
srcmm={l:member_map(SRCG/f'UI_{l}') for l in langs}; jpmm=member_map(SRCG/'UI')
raster_stage=defaultdict(dict); raster_changes=[]
def source_component(lang,crel):
    root=SRCG/('UI' if lang=='jp' else f'UI_{lang}'); mm=jpmm if lang=='jp' else srcmm[lang]
    return extract_component(root,mm,crel)
def current_component(crel): return extract_component(TRROOT,trmm,crel)
def get_inner(comp,inner):
    try:return dict(DarcArchive(comp).files()).get(inner)
    except:return None

def localized_base(crel,inner):
    ec=source_component('en',crel); eb=get_inner(ec,inner)
    if not eb: raise KeyError((crel,inner))
    en=decode_bclim(eb).convert('RGBA'); others=[]
    for l in ['de','fr','es','it']:
        c=source_component(l,crel); b=get_inner(c,inner) if c else None
        if b:
            try:
                im=decode_bclim(b).convert('RGBA')
                if im.size==en.size: others.append(im)
            except: pass
    # Western-language differences isolate localized glyphs without touching button icons.
    if others:
        base,bb,mask=inpaint_language_area(en,others)
    else:
        base,bb,mask=en.copy(),(0,0,en.width,en.height),None
    return en,base,bb

def erase_text_luma(en, region=None):
    im=en.convert('RGBA'); arr=np.asarray(im).copy(); h,w=arr.shape[:2]
    if region is None: region=(0,0,w,h)
    x0,y0,x1,y1=region; roi=arr[y0:y1,x0:x1]
    rgb=roi[:,:,:3].astype(np.float32); lum=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
    med=float(np.median(lum))
    if med>=128: m=(lum < med-28)
    else: m=(lum > med+28)
    mask=np.zeros((h,w),np.uint8); mask[y0:y1,x0:x1]=(m.astype(np.uint8)*255)
    mask=cv2.dilate(mask,np.ones((3,3),np.uint8),iterations=1)
    # keep mask strictly in requested text region so ornaments outside remain untouched
    keep=np.zeros_like(mask); keep[y0:y1,x0:x1]=255; mask=cv2.bitwise_and(mask,keep)
    if mask.max()==0: return im
    out=arr.copy(); out[:,:,:3]=cv2.inpaint(arr[:,:,:3],mask,2,cv2.INPAINT_TELEA)
    out[:,:,3]=cv2.inpaint(arr[:,:,3],mask,2,cv2.INPAINT_TELEA)
    return Image.fromarray(out.astype(np.uint8),'RGBA')

def flat_plate(en):
    arr=np.asarray(en.convert('RGBA')); h,w=arr.shape[:2]
    border=np.concatenate([arr[0,:,:],arr[-1,:,:],arr[:,0,:],arr[:,-1,:]],axis=0)
    good=border[border[:,3]>20]
    col=np.median(good,axis=0).astype(np.uint8) if len(good) else np.array([0,0,0,0],np.uint8)
    out=np.empty_like(arr); out[:]=col
    # preserve original alpha silhouette in case the plate is not fully opaque
    out[:,:,3]=arr[:,:,3]
    return Image.fromarray(out,'RGBA')

def draw_capped(canvas,text,box,fill,serif=True,stroke_width=0,stroke=(0,0,0,255),min_size=4,max_size=14,align='center'):
    fp=pick_font(serif); d=ImageDraw.Draw(canvas); x0,y0,x1,y1=box; best=ImageFont.truetype(fp,min_size)
    for size in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(fp,size); bb=d.textbbox((0,0),text,font=f,stroke_width=stroke_width)
        if bb[2]-bb[0]<=x1-x0 and bb[3]-bb[1]<=y1-y0: best=f; break
    bb=d.textbbox((0,0),text,font=best,stroke_width=stroke_width); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    if align=='left': x=x0-bb[0]
    elif align=='right': x=x1-tw-bb[0]
    else: x=x0+(x1-x0-tw)//2-bb[0]
    y=y0+(y1-y0-th)//2-bb[1]
    d.text((x,y),text,font=best,fill=fill,stroke_width=stroke_width,stroke_fill=stroke)
    return {'font_size':getattr(best,'size',None),'bbox':[x,y,x+tw,y+th],'box':list(box)}

def set_raster(crel,inner,newimg,source_template=None,label=''):
    comp=current_component(crel); arc=DarcArchive(comp); files=dict(arc.files()); old=files.get(inner)
    if old is None: raise KeyError((crel,inner))
    nb=encode_rgba8_bclim(newimg,source_template or old); newcomp=arc.rebuild({inner:nb})
    frel,name=trmm[crel]; raster_stage[frel][name]=newcomp
    raster_changes.append({'archive':crel,'inner':inner,'label':label,'size':list(newimg.size)})

# To safely patch multiple images in same component, accumulate per-component image replacements then rebuild once.
raster_specs=[]
# novel index IDs
nov=json.loads(Path('/mnt/data/v37_ui_vs_jp/index.json').read_text(encoding='utf8')); novby={r['id']:r for r in nov}
NOV_TEXT={35:'Konuş',36:'Gir',37:'Çık',38:'İlerle',39:'Bin',40:'İn',41:'Aç',42:'İncele',43:'Dua Et',46:'Olayı Atla',47:'Atla',87:'Düz.',184:'Hava Gemisi',275:'Mesaj',281:'HAZIR',282:'KAÇIYOR'}
for iid,text in NOV_TEXT.items():
    r=novby.get(iid)
    if r:
        for occ in r['occurrences']: raster_specs.append(('nov',iid,text,occ['archive'],occ['inner']))
# old index selected compact labels/titles
old=json.loads((TOOLS/'unique_bclim_index.json').read_text(encoding='utf8')); oldby={r['id']:r for r in old}
OLD_TEXT={6:'Mesaj',11:'Para',127:'Büyüler',144:'Kaydet',160:'Ytnk. Bağı',184:'Savaş Sonuçları'}
for iid,text in OLD_TEXT.items():
    r=oldby.get(iid)
    if r:
        for occ in r['occurrences']: raster_specs.append(('old',iid,text,occ['archive'],occ['inner']))

bycomp=defaultdict(list)
for spec in raster_specs: bycomp[spec[3]].append(spec)
for crel,specs in bycomp.items():
    cur=current_component(crel)
    if not cur: continue
    arc=DarcArchive(cur); files=dict(arc.files()); replacements={}
    for kind,iid,text,_,inner in specs:
        oldb=files.get(inner)
        if not oldb: continue
        try:
            en,base,bb=localized_base(crel,inner)
            w,h=en.size
            # Older western-shared plates can retain the same English pixels across donor locales;
            # erase their local text band by luminance before redrawing to avoid ghost letters.
            if kind=='old' and iid==6:
                base=erase_text_luma(en,(0,0,min(49,w),h))
            elif kind=='old' and iid in (11,144,160):
                jpc=source_component('jp',crel); jpb=get_inner(jpc,inner) if jpc else None
                if jpb:
                    try: base,_,_=inpaint_language_area(en,[decode_bclim(jpb).convert('RGBA')])
                    except: base=erase_text_luma(en,(0,0,w,h))
                else: base=erase_text_luma(en,(0,0,w,h))
            elif kind=='old' and iid==127:
                base=flat_plate(en)
            info={}
            # Button guide: keep text in same compact right-hand band as official labels.
            if kind=='nov' and 35<=iid<=43:
                box=(20,1,w-1,h-1); info=draw_capped(base,text,box,(20,20,28,255),serif=True,stroke_width=0,min_size=5,max_size=(11 if len(text)<=3 else 10 if len(text)<=5 else 9))
            elif kind=='nov' and iid==46:
                info=draw_capped(base,text,(17,1,w-2,h-1),(225,225,230,255),serif=True,stroke_width=1,stroke=(15,15,18,220),min_size=5,max_size=11)
            elif kind=='nov' and iid==47:
                info=draw_capped(base,text,(17,1,w-2,h-1),(225,225,230,255),serif=True,stroke_width=1,stroke=(15,15,18,220),min_size=5,max_size=11)
            elif kind=='nov' and iid==87:
                info=draw_capped(base,text,(2,1,w-2,h-1),(35,45,65,255),serif=True,stroke_width=0,min_size=5,max_size=11)
            elif kind=='nov' and iid==184:
                info=draw_capped(base,text,(10,5,w-8,h-5),(245,245,240,255),serif=True,stroke_width=1,stroke=(30,30,30,235),min_size=7,max_size=18)
            elif kind=='nov' and iid==275:
                # The decorative Message plate should stay much smaller than the v3.10 remake.
                info=draw_capped(base,text,(3,3,w-18,h-3),(90,210,245,255),serif=True,stroke_width=1,stroke=(15,25,35,235),min_size=6,max_size=13)
            elif kind=='nov' and iid==281:
                info=draw_capped(base,text,(24,1,64,h-1),(245,245,245,255),serif=True,stroke_width=0,min_size=5,max_size=9)
            elif kind=='nov' and iid==282:
                info=draw_capped(base,text,(19,1,70,h-1),(225,215,215,255),serif=True,stroke_width=0,min_size=5,max_size=9)
            elif kind=='old' and iid==6:
                info=draw_capped(base,text,(1,0,46,h),(190,155,70,255),serif=True,stroke_width=0,min_size=5,max_size=9)
            elif kind=='old' and iid==11:
                info=draw_capped(base,text,(1,1,w-1,h-1),(225,240,245,255),serif=True,stroke_width=0,min_size=5,max_size=12)
            elif kind=='old' and iid==127:
                info=draw_capped(base,text,(1,1,w-1,h-1),(35,35,60,255),serif=True,stroke_width=0,min_size=5,max_size=12)
            elif kind=='old' and iid==144:
                info=draw_capped(base,text,(1,0,w-1,h),(245,250,250,255),serif=True,stroke_width=0,min_size=5,max_size=8)
            elif kind=='old' and iid==160:
                info=draw_capped(base,text,(2,1,w-2,h-1),(35,35,60,255),serif=True,stroke_width=0,min_size=5,max_size=11)
            elif kind=='old' and iid==184:
                info=draw_capped(base,text,(14,8,w-14,h-8),(245,250,245,255),serif=True,stroke_width=1,stroke=(20,75,95,235),min_size=8,max_size=22)
            else: continue
            nb=encode_rgba8_bclim(base,oldb); replacements[inner]=nb
            raster_changes.append({'kind':kind,'id':iid,'archive':crel,'inner':inner,'text':text,'draw':info,'image_size':[w,h]})
        except Exception as ex:
            raster_changes.append({'kind':kind,'id':iid,'archive':crel,'inner':inner,'text':text,'error':repr(ex)})
    if replacements:
        newcomp=arc.rebuild(replacements); frel,name=trmm[crel]; raster_stage[frel][name]=newcomp
# There can be multiple components in same crowd; rebuild every crowd once.
for frel,repls in raster_stage.items(): rebuild_crowd(TRROOT,frel,repls)
report['raster']['changes']=raster_changes
report['raster']['successful']=sum('error' not in x for x in raster_changes)
report['raster']['failed']=[x for x in raster_changes if 'error' in x]

# Raster preview from final build
def final_inner(crel,inner):
    mm=member_map(TRROOT); c=extract_component(TRROOT,mm,crel); return get_inner(c,inner)
preview_specs=[]
seen=set()
for x in raster_changes:
    if 'error' in x: continue
    k=(x['archive'],x['inner'])
    if k in seen: continue
    seen.add(k)
    try:
        im=decode_bclim(final_inner(*k)).convert('RGBA'); preview_specs.append((x['text'],Path(x['inner']).name,im))
    except: pass
thumb=[]
for text,name,im in preview_specs:
    s=max(1,min(4,280//max(im.width,1))); v=im.resize((im.width*s,im.height*s),Image.NEAREST); thumb.append((text,name,v))
if thumb:
    cw=330; chh=110; cols=3; rows=math.ceil(len(thumb)/cols); sheet=Image.new('RGB',(cw*cols,chh*rows),'white'); dr=ImageDraw.Draw(sheet)
    for k,(text,name,v) in enumerate(thumb):
        x=(k%cols)*cw; y=(k//cols)*chh; dr.text((x+3,y+3),f'{text} / {name}',fill='black'); sheet.paste(v.convert('RGB'),(x+3,y+25))
    sheet.save(REPORTS/'BUTTON_RASTER_REFINEMENT_v311.png')

# ---------------- post button audit ----------------
# Simple verification on the exact BCLYT entries we changed.
post=[]; trmm2=member_map(TRROOT)
for r in bchanges:
    c=extract_component(TRROOT,trmm2,r['archive']); b=dict(DarcArchive(c).files())[r['inner']]
    e=next(x for x in bclyt_entries(b) if x['pane']==r['pane'] and x['ordinal']==r['ordinal'])
    rr=trw(e['text'])*(e['font_x']/14.0); post.append({**r,'post_rendered':rr,'post_ratio':rr/max(r['target'],.001)})
report['buttons']['post']=post
report['buttons']['remaining_over_1_03']=sum(x['post_ratio']>1.03 for x in post)

# ---------------- docs/reports ----------------
(REPORTS/'FONT_AND_BUTTON_AUDIT_v311.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(DOCS/'FONT_GLYPH_KALITE_v3.11_TR.md').write_text('''# Font glyph kalite düzeltmesi — v3.11

Gerçek 3DS geri bildiriminde küçük/altyazı yazısında `ğ` breve işareti ve kuyruğu yeterince seçilmiyordu. Önceki breve birkaç çapraz pikselden oluştuğu için düşük çözünürlükte X/V gibi görünebiliyordu.

v3.11 her iki runtime fontunda (`Graphics/UI/Font/Font`, `Graphics/UI_en/Font/Font`) `ğ/ð` glyph'ini kaynak `g` gövdesinden yeniden kurar. Üst işaret üç satırlık belirgin U-biçimli breve olarak çizilir. Descender pikselleri tam alpha yapılır; 14px küçük fontta alt g halkasının son satırı kapatılarak kuyruğun kesik görünmesi azaltılır. `Ğ/Ð` de aynı breve geometrisini kullanır.

`ı/þ` için kaynak küçük `i` glyph'i her build'de baştan kopyalanır ve yalnız bağlantısız nokta bileşeninin satırları silinir. Gövde taşınmaz, döndürülmez veya aynalanmaz.

Reports klasöründeki `FONT_GLYPHS_COMMON_v311.png` ve `FONT_GLYPHS_UI_EN_v311.png` dosyaları gerçek CFNT bitmaplerinin nearest-neighbor büyütülmüş kontrol görüntüleridir.
''',encoding='utf8')
(DOCS/'DUGME_VE_RASTER_BOYUT_v3.11_TR.md').write_text(f'''# Düğme/raster yazı boyutu — v3.11

v3.10'a kadar BCLYT başlıklarının önemli kısmı resmi EN/DE/FR/ES/IT genişlikleriyle karşılaştırılıyordu; resim içine gömülü BCLIM düğme yazıları ise çoğunlukla yalnız hedef kutuya sığdırılıyordu. Gerçek cihazda bu durum Türkçe yazının kaynak düğmeden daha iri görünmesine yol açtı.

v3.11 iki düzeltme yapar:

1. `Evet/Hayır` gibi BCLYT seçim düğmeleri aynı pane'in beş resmi dildeki en geniş görünür karşılığına göre yatay olarak ölçeklenir. Bu build'de {len(bchanges)} kayıt düzeltildi.
2. ButtonGuide, EventSkip, Düzenle, Hava Gemisi, Mesaj, Hazır/Kaçıyor, Kaydet, Para, Büyüler, Yetenek Bağı ve Savaş Sonuçları gibi raster etiketler orijinal İngilizce kaynak texture'dan yeniden oluşturulur. Türkçe metin kaynak yazının görsel bandı ve yükseklik sınırı içinde çizilir. Dar 128×16 Abilink rasterında yamadaki `Yetenek Bağı` teriminin kısa biçimi `Ytnk. Bağı` kullanılır; normal metin alanlarında tam terim korunur.

Kontrol görüntüsü: `Reports/BUTTON_RASTER_REFINEMENT_v311.png`.
''',encoding='utf8')
(DOCS/'CHANGELOG_v3.11_TR.md').write_text(f'''# Bravely Default TR — v3.11

- `ı` glyph'i her iki fontta kaynak `i`den yalnız nokta silinerek yeniden üretildi.
- `ğ` ve runtime alias `ð` için belirgin U-biçimli breve ve güçlendirilmiş alt kuyruk eklendi; küçük 14px fontta kesilen alt halka kapatıldı.
- Büyük `Ğ/Ð` breve geometrisi de aynı yöntemle yenilendi.
- {len(bchanges)} BCLYT düğme/seçim etiketi resmi EN/DE/FR/ES/IT görünür genişliklerine göre yeniden ölçeklendi.
- {report['raster']['successful']} raster kullanımında düğme/etiket yazı boyutu kaynak görüntüye yaklaştırıldı. `Yetenek Bağı` dar rasterda `Ytnk. Bağı`, `Hava Gemisi Menüsü` başlığında bağlam gereği `Hava Gemisi`, `Düzenle` çok dar 36px butonda `Düz.` kullanılır.
- Önceki v3.10 Common_en çevirileri, Türkçe BP/CP/MP terminolojisi ve bütün önceki ilerleme korunur.
''',encoding='utf8')
# Add this build script to tools
shutil.copy2('/mnt/data/build_v311.py',TOOLS/'build_progress_v311.py')

# technical crowd audit
errs=[]; pairs=entries=0
for ip in ROMFS.rglob('index.fs'):
    cp=ip.with_name('crowd.fs')
    if not cp.is_file(): continue
    pairs+=1
    try:
        es=rb.parse_index(ip.read_bytes()); cb=cp.read_bytes(); entries+=len(es); spans=[]
        for e in es:
            if e['offset']+e['size']>len(cb): errs.append({'path':str(ip.relative_to(ROMFS)),'entry':e['name'],'error':'out_of_range'})
            spans.append((e['offset'],e['offset']+e['size'],e['name']))
        ss=sorted(spans)
        for a,b in zip(ss,ss[1:]):
            if a[1]>b[0]: errs.append({'path':str(ip.relative_to(ROMFS)),'error':'overlap','a':a,'b':b})
    except Exception as ex: errs.append({'path':str(ip.relative_to(ROMFS)),'error':repr(ex)})
report['technical']={'crowd_pairs':pairs,'crowd_entries':entries,'errors':errs}
(REPORTS/'TECHNICAL_AUDIT_v311.json').write_text(json.dumps(report['technical'],ensure_ascii=False,indent=2),encoding='utf8')
if errs: raise RuntimeError(errs[:5])
# update primary report after technical field
(REPORTS/'FONT_AND_BUTTON_AUDIT_v311.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
# manifest
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file(): manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
# zips
full=Path('/mnt/data/BravelyDefault_TR_Progress_v3.11_2026-08-22.zip'); eur=Path('/mnt/data/BravelyDefault_TR_Progress_v3.11_LayeredFS_EUR.zip'); usa=Path('/mnt/data/BravelyDefault_TR_Progress_v3.11_LayeredFS_USA.zip')
for z in (full,eur,usa):
    if z.exists(): z.unlink()
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(OUT.parent))
for zpath,titleid in [(eur,'00040000000FC600'),(usa,'00040000000FC500')]:
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROMFS.rglob('*')):
            if p.is_file(): z.write(p,Path('luma/titles')/titleid/'romfs'/p.relative_to(ROMFS))
for z in (full,eur,usa):
    with zipfile.ZipFile(z) as q:
        bad=q.testzip(); assert bad is None,bad
print(json.dumps({'full':str(full),'eur':str(eur),'usa':str(usa),'font_infos':font_infos,'bclyt_changes':len(bchanges),'raster_ok':report['raster']['successful'],'raster_failed':len(report['raster']['failed']),'crowd_pairs':pairs,'crowd_entries':entries,'errors':len(errs)},ensure_ascii=False,indent=2))
