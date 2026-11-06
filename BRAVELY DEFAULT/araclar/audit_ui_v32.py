#!/usr/bin/env python3
from pathlib import Path
import sys,json
from collections import defaultdict
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
from bravely_ui_tools import DarcArchive,bclyt_entries,patch_cfnt_turkish,make_text_width_fn
from translations_tr import translate_ui
UI=Path('/mnt/data/work_v2/ui_lang_extract/UI_en'); LR=UI.parent
langs=['UI_de','UI_es','UI_fr','UI_it']
cache={}
localized=[]; missing=[]
for src in sorted(UI.rglob('*')):
 if not src.is_file() or src.name in ('crowd.fs','index.fs'): continue
 rel=str(src.relative_to(UI)); data=src.read_bytes()
 if data[:4]!=b'darc': continue
 try: ea=DarcArchive(data); ef=dict(ea.files())
 except: continue
 langfiles={}
 for lang in langs:
  p=LR/lang/rel
  try: langfiles[lang]=dict(DarcArchive(p.read_bytes()).files())
  except: langfiles[lang]={}
 for ip,b in ef.items():
  if b[:4]!=b'CLYT': continue
  enents=bclyt_entries(b)
  otherents={L:{} for L in langs}
  for lang in langs:
   ob=langfiles[lang].get(ip)
   if ob and ob[:4]==b'CLYT': otherents[lang]={(e['pane'],e['ordinal']):e['text'] for e in bclyt_entries(ob)}
  for e in enents:
   key=(e['pane'],e['ordinal']); old=e['text']
   if not any(key in otherents[L] and otherents[L][key]!=old for L in langs): continue
   tr=translate_ui(old,e['pane'],e['ordinal'],rel+'::'+ip)
   row={'archive':rel,'inner':ip,'pane':e['pane'],'ordinal':e['ordinal'],'english':old,'turkish':tr}
   localized.append(row)
   if tr is None or tr==old: missing.append(row)

rep={'localized_occurrences':len(localized),'localized_unique_english':len({x['english'] for x in localized}),
     'translated_occurrences':len(localized)-len(missing),'missing_occurrences':len(missing),
     'missing_unique':sorted({x['english'] for x in missing}), 'missing':missing}
(HERE/'UI_TRANSLATION_AUDIT.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in rep.items() if k!='missing'},ensure_ascii=False,indent=2))
