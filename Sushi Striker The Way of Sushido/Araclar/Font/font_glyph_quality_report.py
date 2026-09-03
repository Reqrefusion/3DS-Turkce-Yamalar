#!/usr/bin/env python3
import argparse,struct,csv,statistics
from pathlib import Path
from lz11_codec import decompress
from bffnt_patch_tr_v2 import parse,extract_glyph
TR='ÇçĞğİıÖöŞşÜü'

def carc_fonts(path):
 d=decompress(path.read_bytes());e='<' if d[6:8]==b'\xff\xfe' else '>';hs=struct.unpack_from(e+'H',d,4)[0];do=struct.unpack_from(e+'I',d,12)[0];sf,n=struct.unpack_from(e+'HH',d,hs+4);no=hs+sf
 for i in range(n):
  h,a,st,en=struct.unpack_from(e+'IIII',d,no+i*16);b=d[do+st:do+en]
  if b[:4]==b'FFNT':yield i,h,b

def bbox_s(im):
 b=im.getbbox();return '' if not b else f'{b[0]},{b[1]},{b[2]},{b[3]}'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--patched',required=True);ap.add_argument('--report',required=True);a=ap.parse_args();root=Path(a.patched);rows=[]
 for p in sorted(root.rglob('*.Carc')):
  rel=p.relative_to(root)
  for node,h,b in carc_fonts(p):
   info=parse(b);m=info['mapping']
   if not all(ord(c) in m for c in TR):continue
   def g(c):return extract_glyph(b,info,m[ord(c)])
   tops=[g(c).getbbox()[1] for c in 'aceosuvx' if ord(c) in m and g(c).getbbox()]
   xh=statistics.median(tops) if tops else ''
   row={'archive':str(rel),'node':node,'hash':f'{h:08X}','cell':f"{info['cw']}x{info['ch']}",'baseline':info['baseline'],'xheight_top':xh}
   for c in 'GĞgğIİiıSŞsşCÇcçAÄaäOÖoöUÜuü':
    if ord(c) in m:
     idx=m[ord(c)];row[c+'_glyph']=idx;row[c+'_bbox']=bbox_s(g(c));row[c+'_width']=str(info['widths'].get(idx,''))
   row['dotless_i_distinct']='PASS' if g('i').tobytes()!=g('ı').tobytes() else 'FAIL'
   row['upper_accent_align']='PASS' if abs(g('Ğ').getbbox()[1]-g('Ä').getbbox()[1])<=2 and abs(g('İ').getbbox()[1]-g('Ä').getbbox()[1])<=2 else 'FAIL'
   row['lower_accent_align']='PASS' if abs(g('ğ').getbbox()[1]-g('ä').getbbox()[1])<=2 else 'FAIL'
   row['cedilla_align']='PASS' if abs(g('Ş').getbbox()[3]-g('Ç').getbbox()[3])<=1 and abs(g('ş').getbbox()[3]-g('ç').getbbox()[3])<=1 else 'FAIL'
   row['widths']='PASS' if all(info['widths'][m[ord(t)]]==info['widths'][m[ord(base)]] for t,base in [('Ğ','G'),('ğ','g'),('İ','I'),('ı','i'),('Ş','S'),('ş','s')]) else 'FAIL'
   rows.append(row)
 keys=[]
 for r in rows:
  for k in r:
   if k not in keys:keys.append(k)
 with Path(a.report).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 fails=sum(any(r[k]=='FAIL' for k in ['dotless_i_distinct','upper_accent_align','lower_accent_align','cedilla_align','widths']) for r in rows)
 print('fonts',len(rows),'quality_fail',fails)
 raise SystemExit(1 if fails else 0)
if __name__=='__main__':main()
