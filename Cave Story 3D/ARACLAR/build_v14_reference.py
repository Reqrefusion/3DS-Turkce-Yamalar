from pathlib import Path
import shutil, re, csv, hashlib, struct, subprocess, textwrap, os
from PIL import Image, ImageDraw
import numpy as np

V13=Path('/mnt/data/cs3d_v13/Cave_Story_3D_TR_v13_font_reset_guvenli')
ORIG_FONT=V13/'KARSILASTIRMA_ORIJINAL_FONT'
ORIG_EXEFS=Path('/mnt/data/exefsinspect/exefs')
V10_REPORT=V13/'RAPORLAR/EXEFS_TURKCE_YAMA_V10.tsv'
BASE=Path('/mnt/data/cs3d_v14')
OUT=BASE/'Cave_Story_3D_TR_v14_font_metrik_turkce_ui'
if OUT.exists(): shutil.rmtree(OUT)
BASE.mkdir(parents=True,exist_ok=True)
shutil.copytree(V13,OUT)
DATA=OUT/'000400000004D200/romfs/data'
EXEFS=OUT/'000400000004D200/exefs'
REPORTS=OUT/'RAPORLAR'; PREV=OUT/'ONIZLEMELER'; TOOLS=OUT/'ARACLAR'
for p in [REPORTS,PREV,TOOLS,EXEFS]: p.mkdir(parents=True,exist_ok=True)

# -----------------------------
# FONT V14: exact base glyph body + target-only metrics/kerning
# -----------------------------
orig_img=Image.open(ORIG_FONT/'font_batang_0.tga').convert('RGBA')
orig_fnt_bytes=(ORIG_FONT/'font_batang.fnt').read_bytes()
orig_text=orig_fnt_bytes.decode('latin1')

def parse_chars(text):
    out={}
    for ln in text.splitlines():
        if ln.startswith('char id='):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',ln)}
            out[d['id']]=d
    return out

def parse_kerns(text):
    out=[]
    for ln in text.splitlines():
        if ln.startswith('kerning first='):
            d={k:int(v) for k,v in re.findall(r'(first|second|amount)=(-?\d+)',ln)}
            out.append((d['first'],d['second'],d['amount']))
    return out

chars=parse_chars(orig_text); orig_kerns=parse_kerns(orig_text)
alpha=np.array(orig_img)[:,:,3]
def crop(cid):
    d=chars[cid]
    return alpha[d['y']:d['y']+d['height'],d['x']:d['x']+d['width']].copy()

G=crop(71); I=crop(73); S=crop(83); g=crop(103); i_g=crop(105); s=crop(115)
Cced=crop(199); cced=crop(231)

# Exact body preservation + tiny accents designed around Calibri's existing alpha levels.
breve8=np.zeros((3,8),dtype=np.uint8)
breve8[0,1]=95; breve8[0,6]=95
breve8[1,1]=203; breve8[1,6]=203
breve8[2,2]=95; breve8[2,3]=219; breve8[2,4]=219; breve8[2,5]=95
breve7=np.zeros((3,7),dtype=np.uint8)
breve7[0,1]=95; breve7[0,5]=95
breve7[1,1]=203; breve7[1,5]=203
breve7[2,2]=111; breve7[2,3]=231; breve7[2,4]=111

glyphs={}
# Ğ: G body copied byte-for-byte, placed after 3-row breve. Base G screen y remains identical.
a=np.zeros((13,8),dtype=np.uint8); a[0:3]=breve8; a[3:13]=G; glyphs[208]=a
# İ: exact uppercase I body, with the same lowercase-i dot alpha centered above it.
a=np.zeros((13,4),dtype=np.uint8); a[1]=i_g[1]; a[3:13]=I; glyphs[221]=a
# Ş: exact S body. Reuse original Ç cedilla alpha at the same baseline-relative position.
a=np.zeros((12,7),dtype=np.uint8); a[0:10]=S; a[9,3]=Cced[9,3]; a[9,4]=Cced[9,4]; a[10,3]=Cced[10,3]; a[10,4]=Cced[10,4]; glyphs[222]=a
# ğ: exact g body at the original baseline position, breve above.
a=np.zeros((13,7),dtype=np.uint8); a[0:3]=breve7; a[3:13]=g; glyphs[240]=a
# ı: exact i stem, only dot/top empty rows removed. Advance remains exactly i.
glyphs[253]=i_g[2:10].copy()
# ş: exact s body; cedilla from original ç at same baseline-relative position.
a=np.zeros((10,6),dtype=np.uint8); a[0:8]=s; a[7,2]=cced[7,3]; a[7,3]=cced[7,4]; a[8,2]=cced[8,3]; a[8,3]=cced[8,4]; glyphs[254]=a

PLACEMENT={208:(2,82),221:(12,82),222:(18,82),240:(27,82),253:(36,82),254:(42,82)}
METRICS={
 208:dict(width=8,height=13,xoffset=0,yoffset=0,xadvance=8),  # G advance=8, body screen y=3
 221:dict(width=4,height=13,xoffset=0,yoffset=0,xadvance=4),  # I advance=4; fixes extra spacing
 222:dict(width=7,height=12,xoffset=-1,yoffset=3,xadvance=6), # exactly S metrics + cedilla
 240:dict(width=7,height=13,xoffset=0,yoffset=2,xadvance=6),  # g body remains y=5
 253:dict(width=4,height=8,xoffset=0,yoffset=5,xadvance=4),   # i stem metrics without dot
 254:dict(width=6,height=10,xoffset=0,yoffset=5,xadvance=6), # exactly s metrics + cedilla
}
BASEMAP={208:71,221:73,222:83,240:103,253:105,254:115}
TARGETS=set(BASEMAP)
BASE_TO_TARGET={v:k for k,v in BASEMAP.items()}

# Place glyphs only in the originally-empty bottom atlas band. Original 190 glyph pixels remain untouched.
out_arr=np.array(orig_img).copy()
for cid,a in glyphs.items():
    x,y=PLACEMENT[cid]; h,w=a.shape
    out_arr[y:y+h,x:x+w,:3]=255
    out_arr[y:y+h,x:x+w,3]=a
out_img=Image.fromarray(out_arr,'RGBA')
out_img.save(DATA/'font_batang_0.tga',format='TGA')

# Rewrite exactly six char records. Preserve all unrelated kerning pairs byte-semantically;
# discard legacy Ý/ý/etc target-id kernings, replace only with clones of G/I/S/g/i/s behavior.
def char_line(cid,x,y,m):
    return (f"char id={cid:<4} x={x:<5} y={y:<5} width={m['width']:<5} height={m['height']:<5} "
            f"xoffset={m['xoffset']:<5} yoffset={m['yoffset']:<5} xadvance={m['xadvance']:<5} page=0  chnl=15")
lines=orig_text.replace('\r\n','\n').split('\n')
header_idx=next(i for i,l in enumerate(lines) if l.startswith('kernings count='))
pre=[]
for ln in lines[:header_idx]:
    m=re.match(r'char id=(\d+)',ln)
    if m and int(m.group(1)) in TARGETS:
        cid=int(m.group(1)); x,y=PLACEMENT[cid]
        pre.append(char_line(cid,x,y,METRICS[cid]))
    else:
        pre.append(ln)
# Preserve all kerning entries that do not involve a target id.
kept=[k for k in orig_kerns if k[0] not in TARGETS and k[1] not in TARGETS]
merged={(f,s):a for f,s,a in kept}
# Mirror only original/base-letter kerning behavior to Turkish target IDs.
for f,s,a in kept:
    fs=[f]+([BASE_TO_TARGET[f]] if f in BASE_TO_TARGET else [])
    ss=[s]+([BASE_TO_TARGET[s]] if s in BASE_TO_TARGET else [])
    for ff in fs:
        for s2 in ss:
            if ff==f and s2==s: continue
            merged[(ff,s2)]=a
new_kerns=[(f,s,a) for (f,s),a in sorted(merged.items())]
pre.append(f'kernings count={len(new_kerns)}')
for f,s,a in new_kerns:
    pre.append(f"kerning first={f:<4} second={s:<4} amount={a}")
new_text='\r\n'.join(pre)+'\r\n'
(DATA/'font_batang.fnt').write_bytes(new_text.encode('latin1'))

# Font QA: all non-target char metrics exactly identical, all non-target kerning pairs identical.
new_chars=parse_chars(new_text); new_kerns_parsed=parse_kerns(new_text)
non_target_char_diff=[]
for cid,d in chars.items():
    if cid in TARGETS: continue
    if new_chars[cid]!=d: non_target_char_diff.append(cid)
orig_non_target={(f,s):a for f,s,a in orig_kerns if f not in TARGETS and s not in TARGETS}
new_non_target={(f,s):a for f,s,a in new_kerns_parsed if f not in TARGETS and s not in TARGETS}
assert orig_non_target==new_non_target
assert not non_target_char_diff
# Pixel QA outside the placement rectangles: difference must be zero.
orig_arr=np.array(orig_img); diff=np.any(orig_arr!=out_arr,axis=2)
allowed=np.zeros(diff.shape,dtype=bool)
for cid,a in glyphs.items():
    x,y=PLACEMENT[cid]; h,w=a.shape; allowed[y:y+h,x:x+w]=True
outside=int(np.count_nonzero(diff & ~allowed)); assert outside==0

# -----------------------------
# ExeFS V14: CP1254 Turkish everywhere + autosave warning
# -----------------------------
orig_code=(ORIG_EXEFS/'code.bin').read_bytes()
# offset, old, slot size including NUL/padding, Turkish
slots=[
(0x060a6c,'Loading',10,'Yükleme'),
(0x067588,'Story Mode',16,'Öykü Modu'),
(0x067598,'Time Attack',12,'Süre Yarışı'),
(0x0675a8,'Classic Mode',16,'Klasik Mod'),
(0x0675c0,'Yes',4,'E'),(0x0675c4,'No',4,'H'),
(0x0675c8,'Easy Mode',12,'Kolay Mod'),
(0x0675d4,'Best choice for first-time players.',36,'İlk kez oynayanlar için uygun.'),
(0x0675f8,'Normal Mode',12,'Normal Mod'),
(0x067604,'For players familiar with Cave Story.',40,'Oyuna aşina oyuncular için.'),
(0x06762c,'Hard Mode',12,'Zor Mod'),
(0x067638,'Not recommended for first-time players.',40,'İlk kez oynayanlara önerilmez.'),
(0x0679b0,'New Game',12,'Yeni Oyun'),
(0x0c0418,'Story Mode',12,'Öykü Modu'),(0x0c0424,'Time Attack',12,'Süre Yarışı'),
(0x0c0430,'Classic Mode',16,'Klasik Mod'),(0x0c0440,'Clear Slot',12,'Kaydı Sil'),
(0x0c044c,'Are you sure?',16,'Emin misin?'),(0x0c045c,'Yes',4,'E'),(0x0c0460,'No',3,'H'),
(0x0c0918,'Continue Game',16,'Devam Et'),(0x0c0928,'Exit Game',12,'Oyundan Çık'),
(0x0c0934,'Yes',4,'E'),(0x0c0938,'No',3,'H'),
(0x09df1c,'All unsaved data will be lost, are',36,'Kaydedilmemiş veriler silinecek.'),
(0x09df44,'you sure you want to quit?',32,'Çıkmak istediğine emin mi?'),
(0x0d00c8,'The save data could not be accessed.',37,'Kayıt verisine erişilemedi.'),
# Save / Game Card warning strings. These are referenced as two-string message groups.
(0x0d010d,'the Nintendo 3DS Game Card',27,'Nintendo 3DS Oyun Kartı'),
(0x0d0128,'Do not turn the system off or remove',37,'Sistemi kapatmayın; çıkarmayın:'),
(0x0d0198,'Please turn the power off and reinsert',39,'Kapatıp tekrar takın:'),
]

def validate_slot(off,old,slotlen):
    b=old.encode('ascii')
    assert orig_code[off:off+len(b)]==b,(hex(off),old)
    assert orig_code[off+len(b)]==0,(hex(off),'no NUL')
    tail=orig_code[off+len(b)+1:off+slotlen]
    assert all(x==0 for x in tail),(hex(off),'nonzero pad',tail.hex())

for off,old,n,new in slots:
    validate_slot(off,old,n)
    assert len(new.encode('cp1254'))+1<=n,(hex(off),new,len(new.encode('cp1254')),n)

# Proper Turkish location names from V10 manual location table.
v10rows=list(csv.DictReader(V10_REPORT.open(encoding='utf-8'),delimiter='\t'))
locs=[]
for r in v10rows:
    if r['kategori']!='Mekân adı': continue
    off=int(r['offset'],16); old=r['ingilizce']; new=r['turkce']
    oldb=old.encode('ascii')
    assert orig_code[off:off+len(oldb)]==oldb,(hex(off),old)
    assert orig_code[off+len(oldb)]==0
    assert all(x==0 for x in orig_code[off+len(oldb)+1:off+64])
    assert len(new.encode('cp1254'))+1<=64
    locs.append((off,old,64,new))

code=bytearray(orig_code); patch_rows=[]; allowed=set()
for off,old,n,new in slots+locs:
    nb=new.encode('cp1254')
    code[off:off+n]=b'\0'*n; code[off:off+len(nb)]=nb
    allowed.update(range(off,off+n))
    patch_rows.append((f'0x{off:06X}',old,new,len(nb),n))
code=bytes(code)
# Critical V10 crash pointers must be original.
for off in [0x675b8,0x675bc]: assert code[off:off+4]==orig_code[off:off+4]
assert int.from_bytes(code[0x675bc:0x675c0],'little')==0x001e3228
bad=[i for i,(a,b) in enumerate(zip(orig_code,code)) if a!=b and i not in allowed]; assert not bad
EXEFS.joinpath('code.bin').write_bytes(code)
for fn in ['banner.bin','icon.bin','logo.bin']: shutil.copy2(ORIG_EXEFS/fn,EXEFS/fn)

# IPS generator

def make_ips(a,b,path):
    out=bytearray(b'PATCH');i=0;L=len(a)
    while i<L:
        if a[i]==b[i]: i+=1; continue
        start=i; buf=bytearray()
        while i<L and a[i]!=b[i] and len(buf)<65535:
            buf.append(b[i]);i+=1
        out += start.to_bytes(3,'big')+len(buf).to_bytes(2,'big')+buf
    out+=b'EOF';path.write_bytes(out)
make_ips(orig_code,code,OUT/'000400000004D200/code.ips')

# Verify IPS reproduction.
def apply_ips(src,ips):
    out=bytearray(src); b=ips; assert b[:5]==b'PATCH'; pos=5
    while b[pos:pos+3]!=b'EOF':
        off=int.from_bytes(b[pos:pos+3],'big'); pos+=3
        sz=int.from_bytes(b[pos:pos+2],'big'); pos+=2
        if sz:
            out[off:off+sz]=b[pos:pos+sz]; pos+=sz
        else:
            rle=int.from_bytes(b[pos:pos+2],'big');pos+=2; val=b[pos];pos+=1;out[off:off+rle]=bytes([val])*rle
    return bytes(out)
assert apply_ips(orig_code,(OUT/'000400000004D200/code.ips').read_bytes())==code

# -----------------------------
# Reports / previews
# -----------------------------
# Create glyph comparison preview using new metrics.
def render_text(sample, scale=4):
    fchars=parse_chars(new_text)
    kern={(f,s):a for f,s,a in new_kerns_parsed}
    bs=sample.encode('cp1254')
    # pre-measure
    width=12; prev=None
    for b in bs:
        if prev is not None: width+=kern.get((prev,b),0)
        width+=fchars.get(b,{'xadvance':6})['xadvance']; prev=b
    can=Image.new('RGBA',(max(width+12,500),34),(22,22,28,255)); x=8; prev=None
    for b in bs:
        if prev is not None:x+=kern.get((prev,b),0)
        d=fchars.get(b)
        if d:
            crop=out_img.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height']))
            can.alpha_composite(crop,(x+d['xoffset'],5+d['yoffset']));x+=d['xadvance']
        else:x+=6
        prev=b
    return can.resize((can.width*scale,can.height*scale),Image.Resampling.NEAREST)

samples=[
'S Ş s ş    I İ i ı    G Ğ g ğ',
'Öykü Modu   Süre Yarışı   Yükleme',
'Başlangıç Noktası   İlk Mağara   Çalılıklar',
'İşin ışığı şimdi değişti. Görüşürüz!',
]
renders=[render_text(s,4) for s in samples]
W=max(x.width for x in renders);H=sum(x.height for x in renders)
canvas=Image.new('RGBA',(W,H),(22,22,28,255)); y=0
for r in renders: canvas.alpha_composite(r,(0,y));y+=r.height
canvas.convert('RGB').save(PREV/'FONT_V14_KARSILASTIRMA.png')

# Target glyph detail sheet
newc=parse_chars(new_text)
sheet=Image.new('RGBA',(6*120,180),(30,30,35,255));d=ImageDraw.Draw(sheet)
labels=[(83,'S'),(222,'Ş'),(115,'s'),(254,'ş'),(73,'I'),(221,'İ')]
for j,(cid,label) in enumerate(labels):
    c=newc[cid]; cr=out_img.crop((c['x'],c['y'],c['x']+c['width'],c['y']+c['height'])).resize((c['width']*10,c['height']*10),Image.Resampling.NEAREST)
    sheet.alpha_composite(cr,(j*120+10,25));d.text((j*120+10,5),label,fill='white');d.text((j*120+5,155),f"xa={c['xadvance']} xo={c['xoffset']} yo={c['yoffset']}",fill='white')
sheet.convert('RGB').save(PREV/'FONT_S_SH_I_I_V14.png')

with (REPORTS/'FONT_METRIK_QA_V14.txt').open('w',encoding='utf-8') as f:
    f.write('Cave Story 3D TR V14 - Font Metrik QA\n=====================================\n')
    f.write(f'Orijinal char sayisi: {len(chars)}\n')
    f.write(f'Hedef disi char metrik farki: {len(non_target_char_diff)}\n')
    f.write(f'Orijinal kerning: {len(orig_kerns)}\n')
    f.write(f'Yeni kerning: {len(new_kerns)}\n')
    f.write(f'Hedef karakterleri icermeyen kerning seti birebir korundu: EVET ({len(orig_non_target)} cift)\n')
    f.write(f'Yeni atlas izinli alan disinda degisen piksel: {outside}\n\n')
    for cid in [208,221,222,240,253,254]:
        base=BASEMAP[cid]
        f.write(f'{cid:3} / {bytes([cid]).decode("cp1254")}: base={chr(base)} base_xadvance={chars[base]["xadvance"]} yeni_xadvance={newc[cid]["xadvance"]} xoffset={newc[cid]["xoffset"]} yoffset={newc[cid]["yoffset"]}\n')
    f.write('\nNot: Ş/ş govdesi orijinal S/s alfa piksellerinin birebir kopyasidir; yalniz cedilla eklenmistir.\n')
    f.write('İ xadvance=4 ve xoffset=0 olarak orijinal I ile birebir eslestirildi.\n')

with (REPORTS/'EXEFS_TURKCE_KARAKTER_VE_KAYIT_UYARISI_V14.tsv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['offset','ingilizce','v14_turkce','yeni_byte','slot_byte']);w.writerows(patch_rows)

# Scan ASCII-fallback strings known from V13. Must be absent in V14 code.
legacy=[b'Oyku Modu',b'Sure Yarisi',b'Yukleme',b'Kaydi Sil',b'Oyundan Cik',b'Ilk Magara',b'Baslangic Noktasi',b'Caliliklar',b'Kum Bolgesi',b'Mimiga Koyu']
legacy_hits=[x.decode('ascii') for x in legacy if x in code]
assert not legacy_hits, legacy_hits
# Autosave English must be gone at exact slots.
assert b'Do not turn the system off or remove' not in code
assert b'the Nintendo 3DS Game Card' not in code

(REPORTS/'QA_V14_OZET.txt').write_text(textwrap.dedent(f'''\
Cave Story 3D TR V14 - QA Özeti
===============================
- V13 tabanindaki UI atlas/ROMFS düzeltmeleri korundu.
- ExeFS yeniden orijinal code.bin üzerinden CP1254 Türkçe olarak üretildi.
- ASCII kaçışlı menü/mekân dizgeleri taraması: 0 bilinen kalıntı.
- Otomatik kayıt/kart uyarısı İngilizce kalıntısı: 0.
- V10 crash kritik pointer 0x0675BC: 0x{int.from_bytes(code[0x675bc:0x675c0],'little'):08X} (orijinal, temiz).
- IPS yeniden uygulama: code.bin ile byte-byte aynı.
- Font hedef dışı char metrik farkı: {len(non_target_char_diff)}.
- Font hedef dışı kerning seti: birebir aynı ({len(orig_non_target)} çift).
- Font atlasında izin verilen yeni glif alanları dışında piksel farkı: {outside}.
- İ advance: {newc[221]['xadvance']} (orijinal I: {chars[73]['xadvance']}).
- Ş advance: {newc[222]['xadvance']} (orijinal S: {chars[83]['xadvance']}).
- ş advance: {newc[254]['xadvance']} (orijinal s: {chars[115]['xadvance']}).
'''),encoding='utf-8')

# Reproducer tool (copy this builder into package, with note that paths are session-local references)
shutil.copy2('/mnt/data/build_v14.py',TOOLS/'build_v14_reference.py')
(OUT/'V14_SURUM_NOTLARI.txt').write_text(textwrap.dedent('''\
Cave Story 3D TR V14
- Menü/mekân ExeFS metinlerinde gerçek Türkçe karakterler geri getirildi (Öykü, Süre, İlk, Başlangıç, Çalılıklar...).
- Otomatik kayıt / Nintendo 3DS Oyun Kartı uyarısı Türkçeleştirildi.
- Türkçe font altı glif için yeniden tasarlandı: ana harf gövdeleri orijinal piksellerle birebir; metrikler ana harflerle eşleşiyor.
- Özellikle İ xadvance/xoffset I ile, Ş S ile, ş s ile eşleştirildi.
- Diğer font karakterlerinin metrik/kerning davranışına dokunulmadı.
'''),encoding='utf-8')

# Zip + sha
zip_path=Path('/mnt/data/Cave_Story_3D_TR_v14_font_metrik_turkce_ui.zip')
if zip_path.exists(): zip_path.unlink()
subprocess.run(['bash','-lc',f'cd {BASE} && zip -qr {zip_path} {OUT.name}'],check=True)
sha=hashlib.sha256(zip_path.read_bytes()).hexdigest()
sha_path=Path('/mnt/data/Cave_Story_3D_TR_v14_font_metrik_turkce_ui.sha256')
sha_path.write_text(f'{sha}  {zip_path.name}\n',encoding='utf-8')
print('OUT',OUT)
print('ZIP',zip_path)
print('SHA',sha)
print('font kernings',len(orig_kerns),'->',len(new_kerns),'non-target preserved',len(orig_non_target))
print('İ metrics',newc[221])
