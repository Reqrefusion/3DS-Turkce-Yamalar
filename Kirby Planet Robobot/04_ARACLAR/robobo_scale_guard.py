#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, csv, re

OFFICIAL = [
    'EU_English','EU_French','EU_German','EU_Italian','EU_Spanish',
    'JP_Japanese','US_English','US_French','US_Spanish'
]
SCALE_RE = re.compile(r'⟦MSBT:0E00000002000200([0-9A-Fa-f]{4})⟧')


def scale_values(text: str):
    out=[]
    for m in SCALE_RE.finditer(text or ''):
        out.append(int.from_bytes(bytes.fromhex(m.group(1)), 'little'))
    return out


def has_active_scale(text: str) -> bool:
    return any(v != 100 for v in scale_values(text))


def strip_scale_tokens(text: str) -> str:
    return SCALE_RE.sub('', text or '')


def guard_csv_dir(csv_dir: Path, report: Path|None=None, apply: bool=False):
    rows_report=[]
    total=0
    unsupported=0
    changed=0
    for cp in sorted(csv_dir.glob('*.csv')):
        with cp.open(encoding='utf-8-sig', newline='') as f:
            reader=csv.DictReader(f)
            fieldnames=reader.fieldnames or []
            rows=list(reader)
        file_changed=False
        for row in rows:
            total += 1
            tr=row.get('TR_Turkish','') or ''
            tr_active=has_active_scale(tr)
            official_active={lang: has_active_scale(row.get(lang,'') or '') for lang in OFFICIAL}
            official_any=any(official_active.values())
            if tr_active and not official_any:
                unsupported += 1
                new=strip_scale_tokens(tr)
                rows_report.append({
                    'file':cp.name,
                    'index':row.get('index',''),
                    'label':row.get('label',''),
                    'TR_onceki':tr,
                    'TR_sonraki':new,
                    'TR_olcek_onceki':','.join(map(str,scale_values(tr))),
                    'Resmi_dillerde_olcek':'YOK',
                    'islem':'TR ölçek kodu kaldırıldı; görünür metin ve diğer kontrol kodları korundu',
                })
                if apply and new != tr:
                    row['TR_Turkish']=new
                    file_changed=True
                    changed += 1
        if apply and file_changed:
            with cp.open('w', encoding='utf-8-sig', newline='') as f:
                w=csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
                w.writeheader(); w.writerows(rows)
    if report:
        report.parent.mkdir(parents=True,exist_ok=True)
        fields=['file','index','label','TR_onceki','TR_sonraki','TR_olcek_onceki','Resmi_dillerde_olcek','islem']
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n'); w.writeheader(); w.writerows(rows_report)
    return total, unsupported, changed


def main():
    ap=argparse.ArgumentParser(description='Robobot TR ölçek kodlarını resmî dil kullanımına göre doğrular.')
    ap.add_argument('--csv-dir', type=Path, default=Path(__file__).resolve().parents[1]/'01_CEVIRI/MSBT_CSV')
    ap.add_argument('--report', type=Path, default=Path(__file__).resolve().parents[1]/'05_RAPORLAR/RESMI_DIL_OLCEK_KURALI.csv')
    ap.add_argument('--apply', action='store_true', help='Resmî dillerde hiç ölçek olmayan satırlardaki TR ölçek tokenlarını kaldırır.')
    a=ap.parse_args()
    total,bad,changed=guard_csv_dir(a.csv_dir,a.report,a.apply)
    print(f'Kayıt: {total}')
    print(f'Resmî dillerde ölçek yokken TR ölçeği bulunan: {bad}')
    if a.apply: print(f'Düzeltilen: {changed}')
    if bad and not a.apply: raise SystemExit(1)

if __name__=='__main__': main()
