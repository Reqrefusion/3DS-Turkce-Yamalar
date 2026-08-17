from pathlib import Path
import sys,struct,hashlib,collections
from PIL import Image
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,pack_container,parse_osb,decode_osb_rgba4444,encode_osb_rgba4444,OSB_KEY
ORIG=Path('/mnt/data/v4work/orig/romfs')
OUT=Path('/mnt/data/bloodstained_tr_v5_complete/luma/titles/00040000001D3C00/romfs')

def rec(raw,h,i): return struct.unpack_from('<6I',raw,h[7]+4+i*24)
def qoffs(raw,h,i):
 r=rec(raw,h,i);a=h[7]+4+i*24+r[2];return [a+j*80 for j in range(r[4]//4)]
def qrect(raw,o):
 vs=[struct.unpack_from('<5f',raw,o+k*20) for k in range(4)];xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
 return min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv)
def tile_for_quad(atlas,r):
 aw,ah=atlas.size;x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
 return atlas.crop((x0,y0,x1,y1)).resize((8,8),Image.Resampling.NEAREST)
def thash(im):return hashlib.sha1(im.convert('RGBA').tobytes()).hexdigest()

# Recover native 8x8 glyph masks from GraphicText00.
p=ORIG/'GraphicText00.osbctr';gr=unpack_container(p,OSB_KEY);gh=parse_osb(gr);ga=decode_osb_rgba4444(gr)
source={15:'PRESSANYBUTTON',16:'GAMESTART',17:'BOSSRUSH',18:'OPTIONS',21:'KEYCONFIG',22:'VIBRATION',24:'LANGUAGE',25:'COSTUMECHANGE',26:'FILESELECT',27:'PAUSE',28:'CURSEOFTHEMOON',29:'GAMEOVER',34:'LIFE',35:'LIVES',36:'SCORE',37:'WEAPON',38:'COPY',39:'DELETE',40:'STAGE',41:'NORMAL',42:'NIGHTMARE',43:'ULTIMATE',44:'MODE',45:'CASUAL',46:'VETERAN',47:'STYLE',48:'TIME',49:'NODATA',50:'END',51:'EXITGAME',52:'CONTINUE',53:'STYLECHANGE',54:'MOVE',55:'ATTACK',56:'SUBWEAPON',57:'JUMP',58:'DASH',59:'CHARACTERCHANGERIGHT',60:'CHARACTERCHANGELEFT',61:'COMMANDSUBWEAPON',62:'COMMANDDASH',66:'COLOR1',67:'COLOR2',68:'COLOR3',69:'YES',70:'NO',71:'ON',72:'OFF',73:'JAPANESE',74:'ENGLISH',101:'BUTTONCONFIG'}
samp=collections.defaultdict(list)
for i,text in source.items():
 os=qoffs(gr,gh,i)
 chars=list(text)
 if len(os)!=len(chars): continue
 # render order is left to right for these labels
 pairs=sorted([(qrect(gr,o),o) for o in os],key=lambda z:z[0][0])
 for ch,(r,o) in zip(chars,pairs):
  t=tile_for_quad(ga,r);samp[ch].append(t)
glyph={}
for ch,arr in samp.items():
 cnt=collections.Counter(thash(t) for t in arr);hh=cnt.most_common(1)[0][0];glyph[ch]=next(t for t in arr if thash(t)==hh).getchannel('A')
for c in 'AYRLDUK':
 if c not in glyph: raise RuntimeError('missing glyph '+c)

def crop_info(raw,h,atlas,node):
 o=qoffs(raw,h,node)[0];r=qrect(raw,o);aw,ah=atlas.size
 return (round(r[4]*aw),round(r[5]*aw),round(r[6]*ah),round(r[7]*ah))

def opaque_runs(alpha):
 proj=[alpha.crop((x,0,x+1,alpha.height)).getbbox() is not None for x in range(alpha.width)]
 runs=[];s=None
 for x,on in enumerate(proj+[False]):
  if on and s is None:s=x
  elif not on and s is not None:runs.append((s,x));s=None
 return runs

def dominant_color(crop,run):
 colors=[]
 for y in range(crop.height):
  for x in range(run[0],min(run[1],crop.width)):
   r,g,b,a=crop.getpixel((x,y))
   if a>0: colors.append((r,g,b))
 if not colors:return (255,255,255)
 return collections.Counter(colors).most_common(1)[0][0]

def patch_word(filename,node,target,centers=None,keep_dot=False):
 raw=bytearray(unpack_container(ORIG/filename,OSB_KEY));h=parse_osb(raw);atlas=decode_osb_rgba4444(raw)
 x0,x1,y0,y1=crop_info(raw,h,atlas,node);src=atlas.crop((x0,y0,x1,y1)).convert('RGBA');runs=opaque_runs(src.getchannel('A'))
 letter_runs=runs[:-1] if keep_dot else runs
 if centers is None:
  centers=[(a+b-1)/2 for a,b in letter_runs]
 if len(centers)!=len(target): raise RuntimeError((filename,len(centers),target,runs))
 colors=[dominant_color(src,letter_runs[min(i,len(letter_runs)-1)]) for i in range(len(target))]
 dest=Image.new('RGBA',src.size,(0,0,0,0))
 # native 8x8 mask -> 14x14 pixel style, centered on source glyph centers
 for i,(ch,cx) in enumerate(zip(target,centers)):
  mask=glyph[ch].resize((14,14),Image.Resampling.NEAREST)
  tile=Image.new('RGBA',(14,14),colors[i]+(0,));tile.putalpha(mask)
  xx=round(cx-6.5);yy=1
  dest.alpha_composite(tile,(xx,yy))
 if keep_dot:
  # preserve original period/decorative final pixel run exactly.
  a,b=runs[-1];piece=src.crop((a,0,b,src.height));dest.alpha_composite(piece,(a,0))
 atlas.paste(dest,(x0,y0))
 raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas)
 out=OUT/filename;out.write_bytes(pack_container(bytes(raw),OSB_KEY))
 # validation
 vr=unpack_container(out,OSB_KEY);vh=parse_osb(vr);va=decode_osb_rgba4444(vr);assert encode_osb_rgba4444(va)==vr[vh[5]:vh[5]+vh[1]]
 print(filename,'runs',runs,'centers',centers,'target',target)

# Source centers are measured from the original words; use them instead of expanding Turkish words.
patch_word('Option00.osbctr',37,'AYARLAR',centers=[8,24,40,52,64,80,96])
patch_word('Pause00.osbctr',29,'DURAK',centers=[8,24,40,56,72],keep_dot=True)
