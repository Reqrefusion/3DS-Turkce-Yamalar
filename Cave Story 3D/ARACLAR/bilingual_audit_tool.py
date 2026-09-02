#!/usr/bin/env python3
"""İngilizce orijinal ile yerelleştirilmiş SJS metin aralıklarını komutlara göre hizalar.
Komut sırası aynıysa görünür metin parçaları güvenli biçimde yan yana denetlenebilir.
"""
from pathlib import Path
import argparse,re,csv,sys
CMD=re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
def load(p,enc): return p.read_bytes().decode(enc,'surrogateescape')
def safe(s):
    return ''.join((f'\\x{ord(c)-0xDC00:02X}' if 0xDC80 <= ord(c) <= 0xDCFF else c) for c in s)
def split(t):
    cmds=CMD.findall(t); txt=CMD.split(t); return cmds,txt
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('original'); ap.add_argument('localized'); ap.add_argument('-o','--output',default='bilingual_audit.tsv'); a=ap.parse_args()
    o,l=Path(a.original),Path(a.localized); rows=[]; bad=[]
    for op in sorted(o.rglob('*.sjs')):
        rel=op.relative_to(o); lp=l/rel
        if not lp.exists(): bad.append((str(rel),'eksik')); continue
        if rel.as_posix()=='credit.sjs': continue
        ec,et=split(load(op,'cp1252')); tc,tt=split(load(lp,'cp1254'))
        if ec!=tc or len(et)!=len(tt): bad.append((str(rel),'komut hizası')); continue
        for i,(e,t) in enumerate(zip(et,tt)):
            if e.strip() or t.strip(): rows.append((rel.as_posix(),i,safe(e).replace('\r','\\r').replace('\n','\\n'),safe(t).replace('\r','\\r').replace('\n','\\n')))
    with open(a.output,'w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','parca','ingilizce','turkce']); w.writerows(rows)
    print('hizalanan parça:',len(rows),'sorunlu dosya:',len(bad),'çıktı:',a.output)
    for x in bad: print('HATA',*x)
    sys.exit(1 if bad else 0)
if __name__=='__main__': main()
