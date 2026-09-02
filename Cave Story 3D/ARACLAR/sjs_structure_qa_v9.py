#!/usr/bin/env python3
"""Structural QA allowing the intentional ROMFS-only removal of <MNA commands."""
from pathlib import Path
import re,argparse,sys,csv
CMD=re.compile(rb'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?'); EV=re.compile(rb'(?m)^#\d{4}')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('original');ap.add_argument('localized');ap.add_argument('--report');a=ap.parse_args();o,l=Path(a.original),Path(a.localized);bad=[];rows=[];n=0;removed=0
 for op in sorted(o.rglob('*.sjs')):
  rel=op.relative_to(o);lp=l/rel
  if not lp.exists():bad.append((rel,'eksik'));continue
  n+=1
  if rel.as_posix()=='credit.sjs':continue
  x,y=op.read_bytes(),lp.read_bytes();xc=CMD.findall(x);yc=CMD.findall(y)
  xc_no_mna=[c for c in xc if c!=b'<MNA']; mna=xc.count(b'<MNA');removed+=mna
  if xc_no_mna!=yc:bad.append((rel,'komut dizisi (MNA disinda fark)'))
  if EV.findall(x)!=EV.findall(y):bad.append((rel,'event kimlikleri'))
  rows.append((str(rel),mna,len(xc),len(yc),'OK' if xc_no_mna==yc and EV.findall(x)==EV.findall(y) else 'HATA'))
 if a.report:
  with open(a.report,'w',encoding='utf-8',newline='') as f:
   w=csv.writer(f,delimiter='\t');w.writerow(['dosya','orijinal_MNA','orijinal_komut','yerel_komut','durum']);w.writerows(rows)
 print(f'kontrol_edilen={n} kasitli_MNA_kaldirma={removed} MNA_disinda_sorun={len(bad)}')
 for r,k in bad:print('HATA',r,k)
 sys.exit(1 if bad else 0)
if __name__=='__main__':main()
