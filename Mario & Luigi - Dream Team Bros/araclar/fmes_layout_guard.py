#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMes layout guard.

This helper audits centered/letter-like FMes JSON for risky long visible lines and
for <C:0001,0004,> placement differences versus official-language references.

It does not replace fmes_safe_packager.py. Use this after translation/tag edits,
then build with fmes_safe_packager.py.
"""
from __future__ import annotations
import argparse, csv, json, re, unicodedata
from pathlib import Path
from collections import Counter

TAG_RE = re.compile(r"<[^>]+>")
LINE_SEP_RE = re.compile(r"(<U:000A>|\n)")
PAGE_SEP_RE = re.compile(r"(<C:0003,0001,><C:0000,0004,>|<C:0000,0004,>)")
CENTER_TAG = "<C:0001,0004,>"

def visible_text(s: str) -> str:
    return TAG_RE.sub("", s.replace("<U:000A>", "\n"))

def width(s: str) -> int:
    total = 0
    for ch in s:
        if ch == "\n":
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") or ch == "\u3000" else 1
    return total

def pages_and_lines(txt: str):
    pages = PAGE_SEP_RE.split(txt)
    page_no = 0
    for part in pages:
        if not part or PAGE_SEP_RE.fullmatch(part):
            continue
        pieces = LINE_SEP_RE.split(part)
        line = ""
        lines = []
        for piece in pieces:
            if LINE_SEP_RE.fullmatch(piece or ""):
                lines.append(line)
                line = ""
            else:
                line += piece
        lines.append(line)
        yield page_no, lines
        page_no += 1

def line_index_of_center_tags(txt: str):
    out = []
    start = 0
    while True:
        i = txt.find(CENTER_TAG, start)
        if i < 0:
            break
        before = txt[:i].replace("<U:000A>", "\n")
        out.append(before.count("\n"))
        start = i + len(CENTER_TAG)
    return tuple(out)

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def cmd_audit(args):
    tr = load_json(Path(args.json))
    rows = []
    for msbt, entries in tr.items():
        for entry, obj in entries.items():
            txt = obj.get("tokenized_text", obj.get("text", ""))
            if args.center_only and CENTER_TAG not in txt:
                continue
            for page, lines in pages_and_lines(txt):
                visible_lines = [visible_text(x) for x in lines]
                page_visible_count = sum(1 for x in visible_lines if x.strip())
                for line_no, v in enumerate(visible_lines):
                    w = width(v)
                    if w >= args.max_width:
                        rows.append({
                            "msbt": msbt,
                            "entry": entry,
                            "page": page,
                            "line": line_no,
                            "width": w,
                            "page_visible_lines": page_visible_count,
                            "visible": v,
                        })
    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["msbt","entry","page","line","width","page_visible_lines","visible"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} risky lines to {out}")

def cmd_compare_center(args):
    tr = load_json(Path(args.json))
    official = [load_json(Path(p)) for p in args.official_json]
    rows = []
    for msbt, entries in tr.items():
        for entry, obj in entries.items():
            tpos = line_index_of_center_tags(obj.get("tokenized_text", obj.get("text", "")))
            opos = []
            for off in official:
                if msbt in off and entry in off[msbt]:
                    opos.append(line_index_of_center_tags(off[msbt][entry].get("tokenized_text", off[msbt][entry].get("text", ""))))
            if not opos:
                continue
            maj, support = Counter(opos).most_common(1)[0]
            if support >= args.min_support and tpos != maj:
                rows.append({
                    "msbt": msbt,
                    "entry": entry,
                    "turkish_positions": str(tpos),
                    "official_majority_positions": str(maj),
                    "support": support,
                })
    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["msbt","entry","turkish_positions","official_majority_positions","support"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} center-tag position mismatches to {out}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit-lines")
    a.add_argument("--json", required=True)
    a.add_argument("--out-csv", required=True)
    a.add_argument("--max-width", type=int, default=45)
    a.add_argument("--center-only", action="store_true")
    a.set_defaults(func=cmd_audit)
    c = sub.add_parser("compare-center-tags")
    c.add_argument("--json", required=True)
    c.add_argument("--official-json", nargs="+", required=True)
    c.add_argument("--out-csv", required=True)
    c.add_argument("--min-support", type=int, default=5)
    c.set_defaults(func=cmd_compare_center)
    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
