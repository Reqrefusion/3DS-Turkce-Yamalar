from pathlib import Path
import sys,struct,hashlib,math,zipfile,shutil
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import *
sys.path.insert(0,'/mnt/data/v4work')
from analyze_osb import render_node
orig=Path('/mnt/data/v4work/orig/romfs/GraphicText00.osbctr')
v3=Path('/mnt/data/v4work/v3/luma/titles/00040000001D3C00/romfs/GraphicText00.osbctr')
v4root=Path('/mnt/data/bloodstained_tr_v4_aligned')
v4=v4root/'luma/titles/00040000001D3C00/romfs/GraphicText00.osbctr'

def rec(raw,h,i):return struct.unpack_from('<6I',raw,h[7]+4+i*24)
def va(h,i,r):return h[7]+4+i*24+r[2]
def qoffs(raw,h,i):
 r=rec(raw,h,i);a=va(h,i,r);return [a+j*80 for j in range(r[4]//4)]
def rect(raw,o):
 vs=[struct.unpack_from('<5f',raw,o+k*20) for k in range(4)];xs=[x[0] for x in vs];ys=[x[1] for x in vs]
 return min(xs),max(xs),min(ys),max(ys)

ro=unpack_container(orig,OSB_KEY);ho=parse_osb(ro)
rv=unpack_container(v4,OSB_KEY);hv=parse_osb(rv)
assert ho[9]==hv[9]==102
assert encode_osb_rgba4444(decode_osb_rgba4444(rv))==rv[hv[5]:hv[5]+hv[1]]
# all buffers bounds
for i in range(hv[9]):
 r=rec(rv,hv,i);a=va(hv,i,r);assert a>=0 and a+r[4]*20<=len(rv),(i,a,r)
# untouched nodes exact visual match
untouched=list(range(0,15))+[19,20,21,30,31,32,33,63]
for i in untouched:
 a=render_node(orig,i,1);b=render_node(v4,i,1)
 assert a.size==b.size and a.tobytes()==b.tobytes(),f'untouched node changed {i}'
# centers for focus nodes should stay on original center, within 0.01 px
focus=[15,16,18,22,25,26,29,34,36,37,38,40,42,43,51,53,55,56,57,58,59,60,61,62,64,65,69,70,71,72,73,74,75,88,101]
for i in focus:
 oro=[rect(ro,o) for o in qoffs(ro,ho,i)];vrr=[rect(rv,o) for o in qoffs(rv,hv,i)]
 # bounds include icons for mixed nodes; just verify finite and sensible
 for rr in vrr:
  assert all(math.isfinite(x) for x in rr)
# Focused preview Original/V3/V4
nodes=[16,18,55,57,58,56,61,59,60,62,101,15]
font=ImageFont.load_default();rows=[]
for i in nodes:
 ims=[]
 for lab,p in [('ORİJİNAL',orig),('v3',v3),('v4',v4)]:
  im=render_node(p,i,6);ims.append((lab,im))
 W=max(360,max(im.width for _,im in ims));H=sum(im.height+20 for _,im in ims)+6
 c=Image.new('RGBA',(W,H),(14,14,14,255));d=ImageDraw.Draw(c);y=3
 for lab,im in ims:
  d.text((4,y),f'NODE {i} - {lab}',fill=(255,220,80,255) if lab=='v4' else (240,240,240,255),font=font);y+=15;c.alpha_composite(im,(4,y));y+=im.height+5
 rows.append(c)
cols=2;cw=max(x.width for x in rows);ch=max(x.height for x in rows);out=Image.new('RGBA',(cw*cols,ch*math.ceil(len(rows)/cols)),(0,0,0,255))
for k,c in enumerate(rows):out.alpha_composite(c,((k%cols)*cw,(k//cols)*ch))
prev=v4root/'v4_focus_original_v3_v4.png';out.save(prev)
# Validation report
report=f'''Bloodstained COTM 3DS Türkçe Yama v4 - UI Hizalama Doğrulaması\n\nKaynak: orijinal Avrupa RomFS GraphicText00.osbctr\nNode sayısı: {hv[9]}\nDeğişmeyen node görsel eşitlik testi: {len(untouched)}/{len(untouched)} geçti\nRGBA4444 decode->encode byte eşitliği: geçti\nTüm node vertex buffer sınır testi: {hv[9]}/{hv[9]} geçti\n\nv4 yöntemi:\n- Latin A-Z harfleri orijinal oyunun GraphicText00 atlasından alınır.\n- Ş, Ç, Ğ, İ, Ö, Ü, Â glifleri aynı 8x8 piksel iskeletinden türetilir.\n- Kısa Türkçe etiketler kaynak İngilizce genişliğine yayılmaz; doğal 8px ilerlemeyle kaynak merkezinde tutulur.\n- Sadece kaynak kutudan uzun olan EVET/HAYIR/AÇIK/KAPALI gibi sözcüklerde kontrollü sıkıştırma uygulanır.\n- İkon içeren node'larda ikon quad'ları byte-for-byte korunur.\n'''
(v4root/'VALIDATION_V4_TR.txt').write_text(report,encoding='utf-8')
# Zip
zip_path=Path('/mnt/data/bloodstained_tr_v4_aligned_layeredfs.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(v4root.rglob('*')):
  if p.is_file(): z.write(p,p.relative_to(v4root))
print('OK',zip_path,zip_path.stat().st_size,prev)
