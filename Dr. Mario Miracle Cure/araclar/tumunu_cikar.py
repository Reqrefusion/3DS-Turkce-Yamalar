#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json
from pathlib import Path
import drmario_tool as t

def safe_name(s:str)->str: return s.replace('..','_').lstrip('/\\')

def process_pack(src:Path,romfs:Path,outroot:Path,png:bool):
    rel=src.relative_to(romfs); base=outroot/rel.parent; base.mkdir(parents=True,exist_ok=True)
    raw=t.sszl_unpack(src.read_bytes()); (base/'main.arcv').write_bytes(raw); ar=t.arcv_parse(raw); ardir=base/'arcv'; ardir.mkdir(exist_ok=True); summary=[]
    for e in ar['entries']:
        name=safe_name(e['name']); q=ardir/name; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(e['data'])
        item={'name':e['name'],'size':len(e['data']),'type':e['data'][:4].decode('ascii','replace')}
        if e['data'][:8]==b'MsgStdBn':
            jd=base/'msbt_json'; jd.mkdir(exist_ok=True); t.msbt_export_json(e['data'],jd/(Path(name).stem+'.json'))
        elif e['data'][:4]==b'SARC':
            sd=base/'sarc'; t.sarc_extract(e['data'],sd)
            if png:
                pd=base/'png'
                for f in sd.rglob('*.bflim'):
                    try: im,_=t.bflim_decode_image(f.read_bytes())
                    except (NotImplementedError,ValueError): continue
                    target=(pd/f.relative_to(sd)).with_suffix('.png'); target.parent.mkdir(parents=True,exist_ok=True); im.save(target)
        summary.append(item)
    (base/'_paket.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(ar['entries'])

def main():
    ap=argparse.ArgumentParser(description='Dr. Mario RomFS içindeki SSZL/ARCV/SARC/MSBT/BFLIM kaynaklarını topluca çıkarır.')
    ap.add_argument('romfs',help='romfs klasörü'); ap.add_argument('cikti',help='çıktı klasörü'); ap.add_argument('--png-yok',action='store_true',help='BFLIM dosyalarını PNG olarak ayrıca çıkartma')
    a=ap.parse_args(); romfs=Path(a.romfs).resolve(); out=Path(a.cikti).resolve(); roots=[romfs/'message/ms/bin',romfs/'common/2d',romfs/'game/2d',romfs/'menu/2d']; files=[]
    for r in roots:
        if r.exists(): files.extend(sorted(r.rglob('main.lzss')))
    if not files: raise SystemExit('Desteklenen main.lzss dosyaları bulunamadı; romfs kökünü verdiğinizden emin olun.')
    total=0
    for i,p in enumerate(files,1):
        n=process_pack(p,romfs,out,not a.png_yok); total+=n; print(f'[{i}/{len(files)}] {p.relative_to(romfs)}')
    print(f'Tamamlandı: {len(files)} paket, {total} ARCV girdisi -> {out}')

if __name__=='__main__': main()
