from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import struct
import re


class FormatError(Exception):
    pass


def align_up(n: int, a: int) -> int:
    return (n + a - 1) // a * a


# ---------------- LZ11 ----------------

def lz11_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x11:
        raise FormatError("LZ11 başlığı (0x11) bulunamadı")
    if len(data) < 4:
        raise FormatError("Eksik LZ11 başlığı")
    out_size = data[1] | (data[2] << 8) | (data[3] << 16)
    pos = 4
    if out_size == 0:
        if len(data) < 8:
            raise FormatError("Eksik geniş LZ11 başlığı")
        out_size = struct.unpack_from('<I', data, 4)[0]
        pos = 8
    out = bytearray()
    while len(out) < out_size:
        if pos >= len(data):
            raise FormatError("LZ11 verisi beklenmedik şekilde bitti")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_size:
                break
            if not (flags & (1 << bit)):
                if pos >= len(data):
                    raise FormatError("LZ11 literal eksik")
                out.append(data[pos])
                pos += 1
                continue

            if pos >= len(data):
                raise FormatError("LZ11 eşleşme verisi eksik")
            b1 = data[pos]
            hi = b1 >> 4
            if hi == 0:
                if pos + 2 >= len(data):
                    raise FormatError("LZ11 3-byte eşleşme eksik")
                b2, b3 = data[pos + 1], data[pos + 2]
                length = (((b1 & 0xF) << 4) | (b2 >> 4)) + 0x11
                disp = (((b2 & 0xF) << 8) | b3) + 1
                pos += 3
            elif hi == 1:
                if pos + 3 >= len(data):
                    raise FormatError("LZ11 4-byte eşleşme eksik")
                b2, b3, b4 = data[pos + 1], data[pos + 2], data[pos + 3]
                length = (((b1 & 0xF) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                disp = (((b3 & 0xF) << 8) | b4) + 1
                pos += 4
            else:
                if pos + 1 >= len(data):
                    raise FormatError("LZ11 2-byte eşleşme eksik")
                b2 = data[pos + 1]
                length = hi + 1
                disp = (((b1 & 0xF) << 8) | b2) + 1
                pos += 2

            if disp > len(out):
                raise FormatError(f"Geçersiz LZ11 displacement: {disp}")
            src = len(out) - disp
            for i in range(length):
                if len(out) >= out_size:
                    break
                out.append(out[src + (i % disp)])
    return bytes(out)


def _lz11_find_match(data: bytes, pos: int, chains: Dict[bytes, List[int]], max_candidates: int = 96) -> Tuple[int, int]:
    if pos + 2 >= len(data):
        return 0, 0
    key = data[pos:pos+3]
    candidates = chains.get(key)
    if not candidates:
        return 0, 0
    best_len = 0
    best_disp = 0
    max_len = min(len(data) - pos, 0x111 + 0xFFFF)
    # En yakın adaylar genelde hem daha iyi hem daha hızlıdır.
    checked = 0
    for c in reversed(candidates):
        disp = pos - c
        if disp <= 0:
            continue
        if disp > 4096:
            break
        checked += 1
        if checked > max_candidates:
            break
        # Overlap'a izin ver: decompressor aynı displacement'ı döngüsel kopyalar.
        l = 3
        while l < max_len and data[pos + l] == data[c + (l % disp)]:
            l += 1
        if l > best_len:
            best_len, best_disp = l, disp
            if l == max_len:
                break
    if best_len < 3:
        return 0, 0
    return best_len, best_disp


def lz11_compress(data: bytes) -> bytes:
    n = len(data)
    out = bytearray()
    if n < 0x1000000:
        out += bytes((0x11, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF))
    else:
        out += b'\x11\x00\x00\x00' + struct.pack('<I', n)

    chains: Dict[bytes, List[int]] = {}

    def add_pos(p: int):
        if p + 2 >= n:
            return
        key = data[p:p+3]
        arr = chains.setdefault(key, [])
        arr.append(p)
        # Büyümeyi sınırlamak performans için yeterli; pencere zaten 4096.
        if len(arr) > 256:
            del arr[:len(arr)-256]

    pos = 0
    while pos < n:
        flag_pos = len(out)
        out.append(0)
        flags = 0
        token_bytes = bytearray()
        for slot in range(8):
            if pos >= n:
                break
            length, disp = _lz11_find_match(data, pos, chains)
            if length >= 3:
                flags |= 1 << (7 - slot)
                d = disp - 1
                if length <= 0x10:
                    v = length - 1
                    token_bytes += bytes(((v << 4) | ((d >> 8) & 0xF), d & 0xFF))
                elif length <= 0x110:
                    v = length - 0x11
                    token_bytes += bytes(((v >> 4) & 0xF, ((v & 0xF) << 4) | ((d >> 8) & 0xF), d & 0xFF))
                else:
                    v = length - 0x111
                    token_bytes += bytes((0x10 | ((v >> 12) & 0xF), (v >> 4) & 0xFF, ((v & 0xF) << 4) | ((d >> 8) & 0xF), d & 0xFF))
                old = pos
                pos += length
                for p in range(old, pos):
                    add_pos(p)
            else:
                token_bytes.append(data[pos])
                add_pos(pos)
                pos += 1
        out[flag_pos] = flags
        out += token_bytes

    while len(out) % 4:
        out.append(0xFF)
    return bytes(out)


# ---------------- DARC ----------------

@dataclass
class DarcEntry:
    raw0: int
    field1: int
    field2: int
    name: str
    data: Optional[bytes] = None

    @property
    def is_dir(self) -> bool:
        return bool(self.raw0 & 0x01000000)


@dataclass
class DarcArchive:
    endian: str
    header_size: int
    version: int
    file_table_offset: int
    entries: List[DarcEntry]

    @classmethod
    def parse(cls, blob: bytes) -> 'DarcArchive':
        if blob[:4] != b'darc':
            raise FormatError("DARC magic bulunamadı")
        bom = blob[4:6]
        if bom == b'\xff\xfe':
            endian = '<'
            enc = 'utf-16le'
        elif bom == b'\xfe\xff':
            endian = '>'
            enc = 'utf-16be'
        else:
            raise FormatError("DARC BOM geçersiz")
        if len(blob) < 0x1C:
            raise FormatError("DARC başlığı eksik")
        header_size, version, file_size, table_off, table_size, data_off = struct.unpack_from(endian + 'HIIIII', blob, 6)
        if table_off + 12 > len(blob):
            raise FormatError("DARC tablo offseti geçersiz")
        r0, r1, total = struct.unpack_from(endian + 'III', blob, table_off)
        if total <= 0 or total > 100000:
            raise FormatError("DARC entry sayısı geçersiz")
        node_end = table_off + total * 12
        name_size = table_size - total * 12
        if name_size < 0 or node_end + name_size > len(blob):
            raise FormatError("DARC isim tablosu geçersiz")
        name_table = blob[node_end:node_end + name_size]

        def read_name(off: int) -> str:
            if off < 0 or off >= len(name_table):
                return ''
            p = off
            end = p
            while end + 1 < len(name_table) and name_table[end:end+2] != b'\x00\x00':
                end += 2
            return name_table[p:end].decode(enc, errors='replace')

        entries: List[DarcEntry] = []
        for i in range(total):
            raw0, f1, f2 = struct.unpack_from(endian + 'III', blob, table_off + i * 12)
            name_off = raw0 & 0x00FFFFFF
            is_dir = bool(raw0 & 0x01000000)
            dat = None
            if not is_dir:
                if f1 + f2 > len(blob):
                    raise FormatError(f"DARC file entry sınır dışı: {i}")
                dat = blob[f1:f1+f2]
            entries.append(DarcEntry(raw0, f1, f2, read_name(name_off), dat))
        return cls(endian, header_size, version, table_off, entries)

    def paths(self) -> List[str]:
        # DARC dizinlerinde field2, dizinin kapsadığı son+1 entry indeksidir.
        paths = [''] * len(self.entries)
        stack: List[Tuple[int, int, str]] = []  # (idx,end,path)
        for i, e in enumerate(self.entries):
            while stack and i >= stack[-1][1]:
                stack.pop()
            parent = stack[-1][2] if stack else ''
            if i == 0:
                paths[i] = ''
            else:
                paths[i] = f"{parent}/{e.name}".strip('/')
            if e.is_dir:
                stack.append((i, e.field2, paths[i]))
        return paths

    def files(self) -> Dict[str, bytes]:
        paths = self.paths()
        return {paths[i]: e.data or b'' for i, e in enumerate(self.entries) if not e.is_dir}

    def replace_file(self, path: str, data: bytes):
        paths = self.paths()
        for i, p in enumerate(paths):
            if p == path and not self.entries[i].is_dir:
                self.entries[i].data = data
                return
        raise KeyError(path)

    def build(self, alignment: int = 0x20) -> bytes:
        endian = self.endian
        enc = 'utf-16le' if endian == '<' else 'utf-16be'
        # İsim tablosunu yeniden oluştur; dizin indeks/parent alanlarını olduğu gibi koru.
        name_table = bytearray()
        name_offsets: List[int] = []
        for e in self.entries:
            name_offsets.append(len(name_table))
            name_table += e.name.encode(enc) + b'\x00\x00'
        table_size = len(self.entries) * 12 + len(name_table)
        data_start = align_up(self.file_table_offset + table_size, alignment)
        out = bytearray(b'\x00' * data_start)
        out[:4] = b'darc'
        out[4:6] = b'\xff\xfe' if endian == '<' else b'\xfe\xff'

        # Dosyaları yerleştir ve yeni offset/size alanlarını hazırla.
        new_fields: List[Tuple[int, int, int]] = []
        cursor = data_start
        first_file_off = data_start
        seen_file = False
        for i, e in enumerate(self.entries):
            raw0 = (e.raw0 & 0xFF000000) | (name_offsets[i] & 0x00FFFFFF)
            if e.is_dir:
                new_fields.append((raw0, e.field1, e.field2))
            else:
                cursor = align_up(cursor, alignment)
                if len(out) < cursor:
                    out += b'\x00' * (cursor - len(out))
                dat = e.data or b''
                off = cursor
                out += dat
                cursor += len(dat)
                if not seen_file:
                    first_file_off = off
                    seen_file = True
                new_fields.append((raw0, off, len(dat)))

        final_size = align_up(len(out), alignment)
        if len(out) < final_size:
            out += b'\x00' * (final_size - len(out))
        file_size = len(out)
        struct.pack_into(endian + 'HIIIII', out, 6,
                         self.header_size, self.version, file_size,
                         self.file_table_offset, table_size, first_file_off)
        for i, vals in enumerate(new_fields):
            struct.pack_into(endian + 'III', out, self.file_table_offset + i * 12, *vals)
        noff = self.file_table_offset + len(self.entries) * 12
        out[noff:noff+len(name_table)] = name_table
        return bytes(out)


# ---------------- MSBT ----------------

_TOKEN_RE = re.compile(r'\{(?:TAG|END)_\d+\}')

@dataclass
class MsbtMessage:
    index: int
    label: str
    source_markup: str
    token_map: Dict[str, bytes]


@dataclass
class _MsbtSection:
    magic: bytes
    reserved: bytes
    payload: bytes


class MsbtFile:
    def __init__(self, blob: bytes):
        self.original = blob
        if blob[:8] != b'MsgStdBn':
            raise FormatError("MSBT magic bulunamadı")
        bom = blob[8:10]
        if bom == b'\xff\xfe':
            self.endian = '<'
            self.utf16 = 'utf-16le'
        elif bom == b'\xfe\xff':
            self.endian = '>'
            self.utf16 = 'utf-16be'
        else:
            raise FormatError("MSBT BOM geçersiz")
        self.encoding = blob[0x0C]
        self.version = blob[0x0D]
        self.section_count = struct.unpack_from(self.endian + 'H', blob, 0x0E)[0]
        if self.encoding != 1:
            raise FormatError(f"Bu araç şu anda UTF-16 MSBT destekliyor (encoding={self.encoding})")
        self.header = bytearray(blob[:0x20])
        self.sections: List[_MsbtSection] = []
        off = 0x20
        for _ in range(self.section_count):
            if off + 0x10 > len(blob):
                raise FormatError("MSBT section başlığı eksik")
            magic = blob[off:off+4]
            size = struct.unpack_from(self.endian + 'I', blob, off+4)[0]
            reserved = blob[off+8:off+0x10]
            p0, p1 = off + 0x10, off + 0x10 + size
            if p1 > len(blob):
                raise FormatError(f"MSBT {magic!r} section sınır dışı")
            self.sections.append(_MsbtSection(magic, reserved, blob[p0:p1]))
            off = align_up(p1, 0x10)
        self.labels = self._parse_labels()
        self.raw_strings = self._parse_txt2_strings()
        self.messages = self._make_messages()

    def _section(self, magic: bytes) -> _MsbtSection:
        for s in self.sections:
            if s.magic == magic:
                return s
        raise FormatError(f"MSBT section yok: {magic.decode('ascii', 'replace')}")

    def _parse_labels(self) -> Dict[int, str]:
        try:
            data = self._section(b'LBL1').payload
        except FormatError:
            return {}
        if len(data) < 4:
            return {}
        groups = struct.unpack_from(self.endian + 'I', data, 0)[0]
        labels: Dict[int, str] = {}
        for g in range(groups):
            base = 4 + g * 8
            if base + 8 > len(data):
                break
            count, off = struct.unpack_from(self.endian + 'II', data, base)
            p = off
            for _ in range(count):
                if p >= len(data):
                    break
                ln = data[p]
                p += 1
                if p + ln + 4 > len(data):
                    break
                name = data[p:p+ln].decode('utf-8', errors='replace')
                p += ln
                idx = struct.unpack_from(self.endian + 'I', data, p)[0]
                p += 4
                labels[idx] = name
        return labels

    def _parse_txt2_strings(self) -> List[bytes]:
        data = self._section(b'TXT2').payload
        if len(data) < 4:
            raise FormatError("TXT2 eksik")
        count = struct.unpack_from(self.endian + 'I', data, 0)[0]
        if 4 + count * 4 > len(data):
            raise FormatError("TXT2 offset tablosu bozuk")
        offsets = list(struct.unpack_from(self.endian + f'{count}I', data, 4)) if count else []
        result = []
        for off in offsets:
            if off >= len(data):
                raise FormatError("TXT2 string offset sınır dışı")
            p = off
            while True:
                if p + 2 > len(data):
                    raise FormatError("TXT2 string sonlandırıcısı bulunamadı")
                cu = struct.unpack_from(self.endian + 'H', data, p)[0]
                if cu == 0:
                    result.append(data[off:p])
                    break
                if cu == 0x000E:
                    if p + 8 > len(data):
                        raise FormatError("Eksik MSBT kontrol etiketi")
                    param_size = struct.unpack_from(self.endian + 'H', data, p + 6)[0]
                    p += 8 + param_size
                elif cu == 0x000F:
                    p += 6
                else:
                    p += 2
        return result

    def _markup_from_raw(self, raw: bytes) -> Tuple[str, Dict[str, bytes]]:
        p = 0
        parts: List[str] = []
        textbuf = bytearray()
        token_map: Dict[str, bytes] = {}
        tag_no = 0
        end_no = 0

        def flush():
            nonlocal textbuf
            if textbuf:
                parts.append(bytes(textbuf).decode(self.utf16, errors='strict'))
                textbuf = bytearray()

        while p < len(raw):
            cu = struct.unpack_from(self.endian + 'H', raw, p)[0]
            if cu == 0x000E:
                flush()
                if p + 8 > len(raw):
                    raise FormatError("Eksik TAG")
                param_size = struct.unpack_from(self.endian + 'H', raw, p+6)[0]
                blob = raw[p:p+8+param_size]
                tag_no += 1
                tok = f'{{TAG_{tag_no}}}'
                token_map[tok] = blob
                parts.append(tok)
                p += len(blob)
            elif cu == 0x000F:
                flush()
                blob = raw[p:p+6]
                end_no += 1
                tok = f'{{END_{end_no}}}'
                token_map[tok] = blob
                parts.append(tok)
                p += len(blob)
            else:
                textbuf += raw[p:p+2]
                p += 2
        flush()
        return ''.join(parts), token_map

    def _make_messages(self) -> List[MsbtMessage]:
        result = []
        for i, raw in enumerate(self.raw_strings):
            markup, token_map = self._markup_from_raw(raw)
            result.append(MsbtMessage(i, self.labels.get(i, f'#{i}'), markup, token_map))
        return result

    def validate_markup(self, index: int, markup: str) -> Tuple[bool, str]:
        source_tokens = list(self.messages[index].token_map.keys())
        found = _TOKEN_RE.findall(markup)
        if sorted(found) != sorted(source_tokens):
            missing = [t for t in source_tokens if t not in found]
            extra = [t for t in found if t not in source_tokens]
            return False, f"Kontrol kodları uyuşmuyor. Eksik: {missing or '-'} Fazla: {extra or '-'}"
        for t in source_tokens:
            if found.count(t) != 1:
                return False, f"{t} tam bir kez bulunmalı"
        return True, ''

    def _raw_from_markup(self, index: int, markup: str) -> bytes:
        ok, why = self.validate_markup(index, markup)
        if not ok:
            raise FormatError(why)
        token_map = self.messages[index].token_map
        out = bytearray()
        p = 0
        for m in _TOKEN_RE.finditer(markup):
            out += markup[p:m.start()].encode(self.utf16)
            out += token_map[m.group(0)]
            p = m.end()
        out += markup[p:].encode(self.utf16)
        return bytes(out)

    def build(self, translations: Dict[int, str]) -> bytes:
        strings: List[bytes] = []
        for i, raw in enumerate(self.raw_strings):
            target = translations.get(i, self.messages[i].source_markup)
            strings.append(self._raw_from_markup(i, target))
        count = len(strings)
        txt = bytearray(struct.pack(self.endian + 'I', count))
        txt += b'\x00' * (4 * count)
        cursor = 4 + 4 * count
        offsets = []
        for raw in strings:
            offsets.append(cursor)
            txt += raw + b'\x00\x00'
            cursor = len(txt)
        for i, off in enumerate(offsets):
            struct.pack_into(self.endian + 'I', txt, 4 + i*4, off)

        sections = []
        for s in self.sections:
            payload = bytes(txt) if s.magic == b'TXT2' else s.payload
            sections.append(_MsbtSection(s.magic, s.reserved, payload))

        out = bytearray(self.header)
        for s in sections:
            out += s.magic
            out += struct.pack(self.endian + 'I', len(s.payload))
            out += s.reserved
            out += s.payload
            while len(out) % 0x10:
                out.append(0xAB)
        struct.pack_into(self.endian + 'I', out, 0x12, len(out))
        return bytes(out)


def open_lz_darc(path: Path) -> Tuple[bytes, DarcArchive]:
    raw = path.read_bytes()
    if raw[:1] == b'\x11':
        dec = lz11_decompress(raw)
    elif raw[:4] == b'darc':
        dec = raw
    else:
        raise FormatError(f"Ne LZ11 ne DARC: {path.name}")
    return dec, DarcArchive.parse(dec)
