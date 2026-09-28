"""Rebuild the remaining special title atlases with per-family blank plates.

The question marks in title215 are an intentional mystery icon and kept.
"""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import sf4_tr_tool as sf4
import toplu_unvanlari_yenile as general
import on_portreli_unvani_yenile as portrait
ROOT=Path(__file__).resolve().parent.parent;HERE=Path(__file__).resolve().parent
BASE=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title';CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler'
LABELS={
 0:(None,'Acemi Dövüşçü','Dipte Sürünen'),
 4:('Acımasız','Ultra!','Süper!'),
 5:('Sıradan Dövüşçü','Acı Zafer','Teknisyen'),
 6:('Ben Varken Olmaz','Bunu Bekliyordum','Önce Gelen Kapar'),
 7:('Sersem Civcivler','Nohut Kafa','Civciv Kafalı'),
 60:('Yeniden Kullan, Dönüştür','Ağır Ağır, Güzel Güzel','Yorulmak Bilmez Gezgin'),
 201:('Gouken Avcısı','6 Tuş Savaşçısı','Joystick Ustası'),
 202:('Daha Çok Jeton','Kombo Kralı','Odak Ustası'),
 203:('Tek Olan','Arcade Aristokratı','Savaşçının Düşleri'),
 204:('Ultra Şampiyonu','Süper Ezici','İyi Geceler De'),
}

def plate(n):
    if n==7:
        source=Image.open(CLEAN/'title008_textless.png').convert('RGBA')
        out=Image.new('RGBA',(256,128))
        strip=source.crop((0,0,256,35))
        for top in (0,37,75):out.alpha_composite(strip,(0,top))
    elif n==60:
        out=Image.new('RGBA',(256,128))
        red=Image.open(CLEAN/'title059_textless.png').convert('RGBA')
        for top in (0,37):out.alpha_composite(red.crop((0,top,256,top+35)),(0,top))
        # Last row has a distinct white character banner. The five source
        # languages supply the left silhouette; the blank brush supplies text area.
        folder=BASE/'title060.arc'
        sources=np.stack([np.asarray(Image.open(next(folder.glob(f'*.{s}.png'))).convert('RGBA'))
                          for s in ('eng','fre','ger','ita','spa')])
        lum=(sources[:,:,:,:3].astype('float32')*np.array([.22,.65,.13])).sum(axis=3)
        portrait_pixels=np.take_along_axis(sources,lum.argmin(axis=0)[None,:,:,None],axis=0)[0]
        ribbon=portrait.SOURCE.crop((47,615,1704,887)).resize((180,35),Image.Resampling.LANCZOS)
        out.alpha_composite(ribbon,(0,75))
        a=np.asarray(out).copy()
        for x in range(36):
            t=max(0,min(1,(x-22)/14))
            a[75:110,x]=np.uint8((1-t)*portrait_pixels[75:110,x]+t*a[75:110,x])
        out=Image.fromarray(a,'RGBA')
    elif n==201:
        out=general.clean(n)
        red=Image.open(CLEAN/'title055_textless.png').convert('RGBA')
        out.paste(red.crop((0,0,256,35)),(0,0))
    elif n==0:
        out=general.clean(n)
        arr=np.asarray(out).copy()
        for top in (37,75):
            for y in range(top+6,top+34):
                # Solid original pill surface beyond the longest foreign label.
                rgba=arr[y,164].copy()
                arr[y,26:159]=rgba
        out=Image.fromarray(arr,'RGBA')
    else:
        out=general.clean(n)
    out.save(CLEAN/f'title{n:03}_textless.png')
    return out

def write(n):
    image=plate(n).resize((1024,512),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(image)
    for row,label in enumerate(LABELS[n]):
        if label is None:continue
        size=57
        while True:
            font=ImageFont.truetype(str(HERE/'fonts/DejaVuSans-Bold.ttf'),size)
            box=draw.textbbox((0,0),label,font=font,stroke_width=4)
            if box[2]-box[0] <= (515 if n in (0,7,60,201) else 605):break
            size-=1
        left,width=(35,530) if n==60 else ((27,560) if n in (0,7,201) else (18,610))
        # Refit against the actual panel width chosen above.
        while box[2]-box[0]>width:
            size-=1;font=ImageFont.truetype(str(HERE/'fonts/DejaVuSans-Bold.ttf'),size)
            box=draw.textbbox((0,0),label,font=font,stroke_width=4)
        x=4*left+(width-(box[2]-box[0]))//2-box[0]
        y=4*(4+37*row)+(100-(box[3]-box[1]))//2-box[1]
        draw.text((x,y),label,font=font,fill=(255,249,242,255),stroke_width=4,stroke_fill=(132,26,38,255))
    path=next((BASE/f'title{n:03}.arc').glob('*.tur.png'))
    image.resize((256,128),Image.Resampling.LANCZOS).save(path)
    arcpath=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{n:03}.arc'
    arc=sf4.ArcFile(arcpath.read_bytes());arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(path,arc.unpack(0))}))

def mystery():
    n=215
    folder=BASE/'title215.arc';src=Image.open(next(folder.glob('*.eng.png'))).convert('RGBA')
    a=np.asarray(src).copy()
    # Editable blank bar: keep the original border and uniformly paint the
    # middle where three question marks live. Installed mystery icon stays ???.
    for y in range(8,37):
        a[y,45:170]=a[y,35]
    Image.fromarray(a,'RGBA').save(CLEAN/'title215_textless.png')
    target=next(folder.glob('*.tur.png'))
    src.save(target)
    arcpath=ROOT/'YAMA/_eng/_GUI/_id/_title/title215.arc'
    arc=sf4.ArcFile(arcpath.read_bytes());arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(target,arc.unpack(0))}))
if __name__=='__main__':
    for n in LABELS:write(n);print(n)
    mystery();print(215)
