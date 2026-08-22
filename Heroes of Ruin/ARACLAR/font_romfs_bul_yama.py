from __future__ import annotations
import argparse
from pathlib import Path
from hor_font_patch import patch_font


def main():
    ap=argparse.ArgumentParser(description='RomFS icinde BCFNT/BCFNT_ bul, Turkce fontu ayni goreli konuma yaz')
    ap.add_argument('romfs')
    ap.add_argument('output_romfs')
    a=ap.parse_args()
    src=Path(a.romfs); out=Path(a.output_romfs)
    cand=[p for p in src.rglob('*') if p.is_file() and ('.bcfnt' in p.name.lower() or p.suffix.lower()=='.bcfnt_')]
    if not cand:
        raise SystemExit('BCFNT/BCFNT_ bulunamadi.')
    if len(cand)>1:
        print('Birden fazla font bulundu:')
        for p in cand: print(' -',p.relative_to(src))
        raise SystemExit('Tek font kalacak sekilde yolu elle belirt veya hor_font_patch.py kullan.')
    p=cand[0]
    raw, packed, _=patch_font(p.read_bytes())
    rel=p.relative_to(src)
    target=out/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if p.name.lower().endswith('_'):
        target.write_bytes(packed)
    else:
        target.write_bytes(raw)
    print('Bulundu:',rel)
    print('Yamali font:',target)

if __name__=='__main__': main()
