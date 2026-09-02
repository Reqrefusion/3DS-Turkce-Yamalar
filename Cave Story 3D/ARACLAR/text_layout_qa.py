#!/usr/bin/env python3
"""SJS görünür metin parçalarında aşırı uzun satırları raporlar; otomatik sarma yapmaz."""
from pathlib import Path
import argparse,re,csv
CMD=re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--limit',type=int,default=42); ap.add_argument('-o','--output',default='text_layout_qa.tsv'); a=ap.parse_args(); root=Path(a.root); rows=[]
 for p in sorted(root.rglob('*.sjs')):
  if p.name=='credit.sjs': continue
  t=p.read_bytes().decode('cp1254','surrogateescape')
  # Komutlar metin kutusunda doğal sınır/pause olabilir; birleştirmeyiz.
  chunks=CMD.split(t)
  approx_line=1
  for chunk in chunks:
   for line in chunk.splitlines():
    v=line.strip()
    if v and not v.startswith('#') and not v.startswith('XX:') and 'Â' not in v and len(v)>a.limit:
     rows.append((p.relative_to(root).as_posix(),approx_line,len(v),v))
    approx_line += 1
 with open(a.output,'w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','yaklasik_satir','karakter','metin']); w.writerows(rows)
 print(f'{a.limit} karakteri aşan görünür satır:',len(rows))
if __name__=='__main__': main()
