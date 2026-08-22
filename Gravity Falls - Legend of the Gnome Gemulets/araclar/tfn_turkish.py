#!/usr/bin/env python3
"""Audit and fallback-patch UbiArt .tfn.ckd raster-font maps for Turkish.

Gravity Falls TFN glyph records are fixed 44-byte structures beginning with
big-endian words 15,40. The patch reuses six extremely rare donor records and
points them at the existing G/g/I/i/S/s glyph regions. It does not alter the
texture atlas, so diacritics are not visually drawn; it is a readable fallback.
"""
from __future__ import annotations
import argparse, struct
from pathlib import Path

TR = "ÇĞİÖŞÜçğıöşü"
ALIASES = {"Ğ":"G", "ğ":"g", "İ":"I", "ı":"i", "Ş":"S", "ş":"s"}
# Rare characters sacrificed by the fallback. These are present in the stock font.
DONORS = [0x0192, 0x02C6, 0x02DC, 0x2030, 0x2039, 0x203A]  # ƒ ˆ ˜ ‰ ‹ ›
MARK = struct.pack(">II", 15, 40)
REC_SIZE = 44


def records(data: bytes):
    out = []
    pos = 0
    while True:
        i = data.find(MARK, pos)
        if i < 0: break
        if i + REC_SIZE <= len(data):
            cp = struct.unpack_from(">I", data, i+8)[0]
            out.append((cp, i))
        pos = i + REC_SIZE
    # Stock files have 217 ordinary records; reject accidental parsing of unrelated files.
    if len(out) < 100:
        raise ValueError("Not a recognized Gravity Falls TFN CKD font map")
    return out


def cmd_check(args):
    data=Path(args.input).read_bytes(); m=dict(records(data)); m.setdefault(0x20, -1)
    print(f"glyph records: {len(m)}")
    for c in TR: print(f"  {c} U+{ord(c):04X}: {'OK' if ord(c) in m else 'MISSING'}")
    miss=[c for c in TR if ord(c) not in m]; print("missing:","".join(miss) if miss else "none")


def cmd_patch(args):
    data=bytearray(Path(args.input).read_bytes()); m=dict(records(data))
    missing=[c for c in ALIASES if ord(c) not in m]
    if not missing:
        Path(args.output).write_bytes(data);print("No patch needed");return
    donors=[cp for cp in DONORS if cp in m]
    if len(donors)<len(missing): raise ValueError("Not enough donor glyph records")
    for c, donor in zip(missing, donors):
        base = ALIASES[c]
        if ord(base) not in m: raise ValueError(f"Base glyph {base} missing")
        src_off=m[ord(base)]; dst_off=m[donor]
        rec=bytearray(data[src_off:src_off+REC_SIZE])
        struct.pack_into(">I",rec,8,ord(c))
        data[dst_off:dst_off+REC_SIZE]=rec
        print(f"  U+{donor:04X} donor -> {c} U+{ord(c):04X}, visually aliases {base}")
    Path(args.output).write_bytes(data)
    m2=dict(records(data)); miss=[c for c in TR if ord(c) not in m2]
    if miss: raise ValueError("Patch verification failed: "+"".join(miss))
    print(f"Wrote {args.output}")


def main():
    ap=argparse.ArgumentParser(description="Audit/fallback-patch Gravity Falls UbiArt TFN font maps")
    sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("check");p.add_argument("input");p.set_defaults(func=cmd_check)
    p=sp.add_parser("patch-alias");p.add_argument("input");p.add_argument("output");p.set_defaults(func=cmd_patch)
    a=ap.parse_args();a.func(a)
if __name__=="__main__":main()
