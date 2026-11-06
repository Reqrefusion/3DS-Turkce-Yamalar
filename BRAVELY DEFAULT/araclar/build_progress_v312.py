#!/usr/bin/env python3
from pathlib import Path
import sys, shutil, json, struct, hashlib, zipfile, math
from collections import defaultdict, Counter
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE=Path('/mnt/data/build_v311/BravelyDefault_TR_Progress_v3.11_2026-08-22')
OUTROOT=Path('/mnt/data/build_v312')
OUT=OUTROOT/'BravelyDefault_TR_Progress_v3.12_2026-08-22'
SRCG=Path('/mnt/data/fix_font_v34/src/di#U011fer #U015feyler/Graphics')
if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUTROOT.mkdir(parents=True)
shutil.copytree(BASE,OUT)
TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'; ROMFS=OUT/'romfs'; TRROOT=ROMFS/'Graphics/UI_en'
sys.path.insert(0,str(TOOLS))
import repack_bravely as rb
from bravely_ui_tools import DarcArchive, cfnt_char_map, _sheet_to_bitmap_la4, _bitmap_to_sheet_la4, _alpha, bclyt_entries
from bclim_tools import decode_bclim, encode_rgba8_bclim
from raster_patch_tools import pick_font

VERSION='v3.12'
report={'version':VERSION,'subtitle_font':{},'font':{},'return_to_title':{},'technical':{}}
def sha(b): return hashlib.sha256(b).hexdigest()

# ---------- archive helpers ----------
def member_map(root:Path):
    m={}
    for idx in root.rglob('index.fs'):
        cp=idx.with_name('crowd.fs')
        if not cp.is_file(): continue
        try: es=rb.parse_index(idx.read_bytes())
        except: continue
        frel=str(idx.parent.relative_to(root)).replace('\\','/')
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

# ---------- CFNT helpers ----------
def cfnt_sections(d:bytes):
    hs=struct.unpack_from('<H',d,6)[0]; off=hs; out=[]
    while off+8<=len(d):
        mg=d[off:off+4]; sz=struct.unpack_from('<I',d,off+4)[0]
        if sz<8 or off+sz>len(d): break
        out.append((mg,off,sz)); off+=sz
    return out

def patch_cfnt_v312(cfnt:bytes):
    d=bytearray(cfnt); cmap=cfnt_char_map(cfnt)
    for c in ['i','g','G','ı','þ','ğ','ð','Ğ','Ð']:
        if c not in cmap: raise ValueError(f'missing {c!r}')
    secs=cfnt_sections(cfnt); t=next(o for m,o,s in secs if m==b'TGLP')
    cw,ch,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,t+8)
    if fmt!=9: raise ValueError('Expected LA4 CFNT')
    cache={}
    def bitmap(si):
        if si not in cache:
            st=sheetoff+si*sheetsize; cache[si]=_sheet_to_bitmap_la4(bytes(d[st:st+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cw+1); y0=(rem//cols)*(ch+1); bm=bitmap(si)
        return [[bm[(y0+y)*sw+x0+x] for x in range(cw)] for y in range(ch)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cw+1); y0=(rem//cols)*(ch+1); bm=bitmap(si)
        for y in range(ch):
            for x in range(cw): bm[(y0+y)*sw+x0+x]=c[y][x]
    def bbox(c):
        pts=[(x,y) for y,row in enumerate(c) for x,v in enumerate(row) if _alpha(v)>0]
        return (min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)) if pts else (0,0,cw-1,ch-1)
    # dotless i: start from original i, remove detached dot, then remove the left/right hook in the first stem row.
    base_i=getcell(cmap['i']); rows_on=[any(_alpha(v)>0 for v in row) for row in base_i]
    groups=[]; st=None
    for y,on in enumerate(rows_on+[False]):
        if on and st is None: st=y
        elif not on and st is not None: groups.append((st,y-1)); st=None
    if len(groups)<2: raise ValueError('i has no detached dot')
    dot=groups[0]; body=groups[1]
    di=[r[:] for r in base_i]
    for y in range(dot[0],dot[1]+1):
        for x in range(cw): di[y][x]=0xf0
    body0=body[0]
    # The 14/17px source i has a one-row left shoulder at body start. At 3DS scale it looks reversed.
    # Replace only that first row with the next row's centered stem; all remaining i pixels stay untouched.
    srcrow=min(body0+1,body[1])
    di[body0]=di[srcrow][:]
    for c in ('ı','þ'): setcell(cmap[c],di)

    # g-breve: preserve the official g/G body and descender EXACTLY. Add only a strong separated breve.
    accent_meta={}
    def with_breve(basech):
        cell=[r[:] for r in getcell(cmap[basech])]
        x0,y0,x1,y1=bbox(cell); cx=(x0+x1)//2
        # leave one fully blank row immediately above base body
        bottom=y0-2
        mid=bottom-1; top=mid-1
        if top<0:
            top=0; mid=1; bottom=2
        # clear our accent rows (base has no pixels there in these fonts, but make it deterministic)
        for y in range(top,bottom+1):
            for x in range(cw): cell[y][x]=0xf0
        # wide shallow curved breve: #.....# / .#...#. / ..###..
        half=3 if cw<=14 else 4
        lx=max(0,cx-half); rx=min(cw-1,cx+half)
        cell[top][lx]=0xff; cell[top][rx]=0xff
        if lx+1<=rx-1:
            cell[mid][lx+1]=0xff; cell[mid][rx-1]=0xff
        lo=min(rx-2,lx+2); hi=max(lx+2,rx-2)
        for x in range(lo,hi+1): cell[bottom][x]=0xff
        return cell,{'base_bbox':[x0,y0,x1,y1],'breve_rows':[top,mid,bottom],'breve_x':[lx,rx],'gap_row':y0-1}
    g,gm=with_breve('g'); G,GM=with_breve('G')
    for c in ('ğ','ð'): setcell(cmap[c],g)
    for c in ('Ğ','Ð'): setcell(cmap[c],G)
    # copy source widths to aliases/new chars
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
    return bytes(d),{'cell':[cw,ch],'baseline':baseline,'dot_rows':list(dot),'body_rows':list(body),'normalized_body_first_row':body0,'g':gm,'G':GM,'map':{c:cmap[c] for c in ['i','ı','þ','g','ğ','ð']}}

font_infos=[]
for rel in ['Graphics/UI/Font/Font','Graphics/UI_en/Font/Font']:
    p=ROMFS/rel; arc=DarcArchive(p.read_bytes()); repl={}
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,info=patch_cfnt_v312(b); repl[ip]=nb; info.update({'archive':rel,'inner':ip,'sha256':sha(nb)}); font_infos.append(info)
    if repl: p.write_bytes(arc.rebuild(repl))
report['font']['patched']=font_infos

# ---------- verify subtitle font selection from source BCLYT ----------
def read_font_names(b:bytes):
    # pCfnl section stores nul-terminated font file names; extract known bcfnt strings safely.
    import re
    return sorted(set(x.decode('ascii','ignore') for x in re.findall(rb'[A-Za-z0-9_./-]+\.bcfnt',b)))
subaudit=[]
for rel in ['Layout/70_Subtitles','Layout/71_SubtitlesLower']:
    p=SRCG/'UI_en'/rel
    a=DarcArchive(p.read_bytes())
    for ip,b in a.files():
        if b[:4]==b'CLYT':
            ents=bclyt_entries(b)
            subaudit.append({'layout':rel,'inner':ip,'fonts':read_font_names(b),'txt1':[{'pane':e['pane'],'font_x':e['font_x'],'font_y':e['font_y'],'width':e['width'],'height':e['height']} for e in ents]})
report['subtitle_font']={'evidence':subaudit,'conclusion':'EU English subtitle layouts reference hikari.bcfnt at 14x14; patch target is Graphics/UI_en/Font/Font.'}

# ---------- glyph preview ----------
def extract_cells(font_archive:Path, chars):
    a=DarcArchive(font_archive.read_bytes()); cf=next(b for _,b in a.files() if b[:4]==b'CFNT'); cmap=cfnt_char_map(cf); secs=cfnt_sections(cf); t=next(o for m,o,s in secs if m==b'TGLP')
    cw,ch,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',cf,t+8); cache={}
    def cell(c):
        gi=cmap[c];si=gi//(cols*rows);rem=gi%(cols*rows);x0=(rem%cols)*(cw+1);y0=(rem//cols)*(ch+1)
        if si not in cache:
            st=sheetoff+si*sheetsize;cache[si]=_sheet_to_bitmap_la4(cf[st:st+sheetsize],sw,sh)
        bm=cache[si];return [[_alpha(bm[(y0+y)*sw+x0+x]) for x in range(cw)] for y in range(ch)]
    return cw,ch,baseline,{c:cell(c) for c in chars}
def make_preview(path,out,title):
    chars=['i','ı','þ','g','ğ','ð']; cw,ch,baseline,cells=extract_cells(path,chars); scale=14; pad=25; W=(cw*scale+pad)*len(chars); H=ch*scale+55
    im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
    for j,c in enumerate(chars):
        ox=j*(cw*scale+pad);d.text((ox+3,3),c,fill='black')
        for y,row in enumerate(cells[c]):
            for x,v in enumerate(row):
                if v:
                    q=255-int(v/15*255); d.rectangle((ox+x*scale,28+y*scale,ox+(x+1)*scale-1,28+(y+1)*scale-1),fill=(q,q,q))
        d.line((ox,28+baseline*scale,ox+cw*scale,28+baseline*scale),fill=(200,0,0))
    im.save(out)
make_preview(ROMFS/'Graphics/UI_en/Font/Font',REPORTS/'SUBTITLE_FONT_GLYPHS_v312.png','UI_en')
make_preview(ROMFS/'Graphics/UI/Font/Font',REPORTS/'COMMON_FONT_GLYPHS_v312.png','UI')

# ---------- Return-to-title compound raster fixes ----------
trmm=member_map(TRROOT); srcmm=member_map(SRCG/'UI_en')
crel='Layout/51_ARmovieTXT'
curcomp=extract_component(TRROOT,trmm,crel); srccomp=extract_component(SRCG/'UI_en',srcmm,crel)
if not curcomp or not srccomp: raise RuntimeError('ARmovieTXT missing')
curarc=DarcArchive(curcomp); srcarc=DarcArchive(srccomp); curfiles=dict(curarc.files()); srcfiles=dict(srcarc.files())

def draw_fit(im,text,box,max_size=10,min_size=6,fill=(255,255,255,255),stroke=1,stroke_fill=(30,30,30,220),serif=True):
    d=ImageDraw.Draw(im); fp=pick_font(serif)
    x0,y0,x1,y1=box; best=None
    for sz in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(fp,sz); bb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
        if bb[2]-bb[0]<=x1-x0 and bb[3]-bb[1]<=y1-y0: best=f; break
    if best is None: best=ImageFont.truetype(fp,min_size)
    bb=d.textbbox((0,0),text,font=best,stroke_width=stroke); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x=x0+(x1-x0-tw)//2-bb[0]; y=y0+(y1-y0-th)//2-bb[1]
    d.text((x,y),text,font=best,fill=fill,stroke_width=stroke,stroke_fill=stroke_fill)
    return {'font_size':best.size,'bbox':[x,y,x+tw,y+th],'box':list(box)}

def clean_rect(im,box,color):
    a=np.array(im).copy();x0,y0,x1,y1=box;a[y0:y1,x0:x1]=np.array(color,dtype=np.uint8);return Image.fromarray(a,'RGBA')

repl={}; fixes=[]; previews=[]
# ID7 camera_l_btn2: preserve all left controls and the original rounded panel. Only clear panel interior text.
inn='./root/timg/camera_l_btn2.bclim'; en=decode_bclim(srcfiles[inn]).convert('RGBA')
base=en.copy(); sample=en.getpixel((135,10)); base=clean_rect(base,(143,4,232,16),sample)
info=draw_fit(base,'Başlığa Dön',(137,2,238,18),max_size=11,min_size=6,fill=(255,255,255,190),stroke=1,stroke_fill=(80,80,80,180),serif=True)
repl[inn]=encode_rgba8_bclim(base,curfiles[inn]); fixes.append({'inner':inn,'id':7,'text':'Başlığa Dön','draw':info,'protected_left_identical':np.array_equal(np.asarray(base)[:,:130],np.asarray(en)[:,:130])});previews.append(('ID7',en,decode_bclim(curfiles[inn]).convert('RGBA'),base))
# ID8 camera_l_btn4: START lives at x=47..94. Never modify x<97; never modify right camera/R icon x>=210.
inn='./root/timg/camera_l_btn4.bclim'; en=decode_bclim(srcfiles[inn]).convert('RGBA')
base=en.copy(); sample=en.getpixel((105,10)); base=clean_rect(base,(108,4,208,16),sample)
info=draw_fit(base,'Başlığa Dön',(102,2,208,18),max_size=11,min_size=6,fill=(248,248,248,255),stroke=1,stroke_fill=(25,25,25,220),serif=True)
start_ident=np.array_equal(np.asarray(base)[:,47:95],np.asarray(en)[:,47:95]); right_ident=np.array_equal(np.asarray(base)[:,210:],np.asarray(en)[:,210:])
repl[inn]=encode_rgba8_bclim(base,curfiles[inn]); fixes.append({'inner':inn,'id':8,'text':'Başlığa Dön','draw':info,'start_region':[47,95],'start_region_identical':bool(start_ident),'right_icon_region_identical':bool(right_ident)});previews.append(('ID8',en,decode_bclim(curfiles[inn]).convert('RGBA'),base))
# ID10 start2: preserve B icon and original rounded panel, redraw text in the panel only.
inn='./root/timg/start2.bclim'; en=decode_bclim(srcfiles[inn]).convert('RGBA')
base=en.copy(); sample=en.getpixel((50,8)); base=clean_rect(base,(52,3,168,14),sample)
info=draw_fit(base,'Başlığa Dön',(45,1,169,16),max_size=11,min_size=6,fill=(250,250,250,255),stroke=1,stroke_fill=(35,35,35,220),serif=True)
b_icon_ident=np.array_equal(np.asarray(base)[:,:40],np.asarray(en)[:,:40])
repl[inn]=encode_rgba8_bclim(base,curfiles[inn]); fixes.append({'inner':inn,'id':10,'text':'Başlığa Dön','draw':info,'b_icon_region_identical':bool(b_icon_ident)});previews.append(('ID10',en,decode_bclim(curfiles[inn]).convert('RGBA'),base))
# rebuild AR component in correct crowd
newcomp=curarc.rebuild(repl); frel,name=trmm[crel]; rebuild_crowd(TRROOT,frel,{name:newcomp})
report['return_to_title']['fixes']=fixes

# Preview source / v3.11 / v3.12 for the three compound buttons
scale=3; cellw=750; rowh=90; sheet=Image.new('RGB',(cellw,rowh*len(previews)),'white');d=ImageDraw.Draw(sheet)
for r,(label,en,old,new) in enumerate(previews):
    y=r*rowh; d.text((5,y+3),f'{label}: EN source / v3.11 / v3.12',fill='black')
    x=5
    for im in [en,old,new]:
        v=im.resize((im.width*scale,im.height*scale),Image.NEAREST).convert('RGB'); sheet.paste(v,(x,y+25)); x+=v.width+15
sheet.save(REPORTS/'RETURN_TO_TITLE_BUTTONS_v312.png')

# ---------- docs ----------
(DOCS/'ALTYAZI_FONT_VE_GLYPH_FIX_v3.12_TR.md').write_text('''# Altyazı fontu ve ı/ğ düzeltmesi — v3.12

Bu turda altyazı fontunun hangi dosya olduğu doğrudan BCLYT kaynağından doğrulandı.

- `Graphics/UI_en/Layout/70_Subtitles/root/blyt/Subtitles.bclyt`
- `Graphics/UI_en/Layout/71_SubtitlesLower/root/blyt/Subtitles.bclyt`

İki layout da `hikari.bcfnt` adını içeriyor. İngilizce/Avrupa layoutlarında txt1 font boyutu 14×14'tür ve bunun karşılığı `Graphics/UI_en/Font/Font` içindeki 14×14 `hikari.bcfnt` dosyasıdır.

v3.11'de `ı` kaynak `i`den nokta silinerek üretiliyordu; ancak küçük fontun gövdesinin ilk satırında sola taşan tek satırlık bir omuz/serif vardır. 3DS ölçeklemesinde bu şekil ters/çarpık i gibi görünür. v3.12 noktayı kaldırdıktan sonra yalnız ilk gövde satırını bir sonraki merkezlenmiş gövde satırıyla eşitler. Alt gövde ve alt serif değişmez.

v3.11 `ğ` kuyruğunu güçlendirmeye çalışıyordu. Gerçek cihaz geri bildiriminde bunun kuyruğu bloklaştırdığı görüldü. v3.12 kaynak `g` bitmapini ve kuyruğunu birebir korur; yalnız gövdenin üstünde bir boş satır bırakarak daha geniş, tam alpha, üç satırlı breve ekler. Böylece kuyruk artık oyunun kendi `g` harfiyle aynıdır.

Kontrol: `Reports/SUBTITLE_FONT_GLYPHS_v312.png`.
''',encoding='utf8')
(DOCS/'BASLIGA_DON_START_DUGMESI_v3.12_TR.md').write_text('''# Başlığa Dön / START düğmesi — v3.12

Sorun yazı uzunluğundan ibaret değildi. `Layout/51_ARmovieTXT` içindeki birleşik BCLIM düğmeler eski raster patch'te yeniden çizilirken korunması gereken düğme zemini ve kontrol ikonlarına taşılmıştı.

Özellikle `camera_l_btn4.bclim` texture'ında START göstergesi x=47..94 aralığındadır. v3.12 bu bölgeyi kaynak İngilizce texture'dan byte/piksel olarak aynen korur ve Türkçe metni yalnız sağdaki x=102..208 metin paneline çizer. Sağdaki kamera/R bölgesi de korunur.

`camera_l_btn2.bclim` ve `start2.bclim` de aynı prensiple, kaynak düğme zemini ve ikonları korunarak yeniden yapılmıştır.

Kontrol görseli: `Reports/RETURN_TO_TITLE_BUTTONS_v312.png`.
''',encoding='utf8')
(DOCS/'CHANGELOG_v3.12_TR.md').write_text('''# Bravely Default TR — v3.12

- Altyazı layoutlarının `hikari.bcfnt` kullandığı BCLYT içinden doğrulandı.
- 14px altyazı fontunda `ı` gövdesinin ilk satırındaki ters/sol omuz kaldırıldı; noktasız i merkezlenmiş dikey gövdeye dönüştürüldü.
- `ğ` için v3.11'deki yapay kuyruk kalınlaştırması kaldırıldı. Kaynak `g` kuyruğu birebir korunuyor; yalnız daha görünür, gövdeden ayrılmış breve ekleniyor.
- `Başlığa Dön` yazısının START göstergesini kapattığı `camera_l_btn4` texture'ı kaynak görselden yeniden üretildi; START bölgesi artık hiç değiştirilmiyor.
- `camera_l_btn2` ve `start2` Başlığa Dön düğmeleri de ikon/zemin korunarak yeniden yapıldı.
- Önceki v3.11 çeviri, Common_en, Türkçe uyumluluk kodlaması, raster ve terminoloji ilerlemesinin tamamı korunur.
''',encoding='utf8')
shutil.copy2('/mnt/data/build_v312.py',TOOLS/'build_progress_v312.py')

# ---------- technical audit ----------
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
if errs: raise RuntimeError(errs[:5])
(REPORTS/'V312_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'TECHNICAL_AUDIT_v312.json').write_text(json.dumps(report['technical'],ensure_ascii=False,indent=2),encoding='utf8')

# manifest
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file(): manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')

# zips
full=Path('/mnt/data/BravelyDefault_TR_Progress_v3.12_2026-08-22.zip'); eur=Path('/mnt/data/BravelyDefault_TR_Progress_v3.12_LayeredFS_EUR.zip'); usa=Path('/mnt/data/BravelyDefault_TR_Progress_v3.12_LayeredFS_USA.zip')
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
# post-zip exact existence and font hashes
post={}
with zipfile.ZipFile(eur) as z:
    for rel in ['Graphics/UI/Font/Font','Graphics/UI_en/Font/Font']:
        n='luma/titles/00040000000FC600/romfs/'+rel; b=z.read(n); post[rel]={'size':len(b),'sha256':sha(b)}
    n='luma/titles/00040000000FC600/romfs/Graphics/UI_en/Layout/crowd.fs'; post['layout_crowd']={'size':len(z.read(n)),'sha256':sha(z.read(n))}
report['post_zip_eur']=post
(REPORTS/'V312_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'full':str(full),'eur':str(eur),'usa':str(usa),'font':font_infos,'subtitle':subaudit,'return':fixes,'technical':report['technical'],'post':post},ensure_ascii=False,indent=2))
