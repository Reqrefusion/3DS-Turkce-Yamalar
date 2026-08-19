#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import csv, sys, importlib.util
TR='ÇĞİÖŞÜçğıöşü'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def main():
    root=Path(__file__).resolve().parents[1]
    msbt=load(root/'04_ARACLAR/kirby_msbt_tool.py','robobo_msbt_verify')
    font=load(root/'04_ARACLAR/kirby_font_tr_patch.py','robobo_font_verify')
    scale_guard=load(root/'04_ARACLAR/robobo_scale_guard.py','robobo_scale_guard_verify')
    csvdir=root/'01_CEVIRI/MSBT_CSV'; built=root/'BUILD_OUTPUT/ROMFS_ONLY/romfs/msg/EU_English'
    errors=[]; checked=0
    _total, unsupported_scale, _changed = scale_guard.guard_csv_dir(csvdir, root/'05_RAPORLAR/BUILD_OLCEK_KODU_KONTROLU.csv', apply=False)
    if unsupported_scale:
        errors.append(f'Resmî dillerde kullanılmayan TR ölçek kodu: {unsupported_scale} kayıt')
    for cp in sorted(csvdir.glob('*.csv')):
        mp=built/(cp.stem+'.msbt')
        if not mp.exists(): errors.append(f'Eksik MSBT: {mp.name}'); continue
        m=msbt.MSBT.from_file(mp); by={m.primary_label(i):m.texts[i] for i in range(len(m.texts))}
        with cp.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        for r in rows:
            checked+=1; exp=r.get('TR_Turkish','') or r.get('EU_English','')
            got=by.get(r['label'])
            if got!=exp: errors.append(f'{cp.name}:{r["label"]}: CSV/MSBT farkı')
    fontroot=root/'BUILD_OUTPUT/ROMFS_ONLY/romfs/font'
    textfonts=okfonts=0
    for fp in sorted(fontroot.rglob('*.bcfnt.cmp')):
        f=font.BCFNT(fp.read_bytes())
        if all(c in f.mapping for c in 'GISgis'):
            textfonts+=1
            miss=''.join(c for c in TR if f.runtime_lookup(c) is None)
            if miss: errors.append(f'{fp.name}: runtime TR eksik {miss}')
            else: okfonts+=1
    print(f'Metin karşılaştırması: {checked} kayıt')
    print(f'Font runtime: {okfonts}/{textfonts} Latin metin fontu tam Türkçe')
    if errors:
        print(f'HATA: {len(errors)}'); [print(' -',e) for e in errors[:100]]; raise SystemExit(1)
    print('QA: OK')
if __name__=='__main__': main()
