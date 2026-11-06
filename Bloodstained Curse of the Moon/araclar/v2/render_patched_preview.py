from pathlib import Path
import sys,struct,math
from PIL import Image,ImageDraw
sys.path.insert(0,'/mnt/data/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,parse_osb,decode_osb_rgba4444,OSB_KEY
ROOT=Path('/mnt/data/bloodstained_tr_full_v2/luma/titles/00040000001D3C00/romfs')
OUT=Path('/mnt/data/bloodstained_tr_full_v2/previews');OUT.mkdir(parents=True,exist_ok=True)

def get_quads(raw,h,idx):
 post=h[7];r=struct.unpack_from('<6I',raw,post+4+idx*24);vc=r[4];off=post+r[2]+((4+24*idx)%80);qs=[]
 for j in range(0,vc,4):
  vs=[struct.unpack_from('<5f',raw,off+(j+k)*20) for k in range(4)];xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
  if all(math.isfinite(z) for z in xs+ys+us+vv): qs.append((min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv)))
 return qs

def render(fn,idx,scale=2):
 p=ROOT/fn;raw=unpack_container(p,OSB_KEY);h=parse_osb(raw);atlas=decode_osb_rgba4444(raw);qs=get_quads(raw,h,idx)
 if not qs:return Image.new('RGBA',(64,32),(0,0,0,255))
 minx=math.floor(min(q[0] for q in qs));maxx=math.ceil(max(q[1] for q in qs));miny=math.floor(min(q[2] for q in qs));maxy=math.ceil(max(q[3] for q in qs));W=max(1,maxx-minx);H=max(1,maxy-miny)
 c=Image.new('RGBA',(W,H),(0,0,0,255));aw,ah=atlas.size
 for q in qs:
  x0,x1,y0,y1,u0,u1,v0,v1=q;sx0=int(round(u0*aw));sx1=int(round(u1*aw));sy0=int(round(v0*ah));sy1=int(round(v1*ah));
  if sx1<=sx0 or sy1<=sy0:continue
  tile=atlas.crop((sx0,sy0,sx1,sy1));tw=max(1,int(round(x1-x0)));th=max(1,int(round(y1-y0)));tile=tile.resize((tw,th),Image.Resampling.NEAREST)
  c.alpha_composite(tile,(int(round(x0-minx)),int(round(maxy-y1))))
 return c.resize((c.width*scale,c.height*scale),Image.Resampling.NEAREST)

def sheet(name,specs):
 ims=[]
 for fn,i in specs:
  im=render(fn,i,2); box=Image.new('RGBA',(max(440,im.width+12),im.height+28),(30,30,30,255));d=ImageDraw.Draw(box);d.text((6,5),f'{fn} / NODE {i}',fill='white');box.alpha_composite(im,(6,24));ims.append(box)
 w=max(x.width for x in ims);h=sum(x.height+6 for x in ims);sh=Image.new('RGBA',(w,h),(50,50,50,255));y=0
 for im in ims:sh.alpha_composite(im,(0,y));y+=im.height+6
 path=OUT/name;sh.save(path);print(path,sh.size)

sheet('story_preview.png',[
 ('Openingext00_en.osbctr',0),('Openingext00_en.osbctr',1),
 ('DemoText00_en.osbctr',62),('DemoText00_en.osbctr',140),('DemoText00_en.osbctr',256),('DemoText00_en.osbctr',302),('DemoText00_en.osbctr',324),
 ('DemoText01_en.osbctr',82),('DemoText01_en.osbctr',134),('DemoText02_en.osbctr',52),('DemoText02_en.osbctr',182),
 ('TutorialText00_en.osbctr',0),('TutorialText00_en.osbctr',3),('TutorialText00_en.osbctr',11),('TutorialText00_en.osbctr',12),('TutorialText00_en.osbctr',13),('TutorialText00_en.osbctr',20),
 ('GraphicText02_en.osbctr',0),('GraphicText02_en.osbctr',9),('EndingText00_en.osbctr',1),('EndingText00_en.osbctr',2),('EndingText00_en.osbctr',11),('EndingText00_en.osbctr',14)])
sheet('ui_preview.png',[
 ('Clear00.osbctr',0),('Start00.osbctr',0),('GraphicText01.osbctr',0),('GraphicText01.osbctr',4),('Thank00.osbctr',0),('Title00.osbctr',2),
 ('GraphicText00.osbctr',15),('GraphicText00.osbctr',22),('GraphicText00.osbctr',43),('GraphicText00.osbctr',47),('GraphicText00.osbctr',53),('GraphicText00.osbctr',60),('GraphicText00.osbctr',75),('GraphicText00.osbctr',76),('GraphicText00.osbctr',78),('GraphicText00.osbctr',92)])
