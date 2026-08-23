#!/usr/bin/env python3
from pathlib import Path
import sys,tempfile,subprocess,csv,json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'font'))
from xfsa_extract import parse

def extract(fa,out):
 b=Path(fa).read_bytes(); _,files=parse(str(fa)); roots={}
 for n,p,s,i in files:
  n=n.replace('\\','/')
  if n.startswith('txt/') and n.lower().endswith('.xs'):
   parts=n.split('/'); lang=parts[1]; rel='/'.join(parts[2:]); d=out/lang; dst=d/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(b[p:p+s]); roots[lang]=d
 return roots

def main():
 import argparse
 ap=argparse.ArgumentParser(description='Bir veya daha fazla Level-5 XFSA dil arşivinden XSCR metinlerini çıkarıp karşılaştırmalı CSV oluşturur.')
 ap.add_argument('archives',nargs='+'); ap.add_argument('-o','--output',default='DIL_REFERANS.csv')
 a=ap.parse_args(); projects={}
 with tempfile.TemporaryDirectory(prefix='layton_lang_') as td:
  td=Path(td)
  for fa in a.archives:
   roots=extract(Path(fa),td/Path(fa).stem)
   for lang,root in roots.items():
    pj=td/f'{Path(fa).stem}_{lang}.jsonl'
    subprocess.run([sys.executable,str(HERE/'xs'/'arac'/'layton_xs_tool.py'),'export',str(root),str(pj)],check=True,stdout=subprocess.DEVNULL)
    data={}
    for line in pj.open(encoding='utf-8'):
     r=json.loads(line)
     if r.get('kind')=='text': data[(r['file'],r['id'])]=r['original']
    projects[f'{Path(fa).stem}:{lang}']=data
  keys=sorted(set().union(*(d.keys() for d in projects.values()))) if projects else []
  with open(a.output,'w',encoding='utf-8-sig',newline='') as f:
   cols=['file','id']+list(projects)
   w=csv.writer(f);w.writerow(cols)
   for k in keys:w.writerow([k[0],k[1]]+[projects[c].get(k,'') for c in projects])
  print(f'Hazır: {a.output} ({len(keys)} kayıt, {len(projects)} dil/arşiv)')
if __name__=='__main__':main()
