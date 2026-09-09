#!/usr/bin/env python3
"""
Face Raiders (Nintendo 3DS) MSBT localization helper.

Features:
  * Reads a decrypted NCCH/CXI directly (or a ZIP containing CXIs).
  * Parses Nintendo 3DS RomFS without third-party modules.
  * Exports every StgFace MSBT language side-by-side to UTF-8-SIG CSV.
  * Validates printf placeholders, private-use button glyphs and estimated UI fit.
  * Rebuilds a base MSBT with the Turkish column.
  * Writes the result directly into a Luma3DS LayeredFS directory tree.

This tool does NOT decrypt encrypted NCCH/CXI files. If RomFS is encrypted,
first dump/decrypt it using your own console/tooling.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import struct
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

ALIGN = lambda n, a=0x10: (n + a - 1) & ~(a - 1)
TOKEN_RE = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?)?(?:hh|h|ll|l|L|z|j|t)?[A-Za-z%]')
RAW_TOKEN_RE = re.compile(r'\[\[(?:TAG|END|RAW):([0-9a-fA-F]+)\]\]')


def u32(b: bytes, off: int, endian: str = '<') -> int:
    return struct.unpack_from(endian + 'I', b, off)[0]


def u64(b: bytes, off: int, endian: str = '<') -> int:
    return struct.unpack_from(endian + 'Q', b, off)[0]


def replace_escaped_pua(text: str) -> str:
    """Turn literal \\uE000-style sequences into PUA glyphs without touching Turkish UTF-8."""
    return re.sub(r'\\u([eEfF][0-9a-fA-F]{3})', lambda m: chr(int(m.group(1), 16)), text)


def ascii_turkish(text: str) -> str:
    table = str.maketrans({
        'ç':'c','Ç':'C','ğ':'g','Ğ':'G','ı':'i','İ':'I','ö':'o','Ö':'O','ş':'s','Ş':'S','ü':'u','Ü':'U',
        '’':"'", '“':'"', '”':'"', '…':'...'
    })
    return text.translate(table)


@dataclass
class RomFile:
    path: str
    offset: int
    size: int


class NCCHRomFS:
    """Minimal read-only parser for decrypted NCCH/CXI + RomFS."""
    def __init__(self, ncch: bytes, source_name: str = '<memory>'):
        self.ncch = ncch
        self.source_name = source_name
        if len(ncch) < 0x200 or ncch[0x100:0x104] != b'NCCH':
            raise ValueError(f'{source_name}: NCCH magic not found at 0x100')
        self.title_id = u64(ncch, 0x108)
        rom_units, rom_size_units = struct.unpack_from('<II', ncch, 0x1B0)
        self.romfs_offset = rom_units * 0x200
        self.romfs_size = rom_size_units * 0x200
        if self.romfs_offset <= 0 or self.romfs_offset + self.romfs_size > len(ncch):
            raise ValueError(f'{source_name}: invalid RomFS range')
        self.romfs = ncch[self.romfs_offset:self.romfs_offset + self.romfs_size]
        if self.romfs[:4] != b'IVFC':
            raise ValueError(
                f'{source_name}: RomFS does not start with IVFC. '
                'The CXI is probably encrypted; decrypt/dump it first.'
            )
        self.files = self._parse_files()
        self.by_path = {f.path: f for f in self.files}

    def _parse_files(self) -> List[RomFile]:
        r = self.romfs
        # NCCH RomFS stores the physical Level-3 filesystem at 0x1000.
        l3 = 0x1000
        if len(r) < l3 + 0x28 or u32(r, l3) != 0x28:
            raise ValueError(f'{self.source_name}: unsupported/invalid RomFS Level-3 header')
        (hlen, dht_o, dht_l, dmt_o, dmt_l,
         fht_o, fht_l, fmt_o, fmt_l, data_o) = struct.unpack_from('<10I', r, l3)
        dmt = l3 + dmt_o
        fmt = l3 + fmt_o
        data = l3 + data_o
        if not (0 <= dmt < len(r) and 0 <= fmt < len(r) and 0 <= data <= len(r)):
            raise ValueError('RomFS table offset outside image')

        seen_dirs, seen_files = set(), set()
        out: List[RomFile] = []

        def dirent(off: int):
            o = dmt + off
            parent, sib, child, first, hash_next, name_len = struct.unpack_from('<6I', r, o)
            name = r[o+0x18:o+0x18+name_len].decode('utf-16le') if name_len else ''
            return parent, sib, child, first, hash_next, name_len, name

        def fileent(off: int):
            o = fmt + off
            parent, sib = struct.unpack_from('<II', r, o)
            data_off, size = struct.unpack_from('<QQ', r, o+8)
            hash_next, name_len = struct.unpack_from('<II', r, o+0x18)
            name = r[o+0x20:o+0x20+name_len].decode('utf-16le')
            return parent, sib, data_off, size, hash_next, name_len, name

        def walk_dir(off: int, parts: List[str]):
            if off == 0xFFFFFFFF or off in seen_dirs:
                return
            seen_dirs.add(off)
            parent, sib, child, first, hash_next, name_len, name = dirent(off)
            here = parts + ([name] if name else [])

            fo = first
            while fo != 0xFFFFFFFF and fo not in seen_files:
                seen_files.add(fo)
                fp, fsib, doff, size, fh, fnl, fname = fileent(fo)
                abs_off = data + doff
                if abs_off + size > len(r):
                    raise ValueError(f'RomFS file outside image: {fname}')
                out.append(RomFile('/'.join(here + [fname]), abs_off, size))
                fo = fsib

            co = child
            while co != 0xFFFFFFFF and co not in seen_dirs:
                next_sib = dirent(co)[1]
                walk_dir(co, here)
                co = next_sib

        walk_dir(0, [])
        return out

    def get(self, path: str) -> bytes:
        f = self.by_path[path]
        return self.romfs[f.offset:f.offset+f.size]

    def find(self, prefix: str = '', suffix: str = '') -> List[str]:
        return sorted(p for p in self.by_path if p.startswith(prefix) and p.endswith(suffix))


class MSBT:
    """Small MSBT reader/writer preserving non-TXT2 blocks."""
    def __init__(self, data: bytes):
        self.data = data
        if data[:8] != b'MsgStdBn':
            raise ValueError('Not an MSBT (MsgStdBn missing)')
        self.endian = '<' if data[8:10] == b'\xff\xfe' else '>'
        self.encoding = data[0x0C]
        if self.encoding != 1:
            raise ValueError(f'Only UTF-16 MSBT is supported here (encoding={self.encoding})')
        self.block_count = struct.unpack_from(self.endian+'H', data, 0x0E)[0]
        self.blocks: List[Tuple[str,int,int,bytes,bytes]] = []
        off = 0x20
        for _ in range(self.block_count):
            sig = data[off:off+4].decode('ascii')
            size = u32(data, off+4, self.endian)
            header = data[off:off+0x10]
            payload = data[off+0x10:off+0x10+size]
            self.blocks.append((sig, off, size, header, payload))
            off = ALIGN(off + 0x10 + size)
        self.labels = self._parse_labels()
        self.text_raw = self._parse_texts()
        self.index_to_labels: Dict[int,List[str]] = {}
        for label, idx in self.labels.items():
            self.index_to_labels.setdefault(idx, []).append(label)

    @property
    def codec(self) -> str:
        return 'utf-16le' if self.endian == '<' else 'utf-16be'

    def _block(self, sig: str):
        return next(b for b in self.blocks if b[0] == sig)

    def _parse_labels(self) -> Dict[str,int]:
        p = self._block('LBL1')[4]
        group_count = u32(p, 0, self.endian)
        groups = [struct.unpack_from(self.endian+'II', p, 4+i*8) for i in range(group_count)]
        labels: Dict[str,int] = {}
        for count, off in groups:
            q = off
            for _ in range(count):
                ln = p[q]; q += 1
                name = p[q:q+ln].decode('utf-8'); q += ln
                idx = u32(p, q, self.endian); q += 4
                labels[name] = idx
        return labels

    def _parse_texts(self) -> List[bytes]:
        p = self._block('TXT2')[4]
        n = u32(p, 0, self.endian)
        offsets = list(struct.unpack_from(self.endian+f'{n}I', p, 4))
        out: List[bytes] = []
        for i, start in enumerate(offsets):
            stop = offsets[i+1] if i+1 < n else len(p)
            raw = p[start:stop]
            pos = 0
            while pos + 1 < len(raw):
                cu = struct.unpack_from(self.endian+'H', raw, pos)[0]
                if cu == 0:
                    raw = raw[:pos]
                    break
                if cu == 0x000E:
                    if pos + 8 > len(raw): break
                    param_size = struct.unpack_from(self.endian+'H', raw, pos+6)[0]
                    pos += 8 + param_size
                elif cu == 0x000F:
                    pos += 6
                else:
                    pos += 2
            out.append(raw)
        return out

    def decode_message(self, raw: bytes) -> str:
        out: List[str] = []
        pos = 0
        while pos < len(raw):
            if pos + 2 > len(raw):
                out.append(f'[[RAW:{raw[pos:].hex()}]]')
                break
            cu = struct.unpack_from(self.endian+'H', raw, pos)[0]
            if cu == 0x000E:
                if pos + 8 > len(raw):
                    out.append(f'[[RAW:{raw[pos:].hex()}]]')
                    break
                param_size = struct.unpack_from(self.endian+'H', raw, pos+6)[0]
                ln = 8 + param_size
                out.append(f'[[TAG:{raw[pos:pos+ln].hex()}]]')
                pos += ln
            elif cu == 0x000F:
                ln = min(6, len(raw)-pos)
                out.append(f'[[END:{raw[pos:pos+ln].hex()}]]')
                pos += ln
            else:
                start = pos
                while pos + 1 < len(raw):
                    x = struct.unpack_from(self.endian+'H', raw, pos)[0]
                    if x in (0x000E, 0x000F):
                        break
                    pos += 2
                out.append(raw[start:pos].decode(self.codec, errors='replace'))
        return ''.join(out)

    def encode_message(self, text: str) -> bytes:
        text = replace_escaped_pua(text)
        out = bytearray()
        pos = 0
        for m in RAW_TOKEN_RE.finditer(text):
            out += text[pos:m.start()].encode(self.codec)
            out += bytes.fromhex(m.group(1))
            pos = m.end()
        out += text[pos:].encode(self.codec)
        return bytes(out)

    def texts(self) -> List[str]:
        return [self.decode_message(x) for x in self.text_raw]

    def rebuild(self, new_texts: List[str]) -> bytes:
        if len(new_texts) != len(self.text_raw):
            raise ValueError(f'Text count mismatch: {len(new_texts)} != {len(self.text_raw)}')
        enc = [self.encode_message(s) + (b'\x00\x00' if self.endian == '<' else b'\x00\x00') for s in new_texts]
        n = len(enc)
        payload = bytearray()
        payload += struct.pack(self.endian+'I', n)
        base = 4 + 4*n
        cur = base
        for s in enc:
            payload += struct.pack(self.endian+'I', cur)
            cur += len(s)
        for s in enc:
            payload += s

        out = bytearray(self.data[:0x20])
        for sig, old_off, old_size, header, old_payload in self.blocks:
            if sig == 'TXT2':
                h = bytearray(header)
                struct.pack_into(self.endian+'I', h, 4, len(payload))
                out += h + payload
            else:
                out += header + old_payload
            while len(out) % 0x10:
                out.append(0xAB)
        struct.pack_into(self.endian+'I', out, 0x12, len(out))
        return bytes(out)


LANG_ORDER = [
    'EU_Dutch','EU_English','EU_French','EU_German','EU_Italian','EU_Portuguese',
    'EU_Russian','EU_Spanish','JP_Japanese','US_English','US_French','US_Portuguese','US_Spanish'
]
LATIN_LANGS = [x for x in LANG_ORDER if x != 'JP_Japanese' and 'Russian' not in x]


def load_ncch_candidates(path: Path) -> Iterable[Tuple[str,bytes]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, 'r') as z:
            for name in z.namelist():
                if name.lower().endswith('.cxi'):
                    yield name, z.read(name)
    else:
        yield path.name, path.read_bytes()


def choose_romfs(path: Path, group: str) -> NCCHRomFS:
    errors = []
    needle = f'hal/msg/{group}/'
    for name, data in load_ncch_candidates(path):
        try:
            rom = NCCHRomFS(data, name)
            if any(p.startswith(needle) and p.endswith('.msbt') for p in rom.by_path):
                return rom
        except Exception as e:
            errors.append(f'{name}: {e}')
    details = '\n'.join(errors)
    raise SystemExit(f'No CXI containing {needle}*.msbt was found.\n{details}')


def language_from_path(path: str, group: str) -> str:
    stem = Path(path).stem
    return stem[len(group):] if stem.startswith(group) else stem


def line_units(line: str) -> float:
    units = 0.0
    for ch in line:
        o = ord(ch)
        if ch in ' \t': units += 0.5
        elif ch in "ilIıİ.,:;!'|`": units += 0.55
        elif ch in 'mwMW@%&QO0': units += 1.2
        elif 0xE000 <= o <= 0xF8FF: units += 1.8
        elif ch in '“”()[]{}': units += 0.8
        else: units += 1.0
    return round(units, 2)


def fit_metrics(values: Dict[str,str], tr: str) -> Tuple[int,float,int,float,str,str]:
    source_lines = 1
    safe_units = 0.0
    for lang, text in values.items():
        if not text: continue
        lines = text.split('\n')
        source_lines = max(source_lines, len(lines))
        if lang in LATIN_LANGS:
            safe_units = max(safe_units, max((line_units(x) for x in lines), default=0))
    tr_lines_arr = tr.split('\n') if tr else ['']
    tr_lines = len(tr_lines_arr) if tr else 0
    tr_units = max((line_units(x) for x in tr_lines_arr), default=0)
    if not tr:
        return source_lines, safe_units, 0, 0.0, 'EMPTY', ''
    line_ok = tr_lines <= source_lines
    ratio = (tr_units / safe_units) if safe_units else 0
    if line_ok and ratio <= 1.03:
        status = 'OK'
        note = 'Shipped Latin localizations suggest this should fit.'
    elif line_ok and ratio <= 1.12:
        status = 'TIGHT'
        note = 'Close to/just above the widest shipped Latin line; test on hardware.'
    else:
        status = 'REVIEW'
        note = 'Exceeds the empirical line/width envelope; shorten or test carefully.'
    return source_lines, safe_units, tr_lines, tr_units, status, note


def fmt_tokens(s: str) -> Counter:
    return Counter(TOKEN_RE.findall(s.replace('%%', '')))


def pua_chars(s: str) -> Counter:
    return Counter(ch for ch in s if 0xE000 <= ord(ch) <= 0xF8FF)


def export_csv(rom: NCCHRomFS, group: str, out_csv: Path, turkish_by_label: Dict[str,str] | None = None,
               notes_by_label: Dict[str,str] | None = None):
    prefix = f'hal/msg/{group}/{group}'
    paths = rom.find(prefix=prefix, suffix='.msbt')
    if not paths:
        raise SystemExit(f'No MSBT files found for {group}')
    lang_msbt: Dict[str,MSBT] = {}
    for p in paths:
        lang = language_from_path(p, group)
        lang_msbt[lang] = MSBT(rom.get(p))

    base_lang = 'EU_English' if 'EU_English' in lang_msbt else next(iter(lang_msbt))
    base = lang_msbt[base_lang]
    langs = [x for x in LANG_ORDER if x in lang_msbt] + sorted(set(lang_msbt)-set(LANG_ORDER))
    for lang, m in lang_msbt.items():
        if m.labels != base.labels or len(m.text_raw) != len(base.text_raw):
            raise SystemExit(f'{lang}: label/index structure differs from {base_lang}; automatic alignment refused.')

    turkish_by_label = turkish_by_label or {}
    notes_by_label = notes_by_label or {}
    headers = ['Index','Label'] + langs + [
        'Turkish','Source_Max_Lines','Source_Safe_Line_Units','Turkish_Lines','Turkish_Max_Line_Units',
        'Fit_Status','Placeholder_Check','PUA_Glyph_Check','Translation_Note','Fit_Note'
    ]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        decoded = {lang:m.texts() for lang,m in lang_msbt.items()}
        for i in range(len(base.text_raw)):
            labels = base.index_to_labels.get(i, [])
            label = labels[0] if labels else f'__index_{i}'
            values = {lang:decoded[lang][i] for lang in langs}
            tr = replace_escaped_pua(turkish_by_label.get(label, ''))
            src = values.get(base_lang, '')
            sm, su, tl, tu, status, fit_note = fit_metrics(values, tr)
            ph_ok = 'OK' if (not tr or fmt_tokens(src) == fmt_tokens(tr)) else 'MISMATCH'
            pua_ok = 'OK' if (not tr or pua_chars(src) == pua_chars(tr)) else 'MISMATCH'
            row = {'Index':i, 'Label':label, **values, 'Turkish':tr,
                   'Source_Max_Lines':sm, 'Source_Safe_Line_Units':su,
                   'Turkish_Lines':tl, 'Turkish_Max_Line_Units':tu,
                   'Fit_Status':status, 'Placeholder_Check':ph_ok, 'PUA_Glyph_Check':pua_ok,
                   'Translation_Note':notes_by_label.get(label,''), 'Fit_Note':fit_note}
            w.writerow(row)
    return len(base.text_raw), langs, base_lang


def read_csv_translation(csv_path: Path) -> Tuple[List[dict], Dict[str,str]]:
    with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows or 'Label' not in rows[0] or 'Turkish' not in rows[0]:
        raise SystemExit('CSV must contain Label and Turkish columns.')
    tr = {r['Label']:replace_escaped_pua(r.get('Turkish','')) for r in rows}
    return rows, tr


def inject_layeredfs(rom: NCCHRomFS, group: str, csv_path: Path, out_root: Path,
                     base_language: str, ascii_fallback: bool = False, allow_blank: bool = False) -> Path:
    rows, tr_by_label = read_csv_translation(csv_path)
    base_path = f'hal/msg/{group}/{group}{base_language}.msbt'
    if base_path not in rom.by_path:
        raise SystemExit(f'Base MSBT not found: {base_path}')
    m = MSBT(rom.get(base_path))
    old = m.texts()
    new = list(old)
    problems = []

    for label, idx in m.labels.items():
        if label not in tr_by_label:
            problems.append(f'{label}: missing from CSV')
            continue
        tr = tr_by_label[label]
        src = old[idx]
        if src and not tr and not allow_blank:
            problems.append(f'{label}: source is non-empty but Turkish is blank')
            continue
        if tr:
            if fmt_tokens(src) != fmt_tokens(tr):
                problems.append(f'{label}: printf placeholders differ: {fmt_tokens(src)} != {fmt_tokens(tr)}')
            if pua_chars(src) != pua_chars(tr):
                problems.append(f'{label}: private-use/button glyphs differ')
            new[idx] = ascii_turkish(tr) if ascii_fallback else tr
        elif allow_blank:
            new[idx] = ''

    if problems:
        msg = '\n'.join('  - '+x for x in problems[:50])
        more = '' if len(problems) <= 50 else f'\n  ... and {len(problems)-50} more'
        raise SystemExit(f'Injection aborted due to validation errors:\n{msg}{more}')

    patched = m.rebuild(new)
    title = f'{rom.title_id:016X}'
    out_file = out_root / 'luma' / 'titles' / title / 'romfs' / base_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_bytes(patched)

    # Re-open rebuilt MSBT to make sure offsets/counts are valid.
    check = MSBT(patched)
    if check.texts() != new:
        raise SystemExit('Internal verification failed after rebuilding MSBT.')
    return out_file


def cmd_export(args):
    rom = choose_romfs(Path(args.input), args.group)
    n, langs, base = export_csv(rom, args.group, Path(args.csv))
    print(f'CXI: {rom.source_name}')
    print(f'Title ID: {rom.title_id:016X}')
    print(f'Exported {n} aligned rows / {len(langs)} languages -> {args.csv}')
    print(f'Base language for validation: {base}')


def cmd_validate(args):
    rows, tr = read_csv_translation(Path(args.csv))
    base_col = args.base_language
    problems = []
    fit_counts = Counter()
    for r in rows:
        src = r.get(base_col, '')
        t = tr[r['Label']]
        if src and not t:
            problems.append(f"{r['Label']}: Turkish blank")
            continue
        if t and fmt_tokens(src) != fmt_tokens(t):
            problems.append(f"{r['Label']}: placeholder mismatch")
        if t and pua_chars(src) != pua_chars(t):
            problems.append(f"{r['Label']}: PUA/button glyph mismatch")
        vals = {k:r.get(k,'') for k in LANG_ORDER if k in r}
        *_, status, note = fit_metrics(vals, t)
        fit_counts[status] += 1
    print('Fit:', ', '.join(f'{k}={v}' for k,v in fit_counts.items()))
    if problems:
        for x in problems[:100]: print('ERROR:', x)
        raise SystemExit(2)
    print('Validation OK: placeholders and button glyphs are preserved.')


def cmd_inject(args):
    rom = choose_romfs(Path(args.input), args.group)
    out = inject_layeredfs(rom, args.group, Path(args.csv), Path(args.out), args.base_language,
                           ascii_fallback=args.ascii_fallback, allow_blank=args.allow_blank)
    print(f'CXI: {rom.source_name}')
    print(f'Title ID: {rom.title_id:016X}')
    print(f'Patched LayeredFS file: {out}')


def build_parser():
    p = argparse.ArgumentParser(description='Face Raiders MSBT CSV exporter + LayeredFS injector')
    sub = p.add_subparsers(dest='cmd', required=True)

    e = sub.add_parser('export', help='Export all language MSBTs side-by-side to CSV')
    e.add_argument('input', help='Decrypted .cxi or a .zip containing CXIs')
    e.add_argument('csv', help='Output CSV path')
    e.add_argument('--group', default='StgFace', help='MSBT group (default: StgFace)')
    e.set_defaults(func=cmd_export)

    v = sub.add_parser('validate', help='Validate a translated CSV')
    v.add_argument('csv')
    v.add_argument('--base-language', default='EU_English')
    v.set_defaults(func=cmd_validate)

    i = sub.add_parser('inject', help='Build a LayeredFS replacement MSBT from Turkish CSV')
    i.add_argument('input', help='Decrypted .cxi or a .zip containing CXIs')
    i.add_argument('csv', help='CSV containing the Turkish column')
    i.add_argument('out', help='Output directory (will contain luma/titles/...)')
    i.add_argument('--group', default='StgFace')
    i.add_argument('--base-language', default='EU_English', help='Existing language slot to replace')
    i.add_argument('--ascii-fallback', action='store_true', help='Strip Turkish diacritics for font testing')
    i.add_argument('--allow-blank', action='store_true', help='Allow blank Turkish text to replace non-empty source')
    i.set_defaults(func=cmd_inject)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
