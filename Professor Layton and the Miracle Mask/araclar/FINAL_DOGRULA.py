#!/usr/bin/env python3
from pathlib import Path
import sys,hashlib,struct,tempfile,shutil,subprocess
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'font'))
from xfsa_extract import parse
from xpck_extract import parse as xpck_extract
from fnt01_parse import parse as fnt_parse
root=HERE.parent
arc=root/'hazir'/'romfs'/'lt5'/'arc'
for fn,expected in [('lt5_a.fa',1323),('lt5_uk.fa',2857)]:
 p=arc/fn;_,fs=parse(str(p));assert len(fs)==expected,(fn,len(fs));print(fn,'OK',len(fs),'üye',hashlib.sha256(p.read_bytes()).hexdigest())
with tempfile.TemporaryDirectory() as td:
 td=Path(td); b=(arc/'lt5_a.fa').read_bytes();_,fs=parse(str(arc/'lt5_a.fa'))
 for n,p,s,i in fs:
  if n in ('fnt/[eu]/nrm.xf','fnt/[eu]/sml.xf'):
   xf=td/Path(n).name;xf.write_bytes(b[p:p+s]);ex=td/(xf.stem+'_x');ex.mkdir();xpck_extract(str(xf),str(ex));f=fnt_parse(str(ex/'FNT.bin'));c={z['cp'] for z in f['infos']};assert all(x in c for x in range(0xE000,0xE012));print(n,'Türkçe PUA18 OK')
print('FINAL DOGRULAMA: OK')
