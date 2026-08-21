#!/usr/bin/env python3
from pathlib import Path
import sys, json, shutil, struct, hashlib, zipfile, re
from collections import defaultdict, Counter
BASE=Path('/mnt/data/build_v38/BravelyDefault_TR_Progress_v3.8_2026-08-22')
OUT=Path('/mnt/data/build_v39/BravelyDefault_TR_Progress_v3.9_2026-08-22')
SRC=Path('/mnt/data/v37_source_common/Common_en')
if OUT.exists(): shutil.rmtree(OUT)
OUT.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(BASE,OUT)
ROMFS=OUT/'romfs'; COMMON=ROMFS/'Common_en'; TOOLS=OUT/'Tools'; DOCS=OUT/'Docs'; REPORTS=OUT/'Reports'
sys.path.insert(0,str(TOOLS))
import repack_bravely as rb
from turkish_compat_encoding_v36 import ENCODE,DECODE

def enc(s): return ''.join(ENCODE.get(c,c) for c in s)
def dec(s): return ''.join(DECODE.get(c,c) for c in s)
def sha(b): return hashlib.sha256(b).hexdigest()

# Workbook layouts from the extracted source tree.
layouts={}
for xp in SRC.rglob('*.xls'):
    try: wb=rb.parse_biff(xp)
    except Exception: continue
    for sn,cells in wb.items():
        try: t=rb.resolve_sheet_target(xp,sn)
        except Exception: t=None
        if t is not None:
            try: rel=str(t.relative_to(SRC)).replace('\\','/')
            except Exception: continue
            layouts[rel]=cells

def build_members(root):
    m={}
    for idx in root.rglob('index.fs'):
        cp=idx.with_name('crowd.fs')
        if not cp.is_file(): continue
        frel=str(idx.parent.relative_to(root)).replace('\\','/')
        try: ents=rb.parse_index(idx.read_bytes())
        except Exception: continue
        for e in ents:
            rel=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
            m[rel]=(frel,e['name'])
    return m
members=build_members(COMMON)

def extract(rel):
    p=COMMON/rel
    if p.is_file(): return p.read_bytes(),('direct',rel)
    z=members.get(rel)
    if not z: return None,None
    frel,name=z; ib=(COMMON/frel/'index.fs').read_bytes(); cb=(COMMON/frel/'crowd.fs').read_bytes()
    for e in rb.parse_index(ib):
        if e['name']==name: return cb[e['offset']:e['offset']+e['size']],('crowd',frel)
    return None,None

def rebuild_crowd(frel,repl):
    idxp=COMMON/frel/'index.fs'; cp=COMMON/frel/'crowd.fs'
    ib=idxp.read_bytes(); old=cp.read_bytes(); outi=bytearray(ib); outc=bytearray(); changed=0
    for e in rb.parse_index(ib):
        while len(outc)%4: outc.append(0)
        off=len(outc); b=repl.get(e['name'],old[e['offset']:e['offset']+e['size']])
        if e['name'] in repl: changed+=1
        outc+=b; struct.pack_into('<I',outi,e['pos']+4,off); struct.pack_into('<I',outi,e['pos']+8,len(b))
    while len(outc)%4: outc.append(0)
    idxp.write_bytes(outi); cp.write_bytes(outc)
    return changed

# Conservative brevity corrections. These are labels/names, not prose.
FILE_EXACT={
 'Paramater/DetailInfoSupportTable.btb':{
   'Zaman Büyüsü Büyü Puanı Tasarrufu':'Zaman Büyüsü MP Tasarrufu',
   'Kılıç Büyüsü Büyü Puanı Tasarrufu':'Çağırma Büyüsü MP Tasarrufu',
   'Beyaz Büyü Büyü Puanı Tasarrufu':'Beyaz Büyü MP Tasarrufu',
   'Kara Büyü Büyü Puanı Tasarrufu':'Kara Büyü MP Tasarrufu',
   'Tüm Büyüler Büyü Puanı Tasarrufu':'Büyü MP Tasarrufu',
   'İş Puanı Artışı':'JP Artışı',
   'Cesaret Puanı Yeteneği Güçlendir':'BP Yetenek Takviyesi',
   'Cesaret Puanı Sınırı Artışı':'BP Sınırı Artışı',
   'Büyü Puanı %10 Artışı':'MP %10 Artışı',
   'Büyü Puanı %20 Artışı':'MP %20 Artışı',
   'Büyü Puanı %30 Artışı':'MP %30 Artışı',
   'Cesaret Puanı Yenileme':'BP Yenileme',
   'Hasardan Büyü Puanı':'MP Dönüşümü',
   'Hava Hareketleri':'Hava Hamleleri',
   'Yumruk Silahı Ustalığı':'Yumruk Ustalığı',
   'Canı Azamiye Çıkar':'Azami HP',
 },
 'Paramater/SupportAbility.btb':{
   'Fiziksel Saldırı %10 Artış':'Fiz. Saldırı %10',
   'Fiziksel Saldırı %20 Artış':'Fiz. Saldırı %20',
   'Fiziksel Saldırı %30 Artış':'Fiz. Saldırı %30',
   'Fiziksel Savunma %10 Artış':'Fiz. Savunma %10',
   'Fiziksel Savunma %20 Artış':'Fiz. Savunma %20',
   'Fiziksel Savunma %30 Artış':'Fiz. Savunma %30',
   'Büyü Saldırısı %10 Artış':'Büyü Sald. %10',
   'Büyü Saldırısı %20 Artış':'Büyü Sald. %20',
   'Büyü Saldırısı %30 Artış':'Büyü Sald. %30',
   'Büyü Savunması %10 Artış':'Büyü Sav. %10',
   'Büyü Savunması %20 Artış':'Büyü Sav. %20',
   'Büyü Savunması %30 Artış':'Büyü Sav. %30',
 },
 'Paramater/SupportAbilityAL.btb':{
   'Fiziksel Saldırı %10 Artış':'Fiz. Saldırı %10',
   'Fiziksel Saldırı %20 Artış':'Fiz. Saldırı %20',
   'Fiziksel Saldırı %30 Artış':'Fiz. Saldırı %30',
   'Fiziksel Savunma %10 Artış':'Fiz. Savunma %10',
   'Fiziksel Savunma %20 Artış':'Fiz. Savunma %20',
   'Fiziksel Savunma %30 Artış':'Fiz. Savunma %30',
   'Büyü Saldırısı %10 Artış':'Büyü Sald. %10',
   'Büyü Saldırısı %20 Artış':'Büyü Sald. %20',
   'Büyü Saldırısı %30 Artış':'Büyü Sald. %30',
   'Büyü Savunması %10 Artış':'Büyü Sav. %10',
   'Büyü Savunması %20 Artış':'Büyü Sav. %20',
   'Büyü Savunması %30 Artış':'Büyü Sav. %30',
 },
 'Paramater/SpecialPartsTable.btb':{
   'Cesaret Puanı Artışı Sv.1':'BP Artışı Sv.1',
   'Cesaret Puanı Artışı Sv.2':'BP Artışı Sv.2',
   'Büyü Saldırısı +':'Büyü Sald. +',
   'Büyü Saldırısı -':'Büyü Sald. -',
   'Büyü Savunması +':'Büyü Sav. +',
   'Büyü Savunması -':'Büyü Sav. -',
 },
 'MessageTable/NoteMessageData.btb':{
   'Canavar Ansiklopedisi':'Canavarlar',
 },
 'Paramater/DetailInfoCommandTable.btb':{
   'Etki Alanını Genişlet':'Alanı Genişlet',
 },
 'Paramater/CommandAbility.btb':{
   'Göklere Sıçra (zıplama)':'Göklere Sıçra',
 },
 'MessageTable/MenuMessageData.btb':{
   'Otomatik Oynatma':'Otomatik Oynat',
 },
 'MenuTable/EventViewerPartyChat.mtb':{
   '[PCF1] ve [PCF2] Kapışıyor':'[PCF1] vs. [PCF2]',
 },
 'PartyChat/PartyChatScript5.btb':{
   '[PCF1] ve [PCF2] Kapışıyor':'[PCF1] vs. [PCF2]',
 },
 'Paramater/SyogoTable.btb':{
   'Hevesli Tapınak Şövalyesi':'Hevesli Tapınakçı',
 },
}
# Dynamic class/name labels: compact exact-field forms only; prose keeps the user's original wording.
GLOBAL_EXACT={
 'Tapınak Şövalyesi':'Tapınakçı',
 '*Tapınak Şövalyesi':'*Tapınakçı',
 'Tapınak Şövalyesi Braev':'Tapınakçı Braev',
 'Hevesli Tapınak Şövalyesi':'Hevesli Tapınakçı',
}
# Event-viewer titles need correct Turkish suffixes when compacted.
FILE_EXACT.setdefault('MenuTable/EventViewer.mtb',{}).update({
 'Tapınak Şövalyesinin İdealleri':'Tapınakçının İdealleri',
 'Tapınak Şövalyesinin Hediyesi':'Tapınakçının Hediyesi',
 'Tapınak Şövalyesi Yas Tutuyor':'Tapınakçı Yas Tutuyor',
 "Kızıl'ın Sırrı Açığa Çıkıyor":"Kızıl'ın Sırrı",
 'Oyuncak Bebekler Gibi':'Kuklalar Gibi',
 'Yerinde Duramayan Bacaklar':'Huzursuz Bacaklar',
})
# Confirmed row mismatch in user workbook/source: TW_10 rows 621..635 field 2.
TW10_FIX={
 621:'Egil geldiğinden beri hancı eski\nhâline döndü.',
 622:'Han sonunda yeniden canlandı.',
 623:'Çok yalnız görünüyordu. Umarım yakında\nkendini daha iyi hisseder…',
 624:'Ah, merhaba. Hoş geldin.',
 625:'Hoş geldin! Geceyi burada mı\ngeçireceksin?',
 626:'Çok çalışıyorsun, ha? İyice dinlenmeyi\nde unutma!',
 627:'Şimdilik dışarı çıkmasan daha iyi.',
 628:'Kralını korumak için canını verdi. Eminim\nhiç pişman değildi… Şimdi biraz dinlen.',
 629:'Sıradan bir düşman değil. Lütfen…\ndikkatli ol.',
 630:'Ah… Sizsiniz. Kusura bakmayın,\nbugün biraz yorgunum…',
 631:'Artık güne başlayacak gücü kendimde\nbulamıyorum.',
 632:'Onu her düşündüğümde kalbim yeniden\nparçalanıyor…',
 633:'Ah, merhaba. Sizi… sizi görmek güzel.\nRahatınıza bakın…',
 634:'Yeniden hayata döndüm. Bunu size\nborçluyum.',
 635:'Ah, sizsiniz. Gördüğünüz gibi Egil\nher zamanki gibi enerjik.',
}

def transform(cur,cells,rel):
    m=rb.btbf_meta(cur); mat=rb.sheet_matrix(cells); vt,pt,vc=rb.text_layout(mat,m)
    if len(mat)-1!=m['count']: raise ValueError((rel,'rows',len(mat)-1,m['count']))
    data=bytearray(cur[0x30:m['label_start']]); labels=cur[m['label_start']:m['text_start']]; oldblk=cur[m['text_start']:m['text_start']+m['text_size']]
    newblk=bytearray(); changes=[]
    for r in range(1,len(mat)):
        for k,pc in enumerate(pt):
            fi=pc-vc; roff=(r-1)*m['record_size']+4*fi; ptr=struct.unpack_from('<I',data,roff)[0]
            if ptr==0xffffffff or ptr>=m['text_size']: continue
            oldraw=rb.read_utf16z(oldblk,ptr) or ''; old=dec(oldraw); new=old
            if rel=='TextTable/TW_10.txb' and k==2 and r in TW10_FIX: new=TW10_FIX[r]
            if old in FILE_EXACT.get(rel,{}): new=FILE_EXACT[rel][old]
            if old in GLOBAL_EXACT: new=GLOBAL_EXACT[old]
            ne=enc(new); np=len(newblk); struct.pack_into('<I',data,roff,np); newblk+=ne.encode('utf-16le')+b'\0\0'
            if new!=old: changes.append({'row':r,'field':k,'old':old,'new':new})
    hdr=bytearray(cur[:0x30]); size=m['text_start']+len(newblk); struct.pack_into('<I',hdr,4,size); struct.pack_into('<I',hdr,0x1c,len(newblk))
    return bytes(hdr)+bytes(data)+labels+bytes(newblk),changes

crowd_repl=defaultdict(dict); allchanges=[]
for rel,cells in layouts.items():
    cur,loc=extract(rel)
    if not cur or cur[:4]!=b'BTBF': continue
    # Fast skip unless target file, dynamic term present, or TW10.
    if rel not in FILE_EXACT and rel!='TextTable/TW_10.txb' and not any(enc(k).encode('utf-16le') in cur for k in GLOBAL_EXACT): continue
    nb,ch=transform(cur,cells,rel)
    if not ch: continue
    allchanges.append({'file':rel,'count':len(ch),'changes':ch})
    if loc[0]=='direct': (COMMON/rel).write_bytes(nb)
    else: crowd_repl[loc[1]][Path(rel).name]=nb
for frel,repl in crowd_repl.items(): rebuild_crowd(frel,repl)

# Verification of TW10 against intended overrides and changed labels.
def extract_after(rel):
    # members offsets may have changed, so parse current index each call
    p=COMMON/rel
    if p.is_file(): return p.read_bytes()
    par=str(Path(rel).parent).replace('\\','/'); name=Path(rel).name
    ib=(COMMON/par/'index.fs').read_bytes(); cb=(COMMON/par/'crowd.fs').read_bytes()
    for e in rb.parse_index(ib):
        if e['name']==name:return cb[e['offset']:e['offset']+e['size']]

verify={'tw10':[],'brevity':[]}
rel='TextTable/TW_10.txb'; b=extract_after(rel); cells=layouts[rel]; m=rb.btbf_meta(b); mat=rb.sheet_matrix(cells);vt,pt,vc=rb.text_layout(mat,m); blk=b[m['text_start']:]
for r,want in TW10_FIX.items():
    pc=pt[2];fi=pc-vc;ptr=struct.unpack_from('<I',b,0x30+(r-1)*m['record_size']+4*fi)[0]; got=dec(rb.read_utf16z(blk,ptr) or '')
    verify['tw10'].append({'row':r,'ok':got==want,'got':got,'expected':want})
    assert got==want
for f in allchanges:
    for c in f['changes']:
        if f['file']!='TextTable/TW_10.txb':
            verify['brevity'].append({'file':f['file'],'old':c['old'],'new':c['new'],'old_len':len(c['old']),'new_len':len(c['new']),'delta':len(c['new'])-len(c['old'])})

# Technical crowd audit.
errs=[]; pairs=entries=0
for idx in ROMFS.rglob('index.fs'):
    cp=idx.with_name('crowd.fs')
    if not cp.is_file(): continue
    pairs+=1
    try:
        es=rb.parse_index(idx.read_bytes()); cb=cp.read_bytes(); entries+=len(es); spans=[]
        for e in es:
            if e['offset']+e['size']>len(cb): errs.append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'out_of_range'})
            spans.append((e['offset'],e['offset']+e['size'],e['name']))
        ss=sorted(spans)
        for a,b in zip(ss,ss[1:]):
            if a[1]>b[0]: errs.append({'path':str(idx.relative_to(ROMFS)),'error':'overlap','a':a,'b':b})
    except Exception as ex: errs.append({'path':str(idx.relative_to(ROMFS)),'error':repr(ex)})
if errs: raise RuntimeError(errs[:5])

# Reports/docs.
summary={'version':'v3.9','base':'v3.8','common_files_changed':len(allchanges),'common_text_changes':sum(x['count'] for x in allchanges),'brevity_changes':len(verify['brevity']),'tw10_row_fixes':len(TW10_FIX),'technical':{'crowd_pairs':pairs,'crowd_entries':entries,'errors':errs},'files':allchanges}
(REPORTS/'BREVITY_AND_ALIGNMENT_AUDIT_v39.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'TW10_ALIGNMENT_FIX_v39.json').write_text(json.dumps(verify['tw10'],ensure_ascii=False,indent=2),encoding='utf8')
(REPORTS/'TECHNICAL_AUDIT_v39.json').write_text(json.dumps(summary['technical'],ensure_ascii=False,indent=2),encoding='utf8')
# baseline audit snapshots from this investigation
for src,name in [('/mnt/data/v39_ui_length_audit.json','UI_LENGTH_AUDIT_POST_v38.json'),('/mnt/data/v39_common_length_audit.json','COMMON_LENGTH_AUDIT_BASELINE_v39.json')]:
    if Path(src).is_file(): shutil.copy2(src,REPORTS/name)
(DOCS/'KISALIK_VE_DINAMIK_METIN_DENETIMI_v3.9_TR.md').write_text('''# Kısalık ve dinamik metin denetimi — v3.9\n\nv3.8 yalnız BCLYT başlık/etiket genişliklerini resmi EN/DE/FR/ES/IT yerleşimleriyle karşılaştırıyordu. v3.9 buna Common_en içindeki dinamik ad/etiketleri ekler.\n\nTemel kural: açıklama ve diyaloglarda anlam uğruna doğal Türkçe uzunluk korunur; dar listelerde ise oyunun kendisinin kullandığı MP/BP/JP kısaltmaları gereksiz yere açılmaz. Bu nedenle `Büyü Puanı`, `Cesaret Puanı`, `İş Puanı` gibi uzun açılımlar yalnız kısa yetenek/istatistik adlarında MP/BP/JP biçimine döndürüldü.\n\nAyrıca `Templar` için `Tapınak Şövalyesi` dinamik sınıf adı diğer sınıflara göre aşırı uzun olduğu için aynı kavramı koruyan `Tapınakçı` terimine çekildi.\n\n`TextTable/TW_10.txb` içinde 621–635 arasındaki 15 satırın Türkçe çalışma kitabında kaynak İngilizceyle eşleşmediği doğrulandı. Bu satırlar kaynak İngilizceye göre yeniden çevrildi.\n''',encoding='utf8')
(DOCS/'CHANGELOG_v3.9_TR.md').write_text(f'''# Bravely Default TR — v3.9\n\n- v3.8'in resmi dil genişliği denetimi korunur.\n- Common_en dinamik kısa adları için ayrıca uzunluk denetimi yapıldı.\n- MP/BP/JP'nin gereksiz yere tam açıldığı kısa yetenek/istatistik adları kısaltıldı.\n- `Tapınak Şövalyesi` → `Tapınakçı` olarak tutarlılaştırıldı.\n- `Canavar Ansiklopedisi` → `Canavarlar`, `Etki Alanını Genişlet` → `Alanı Genişlet`, `Otomatik Oynatma` → `Otomatik Oynat` gibi net uzunluk düzeltmeleri yapıldı.\n- `TW_10` içindeki 15 satırlık doğrulanmış yanlış eşleşme kaynak İngilizceye göre yeniden çevrildi.\n- Common_en değişiklik sayısı: {sum(x['count'] for x in allchanges)}.\n- Teknik crowd/index denetimi: {pairs} çift / {entries} giriş / 0 hata.\n''',encoding='utf8')
shutil.copy2('/mnt/data/build_v39.py',TOOLS/'build_progress_v39.py')
# Update readme version note without destroying history.
with open(OUT/'README_TR.md','a',encoding='utf8') as f:
    f.write('\n\n## v3.9 notu\nDinamik kısa etiketler için MP/BP/JP kısalık denetimi ve TW_10 satır hizası düzeltmeleri eklendi. Ayrıntılar Docs/CHANGELOG_v3.9_TR.md içindedir.\n')
# manifest last
manifest=[]
for p in sorted(OUT.rglob('*')):
    if p.is_file() and p.name!='MANIFEST_SHA256.json': manifest.append({'path':str(p.relative_to(OUT)),'size':p.stat().st_size,'sha256':sha(p.read_bytes())})
(OUT/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
# zip
full=Path('/mnt/data/BravelyDefault_TR_Progress_v3.9_2026-08-22.zip'); eur=Path('/mnt/data/BravelyDefault_TR_Progress_v3.9_LayeredFS_EUR.zip'); usa=Path('/mnt/data/BravelyDefault_TR_Progress_v3.9_LayeredFS_USA.zip')
for z in (full,eur,usa):
    if z.exists(): z.unlink()
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file(): z.write(p,p.relative_to(OUT.parent))
for zp,tid in [(eur,'00040000000FC600'),(usa,'00040000000FC500')]:
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROMFS.rglob('*')):
            if p.is_file(): z.write(p,Path('luma/titles')/tid/'romfs'/p.relative_to(ROMFS))
for z in (full,eur,usa):
    with zipfile.ZipFile(z) as q: assert q.testzip() is None
print(json.dumps({'full':str(full),'eur':str(eur),'usa':str(usa),'files_changed':len(allchanges),'text_changes':sum(x['count'] for x in allchanges),'brevity_changes':len(verify['brevity']),'tw10_fixes':len(TW10_FIX),'crowd_pairs':pairs,'crowd_entries':entries},ensure_ascii=False,indent=2))
for f in allchanges:
    print('\n',f['file'],f['count'])
    for c in f['changes'][:30]: print(' ',c['old'].replace('\n',' / '),'->',c['new'].replace('\n',' / '))
