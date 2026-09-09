#!/usr/bin/env python3
from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parents[1]
check=root/'CHECKSUMS.txt'
if not check.exists(): raise SystemExit('CHECKSUMS.txt bulunamadı')
bad=[];n=0
for line in check.read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    h,rel=line.split('  ',1);p=root/rel
    got=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'MISSING'
    n+=1
    if got!=h:bad.append((rel,h,got))
print(f'{n} dosya kontrol edildi; hata: {len(bad)}')
for x in bad:print(*x)
raise SystemExit(1 if bad else 0)
