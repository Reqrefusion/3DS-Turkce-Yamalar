from pathlib import Path
import sys,struct,math,hashlib
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
KIT=Path('/mnt/data/bloodstained_tr_kit');sys.path.insert(0,str(KIT))
from bloodstained_tr_tool import unpack_container,pack_container,parse_osb,decode_osb_rgba4444,encode_osb_rgba4444,OSB_KEY,load_ttb,write_ttb
ROM=Path('/mnt/data/bloodstain_work/romfs')
OUT=Path('/mnt/data/bloodstained_tr_full_v2')
OUTROM=OUT/'luma'/'titles'/'00040000001D3C00'/'romfs'
FONT=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',8)

def rec(raw,h,i): return list(struct.unpack_from('<6I',raw,h[7]+4+i*24))
def vertex_abs(h,i,r): return h[7]+r[2]+((4+24*i)%80)
def node_quad_offsets(raw,h,i):
 r=rec(raw,h,i);a=vertex_abs(h,i,r);return [a+j*80 for j in range(r[4]//4)]
def quad_values(raw,qoff): return [struct.unpack_from('<5f',raw,qoff+k*20) for k in range(4)]
def quad_rect(raw,qoff):
 vs=quad_values(raw,qoff);xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
 return (min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv))
def is_glyph(raw,qoff,tol=.15):
 q=quad_rect(raw,qoff);return abs((q[1]-q[0])-8)<tol and abs((q[3]-q[2])-8)<tol
def clone_overlaps(raw):
 raw=bytearray(raw);h=parse_osb(raw);n=h[9];post=h[7];rs=[rec(raw,h,i) for i in range(n)];ints=[]
 for i,r in enumerate(rs):
  a=vertex_abs(h,i,r);ints.append((a,a+r[4]*20))
 clone=set()
 for i in range(1,n):
  a,b=ints[i]
  if any(max(a,c)<min(b,d) for c,d in ints[:i]): clone.add(i)
 appended=bytearray()
 for i in sorted(clone):
  r=rs[i];a,b=ints[i];vb=bytes(raw[a:b]);shift=(4+24*i)%80;cur=len(raw)+len(appended)-post;rel0=(cur+15)//16*16;appended+=b'\0'*(rel0-cur);appended+=b'\0'*shift;appended+=vb;struct.pack_into('<I',raw,post+4+i*24+8,rel0)
 raw+=appended;struct.pack_into('<I',raw,24,len(raw)-post);return raw

def cell_range(q,w,h):
 x0=int(round(q[4]*w));x1=int(round(q[5]*w));y0=int(round(q[6]*h));y1=int(round(q[7]*h));s=set()
 for cy in range(max(0,y0//8),min(h//8,(y1+7)//8)):
  for cx in range(max(0,x0//8),min(w//8,(x1+7)//8)):s.add((cx,cy))
 return s

def tile_magenta(atlas,q):
 w,h=atlas.size;x0=int(round(q[4]*w));x1=int(round(q[5]*w));y0=int(round(q[6]*h));y1=int(round(q[7]*h));im=atlas.crop((x0,y0,x1,y1)).convert('RGBA');ps=[p for p in im.getdata() if p[3]>40]
 if not ps:return False
 r=sum(p[0] for p in ps)/len(ps);g=sum(p[1] for p in ps)/len(ps);b=sum(p[2] for p in ps)/len(ps);return r>120 and b>60 and r>g*1.5

def draw_cell(atlas,cell,ch,fill):
 x,y=cell[0]*8,cell[1]*8;atlas.paste((0,0,0,0),(x,y,x+8,y+8))
 if ch:
  t=Image.new('RGBA',(8,8),(0,0,0,0));d=ImageDraw.Draw(t);bb=d.textbbox((0,0),ch,font=FONT);tw,th=bb[2]-bb[0],bb[3]-bb[1];d.text(((8-tw)//2-bb[0],(8-th)//2-bb[1]),ch,font=FONT,fill=fill);atlas.alpha_composite(t,(x,y))
def uv(cell,w,h):
 x,y=cell[0]*8,cell[1]*8;return ((x+.02)/w,(x+7.98)/w,(y+.02)/h,(y+7.98)/h)
def set_quad(raw,qoff,x0,x1,y0,y1,u0,u1,v0,v1):
 old=quad_values(raw,qoff);xs=[v[0] for v in old];ys=[v[1] for v in old];us=[v[3] for v in old];vv=[v[4] for v in old];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);umin,umax=min(us),max(us);vmin,vmax=min(vv),max(vv)
 for k,(x,y,z,u0o,v0o) in enumerate(old):
  nx=x0 if abs(x-xmin)<=abs(x-xmax) else x1;ny=y0 if abs(y-ymin)<=abs(y-ymax) else y1;nu=u0 if abs(u0o-umin)<=abs(u0o-umax) else u1;nv=v0 if abs(v0o-vmin)<=abs(v0o-vmax) else v1;struct.pack_into('<5f',raw,qoff+k*20,nx,ny,z,nu,nv)

def patch_staffroll_graphics():
 fn='Staffroll_Text00.osbctr';raw=clone_overlaps(unpack_container(ROM/fn,OSB_KEY));h=parse_osb(raw);atlas=decode_osb_rgba4444(raw);w,hh=atlas.size
 trans={
 0:['YÖNETMEN','SENARYO SORUMLUSU','PLAN'],
 1:['BAŞ KARAKTER GRAFİK','KARAKTER GRAFİK'],
 2:['BAŞ ARKA PLAN GRAFİK','ARKA PLAN GRAFİK','BAŞ ARAYÜZ','ARAYÜZ'],
 3:['BAŞ PROGRAMCI','PROGRAMCI'],4:['BAŞ PROGRAMCI','PROGRAMCI'],5:['BAŞ PROGRAMCI','PROGRAMCI'],6:['PROGRAMCI'],7:['PROGRAMCI'],
 8:['SES TASARIMI','SES MÜHENDİSİ'],9:['YARDIMCI MÜHENDİS','SES EFEKTLERİ'],10:['MÜZİK'],11:['SES YAPIMCISI'],
 12:['YERELLEŞTİRME ŞEFİ','İNGİLİZCE ÇEVİRİ','E-KILAVUZ ÇEVİRİSİ'],13:['KK'],14:['KARAKTER ÇİZERİ','LOGO TASARIMI'],
 15:['Hİ','ÖZEL TEŞEKKÜR'],16:['Hİ','ÖZEL TEŞEKKÜR'],17:['Hİ','ÖZEL TEŞEKKÜR'],18:['YAPIMCI'],
 19:['YAPIM / ORİJİNAL ESER'],20:['YAPIM / ORİJİNAL ESER'],21:['ESER']}
 groups=[]; selected=set()
 for node,texts in trans.items():
  rows=defaultdict(list)
  for qoff in node_quad_offsets(raw,h,node):
   if not is_glyph(raw,qoff):continue
   q=quad_rect(raw,qoff)
   if tile_magenta(atlas,q):rows[round(q[3],2)].append(qoff)
  rowlist=[rows[y] for y in sorted(rows,reverse=True)]
  if len(rowlist)!=len(texts):
   raise RuntimeError(f'node {node}: magenta row count {len(rowlist)} != {len(texts)}')
  for qoffs,text in zip(rowlist,texts):
   if sum(1 for c in text if not c.isspace())>len(qoffs):raise RuntimeError(f'node {node} capacity {len(qoffs)} < {text}')
   groups.append((qoffs,text,(238,0,85,255)));selected.update(qoffs)
 # ALL INTI STAFF is white and must also be localized in the three scrolling variants.
 for node in (15,16,17):
  rows=defaultdict(list)
  for qoff in node_quad_offsets(raw,h,node):
   if not is_glyph(raw,qoff) or qoff in selected:continue
   q=quad_rect(raw,qoff);rows[round(q[3],2)].append(qoff)
  # lowest 12-glyph row corresponds to ALL INTI STAFF.
  cand=[(y,qs) for y,qs in rows.items() if len(qs)==12]
  y,qoffs=min(cand,key=lambda z:z[0]);text='TÜM INTI EKİBİ'
  assert sum(1 for c in text if not c.isspace())<=len(qoffs)
  groups.append((qoffs,text,(255,255,255,255)));selected.update(qoffs)
 # Protect all atlas cells still used by any untouched quad; target-only cells + truly unused cells are free.
 protected=set()
 for i in range(h[9]):
  for qoff in node_quad_offsets(raw,h,i):
   if qoff not in selected:protected |= cell_range(quad_rect(raw,qoff),w,hh)
 avail=[(cx,cy) for cy in range(hh//8) for cx in range(w//8) if (cx,cy) not in protected]
 chars=[]
 for _,txt,_ in groups:
  for c in txt:
   if not c.isspace() and c not in chars:chars.append(c)
 if len(avail)<len(chars)+2:raise RuntimeError(f'free atlas cells {len(avail)} chars {len(chars)}')
 cmap={c:avail[i] for i,c in enumerate(chars)};blank_mag=avail[len(chars)];blank_white=avail[len(chars)+1]
 for c,cell in cmap.items():draw_cell(atlas,cell,c,(255,255,255,255)) # color will be handled by separate color copies below
 # Need separate magenta and white cell sets because same letters occur in both colors.
 # Reallocate from remaining cells for color-specific glyphs.
 idx=len(chars)+2; magchars=[];whitechars=[]
 for _,txt,col in groups:
  dest=magchars if col[0]<250 else whitechars
  for c in txt:
   if not c.isspace() and c not in dest:dest.append(c)
 need=len(magchars)+len(whitechars)+2
 if len(avail)<need:raise RuntimeError(f'free atlas cells {len(avail)} need {need}')
 magmap={c:avail[i] for i,c in enumerate(magchars)};off=len(magchars);whitemap={c:avail[off+i] for i,c in enumerate(whitechars)};off+=len(whitechars);blankm=avail[off];blankw=avail[off+1]
 for c,cell in magmap.items():draw_cell(atlas,cell,c,(238,0,85,255))
 for c,cell in whitemap.items():draw_cell(atlas,cell,c,(255,255,255,255))
 draw_cell(atlas,blankm,'',(238,0,85,255));draw_cell(atlas,blankw,'',(255,255,255,255))
 for qoffs,text,col in groups:
  rects=[quad_rect(raw,q) for q in qoffs];qoffs=[q for _,q in sorted(zip([quad_rect(raw,q)[0] for q in qoffs],qoffs))];rects=[quad_rect(raw,q) for q in qoffs]
  minx=min(r[0] for r in rects);y1=max(r[3] for r in rects);y0=y1-8;x=minx;pos=[]
  mp=magmap if col[0]<250 else whitemap;blank=blankm if col[0]<250 else blankw
  for c in text:
   if not c.isspace():pos.append((c,x,x+8,y0,y1))
   x+=8
  for k,qoff in enumerate(qoffs):
   if k<len(pos):
    c,x0,x1,yy0,yy1=pos[k];u0,u1,v0,v1=uv(mp[c],w,hh);set_quad(raw,qoff,x0,x1,yy0,yy1,u0,u1,v0,v1)
   else:
    r=quad_rect(raw,qoff);u0,u1,v0,v1=uv(blank,w,hh);set_quad(raw,qoff,r[0],r[1],r[2],r[3],u0,u1,v0,v1)
 raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas);out=OUTROM/fn;out.write_bytes(pack_container(bytes(raw),OSB_KEY));vr=unpack_container(out,OSB_KEY);parse_osb(vr);decode_osb_rgba4444(vr);return out

# Fix one remaining visible English loan label in a Turkish menu sentence.
title=load_ttb(OUTROM/'Title.ttb');write_ttb(OUTROM/'Title.ttb',title,{3:'<emoji/Decide> Onayla    Oyundaki patronlarla savaş.'});assert load_ttb(OUTROM/'Title.ttb').text_for_record(3)=='<emoji/Decide> Onayla    Oyundaki patronlarla savaş.'
out=patch_staffroll_graphics();print('patched',out)
# README final status.
readme='''Bloodstained: Curse of the Moon (Nintendo 3DS) - Türkçe Yama v2\nSürüm: Avrupa / CTR-N-BLMP / TitleID 00040000001D3C00\n\nBu sürümde Türkçeleştirilen oyuncuya görünen İngilizce içerik:\n- Menü, sistem, kayıt/yükleme, seçenekler, sonuç ve oyun modu metinleri\n- Açılış hikâye anlatımı ve Nightmare giriş anlatımı\n- Miriam / Alfred / Gebel karşılaşma konuşmaları (typewriter animasyonu dahil)\n- Tutorial/anlatım ekranları ve Ruh Sanatı/yetenek adları\n- Bölüm başlık kartları\n- Ending / Bad End / devam ekranlarındaki anlatım metinleri\n- GAME OVER / STAGE CLEAR / START / CONGRATULATIONS / NOW LOADING / SAVING gibi grafik UI yazıları\n- Jenerikteki görev/rol başlıkları (grafik ve TTB katmanı)\n- Telif/rights metinleri\n\nBilinçli olarak çevrilmeyenler: Bloodstained: Curse of the Moon resmi oyun logosu/adı, INTI CREATES marka logosu, kişi/şirket/özel adları. Bunlar yerelleştirme metni değil özel ad/markadır.\n\nKurulum:\nZIP içindeki luma klasörünü SD kartın köküne birleştirin.\nHedef yol: SD:/luma/titles/00040000001D3C00/romfs/\nLuma3DS LayeredFS / game patching etkin olmalıdır.\n\nDoğrulama:\nÜretilen TTB ve OSBCTR dosyaları tekrar açılıp ayrıştırıldı; OSB texture verileri decode edildi ve görsel önizlemeler kontrol edildi. Gerçek 3DS/emülatör çalışma zamanı bu ortamda test edilemedi. Oyunda kalan bir İngilizce metin veya taşma görürseniz ekran görüntüsü ile bildirin; ilgili kaynak doğrudan düzeltilebilir.\n'''
(OUT/'README_TR.txt').write_text(readme,encoding='utf-8')
# checksums
lines=[]
for p in sorted(OUTROM.iterdir()):
 if p.is_file():lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(OUT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('files',len([p for p in OUTROM.iterdir() if p.is_file()]))
