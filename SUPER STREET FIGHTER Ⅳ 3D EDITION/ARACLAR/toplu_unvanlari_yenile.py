"""Compare five source languages and rebuild title023-038 as clean plates and Turkish ARC/TEX."""
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
import sf4_tr_tool as sf4
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title'
CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler';CLEAN.mkdir(parents=True,exist_ok=True)
FONT=ROOT/'ARACLAR/fonts/DejaVuSans-Bold.ttf'
LABELS={
23:('Kararsız','Süper Dâhi','Yardımcı Eğitmen'),
24:('Yarım Pişmiş','Kışkırtıcı','Koca Yürekli'),
25:('Yüzüme Vurma','Doğayla Bir','Solmuş Çiçek'),
26:('Müdür Yardımcısı','Kendini Tutma','Cesur Savaşçı'),
27:('Eğitmen','Enerji Dolu','Öğretmen'),
28:('Kara Sevda','Kısasa Kısas','Samuray Ruhu'),
29:('Gözü Kara','Şef','Aldatmaca Ustası'),
30:('Kahraman','Usta','Mızmız Değil'),
31:('Kaya Gibi','Moe','Ateşe Uçan Pervane'),
32:('Tepenin Kralı','Kontrolden Çıkmış','Yönetici'),
33:('Kendini En İyi İlan Eden','Mesih','Ebedî Meydan Okuyan'),
34:('Sorun Yok!','Sanatçı','Şeytani'),
35:('Bilgi Güçtür','Barışçı','Hayatta Bir Kez'),
36:('Genel Müdür','Zafer İlanı','İlah'),
37:('Yumruk Çarpıştıran','Yakaladım Seni','Tutuş Kralı'),
38:('Doğuştan Yetenek','Budala','Ani Öfke'),
}
def clean(n):
    folder=BASE/f'title{n:03}.arc'
    source=np.stack([np.asarray(Image.open(next(folder.glob(f'*.{lang}.png'))).convert('RGBA')) for lang in ('eng','fre','ger','ita','spa')])
    src=source[0].copy();spread=source.astype(np.int16).max(axis=0)-source.astype(np.int16).min(axis=0)
    zone=np.zeros((128,256),bool)
    for top in (0,37,75):zone[top+5:top+31,9:186]=True
    mask=ndi.binary_dilation((spread.max(axis=2)>38)&zone,iterations=2)&zone
    out=src.copy()
    for y in range(128):
        good=np.flatnonzero((~mask[y])&zone[y]&(src[y,:,3]>5));bad=np.flatnonzero(mask[y])
        if len(good)<3 or len(bad)==0:continue
        idx=np.searchsorted(good,bad);left=good[np.maximum(0,idx-1)];right=good[np.minimum(idx,len(good)-1)]
        out[y,bad]=src[y,np.where(right-bad<bad-left,right,left)]
    smooth=ndi.gaussian_filter(out.astype(float),sigma=(1.1,2.2,0))
    out[mask]=np.uint8(smooth[mask].clip(0,255))
    plate=Image.fromarray(out,'RGBA');plate.save(CLEAN/f'title{n:03}_textless.png')
    return plate

def draw(n,plate):
    image=plate.resize((1024,512),Image.Resampling.NEAREST);d=ImageDraw.Draw(image)
    for row,label in enumerate(LABELS[n]):
        if n in (33,34,35):fill=(255,235,224,255);stroke=(122,24,28,255);size=55
        elif n in (26,27,28,29):fill=(255,252,242,255);stroke=(109,24,33,255);size=56
        else:fill=(255,248,244,255);stroke=(137,23,39,255);size=56
        width=3 if n in (33,34,35) else 4
        f=ImageFont.truetype(str(FONT),size)
        while True:
            box=d.textbbox((0,0),label,font=f,stroke_width=width)
            if box[2]-box[0]<=608:break
            f=ImageFont.truetype(str(FONT),f.size-1)
        x=4*20+(608-(box[2]-box[0]))//2-box[0]
        y=4*(5+37*row)+(105-(box[3]-box[1]))//2-box[1]
        d.text((x,y),label,font=f,fill=fill,stroke_width=width,stroke_fill=stroke)
    folder=BASE/f'title{n:03}.arc';path=next(folder.glob('*.tur.png'))
    image.resize((256,128),Image.Resampling.LANCZOS).save(path)
    arcpath=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{n:03}.arc'
    arc=sf4.ArcFile(arcpath.read_bytes());arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(path,arc.unpack(0))}))
if __name__=='__main__':
    for n in LABELS:draw(n,clean(n));print(n)
