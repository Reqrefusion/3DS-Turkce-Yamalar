#!/usr/bin/env python3
from pathlib import Path
import argparse,math
try: from PIL import Image,ImageDraw
except ImportError: raise SystemExit('Pillow gerekli: python -m pip install Pillow')

def main():
    ap=argparse.ArgumentParser(description='PNG gliflerini tek önizleme sayfasında birleştirir')
    ap.add_argument('input');ap.add_argument('output');ap.add_argument('--cols',type=int,default=6);ap.add_argument('--scale',type=int,default=8);a=ap.parse_args()
    ps=sorted(Path(a.input).glob('*.png'))
    if not ps:raise SystemExit('PNG yok')
    ims=[Image.open(p).convert('L') for p in ps];w=max(i.width for i in ims)*a.scale+20;h=max(i.height for i in ims)*a.scale+36
    rows=math.ceil(len(ims)/a.cols);out=Image.new('L',(w*a.cols,h*rows),255);d=ImageDraw.Draw(out)
    for n,(p,im) in enumerate(zip(ps,ims)):
        x=(n%a.cols)*w;y=(n//a.cols)*h;out.paste(im.resize((im.width*a.scale,im.height*a.scale),Image.Resampling.NEAREST),(x+10,y+10));d.text((x+10,y+h-20),p.stem,fill=0)
    out.save(a.output);print(a.output)
if __name__=='__main__':main()
