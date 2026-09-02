#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw
import re
BASE=Path(__file__).resolve().parents[1]; DATA=BASE/'000400000004D200/romfs/data'; OUT=BASE/'ONIZLEMELER/metin_kutusu_ornekleri_v9.png'
def parse_font():
 t=(DATA/'font_batang.fnt').read_text('latin1'); chars={};kern={}
 for l in t.splitlines():
  if l.startswith('char id='):
   d={a:int(b) for a,b in re.findall(r'(\w+)=(-?\d+)',l)};chars[d['id']]=d
  elif l.startswith('kerning first='):
   d={a:int(b) for a,b in re.findall(r'(\w+)=(-?\d+)',l)};kern[(d['first'],d['second'])]=d['amount']
 return chars,kern
chars,kern=parse_font(); atlas=Image.open(DATA/'font_batang_0.tga').convert('RGBA')
def draw_text(im,text,x,y):
 prev=None
 for b in text.encode('cp1254'):
  if prev is not None:x+=kern.get((prev,b),0)
  d=chars[b]; g=atlas.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height']))
  im.alpha_composite(g,(x+d['xoffset'],y+d['yoffset']));x+=d['xadvance'];prev=b
SAMPLES=[
['+Kontrol Düğmesi\'nde Aşağı\'ya basarak','Kayıt Noktalarını kullanabilir, eşya','toplayabilir ve kapılardan geçebilirsin.'],
['Sevdiği hayat bir gecede','harabeye döndü...','...Yalnız kızgın küllerle örtüldü.'],
["Doktor'dan ilk kaçan Itoh'du;",'ama buradan fazla uzağa','gidemediğini düşünüyorum.'],
['Kaçtıktan sonra sen ve Kazuma,','dağların güvenli koynunda,','gözlerden uzak yaşadınız...'],
]
w=250; bh=60; canvas=Image.new('RGBA',(w,len(SAMPLES)*bh),(15,18,25,255));d=ImageDraw.Draw(canvas)
for i,lines in enumerate(SAMPLES):
 y0=i*bh; d.rectangle((2,y0+2,w-3,y0+bh-3),outline=(100,105,115,255),fill=(30,34,45,255))
 for j,line in enumerate(lines):draw_text(canvas,line,8,y0+8+j*16)
canvas.resize((w*3,len(SAMPLES)*bh*3),Image.Resampling.NEAREST).save(OUT)
print(OUT)
