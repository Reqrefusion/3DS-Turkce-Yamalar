"""Seven pink title atlases, two shared textless plates, native silhouettes.

Outputs game PNG/TEX/ARC and editable 256x128 transparent textless plates.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage
import sf4_tr_tool as sf4

ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
BASE=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title'
CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler'
CLEAN.mkdir(parents=True,exist_ok=True)
LABELS={
 '016':('Kriz Ası','Biraz Yavaş','Ben Gariban'),
 '017':('Antrenmanda','Tavuk','Amansız'),
 '018':('Cellat','Korumalı','Kuyruk Sallayan'),
 '019':('Geç Açan Çiçek','Sıradan Biri','Yükselişte'),
 '020':('Seçkin','Mürit','Pis Köpek'),
 '021':('Zaman Ustası','Keyfine Bak','Kötü Karma'),
 '022':('Deli Adam','Kendi Ayakları Üstünde','Orta Kademe Yönetici'),
}

def shared_plate(number):
    source=Image.open(HERE/f'sourceplates/title{number}_textless.png').convert('RGBA')
    source=source.resize((256,128),Image.Resampling.LANCZOS)
    original=np.asarray(Image.open(next((BASE/f'title{number}.arc').glob('*.eng.png'))).convert('RGBA'))
    generated=np.asarray(source)
    out=np.zeros((128,256,4),dtype='uint8')
    # Per-row fit avoids moved brush strokes. Native alpha restores the
    # translucency and exact contour that a regenerated plate cannot know.
    for lo,hi in ((0,43),(43,82),(82,125)):
        def box(a):
            ys,xs=np.where(a[lo:hi,:,3]>60)
            ys=ys+lo
            return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
        gx0,gy0,gx1,gy1=box(generated)
        sx0,sy0,sx1,sy1=box(original)
        crop=source.crop((gx0,gy0,gx1,gy1)).resize((sx1-sx0,sy1-sy0),Image.Resampling.LANCZOS)
        plate_pixels=np.asarray(crop)
        out[sy0:sy1,sx0:sx1]=plate_pixels
        caps=[]
        for y in range(sy0,sy1):
            shade=original[y,max(sx0,24):min(sx1,172),3]
            untouched=shade[(shade>8)&(shade<190)]
            caps.append(int(np.median(untouched)) if len(untouched)>6 else 125)
        caps=ndimage.gaussian_filter1d(np.array(caps,dtype='float32'),1.4)
        for y in range(sy0,sy1):
            alpha=original[y,sx0:sx1,3]
            bg=alpha[(alpha>5)&(alpha<190)]
            cap=int(np.median(bg)*1.18) if len(bg)>6 else 135
            out[y,sx0:sx1,3]=np.minimum(out[y,sx0:sx1,3],np.minimum(alpha,cap))
            # Source alpha itself contains the white source-language letters.
            # Use one opacity per scan line across the central brush; the
            # generated RGB retains its texture and native alpha its contour.
            left=max(sx0,24);right=min(sx1,172)
            shade=original[y,left:right,3]
            row_alpha=int(caps[y-sy0])
            native=(shade>0).astype('uint8')
            plate=plate_pixels[y-sy0,left-sx0:right-sx0,3].astype('float32')
            out[y,left:right,3]=(native*np.minimum(255,plate*row_alpha/255)).astype('uint8')
    return Image.fromarray(out,'RGBA')

def make_clean(number,rose,magenta):
    if number=='016':
        # Crisis Ace uses the red strip of title014; pale rose for rows 2/3.
        parent=Image.open(CLEAN/'title014_textless.png').convert('RGBA')
        out=rose.copy()
        out.paste(parent.crop((0,0,256,37)),(0,0))
    elif number=='019':
        out=rose.copy()
        out.paste(magenta.crop((0,75,256,128)),(0,75))
    else:
        out=rose.copy() if number in ('017','018') else magenta.copy()
    out.save(CLEAN/f'title{number}_textless.png')
    return out

def paint(number,background):
    img=background.resize((1024,512),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(img)
    fontfile=HERE/'fonts/DejaVuSans-Bold.ttf'
    for row,label in enumerate(LABELS[number]):
        font=ImageFont.truetype(str(fontfile),54)
        while True:
            bbox=draw.textbbox((0,0),label,font=font,stroke_width=4)
            if bbox[2]-bbox[0]<=580:break
            font=ImageFont.truetype(str(fontfile),font.size-1)
        x=4*20+(580-(bbox[2]-bbox[0]))//2-bbox[0]
        y=4*(6+37*row)+(98-(bbox[3]-bbox[1]))//2-bbox[1]
        draw.text((x,y),label,font=font,fill=(255,248,243,255),
                  stroke_width=4,stroke_fill=(134,32,51,255))
    path=next((BASE/f'title{number}.arc').glob('*.tur.png'))
    img.resize((256,128),Image.Resampling.LANCZOS).save(path)
    arcpath=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{number}.arc'
    arc=sf4.ArcFile(arcpath.read_bytes())
    arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(path,arc.unpack(0))}))

if __name__=='__main__':
    rose=shared_plate('017');magenta=shared_plate('020')
    for number in LABELS:
        paint(number,make_clean(number,rose,magenta))
        print('title'+number)
