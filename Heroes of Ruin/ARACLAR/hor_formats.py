from __future__ import annotations

import csv
import json
import re
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# ---------------- BLZ / backwards-LZ ----------------

def _u32(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from('<I', data, off)[0]


def blz_decompress(data: bytes) -> bytes:
    """Decompress the BLZ/backwards-LZ variant used by Heroes of Ruin.

    Also accepts the standard 'stored' form: raw bytes + four zero bytes.
    """
    if len(data) < 4:
        return data
    if data[-4:] == b'\0\0\0\0':
        return data[:-4]
    if len(data) < 8:
        raise ValueError('BLZ file is too short')

    comp_header, extra = struct.unpack_from('<II', data, len(data) - 8)
    header_len = comp_header >> 24
    comp_len = comp_header & 0x00FFFFFF
    if extra == 0:
        return data[:-4] if data[-4:] == b'\0\0\0\0' else data
    if not (8 <= header_len <= len(data)):
        raise ValueError(f'Invalid BLZ header length: {header_len}')
    if not (header_len <= comp_len <= len(data)):
        raise ValueError(f'Invalid BLZ compressed length: {comp_len}')

    passthrough = len(data) - comp_len
    src = len(data) - header_len
    out_len = len(data) + extra
    out = bytearray(out_len)
    out[:len(data)] = data
    dst = out_len

    # Read from the same output buffer: this mirrors the in-place decoder.
    while src > passthrough and dst > passthrough:
        src -= 1
        flags = out[src]
        for bit in range(8):
            if src <= passthrough or dst <= passthrough:
                break
            if flags & (0x80 >> bit):
                if src - 2 < passthrough:
                    raise ValueError('Truncated BLZ match token')
                src -= 1
                a = out[src]
                src -= 1
                b = out[src]
                length = (a >> 4) + 3
                distance = (((a & 0x0F) << 8) | b) + 3
                for _ in range(length):
                    if dst <= passthrough:
                        break
                    dst -= 1
                    ref = dst + distance
                    if ref >= len(out):
                        raise ValueError('Invalid BLZ back-reference')
                    out[dst] = out[ref]
            else:
                src -= 1
                dst -= 1
                out[dst] = out[src]

    if dst != passthrough:
        raise ValueError(f'BLZ decode ended early (dst={dst:#x}, prefix={passthrough:#x})')
    return bytes(out)


def _blz_compress_stream(data: bytes) -> bytes:
    """Compress one BLZ region. Output excludes footer and is reversed for BLZ."""
    rev = data[::-1]
    out = bytearray()
    # One recent position per 3-byte key. Fast and deterministic; not optimal,
    # but comfortably compresses HoR STRL/DARC assets.
    last: dict[int, int] = {}
    pos = 0

    while pos < len(rev):
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if pos >= len(rev):
                break

            best_len = 0
            best_dist = 0
            if pos + 2 < len(rev):
                key = (rev[pos] << 16) | (rev[pos + 1] << 8) | rev[pos + 2]
                match_pos = last.get(key, -1)
                if match_pos >= 0:
                    dist = pos - match_pos
                    if 3 <= dist <= 0x1002:
                        length = 3
                        max_len = min(18, len(rev) - pos)
                        while length < max_len and rev[match_pos + length] == rev[pos + length]:
                            length += 1
                        best_len = length
                        best_dist = dist

            if best_len >= 3:
                flags |= 0x80 >> bit
                stored = best_dist - 3
                out.append(((best_len - 3) << 4) | ((stored >> 8) & 0x0F))
                out.append(stored & 0xFF)
                consumed = best_len
            else:
                out.append(rev[pos])
                consumed = 1

            for p in range(pos, pos + consumed):
                if p + 2 < len(rev):
                    key = (rev[p] << 16) | (rev[p + 1] << 8) | rev[p + 2]
                    last[key] = p
            pos += consumed

        out[flag_pos] = flags

    return bytes(out)[::-1]


def _blz_pack_with_prefix(data: bytes, prefix_len: int) -> bytes | None:
    compressed = _blz_compress_stream(data[prefix_len:])
    # Whole file is 4-byte aligned. Footer/header length includes alignment bytes.
    pad_len = (-(prefix_len + len(compressed) + 8)) % 4
    header_len = 8 + pad_len
    comp_len = len(compressed) + header_len
    final_len = prefix_len + comp_len
    extra = len(data) - final_len
    if extra <= 0 or comp_len > 0x00FFFFFF or header_len > 0xFF:
        return None
    footer0 = (header_len << 24) | comp_len
    return data[:prefix_len] + compressed + (b'\xFF' * pad_len) + struct.pack('<II', footer0, extra)


def blz_compress(data: bytes) -> bytes:
    """Compress with an automatically chosen raw prefix and verify in-place safety."""
    if not data:
        return b'\0\0\0\0'

    # A raw prefix is sometimes required so backwards decompression never destroys
    # compressed bytes that have not yet been read. Try increasingly conservative
    # prefixes and verify using our same-buffer decoder.
    n = len(data)
    candidates = [0]
    for div in (32, 16, 12, 8, 6, 4, 3, 2):
        p = n // div
        if p not in candidates:
            candidates.append(p)
    candidates = sorted(set(candidates))

    best: bytes | None = None
    for prefix in candidates:
        packed = _blz_pack_with_prefix(data, prefix)
        if packed is None:
            continue
        try:
            if blz_decompress(packed) == data:
                best = packed
                break
        except ValueError:
            pass

    if best is None:
        # Standard BLZ stored form. The game loader recognizes zero extra size.
        return data + b'\0\0\0\0'
    return best


# ---------------- STRL ----------------

STRL_MAGIC = 0x0000FEFF
STRL_VERSION = 0x21

_TOKEN_RE = re.compile(
    r'(#[^#\r\n]+#|\{\{0x[0-9A-Fa-f]+\}\}|\$[A-Za-z0-9_]+\$?|%%[^%\r\n]+%%|%Name_[A-Za-z0-9_]+%|%(?:l?s|u[a-z]?))'
)


def protected_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


@dataclass
class StrlEntry:
    index: int
    ident: int
    text: str


def parse_strl_raw(raw: bytes) -> list[StrlEntry]:
    if len(raw) < 0x14:
        raise ValueError('STRL is too short')
    magic, version, count, header_size, pool_off = struct.unpack_from('<IIIII', raw, 0)
    if magic != STRL_MAGIC:
        raise ValueError(f'Not an HoR STRL (magic={magic:#x})')
    if version != STRL_VERSION:
        raise ValueError(f'Unexpected STRL version {version:#x}')
    if header_size != 0x14:
        raise ValueError(f'Unexpected STRL header size {header_size:#x}')
    expected_pool = 0x14 + count * 12
    if pool_off != expected_pool:
        raise ValueError(f'Unexpected STRL string pool offset {pool_off:#x}; expected {expected_pool:#x}')
    if pool_off > len(raw):
        raise ValueError('STRL pool lies outside file')

    entries: list[StrlEntry] = []
    for i in range(count):
        off = 0x14 + i * 12
        ident, byte_len, rel = struct.unpack_from('<III', raw, off)
        start = pool_off + rel
        end = start + byte_len
        if start < pool_off or end > len(raw) or byte_len < 2 or byte_len % 2:
            raise ValueError(f'Invalid STRL entry {i}')
        blob = raw[start:end]
        if blob[-2:] != b'\0\0':
            raise ValueError(f'STRL entry {i} has no UTF-16 NUL terminator')
        text = blob[:-2].decode('utf-16le')
        entries.append(StrlEntry(i, ident, text))
    return entries


def parse_strl_file(path: Path) -> list[StrlEntry]:
    return parse_strl_raw(blz_decompress(path.read_bytes()))


def build_strl_raw(records: Iterable[tuple[int, str]]) -> bytes:
    records = list(records)
    count = len(records)
    pool_off = 0x14 + count * 12
    table = bytearray()
    pool = bytearray()
    offsets: dict[bytes, int] = {}

    for ident, text in records:
        encoded = text.encode('utf-16le') + b'\0\0'
        rel = offsets.get(encoded)
        if rel is None:
            rel = len(pool)
            offsets[encoded] = rel
            pool.extend(encoded)
        table.extend(struct.pack('<III', ident & 0xFFFFFFFF, len(encoded), rel))

    hdr = struct.pack('<IIIII', STRL_MAGIC, STRL_VERSION, count, 0x14, pool_off)
    return hdr + bytes(table) + bytes(pool)


def _entries_to_payload(src_name: str, entries: list[StrlEntry]) -> dict:
    return {
        'format': 'Heroes of Ruin STRL 0x21',
        'source_file': src_name,
        'encoding': 'UTF-16LE',
        'notes': 'Edit only the text field. Keep protected control/variable tokens unchanged.',
        'entries': [
            {
                'index': e.index,
                'id': f'0x{e.ident:08X}',
                'source': e.text,
                'text': e.text,
            }
            for e in entries
        ],
    }


def export_strl(input_path: Path, output_path: Path) -> None:
    entries = parse_strl_file(input_path)
    payload = _entries_to_payload(input_path.name, entries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == '.csv':
        with output_path.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['index', 'id', 'source', 'text'])
            w.writeheader()
            for row in payload['entries']:
                w.writerow(row)
    else:
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _load_translation(path: Path) -> list[dict]:
    if path.suffix.lower() == '.csv':
        with path.open('r', encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    obj = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(obj, list):
        return obj
    return obj['entries']


def import_strl(translation_path: Path, output_path: Path, allow_token_change: bool = False) -> list[str]:
    rows = _load_translation(translation_path)
    records: list[tuple[int, str]] = []
    warnings: list[str] = []
    for idx, row in enumerate(rows):
        ident_s = str(row['id']).strip()
        ident = int(ident_s, 0)
        # Ordinary extracts use source/text. Multi-language comparison files
        # use en/fr/de/it/es/tr; in that format English is the validation
        # source and the Turkish column is the string to inject.
        source = str(row.get('source', row.get('en', '')))
        if 'text' in row:
            text = str(row.get('text', source))
        elif 'tr' in row:
            value = row.get('tr', '')
            text = source if value is None or str(value) == '' else str(value)
        else:
            text = source
        if not allow_token_change:
            a = Counter(protected_tokens(source))
            b = Counter(protected_tokens(text))
            if a != b:
                missing = list((a - b).elements())
                added = list((b - a).elements())
                raise ValueError(
                    f'Protected token mismatch at row {idx} / {ident_s}: '
                    f'missing={missing}, added={added}'
                )
        records.append((ident, text))

    raw = build_strl_raw(records)
    packed = blz_compress(raw)
    # Final round-trip guard.
    if blz_decompress(packed) != raw:
        raise RuntimeError('Internal BLZ round-trip check failed')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(packed)
    return warnings


# ---------------- DARC ----------------

@dataclass
class DarcNode:
    index: int
    name: str
    is_dir: bool
    field1: int
    field2: int
    node_offset: int
    path: str = ''


@dataclass
class DarcArchive:
    raw: bytes
    nodes: list[DarcNode]
    data_offset: int
    file_length: int


def parse_darc(raw: bytes) -> DarcArchive:
    if len(raw) < 0x1C or raw[:4] != b'darc':
        raise ValueError('Not a DARC archive')
    bom, hdr_len = struct.unpack_from('<HH', raw, 4)
    if bom != 0xFEFF:
        raise ValueError(f'Only little-endian DARC is supported (BOM={bom:#x})')
    version, file_len, table_off, table_len, data_off = struct.unpack_from('<IIIII', raw, 8)
    if hdr_len < 0x1C or table_off + 12 > len(raw):
        raise ValueError('Invalid DARC header')
    root_name, root_parent, node_count = struct.unpack_from('<III', raw, table_off)
    if not (root_name & 0x01000000) or not (1 <= node_count <= 100000):
        raise ValueError('Invalid DARC root node')
    names_base = table_off + node_count * 12
    if names_base > len(raw):
        raise ValueError('DARC node table outside file')

    def get_name(word: int) -> str:
        rel = word & 0x00FFFFFF
        p = names_base + rel
        if p < names_base or p >= len(raw):
            return f'<bad-name-{rel:#x}>'
        end = p
        while end + 1 < len(raw) and raw[end:end+2] != b'\0\0':
            end += 2
        return raw[p:end].decode('utf-16le', errors='replace')

    nodes: list[DarcNode] = []
    for i in range(node_count):
        noff = table_off + i * 12
        name_word, f1, f2 = struct.unpack_from('<III', raw, noff)
        nodes.append(DarcNode(i, get_name(name_word), bool(name_word & 0x01000000), f1, f2, noff))

    # Build paths from DARC pre-order directory end indices.
    dir_stack: list[tuple[int, str]] = [(nodes[0].field2, '')]
    for n in nodes[1:]:
        while dir_stack and n.index >= dir_stack[-1][0]:
            dir_stack.pop()
        parent = dir_stack[-1][1] if dir_stack else ''
        if n.name in ('', '.'):
            path = parent
        else:
            path = f'{parent}/{n.name}'.strip('/')
        n.path = path
        if n.is_dir:
            dir_stack.append((n.field2, path))

    return DarcArchive(raw, nodes, data_off, file_len)


def darc_extract(input_path: Path, output_dir: Path, manifest_path: Path | None = None) -> dict:
    packed = input_path.read_bytes()
    raw = blz_decompress(packed)
    arc = parse_darc(raw)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    file_nodes = [n for n in arc.nodes if not n.is_dir]
    sorted_offsets = sorted(n.field1 for n in file_nodes)

    for n in file_nodes:
        start, size = n.field1, n.field2
        if start + size > len(raw):
            raise ValueError(f'DARC file {n.path} exceeds archive')
        out = output_dir / n.path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw[start:start+size])
        next_offsets = [o for o in sorted_offsets if o > start]
        cap_end = min(next_offsets) if next_offsets else min(len(raw), arc.file_length)
        files.append({
            'node_index': n.index,
            'path': n.path,
            'offset': start,
            'size': size,
            'capacity_until_next_file': max(0, cap_end - start),
        })

    manifest = {
        'source': input_path.name,
        'decompressed_size': len(raw),
        'data_offset': arc.data_offset,
        'files': files,
    }
    if manifest_path is None:
        manifest_path = output_dir / '_darc_manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def darc_inject(original_path: Path, replacement_root: Path, output_path: Path) -> list[str]:
    raw = bytearray(blz_decompress(original_path.read_bytes()))
    arc = parse_darc(bytes(raw))
    file_nodes = [n for n in arc.nodes if not n.is_dir]
    sorted_nodes = sorted(file_nodes, key=lambda n: n.field1)
    notes: list[str] = []

    for i, n in enumerate(sorted_nodes):
        repl = replacement_root / n.path
        if not repl.is_file():
            continue
        blob = repl.read_bytes()
        start = n.field1
        next_off = sorted_nodes[i + 1].field1 if i + 1 < len(sorted_nodes) else min(len(raw), arc.file_length)
        capacity = next_off - start
        if len(blob) > capacity:
            raise ValueError(
                f'{n.path}: replacement is {len(blob)} bytes but in-place capacity is {capacity}. '
                'This injector intentionally does not rebuild DARC layout.'
            )
        raw[start:start+len(blob)] = blob
        if len(blob) < n.field2:
            raw[start+len(blob):start+n.field2] = b'\0' * (n.field2 - len(blob))
        # Update file-size field in node table.
        struct.pack_into('<I', raw, n.node_offset + 8, len(blob))
        notes.append(f'{n.path}: {n.field2} -> {len(blob)} bytes')

    packed = blz_compress(bytes(raw))
    if blz_decompress(packed) != bytes(raw):
        raise RuntimeError('DARC BLZ round-trip check failed')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(packed)
    return notes


# ---------------- BCFNT / CFNU charset inspection ----------------

TURKISH_CHARS = 'ÇĞİÖŞÜçğıöşü'


def bcfnt_codepoints(data: bytes) -> set[int]:
    """Collect Unicode codepoints from little-endian CMAP sections by scanning blocks.

    Works with ordinary BCFNT and shared-font dumps that contain CFNU/CMAP blocks.
    """
    cps: set[int] = set()
    starts = []
    p = 0
    while True:
        p = data.find(b'CMAP', p)
        if p < 0:
            break
        starts.append(p)
        p += 4

    for p in starts:
        if p + 0x14 > len(data):
            continue
        size = _u32(data, p + 4)
        begin, end, method, _reserved = struct.unpack_from('<HHHH', data, p + 8)
        if size < 0x14 or p + size > len(data) or end < begin:
            continue
        body = p + 0x14
        if method == 0:
            if body + 2 <= p + size:
                base = struct.unpack_from('<H', data, body)[0]
                for cp in range(begin, end + 1):
                    # Direct mapping covers the whole range; glyph index itself is irrelevant here.
                    _glyph = base + (cp - begin)
                    cps.add(cp)
        elif method == 1:
            count = end - begin + 1
            if body + count * 2 <= p + size:
                vals = struct.unpack_from('<' + 'H' * count, data, body)
                for j, glyph in enumerate(vals):
                    if glyph != 0xFFFF:
                        cps.add(begin + j)
        elif method == 2:
            if body + 2 <= p + size:
                count = struct.unpack_from('<H', data, body)[0]
                q = body + 2
                for _ in range(count):
                    if q + 4 > p + size:
                        break
                    cp, glyph = struct.unpack_from('<HH', data, q)
                    q += 4
                    if glyph != 0xFFFF:
                        cps.add(cp)
    return cps


def font_report(path: Path) -> str:
    data = path.read_bytes()
    cps = bcfnt_codepoints(data)
    magics = []
    for m in (b'CFNT', b'CFNU', b'FFNT'):
        pos = data.find(m)
        if pos >= 0:
            magics.append(f'{m.decode("ascii")}@0x{pos:X}')
    present = ''.join(ch for ch in TURKISH_CHARS if ord(ch) in cps)
    missing = ''.join(ch for ch in TURKISH_CHARS if ord(ch) not in cps)
    lines = [
        f'File: {path}',
        f'Font signatures: {", ".join(magics) if magics else "not found"}',
        f'CMAP codepoints found: {len(cps)}',
        f'Turkish glyphs present: {present or "(none)"}',
        f'Turkish glyphs missing: {missing or "(none)"}',
    ]
    return '\n'.join(lines)

# ---------------- BCLYT text panes / UI localization candidates ----------------

@dataclass
class BclytText:
    section_index: int
    pane_name: str
    text: str


def parse_bclyt_texts(raw: bytes) -> list[BclytText]:
    if len(raw) < 0x14 or raw[:4] != b'CLYT':
        raise ValueError('Not a little-endian CLYT/BCLYT file')
    bom, header_len = struct.unpack_from('<HH', raw, 4)
    if bom != 0xFEFF:
        raise ValueError('Only little-endian BCLYT is supported')
    section_count = struct.unpack_from('<H', raw, 0x10)[0]
    pos = header_len
    out: list[BclytText] = []
    for si in range(section_count):
        if pos + 8 > len(raw):
            raise ValueError(f'BCLYT section {si} header outside file')
        sig = raw[pos:pos+4]
        size = _u32(raw, pos + 4)
        if size < 8 or pos + size > len(raw):
            raise ValueError(f'Invalid BCLYT section {si} size {size}')
        if sig == b'txt1':
            if size < 0x74:
                raise ValueError(f'txt1 section {si} is too short')
            pane_raw = raw[pos+0x0C:pos+0x1C]
            pane_name = pane_raw.split(b'\0', 1)[0].decode('ascii', errors='replace')
            text_off = _u32(raw, pos + 0x58)
            if text_off > size:
                raise ValueError(f'txt1 section {si}: bad string offset {text_off:#x}')
            if text_off == size:
                text = ''
            else:
                start = pos + text_off
                end_limit = pos + size
                q = start
                while q + 1 < end_limit and raw[q:q+2] != b'\0\0':
                    q += 2
                if q + 1 >= end_limit:
                    raise ValueError(f'txt1 section {si}: missing UTF-16 terminator')
                text = raw[start:q].decode('utf-16le', errors='strict')
            out.append(BclytText(si, pane_name, text))
        pos += size
    return out


def rebuild_bclyt_texts(raw: bytes, replacements: dict[int, str]) -> bytes:
    if not replacements:
        return raw
    if len(raw) < 0x14 or raw[:4] != b'CLYT':
        raise ValueError('Not a BCLYT file')
    bom, header_len = struct.unpack_from('<HH', raw, 4)
    if bom != 0xFEFF:
        raise ValueError('Only little-endian BCLYT is supported')
    section_count = struct.unpack_from('<H', raw, 0x10)[0]
    pos = header_len
    sections: list[bytes] = []

    for si in range(section_count):
        if pos + 8 > len(raw):
            raise ValueError('Truncated BCLYT')
        size = _u32(raw, pos + 4)
        if size < 8 or pos + size > len(raw):
            raise ValueError(f'Invalid BCLYT section size at {si}')
        sec = bytearray(raw[pos:pos+size])
        if sec[:4] == b'txt1' and si in replacements:
            if size < 0x74:
                raise ValueError(f'txt1 section {si} too short')
            text_off = _u32(sec, 0x58)
            if text_off > len(sec):
                raise ValueError(f'txt1 section {si}: invalid text offset')
            new_text = replacements[si]
            if new_text == '' and text_off == len(sec):
                new_sec = sec  # preserve the game's zero-length txt1 form
            else:
                encoded = new_text.encode('utf-16le') + b'\0\0'
                new_sec = bytearray(sec[:text_off])
                new_sec.extend(encoded)
                while len(new_sec) % 4:
                    new_sec.append(0)
                struct.pack_into('<I', new_sec, 4, len(new_sec))
            sec = new_sec
        sections.append(bytes(sec))
        pos += size

    # Preserve any unusual tail bytes, although normal BCLYT ends at the last section.
    tail = raw[pos:]
    header = bytearray(raw[:header_len])
    rebuilt = header + b''.join(sections) + tail
    struct.pack_into('<I', rebuilt, 0x0C, len(rebuilt))

    # Ensure requested replacements survived the rebuild.
    parsed = {x.section_index: x.text for x in parse_bclyt_texts(bytes(rebuilt))}
    for si, text in replacements.items():
        if parsed.get(si) != text:
            raise RuntimeError(f'BCLYT text round-trip failed for section {si}')
    return bytes(rebuilt)


def classify_ui_text(text: str) -> str:
    if re.fullmatch(r'%%[^%\r\n]+%%', text):
        return 'runtime_key_do_not_translate'
    low = text.lower().strip()
    placeholder_phrases = (
        'goes here', 'description...', '< subtitle >', '< words here >',
        'query info', 'btn text', 'cbox text', 'button name', 'slider name',
        'player name', 'zone name', 'area name', 'skill name', 'quest name',
        'tree name', 'power title', 'level name', 'custom value', 'custom zone',
        'really long name', 'prereq skill', 'two lines', 'item name',
    )
    if any(p in low for p in placeholder_phrases):
        return 'likely_template_or_placeholder'
    return 'literal_candidate_review_in_game'


def extract_ui_text_candidates(ui_dir: Path, output_path: Path) -> dict:
    entries = []
    arc_count = 0
    bclyt_count = 0
    for arc_path in sorted(ui_dir.glob('*.arc_')):
        raw_arc = blz_decompress(arc_path.read_bytes())
        arc = parse_darc(raw_arc)
        arc_count += 1
        for node in arc.nodes:
            if node.is_dir or not node.name.lower().endswith('.bclyt'):
                continue
            bclyt_count += 1
            blob = raw_arc[node.field1:node.field1+node.field2]
            try:
                panes = parse_bclyt_texts(blob)
            except ValueError:
                continue
            for pane in panes:
                if pane.text == '':
                    continue
                entries.append({
                    'archive': arc_path.name,
                    'bclyt_path': node.path,
                    'section_index': pane.section_index,
                    'pane_name': pane.pane_name,
                    'classification': classify_ui_text(pane.text),
                    'source': pane.text,
                    'text': pane.text,
                })
    payload = {
        'format': 'Heroes of Ruin BCLYT txt1 candidate bundle',
        'notes': [
            'These are static/default txt1 strings inside UI layouts. Many are placeholders or runtime keys.',
            'Translate only strings you confirm are visible in-game. Never translate runtime_key_do_not_translate entries.',
            'Build writes only entries whose text differs from source.',
        ],
        'archives_scanned': arc_count,
        'bclyt_files_scanned': bclyt_count,
        'entries': entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return payload


def _replace_darc_files(raw_arc: bytes, replacements: dict[str, bytes]) -> bytes:
    if not replacements:
        return raw_arc
    out = bytearray(raw_arc)
    arc = parse_darc(raw_arc)
    files = sorted((n for n in arc.nodes if not n.is_dir), key=lambda n: n.field1)
    by_path = {n.path: n for n in files}
    for path in replacements:
        if path not in by_path:
            raise ValueError(f'DARC replacement path not found: {path}')

    for i, n in enumerate(files):
        if n.path not in replacements:
            continue
        blob = replacements[n.path]
        next_off = files[i + 1].field1 if i + 1 < len(files) else min(len(out), arc.file_length)
        capacity = next_off - n.field1
        if len(blob) > capacity:
            raise ValueError(
                f'{n.path}: rebuilt BCLYT is {len(blob)} bytes but DARC in-place capacity is {capacity}. '
                'Shorten the text or use a full DARC layout rebuilder.'
            )
        out[n.field1:n.field1+len(blob)] = blob
        # Zero the remainder of the old file body only. Do not erase inter-file padding.
        if len(blob) < n.field2:
            out[n.field1+len(blob):n.field1+n.field2] = b'\0' * (n.field2 - len(blob))
        struct.pack_into('<I', out, n.node_offset + 8, len(blob))
    return bytes(out)


def build_ui_text_patches(ui_dir: Path, translation_json: Path, output_ui_dir: Path,
                          allow_token_change: bool = False) -> dict:
    obj = json.loads(translation_json.read_text(encoding='utf-8'))
    rows = obj['entries'] if isinstance(obj, dict) else obj
    changes_by_arc: dict[str, list[dict]] = {}
    for row in rows:
        source = str(row.get('source', ''))
        text = str(row.get('text', source))
        if text == source:
            continue
        classification = row.get('classification', '')
        if classification == 'runtime_key_do_not_translate':
            raise ValueError(f'Runtime UI key must not be translated: {source}')
        if not allow_token_change and Counter(protected_tokens(source)) != Counter(protected_tokens(text)):
            raise ValueError(f'Protected UI token mismatch: {source!r} -> {text!r}')
        changes_by_arc.setdefault(row['archive'], []).append(row)

    output_ui_dir.mkdir(parents=True, exist_ok=True)
    report = {'archives_modified': [], 'changed_text_entries': 0}
    for arc_name, changes in sorted(changes_by_arc.items()):
        src_arc_path = ui_dir / arc_name
        if not src_arc_path.is_file():
            raise FileNotFoundError(src_arc_path)
        raw_arc = blz_decompress(src_arc_path.read_bytes())
        arc = parse_darc(raw_arc)
        by_path = {n.path: n for n in arc.nodes if not n.is_dir}
        grouped: dict[str, dict[int, str]] = {}
        for row in changes:
            grouped.setdefault(row['bclyt_path'], {})[int(row['section_index'])] = str(row['text'])

        file_repls: dict[str, bytes] = {}
        for bclyt_path, reps in grouped.items():
            n = by_path.get(bclyt_path)
            if n is None:
                raise ValueError(f'{arc_name}: BCLYT not found: {bclyt_path}')
            old = raw_arc[n.field1:n.field1+n.field2]
            file_repls[bclyt_path] = rebuild_bclyt_texts(old, reps)

        new_raw = _replace_darc_files(raw_arc, file_repls)
        packed = blz_compress(new_raw)
        if blz_decompress(packed) != new_raw:
            raise RuntimeError(f'{arc_name}: BLZ validation failed')
        dest = output_ui_dir / arc_name
        dest.write_bytes(packed)
        report['archives_modified'].append({
            'archive': arc_name,
            'changed_entries': len(changes),
            'packed_size': len(packed),
        })
        report['changed_text_entries'] += len(changes)
    return report
