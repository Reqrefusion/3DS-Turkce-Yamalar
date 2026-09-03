#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import sys,struct,re,csv,argparse
try:
 from lz11_codec import decompress
 from bffnt_patch_tr_v2 import parse
except ImportError:
 sys.path.insert(0,'/mnt/data/v131x/Araclar/Font');from lz11_codec import decompress;from bffnt_patch_tr_v2 import parse
REQ='GgIiSsCcÇçAaÄä';TR='ĞğİıŞş'
def shash(name,m=0x65):
 h=0
 for b in name.encode():h=(h*m+b)&0xffffffff
 return h

def scan_one(args):
 p,root=args;p=Path(p);root=Path(root)
 try:d=decompress(p.read_bytes());e='<' if d[6:8]==b'\xff\xfe' else '>';hdr=struct.unpack_from(e+'H',d,4)[0];hsz,nodes,mult=struct.unpack_from(e+'HHI',d,hdr+4);no=hdr+hsz;do=struct.unpack_from(e+'I',d,12)[0]
 except Exception as ex:return []
 # infer embedded font names from FLYT references
 refs=set()
 for i in range(nodes):
  hh,a,st,en=struct.unpack_from(e+'IIII',d,no+i*16);dat=d[do+st:do+en]
  if dat[:4]==b'FLYT':
   for s in re.findall(rb'[A-Za-z0-9_./-]+\.bffnt',dat): refs.add(s.decode('ascii','ignore'))
 names={shash('font/'+n,mult):n for n in refs if n!='nintendo_NTLG-DB_002_40px.bffnt'}
 rows=[]
 for i in range(nodes):
  hh,a,st,en=struct.unpack_from(e+'IIII',d,no+i*16);dat=d[do+st:do+en]
  if dat[:4]!=b'FFNT':continue
  try:
   inf=parse(dat);mp=inf['mapping'];eligible=inf['fmt']==11 and all(ord(c) in mp for c in REQ);missing=''.join(c for c in TR if ord(c) not in mp);tr12=''.join(c for c in 'ÇçĞğİıÖöŞşÜü' if ord(c) in mp)
   finf=struct.unpack_from(inf['e']+'4sI4B2H4B3I',dat,20);pos=finf[-1]-8;scansec=uns=0
   while pos:
    magic,size,start,end,method,res,nxt=struct.unpack_from(inf['e']+'4sI4HI',dat,pos)
    if method==2:
     scansec+=1;q=pos+20;cnt=struct.unpack_from(inf['e']+'H',dat,q)[0];q+=2;cps=[struct.unpack_from(inf['e']+'H',dat,q+j*4)[0] for j in range(cnt)]
     if cps!=sorted(cps):uns+=1
    pos=nxt-8 if nxt else 0
   rows.append({'archive':str(p.relative_to(root)),'node':i,'sarc_hash':f'{hh:08X}','font_name':names.get(hh,''),'fmt':inf['fmt'],'cell':f"{inf['cw']}x{inf['ch']}",'latin_eligible':'YES' if eligible else 'NO','missing_TR6':missing,'present_TR12':tr12,'scan_sections':scansec,'unsorted_scan_sections':uns,'size':len(dat)})
  except Exception as ex:
   rows.append({'archive':str(p.relative_to(root)),'node':i,'sarc_hash':f'{hh:08X}','font_name':names.get(hh,''),'fmt':'ERR','cell':'','latin_eligible':'NO','missing_TR6':'ERR','present_TR12':'','scan_sections':0,'unsorted_scan_sections':0,'size':len(dat)})
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--layout-dir',required=True);ap.add_argument('--out',required=True);ap.add_argument('--workers',type=int,default=8);a=ap.parse_args();root=Path(a.layout_dir);files=list(root.rglob('*.Carc'));rows=[]
 with ProcessPoolExecutor(max_workers=a.workers) as ex:
  for f in as_completed([ex.submit(scan_one,(str(p),str(root))) for p in files]):rows.extend(f.result())
 rows.sort(key=lambda r:(r['archive'],r['node']))
 with open(a.out,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
 print('CARC',len(files),'FFNT',len(rows),'font_CARC',len(set(r['archive'] for r in rows)),'eligible',sum(r['latin_eligible']=='YES' for r in rows),'eligible_CARC',len(set(r['archive'] for r in rows if r['latin_eligible']=='YES')),'unsorted',sum(int(r['unsorted_scan_sections']) for r in rows))
if __name__=='__main__':main()
