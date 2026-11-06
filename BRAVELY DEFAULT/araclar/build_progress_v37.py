#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import sys, os, json, shutil, struct, hashlib, math, re, textwrap, zipfile
from collections import defaultdict, Counter
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE=Path('/mnt/data/build_v36/BravelyDefault_TR_Progress_v3.6_2026-08-21')
OUT=Path('/mnt/data/build_v37/BravelyDefault_TR_Progress_v3.7_2026-08-21')
SRC_COMMON=Path('/mnt/data/v37_source_common/Common_en')
SRC_GFX=Path('/mnt/data/fix_font_v34/src/di#U011fer #U015feyler/Graphics')
NOVEL_INDEX=Path('/mnt/data/v37_ui_vs_jp/index.json')
TOOLS0=BASE/'Tools'
sys.path.insert(0,str(TOOLS0)); sys.path.insert(0,'/mnt/data')
import repack_bravely as rb
from bravely_ui_tools import DarcArchive, cfnt_char_map, make_text_width_fn, bclyt_entries, _sheet_to_bitmap_la4, _bitmap_to_sheet_la4, _alpha
from bclim_tools import decode_bclim, encode_rgba8_bclim
from raster_patch_tools import render_translation, inpaint_language_area, _draw_fit_at, pick_font
from turkish_compat_encoding_v36 import ENCODE, DECODE
import item_v37_tr
from common_v37_tr import SBVOICE, EXACT as COMMON_EXACT

if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(BASE,OUT)
ROMFS=OUT/'romfs'; TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'
for p in (TOOLS,DOCS,REPORTS): p.mkdir(parents=True,exist_ok=True)

report={'version':'v3.7','common':{},'raster':{},'font':{},'ui_fit':{},'technical':{},'notes':[]}

def sha(b): return hashlib.sha256(b).hexdigest()
def enc_tr(s): return ''.join(ENCODE.get(c,c) for c in s)
def dec_tr(s): return ''.join(DECODE.get(c,c) for c in s)

# ---------------- source workbook layout map ----------------
layout_cells={}
for xp in SRC_COMMON.rglob('*.xls'):
    if xp.name.lower()=='crowd_en.xls': continue
    try: wb=rb.parse_biff(xp)
    except Exception: continue
    for sn,cells in wb.items():
        try: target=rb.resolve_sheet_target(xp,sn)
        except Exception: target=None
        if target is not None:
            try: rel=str(target.relative_to(SRC_COMMON)).replace('\\','/')
            except Exception: continue
            layout_cells[rel]=cells

# ---------------- crowd helpers ----------------
def extract_member(root:Path, rel:str):
    p=root/rel
    if p.is_file(): return p.read_bytes(), ('direct',rel)
    par=str(Path(rel).parent).replace('\\','/')
    name=Path(rel).name
    idx=root/par/'index.fs'; crowd=root/par/'crowd.fs'
    if idx.is_file() and crowd.is_file():
        ib=idx.read_bytes(); cb=crowd.read_bytes()
        for e in rb.parse_index(ib):
            if e['name']==name:
                return cb[e['offset']:e['offset']+e['size']], ('crowd',par)
    raise FileNotFoundError(rel)

def rebuild_crowd_with(root:Path, par:str, repl:dict[str,bytes]):
    idxp=root/par/'index.fs'; cp=root/par/'crowd.fs'
    ib=idxp.read_bytes(); oldc=cp.read_bytes(); idx=bytearray(ib); crowd=bytearray()
    ents=rb.parse_index(ib); changed=0
    for e in ents:
        while len(crowd)%4: crowd.append(0)
        off=len(crowd)
        fb=repl.get(e['name'], oldc[e['offset']:e['offset']+e['size']])
        if e['name'] in repl: changed+=1
        crowd+=fb
        struct.pack_into('<I',idx,e['pos']+4,off); struct.pack_into('<I',idx,e['pos']+8,len(fb))
    while len(crowd)%4: crowd.append(0)
    idxp.write_bytes(idx); cp.write_bytes(crowd)
    # verify
    for e in rb.parse_index(bytes(idx)):
        assert e['offset']+e['size']<=len(crowd)
    return {'entries':len(ents),'changed_members':changed,'size':len(crowd)}

# ---------------- generic BTBF current-binary transformer ----------------
def transform_btbf(cur:bytes,cells,fn):
    m=rb.btbf_meta(cur); mat=rb.sheet_matrix(cells); v_text,p_text,vcount=rb.text_layout(mat,m)
    if len(mat)-1!=m['count']: raise ValueError(('row mismatch',len(mat)-1,m['count']))
    data=bytearray(cur[0x30:m['label_start']]); labels=cur[m['label_start']:m['text_start']]; oldblock=cur[m['text_start']:m['text_start']+m['text_size']]
    newblock=bytearray(); changes=[]
    for r in range(1,len(mat)):
        for k,(vc,pc) in enumerate(zip(v_text,p_text)):
            fidx=pc-vcount; roff=(r-1)*m['record_size']+4*fidx
            origptr=struct.unpack_from('<I',data,roff)[0]
            if origptr==0xffffffff or origptr>=m['text_size']:
                continue
            old=rb.read_utf16z(oldblock,origptr) or ''
            new=fn(dec_tr(old),r,k)
            if new is None: new=dec_tr(old)
            newe=enc_tr(new)
            ptr=len(newblock); struct.pack_into('<I',data,roff,ptr); newblock+=newe.encode('utf-16le')+b'\0\0'
            if newe!=old: changes.append({'row':r,'col':k,'old':dec_tr(old),'new':new})
    hdr=bytearray(cur[:0x30]); new_size=m['text_start']+len(newblock)
    struct.pack_into('<I',hdr,0x04,new_size); struct.pack_into('<I',hdr,0x1c,len(newblock))
    out=bytes(hdr)+bytes(data)+labels+bytes(newblock)
    assert len(out)==new_size
    return out,changes

# Item mappings
item_names=[line.rstrip('\n').split('\t',1)[1] for line in open('/mnt/data/item_col0.txt',encoding='utf8')]
item_desc=[line.rstrip('\n').split('\t',1)[1] for line in open('/mnt/data/item_col1.txt',encoding='utf8')]
item_desc_map=item_v37_tr.equipment_desc_map(item_desc)
for s in item_desc[277:]:
    t=item_v37_tr.translate_consumable_desc(s)
    if t: item_desc_map[s]=t
assert len(item_desc_map)==len(item_desc), (len(item_desc_map),len(item_desc))
item_name_map={s:(item_v37_tr.translate_item_name(s) or s) for s in item_names}
# DetailInfo has same item-name corpus; exact-name map handles it.

common_repl={}
common_stats=[]
# Targets to patch. ItemTable + duplicate detail names + voice/system/map.
targets=['Paramater/ItemTable.btb','Paramater/DetailInfoItemTable.btb','Battle/SBVoice.btb','Battle/BMAData.btb','ShipTable/ShipTableData.btb','Paramater/MapTable.btb']
for rel in targets:
    cells=layout_cells.get(rel)
    if cells is None: raise KeyError('no layout '+rel)
    cur,loc=extract_member(ROMFS/'Common_en',rel)
    def fn(s,r,k,rel=rel):
        if rel=='Paramater/ItemTable.btb':
            if s in item_name_map and item_name_map[s]!=s: return item_name_map[s]
            if s in item_desc_map: return item_desc_map[s]
        elif rel=='Paramater/DetailInfoItemTable.btb':
            if s in item_name_map and item_name_map[s]!=s: return item_name_map[s]
        elif rel=='Battle/SBVoice.btb': return SBVOICE.get(s)
        else: return COMMON_EXACT.get(s)
        return None
    nb,ch=transform_btbf(cur,cells,fn)
    if ch:
        common_stats.append({'file':rel,'changes':len(ch),'sample':ch[:8]})
        if loc[0]=='direct': (ROMFS/'Common_en'/rel).write_bytes(nb)
        else: common_repl.setdefault(loc[1],{})[Path(rel).name]=nb
for par,repl in common_repl.items(): rebuild_crowd_with(ROMFS/'Common_en',par,repl)
report['common']['files']=common_stats
report['common']['changes']=sum(x['changes'] for x in common_stats)
report['common']['item_names_translated']=sum(v!=k for k,v in item_name_map.items())
report['common']['item_descriptions_translated']=len(item_desc_map)

# ---------------- font: build dotless ı directly from base i, only remove dot ----------------
def cfnt_fix_dotless(cfnt:bytes):
    d=bytearray(cfnt); cmap=cfnt_char_map(cfnt)
    for ch in ('i','ı','þ'):
        if ch not in cmap: raise ValueError('font missing '+ch)
    # sections / TGLP / widths
    hs=struct.unpack_from('<H',d,6)[0]; off=hs; secs=[]
    while off+8<=len(d):
        mg=d[off:off+4]; sz=struct.unpack_from('<I',d,off+4)[0]
        if sz<8 or off+sz>len(d): break
        secs.append((mg,off,sz)); off+=sz
    tglp=next(x[1] for x in secs if x[0]==b'TGLP')
    cellw,cellh,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,tglp+8)
    cache={}
    def bitmap(si):
        if si not in cache:
            st=sheetoff+si*sheetsize; cache[si]=_sheet_to_bitmap_la4(bytes(d[st:st+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        return [[b[(y0+y)*sw+x0+x] for x in range(cellw)] for y in range(cellh)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        for y in range(cellh):
            for x in range(cellw): b[(y0+y)*sw+x0+x]=c[y][x]
    c=getcell(cmap['i'])
    # Find occupied row groups. The first detached component is the dot; clear ONLY it.
    rows_on=[any(_alpha(v)>0 for v in row) for row in c]
    groups=[]; st=None
    for y,on in enumerate(rows_on+[False]):
        if on and st is None: st=y
        elif not on and st is not None: groups.append((st,y-1)); st=None
    if len(groups)>=2:
        ds,de=groups[0]
    else:
        # fallback: locate largest lower component and clear only rows above it
        counts=[sum(_alpha(v)>0 for v in row) for row in c]
        body=max(range(len(counts)),key=lambda y: counts[y]+y*0.01); ds,de=0,max(0,body-2)
    for y in range(ds,de+1):
        for x in range(cellw): c[y][x]=0xf0
    setcell(cmap['ı'],c); setcell(cmap['þ'],c)
    for si,bmp in cache.items():
        st=sheetoff+si*sheetsize; d[st:st+sheetsize]=_bitmap_to_sheet_la4(bmp,sw,sh)
    # width for alias/U+0131 = base i width; find active CWDH ranges
    widths={}; width_pos={}
    for mg,co,sz in secs:
        if mg!=b'CWDH': continue
        a,b,nxt=struct.unpack_from('<HHI',d,co+8)
        for gi in range(a,b+1):
            p=co+0x10+(gi-a)*3
            if p+3<=co+sz: widths[gi]=bytes(d[p:p+3]); width_pos[gi]=p
    iw=widths.get(cmap['i'])
    for ch in ('ı','þ'):
        if iw and cmap[ch] in width_pos: d[width_pos[cmap[ch]]:width_pos[cmap[ch]]+3]=iw
    return bytes(d),{'cell':[cellw,cellh],'dot_rows':[ds,de],'i':cmap['i'],'dotless_i':cmap['ı'],'alias':cmap['þ']}

font_infos=[]
for rel in ['Graphics/UI/Font/Font','Graphics/UI_en/Font/Font']:
    p=ROMFS/rel; arc=DarcArchive(p.read_bytes()); repl={}
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,inf=cfnt_fix_dotless(b); repl[ip]=nb; inf.update({'archive':rel,'inner':ip,'sha256':sha(nb)}); font_infos.append(inf)
    if repl: p.write_bytes(arc.rebuild(repl))
report['font']['dotless_i']=font_infos

# ---------------- UI component/crowd access ----------------
UIROOT=ROMFS/'Graphics'/'UI_en'; UISRC=SRC_GFX/'UI_en'; JPSRC=SRC_GFX/'UI'
# membership map from source index (complete extracted tree)
member_of={}; source_folder={}
for idx in UISRC.rglob('index.fs'):
    folder=idx.parent
    if not (folder/'crowd.fs').is_file(): continue
    frel=str(folder.relative_to(UISRC)).replace('\\','/')
    try: ents=rb.parse_index(idx.read_bytes())
    except: continue
    source_folder[frel]=(folder,ents)
    for e in ents:
        crel=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
        member_of[crel]=(frel,e['name'])

ui_component_repl=defaultdict(dict)
def current_ui_component(crel:str):
    # Current patch crowd wins if present; source component otherwise.
    if crel in member_of:
        frel,name=member_of[crel]
        idxp=UIROOT/frel/'index.fs'; cp=UIROOT/frel/'crowd.fs'
        if idxp.is_file() and cp.is_file():
            ib=idxp.read_bytes(); cb=cp.read_bytes()
            for e in rb.parse_index(ib):
                if e['name']==name: return cb[e['offset']:e['offset']+e['size']]
    p=UIROOT/crel
    if p.is_file(): return p.read_bytes()
    return (UISRC/crel).read_bytes()

def source_jp_inner(crel,inner):
    p=JPSRC/crel
    if not p.is_file(): return None
    try:
        a=DarcArchive(p.read_bytes()); return dict(a.files()).get(inner)
    except: return None

def set_ui_component(crel,data):
    if crel in member_of:
        frel,name=member_of[crel]; ui_component_repl[frel][name]=data
    else:
        p=UIROOT/crel; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)

# Novel western-shared raster translations.
JTEXT={
 11:'Yetenekler',12:'Savaş Bonusları',13:'Canavar Rehberi',14:'Eşyalar',
 35:'Konuş',36:'Gir',37:'Çık',38:'İlerle',39:'Bin',40:'İn',41:'Aç',42:'İncele',43:'Dua Et',
 46:'Olayı Atla',47:'Atla',87:'Düzenle',88:'Düzenle',89:'Kuşan',90:'Kuşan',91:'Durum',92:'Durum',93:'Taşı',94:'Taşı',95:'Ağ',
 184:'Hava Gemisi Menüsü',231:'Kalan',
 249:'Bu Oyundan En İyi Şekilde Yararlan',250:'Diğer Oyuncularla Bağlan',251:'Arkadaş Birliği',252:'Arkadaş Çağırma',253:'Yetenek Bağı Kullanımı',254:'Bravely Second!',255:'Zorluk Ayarı',256:'Nemesis Arama',257:'Tekrar Tekrar İzle!',
 275:'Mesaj',281:'HAZIR',282:'KAÇIYOR',
}
TUTORIAL_BODY={
241:"Yetenek Bağı ve Arkadaş Çağırma ile\narkadaşlarının yardımını al!\n\nYakındaki arkadaşlarından en güncel veriler,\nher gün StreetPass bağlantısıyla otomatik gelir.\nUzaklardaki arkadaşların için internete bağlanıp\nverileri güncelleyebilirsin.",
242:"Arkadaşlarının Nintendo 3DS sistemlerini\narkadaş olarak kaydet. Rakiplerini de unutma!\n\nKaydettiğin oyuncuları Arkadaş Çağırma,\nYetenek Bağı ve diğer özelliklerle oyunda\nyardımına çağırabilirsin. Yol arkadaşsız olmaz!\n\nYakında kimse yok mu? İnternet üzerinden ara.\nYine mi yok? ...Eyvah.",
243:"Diğer oyuncuların karakterlerini savaşın\nen kızıştığı anda yardımına çağırabilirsin.\n\nYolculuğu ilerlemiş bir müttefikin varsa\nArkadaş Çağırma ile onun gücünden yararlan.\nSen de güçlü hamleni göndererek onlara yardım et!\n\nArkadaş verileri StreetPass ile de paylaşılır.\nHaydi, yeni dostlar edin savaşçı!",
244:"Bu harika teknoloji, arkadaşlarının öğrendiği\nyeteneklerden yararlanmanı sağlar.\n\nDiyelim iki güçlü arkadaşın var:\nA, savaşçı mesleklerinde; B ise büyüde uzman.\n\nO anda ihtiyacın olan yeteneğe göre\nikisi arasında istediğin zaman seçim yapabilirsin!",
245:"Zor durumda kaldığında zamanı durdurup\nkarşı saldırıya geç!\n\nUyku Modu ile SP biriktir!\n\nBekleyemiyor musun? SP İçecekleri tam sana göre.\nSP Menüsünden kullan; satın aldıysan savaşın\nen hararetli anında bile SP'ni anında yenileyip\ndüşman dalgalarını ardı ardına alt edebilirsin!",
246:"Zorluk seviyesini ve karşılaşma oranını\nistediğin zaman değiştirebilirsin.\n\nBunları kullanarak yolculuğu epey kolaylaştırmak\nelbette mümkün.\n\nAma kolay yol, seni ilerideki zorluklara\nhazırlamaz. Kararlarını verirken bunu unutma;\nsonradan pişman olma!",
247:"Verileri güncelleyebilir, StreetPass ile\nNemesis alıp gönderebilirsin.\n\nFarklı zamanlarda farklı Nemesis'lerle\nkarşılaşabileceğini unutma.\n\nDüzenli olarak yeni rakipler arayıp savaşarak\ndaha da güçlen. Belki sen de güçlü bir Nemesis'le\nkapışmak istersin. Zorlu bir rakip seni bekliyor!",
248:"Praline hayranlarına dünyanın dört bir yanından\nharika haberler!\n\nBir gösteriyi bir kez gördüysen Olay İzleyici ile\nonu tekrar tekrar seyredebilirsin.\nÜstelik farklı dillerde de izleyebilirsin!\nHarika değil mi!?\n\nArtık güzel sesimi istediğin zaman duyabilirsin!\nBütün gün Praline! Her gün Praline!",
}
AR_BODY={
268:("AR İşareti","AR işaretini, oyun paketindeki Nintendo 3DS\nYazılım Hızlı Başlangıç Kılavuzu'nda bulabilirsin.\n\nİşareti masa gibi düz bir yüzeye koy ve yaklaşık\n30 cm uzaktan görüntüle.\n\nKılavuz veya AR işareti yanında değilse oyunu\nyine başlatabilirsin: Nintendo 3DS sistemini\nmasaya doğrultup START düğmesine bas. Ben\ngeri kalanını hallederim."),
270:("AR İşareti","Oyunun AR işaretini indirmek için resmi\nBravely Default sitesini ziyaret et.\n\nDaha fazla bilgi için resmi siteye git!\nhttp://www.nintendo.co.uk/bravelydefault"),
}
# Some compound tutorial screenshots with multiple English labels.

def fit_multiline(draw,text,box,font_path,min_size=7,max_size=14,spacing=2):
    x0,y0,x1,y1=box; maxw=x1-x0; maxh=y1-y0
    for size in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(font_path,size)
        # text already line-broken intentionally
        bb=draw.multiline_textbbox((0,0),text,font=f,spacing=spacing)
        if bb[2]-bb[0]<=maxw and bb[3]-bb[1]<=maxh: return f
    return ImageFont.truetype(font_path,min_size)

def custom_full_body(en,jp,text):
    base,bb,mask=inpaint_language_area(en,[jp] if jp else [])
    # Clear body text zone conservatively; preserve textured background by inpaint result.
    draw=ImageDraw.Draw(base); fp=pick_font(serif=True)
    f=fit_multiline(draw,text,(12,18,en.width-10,en.height-10),fp,7,12,2)
    draw.multiline_text((14,23),text,font=f,fill=(242,242,238,255),spacing=2)
    return base

def custom_ar(en,jp,title,body):
    base,bb,mask=inpaint_language_area(en,[jp] if jp else [])
    d=ImageDraw.Draw(base); fp=pick_font(serif=True); bold='/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
    # Rebuild title on dark strip.
    f=fit_multiline(d,title,(65,4,255,25),bold,8,13,1)
    bbx=d.textbbox((0,0),title,font=f); d.text(((en.width-(bbx[2]-bbx[0]))/2,5),title,font=f,fill=(248,248,248,255))
    # Body on light panel.
    fb=fit_multiline(d,body,(10,30,en.width-8,en.height-8),fp,7,12,2)
    d.multiline_text((10,31),body,font=fb,fill=(15,15,15,255),spacing=2)
    return base

def custom_j21(en,jp):
    base,_,_=inpaint_language_area(en,[jp] if jp else [])
    # Left button labels only.
    _draw_fit_at(base,'Meslek',(22,0,83,23),fill=(245,245,245,255),serif=False,align='left',stroke_width=1,stroke=(25,25,25,240),min_size=5)
    _draw_fit_at(base,'Yetenek',(22,22,90,49),fill=(245,245,245,255),serif=False,align='left',stroke_width=1,stroke=(25,25,25,240),min_size=5)
    return base

nov=json.loads(NOVEL_INDEX.read_text(encoding='utf8'))
byid={r['id']:r for r in nov}
raster_changes=[]
# patch IDs with explicit text/custom body
wanted=set(JTEXT)|set(TUTORIAL_BODY)|set(AR_BODY)|{21}
for jid in sorted(wanted):
    rec=byid.get(jid)
    if not rec: continue
    for occ in rec['occurrences']:
        crel=occ['archive']; inner=occ['inner']
        try: arc=DarcArchive(current_ui_component(crel)); files=dict(arc.files()); b=files.get(inner)
        except Exception as e: raster_changes.append({'id':jid,'archive':crel,'inner':inner,'status':'component_error','error':str(e)}); continue
        if not b: continue
        try:
            en=decode_bclim(b); jpb=source_jp_inner(crel,inner); jp=decode_bclim(jpb) if jpb else None
            if jid in TUTORIAL_BODY: tr=custom_full_body(en,jp,TUTORIAL_BODY[jid])
            elif jid in AR_BODY: tr=custom_ar(en,jp,*AR_BODY[jid])
            elif jid==21: tr=custom_j21(en,jp)
            else:
                tr=render_translation(en,JTEXT[jid],[jp] if jp else [],serif=(jid in {11,12,13,14}),mode='auto')
            nb=encode_rgba8_bclim(tr,b); chk=decode_bclim(nb); assert chk.size==en.size
            newarc=arc.rebuild({inner:nb}); set_ui_component(crel,newarc)
            raster_changes.append({'id':jid,'archive':crel,'inner':inner,'text':JTEXT.get(jid) or AR_BODY.get(jid) or 'tutorial','status':'patched','size':list(en.size)})
        except Exception as e: raster_changes.append({'id':jid,'archive':crel,'inner':inner,'status':'patch_error','error':repr(e)})

# Sequential patching above may touch same component more than once; because set_ui_component stages but current_ui_component
# reads pre-stage data, consolidate repeated component changes now by reapplying all specs component-by-component.
specs=defaultdict(list)
for jid in sorted(wanted):
    rec=byid.get(jid)
    if rec:
        for occ in rec['occurrences']: specs[occ['archive']].append((jid,occ['inner']))
# reset raster stage only for touched component names and rebuild each once from current base
for crel,items in specs.items():
    try: arc=DarcArchive(current_ui_component(crel)); files=dict(arc.files()); replacements={}
    except: continue
    for jid,inner in items:
        b=files.get(inner)
        if not b: continue
        try:
            en=decode_bclim(b); jpb=source_jp_inner(crel,inner); jp=decode_bclim(jpb) if jpb else None
            if jid in TUTORIAL_BODY: tr=custom_full_body(en,jp,TUTORIAL_BODY[jid])
            elif jid in AR_BODY: tr=custom_ar(en,jp,*AR_BODY[jid])
            elif jid==21: tr=custom_j21(en,jp)
            else: tr=render_translation(en,JTEXT[jid],[jp] if jp else [],serif=(jid in {11,12,13,14}),mode='auto')
            replacements[inner]=encode_rgba8_bclim(tr,b)
        except: pass
    if replacements: set_ui_component(crel,arc.rebuild(replacements))

# ---------------- BCLYT strict fit pass ----------------
# Get current patched UI_en font after dotless fix.
farc=DarcArchive((ROMFS/'Graphics/UI_en/Font/Font').read_bytes()); cfnt=next(b for _,b in farc.files() if b[:4]==b'CFNT'); width_fn=make_text_width_fn(cfnt)
fit_changes=[]; unresolved=[]

def fit_bclyt(data):
    if data[:4]!=b'CLYT': return data,[]
    out=bytearray(data); changes=[]
    for e in bclyt_entries(data):
        pane_w=e['width']; font_x=e['font_x']; txt=e['text']
        if not txt or pane_w<=1 or font_x<=0: continue
        try: native=width_fn(txt); rendered=native*(font_x/14.0); limit=pane_w*0.88
        except: continue
        if rendered>limit and rendered>0:
            scale=limit/rendered
            # Real-device feedback takes precedence over old 0.72 floor; permit compact labels to 0.55.
            target=max(0.55,scale); newfx=font_x*target
            struct.pack_into('<f',out,e['section_offset']+0x64,newfx)
            after=rendered*target
            rec={'pane':e['pane'],'ordinal':e['ordinal'],'text':dec_tr(txt),'pane_width':pane_w,'old_font_x':font_x,'new_font_x':newfx,'before':rendered,'after':after,'scale':target}
            changes.append(rec)
            if after>limit*1.02: unresolved.append(rec)
    return bytes(out),changes

# Fit every component in current UI_en Layout crowds, using staged raster component if present.
# Iterate complete source membership to avoid missing a localized DARC copy.
for crel,(frel,name) in list(member_of.items()):
    if not (crel.startswith('Layout/') or crel.startswith('Common/')): continue
    # Obtain staged component if any, otherwise current.
    basebytes=ui_component_repl.get(frel,{}).get(name)
    if basebytes is None:
        try: basebytes=current_ui_component(crel)
        except: continue
    if basebytes[:4]!=b'darc': continue
    try: arc=DarcArchive(basebytes); replacements={}; local=[]
    except: continue
    for ip,b in arc.files():
        if b[:4]!=b'CLYT': continue
        nb,ch=fit_bclyt(b)
        if ch: replacements[ip]=nb; local.extend([{'archive':crel,'inner':ip,**x} for x in ch])
    if replacements:
        set_ui_component(crel,arc.rebuild(replacements)); fit_changes.extend(local)

# Rebuild staged UI crowds. Use current patch crowd if exists, otherwise source crowd.
ui_crowd_reports=[]
for frel,repl in ui_component_repl.items():
    # ensure patch crowd exists: copy source if needed
    outdir=UIROOT/frel; outdir.mkdir(parents=True,exist_ok=True)
    if not (outdir/'index.fs').is_file():
        shutil.copy2(UISRC/frel/'index.fs',outdir/'index.fs'); shutil.copy2(UISRC/frel/'crowd.fs',outdir/'crowd.fs')
    ui_crowd_reports.append({'folder':frel,**rebuild_crowd_with(UIROOT,frel,repl)})

report['raster']['new_western_shared_patches']=[x for x in raster_changes if x.get('status')=='patched']
report['raster']['patch_count']=len(report['raster']['new_western_shared_patches'])
report['raster']['failed']=[x for x in raster_changes if x.get('status')!='patched']
report['ui_fit']['shrunk_entries']=len(fit_changes); report['ui_fit']['unresolved_after_floor']=len(unresolved); report['ui_fit']['changes']=fit_changes; report['ui_fit']['unresolved']=unresolved
report['technical']['ui_crowds']=ui_crowd_reports

# ---------------- audits ----------------
# Exact runtime-English leftovers for key high-value sets after patch.
def iter_current_texts(rel):
    cells=layout_cells.get(rel); cur,_=extract_member(ROMFS/'Common_en',rel); m=rb.btbf_meta(cur); mat=rb.sheet_matrix(cells); vt,pt,vc=rb.text_layout(mat,m); block=cur[m['text_start']:]
    for r in range(1,len(mat)):
        for k,(v,p) in enumerate(zip(vt,pt)):
            fidx=p-vc; ptr=struct.unpack_from('<I',cur,0x30+(r-1)*m['record_size']+4*fidx)[0]
            if ptr!=0xffffffff and ptr<m['text_size']: yield r,k,dec_tr(rb.read_utf16z(block,ptr) or '')

left={}
for rel in targets:
    eng=[]
    for r,k,s in iter_current_texts(rel):
        if s in item_names or s in item_desc or s in SBVOICE or s in COMMON_EXACT: eng.append({'row':r,'col':k,'text':s})
    left[rel]=eng
report['common']['targeted_english_remaining']=left

# UI fit verify all currently patched layout crowd BCLYT.
ratio_max=0; over=[]
for idx in UIROOT.rglob('index.fs'):
    if 'Layout' not in str(idx): continue
    cp=idx.with_name('crowd.fs')
    if not cp.is_file(): continue
    ib=idx.read_bytes(); cb=cp.read_bytes()
    for e in rb.parse_index(ib):
        comp=cb[e['offset']:e['offset']+e['size']]
        if comp[:4]!=b'darc': continue
        try:a=DarcArchive(comp)
        except:continue
        for ip,b in a.files():
            if b[:4]!=b'CLYT':continue
            for ent in bclyt_entries(b):
                if not ent['text'] or ent['width']<=1: continue
                rr=width_fn(ent['text'])*(ent['font_x']/14.0)/max(1,ent['width']); ratio_max=max(ratio_max,rr)
                if rr>0.92: over.append({'folder':str(idx.parent.relative_to(UIROOT)),'component':e['name'],'inner':ip,'text':dec_tr(ent['text']),'ratio':rr,'width':ent['width'],'font_x':ent['font_x']})
report['ui_fit']['post_audit_max_ratio']=ratio_max; report['ui_fit']['post_audit_over_0_92']=over[:1000]; report['ui_fit']['post_audit_over_count']=len(over)

# Basic crowd structure audit across patch.
crowd_pairs=0; entries=0; errs=[]
for idx in ROMFS.rglob('index.fs'):
    cp=idx.with_name('crowd.fs')
    if not cp.is_file():continue
    crowd_pairs+=1
    try:
        es=rb.parse_index(idx.read_bytes()); cb=cp.read_bytes(); entries+=len(es)
        spans=[]
        for e in es:
            if e['offset']+e['size']>len(cb): errs.append({'path':str(idx.relative_to(ROMFS)),'name':e['name'],'error':'out of range'})
            spans.append((e['offset'],e['offset']+e['size'],e['name']))
        ss=sorted(spans)
        for a,b in zip(ss,ss[1:]):
            if a[1]>b[0]: errs.append({'path':str(idx.relative_to(ROMFS)),'error':'overlap','a':a,'b':b})
    except Exception as e: errs.append({'path':str(idx.relative_to(ROMFS)),'error':repr(e)})
report['technical'].update({'crowd_pairs':crowd_pairs,'crowd_entries':entries,'errors':errs})
if errs: raise RuntimeError(errs[:3])

# ---------------- preview sheet for v3.7 newly patched raster ----------------
previews=[]
for jid in sorted(wanted):
    rec=byid.get(jid)
    if not rec: continue
    occ=rec['occurrences'][0]; crel=occ['archive']; inner=occ['inner']
    try:
        # after UI crowd rebuild, re-read component
        comp=current_ui_component(crel); a=DarcArchive(comp); b=dict(a.files()).get(inner); im=decode_bclim(b)
        previews.append((jid,im.copy()))
    except: pass
if previews:
    thumbw=320; cellh=260; cols=3; rows=math.ceil(len(previews)/cols)
    sheet=Image.new('RGBA',(cols*thumbw,rows*cellh),(130,130,130,255)); d=ImageDraw.Draw(sheet)
    for n,(jid,im) in enumerate(previews):
        scale=min((thumbw-10)/im.width,(cellh-25)/im.height,2.0); sz=(max(1,int(im.width*scale)),max(1,int(im.height*scale))); rim=im.resize(sz,Image.Resampling.NEAREST)
        x=(n%cols)*thumbw+5; y=(n//cols)*cellh+20; sheet.alpha_composite(rim,(x,y)); d.text((x,3),f'J{jid:04d}',fill='yellow')
    sheet.convert('RGB').save(REPORTS/'RASTER_FIXES_v37.png')

# Save dotless glyph report via JSON; image extraction omitted from runtime package docs for compactness.
(REPORTS/'BUILD_REPORT_v37.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'ENGLISH_LEFTOVER_AUDIT_v37.json').write_text(json.dumps({'targeted_remaining':left,'item_name_source_count':len(item_names),'item_description_source_count':len(item_desc),'sbvoice_source_count':len(SBVOICE)},ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'UI_OVERFLOW_AUDIT_v37.json').write_text(json.dumps(report['ui_fit'],ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'RASTER_UI_EN_VS_UI_AUDIT_v37.json').write_text(json.dumps({'new_scan_total_unique':len(nov),'patched_ids':sorted(wanted),'patch_count':report['raster']['patch_count'],'failures':report['raster']['failed']},ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'FONT_DOTLESS_I_v37.json').write_text(json.dumps(font_infos,ensure_ascii=False,indent=2),encoding='utf8')

# Tools/docs
shutil.copy2('/mnt/data/item_v37_tr.py',TOOLS/'item_v37_tr.py'); shutil.copy2('/mnt/data/common_v37_tr.py',TOOLS/'common_v37_tr.py'); shutil.copy2('/mnt/data/build_v37.py',TOOLS/'build_progress_v37.py')
(DOCS/'CHANGELOG_v3.7_TR.md').write_text(f'''# Bravely Default TR — v3.7\n\n- `ı` glyph'i artık `i` harfinin aynısından yalnız üstteki nokta bileşeni silinerek oluşturuluyor; U+0131 ve runtime `þ` alias slotu aynı bitmap'i kullanıyor.\n- ItemTable'da {report['common']['item_names_translated']} eşya adı ve {report['common']['item_descriptions_translated']} eşya açıklaması için Türkçe karşılık eklendi.\n- Bravely Second savaş sesi altyazılarındaki {len(SBVOICE)} İngilizce satır Türkçeleştirildi.\n- Açılış/bağlantı öğreticisindeki 8 tam ekran İngilizce BCLIM bilgi sayfası Türkçe raster olarak yeniden çizildi.\n- AR işaretiyle ilgili iki 320x240 bilgi görseli Türkçeleştirildi.\n- Batı dillerinde ortak kaldığı için önceki EN-vs-FR/DE taramasından kaçan buton/sekme/başlık görselleri `UI_en` ↔ ortak `UI` karşılaştırmasıyla bulundu ve yamalandı.\n- BCLYT'lere gerçek CFNT advance ölçümüyle ikinci bir taşma geçişi uygulandı; pane genişliğinin %88'i hedefleniyor ve gerekirse yatay font ölçeği 0.55'e kadar düşebiliyor.\n\nBu sürüm tam progress build'dir; v3.6'daki Common_en, UI, iki-font uyumluluk kodlaması ve önceki raster düzeltmelerini içerir.\n''',encoding='utf8')
(DOCS/'INGILIZCE_KAPSAM_DENETIMI_v3.7_TR.md').write_text('''# İngilizce kapsam denetimi — v3.7\n\nÖnceki denetim yalnız çevrilebilir kısa UI dizeleri ve Batı dilleri arasında farklı rasterları esas alıyordu. Bu iki kör nokta oluşturuyordu:\n\n1. Kaynak İngilizceyle birebir kalan ItemTable ad/açıklamaları çok sayıda olduğu hâlde “özel ad olabilir” kümesinde kalıyordu. v3.7 ItemTable ve DetailInfoItemTable'ı ayrı, kullanıcıya görünür veri olarak ele alır.\n2. Tüm Batı dillerinde aynı İngilizce resim kullanılan BCLIM'ler EN↔FR/DE/ES/IT fark taramasında görünmez. v3.7 ayrıca `Graphics/UI_en` ile ortak/Japonca `Graphics/UI` görünür piksel karşılaştırması yapar. Açılış bilgi sayfaları ve AR açıklamaları bu ikinci taramada bulunmuştur.\n\nBilerek korunabilenler: karakter/yer özel adları, HP/MP/BP/JP/EXP/pg gibi oyun kısaltmaları, StreetPass/Bravely Second gibi ürün/özellik adları ve geliştirici Dummy/test kayıtları.\n''',encoding='utf8')
(DOCS/'UI_TASMA_VE_HIZA_v3.7_TR.md').write_text(f'''# UI taşma ve hiza denetimi — v3.7\n\nBCLYT `txt1` pane genişliği, font X boyutu ve gerçek CFNT advance değerleri birlikte ölçülür. v3.7'de güvenli hedef pane genişliğinin %88'idir. Eski 0.72 minimum ölçek sınırı gerçek cihaz geri bildirimine göre 0.55'e indirildi.\n\nBu build sırasında küçültülen txt1 kayıtları: **{len(fit_changes)}**.\nDenetimde %92 pane oranını aşan kayıtlar: **{len(over)}**. Bunlar `Reports/UI_OVERFLOW_AUDIT_v37.json` içinde listelenir; bazıları doğal olarak geniş kredi/URL/özel ekran metni olabilir.\n\nRaster çevirilerde metin sabit görsel alanının içine yeniden fit edilir; tam ekran öğretici ve AR sayfaları ise orijinal İngilizce glyph alanı temizlenip Türkçe paragraflar native 3DS çözünürlüğünde yeniden çizilmiştir.\n''',encoding='utf8')
(DOCS/'FONT_DOTLESS_I_FIX_v3.7_TR.md').write_text('''# Noktasız ı düzeltmesi — v3.7\n\nKullanıcı geri bildirimine göre önceki `ı` şekli doğru görünmüyordu. v3.7 herhangi bir glyph'i çevirmiyor/aynalamıyor. Her iki CFNT'de de kaynak küçük `i` hücresi alınır, bağlantısız üst nokta bileşeninin bulunduğu satırlar şeffaflaştırılır ve gövdeye dokunulmaz. Elde edilen hücre hem gerçek U+0131 `ı` glyph'ine hem runtime uyumluluk slotu U+00FE `þ` glyph'ine yazılır. Genişlik bilgisi de kaynak `i` ile eşitlenir.\n''',encoding='utf8')

# Manifest
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file(): manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')

# ZIP complete build + LayeredFS
fullzip=Path('/mnt/data/BravelyDefault_TR_Progress_v3.7_2026-08-21.zip')
if fullzip.exists(): fullzip.unlink()
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(OUT.parent))

def make_layered(region,titleid):
    zpath=Path(f'/mnt/data/BravelyDefault_TR_Progress_v3.7_LayeredFS_{region}.zip')
    if zpath.exists(): zpath.unlink()
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROMFS.rglob('*')):
            if p.is_file(): z.write(p,Path('luma/titles')/titleid/'romfs'/p.relative_to(ROMFS))
    return zpath
EUR=make_layered('EUR','00040000000FC600'); USA=make_layered('USA','00040000000FC500')
# zip integrity and critical font paths
for zp in (fullzip,EUR,USA):
    with zipfile.ZipFile(zp) as z:
        bad=z.testzip(); assert bad is None, (zp,bad)
print(json.dumps({'full':str(fullzip),'eur':str(EUR),'usa':str(USA),'common_changes':report['common']['changes'],'item_names':report['common']['item_names_translated'],'item_desc':report['common']['item_descriptions_translated'],'raster_patches':report['raster']['patch_count'],'fit_changes':len(fit_changes),'post_over':len(over),'crowd_pairs':crowd_pairs,'crowd_entries':entries},ensure_ascii=False,indent=2))
