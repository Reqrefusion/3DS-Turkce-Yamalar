#!/usr/bin/env python3
from pathlib import Path
import re, argparse, csv
CMD=re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?|#\d{4}')
# Exact English-origin line matches are useful because they don't mistake Turkish ASCII words for English.
def chunks(p,enc):
    t=p.read_bytes().decode(enc,'ignore'); t=CMD.sub('\n',t)
    return {x.strip() for x in t.splitlines() if re.search(r'[A-Za-z]{3}',x) and len(x.strip())>=3}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('original'); ap.add_argument('localized'); ap.add_argument('-o','--output',default='english_residue.tsv'); a=ap.parse_args()
    orig,loc=Path(a.original),Path(a.localized); rows=[]
    for op in orig.rglob('*.sjs'):
        rel=op.relative_to(orig); lp=loc/rel
        if not lp.exists(): continue
        for s in sorted(chunks(op,'cp1252') & chunks(lp,'cp1254')):
            rows.append((str(rel),s))
    with open(a.output,'w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','orijinalle_ayni_kalan_metin']); w.writerows(rows)
    print(len(rows),'satır inceleme listesine yazıldı:',a.output)
if __name__=='__main__': main()
