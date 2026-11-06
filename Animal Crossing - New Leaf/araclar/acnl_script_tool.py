#!/usr/bin/env python3
"""
ACNL Script UMSBT CSV exporter/injector

Designed for the Animal Crossing: New Leaf EU Script folder layout observed in
Script.zip: every .umsbt contains five little-endian MSBT files in this order:
EN, ES, FR, IT, DE.

No third-party dependencies.
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
from typing import Dict, List, Optional, Sequence, Tuple

LANGS = ["EN", "ES", "FR", "IT", "DE"]
TAG_RE = re.compile(r"\{\{TAG:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4}):([0-9A-Fa-f]*)\}\}")
END_RE = re.compile(r"\{\{END:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})\}\}")
EMPTY_TOKEN = "{{EMPTY}}"


class FormatError(Exception):
    pass


def u16(b: bytes, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]


def u32(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]


def p16(v: int) -> bytes:
    return struct.pack("<H", v)


def p32(v: int) -> bytes:
    return struct.pack("<I", v)


def align16(n: int) -> int:
    return (n + 15) & ~15


@dataclass
class Section:
    magic: bytes
    payload: bytes
    header_reserved: bytes


@dataclass
class ParsedMSBT:
    original: bytes
    encoding: int
    sections: List[Section]
    labels: Dict[int, str]
    strings_raw: List[bytes]


def parse_umsbt(data: bytes) -> List[bytes]:
    pairs: List[Tuple[int, int]] = []
    off = 0
    while off + 8 <= len(data):
        sub_off, sub_size = struct.unpack_from("<II", data, off)
        off += 8
        if sub_off == 0 or sub_size == 0:
            break
        if sub_off + sub_size > len(data):
            raise FormatError(f"UMSBT alt dosyası sınır dışında: off={sub_off:#x}, size={sub_size:#x}")
        chunk = data[sub_off:sub_off + sub_size]
        if not chunk.startswith(b"MsgStdBn"):
            raise FormatError(f"UMSBT içinde MsgStdBn bulunamadı: {sub_off:#x}")
        pairs.append((sub_off, sub_size))
    if not pairs:
        raise FormatError("Geçerli UMSBT tablo girdisi bulunamadı")
    return [data[o:o+s] for o, s in pairs]


def pack_umsbt(msbts: Sequence[bytes]) -> bytes:
    # table = N offset/size pairs + terminating zero pair; align the first MSBT to 16 bytes
    table_len = (len(msbts) + 1) * 8
    first = align16(table_len)
    out = bytearray(b"\x00" * first)
    pairs: List[Tuple[int, int]] = []
    for m in msbts:
        pos = align16(len(out))
        if pos > len(out):
            out.extend(b"\x00" * (pos - len(out)))
        pairs.append((pos, len(m)))
        out.extend(m)
    for i, (o, s) in enumerate(pairs):
        struct.pack_into("<II", out, i * 8, o, s)
    # terminating pair already zeroed
    return bytes(out)


def parse_sections(msbt: bytes) -> Tuple[int, List[Section]]:
    if len(msbt) < 0x20 or msbt[:8] != b"MsgStdBn":
        raise FormatError("MSBT başlığı geçersiz")
    if msbt[8:10] != b"\xff\xfe":
        raise FormatError("Bu araç şu anda yalnız little-endian MSBT destekliyor")
    encoding = msbt[0x0C]
    section_count = u16(msbt, 0x0E)
    pos = 0x20
    sections: List[Section] = []
    for _ in range(section_count):
        if pos + 16 > len(msbt):
            raise FormatError("MSBT section başlığı eksik")
        magic = msbt[pos:pos+4]
        size = u32(msbt, pos+4)
        reserved = msbt[pos+8:pos+16]
        start = pos + 16
        end = start + size
        if end > len(msbt):
            raise FormatError(f"MSBT section sınır dışında: {magic!r}")
        sections.append(Section(magic=magic, payload=msbt[start:end], header_reserved=reserved))
        pos = align16(end)
    return encoding, sections


def parse_labels(sections: Sequence[Section]) -> Dict[int, str]:
    sec = next((s for s in sections if s.magic == b"LBL1"), None)
    if sec is None:
        return {}
    b = sec.payload
    if len(b) < 4:
        raise FormatError("LBL1 çok kısa")
    groups = u32(b, 0)
    if len(b) < 4 + groups * 8:
        raise FormatError("LBL1 grup tablosu eksik")
    result: Dict[int, str] = {}
    for i in range(groups):
        count, rel = struct.unpack_from("<II", b, 4 + i*8)
        q = rel
        for _ in range(count):
            if q >= len(b):
                raise FormatError("LBL1 label sınır dışında")
            ln = b[q]
            q += 1
            if q + ln + 4 > len(b):
                raise FormatError("LBL1 label verisi eksik")
            name = b[q:q+ln].decode("ascii", errors="replace")
            q += ln
            idx = u32(b, q)
            q += 4
            result[idx] = name
    return result


def parse_txt2_strings(sections: Sequence[Section], encoding: int) -> List[bytes]:
    sec = next((s for s in sections if s.magic == b"TXT2"), None)
    if sec is None:
        raise FormatError("TXT2 section bulunamadı")
    b = sec.payload
    if len(b) < 4:
        raise FormatError("TXT2 çok kısa")
    count = u32(b, 0)
    if len(b) < 4 + count*4:
        raise FormatError("TXT2 offset tablosu eksik")
    offsets = [u32(b, 4 + i*4) for i in range(count)]
    strings: List[bytes] = []
    for i, rel in enumerate(offsets):
        if rel >= len(b):
            raise FormatError("TXT2 string offset sınır dışında")
        # Use the next offset as a hard upper bound. This avoids accidentally treating
        # binary zero bytes inside control-tag parameters as terminators.
        hard_end = offsets[i+1] if i+1 < count else len(b)
        if hard_end < rel or hard_end > len(b):
            raise FormatError("TXT2 offset sırası geçersiz")
        raw = b[rel:hard_end]
        strings.append(trim_string_terminator(raw, encoding))
    return strings


def trim_string_terminator(raw: bytes, encoding: int) -> bytes:
    if encoding == 1:  # UTF-16LE
        p = 0
        while p + 2 <= len(raw):
            ch = u16(raw, p)
            if ch == 0:
                return raw[:p]
            if ch == 0x000E:
                if p + 8 > len(raw):
                    raise FormatError("Eksik UTF-16 TAG")
                size = u16(raw, p+6)
                p += 8 + size
            elif ch == 0x000F:
                if p + 6 > len(raw):
                    raise FormatError("Eksik UTF-16 END tag")
                p += 6
            else:
                p += 2
        raise FormatError("UTF-16 string terminator bulunamadı")
    elif encoding == 0:  # nominal UTF-8; ACNL ASR files are effectively single-byte Western text
        p = 0
        while p < len(raw):
            ch = raw[p]
            if ch == 0:
                return raw[:p]
            if ch == 0x0E:
                if p + 7 > len(raw):
                    raise FormatError("Eksik 8-bit TAG")
                size = u16(raw, p+5)
                p += 7 + size
            elif ch == 0x0F:
                if p + 5 > len(raw):
                    raise FormatError("Eksik 8-bit END tag")
                p += 5
            else:
                p += 1
        raise FormatError("8-bit string terminator bulunamadı")
    else:
        raise FormatError(f"Desteklenmeyen MSBT encoding: {encoding}")


def parse_msbt(msbt: bytes) -> ParsedMSBT:
    encoding, sections = parse_sections(msbt)
    labels = parse_labels(sections)
    strings = parse_txt2_strings(sections, encoding)
    return ParsedMSBT(msbt, encoding, sections, labels, strings)


def raw_to_text(raw: bytes, encoding: int, single_byte_codec: str = "cp1252") -> str:
    out: List[str] = []
    if encoding == 1:
        p = 0
        textbuf = bytearray()
        def flush() -> None:
            if textbuf:
                out.append(bytes(textbuf).decode("utf-16le", errors="surrogatepass"))
                textbuf.clear()
        while p < len(raw):
            if p + 2 > len(raw):
                raise FormatError("Tek UTF-16 byte kaldı")
            ch = u16(raw, p)
            if ch == 0x000E:
                flush()
                if p + 8 > len(raw): raise FormatError("Eksik TAG")
                group, typ, size = struct.unpack_from("<HHH", raw, p+2)
                end = p + 8 + size
                if end > len(raw): raise FormatError("TAG parametresi eksik")
                params = raw[p+8:end]
                out.append(f"{{{{TAG:{group:04X}:{typ:04X}:{params.hex().upper()}}}}}")
                p = end
            elif ch == 0x000F:
                flush()
                if p + 6 > len(raw): raise FormatError("Eksik END")
                group, typ = struct.unpack_from("<HH", raw, p+2)
                out.append(f"{{{{END:{group:04X}:{typ:04X}}}}}")
                p += 6
            else:
                textbuf.extend(raw[p:p+2])
                p += 2
        flush()
    elif encoding == 0:
        p = 0
        textbuf = bytearray()
        def flush8() -> None:
            if textbuf:
                out.append(bytes(textbuf).decode(single_byte_codec, errors="replace"))
                textbuf.clear()
        while p < len(raw):
            ch = raw[p]
            if ch == 0x0E:
                flush8()
                if p + 7 > len(raw): raise FormatError("Eksik 8-bit TAG")
                group, typ, size = struct.unpack_from("<HHH", raw, p+1)
                end = p + 7 + size
                if end > len(raw): raise FormatError("8-bit TAG parametresi eksik")
                params = raw[p+7:end]
                out.append(f"{{{{TAG:{group:04X}:{typ:04X}:{params.hex().upper()}}}}}")
                p = end
            elif ch == 0x0F:
                flush8()
                if p + 5 > len(raw): raise FormatError("Eksik 8-bit END")
                group, typ = struct.unpack_from("<HH", raw, p+1)
                out.append(f"{{{{END:{group:04X}:{typ:04X}}}}}")
                p += 5
            else:
                textbuf.append(ch)
                p += 1
        flush8()
    else:
        raise FormatError(f"Desteklenmeyen encoding {encoding}")
    return "".join(out)


def text_to_raw(text: str, encoding: int, single_byte_codec: str = "cp1252") -> bytes:
    if text == EMPTY_TOKEN:
        return b""
    out = bytearray()
    pos = 0
    while pos < len(text):
        m1 = TAG_RE.search(text, pos)
        m2 = END_RE.search(text, pos)
        matches = [m for m in (m1, m2) if m is not None]
        m = min(matches, key=lambda x: x.start()) if matches else None
        end_plain = m.start() if m else len(text)
        plain = text[pos:end_plain]
        if "{{TAG:" in plain or "{{END:" in plain:
            raise FormatError("Bozuk kontrol tag tokeni var. {{TAG:....}} / {{END:....}} biçimini değiştirmeyin.")
        try:
            if encoding == 1:
                out.extend(plain.encode("utf-16le", errors="surrogatepass"))
            elif encoding == 0:
                out.extend(plain.encode(single_byte_codec, errors="strict"))
            else:
                raise FormatError(f"Desteklenmeyen encoding {encoding}")
        except UnicodeEncodeError as e:
            raise FormatError(
                f"Metin {single_byte_codec} ile kodlanamıyor ({e}). "
                "Bu genelde *_ASR.umsbt dosyalarında olur; TRANSLATION alanını boş bırakabilir veya yalnız desteklenen karakterleri kullanabilirsin."
            ) from e
        if not m:
            break
        if m.re is TAG_RE:
            group = int(m.group(1), 16)
            typ = int(m.group(2), 16)
            params_hex = m.group(3)
            if len(params_hex) % 2:
                raise FormatError("TAG hex parametresi çift uzunlukta olmalı")
            params = bytes.fromhex(params_hex)
            if len(params) > 0xFFFF:
                raise FormatError("TAG parametresi çok uzun")
            if encoding == 1:
                out.extend(p16(0x000E) + p16(group) + p16(typ) + p16(len(params)) + params)
            else:
                out.extend(b"\x0E" + p16(group) + p16(typ) + p16(len(params)) + params)
        else:
            group = int(m.group(1), 16)
            typ = int(m.group(2), 16)
            if encoding == 1:
                out.extend(p16(0x000F) + p16(group) + p16(typ))
            else:
                out.extend(b"\x0F" + p16(group) + p16(typ))
        pos = m.end()
    return bytes(out)


def build_txt2_payload(strings_raw: Sequence[bytes], encoding: int) -> bytes:
    count = len(strings_raw)
    header_len = 4 + 4*count
    out = bytearray(p32(count) + b"\x00"*(4*count))
    offsets: List[int] = []
    term = b"\x00\x00" if encoding == 1 else b"\x00"
    for raw in strings_raw:
        offsets.append(len(out))
        out.extend(raw)
        out.extend(term)
    for i, rel in enumerate(offsets):
        struct.pack_into("<I", out, 4 + i*4, rel)
    return bytes(out)


def rebuild_msbt(parsed: ParsedMSBT, new_strings_raw: Sequence[bytes], encoding_override: Optional[int] = None) -> bytes:
    encoding = parsed.encoding if encoding_override is None else encoding_override
    out = bytearray(parsed.original[:0x20])
    out[0x0C] = encoding
    found = False
    for sec in parsed.sections:
        payload = sec.payload
        if sec.magic == b"TXT2":
            payload = build_txt2_payload(new_strings_raw, encoding)
            found = True
        out.extend(sec.magic)
        out.extend(p32(len(payload)))
        out.extend(sec.header_reserved)
        out.extend(payload)
        pad = align16(len(out)) - len(out)
        if pad:
            out.extend(b"\xAB" * pad)
    if not found:
        raise FormatError("TXT2 yok")
    # File size is stored at offset 0x12 for MsgStdBn v3.
    struct.pack_into("<I", out, 0x12, len(out))
    return bytes(out)


def promote_strings_to_utf16(pm: ParsedMSBT, codec: str) -> List[bytes]:
    """Convert every string in an 8-bit ACNL MSBT to UTF-16LE, preserving control tags."""
    if pm.encoding == 1:
        return list(pm.strings_raw)
    if pm.encoding != 0:
        raise FormatError(f"UTF-16 dönüşümü desteklenmeyen encoding: {pm.encoding}")
    out: List[bytes] = []
    for raw in pm.strings_raw:
        text = raw_to_text(raw, 0, codec)
        out.append(text_to_raw(text, 1, codec))
    return out


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def iter_umsbt(root: Path):
    yield from sorted(root.rglob("*.umsbt"), key=lambda p: p.as_posix().lower())


def export_csv_dir(script_dir: Path, csv_dir: Path, codec: str) -> None:
    files = list(iter_umsbt(script_dir))
    if not files:
        raise FormatError("Klasörde .umsbt bulunamadı")
    if csv_dir.exists() and csv_dir.is_file():
        raise FormatError(f"Çıktı bir klasör olmalı, dosya değil: {csv_dir}")
    csv_dir.mkdir(parents=True, exist_ok=True)
    rows = 0
    for p in files:
        rel = p.relative_to(script_dir)
        out_csv = (csv_dir / rel).with_suffix('.csv')
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        chunks = parse_umsbt(p.read_bytes())
        if len(chunks) != 5:
            raise FormatError(f"{rel.as_posix()}: 5 dil yerine {len(chunks)} MSBT bulundu")
        parsed = [parse_msbt(c) for c in chunks]
        counts = {len(x.strings_raw) for x in parsed}
        if len(counts) != 1:
            raise FormatError(f"{rel.as_posix()}: dillerin mesaj sayıları eşleşmiyor")
        count = len(parsed[0].strings_raw)
        with out_csv.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['entry', 'label', *LANGS, 'TRANSLATION'])
            w.writeheader()
            for idx in range(count):
                row = {
                    'entry': str(idx),
                    'label': parsed[0].labels.get(idx, ''),
                    'TRANSLATION': '',
                }
                for lang, pm in zip(LANGS, parsed):
                    row[lang] = raw_to_text(pm.strings_raw[idx], pm.encoding, codec)
                w.writerow(row)
                rows += 1
    print(f"OK: {len(files)} UMSBT -> {len(files)} ayrı CSV, toplam {rows} satır -> {csv_dir}")


def load_translations(source: Path, column: str) -> Dict[Tuple[str, int], str]:
    """Load translations from the new per-file CSV directory or legacy single CSV."""
    if source.is_file():
        # Legacy single-CSV compatibility.
        result: Dict[Tuple[str, int], str] = {}
        with source.open('r', encoding='utf-8-sig', newline='') as f:
            r = csv.DictReader(f)
            required = {'path', 'entry', column}
            missing = required - set(r.fieldnames or [])
            if missing:
                raise FormatError(f"CSV sütunları eksik: {', '.join(sorted(missing))}")
            for line_no, row in enumerate(r, 2):
                path = (row.get('path') or '').strip().replace('\\', '/')
                pp = Path(path)
                if not path or pp.is_absolute() or '..' in pp.parts or pp.suffix.lower() != '.umsbt':
                    raise FormatError(f"CSV satır {line_no}: geçersiz/tehlikeli path: {path!r}")
                try:
                    entry = int(row.get('entry') or '')
                except ValueError:
                    raise FormatError(f"CSV satır {line_no}: entry sayı değil")
                text = row.get(column, '')
                if text != '':
                    result[(path, entry)] = text
        return result

    if not source.is_dir():
        raise FormatError(f"CSV klasörü bulunamadı: {source}")

    csv_files = sorted(source.rglob('*.csv'), key=lambda p: p.as_posix().lower())
    if not csv_files:
        raise FormatError(f"CSV klasöründe .csv bulunamadı: {source}")

    result: Dict[Tuple[str, int], str] = {}
    for csv_path in csv_files:
        rel_csv = csv_path.relative_to(source)
        rel_umsbt = rel_csv.with_suffix('.umsbt').as_posix()
        if '..' in Path(rel_umsbt).parts:
            raise FormatError(f"Geçersiz CSV yolu: {rel_csv.as_posix()}")
        with csv_path.open('r', encoding='utf-8-sig', newline='') as f:
            r = csv.DictReader(f)
            required = {'entry', column}
            missing = required - set(r.fieldnames or [])
            if missing:
                raise FormatError(f"{rel_csv.as_posix()}: CSV sütunları eksik: {', '.join(sorted(missing))}")
            for line_no, row in enumerate(r, 2):
                try:
                    entry = int(row.get('entry') or '')
                except ValueError:
                    raise FormatError(f"{rel_csv.as_posix()} satır {line_no}: entry sayı değil")
                text = row.get(column, '')
                if text != '':
                    key = (rel_umsbt, entry)
                    if key in result:
                        raise FormatError(f"Aynı mesaj birden fazla kez tanımlanmış: {rel_umsbt}#{entry}")
                    result[key] = text
    return result


def inject(script_dir: Path, csv_source: Path, output_dir: Path, target: str, column: str, codec: str) -> None:
    target = target.upper()
    if target not in LANGS:
        raise FormatError(f"Hedef dil {LANGS} içinden biri olmalı")
    target_idx = LANGS.index(target)
    trans = load_translations(csv_source, column)
    copy_tree(script_dir, output_dir)
    by_path: Dict[str, Dict[int, str]] = {}
    for (path, idx), text in trans.items():
        by_path.setdefault(path, {})[idx] = text

    changed_files = 0
    changed_entries = 0
    promoted_files = 0
    missing_paths: List[str] = []
    for rel, edits in sorted(by_path.items()):
        src_file = script_dir / Path(rel)
        dst_file = output_dir / Path(rel)
        if not src_file.is_file():
            missing_paths.append(rel)
            continue
        chunks = parse_umsbt(src_file.read_bytes())
        if target_idx >= len(chunks):
            raise FormatError(f"{rel}: hedef dil yuvası yok")
        pm = parse_msbt(chunks[target_idx])

        # ACNL's three *_ASR files use an 8-bit Western encoding. If a Turkish
        # translation cannot be represented there, promote the entire target MSBT
        # to UTF-16LE. Nintendo's message format stores the encoding in the MSBT
        # header, so this keeps Turkish code points lossless instead of substituting
        # lookalikes or corrupting bytes.
        target_encoding = pm.encoding
        needs_promotion = False
        if pm.encoding == 0:
            for idx, text in edits.items():
                try:
                    text_to_raw(text, 0, codec)
                except FormatError:
                    needs_promotion = True
                    break
        if needs_promotion:
            strings = promote_strings_to_utf16(pm, codec)
            target_encoding = 1
            promoted_files += 1
        else:
            strings = list(pm.strings_raw)

        file_changed = needs_promotion
        for idx, text in edits.items():
            if idx < 0 or idx >= len(strings):
                raise FormatError(f"{rel}: entry {idx} sınır dışında (0..{len(strings)-1})")
            new_raw = text_to_raw(text, target_encoding, codec)
            if new_raw != strings[idx]:
                strings[idx] = new_raw
                changed_entries += 1
                file_changed = True
        if file_changed:
            chunks[target_idx] = rebuild_msbt(pm, strings, target_encoding)
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            dst_file.write_bytes(pack_umsbt(chunks))
            changed_files += 1

    if missing_paths:
        preview = ', '.join(missing_paths[:5])
        raise FormatError(f"CSV klasöründe olup Script klasöründe bulunmayan {len(missing_paths)} dosya var: {preview}")
    print(f"OK: hedef={target}, değişen dosya={changed_files}, değişen mesaj={changed_entries}, UTF16'ya yükseltilen ASR={promoted_files} -> {output_dir}")

def inspect(script_dir: Path) -> None:
    files = list(iter_umsbt(script_dir))
    if not files:
        raise FormatError(".umsbt bulunamadı")
    wrapper_counts: Dict[int, int] = {}
    entries = 0
    enc_counts: Dict[int, int] = {}
    for p in files:
        chunks = parse_umsbt(p.read_bytes())
        wrapper_counts[len(chunks)] = wrapper_counts.get(len(chunks), 0) + 1
        parsed = [parse_msbt(c) for c in chunks]
        entries += len(parsed[0].strings_raw) if parsed else 0
        for x in parsed:
            enc_counts[x.encoding] = enc_counts.get(x.encoding, 0) + 1
    print(f"UMSBT dosyası : {len(files)}")
    print(f"Wrapper dağılımı: {wrapper_counts}")
    print(f"Hizalı mesaj satırı: {entries}")
    print(f"MSBT encoding: {enc_counts}  (1=UTF-16LE, 0=8-bit/ASR)")
    sample = script_dir / "Bbs" / "BBS_Default.umsbt"
    if sample.is_file():
        chunks = parse_umsbt(sample.read_bytes())
        print("Dil sırası örneği (Bbs/BBS_Default.umsbt):")
        for lang, c in zip(LANGS, chunks):
            pm = parse_msbt(c)
            text = raw_to_text(pm.strings_raw[0], pm.encoding).replace("\n", " / ")
            print(f"  {lang}: {text[:90]}")


def validate_csv(script_dir: Path, csv_source: Path, target: str, column: str, codec: str) -> None:
    target = target.upper()
    if target not in LANGS:
        raise FormatError(f"Hedef dil {LANGS} içinden biri olmalı")
    idxlang = LANGS.index(target)
    trans = load_translations(csv_source, column)
    cache: Dict[str, ParsedMSBT] = {}
    errors: List[str] = []
    promoted: set[str] = set()
    for (rel, idx), text in trans.items():
        try:
            if rel not in cache:
                p = script_dir / Path(rel)
                if not p.is_file(): raise FormatError("dosya bulunamadı")
                chunks = parse_umsbt(p.read_bytes())
                cache[rel] = parse_msbt(chunks[idxlang])
            pm = cache[rel]
            if idx < 0 or idx >= len(pm.strings_raw):
                raise FormatError(f"entry sınır dışında: {idx}")
            try:
                text_to_raw(text, pm.encoding, codec)
            except FormatError:
                if pm.encoding == 0:
                    # Injection will promote this target MSBT to UTF-16LE.
                    text_to_raw(text, 1, codec)
                    promoted.add(rel)
                else:
                    raise
        except Exception as e:
            errors.append(f"{rel}#{idx}: {e}")
            if len(errors) >= 20:
                break
    if errors:
        print("HATA:")
        for e in errors: print(" -", e)
        raise FormatError(f"Doğrulama başarısız ({len(errors)} hata gösterildi)")
    print(f"OK: {len(trans)} çevrilmiş satır doğrulandı; hedef={target}; UTF16'ya yükseltilecek ASR={len(promoted)}")

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Animal Crossing: New Leaf UMSBT CSV export/inject aracı")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("inspect", help="Script klasör yapısını analiz et")
    s.add_argument("script_dir", type=Path)

    s = sub.add_parser("export", help="Her UMSBT için ayrı CSV çıkar")
    s.add_argument("script_dir", type=Path)
    s.add_argument("csv_dir", type=Path, help="CSV klasörü (ör. translations)")
    s.add_argument("--single-byte-codec", default="cp1252")

    s = sub.add_parser("validate", help="TRANSLATION alanlarını enjeksiyon öncesi doğrula")
    s.add_argument("script_dir", type=Path)
    s.add_argument("csv_source", type=Path, help="CSV klasörü (veya eski tek CSV)")
    s.add_argument("--target", default="EN", choices=LANGS)
    s.add_argument("--column", default="TRANSLATION")
    s.add_argument("--single-byte-codec", default="cp1252")

    s = sub.add_parser("inject", help="CSV çevirilerini seçilen dil yuvasına enjekte et")
    s.add_argument("script_dir", type=Path)
    s.add_argument("csv_source", type=Path, help="CSV klasörü (veya eski tek CSV)")
    s.add_argument("output_dir", type=Path)
    s.add_argument("--target", default="EN", choices=LANGS)
    s.add_argument("--column", default="TRANSLATION")
    s.add_argument("--single-byte-codec", default="cp1252")
    return p


def main() -> int:
    try:
        args = build_argparser().parse_args()
        if args.cmd == "inspect": inspect(args.script_dir)
        elif args.cmd == "export": export_csv_dir(args.script_dir, args.csv_dir, args.single_byte_codec)
        elif args.cmd == "validate": validate_csv(args.script_dir, args.csv_source, args.target, args.column, args.single_byte_codec)
        elif args.cmd == "inject": inject(args.script_dir, args.csv_source, args.output_dir, args.target, args.column, args.single_byte_codec)
        return 0
    except (FormatError, OSError, csv.Error) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
