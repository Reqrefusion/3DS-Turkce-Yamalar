#!/usr/bin/env python3
"""Conservative Turkish deasciification residue audit using a Turkish word list.
Only reports words that are absent as written but have exactly one diacriticized
candidate after Turkish characters are folded to ASCII. It does not auto-edit.
"""
from pathlib import Path
import argparse,re,collections,csv
TRANS=str.maketrans({'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','â':'a','î':'i','û':'u','Ç':'c','Ğ':'g','İ':'i','I':'i','Ö':'o','Ş':'s','Ü':'u','Â':'a','Î':'i','Û':'u'})
TRLOW=str.maketrans({'İ':'i','I':'ı','Ş':'ş','Ğ':'ğ','Ü':'ü','Ö':'ö','Ç':'ç'})
def lower_tr(s): return s.translate(TRLOW).lower()
def key(s): return lower_tr(s.translate(TRANS))
IGNORE={'öldüğün'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('wordlist'); ap.add_argument('-o','--output',default='dictionary_residue.tsv'); a=ap.parse_args()
 ds=set(); rev=collections.defaultdict(set)
 for line in Path(a.wordlist).read_text('utf-8',errors='ignore').splitlines():
  w=line.strip()
  if re.fullmatch(r'[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]+',w):
   wl=lower_tr(w); ds.add(wl); rev[key(w)].add(wl)
 rows=[]; wr=re.compile(r'[A-Za-zÇĞİÖŞÜçğıöşüÂÎÛâîû]{5,}')
 root=Path(a.root)
 for p in sorted(root.rglob('*.sjs')):
  if p.name=='credit.sjs': continue
  t=p.read_bytes().decode('cp1254','surrogateescape')
  t=re.sub(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?',' ',t)
  for ln,line in enumerate(t.splitlines(),1):
   for m in wr.finditer(line):
    w=m.group(0); wl=lower_tr(w)
    if wl in ds or wl in IGNORE or w.isupper(): continue
    cs={x for x in rev.get(key(w),set()) if x!=wl and any(c in x for c in 'çğıöşüâîû')}
    if len(cs)==1: rows.append((p.relative_to(root).as_posix(),ln,w,next(iter(cs)),line.strip()))
 with open(a.output,'w',encoding='utf-8',newline='') as f:
  cw=csv.writer(f,delimiter='\t'); cw.writerow(['dosya','satir','mevcut','aday','baglam']); cw.writerows(rows)
 print('yüksek güvenli sözlük kalıntısı:',len(rows))
if __name__=='__main__': main()
