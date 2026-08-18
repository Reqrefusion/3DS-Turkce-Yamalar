#!/usr/bin/env python3
from pathlib import Path
import csv,importlib.util,re,sys
ROOT=Path(__file__).resolve().parent
TOOL=ROOT/'tools/rhm_tr_text_tool.py'; BUILD=ROOT/'build/pajama.zlib'; PROJECT=ROOT/'project/EUENmessage/pajama_sarc/arc'
spec=importlib.util.spec_from_file_location('rhmv22',TOOL); r=importlib.util.module_from_spec(spec); sys.modules['rhmv22']=r; spec.loader.exec_module(r)
def clean(s): return re.sub(r'\[\[.*?\]\]','',s)
sarc=r.Sarc(r.read_wrapped_zlib(BUILD)); files=sarc.files(); inj=unk=mis=tok=rt=long=phys=0
for table in sorted(PROJECT.rglob('*.msbt.tsv')):
 parts=table.parts; k=parts.index('pajama_sarc'); internal='/'.join(parts[k+1:])[:-4]
 with table.open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
 for row in rows:
  if '\n' in row['Turkish'] or '\r' in row['Turkish']: phys+=1
 if internal not in files: unk+=len(rows); continue
 b=files[internal]; entries=r.msbt_entries(b); emap={lab:text for _,lab,text in entries}; sec,_=r.msbt_sections(b); raws=r.parse_txt2_raw(b,sec)
 for (_,lab,text),raw in zip(entries,raws):
  try:
   if r.editable_to_raw(r.raw_to_editable(raw,sec),sec)!=raw: rt+=1
  except Exception: rt+=1
 for row in rows:
  if row['label'] not in emap: unk+=1; continue
  inj+=1; tr=row['Turkish']; got=emap[row['label']]
  if got!=tr: mis+=1
  if r.protected_tokens(got)!=r.protected_tokens(tr): tok+=1
  for line in clean(tr).split('\\n'):
   if len(line)>52: long+=1
print('RHM TR v22 bağımsız metin doğrulaması')
print('Enjekte edilebilir:',inj,'referans-only:',unk,'fark:',mis,'token:',tok,'roundtrip:',rt,'>52:',long,'fiziksel newline:',phys)
if (inj,unk)!=(5715,2) or mis or tok or rt or long or phys: raise SystemExit(1)
print('SONUÇ: TEMİZ')
