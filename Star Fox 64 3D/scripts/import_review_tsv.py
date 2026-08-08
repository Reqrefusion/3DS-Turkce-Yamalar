#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv
from pathlib import Path
from translation_common import control_tokens, dump_jsonl, load_jsonl, max_visible_chars, source_hash

def main() -> int:
    ap=argparse.ArgumentParser(description="Yerel review TSV değişikliklerini çeviri JSONL dosyasına aktarır")
    ap.add_argument('review_tsv')
    ap.add_argument('--translation', default='translations/tr_TR.jsonl')
    args=ap.parse_args()
    jp=Path(args.translation); rows=load_jsonl(jp); mapping={(r['file'],r['index']):r for r in rows}
    changed=0
    with Path(args.review_tsv).open('r',encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f,delimiter='\t')
        for n,row in enumerate(rd,2):
            key=(row['file'],int(row['index']))
            if key not in mapping: raise SystemExit(f"HATA satır {n}: bilinmeyen kayıt {key}")
            rec=mapping[key]; original=row.get('original') or ''; tr=row.get('translation')
            if tr is None or tr=='': tr=original
            if source_hash(original) != rec['source_sha256']: raise SystemExit(f"HATA satır {n}: original kaynak SHA uyuşmuyor")
            if control_tokens(tr) != rec['control_tokens']: raise SystemExit(f"HATA satır {n}: kontrol tokenları değişmiş")
            if tr.count('\n')+1 > rec['source_line_count']: raise SystemExit(f"HATA satır {n}: satır sayısı kaynak sınırını aşıyor")
            if max_visible_chars(tr) > rec['source_max_visible_chars'] + 8: raise SystemExit(f"HATA satır {n}: görünür satır uzunluğu kaynak +8 toleransını aşıyor")
            if tr != rec['translation']:
                rec['translation']=tr; changed+=1
    dump_jsonl(jp, rows)
    print(f"OK: {changed} kayıt güncellendi -> {jp}")
    return 0
if __name__=='__main__': raise SystemExit(main())
