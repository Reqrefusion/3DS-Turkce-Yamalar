#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORAS TR Text Tool
Extracts/rebuilds Pokémon Omega Ruby / Alpha Sapphire Gen 6 GARC text archives.
Stdlib-only. Supports GARC v4/v6, Gen6 encrypted text entries, TSV translation projects.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import zipfile

TOOL_VERSION = "1.2.0"
KEY_BASE = 0x7C89
KEY_ADVANCE = 0x2983
KEY_VARIABLE = 0x0010
KEY_TERMINATOR = 0x0000
KEY_TEXTRETURN = 0xBE00
KEY_TEXTCLEAR = 0xBE01
KEY_TEXTWAIT = 0xBE02
KEY_TEXTNULL = 0xBDFF

REMAP_DECODE = {0xE07F: 0x202F, 0xE08D: 0x2026, 0xE08E: 0x2642, 0xE08F: 0x2640}
REMAP_ENCODE = {v: k for k, v in REMAP_DECODE.items()}
TURKISH_REL_PATHS = {"7/3", "8/1"}
LANGUAGE_SETS = [
    {
        "file": "01_Text_Set_A.tsv",
        "label": "Text Set A",
        "languages": [
            ("Japanese_Kana", "7/1"),
            ("Japanese_Kanji", "7/2"),
            ("Turkish", "7/3"),
            ("French", "7/4"),
            ("Italian", "7/5"),
            ("German", "7/6"),
            ("Spanish", "7/7"),
            ("Korean", "7/8"),
        ],
    },
    {
        "file": "02_Text_Set_B.tsv",
        "label": "Text Set B",
        "languages": [
            ("Japanese_Kana", "7/9"),
            ("Japanese_Kanji", "8/0"),
            ("Turkish", "8/1"),
            ("French", "8/2"),
            ("Italian", "8/3"),
            ("German", "8/4"),
            ("Spanish", "8/5"),
            ("Korean", "8/6"),
        ],
    },
]
COMPARE_REL_PATHS = {rel for spec in LANGUAGE_SETS for _, rel in spec["languages"]}

class ToolError(Exception):
    pass

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def align(n: int, a: int) -> int:
    return (n + a - 1) // a * a

def u16(data: bytes, off: int) -> int:
    return struct.unpack_from('<H', data, off)[0]

def u32(data: bytes, off: int) -> int:
    return struct.unpack_from('<I', data, off)[0]

def i16(data: bytes, off: int) -> int:
    return struct.unpack_from('<h', data, off)[0]

def i32(data: bytes, off: int) -> int:
    return struct.unpack_from('<i', data, off)[0]

def _magic_ok(actual: bytes, logical: bytes) -> bool:
    # On disk, little-endian u32 writes common signatures reversed as bytes: GARC->CRAG, FATO->OTAF, ...
    return actual == logical[::-1] or actual == logical

class GarcArchive:
    def __init__(self, data: bytes):
        self.original = data
        self.version = 0
        self.header_size = 0
        self.fato_padding = 0xFFFF
        self.entries: list[dict] = []
        self._parse(data)

    def _parse(self, b: bytes) -> None:
        if len(b) < 0x1C or not _magic_ok(b[:4], b'GARC'):
            raise ToolError('Geçerli bir GARC arşivi değil.')
        self.header_size = u32(b, 4)
        bom = u16(b, 8)
        self.version = u16(b, 10)
        chunks = u32(b, 12)
        data_offset = u32(b, 16)
        file_len = u32(b, 20)
        if bom != 0xFEFF or chunks != 4 or file_len != len(b):
            raise ToolError('GARC başlığı beklenen yapıda değil.')
        if self.version not in (0x0400, 0x0600):
            raise ToolError(f'Desteklenmeyen GARC sürümü: 0x{self.version:04X}')
        if self.header_size not in (0x1C, 0x24):
            raise ToolError(f'Beklenmeyen GARC başlık boyutu: 0x{self.header_size:X}')

        pos = self.header_size
        if not _magic_ok(b[pos:pos+4], b'FATO'):
            raise ToolError('FATO bölümü bulunamadı.')
        fato_size = u32(b, pos + 4)
        entry_count = u16(b, pos + 8)
        self.fato_padding = u16(b, pos + 10)
        fato_offsets = [u32(b, pos + 12 + i * 4) for i in range(entry_count)]
        pos += fato_size

        if not _magic_ok(b[pos:pos+4], b'FATB'):
            raise ToolError('FATB bölümü bulunamadı.')
        fatb_size = u32(b, pos + 4)
        file_count = u32(b, pos + 8)
        q = pos + 12
        records = []
        sub_count_total = 0
        for idx in range(entry_count):
            if q + 4 > len(b):
                raise ToolError('FATB kesik.')
            vector = u32(b, q); q += 4
            subs = []
            for bit in range(32):
                if (vector >> bit) & 1:
                    if q + 12 > len(b):
                        raise ToolError('FATB alt kayıtları kesik.')
                    start, end, length = struct.unpack_from('<III', b, q); q += 12
                    subs.append({'bit': bit, 'start': start, 'end': end, 'length': length})
                    sub_count_total += 1
            records.append({'vector': vector, 'subs': subs})
        if file_count != sub_count_total:
            # Some tools use entry count here; accept but preserve semantic count when rebuilding.
            pass
        if q > pos + fatb_size:
            raise ToolError('FATB boyutu tutarsız.')
        pos += fatb_size

        if not _magic_ok(b[pos:pos+4], b'FIMB'):
            raise ToolError('FIMB bölümü bulunamadı.')
        fimb_size = u32(b, pos + 4)
        fimb_data_size = u32(b, pos + 8)
        data_base = pos + fimb_size
        if data_base != data_offset:
            raise ToolError('GARC veri offseti tutarsız.')
        if data_base + fimb_data_size > len(b):
            raise ToolError('FIMB veri boyutu dosyayı aşıyor.')

        entries = []
        for idx, rec in enumerate(records):
            out_subs = []
            for sub in rec['subs']:
                start, end, length = sub['start'], sub['end'], sub['length']
                if start > end or length > end - start or data_base + end > len(b):
                    raise ToolError(f'GARC kayıt {idx} offsetleri geçersiz.')
                raw = b[data_base + start:data_base + start + length]
                out_subs.append({'bit': sub['bit'], 'data': raw})
            entries.append({'subs': out_subs})
        self.entries = entries

    @property
    def file_count(self) -> int:
        return sum(len(e['subs']) for e in self.entries)

    def flat_files(self):
        for ei, entry in enumerate(self.entries):
            for sub in entry['subs']:
                yield ei, sub['bit'], sub['data']

    def replace(self, entry_index: int, bit: int, new_data: bytes) -> None:
        try:
            entry = self.entries[entry_index]
        except IndexError:
            raise ToolError(f'GARC entry yok: {entry_index}')
        for sub in entry['subs']:
            if sub['bit'] == bit:
                sub['data'] = new_data
                return
        raise ToolError(f'GARC entry {entry_index} içinde alt dosya {bit} yok.')

    def build(self, pad_to: int | None = None) -> bytes:
        # ORAS v4 uses 4-byte alignment. v6 stores its preferred alignment in header; 4 is a safe/default value.
        if pad_to is None:
            pad_to = 4
        if pad_to < 1:
            pad_to = 4

        entry_count = len(self.entries)
        fato_size = 0x0C + 4 * entry_count
        fatb_body = 0
        sub_total = 0
        vectors = []
        for entry in self.entries:
            vector = 0
            for sub in entry['subs']:
                vector |= 1 << int(sub['bit'])
                sub_total += 1
            vectors.append(vector)
            fatb_body += 4 + 12 * len(entry['subs'])
        fatb_size = 0x0C + fatb_body
        fimb_size = 0x0C
        header_size = 0x24 if self.version == 0x0600 else 0x1C
        data_offset = header_size + fato_size + fatb_size + fimb_size

        fato_offsets = []
        cursor = 0
        for entry in self.entries:
            fato_offsets.append(cursor)
            cursor += 4 + 12 * len(entry['subs'])

        # Build data and new FATB ranges.
        data_blob = bytearray()
        ranges = []
        largest_unpadded = 0
        largest_padded = 0
        for entry in self.entries:
            er = []
            for sub in entry['subs']:
                raw = bytes(sub['data'])
                start = len(data_blob)
                padded_len = align(len(raw), pad_to)
                data_blob += raw
                if padded_len > len(raw):
                    data_blob += b'\xFF' * (padded_len - len(raw))
                end = len(data_blob)
                er.append((start, end, len(raw)))
                largest_unpadded = max(largest_unpadded, len(raw))
                largest_padded = max(largest_padded, padded_len)
            ranges.append(er)

        out = io.BytesIO()
        w = out.write
        # Signatures are written as little-endian integers by Nintendo/community tools, appearing reversed in bytes.
        w(b'CRAG')
        w(struct.pack('<IHHI', header_size, 0xFEFF, self.version, 4))
        w(struct.pack('<III', data_offset, data_offset + len(data_blob), largest_padded if self.version == 0x0600 else largest_unpadded))
        if self.version == 0x0600:
            w(struct.pack('<II', largest_unpadded, pad_to))
        w(b'OTAF')
        w(struct.pack('<IHH', fato_size, entry_count, self.fato_padding))
        for off in fato_offsets:
            w(struct.pack('<I', off))
        w(b'BTAF')
        w(struct.pack('<II', fatb_size, sub_total))
        for vector, er in zip(vectors, ranges):
            w(struct.pack('<I', vector))
            for start, end, length in er:
                w(struct.pack('<III', start, end, length))
        w(b'BMIF')
        w(struct.pack('<II', fimb_size, len(data_blob)))
        w(data_blob)
        result = out.getvalue()
        if len(result) != data_offset + len(data_blob):
            raise ToolError('İç hata: GARC toplam boyutu hesaplanamadı.')
        return result


def looks_like_text_file(data: bytes) -> bool:
    try:
        if len(data) < 20:
            return False
        sections = u16(data, 0)
        line_count = u16(data, 2)
        total = u32(data, 4)
        initial = u32(data, 8)
        sdo = u32(data, 12)
        if sections != 1 or initial != 0 or sdo != 16:
            return False
        if sdo + total != len(data) or u32(data, sdo) != total:
            return False
        table_end = sdo + 4 + line_count * 8
        if table_end > len(data):
            return False
        for i in range(line_count):
            off = i32(data, sdo + 4 + i * 8) + sdo
            ln = i16(data, sdo + 8 + i * 8)
            if ln < 0 or off < table_end or off + ln * 2 > len(data):
                return False
        return True
    except (struct.error, IndexError):
        return False


def line_key(index: int) -> int:
    return (KEY_BASE + index * KEY_ADVANCE) & 0xFFFF


def crypt_line(data: bytes, key: int) -> bytes:
    if len(data) % 2:
        raise ToolError('Şifreli metin satırı tek byte uzunlukta.')
    out = bytearray(len(data))
    for i in range(0, len(data), 2):
        value = u16(data, i) ^ key
        struct.pack_into('<H', out, i, value)
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return bytes(out)


def decode_line(dec: bytes) -> str:
    vals = [u16(dec, i) for i in range(0, len(dec), 2)]
    out: list[str] = []
    i = 0
    while i < len(vals):
        v = vals[i]; i += 1
        if v == KEY_TERMINATOR:
            break
        if v == KEY_VARIABLE:
            if i + 1 >= len(vals):
                raise ToolError('Eksik VAR kontrol kodu.')
            count = vals[i]; variable = vals[i+1]; i += 2
            arg_count = max(0, count - 1)
            if i + arg_count > len(vals):
                raise ToolError('VAR argümanları eksik.')
            args = vals[i:i+arg_count]; i += arg_count
            if variable == KEY_TEXTRETURN:
                out.append(r'\r')
            elif variable == KEY_TEXTCLEAR:
                out.append(r'\c')
            elif variable == KEY_TEXTWAIT and args:
                out.append(f'[WAIT {args[0]}]')
            elif variable == KEY_TEXTNULL and args:
                out.append(f'[~ {args[0]}]')
            else:
                suffix = '(' + ','.join(f'{x:04X}' for x in args) + ')' if args else ''
                out.append(f'[VAR {variable:04X}{suffix}]')
            continue
        if v == 0x000A:
            out.append(r'\n')
        elif v == 0x005C:
            out.append(r'\\')
        elif v == 0x005B:
            out.append(r'\[')
        else:
            v = REMAP_DECODE.get(v, v)
            # Text is stored as UTF-16 code units; combine valid surrogate pairs for UTF-8 TSV output.
            if 0xD800 <= v <= 0xDBFF and i < len(vals) and 0xDC00 <= vals[i] <= 0xDFFF:
                lo = vals[i]; i += 1
                cp = 0x10000 + ((v - 0xD800) << 10) + (lo - 0xDC00)
                out.append(chr(cp))
            elif 0xD800 <= v <= 0xDFFF:
                # Preserve malformed/lone UTF-16 units in an editable round-trip token.
                out.append(f'[U16 {v:04X}]')
            else:
                out.append(chr(v))
    return ''.join(out)


def decode_text_file(data: bytes) -> list[str]:
    if not looks_like_text_file(data):
        raise ToolError('Bu GARC alt dosyası Gen 6 metin dosyası değil.')
    line_count = u16(data, 2)
    sdo = u32(data, 12)
    result = []
    for idx in range(line_count):
        off = i32(data, sdo + 4 + idx * 8) + sdo
        length_units = i16(data, sdo + 8 + idx * 8)
        encrypted = data[off:off + length_units * 2]
        result.append(decode_line(crypt_line(encrypted, line_key(idx))))
    return result


def _parse_var_token(token: str) -> list[int]:
    token = token.strip()
    if token.startswith('WAIT '):
        return [KEY_VARIABLE, 1, KEY_TEXTWAIT, int(token[5:].strip(), 10) & 0xFFFF]
    if token.startswith('~ '):
        return [KEY_VARIABLE, 1, KEY_TEXTNULL, int(token[2:].strip(), 10) & 0xFFFF]
    if token.startswith('U16 '):
        try:
            return [int(token[4:].strip(), 16) & 0xFFFF]
        except ValueError:
            raise ToolError(f'Hatalı U16 etiketi: [{token}]')
    if token.startswith('VAR '):
        body = token[4:].strip()
        args: list[int] = []
        if '(' in body:
            if not body.endswith(')'):
                raise ToolError(f'Hatalı VAR: [{token}]')
            code, argstr = body[:-1].split('(', 1)
            if argstr.strip():
                args = [int(x.strip(), 16) & 0xFFFF for x in argstr.split(',')]
        else:
            code = body
        try:
            variable = int(code.strip(), 16) & 0xFFFF
        except ValueError:
            raise ToolError(f'VAR kodu hex olmalı: [{token}]')
        return [KEY_VARIABLE, 1 + len(args), variable, *args]
    raise ToolError(f'Bilinmeyen kontrol etiketi: [{token}]')


def encode_line(text: str) -> bytes:
    vals: list[int] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '\\':
            if i + 1 >= len(text):
                raise ToolError('Satır sonunda tek \\ kullanılamaz.')
            esc = text[i+1]; i += 2
            if esc == 'n': vals.append(0x000A)
            elif esc == 'r': vals.extend([KEY_VARIABLE, 1, KEY_TEXTRETURN])
            elif esc == 'c': vals.extend([KEY_VARIABLE, 1, KEY_TEXTCLEAR])
            elif esc == '\\': vals.append(0x005C)
            elif esc == '[': vals.append(0x005B)
            else: raise ToolError(f'Bilinmeyen kaçış: \\{esc}')
            continue
        if ch == '[':
            end = text.find(']', i + 1)
            if end < 0:
                raise ToolError('Kapanmamış [ kontrol etiketi var.')
            vals.extend(_parse_var_token(text[i+1:end]))
            i = end + 1
            continue
        cp = ord(ch)
        if cp > 0x10FFFF:
            raise ToolError(f'Geçersiz Unicode karakteri: U+{cp:06X}')
        if cp > 0xFFFF:
            cp2 = cp - 0x10000
            vals.append(0xD800 + (cp2 >> 10))
            vals.append(0xDC00 + (cp2 & 0x3FF))
        else:
            vals.append(REMAP_ENCODE.get(cp, cp))
        i += 1
    vals.append(KEY_TERMINATOR)
    return struct.pack('<' + 'H' * len(vals), *vals)


def build_text_file(lines: list[str]) -> bytes:
    if len(lines) > 0xFFFF:
        raise ToolError('Bir metin dosyasında 65535 satırdan fazlası desteklenmiyor.')
    enc_lines: list[bytes] = []
    for idx, line in enumerate(lines):
        plain = encode_line(line)
        enc = crypt_line(plain, line_key(idx))
        # Game files conventionally pad each encrypted line to an even number of u16s (4-byte boundary).
        if len(enc) % 4 == 2:
            enc += b'\x00\x00'
        enc_lines.append(enc)

    table_size = 4 + len(lines) * 8
    cursor = table_size
    table = bytearray()
    body = bytearray()
    for enc in enc_lines:
        units = len(enc) // 2
        if units > 0x7FFF:
            raise ToolError('Tek bir metin satırı çok uzun.')
        table += struct.pack('<IHH', cursor, units, 0)
        body += enc
        cursor += len(enc)
    total = table_size + len(body)
    header = struct.pack('<HHIII', 1, len(lines), total, 0, 16)
    return header + struct.pack('<I', total) + table + body


def read_tsv(path: Path) -> list[str]:
    lines = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f, delimiter='\t')
        if not r.fieldnames or 'line_id' not in r.fieldnames or 'text' not in r.fieldnames:
            raise ToolError(f'TSV başlığı hatalı: {path}')
        expected = 0
        for row in r:
            try:
                idx = int(row['line_id'])
            except Exception:
                raise ToolError(f'Geçersiz line_id: {path}')
            if idx != expected:
                raise ToolError(f'{path}: line_id sırası bozuk; {expected} bekleniyordu, {idx} geldi.')
            lines.append(row.get('text', '') or '')
            expected += 1
    return lines


def write_tsv(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        w.writerow(['line_id', 'text'])
        for i, text in enumerate(lines):
            w.writerow([i, text])


def write_master_tsv(path: Path, rows: list[tuple[int, int, int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        w.writerow(['entry', 'bit', 'line_id', 'text'])
        for entry, bit, line_id, text in rows:
            w.writerow([entry, bit, line_id, text])


def read_master_tsv(path: Path) -> dict[tuple[int, int], list[str]]:
    groups: dict[tuple[int, int], list[str]] = {}
    expected: dict[tuple[int, int], int] = {}
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f, delimiter='\t')
        required = {'entry', 'bit', 'line_id', 'text'}
        if not r.fieldnames or not required.issubset(set(r.fieldnames)):
            raise ToolError(f'TSV başlığı hatalı: {path}')
        for row in r:
            try:
                entry = int(row['entry']); bit = int(row['bit']); line_id = int(row['line_id'])
            except Exception:
                raise ToolError(f'Geçersiz entry/bit/line_id: {path}')
            key = (entry, bit)
            exp = expected.get(key, 0)
            if line_id != exp:
                raise ToolError(f'{path}: entry {entry}/{bit} için line_id {exp} bekleniyordu, {line_id} geldi.')
            groups.setdefault(key, []).append(row.get('text', '') or '')
            expected[key] = exp + 1
    return groups

def _discover_input(input_path: Path) -> tuple[Path, tempfile.TemporaryDirectory | None]:
    if input_path.is_dir():
        return input_path, None
    if input_path.is_file() and zipfile.is_zipfile(input_path):
        td = tempfile.TemporaryDirectory(prefix='oras_tr_')
        base = Path(td.name).resolve()
        with zipfile.ZipFile(input_path) as z:
            for info in z.infolist():
                name = info.filename.replace('\\', '/')
                target = (base / name).resolve()
                if target != base and base not in target.parents:
                    td.cleanup()
                    raise ToolError('ZIP içinde güvensiz yol bulundu.')
            z.extractall(td.name)
        return Path(td.name), td
    raise ToolError('Girdi bir klasör veya ZIP olmalı.')


def _relative_garc_candidates(root: Path):
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        try:
            head = p.read_bytes()[:4]
        except OSError:
            continue
        if _magic_ok(head, b'GARC'):
            yield p, p.relative_to(root).as_posix()


def _archive_to_rows(data: bytes) -> tuple[GarcArchive, list[tuple[int, int, int, str]], list[dict]]:
    garc = GarcArchive(data)
    rows: list[tuple[int, int, int, str]] = []
    text_entries: list[dict] = []
    for ei, bit, inner in garc.flat_files():
        if not looks_like_text_file(inner):
            continue
        lines = decode_text_file(inner)
        for line_id, text in enumerate(lines):
            rows.append((ei, bit, line_id, text))
        text_entries.append({
            'entry': ei, 'bit': bit, 'line_count': len(lines),
            'original_inner_sha256': sha256(inner)
        })
    return garc, rows, text_entries


def _rows_to_map(rows: list[tuple[int, int, int, str]]) -> dict[tuple[int, int, int], str]:
    return {(e, b, line_id): text for e, b, line_id, text in rows}


def write_comparison_tsv(path: Path, language_rows: dict[str, list[tuple[int, int, int, str]]]) -> int:
    languages = list(language_rows)
    if 'Turkish' not in language_rows:
        raise ToolError('Karşılaştırma için Turkish sütunu bulunamadı.')
    maps = {lang: _rows_to_map(rows) for lang, rows in language_rows.items()}
    master_keys = [(e, b, line_id) for e, b, line_id, _ in language_rows['Turkish']]
    master_set = set(master_keys)
    for lang in languages:
        other = set(maps[lang])
        if other != master_set:
            missing = len(master_set - other)
            extra = len(other - master_set)
            raise ToolError(f'Dil satır yapısı uyuşmuyor: {lang} (eksik {missing}, fazla {extra}).')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['entry', 'bit', 'line_id', *languages])
        for key in master_keys:
            w.writerow([key[0], key[1], key[2], *(maps[lang][key] for lang in languages)])
    return len(master_keys)


def read_comparison_turkish(path: Path) -> dict[tuple[int, int], list[str]]:
    groups: dict[tuple[int, int], list[str]] = {}
    expected: dict[tuple[int, int], int] = {}
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f, delimiter='\t')
        required = {'entry', 'bit', 'line_id', 'Turkish'}
        if not r.fieldnames or not required.issubset(set(r.fieldnames)):
            raise ToolError(f'Karşılaştırma TSV başlığı hatalı: {path}')
        for row in r:
            try:
                entry = int(row['entry']); bit = int(row['bit']); line_id = int(row['line_id'])
            except Exception:
                raise ToolError(f'Geçersiz entry/bit/line_id: {path}')
            key = (entry, bit)
            exp = expected.get(key, 0)
            if line_id != exp:
                raise ToolError(f'{path}: entry {entry}/{bit} için line_id {exp} bekleniyordu, {line_id} geldi.')
            groups.setdefault(key, []).append(row.get('Turkish', '') or '')
            expected[key] = exp + 1
    return groups


def extract_project(input_path: Path, project_dir: Path, mode: str = 'turkish') -> dict:
    if mode not in {'turkish', 'all', 'compare'}:
        raise ToolError(f'Bilinmeyen çıkarma modu: {mode}')
    source_root, td = _discover_input(input_path)
    try:
        candidates = list(_relative_garc_candidates(source_root))
        by_rel = {rel: p for p, rel in candidates}
        if mode == 'turkish':
            selected = [(p, rel) for p, rel in candidates if rel in TURKISH_REL_PATHS]
            if not selected:
                selected = candidates
        elif mode == 'compare':
            missing = sorted(COMPARE_REL_PATHS - set(by_rel))
            if missing:
                raise ToolError('Karşılaştırmalı mod için eksik GARC dosyaları: ' + ', '.join(missing))
            selected = [(by_rel[rel], rel) for rel in sorted(COMPARE_REL_PATHS)]
        else:
            selected = candidates
        if not selected:
            raise ToolError('Girdi içinde GARC arşivi bulunamadı.')

        if project_dir.exists() and any(project_dir.iterdir()):
            raise ToolError(f'Proje klasörü boş değil: {project_dir}')
        project_dir.mkdir(parents=True, exist_ok=True)
        originals = project_dir / 'original'
        texts_root = project_dir / 'texts'
        originals.mkdir(exist_ok=True)
        texts_root.mkdir(exist_ok=True)

        manifest = {
            'tool': 'ORAS TR Text Tool', 'tool_version': TOOL_VERSION,
            'source_name': input_path.name, 'mode': mode,
            'build_targets': sorted(TURKISH_REL_PATHS) if mode == 'compare' else None,
            'comparison_sets': [], 'archives': []
        }
        row_cache: dict[str, list[tuple[int, int, int, str]]] = {}
        total_text_entries = 0
        total_lines = 0
        for p, rel in selected:
            data = p.read_bytes()
            garc, master_rows, text_entries = _archive_to_rows(data)
            safe_name = rel.replace('/', '_').replace('\\', '_')
            original_name = safe_name + '.garc'
            (originals / original_name).write_bytes(data)
            tsv_rel = f'texts/{safe_name}.tsv'
            archive_rec = {
                'relative_path': rel, 'original_file': f'original/{original_name}',
                'sha256': sha256(data), 'version': garc.version,
                'entry_count': len(garc.entries), 'file_count': garc.file_count,
                'text_tsv': tsv_rel, 'text_entries': text_entries,
                'writable': mode != 'compare' or rel in TURKISH_REL_PATHS,
            }
            write_master_tsv(project_dir / tsv_rel, master_rows)
            manifest['archives'].append(archive_rec)
            row_cache[rel] = master_rows
            total_text_entries += len(text_entries)
            total_lines += len(master_rows)

        comparison_lines = 0
        if mode == 'compare':
            comp_dir = project_dir / 'comparison'
            comp_dir.mkdir(exist_ok=True)
            for spec in LANGUAGE_SETS:
                language_rows = {lang: row_cache[rel] for lang, rel in spec['languages']}
                rel_file = f"comparison/{spec['file']}"
                line_count = write_comparison_tsv(project_dir / rel_file, language_rows)
                comparison_lines += line_count
                turkish_rel = next(rel for lang, rel in spec['languages'] if lang == 'Turkish')
                manifest['comparison_sets'].append({
                    'label': spec['label'], 'file': rel_file,
                    'turkish_relative_path': turkish_rel,
                    'languages': [{'name': lang, 'relative_path': rel} for lang, rel in spec['languages']],
                    'line_count': line_count,
                })

        (project_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        return {
            'archives': len(manifest['archives']), 'text_entries': total_text_entries,
            'lines': total_lines, 'comparison_lines': comparison_lines, 'mode': mode
        }
    finally:
        if td is not None:
            td.cleanup()


def _comparison_groups_for_manifest(project_dir: Path, manifest: dict) -> dict[str, dict[tuple[int, int], list[str]]]:
    result: dict[str, dict[tuple[int, int], list[str]]] = {}
    for spec in manifest.get('comparison_sets', []):
        p = project_dir / spec['file']
        if not p.exists():
            raise ToolError(f'Karşılaştırma TSV eksik: {p}')
        result[spec['turkish_relative_path']] = read_comparison_turkish(p)
    return result


def build_project(project_dir: Path, output_dir: Path, verify: bool = True) -> dict:
    manifest_path = project_dir / 'manifest.json'
    if not manifest_path.exists():
        raise ToolError('manifest.json bulunamadı.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    mode = manifest.get('mode', 'turkish' if manifest.get('turkish_only', True) else 'all')
    comparison_groups = _comparison_groups_for_manifest(project_dir, manifest) if mode == 'compare' else {}
    output_dir.mkdir(parents=True, exist_ok=True)
    rebuilt = 0
    changed_inner = 0
    output_hashes: dict[str, str] = {}
    targets = set(manifest.get('build_targets') or []) if mode == 'compare' else None

    for rec in manifest.get('archives', []):
        rel_str = rec['relative_path']
        if targets is not None and rel_str not in targets:
            continue
        original_path = project_dir / rec['original_file']
        if not original_path.exists():
            raise ToolError(f'Orijinal GARC kopyası eksik: {original_path}')
        original = original_path.read_bytes()
        if sha256(original) != rec.get('sha256'):
            raise ToolError(f'Orijinal GARC değişmiş: {original_path}')
        garc = GarcArchive(original)
        if mode == 'compare':
            groups = comparison_groups.get(rel_str)
            if groups is None:
                raise ToolError(f'{rel_str} için karşılaştırmalı Turkish verisi bulunamadı.')
            source_label = next((x['file'] for x in manifest.get('comparison_sets', []) if x['turkish_relative_path'] == rel_str), rel_str)
        else:
            tsv_path = project_dir / rec.get('text_tsv', '')
            if not tsv_path.exists():
                raise ToolError(f'TSV eksik: {tsv_path}')
            groups = read_master_tsv(tsv_path)
            source_label = str(tsv_path)

        original_lookup = {(e, b): d for e, b, d in garc.flat_files()}
        for tr in rec.get('text_entries', []):
            key = (tr['entry'], tr['bit'])
            if key not in groups:
                if tr['line_count'] == 0:
                    lines = []
                else:
                    raise ToolError(f'{source_label}: entry {key[0]}/{key[1]} eksik.')
            else:
                lines = groups[key]
            if len(lines) != tr['line_count']:
                raise ToolError(f'{source_label}: entry {key[0]}/{key[1]} satır sayısı değişmiş ({tr["line_count"]} olmalı).')
            old_inner = original_lookup.get(key)
            if old_inner is None:
                raise ToolError('Manifestteki GARC entry bulunamadı.')
            original_lines = decode_text_file(old_inner)
            if lines == original_lines:
                continue
            new_inner = build_text_file(lines)
            garc.replace(tr['entry'], tr['bit'], new_inner)
            changed_inner += 1
        rebuilt_data = garc.build()
        rel = Path(rel_str)
        out_path = output_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(rebuilt_data)
        output_hashes[rel_str] = sha256(rebuilt_data)
        if verify:
            check = GarcArchive(rebuilt_data)
            lookup = {(e, b): d for e, b, d in check.flat_files()}
            for tr in rec.get('text_entries', []):
                d = lookup[(tr['entry'], tr['bit'])]
                lines2 = decode_text_file(d)
                if len(lines2) != tr['line_count']:
                    raise ToolError(f'Doğrulama hatası: {rel_str} entry {tr["entry"]}')
        rebuilt += 1
    return {'archives': rebuilt, 'changed_inner': changed_inner, 'sha256': output_hashes, 'mode': mode}


def verify_project(project_dir: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix='oras_verify_') as td:
        return build_project(project_dir, Path(td), verify=True)


def create_gui() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as e:
        raise ToolError(f'Tkinter açılamadı: {e}')

    root = tk.Tk()
    root.title(f'ORAS TR Text Tool v{TOOL_VERSION}')
    root.geometry('760x500')
    root.minsize(680, 430)

    frm = ttk.Frame(root, padding=18); frm.pack(fill='both', expand=True)
    ttk.Label(frm, text='Pokémon Omega Ruby / Alpha Sapphire Türkçe Metin Aracı', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
    ttk.Label(frm, text='GARC + Gen 6 şifreli metin dosyalarını çıkarır, dilleri karşılaştırır ve Türkçe metni tekrar paketler.', wraplength=700).pack(anchor='w', pady=(5, 12))

    mode_var = tk.StringVar(value='compare')
    modes = ttk.Frame(frm); modes.pack(anchor='w', pady=(0, 10))
    ttk.Radiobutton(modes, text='Karşılaştırmalı 8 dil (önerilen)', variable=mode_var, value='compare').pack(side='left', padx=(0, 12))
    ttk.Radiobutton(modes, text='Sadece Türkçe', variable=mode_var, value='turkish').pack(side='left', padx=(0, 12))
    ttk.Radiobutton(modes, text='Tüm GARC dosyaları', variable=mode_var, value='all').pack(side='left')

    log = tk.Text(frm, height=13, wrap='word', state='disabled')
    log.pack(fill='both', expand=True, pady=(8, 10))
    def say(msg: str):
        log.configure(state='normal'); log.insert('end', msg + '\n'); log.see('end'); log.configure(state='disabled'); root.update_idletasks()

    btns = ttk.Frame(frm); btns.pack(fill='x')

    def do_extract():
        src = filedialog.askopenfilename(title='ZIP seç (veya İptal edip klasör seç)', filetypes=[('ZIP', '*.zip'), ('Tüm dosyalar', '*.*')])
        if not src:
            src = filedialog.askdirectory(title='7 ve 8 klasörlerini içeren klasörü seç')
        if not src: return
        dst = filedialog.askdirectory(title='Çeviri projesinin oluşturulacağı klasörü seç')
        if not dst: return
        project = Path(dst) / 'ORAS_TR_Project'
        try:
            say(f'Çıkarılıyor ({mode_var.get()}): {src}')
            st = extract_project(Path(src), project, mode=mode_var.get())
            extra = f', {st["comparison_lines"]} karşılaştırmalı satır' if st['comparison_lines'] else ''
            say(f'Tamam: {st["archives"]} GARC, {st["text_entries"]} metin dosyası, {st["lines"]} arşiv satırı{extra}.')
            if st['mode'] == 'compare':
                messagebox.showinfo('Tamam', f'Proje oluşturuldu:\n{project}\n\ncomparison klasöründeki TSV dosyalarında yalnızca Turkish sütununu düzenleyin.')
            else:
                messagebox.showinfo('Tamam', f'Proje oluşturuldu:\n{project}')
        except Exception as e:
            say(f'HATA: {e}'); messagebox.showerror('Hata', str(e))

    def do_build():
        proj = filedialog.askdirectory(title='manifest.json bulunan proje klasörünü seç')
        if not proj: return
        out_parent = filedialog.askdirectory(title='Yeniden oluşturulan dosyaların çıkacağı klasörü seç')
        if not out_parent: return
        out = Path(out_parent) / 'rebuilt'
        try:
            say(f'Paketleniyor: {proj}')
            st = build_project(Path(proj), out, verify=True)
            say(f'Tamam: {st["archives"]} GARC yeniden oluşturuldu; {st["changed_inner"]} iç metin dosyası değişti.')
            messagebox.showinfo('Tamam', f'Yeni dosyalar:\n{out}\n\nRomFS yol yapısı korunmuştur.')
        except Exception as e:
            say(f'HATA: {e}'); messagebox.showerror('Hata', str(e))

    def do_verify():
        proj = filedialog.askdirectory(title='Doğrulanacak proje klasörünü seç')
        if not proj: return
        try:
            say('Proje doğrulanıyor...')
            st = verify_project(Path(proj))
            say(f'Doğrulama başarılı: {st["archives"]} hedef arşiv.')
            messagebox.showinfo('Doğrulama', 'Proje yeniden paketlenip tekrar okunabildi. Yapısal doğrulama başarılı.')
        except Exception as e:
            say(f'HATA: {e}'); messagebox.showerror('Hata', str(e))

    ttk.Button(btns, text='1) Metinleri Çıkar', command=do_extract).pack(side='left', padx=(0, 8))
    ttk.Button(btns, text='2) Geri Enjekte / Paketle', command=do_build).pack(side='left', padx=(0, 8))
    ttk.Button(btns, text='Projeyi Doğrula', command=do_verify).pack(side='left')
    ttk.Label(frm, text='Karşılaştırmalı modda Japanese/French/Italian/German/Spanish/Korean sütunları yalnızca referanstır; enjeksiyonda sadece Turkish okunur.', wraplength=700).pack(anchor='w', pady=(12, 0))
    root.mainloop()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='ORAS Gen 6 GARC Türkçe metin çıkarma / karşılaştırma / geri enjekte aracı')
    ap.add_argument('--version', action='version', version=f'%(prog)s {TOOL_VERSION}')
    sub = ap.add_subparsers(dest='cmd')
    ex = sub.add_parser('extract', help='GARC metinlerini TSV projesine çıkar')
    ex.add_argument('input', type=Path, help='7/8 klasörlerini içeren klasör veya ZIP')
    ex.add_argument('project', type=Path, help='Çıkış proje klasörü')
    mode = ex.add_mutually_exclusive_group()
    mode.add_argument('--all', action='store_true', help='Tüm GARC arşivlerini ayrı TSV olarak çıkar')
    mode.add_argument('--compare', action='store_true', help='8 dili yan yana karşılaştırmalı TSV olarak çıkar')
    bu = sub.add_parser('build', help='TSV projesini yeniden GARC olarak paketle')
    bu.add_argument('project', type=Path)
    bu.add_argument('output', type=Path)
    ve = sub.add_parser('verify', help='Projeyi geçici olarak paketleyip doğrula')
    ve.add_argument('project', type=Path)
    sub.add_parser('gui', help='Grafik arayüzü aç')
    args = ap.parse_args(argv)
    try:
        if args.cmd in (None, 'gui'):
            create_gui(); return 0
        if args.cmd == 'extract':
            mode_name = 'compare' if args.compare else ('all' if args.all else 'turkish')
            st = extract_project(args.input, args.project, mode=mode_name)
            print(json.dumps(st, ensure_ascii=False)); return 0
        if args.cmd == 'build':
            st = build_project(args.project, args.output, verify=True)
            print(json.dumps(st, ensure_ascii=False)); return 0
        if args.cmd == 'verify':
            st = verify_project(args.project)
            print(json.dumps(st, ensure_ascii=False)); return 0
    except ToolError as e:
        print(f'HATA: {e}', file=sys.stderr); return 2
    except Exception as e:
        print(f'BEKLENMEYEN HATA: {e}', file=sys.stderr); return 3
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
