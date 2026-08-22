#!/usr/bin/env python3
"""Audit and fallback-patch a Nintendo 3DS BCFNT for Turkish characters.

The fallback patch adds CMAP aliases for missing Turkish letters by mapping them
to the closest existing ASCII glyph. This makes Turkish UTF-8 text render rather
than showing missing-glyph boxes, but it does NOT draw the diacritics for
Ğ/ğ, İ/ı, Ş/ş. For perfect typography, replace the font with a BCFNT generated
from a Turkish-capable source font, then inject it with ipk_tool.py.
"""
from __future__ import annotations
import argparse, struct
from pathlib import Path

TR = "ÇĞİÖŞÜçğıöşü"
ALIASES = {"Ğ":"G", "ğ":"g", "İ":"I", "ı":"i", "Ş":"S", "ş":"s"}


def endian(data: bytes) -> str:
    if data[:4] not in (b"CFNT", b"TNFC", b"CFNU"):
        raise ValueError("Not a CFNT/BCFNT file")
    bom = data[4:6]
    if bom == b"\xff\xfe": return "<"  # this game's BCFNT is little-endian
    if bom == b"\xfe\xff": return ">"
    raise ValueError("Unknown byte-order mark")


def cmap_blocks(data: bytes, order: str):
    # FINF begins at 0x14 for v3 CFNT. Its CMAP pointer is at FINF+0x18 and points to block+8.
    finf = data.find(b"FINF")
    if finf < 0: raise ValueError("FINF not found")
    cmap_ptr = struct.unpack_from(order+"I", data, finf+0x18)[0]
    off = cmap_ptr - 8
    seen = set()
    out = []
    while off and off not in seen:
        seen.add(off)
        magic, size, begin, end, method, reserved, nxt = struct.unpack_from(order+"4sIHHHHI", data, off)
        if magic != b"CMAP": raise ValueError(f"Bad CMAP at 0x{off:X}")
        out.append((off,size,begin,end,method,reserved,nxt))
        off = nxt - 8 if nxt else 0
    return out


def parse_charset(data: bytes):
    order = endian(data); mapping = {}
    blocks = cmap_blocks(data, order)
    for off,size,begin,end,method,reserved,nxt in blocks:
        p = off + 20
        if method == 0:
            idx0 = struct.unpack_from(order+"H", data, p)[0]
            for cp in range(begin,end+1): mapping[cp] = idx0 + cp - begin
        elif method == 1:
            vals = struct.unpack_from(order + "H"*(end-begin+1), data, p)
            for cp, idx in zip(range(begin,end+1), vals):
                if idx != 0xFFFF: mapping[cp] = idx
        elif method == 2:
            count = struct.unpack_from(order+"H", data, p)[0]; p += 2
            for _ in range(count):
                cp, idx = struct.unpack_from(order+"HH", data, p); p += 4
                mapping[cp] = idx
        else:
            raise ValueError(f"Unknown CMAP method {method}")
    return order, mapping, blocks


def cmd_check(args):
    data = Path(args.input).read_bytes(); _, m, _ = parse_charset(data)
    missing = [c for c in TR if ord(c) not in m]
    print(f"mapped characters: {len(m)}")
    print("Turkish coverage:")
    for c in TR: print(f"  {c} U+{ord(c):04X}: {'OK' if ord(c) in m else 'MISSING'}")
    print("missing:", "".join(missing) if missing else "none")


def cmd_charset(args):
    data = Path(args.input).read_bytes(); _, m, _ = parse_charset(data)
    Path(args.output).write_text("".join(chr(cp) for cp in sorted(m)), encoding="utf-8")
    print(f"Wrote {len(m)} mapped characters to {args.output}")


def cmd_patch(args):
    src = Path(args.input); data = bytearray(src.read_bytes())
    order, mapping, blocks = parse_charset(data)
    needed = {ord(k): mapping[ord(v)] for k,v in ALIASES.items() if ord(k) not in mapping}
    if not needed:
        Path(args.output).write_bytes(data); print("No patch needed; font already covers fallback characters"); return
    # Use the final CMAP, which is a Scan block and is the last section in this Gravity Falls font.
    off,size,begin,end,method,reserved,nxt = blocks[-1]
    if method != 2 or nxt != 0:
        raise ValueError("Final CMAP is not a terminal Scan block; refusing unsafe patch")
    if off + size != len(data):
        raise ValueError("Final CMAP is not at EOF; refusing unsafe patch")
    p = off + 20
    count = struct.unpack_from(order+"H", data, p)[0]; p += 2
    pairs = [struct.unpack_from(order+"HH", data, p+i*4) for i in range(count)]
    d = dict(pairs); d.update(needed)
    pairs = sorted(d.items())
    body = bytearray(struct.pack(order+"H", len(pairs)))
    for cp, idx in pairs: body += struct.pack(order+"HH", cp, idx)
    # Align section size to 4 bytes, matching the original font.
    new_size = 20 + len(body)
    body += b"\x00" * ((4 - new_size % 4) % 4)
    new_size = 20 + len(body)
    block = bytearray(struct.pack(order+"4sIHHHHI", b"CMAP", new_size, begin, end, method, reserved, 0)) + body
    out = data[:off] + block
    struct.pack_into(order+"I", out, 0x0C, len(out))
    Path(args.output).write_bytes(out)
    _, m2, _ = parse_charset(out)
    missing = [c for c in TR if ord(c) not in m2]
    if missing: raise ValueError("Patch verification failed: " + "".join(missing))
    print(f"Patched {len(needed)} aliases; wrote {args.output}")
    for cp, idx in sorted(needed.items()): print(f"  U+{cp:04X} -> glyph {idx}")


def main():
    ap=argparse.ArgumentParser(description="Audit/fallback-patch Gravity Falls tAhoMA BCFNT for Turkish")
    sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("check");p.add_argument("input");p.set_defaults(func=cmd_check)
    p=sp.add_parser("charset");p.add_argument("input");p.add_argument("output");p.set_defaults(func=cmd_charset)
    p=sp.add_parser("patch-alias");p.add_argument("input");p.add_argument("output");p.set_defaults(func=cmd_patch)
    a=ap.parse_args();a.func(a)
if __name__=="__main__":main()
