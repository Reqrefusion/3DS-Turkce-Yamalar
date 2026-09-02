#!/usr/bin/env python3
"""Cave Story 3D TR v6 birleşik son QA.

İngilizce ROMFS data kökü ile Türkçe data kökünü karşılaştırır.
"""
from pathlib import Path
import argparse,re,sys
try:
 from PIL import Image
except Exception:
 Image=None
CMD=re.compile(rb'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
EV=re.compile(rb'(?m)^#\d{4}')
BR=re.compile(br'\[([^\]]*)\]')
IMAGES=['font_batang_0.tga','loading.pbm','title.pbm','title.tga','splash_legal_01.tga','splash_pixel_01.tga','textbox.pbm','textbox.tga','caret.pbm','caret.tga','minimapframe.pbm','pixel.bmp']
ROLE_TERMS=['CAST','FROM THE SURFACE','MIMIGA VILLAGE','BUSHLANDS','SAND ZONE','LABYRINTH','PLANTATION','VILLAINS','MONSTERS','BOSSES','CREATED BY','EXECUTIVE PRODUCER','DEVELOPMENT DIRECTOR','LEAD PROGRAMMER','PROGRAMMERS','ENVIRONMENTAL ARTISTS','CONCEPT ARTISTS','CHARACTER ANIMATORS','QUALITY ASSURANCE','Thanks for Playing']

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('english'); ap.add_argument('turkish'); a=ap.parse_args(); e=Path(a.english); t=Path(a.turkish); problems=[]
 # SJS structure/event ids
 count=0
 for ep in sorted(e.rglob('*.sjs')):
  rel=ep.relative_to(e); tp=t/rel
  if not tp.exists(): problems.append(f'Eksik SJS: {rel}'); continue
  count+=1
  if rel.as_posix()=='credit.sjs': continue
  x,y=ep.read_bytes(),tp.read_bytes()
  if CMD.findall(x)!=CMD.findall(y): problems.append(f'Komut farkı: {rel}')
  if EV.findall(x)!=EV.findall(y): problems.append(f'Event farkı: {rel}')
 # credit binary skeleton
 x=(e/'credit.sjs').read_bytes(); y=(t/'credit.sjs').read_bytes()
 if BR.sub(b'[]',x)!=BR.sub(b'[]',y): problems.append('credit.sjs bracket dışı yapı farklı')
 if x.count(b'\xC2')!=32 or y.count(b'\xC2')!=32: problems.append('credit.sjs 0xC2 sayısı farklı')
 # line length
 text_long=0
 ctext=re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
 for p in t.rglob('*.sjs'):
  if p.name=='credit.sjs': continue
  s=p.read_bytes().decode('cp1254','surrogateescape')
  for chunk in ctext.split(s):
   for line in chunk.splitlines():
    v=line.strip()
    if v and not v.startswith('#') and not v.startswith('XX:') and 'Â' not in v and len(v)>42: text_long+=1
 if text_long: problems.append(f'42 karakter üstü görünür satır: {text_long}')
 # credits role residue
 role_hits=0
 for p in t.glob('credits_text*.txt'):
  s=p.read_bytes().decode('cp1254','surrogateescape')
  role_hits+=sum(term in s for term in ROLE_TERMS)
 if role_hits: problems.append(f'Jenerik İngilizce rol kalıntısı: {role_hits}')
 # image mode/size for localized image set
 image_checked=0
 if Image:
  for rel in IMAGES:
   ep=e/rel; tp=t/rel
   if ep.exists() and tp.exists():
    with Image.open(ep) as a1, Image.open(tp) as b1:
     image_checked+=1
     if (a1.size,a1.mode,a1.info.get('bits'))!=(b1.size,b1.mode,b1.info.get('bits')):
      problems.append(f'Görsel biçim farkı: {rel}')
 print(f'SJS: {count}/113')
 print('credit 0xC2: İngilizce',x.count(b'\xC2'),'Türkçe',y.count(b'\xC2'))
 print('42+ görünür satır:',text_long)
 print('jenerik İngilizce rol kalıntısı:',role_hits)
 print('görsel biçim kontrolü:',image_checked)
 print('SONUÇ:', 'TEMİZ' if not problems else 'SORUN VAR')
 for z in problems: print('HATA:',z)
 sys.exit(1 if problems else 0)
if __name__=='__main__': main()
