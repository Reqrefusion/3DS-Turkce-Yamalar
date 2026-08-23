#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,json
ap=argparse.ArgumentParser(description='CEVIRI_KOLAY.csv içindeki Türkçe sütununu ana JSONL projeye geri birleştirir.')
ap.add_argument('project');ap.add_argument('easy_csv');ap.add_argument('output')
a=ap.parse_args(); changes={}
with open(a.easy_csv,encoding='utf-8-sig',newline='') as f:
 for r in csv.DictReader(f):changes[(r['file'],r['id'])]=r['turkce']
count=0
with open(a.project,encoding='utf-8') as fi,open(a.output,'w',encoding='utf-8',newline='') as fo:
 for line in fi:
  r=json.loads(line);k=(r.get('file'),r.get('id'))
  if r.get('kind')=='text' and k in changes and changes[k]!=r.get('translation'):
   r['translation']=changes[k];count+=1
  fo.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
print(f'Hazır: {a.output}; güncellenen kayıt: {count}')
