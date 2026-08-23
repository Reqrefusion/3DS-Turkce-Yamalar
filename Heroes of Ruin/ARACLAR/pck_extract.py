#!/usr/bin/env python3
import struct,argparse
from pathlib import Path

def parse_pck(path):
 b=Path(path).read_bytes()
 if b[:4]!=b'AKPK': raise ValueError('not AKPK')
 en='<'
 header_size,flag,sec1,sec2,sec3=struct.unpack_from(en+'IIIII',b,4)
 pos=24; sec4=0
 if sec1+sec2+sec3+0x10 < header_size:
  sec4=struct.unpack_from(en+'I',b,pos)[0]; pos+=4
 # languages section starts pos
 s1start=pos; nlangs=struct.unpack_from(en+'I',b,pos)[0]; pos+=4
 pairs=[]
 for _ in range(nlangs):
  off,lid=struct.unpack_from(en+'II',b,pos); pos+=8; pairs.append((off,lid))
 langs={}
 for off,lid in pairs:
  p=s1start+off
  end=b.find(b'\0',p)
  langs[lid]=b[p:end].decode('utf-8','replace')
 pos=s1start+sec1
 def table(pos,size):
  n=struct.unpack_from(en+'I',b,pos)[0]; start=pos; pos+=4
  es=(size-4)//n if n else 0
  out=[]
  for i in range(n):
   if es==20:
    id,block,sz,off,lid=struct.unpack_from(en+'IIIII',b,pos)
   elif es==24:
    id,block=struct.unpack_from(en+'II',b,pos); sz=struct.unpack_from(en+'Q',b,pos+8)[0]; off,lid=struct.unpack_from(en+'II',b,pos+16)
   else: raise ValueError(f'entry size {es}')
   if block: off*=block
   out.append({'id':id,'block':block,'size':sz,'offset':off,'lang_id':lid,'lang':langs.get(lid,str(lid))})
   pos+=es
  return out,start+size
 banks,pos=table(pos,sec2)
 sounds,pos=table(pos,sec3)
 externals=[]
 if sec4:
  externals,pos=table(pos,sec4)
 return b,langs,banks,sounds,externals

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('pck'); ap.add_argument('--id',type=int); ap.add_argument('--out'); a=ap.parse_args()
 b,langs,banks,sounds,ext=parse_pck(a.pck)
 print('langs',langs,'banks',len(banks),'sounds',len(sounds),'ext',len(ext))
 if a.id is not None:
  e=next(x for x in sounds if x['id']==a.id); print(e, b[e['offset']:e['offset']+4])
  if a.out: Path(a.out).write_bytes(b[e['offset']:e['offset']+e['size']])
if __name__=='__main__': main()
