#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brain Train 3DS Localization Tool
- Nintendo LZ10/LZ11/RLE/raw auto handling
- MSBT multi-language CSV export + CSV injection
- BCFNT/CFNT Turkish patch font repair by merging missing glyphs from other language fonts

No third-party Python packages are required.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Iterable, Set

ALIGN_MSBT = 0x10
PAD_MSBT = 0xAB


# -----------------------------
# Compression codecs
# -----------------------------

def _read_nintendo_size(data: bytes, pos: int = 1) -> Tuple[int, int]:
    if len(data) < pos + 3:
        raise ValueError("Compressed stream is too short")
    size = data[pos] | (data[pos + 1] << 8) | (data[pos + 2] << 16)
    pos += 3
    if size == 0:
        if len(data) < pos + 4:
            raise ValueError("Missing extended decompressed size")
        size = struct.unpack_from('<I', data, pos)[0]
        pos += 4
    return size, pos


def _write_nintendo_header(kind: int, size: int) -> bytearray:
    out = bytearray([kind])
    if size < 0x1000000:
        out += bytes((size & 0xFF, (size >> 8) & 0xFF, (size >> 16) & 0xFF))
    else:
        out += b'\x00\x00\x00'
        out += struct.pack('<I', size)
    return out


def decompress_lz10(data: bytes) -> bytes:
    if not data or data[0] != 0x10:
        raise ValueError("Not an LZ10 stream")
    out_len, pos = _read_nintendo_size(data)
    out = bytearray()
    while len(out) < out_len:
        if pos >= len(data):
            raise ValueError("Unexpected EOF in LZ10 flag byte")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_len:
                break
            if flags & (1 << bit):
                if pos + 2 > len(data):
                    raise ValueError("Unexpected EOF in LZ10 back-reference")
                b1, b2 = data[pos], data[pos + 1]
                pos += 2
                length = (b1 >> 4) + 3
                disp = (((b1 & 0x0F) << 8) | b2) + 1
                if disp > len(out):
                    raise ValueError("Invalid LZ10 displacement")
                for _ in range(length):
                    out.append(out[-disp])
                    if len(out) >= out_len:
                        break
            else:
                if pos >= len(data):
                    raise ValueError("Unexpected EOF in LZ10 literal")
                out.append(data[pos])
                pos += 1
    return bytes(out)


def decompress_lz11(data: bytes) -> bytes:
    if not data or data[0] != 0x11:
        raise ValueError("Not an LZ11 stream")
    out_len, pos = _read_nintendo_size(data)
    out = bytearray()
    while len(out) < out_len:
        if pos >= len(data):
            raise ValueError("Unexpected EOF in LZ11 flag byte")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_len:
                break
            if not (flags & (1 << bit)):
                if pos >= len(data):
                    raise ValueError("Unexpected EOF in LZ11 literal")
                out.append(data[pos])
                pos += 1
                continue

            if pos + 2 > len(data):
                raise ValueError("Unexpected EOF in LZ11 back-reference")
            b1, b2 = data[pos], data[pos + 1]
            pos += 2
            nib = b1 >> 4
            if nib == 0:
                if pos >= len(data):
                    raise ValueError("Unexpected EOF in LZ11 medium back-reference")
                b3 = data[pos]
                pos += 1
                length = (((b1 & 0x0F) << 4) | (b2 >> 4)) + 0x11
                disp = (((b2 & 0x0F) << 8) | b3) + 1
            elif nib == 1:
                if pos + 2 > len(data):
                    raise ValueError("Unexpected EOF in LZ11 long back-reference")
                b3, b4 = data[pos], data[pos + 1]
                pos += 2
                length = (((b1 & 0x0F) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                disp = (((b3 & 0x0F) << 8) | b4) + 1
            else:
                length = nib + 1
                disp = (((b1 & 0x0F) << 8) | b2) + 1
            if disp > len(out):
                raise ValueError("Invalid LZ11 displacement")
            for _ in range(length):
                out.append(out[-disp])
                if len(out) >= out_len:
                    break
    return bytes(out)


def decompress_rle(data: bytes) -> bytes:
    if not data or data[0] != 0x30:
        raise ValueError("Not a Nintendo RLE stream")
    out_len, pos = _read_nintendo_size(data)
    out = bytearray()
    while len(out) < out_len:
        if pos >= len(data):
            raise ValueError("Unexpected EOF in RLE stream")
        flag = data[pos]
        pos += 1
        if flag & 0x80:
            count = (flag & 0x7F) + 3
            if pos >= len(data):
                raise ValueError("Unexpected EOF in RLE run")
            value = data[pos]
            pos += 1
            out.extend([value] * min(count, out_len - len(out)))
        else:
            count = (flag & 0x7F) + 1
            if pos + count > len(data):
                raise ValueError("Unexpected EOF in RLE literals")
            out.extend(data[pos:pos + min(count, out_len - len(out))])
            pos += count
    return bytes(out)


def _find_lz_match(data: bytes, pos: int, max_len: int, candidates: int = 16) -> Tuple[int, int]:
    """Return (length, displacement). Uses C-level rfind plus a small candidate scan."""
    if pos + 3 > len(data):
        return 0, 0
    start = max(0, pos - 0x1000)
    key = data[pos:pos + 3]
    search_end = pos
    best_len = 0
    best_disp = 0
    limit = min(max_len, len(data) - pos)
    for _ in range(candidates):
        j = data.rfind(key, start, search_end)
        if j < 0:
            break
        disp = pos - j
        if not (1 <= disp <= 0x1000):
            search_end = j
            continue
        length = 3
        # Comparing against the original data is valid even for overlapping LZ copies.
        while length < limit and data[j + length] == data[pos + length]:
            length += 1
        if length > best_len:
            best_len, best_disp = length, disp
            if length == limit:
                break
        search_end = j
    return best_len, best_disp


def compress_lz10(data: bytes) -> bytes:
    out = _write_nintendo_header(0x10, len(data))
    pos = 0
    while pos < len(data):
        flag_pos = len(out)
        out.append(0)
        flags = 0
        chunks = bytearray()
        for bit in range(7, -1, -1):
            if pos >= len(data):
                break
            length, disp = _find_lz_match(data, pos, 18)
            if length >= 3:
                flags |= 1 << bit
                d = disp - 1
                chunks.append(((length - 3) << 4) | ((d >> 8) & 0x0F))
                chunks.append(d & 0xFF)
                pos += length
            else:
                chunks.append(data[pos])
                pos += 1
        out[flag_pos] = flags
        out.extend(chunks)
    return bytes(out)


def compress_lz11(data: bytes) -> bytes:
    out = _write_nintendo_header(0x11, len(data))
    pos = 0
    while pos < len(data):
        flag_pos = len(out)
        out.append(0)
        flags = 0
        chunks = bytearray()
        for bit in range(7, -1, -1):
            if pos >= len(data):
                break
            length, disp = _find_lz_match(data, pos, 0x10110)
            if length >= 3:
                flags |= 1 << bit
                d = disp - 1
                if length <= 0x10:
                    chunks.append(((length - 1) << 4) | ((d >> 8) & 0x0F))
                    chunks.append(d & 0xFF)
                elif length <= 0x110:
                    l = length - 0x11
                    chunks.append((l >> 4) & 0x0F)
                    chunks.append(((l & 0x0F) << 4) | ((d >> 8) & 0x0F))
                    chunks.append(d & 0xFF)
                else:
                    l = length - 0x111
                    chunks.append(0x10 | ((l >> 12) & 0x0F))
                    chunks.append((l >> 4) & 0xFF)
                    chunks.append(((l & 0x0F) << 4) | ((d >> 8) & 0x0F))
                    chunks.append(d & 0xFF)
                pos += length
            else:
                chunks.append(data[pos])
                pos += 1
        out[flag_pos] = flags
        out.extend(chunks)
    return bytes(out)


def compress_rle(data: bytes) -> bytes:
    out = _write_nintendo_header(0x30, len(data))
    pos = 0
    n = len(data)
    while pos < n:
        run = 1
        while pos + run < n and data[pos + run] == data[pos] and run < 130:
            run += 1
        if run >= 3:
            out.append(0x80 | (run - 3))
            out.append(data[pos])
            pos += run
            continue
        lit_start = pos
        pos += run
        while pos < n and pos - lit_start < 128:
            look = 1
            while pos + look < n and data[pos + look] == data[pos] and look < 3:
                look += 1
            if look >= 3:
                break
            pos += 1
        count = pos - lit_start
        out.append(count - 1)
        out.extend(data[lit_start:pos])
    return bytes(out)


def detect_compression(data: bytes) -> str:
    if not data:
        return 'raw'
    if data[0] == 0x10:
        return 'lz10'
    if data[0] == 0x11:
        return 'lz11'
    if data[0] == 0x30:
        return 'rle'
    return 'raw'


def decompress_auto(data: bytes) -> Tuple[bytes, str]:
    kind = detect_compression(data)
    if kind == 'lz10':
        return decompress_lz10(data), kind
    if kind == 'lz11':
        return decompress_lz11(data), kind
    if kind == 'rle':
        return decompress_rle(data), kind
    return data, kind


def compress_as(data: bytes, kind: str) -> bytes:
    if kind == 'lz10':
        return compress_lz10(data)
    if kind == 'lz11':
        return compress_lz11(data)
    if kind == 'rle':
        return compress_rle(data)
    if kind == 'raw':
        return data
    raise ValueError(f"Unsupported compression kind: {kind}")


# -----------------------------
# MSBT parser/writer
# -----------------------------

@dataclass
class MSBTSection:
    magic: bytes
    header: bytes
    data: bytes


class MSBTFile:
    def __init__(self, raw: bytes):
        if raw[:8] != b'MsgStdBn':
            raise ValueError("Not an MSBT/MsgStdBn file")
        self.raw = raw
        bom = raw[8:10]
        if bom == b'\xFF\xFE':
            self.order = '<'
            self.utf16 = 'utf-16le'
        elif bom == b'\xFE\xFF':
            self.order = '>'
            self.utf16 = 'utf-16be'
        else:
            raise ValueError(f"Unsupported MSBT BOM: {bom.hex()}")
        self.header = bytearray(raw[:0x20])
        self.section_count = struct.unpack_from(self.order + 'H', raw, 0x0E)[0]
        # Encoding byte 0x0C = 1 in the supplied files (UTF-16).
        self.encoding = raw[0x0C]
        if self.encoding != 1:
            raise ValueError(f"This tool currently supports UTF-16 MSBT text (encoding=1), got {self.encoding}")
        self.sections: List[MSBTSection] = []
        pos = 0x20
        for _ in range(self.section_count):
            if pos + 0x10 > len(raw):
                raise ValueError("MSBT section header exceeds file size")
            magic = raw[pos:pos + 4]
            size = struct.unpack_from(self.order + 'I', raw, pos + 4)[0]
            header = raw[pos:pos + 0x10]
            data = raw[pos + 0x10:pos + 0x10 + size]
            self.sections.append(MSBTSection(magic, header, data))
            pos = (pos + 0x10 + size + 0x0F) & ~0x0F
        self.labels_by_index, self.index_by_label = self._parse_labels()
        self.entries = self._parse_txt2()

    def _section(self, magic: bytes) -> MSBTSection:
        for s in self.sections:
            if s.magic == magic:
                return s
        raise ValueError(f"MSBT section {magic!r} not found")

    def _parse_labels(self) -> Tuple[Dict[int, str], Dict[str, int]]:
        try:
            sec = self._section(b'LBL1')
        except ValueError:
            return {}, {}
        data = sec.data
        if len(data) < 4:
            return {}, {}
        groups = struct.unpack_from(self.order + 'I', data, 0)[0]
        table_end = 4 + groups * 8
        if table_end > len(data):
            raise ValueError("Invalid LBL1 group table")
        by_idx: Dict[int, str] = {}
        by_label: Dict[str, int] = {}
        for i in range(groups):
            count, off = struct.unpack_from(self.order + 'II', data, 4 + i * 8)
            pos = off
            for _ in range(count):
                if pos >= len(data):
                    raise ValueError("LBL1 label offset outside section")
                ln = data[pos]
                pos += 1
                name = data[pos:pos + ln].decode('utf-8', errors='replace')
                pos += ln
                if pos + 4 > len(data):
                    raise ValueError("Truncated LBL1 label entry")
                idx = struct.unpack_from(self.order + 'I', data, pos)[0]
                pos += 4
                by_idx.setdefault(idx, name)
                by_label.setdefault(name, idx)
        return by_idx, by_label

    def _parse_txt2(self) -> List[bytes]:
        sec = self._section(b'TXT2')
        data = sec.data
        if len(data) < 4:
            return []
        count = struct.unpack_from(self.order + 'I', data, 0)[0]
        if 4 + count * 4 > len(data):
            raise ValueError("Invalid TXT2 offset table")
        offsets = list(struct.unpack_from(self.order + f'{count}I', data, 4)) if count else []
        entries = []
        for i, off in enumerate(offsets):
            end = offsets[i + 1] if i + 1 < count else len(data)
            if off > end or end > len(data):
                raise ValueError("Invalid TXT2 entry offset")
            entries.append(data[off:end])
        return entries

    def key_for_index(self, idx: int) -> str:
        return self.labels_by_index.get(idx, f'#INDEX_{idx}')

    def display_text(self, idx: int) -> str:
        return encode_msbt_entry(self.entries[idx], self.order)

    def rebuild(self, new_entries: List[bytes]) -> bytes:
        if len(new_entries) != len(self.entries):
            raise ValueError("TXT2 entry count must stay unchanged for safe injection")
        count = len(new_entries)
        table_size = 4 + count * 4
        offsets: List[int] = []
        pos = table_size
        for e in new_entries:
            offsets.append(pos)
            pos += len(e)
        txt_data = bytearray()
        txt_data += struct.pack(self.order + 'I', count)
        if count:
            txt_data += struct.pack(self.order + f'{count}I', *offsets)
        for e in new_entries:
            txt_data += e

        out = bytearray(self.header)
        for sec in self.sections:
            header = bytearray(sec.header)
            data = bytes(txt_data) if sec.magic == b'TXT2' else sec.data
            struct.pack_into(self.order + 'I', header, 4, len(data))
            out += header
            out += data
            while len(out) % ALIGN_MSBT:
                out.append(PAD_MSBT)
        struct.pack_into(self.order + 'I', out, 0x12, len(out))
        return bytes(out)


TOKEN_RE = re.compile(r'\[\[(MSBT:START:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]*|MSBT:END:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}|U\+[0-9A-Fa-f]{4,6})\]\]')


def _decode_utf16_piece(piece: bytes, order: str) -> str:
    return piece.decode('utf-16le' if order == '<' else 'utf-16be', errors='surrogatepass')


def encode_msbt_entry(entry: bytes, order: str) -> str:
    """Encode an MSBT UTF-16 entry for lossless CSV editing.

    Nintendo MSBT control sequences are not uniform across all games: some tags use
    the common START/group/type/size layout, while others use game-specific layouts.
    Rather than guessing a tag length and corrupting text, this exporter preserves
    every unsafe UTF-16 code unit verbatim as [[U+XXXX]]. Printable text remains
    readable/editable, while control headers, private-use icons and sentinels are
    round-trip safe.
    """
    # Remove exactly one UTF-16 NUL terminator when present.
    if len(entry) >= 2 and entry[-2:] == b'\x00\x00':
        entry = entry[:-2]
    if len(entry) % 2:
        raise ValueError("MSBT UTF-16 entry has an odd byte length")

    out: List[str] = []
    normal = bytearray()

    def flush() -> None:
        nonlocal normal
        if normal:
            text = _decode_utf16_piece(bytes(normal), order)
            # Avoid accidental collision with our token syntax. Two literal '['
            # characters become two explicit U+005B tokens and decode identically.
            text = text.replace('[[', '[[U+005B]][[U+005B]]')
            out.append(text)
            normal = bytearray()

    for pos in range(0, len(entry), 2):
        u = struct.unpack_from(order + 'H', entry, pos)[0]
        # Keep common whitespace readable. Preserve all other C0 controls, private
        # use code points (often game icons), and U+FF00 explicitly.
        if (u < 0x20 and u not in (0x09, 0x0A, 0x0D)) or 0xE000 <= u <= 0xF8FF or u == 0xFF00:
            flush()
            out.append(f'[[U+{u:04X}]]')
        else:
            normal += entry[pos:pos + 2]
    flush()
    return ''.join(out)

def decode_msbt_text(text: str, order: str) -> bytes:
    enc = 'utf-16le' if order == '<' else 'utf-16be'
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(text):
        out += text[pos:m.start()].encode(enc, errors='surrogatepass')
        token = m.group(1)
        if token.startswith('MSBT:START:'):
            _, _, g, t, arghex = token.split(':', 4)
            args = bytes.fromhex(arghex) if arghex else b''
            out += struct.pack(order + '4H', 0x000E, int(g, 16), int(t, 16), len(args))
            out += args
        elif token.startswith('MSBT:END:'):
            _, _, g, t = token.split(':', 3)
            out += struct.pack(order + '3H', 0x000F, int(g, 16), int(t, 16))
        elif token.startswith('U+'):
            cp = int(token[2:], 16)
            if cp > 0xFFFF:
                out += chr(cp).encode(enc)
            else:
                out += struct.pack(order + 'H', cp)
        pos = m.end()
    out += text[pos:].encode(enc, errors='surrogatepass')
    out += b'\x00\x00'
    return bytes(out)


def read_msbt_path(path: Path) -> Tuple[MSBTFile, str]:
    packed = path.read_bytes()
    raw, kind = decompress_auto(packed)
    return MSBTFile(raw), kind


def export_multilang_csv(msg_root: Path, out_dir: Path, patch_root: Optional[Path] = None,
                         patch_column: str = 'TR_Patch') -> List[Path]:
    msg_root = Path(msg_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    langs = sorted(p.name for p in msg_root.iterdir() if p.is_dir())
    if not langs:
        raise ValueError(f"No language folders found under {msg_root}")
    filenames: Set[str] = set()
    for lang in langs:
        filenames.update(p.name for p in (msg_root / lang).glob('*.msbt*'))
    if patch_root and Path(patch_root).is_dir():
        filenames.update(p.name for p in Path(patch_root).glob('*.msbt*'))

    created = []
    for filename in sorted(filenames):
        per_lang: Dict[str, MSBTFile] = {}
        for lang in langs:
            p = msg_root / lang / filename
            if p.is_file():
                try:
                    per_lang[lang] = read_msbt_path(p)[0]
                except Exception as e:
                    raise RuntimeError(f"Failed to read {p}: {e}") from e
        if patch_root:
            p = Path(patch_root) / filename
            if p.is_file():
                per_lang[patch_column] = read_msbt_path(p)[0]
        if not per_lang:
            continue

        preferred = 'EU_English' if 'EU_English' in per_lang else next(iter(per_lang))
        ref = per_lang[preferred]
        keys: List[str] = [ref.key_for_index(i) for i in range(len(ref.entries))]
        seen = set(keys)
        for msbt in per_lang.values():
            for i in range(len(msbt.entries)):
                k = msbt.key_for_index(i)
                if k not in seen:
                    seen.add(k)
                    keys.append(k)

        lookups: Dict[str, Dict[str, int]] = {}
        for lang, msbt in per_lang.items():
            d = {msbt.key_for_index(i): i for i in range(len(msbt.entries))}
            lookups[lang] = d

        columns = langs + ([patch_column] if patch_column in per_lang else [])
        out_path = out_dir / (filename.replace('.LZ', '') + '.csv')
        with out_path.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['Key', 'ReferenceIndex', 'Label'] + columns,
                               quoting=csv.QUOTE_ALL)
            w.writeheader()
            for ref_idx, key in enumerate(keys):
                label = '' if key.startswith('#INDEX_') else key
                row = {'Key': key, 'ReferenceIndex': ref_idx, 'Label': label}
                for lang in columns:
                    msbt = per_lang.get(lang)
                    idx = lookups.get(lang, {}).get(key)
                    if msbt is None or idx is None:
                        row[lang] = ''
                    else:
                        row[lang] = msbt.display_text(idx)
                w.writerow(row)
        created.append(out_path)
    return created


def inject_csv_dir(csv_dir: Path, base_msg_dir: Path, out_msg_dir: Path, column: str,
                   keep_unmentioned: bool = True) -> List[Path]:
    csv_dir = Path(csv_dir)
    base_msg_dir = Path(base_msg_dir)
    out_msg_dir = Path(out_msg_dir)
    out_msg_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for base_path in sorted(base_msg_dir.glob('*.msbt*')):
        csv_name = base_path.name.replace('.LZ', '') + '.csv'
        csv_path = csv_dir / csv_name
        if not csv_path.is_file():
            if keep_unmentioned:
                shutil.copy2(base_path, out_msg_dir / base_path.name)
            continue
        msbt, kind = read_msbt_path(base_path)
        rows: Dict[str, Dict[str, str]] = {}
        with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or column not in reader.fieldnames:
                raise ValueError(f"Column {column!r} not found in {csv_path.name}")
            for row in reader:
                key = row.get('Key') or row.get('Label') or ''
                if key:
                    rows[key] = row

        new_entries = list(msbt.entries)
        for i in range(len(new_entries)):
            key = msbt.key_for_index(i)
            row = rows.get(key)
            if row is None:
                continue
            value = row.get(column)
            if value is None:
                continue
            try:
                new_entries[i] = decode_msbt_text(value, msbt.order)
            except Exception as e:
                raise ValueError(f"{csv_path.name}, key {key}: invalid MSBT token/text: {e}") from e
        rebuilt = msbt.rebuild(new_entries)
        packed = compress_as(rebuilt, kind)
        out_path = out_msg_dir / base_path.name
        out_path.write_bytes(packed)
        # Immediate verification.
        verify_raw, _ = decompress_auto(packed)
        verify = MSBTFile(verify_raw)
        if len(verify.entries) != len(msbt.entries):
            raise RuntimeError(f"Round-trip verification failed for {out_path.name}")
        created.append(out_path)
    return created


# -----------------------------
# BCFNT parser + glyph merge
# -----------------------------

@dataclass
class FontInfo:
    raw: bytes
    order: str
    header_size: int
    finf_start: int
    finf: tuple
    tglp_start: int
    tglp: tuple
    cwdh_start: int
    mapping: Dict[int, int]
    widths: Dict[int, Tuple[int, int, int]]

    @property
    def sheet_size(self) -> int:
        return self.tglp[6]

    @property
    def sheet_count(self) -> int:
        return self.tglp[7]

    @property
    def pixel_format(self) -> int:
        return self.tglp[8]

    @property
    def cols(self) -> int:
        return self.tglp[9]

    @property
    def rows(self) -> int:
        return self.tglp[10]

    @property
    def sheet_width(self) -> int:
        return self.tglp[11]

    @property
    def sheet_height(self) -> int:
        return self.tglp[12]

    @property
    def sheet_data_offset(self) -> int:
        return self.tglp[13]

    @property
    def cell_width(self) -> int:
        return self.tglp[2]

    @property
    def cell_height(self) -> int:
        return self.tglp[3]

    @property
    def slots_per_sheet(self) -> int:
        return self.cols * self.rows

    @property
    def capacity(self) -> int:
        return self.sheet_count * self.slots_per_sheet


BCFNT_HEADER = '4s2H3I'
FINF_STRUCT = '4sI2BH4B3I4B'
TGLP_STRUCT = '4sI4BI6HI'
CWDH_STRUCT = '4sI2HI'
CMAP_STRUCT = '4sI4HI'


def parse_bcfnt(raw: bytes) -> FontInfo:
    if raw[:4] not in (b'CFNT', b'CFNU'):
        raise ValueError("Not a CFNT/BCFNT file")
    bom_be = struct.unpack_from('>H', raw, 4)[0]
    if bom_be == 0xFFFE:
        order = '<'
    elif bom_be == 0xFEFF:
        order = '>'
    else:
        raise ValueError("Invalid CFNT byte-order marker")
    magic, bom, hsize, version, file_size, sections = struct.unpack_from(order + BCFNT_HEADER, raw, 0)
    finf_start = hsize
    finf = struct.unpack_from(order + FINF_STRUCT, raw, finf_start)
    if finf[0] != b'FINF':
        raise ValueError("FINF section not found")
    tglp_off, cwdh_off, cmap_off = finf[9:12]
    tglp_start = tglp_off - 8
    tglp = struct.unpack_from(order + TGLP_STRUCT, raw, tglp_start)
    if tglp[0] != b'TGLP':
        raise ValueError("TGLP section not found")

    mapping: Dict[int, int] = {}
    off = cmap_off
    seen = set()
    while off and off not in seen:
        seen.add(off)
        p = off - 8
        magic, size, start, end, typ, reserved, next_off = struct.unpack_from(order + CMAP_STRUCT, raw, p)
        if magic != b'CMAP':
            raise ValueError("Broken CMAP chain")
        data_pos = p + 20
        if typ == 0:  # direct
            index_off = struct.unpack_from(order + 'H', raw, data_pos)[0]
            for code in range(start, end + 1):
                mapping[code] = index_off + (code - start)
        elif typ == 1:  # table
            n = end - start + 1
            vals = struct.unpack_from(order + f'{n}H', raw, data_pos)
            for code, idx in zip(range(start, end + 1), vals):
                if idx != 0xFFFF:
                    mapping[code] = idx
        elif typ == 2:  # scan
            n = struct.unpack_from(order + 'H', raw, data_pos)[0]
            pos = data_pos + 2
            for _ in range(n):
                code, idx = struct.unpack_from(order + '2H', raw, pos)
                pos += 4
                mapping[code] = idx
        else:
            raise ValueError(f"Unsupported CMAP mapping type {typ}")
        off = next_off

    widths: Dict[int, Tuple[int, int, int]] = {}
    off = cwdh_off
    seen.clear()
    cwdh_start = cwdh_off - 8
    while off and off not in seen:
        seen.add(off)
        p = off - 8
        magic, size, start, end, next_off = struct.unpack_from(order + CWDH_STRUCT, raw, p)
        if magic != b'CWDH':
            raise ValueError("Broken CWDH chain")
        pos = p + 16
        for idx in range(start, end + 1):
            if pos + 3 > p + size:
                break
            left = struct.unpack_from('b', raw, pos)[0]
            widths[idx] = (left, raw[pos + 1], raw[pos + 2])
            pos += 3
        off = next_off

    return FontInfo(raw, order, hsize, finf_start, finf, tglp_start, tglp, cwdh_start, mapping, widths)


def font_compatible(a: FontInfo, b: FontInfo) -> bool:
    return (
        a.cell_width == b.cell_width and a.cell_height == b.cell_height and
        a.sheet_size == b.sheet_size and a.pixel_format == b.pixel_format and
        a.cols == b.cols and a.rows == b.rows and
        a.sheet_width == b.sheet_width and a.sheet_height == b.sheet_height
    )


def _swizzle_index_8bpp(x: int, y: int, width: int) -> int:
    tx, ty = x // 8, y // 8
    ix, iy = x & 7, y & 7
    morton = (
        (ix & 1) |
        ((iy & 1) << 1) |
        (((ix >> 1) & 1) << 2) |
        (((iy >> 1) & 1) << 3) |
        (((ix >> 2) & 1) << 4) |
        (((iy >> 2) & 1) << 5)
    )
    return ty * width * 8 + tx * 64 + morton



def _pixel_alpha(sheet: bytes, font: FontInfo, x: int, y: int) -> int:
    """Return a glyph-sheet pixel alpha (0..255) for formats used by this game."""
    pi = _swizzle_index_8bpp(x, y, font.sheet_width)
    if font.pixel_format == 8:  # A8
        return sheet[pi]
    if font.pixel_format == 9:  # LA4: high nibble luminance, low nibble alpha
        return (sheet[pi] & 0x0F) * 17
    if font.pixel_format == 11:  # A4: two pixels per byte, low nibble first
        b = sheet[pi // 2]
        return ((b >> ((pi & 1) * 4)) & 0x0F) * 17
    raise ValueError(f"Unsupported BCFNT raster format for alpha editing: {font.pixel_format}")


def _set_pixel_alpha(sheet: bytearray, font: FontInfo, x: int, y: int, alpha: int) -> None:
    alpha = max(0, min(255, int(alpha)))
    pi = _swizzle_index_8bpp(x, y, font.sheet_width)
    if font.pixel_format == 8:  # A8
        sheet[pi] = alpha
        return
    if font.pixel_format == 9:  # LA4
        a = max(0, min(15, int(round(alpha / 17.0))))
        sheet[pi] = 0 if a == 0 else (0xF0 | a)
        return
    if font.pixel_format == 11:  # A4
        a = max(0, min(15, int(round(alpha / 17.0))))
        bi = pi // 2
        shift = (pi & 1) * 4
        sheet[bi] = (sheet[bi] & ~(0x0F << shift)) | (a << shift)
        return
    raise ValueError(f"Unsupported BCFNT raster format for alpha editing: {font.pixel_format}")


def _glyph_alpha_matrix(font: FontInfo, codepoint: int) -> List[List[int]]:
    idx = font.mapping[codepoint]
    sheet_idx = idx // font.slots_per_sheet
    slot = idx % font.slots_per_sheet
    sheet = _extract_sheet(font, sheet_idx)
    x0 = (slot % font.cols) * (font.cell_width + 1)
    y0 = (slot // font.cols) * (font.cell_height + 1)
    return [
        [_pixel_alpha(sheet, font, x0 + x, y0 + y) for x in range(font.cell_width)]
        for y in range(font.cell_height)
    ]


def _glyph_is_blank(font: FontInfo, codepoint: int) -> bool:
    if codepoint not in font.mapping:
        return True
    try:
        mask = _glyph_alpha_matrix(font, codepoint)
    except ValueError:
        return False
    return not any(any(v > 0 for v in row) for row in mask)


def _mask_bbox(mask: List[List[int]], threshold: int = 24) -> Optional[Tuple[int, int, int, int]]:
    if not mask or not mask[0]:
        return None
    xs: List[int] = []
    ys: List[int] = []
    for y, row in enumerate(mask):
        for x, v in enumerate(row):
            if v > threshold:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _resize_mask(mask: List[List[int]], new_w: int, new_h: int) -> List[List[int]]:
    """Small dependency-free bilinear scaler for glyph alpha masks."""
    if new_w <= 0 or new_h <= 0:
        return []
    old_h = len(mask)
    old_w = len(mask[0]) if old_h else 0
    if old_w == 0 or old_h == 0:
        return [[0] * new_w for _ in range(new_h)]
    if old_w == new_w and old_h == new_h:
        return [row[:] for row in mask]
    out = [[0] * new_w for _ in range(new_h)]
    for y in range(new_h):
        sy = 0.0 if new_h == 1 else y * (old_h - 1) / (new_h - 1)
        y0 = int(sy); y1 = min(y0 + 1, old_h - 1); fy = sy - y0
        for x in range(new_w):
            sx = 0.0 if new_w == 1 else x * (old_w - 1) / (new_w - 1)
            x0 = int(sx); x1 = min(x0 + 1, old_w - 1); fx = sx - x0
            a = mask[y0][x0] * (1 - fx) + mask[y0][x1] * fx
            b = mask[y1][x0] * (1 - fx) + mask[y1][x1] * fx
            out[y][x] = int(round(a * (1 - fy) + b * fy))
    return out


def _accent_overlay(donor: FontInfo, codepoint: int, base_codepoint: int,
                    target_base: List[List[int]], target_w: int, target_h: int) -> List[List[int]]:
    """Preserve the target font's base letter and borrow only the Turkish diacritic."""
    tur = _glyph_alpha_matrix(donor, codepoint)
    base = _glyph_alpha_matrix(donor, base_codepoint)
    bb = _mask_bbox(base)
    if bb is None:
        return _resize_mask(tur, target_w, target_h)
    _, top, _, bottom = bb
    top_accent = chr(codepoint) in 'ĞğİÖöÜü'
    accent = [[0] * donor.cell_width for _ in range(donor.cell_height)]
    # Turkish glyphs in these BCFNTs use the same base outline as their plain letter.
    # Keep positive difference in the accent side of the base glyph; this avoids
    # replacing the target's own letter style.
    for y in range(donor.cell_height):
        for x in range(donor.cell_width):
            d = max(0, tur[y][x] - base[y][x])
            if top_accent:
                if y <= top + max(2, donor.cell_height // 8):
                    accent[y][x] = d
            else:
                if y >= bottom - max(2, donor.cell_height // 10):
                    accent[y][x] = d
    if _mask_bbox(accent) is None:
        # Fallback: take all pixels outside the donor base's main vertical body.
        for y in range(donor.cell_height):
            for x in range(donor.cell_width):
                if (top_accent and y < top) or ((not top_accent) and y >= bottom):
                    accent[y][x] = tur[y][x]
    scaled = _resize_mask(accent, target_w, target_h)
    out = [row[:] for row in target_base]
    for y in range(target_h):
        for x in range(target_w):
            out[y][x] = max(out[y][x], scaled[y][x])
    return out


def _dotless_i(mask: List[List[int]]) -> List[List[int]]:
    """Remove the detached dot component from a lowercase i glyph."""
    h = len(mask); w = len(mask[0]) if h else 0
    seen: Set[Tuple[int, int]] = set()
    comps: List[List[Tuple[int, int]]] = []
    for y in range(h):
        for x in range(w):
            if mask[y][x] <= 24 or (x, y) in seen:
                continue
            stack = [(x, y)]; seen.add((x, y)); comp = []
            while stack:
                cx, cy = stack.pop(); comp.append((cx, cy))
                for nx, ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and mask[ny][nx] > 24:
                        seen.add((nx, ny)); stack.append((nx, ny))
            comps.append(comp)
    if len(comps) < 2:
        return [row[:] for row in mask]
    # Main stem is normally the largest component. Keep it and any components at
    # the same/lower vertical range; discard only detached component(s) above it.
    main = max(comps, key=len)
    main_top = min(y for _, y in main)
    remove = set()
    for comp in comps:
        if comp is main:
            continue
        if max(y for _, y in comp) < main_top:
            remove.update(comp)
    out = [row[:] for row in mask]
    for x, y in remove:
        out[y][x] = 0
    return out


def _write_glyph_mask(font: FontInfo, sheet: bytearray, slot: int, mask: List[List[int]]) -> None:
    x0 = (slot % font.cols) * (font.cell_width + 1)
    y0 = (slot // font.cols) * (font.cell_height + 1)
    for y in range(font.cell_height):
        for x in range(font.cell_width):
            _set_pixel_alpha(sheet, font, x0 + x, y0 + y, mask[y][x])

def _extract_sheet(font: FontInfo, sheet_idx: int) -> bytearray:
    if sheet_idx < 0 or sheet_idx >= font.sheet_count:
        raise IndexError("Sheet index out of range")
    start = font.sheet_data_offset + sheet_idx * font.sheet_size
    end = start + font.sheet_size
    if end > len(font.raw):
        raise ValueError("TGLP sheet exceeds file size")
    return bytearray(font.raw[start:end])


def _copy_glyph_cell(source_font: FontInfo, source_sheet: bytes, source_slot: int,
                     target_font: FontInfo, target_sheet: bytearray, target_slot: int) -> None:
    if not font_compatible(source_font, target_font):
        raise ValueError("Direct glyph-cell copy requires compatible BCFNT geometry/format")
    sx = (source_slot % source_font.cols) * (source_font.cell_width + 1)
    sy = (source_slot // source_font.cols) * (source_font.cell_height + 1)
    tx = (target_slot % target_font.cols) * (target_font.cell_width + 1)
    ty = (target_slot // target_font.cols) * (target_font.cell_height + 1)
    if source_font.pixel_format == 9:
        # LA4 is byte-per-pixel: preserve both luminance and alpha bit-for-bit.
        for y in range(source_font.cell_height):
            for x in range(source_font.cell_width):
                si = _swizzle_index_8bpp(sx + x, sy + y, source_font.sheet_width)
                ti = _swizzle_index_8bpp(tx + x, ty + y, target_font.sheet_width)
                target_sheet[ti] = source_sheet[si]
        return
    if source_font.pixel_format in (8, 11):
        for y in range(source_font.cell_height):
            for x in range(source_font.cell_width):
                a = _pixel_alpha(source_sheet, source_font, sx + x, sy + y)
                _set_pixel_alpha(target_sheet, target_font, tx + x, ty + y, a)
        return
    raise ValueError(f"Unsupported direct glyph-cell format: {source_font.pixel_format}")


def _align4(n: int) -> int:
    return (n + 3) & ~3


def repair_bcfnt(target_raw: bytes, donor_raws: List[Tuple[str, bytes]], preferred_raw: Optional[bytes] = None) -> Tuple[bytes, dict]:
    target = parse_bcfnt(target_raw)
    donors: List[Tuple[str, FontInfo]] = []
    for name, raw in donor_raws:
        try:
            d = parse_bcfnt(raw)
        except Exception:
            continue
        if font_compatible(target, d):
            donors.append((name, d))
    if not donors:
        raise ValueError("No compatible donor fonts found")

    desired: Set[int] = set(target.mapping)
    for _, d in donors:
        desired.update(d.mapping)
    missing = sorted(desired - set(target.mapping))

    # Start from the target's existing TGLP sheets.
    sheets = [_extract_sheet(target, i) for i in range(target.sheet_count)]
    mapping = dict(target.mapping)
    widths = dict(target.widths)
    used = set(mapping.values())
    capacity = target.capacity
    # Prefer slots that are physically present but not described/used.
    free_slots = [i for i in range(capacity) if i not in used and i not in widths]
    # Then allow unreferenced described slots only if needed.
    free_slots += [i for i in range(capacity) if i not in used and i in widths and i not in free_slots]

    added_records = []
    donor_priority = {name: i for i, name in enumerate([
        'EU_English', 'EU_French', 'EU_German', 'EU_Spanish', 'EU_Italian', 'EU_Dutch',
        'US_English', 'US_French', 'US_Spanish'
    ])}
    donors.sort(key=lambda x: donor_priority.get(x[0], 999))

    def default_width(font: FontInfo) -> Tuple[int, int, int]:
        # FINF: default left/glyphWidth/charWidth are fields 5,6,7.
        return (int(font.finf[5]), int(font.finf[6]), int(font.finf[7]))

    for code in missing:
        source_name = None
        source = None
        source_idx = None
        for name, d in donors:
            if code in d.mapping:
                source_name, source, source_idx = name, d, d.mapping[code]
                break
        if source is None or source_idx is None:
            continue

        if free_slots:
            dest_idx = free_slots.pop(0)
        else:
            # Add a new transparent sheet, then expose all its slots as free.
            sheets.append(bytearray(target.sheet_size))
            old_capacity = capacity
            capacity += target.slots_per_sheet
            free_slots.extend(range(old_capacity, capacity))
            dest_idx = free_slots.pop(0)

        src_sheet_idx = source_idx // source.slots_per_sheet
        src_slot = source_idx % source.slots_per_sheet
        dst_sheet_idx = dest_idx // target.slots_per_sheet
        dst_slot = dest_idx % target.slots_per_sheet
        src_sheet = _extract_sheet(source, src_sheet_idx)
        _copy_glyph_cell(source, src_sheet, src_slot, target, sheets[dst_sheet_idx], dst_slot)
        widths[dest_idx] = source.widths.get(source_idx, default_width(source))
        mapping[code] = dest_idx
        added_records.append({
            'char': chr(code), 'codepoint': f'U+{code:04X}', 'donor': source_name,
            'source_glyph': source_idx, 'target_glyph': dest_idx
        })

    # Make CWDH cover the entire texture capacity so every slot has deterministic metrics.
    new_sheet_count = len(sheets)
    new_capacity = new_sheet_count * target.slots_per_sheet
    fallback = default_width(target)
    metric_rows = [widths.get(i, fallback) for i in range(new_capacity)]

    # Prefix includes header + FINF + TGLP header/padding, then rebuilt sheets.
    sheet_data_start = target.sheet_data_offset
    prefix = bytearray(target.raw[:sheet_data_start])
    for sheet in sheets:
        prefix += sheet

    # Restore FINF defaults/alter glyph from preferred original same font where available.
    if preferred_raw is not None:
        pref = parse_bcfnt(preferred_raw)
        if font_compatible(target, pref):
            prefix[target.finf_start:target.finf_start + 0x20] = pref.raw[pref.finf_start:pref.finf_start + 0x20]

    # Patch TGLP header: section size and sheet count.
    new_tglp_size = len(prefix) - target.tglp_start
    struct.pack_into(target.order + 'I', prefix, target.tglp_start + 4, new_tglp_size)
    struct.pack_into(target.order + 'H', prefix, target.tglp_start + 16, new_sheet_count)

    # One canonical CWDH section.
    cwdh_start = len(prefix)
    cwdh_size = _align4(16 + new_capacity * 3)
    cwdh = bytearray(cwdh_size)
    struct.pack_into(target.order + CWDH_STRUCT, cwdh, 0, b'CWDH', cwdh_size, 0, new_capacity - 1, 0)
    pos = 16
    for left, glyph_w, char_w in metric_rows:
        struct.pack_into('b', cwdh, pos, max(-128, min(127, int(left))))
        cwdh[pos + 1] = int(glyph_w) & 0xFF
        cwdh[pos + 2] = int(char_w) & 0xFF
        pos += 3

    # One canonical scan CMAP containing every target+donor character mapping.
    items = sorted(mapping.items())
    if len(items) > 0xFFFF:
        raise ValueError("Too many CMAP entries")
    cmap_start = cwdh_start + len(cwdh)
    cmap_size = _align4(20 + 2 + len(items) * 4)
    cmap = bytearray(cmap_size)
    struct.pack_into(target.order + CMAP_STRUCT, cmap, 0, b'CMAP', cmap_size, 0, 0xFFFF, 2, 0, 0)
    struct.pack_into(target.order + 'H', cmap, 20, len(items))
    pos = 22
    for code, idx in items:
        if code > 0xFFFF or idx > 0xFFFF:
            raise ValueError("BCFNT CMAP uses 16-bit codepoints/glyph indices")
        struct.pack_into(target.order + '2H', cmap, pos, code, idx)
        pos += 4

    out = prefix + cwdh + cmap

    # FINF offsets (offset points 8 bytes into each section by NW4C convention).
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x14, cwdh_start + 8)
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x18, cmap_start + 8)
    # Preserve TGLP offset from restored/preferred FINF only if correct; force it to target.
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x10, target.tglp_start + 8)
    # CFNT header: file size and 4 sections: FINF/TGLP/CWDH/CMAP.
    struct.pack_into(target.order + 'I', out, 0x0C, len(out))
    struct.pack_into(target.order + 'I', out, 0x10, 4)

    # Verification.
    verified = parse_bcfnt(bytes(out))
    still_missing = desired - set(verified.mapping)
    if still_missing:
        raise RuntimeError(f"Font merge verification failed; still missing: {sorted(still_missing)[:10]}")

    report = {
        'target_chars_before': len(target.mapping),
        'target_chars_after': len(verified.mapping),
        'sheets_before': target.sheet_count,
        'sheets_after': verified.sheet_count,
        'capacity_before': target.capacity,
        'capacity_after': verified.capacity,
        'added': added_records,
    }
    return bytes(out), report



TURKISH_CORE = 'ÇĞİÖŞÜçğıöşü'
TURKISH_BASE = {
    'Ç': 'C', 'Ğ': 'G', 'İ': 'I', 'Ö': 'O', 'Ş': 'S', 'Ü': 'U',
    'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
}


def _rebuild_font_with_raster_additions(target_raw: bytes,
                                         additions: Dict[int, Tuple[List[List[int]], Tuple[int, int, int], str]]) -> Tuple[bytes, List[dict]]:
    target = parse_bcfnt(target_raw)
    if not additions:
        return target_raw, []
    if target.pixel_format not in (8, 9, 11):
        raise ValueError(f"Turkish glyph synthesis supports A8/LA4/A4; got format {target.pixel_format}")

    sheets = [_extract_sheet(target, i) for i in range(target.sheet_count)]
    mapping = dict(target.mapping)
    widths = dict(target.widths)
    used = set(mapping.values())
    capacity = target.capacity
    free_slots = [i for i in range(capacity) if i not in used and i not in widths]
    free_slots += [i for i in range(capacity) if i not in used and i in widths and i not in free_slots]
    records: List[dict] = []

    for code in sorted(additions):
        mask, metric, donor_name = additions[code]
        replaced = code in mapping
        if replaced:
            dest_idx = mapping[code]
        elif free_slots:
            dest_idx = free_slots.pop(0)
        else:
            sheets.append(bytearray(target.sheet_size))
            old_capacity = capacity
            capacity += target.slots_per_sheet
            free_slots.extend(range(old_capacity, capacity))
            dest_idx = free_slots.pop(0)
        dst_sheet_idx = dest_idx // target.slots_per_sheet
        dst_slot = dest_idx % target.slots_per_sheet
        _write_glyph_mask(target, sheets[dst_sheet_idx], dst_slot, mask)
        mapping[code] = dest_idx
        widths[dest_idx] = metric
        records.append({'char': chr(code), 'codepoint': f'U+{code:04X}', 'donor': donor_name,
                        'target_glyph': dest_idx, 'replaced': replaced})

    new_sheet_count = len(sheets)
    new_capacity = new_sheet_count * target.slots_per_sheet
    fallback = (int(target.finf[5]), int(target.finf[6]), int(target.finf[7]))
    metric_rows = [widths.get(i, fallback) for i in range(new_capacity)]

    prefix = bytearray(target.raw[:target.sheet_data_offset])
    for sheet in sheets:
        prefix += sheet
    new_tglp_size = len(prefix) - target.tglp_start
    struct.pack_into(target.order + 'I', prefix, target.tglp_start + 4, new_tglp_size)
    struct.pack_into(target.order + 'H', prefix, target.tglp_start + 16, new_sheet_count)

    cwdh_start = len(prefix)
    cwdh_size = _align4(16 + new_capacity * 3)
    cwdh = bytearray(cwdh_size)
    struct.pack_into(target.order + CWDH_STRUCT, cwdh, 0, b'CWDH', cwdh_size, 0, new_capacity - 1, 0)
    pos = 16
    for left, glyph_w, char_w in metric_rows:
        struct.pack_into('b', cwdh, pos, max(-128, min(127, int(left))))
        cwdh[pos + 1] = max(0, min(255, int(glyph_w)))
        cwdh[pos + 2] = max(0, min(255, int(char_w)))
        pos += 3

    items = sorted(mapping.items())
    cmap_start = cwdh_start + len(cwdh)
    cmap_size = _align4(20 + 2 + len(items) * 4)
    cmap = bytearray(cmap_size)
    struct.pack_into(target.order + CMAP_STRUCT, cmap, 0, b'CMAP', cmap_size, 0, 0xFFFF, 2, 0, 0)
    struct.pack_into(target.order + 'H', cmap, 20, len(items))
    pos = 22
    for code, idx in items:
        struct.pack_into(target.order + '2H', cmap, pos, code, idx)
        pos += 4

    out = prefix + cwdh + cmap
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x14, cwdh_start + 8)
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x18, cmap_start + 8)
    struct.pack_into(target.order + 'I', out, target.finf_start + 0x10, target.tglp_start + 8)
    struct.pack_into(target.order + 'I', out, 0x0C, len(out))
    struct.pack_into(target.order + 'I', out, 0x10, 4)
    verified = parse_bcfnt(bytes(out))
    for code in additions:
        if code not in verified.mapping:
            raise RuntimeError(f"Synthesized glyph U+{code:04X} missing after rebuild")
    return bytes(out), records


def _choose_turkish_donor(target: FontInfo, candidates: List[Tuple[str, FontInfo]], code: int, base: int) -> Tuple[str, FontInfo]:
    usable = [(name, d) for name, d in candidates if code in d.mapping and base in d.mapping]
    if not usable:
        usable = [(name, d) for name, d in candidates if code in d.mapping]
    if not usable:
        raise ValueError(f"No donor contains U+{code:04X}")
    def score(item: Tuple[str, FontInfo]) -> float:
        _, d = item
        dw = abs(target.cell_width - d.cell_width) / max(1, target.cell_width)
        dh = abs(target.cell_height - d.cell_height) / max(1, target.cell_height)
        # Prefer matching sheet pixel format slightly, but geometry/style size dominates.
        fmt = 0.0 if target.pixel_format == d.pixel_format else 0.12
        return dw + dh + fmt
    return min(usable, key=score)



def merge_missing_from_language_variants(target_raw: bytes,
                                         donor_raws: List[Tuple[str, bytes]]) -> Tuple[bytes, List[dict]]:
    """Merge same-font glyphs even when language variants use different sheet geometry.

    Compatible variants are copied bit-for-bit by repair_bcfnt first. This pass handles
    the remaining union by raster-resizing glyphs from the closest same-name language
    variant, which is important for Brain Train's special/title fonts whose dimensions
    differ by language.
    """
    target = parse_bcfnt(target_raw)
    donors: List[Tuple[str, FontInfo]] = []
    union: Set[int] = set(target.mapping)
    for name, raw in donor_raws:
        try:
            d = parse_bcfnt(raw)
        except Exception:
            continue
        donors.append((name, d))
        union.update(d.mapping)
    missing = sorted(union - set(target.mapping))
    if not missing:
        return target_raw, []
    additions: Dict[int, Tuple[List[List[int]], Tuple[int, int, int], str]] = {}
    for code in missing:
        candidates = [(name, d) for name, d in donors if code in d.mapping]
        if not candidates:
            continue
        def score(item: Tuple[str, FontInfo]) -> float:
            _, d = item
            dw = abs(target.cell_width - d.cell_width) / max(1, target.cell_width)
            dh = abs(target.cell_height - d.cell_height) / max(1, target.cell_height)
            fmt = 0.0 if target.pixel_format == d.pixel_format else 0.15
            return dw + dh + fmt
        donor_name, donor = min(candidates, key=score)
        mask = _resize_mask(_glyph_alpha_matrix(donor, code), target.cell_width, target.cell_height)
        didx = donor.mapping[code]
        dm = donor.widths.get(didx, (int(donor.finf[5]), int(donor.finf[6]), int(donor.finf[7])))
        scale = target.cell_width / max(1.0, donor.cell_width)
        metric = (
            max(-128, min(127, int(round(dm[0] * scale)))),
            max(0, min(255, int(round(dm[1] * scale)))),
            max(0, min(255, int(round(dm[2] * scale)))),
        )
        additions[code] = (mask, metric, donor_name)
    return _rebuild_font_with_raster_additions(target_raw, additions)



def repair_blank_mapped_glyphs(target_raw: bytes,
                               donor_raws: List[Tuple[str, bytes]]) -> Tuple[bytes, List[dict]]:
    """Replace mapped-but-empty visible glyph cells using the closest non-empty donor."""
    target = parse_bcfnt(target_raw)
    if target.pixel_format not in (8, 9, 11):
        return target_raw, []
    blank_codes = []
    for code in sorted(target.mapping):
        ch = chr(code)
        if ch.isspace():
            continue
        if _glyph_is_blank(target, code):
            blank_codes.append(code)
    if not blank_codes:
        return target_raw, []
    donors: List[Tuple[str, FontInfo]] = []
    for name, raw in donor_raws:
        try:
            d = parse_bcfnt(raw)
        except Exception:
            continue
        if d.pixel_format in (8, 9, 11):
            donors.append((name, d))
    additions: Dict[int, Tuple[List[List[int]], Tuple[int, int, int], str]] = {}
    for code in blank_codes:
        candidates = [(name, d) for name, d in donors
                      if code in d.mapping and not _glyph_is_blank(d, code)]
        if not candidates:
            continue
        def score(item: Tuple[str, FontInfo]) -> float:
            _, d = item
            dw = abs(target.cell_width - d.cell_width) / max(1, target.cell_width)
            dh = abs(target.cell_height - d.cell_height) / max(1, target.cell_height)
            fmt = 0.0 if target.pixel_format == d.pixel_format else 0.12
            return dw + dh + fmt
        donor_name, donor = min(candidates, key=score)
        mask = _resize_mask(_glyph_alpha_matrix(donor, code), target.cell_width, target.cell_height)
        tidx = target.mapping[code]
        metric = target.widths.get(tidx, (int(target.finf[5]), int(target.finf[6]), int(target.finf[7])))
        additions[code] = (mask, metric, donor_name)
    return _rebuild_font_with_raster_additions(target_raw, additions)


def synthesize_missing_turkish(target_raw: bytes,
                               donor_raws: List[Tuple[str, bytes]]) -> Tuple[bytes, List[dict]]:
    target = parse_bcfnt(target_raw)
    missing = [c for c in TURKISH_CORE if ord(c) not in target.mapping or _glyph_is_blank(target, ord(c))]
    if not missing:
        return target_raw, []
    candidates: List[Tuple[str, FontInfo]] = []
    for name, raw in donor_raws:
        try:
            d = parse_bcfnt(raw)
        except Exception:
            continue
        if all(ord(c) in d.mapping for c in TURKISH_CORE):
            candidates.append((name, d))
    if not candidates:
        raise ValueError("No complete Turkish donor font is available")

    additions: Dict[int, Tuple[List[List[int]], Tuple[int, int, int], str]] = {}
    default_metric = (int(target.finf[5]), int(target.finf[6]), int(target.finf[7]))
    for ch in missing:
        code = ord(ch)
        base_ch = TURKISH_BASE[ch]
        base_code = ord(base_ch)
        donor_name, donor = _choose_turkish_donor(target, candidates, code, base_code)

        if ch == 'ı' and base_code in target.mapping and not _glyph_is_blank(target, base_code):
            target_base = _glyph_alpha_matrix(target, base_code)
            mask = _dotless_i(target_base)
            if mask == target_base:
                mask = _resize_mask(_glyph_alpha_matrix(donor, code), target.cell_width, target.cell_height)
        elif base_code in target.mapping and base_code in donor.mapping and not _glyph_is_blank(target, base_code):
            target_base = _glyph_alpha_matrix(target, base_code)
            mask = _accent_overlay(donor, code, base_code, target_base, target.cell_width, target.cell_height)
            if mask == target_base or not any(any(v > 0 for v in row) for row in mask):
                mask = _resize_mask(_glyph_alpha_matrix(donor, code), target.cell_width, target.cell_height)
        else:
            mask = _resize_mask(_glyph_alpha_matrix(donor, code), target.cell_width, target.cell_height)

        if base_code in target.mapping:
            base_idx = target.mapping[base_code]
            metric = target.widths.get(base_idx, default_metric)
        else:
            didx = donor.mapping[code]
            dm = donor.widths.get(didx, (int(donor.finf[5]), int(donor.finf[6]), int(donor.finf[7])))
            scale = target.cell_width / max(1.0, donor.cell_width)
            metric = (
                max(-128, min(127, int(round(dm[0] * scale)))),
                max(0, min(255, int(round(dm[1] * scale)))),
                max(0, min(255, int(round(dm[2] * scale)))),
            )
        additions[code] = (mask, metric, donor_name)

    return _rebuild_font_with_raster_additions(target_raw, additions)

def repair_fonts_extended(msg_root: Path, patch_font_dir: Path, out_dir: Path, report_csv: Optional[Path] = None) -> List[Path]:
    """Build a complete repaired font set.

    Pass 1 merges every compatible European/US language variant of each font.
    If the user's Turkish patch contains that font, it is used as the target so
    its hand-made Turkish glyphs win. Pass 2 fills Turkish core glyphs still
    absent from unmodified/special fonts by preserving their local base letter
    where possible and borrowing only the diacritic from the closest complete
    SPARTA donor; if the base itself is absent, the complete glyph is rescaled.
    """
    msg_root = Path(msg_root)
    patch_font_dir = Path(patch_font_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lang_dirs = sorted([p for p in msg_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    if not lang_dirs:
        raise ValueError(f"No language folders found under {msg_root}")
    eu_en = msg_root / 'EU_English'
    seed_dir = eu_en if eu_en.is_dir() else lang_dirs[0]
    font_names = sorted(p.name for p in seed_dir.glob('*.bcfnt*'))
    if not font_names:
        raise ValueError(f"No BCFNT files found under {seed_dir}")

    stage_raws: Dict[str, bytes] = {}
    meta: Dict[str, dict] = {}
    for name in font_names:
        patch_path = patch_font_dir / name
        preferred_path = eu_en / name if (eu_en / name).is_file() else seed_dir / name
        target_path = patch_path if patch_path.is_file() else preferred_path
        target_raw, target_kind = decompress_auto(target_path.read_bytes())
        before = parse_bcfnt(target_raw)
        donor_raws: List[Tuple[str, bytes]] = []
        preferred_raw = None
        for ld in lang_dirs:
            dp = ld / name
            if not dp.is_file():
                continue
            raw, _ = decompress_auto(dp.read_bytes())
            donor_raws.append((ld.name, raw))
            if ld.name == 'EU_English':
                preferred_raw = raw
        if not donor_raws:
            donor_raws = [('base', target_raw)]
        fixed_union_raw, union_report = repair_bcfnt(target_raw, donor_raws, preferred_raw=preferred_raw)
        # Some same-name font variants use different cell/sheet geometry per language;
        # merge those remaining glyphs by raster resizing instead of silently skipping them.
        fixed_union_raw, raster_union = merge_missing_from_language_variants(fixed_union_raw, donor_raws)
        stage_raws[name] = fixed_union_raw
        meta[name] = {
            'source': 'TurkishPatch' if patch_path.is_file() else 'EU_English',
            'kind': target_kind,
            'before_chars': len(before.mapping),
            'before_sheets': before.sheet_count,
            'union_added': union_report['added'] + raster_union,
            'compressed_before': target_path.stat().st_size,
        }

    # Repair glyphs that are mapped but have an empty raster cell (notably many
    # accented Latin glyphs in SPARTA2/SPARTA15). Use the full same-game font pool
    # so a visually close non-empty glyph can be borrowed when every language copy
    # of the same font is blank.
    blank_donor_pool = [(name.rsplit('.bcfnt', 1)[0], raw) for name, raw in stage_raws.items()]
    for name in font_names:
        repaired, blank_records = repair_blank_mapped_glyphs(stage_raws[name], blank_donor_pool)
        stage_raws[name] = repaired
        meta[name]['blank_repaired'] = blank_records

    # Complete donor pool includes the user's hand-made Turkish fonts and SPARTA4,
    # which already carries broad Latin/Turkish coverage in the original game.
    complete_donors = [(name.rsplit('.bcfnt', 1)[0], raw) for name, raw in stage_raws.items()
                       if all(ord(c) in parse_bcfnt(raw).mapping and not _glyph_is_blank(parse_bcfnt(raw), ord(c))
                              for c in TURKISH_CORE)]
    if not complete_donors:
        raise RuntimeError("No complete Turkish donor font found after European merge")

    created: List[Path] = []
    report_rows: List[dict] = []
    for name in font_names:
        stage = stage_raws[name]
        final_raw, synth_records = synthesize_missing_turkish(stage, complete_donors)
        final = parse_bcfnt(final_raw)
        missing_tr = ''.join(c for c in TURKISH_CORE if ord(c) not in final.mapping)
        if missing_tr:
            raise RuntimeError(f"{name}: Turkish glyph synthesis incomplete: {missing_tr}")
        packed = compress_as(final_raw, meta[name]['kind'])
        out_path = out_dir / name
        out_path.write_bytes(packed)
        verify_raw, _ = decompress_auto(packed)
        verify = parse_bcfnt(verify_raw)
        if any(ord(c) not in verify.mapping for c in TURKISH_CORE):
            raise RuntimeError(f"{name}: packed font verification failed")
        created.append(out_path)
        union_added = meta[name]['union_added']
        report_rows.append({
            'Font': name,
            'BaseSource': meta[name]['source'],
            'CharactersBefore': meta[name]['before_chars'],
            'CharactersAfter': len(verify.mapping),
            'SheetsBefore': meta[name]['before_sheets'],
            'SheetsAfter': verify.sheet_count,
            'EuropeanUnionAdded': ' '.join(r['char'] for r in union_added),
            'EuropeanDonors': ', '.join(sorted(set(r['donor'] for r in union_added))),
            'BlankGlyphsRepaired': ' '.join(r['char'] for r in meta[name].get('blank_repaired', [])),
            'BlankGlyphDonors': ', '.join(sorted(set(r['donor'] for r in meta[name].get('blank_repaired', [])))),
            'TurkishSynthesized': ' '.join(r['char'] for r in synth_records),
            'TurkishDonors': ', '.join(sorted(set(r['donor'] for r in synth_records))),
            'MissingTurkishCore': '',
            'CompressedBytesBefore': meta[name]['compressed_before'],
            'CompressedBytesAfter': out_path.stat().st_size,
        })

    if report_csv:
        report_csv = Path(report_csv)
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open('w', encoding='utf-8-sig', newline='') as f:
            fields = list(report_rows[0].keys()) if report_rows else ['Font']
            w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
            w.writeheader(); w.writerows(report_rows)
    return created


def repair_fonts_safe(msg_root: Path, patch_font_dir: Path, out_dir: Path,
                      report_csv: Optional[Path] = None) -> List[Path]:
    """High-confidence repair: only touch fonts already present in the Turkish patch.

    Hand-made Turkish glyphs are preserved. Missing same-font glyphs are merged from
    every language variant (bit-for-bit when geometry matches, raster-scaled when a
    language-specific version uses different geometry). FINF defaults are restored
    from original EU_English. No new Turkish glyph is invented for unrelated special
    fonts, so this mode is the recommended patch build.
    """
    msg_root = Path(msg_root); patch_font_dir = Path(patch_font_dir); out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lang_dirs = sorted([p for p in msg_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    patch_paths = sorted(patch_font_dir.glob('*.bcfnt*'))
    created: List[Path] = []; rows: List[dict] = []
    for patch_path in patch_paths:
        target_raw, target_kind = decompress_auto(patch_path.read_bytes())
        before = parse_bcfnt(target_raw)
        donor_raws: List[Tuple[str, bytes]] = []
        preferred_raw = None
        for ld in lang_dirs:
            dp = ld / patch_path.name
            if not dp.is_file():
                continue
            raw, _ = decompress_auto(dp.read_bytes())
            donor_raws.append((ld.name, raw))
            if ld.name == 'EU_English': preferred_raw = raw
        fixed, report1 = repair_bcfnt(target_raw, donor_raws, preferred_raw=preferred_raw)
        fixed, report2 = merge_missing_from_language_variants(fixed, donor_raws)
        vf = parse_bcfnt(fixed)
        missing_tr = ''.join(c for c in TURKISH_CORE if ord(c) not in vf.mapping or _glyph_is_blank(vf, ord(c)))
        if missing_tr:
            raise RuntimeError(f"{patch_path.name}: Turkish glyph missing/blank after safe repair: {missing_tr}")
        # Verify all mapped visible glyphs in the patch target remain non-empty unless
        # they were already intentionally whitespace. This catches accidental sheet damage.
        packed = compress_as(fixed, target_kind)
        out_path = out_dir / patch_path.name
        out_path.write_bytes(packed)
        check = parse_bcfnt(decompress_auto(packed)[0])
        created.append(out_path)
        added = report1['added'] + report2
        rows.append({
            'Font': patch_path.name,
            'Mode': 'safe',
            'CharactersBefore': len(before.mapping),
            'CharactersAfter': len(check.mapping),
            'SheetsBefore': before.sheet_count,
            'SheetsAfter': check.sheet_count,
            'EuropeanUnionAdded': ' '.join(r['char'] for r in added),
            'EuropeanDonors': ', '.join(sorted(set(r['donor'] for r in added))),
            'MissingTurkishCore': '',
            'CompressedBytesBefore': patch_path.stat().st_size,
            'CompressedBytesAfter': out_path.stat().st_size,
        })
    if report_csv:
        report_csv = Path(report_csv); report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open('w', encoding='utf-8-sig', newline='') as f:
            fields = list(rows[0].keys()) if rows else ['Font']
            w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)
    return created


def repair_fonts(msg_root: Path, patch_font_dir: Path, out_dir: Path,
                 report_csv: Optional[Path] = None, mode: str = 'safe') -> List[Path]:
    mode = mode.lower().strip()
    if mode == 'safe':
        return repair_fonts_safe(msg_root, patch_font_dir, out_dir, report_csv)
    if mode == 'extended':
        return repair_fonts_extended(msg_root, patch_font_dir, out_dir, report_csv)
    raise ValueError("Font repair mode must be 'safe' or 'extended'")

def audit_fonts(msg_root: Path, patch_font_dir: Path, out_csv: Path) -> None:
    msg_root = Path(msg_root); patch_font_dir = Path(patch_font_dir); out_csv = Path(out_csv)
    langs = sorted([p for p in msg_root.iterdir() if p.is_dir()], key=lambda p: p.name)
    rows = []
    for p in sorted(patch_font_dir.glob('*.bcfnt*')):
        target = parse_bcfnt(decompress_auto(p.read_bytes())[0])
        union: Set[int] = set()
        for ld in langs:
            dp = ld / p.name
            if dp.is_file():
                d = parse_bcfnt(decompress_auto(dp.read_bytes())[0])
                union.update(d.mapping)
        missing = sorted(union - set(target.mapping))
        visible_blank = []
        if target.pixel_format in (8, 9, 11):
            visible_blank = sorted(cp for cp in target.mapping
                                   if not chr(cp).isspace() and _glyph_is_blank(target, cp))
        bad_tr = ''.join(c for c in TURKISH_CORE
                         if ord(c) not in target.mapping or
                         (target.pixel_format in (8, 9, 11) and _glyph_is_blank(target, ord(c))))
        eu_default = None
        ep = msg_root / 'EU_English' / p.name
        if ep.is_file():
            eu = parse_bcfnt(decompress_auto(ep.read_bytes())[0])
            eu_default = eu.finf[4:8]
        rows.append({
            'Font': p.name,
            'MappedCharacters': len(target.mapping),
            'GlyphCapacity': target.capacity,
            'MissingFromAllLanguageUnion': ''.join(chr(c) for c in missing),
            'MappedButBlankVisibleGlyphs': ''.join(chr(c) for c in visible_blank),
            'MissingOrBlankTurkishCore': bad_tr,
            'FINF_DefaultLeft': target.finf[5],
            'FINF_DefaultGlyphWidth': target.finf[6],
            'FINF_DefaultCharWidth': target.finf[7],
            'FINF_AlterCharIndex': target.finf[4],
            'FINF_Matches_EU_English': '' if eu_default is None else str(target.finf[4:8] == eu_default),
        })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8-sig', newline='') as f:
        fields = list(rows[0].keys()) if rows else ['Font']
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL); w.writeheader(); w.writerows(rows)


# -----------------------------
# GUI
# -----------------------------

def launch_gui() -> None:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title('Brain Train 3DS Localization Tool')
    root.geometry('900x610')

    nb = ttk.Notebook(root)
    nb.pack(fill='both', expand=True, padx=10, pady=10)

    def path_row(parent, row, label, var, choose_dir=True):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', padx=5, pady=6)
        ttk.Entry(parent, textvariable=var, width=85).grid(row=row, column=1, sticky='ew', padx=5, pady=6)
        def choose():
            p = filedialog.askdirectory() if choose_dir else filedialog.askopenfilename()
            if p: var.set(p)
        ttk.Button(parent, text='Seç...', command=choose).grid(row=row, column=2, padx=5, pady=6)

    # Export tab
    tab1 = ttk.Frame(nb); nb.add(tab1, text='MSBT → CSV')
    tab1.columnconfigure(1, weight=1)
    v_msg = tk.StringVar(); v_patch = tk.StringVar(); v_csvout = tk.StringVar(); v_patchcol = tk.StringVar(value='TR_Patch')
    path_row(tab1, 0, 'Ana msg klasörü (dil klasörlerini içerir):', v_msg)
    path_row(tab1, 1, 'Türkçe patch EU_English klasörü (opsiyonel):', v_patch)
    path_row(tab1, 2, 'CSV çıktı klasörü:', v_csvout)
    ttk.Label(tab1, text='Patch sütun adı:').grid(row=3, column=0, sticky='w', padx=5, pady=6)
    ttk.Entry(tab1, textvariable=v_patchcol).grid(row=3, column=1, sticky='w', padx=5, pady=6)
    def do_export():
        try:
            files = export_multilang_csv(Path(v_msg.get()), Path(v_csvout.get()), Path(v_patch.get()) if v_patch.get() else None, v_patchcol.get() or 'TR_Patch')
            messagebox.showinfo('Tamam', f'{len(files)} CSV oluşturuldu.')
        except Exception as e:
            messagebox.showerror('Hata', str(e))
    ttk.Button(tab1, text='Tüm MSBT dosyalarını CSV’ye çıkar', command=do_export).grid(row=4, column=1, sticky='w', padx=5, pady=15)

    # Inject tab
    tab2 = ttk.Frame(nb); nb.add(tab2, text='CSV → MSBT')
    tab2.columnconfigure(1, weight=1)
    v_csvin = tk.StringVar(); v_base = tk.StringVar(); v_msbtout = tk.StringVar(); v_col = tk.StringVar(value='TR_Patch')
    path_row(tab2, 0, 'CSV klasörü:', v_csvin)
    path_row(tab2, 1, 'Enjeksiyon tabanı (örn. EU_English):', v_base)
    path_row(tab2, 2, 'Yeni MSBT çıktı klasörü:', v_msbtout)
    ttk.Label(tab2, text='Enjekte edilecek sütun:').grid(row=3, column=0, sticky='w', padx=5, pady=6)
    ttk.Entry(tab2, textvariable=v_col).grid(row=3, column=1, sticky='w', padx=5, pady=6)
    def do_inject():
        try:
            files = inject_csv_dir(Path(v_csvin.get()), Path(v_base.get()), Path(v_msbtout.get()), v_col.get())
            messagebox.showinfo('Tamam', f'{len(files)} MSBT oluşturuldu ve doğrulandı.')
        except Exception as e:
            messagebox.showerror('Hata', str(e))
    ttk.Button(tab2, text='CSV çevirisini MSBT’ye enjekte et', command=do_inject).grid(row=4, column=1, sticky='w', padx=5, pady=15)

    # Font repair tab
    tab3 = ttk.Frame(nb); nb.add(tab3, text='Font Düzelt')
    tab3.columnconfigure(1, weight=1)
    v_fmsg = tk.StringVar(); v_fpatch = tk.StringVar(); v_fout = tk.StringVar(); v_freport = tk.StringVar(); v_fmode = tk.StringVar(value='safe')
    path_row(tab3, 0, 'Ana msg klasörü (tüm Avrupa/US dilleri):', v_fmsg)
    path_row(tab3, 1, 'Türkçe patch font klasörü:', v_fpatch)
    path_row(tab3, 2, 'Düzeltilmiş font çıktı klasörü:', v_fout)
    path_row(tab3, 3, 'Rapor klasörü:', v_freport)
    ttk.Label(tab3, text='Mod:').grid(row=4, column=0, sticky='w', padx=5, pady=6)
    ttk.Combobox(tab3, textvariable=v_fmode, values=('safe','extended'), state='readonly', width=16).grid(row=4, column=1, sticky='w', padx=5, pady=6)
    def do_font():
        try:
            report = Path(v_freport.get()) / 'font_repair_report.csv' if v_freport.get() else None
            files = repair_fonts(Path(v_fmsg.get()), Path(v_fpatch.get()), Path(v_fout.get()), report, v_fmode.get())
            messagebox.showinfo('Tamam', f'{len(files)} font birleştirildi ve doğrulandı.')
        except Exception as e:
            messagebox.showerror('Hata', str(e))
    ttk.Button(tab3, text='Fontları onar', command=do_font).grid(row=5, column=1, sticky='w', padx=5, pady=15)

    note = ttk.Label(root, text='Not: Mevcut Brain Train dosyalarında LZ11 kullanılıyor. Araç raw/LZ10/LZ11/Nintendo RLE’yi otomatik tanır.', anchor='w')
    note.pack(fill='x', padx=12, pady=(0, 8))
    root.mainloop()


# -----------------------------
# CLI
# -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Brain Train 3DS MSBT/BCFNT localization tool')
    sub = parser.add_subparsers(dest='cmd')

    p = sub.add_parser('export', help='Export all language MSBT files side-by-side to CSV')
    p.add_argument('--msg-root', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--patch-root', type=Path)
    p.add_argument('--patch-column', default='TR_Patch')

    p = sub.add_parser('inject', help='Inject one CSV language column back into MSBT files')
    p.add_argument('--csv-dir', required=True, type=Path)
    p.add_argument('--base-msg-dir', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--column', default='TR_Patch')

    p = sub.add_parser('repair-fonts', help='Merge missing glyphs from other language BCFNT files')
    p.add_argument('--msg-root', required=True, type=Path)
    p.add_argument('--patch-font-dir', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--report', type=Path)
    p.add_argument('--mode', choices=('safe','extended'), default='safe', help='safe: only patch fonts; extended: synthesize missing Turkish glyphs into all fonts')

    p = sub.add_parser('audit-fonts', help='Audit patch font coverage')
    p.add_argument('--msg-root', required=True, type=Path)
    p.add_argument('--patch-font-dir', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)

    p = sub.add_parser('codec-test', help='Round-trip all compressed files under a directory')
    p.add_argument('root', type=Path)

    args = parser.parse_args(argv)
    if args.cmd is None:
        launch_gui(); return 0
    if args.cmd == 'export':
        files = export_multilang_csv(args.msg_root, args.out, args.patch_root, args.patch_column)
        print(f'Created {len(files)} CSV files in {args.out}')
    elif args.cmd == 'inject':
        files = inject_csv_dir(args.csv_dir, args.base_msg_dir, args.out, args.column)
        print(f'Created {len(files)} MSBT files in {args.out}')
    elif args.cmd == 'repair-fonts':
        files = repair_fonts(args.msg_root, args.patch_font_dir, args.out, args.report, args.mode)
        print(f'Created {len(files)} repaired fonts in {args.out}')
    elif args.cmd == 'audit-fonts':
        audit_fonts(args.msg_root, args.patch_font_dir, args.out)
        print(f'Wrote {args.out}')
    elif args.cmd == 'codec-test':
        ok = 0
        for path in args.root.rglob('*'):
            if not path.is_file():
                continue
            packed = path.read_bytes(); raw, kind = decompress_auto(packed)
            if kind == 'raw':
                continue
            repacked = compress_as(raw, kind)
            raw2, kind2 = decompress_auto(repacked)
            if raw2 != raw:
                raise RuntimeError(f'Codec round-trip failed: {path}')
            ok += 1
            print(kind, path)
        print(f'Codec round-trip OK for {ok} files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
