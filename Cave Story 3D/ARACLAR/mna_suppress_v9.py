#!/usr/bin/env python3
"""Suppress engine-owned English map-name banners by removing only <MNA commands.
The actual map-name table is not present in the supplied ROMFS. This is the stable ROMFS-only workaround.
"""
from pathlib import Path
import argparse,csv
def main():
 ap=argparse.ArgumentParser();base=Path(__file__).resolve().parents[1]
 ap.add_argument('--data',default=str(base/'000400000004D200/romfs/data'));ap.add_argument('--report',default=str(base/'RAPORLAR/MNA_KALDIRILANLAR_V9.tsv'));a=ap.parse_args()
 root=Path(a.data); rows=[];total=0
 for p in sorted(root.rglob('*.sjs')):
  if p.name=='credit.sjs':continue
  b=p.read_bytes();n=b.count(b'<MNA')
  if n:
   p.write_bytes(b.replace(b'<MNA',b''));rows.append((str(p.relative_to(root)),n));total+=n
 with open(a.report,'w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,delimiter='\t');w.writerow(['dosya','kaldirilan_MNA']);w.writerows(rows)
 print(f'files={len(rows)} removed_MNA={total}')
if __name__=='__main__':main()
