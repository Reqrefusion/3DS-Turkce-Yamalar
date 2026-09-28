"""Write editable, transparent 256x128 textless plates for earlier atlases."""
from pathlib import Path
from PIL import Image
from scipy import ndimage
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
ASSETS=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title'
OUT=ROOT/'CALISMA_ALANI/temiz_zeminler'
OUT.mkdir(parents=True,exist_ok=True)
ROWS={'078':(((4,44),(0,36)),((45,84),(38,74)),((85,123),(76,112))),
      '150':(((4,42),(0,36)),((45,82),(38,74)),((85,122),(76,112))),
      '186':(((5,36),(2,34)),((44,74),(39,72)),((82,112),(77,110)))}

def native(number,lang):
    return np.asarray(Image.open(next((ASSETS/f'title{number}.arc').glob(f'*.{lang}.png'))).convert('RGBA')).copy()

def red(number):
    a=native(number,'eng' if number=='008' else 'spa')
    for row,top in enumerate((0,37,75)):
        if number=='008' and row==0:
            # Separate repeating chick/sparkle motif reconstructed from ENG.
            plate=Image.open(HERE/'sourceplates/title008_textless.png').convert('RGBA')
            plate=plate.resize((256,128),Image.Resampling.LANCZOS)
            pink=np.asarray(plate.crop((5,5,251,38)).resize((171,24),Image.Resampling.LANCZOS)).copy()
            a[:37]=0
            native_shape=native('008','eng')[7:31,5:176,3]>0
            pink[:,:,3]=np.where(native_shape,pink[:,:,3],0)
            a[7:31,5:176]=pink
            continue
        if number=='008' and row not in (1,2):continue
        for y in range(top+11,top+28):
            strip=a[y,21:169]
            clean=strip[(strip[:,0]>200)&(strip[:,1]<125)&
                        (strip[:,2]<125)&(strip[:,3]<165)]
            if len(clean)>10:a[y,28:163]=np.median(clean,axis=0).astype('uint8')
    return Image.fromarray(a,'RGBA')

def capsule(number):
    a=native(number,'fre')
    for row,top in enumerate((0,37,75)):
        for y in range(top+8,top+30):
            donors=np.concatenate((a[y,31:40],a[y,164:170]))
            donors=donors[(donors[:,3]>30)&(donors[:,3]<245)]
            if len(donors)<4:donors=a[y,155:170]
            left=24 if number=='003' and row==2 else 30
            if len(donors):a[y,left:165]=np.median(donors,axis=0).astype('uint8')
    return Image.fromarray(a,'RGBA')

def regenerated(number):
    source=Image.open(HERE/f'sourceplates/title{number}_textless.png').convert('RGBA').resize((256,128),Image.Resampling.LANCZOS)
    aligned=Image.new('RGBA',(256,128),(0,0,0,0))
    for (start,stop),(dest,end) in ROWS[number]:
        aligned.alpha_composite(source.crop((0,start,256,stop)).resize((256,end-dest),Image.Resampling.LANCZOS),(0,dest))
    folder=ASSETS/f'title{number}.arc'
    alpha=np.stack([np.asarray(Image.open(next(folder.glob(f'*.{lang}.png'))).convert('RGBA'))[:,:,3]
                    for lang in ('eng','fre','ger','ita','spa')])
    native=np.median(alpha,axis=0).astype('uint8')
    pixels=np.asarray(aligned).copy()
    # Original alpha contains the old text as opaque glyph-shaped patches.
    # Keep only the native *silhouette*; set interior opacity from the clean
    # generated colors, retaining brighter white brush and darker pigment.
    for y in range(128):
        values=native[y,35:175]
        bg=values[(values>10)&(values<200)]
        base=int(np.median(bg)) if len(bg)>6 else 105
        rgb=pixels[y,:,:3].astype('float32')
        white=np.clip((rgb.min(axis=1)-105)/150,0,1)
        estimate=base+(255-base)*white**2
        pixels[y,:,3]=np.minimum(pixels[y,:,3],np.uint8(np.clip(estimate,0,255)))
        pixels[y,:,3]=np.where(native[y,:]>5,pixels[y,:,3],0)
    return Image.fromarray(pixels,'RGBA')

def main():
    for number in ('001','002','003'):
        capsule(number).save(OUT/f'title{number}_textless.png')
    for number in ('008','009','010','011','012','013','014','015'):
        red(number).save(OUT/f'title{number}_textless.png')
    for number in ('078','150','186'):
        regenerated(number).save(OUT/f'title{number}_textless.png')
    print('14 textless plates:',OUT)

if __name__=='__main__':main()
