#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate a Luigi's Mansion 3DS EUR Turkish LayeredFS patch.

Checks:
- ZIP CRC/integrity
- main.gmsg parses and ID set matches original English
- gameplay/control codes (excluding layout breaks) match as multisets
- color tag multiset matches original English
- every visible character used by Turkish main.gmsg has a usable glyph in main.gzf
- patched location.gzf and ending.gzf contain required usable Turkish glyphs
- optional CSV with line-width risk rows based on GZF advance metrics
"""
from __future__ import annotations
import argparse, collections, csv, re, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lm3ds_export_csv import parse_gmsg, parse_gzf

COLOR_RE=re.compile(r'<color=([0-9A-Fa-f]+)>|</color>')
TAG_RE=re.compile(r'<[^>]+>|\[[^\]]+\]')
BREAK_RE=re.compile(r'<br>|<hr>')

def find_member(z:zipfile.ZipFile,suffix:str)->str:
    suffix=suffix.lstrip('/')
    hits=[n for n in z.namelist() if n.replace('\\','/').lstrip('/').endswith(suffix)]
    if not hits: raise FileNotFoundError(suffix)
    return hits[0]

def gameplay_controls(row):
    # 00 terminator, 01 line break, 02 page break are layout controls.
    return [c for c in row.controls if c and c[0] not in (0x00,0x01,0x02)]

def visible_line_widths(text,adv):
    out=[]
    for part in BREAK_RE.split(text):
        part=TAG_RE.sub('',part)
        out.append(sum(adv.get(ch,0) for ch in part))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--original',required=True,help='Original EUR ROMFS zip')
    ap.add_argument('--patch',required=True,help='Built LayeredFS patch zip')
    ap.add_argument('--risk-csv',help='Optional output CSV for wide text lines')
    ap.add_argument('--risk-px',type=int,default=240)
    args=ap.parse_args()

    with zipfile.ZipFile(args.patch) as pz:
        bad=pz.testzip()
        if bad: raise SystemExit(f'ZIP CRC failure: {bad}')
        tr_data=pz.read(find_member(pz,'/romfs/Region_EU/English/main.gmsg'))
        loc_data=pz.read(find_member(pz,'/romfs/Region_EU/location.gzf'))
        end_data=pz.read(find_member(pz,'/romfs/Region_EU/ending.gzf'))
    tr=parse_gmsg(tr_data)

    with zipfile.ZipFile(args.original) as oz:
        en_data=oz.read(find_member(oz,'/romfs/Region_EU/English/main.gmsg'))
        font_data=oz.read(find_member(oz,'/romfs/Region_EU/main.gzf'))
    en=parse_gmsg(en_data)
    if set(en)!=set(tr):
        raise SystemExit(f'ID set mismatch: EN={len(en)} TR={len(tr)}')

    control_mismatch=[]
    color_mismatch=[]
    for mid in en:
        if collections.Counter(gameplay_controls(en[mid])) != collections.Counter(gameplay_controls(tr[mid])):
            control_mismatch.append(mid)
        ec=collections.Counter(m.group(0).lower() for m in COLOR_RE.finditer(en[mid].text))
        tc=collections.Counter(m.group(0).lower() for m in COLOR_RE.finditer(tr[mid].text))
        if ec!=tc: color_mismatch.append(mid)

    _,glyphs=parse_gzf(font_data)
    adv={g.char:g.advance for g in glyphs if g.usable}
    used=set()
    for r in tr.values(): used.update(TAG_RE.sub('',r.text))
    missing=sorted(ch for ch in used if not ch.isspace() and ch not in adv)

    _,lg=parse_gzf(loc_data); lm={g.char:g for g in lg}
    loc_required=['Y','Ç','Ö','â','ö','ğ','İ','ı','Ş','ş']
    loc_missing=[ch for ch in loc_required if ch not in lm or not lm[ch].usable]
    _,eg=parse_gzf(end_data); em={g.char:g for g in eg}
    end_required=list('ğĞİşŞ')
    end_missing=[ch for ch in end_required if ch not in em or not em[ch].usable]

    risks=[]
    for mid,r in tr.items():
        widths=visible_line_widths(r.text,adv)
        for idx,w in enumerate(widths,1):
            if w>=args.risk_px:
                risks.append((mid,idx,w,r.text))
    risks.sort(key=lambda x:x[2],reverse=True)
    if args.risk_csv:
        with open(args.risk_csv,'w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f); w.writerow(['ID','Line','PixelWidth','Text'])
            for mid,line,pw,text in risks: w.writerow([f'0x{mid:04X}',line,pw,text])

    print(f'ZIP integrity: OK')
    print(f'GMSG records: {len(tr)} / {len(en)}')
    print(f'Gameplay control mismatches: {len(control_mismatch)}')
    print(f'Color tag mismatches: {len(color_mismatch)}')
    print(f'Missing main.gzf glyphs: {len(missing)} {missing}')
    print(f'location.gzf missing required glyphs: {loc_missing}')
    print(f'ending.gzf missing required glyphs: {end_missing}')
    print(f'Lines >= {args.risk_px}px: {len(risks)}; max={risks[0][2] if risks else 0}px')
    if control_mismatch or color_mismatch or missing or loc_missing or end_missing:
        print('VALIDATION: FAILED')
        if control_mismatch: print(' control IDs:', ', '.join(f'0x{x:04X}' for x in control_mismatch[:50]))
        if color_mismatch: print(' color IDs:', ', '.join(f'0x{x:04X}' for x in color_mismatch[:50]))
        raise SystemExit(2)
    print('VALIDATION: PASS')

if __name__=='__main__': main()
