from pathlib import Path
from PIL import Image
import shutil, struct, hashlib, subprocess, os, csv, textwrap

V11=Path('/mnt/data/cs3d_v11/Cave_Story_3D_TR_v11_crash_fix_guvenli_exefs')
ORIG=Path('/mnt/data/v10_orig/data')
BASE=Path('/mnt/data/cs3d_v12')
OUT=BASE/'Cave_Story_3D_TR_v12_atlas_uv_fix_aracli'
if OUT.exists(): shutil.rmtree(OUT)
BASE.mkdir(parents=True,exist_ok=True)
shutil.copytree(V11,OUT)
DATA=OUT/'000400000004D200/romfs/data'
TOOLS=OUT/'ARACLAR'; REPORTS=OUT/'RAPORLAR'; PREV=OUT/'ONIZLEMELER'
TOOLS.mkdir(exist_ok=True);REPORTS.mkdir(exist_ok=True);PREV.mkdir(exist_ok=True)

# Exact original UI atlas reset. V10/V11 broad clearing is discarded.
for fn in ['textbox.tga','textbox.pbm','caret.tga','caret.pbm','minimapframe.pbm']:
    shutil.copy2(ORIG/fn,DATA/fn)

# 3x7 compact font. First/last rows usually blank: visible body stays in original glyph source rect.
F={
' ':['000']*7,
'A':['000','010','101','111','101','101','000'],
'B':['000','110','101','110','101','110','000'],
'C':['000','011','100','100','100','011','000'],
'Ç':['010','011','100','100','100','011','010'],
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
'Ö':['101','000','010','101','101','010','000'],
'P':['000','110','101','110','100','100','000'],
'R':['000','110','101','110','101','101','000'],
'S':['000','011','100','010','001','110','000'],
'Ş':['010','011','100','010','001','110','010'],
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
def tw(s,sp=1): return sum(3+sp for _ in s)-sp if s else 0
def draw(setpx,s,x,y,col,sp=1):
    cx=x
    for c in s:
        if c not in F: raise KeyError(c)
        for yy,row in enumerate(F[c]):
            for xx,v in enumerate(row):
                if v=='1':setpx(cx+xx,y+yy,col)
        cx+=3+sp

def center(setpx,s,b,col,sp=1):
    x0,y0,x1,y1=b
    w=tw(s,sp); h=7
    x=x0+max(0,(x1-x0-w)//2); y=y0+max(0,(y1-y0-h)//2)
    draw(setpx,s,x,y,col,sp)
    return (x,y,x+w,y+h)

def read_idx(path):
    raw=bytearray(path.read_bytes()); off=struct.unpack_from('<I',raw,10)[0]; w,h=struct.unpack_from('<ii',raw,18); bpp=struct.unpack_from('<H',raw,28)[0]; H=abs(h); rb=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        sy=H-1-y if h>0 else y; row=raw[off+sy*rb:off+(sy+1)*rb]
        if bpp==4:
            for x in range(w):pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
        elif bpp==1:
            for x in range(w):pix[y][x]=(row[x//8]>>(7-x%8))&1
        else:raise ValueError(bpp)
    return [raw,off,w,h,bpp,rb,pix]
def write_idx(path,info,pix):
    raw,off,w,h,bpp,rb,_=info;H=abs(h)
    for y in range(H):
        dy=H-1-y if h>0 else y;row=bytearray(rb)
        if bpp==4:
            for x,v in enumerate(pix[y]):
                if x%2==0:row[x//2]|=(v&15)<<4
                else:row[x//2]|=v&15
        else:
            for x,v in enumerate(pix[y]):row[x//8]|=(v&1)<<(7-x%8)
        raw[off+dy*rb:off+(dy+1)*rb]=row
    path.write_bytes(raw)

def clear_rgba(im,b,fill=(0,0,0,0)):
    for y in range(b[1],b[3]):
        for x in range(b[0],b[2]):im.putpixel((x,y),fill)
def clear_pix(p,b,fill=0):
    for y in range(b[1],b[3]):
        for x in range(b[0],b[2]):p[y][x]=fill

# IMPORTANT: boxes are the original glyph/text rectangles, not guessed UI rows.
# Decorative hyphens, icons and adjacent sprite pixels are outside these rectangles.
textbox_tga=[
    ('SİLAH',(97,49,128,56),(247,247,234,255)),
    ('ENVANTER',(81,57,143,65),(247,247,234,255)),
    ('HEDEF',(81,65,143,73),(247,247,234,255)),
    ('MAKS',(48,72,71,79),(255,203,0,255)),
    ('PUAN',(81,72,109,80),(247,247,234,255)),
    ('SV',(81,81,92,89),(247,247,234,255)),
    ('HAVA',(124,72,141,80),(180,205,245,255)),
    ('HAVA',(124,80,141,87),(180,205,245,255)),
]
im=Image.open(ORIG/'textbox.tga').convert('RGBA')
allowed_tga=[]
for s,b,col in textbox_tga:
    clear_rgba(im,b);center(lambda x,y,c:im.putpixel((x,y),c),s,b,col,0 if s in ('SİLAH','HAVA') else 1);allowed_tga.append(b)
# YES/NO only text area; keep original plate/border untouched.
yesbox=(164,60,222,68); red=Image.open(ORIG/'textbox.tga').convert('RGBA').getpixel((170,60))
clear_rgba(im,yesbox,red);center(lambda x,y,c:im.putpixel((x,y),c),'EVET/HAYIR',yesbox,(255,255,255,255),1);allowed_tga.append(yesbox)
im.save(DATA/'textbox.tga',format='TGA')

# PBM exact source text rectangles.
textbox_pbm=[
    ('SİLAH',(97,48,132,57),6,0),('ENVANTER',(81,56,143,65),6,1),('HEDEF',(85,64,142,73),6,1),
    ('MAKS',(48,72,71,79),11,1),('PUAN',(81,73,108,80),6,1),('SV',(81,81,95,89),6,1),
    ('HAVA',(123,72,143,80),5,0),('HAVA',(123,80,143,87),5,0),('SÜRÜM',(152,80,207,87),6,1)
]
info=read_idx(ORIG/'textbox.pbm');pix=info[-1];allowed_pbm=[]
for s,b,col,sp in textbox_pbm:
    clear_pix(pix,b,0);center(lambda x,y,c:pix[y].__setitem__(x,c),s,b,col,sp);allowed_pbm.append(b)
# yes/no: preserve red plate, identify original red index at a clean point
redidx=info[-1][60][170];yesb=(162,59,224,69);clear_pix(pix,yesb,redidx);center(lambda x,y,c:pix[y].__setitem__(x,c),'EVET/HAYIR',yesb,6,1);allowed_pbm.append(yesb)
# Footer: exact original text line region only; background underneath is black.
footer=(3,132,239,143);clear_pix(pix,footer,0);center(lambda x,y,c:pix[y].__setitem__(x,c),'ESC:ÇIK  F1:DEVAM  F2:SIFIRLA',footer,6,1);allowed_pbm.append(footer)
write_idx(DATA/'textbox.pbm',info,pix)

# caret: reset original, then only modify narrow source text zones. No neighboring balls/icons are cleared.
caret_entries_tga=[
    ('SEVİYE+',(0,4,55,14),(254,254,254,255),1),('SEVİYE+',(0,20,55,31),(100,114,207,255),1),
    ('SEVİYE-',(0,101,57,111),(255,62,37,255),1),('SEVİYE-',(0,118,57,128),(90,0,0,255),1),
    ('BOŞ!',(107,98,152,108),(255,226,41,255),1),('BOŞ!',(107,112,152,122),(255,62,37,255),1),
    ('ZIPLAMA TUŞUNA BAS!',(1,143,105,153),(254,254,254,255),1),
]
im=Image.open(ORIG/'caret.tga').convert('RGBA');allowed_caret_tga=[]
for s,b,col,sp in caret_entries_tga:
    clear_rgba(im,b);center(lambda x,y,c:im.putpixel((x,y),c),s,b,col,sp);allowed_caret_tga.append(b)
im.save(DATA/'caret.tga',format='TGA')

caret_entries_pbm=[
    ('SEVİYE+',(0,4,55,14),5,1),('SEVİYE+',(0,20,55,31),8,1),
    ('SEVİYE-',(0,101,57,111),12,1),('SEVİYE-',(0,118,57,128),14,1),
    ('BOŞ!',(107,98,152,108),10,1),('BOŞ!',(107,112,152,122),12,1),
    ('ZIPLAMA TUŞUNA BAS!',(1,143,105,153),5,1),
]
info=read_idx(ORIG/'caret.pbm');pix=info[-1];allowed_caret_pbm=[]
for s,b,col,sp in caret_entries_pbm:
    clear_pix(pix,b,0);center(lambda x,y,c:pix[y].__setitem__(x,c),s,b,col,sp);allowed_caret_pbm.append(b)
write_idx(DATA/'caret.pbm',info,pix)

# minimap: exact MAP/INV glyph source rectangles only.
im=Image.open(ORIG/'minimapframe.pbm').convert('RGB');allowed_map=[]
for s,b,col in [('HRT',(210,19,247,30),(255,225,40)),('ENV',(210,28,246,37),(70,255,45))]:
    # preserve black background, clear only old text bbox
    for y in range(b[1],b[3]):
        for x in range(b[0],b[2]):im.putpixel((x,y),(0,0,0))
    center(lambda x,y,c:im.putpixel((x,y),c),s,b,col,1);allowed_map.append(b)
im.save(DATA/'minimapframe.pbm',format='BMP')

# Pixel-difference safety QA: every changed pixel must be within explicitly allowed glyph rectangles.
def in_any(x,y,boxes):return any(x>=b[0] and x<b[2] and y>=b[1] and y<b[3] for b in boxes)
def diff_qa(fn,boxes):
    a=Image.open(ORIG/fn).convert('RGBA');b=Image.open(DATA/fn).convert('RGBA')
    total=outside=0; outside_pts=[]
    for y in range(a.height):
        for x in range(a.width):
            if a.getpixel((x,y))!=b.getpixel((x,y)):
                total+=1
                if not in_any(x,y,boxes):
                    outside+=1
                    if len(outside_pts)<20:outside_pts.append((x,y))
    return total,outside,outside_pts
qa=[]
for fn,boxes in [('textbox.tga',allowed_tga),('textbox.pbm',allowed_pbm),('caret.tga',allowed_caret_tga),('caret.pbm',allowed_caret_pbm),('minimapframe.pbm',allowed_map)]:
    qa.append((fn,*diff_qa(fn,boxes)))
with open(REPORTS/'UI_ATLAS_PIKSEL_GUVENLIK_QA_V12.tsv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['dosya','degisen_piksel','izin_disinda_degisen','ornek'])
    for fn,total,outside,pts in qa:w.writerow([fn,total,outside,str(pts)])
assert all(row[2]==0 for row in qa),qa

# Atlas decision report
with open(REPORTS/'UI_ATLAS_KUTULARI_V12.tsv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['dosya','turkce','orijinal_kaynak_kutusu','neden'])
    for s,b,*_ in textbox_tga:w.writerow(['textbox.tga',s,str(b),'Yalniz orijinal yazi piksel alani; dekoratif cizgi/ikonlara dokunulmaz'])
    w.writerow(['textbox.tga','EVET/HAYIR',str(yesbox),'Kirmizi plakanin sadece yazi bolgesi'])
    for s,b,*_ in caret_entries_tga:w.writerow(['caret.tga',s,str(b),'Orijinal etiket bolgesi; komsu efekt/ikon alani korunur'])
    for s,b,*_ in [('HRT',(210,19,247,30)),('ENV',(210,28,246,37))]:w.writerow(['minimapframe.pbm',s,str(b),'MAP/INV kaynak yazisinin gercek piksel kutusu'])

# ExeFS slot sanity (V11 is kept unchanged for this pass).
code=(OUT/'000400000004D200/exefs/code.bin').read_bytes()
# known pointer values fixed in V11
checks=[(0x675B8,0x001E3260),(0x675BC,0x001E3228)]
with open(REPORTS/'EXEFS_V11_KORUNDU_QA_V12.txt','w',encoding='utf-8') as f:
    for off,exp in checks:
        got=int.from_bytes(code[off:off+4],'little');f.write(f'0x{off:06X}: 0x{got:08X} expected 0x{exp:08X} => {"OK" if got==exp else "HATA"}\n');assert got==exp
    f.write('V12 UI atlas duzeltmesi ExeFS/code.bin dosyasini degistirmedi.\n')

# Create fallback original UI set for A/B test.
fallback=OUT/'KARSILASTIRMA_ORIJINAL_UI'/'000400000004D200'/'romfs'/'data';fallback.mkdir(parents=True,exist_ok=True)
for fn in ['textbox.tga','textbox.pbm','caret.tga','caret.pbm','minimapframe.pbm']:
    shutil.copy2(ORIG/fn,fallback/fn)
(OUT/'KARSILASTIRMA_ORIJINAL_UI'/'README.txt').write_text(
    'Bu klasor yalniz A/B test icindir. V12 varsayilan UI atlaslarinda sorun gorursen buradaki 5 orijinal dosyayi gecici olarak kullan. Boylece sorun atlas kaynakli mi kesinlestirilebilir.\n',encoding='utf-8')

# Previews with source rectangles overlay and plain zooms.
for fn in ['textbox.tga','textbox.pbm','caret.tga','caret.pbm','minimapframe.pbm']:
    im=Image.open(DATA/fn).convert('RGB')
    scale=6 if fn.startswith('textbox') else 4
    im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST).save(PREV/(fn.replace('.','_')+'_v12.png'))

# Side by side original/v12 for textbox/caret
from PIL import ImageDraw
for fn in ['textbox.tga','caret.tga','minimapframe.pbm']:
    a=Image.open(ORIG/fn).convert('RGB');b=Image.open(DATA/fn).convert('RGB');s=3
    aa=a.resize((a.width*s,a.height*s),Image.Resampling.NEAREST);bb=b.resize((b.width*s,b.height*s),Image.Resampling.NEAREST)
    canvas=Image.new('RGB',(aa.width+bb.width,max(aa.height,bb.height)),(30,30,30));canvas.paste(aa,(0,0));canvas.paste(bb,(aa.width,0))
    d=ImageDraw.Draw(canvas);d.text((5,5),'ORIJINAL',fill=(255,255,0));d.text((aa.width+5,5),'V12',fill=(255,255,0))
    canvas.save(PREV/(fn.replace('.','_')+'_karsilastirma_v12.png'))

# Tool source for repeatability
shutil.copy2(Path(__file__),TOOLS/'build_v12_atlas_uv_fix.py')

(REPORTS/'QA_V12_OZET.txt').write_text(textwrap.dedent(f'''\
Cave Story 3D TR V12 - Atlas/UV Yerlesim Duzeltmesi
====================================================

Temel bulgu:
- V10/V11 araclari yazi degistirirken gercek glyph alanindan cok daha buyuk dikdortgenleri temizliyordu.
- Bu, dekoratif cizgileri / komsu sprite piksellerini siliyor ve oyunda bos/kirik UI bolgelerine neden olabiliyordu.

V12:
- textbox.tga/pbm, caret.tga/pbm, minimapframe.pbm ORIJINAL ROMFS atlaslarindan yeniden kuruldu.
- Yalniz orijinal yazi/glyph kaynak kutulari degistirildi.
- Izin verilen kutular disinda degisen piksel: {sum(x[2] for x in qa)}
- ExeFS V11 guvenli crash-fix surumu aynen korundu.
- Karsilastirma icin tamamen orijinal 5 UI atlasi da pakete eklendi.

Kisa etiket tercihleri:
- ARMS -> SILAH (gorselde SİLAH)
- INVENTORY -> ENVANTER
- DESTINATION -> HEDEF
- Points -> PUAN
- Lv -> SV
- AIR -> HAVA
- MAP -> HRT
- INV -> ENV

Testte once varsayilan V12'yi kullan. Eger hala atlas kaynakli bosluk varsa KARSILASTIRMA_ORIJINAL_UI klasorundeki 5 dosyayla A/B test yap.
'''),encoding='utf-8')

(OUT/'V12_SURUM_NOTLARI.txt').write_text('V12: UI atlaslari orijinalden yeniden kuruldu; genis alan silme hatasi kaldirildi. ExeFS V11 crash fix aynen korundu.\n',encoding='utf-8')

# zip + sha
zip_path=Path('/mnt/data/Cave_Story_3D_TR_v12_atlas_uv_fix_aracli.zip')
if zip_path.exists():zip_path.unlink()
subprocess.run(['bash','-lc',f'cd {BASE} && zip -qr {zip_path} {OUT.name}'],check=True)
sha=hashlib.sha256(zip_path.read_bytes()).hexdigest();Path('/mnt/data/Cave_Story_3D_TR_v12_atlas_uv_fix_aracli.sha256').write_text(f'{sha}  {zip_path.name}\n')
print(zip_path);print(sha)
print('QA',qa)
