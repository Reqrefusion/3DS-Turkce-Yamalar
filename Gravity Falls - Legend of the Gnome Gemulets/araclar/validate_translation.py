#!/usr/bin/env python3
"""Validate one or more Gravity Falls translation CSV files.

Supports the split translation layout (main.csv + dialogue.csv) and the older
single CSV layout. Checks UbiArt tags and warns about very large expansion.
"""
from __future__ import annotations
import argparse, csv, re
from collections import Counter
from pathlib import Path

TAG = re.compile(r"\[[^\]\r\n]+\]")

def tags(s: str) -> Counter[str]:
    return Counter(TAG.findall(s or ""))

def iter_csv_paths(items: list[str]):
    for item in items:
        p = Path(item)
        if p.is_dir():
            for name in ("main.csv", "dialogue.csv"):
                q = p / name
                if q.exists():
                    yield q
        else:
            yield p

def main() -> None:
    ap = argparse.ArgumentParser(description="Check Gravity Falls translation CSV tags/lengths")
    ap.add_argument("csv", nargs="+", help="CSV file(s) or a directory containing main.csv and dialogue.csv")
    ap.add_argument("--max-ratio", type=float, default=1.8, help="Warn when translated text is this many times longer than source (default 1.8)")
    a = ap.parse_args()

    errors = 0
    warnings = 0
    translated = 0
    files = 0

    for path in iter_csv_paths(a.csv):
        files += 1
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        group_default = path.stem if path.stem in {"main", "dialogue"} else "?"
        for r in rows:
            tr = r.get("Turkish", r.get("translation", "")) or ""
            if not tr:
                continue
            translated += 1
            src = r.get("English", r.get("source", "")) or ""
            group = r.get("group") or group_default
            if tags(src) != tags(tr):
                errors += 1
                print(f"ERROR {path.name}:{group} id={r.get('id')}: tag mismatch")
                print(f"  source tags: {dict(tags(src))}")
                print(f"  transl. tags: {dict(tags(tr))}")
            if len(src) >= 10 and len(tr) / max(1, len(src)) > a.max_ratio:
                warnings += 1
                print(f"WARN  {path.name}:{group} id={r.get('id')}: length {len(src)} -> {len(tr)} ({len(tr)/len(src):.2f}x)")

    if not files:
        raise SystemExit("No CSV files found")
    print(f"Checked {translated} translated rows in {files} CSV file(s): {errors} tag errors, {warnings} length warnings")
    if errors:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
