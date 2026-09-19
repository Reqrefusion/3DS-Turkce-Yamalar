#!/usr/bin/env python3
"""Teslim edilen ZIP çıkarıldıktan sonra bütünlük ve arşiv denetimi."""
import hashlib,json
from pathlib import Path
import drmario_tool as t
PKG=Path(__file__).resolve().parent.parent

def main():
 manifest=PKG/'DOSYA_DOGRULAMA_SHA256.txt'
 for row in manifest.read_text(encoding='utf-8').splitlines():
  digest,name=row.split('  ',1);p=PKG/name
  if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit('Dosya değişmiş veya eksik: '+name)
 tr=json.loads((PKG/'ceviri/metinler_tr.json').read_text(encoding='utf-8'));packs=list((PKG/'LayeredFS').rglob('main.lzss'))
 if len(packs)!=21:raise SystemExit('21 arşiv bekleniyor.')
 count=0
 for p in packs:
  ar=t.arcv_parse(t.sszl_unpack(p.read_bytes()))
  for e in ar['entries']:
   if e['name'] in tr:
    if t.msbt_texts(e['data'])!=tr[e['name']]:raise SystemExit('Metin farklı: '+str(p)+'/'+e['name'])
    count+=len(tr[e['name']])
   elif e['data'][:4]==b'SARC':
    s=t.sarc_parse(e['data'])
    if s['file_size']!=len(e['data']):raise SystemExit('SARC uzunluğu farklı')
 print(f'Bütünlük geçti. {len(packs)} arşiv açıldı; dokuz dilde toplam {count} metin doğrulandı.')
if __name__=='__main__':main()
