from pathlib import Path
import sys,hashlib,struct,collections
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,parse_osb,decode_osb_rgba4444,OSB_KEY
from analyze_osb import qoffs,qrect
rom=Path('/mnt/data/v4work/orig/romfs')

def hh(im): return hashlib.sha1(im.convert('RGBA').tobytes()).hexdigest()
src=rom/'GraphicText00.osbctr'; raw=unpack_container(src,OSB_KEY); h=parse_osb(raw); at=decode_osb_rgba4444(raw); aw,ah=at.size
# known text nodes excluding icons
known={15:'PRESSANYBUTTON',16:'GAMESTART',17:'BOSSRUSH',18:'OPTIONS',19:'??????',22:'VIBRATION',23:'HDRumble',24:'LANGUAGE',25:'COSTUMECHANGE',26:'FILESELECT',27:'PAUSE',28:'CURSEOFTHEMOON',29:'GAMEOVER',30:'ZANGETSU',31:'MIRIAM',32:'ALFRED',33:'ZEEBEL',34:'LIFE',35:'LIVES',36:'SCORE',37:'WEAPON',38:'COPY',39:'DELETE',40:'STAGE',41:'NORMAL',42:'NIGHTMARE',43:'ULTIMATE',44:'MODE',45:'CASUAL',46:'VETERAN',47:'STYLE',48:'TIME',49:'NODATA',50:'END',51:'EXITGAME',52:'CONTINUE',53:'STYLECHANGE',54:'MOVE',55:'ATTACK',56:'SUBWEAPON',57:'JUMP',58:'DASH',59:'CHARACTERCHANGERIGHT',60:'CHARACTERCHANGELEFT',61:'COMMANDSUBWEAPON',62:'COMMANDDASH',66:'COLOR1',67:'COLOR2',68:'COLOR3',69:'YES',70:'NO',71:'ON',72:'OFF',73:'JAPANESE',74:'ENGLISH',101:'BUTTONCONFIG'}
canon=set()
for i,text in known.items():
    offs=qoffs(raw,h,i)
    # simply hash all 8x8 quads; even icons are okay, but source nodes here mostly text
    for o in offs:
        r=qrect(raw,o)
        if abs((r[1]-r[0])-8)>.2 or abs((r[3]-r[2])-8)>.2: continue
        x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
        tile=at.crop((x0,y0,x1,y1)).resize((8,8))
        if tile.getbbox(): canon.add(hh(tile))
print('canon',len(canon))
rows=[]
for p in rom.glob('*.osbctr'):
  try:
    r=unpack_container(p,OSB_KEY); ph=parse_osb(r); pa=decode_osb_rgba4444(r); w,he=pa.size
  except Exception: continue
  hits=0; qcount=0; nodes_hit=0
  for i in range(ph[9]):
    nh=0
    try: offs=qoffs(r,ph,i)
    except Exception: continue
    for o in offs:
      try: rr=qrect(r,o)
      except Exception: continue
      if abs((rr[1]-rr[0])-8)>.2 or abs((rr[3]-rr[2])-8)>.2: continue
      x0=round(rr[4]*w);x1=round(rr[5]*w);y0=round(rr[6]*he);y1=round(rr[7]*he)
      if x1<=x0 or y1<=y0: continue
      tile=pa.crop((x0,y0,x1,y1)).resize((8,8))
      qcount+=1
      if tile.getbbox() and hh(tile) in canon: hits+=1; nh+=1
    if nh>=2: nodes_hit+=1
  if hits>=2: rows.append((hits,nodes_hit,qcount,ph[9],p.name,w,he))
for row in sorted(rows,reverse=True): print(*row)
