from pathlib import Path
import sys,hashlib,struct
from collections import Counter
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,parse_osb,decode_osb_rgba4444,OSB_KEY
from analyze_osb import qoffs,qrect
rom=Path('/mnt/data/v4work/orig/romfs')
# glyph hashes from GraphicText00 atlas referenced by known label nodes
src=rom/'GraphicText00.osbctr'; raw=unpack_container(src,OSB_KEY); h=parse_osb(raw); at=decode_osb_rgba4444(raw); aw,ah=at.size
known_nodes=list(range(15,19))+list(range(22,75))+list(range(75,102))
# 8x8 exact tiles referenced in nodes, collect hashes that recur >=2 and aren't blank
def hh(im): return hashlib.sha1(im.convert('RGBA').tobytes()).hexdigest()
hashes=[]
for i in known_nodes:
    for o in qoffs(raw,h,i):
        r=qrect(raw,o)
        if abs((r[1]-r[0])-8)>.2 or abs((r[3]-r[2])-8)>.2: continue
        x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
        tile=at.crop((x0,y0,x1,y1)).resize((8,8))
        if tile.getbbox(): hashes.append(hh(tile))
counts=Counter(hashes)
glyphset={x for x,c in counts.items() if c>=2}
print('glyphset',len(glyphset))
rows=[]
for p in rom.glob('*.osbctr'):
    try:
        r=unpack_container(p,OSB_KEY); ph=parse_osb(r); pa=decode_osb_rgba4444(r); w,he=pa.size
    except Exception: continue
    hits=0; cells=0
    for y in range(0,he,8):
      for x in range(0,w,8):
        tile=pa.crop((x,y,x+8,y+8));
        if tile.getbbox():
            cells += 1
            if hh(tile) in glyphset: hits+=1
    if hits:
      rows.append((hits,cells,ph[9],p.name,w,he))
for row in sorted(rows,reverse=True): print(*row)
