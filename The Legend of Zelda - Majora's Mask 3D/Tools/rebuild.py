"""Rebuild native MM3D UI textures from clean supplied assets; preserve all other bytes.
Run from any directory: python /path/to/package/Tools/rebuild.py
Requires Pillow, numpy, scipy. An optional C++ compiler speeds up ETC encoding.
"""
from pathlib import Path
import sys, json, shutil, ctypes, subprocess
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont
OUT=Path(__file__).resolve().parents[1]
ROOT=OUT.parent
sys.path.insert(0,str(OUT/'Tools'))
import mm3d_tr_tool_v3 as t
OLD=OUT/'BuildInputs/previous'
SRC=OUT/'BuildInputs/sources'
if not OLD.exists():OLD=ROOT/'work/MM3D_TR_v0.9.9_CLEANBG_R4'
if not SRC.exists():SRC=ROOT/'sources'
for folder in ['Graphics','QA']: (OUT/folder).mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
import etc1_codec
libpath=OUT/'Tools/fast_etc.so'
if not libpath.exists() and shutil.which('g++'):
 subprocess.run(['g++','-O3','-shared','-fPIC',str(OUT/'Tools/fast_etc.cpp'),'-o',str(libpath)],check=True)
if libpath.exists():
 lib=ctypes.CDLL(str(libpath));lib.encode_block.argtypes=[ctypes.POINTER(ctypes.c_uint8)];lib.encode_block.restype=ctypes.c_uint64
 def fast(p):
  a=np.asarray(p,dtype=np.uint8).copy();return int(lib.encode_block(a.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)))).to_bytes(8,'little')
 etc1_codec.encode_block=fast
report={'assets':[], 'labels':[], 'game_tested':False}
assets={}
extracted=OUT/'QA/source_textures';extracted.mkdir(exist_ok=True)
for gar in (SRC/'layout/EU_English').glob('*.gar'):
 for entry in t.Gar2.load(gar).entries:
  if entry.data[:4]==b'ctxb':(extracted/(gar.stem+'__'+entry.path)).write_bytes(entry.data)
for p in extracted.glob('*.ctxb'):
 key=p.name.split('__',1)[1].removesuffix('.ctxb')
 assets[key]={'source':p,'original':t.decode_ctxb_texture(p),'file':p.name,'ops':[]}
p=SRC/'menu/menu/savedata_maintainer/eu/english/guideline_parts00.ctxb'
assets['guideline_parts00']={'source':p,'original':t.decode_ctxb_texture(p),'file':'guideline_parts00.ctxb','ops':[]}
for a in assets.values():a['image']=a['original'].copy()

def label(key,box,text,size=14,mode='transparent',fill=(250,250,250,255),stroke=(25,25,25,255),sw=1,font=FONT,align='center',drawbox=None):
 """Only the supplied text cell may change. Opaque buttons keep their alpha and rim."""
 a=assets[key];im=a['image'];x0,y0,x1,y1=box
 assert 0<=x0<x1<=im.width and 0<=y0<y1<=im.height,(key,box)
 orig=np.array(a['original']);arr=np.array(im)
 if mode=='transparent':arr[y0:y1,x0:x1]=0
 else:
  rgb=orig[y0:y1,x0:x1,:3].astype(float);lum=rgb.mean(2);chroma=rgb.max(2)-rgb.min(2)
  if mode=='stone':mask=lum<90
  else:mask=((lum>165)&(chroma<80))|(rgb.max(2)<48)
  # Reconstruct only glyph pixels from neighboring same-row surface samples.
  # No rectangles are painted over the artwork and alpha is never inpainted.
  l=orig[y0:y1,max(0,x0-4):x0,:3].astype(float)
  r=orig[y0:y1,x1:min(im.width,x1+4),:3].astype(float)
  assert l.size and r.size,(key,box)
  left=np.median(l,axis=1);right=np.median(r,axis=1)
  f=np.linspace(0,1,x1-x0)[None,:,None]
  bg=np.clip(left[:,None,:]*(1-f)+right[:,None,:]*f,0,255).astype('uint8')
  if mode!='stone':mask |= lum < bg.mean(2)*0.82
  mask=ndimage.binary_dilation(mask,iterations=2)
  region=arr[y0:y1,x0:x1];region[mask,:3]=bg[mask]
 im=Image.fromarray(arr)
 bx=drawbox or box;bw=bx[2]-bx[0];bh=bx[3]-bx[1];scale=4
 # Fit both width and height before rasterization; leave one pixel of sampling space.
 for fs in range(size*scale,5*scale-1,-1):
  fnt=ImageFont.truetype(font,fs);bb=fnt.getbbox(text,stroke_width=sw*scale)
  if bb[2]-bb[0]<=(bw-1)*scale and bb[3]-bb[1]<=(bh-1)*scale:break
 assert bb[2]-bb[0]<=bw*scale and bb[3]-bb[1]<=bh*scale,(key,text,box)
 tile=Image.new('RGBA',(bw*scale,bh*scale));d=ImageDraw.Draw(tile)
 tw,th=bb[2]-bb[0],bb[3]-bb[1]
 xx=(bw*scale-tw)/2-bb[0] if align=='center' else -bb[0]+scale/2
 yy=(bh*scale-th)/2-bb[1]
 d.text((round(xx),round(yy)),text,font=fnt,fill=fill,stroke_fill=stroke,stroke_width=sw*scale)
 tile=tile.resize((bw,bh),Image.Resampling.LANCZOS)
 im.alpha_composite(tile,(bx[0],bx[1]));a['image']=im
 a['ops'].append(list(box));a['ops'].append(list(bx))
 report['labels'].append({'asset':key,'text':text,'clear_cell':box,'draw_cell':bx,'font_size':fs/scale,'mode':mode})

def reuse(key,box):
 a=assets[key];p=OLD/'Graphics/PNG_UI'/(a['file']+'.png')
 old=Image.open(p).convert('RGBA');a['image'].paste(old.crop(box),box);a['ops'].append(list(box))

def clear(key,box):
 a=assets[key];a['image'].paste((0,0,0,0),box);a['ops'].append(list(box))

# Logo and decorative elements remain the unmodified source pixels.
for b,txt in [((428,11,476,29),'Hayır'),((429,59,476,77),'Evet'),((423,107,483,126),'İptal'),((425,155,483,175),'Sil'),((326,199,367,214),'Geri')]:
 label('guideline_parts00',b,txt,14 if txt!='Geri' else 10,'button')

k='menu_file_select_parts00'
for b,txt,sz in [((368,11,437,32),'Başla',18),((409,48,487,69),'Seçenekler',14),((445,84,497,104),'Kopyala',13),((446,117,497,138),'Sil',14)]:label(k,b,txt,sz,'button')
label(k,(430,149,481,169),'MASKELER',10)
for b,txt in [((244,180,284,209),'1.'),((286,180,326,209),'2.'),((328,180,377,209),'Son')]:label(k,b,txt,18)

k='btn_return'
label(k,(12,47,52,61),'Geri',11,'button')
label(k,(68,47,118,61),'İptal',11,'button')

k='menu_popup_parts00'
for b,txt in [((58,9,93,26),'Evet'),((172,9,222,26),'Sil'),((62,45,91,62),'Hayır'),((161,44,232,62),'Kullanma'),((174,79,222,98),'İptal'),((154,152,237,172),'Üzerine Yaz')]:label(k,b,txt,13,'button')
for b,txt in [((5,114,73,134),'Adın?'),((4,138,104,158),'Dosyayı Sil'),((4,163,96,183),'Dosya Kopyala'),((4,187,106,207),'Dosya Seç'),((22,210,126,232),'İpucu Videosu'),((22,234,126,255),'İpucu Fotoğrafı')]:label(k,b,txt,13,align='left')

k='menu_option_parts00'
for y0,y1,txt in [(0,17,'L-Hedefleme'),(17,34,'Birinci Şahıs'),(34,50,'Hareket Kontrolü'),(50,67,'Yüzme Kontrolü'),(67,83,'Circle Pad Pro'),(83,96,'Serbest Kamera')]:label(k,(0,y0,142,y1),txt,13,sw=0,font=REG,align='left')
for i,txt in enumerate(['Basılı Tut','Değiştir','Normal','Y Ekseni Ters','X Ekseni Ters','İkisi Ters','Kullan','Kullanma','Kapalı','Açık']):
 label(k,(167,i*16,255,min(160,(i+1)*16)),txt,12,sw=0,font=REG)
for b,txt in [((17,100,62,119),'Sayfa 1'),((89,100,140,119),'Sayfa 2'),((30,188,82,207),'Sayfa 2'),((123,188,179,207),'Sayfa 1')]:label(k,b,txt,12,'button')
label(k,(9,227,214,249),"Circle Pad Pro'yu Kalibre Et",13,'stone')
k='menu_option_parts01'
label(k,(0,0,123,16),'Ses Ayarı',13,sw=0,font=REG,align='left')
for b,txt in [((10,16,67,32),'Kısık'),((87,16,151,32),'Normal'),((170,16,229,32),'Yüksek')]:label(k,b,txt,13,sw=0,font=REG)

k='menu_hint_movie_parts00'
label(k,(466,23,506,37),'Sonraki',9,'button')
label(k,(388,62,422,79),'Sayfa',10)
label(k,(458,64,506,82),'Bitti!',12,fill=(255,255,255,255),stroke=(0,130,0,255))
label('menu_hint_movie_parts01',(0,0,64,18),'Anladım!',12,fill=(255,255,255,255),stroke=(0,130,0,255))

k='menu_item_parts00'
for b,txt in [((143,5,190,24),'Eşyalar'),((140,38,194,57),'Maskeler'),((153,70,202,90),'Eşyalar'),((151,105,207,124),'Maskeler')]:label(k,b,txt,13,'button')
k='menu_collect_parts00'
label(k,(415,34,481,57),'Seçenekler',13,'button')
label(k,(390,233,492,255),'Resim Yok',15)
k='menu_map_parts00'
label(k,(81,21,130,36),'Onayla',10,'button')
# Floor notation is localized within each original glyph cell.
for i,txt in enumerate(['1K','2K','3K','4K','B1','B2']):label(k,(143,i*17,169,min(103,(i+1)*17)),txt,15)
for i,txt in enumerate(['1K','2K','3K','4K','B1','B2']):label(k,(183,i*16,207,min(98,(i+1)*16)),txt,11,fill=(20,20,10,255),sw=0)

k='menu_quest_list_parts00'
label(k,(247,0,291,18),'Yeni!',12,fill=(255,255,255,255),stroke=(180,10,0,255))
label(k,(247,20,291,39),'Yeni!',12,fill=(255,255,180,255),stroke=(80,190,110,255))
label(k,(455,114,511,128),'Program',9,'button')
k='menu_schedule_parts00'
for b,txt in [((286,0,319,17),'Yeni!'),((265,89,301,109),'Yeni!')]:label(k,b,txt,12,fill=(255,255,255,255),stroke=(160,20,0,255) if b[1]==0 else (100,190,110,255))
for b,txt in [((41,25,76,45),'1. Gün'),((154,25,194,45),'2. Gün'),((263,25,310,45),'Son Gün')]:label(k,b,txt,13,'button')
label(k,(420,40,452,54),'Ayarla',10,'button')
label(k,(38,112,87,129),'Kaldır',11,'button')
label(k,(389,114,426,131),'Atla',11,'button')
label(k,(12,157,51,173),'Alarm',11,'button')
label(k,(208,156,248,173),'Olaylar',11,'button')
for b,txt in [((287,202,320,220),'1.'),((287,220,320,238),'2.'),((287,238,327,256),'Son')]:label(k,b,txt,15)

k='hud_patrs00_action_text'
for i,txt in enumerate(['Tatl','Alarm','İpucu']):label(k,(257,i*16,306,(i+1)*16),txt,12,align='left')
cols=[['Saldır','İncele','Bariyer','Geri','Aç','Zıpla','Seç','Dal','Hızlan'],['Fırlat','Yuvarlan','Tırman','Bırak','Aşağı','Kaydet','Konuş','Sonraki','Tut'],['İptal','Kaldır','Sar','Bilgi','Uç','Çek','Patlat','Dans Et','Yürü'],['Top Ol','Yüzeye Çık','Yüz','Yumruk','Yere Vur','Kancala','Ateş Et','Çek','İlerle'],['Dal','Dur']]
ys=[94,112,130,148,166,185,203,221,240,256]
for col,words in enumerate(cols):
 for i,txt in enumerate(words):label(k,(col*64,ys[i],col*64+63,ys[i+1]),txt,13)
for b,txt in [((358,34,399,51),'Ekipman'),((412,33,450,51),'Harita'),((365,132,410,149),'Maskeler'),((374,163,421,181),'Eşyalar')]:label(k,b,txt,11,'button')
label(k,(355,190,430,214),'Harita Yok',14)
label(k,(443,143,489,165),'Bak',13)
label(k,(440,191,489,214),'Geri',13)

k='menu_common_parts00'
for b,txt in [((0,34,144,56),'Çift Zaman Ezgisi'),((143,33,211,57),'Görüntüler'),((23,58,126,80),'Program'),((23,81,140,104),'Olay Notları'),((0,106,49,128),'Harita'),((143,58,194,80),'Ekipman'),((143,81,205,104),'Maskeler'),((143,106,197,128),'Eşyalar'),((289,58,373,80),'Seçenekler'),((289,81,423,104),'Nereye Uçalım?'),((289,106,350,128),'Alarm')]:label(k,b,txt,14,align='left')
clear('menu_common_parts01',(0,0,128,32))
for b,txt in [((4,0,35,28),'1.'),((42,0,79,28),'2.'),((83,0,127,28),'Son')]:label('menu_common_parts01',b,txt,16)
k='parts'
for b,txt in [((20,79,96,96),'Tüm Gün'),((17,96,178,112),'İkinci Günün Şafağı'),((19,112,178,128),'Son Günün Şafağı')]:label(k,b,txt,13,sw=0,font=REG)

k='world_map_base00'
# The map's labels are separate UV cells; preserve its icons and parchment.
clear(k,(0,0,410,171));clear(k,(410,0,494,89));clear(k,(0,177,180,256));clear(k,(213,193,286,256))
groups=[
 ['Termina Haritası','Büyük Körfez Kıyısı','Çiftlik','Gorman Pisti','Süt Yolu','Korsan Kalesi','Ikana Kanyonu','Kasaba ve Ova',"Ikana’nın Eski Kalesi"],
 ['Saat Kasabası','Güney Bataklığı','Şelale Ormanı','Dağ Köyü','Romani Çiftliği','Ikana Mezarlığı','Deku Sarayı','Süt Yolu','Güney Bataklığı'],
 ['Termina Ovası','Gizemli Orman','Kar Zirvesi','Goron Köyü','Zora Burnu','Taş Kule']]
for col,words in enumerate(groups):
 for i,txt in enumerate(words):
  left,right=[(0,142),(143,277),(278,409)][col]
  label(k,(left,i*19,right,(i+1)*19),txt,13)
for i,txt in enumerate(['Deniz','Kanyon','Dağ','Bataklık']):label(k,(411,i*21,493,(i+1)*21),txt,15)
for i,txt in enumerate(['Şelale Ormanı Tapınağı','Kar Zirvesi Tapınağı','Büyük Körfez Tapınağı','Taş Kule Tapınağı']):label(k,(0,179+i*19,177,198+i*19),txt,13)
for b,txt in [((214,204,284,221),'Uzaklaştır'),((214,221,284,237),'Yakınlaştır'),((214,237,284,255),'Seç')]:label(k,b,txt,12,align='left')

# Preserve already translated standalone lettering; reset its surroundings to source.
reuse('logo_countdown',(0,50,128,105))
reuse('logo_perfect_parts00',(0,0,256,64))
reuse('menu_startup_parts00',(0,0,256,90))
assets['menu_startup_parts00']['image'].paste(assets['menu_startup_parts00']['original'].crop((28,67,48,85)),(28,67))

romfs=OUT/'0004000000125600/romfs';romfs.mkdir(parents=True,exist_ok=True)
# Full source archives retain their entry tables, nontexture entries, and untouched data.
for gar in (SRC/'layout/EU_English').glob('*.gar'):
 g=t.Gar2.load(gar);raw=bytearray(g.raw)
 for e in g.entries:
  if e.data[:4]!=b'ctxb':continue
  key=Path(e.path).stem;a=assets[key]
  if not a['ops']:continue
  png=OUT/'Graphics'/(a['file']+'.png');a['image'].save(png)
  dest=OUT/'QA'/a['file'];result=t.ctxb_inject_png(a['source'],png,dest)
  raw[e.data_offset:e.data_offset+e.size]=dest.read_bytes()
  a['built']=dest;a['encode']=result
 dest=romfs/'layout/EU_English'/gar.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
# Retain the original patch's ending translation and direct day-title text.
ending=OLD/'0004000000125600/romfs/layout/EU_English/Joker.Main.Ending.gar'
shutil.copy2(ending,romfs/'layout/EU_English'/ending.name)
for src in (OLD/'0004000000125600/romfs/menu/daytelop/eu-en').glob('*.ctxb'):
 dest=romfs/'menu/daytelop/eu-en'/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
a=assets['guideline_parts00'];p=OUT/'Graphics/guideline_parts00.ctxb.png';a['image'].save(p)
dest=romfs/'menu/savedata_maintainer/eu/english/guideline_parts00.ctxb';dest.parent.mkdir(parents=True,exist_ok=True)
a['encode']=t.ctxb_inject_png(a['source'],p,dest);a['built']=dest
p=romfs/'message/eu/eue.gmsg';p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OLD/'0004000000125600/romfs/message/eu/eue.gmsg',p)

# Validate actual final decoded data, not just the source PNGs.
for key,a in assets.items():
 if not a.get('built'):continue
 dec=t.decode_ctxb_texture(a['built']);dec.save(OUT/'QA'/(a['file']+'.decoded.png'))
 base=np.array(a['original']);want=np.array(a['image']);actual=np.array(dec)
 changed=np.any(base!=want,axis=2);allowed=np.zeros(changed.shape,bool)
 for x0,y0,x1,y1 in a['ops']:allowed[y0:y1,x0:x1]=1
 assert not np.any(changed & ~allowed),key
 _,_,_,_,tex=t.parse_ctxb(a['source']);fmt=tex[0].format_name
 # ETC compression changes whole 4x4 blocks; every other block must remain byte-exact.
 if fmt.startswith('ETC'):
  protected=~np.repeat(np.repeat(changed.reshape(base.shape[0]//4,4,base.shape[1]//4,4).any(axis=(1,3)),4,axis=0),4,axis=1)
 else:protected=~changed
 assert np.array_equal(base[protected],actual[protected]),key
 if key=='guideline_parts00':assert np.array_equal(base[:,:260],actual[:,:260]),'Logo changed'
 report['assets'].append({'asset':key,'format':fmt,'changed_pixels_before_encoding':int(changed.sum()),'protected_pixels_exact':int(protected.sum()),'source_size':a['source'].stat().st_size,'output_size':a['built'].stat().st_size,'ops':a['ops'],'encode':a['encode']})
 print(key,fmt,len(a['ops'])//2,'labels; protected pixels:',int(protected.sum()),flush=True)
g=t.GmsgFile.load(p);assert g.rebuild()==p.read_bytes()
report.update({'gmsg_records':g.count,'gmsg_preserved_exact':p.read_bytes()==(OLD/'0004000000125600/romfs/message/eu/eue.gmsg').read_bytes(),'logo_pixels_exact':True})
(OUT/'QA/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('DONE',len(report['assets']),len(report['labels']))
