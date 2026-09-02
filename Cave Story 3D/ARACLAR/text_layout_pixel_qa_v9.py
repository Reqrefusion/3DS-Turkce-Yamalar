#!/usr/bin/env python3
from pathlib import Path
import argparse,re,csv
CMD=re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
def load_font(p):
 t=p.read_text('latin1'); chars={}; kern={}
 for l in t.splitlines():
  if l.startswith('char id='):
   d={a:int(b) for a,b in re.findall(r'(\w+)=(-?\d+)',l)}; chars[d['id']]=d
  elif l.startswith('kerning first='):
   d={a:int(b) for a,b in re.findall(r'(\w+)=(-?\d+)',l)}; kern[(d['first'],d['second'])]=d['amount']
 return chars,kern
def width(s,chars,kern):
 w=0;prev=None
 for b in s.encode('cp1254','replace'):
  if prev is not None:w+=kern.get((prev,b),0)
  w+=chars.get(b,{'xadvance':7})['xadvance'];prev=b
 return w
def main():
 ap=argparse.ArgumentParser(); base=Path(__file__).resolve().parents[1]
 ap.add_argument('--data',default=str(base/'000400000004D200/romfs/data')); ap.add_argument('--threshold',type=int,default=220); ap.add_argument('--report',default=str(base/'RAPORLAR/SATIR_PIXEL_QA_V9.tsv')); a=ap.parse_args()
 root=Path(a.data); chars,kern=load_font(root/'font_batang.fnt'); rows=[]; over3=[]; maxw=0
 for p in sorted(root.rglob('*.sjs')):
  if p.name in {'credit.sjs','head.sjs'}: continue
  txt=p.read_bytes().decode('cp1254','surrogateescape'); frags=CMD.split(txt)
  for fi,frag in enumerate(frags):
   lines=[]
   for ln in frag.replace('\r','').split('\n'):
    s=ln.strip()
    if not s or s.startswith('#'): continue
    # skip obvious technical/debug fragments
    if re.fullmatch(r'[0-9A-Za-z:_+\- ]{1,40}',s) and (':' in s or re.match(r'^\d',s)):
     continue
    ww=width(s,chars,kern); maxw=max(maxw,ww); lines.append((s,ww))
    if ww>a.threshold: rows.append((str(p.relative_to(root)),fi,ww,s))
   if len(lines)>3: over3.append((str(p.relative_to(root)),fi,len(lines),' | '.join(x[0] for x in lines)))
 with open(a.report,'w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,delimiter='\t');w.writerow(['tip','dosya','fragment','deger','metin'])
  for r in rows:w.writerow(['GENIS_SATIR',*r])
  for r in over3:w.writerow(['4PLUS_SATIR',*r])
 print(f'max_width={maxw} over_{a.threshold}={len(rows)} chunks_over_3={len(over3)}')
 for r in rows: print('WIDE',r)
 for r in over3: print('4+',r)
if __name__=='__main__':main()
