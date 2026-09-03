#!/usr/bin/env python3
import argparse,struct,csv,sys
from pathlib import Path
from lz11_codec import decompress
from bffnt_patch_tr_fast import parse
TR='ÇçĞğİıÖöŞşÜü'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--original',required=True);ap.add_argument('--patched',required=True);ap.add_argument('--report',default='FONT_PATCH_VALIDATION.csv');a=ap.parse_args();origdir=Path(a.original);patdir=Path(a.patched);rows=[];fails=0
 for pp in sorted(patdir.glob('*.Carc')):
  op=origdir/pp.name
  if not op.exists():continue
  o=decompress(op.read_bytes());m=decompress(pp.read_bytes())
  if len(o)!=len(m):rows.append([pp.name,'SARC_SIZE','FAIL',len(o),len(m)]);fails+=1;continue
  e='<' if m[6:8]==b'\xff\xfe' else '>';hdr=struct.unpack_from(e+'H',m,4)[0];hsz,nodes,mult=struct.unpack_from(e+'HHI',m,hdr+4);nodeoff=hdr+hsz;doff=struct.unpack_from(e+'I',m,12)[0]
  for i in range(nodes):
   h,attr,st,en=struct.unpack_from(e+'IIII',m,nodeoff+i*16);aa,bb=doff+st,doff+en
   if o[aa:bb]==m[aa:bb]:continue
   if o[aa:aa+4]!=b'FFNT':rows.append([pp.name,f'NODE {i} {h:08X}','FAIL','font dışı node değişti','']);fails+=1;continue
   info=parse(m[aa:bb]);miss=''.join(ch for ch in TR if ord(ch) not in info['mapping']);suitable=all(ord(c) in info['mapping'] for c in 'GgIiSsCcÇç')
   ok=(not suitable) or not miss
   rows.append([pp.name,f'FONT {i} {h:08X}','PASS' if ok else 'FAIL','Eksik='+miss,'']);fails+=0 if ok else 1
 out=Path(a.report)
 with out.open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['archive','test','result','detail','extra']);w.writerows(rows)
 print('PASS' if fails==0 else 'FAIL', 'hata=',fails)
 raise SystemExit(1 if fails else 0)
if __name__=='__main__':main()
