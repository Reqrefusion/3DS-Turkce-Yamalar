#!/usr/bin/env python3
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).parent))
from mh4_lmd_tool_v3 import ArcFile,LmdFile
P=Path('/mnt/data/v7work/patched/eng/data/core_end2.arc')
a=ArcFile.parse(P.read_bytes()); raw=a.entries[139].decompress(); l=LmdFile.parse(raw)
mp=str.maketrans({'Ō':'G','ō':'g','ˇ':'I','˘':'i','Ū':'S','¿':'s'})
trans={}; counts={k:0 for k in 'Ōōˇ˘Ū¿'}
for s in l.strings:
    for k in counts: counts[k]+=s.text.count(k)
    n=s.text.translate(mp)
    if n!=s.text: trans[s.index]=n
new=l.rebuild(trans)
pre=[e.decompress() for e in a.entries]
arc=a.build({139:new}); b=ArcFile.parse(arc)
for i,e in enumerate(b.entries):
    got=e.decompress()
    if i==139:
        if got!=new: raise SystemExit('staffroll mismatch')
    elif got!=pre[i]: raise SystemExit(f'unexpected entry change {i}')
P.write_bytes(arc)
report={'staffroll_entry':139,'strings_changed':len(trans),'safe_donor_counts_replaced':counts,'note':'Credits-only fallback; end_font LFD/TEX remain byte-identical.'}
Path('/mnt/data/v7work/staffroll_fallback_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
