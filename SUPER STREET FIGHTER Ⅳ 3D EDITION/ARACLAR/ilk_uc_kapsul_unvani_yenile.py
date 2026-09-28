"""Repair the first three capsule title atlases using multilingual plates.

The Turkish names Titan and Herkül follow the French title003 names, so the
existing localized labels are retained intentionally.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import sf4_tr_tool as sf4

ROOT=Path(__file__).resolve().parent.parent
FONT=Path(__file__).resolve().parent/'fonts/DejaVuSans-Bold.ttf'
LABELS={
 '001':('Toy Dövüşçü','Paralı Dövüşçü','Fena Değil'),
 '002':('Sihirbaz','Tanınmış Dövüşçü','Benim Yolum'),
 '003':('Titan','Herkül','Mükemmeliyetçi'),
}


def rebuild(index):
 folder=ROOT/f'CALISMA_ALANI/images/_GUI/_id/_title/title{index}.arc'
 path=next(folder.glob('*.fre.png'))
 a=np.asarray(Image.open(path).convert('RGBA')).copy()
 # Preserve all three original portraits, capsule edges, and exterior.
 # The interior is nearly flat: reconstruct each scan line from original
 # uncovered pixels away from the words, retaining translucent alpha.
 for row,top in enumerate((0,37,75)):
  for y in range(top+8,top+30):
   donors=np.concatenate((a[y,31:40],a[y,164:170]))
   donors=donors[(donors[:,3]>30)&(donors[:,3]<245)]
   if len(donors)<4:
    donors=a[y,155:170]
   left=24 if index=='003' and row==2 else 30
   if len(donors):a[y,left:165]=np.median(donors,axis=0).astype('uint8')
 img=Image.fromarray(a,'RGBA').resize((1024,512),Image.Resampling.NEAREST)
 draw=ImageDraw.Draw(img)
 for row,label in enumerate(LABELS[index]):
  font=ImageFont.truetype(str(FONT),52)
  while True:
   bbox=draw.textbbox((0,0),label,font=font,stroke_width=4)
   if bbox[2]-bbox[0]<=548:break
   font=ImageFont.truetype(str(FONT),font.size-1)
  x=4*37+(548-(bbox[2]-bbox[0]))//2-bbox[0]
  y=4*(6+37*row)+(99-(bbox[3]-bbox[1]))//2-bbox[1]
  draw.text((x,y),label,font=font,fill=(255,247,241,255),
            stroke_width=4,stroke_fill=(125,54,69,255))
 target=next(folder.glob('*.tur.png'))
 img.resize((256,128),Image.Resampling.LANCZOS).save(target)
 arc_path=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{index}.arc'
 arc=sf4.ArcFile(arc_path.read_bytes());arc_path.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(target,arc.unpack(0))}))
 assert sf4.ArcFile(arc_path.read_bytes()).unpack(0)[:4]==sf4.TEX_MAGIC

if __name__=='__main__':
 for k in LABELS:rebuild(k);print('title'+k)
