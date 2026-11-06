#!/usr/bin/env python3
from pathlib import Path
import argparse,sys,struct,subprocess,shutil
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from aat3ds_tr_v3 import parse_pack_inc,lz11_decompress,lz11_compress
from bch_utils import parse_bch_textures,decode_texture,replace_texture
COPY={8515:2683,11529:2683,8516:2684,11530:2684,8531:2699,11545:2699,8532:2700,11546:2700,8546:2714,11561:2714,8547:2715,11563:2715}
SAI10=[2691,8523,11537];CHECK=[6873,9709];EVENT=[2707,8539,11554];QUIT=[11562]
def findfont(bold=True,italic=False):
 c=[]
 if sys.platform.startswith('win'):
  c=[Path('C:/Windows/Fonts/arialbi.ttf' if italic else 'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf')]
 else:
  c=[Path('/usr/share/fonts/truetype/croscore/Arimo-BoldItalic.ttf' if italic else '/usr/share/fonts/truetype/croscore/Arimo-Bold.ttf' if bold else '/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf'),Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf')]
 for p in c:
  if p.exists():return p
 raise SystemExit('Arial/Arimo/Liberation Sans fontu bulunamadı. -- Bu araç font dosyası dağıtmaz; sistem fontu kullanır.')
def first(raw,name):
 g=next(x for x in parse_bch_textures(raw) if x['name'].lower()==name.lower());return g['textures'][0]
def patch_sai10(raw):
 t=first(raw,'sai_10u');im=decode_texture(raw,t).convert('RGBA');d=ImageDraw.Draw(im);f=ImageFont.truetype(str(findfont()),20)
 for off,bg,stroke in [(0,(121,47,0,255),(65,22,0,255)),(512,(250,176,11,255),(120,57,0,255))]:
  for x0,y0,x1,y1,text in [(2,245+off,138,275+off,'Git'),(142,245+off,278,275+off,'İncele'),(2,285+off,138,315+off,'Sun'),(142,285+off,278,315+off,'Konuş')]:
   d.rectangle((x0+4,y0+4,x1-4,y1-4),fill=bg);bb=d.textbbox((0,0),text,font=f,stroke_width=2);tw,th=bb[2]-bb[0],bb[3]-bb[1]
   d.text(((x0+x1-tw)//2,(y0+y1-th)//2-bb[1]),text,font=f,fill='white',stroke_width=2,stroke_fill=stroke)
 return replace_texture(raw,t,im)
def patch_check(raw):
 t=first(raw,'btn34');old=decode_texture(raw,t);im=Image.new('RGBA',old.size,(255,255,255,0));d=ImageDraw.Draw(im);f=ImageFont.truetype(str(findfont()),17)
 for y,st in [(1,(255,115,47,255)),(33,(117,49,0,255))]:
  text='İNCELE';bb=d.textbbox((0,0),text,font=f,stroke_width=2);d.text((2,y-bb[1]),text,font=f,fill='white',stroke_width=2,stroke_fill=st)
 return replace_texture(raw,t,im)
def patch_event(raw):
 t=first(raw,'sai_1du');im=decode_texture(raw,t).convert('RGBA');d=ImageDraw.Draw(im);d.rectangle((18,3,110,28),fill=(242,242,242,255));f=ImageFont.truetype(str(findfont(False)),20);text='Olay';bb=d.textbbox((0,0),text,font=f);d.text(((128-(bb[2]-bb[0]))//2,(32-(bb[3]-bb[1]))//2-bb[1]),text,font=f,fill=(98,47,30,255));return replace_texture(raw,t,im)
def patch_quit(raw):
 t=first(raw,'sai_22_');im=decode_texture(raw,t).convert('RGBA');d=ImageDraw.Draw(im);bg=(98,24,24,255);d.rectangle((55,14,266,64),fill=bg);d.rectangle((55,70,266,108),fill=bg);fi=ImageFont.truetype(str(findfont(True,True)),40);fs=ImageFont.truetype(str(findfont()),23)
 for text,font,cy in [('ÇIKIŞ',fi,40),('Oyundan çık?',fs,91)]:
  bb=d.textbbox((0,0),text,font=font,stroke_width=2);x=160-(bb[2]-bb[0])//2;y=cy-(bb[3]-bb[1])//2-bb[1];d.text((x,y),text,font=font,fill='white',stroke_width=4,stroke_fill=(75,35,15,255));d.text((x,y),text,font=font,fill='white',stroke_width=2,stroke_fill=(79,168,35,255))
 return replace_texture(raw,t,im)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('pack');ap.add_argument('inc');ap.add_argument('out_pack');ap.add_argument('out_inc');a=ap.parse_args();pack=Path(a.pack).read_bytes();inc=Path(a.inc).read_bytes();recs=parse_pack_inc(inc)
 def raw(i):r=recs[i];return lz11_decompress(pack,r['offset'])[0]
 repl={d:raw(s) for d,s in COPY.items()};x=patch_sai10(raw(SAI10[0]));repl.update({i:x for i in SAI10});repl.update({i:patch_check(raw(i)) for i in CHECK});x=patch_event(raw(EVENT[0]));repl.update({i:x for i in EVENT});repl[11562]=patch_quit(raw(11562))
 # straightforward portable rebuild; only 21 entries recompressed.
 out=bytearray();oi=bytearray()
 for r in recs:
  i=r['index'];off=len(out)
  if i in repl:blob=lz11_compress(repl[i]);dec=len(repl[i]);comp=len(blob)
  else:blob=pack[r['offset']:r['offset']+r['compressed']];dec=r['decompressed'];comp=r['compressed']
  out+=blob
  while len(out)%4:out.append(0)
  oi+=struct.pack('<QIII',off,dec,comp,r['ident'])
 Path(a.out_pack).write_bytes(out);Path(a.out_inc).write_bytes(oi);print('Tamam: 21 UI entry güncellendi.')
if __name__=='__main__':main()
