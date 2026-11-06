#!/usr/bin/env python3
"""Batch-inject a tree of multilingual CSV files into a baseline MSBT tree.

Expected CSV layout is the one produced by msbt_multilang_csv.py:
  csv_root/menu/dialog.csv -> baseline_root/menu/dialog.msbt

The baseline tree is copied first, then every CSV is injected by LBL1 label.
XMSBT/XML is never used.
"""
from __future__ import annotations
import argparse, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from msbt_direct_tool import inject_csv, verify_roundtrip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('baseline_root', type=Path, help='Tree containing baseline .msbt files')
    ap.add_argument('csv_root', type=Path, help='Tree containing per-MSBT .csv files')
    ap.add_argument('output_root', type=Path, help='Output MSBT tree')
    ap.add_argument('--column', default='TR', help='CSV text column to inject (default: TR)')
    ap.add_argument('--no-verify', action='store_true', help='Skip final MSBT round-trip verification')
    a = ap.parse_args()

    if a.output_root.exists():
        shutil.rmtree(a.output_root)
    shutil.copytree(a.baseline_root, a.output_root)

    csvs = sorted(p for p in a.csv_root.rglob('*.csv') if not p.name.startswith('_'))
    if not csvs:
        raise SystemExit('No CSV files found')

    done = 0
    for c in csvs:
        rel = c.relative_to(a.csv_root).with_suffix('.msbt')
        src = a.baseline_root / rel
        dst = a.output_root / rel
        if not src.exists():
            raise FileNotFoundError(f'Baseline MSBT missing for {rel}')
        inject_csv(src, c, dst, a.column)
        done += 1

    print(f'Injected CSV files: {done}')
    if not a.no_verify:
        nf, nt, errs = verify_roundtrip(a.output_root)
        print(f'Verified MSBT files: {nf}')
        print(f'Verified TXT2 strings: {nt}')
        print(f'Errors: {len(errs)}')
        for e in errs[:50]:
            print(e)
        if errs:
            raise SystemExit(1)

if __name__ == '__main__':
    main()
