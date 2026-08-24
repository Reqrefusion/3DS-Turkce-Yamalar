#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DKCR3D RST0/LANG localization toolkit - V4 SAFE FONT
For Donkey Kong Country Returns 3D (Monster Games RST0 archives).

Commands:
  rst-extract ARCHIVE.res OUT_DIR
  rst-pack    EXTRACTED_DIR OUTPUT.res [--compression lz|literal|none]
  lang-export MSLANG.lng FONT.fnt OUTPUT.csv|json
  lang-import TEMPLATE.lng FONT.fnt INPUT.csv|json OUTPUT.lng
  font-check  FONT.fnt [--chars TEXT]
  make-workspace LANGUAGE.res OUT_DIR
  build       WORKSPACE TRANSLATION.csv|json OUTPUT.res [--compression lz|literal|none]

The LANG format stores glyph-table indices as UTF-8 code points rather than
Unicode characters directly. This tool converts transparently using the GTEX
font's glyph table (.fnt).
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

RST_HEADER_PAD = 0x80
RST_ENTRY_SIZE = 0x2C
RST_FILE_PAD = 0x1000
FONT_HEADER_SIZE = 0x28
FONT_RECORD_SIZE = 0x2C


def u32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from('<I', data, off)[0]


def p32(buf: bytearray, off: int, val: int) -> None:
    struct.pack_into('<I', buf, off, val & 0xFFFFFFFF)


def align(v: int, a: int) -> int:
    return (v + a - 1) & ~(a - 1)


def reversed_fourcc(raw: bytes) -> str:
    return raw[::-1].decode('ascii', 'replace')


# ----------------------------- RST0 compression -----------------------------

def _crc_table():
    out = []
    poly = 0x04C11DB7
    for i in range(256):
        c = i << 24
        for _ in range(8):
            if c & 0x80000000:
                c = ((c << 1) ^ poly) & 0xFFFFFFFF
            else:
                c = (c << 1) & 0xFFFFFFFF
        out.append(c)
    return out


_CRC_TABLE = _crc_table()


def rcmp_crc(data: bytes) -> int:
    """CRC used by the rCMP section (matches the documented Excite algorithm)."""
    if len(data) > 3:
        crc = (~int.from_bytes(data[:4], 'big')) & 0xFFFFFFFF
        pos = 4
    else:
        crc = _CRC_TABLE[128]
        pos = 0
    while pos < len(data):
        crc = (((crc << 8) & 0xFFFFFFFF) | data[pos]) ^ _CRC_TABLE[(crc >> 24) & 0xFF]
        pos += 1
    return (~crc) & 0xFFFFFFFF


def rcmp_decompress(section: bytes, expected_size: int | None = None) -> bytes:
    if section[:4] != b'PMCr':
        raise ValueError('rCMP magic bulunamadı')
    comp_data_size = u32(section, 0x08)
    decomp_size = u32(section, 0x0C)
    if expected_size is not None and decomp_size != expected_size:
        raise ValueError(f'Decompressed size uyuşmuyor: {decomp_size} != {expected_size}')
    if len(section) < 0x19 or section[0x10] != 0x4F:
        raise ValueError('rCMP ikinci başlığı geçersiz')
    if u32(section, 0x11) != comp_data_size or u32(section, 0x15) != decomp_size:
        raise ValueError('rCMP boyut alanları uyuşmuyor')
    crc_expected = u32(section, 0x04)
    crc_actual = rcmp_crc(section[0x10:0x10 + comp_data_size])
    if crc_actual != crc_expected:
        raise ValueError(f'rCMP CRC hatası: {crc_actual:08X} != {crc_expected:08X}')

    pos = 0x19
    out = bytearray()
    while len(out) < decomp_size:
        if pos + 4 > len(section):
            raise ValueError('rCMP kontrol kelimesi yarım kaldı')
        flags = u32(section, pos)
        pos += 4
        if not (flags & 0x80000000):
            raise ValueError(f'rCMP kontrol kelimesi geçersiz: 0x{flags:08X}')
        for bit in range(31):
            if len(out) >= decomp_size:
                break
            if not (flags & (1 << bit)):
                if pos >= len(section):
                    raise ValueError('rCMP literal veri yarım kaldı')
                out.append(section[pos])
                pos += 1
                continue

            if pos >= len(section):
                raise ValueError('rCMP backref yarım kaldı')
            b0 = section[pos]
            kind = b0 & 3
            if kind == 0:
                val = b0
                pos += 1
                dist = val >> 2
                count = 3
            elif kind == 1:
                val = int.from_bytes(section[pos:pos+2], 'little')
                pos += 2
                dist = val >> 2
                count = 3
            elif kind == 2:
                val = int.from_bytes(section[pos:pos+2], 'little')
                pos += 2
                dist = val >> 6
                count = ((val >> 2) & 0xF) + 3
            else:
                if b0 & 0x7C:
                    val = int.from_bytes(section[pos:pos+3], 'little')
                    pos += 3
                    dist = val >> 7
                    count = ((val >> 2) & 0x1F) + 2
                else:
                    val = int.from_bytes(section[pos:pos+4], 'little')
                    pos += 4
                    dist = val >> 15
                    count = ((val >> 7) & 0xFF) + 3
            if dist <= 0 or dist > len(out):
                raise ValueError(f'Geçersiz rCMP mesafesi: {dist}, çıktı={len(out)}')
            for _ in range(count):
                out.append(out[-dist])
                if len(out) >= decomp_size:
                    break
    return bytes(out)


def _encode_backref(dist: int, length: int) -> bytes | None:
    if dist <= 0 or dist > 0x1FFFF or length < 3:
        return None
    if length == 3:
        if dist <= 0x3F:
            return bytes([(dist << 2) | 0])
        if dist <= 0x3FFF:
            return ((dist << 2) | 1).to_bytes(2, 'little')
        # 24-bit form, B=1 -> length 3
        return ((dist << 7) | (1 << 2) | 3).to_bytes(3, 'little')
    if length <= 18 and dist <= 0x3FF:
        return ((dist << 6) | ((length - 3) << 2) | 2).to_bytes(2, 'little')
    if length <= 33:
        b = length - 2
        if 1 <= b <= 0x1F:
            return ((dist << 7) | (b << 2) | 3).to_bytes(3, 'little')
    if length <= 258:
        b = length - 3
        return ((dist << 15) | (b << 7) | 3).to_bytes(4, 'little')
    return None


def _max_encodable_len(dist: int) -> int:
    return 258 if dist <= 0x1FFFF else 0


def rcmp_compress(data: bytes, mode: str = 'lz') -> bytes:
    """Create a valid DKCR3D rCMP section.

    mode='literal' is simple and larger; mode='lz' uses a conservative greedy
    matcher compatible with the documented decoder.
    """
    tokens: list[tuple[bool, bytes]] = []

    if mode == 'literal':
        tokens = [(False, bytes([b])) for b in data]
    elif mode == 'lz':
        # Recent positions for 3-byte prefixes. Limiting candidates keeps this fast.
        recent: dict[bytes, deque[int]] = defaultdict(lambda: deque(maxlen=48))
        pos = 0
        n = len(data)
        while pos < n:
            best_len = 0
            best_dist = 0
            if pos + 3 <= n:
                key = data[pos:pos+3]
                dq = recent.get(key)
                if dq:
                    for prev in reversed(dq):
                        dist = pos - prev
                        if dist > 0x1FFFF:
                            break
                        lim = min(258, n - pos)
                        # Direct comparison against original data correctly handles
                        # overlap because the target output is the same byte stream.
                        ln = 3
                        while ln < lim and data[prev + (ln % dist)] == data[pos + ln]:
                            ln += 1
                        enc = _encode_backref(dist, ln)
                        if enc is not None and ln > best_len:
                            best_len, best_dist = ln, dist
                            if ln == lim:
                                break
            if best_len >= 3:
                enc = _encode_backref(best_dist, best_len)
                if enc is None:
                    best_len = 0
                else:
                    tokens.append((True, enc))
                    end = pos + best_len
                    for q in range(pos, end):
                        if q + 3 <= n:
                            recent[data[q:q+3]].append(q)
                    pos = end
                    continue

            tokens.append((False, bytes([data[pos]])))
            if pos + 3 <= n:
                recent[data[pos:pos+3]].append(pos)
            pos += 1
    else:
        raise ValueError('compression mode lz veya literal olmalı')

    stream = bytearray()
    for start in range(0, len(tokens), 31):
        group = tokens[start:start+31]
        flags = 0x80000000
        payload = bytearray()
        for bit, (is_ref, blob) in enumerate(group):
            if is_ref:
                flags |= 1 << bit
            payload += blob
        stream += struct.pack('<I', flags)
        stream += payload

    comp_data_size = 9 + len(stream)
    second = bytearray()
    second.append(0x4F)
    second += struct.pack('<II', comp_data_size, len(data))
    second += stream
    crc = rcmp_crc(second)
    return b'PMCr' + struct.pack('<III', crc, comp_data_size, len(data)) + bytes(second)


# ---------------------------------- RST0 -----------------------------------

def read_rst(path: Path):
    raw = path.read_bytes()
    if len(raw) < 0x80 or raw[:4] != b'0TSR' or raw[4] != 0x44:
        raise ValueError('Bu dosya DKCR3D RST0 arşivi gibi görünmüyor')
    comp_type = u32(raw, 0x0C)
    logical_size = u32(raw, 0x10)
    toc_off = u32(raw, 0x18)
    count = u32(raw, 0x20)
    decomp_size = u32(raw, 0x24)
    comp_size = u32(raw, 0x28)
    if toc_off != 0x80:
        raise ValueError(f'Beklenmeyen ToC offseti: 0x{toc_off:X}')
    if comp_type == 0:
        section = raw[toc_off:toc_off + decomp_size]
    elif comp_type == 2:
        section = rcmp_decompress(raw[toc_off:toc_off + comp_size], decomp_size)
    else:
        raise ValueError(f'Desteklenmeyen RST0 sıkıştırma tipi: {comp_type}')

    str_size = u32(raw, 0x34)
    id_size = u32(raw, 0x38)
    defs_size = count * RST_ENTRY_SIZE
    str_base = defs_size
    id_base = str_base + str_size
    if id_base + id_size > len(section):
        raise ValueError('RST0 ToC boyutları geçersiz')

    resources = []
    for i in range(count):
        off = i * RST_ENTRY_SIZE
        ent = section[off:off+RST_ENTRY_SIZE]
        name_off = u32(ent, 0)
        end = section.find(b'\0', str_base + name_off, str_base + str_size)
        if end < 0:
            raise ValueError(f'Kaynak adı sonlandırılmamış: {i}')
        name = section[str_base + name_off:end].decode('ascii', 'replace')
        size = u32(ent, 0x0C)
        res_off = u32(ent, 0x10)
        if res_off + size > len(section):
            raise ValueError(f'Kaynak arşiv dışına taşıyor: {name}')
        resources.append({
            'index': i,
            'name': name,
            'type': reversed_fourcc(ent[4:8]).rstrip(),
            'entry_hex': ent.hex(),
            'size': size,
            'offset': res_off,
            'data': section[res_off:res_off+size],
        })
    return raw, section, resources


def safe_resource_path(root: Path, name: str) -> Path:
    # RST names are normally flat, but prevent path traversal while retaining folders.
    parts = [p for p in Path(name.replace('\\', '/')).parts if p not in ('', '.', '..', '/')]
    if not parts:
        raise ValueError(f'Geçersiz kaynak adı: {name!r}')
    return root.joinpath(*parts)


def rst_extract(archive: Path, out_dir: Path, quiet: bool = False) -> None:
    raw, section, resources = read_rst(archive)
    out_dir.mkdir(parents=True, exist_ok=True)
    res_root = out_dir / 'resources'
    res_root.mkdir(exist_ok=True)

    count = u32(raw, 0x20)
    str_size = u32(raw, 0x34)
    id_size = u32(raw, 0x38)
    defs_size = count * RST_ENTRY_SIZE
    string_table = section[defs_size:defs_size+str_size]
    id_table = section[defs_size+str_size:defs_size+str_size+id_size]

    manifest = {
        'format': 'DKCR3D_RST0_manifest_v1',
        'source_name': archive.name,
        'header_0x80_b64': base64.b64encode(raw[:0x80]).decode('ascii'),
        'string_table_b64': base64.b64encode(string_table).decode('ascii'),
        'id_table_b64': base64.b64encode(id_table).decode('ascii'),
        'original_compression_type': u32(raw, 0x0C),
        'resources': [
            {k: r[k] for k in ('index', 'name', 'type', 'entry_hex', 'size', 'offset')}
            for r in resources
        ],
    }
    (out_dir / '_rst_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    for r in resources:
        p = safe_resource_path(res_root, r['name'])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r['data'])
        if not quiet:
            print(f"[{r['index']:03}] {r['type']:<5} {r['name']} ({r['size']} bayt)")
    if not quiet:
        print(f'Çıkarıldı: {len(resources)} kaynak -> {out_dir}')


def _build_rst_section(work_dir: Path, manifest: dict) -> bytes:
    resources = manifest['resources']
    count = len(resources)
    string_table = base64.b64decode(manifest['string_table_b64'])
    id_table = base64.b64decode(manifest['id_table_b64'])
    defs = bytearray(count * RST_ENTRY_SIZE)
    for r in resources:
        i = int(r['index'])
        ent = bytes.fromhex(r['entry_hex'])
        if len(ent) != RST_ENTRY_SIZE:
            raise ValueError(f"Manifest entry boyutu hatalı: {r['name']}")
        defs[i*RST_ENTRY_SIZE:(i+1)*RST_ENTRY_SIZE] = ent

    toc = bytearray(defs + string_table + id_table)
    data_start = align(len(toc), 0x80)
    toc += b'\0' * (data_start - len(toc))

    cursor = data_start
    chunks: list[tuple[int, bytes, dict]] = []
    for r in resources:
        p = safe_resource_path(work_dir / 'resources', r['name'])
        if not p.exists():
            raise FileNotFoundError(f"Kaynak eksik: {p}")
        blob = p.read_bytes()
        # Monster Games' original RST0 writer places every resource after the
        # first at the NEXT 0x80 boundary; if the prior resource ends exactly
        # on a boundary it still leaves a full 0x80-byte gap.
        if chunks:
            cursor = align(cursor + 1, 0x80)
        else:
            cursor = data_start
        chunks.append((cursor, blob, r))
        i = int(r['index'])
        p32(toc, i*RST_ENTRY_SIZE + 0x0C, len(blob))
        p32(toc, i*RST_ENTRY_SIZE + 0x10, cursor)
        # 0x14 is the per-resource content CRC used by DKCR3D.
        # Official EN/FR/DE/IT/ES archives confirm it is the same custom
        # CRC routine used by rCMP. It MUST be refreshed when a resource changes.
        p32(toc, i*RST_ENTRY_SIZE + 0x14, rcmp_crc(blob))
        cursor += len(blob)

    section = bytearray(toc)
    for off, blob, _ in chunks:
        if len(section) < off:
            section += b'\0' * (off - len(section))
        if len(section) != off:
            raise ValueError('İç kaynak offset çakışması')
        section += blob
    return bytes(section)


def rst_pack(work_dir: Path, output: Path, compression: str = 'lz', quiet: bool = False) -> None:
    manifest_path = work_dir / '_rst_manifest.json'
    if not manifest_path.exists():
        raise FileNotFoundError(f'Manifest bulunamadı: {manifest_path}')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('format') != 'DKCR3D_RST0_manifest_v1':
        raise ValueError('Manifest sürümü desteklenmiyor')

    header = bytearray(base64.b64decode(manifest['header_0x80_b64']))
    if len(header) != 0x80:
        raise ValueError('Manifest RST başlığı 0x80 bayt değil')
    section = _build_rst_section(work_dir, manifest)

    p32(header, 0x1C, len(manifest['resources']))
    p32(header, 0x20, len(manifest['resources']))
    p32(header, 0x24, len(section))

    # Header 0x3C is the custom CRC of the resource-definition array.
    # This covers sizes, offsets and each resource's content CRC at +0x14.
    defs_size = len(manifest['resources']) * RST_ENTRY_SIZE
    p32(header, 0x3C, rcmp_crc(section[:defs_size]))

    if compression == 'none':
        p32(header, 0x0C, 0)
        p32(header, 0x28, len(section))
        payload = section
    else:
        mode = 'literal' if compression == 'literal' else 'lz'
        payload = rcmp_compress(section, mode=mode)
        p32(header, 0x0C, 2)
        p32(header, 0x28, len(payload))

    # File size is the logical archive size (without final 0x1000 padding).
    p32(header, 0x10, 0x80 + len(payload))

    # Header 0x40 is the custom CRC of bytes 0x00..0x3F. Official archives
    # confirm this must be recomputed after all preceding header fields.
    p32(header, 0x40, rcmp_crc(bytes(header[:0x40])))

    logical = bytes(header) + payload
    padded = logical + b'\0' * (align(len(logical), RST_FILE_PAD) - len(logical))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(padded)

    # Strong self-check: decompress and compare each resource with workspace.
    _, _, packed_resources = read_rst(output)
    for r in packed_resources:
        expected = safe_resource_path(work_dir / 'resources', r['name']).read_bytes()
        if r['data'] != expected:
            raise RuntimeError(f"Paketleme doğrulaması başarısız: {r['name']}")
    if not quiet:
        print(f'Paketlendi: {output}')
        print(f'  RST veri: {len(section):,} bayt')
        print(f'  Dosya:    {len(padded):,} bayt ({compression})')
        print('  Doğrulama: OK')


# ---------------------------------- FONT -----------------------------------

def load_font_map(font_path: Path):
    data = font_path.read_bytes()
    if len(data) < FONT_HEADER_SIZE:
        raise ValueError('FNT dosyası çok küçük')
    count = u32(data, 0x20)
    if count <= 0:
        raise ValueError('FNT glif sayısı geçersiz')
    remaining = len(data) - FONT_HEADER_SIZE
    if remaining % count != 0:
        raise ValueError('FNT kayıt boyutu hesaplanamadı')
    stride = remaining // count
    if stride < 4:
        raise ValueError('FNT kayıt boyutu geçersiz')
    idx_to_cp: dict[int, int] = {}
    cp_to_idx: dict[int, int] = {}
    records = []
    for i in range(count):
        off = FONT_HEADER_SIZE + i * stride
        cp = u32(data, off)
        idx_to_cp[i] = cp
        cp_to_idx.setdefault(cp, i)
        rec = {'glyph_index': i, 'codepoint': cp, 'char': chr(cp) if cp <= 0x10FFFF else ''}
        if stride >= 44:
            vals = struct.unpack_from('<I10f', data, off)
            rec['metrics'] = list(vals[1:])
        records.append(rec)
    return {
        'count': count,
        'stride': stride,
        'idx_to_cp': idx_to_cp,
        'cp_to_idx': cp_to_idx,
        'records': records,
    }


# V4 SAFE FONT: Turkish accented letters are composed at render time from
# the game's original thick base glyph + an existing accent glyph. No TEX is edited.
_TR_DECOMPOSE = {
    'Ğ': 'G˘', 'ğ': 'g˘',
    'İ': 'I˙',
    'Ş': 'S¸', 'ş': 's¸',
}
_TR_RECOMPOSE = {v: k for k, v in _TR_DECOMPOSE.items()}

def game_bytes_to_unicode(blob: bytes, fmap: dict) -> str:
    indexed = blob.decode('utf-8')
    out = []
    for ch in indexed:
        idx = ord(ch)
        cp = fmap['idx_to_cp'].get(idx)
        if cp is None or cp > 0x10FFFF:
            raise ValueError(f'Fontta glif indeksi yok: {idx}')
        out.append(chr(cp))
    text = ''.join(out)
    # Longest-first is future-proof if more composite sequences are added.
    for seq, tr in sorted(_TR_RECOMPOSE.items(), key=lambda kv: len(kv[0]), reverse=True):
        text = text.replace(seq, tr)
    return text


def unicode_to_game_bytes(text: str, fmap: dict) -> bytes:
    expanded = ''.join(_TR_DECOMPOSE.get(ch, ch) for ch in text)
    out = []
    missing = []
    for ch in expanded:
        cp = ord(ch)
        idx = fmap['cp_to_idx'].get(cp)
        if idx is None:
            missing.append(ch)
            continue
        out.append(chr(idx))
    if missing:
        unique = ''.join(dict.fromkeys(missing))
        desc = ', '.join(f'{c} (U+{ord(c):04X})' for c in unique)
        raise ValueError(f'Fontta bulunmayan karakter(ler): {desc}')
    return ''.join(out).encode('utf-8')


def font_check(font_path: Path, chars: str) -> bool:
    fm = load_font_map(font_path)
    print(f'Font: {font_path}')
    print(f"Glif sayısı: {fm['count']} | kayıt boyutu: {fm['stride']} bayt")
    print('Karakter | Unicode | Glif index | Oyundaki UTF-8 | Durum')
    print('-' * 64)
    ok = True
    for ch in chars:
        cp = ord(ch)
        idx = fm['cp_to_idx'].get(cp)
        if idx is None:
            ok = False
            print(f'{ch!s:^8} | U+{cp:04X} | {"-":^10} | {"-":^14} | YOK')
        else:
            enc = chr(idx).encode('utf-8').hex(' ').upper()
            print(f'{ch!s:^8} | U+{cp:04X} | {idx:^10} | {enc:^14} | OK')
    return ok


# ---------------------------------- LANG -----------------------------------

def parse_lang(path: Path):
    data = path.read_bytes()
    if len(data) < 4:
        raise ValueError('LANG dosyası çok küçük')
    count = u32(data, 0)
    table_end = 4 + count * 12
    if table_end > len(data):
        raise ValueError('LANG tablo boyutu geçersiz')

    records = []
    pos = table_end
    value_offset_to_record = {}
    for i in range(count):
        key_end = data.find(b'\0', pos)
        if key_end < 0:
            raise ValueError(f'LANG key sonlandırılmamış: {i}')
        key_start = pos
        key = data[pos:key_end].decode('ascii', 'strict')
        pos = key_end + 1
        value_start = pos
        val_end = data.find(b'\0', pos)
        if val_end < 0:
            raise ValueError(f'LANG value sonlandırılmamış: {i}')
        value = data[pos:val_end]
        pos = val_end + 1
        records.append({
            'index': i,
            'key': key,
            'key_start': key_start,
            'value_start': value_start,
            'raw_value': value,
        })
        value_offset_to_record[value_start] = i
    if pos != len(data):
        raise ValueError(f'LANG sonunda beklenmeyen {len(data)-pos} bayt var')

    table = []
    for i in range(count):
        a, b, voff = struct.unpack_from('<III', data, 4+i*12)
        rec_idx = value_offset_to_record.get(voff)
        if rec_idx is None:
            raise ValueError(f'LANG tablo offseti bir değere işaret etmiyor: 0x{voff:X}')
        table.append({'a': a, 'b': b, 'record_index': rec_idx})
    return data, records, table


def export_rows(lang_path: Path, font_path: Path):
    _, records, _ = parse_lang(lang_path)
    fm = load_font_map(font_path)
    rows = []
    for r in records:
        raw = r['raw_value']
        prefix = b''
        body = raw
        if raw.startswith(b'\x01'):
            prefix, body = b'\x01', raw[1:]
        text = game_bytes_to_unicode(body, fm)
        rows.append({
            'index': r['index'],
            'key': r['key'],
            'text': text,
            'prefix_hex': prefix.hex(),
        })
    return rows


def lang_export(lang_path: Path, font_path: Path, output: Path) -> None:
    rows = export_rows(lang_path, font_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == '.json':
        output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        # UTF-8 BOM makes Turkish characters open cleanly in Excel on Windows.
        with output.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['index', 'key', 'text', 'prefix_hex'])
            w.writeheader()
            w.writerows(rows)
    print(f'{len(rows)} metin dışa aktarıldı -> {output}')


def _load_translation_rows(path: Path):
    if path.suffix.lower() == '.json':
        rows = json.loads(path.read_text(encoding='utf-8-sig'))
    else:
        with path.open('r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
    if not isinstance(rows, list):
        raise ValueError('Çeviri dosyası liste/tablo olmalı')
    return rows


def lang_import(template_lang: Path, font_path: Path, translation: Path, output: Path) -> None:
    _, records, table = parse_lang(template_lang)
    fm = load_font_map(font_path)
    rows = _load_translation_rows(translation)
    by_key = {str(r.get('key', '')): r for r in rows}
    if len(by_key) != len(rows):
        raise ValueError('Çeviri dosyasında yinelenen key var')

    rebuilt_values: list[bytes] = []
    for rec in records:
        key = rec['key']
        row = by_key.get(key)
        if row is None:
            raise ValueError(f'Çeviri satırı eksik: {key}')
        text = str(row.get('text', ''))
        prefix_hex = str(row.get('prefix_hex', '01') or '')
        try:
            prefix = bytes.fromhex(prefix_hex)
        except ValueError as e:
            raise ValueError(f'{key}: prefix_hex geçersiz') from e
        try:
            body = unicode_to_game_bytes(text, fm)
        except ValueError as e:
            raise ValueError(f'{key}: {e}') from e
        rebuilt_values.append(prefix + body)

    count = len(records)
    out = bytearray(b'\0' * (4 + count * 12))
    p32(out, 0, count)
    value_offsets = [0] * count
    for i, rec in enumerate(records):
        keyb = rec['key'].encode('ascii')
        out += keyb + b'\0'
        value_offsets[i] = len(out)
        out += rebuilt_values[i] + b'\0'

    for i, ent in enumerate(table):
        voff = value_offsets[ent['record_index']]
        struct.pack_into('<III', out, 4+i*12, ent['a'], ent['b'], voff)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(out)
    # Parse the result again as a structural self-check.
    parse_lang(output)
    print(f'{count} metin geri yazıldı -> {output}')


# ------------------------------- workflows ---------------------------------

def make_workspace(res_path: Path, out_dir: Path) -> None:
    rst_extract(res_path, out_dir, quiet=True)
    mslang = out_dir / 'resources' / 'mslang.lng'
    fnt = out_dir / 'resources' / 'uifnt_o.fnt'
    if not mslang.exists() or not fnt.exists():
        raise FileNotFoundError('Bu arşivde mslang.lng ve uifnt_o.fnt birlikte bulunamadı')
    csv_path = out_dir / 'translation.csv'
    lang_export(mslang, fnt, csv_path)
    print(f'Çalışma alanı hazır: {out_dir}')
    print(f'Çevrilecek dosya: {csv_path}')


def build_workspace(work_dir: Path, translation: Path, output_res: Path, compression: str) -> None:
    mslang = work_dir / 'resources' / 'mslang.lng'
    fnt = work_dir / 'resources' / 'uifnt_o.fnt'
    if not mslang.exists() or not fnt.exists():
        raise FileNotFoundError('Çalışma alanında mslang.lng/uifnt_o.fnt yok')
    original = work_dir / 'resources' / '_mslang_original.lng'
    # Keep a stable template on first build, so repeated builds do not accumulate changes.
    if not original.exists():
        original.write_bytes(mslang.read_bytes())
    lang_import(original, fnt, translation, mslang)
    rst_pack(work_dir, output_res, compression=compression)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='DKCR3D RST0/LANG Türkçeleştirme araçları')
    sp = ap.add_subparsers(dest='cmd', required=True)

    p = sp.add_parser('rst-extract', help='RST0 .res arşivini çıkar')
    p.add_argument('archive', type=Path)
    p.add_argument('out_dir', type=Path)

    p = sp.add_parser('rst-pack', help='Çıkarılmış RST0 klasörünü paketle')
    p.add_argument('work_dir', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--compression', choices=['lz', 'literal', 'none'], default='lz')

    p = sp.add_parser('lang-export', help='mslang.lng -> Unicode CSV/JSON')
    p.add_argument('lang', type=Path)
    p.add_argument('font', type=Path)
    p.add_argument('output', type=Path)

    p = sp.add_parser('lang-import', help='Unicode CSV/JSON -> mslang.lng')
    p.add_argument('template_lang', type=Path)
    p.add_argument('font', type=Path)
    p.add_argument('translation', type=Path)
    p.add_argument('output', type=Path)

    p = sp.add_parser('font-check', help='Fontta karakter var mı kontrol et')
    p.add_argument('font', type=Path)
    p.add_argument('--chars', default='ÇĞİÖŞÜçğışöü')

    p = sp.add_parser('make-workspace', help='Dil .res dosyasından çeviri çalışma alanı hazırla')
    p.add_argument('language_res', type=Path)
    p.add_argument('out_dir', type=Path)

    p = sp.add_parser('build', help='translation.csv/json ile yeni dil .res üret')
    p.add_argument('work_dir', type=Path)
    p.add_argument('translation', type=Path)
    p.add_argument('output_res', type=Path)
    p.add_argument('--compression', choices=['lz', 'literal', 'none'], default='lz')

    args = ap.parse_args(argv)
    try:
        if args.cmd == 'rst-extract':
            rst_extract(args.archive, args.out_dir)
        elif args.cmd == 'rst-pack':
            rst_pack(args.work_dir, args.output, args.compression)
        elif args.cmd == 'lang-export':
            lang_export(args.lang, args.font, args.output)
        elif args.cmd == 'lang-import':
            lang_import(args.template_lang, args.font, args.translation, args.output)
        elif args.cmd == 'font-check':
            return 0 if font_check(args.font, args.chars) else 2
        elif args.cmd == 'make-workspace':
            make_workspace(args.language_res, args.out_dir)
        elif args.cmd == 'build':
            build_workspace(args.work_dir, args.translation, args.output_res, args.compression)
        return 0
    except Exception as e:
        print(f'HATA: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
