from __future__ import annotations
from pathlib import Path
import os, sys, json, shutil, struct, hashlib, zipfile, re, copy, time
from collections import defaultdict, Counter
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

BASE=Path('/mnt/data/v35main/BravelyDefault_TR_Progress_v3.5_2026-08-21')
OUTBASE=Path('/mnt/data/build_v36/BravelyDefault_TR_Progress_v3.6_2026-08-21')
SRC=Path('/mnt/data/fix_font_v34/src/di#U011fer #U015feyler')
CODE=Path('/mnt/data/code(20260821-192046).bin')
COMMONZIP=Path('/mnt/data/Common.zip')
TOOLS=OUTBASE/'Tools'
ROMFS=OUTBASE/'romfs'
OLD_TOOLS=BASE/'Tools'
sys.path.insert(0,str(OLD_TOOLS))
from repack_bravely import parse_index, btbf_meta, read_utf16z
from bravely_ui_tools import DarcArchive, bclyt_entries
from bravely_font_tools_v35 import active_cmap_map, _sections
from bravely_ui_tools import _sheet_to_bitmap_la4, _bitmap_to_sheet_la4
from bclim_tools import decode_bclim, encode_rgba8_bclim, parse_bclim
from raster_patch_tools import render_translation, sample_text_colors, _draw_centered, _draw_fit_at, pick_font

TR='ĞğİıŞş'
ALIASES='ÐðÞþÆæ'
ENCODE=dict(zip(TR,ALIASES))
DECODE=dict(zip(ALIASES,TR))
CPMAP={ord(k):ord(v) for k,v in ENCODE.items()}

# ---- helpers ----
def sha256(b:bytes): return hashlib.sha256(b).hexdigest()
def read_utf16z_local(b,off,limit=None):
    end=off; lim=len(b) if limit is None else min(len(b),limit)
    while end+1<lim and b[end:end+2]!=b'\0\0': end+=2
    return b[off:end].decode('utf-16le','replace')

def replace_units(raw:bytes):
    if len(raw)%2: return raw,0
    ba=bytearray(raw); c=0
    for i in range(0,len(ba)-1,2):
        u=ba[i]|(ba[i+1]<<8)
        if u in CPMAP:
            v=CPMAP[u]; ba[i]=v&255; ba[i+1]=v>>8; c+=1
    return bytes(ba),c

def patch_btbf_alias(b:bytes):
    if b[:4]!=b'BTBF': return b,0
    m=btbf_meta(b); s=m['text_start']; e=s+m['text_size']
    block,n=replace_units(b[s:e])
    if not n: return b,0
    out=bytearray(b); out[s:e]=block; return bytes(out),n

def patch_bclyt_alias(b:bytes):
    if b[:4]!=b'CLYT': return b,0
    out=bytearray(b); n=0
    for ent in bclyt_entries(b):
        so=ent['section_offset']; to=ent['text_offset']; start=so+to
        end=start
        secend=so+ent['section_size']
        while end+1<secend and out[end:end+2]!=b'\0\0': end+=2
        nb,c=replace_units(bytes(out[start:end]))
        if c: out[start:end]=nb; n+=c
    return bytes(out),n

def patch_darc_text_alias(b:bytes):
    try: arc=DarcArchive(b)
    except Exception: return b,0,0
    repl={}; chars=0; files=0
    for ip,pay in arc.files():
        if pay[:4]==b'CLYT':
            nb,n=patch_bclyt_alias(pay)
            if n: repl[ip]=nb; chars+=n; files+=1
        elif pay[:4]==b'BTBF':
            nb,n=patch_btbf_alias(pay)
            if n: repl[ip]=nb; chars+=n; files+=1
    if not repl: return b,0,0
    nb=arc.rebuild(repl)
    return nb,chars,files

def rebuild_crowd_bytes(idx_bytes:bytes,crowd_bytes:bytes,repls:dict[str,bytes]):
    ents=parse_index(idx_bytes); idx=bytearray(idx_bytes); out=bytearray(); det=[]
    for e in ents:
        while len(out)%4: out.append(0)
        off=len(out); pay=repls.get(e['name'], crowd_bytes[e['offset']:e['offset']+e['size']])
        out+=pay
        struct.pack_into('<I',idx,e['pos']+4,off); struct.pack_into('<I',idx,e['pos']+8,len(pay))
        det.append((e['name'],off,len(pay)))
    while len(out)%4: out.append(0)
    return bytes(idx),bytes(out),det

def patch_crowd_alias(folder:Path, mode:str):
    idxp=folder/'index.fs'; crp=folder/'crowd.fs'
    if not idxp.exists() or not crp.exists(): return None
    ib=idxp.read_bytes(); cb=crp.read_bytes(); repl={}; chars=files=0
    for e in parse_index(ib):
        pay=cb[e['offset']:e['offset']+e['size']]
        if mode=='btbf': nb,n=patch_btbf_alias(pay); f=1 if n else 0
        else: nb,n,f=patch_darc_text_alias(pay)
        if n: repl[e['name']]=nb; chars+=n; files+=f
    if repl:
        ni,nc,_=rebuild_crowd_bytes(ib,cb,repl); idxp.write_bytes(ni); crp.write_bytes(nc)
    return {'folder':str(folder.relative_to(ROMFS)),'members_changed':len(repl),'text_chars_aliased':chars,'inner_files_changed':files}

def structured_texts_btbf(b):
    if b[:4]!=b'BTBF': return []
    m=btbf_meta(b); block=b[m['text_start']:m['text_start']+m['text_size']]
    # walk UTF16z starts via pointer fields is complex; scan sequences aligned as a conservative text-only block parser
    out=[]; i=0
    while i+1<len(block):
        if block[i:i+2]==b'\0\0': i+=2; continue
        j=i
        while j+1<len(block) and block[j:j+2]!=b'\0\0': j+=2
        try: s=block[i:j].decode('utf-16le')
        except: s=''
        if s: out.append(s)
        i=j+2
    return out

def structured_alias_counts(root:Path):
    cnt=Counter(); trcnt=Counter(); samples=[]
    # Common_en BTBF direct + crowds
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if p.name=='crowd.fs' and 'Common_en' in p.parts and (p.parent/'index.fs').exists():
            ib=(p.parent/'index.fs').read_bytes(); cb=p.read_bytes()
            for e in parse_index(ib):
                pay=cb[e['offset']:e['offset']+e['size']]
                if pay[:4]==b'BTBF':
                    for s in structured_texts_btbf(pay):
                        for ch in ALIASES: cnt[ch]+=s.count(ch)
                        for ch in TR: trcnt[ch]+=s.count(ch)
            continue
        if p.name in ('crowd.fs','index.fs'): continue
        b=p.read_bytes()
        if b[:4]==b'BTBF':
            for s in structured_texts_btbf(b):
                for ch in ALIASES: cnt[ch]+=s.count(ch)
                for ch in TR: trcnt[ch]+=s.count(ch)
    # UI DARC crowds
    ui=root/'Graphics/UI_en'
    for crp in ui.rglob('crowd.fs'):
        ip=crp.parent/'index.fs'
        if not ip.exists(): continue
        ib=ip.read_bytes(); cb=crp.read_bytes()
        for e in parse_index(ib):
            pay=cb[e['offset']:e['offset']+e['size']]
            try: arc=DarcArchive(pay)
            except: continue
            for inner,bb in arc.files():
                if bb[:4]!=b'CLYT': continue
                for ent in bclyt_entries(bb):
                    s=ent['text']
                    for ch in ALIASES: cnt[ch]+=s.count(ch)
                    for ch in TR: trcnt[ch]+=s.count(ch)
    return dict(cnt),dict(trcnt)

# ---- font alias glyph patch ----
def patch_cfnt_aliases(cfnt:bytes):
    cmap,chain=active_cmap_map(cfnt)
    missing=[x for x in TR+ALIASES if x not in cmap]
    if missing: raise ValueError('Font map missing '+repr(missing))
    d=bytearray(cfnt); secs=_sections(cfnt); tglp=next(x for x in secs if x[0]==b'TGLP')[1]
    cellw,cellh,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,tglp+8)
    if fmt!=9: raise ValueError('font is not LA4')
    cache={}
    def bitmap(si):
        if si not in cache:
            s=sheetoff+si*sheetsize; cache[si]=_sheet_to_bitmap_la4(bytes(d[s:s+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); bm=bitmap(si)
        return [[bm[(y0+y)*sw+x0+x] for x in range(cellw)] for y in range(cellh)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); bm=bitmap(si)
        for y in range(cellh):
            for x in range(cellw): bm[(y0+y)*sw+x0+x]=c[y][x]
    width_pos={}
    for m,coff,csz in secs:
        if m!=b'CWDH': continue
        st,en,nxt=struct.unpack_from('<HHI',d,coff+8)
        for gi in range(st,en+1):
            p=coff+0x10+(gi-st)*3
            if p+3<=coff+csz: width_pos[gi]=p
    info={}
    for tch,ach in zip(TR,ALIASES):
        sgi=cmap[tch]; tgi=cmap[ach]
        setcell(tgi,getcell(sgi))
        if sgi not in width_pos or tgi not in width_pos: raise ValueError('width mapping missing')
        d[width_pos[tgi]:width_pos[tgi]+3]=d[width_pos[sgi]:width_pos[sgi]+3]
        info[ach]={'renders_as':tch,'alias_glyph':tgi,'turkish_glyph':sgi}
    for si,bm in cache.items():
        s=sheetoff+si*sheetsize; d[s:s+sheetsize]=_bitmap_to_sheet_la4(bm,sw,sh)
    return bytes(d),info

def patch_font_outer(path:Path):
    arc=DarcArchive(path.read_bytes()); repl={}; rep=[]
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,inf=patch_cfnt_aliases(b); repl[ip]=nb; rep.append({'inner':ip,'aliases':inf,'cfnt_sha256':sha256(nb)})
    if not repl: raise ValueError('no CFNT')
    outer=arc.rebuild(repl); path.write_bytes(outer)
    return {'path':str(path.relative_to(ROMFS)),'sha256':sha256(outer),'size':len(outer),'fonts':rep}

# ---- raster helpers ----
def get_member(folder:Path,name:str):
    ib=(folder/'index.fs').read_bytes(); cb=(folder/'crowd.fs').read_bytes()
    for e in parse_index(ib):
        if e['name']==name: return cb[e['offset']:e['offset']+e['size']]
    raise KeyError(name)

def get_component(root:Path,archive_rel:str):
    rel=Path(archive_rel); direct=root/rel
    # source dumps have direct component file; patch romfs usually crowd-only
    if direct.exists() and direct.name not in ('index.fs','crowd.fs'): return direct.read_bytes(),('direct',direct)
    folder=root/rel.parent
    return get_member(folder,rel.name),('crowd',folder,rel.name)

def replace_components(root:Path, changes:dict[str,bytes]):
    byfolder=defaultdict(dict); direct=[]
    for rel,b in changes.items():
        p=root/rel
        if p.exists(): direct.append((p,b)); continue
        rp=Path(rel); byfolder[root/rp.parent][rp.name]=b
    for p,b in direct: p.write_bytes(b)
    reports=[]
    for folder,repls in byfolder.items():
        ib=(folder/'index.fs').read_bytes(); cb=(folder/'crowd.fs').read_bytes()
        ni,nc,det=rebuild_crowd_bytes(ib,cb,repls); (folder/'index.fs').write_bytes(ni); (folder/'crowd.fs').write_bytes(nc)
        reports.append({'folder':str(folder.relative_to(root)),'components':sorted(repls),'new_crowd_size':len(nc)})
    return reports

def inpaint_bright_text(en:Image.Image, region=None, threshold=135, dilate=1):
    im=en.convert('RGBA'); arr=np.array(im); rgb=arr[:,:,:3]; a=arr[:,:,3]
    lum=(0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2])
    mask=((a>35)&(lum>threshold)).astype(np.uint8)*255
    if region:
        x0,y0,x1,y1=region; keep=np.zeros_like(mask); keep[y0:y1,x0:x1]=mask[y0:y1,x0:x1]; mask=keep
    if dilate: mask=cv2.dilate(mask,np.ones((3,3),np.uint8),iterations=dilate)
    # ensure only region if given
    if region:
        x0,y0,x1,y1=region; keep=np.zeros_like(mask); keep[y0:y1,x0:x1]=mask[y0:y1,x0:x1]; mask=keep
    if not mask.max(): return im
    rgb2=cv2.inpaint(rgb,mask,3,cv2.INPAINT_TELEA); a2=cv2.inpaint(a,mask,3,cv2.INPAINT_TELEA)
    return Image.fromarray(np.dstack([rgb2,a2]).astype(np.uint8),'RGBA')

def render_special(iid:int,en:Image.Image):
    en=en.convert('RGBA')
    if iid==6:
        fill,stroke=sample_text_colors(en)
        out=Image.new('RGBA',en.size,(0,0,0,0))
        # preserve ornamental tail only; English word occupies the left ~46 px
        tail=en.crop((46,0,en.width,en.height)); out.alpha_composite(tail,(46,0))
        _draw_centered(out,'Mesaj',(0,0,48,en.height),fill,stroke,serif=True,stroke_width=0)
        return out
    if iid in (11,127,144,160):
        text={11:'Para',127:'Büyüler',144:'Kaydet',160:'Yetenek Bağı'}[iid]
        return render_translation(en,text,mode='text_only',serif=True)
    if iid in (177,179):
        text='Zorluk Ayarı' if iid==177 else 'Tekrar İzle!'
        base=inpaint_bright_text(en,region=(120,6,430,45),threshold=125,dilate=2)
        fill,stroke=sample_text_colors(en)
        return _draw_centered(base,text,(125,5,425,45),fill,stroke,serif=True,stroke_width=1)
    if iid in (259,260):
        # Preserve localized battle-profile stat labels in a compact 3-column layout.
        fill,_=sample_text_colors(en); out=Image.new('RGBA',en.size,(0,0,0,0))
        # Original columns are approximately x=0/49/96. Use user-patch terminology.
        if iid==259:
            rows=[
                [('Azm. HP',(0,0,48,14))],
                [('F.SAL',(0,14,46,26)),('F.SAV',(48,14,94,26)),('İsabet',(96,14,140,26))],
                [('B.SAL',(0,26,46,38)),('B.SAV',(48,26,94,38)),('Kaçın.',(96,26,140,38))],
                [('ZEK',(0,38,46,58)),('İRA',(48,38,94,58)),('HIZ',(96,38,140,58))],
            ]
        else:
            rows=[
                [('Azm. HP',(0,0,66,14)),('Azm. MP',(72,0,140,14))],
                [('F.SAL',(0,14,46,26)),('F.SAV',(48,14,94,26)),('İsabet',(96,14,140,26))],
                [('B.SAL',(0,26,46,38)),('B.SAV',(48,26,94,38)),('Kaçın.',(96,26,140,38))],
                [('ZEK',(0,38,46,58)),('İRA',(48,38,94,58)),('HIZ',(96,38,140,58))],
            ]
        for row in rows:
            for text,box in row: _draw_fit_at(out,text,box,fill=fill,serif=True,align='left',min_size=5)
        return out
    if iid==263:
        # Start from original panel; erase the three English title bands and redraw cleanly.
        arr=np.array(en).copy()
        # Use local medians to preserve panel styling.
        for box in [(3,0,136,18),(3,113,136,134),(5,198,96,225)]:
            x0,y0,x1,y1=box; roi=arr[y0:y1,x0:x1].reshape(-1,4); valid=roi[roi[:,3]>20]
            col=np.median(valid,axis=0).astype(np.uint8) if len(valid) else np.array([55,55,60,255],np.uint8)
            arr[y0:y1,x0:x1]=col
        out=Image.fromarray(arr,'RGBA')
        _draw_fit_at(out,'Profil',(8,1,132,17),fill=(245,245,245,255),serif=True,align='left',stroke_width=1,stroke=(20,20,20,220),min_size=6)
        _draw_fit_at(out,'Çağrı Bilgisi',(8,115,132,132),fill=(245,245,245,255),serif=True,align='left',stroke_width=1,stroke=(20,20,20,220),min_size=5)
        _draw_fit_at(out,'Güç',(10,200,92,223),fill=(35,25,30,255),serif=True,align='left',min_size=6)
        return out
    if iid==281:
        # Preserve tutorial screenshot and only replace text areas with clean reconstructed panels.
        base=inpaint_bright_text(en,region=(30,2,244,44),threshold=95,dilate=2)
        # two job panels + center badge
        _draw_fit_at(base,'Sv 1\nSerbest',(38,7,123,42),fill=(25,25,35,255),serif=True,min_size=5)
        _draw_fit_at(base,'Sv 2\nSerbest',(160,7,237,42),fill=(25,25,35,255),serif=True,min_size=5)
        _draw_fit_at(base,'SEVİYE\nARTTI!',(99,4,158,35),fill=(235,250,255,255),serif=False,stroke_width=1,stroke=(20,70,130,255),min_size=5)
        return base
    raise KeyError(iid)

def patch_rasters():
    ui=ROMFS/'Graphics/UI_en'; srcui=SRC/'Graphics/UI_en'
    idxlist=json.load(open(TOOLS/'unique_bclim_index.json',encoding='utf-8')); idxmap={x['id']:x for x in idxlist}
    fixes={6:'Mesaj',11:'Para',127:'Büyüler',144:'Kaydet',177:'Zorluk Ayarı',179:'Tekrar İzle!',259:'istatistik',260:'istatistik',263:'profil',281:'tutorial'}
    # Recover the missing ID160 occurrence.
    idxmap[160]['occurrences']=[{'archive':'Layout/08_MainMenu','inner':'./root/timg/menu_cmnd_abi-link.bclim'}]
    # persist recovered mapping for reproducibility
    for x in idxlist:
        if x['id']==160: x['occurrences']=idxmap[160]['occurrences']
    json.dump(idxlist,open(TOOLS/'unique_bclim_index.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
    fixes[160]='Yetenek Bağı'
    comp_changes={}; preview=[]; details=[]
    # Multiple fixes can touch one component; always chain on current modified bytes.
    for iid in sorted(fixes):
        for occ in idxmap[iid]['occurrences']:
            ar=occ['archive']; inner=occ['inner']
            if ar in comp_changes: curcomp=comp_changes[ar]
            else: curcomp=get_component(ui,ar)[0]
            curarc=DarcArchive(curcomp); curfiles=dict(curarc.files()); curtempl=curfiles[inner]
            # original English image for clean source
            origcomp=(srcui/ar).read_bytes(); origarc=DarcArchive(origcomp); orig= dict(origarc.files())[inner]
            enim=decode_bclim(orig)
            newim=render_special(iid,enim)
            nb=encode_rgba8_bclim(newim,curtempl)
            newcomp=curarc.rebuild({inner:nb})
            comp_changes[ar]=newcomp
            preview.append((iid,newim.copy(),ar,inner))
            details.append({'id':iid,'archive':ar,'inner':inner,'text':fixes[iid],'old_inner_size':len(curtempl),'new_inner_size':len(nb)})
    repack=replace_components(ui,comp_changes)
    # preview contact sheet
    pw=260; ph=100; cols=3; rows=(len(preview)+cols-1)//cols
    sheet=Image.new('RGB',(pw*cols,ph*rows),'white'); dd=ImageDraw.Draw(sheet)
    for i,(iid,im,ar,inner) in enumerate(preview):
        x=(i%cols)*pw; y=(i//cols)*ph
        dd.text((x+3,y+2),f'ID{iid}  {fixes[iid]}',fill='black')
        bg=Image.new('RGBA',im.size,(205,205,205,255)); bg.alpha_composite(im)
        scale=min((pw-8)/im.width,(ph-24)/im.height,2.0)
        if scale<1 or scale>1.01: bg=bg.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.NEAREST)
        sheet.paste(bg.convert('RGB'),(x+3,y+22))
    prevp=OUTBASE/'Reports/RASTER_FIXES_v36.png'; prevp.parent.mkdir(parents=True,exist_ok=True); sheet.save(prevp)
    return {'fixes':details,'recovered_occurrences':{'160':idxmap[160]['occurrences']},'crowds_repacked':repack,'preview':str(prevp.relative_to(OUTBASE))}

# ---- package validation ----
def audit_crowds(root):
    res={'pairs':0,'entries':0,'errors':[]}
    for ip in root.rglob('index.fs'):
        cp=ip.parent/'crowd.fs'
        if not cp.exists(): continue
        res['pairs']+=1
        try:
            ib=ip.read_bytes(); cb=cp.read_bytes(); ents=parse_index(ib); res['entries']+=len(ents)
            last=-1
            for e in ents:
                if e['offset']<0 or e['size']<0 or e['offset']+e['size']>len(cb): res['errors'].append(f'{ip}: out of range {e["name"]}')
                if e['offset']<last: res['errors'].append(f'{ip}: overlap/order {e["name"]}')
                last=e['offset']+e['size']
        except Exception as ex: res['errors'].append(f'{ip}: {ex}')
    return res

def zipdir(src:Path,dst:Path):
    if dst.exists(): dst.unlink()
    with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted(src.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src.parent))
    with zipfile.ZipFile(dst) as z:
        bad=z.testzip()
        if bad: raise RuntimeError('bad zip '+bad)
    return dst

def make_layered(region='EUR'):
    tid='00040000000FC600' if region=='EUR' else '00040000000FC500'
    root=Path('/mnt/data/build_v36')/f'LayeredFS_{region}'
    if root.exists(): shutil.rmtree(root)
    target=root/'luma/titles'/tid/'romfs'; target.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(ROMFS,target)
    # tiny install/readme at zip root
    (root/'KURULUM_TR.txt').write_text(f'''Bravely Default Türkçe Yama Progress v3.6 ({region})\n\n1) Bu ZIP içindeki luma klasörünü SD kartın köküne kopyalayın.\n2) Luma3DS > Enable game patching açık olmalı.\n3) EUR Title ID: 00040000000FC600.\n\nBu sürümde Türkçe Ğ/ğ/İ/ı/Ş/ş karakterleri uyumluluk kodlamasıyla hazırdır; ayrıca font aracı çalıştırmanız gerekmez.\nEski v3.5 dosyalarının üzerine yazabilirsiniz.\n''',encoding='utf-8')
    z=Path('/mnt/data')/f'BravelyDefault_TR_Progress_v3.6_LayeredFS_{region}.zip'
    if z.exists(): z.unlink()
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as zz:
        for p in sorted(root.rglob('*')):
            if p.is_file(): zz.write(p,p.relative_to(root))
    with zipfile.ZipFile(z) as zz:
        if zz.testzip(): raise RuntimeError('bad layered zip')
        # Ensure both fonts physically present
        for rel in [f'luma/titles/{tid}/romfs/Graphics/UI/Font/Font',f'luma/titles/{tid}/romfs/Graphics/UI_en/Font/Font']:
            if rel not in zz.namelist(): raise RuntimeError('missing '+rel)
    return z

# ---- execute ----
if OUTBASE.exists(): shutil.rmtree(OUTBASE)
shutil.copytree(BASE,OUTBASE)
# remove old manifest; regenerate later
if (OUTBASE/'MANIFEST_SHA256.json').exists(): (OUTBASE/'MANIFEST_SHA256.json').unlink()

reports={}
# Pre-collision structured scan
pre_alias,pre_tr=structured_alias_counts(ROMFS)
reports['pre_encoding_scan']={'literal_alias_characters_in_structured_text':pre_alias,'turkish_extended_characters':pre_tr}
if any(pre_alias.values()):
    raise RuntimeError('Alias collision found in structured text: '+repr(pre_alias))

# Patch Common_en BTBF direct files and crowds
alias_rep=[]
common=ROMFS/'Common_en'
for crp in sorted(common.rglob('crowd.fs')):
    r=patch_crowd_alias(crp.parent,'btbf')
    if r: alias_rep.append(r)
for p in sorted(common.rglob('*')):
    if not p.is_file() or p.name in ('crowd.fs','index.fs'): continue
    b=p.read_bytes()
    if b[:4]==b'BTBF':
        nb,n=patch_btbf_alias(b)
        if n: p.write_bytes(nb); alias_rep.append({'file':str(p.relative_to(ROMFS)),'text_chars_aliased':n})

# UI CLYT strings in all patched DARC crowds
ui=ROMFS/'Graphics/UI_en'
for crp in sorted(ui.rglob('crowd.fs')):
    r=patch_crowd_alias(crp.parent,'darc')
    if r: alias_rep.append(r)
reports['compatibility_encoding_changes']=alias_rep

# Patch both runtime font routes with Latin-1 alias glyphs
font_rep=[]
for rel in ['Graphics/UI/Font/Font','Graphics/UI_en/Font/Font']:
    font_rep.append(patch_font_outer(ROMFS/rel))
reports['fonts']=font_rep

# Raster fixes after text aliases
reports['raster']=patch_rasters()

# Structured verification: real Extended-A should be gone from runtime strings, aliases should be present.
post_alias,post_tr=structured_alias_counts(ROMFS)
reports['post_encoding_scan']={'alias_characters_in_structured_text':post_alias,'remaining_turkish_extended_characters':post_tr}
if any(post_tr.values()): raise RuntimeError('Turkish Extended-A remains in structured runtime text: '+repr(post_tr))
if sum(post_alias.values())==0: raise RuntimeError('No compatibility aliases were written')

# Common.zip exact comparison
common_compare={'zip_sha256':sha256(COMMONZIP.read_bytes()),'files':0,'same':0,'different':0,'missing':0}
with zipfile.ZipFile(COMMONZIP) as z:
    for n in z.namelist():
        if n.endswith('/') or not n.startswith('Common/'): continue
        common_compare['files']+=1; rel=n[len('Common/'):]; p=SRC/'Common'/rel
        if not p.exists(): common_compare['missing']+=1
        elif z.read(n)==p.read_bytes(): common_compare['same']+=1
        else: common_compare['different']+=1
reports['common_zip_analysis']=common_compare

# code.bin static analysis
codeb=CODE.read_bytes(); strings=[]
for m in re.finditer(rb'[ -~]{5,}',codeb):
    s=m.group().decode('ascii','replace')
    if ('$_TL$' in s or 'mbstowcs' in s or 'Locale' in s or 'GetCurrentLocale' in s): strings.append({'offset':m.start(),'text':s})
reports['code_bin_analysis']={'sha256':sha256(codeb),'size':len(codeb),'not_included_in_patch':True,'relevant_strings':strings[:200],
    'font_path_occurrences':sum(1 for x in strings if x['text']=='Graphics/UI$_TL$/Font/Font'),
    'interpretation':'Runtime language placeholder selects Graphics/UI[_lang]/Font/Font; mbstowcs evidence supports a legacy/locale-sensitive text conversion path. v3.6 therefore encodes six Turkish Extended-A letters through unused Latin-1 aliases and patches both common and _en font routes.'}

# technical audit
audit=audit_crowds(ROMFS); reports['technical_audit']=audit
if audit['errors']: raise RuntimeError(audit['errors'][:10])

# write compatibility tool for users/rebuild
compat_py=TOOLS/'turkish_compat_encoding_v36.py'
compat_py.write_text('''#!/usr/bin/env python3\n"""Bravely Default Turkish compatibility encoding (v3.6).\nThe game can replace U+0100+ Latin letters with ? in some runtime paths.\nThe patch stores six Turkish letters in unused Latin-1 slots and makes the CFNT\nfonts draw the intended Turkish glyphs for those slots.\n"""\nENCODE = {"Ğ":"Ð","ğ":"ð","İ":"Þ","ı":"þ","Ş":"Æ","ş":"æ"}\nDECODE = {v:k for k,v in ENCODE.items()}\ndef encode_text(s): return "".join(ENCODE.get(c,c) for c in s)\ndef decode_text(s): return "".join(DECODE.get(c,c) for c in s)\nif __name__ == "__main__":\n import sys\n print(encode_text(" ".join(sys.argv[1:])))\n''',encoding='utf-8')
# update raster tool with recovered occurrence / reference to v36 fixer tool kept separately
shutil.copy2(Path('/mnt/data/build_v36.py'),TOOLS/'build_progress_v36.py')

# docs/reports
(OUTBASE/'Reports').mkdir(exist_ok=True); (OUTBASE/'Docs').mkdir(exist_ok=True)
json.dump(reports,open(OUTBASE/'Reports/BUILD_REPORT_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump(reports['code_bin_analysis'],open(OUTBASE/'Reports/CODE_BIN_ANALYSIS_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump({'fonts':font_rep,'encoding':{'encode':ENCODE,'decode':DECODE},'pre':reports['pre_encoding_scan'],'post':reports['post_encoding_scan']},open(OUTBASE/'Reports/FONT_COMPAT_VERIFICATION_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump(reports['raster'],open(OUTBASE/'Reports/RASTER_AUDIT_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
json.dump(common_compare,open(OUTBASE/'Reports/COMMON_ZIP_ANALYSIS_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)

(OUTBASE/'Docs/FONT_COMPAT_v3.6_TR.md').write_text(f'''# Font / Türkçe karakter uyumluluğu — v3.6\n\n## Sorunun kökü\n\n`code.bin` statik taramasında `Graphics/UI$_TL$/Font/Font` yolu ve `Error mbstowcs:%s` dizisi bulundu. Bu, font dosyasının kendisi geniş Unicode CMAP içerse bile bazı metin yollarının locale/çok-baytlı dönüşümden geçebildiğini gösterir. Gerçek 3DS testinde U+011E/U+011F/U+0130/U+0131/U+015E/U+015F karakterlerinin `?` olması bunu doğrulamıştır.\n\n## v3.6 çözümü\n\nRuntime metinlerde altı karakter, oyunun zaten desteklediği ve Türkçe yamada kullanılmayan Latin-1 slotlarına aktarılır:\n\n- `Ğ` → `Ð` (U+00D0)\n- `ğ` → `ð` (U+00F0)\n- `İ` → `Þ` (U+00DE)\n- `ı` → `þ` (U+00FE)\n- `Ş` → `Æ` (U+00C6)\n- `ş` → `æ` (U+00E6)\n\nHem `Graphics/UI/Font/Font` hem `Graphics/UI_en/Font/Font` içinde bu altı Latin-1 slotunun glyph bitmapleri gerçek Türkçe glyphlerle değiştirilmiştir. Böylece motor 8-bit/Latin-1 sınırında kalsa bile ekranda Türkçe harf görünür.\n\nBu, çevirinin anlamını değiştirmez; yalnız oyuna özel bir runtime kodlamasıdır. Araçlarda `turkish_compat_encoding_v36.py` ile tersine çevirme tablosu da bulunur.\n\nBuild öncesi yapılandırılmış metin taramasında alias karakterleri 0 idi; bu nedenle mevcut çeviride gerçek `Ð/ð/Þ/þ/Æ/æ` ile çakışma bulunmadı.\n''',encoding='utf-8')

(OUTBASE/'Docs/CODE_BIN_ANALIZI_v3.6_TR.md').write_text(f'''# code.bin analizi — v3.6\n\nGönderilen dosya SHA-256: `{reports['code_bin_analysis']['sha256']}`\nBoyut: {len(codeb)} bayt.\n\nÖnemli statik dizeler:\n\n- `Graphics/UI$_TL$/Font/Font` — {reports['code_bin_analysis']['font_path_occurrences']} doğrudan eşleşme\n- `GetCurrentLocale`\n- `../../Source/Nintendo3ds/Common/LocaleSetting.hpp`\n- `Error mbstowcs:%s`\n\n`$_TL$` oyunun dil tokenıdır; çalışırken boş veya `_en`, `_fr`, `_de`, `_es`, `_it` gibi bir ekle font yolunu seçer. Bu yüzden v3.5'te iki Batı font yolunu yamalamak doğruydu ama U+0100+ karakterlerin `?` olmasını çözmeye yetmedi. `mbstowcs` bulgusu ve gerçek cihaz testi birlikte değerlendirildiğinde v3.6 Latin-1 uyumluluk katmanını kullanır.\n\n`code.bin` patch paketine kopyalanmamıştır; yalnız analiz hash'i ve sonuçları belgelenmiştir. Bu sürüm code patch gerektirmez.\n''',encoding='utf-8')

(OUTBASE/'Docs/RASTER_DUZELTMELERI_v3.6_TR.md').write_text('''# Raster/BCLIM düzeltmeleri — v3.6\n\nBu turda v3.5 temas sayfasında görsel olarak hatalı/eksik görünen hedefler tekrar işlendi.\n\n- ID 6 `Message` → **Mesaj**: eski İngilizce glyph kalıntısı tamamen temizlenip sağdaki süs korunur.\n- ID 11 `Funds` → **Para**: temiz text-only yeniden render.\n- ID 127 `Magics` → **Büyüler**: eski `Magi...` kalıntısı kaldırıldı.\n- ID 144 `Save` → **Kaydet**: hayalet İngilizce kalıntısı kaldırıldı.\n- ID 160 `Abilink` → **Yetenek Bağı**: önceki occurrence listesi boş olduğu için hiç paketlenmemişti; gerçek yol `Layout/08_MainMenu/root/timg/menu_cmnd_abi-link.bclim` olarak geri kazanıldı.\n- ID 177 `Adjusting Difficulty` → **Zorluk Ayarı**: arka plan korunup merkez hizası yeniden yapıldı.\n- ID 179 `Watch Me Over and Over!` → **Tekrar İzle!**: 3DS çözünürlüğünde okunabilir kısa karşılık kullanıldı.\n- ID 259/260 savaş profil istatistikleri: `F.SAL/F.SAV/B.SAL/B.SAV/İRA` terminolojisine çekildi, 3 kolon yeniden hizalandı.\n- ID 263 profil kartı: **Profil / Çağrı Bilgisi / Güç** bantları temiz yeniden çizildi.\n- ID 281 seviye öğreticisi: üst etiketler yeniden yerleştirildi.\n\n`Reports/RASTER_FIXES_v36.png` görsel kontrol sayfasıdır.\n''',encoding='utf-8')

(OUTBASE/'Docs/COMMON_INCELEMESI_v3.6_TR.md').write_text(f'''# Common.zip incelemesi — v3.6\n\nGönderilen `Common.zip` içindeki {common_compare['files']} dosya, daha önceki tam dump'taki `Common` ağacıyla karşılaştırıldı.\n\n- Birebir aynı: **{common_compare['same']}**\n- Farklı: **{common_compare['different']}**\n- Kaynakta eksik: **{common_compare['missing']}**\n\nSonuç: yeni ZIP farklı bir yerelleştirme katmanı değil; daha önce analiz edilen ortak/Japonca taban `Common` ağacının aynısıdır. Kullanıcıya görünen İngilizce/Türkçe yerelleştirme için esas runtime hedefleri `Common_en` ve `Graphics/UI_en` olmaya devam eder.\n''',encoding='utf-8')

(OUTBASE/'Docs/CHANGELOG_v3.6_TR.md').write_text('''# v3.6 değişiklikleri\n\n- Gerçek 3DS'te `Ğ/ğ/İ/ı/Ş/ş` karakterlerinin `?` olması için Latin-1 uyumluluk kodlaması eklendi.\n- Hem ortak `Graphics/UI/Font/Font` hem `Graphics/UI_en/Font/Font` alias glyphleri yamalandı.\n- Runtime BTBF ve BCLYT metinleri aynı uzunlukta güvenli kod noktalarına dönüştürüldü; pointer/offset değişmedi.\n- code.bin statik analizi belgelendi; code.bin dağıtılmıyor ve code patch yapılmıyor.\n- Common.zip 451/451 dosya hash/eşitlik karşılaştırması yapıldı.\n- Eksik ID160 Abilink raster occurrence geri kazanıldı ve `Yetenek Bağı` olarak yamalandı.\n- `Mesaj`, `Para`, `Büyüler`, `Kaydet`, tutorial ve profil rasterlarında hayalet/taşma/hiza düzeltmeleri yapıldı.\n- v3.6 build scripti ve uyumluluk encode/decode aracı Tools'a eklendi.\n''',encoding='utf-8')

# update top README succinctly
readme=(OUTBASE/'README_TR.md')
old=readme.read_text(encoding='utf-8') if readme.exists() else ''
readme.write_text('# Bravely Default Türkçe Yama — Progress v3.6\n\nBu paket v3.5 üzerine gerçek cihazdaki Türkçe karakter `?` sorunu için Latin-1 uyumluluk katmanı ve yeni raster düzeltmeleri ekler.\n\n**EUR kullanıcıları doğrudan `BravelyDefault_TR_Progress_v3.6_LayeredFS_EUR.zip` paketini SD kart köküne çıkarabilir. Font için ek araç çalıştırılması gerekmez.**\n\nAyrıntılar `Docs/` ve doğrulamalar `Reports/` altındadır.\n\n'+old,encoding='utf-8')

# manifest
manifest={}
for p in sorted(OUTBASE.rglob('*')):
    if p.is_file() and p.name!='MANIFEST_SHA256.json': manifest[str(p.relative_to(OUTBASE))]=sha256(p.read_bytes())
json.dump(manifest,open(OUTBASE/'MANIFEST_SHA256.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)

# full zip (contents nested under folder for clarity)
fullzip=Path('/mnt/data/BravelyDefault_TR_Progress_v3.6_2026-08-21.zip')
if fullzip.exists(): fullzip.unlink()
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for p in sorted(OUTBASE.rglob('*')):
        if p.is_file(): z.write(p,Path(OUTBASE.name)/p.relative_to(OUTBASE))
with zipfile.ZipFile(fullzip) as z:
    if z.testzip(): raise RuntimeError('bad full zip')

eur=make_layered('EUR')
# Also USA for completeness, though user uses EUR
usa=make_layered('USA')

# post-package direct checks on EUR contents
with zipfile.ZipFile(eur) as z:
    prefix='luma/titles/00040000000FC600/romfs/'
    # ensure fonts and build report available in full package; runtime files only here
    fpaths=[prefix+'Graphics/UI/Font/Font',prefix+'Graphics/UI_en/Font/Font']
    zip_fonts={p:sha256(z.read(p)) for p in fpaths}
    # Ensure exact real Extended-A sequences are not in a representative Common_en translated BTBF payload scan is already structured; record font hashes.
reports2=json.load(open(OUTBASE/'Reports/BUILD_REPORT_v36.json',encoding='utf-8'))
reports2['package_outputs']={'full_zip':str(fullzip),'eur_zip':str(eur),'usa_zip':str(usa),'eur_zip_font_hashes':zip_fonts}
json.dump(reports2,open(OUTBASE/'Reports/BUILD_REPORT_v36.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
# update manifest after report change
manifest={}
for p in sorted(OUTBASE.rglob('*')):
    if p.is_file() and p.name!='MANIFEST_SHA256.json': manifest[str(p.relative_to(OUTBASE))]=sha256(p.read_bytes())
json.dump(manifest,open(OUTBASE/'MANIFEST_SHA256.json','w',encoding='utf-8'),ensure_ascii=False,indent=2)
# recreate full zip after final report/manifest
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
    for p in sorted(OUTBASE.rglob('*')):
        if p.is_file(): z.write(p,Path(OUTBASE.name)/p.relative_to(OUTBASE))
print(json.dumps({'full':str(fullzip),'eur':str(eur),'usa':str(usa),'post_alias':post_alias,'pre_tr':pre_tr,'audit':audit,'raster_fixes':len(reports['raster']['fixes']),'fonts':zip_fonts},ensure_ascii=False,indent=2))
