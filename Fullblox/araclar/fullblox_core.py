#!/usr/bin/env python3
"""Pullblox / Pushmo MSBT translation helper.

Standard-library-only tool for this game's MsgStdBn files.
- Export five official languages side-by-side to UTF-8-SIG CSV.
- Represent MSBT inline control codes losslessly as visible tokens.
- Inject the Turkish column into the English MSBT template.
- Validate labels, control-code structure, encoding, and output round-trip.
- Optionally calculate CFNT glyph widths for text fit reports.

This script intentionally edits TXT2 only. All other MSBT sections remain byte-for-byte
from the source template.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

TAG_RE = re.compile(r"⟦(?:TAG:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]*|END:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4})⟧")
TOKEN_RE = re.compile(r"⟦(TAG|END):([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})(?::([0-9A-Fa-f]*))?⟧")

@dataclass
class Section:
    magic: str
    start: int
    data_start: int
    size: int
    aligned_end: int
    header_tail: bytes
    raw_full: bytes
    pad_byte: int

@dataclass
class MSBT:
    path: Path
    data: bytes
    endian: str
    encoding: int
    sections: List[Section]
    labels_by_index: List[str]
    texts_raw: List[bytes]


def u16(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + 'H', data, off)[0]

def u32(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + 'I', data, off)[0]

def p16(v: int, endian: str) -> bytes:
    return struct.pack(endian + 'H', v)

def p32(v: int, endian: str) -> bytes:
    return struct.pack(endian + 'I', v)


def parse_msbt(path: Path) -> MSBT:
    data = path.read_bytes()
    if len(data) < 0x20 or data[:8] != b'MsgStdBn':
        raise ValueError(f'{path}: not an MSBT / MsgStdBn file')
    bom = data[8:10]
    if bom == b'\xff\xfe':
        endian = '<'
    elif bom == b'\xfe\xff':
        endian = '>'
    else:
        raise ValueError(f'{path}: unknown BOM {bom.hex()}')
    encoding = data[0x0C]
    if encoding not in (0, 1):
        raise ValueError(f'{path}: unsupported MSBT encoding byte {encoding}')
    section_count = u16(data, 0x0E, endian)
    header_size = 0x20
    pos = header_size
    sections: List[Section] = []
    for _ in range(section_count):
        if pos + 0x10 > len(data):
            raise ValueError(f'{path}: truncated section header at {pos:#x}')
        magic_b = data[pos:pos+4]
        try:
            magic = magic_b.decode('ascii')
        except Exception:
            raise ValueError(f'{path}: invalid section magic {magic_b!r} at {pos:#x}')
        size = u32(data, pos + 4, endian)
        end = pos + 0x10 + size
        aligned_end = (end + 0x0F) & ~0x0F
        if end > len(data) or aligned_end > len(data):
            # final file sometimes can end exactly at unaligned section; tolerate only if actual file ends there
            if end == len(data):
                aligned_end = end
            else:
                raise ValueError(f'{path}: invalid section size for {magic}')
        pad = data[end:aligned_end]
        pad_byte = pad[0] if pad else 0xAB
        sections.append(Section(magic, pos, pos+0x10, size, aligned_end,
                                data[pos+8:pos+16], data[pos:aligned_end], pad_byte))
        pos = aligned_end
    if pos != len(data):
        raise ValueError(f'{path}: parsed length {pos:#x} != file length {len(data):#x}')

    smap = {s.magic: s for s in sections}
    if 'LBL1' not in smap or 'TXT2' not in smap:
        raise ValueError(f'{path}: LBL1/TXT2 missing')

    # TXT2 first, to know number of message slots.
    txt = smap['TXT2']
    count = u32(data, txt.data_start, endian)
    if count > 100000:
        raise ValueError(f'{path}: unreasonable TXT2 count {count}')
    offsets = [u32(data, txt.data_start + 4 + i*4, endian) for i in range(count)]
    if offsets and offsets[0] < 4 + 4*count:
        raise ValueError(f'{path}: TXT2 offset table overlaps data')
    texts_raw: List[bytes] = []
    for i, off in enumerate(offsets):
        nxt = offsets[i+1] if i+1 < count else txt.size
        if off > nxt or nxt > txt.size:
            raise ValueError(f'{path}: invalid TXT2 offsets at {i}')
        raw = data[txt.data_start + off: txt.data_start + nxt]
        texts_raw.append(raw)

    # Labels are hash-bucketed but each has a direct TXT2 index.
    lbl = smap['LBL1']
    groups = u32(data, lbl.data_start, endian)
    labels: List[Optional[str]] = [None] * count
    for g in range(groups):
        ent_count = u32(data, lbl.data_start + 4 + g*8, endian)
        rel = u32(data, lbl.data_start + 8 + g*8, endian)
        q = lbl.data_start + rel
        for _ in range(ent_count):
            if q >= lbl.data_start + lbl.size:
                raise ValueError(f'{path}: LBL1 entry out of bounds')
            n = data[q]
            q += 1
            name = data[q:q+n].decode('ascii')
            q += n
            idx = u32(data, q, endian)
            q += 4
            if idx >= count:
                raise ValueError(f'{path}: label {name} has invalid index {idx}')
            if labels[idx] is not None:
                raise ValueError(f'{path}: duplicate label index {idx}')
            labels[idx] = name
    if any(x is None for x in labels):
        missing = [i for i,x in enumerate(labels) if x is None][:10]
        raise ValueError(f'{path}: missing labels for TXT2 indexes {missing}')

    return MSBT(path, data, endian, encoding, sections, [str(x) for x in labels], texts_raw)


def raw_to_csv_text(raw: bytes, endian: str, encoding: int) -> str:
    """Losslessly serialize a TXT2 message. Inline controls become ⟦TAG...⟧ tokens."""
    if encoding == 0:  # UTF-8 MSBT; not used by Pullblox, handled conservatively
        # For UTF-8 games control parsing differs. Preserve bytes via escaped token if nontrivial.
        if raw.endswith(b'\x00'):
            raw = raw[:-1]
        return raw.decode('utf-8')
    out: List[str] = []
    i = 0
    # Text entries are null-terminated; parsing by structure avoids confusing zeros in control args.
    while i + 2 <= len(raw):
        c = u16(raw, i, endian)
        if c == 0:
            # A true terminator should be at the message boundary.
            break
        if c == 0x000E:
            if i + 8 > len(raw):
                raise ValueError('truncated 0x000E tag')
            group = u16(raw, i+2, endian)
            typ = u16(raw, i+4, endian)
            arg_len = u16(raw, i+6, endian)
            if i + 8 + arg_len > len(raw):
                raise ValueError('truncated 0x000E tag args')
            args = raw[i+8:i+8+arg_len]
            out.append(f'⟦TAG:{group:04X}:{typ:04X}:{args.hex().upper()}⟧')
            i += 8 + arg_len
        elif c == 0x000F:
            if i + 6 > len(raw):
                raise ValueError('truncated 0x000F tag')
            group = u16(raw, i+2, endian)
            typ = u16(raw, i+4, endian)
            out.append(f'⟦END:{group:04X}:{typ:04X}⟧')
            i += 6
        else:
            # Decode one UTF-16 code unit or surrogate pair.
            if 0xD800 <= c <= 0xDBFF and i + 4 <= len(raw):
                c2 = u16(raw, i+2, endian)
                if 0xDC00 <= c2 <= 0xDFFF:
                    bs = raw[i:i+4]
                    i += 4
                else:
                    bs = raw[i:i+2]
                    i += 2
            else:
                bs = raw[i:i+2]
                i += 2
            out.append(bs.decode('utf-16le' if endian == '<' else 'utf-16be'))
    return ''.join(out)


def csv_text_to_raw(text: str, endian: str, encoding: int) -> bytes:
    if encoding == 0:
        return text.encode('utf-8') + b'\x00'
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(text):
        plain = text[pos:m.start()]
        if '\x0e' in plain.lower() or '\x0f' in plain.lower():
            raise ValueError('literal control characters are not allowed in plain text')
        out += plain.encode('utf-16le' if endian == '<' else 'utf-16be')
        kind, gs, ts, args = m.group(1), m.group(2), m.group(3), m.group(4)
        group, typ = int(gs,16), int(ts,16)
        if kind == 'TAG':
            argb = bytes.fromhex(args or '')
            out += p16(0x000E,endian) + p16(group,endian) + p16(typ,endian) + p16(len(argb),endian) + argb
        else:
            out += p16(0x000F,endian) + p16(group,endian) + p16(typ,endian)
        pos = m.end()
    tail = text[pos:]
    out += tail.encode('utf-16le' if endian == '<' else 'utf-16be')
    out += p16(0, endian)
    return bytes(out)


def control_signature(text: str) -> List[Tuple[str,str,str,str]]:
    return [(m.group(1), m.group(2).upper(), m.group(3).upper(), (m.group(4) or '').upper()) for m in TOKEN_RE.finditer(text)]


def visible_text(text: str) -> str:
    return TAG_RE.sub('', text)


def build_msbt(template: MSBT, new_texts: List[str]) -> bytes:
    if len(new_texts) != len(template.texts_raw):
        raise ValueError('message count mismatch')
    raw_texts = [csv_text_to_raw(t, template.endian, template.encoding) for t in new_texts]
    count = len(raw_texts)
    table_len = 4 + 4*count
    offsets = []
    running = table_len
    for raw in raw_texts:
        offsets.append(running)
        running += len(raw)
    txt_data = bytearray()
    txt_data += p32(count, template.endian)
    for off in offsets:
        txt_data += p32(off, template.endian)
    for raw in raw_texts:
        txt_data += raw

    out = bytearray(template.data[:0x20])
    for sec in template.sections:
        if sec.magic != 'TXT2':
            out += sec.raw_full
            continue
        sec_bytes = bytearray()
        sec_bytes += b'TXT2'
        sec_bytes += p32(len(txt_data), template.endian)
        sec_bytes += sec.header_tail
        sec_bytes += txt_data
        pad_len = (-len(sec_bytes)) % 16
        sec_bytes += bytes([sec.pad_byte]) * pad_len
        out += sec_bytes
    # File size field at 0x12.
    out[0x12:0x16] = p32(len(out), template.endian)
    return bytes(out)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def roundtrip_self_test(msbt: MSBT) -> None:
    texts = [raw_to_csv_text(r, msbt.endian, msbt.encoding) for r in msbt.texts_raw]
    rebuilt = build_msbt(msbt, texts)
    if rebuilt != msbt.data:
        # locate first differing offset to make failure actionable
        lim = min(len(rebuilt), len(msbt.data))
        diff = next((i for i in range(lim) if rebuilt[i] != msbt.data[i]), lim)
        raise AssertionError(f'round-trip mismatch for {msbt.path}; first diff {diff:#x}; old/new sizes {len(msbt.data)}/{len(rebuilt)}')


def lz11_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x11:
        raise ValueError('not Nintendo LZ11')
    size = data[1] | (data[2] << 8) | (data[3] << 16)
    pos = 4
    if size == 0:
        size = int.from_bytes(data[4:8], 'little')
        pos = 8
    out = bytearray()
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not (flags & (1 << bit)):
                out.append(data[pos]); pos += 1
                continue
            b1, b2 = data[pos], data[pos+1]
            hi = b1 >> 4
            if hi == 0:
                b3 = data[pos+2]; pos += 3
                length = (((b1 & 0x0F) << 4) | (b2 >> 4)) + 0x11
                disp = (((b2 & 0x0F) << 8) | b3) + 1
            elif hi == 1:
                b3, b4 = data[pos+2], data[pos+3]; pos += 4
                length = (((b1 & 0x0F) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                disp = (((b3 & 0x0F) << 8) | b4) + 1
            else:
                pos += 2
                length = hi + 1
                disp = (((b1 & 0x0F) << 8) | b2) + 1
            if disp > len(out):
                raise ValueError('invalid LZ11 back-reference')
            for _ in range(length):
                out.append(out[-disp])
                if len(out) >= size:
                    break
    return bytes(out)


class CFNTMetrics:
    """Minimal NintendoWare CFNT/FFNT metric reader (CMAP + CWDH only)."""
    def __init__(self, data: bytes):
        magic = data[:4]
        if magic not in (b'CFNT', b'FFNT'):
            raise ValueError('not CFNT/FFNT')
        self.magic = magic
        bom = data[4:6]
        self.endian = '<' if bom == b'\xff\xfe' else '>' if bom == b'\xfe\xff' else None
        if self.endian is None:
            raise ValueError('unknown CFNT BOM')
        self.data = data
        # FINF is the first block in this font. Find robustly in header-sized region.
        finf = data.find(b'FINF', 0x14, 0x100)
        if finf < 0:
            raise ValueError('FINF not found')
        e = self.endian
        if self.magic == b'FFNT':
            # Newer NW4C FINF: height/width/ascent precede linefeed and
            # default width triplet. TGLP/CWDH/CMAP pointers are shifted by 4.
            self.default_char_width = data[finf+0x12]
            cwdh_ptr = u32(data, finf+0x18, e)
            cmap_ptr = u32(data, finf+0x1C, e)
        else:
            self.default_char_width = data[finf+0x0E]
            cwdh_ptr = u32(data, finf+0x14, e)
            cmap_ptr = u32(data, finf+0x18, e)
        # NintendoWare pointers target block data at +8.
        self.width_by_glyph: Dict[int,int] = {}
        seen = set()
        ptr = cwdh_ptr
        while ptr and ptr not in seen:
            seen.add(ptr)
            off = ptr - 8
            if data[off:off+4] != b'CWDH':
                raise ValueError(f'bad CWDH pointer {ptr:#x}')
            start = u16(data, off+8, e); end = u16(data, off+10, e)
            nxt = u32(data, off+12, e)
            q = off + 0x10
            for gi in range(start, end+1):
                left = struct.unpack_from('b', data, q)[0]
                glyphw = data[q+1]
                charw = data[q+2]
                self.width_by_glyph[gi] = charw
                q += 3
            ptr = nxt
        self.glyph_by_code: Dict[int,int] = {}
        seen.clear(); ptr = cmap_ptr
        while ptr and ptr not in seen:
            seen.add(ptr)
            off = ptr - 8
            if data[off:off+4] != b'CMAP':
                raise ValueError(f'bad CMAP pointer {ptr:#x}')
            begin = u16(data, off+8, e); end = u16(data, off+10, e)
            method = u16(data, off+12, e)
            nxt = u32(data, off+16, e)
            q = off + 0x14
            if method == 0:
                idx0 = u16(data, q, e)
                for code in range(begin, end+1):
                    self.glyph_by_code[code] = idx0 + (code - begin)
            elif method == 1:
                for code in range(begin, end+1):
                    gi = u16(data, q, e); q += 2
                    if gi != 0xFFFF:
                        self.glyph_by_code[code] = gi
            elif method == 2:
                n = u16(data, q, e); q += 2
                for _ in range(n):
                    code = u16(data, q, e); gi = u16(data, q+2, e); q += 4
                    self.glyph_by_code[code] = gi
            else:
                raise ValueError(f'unknown CMAP method {method}')
            ptr = nxt

    def char_width(self, ch: str) -> int:
        code = ord(ch)
        gi = self.glyph_by_code.get(code)
        if gi is None:
            # Nintendo 3DS system symbols U+E000..U+E07E are rendered by the
            # system/fallback font in Fallblox, not Kurokane.cfnt. Their exact
            # advance is therefore not present in this CFNT. Use a conservative
            # 32 px advance for fit checks instead of the game's 26 px default.
            if 0xE000 <= code <= 0xE07E:
                return max(self.default_char_width, 32)
            return self.default_char_width
        return self.width_by_glyph.get(gi, self.default_char_width)

    def line_width(self, s: str) -> int:
        return sum(self.char_width(ch) for ch in s)

    def text_stats(self, tokenized: str) -> Tuple[int,int,int]:
        s = visible_text(tokenized)
        lines = s.split('\n')
        widths = [self.line_width(line) for line in lines] or [0]
        return len(lines), max(widths), sum(widths)


def load_metrics(font_lz: Optional[Path]) -> Optional[CFNTMetrics]:
    if not font_lz:
        return None
    data = font_lz.read_bytes()
    if data[:1] == b'\x11':
        data = lz11_decompress(data)
    return CFNTMetrics(data)


def official_paths(root: Path) -> Dict[str, Path]:
    return {
        'English': root/'EURen/msg/orca.msbt',
        'German': root/'EURde/msg/orca.msbt',
        'Spanish': root/'EURes/msg/orca.msbt',
        'French': root/'EURfr/msg/orca.msbt',
        'Italian': root/'EURit/msg/orca.msbt',
    }


def export_csv(root: Path, out_csv: Path, font_lz: Optional[Path] = None, existing_turkish: Optional[Path] = None) -> None:
    paths = official_paths(root)
    lang_msbt = {k: parse_msbt(v) for k,v in paths.items()}
    for m in lang_msbt.values():
        roundtrip_self_test(m)
    eng = lang_msbt['English']
    for lang,m in lang_msbt.items():
        if m.labels_by_index != eng.labels_by_index:
            raise ValueError(f'{lang}: label/index layout differs from English')
    decoded = {lang: [raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw] for lang,m in lang_msbt.items()}
    old_tr: Dict[str,dict] = {}
    if existing_turkish and existing_turkish.exists():
        with existing_turkish.open('r',encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f): old_tr[row['label']] = row
    metrics = load_metrics(font_lz)
    fields = ['index','label','English','German','Spanish','French','Italian','Turkish',
              'official_max_lines','official_max_px','turkish_lines','turkish_max_px','fit_ratio','fit_status',
              'control_status','translation_status','translator_note']
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for i,label in enumerate(eng.labels_by_index):
            official = [decoded[l][i] for l in ('English','German','Spanish','French','Italian')]
            trrow = old_tr.get(label,{})
            tr = trrow.get('Turkish','')
            if metrics:
                stats=[metrics.text_stats(t) for t in official]
                max_lines=max(x[0] for x in stats); max_px=max(x[1] for x in stats)
                if tr:
                    tl,tp,_=metrics.text_stats(tr); ratio=(tp/max_px if max_px else 1.0)
                    fit='OK' if tl<=max_lines and ratio<=1.05 else ('REVIEW' if tl<=max_lines+1 and ratio<=1.20 else 'RISK')
                else: tl=tp=0; ratio=0.0; fit='EMPTY'
            else:
                max_lines=max((visible_text(t).count('\n')+1 for t in official), default=0)
                max_px=0; tl=(visible_text(tr).count('\n')+1 if tr else 0); tp=0; ratio=0; fit='N/A'
            cs='OK' if (not tr or control_signature(tr)==control_signature(decoded['English'][i])) else 'MISMATCH'
            w.writerow({
                'index':i,'label':label,
                **{l:decoded[l][i] for l in decoded},
                'Turkish':tr,
                'official_max_lines':max_lines,'official_max_px':max_px,
                'turkish_lines':tl,'turkish_max_px':tp,'fit_ratio':f'{ratio:.3f}',
                'fit_status':fit,'control_status':cs,
                'translation_status':trrow.get('translation_status','EMPTY' if not tr else 'DRAFT'),
                'translator_note':trrow.get('translator_note',''),
            })
    print(f'Exported {len(eng.labels_by_index)} rows -> {out_csv}')


def inject_csv(template_path: Path, csv_path: Path, out_msbt: Path, strict: bool=True) -> None:
    m = parse_msbt(template_path)
    roundtrip_self_test(m)
    source = [raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw]
    by_label={}
    with csv_path.open('r',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f): by_label[row['label']] = row
    new=[]; problems=[]
    for i,label in enumerate(m.labels_by_index):
        row=by_label.get(label)
        if row is None:
            problems.append(f'{label}: missing CSV row'); new.append(source[i]); continue
        tr=row.get('Turkish','')
        # Empty source strings should remain empty. Empty Turkish on non-empty source falls back to English unless strict.
        if not visible_text(source[i]):
            tr = source[i]
        elif not tr:
            if strict: problems.append(f'{label}: Turkish is empty')
            tr = source[i]
        if control_signature(tr) != control_signature(source[i]):
            problems.append(f'{label}: control sequence mismatch')
        try:
            csv_text_to_raw(tr,m.endian,m.encoding)
        except Exception as e:
            problems.append(f'{label}: cannot encode Turkish: {e}')
        new.append(tr)
    if problems and strict:
        raise ValueError('Injection blocked:\n  ' + '\n  '.join(problems[:100]) + ('\n  ...' if len(problems)>100 else ''))
    data=build_msbt(m,new)
    out_msbt.parent.mkdir(parents=True,exist_ok=True); out_msbt.write_bytes(data)
    # Reparse built file and verify all injected text exactly round-trips.
    check=parse_msbt(out_msbt)
    got=[raw_to_csv_text(r,check.endian,check.encoding) for r in check.texts_raw]
    if got != new:
        raise AssertionError('post-build text verification failed')
    if check.labels_by_index != m.labels_by_index:
        raise AssertionError('post-build label verification failed')
    print(f'Injected {len(new)} entries -> {out_msbt} SHA256={sha256(data)}')
    if problems:
        print(f'WARNING: built non-strict with {len(problems)} issue(s)', file=sys.stderr)


def validate_csv(root: Path, csv_path: Path, font_lz: Optional[Path]=None) -> dict:
    eng=parse_msbt(root/'EURen/msg/orca.msbt'); roundtrip_self_test(eng)
    source=[raw_to_csv_text(r,eng.endian,eng.encoding) for r in eng.texts_raw]
    metrics=load_metrics(font_lz)
    rows={}
    with csv_path.open('r',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f): rows[row['label']]=row
    counts={'total':len(source),'source_nonempty':0,'translated_nonempty':0,'empty_missing':0,'control_mismatch':0,'encoding_error':0,'fit_review':0,'fit_risk':0,'two_line_overflow':0,'source_2line_to_3plus':0,'unknown_glyph':0}
    issues=[]
    official_dec=None
    if metrics:
        langs={k:parse_msbt(v) for k,v in official_paths(root).items()}
        official_dec={k:[raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw] for k,m in langs.items()}
    required_tr_chars=set()
    source_chars=set(ch for src in source for ch in visible_text(src) if ch not in '\n\r\t')
    for i,label in enumerate(eng.labels_by_index):
        src=source[i]; row=rows.get(label,{}); tr=row.get('Turkish','')
        if visible_text(src): counts['source_nonempty']+=1
        if tr: counts['translated_nonempty']+=1
        elif visible_text(src): counts['empty_missing']+=1; issues.append((label,'EMPTY','Turkish translation missing'))
        if tr and control_signature(tr)!=control_signature(src): counts['control_mismatch']+=1; issues.append((label,'CONTROL','control token sequence differs from English source'))
        if tr:
            try: csv_text_to_raw(tr,eng.endian,eng.encoding)
            except Exception as e: counts['encoding_error']+=1; issues.append((label,'ENCODING',str(e)))
            required_tr_chars.update(ch for ch in visible_text(tr) if ch not in '\n\r\t')
        if metrics and tr:
            official=[official_dec[k][i] for k in official_dec]
            ostats=[metrics.text_stats(t) for t in official]
            max_lines=max(x[0] for x in ostats); max_px=max(x[1] for x in ostats)
            tl,tp,_=metrics.text_stats(tr); ratio=tp/max_px if max_px else 1.0
            # Overflow guards learned from device testing: a box whose shipped languages use
            # at most two lines must never gain a third Turkish line, and its widest Turkish
            # line must not exceed the widest shipped-language line for that message.
            src_lines=metrics.text_stats(src)[0]
            if max_lines == 2 and (tl > 2 or tp > max_px):
                counts['two_line_overflow'] += 1
                issues.append((label,'TWO_LINE_OVERFLOW',f'{tl} lines/{tp}px vs 2-line shipped max {max_px}px'))
            if src_lines <= 2 and tl > 2:
                counts['source_2line_to_3plus'] += 1
                issues.append((label,'SOURCE_2LINE_TO_3PLUS',f'English {src_lines} line(s), Turkish {tl} lines'))
            if tl>max_lines+1 or ratio>1.20:
                counts['fit_risk']+=1; issues.append((label,'FIT_RISK',f'{tl} lines/{tp}px vs official max {max_lines} lines/{max_px}px ratio={ratio:.2f}'))
            elif tl>max_lines or ratio>1.05:
                counts['fit_review']+=1; issues.append((label,'FIT_REVIEW',f'{tl} lines/{tp}px vs official max {max_lines} lines/{max_px}px ratio={ratio:.2f}'))
    if metrics:
        # Private-use/icon characters already present in the shipped English source are not
        # new Turkish glyph requirements; the game renders those through its existing icon path.
        missing=sorted(ch for ch in required_tr_chars if ord(ch) not in metrics.glyph_by_code and ch not in source_chars)
        counts['unknown_glyph']=len(missing)
        if missing: issues.append(('*','GLYPH','missing glyphs: '+''.join(missing)))
    report={'counts':counts,'issues':[{'label':a,'kind':b,'detail':c} for a,b,c in issues]}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def main():
    ap=argparse.ArgumentParser(description='Pullblox MSBT Turkish translation helper')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('export'); p.add_argument('--romfs',type=Path,required=True); p.add_argument('--csv',type=Path,required=True); p.add_argument('--font',type=Path); p.add_argument('--merge',type=Path)
    p=sp.add_parser('inject'); p.add_argument('--template',type=Path,required=True); p.add_argument('--csv',type=Path,required=True); p.add_argument('--out',type=Path,required=True); p.add_argument('--non-strict',action='store_true')
    p=sp.add_parser('validate'); p.add_argument('--romfs',type=Path,required=True); p.add_argument('--csv',type=Path,required=True); p.add_argument('--font',type=Path); p.add_argument('--json',type=Path)
    a=ap.parse_args()
    if a.cmd=='export': export_csv(a.romfs,a.csv,a.font,a.merge)
    elif a.cmd=='inject': inject_csv(a.template,a.csv,a.out,strict=not a.non_strict)
    elif a.cmd=='validate':
        rep=validate_csv(a.romfs,a.csv,a.font)
        if a.json: a.json.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__': main()
