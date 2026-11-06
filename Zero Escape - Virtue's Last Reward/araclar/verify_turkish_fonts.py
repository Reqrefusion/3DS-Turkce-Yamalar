#!/usr/bin/env python3
from pathlib import Path
import struct, sys, hashlib

REQUIRED = 'çğıöşüÇĞİÖŞÜ'

def parse_map(data: bytes):
    if len(data) < 24:
        raise ValueError('dosya çok kısa')
    magic, total, nlen = struct.unpack_from('<III', data, 0)
    o = 12 + nlen
    if o + 4 > len(data): raise ValueError('bozuk başlık')
    slen = struct.unpack_from('<I', data, o)[0]; o += 4 + slen
    if o + 4 > len(data): raise ValueError('bozuk string alanı')
    count = struct.unpack_from('<I', data, o)[0]; o += 4
    if o + count * 8 > len(data): raise ValueError('karakter tablosu dosya dışına taşıyor')
    entries=[]
    for _ in range(count):
        cp, idx = struct.unpack_from('<II', data, o); o += 8
        entries.append((cp, idx))
    return magic, total, entries

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '../fonts').resolve()
    files = sorted(root.glob('*.dat'))
    if not files:
        print('HATA: .dat bulunamadı:', root); return 2
    bad = 0
    for p in files:
        try:
            b=p.read_bytes(); magic,total,entries=parse_map(b)
            cps=[cp for cp,_ in entries]
            missing=[c for c in REQUIRED if ord(c) not in cps]
            dups=len(cps)-len(set(cps))
            ok=not missing and dups==0
            print(f"{'OK' if ok else 'HATA':4} {p.name:24} map={len(entries):4} duplicate={dups:2} missing={''.join(missing) or '-'} sha256={hashlib.sha256(b).hexdigest()}")
            bad += 0 if ok else 1
        except Exception as e:
            bad += 1; print('HATA',p.name,e)
    print(f'\nSonuç: {len(files)-bad}/{len(files)} font doğrulandı.')
    return 1 if bad else 0

if __name__=='__main__':
    raise SystemExit(main())
