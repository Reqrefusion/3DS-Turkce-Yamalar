from pathlib import Path
from PIL import Image, ImageDraw
import shutil, struct, re, csv, hashlib, subprocess, os, textwrap
import numpy as np

V14=Path('/mnt/data/cs3d_v14/Cave_Story_3D_TR_v14_font_metrik_turkce_ui')
ORIG=Path('/mnt/data/v10_orig/data')
BASE=Path('/mnt/data/cs3d_v15')
OUT=BASE/'Cave_Story_3D_TR_v15_font_spacing_yesno_fix'
if OUT.exists(): shutil.rmtree(OUT)
BASE.mkdir(parents=True, exist_ok=True)
shutil.copytree(V14, OUT)
DATA=OUT/'000400000004D200/romfs/data'
TOOLS=OUT/'ARACLAR'; REPORTS=OUT/'RAPORLAR'; PREV=OUT/'ONIZLEMELER'
for p in [TOOLS,REPORTS,PREV]: p.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# YES/NO: preserve original option centers and original slash exactly.
# ------------------------------------------------------------------
FONT5={
'E':["11111","10000","10000","11110","10000","10000","11111"],
'V':["10001","10001","10001","10001","10001","01010","00100"],
'T':["11111","00100","00100","00100","00100","00100","00100"],
'H':["10001","10001","10001","11111","10001","10001","10001"],
'A':["01110","10001","10001","11111","10001","10001","10001"],
'Y':["10001","10001","01010","00100","00100","00100","00100"],
'I':["11111","00100","00100","00100","00100","00100","11111"],
'R':["11110","10001","10001","11110","10100","10010","10001"],
}
def text_width(s, spacing=1):
    return len(s)*5 + max(0,len(s)-1)*spacing

def draw5(setpx,s,x,y,col,spacing=1):
    cx=x
    for ch in s:
        for yy,row in enumerate(FONT5[ch]):
            for xx,v in enumerate(row):
                if v=='1': setpx(cx+xx,y+yy,col)
        cx += 5+spacing

# TGA: start from V14 but restore entire choice label area from original first.
v14_tga=Image.open(DATA/'textbox.tga').convert('RGBA')
orig_tga=Image.open(ORIG/'textbox.tga').convert('RGBA')
# restore original option area incl slash
v14_tga.paste(orig_tga.crop((158,57,236,71)),(158,57))
red=orig_tga.getpixel((170,60)); white=(255,255,255,255)
# measured original ink boxes: YES 164..187, NO 204..220, y61..66; slash 192..196 unchanged.
yes_center=(164+187)/2
no_center=(204+220)/2
w_e=text_width('EVET'); w_h=text_width('HAYIR')
x_e=164  # preserve original YES left edge; center differs by only -0.5px
x_h=198  # exact original NO center
# Clear choice-specific regions only, never the slash zone.
for box in [(160,59,190,69),(198,59,235,69)]:
    for y in range(box[1],box[3]):
        for x in range(box[0],box[2]): v14_tga.putpixel((x,y),red)
draw5(lambda x,y,c:v14_tga.putpixel((x,y),c),'EVET',x_e,60,white,1)
draw5(lambda x,y,c:v14_tga.putpixel((x,y),c),'HAYIR',x_h,60,white,1)
v14_tga.save(DATA/'textbox.tga',format='TGA')

# indexed BMP helpers preserve original 4-bit structure.
def read_idx(path):
    raw=bytearray(path.read_bytes()); off=struct.unpack_from('<I',raw,10)[0]
    w,h=struct.unpack_from('<ii',raw,18); bpp=struct.unpack_from('<H',raw,28)[0]
    H=abs(h); rb=((w*bpp+31)//32)*4
    pix=[[0]*w for _ in range(H)]
    for y in range(H):
        sy=H-1-y if h>0 else y; row=raw[off+sy*rb:off+(sy+1)*rb]
        if bpp==4:
            for x in range(w): pix[y][x]=(row[x//2]>>4)&15 if x%2==0 else row[x//2]&15
        elif bpp==1:
            for x in range(w): pix[y][x]=(row[x//8]>>(7-x%8))&1
        else: raise ValueError(bpp)
    return [raw,off,w,h,bpp,rb,pix]
def write_idx(path,info,pix):
    raw,off,w,h,bpp,rb,_=info; H=abs(h)
    for y in range(H):
        dy=H-1-y if h>0 else y; row=bytearray(rb)
        if bpp==4:
            for x,v in enumerate(pix[y]):
                if x%2==0: row[x//2]|=(v&15)<<4
                else: row[x//2]|=v&15
        else:
            for x,v in enumerate(pix[y]): row[x//8]|=(v&1)<<(7-x%8)
        raw[off+dy*rb:off+(dy+1)*rb]=row
    path.write_bytes(raw)

cur_info=read_idx(DATA/'textbox.pbm'); cur=cur_info[-1]
org_info=read_idx(ORIG/'textbox.pbm'); org=org_info[-1]
# restore option area from original indexed pixels (slash included exactly)
for y in range(57,72):
    for x in range(157,237): cur[y][x]=org[y][x]
redidx=org[58][170]; whiteidx=org[60][163]  # clean plate index 8; old sample hit antialias index 7
yes_center_p=(163+184)/2
no_center_p=(204+218)/2
x_ep=163 # preserve original YES left edge; center differs by only +0.5px
x_hp=197 # exact original NO center
for box in [(159,58,190,70),(197,58,236,70)]:
    for y in range(box[1],box[3]):
        for x in range(box[0],box[2]): cur[y][x]=redidx
draw5(lambda x,y,c:cur[y].__setitem__(x,c),'EVET',x_ep,60,whiteidx,1)
draw5(lambda x,y,c:cur[y].__setitem__(x,c),'HAYIR',x_hp,60,whiteidx,1)
write_idx(DATA/'textbox.pbm',cur_info,cur)

# ------------------------------------------------------------------
# FONT metric/side-bearing/kerning audit. No global font rewrite.
# ------------------------------------------------------------------
fnt=(DATA/'font_batang.fnt').read_text(encoding='latin1')
font_img=Image.open(DATA/'font_batang_0.tga').convert('RGBA')
orig_fnt=(ORIG/'font_batang.fnt').read_text(encoding='latin1')
orig_img=Image.open(ORIG/'font_batang_0.tga').convert('RGBA')

def parse_chars(t):
    out={}
    for ln in t.splitlines():
        if ln.startswith('char id='):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',ln)}; out[d['id']]=d
    return out
def parse_kerns(t):
    out=[]
    for ln in t.splitlines():
        if ln.startswith('kerning first='):
            d={k:int(v) for k,v in re.findall(r'(first|second|amount)=(-?\d+)',ln)}
            out.append((d['first'],d['second'],d['amount']))
    return out
chars=parse_chars(fnt); ochars=parse_chars(orig_fnt); kerns=parse_kerns(fnt); okerns=parse_kerns(orig_fnt)
BASEMAP={208:71,221:73,222:83,240:103,253:105,254:115}
name={208:'Ğ',221:'İ',222:'Ş',240:'ğ',253:'ı',254:'ş'}
rows=[]

def ink_metrics(img,d):
    a=np.array(img.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height'])))[:,:,3]
    yy,xx=np.where(a>8)
    return (d['xoffset']+int(xx.min()), d['xoffset']+int(xx.max())+1)

for cid,bid in BASEMAP.items():
    d=chars[cid]; b=ochars[bid]
    il,ir=ink_metrics(font_img,d); bl,br=ink_metrics(orig_img,b)
    target_pairs={(f,s,a) for f,s,a in kerns if f==cid or s==cid}
    # V14 mirrors base kerning in every applicable combination, including
    # target-target pairs (e.g. original I-g -> İ-ğ). Rebuild that expected set.
    base_to_target={71:208,73:221,83:222,103:240,105:253,115:254}
    expected_all=set()
    for f,s,a in okerns:
        if f in BASEMAP or s in BASEMAP:
            # Legacy target-id pairs in the original file are intentionally ignored.
            continue
        fs=[f]+([base_to_target[f]] if f in base_to_target else [])
        ss=[s]+([base_to_target[s]] if s in base_to_target else [])
        for ff in fs:
            for ss2 in ss:
                expected_all.add((ff,ss2,a))
    expected={x for x in expected_all if x[0]==cid or x[1]==cid}
    missing=sorted(expected-target_pairs); extra=sorted(target_pairs-expected)
    assert d['xadvance']==b['xadvance'],(cid,'xadvance')
    assert d['xoffset']==b['xoffset'],(cid,'xoffset')
    assert (il,ir)==(bl,br),(cid,'sidebearing',(il,ir),(bl,br))
    assert not missing and not extra,(cid,missing,extra)
    rows.append([name[cid],chr(bid),d['xadvance'],d['xoffset'],d['yoffset'],il,d['xadvance']-ir,len(expected),'OK'])

# Body alpha equality checks: accents excluded; body must match source exactly.
def crop_alpha(img,d):
    return np.array(img.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height'])))[:,:,3]
checks=[]
# target slice, base full/slice
mapping_slices={208:(slice(3,13),71,slice(None)),221:(slice(3,13),73,slice(None)),222:(slice(0,9),83,slice(0,9)),240:(slice(3,13),103,slice(None)),253:(slice(0,8),105,slice(2,10)),254:(slice(0,7),115,slice(0,7))}
for cid,(ts,bid,bs) in mapping_slices.items():
    ta=crop_alpha(font_img,chars[cid])[ts]
    ba=crop_alpha(orig_img,ochars[bid])[bs]
    eq=bool(np.array_equal(ta,ba)); assert eq,(cid,'body pixel mismatch')
    checks.append((name[cid],chr(bid),eq))

with (REPORTS/'FONT_ADVANCE_XOFFSET_QA_V15.tsv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t'); w.writerow(['turkce','baz','xadvance','xoffset','yoffset','sol_ink_px','sag_bosluk_px','klon_kerning_cifti','sonuc']);w.writerows(rows)

# Yes/no geometry report exact center preservation.
actual_center_e=x_e+(w_e-1)/2; actual_center_h=x_h+(w_h-1)/2
actual_center_ep=x_ep+(w_e-1)/2; actual_center_hp=x_hp+(w_h-1)/2
with (REPORTS/'EVET_HAYIR_YERLESIM_QA_V15.txt').open('w',encoding='utf-8') as f:
    f.write('Cave Story 3D TR V15 - EVET/HAYIR Yerleşim QA\n================================================\n')
    f.write(f'TGA orijinal YES ink: x=164..187 merkez={yes_center:.1f}\n')
    f.write(f'TGA V15 EVET: x={x_e}..{x_e+w_e-1} merkez={actual_center_e:.1f}\n')
    f.write(f'TGA orijinal NO ink: x=204..220 merkez={no_center:.1f}\n')
    f.write(f'TGA V15 HAYIR: x={x_h}..{x_h+w_h-1} merkez={actual_center_h:.1f}\n')
    f.write('TGA slash: orijinal piksel verisi korunur (x=192..196).\n\n')
    f.write(f'PBM orijinal YES ink: x=163..184 merkez={yes_center_p:.1f}\n')
    f.write(f'PBM V15 EVET: x={x_ep}..{x_ep+w_e-1} merkez={actual_center_ep:.1f}\n')
    f.write(f'PBM orijinal NO ink: x=204..218 merkez={no_center_p:.1f}\n')
    f.write(f'PBM V15 HAYIR: x={x_hp}..{x_hp+w_h-1} merkez={actual_center_hp:.1f}\n')
    f.write('PBM slash: orijinal piksel verisi korunur.\n')
    f.write('\nKarar: kelimeler tek blok halinde ortalanmadi; her secenegin kendi orijinal merkezine ayri ayri hizalandi.\n')

# Verify slash pixels byte-for-pixel with original after final output.
out_tga=Image.open(DATA/'textbox.tga').convert('RGBA')
for y in range(59,69):
    for x in range(191,198):
        assert out_tga.getpixel((x,y))==orig_tga.getpixel((x,y)),('TGA slash changed',x,y)
out_info=read_idx(DATA/'textbox.pbm'); outpix=out_info[-1]
for y in range(58,70):
    for x in range(193,197):
        assert outpix[y][x]==org[y][x],('PBM slash changed',x,y)

# Other V14 files must be unchanged: hash compare except textbox.tga/pbm + reports/tool metadata.
changed=[]
for p in (V14/'000400000004D200').rglob('*'):
    if not p.is_file(): continue
    rel=p.relative_to(V14)
    q=OUT/rel
    if q.exists() and hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(q.read_bytes()).digest(): changed.append(str(rel))
assert sorted(changed)==sorted(['000400000004D200/romfs/data/textbox.pbm','000400000004D200/romfs/data/textbox.tga']),changed

# Build visual previews: native x6 and annotated center lines.
for fn in ['textbox.tga','textbox.pbm']:
    im=Image.open(DATA/fn).convert('RGBA')
    crop=im.crop((154,52,240,75)) if fn.endswith('tga') else im.crop((154,52,240,74))
    crop.resize((crop.width*8,crop.height*8),Image.Resampling.NEAREST).convert('RGB').save(PREV/(fn.replace('.','_')+'_EVET_HAYIR_V15.png'))

# Font preview rendered from actual BMFont atlas/metrics with advance guides.
def render_sample(text, filename):
    k={(f,s):a for f,s,a in kerns}
    bs=text.encode('cp1254')
    W=20; prev=None
    for c in bs:
        if prev is not None: W+=k.get((prev,c),0)
        W+=chars[c]['xadvance']; prev=c
    can=Image.new('RGBA',(W+20,34),(24,24,30,255)); d=ImageDraw.Draw(can); x=10; prev=None
    for c in bs:
        if prev is not None:x+=k.get((prev,c),0)
        cd=chars[c]
        # advance guide
        d.line((x,1,x,31),fill=(70,70,80,255))
        gl=font_img.crop((cd['x'],cd['y'],cd['x']+cd['width'],cd['y']+cd['height']))
        can.alpha_composite(gl,(x+cd['xoffset'],4+cd['yoffset']))
        x+=cd['xadvance'];prev=c
    d.line((x,1,x,31),fill=(100,100,110,255))
    can.resize((can.width*5,can.height*5),Image.Resampling.NEAREST).convert('RGB').save(PREV/filename)
render_sample('IİI İİ IŞIK ŞİŞE şişe ışık','FONT_ADVANCE_REHBER_V15.png')
render_sample('SŞS sşs GĞG gğg iıi','FONT_GOVDE_KARSILASTIRMA_V15.png')

# Tool copies for repeatability.
tool=(TOOLS/'v15_font_yesno_guard.py')
tool.write_text(Path('/mnt/data/build_v15.py').read_text(encoding='utf-8'),encoding='utf-8')

(REPORTS/'QA_V15_OZET.txt').write_text(textwrap.dedent(f'''\
Cave Story 3D TR V15 - QA Özeti
================================
- V14 oyun metni, ExeFS ve font atlası korunmuştur.
- Bu sürümde yalnız textbox.tga ve textbox.pbm EVET/HAYIR yerleşimi değiştirilmiştir.
- EVET ve HAYIR tek blok olarak ortalanmaz; orijinal YES/NO seçim merkezleri ayrı ayrı korunur.
- Ayırıcı '/' orijinal atlas pikseli olarak değiştirilmeden korunur.
- Font xadvance/xoffset doğrulaması: 6/6 Türkçe karakter OK.
- Font yan boşluk (ink side-bearing) doğrulaması: 6/6 baz harfle birebir.
- Baz gövde alfa pikselleri: 6/6 birebir.
- Baz karakterden klonlanan kerning çiftleri: eksik 0 / fazla 0.
- V14'e göre oyun dosyası değişikliği: yalnız textbox.tga + textbox.pbm.

TGA seçenek merkezleri:
  YES {yes_center:.1f} -> EVET {actual_center_e:.1f}
  NO  {no_center:.1f} -> HAYIR {actual_center_h:.1f}
PBM seçenek merkezleri:
  YES {yes_center_p:.1f} -> EVET {actual_center_ep:.1f}
  NO  {no_center_p:.1f} -> HAYIR {actual_center_hp:.1f}
'''),encoding='utf-8')

(OUT/'V15_SURUM_NOTLARI.txt').write_text('V15: Font advance/xoffset/yan bosluk/kerning kesin QA + EVET/HAYIR secim merkezi hizalama duzeltmesi.\n',encoding='utf-8')

# zip + sha
zip_path=Path('/mnt/data/Cave_Story_3D_TR_v15_font_spacing_yesno_fix.zip')
if zip_path.exists(): zip_path.unlink()
subprocess.run(['bash','-lc',f'cd {BASE} && zip -qr {zip_path} {OUT.name}'],check=True)
sha=hashlib.sha256(zip_path.read_bytes()).hexdigest()
Path('/mnt/data/Cave_Story_3D_TR_v15_font_spacing_yesno_fix.sha256').write_text(f'{sha}  {zip_path.name}\n',encoding='utf-8')
print(zip_path)
print(sha)
print(rows)
print('TGA',yes_center,actual_center_e,no_center,actual_center_h,'PBM',yes_center_p,actual_center_ep,no_center_p,actual_center_hp)
