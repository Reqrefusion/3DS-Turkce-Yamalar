import sys,struct,hashlib,collections,math
from pathlib import Path
from PIL import Image
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import *

def rec(raw,h,i): return struct.unpack_from('<6I',raw,h[7]+4+i*24)
def va(h,i,r): return h[7]+4+i*24+r[2]
def qoffs(raw,h,i):
 r=rec(raw,h,i); a=va(h,i,r); return [a+j*80 for j in range(r[4]//4)]
def qrect(raw,o):
 vs=[struct.unpack_from('<5f',raw,o+k*20) for k in range(4)];xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
 return min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv)
source={
15:'PRESS ANY BUTTON',16:'GAME START',17:'BOSS RUSH',18:'OPTIONS',19:'??????',
22:'VIBRATION',23:'HD Rumble',24:'LANGUAGE',25:'COSTUME CHANGE',26:'FILE SELECT',27:'PAUSE',28:'CURSE OF THE MOON',29:'GAME OVER',30:'ZANGETSU',31:'MIRIAM',32:'ALFRED',33:'ZEEBEL',34:'LIFE',35:'LIVES',36:'SCORE',37:'WEAPON',38:'COPY',39:'DELETE',40:'STAGE',41:'NORMAL',42:'NIGHTMARE',43:'ULTIMATE',44:'MODE',45:'CASUAL',46:'VETERAN',47:'STYLE',48:'TIME',49:'NO DATA',50:'END',51:'EXIT GAME',52:'CONTINUE',53:'STYLE CHANGE',54:'MOVE',55:'ATTACK',56:'SUB WEAPON',57:'JUMP',58:'DASH',59:'CHARACTER CHANGE RIGHT',60:'CHARACTER CHANGE LEFT',61:'COMMAND SUB WEAPON',62:'COMMAND DASH',66:'COLOR 1',67:'COLOR 2',68:'COLOR 3',69:'YES',70:'NO',71:'ON',72:'OFF',73:'JAPANESE',74:'ENGLISH',75:'NOW LOADING',76:'NOW LOADING',77:'NOW LOADING',78:'NOW LOADING',79:'NOW LOADING',80:'NOW LOADING',81:'NOW LOADING',82:'NOW LOADING',83:'NOW LOADING',84:'NOW LOADING',85:'NOW LOADING',86:'NOW LOADING',87:'LOADED',88:'NOW SAVING',89:'NOW SAVING',90:'NOW SAVING',91:'NOW SAVING',92:'NOW SAVING',93:'NOW SAVING',94:'NOW SAVING',95:'NOW SAVING',96:'NOW SAVING',97:'NOW SAVING',98:'NOW SAVING',99:'NOW SAVING',100:'SAVED',101:'BUTTON CONFIG'}
raw=unpack_container(Path('/mnt/data/v4work/orig/romfs/GraphicText00.osbctr'),OSB_KEY);h=parse_osb(raw);at=decode_osb_rgba4444(raw);aw,ah=at.size
samples=collections.defaultdict(list)
for i,text in source.items():
 os=qoffs(raw,h,i); chars=[c for c in text if c!=' ']
 if len(os)!=len(chars): print('COUNT MISMATCH',i,text,len(os),len(chars));continue
 # all single row; sort by x0
 ors=sorted([(qrect(raw,o),o) for o in os],key=lambda x:(-round(x[0][3],2),x[0][0]))
 for ch,(r,o) in zip(chars,ors):
  x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
  tile=at.crop((x0,y0,x1,y1)).resize((8,8),Image.Resampling.NEAREST)
  samples[ch.upper()].append((hashlib.sha1(tile.tobytes()).hexdigest()[:8],i,tile,(x0,y0,x1,y1)))
print('chars',sorted(samples))
for ch in sorted(samples):
 c=collections.Counter(x[0] for x in samples[ch]);print(ch,len(samples[ch]),c.most_common(5))
 # save most common first tile
 hh=c.most_common(1)[0][0]
 t=next(x[2] for x in samples[ch] if x[0]==hh);t.resize((64,64),Image.Resampling.NEAREST).save(f'/mnt/data/v4work/glyph_{ord(ch):04X}.png')
