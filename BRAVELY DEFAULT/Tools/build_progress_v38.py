#!/usr/bin/env python3
from pathlib import Path
import sys, json, shutil, struct, hashlib, zipfile, re
from collections import defaultdict
BASE=Path('/mnt/data/build_v37/BravelyDefault_TR_Progress_v3.7_2026-08-21')
OUT=Path('/mnt/data/build_v38/BravelyDefault_TR_Progress_v3.8_2026-08-22')
SRC=Path('/mnt/data/fix_font_v34/src/di#U011fer #U015feyler/Graphics')
if OUT.exists(): shutil.rmtree(OUT)
shutil.copytree(BASE,OUT)
TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'; ROMFS=OUT/'romfs'; TRROOT=ROMFS/'Graphics/UI_en'
sys.path.insert(0,str(TOOLS))
import repack_bravely as rb
from bravely_ui_tools import DarcArchive, bclyt_entries, make_text_width_fn
from turkish_compat_encoding_v36 import DECODE
langs=['en','de','fr','es','it']

def dec(s): return ''.join(DECODE.get(c,c) for c in s)
def sha(b): return hashlib.sha256(b).hexdigest()

def build_members(root):
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

def extract(root, memmap, crel):
    p=root/crel
    if p.is_file(): return p.read_bytes()
    z=memmap.get(crel)
    if not z: return None
    frel,name=z; idxp=root/frel/'index.fs'; cp=root/frel/'crowd.fs'
    if not idxp.is_file() or not cp.is_file(): return None
    ib=idxp.read_bytes(); cb=cp.read_bytes()
    for e in rb.parse_index(ib):
        if e['name']==name: return cb[e['offset']:e['offset']+e['size']]
    return None

def rebuild_crowd(root, frel, repl):
    idxp=root/frel/'index.fs'; cp=root/frel/'crowd.fs'
    ib=idxp.read_bytes(); old=cp.read_bytes(); outi=bytearray(ib); outc=bytearray(); changed=0
    for e in rb.parse_index(ib):
        while len(outc)%4: outc.append(0)
        off=len(outc); b=repl.get(e['name'],old[e['offset']:e['offset']+e['size']])
        if e['name'] in repl: changed+=1
        outc+=b
        struct.pack_into('<I',outi,e['pos']+4,off); struct.pack_into('<I',outi,e['pos']+8,len(b))
    while len(outc)%4: outc.append(0)
    idxp.write_bytes(outi); cp.write_bytes(outc)
    return changed

src_members={l:build_members(SRC/f'UI_{l}') for l in langs}
tr_members=build_members(TRROOT)
# official width functions
wfn={}
for l in langs:
    p=SRC/f'UI_{l}/Font/Font'; a=DarcArchive(p.read_bytes()); cf=next(b for _,b in a.files() if b[:4]==b'CFNT'); wfn[l]=make_text_width_fn(cf)
p=TRROOT/'Font/Font'; a=DarcArchive(p.read_bytes()); cf=next(b for _,b in a.files() if b[:4]==b'CFNT'); trw=make_text_width_fn(cf)

# Preload official components only on demand
component_stage=defaultdict(dict)
audit=[]; applied=[]

# Optional wording improvements for long labels while preserving terminology.
wording={
    'StreetPass Verisini Güncelle':'StreetPass Verisini Yenile',
    'Gönderirken Veriyi Güncelle':'Gönderimde Veriyi Güncelle',
}

def replace_txt1_text(data, pane, ordinal, old_dec, new_dec):
    # Replace visible text in a single matching txt1, preserving section prefix and updating lengths.
    if data[:4]!=b'CLYT': return data,False
    from turkish_compat_encoding_v36 import ENCODE
    def enc(s): return ''.join(ENCODE.get(c,c) for c in s)
    hdr=struct.unpack_from('<H',data,6)[0]; out=bytearray(data[:hdr]); off=hdr; txtn=0; done=False
    while off+8<=len(data):
        mg=data[off:off+4]; sz=struct.unpack_from('<I',data,off+4)[0]
        if sz<8 or off+sz>len(data): out+=data[off:]; break
        sec=bytearray(data[off:off+sz])
        if mg==b'txt1' and sz>=0x74:
            pn=sec[0x0c:0x1c].split(b'\0',1)[0].decode('ascii','replace')
            to=struct.unpack_from('<I',sec,0x58)[0]
            # read current
            cur=''
            if 0<to<len(sec):
                i=to; bb=bytearray()
                while i+1<len(sec) and sec[i:i+2]!=b'\0\0': bb+=sec[i:i+2]; i+=2
                cur=bb.decode('utf-16le','replace')
            if pn==pane and txtn==ordinal and dec(cur)==old_dec:
                nb=(enc(new_dec)).encode('utf-16le')+b'\0\0'
                struct.pack_into('<HH',sec,0x4c,len(nb),len(nb))
                sec=sec[:to]+nb
                while len(sec)%4: sec.append(0)
                struct.pack_into('<I',sec,4,len(sec)); done=True
            txtn+=1
        out+=sec; off+=sz
    struct.pack_into('<I',out,0x0c,len(out))
    return bytes(out),done

def patch_fontx(data,pane,ordinal,newfx):
    out=bytearray(data)
    for e in bclyt_entries(data):
        if e['pane']==pane and e['ordinal']==ordinal:
            struct.pack_into('<f',out,e['section_offset']+0x64,float(newfx)); return bytes(out),True
    return data,False

# current source component fetch
for crel in sorted(tr_members):
    if not (crel.startswith('Layout/') or crel.startswith('Common/')): continue
    tcomp=extract(TRROOT,tr_members,crel)
    if not tcomp or tcomp[:4]!=b'darc': continue
    try: ta=DarcArchive(tcomp); tfiles=dict(ta.files())
    except: continue
    donor_files={}
    for l in langs:
        c=extract(SRC/f'UI_{l}',src_members[l],crel)
        if c and c[:4]==b'darc':
            try: donor_files[l]=dict(DarcArchive(c).files())
            except: pass
    replacements={}
    for ip,tb0 in tfiles.items():
        if tb0[:4]!=b'CLYT': continue
        tb=tb0
        # First apply selected wording improvements where exact visible text exists.
        for e in bclyt_entries(tb):
            td=dec(e['text'])
            if td in wording:
                tb2,ok=replace_txt1_text(tb,e['pane'],e['ordinal'],td,wording[td])
                if ok: tb=tb2
        entries=bclyt_entries(tb)
        donor_entries={}
        for l,files in donor_files.items():
            b=files.get(ip)
            if b and b[:4]==b'CLYT': donor_entries[l]=bclyt_entries(b)
        changed=False
        for e in entries:
            if not e['text'] or e['width']<=1 or e['font_x']<=0: continue
            key=(e['pane'],e['ordinal']); ds=[]
            for l,ents in donor_entries.items():
                d=next((x for x in ents if (x['pane'],x['ordinal'])==key),None)
                if not d or not d['text']: continue
                try: rend=wfn[l](d['text'])*(d['font_x']/14.0)
                except: continue
                ds.append({'lang':l,'text':d['text'],'rendered':rend,'pane_w':d['width'],'font_x':d['font_x'],'font_y':d['font_y']})
            if len(ds)<2: continue
            trtxt=dec(e['text'])
            # Re-read visible text after wording replacement from current tb before width compute.
            curent=next((x for x in bclyt_entries(tb) if x['pane']==e['pane'] and x['ordinal']==e['ordinal']),e)
            trtxt=dec(curent['text']); raw=curent['text']
            try: trrend=trw(raw)*(curent['font_x']/14.0)
            except: continue
            maxd=max(ds,key=lambda d:d['rendered']); maxrend=maxd['rendered']
            maxlen=max(len(d['text']) for d in ds)
            ratio=trrend/maxrend if maxrend else 0; pane_ratio=trrend/max(curent['width'],1)
            # Locale-aware risk: Turkish visibly longer than every official localization AND uses most of its pane,
            # or textual length substantially exceeds official labels while already near the edge.
            risk=((ratio>1.03 and pane_ratio>0.65 and len(trtxt.strip())>=6) or
                  (len(trtxt)>maxlen+2 and pane_ratio>0.78 and ratio>0.995))
            if not risk: continue
            target=maxrend*0.98
            desired=curent['font_x']*(target/trrend) if trrend>0 else curent['font_x']
            # Never enlarge; horizontal compression only. Do not go below 8px-equivalent unless unavoidable.
            newfx=min(curent['font_x'],max(8.0,desired))
            before=trrend; after=trw(raw)*(newfx/14.0)
            # If hard floor still exceeds official longest, allow down to 7 only for very tight labels.
            if after>maxrend*1.03 and pane_ratio>0.82:
                newfx=min(newfx,max(7.0,curent['font_x']*(maxrend/trrend)*0.98)); after=trw(raw)*(newfx/14.0)
            if newfx < curent['font_x']-0.01:
                tb,ok=patch_fontx(tb,curent['pane'],curent['ordinal'],newfx)
                if ok:
                    changed=True
                    rec={'archive':crel,'inner':ip,'pane':curent['pane'],'ordinal':curent['ordinal'],'text':trtxt,
                         'before_rendered':before,'after_rendered':after,'pane_width':curent['width'],
                         'old_font_x':curent['font_x'],'new_font_x':newfx,'ratio_to_official_max_before':ratio,
                         'max_official':maxd,'all_official':ds,'max_official_text_len':maxlen}
                    applied.append(rec)
        if tb!=tb0:
            replacements[ip]=tb
    if replacements:
        newcomp=ta.rebuild(replacements)
        frel,name=tr_members[crel]
        component_stage[frel][name]=newcomp

# rebuild current patch crowds
for frel,repl in component_stage.items(): rebuild_crowd(TRROOT,frel,repl)

# Post-audit same locale-aware rule after patch
# Re-run via subprocess audit script after output is in place would require BASE path override; inline targeted verification from applied records.
verify=[]
for rec in applied:
    frel,name=tr_members[rec['archive']]
    comp=extract(TRROOT,tr_members,rec['archive'])
    a=DarcArchive(comp); b=dict(a.files())[rec['inner']]
    e=next(x for x in bclyt_entries(b) if x['pane']==rec['pane'] and x['ordinal']==rec['ordinal'])
    rr=trw(e['text'])*(e['font_x']/14.0); mx=rec['max_official']['rendered']
    verify.append({'archive':rec['archive'],'inner':rec['inner'],'pane':rec['pane'],'text':dec(e['text']),'rendered':rr,'official_max':mx,'ratio':rr/mx if mx else 0,'font_x':e['font_x']})

report={'version':'v3.8','method':'locale-aware visual-width fit','official_locales':langs,'applied_count':len(applied),'applied':applied,'verification':verify,
        'remaining_over_1_03':sum(v['ratio']>1.03 for v in verify),'notes':['Only horizontal txt1 font_x is reduced. Vertical font size and glyph/font assets are unchanged.','Risk is determined against the longest rendered official EN/DE/FR/ES/IT localization for the same pane/ordinal, not a generic pane percentage.']}
REPORTS.mkdir(exist_ok=True)
(REPORTS/'LOCALE_AWARE_TITLE_FIT_v38.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

# Documentation
(DOCS/'BASLIK_UZUNLUK_VE_HIZA_v3.8_TR.md').write_text(f'''# Başlık uzunluğu ve hiza denetimi — v3.8\n\nv3.7'nin genel pane yüzdesi denetimi gerçek cihazdaki başlık/etiket problemini tam temsil etmiyordu. v3.8 aynı `txt1` kaydını İngilizce, Almanca, Fransızca, İspanyolca ve İtalyanca resmi dosyalarda eşleştirir. Her dil için kendi CFNT advance genişliği ve kendi `font_x` değeri kullanılarak gerçek görünür metin genişliği hesaplanır.\n\nTürkçe metin, aynı kaydın **en geniş resmi yerelleştirmesinden** belirgin biçimde genişse ve kendi alanının büyük bölümünü kullanıyorsa yalnız yatay `font_x` küçültülür. Dikey boyut, pane konumu, hizalama ve font glyph'leri değiştirilmez. Böylece bütün UI'yi küçültmek yerine yalnız riskli uzun başlıklar düzeltilir.\n\nBu build'de düzeltilen kayıt sayısı: **{len(applied)}**.\n\nÖrnek riskler: `Arkadaş Menüsü`, `Mızraklar`, `Miğferler`, `İsabet:`, `Kaçınma:`, `Arkadaşlar`, uzun Config/StreetPass başlıkları. Ayrıntılı önce/sonra ölçümleri `Reports/LOCALE_AWARE_TITLE_FIT_v38.json` içindedir.\n''',encoding='utf8')
(DOCS/'CHANGELOG_v3.8_TR.md').write_text(f'''# Bravely Default TR — v3.8\n\n- v3.7'nin genel `%88 pane` yaklaşımına ek olarak resmi diller arası görsel genişlik karşılaştırması eklendi.\n- EN/DE/FR/ES/IT aynı pane metinleri kendi resmi fontlarıyla ölçülüyor. Türkçe en uzun resmi karşılığı aşıyorsa yalnız o kaydın yatay ölçeği düzeltiliyor.\n- `{wording['Gönderirken Veriyi Güncelle']}` ve `{wording['StreetPass Verisini Güncelle']}` ifadeleri daha doğal ve daha kısa karşılıklarla güncellendi.\n- Toplam {len(applied)} uzun başlık/etiket kaydı locale-aware fit geçişinden geçti.\n- v3.7'deki Türkçe font uyumluluğu, noktasız `ı`, İngilizce kapsam düzeltmeleri ve raster yamaları aynen korunur.\n''',encoding='utf8')
# add script and source audit snapshot
shutil.copy2('/mnt/data/build_v38.py',TOOLS/'build_progress_v38.py')
shutil.copy2('/mnt/data/v38_longer_than_locales.json',REPORTS/'LONGER_THAN_OFFICIAL_LOCALES_BASELINE_v38.json')

# Technical crowd audit
errs=[]; pairs=entries=0
for idx in ROMFS.rglob('index.fs'):
    cp=idx.with_name('crowd.fs')
    if not cp.is_file(): continue
    pairs+=1
    try:
        es=rb.parse_index(idx.read_bytes()); cb=cp.read_bytes(); entries+=len(es)
        spans=[]
        for e in es:
            if e['offset']+e['size']>len(cb): errs.append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'out_of_range'})
            spans.append((e['offset'],e['offset']+e['size'],e['name']))
        for a,b in zip(sorted(spans),sorted(spans)[1:]):
            if a[1]>b[0]: errs.append({'path':str(idx.relative_to(ROMFS)),'error':'overlap','a':a,'b':b})
    except Exception as ex: errs.append({'path':str(idx.relative_to(ROMFS)),'error':repr(ex)})
tech={'crowd_pairs':pairs,'crowd_entries':entries,'errors':errs}
(REPORTS/'TECHNICAL_AUDIT_v38.json').write_text(json.dumps(tech,ensure_ascii=False,indent=2),encoding='utf8')
if errs: raise RuntimeError(errs[:3])
# manifest
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file(): manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
# zips
full=Path('/mnt/data/BravelyDefault_TR_Progress_v3.8_2026-08-22.zip'); eur=Path('/mnt/data/BravelyDefault_TR_Progress_v3.8_LayeredFS_EUR.zip'); usa=Path('/mnt/data/BravelyDefault_TR_Progress_v3.8_LayeredFS_USA.zip')
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
        assert q.testzip() is None
print(json.dumps({'full':str(full),'eur':str(eur),'usa':str(usa),'applied':len(applied),'remaining':report['remaining_over_1_03'],'crowd_pairs':pairs,'crowd_entries':entries,'wording':wording},ensure_ascii=False,indent=2))
for r in applied:
    print(f"{r['text']}: {r['old_font_x']:.2f}->{r['new_font_x']:.2f} width {r['before_rendered']:.1f}->{r['after_rendered']:.1f}, official {r['max_official']['rendered']:.1f} ({r['max_official']['lang']} {r['max_official']['text']})")
