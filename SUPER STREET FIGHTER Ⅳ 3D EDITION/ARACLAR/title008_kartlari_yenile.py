"""Rebuild all three card titles on a separate textless source plate."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sf4_tr_tool as sf4

ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
FOLDER=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title/title008.arc'
TARGET=next(FOLDER.glob('*.tur.png'))
ARC=ROOT/'YAMA/_eng/_GUI/_id/_title/title008.arc'
CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler/title008_textless.png'

def rebuild():
    image=Image.open(CLEAN).convert('RGBA').resize((1024,512),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(image)
    for row,label in enumerate(('Efsane Civciv','Ezici Vale','Yıkım Valesi')):
        fontfile=HERE/('fonts/DejaVuSans-Bold.ttf' if row==0 else 'fonts/NimbusSansNarrow-BoldOblique.otf')
        font=ImageFont.truetype(str(fontfile),52 if row==0 else 64)
        while True:
            bbox=draw.textbbox((0,0),label,font=font,stroke_width=5)
            if bbox[2]-bbox[0]<=570:break
            font=ImageFont.truetype(str(fontfile),font.size-1)
        x=4*20+(570-(bbox[2]-bbox[0]))//2-bbox[0]
        y=4*(7+37*row)+(94-(bbox[3]-bbox[1]))//2-bbox[1]
        draw.text((x,y),label,font=font,fill=(255,251,245,255),
                  stroke_width=5,stroke_fill=(155,27,48,255))
    image.resize((256,128),Image.Resampling.LANCZOS).save(TARGET)
    arc=sf4.ArcFile(ARC.read_bytes())
    ARC.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(TARGET,arc.unpack(0))}))

if __name__=='__main__':rebuild()
