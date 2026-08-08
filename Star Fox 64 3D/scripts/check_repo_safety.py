#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
BLOCKED_SUFFIXES={'.msbt','.msbp','.cia','.3ds','.cci','.cxi','.romfs'}
BLOCKED_NAMES={'Resources.zip'}
ignore_parts={'.git','dist','build','review','__pycache__'}
problems=[]
for p in ROOT.rglob('*'):
    if not p.is_file():
        continue
    rel=p.relative_to(ROOT)
    if any(part in ignore_parts for part in rel.parts):
        continue
    if p.name in BLOCKED_NAMES or p.suffix.lower() in BLOCKED_SUFFIXES:
        problems.append(rel.as_posix())
if problems:
    print('HATA: repoda oyun varlığı olabilecek yasaklı dosyalar bulundu:', file=sys.stderr)
    for x in problems: print(' - '+x, file=sys.stderr)
    raise SystemExit(1)
print('OK: repo kaynak paketinde Resources.zip/MSBT/MSBP/ROM türü oyun dosyası yok.')
