#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent
sys.path.insert(0, str(ROOT/'tools'))
from translation_common import load_jsonl, source_hash
import starfox64_3d_tr_tool as tool

def main() -> int:
    ap=argparse.ArgumentParser(description="Yerel inceleme için İngilizce + Türkçe TSV üretir; bu dosyayı Git'e eklemeyin.")
    ap.add_argument('resources')
    ap.add_argument('--translation', default=str(ROOT/'translations'/'tr_TR.jsonl'))
    ap.add_argument('--output', default=str(ROOT/'review'/'tr_TR_review.tsv'))
    args=ap.parse_args()
    rows=load_jsonl(Path(args.translation)); by_key={(r['file'],r['index']):r for r in rows}
    rs=tool.open_resource_source(Path(args.resources))
    try:
        originals={}
        for p in tool.find_msbt_files(rs):
            key=tool.rel_key(rs,p)
            needed=[idx for (f,idx) in by_key if f==key]
            if not needed: continue
            m=tool.parse_msbt(p)
            for idx in needed:
                ent=m.entries[idx]
                if source_hash(ent.text) != by_key[(key,idx)]['source_sha256']:
                    raise SystemExit(f"HATA: {key}/{idx} kaynak SHA uyuşmuyor")
                originals[(key,idx)]=ent.text
        out=Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f,delimiter='\t',quoting=csv.QUOTE_ALL,lineterminator='\n')
            w.writerow(['file','index','label','original','translation'])
            for r in rows:
                key=(r['file'],r['index'])
                if key not in originals: raise SystemExit(f"HATA: kaynak bulunamadı: {key}")
                w.writerow([r['file'],r['index'],r['label'],originals[key],r['translation']])
        print(f"OK: {len(rows)} kayıt -> {out}")
        print("Not: review/ klasörü .gitignore içindedir; bu TSV'yi repoya commit etmeyin.")
        return 0
    finally: rs.close()
if __name__=='__main__': raise SystemExit(main())
