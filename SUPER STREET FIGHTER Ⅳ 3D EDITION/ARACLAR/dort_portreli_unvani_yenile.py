"""Clean source-derived portrait ribbons for title055-059 and write Turkish TEX/ARC.

The decorative textless base is redrawn from title055 English reference;
Source ENG/FRE/GER/ITA/SPA remain in each title folder for checking.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import sf4_tr_tool as sf4
ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
BASE=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title'
CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler';CLEAN.mkdir(parents=True,exist_ok=True)
LABELS={
55:('Ateşle Sınanmak','Acele İşe Şeytan Karışır','Tedbir İyidir'),
56:('Geçmiş Geride Kaldı','Fırtına Öncesi Sessizlik','Şerde Hayır Var'),
57:('Talih Yüzüne Güldü','Umursamaz','Göze Batan Tüketici'),
58:('Durup Dururken',"Peter'dan Al Paul'a Ver",'Bir Gece Üstüne Uyu'),
59:('Ateşe Ateşle Karşılık Ver','Fırsat Kapıyı Çalar','Tecrübe Konuşur'),
}
def plate():
    source=Image.open(HERE/'sourceplates/title055_058_generated_textless.png').convert('RGBA')
    out=Image.new('RGBA',(256,128))
    for top,bottom,y in ((18,270,0),(338,565,37),(612,850,75)):
        crop=source.crop((0,top,1550,bottom)).resize((176,32),Image.Resampling.LANCZOS)
        out.alpha_composite(crop,(0,y+2))
    return out

def rose_plate(original):
    """Match title059's vivid magenta ribbons while retaining the red portrait."""
    a=np.asarray(original).copy()
    x=np.arange(256)[None,:]
    weight=np.clip((x-29)/15,0,1).astype('float32')
    a[:,:,1]=np.uint8(a[:,:,1]*(1-0.29*weight))
    a[:,:,2]=np.uint8(np.minimum(255,a[:,:,2]+(45*weight)).clip(0,255))
    return Image.fromarray(a,'RGBA')

def write(n,clean):
    clean.save(CLEAN/f'title{n:03}_textless.png')
    im=clean.resize((1024,512),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(im)
    for row,label in enumerate(LABELS[n]):
        size=60
        while True:
            font=ImageFont.truetype(str(HERE/'fonts/NimbusSansNarrow-BoldOblique.otf'),size)
            box=draw.textbbox((0,0),label,font=font,stroke_width=4)
            if box[2]-box[0] <= 504:break
            size-=1
        x=4*42+(504-(box[2]-box[0]))//2-box[0]
        y=4*(4+37*row)+(95-(box[3]-box[1]))//2-box[1]
        draw.text((x,y),label,font=font,fill=(255,249,243,255),stroke_width=4,stroke_fill=(119,24,31,255))
    path=next((BASE/f'title{n:03}.arc').glob('*.tur.png'))
    im.resize((256,128),Image.Resampling.LANCZOS).save(path)
    arcpath=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{n:03}.arc'
    arc=sf4.ArcFile(arcpath.read_bytes());arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(path,arc.unpack(0))}))
if __name__=='__main__':
    background=plate()
    for n in LABELS:write(n,rose_plate(background) if n==59 else background);print(n)
