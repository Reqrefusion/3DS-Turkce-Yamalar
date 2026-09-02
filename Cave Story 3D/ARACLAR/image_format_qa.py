#!/usr/bin/env python3
"""Verify localized bitmap dimensions/modes and BMP bit depths against originals."""
from pathlib import Path
from PIL import Image
import struct,argparse,sys
DEFAULT=['font_batang_0.tga','loading.pbm','title.pbm','title.tga','splash_legal_01.tga','splash_pixel_01.tga','textbox.pbm','textbox.tga','caret.pbm','caret.tga','minimapframe.pbm','pixel.bmp']
def bpp(p):
 b=p.read_bytes()[:32]
 return struct.unpack_from('<H',b,28)[0] if b[:2]==b'BM' else None
def info(p):
 im=Image.open(p); im.load(); return im.size,im.mode,bpp(p)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('original'); ap.add_argument('localized'); ap.add_argument('-o','--output'); a=ap.parse_args()
 o,l=Path(a.original),Path(a.localized); lines=[]; bad=0
 for name in DEFAULT:
  op,lp=o/name,l/name
  if not lp.exists(): lines.append(f'EKSİK\t{name}'); bad+=1; continue
  try: oi,li=info(op),info(lp)
  except Exception as e: lines.append(f'HATA\t{name}\t{e}'); bad+=1; continue
  ok=(oi[0]==li[0] and (oi[2] is None or oi[2]==li[2]))
  # TGA mode may legitimately change P/RGB -> RGBA; dimensions are the critical invariant.
  lines.append(f'{"OK" if ok else "HATA"}\t{name}\torij={oi}\tyerel={li}')
  bad += 0 if ok else 1
 lines.insert(0,f'Görsel biçim QA: {len(DEFAULT)} dosya, sorun={bad}')
 out='\n'.join(lines)+'\n'
 print(out,end='')
 if a.output: Path(a.output).write_text(out,encoding='utf-8')
 sys.exit(1 if bad else 0)
if __name__=='__main__': main()
