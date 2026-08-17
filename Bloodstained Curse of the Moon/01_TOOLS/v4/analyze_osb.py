import sys,struct,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,parse_osb,decode_osb_rgba4444,OSB_KEY

def rec(raw,h,i): return struct.unpack_from('<6I',raw,h[7]+4+i*24)
def vertex_abs(h,i,r): return h[7]+4+i*24+r[2]
def qoffs(raw,h,i):
 r=rec(raw,h,i); a=vertex_abs(h,i,r); return [a+j*4*20 for j in range(r[4]//4)]
def qvals(raw,off): return [struct.unpack_from('<5f',raw,off+k*20) for k in range(4)]
def qrect(raw,off):
 vs=qvals(raw,off); xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
 return min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv)

def render_node(path,i,scale=2):
 raw=unpack_container(Path(path),OSB_KEY);h=parse_osb(raw);at=decode_osb_rgba4444(raw); aw,ah=at.size
 os=qoffs(raw,h,i)
 if not os: return Image.new('RGBA',(1,1))
 rs=[qrect(raw,o) for o in os]
 minx=math.floor(min(r[0] for r in rs));maxx=math.ceil(max(r[1] for r in rs));miny=math.floor(min(r[2] for r in rs));maxy=math.ceil(max(r[3] for r in rs))
 W=max(1,maxx-minx);H=max(1,maxy-miny)
 can=Image.new('RGBA',(W,H),(0,0,0,0))
 for o,r in zip(os,rs):
  ux0=round(r[4]*aw);ux1=round(r[5]*aw);uy0=round(r[6]*ah);uy1=round(r[7]*ah)
  piece=at.crop((ux0,uy0,ux1,uy1))
  x0=round(r[0]-minx);x1=round(r[1]-minx)
  # model coords y up; image y down
  y0=round(maxy-r[3]);y1=round(maxy-r[2])
  if x1>x0 and y1>y0:
   piece=piece.resize((x1-x0,y1-y0),Image.Resampling.NEAREST)
   can.alpha_composite(piece,(x0,y0))
 if scale!=1: can=can.resize((W*scale,H*scale),Image.Resampling.NEAREST)
 return can

def montage(orig,patch,out,nodes=None,cols=4):
 ro=unpack_container(Path(orig),OSB_KEY);h=parse_osb(ro); n=h[9]
 if nodes is None:nodes=range(n)
 cells=[]; font=ImageFont.load_default()
 for i in nodes:
  a=render_node(orig,i,2); b=render_node(patch,i,2)
  W=max(a.width,b.width,120); H=a.height+b.height+30
  c=Image.new('RGBA',(W,H),(20,20,20,255)); d=ImageDraw.Draw(c)
  d.text((2,2),f'node {i} ORIG',fill='white',font=font); c.alpha_composite(a,(0,12))
  y=14+a.height; d.text((2,y),f'node {i} PATCH',fill='yellow',font=font); c.alpha_composite(b,(0,y+12))
  cells.append(c)
 cw=max(c.width for c in cells); ch=max(c.height for c in cells); rows=math.ceil(len(cells)/cols)
 m=Image.new('RGBA',(cw*cols,ch*rows),(0,0,0,255))
 for k,c in enumerate(cells):m.alpha_composite(c,((k%cols)*cw,(k//cols)*ch))
 m.save(out)

if __name__=='__main__':
 orig='/mnt/data/v4work/orig/romfs/GraphicText00.osbctr'
 patch='/mnt/data/v4work/v3/luma/titles/00040000001D3C00/romfs/GraphicText00.osbctr'
 montage(orig,patch,'/mnt/data/v4work/gt00_compare_correct.png',range(14,102),cols=4)
