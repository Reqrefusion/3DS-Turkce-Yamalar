from PIL import Image, ImageDraw, ImageFont
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path
import ast

Z = ZipFile('upload/SF4_3DS_Turkce_206_Atlas_Temiz_Zemin_V19(1).zip')
BASE=Path('v19_source/SF4_3DS_Turkce_206_Atlas_Temiz_Zemin_V19/ARACLAR')
LABELS={}
for p in BASE.glob('*.py'):
    try: nodes=ast.parse(p.read_text()).body
    except:continue
    for node in nodes:
        if not isinstance(node,ast.Assign) or not any(isinstance(t,ast.Name) and t.id in ('LABELS','TITLES') for t in node.targets):continue
        try:d=ast.literal_eval(node.value)
        except:continue
        for k,v in d.items():
            if str(k).isdigit() and isinstance(v,tuple):LABELS[int(k)]=v
LABELS[8]=('Efsane Civciv','Ezici Vale','Yıkım Valesi')

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MONO='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def original(n):
    p=next(x for x in Z.namelist() if f'/title{n:03}.arc/' in x and x.endswith('.eng.png'))
    return Image.open(BytesIO(Z.read(p))).convert('RGBA')
def plate(n):
    p=next(x for x in Z.namelist() if x.endswith(f'/temiz_zeminler/title{n:03}_textless.png'))
    return Image.open(BytesIO(Z.read(p))).convert('RGBA')

def style(n):
    if 8<=n<=15 or 20<=n<=42: return 'plain'
    return 'outline'

def make(n):
    canvas=plate(n)
    mode=style(n)
    for row,label in enumerate(LABELS[n]):
        if not label:continue
        # Native vertical card tops are 0, 38, 76. Preserve all plate pixels.
        top=38*row
        if n in (0,1,2,3): left,right,cy=24,170,top+19
        elif n>=201:left,right,cy=16,174,top+19
        else:left,right,cy=14,173,top+18
        mono=mode=='plain' and 8<=n<=15
        fontpath=MONO if mono else FONT
        cap=15 if mode=='outline' else 16
        if n>=201:cap=15
        size=cap*4
        while True:
            font=ImageFont.truetype(fontpath,size)
            bbox=ImageDraw.Draw(Image.new('L',(4,4))).textbbox((0,0),label,font=font,stroke_width=(5 if mode=='outline' else 0))
            if bbox[2]-bbox[0]<=4*(right-left-3) or size<=32:break
            size-=1
        # Place the text's actual ink box, rather than its font baseline.
        width,height=bbox[2]-bbox[0],bbox[3]-bbox[1]
        x=4*(left+right)//2-width//2-bbox[0]
        y=4*cy-height//2-bbox[1]
        overlay=Image.new('RGBA',(1024,512))
        d=ImageDraw.Draw(overlay)
        if mode=='outline':
            d.text((x,y),label,font=font,fill=(255,251,244,255),stroke_width=5,stroke_fill=(213,27,34,255))
        else:
            d.text((x,y),label,font=font,fill=(255,247,239,255))
        canvas=Image.alpha_composite(canvas,overlay.resize((256,128),Image.Resampling.LANCZOS))
    return canvas

if __name__=='__main__':
    numbers=[0,5,12,20,23,33,42,43,49,55,61,128,201,204]
    out=Image.new('RGB',(3*256,128*len(numbers)),(30,28,29))
    for idx,n in enumerate(numbers):
        for j,im in enumerate((original(n),plate(n),make(n))):out.paste(im.convert('RGB'),(256*j,128*idx))
        ImageDraw.Draw(out).text((0,128*idx),str(n),fill='yellow')
    out.save('typography_trial_v29.png')
