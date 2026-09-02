from pathlib import Path
from PIL import Image
import shutil, subprocess, hashlib, struct, csv, re, os, textwrap

V9=Path('/mnt/data/cs3d_v9/Cave_Story_3D_TR_v9_derin_test_aracli')
V7=next(Path('/mnt/data/v10_v7src').glob('Cave_Story_3D_TR_v7*'))
ORIG=Path('/mnt/data/v10_orig/data')
EXEFS_ORIG=Path('/mnt/data/cs3d_exefs/exefs')
BASE=Path('/mnt/data/cs3d_v10')
OUT=BASE/'Cave_Story_3D_TR_v10_exefs_ui_duzeltme_aracli'
if OUT.exists(): shutil.rmtree(OUT)
BASE.mkdir(parents=True, exist_ok=True)
shutil.copytree(V9,OUT)
DATA=OUT/'000400000004D200/romfs/data'
TOOLS=OUT/'ARACLAR'; REPORTS=OUT/'RAPORLAR'; PREV=OUT/'ONIZLEMELER'
REPORTS.mkdir(exist_ok=True); PREV.mkdir(exist_ok=True); TOOLS.mkdir(exist_ok=True)

# Restore all SJS from V7 (contains MNA), then apply V9 compatibility/layout passes.
v7data=V7/'000400000004D200/romfs/data'
for p in v7data.rglob('*.sjs'):
    rel=p.relative_to(v7data); dst=DATA/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst)
subprocess.run(['python',str(OUT/'ARACLAR/font_compatibility_cleanup_v9.py'),'--data',str(DATA)],check=True,capture_output=True,text=True)
subprocess.run(['python',str(OUT/'ARACLAR/manual_layout_fixes_v9.py'),'--data',str(DATA),'--report',str(REPORTS/'SATIR_MANUEL_DUZELTMELERI_V10.tsv')],check=True,capture_output=True,text=True)

# --- sprite-safe 3x7 UI font ---
F={
' ':['000']*7,
'A':['000','010','101','111','101','101','000'],
'B':['000','110','101','110','101','110','000'],
'C':['000','011','100','100','100','011','000'],
'Ç':['011','100','100','100','011','010','100'],
'D':['000','110','101','101','101','110','000'],
'E':['000','111','100','110','100','111','000'],
'F':['000','111','100','110','100','100','000'],
'H':['000','101','101','111','101','101','000'],
'I':['000','111','010','010','010','111','000'],
'İ':['010','000','111','010','010','111','000'],
'K':['000','101','110','100','110','101','000'],
'L':['000','100','100','100','100','111','000'],
'M':['000','101','111','111','101','101','000'],
'N':['000','101','111','111','111','101','000'],
'O':['000','010','101','101','101','010','000'],
'P':['000','110','101','110','100','100','000'],
'R':['000','110','101','110','101','101','000'],
'S':['000','011','100','010','001','110','000'],
'Ş':['011','100','010','001','110','010','100'],
'T':['000','111','010','010','010','010','000'],
'U':['000','101','101','101','101','111','000'],
'Ü':['101','000','101','101','101','111','000'],
'V':['000','101','101','101','101','010','000'],
'Y':['000','101','101','010','010','010','000'],
'Z':['000','111','001','010','100','111','000'],
'+':['000','000','010','111','010','000','000'],
'-':['000','000','000','111','000','000','000'],
'.':['000','000','000','000','000','010','000'],
'/':['000','001','001','010','100','100','000'],
'!':['000','010','010','010','000','010','000'],
':':['000','000','010','000','010','000','000'],
'0':['000','010','101','101','101','010','000'],
'1':['000','010','110','010','010','111','000'],
'2':['000','110','001','010','100','111','000'],
'3':['000','110','001','010','001','110','000'],
'4':['000','101','101','111','001','001','000'],
'5':['000','111','100','110','001','110','000'],
'6':['000','011','100','110','101','010','000'],
'7':['000','111','001','010','010','010','000'],
'8':['000','010','101','010','101','010','000'],
'9':['000','010','101','011','001','110','000'],
}
def tw(s,sp=1): return sum(len(F[c][0])+sp for c in s)-sp if s else 0
def draw(setpx,s,x,y,col,sp=1):
    cx=x
    for c in s:
        pat=F[c]
        for yy,row in enumerate(pat):
            for xx,v in enumerate(row):
                if v=='1': setpx(cx+xx,y+yy,col)
        cx += len(pat[0])+sp

def center(setpx,s,box,col,sp=1):
    x0,y0,x1,y1=box; x=x0+(x1-x0-tw(s,sp))//2; y=y0+(y1-y0-7)//2; draw(setpx,s,x,y,col,sp)

def read_idx(path):
    raw=bytearray(path.read_bytes()); off=struct.unpack_from('<I',raw,10)[0]; w,h=struct.unpack_from('<ii',raw,18); bpp=struct.unpack_from('<H',raw,28)[0]; H=abs(h); rb=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        sy=H-1-y if h>0 else y; row=raw[off+sy*rb:off+(sy+1)*rb]
        if bpp==4:
            for x in range(w):pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
        elif bpp==1:
            for x in range(w):pix[y][x]=(row[x//8]>>(7-x%8))&1
        else: raise ValueError(bpp)
    return [raw,off,w,h,bpp,rb,pix]
def write_idx(path,info,pix):
    raw,off,w,h,bpp,rb,_=info;H=abs(h)
    for y in range(H):
        dy=H-1-y if h>0 else y; row=bytearray(rb)
        if bpp==4:
            for x,v in enumerate(pix[y]):
                if x%2==0:row[x//2]|=(v&15)<<4
                else:row[x//2]|=v&15
        else:
            for x,v in enumerate(pix[y]):row[x//8]|=(v&1)<<(7-x%8)
        raw[off+dy*rb:off+(dy+1)*rb]=row
    path.write_bytes(raw)
def clear_rgba(im,b,fill=(0,0,0,0)):
    x0,y0,x1,y1=b
    for y in range(y0,y1):
        for x in range(x0,x1):im.putpixel((x,y),fill)
def clear_pix(p,b,fill=0):
    x0,y0,x1,y1=b
    for y in range(y0,y1):
        for x in range(x0,x1):p[y][x]=fill

# textbox TGA from original; every translated label stays INSIDE original 7px sprite crop.
im=Image.open(ORIG/'textbox.tga').convert('RGBA')
white=(247,247,234,255);yellow=(255,203,0,255);blue=(180,205,245,255)
labels=[((0,49,28,56),'BOSS',white),((80,49,116,56),'SİLAH',white),((80,57,148,64),'ENVANTER',white),((80,65,150,72),'HEDEF',white),((48,73,74,80),'MAKS',yellow),((80,73,120,80),'PUAN',white),((80,81,96,88),'SVY',white),((124,73,148,80),'HAVA',blue),((124,81,148,88),'HAVA',blue)]

clear_boxes=[(0,47,30,57),(80,47,151,57),(80,56,151,64),(80,64,151,72),(48,72,75,80),(80,72,123,80),(80,80,100,88),(122,72,151,88)]
for cb in clear_boxes: clear_rgba(im,cb)
for b,s,c in labels: center(lambda x,y,col:im.putpixel((x,y),col),s,b,c,1)
# yes/no plate
red=im.getpixel((180,62));b=(163,56,226,70);clear_rgba(im,b,red);center(lambda x,y,col:im.putpixel((x,y),col),'EVET/HAYIR',b,white,1)
im.save(DATA/'textbox.tga',format='TGA')

# textbox PBM
info=read_idx(ORIG/'textbox.pbm');pix=info[-1]
labels_p=[((0,49,28,56),'BOSS',6),((80,49,116,56),'SİLAH',6),((80,57,148,64),'ENVANTER',6),((80,65,150,72),'HEDEF',6),((48,73,74,80),'MAKS',11),((80,73,120,80),'PUAN',6),((80,81,96,88),'SVY',6),((124,73,148,80),'HAVA',5),((124,81,148,88),'HAVA',5),((154,81,222,88),'SÜRÜM',6)]

for cb in clear_boxes: clear_pix(pix,cb,0)
clear_pix(pix,(154,80,223,89),0)
for b,s,c in labels_p:center(lambda x,y,col:pix[y].__setitem__(x,col),s,b,c,1)
b=(163,56,226,70);clear_pix(pix,b,8);center(lambda x,y,col:pix[y].__setitem__(x,col),'EVET/HAYIR',b,6,1)
# Pause footer exact atlas row, compact to fit.
footer=(0,131,244,144);clear_pix(pix,footer,0);center(lambda x,y,col:pix[y].__setitem__(x,col),'ESC:ÇIK / F1:DEVAM / F2:SIFIRLA',footer,6,1)
write_idx(DATA/'textbox.pbm',info,pix)

# caret TGA/PBM sprite-safe
for ext in ['tga','pbm']:
    if ext=='tga':
        im=Image.open(ORIG/'caret.tga').convert('RGBA')
        entries=[((0,5,57,12),'SEVİYE+',(254,254,254,255)),((0,21,57,28),'SEVİYE+',(100,114,207,255)),((0,101,57,108),'SEVİYE-',(255,62,37,255)),((0,118,57,125),'SEVİYE-',(90,0,0,255)),((107,99,151,106),'BOŞ!',(255,226,41,255)),((107,112,151,119),'BOŞ!',(255,62,37,255)),((0,145,106,152),'ZIPLAMA TUŞUNA BAS!',(254,254,254,255))]
        
        for cb in [(0,3,57,17),(0,19,57,31),(0,99,57,111),(0,117,57,129),(107,96,151,111),(107,111,151,125),(0,143,108,155)]: clear_rgba(im,cb)
        for b,s,c in entries:center(lambda x,y,col:im.putpixel((x,y),col),s,b,c,1)
        im.save(DATA/'caret.tga',format='TGA')
    else:
        info=read_idx(ORIG/'caret.pbm');pix=info[-1]
        entries=[((0,5,57,12),'SEVİYE+',5),((0,21,57,28),'SEVİYE+',8),((0,101,57,108),'SEVİYE-',12),((0,118,57,125),'SEVİYE-',14),((107,99,151,106),'BOŞ!',10),((107,112,151,119),'BOŞ!',12),((0,145,106,152),'ZIPLAMA TUŞUNA BAS!',5)]
        
        for cb in [(0,3,57,17),(0,19,57,31),(0,99,57,111),(0,117,57,129),(107,96,151,111),(107,111,151,125),(0,143,108,155)]: clear_pix(pix,cb,0)
        for b,s,c in entries:center(lambda x,y,col:pix[y].__setitem__(x,col),s,b,c,1)
        write_idx(DATA/'caret.pbm',info,pix)

# minimapframe from original, compact labels inside old MAP/INV area.
im=Image.open(ORIG/'minimapframe.pbm').convert('RGB')
for b,s,c in [((220,18,250,27),'HRT',(255,225,40)),((220,28,250,37),'ENV',(70,255,45))]:
    x0,y0,x1,y1=b
    for y in range(y0,y1):
        for x in range(x0,x1):im.putpixel((x,y),(0,0,0))
    center(lambda x,y,col:im.putpixel((x,y),col),s,b,c,1)
im.save(DATA/'minimapframe.pbm',format='BMP')

# Previews
for fn in ['textbox.tga','textbox.pbm','caret.tga','caret.pbm','minimapframe.pbm','font_batang_0.tga','loading.pbm','title.tga']:
    im=Image.open(DATA/fn); scale=5 if im.width<350 else 3; im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST).save(PREV/(fn.replace('.','_')+'_v10.png'))

# Create sprite-safe atlas QA report, measure all replacement text widths against box widths.
rows=[]
for b,s,c in labels+[(x[0],x[1],x[2]) for x in []]: pass
all_ui=[('textbox',b,s) for b,s,_ in labels]+[('textbox', (163,56,226,70),'EVET/HAYIR')]+[('caret',b,s) for b,s,_ in [((0,5,57,12),'SEVİYE+',0),((0,21,57,28),'SEVİYE+',0),((0,101,57,108),'SEVİYE-',0),((0,118,57,125),'SEVİYE-',0),((107,99,151,106),'BOŞ!',0),((107,112,151,119),'BOŞ!',0),((0,145,106,152),'ZIPLAMA TUŞUNA BAS!',0)]]
with open(REPORTS/'UI_SPRITE_KIRPILMA_QA_V10.tsv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['atlas','metin','kutu','metin_px','kutu_px','durum'])
    for atlas,b,s in all_ui:
        width=tw(s,1);boxw=b[2]-b[0];w.writerow([atlas,s,str(b),width,boxw,'OK' if width<=boxw else 'TASMA'])

# --- ExeFS code.bin patch ---
code_orig=(EXEFS_ORIG/'code.bin').read_bytes(); code=bytearray(code_orig); patch_rows=[]
def patch_at(off, old, new, cap=None, category='UI'):
    oldb=old.encode('ascii'); newb=new.encode('cp1254')
    assert code_orig[off:off+len(oldb)]==oldb,(hex(off),old,code_orig[off:off+len(oldb)])
    if cap is None: cap=len(oldb)
    if len(newb)>cap: raise ValueError((old,new,len(newb),cap))
    # zero complete capacity so stale suffixes cannot remain; never exceed documented field/slot.
    code[off:off+cap]=b'\0'*cap; code[off:off+len(newb)]=newb
    patch_rows.append((f'0x{off:06X}',category,old,new,len(newb),cap))

# UI/menu strings (slot capacities measured to next fixed string/data).
ui=[
(0x60a6c,'Loading','Yükleme',9),
(0x67588,'Story Mode','Öykü Modu',15),(0x67598,'Time Attack','Süre Yarışı',11),(0x675a8,'Classic Mode','Klasik Mod',23),
(0x675c0,'Yes','E',3),(0x675c4,'No','H',3),(0x675c8,'Easy Mode','Kolay Mod',11),
(0x675d4,'Best choice for first-time players.','İlk kez oynayanlar için iyi seçim.',35),
(0x675f8,'Normal Mode','Normal Mod',11),(0x67604,'For players familiar with Cave Story.','Cave Story deneyimi olanlar için.',39),
(0x6762c,'Hard Mode','Zor Mod',11),(0x67638,'Not recommended for first-time players.','İlk kez oynayanlara önerilmez.',39),
(0x679b0,'New Game','Yeni Oyun',11),
(0xc0418,'Story Mode','Öykü Modu',11),(0xc0424,'Time Attack','Süre Yarışı',11),(0xc0430,'Classic Mode','Klasik Mod',15),
(0xc0440,'Clear Slot','Kaydı Sil',11),(0xc044c,'Are you sure?','Emin misin?',15),(0xc045c,'Yes','E',3),(0xc0460,'No','H',2),
(0xc0918,'Continue Game','Devam Et',15),(0xc0928,'Exit Game','Oyundan Çık',11),(0xc0934,'Yes','E',3),(0xc0938,'No','H',2),
(0x9df1c,'All unsaved data will be lost, are','Kaydedilmemiş veriler silinecek.',35),(0x9df44,'you sure you want to quit?','Çıkmak istediğine emin mi?',27),
(0xd00c8,'The save data could not be accessed.','Kayıt verilerine erişilemedi.',36),
]
for r in ui: patch_at(*r,category='UI/menü')

# Stage display-name table: 108 entries, English field is 64 bytes at 0xE332C + n*0x10C.
trans={
'Nothing':'Hiçlik',"Arthur's House":"Arthur'un Evi",'Egg Corridor':'Yumurta Koridoru','Egg No.00':'Yumurta No.00','Egg No.06':'Yumurta No.06','Egg Observation Room':'Yumurta Gözlem Odası','Bushlands':'Çalılıklar',"Santa's House":"Santa'nın Evi", "Chako's House":"Chako'nun Evi",'Labyrinth I':'Labirent I','Sand Zone':'Kum Bölgesi','Mimiga Village':'Mimiga Köyü','First Cave':'İlk Mağara','Start Point':'Başlangıç Noktası','Shack':'Kulübe','Reservoir':'Rezervuar','Cemetery':'Mezarlık','Yamashita Farm':'Yamashita Çiftliği','Shelter':'Sığınak','Assembly Hall':'Toplantı Salonu','Save Point':'Kayıt Noktası','Side Room':'Yan Oda',"Cthulhu's Abode":"Cthulhu'nun Evi",'Egg No. 01':'Yumurta No. 01','Power Supply Room':'Güç Kaynağı Odası','Execution Chamber':'İnfaz Odası','Gum':'Sakız','Sand Zone Residence':'Kum Bölgesi Evi','Bushlands Hut':'Çalılıklar Kulübesi','Main Artery':'Ana Damar','Small Room':'Küçük Oda',"Jenka's House":"Jenka'nın Evi",'Deserted House':'Terk Edilmiş Ev','Warehouse':'Depo','Labyrinth H':'Labirent H','Labyrinth W':'Labirent W','Camp':'Kamp','Clinic Ruins':'Klinik Harabeleri','Labyrinth Shop':'Labirent Dükkânı','Labyrinth B':'Labirent B','Boulder Chamber':'Kaya Odası','Labyrinth M':'Labirent M','Dark Place':'Karanlık Yer','Core':'Çekirdek','Waterway':'Su Yolu','Egg Corridor?':'Yumurta Koridoru?',"Cthulhu's Abode?":"Cthulhu'nun Evi?",'Egg Observation Room?':'Yumurta Gözlem Odası?','Egg No. 00':'Yumurta No. 00','Outer Wall':'Dış Duvar','Storehouse':'Ambar','Plantation':'Plantasyon','Jail No. 1':'Hapishane No. 1','Hideout':'Saklanma Yeri','Rest Area':'Dinlenme Alanı','Teleporter':'Işınlayıcı','Jail No. 2':'Hapishane No. 2','Balcony':'Balkon','Final Cave':'Son Mağara','Throne Room':'Taht Odası',"The King's Table":'Kralın Sofrası','Prefab Building':'Prefabrik Bina','Last Cave (Hidden)':'Son Mağara (Gizli)','Black Space':'Karanlık Boşluk','Little House':'Küçük Ev','Fall':'Düşüş','Waterway Cabin':'Su Yolu Kulübesi','Blood Stained Sanctuary - B1':'Kanlı Kutsal Alan - B1','Blood Stained Sanctuary - B2':'Kanlı Kutsal Alan - B2','Blood Stained Sanctuary - B3':'Kanlı Kutsal Alan - B3','Storage':'Depo','Passage?':'Geçit?','Statue Chamber':'Heykel Odası','Seal Chamber':'Mühür Odası','Corridor':'Koridor','Hermit Gunsmith':'Münzevi Silah Ustası','Clock Room':'Saat Odası','Inner Wall':'İç Duvar','Small Grave':'Küçük Mezar','Falling Tower':'Çöken Kule','Egg Corridor Detour':'Yumurta Koridoru Yan Yol'
}
base=0xe332c; step=0x10c; loc_count=0
for n in range(108):
    off=base+n*step; end=code_orig.find(b'\0',off,off+64); oldb=code_orig[off:end]
    if not oldb: continue
    try:old=oldb.decode('ascii')
    except: continue
    new=trans.get(old)
    if new:
        patch_at(off,old,new,63,category='Mekân adı');loc_count+=1

# Save patched code.bin and full exefs helper copy.
EXEFS_DIR=OUT/'000400000004D200/exefs';EXEFS_DIR.mkdir(parents=True,exist_ok=True)
(EXEFS_DIR/'code.bin').write_bytes(code)
# keep originals of non-code ExeFS for users who rebuild a full ExeFS tree
for fn in ['banner.bin','icon.bin','logo.bin']: shutil.copy2(EXEFS_ORIG/fn,EXEFS_DIR/fn)

# IPS patch generator against supplied original code.bin.
def make_ips(orig,new,path):
    out=bytearray(b'PATCH');i=0;L=len(orig)
    while i<L:
        if orig[i]==new[i]: i+=1; continue
        start=i;buf=bytearray()
        while i<L and orig[i]!=new[i] and len(buf)<65535:
            buf.append(new[i]);i+=1
        out += start.to_bytes(3,'big')+len(buf).to_bytes(2,'big')+buf
    out += b'EOF';path.write_bytes(out)
make_ips(code_orig,bytes(code),OUT/'000400000004D200/code.ips')

# patch report
with open(REPORTS/'EXEFS_TURKCE_YAMA_V10.tsv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['offset','kategori','ingilizce','turkce','yeni_byte','alan_byte']);w.writerows(patch_rows)

# Verify patched map table contains no listed English display strings where translation exists.
remaining=[]
for n in range(108):
    off=base+n*step; end=bytes(code).find(b'\0',off,off+64); raw=bytes(code)[off:end]
    try:s=raw.decode('cp1254')
    except:s='?'
    if s in trans: remaining.append((n,hex(off),s))

# SJS structural QA against original, exact command sequence INCLUDING MNA.
cmd_re=re.compile(rb'<[A-Z0-9]{3}(?:[^<\r\n]*)?')
def cmds(b): return [m.group(0)[:4] for m in cmd_re.finditer(b)]
# Better command names only, avoids text payload false positives.
def cmdnames(b): return re.findall(rb'<([A-Z0-9]{3})',b)
struct=[]; bad=0;mna=0
for p in sorted(ORIG.rglob('*.sjs')):
    rel=p.relative_to(ORIG); q=DATA/rel
    if not q.exists():continue
    a=cmdnames(p.read_bytes()); c=cmdnames(q.read_bytes()); mna+=c.count(b'MNA')
    ok=a==c;bad+=not ok;struct.append((str(rel),len(a),len(c),'OK' if ok else 'FARK'))
with open(REPORTS/'SJS_YAPI_QA_V10.tsv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['dosya','orijinal_komut','v10_komut','durum']);w.writerows(struct)

# Font unsupported-byte scan: visible SJS cp1254 IDs must exist in fnt.
fnt=(DATA/'font_batang.fnt').read_text('latin1'); ids={int(x) for x in re.findall(r'char id=(\d+)',fnt)}
unsupported=[]
for p in DATA.rglob('*.sjs'):
    if p.name in {'head.sjs','credit.sjs'}:continue
    b=p.read_bytes()
    for x in set(b):
        if x>=32 and x not in ids and x not in (10,13):unsupported.append((str(p.relative_to(DATA)),x))

# Code QA: untouched size; each patch old field replaced and no stage translated entry remains English.
qa=textwrap.dedent(f'''\
Cave Story 3D TR V10 - Derin Test QA
====================================
ExeFS code.bin boyutu: {len(code)} (orijinal {len(code_orig)})
ExeFS yama kaydi: {len(patch_rows)}
Mekan adi yamasi: {loc_count} / 108 tablo girdisi (bos/özel girdiler hariç)
Cevirisi tanimli olup Ingilizce kalan mekan girdisi: {len(remaining)}
SJS komut yapisi farki: {bad}
SJS icindeki MNA komutu: {mna} (yer adlari artik Turkce ExeFS tablosundan gelecek)
Fontta tanimsiz gorunur byte bulgusu: {len(unsupported)}
UI atlas yaklaşımı: tum yeniden cizilen kucuk etiketler orijinal 7px sprite kutularinin icinde.

Önemli düzeltmeler:
- SİLAH artık ARMS'in sabit UV kutusuna sığan kompakt glifle çiziliyor; "SİL" diye kırpılmıyor.
- ENVANTER/HEDEF/PUAN/SVY/HAVA dikey koordinatları orijinal atlas satırlarına döndürüldü.
- "SV" yerine "SVY" kullanıldı; V harfinin U gibi okunması azaltıldı.
- ExeFS'teki New Game/Continue Game/Exit Game/Loading/mod seçimleri Türkçeleştirildi.
- 108 elemanlı motor mekân tablosunun görünen İngilizce adları CP1254 Türkçe olarak yamanıyor.
''')
(REPORTS/'QA_V10_OZET.txt').write_text(qa,encoding='utf-8')

# README/install notes
(OUT/'V10_TEST_NOTLARI.txt').write_text(textwrap.dedent('''\
Cave Story 3D TR V10 - ExeFS + UI kırpılma düzeltme test sürümü

Bu sürüm ROMFS yanında ExeFS yaması da içerir.
- 000400000004D200/romfs/... : metin/font/görsel yaması
- 000400000004D200/code.ips  : orijinal code.bin üzerine IPS yaması (Luma tipi kullanım için)
- 000400000004D200/exefs/code.bin : doğrudan yeniden paketleme/Citra ExeFS değişimi için yamalı code.bin

Özellikle test edilmesi gerekenler:
1. Envanter ekranında SİLAH / ENVANTER / HEDEF / PUAN / SVY / HAVA etiketlerinin tamamı görünmeli.
2. Daha önce "SİL" gibi görünen silah başlığı artık tam SİLAH olmalı.
3. Yeni oyun / devam / çıkış / yükleme ve mod seçimi metinleri Türkçe olmalı.
4. Haritaya girerken motorun gösterdiği mekan adları Türkçe olmalı.
5. Ğ İ Ş ğ ı ş ana metin fontunda diğer harflerle aynı kalınlıkta görünmeli.

Not: code.ips ile yamalı code.bin aynı değişiklikleri temsil eder; ikisini aynı anda uygulama.
'''),encoding='utf-8')

# Put tools for new fixes.
shutil.copy2('/mnt/data/build_v10.py',TOOLS/'build_v10_reference.py')
# Extract ExeFS patcher standalone from reports? provide simple verifier.
(TOOLS/'exefs_patch_verify_v10.py').write_text(textwrap.dedent('''\
#!/usr/bin/env python3
from pathlib import Path
import hashlib
base=Path(__file__).resolve().parents[1]
p=base/'000400000004D200/exefs/code.bin'
print('code.bin',p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
print('code.ips',(base/'000400000004D200/code.ips').stat().st_size)
'''),encoding='utf-8')

# Make combined UI preview sheet
ims=[]
for fn in ['textbox_tga_v10.png','textbox_pbm_v10.png','caret_tga_v10.png','minimapframe_pbm_v10.png','font_batang_0_tga_v10.png','loading_pbm_v10.png']:
    p=PREV/fn
    if p.exists():ims.append((fn,Image.open(p).convert('RGB')))
if ims:
    W=max(im.width for _,im in ims); H=sum(im.height+30 for _,im in ims)
    sheet=Image.new('RGB',(W,H),'white');y=0
    from PIL import ImageDraw
    d=ImageDraw.Draw(sheet)
    for name,im in ims:
        d.text((5,y+5),name,fill='black');y+=25;sheet.paste(im,(0,y));y+=im.height+5
    sheet.save(PREV/'UI_TOPLU_V10.png')

# Zip + sha
zip_path=Path('/mnt/data/Cave_Story_3D_TR_v10_exefs_ui_duzeltme_aracli.zip')
if zip_path.exists():zip_path.unlink()
subprocess.run(['bash','-lc',f'cd {BASE} && zip -qr {zip_path} {OUT.name}'],check=True)
sha=hashlib.sha256(zip_path.read_bytes()).hexdigest();Path('/mnt/data/Cave_Story_3D_TR_v10_exefs_ui_duzeltme_aracli.sha256').write_text(f'{sha}  {zip_path.name}\n')
print('OUT',OUT);print('ZIP',zip_path);print('SHA',sha);print(qa)
