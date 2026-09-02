#!/usr/bin/env python3
"""Bilinen eski/yanlış terminoloji ve dil kalıntılarını SJS dosyalarında denetler."""
from pathlib import Path
import argparse,csv
BAD=[
 'Sakız Bazı','Sakız bazı','Sakız bazasi','Panzehiri doktora verdin',
 "Her Derde Deva'yi","Kutup Yıldızı'nin","Kutup Yıldızı'ni","Jenka'nin",
 'Yeryüzünden gelecek\r\nsaldırıya karşı','Yine mi dışarıda???','Bilinç... kayboluyor...',
 'SİZ İKİSİ BENİ DİNLİYOR MUSUNUZ','SIZ İKİSİ BENİ DİNLİYOR MUSUNUZ',
 'ASANSÖR INDIRILSIN MI?','Sistemi kapatma ve Nintendo 3DS',
 'Size yardım etmem.\r\nARAMIZDA KALSIN!','insanlara saldırmak istiyor',
 'beni başka bir Mimiga sanıp','geçmişte de ölmüş','Aptal ahmak!!',
]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('-o','--output',default='glossary_qa.tsv'); a=ap.parse_args(); root=Path(a.root); rows=[]
 for p in sorted(root.rglob('*.sjs')):
  if p.name=='credit.sjs': continue
  t=p.read_bytes().decode('cp1254','surrogateescape')
  for x in BAD:
   start=0
   while True:
    i=t.find(x,start)
    if i<0: break
    line=t.count('\n',0,i)+1; rows.append((p.relative_to(root).as_posix(),line,x)); start=i+1
 with open(a.output,'w',encoding='utf-8',newline='') as f:
  w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','satir','yasak_eski_ifade']); w.writerows(rows)
 print('eski/yanlış terim kalıntısı:',len(rows))
 for r in rows: print('KALINTI',*r)
if __name__=='__main__': main()
