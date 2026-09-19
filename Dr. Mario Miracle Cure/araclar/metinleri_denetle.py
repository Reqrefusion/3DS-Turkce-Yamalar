#!/usr/bin/env python3
"""Satır, yaklaşık genişlik ve dinamik işaret denetimi."""
import json
from pathlib import Path
from PIL import ImageFont
from yamayi_olustur import placeholders
PKG=Path(__file__).resolve().parent.parent

def main():
 tr=json.loads((PKG/'ceviri/metinler_tr.json').read_text(encoding='utf-8'))
 rows=json.loads((PKG/'ceviri/metin_denetimi.json').read_text(encoding='utf-8'))['metinler']
 font=ImageFont.truetype(str(PKG/'araclar/fontlar/Duz.ttf'),100);errors=[];multi=0
 expected={}
 for r in rows:expected[r['dosya']]=expected.get(r['dosya'],0)+1
 if {k:len(v) for k,v in tr.items()}!=expected:raise SystemExit('MSBT dosyaları veya giriş sayıları değişmiş.')
 for r in rows:
  name=r['dosya'];i=r['indeks'];s=tr[name][i];en=r['ozgun'];tag=f'{name}:{i}'
  if placeholders(s)!=placeholders(en):errors.append(tag+' değişken işaretleri farklı')
  if any(len(x.strip())==1 and x.strip().isalpha() for x in s.splitlines()):errors.append(tag+' tek harflik satır')
  if '\n' in en or '\n' in s:
   multi+=1
   if len(s.split('\n'))>len(en.split('\n')):errors.append(tag+' satır sayısı özgün metni aşıyor')
   if max(map(font.getlength,s.split('\n')))>max(map(font.getlength,en.split('\n')))+.02:errors.append(tag+' yaklaşık satır genişliği özgün metni aşıyor')
  if '%ls' in s and any('%ls' in line and line.strip()!='%ls' for line in s.splitlines()):errors.append(tag+' oyuncu adı ayrı satırda olmalı')
 if errors:raise SystemExit('\n'.join(errors))
 print(f'{len(rows)} metin; {multi} çok satırlı giriş: kontroller geçti. Genişlik ölçümü tahminidir.')
if __name__=='__main__':main()
