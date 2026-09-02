#!/usr/bin/env python3
from pathlib import Path
import re,argparse,sys
CMD=re.compile(rb'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?'); EV=re.compile(rb'(?m)^#\d{4}')
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('original'); ap.add_argument('localized'); a=ap.parse_args(); o,l=Path(a.original),Path(a.localized); bad=[]; n=0
 for op in sorted(o.rglob('*.sjs')):
  rel=op.relative_to(o); lp=l/rel
  if not lp.exists(): bad.append((rel,'eksik')); continue
  n+=1
  if rel.as_posix()=='credit.sjs': continue
  x,y=op.read_bytes(),lp.read_bytes()
  if CMD.findall(x)!=CMD.findall(y): bad.append((rel,'komut dizisi'))
  if EV.findall(x)!=EV.findall(y): bad.append((rel,'event kimlikleri'))
 print('kontrol edilen:',n,'sorun:',len(bad))
 for r,k in bad: print('HATA',r,k)
 sys.exit(1 if bad else 0)
if __name__=='__main__': main()
