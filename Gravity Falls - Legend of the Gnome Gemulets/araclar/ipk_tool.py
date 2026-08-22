#!/usr/bin/env python3
"""UbiArt IPK tool for the Gravity Falls 3DS archive variant.

Supports listing, extraction and in-place logical replacement while rebuilding
raw-data offsets. Unmodified files are copied as their original stored bytes, so
compressed assets do not get recompressed unless they are the replacement target.
"""
from __future__ import annotations
import argparse, lzma, struct, zlib
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"\x50\xEC\x12\xBA"
HEADER_SIZE = 56  # Gravity Falls CTR: 14 big-endian u32 fields

@dataclass
class Entry:
    index: int
    meta_pos: int
    num_offset: int
    size: int
    compressed_size: int
    timestamp: int
    offset: int
    name: str
    path: str
    checksum: int
    flag: int

    @property
    def full_path(self) -> str:
        # In this old UbiArt variant, 'name' is the directory and 'path' is filename.
        return self.name + self.path


def parse(path: Path):
    data = path.read_bytes()
    if data[:4] != MAGIC:
        raise ValueError("Not a UbiArt IPK (magic 50 EC 12 BA missing)")
    if len(data) < HEADER_SIZE:
        raise ValueError("Truncated IPK")
    header = list(struct.unpack_from(">14I", data, 0))
    base = header[3]
    n = header[4]
    if header[13] != n:
        raise ValueError("Unexpected IPK header variant (num_files2 mismatch)")
    pos = HEADER_SIZE
    entries: list[Entry] = []
    for i in range(n):
        st = pos
        numoff, size, csize = struct.unpack_from(">III", data, pos); pos += 12
        ts, off = struct.unpack_from(">QQ", data, pos); pos += 16
        nlen = struct.unpack_from(">I", data, pos)[0]; pos += 4
        name = data[pos:pos+nlen].decode("utf-8"); pos += nlen
        plen = struct.unpack_from(">I", data, pos)[0]; pos += 4
        pth = data[pos:pos+plen].decode("utf-8"); pos += plen
        checksum, flag = struct.unpack_from(">II", data, pos); pos += 8
        entries.append(Entry(i, st, numoff, size, csize, ts, off, name, pth, checksum, flag))
    if pos != base:
        raise ValueError(f"Metadata end 0x{pos:X} != base offset 0x{base:X}; unsupported IPK layout")
    return data, header, entries


def stored_bytes(data: bytes, base: int, e: Entry) -> bytes:
    n = e.compressed_size if e.compressed_size else e.size
    return data[base+e.offset:base+e.offset+n]


def decompress_entry(raw: bytes, e: Entry) -> tuple[bytes, str]:
    if not e.compressed_size:
        return raw, "none"
    try:
        return zlib.decompress(raw), "zlib"
    except zlib.error:
        pass
    try:
        return lzma.decompress(raw), "lzma"
    except lzma.LZMAError:
        pass
    raise ValueError(f"Compressed entry {e.full_path} is neither zlib nor LZMA")


def choose_entry(entries: list[Entry], query: str) -> Entry:
    exact = [e for e in entries if e.full_path == query]
    if len(exact) == 1:
        return exact[0]
    partial = [e for e in entries if query.lower() in e.full_path.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise KeyError(f"No entry matches {query!r}")
    raise KeyError("Ambiguous query; matches:\n" + "\n".join("  " + e.full_path for e in partial[:50]))


def cmd_list(args):
    _, _, entries = parse(Path(args.ipk))
    for e in entries:
        if not args.filter or args.filter.lower() in e.full_path.lower():
            method = "compressed" if e.compressed_size else "raw"
            print(f"{e.index:4d}  {e.size:9d}  {e.compressed_size:9d}  {method:10s}  {e.full_path}")


def cmd_extract(args):
    data, header, entries = parse(Path(args.ipk)); base = header[3]
    e = choose_entry(entries, args.entry)
    raw = stored_bytes(data, base, e)
    payload, method = decompress_entry(raw, e)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(payload)
    print(f"Extracted {e.full_path} -> {out} ({len(payload)} bytes, storage={method})")


def cmd_extract_all(args):
    data, header, entries = parse(Path(args.ipk)); base = header[3]
    root = Path(args.output); root.mkdir(parents=True, exist_ok=True)
    for e in entries:
        raw = stored_bytes(data, base, e)
        payload, _ = decompress_entry(raw, e)
        out = root / Path(e.full_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
    print(f"Extracted {len(entries)} files to {root}")


def cmd_replace(args):
    ipk = Path(args.ipk)
    data, header, entries = parse(ipk); base = header[3]
    target = choose_entry(entries, args.entry)
    replacement = Path(args.input).read_bytes()

    old_raw = stored_bytes(data, base, target)
    _, old_method = decompress_entry(old_raw, target)
    method = old_method if args.compression == "preserve" else args.compression
    if method == "none":
        new_raw = replacement; new_csize = 0
    elif method == "zlib":
        new_raw = zlib.compress(replacement); new_csize = len(new_raw)
    elif method == "lzma":
        new_raw = lzma.compress(replacement); new_csize = len(new_raw)
    else:
        raise ValueError(method)

    metadata = bytearray(data[:base])
    # Preserve data order by original raw-data offset, not metadata order.
    ordered = sorted(entries, key=lambda x: x.offset)
    new_data = bytearray()
    for e in ordered:
        new_off = len(new_data)
        if e.index == target.index:
            raw = new_raw
            e.size = len(replacement)
            e.compressed_size = new_csize
        else:
            raw = stored_bytes(data, base, e)
        e.offset = new_off
        new_data += raw
        struct.pack_into(">I", metadata, e.meta_pos + 4, e.size)
        struct.pack_into(">I", metadata, e.meta_pos + 8, e.compressed_size)
        struct.pack_into(">Q", metadata, e.meta_pos + 20, e.offset)

    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(metadata) + bytes(new_data))
    print(f"Replaced {target.full_path}; {old_method} -> {method}; wrote {out}")


def cmd_roundtrip(args):
    # Replacing an entry with its extracted uncompressed payload should be identical for raw entries.
    data, header, entries = parse(Path(args.ipk)); base = header[3]
    bad = []
    ordered = sorted(entries, key=lambda x: x.offset)
    expected = 0
    for e in ordered:
        if e.offset != expected:
            bad.append((e.full_path, e.offset, expected))
        expected += e.compressed_size if e.compressed_size else e.size
    if expected != len(data) - base:
        bad.append(("<end>", expected, len(data)-base))
    if bad:
        print("FAIL: archive data is not tightly packed as expected")
        for x in bad[:20]: print(x)
        raise SystemExit(2)
    print("OK: metadata parses and all data spans are tightly packed")


def main():
    ap = argparse.ArgumentParser(description="List/extract/replace Gravity Falls UbiArt IPK files")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("list"); p.add_argument("ipk"); p.add_argument("--filter", default=""); p.set_defaults(func=cmd_list)
    p = sp.add_parser("extract"); p.add_argument("ipk"); p.add_argument("entry"); p.add_argument("output"); p.set_defaults(func=cmd_extract)
    p = sp.add_parser("extract-all"); p.add_argument("ipk"); p.add_argument("output"); p.set_defaults(func=cmd_extract_all)
    p = sp.add_parser("replace"); p.add_argument("ipk"); p.add_argument("entry"); p.add_argument("input"); p.add_argument("output"); p.add_argument("--compression", choices=["preserve","none","zlib","lzma"], default="preserve"); p.set_defaults(func=cmd_replace)
    p = sp.add_parser("check"); p.add_argument("ipk"); p.set_defaults(func=cmd_roundtrip)
    args = ap.parse_args(); args.func(args)

if __name__ == "__main__": main()
