#!/usr/bin/env python3
from pathlib import Path
import sys, json, shutil, struct, hashlib, zipfile, re
from collections import defaultdict, Counter

BASE=Path('/mnt/data/build_v39/BravelyDefault_TR_Progress_v3.9_2026-08-22')
OUT=Path('/mnt/data/build_v310/BravelyDefault_TR_Progress_v3.10_2026-08-22')
SRC_COMMON=Path('/mnt/data/v37_source_common/Common_en')
if OUT.exists(): shutil.rmtree(OUT)
OUT.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(BASE,OUT)
ROMFS=OUT/'romfs'; COMMON=ROMFS/'Common_en'; UI=ROMFS/'Graphics/UI_en'; TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'
sys.path.insert(0,str(TOOLS))
import repack_bravely as rb
from bravely_ui_tools import DarcArchive
from bclim_tools import decode_bclim, encode_rgba8_bclim
from raster_patch_tools import _draw_fit_at, sample_text_colors
from turkish_compat_encoding_v36 import ENCODE, DECODE
from PIL import Image

def enc(s): return ''.join(ENCODE.get(c,c) for c in s)
def dec(s): return ''.join(DECODE.get(c,c) for c in s)
def sha(b): return hashlib.sha256(b).hexdigest()

# Terminology authority derived from the user's existing translation:
# Magic Points -> Büyü Puanı, Brave Points -> Cesaret Puanı, Job -> Meslek.
# Compact abbreviations therefore become BP / CP / MP.
TOKEN_MAP={'MP':'BP','BP':'CP','JP':'MP'}
FULL_TERM_REPL=[
    ('İş Puanı','Meslek Puanı'),('İş puanı','Meslek puanı'),('iş Puanı','meslek Puanı'),('iş puanı','meslek puanı'),
]
TOKEN_RE=re.compile(r'(?<![A-Za-z])(MP|BP|JP)(?![A-Za-z])')

def normalize_text(s):
    out=s
    for a,b in FULL_TERM_REPL: out=out.replace(a,b)
    out=TOKEN_RE.sub(lambda m:TOKEN_MAP[m.group(1)],out)
    return out

# Source workbook layouts tell us exactly which BTBF fields are text pointers.
layouts={}
for xp in SRC_COMMON.rglob('*.xls'):
    try: wb=rb.parse_biff(xp)
    except Exception: continue
    for sn,cells in wb.items():
        try: t=rb.resolve_sheet_target(xp,sn)
        except Exception: t=None
        if t is None: continue
        try: rel=str(t.relative_to(SRC_COMMON)).replace('\\','/')
        except Exception: continue
        layouts[rel]=cells

def build_members(root):
    m={}
    for idx in root.rglob('index.fs'):
        cp=idx.with_name('crowd.fs')
        if not cp.is_file(): continue
        frel=str(idx.parent.relative_to(root)).replace('\\','/')
        try: es=rb.parse_index(idx.read_bytes())
        except Exception: continue
        for e in es:
            rel=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
            m[rel]=(frel,e['name'])
    return m

def extract_component(root,members,rel):
    p=root/rel
    if p.is_file(): return p.read_bytes(),('direct',rel)
    z=members.get(rel)
    if not z: return None,None
    frel,name=z; ib=(root/frel/'index.fs').read_bytes(); cb=(root/frel/'crowd.fs').read_bytes()
    for e in rb.parse_index(ib):
        if e['name']==name: return cb[e['offset']:e['offset']+e['size']],('crowd',frel)
    return None,None

def rebuild_crowd(root,frel,repl):
    idxp=root/frel/'index.fs'; cp=root/frel/'crowd.fs'
    ib=idxp.read_bytes(); old=cp.read_bytes(); outi=bytearray(ib); outc=bytearray(); changed=0
    for e in rb.parse_index(ib):
        while len(outc)%4: outc.append(0)
        off=len(outc); b=repl.get(e['name'],old[e['offset']:e['offset']+e['size']])
        if e['name'] in repl: changed+=1
        outc+=b; struct.pack_into('<I',outi,e['pos']+4,off); struct.pack_into('<I',outi,e['pos']+8,len(b))
    while len(outc)%4: outc.append(0)
    idxp.write_bytes(outi); cp.write_bytes(outc)
    return changed

# ---- Common_en visible BTBF text normalization ----
common_members=build_members(COMMON)
common_stage=defaultdict(dict); common_changes=[]; common_token_counts=Counter()

def transform_btbf(cur,cells,rel):
    m=rb.btbf_meta(cur); mat=rb.sheet_matrix(cells); vt,pt,vc=rb.text_layout(mat,m)
    if not mat or len(mat)-1!=m['count'] or len(vt)!=len(pt): return cur,[]
    data=bytearray(cur[0x30:m['label_start']]); labels=cur[m['label_start']:m['text_start']]; oldblk=cur[m['text_start']:m['text_start']+m['text_size']]
    # First determine whether anything visible changes.
    rows=[]; changes=[]
    for r in range(1,len(mat)):
        row=[]
        for k,pc in enumerate(pt):
            fi=pc-vc; roff=(r-1)*m['record_size']+4*fi; ptr=struct.unpack_from('<I',data,roff)[0]
            if ptr==0xffffffff or ptr>=m['text_size']:
                row.append((roff,ptr,None)); continue
            raw=rb.read_utf16z(oldblk,ptr) or ''
            vis=dec(raw); newvis=normalize_text(vis); newraw=enc(newvis)
            row.append((roff,ptr,newraw))
            if newvis!=vis:
                toks_before=Counter(TOKEN_RE.findall(vis)); toks_after=Counter(TOKEN_RE.findall(newvis))
                changes.append({'row':r,'field':k,'old':vis,'new':newvis,'before_tokens':dict(toks_before),'after_tokens':dict(toks_after)})
        rows.append(row)
    if not changes: return cur,[]
    # Rebuild text block and pointers for all valid text cells.
    newblk=bytearray()
    for row in rows:
        for roff,ptr,newraw in row:
            if newraw is None: continue
            np=len(newblk); struct.pack_into('<I',data,roff,np); newblk+=newraw.encode('utf-16le')+b'\0\0'
    hdr=bytearray(cur[:0x30]); size=m['text_start']+len(newblk); struct.pack_into('<I',hdr,4,size); struct.pack_into('<I',hdr,0x1c,len(newblk))
    nb=bytes(hdr)+bytes(data)+labels+bytes(newblk)
    return nb,changes

for rel,cells in layouts.items():
    cur,loc=extract_component(COMMON,common_members,rel)
    if not cur or cur[:4]!=b'BTBF': continue
    nb,ch=transform_btbf(cur,cells,rel)
    if not ch: continue
    common_changes.append({'file':rel,'count':len(ch),'changes':ch})
    for c in ch:
        for t,n in Counter(TOKEN_RE.findall(c['old'])).items(): common_token_counts[f'{t}->'+TOKEN_MAP[t]]+=n
    if loc[0]=='direct': (COMMON/rel).write_bytes(nb)
    else: common_stage[loc[1]][Path(rel).name]=nb
for frel,repl in common_stage.items(): rebuild_crowd(COMMON,frel,repl)

# ---- UI_en BCLYT visible text normalization ----
ui_members=build_members(UI); ui_stage=defaultdict(dict); ui_changes=[]

def rewrite_bclyt(data,context):
    if data[:4]!=b'CLYT': return data,[]
    hdr=struct.unpack_from('<H',data,6)[0]; out=bytearray(data[:hdr]); off=hdr; changes=[]; ordinal=0
    while off+8<=len(data):
        mg=data[off:off+4]; sz=struct.unpack_from('<I',data,off+4)[0]
        if sz<8 or off+sz>len(data): out+=data[off:]; break
        sec=bytearray(data[off:off+sz])
        if mg==b'txt1' and sz>=0x74:
            pane=sec[0x0c:0x1c].split(b'\0',1)[0].decode('ascii','replace'); to=struct.unpack_from('<I',sec,0x58)[0]
            if 0<to<len(sec):
                i=to; bb=bytearray()
                while i+1<len(sec) and sec[i:i+2]!=b'\0\0': bb+=sec[i:i+2]; i+=2
                raw=bb.decode('utf-16le','replace'); vis=dec(raw); newvis=normalize_text(vis)
                if newvis!=vis:
                    nr=enc(newvis); nb=nr.encode('utf-16le')+b'\0\0'
                    struct.pack_into('<HH',sec,0x4c,len(nb),len(nb)); sec=sec[:to]+nb
                    while len(sec)%4: sec.append(0)
                    struct.pack_into('<I',sec,4,len(sec))
                    changes.append({'context':context,'pane':pane,'ordinal':ordinal,'old':vis,'new':newvis})
            ordinal+=1
        out+=sec; off+=sz
    struct.pack_into('<I',out,0x0c,len(out))
    return bytes(out),changes

for crel,(frel,name) in sorted(ui_members.items()):
    if not (crel.startswith('Layout/') or crel.startswith('Common/')): continue
    comp,_=extract_component(UI,ui_members,crel)
    if not comp or comp[:4]!=b'darc': continue
    try: a=DarcArchive(comp); files=dict(a.files())
    except Exception: continue
    repl={}
    for inner,b in files.items():
        if b[:4]!=b'CLYT': continue
        nb,ch=rewrite_bclyt(b,f'{crel}:{inner}')
        if ch: repl[inner]=nb; ui_changes.extend(ch)
    if repl:
        ui_stage[frel][name]=a.rebuild(repl)
for frel,repl in ui_stage.items(): rebuild_crowd(UI,frel,repl)

# ---- Raster stat label: Azm. MP (Magic Points) -> Azm. BP (Büyü Puanı) ----
# ID260 = Layout/99_Battle/root/timg/HP_MP_PC.bclim.
raster_report=[]
frel='Layout'; comp_name='99_Battle'; inner='./root/timg/HP_MP_PC.bclim'
# re-read current component after BCLYT crowd rebuild
ib=(UI/frel/'index.fs').read_bytes(); cb=(UI/frel/'crowd.fs').read_bytes(); component=None
for e in rb.parse_index(ib):
    if e['name']==comp_name: component=cb[e['offset']:e['offset']+e['size']]
if component:
    a=DarcArchive(component); files=dict(a.files()); templ=files.get(inner)
    if templ:
        oldim=decode_bclim(templ).convert('RGBA'); fill,_=sample_text_colors(oldim); newim=Image.new('RGBA',oldim.size,(0,0,0,0))
        rows=[
            [('Azm. HP',(0,0,66,14)),('Azm. BP',(72,0,140,14))],
            [('F.SAL',(0,14,46,26)),('F.SAV',(48,14,94,26)),('İsabet',(96,14,140,26))],
            [('B.SAL',(0,26,46,38)),('B.SAV',(48,26,94,38)),('Kaçın.',(96,26,140,38))],
            [('ZEK',(0,38,46,58)),('İRA',(48,38,94,58)),('HIZ',(96,38,140,58))],
        ]
        for row in rows:
            for text,box in row: _draw_fit_at(newim,text,box,fill=fill,serif=True,align='left',min_size=5)
        nbclim=encode_rgba8_bclim(newim,templ); ncomp=a.rebuild({inner:nbclim}); rebuild_crowd(UI,frel,{comp_name:ncomp})
        preview=REPORTS/'STAT_ABBREVIATIONS_v310.png'; decode_bclim(nbclim).save(preview)
        raster_report.append({'archive':'Layout/99_Battle','inner':inner,'old':'Azm. MP','new':'Azm. BP','preview':str(preview.relative_to(OUT))})

# ---- Reproducibility tools/policy ----
policy_py=TOOLS/'terminology_abbreviations_v310.py'
policy_py.write_text('''#!/usr/bin/env python3\n"""Turkish terminology-derived abbreviations for Bravely Default TR v3.10.\n\nBüyü Puanı -> BP\nCesaret Puanı -> CP\nMeslek Puanı -> MP\n\nThe mapping is simultaneous: original game MP/BP/JP tokens are normalized to BP/CP/MP.\n"""\nimport re\nTOKEN_MAP={"MP":"BP","BP":"CP","JP":"MP"}\nTOKEN_RE=re.compile(r"(?<![A-Za-z])(MP|BP|JP)(?![A-Za-z])")\ndef normalize(s):\n    s=s.replace("İş Puanı","Meslek Puanı").replace("İş puanı","Meslek puanı").replace("iş puanı","meslek puanı")\n    return TOKEN_RE.sub(lambda m:TOKEN_MAP[m.group(1)],s)\n''',encoding='utf8')
shutil.copy2('/mnt/data/build_v310.py',TOOLS/'build_progress_v310.py')

# Update forward translation dictionary so future UI work uses the same abbreviations.
tp=TOOLS/'translations_tr.py'
text=tp.read_text(encoding='utf8')
text=text.replace("'HP':'HP','MP':'MP'","'HP':'HP','MP':'BP','BP':'CP','JP':'MP'")
text=text.replace("'Gain Job Points':'JP Kazanımı'","'Gain Job Points':'MP Kazanımı'")
text=text.replace("'Total JP':'Toplam JP'","'Total JP':'Toplam MP'")
text=text.replace("'Max MP':'Azami MP'","'Max MP':'Azami BP'")
tp.write_text(text,encoding='utf8')
# Make raster helper future-safe.
rp=TOOLS/'raster_patch_tools.py'; rt=rp.read_text(encoding='utf8').replace("('Azm MP',(74,0,140,18))","('Azm BP',(74,0,140,18))")
rp.write_text(rt,encoding='utf8')

# ---- Verification scans ----
# Re-read every visible Common string and count abbreviation tokens after normalization.
def iter_common_strings():
    members=build_members(COMMON)
    for rel,cells in layouts.items():
        cur,_=extract_component(COMMON,members,rel)
        if not cur or cur[:4]!=b'BTBF': continue
        try: m=rb.btbf_meta(cur); mat=rb.sheet_matrix(cells); vt,pt,vc=rb.text_layout(mat,m)
        except: continue
        blk=cur[m['text_start']:]
        for r in range(1,min(len(mat),m['count']+1)):
            for pc in pt:
                fi=pc-vc; ptr=struct.unpack_from('<I',cur,0x30+(r-1)*m['record_size']+4*fi)[0]
                if ptr==0xffffffff or ptr>=m['text_size']: continue
                yield rel,r,dec(rb.read_utf16z(blk,ptr) or '')

post_counts=Counter(); leftover_work=[]
for rel,r,s in iter_common_strings():
    for t in TOKEN_RE.findall(s): post_counts[t]+=1
    if 'İş Puan' in s or 'iş puan' in s: leftover_work.append({'file':rel,'row':r,'text':s})

# Technical crowd/index audit after all rebuilds.
errs=[]; pairs=entries=0
for idx in ROMFS.rglob('index.fs'):
    cp=idx.with_name('crowd.fs')
    if not cp.is_file(): continue
    pairs+=1
    try:
        es=rb.parse_index(idx.read_bytes()); crowd=cp.read_bytes(); entries+=len(es); spans=[]
        for e in es:
            if e['offset']+e['size']>len(crowd): errs.append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'out_of_range'})
            spans.append((e['offset'],e['offset']+e['size'],e['name']))
        ss=sorted(spans)
        for a,b in zip(ss,ss[1:]):
            if a[1]>b[0]: errs.append({'path':str(idx.relative_to(ROMFS)),'error':'overlap','a':a,'b':b})
    except Exception as ex: errs.append({'path':str(idx.relative_to(ROMFS)),'error':repr(ex)})
if errs: raise RuntimeError(errs[:10])

report={
 'version':'v3.10','base':'v3.9',
 'canonical_terms':{'magic_points':'Büyü Puanı','brave_points':'Cesaret Puanı','job_points':'Meslek Puanı'},
 'compact_abbreviations':{'Büyü Puanı':'BP','Cesaret Puanı':'CP','Meslek Puanı':'MP'},
 'simultaneous_source_token_map':TOKEN_MAP,
 'common_files_changed':len(common_changes),'common_text_changes':sum(x['count'] for x in common_changes),
 'ui_text_changes':len(ui_changes),'raster_changes':raster_report,
 'post_visible_token_counts':dict(post_counts),'leftover_is_puani':leftover_work,
 'technical':{'crowd_pairs':pairs,'crowd_entries':entries,'errors':errs},
 'common_changes':common_changes,'ui_changes':ui_changes,
}
REPORTS.mkdir(exist_ok=True)
(REPORTS/'TURKISH_ABBREVIATION_AUDIT_v310.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'TECHNICAL_AUDIT_v310.json').write_text(json.dumps(report['technical'],ensure_ascii=False,indent=2),encoding='utf8')
(DOCS/'TERIM_KISALTMALARI_v3.10_TR.md').write_text('''# Türkçe kavram kısaltmaları — v3.10\n\nv3.9 dar alanlarda İngilizce kaynak kısaltmaları MP/BP/JP'yi koruyordu. Kullanıcının çeviri terminolojisi esas alındığında bu doğru değildi.\n\nYamadaki ana terimler:\n\n- Magic Points = **Büyü Puanı** → kısa alanlarda **BP**\n- Brave Points = **Cesaret Puanı** → kısa alanlarda **CP**\n- Job Points = **Meslek Puanı** → kısa alanlarda **MP**\n\nJob kavramı yamada `Meslek` olduğu için kalan `İş Puanı` varyantları da `Meslek Puanı` olarak normalize edilir. Dönüşüm eşzamanlıdır; böylece kaynak `JP` önce `MP`ye dönüşüp sonra yanlışlıkla `BP`ye çevrilmez.\n\nAçıklama/diyaloglarda zaten tam Türkçe terim varsa tam biçim korunur. Kaynak dosyada kısaltma kullanılmışsa Türkçe terimin kısaltması kullanılır.\n''',encoding='utf8')
(DOCS/'CHANGELOG_v3.10_TR.md').write_text(f'''# Bravely Default TR — v3.10\n\n- v3.9'daki İngilizce kökenli MP/BP/JP kısaltma politikası kaldırıldı.\n- Büyü Puanı → BP, Cesaret Puanı → CP, Meslek Puanı → MP standardı getirildi.\n- `İş Puanı` kalıntıları `Meslek Puanı` ile tutarlılaştırıldı.\n- Common_en görünür metin değişiklikleri: {sum(x['count'] for x in common_changes)}.\n- BCLYT UI değişiklikleri: {len(ui_changes)}.\n- Savaş profil rasterındaki `Azm. MP` → `Azm. BP`.\n- Teknik crowd/index denetimi: {pairs} çift / {entries} giriş / 0 hata.\n''',encoding='utf8')
with open(OUT/'README_TR.md','a',encoding='utf8') as f:
    f.write('\n\n## v3.10 terminoloji notu\nKısa puan adları artık İngilizce kaynak kısaltmalarından değil Türkçe ana kavramlardan türetilir: Büyü Puanı=BP, Cesaret Puanı=CP, Meslek Puanı=MP. Ayrıntılar `Docs/TERIM_KISALTMALARI_v3.10_TR.md`.\n')

# Manifest after all changes.
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p.name!='MANIFEST_SHA256.json': manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')

# Packages.
full=Path('/mnt/data/BravelyDefault_TR_Progress_v3.10_2026-08-22.zip')
eur=Path('/mnt/data/BravelyDefault_TR_Progress_v3.10_LayeredFS_EUR.zip')
usa=Path('/mnt/data/BravelyDefault_TR_Progress_v3.10_LayeredFS_USA.zip')
for z in (full,eur,usa):
    if z.exists(): z.unlink()
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(OUT.parent))
for zpath,tid in [(eur,'00040000000FC600'),(usa,'00040000000FC500')]:
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROMFS.rglob('*')):
            if p.is_file(): z.write(p,Path('luma/titles')/tid/'romfs'/p.relative_to(ROMFS))
for z in (full,eur,usa):
    with zipfile.ZipFile(z) as q:
        bad=q.testzip(); assert bad is None,bad

print(json.dumps({
 'full':str(full),'eur':str(eur),'usa':str(usa),
 'common_files_changed':len(common_changes),'common_text_changes':sum(x['count'] for x in common_changes),
 'ui_text_changes':len(ui_changes),'raster_changes':len(raster_report),
 'post_visible_tokens':dict(post_counts),'leftover_is_puani':len(leftover_work),
 'crowd_pairs':pairs,'crowd_entries':entries
},ensure_ascii=False,indent=2))
