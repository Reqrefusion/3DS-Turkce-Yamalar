#!/usr/bin/env python3
"""Direct MSBT extractor/injector for Nintendo MSBT files.

This tool never uses XMSBT/XML. It preserves LBL1/ATR1/TSY1/etc. sections and
only rebuilds TXT2 when injecting edited text.

CSV text escape format:
  \\n, \\r, \\t, \\0, \\uXXXX, \\xXX, \\\\  -> escaped characters/bytes
  <MSBT:GGGG:TTTT:PAYLOADHEX>                 -> inline MSBT control

The control payload is kept byte-for-byte in file byte order.
"""
from __future__ import annotations

import argparse
import csv
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# Reuse the tested reader/renderer used by the multilingual CSV exporter.
from msbt_multilang_csv import MSBT, parse_msbt, render_text

CTRL_RE = re.compile(r"<MSBT:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4}):([0-9A-Fa-f]*)>")


def _pack_u16(v: int, endian: str) -> bytes:
    return struct.pack(endian + "H", v)


def _pack_u32(v: int, endian: str) -> bytes:
    return struct.pack(endian + "I", v)


def unrender_text(msbt: MSBT, text: str) -> bytes:
    """Inverse of render_text() for editable CSV text."""
    out = bytearray()
    codec = "utf-16-le" if msbt.endian == "<" else "utf-16-be"
    i = 0
    n = len(text)

    while i < n:
        if text.startswith("<MSBT:", i):
            m = CTRL_RE.match(text, i)
            if m:
                group = int(m.group(1), 16)
                typ = int(m.group(2), 16)
                hx = m.group(3)
                if len(hx) % 2:
                    raise ValueError(f"Odd-length MSBT payload hex near offset {i}")
                payload = bytes.fromhex(hx)
                out += _pack_u16(0x000E, msbt.endian)
                out += _pack_u16(group, msbt.endian)
                out += _pack_u16(typ, msbt.endian)
                out += _pack_u16(len(payload), msbt.endian)
                out += payload
                i = m.end()
                continue

        ch = text[i]
        if ch == "\\":
            if i + 1 >= n:
                raise ValueError("Dangling backslash at end of text")
            esc = text[i + 1]
            if esc == "n":
                val = 0x0A; i += 2
            elif esc == "r":
                val = 0x0D; i += 2
            elif esc == "t":
                val = 0x09; i += 2
            elif esc == "0":
                val = 0x00; i += 2
            elif esc == "\\":
                if msbt.encoding == 0:
                    out += b"\\"
                elif msbt.encoding == 1:
                    out += "\\".encode(codec)
                else:
                    raise ValueError(f"Unsupported encoding byte {msbt.encoding}")
                i += 2
                continue
            elif esc == "u":
                if i + 6 > n or not re.fullmatch(r"[0-9A-Fa-f]{4}", text[i+2:i+6]):
                    raise ValueError(f"Invalid \\u escape near offset {i}")
                val = int(text[i+2:i+6], 16); i += 6
            elif esc == "x":
                if i + 4 > n or not re.fullmatch(r"[0-9A-Fa-f]{2}", text[i+2:i+4]):
                    raise ValueError(f"Invalid \\x escape near offset {i}")
                out.append(int(text[i+2:i+4], 16)); i += 4
                continue
            else:
                # Be strict: accidental escapes in a translation should fail rather
                # than silently create a corrupt TXT2 string.
                raise ValueError(f"Unknown escape \\{esc} near offset {i}")

            if msbt.encoding == 0:
                if val > 0xFF:
                    raise ValueError("\\u escape cannot be represented as one UTF-8 byte")
                out.append(val)
            elif msbt.encoding == 1:
                out += _pack_u16(val, msbt.endian)
            else:
                raise ValueError(f"Unsupported encoding byte {msbt.encoding}")
            continue

        # Ordinary Unicode character.
        if msbt.encoding == 0:
            out += ch.encode("utf-8")
        elif msbt.encoding == 1:
            out += ch.encode(codec)
        else:
            raise ValueError(f"Unsupported encoding byte {msbt.encoding}")
        i += 1

    out += b"\x00" if msbt.encoding == 0 else _pack_u16(0, msbt.endian)
    return bytes(out)


@dataclass
class SectionRecord:
    magic: str
    header: bytes
    data: bytes
    padding: bytes


def parse_section_records(path: Path) -> Tuple[bytes, str, List[SectionRecord]]:
    raw = path.read_bytes()
    if raw[:8] != b"MsgStdBn":
        raise ValueError(f"Not an MSBT: {path}")
    bom = raw[8:10]
    endian = "<" if bom == b"\xff\xfe" else ">" if bom == b"\xfe\xff" else None
    if endian is None:
        raise ValueError("Unknown byte order marker")
    section_count = struct.unpack_from(endian + "H", raw, 0x0E)[0]
    pos = 0x20
    records: List[SectionRecord] = []
    for _ in range(section_count):
        header = raw[pos:pos+0x10]
        magic = header[:4].decode("ascii")
        size = struct.unpack_from(endian + "I", header, 4)[0]
        start = pos + 0x10
        end = start + size
        next_pos = (end + 0x0F) & ~0x0F
        records.append(SectionRecord(magic, header, raw[start:end], raw[end:next_pos]))
        pos = next_pos
    if pos != len(raw):
        raise ValueError(f"Unexpected trailing data: parsed to {pos}, file is {len(raw)}")
    return raw[:0x20], endian, records


def build_txt2_data(endian: str, texts: List[bytes]) -> bytes:
    count = len(texts)
    table_len = 4 + count * 4
    offsets: List[int] = []
    running = table_len
    for t in texts:
        offsets.append(running)
        running += len(t)
    out = bytearray(_pack_u32(count, endian))
    for off in offsets:
        out += _pack_u32(off, endian)
    for t in texts:
        out += t
    return bytes(out)


def rebuild_msbt(path: Path, new_texts: List[bytes], output: Path) -> None:
    header, endian, records = parse_section_records(path)
    out = bytearray(header)
    replaced = False
    for rec in records:
        data = rec.data
        section_header = bytearray(rec.header)
        if rec.magic == "TXT2":
            if replaced:
                raise ValueError("Multiple TXT2 sections are not supported")
            data = build_txt2_data(endian, new_texts)
            struct.pack_into(endian + "I", section_header, 4, len(data))
            replaced = True
        out += section_header
        out += data
        pad_len = (-len(out)) % 16
        if pad_len:
            if len(rec.padding) == pad_len:
                out += rec.padding
            else:
                pad_byte = rec.padding[:1] or b"\xAB"
                out += pad_byte * pad_len
    if not replaced:
        raise ValueError("TXT2 section missing")
    struct.pack_into(endian + "I", out, 0x12, len(out))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(out)


def export_csv(msbt_path: Path, csv_path: Path) -> None:
    m = parse_msbt(msbt_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["Label", "Text"])
        if m.labels:
            for label in m.label_order:
                idx = m.labels[label]
                w.writerow([label, render_text(m, m.texts[idx])])
        else:
            for idx, raw in enumerate(m.texts):
                w.writerow([str(idx), render_text(m, raw)])


def inject_csv(msbt_path: Path, csv_path: Path, output: Path, column: str = "TR") -> None:
    m = parse_msbt(msbt_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        text_col = column if column in reader.fieldnames else "Text" if "Text" in reader.fieldnames else None
        if text_col is None:
            raise ValueError(f"Column {column!r} not found (columns: {reader.fieldnames})")
        if "Label" not in reader.fieldnames:
            raise ValueError("CSV needs a Label column")
        rows = list(reader)

    texts = list(m.texts)
    seen = set()
    for row in rows:
        label = row["Label"]
        if label not in m.labels:
            raise ValueError(f"CSV label {label!r} does not exist in {msbt_path.name}")
        if label in seen:
            raise ValueError(f"Duplicate CSV label {label!r}")
        seen.add(label)
        texts[m.labels[label]] = unrender_text(m, row[text_col])

    missing = set(m.labels) - seen
    if missing:
        raise ValueError(f"CSV is missing {len(missing)} labels, e.g. {sorted(missing)[:5]}")

    rebuild_msbt(msbt_path, texts, output)


def verify_roundtrip(root: Path) -> Tuple[int, int, List[str]]:
    files = sorted(root.rglob("*.msbt"))
    text_count = 0
    errors: List[str] = []
    for p in files:
        try:
            m = parse_msbt(p)
            rebuilt_texts = []
            for raw in m.texts:
                shown = render_text(m, raw)
                back = unrender_text(m, shown)
                text_count += 1
                if back != raw:
                    raise AssertionError(
                        f"text round-trip mismatch: rendered={shown[:120]!r}, "
                        f"orig={raw.hex()[:120]}, back={back.hex()[:120]}"
                    )
                rebuilt_texts.append(back)
            tmp = p.with_name(p.name + ".roundtrip.tmp")
            rebuild_msbt(p, rebuilt_texts, tmp)
            if tmp.read_bytes() != p.read_bytes():
                raise AssertionError("file rebuild is not byte-identical")
            tmp.unlink()
        except Exception as ex:
            errors.append(f"{p}: {ex}")
            try:
                p.with_name(p.name + ".roundtrip.tmp").unlink()
            except FileNotFoundError:
                pass
    return len(files), text_count, errors


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("export", help="Export one MSBT to Label/Text CSV")
    a.add_argument("msbt", type=Path); a.add_argument("csv", type=Path)

    a = sub.add_parser("inject", help="Inject Label/Text (or multilingual TR column) CSV")
    a.add_argument("msbt", type=Path); a.add_argument("csv", type=Path); a.add_argument("output", type=Path)
    a.add_argument("--column", default="TR")

    a = sub.add_parser("verify", help="Render/unrender and file-rebuild round-trip test recursively")
    a.add_argument("root", type=Path)

    args = ap.parse_args()
    if args.cmd == "export":
        export_csv(args.msbt, args.csv)
        print(args.csv)
    elif args.cmd == "inject":
        inject_csv(args.msbt, args.csv, args.output, args.column)
        print(args.output)
    elif args.cmd == "verify":
        nf, nt, errs = verify_roundtrip(args.root)
        print(f"Files tested: {nf}")
        print(f"TXT2 strings tested: {nt}")
        print(f"Errors: {len(errs)}")
        for e in errs[:50]: print(e)
        raise SystemExit(1 if errs else 0)


if __name__ == "__main__":
    main()
