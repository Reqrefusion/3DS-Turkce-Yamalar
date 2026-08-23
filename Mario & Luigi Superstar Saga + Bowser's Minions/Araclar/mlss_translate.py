#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mario & Luigi: Superstar Saga + Bowser's Minions (3DS) translation helper.

Features:
- Reads Nintendo MSBT files used by this game.
- Reads/rebuilds AlphaDream BG4 archives (BMsg.dat/FMsg.dat) while preserving all headers.
- Exports one CSV per top-level message file, languages side-by-side, with a TR column.
- Builds a drop-in translated language slot from the TR column.
- Adds real Turkish glyph bitmaps to CTR BFFNT A4 fonts by deriving them from the font's own glyphs.

No third-party Python packages are required.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import shutil
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

LANGS = ["EU_du", "EU_en", "EU_fr", "EU_ge", "EU_it", "EU_sp"]
LANG_LABELS = {
    "EU_du": "Nederlands (EU_du)",
    "EU_en": "English (EU_en)",
    "EU_fr": "Français (EU_fr)",
    "EU_ge": "Deutsch (EU_ge)",
    "EU_it": "Italiano (EU_it)",
    "EU_sp": "Español (EU_sp)",
}
CSV_LANG_COLUMNS = LANGS
TURKISH_CHARS = "çÇğĞıİöÖşŞüÜ"
FONT_DERIVATIONS = {
    "ç": ("c", "cedilla"), "Ç": ("C", "cedilla"),
    "ğ": ("g", "breve"),   "Ğ": ("G", "breve"),
    "ı": ("i", "dotless"), "İ": ("I", "dot"),
    "ö": ("o", "diaeresis"), "Ö": ("O", "diaeresis"),
    "ş": ("s", "cedilla"), "Ş": ("S", "cedilla"),
    "ü": ("u", "diaeresis"), "Ü": ("U", "diaeresis"),
}
TOKEN_RE = re.compile(r"<(?:0E:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]*|0F:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}|U\+[0-9A-Fa-f]{4,6})>")
TAG_RE = re.compile(r"<(?:0E:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]*|0F:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4})>")


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) // boundary * boundary


def next_pow2(n: int) -> int:
    return 1 if n <= 1 else 1 << (n - 1).bit_length()


@dataclass
class MSBTSection:
    magic: bytes
    size: int
    reserved: bytes
    data: bytes
    pad_byte: int = 0xAB


class MSBT:
    def __init__(self, data: bytes):
        if len(data) < 0x20 or data[:8] != b"MsgStdBn":
            raise ValueError("Geçersiz MSBT: MsgStdBn başlığı yok")
        self.original = data
        self.bom = data[8:10]
        if self.bom == b"\xff\xfe":
            self.endian = "<"
            self.codec = "utf-16le"
        elif self.bom == b"\xfe\xff":
            self.endian = ">"
            self.codec = "utf-16be"
        else:
            raise ValueError("Desteklenmeyen MSBT byte-order işareti")
        self.encoding_byte = data[12]
        if self.encoding_byte != 1:
            raise ValueError(f"Bu araç bu oyun için UTF-16 MSBT bekliyor (encoding={self.encoding_byte})")
        self.num_sections = struct.unpack_from(self.endian + "H", data, 0x0E)[0]
        declared_size = struct.unpack_from(self.endian + "I", data, 0x12)[0]
        if declared_size > len(data):
            raise ValueError("MSBT dosya boyutu alanı dosyadan büyük")
        self.header = bytearray(data[:0x20])
        self.sections: List[MSBTSection] = []
        pos = 0x20
        for _ in range(self.num_sections):
            if pos + 16 > len(data):
                raise ValueError("MSBT bölüm başlığı dosya dışında")
            magic = data[pos:pos+4]
            size = struct.unpack_from(self.endian + "I", data, pos + 4)[0]
            reserved = data[pos+8:pos+16]
            start = pos + 16
            end = start + size
            if end > len(data):
                raise ValueError(f"MSBT {magic!r} bölümü dosya dışında")
            sec_data = data[start:end]
            nxt = align(end, 16)
            padding = data[end:min(nxt, len(data))]
            pad_byte = padding[0] if padding else 0xAB
            self.sections.append(MSBTSection(magic, size, reserved, sec_data, pad_byte))
            pos = nxt
        self._parse_lbl1()
        self._parse_txt2()

    def _section(self, magic: bytes) -> Optional[MSBTSection]:
        for s in self.sections:
            if s.magic == magic:
                return s
        return None

    def _parse_lbl1(self) -> None:
        self.labels_by_index: Dict[int, str] = {}
        sec = self._section(b"LBL1")
        if not sec or len(sec.data) < 4:
            return
        d = sec.data
        ngrp = struct.unpack_from(self.endian + "I", d, 0)[0]
        if 4 + ngrp * 8 > len(d):
            return
        groups = [struct.unpack_from(self.endian + "II", d, 4 + i*8) for i in range(ngrp)]
        for count, off in groups:
            p = off
            for _ in range(count):
                if p >= len(d):
                    break
                ln = d[p]; p += 1
                if p + ln + 4 > len(d):
                    break
                name = d[p:p+ln].decode("ascii", "replace"); p += ln
                idx = struct.unpack_from(self.endian + "I", d, p)[0]; p += 4
                self.labels_by_index.setdefault(idx, name)

    def _find_message_terminator(self, raw: bytes) -> int:
        """Return byte end position including first real UTF-16 NUL terminator.

        MSBT control-tag parameters may contain zero bytes, so this must parse tags.
        """
        p = 0
        L = len(raw)
        while p + 2 <= L:
            code = struct.unpack_from(self.endian + "H", raw, p)[0]
            if code == 0x0000:
                return p + 2
            if code == 0x000E and p + 8 <= L:
                arg_len = struct.unpack_from(self.endian + "H", raw, p + 6)[0]
                q = p + 8 + arg_len
                if q <= L:
                    p = q
                    continue
            if code == 0x000F and p + 6 <= L:
                p += 6
                continue
            p += 2
        return L

    def _parse_txt2(self) -> None:
        sec = self._section(b"TXT2")
        if not sec or len(sec.data) < 4:
            raise ValueError("MSBT TXT2 bölümü bulunamadı")
        d = sec.data
        self.text_count = struct.unpack_from(self.endian + "I", d, 0)[0]
        table_end = 4 + self.text_count * 4
        if table_end > len(d):
            raise ValueError("MSBT TXT2 offset tablosu bozuk")
        self.text_offsets = list(struct.unpack_from(self.endian + f"{self.text_count}I", d, 4))
        self.prefixes: List[bytes] = []
        self.suffixes: List[bytes] = []
        for i, off in enumerate(self.text_offsets):
            nxt = self.text_offsets[i+1] if i + 1 < self.text_count else len(d)
            if off > len(d) or nxt > len(d) or nxt < off:
                raise ValueError("MSBT TXT2 offset sırası bozuk")
            slot = d[off:nxt]
            end = self._find_message_terminator(slot)
            self.prefixes.append(slot[:end])
            self.suffixes.append(slot[end:])

    def key_for_index(self, i: int) -> str:
        return self.labels_by_index.get(i, f"#INDEX:{i:06d}")

    def render_index(self, i: int) -> str:
        return render_msbt_message(self.prefixes[i], self.endian)

    def replace_index(self, i: int, text: str) -> None:
        self.prefixes[i] = parse_msbt_message(text, self.endian)

    def to_bytes(self) -> bytes:
        header = bytearray(self.header)
        out = bytearray(header)
        for sec in self.sections:
            if sec.magic == b"TXT2":
                count = self.text_count
                table_len = 4 + 4 * count
                offsets: List[int] = []
                body = bytearray()
                for pref, suf in zip(self.prefixes, self.suffixes):
                    offsets.append(table_len + len(body))
                    body.extend(pref)
                    body.extend(suf)
                txt = bytearray(struct.pack(self.endian + "I", count))
                if count:
                    txt.extend(struct.pack(self.endian + f"{count}I", *offsets))
                txt.extend(body)
                data = bytes(txt)
                out.extend(b"TXT2")
                out.extend(struct.pack(self.endian + "I", len(data)))
                out.extend(sec.reserved)
                out.extend(data)
            else:
                out.extend(sec.magic)
                out.extend(struct.pack(self.endian + "I", sec.size))
                out.extend(sec.reserved)
                out.extend(sec.data)
            pad = (-len(out)) % 16
            if pad:
                out.extend(bytes([sec.pad_byte]) * pad)
        struct.pack_into(self.endian + "I", out, 0x12, len(out))
        return bytes(out)


def render_msbt_message(raw: bytes, endian: str) -> str:
    chars: List[str] = []
    p = 0
    L = len(raw)
    codec = "utf-16le" if endian == "<" else "utf-16be"
    while p + 2 <= L:
        code = struct.unpack_from(endian + "H", raw, p)[0]
        if code == 0:
            break
        if code == 0x000E and p + 8 <= L:
            group, typ, arg_len = struct.unpack_from(endian + "HHH", raw, p + 2)
            q = p + 8 + arg_len
            if q <= L:
                args = raw[p+8:q].hex().upper()
                chars.append(f"<0E:{group:04X}:{typ:04X}:{args}>")
                p = q
                continue
        if code == 0x000F and p + 6 <= L:
            group, typ = struct.unpack_from(endian + "HH", raw, p + 2)
            chars.append(f"<0F:{group:04X}:{typ:04X}>")
            p += 6
            continue
        if code == 0x000A:
            chars.append("\n"); p += 2; continue
        if code == 0x000D:
            chars.append("\r"); p += 2; continue
        if code == 0x0009:
            chars.append("\t"); p += 2; continue
        if code < 0x20:
            chars.append(f"<U+{code:04X}>"); p += 2; continue
        if 0xD800 <= code <= 0xDBFF and p + 4 <= L:
            low = struct.unpack_from(endian + "H", raw, p+2)[0]
            if 0xDC00 <= low <= 0xDFFF:
                chars.append(raw[p:p+4].decode(codec, "replace")); p += 4; continue
        chars.append(raw[p:p+2].decode(codec, "replace")); p += 2
    return "".join(chars)


def parse_msbt_message(text: str, endian: str) -> bytes:
    codec = "utf-16le" if endian == "<" else "utf-16be"
    out = bytearray()
    p = 0
    while p < len(text):
        if text[p] == "<":
            m = TOKEN_RE.match(text, p)
            if m:
                tok = m.group(0)
                if tok.startswith("<0E:"):
                    parts = tok[1:-1].split(":", 3)
                    group = int(parts[1], 16); typ = int(parts[2], 16)
                    arghex = parts[3]
                    if len(arghex) % 2:
                        raise ValueError(f"Tek sayıda hex karakterli kontrol kodu: {tok}")
                    args = bytes.fromhex(arghex) if arghex else b""
                    out.extend(struct.pack(endian + "HHHH", 0x000E, group, typ, len(args)))
                    out.extend(args)
                elif tok.startswith("<0F:"):
                    parts = tok[1:-1].split(":")
                    out.extend(struct.pack(endian + "HHH", 0x000F, int(parts[1],16), int(parts[2],16)))
                else:
                    cp = int(tok[3:-1], 16)
                    out.extend(struct.pack(endian + "H", cp))
                p = m.end(); continue
        if text[p] == "\\" and p + 1 < len(text):
            esc = text[p+1]
            if esc == "0": out.extend(struct.pack(endian + "H", 0)); p += 2; continue
            if esc == "n": out.extend(struct.pack(endian + "H", 10)); p += 2; continue
            if esc == "r": out.extend(struct.pack(endian + "H", 13)); p += 2; continue
            if esc == "t": out.extend(struct.pack(endian + "H", 9)); p += 2; continue
            if esc == "\\": out.extend("\\".encode(codec)); p += 2; continue
        ch = text[p]
        out.extend(ch.encode(codec))
        p += 1
    # The rendered CSV text never includes the structural terminator, so always append one.
    # (A control tag with zero-length arguments also ends in 00 00; checking bytes.endswith would be wrong.)
    out.extend(struct.pack(endian + "H", 0))
    return bytes(out)


def tag_signature(text: str) -> List[str]:
    return [m.group(0).upper() for m in TAG_RE.finditer(text)]


def special_glyph_signature(text: str) -> List[str]:
    """Return private-use glyphs (buttons/icons) in display order.

    These are ordinary Unicode code points in the CSV, not <0E>/<0F> tags, so
    they need an explicit safety check to prevent accidental deletion/reordering.
    """
    return [f"U+{ord(ch):04X}" for ch in text if 0xE000 <= ord(ch) <= 0xF8FF]


@dataclass
class BG4Entry:
    header_index: int
    offset: int
    size: int
    unknown: int
    name_index: int
    compressed: bool
    name: Optional[str] = None
    data: bytes = b""


class BG4:
    def __init__(self, data: bytes):
        if len(data) < 16 or data[:4] != b"BG4\0":
            raise ValueError("Geçersiz BG4 arşivi")
        self.original = data
        self.constant1, self.header_count = struct.unpack_from("<HH", data, 4)
        self.header_size = struct.unpack_from("<I", data, 8)[0]
        self.derived, self.multiplier = struct.unpack_from("<HH", data, 12)
        if 16 + self.header_count * 14 > self.header_size or self.header_size > len(data):
            raise ValueError("BG4 başlık boyutu geçersiz")
        self.entries: List[BG4Entry] = []
        pos = 16
        for i in range(self.header_count):
            off_field, size, unknown = struct.unpack_from("<III", data, pos)
            name_index = struct.unpack_from("<H", data, pos + 12)[0]
            compressed = bool(off_field & 0x80000000)
            off = off_field & 0x7FFFFFFF
            self.entries.append(BG4Entry(i, off, size, unknown, name_index, compressed))
            pos += 14
        names: List[str] = []
        while pos + 2 <= self.header_size and data[pos:pos+2] != b"\xff\xff":
            try:
                z = data.index(0, pos, self.header_size)
            except ValueError:
                break
            name = data[pos:z].decode("ascii", "replace")
            pos = z + 1
            if name != "(invalid)":
                names.append(name)
        valid = [e for e in self.entries if e.unknown != 0xFFFFFFFF]
        by_name_index = sorted(valid, key=lambda e: e.name_index)
        if len(names) != len(by_name_index):
            raise ValueError(f"BG4 ad sayısı ({len(names)}) ile gerçek dosya sayısı ({len(by_name_index)}) uyuşmuyor")
        for e, name in zip(by_name_index, names):
            e.name = name
        for e in valid:
            if e.offset + e.size > len(data):
                raise ValueError("BG4 dosya girdisi arşiv dışında")
            e.data = data[e.offset:e.offset+e.size]
        self.valid_entries = valid
        self.header_blob = bytearray(data[:self.header_size])

    def by_name(self) -> Dict[str, BG4Entry]:
        return {e.name: e for e in self.valid_entries if e.name is not None}

    def to_bytes(self) -> bytes:
        header = bytearray(self.header_blob)
        out = bytearray(header)
        cursor = self.header_size
        physical = sorted(self.valid_entries, key=lambda e: (e.offset, e.header_index))
        for e in physical:
            new_off = cursor
            new_size = len(e.data)
            field = new_off | (0x80000000 if e.compressed else 0)
            hpos = 16 + e.header_index * 14
            struct.pack_into("<II", header, hpos, field, new_size)
            e.offset = new_off; e.size = new_size
            cursor += new_size
        out = bytearray(header)
        for e in physical:
            out.extend(e.data)
        return bytes(out)


# ---------------- BFFNT font support ----------------

@dataclass
class CMapSection:
    start: int
    end: int
    method: int
    reserved: int
    mapping: Dict[int, int]


class BFFNT:
    def __init__(self, data: bytes):
        if len(data) < 0x34 or data[:4] != b"FFNT":
            raise ValueError("Geçersiz BFFNT")
        self.original = data
        self.endian = "<" if data[4:6] == b"\xff\xfe" else ">"
        self.magic, self.bom, self.header_len, self.version, self.file_size, self.block_count = struct.unpack_from(self.endian + "4sHHIII", data, 0)
        self.finf_start = self.header_len
        finf = struct.unpack_from(self.endian + "4sI4B2H4B3I", data, self.finf_start)
        if finf[0] != b"FINF":
            raise ValueError("BFFNT FINF bulunamadı")
        self.tglp_off, self.cwdh_off, self.cmap_off = finf[-3:]
        self.tglp_start = self.tglp_off - 8
        t = struct.unpack_from(self.endian + "4sI4BI6HI", data, self.tglp_start)
        if t[0] != b"TGLP":
            raise ValueError("BFFNT TGLP bulunamadı")
        (self.tglp_magic, self.tglp_size, self.cell_w, self.cell_h, self.sheet_count, self.max_w,
         self.sheet_size, self.baseline, self.pixel_format, self.cols, self.rows,
         self.sheet_w, self.sheet_h, self.data_off) = t
        self.cwdh_start = self.cwdh_off - 8
        m, size, self.cwdh_begin, self.cwdh_end, self.cwdh_next = struct.unpack_from(self.endian + "4sI2HI", data, self.cwdh_start)
        if m != b"CWDH":
            raise ValueError("BFFNT CWDH bulunamadı")
        if self.cwdh_next != 0:
            raise ValueError("Çok bölümlü CWDH henüz desteklenmiyor")
        nwidth = self.cwdh_end - self.cwdh_begin + 1
        width_pos = self.cwdh_start + 16
        self.width_raw = [data[width_pos+i*3:width_pos+i*3+3] for i in range(nwidth)]
        self.cmaps: List[CMapSection] = []
        off = self.cmap_off - 8
        self.glyph_map: Dict[int, int] = {}
        while off:
            magic, sz, start, end, method, reserved, nxt = struct.unpack_from(self.endian + "4sI4HI", data, off)
            if magic != b"CMAP":
                raise ValueError("BFFNT CMAP zinciri bozuk")
            pos = off + 20
            mp: Dict[int, int] = {}
            if method == 0:
                base = struct.unpack_from(self.endian + "H", data, pos)[0]
                for cp in range(start, end+1): mp[cp] = base + cp - start
            elif method == 1:
                n = end - start + 1
                vals = struct.unpack_from(self.endian + f"{n}H", data, pos)
                for cp, idx in zip(range(start, end+1), vals):
                    if idx != 0xFFFF: mp[cp] = idx
            elif method == 2:
                count = struct.unpack_from(self.endian + "H", data, pos)[0]; pos += 2
                for _ in range(count):
                    cp, idx = struct.unpack_from(self.endian + "HH", data, pos); pos += 4
                    mp[cp] = idx
            else:
                raise ValueError(f"Bilinmeyen CMAP yöntemi: {method}")
            self.cmaps.append(CMapSection(start, end, method, reserved, mp))
            self.glyph_map.update(mp)
            off = nxt - 8 if nxt else 0

    def missing_turkish(self) -> List[str]:
        return [c for c in TURKISH_CHARS if ord(c) not in self.glyph_map]

    @staticmethod
    def _morton(x: int, y: int) -> int:
        r = 0
        for i in range(3):
            r |= ((x >> i) & 1) << (2*i)
            r |= ((y >> i) & 1) << (2*i+1)
        return r

    @classmethod
    def _decode_a4(cls, raw: bytes, w: int, h: int) -> List[int]:
        pix = [0] * (w*h)
        pos = 0
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                tile = raw[pos:pos+32]; pos += 32
                if len(tile) < 32: raise ValueError("A4 texture kısa")
                for y in range(8):
                    for x in range(8):
                        m = cls._morton(x,y); b = tile[m//2]
                        n = (b & 0x0F) if m % 2 == 0 else ((b >> 4) & 0x0F)
                        pix[(ty+y)*w + tx+x] = n
        return pix

    @classmethod
    def _encode_a4(cls, pix: Sequence[int], w: int, h: int) -> bytes:
        out = bytearray()
        for ty in range(0, h, 8):
            for tx in range(0, w, 8):
                tile = bytearray(32)
                for y in range(8):
                    for x in range(8):
                        m = cls._morton(x,y); v = int(pix[(ty+y)*w+tx+x]) & 0x0F
                        bi = m//2
                        if m % 2 == 0: tile[bi] = (tile[bi] & 0xF0) | v
                        else: tile[bi] = (tile[bi] & 0x0F) | (v << 4)
                out.extend(tile)
        return bytes(out)

    def _cell_xy(self, idx: int) -> Tuple[int,int]:
        return 1 + (idx % self.cols) * (self.cell_w + 1), 1 + (idx // self.cols) * (self.cell_h + 1)

    def _extract_cell(self, pix: Sequence[int], idx: int, h: int) -> List[List[int]]:
        x0,y0 = self._cell_xy(idx)
        if y0 + self.cell_h > h:
            raise ValueError("Glyph hücresi texture dışında")
        return [[pix[(y0+y)*self.sheet_w+x0+x] for x in range(self.cell_w)] for y in range(self.cell_h)]

    def _write_cell(self, pix: List[int], idx: int, cell: Sequence[Sequence[int]], h: int) -> None:
        x0,y0 = self._cell_xy(idx)
        if y0 + self.cell_h > h:
            raise ValueError("Yeni glyph hücresi texture dışında")
        for y in range(self.cell_h):
            for x in range(self.cell_w):
                pix[(y0+y)*self.sheet_w+x0+x] = int(cell[y][x]) & 0x0F

    @staticmethod
    def _bbox(cell: Sequence[Sequence[int]]) -> Optional[Tuple[int,int,int,int]]:
        xs=[]; ys=[]
        for y,row in enumerate(cell):
            for x,v in enumerate(row):
                if v:
                    xs.append(x); ys.append(y)
        return (min(xs),min(ys),max(xs),max(ys)) if xs else None

    def _derive_cell(self, base: Sequence[Sequence[int]], kind: str, uppercase: bool) -> List[List[int]]:
        cell = [list(r) for r in base]
        bbox = self._bbox(cell)
        if bbox is None: return cell
        minx,miny,maxx,maxy = bbox
        ink = max(max(r) for r in cell) or 15

        def shift_down_one() -> None:
            nonlocal cell, miny, maxy
            if maxy + 1 < self.cell_h:
                cell = [[0]*self.cell_w] + cell[:-1]
                miny += 1; maxy += 1

        if kind in ("diaeresis", "breve", "dot") and uppercase and miny <= 1:
            shift_down_one()

        bbox2 = self._bbox(cell)
        if bbox2:
            minx,miny,maxx,maxy = bbox2
        cx = (minx + maxx) // 2

        if kind == "dotless":
            occupied = [any(v for v in row) for row in cell]
            first = next((i for i,v in enumerate(occupied) if v), None)
            if first is not None:
                gap = next((i for i in range(first+1, self.cell_h) if not occupied[i]), None)
                if gap is not None and any(occupied[gap+1:]):
                    for y in range(0, gap+1):
                        cell[y] = [0]*self.cell_w
                else:
                    for y in range(first, min(first+2,self.cell_h)):
                        cell[y] = [0]*self.cell_w
        elif kind == "dot":
            y = max(0, miny - 2)
            x = max(0, min(self.cell_w-1, cx))
            cell[y][x] = ink
            if self.cell_w >= 14 and x+1 < self.cell_w: cell[y][x+1] = max(cell[y][x+1], ink//2)
        elif kind == "diaeresis":
            y = max(0, miny - 2)
            span = max(2, (maxx-minx+1)//3)
            x1 = max(0, cx-span); x2 = min(self.cell_w-1, cx+span)
            cell[y][x1] = ink; cell[y][x2] = ink
            if self.cell_w >= 16 and y+1 < miny:
                cell[y+1][x1] = max(cell[y+1][x1], ink//2)
                cell[y+1][x2] = max(cell[y+1][x2], ink//2)
        elif kind == "breve":
            # Small U-shaped breve, using available rows above the base glyph.
            y0 = max(0, miny - 2)
            span = max(1, min(3, (maxx-minx)//3 + 1))
            left=max(0,cx-span); right=min(self.cell_w-1,cx+span)
            cell[y0][left] = ink; cell[y0][right] = ink
            y1 = min(self.cell_h-1, y0+1)
            for x in range(left+1,right): cell[y1][x] = max(cell[y1][x], ink)
        elif kind == "cedilla":
            y1 = maxy + 1
            if y1 < self.cell_h:
                x = max(0,min(self.cell_w-1,cx))
                cell[y1][x] = ink
                if y1 + 1 < self.cell_h:
                    x2 = max(0,x-1)
                    cell[y1+1][x2] = ink
                    if x2+1 < self.cell_w: cell[y1+1][x2+1] = max(cell[y1+1][x2+1], ink//2)
        return cell

    def patch_turkish(self) -> Tuple[bytes, List[str]]:
        missing = self.missing_turkish()
        if not missing:
            return self.original, []
        if self.pixel_format != 0x0B:
            raise ValueError(f"BFFNT formatı A4 değil (format={self.pixel_format})")
        if self.sheet_count != 1:
            raise ValueError("Birden fazla font texture sheet'i desteklenmiyor")
        if self.cwdh_begin != 0:
            raise ValueError("CWDH 0'dan başlamıyor; güvenli patch yapılamadı")
        for c in missing:
            base,_ = FONT_DERIVATIONS[c]
            if ord(base) not in self.glyph_map:
                raise ValueError(f"{c} için taban glyph {base} bulunamadı")

        tex_raw = self.original[self.data_off:self.data_off+self.sheet_size]
        pix = self._decode_a4(tex_raw, self.sheet_w, self.sheet_h)
        new_map: Dict[int,int] = {}
        widths = list(self.width_raw)
        next_idx = self.cwdh_end + 1
        for c in missing:
            new_map[ord(c)] = next_idx
            base_char,_ = FONT_DERIVATIONS[c]
            base_idx = self.glyph_map[ord(base_char)]
            if not (self.cwdh_begin <= base_idx <= self.cwdh_end):
                raise ValueError(f"Taban glyph genişliği CWDH dışında: {base_char}")
            widths.append(self.width_raw[base_idx-self.cwdh_begin])
            next_idx += 1
        new_end = self.cwdh_end + len(missing)

        needed_slots = new_end + 1
        needed_rows = math.ceil(needed_slots / self.cols)
        new_h = self.sheet_h
        if needed_rows * (self.cell_h + 1) + 2 > new_h:
            new_h = next_pow2(needed_rows * (self.cell_h + 1) + 2)
            # CTR textures are tiled in 8x8 blocks.
            new_h = align(new_h, 8)
            newpix = [0] * (self.sheet_w * new_h)
            for y in range(self.sheet_h):
                newpix[y*self.sheet_w:(y+1)*self.sheet_w] = pix[y*self.sheet_w:(y+1)*self.sheet_w]
            pix = newpix
        new_rows = max(self.rows, needed_rows)

        for c in missing:
            base_char, kind = FONT_DERIVATIONS[c]
            base_idx = self.glyph_map[ord(base_char)]
            cell = self._extract_cell(pix, base_idx, new_h)
            derived = self._derive_cell(cell, kind, c.isupper())
            self._write_cell(pix, new_map[ord(c)], derived, new_h)

        new_tex_raw = self._encode_a4(pix, self.sheet_w, new_h)
        new_sheet_size = len(new_tex_raw)

        # Build CWDH.
        cwdh_payload = b"".join(widths)
        cwdh_size = align(16 + len(cwdh_payload), 4)
        cwdh = bytearray(struct.pack(self.endian + "4sI2HI", b"CWDH", cwdh_size, self.cwdh_begin, new_end, 0))
        cwdh.extend(cwdh_payload)
        cwdh.extend(b"\x00" * (cwdh_size - len(cwdh)))

        # Merge Turkish mappings into the final scan CMAP when possible.
        cmaps = [CMapSection(c.start,c.end,c.method,c.reserved,dict(c.mapping)) for c in self.cmaps]
        scan = next((c for c in reversed(cmaps) if c.method == 2), None)
        if scan is None:
            scan = CMapSection(0,0xFFFF,2,0,{})
            cmaps.append(scan)
        scan.mapping.update(new_map)

        def cmap_blob(c: CMapSection, next_abs_plus8: int) -> bytes:
            if c.method == 0:
                # Preserve direct mapping only if contiguous.
                base = c.mapping.get(c.start,0)
                payload = struct.pack(self.endian + "H", base)
            elif c.method == 1:
                vals = [c.mapping.get(cp,0xFFFF) for cp in range(c.start,c.end+1)]
                payload = struct.pack(self.endian + f"{len(vals)}H", *vals)
            else:
                pairs = sorted(c.mapping.items())
                payload = bytearray(struct.pack(self.endian + "H", len(pairs)))
                for cp,idx in pairs: payload.extend(struct.pack(self.endian + "HH", cp, idx))
                payload = bytes(payload)
            size = align(20 + len(payload), 4)
            b = bytearray(struct.pack(self.endian + "4sI4HI", b"CMAP", size, c.start,c.end,c.method,c.reserved,next_abs_plus8))
            b.extend(payload); b.extend(b"\x00" * (size-len(b)))
            return bytes(b)

        # Prefix through the texture data offset is preserved exactly, then texture/CWDH/CMAP are rebuilt.
        out = bytearray(self.original[:self.data_off])
        out.extend(new_tex_raw)
        cwdh_start = len(out)
        out.extend(cwdh)
        cmap_start = len(out)

        # Pre-calculate CMAP section sizes so absolute next pointers are exact.
        tmp_sizes=[]
        for c in cmaps:
            if c.method==0: payload_len=2
            elif c.method==1: payload_len=2*(c.end-c.start+1)
            else: payload_len=2+4*len(c.mapping)
            tmp_sizes.append(align(20+payload_len,4))
        starts=[]; cur=cmap_start
        for sz in tmp_sizes: starts.append(cur); cur += sz
        for i,c in enumerate(cmaps):
            nxt = starts[i+1]+8 if i+1<len(cmaps) else 0
            out.extend(cmap_blob(c,nxt))

        # Patch global headers/offsets in the already-copied prefix.
        struct.pack_into(self.endian + "I", out, 0x0C, len(out))
        # FINF: cwdh/cmap offsets point 8 bytes into the section.
        struct.pack_into(self.endian + "I", out, self.finf_start + 0x18, cwdh_start + 8)
        struct.pack_into(self.endian + "I", out, self.finf_start + 0x1C, cmap_start + 8)
        # TGLP size reaches the next CWDH section; sheet data size / rows / height changed if expanded.
        struct.pack_into(self.endian + "I", out, self.tglp_start + 0x04, cwdh_start - self.tglp_start)
        struct.pack_into(self.endian + "I", out, self.tglp_start + 0x0C, new_sheet_size)
        struct.pack_into(self.endian + "H", out, self.tglp_start + 0x16, new_rows)
        struct.pack_into(self.endian + "H", out, self.tglp_start + 0x1A, new_h)
        return bytes(out), missing


def patch_font_file(src: Path, dst: Path) -> Tuple[List[str], List[str]]:
    font = BFFNT(src.read_bytes())
    before = font.missing_turkish()
    patched, added = font.patch_turkish()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(patched)
    after = BFFNT(patched).missing_turkish()
    return before, after


# ---------------- CSV project ----------------


def extract_msg_from_zip(zip_path: Path, dest_root: Path, progress=print) -> Path:
    """Safely extract only the Msg/ subtree from a supplied game-data ZIP."""
    zip_path=Path(zip_path);dest_root=Path(dest_root)
    if not zip_path.is_file(): raise ValueError("ZIP dosyası bulunamadı")
    out=dest_root/"Msg"
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,"r") as z:
        members=[]
        for info in z.infolist():
            name=info.filename.replace("\\","/")
            parts=Path(name).parts
            if not parts or parts[0]!="Msg" or info.is_dir(): continue
            rel=Path(*parts[1:])
            if not rel.parts or any(x in ("..","") for x in rel.parts): continue
            members.append((info,rel))
        if not members: raise ValueError("ZIP içinde Msg/ klasörü bulunamadı")
        for info,rel in members:
            dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src, dst.open("wb") as fp: shutil.copyfileobj(src,fp)
    progress(f"ZIP kaynağı hazırlandı: {out}")
    return out

def discover_languages(msg_root: Path) -> List[str]:
    found = [x for x in LANGS if (msg_root/x).is_dir()]
    if not found:
        found = sorted(p.name for p in msg_root.iterdir() if p.is_dir() and p.name.startswith("EU_"))
    return found


def message_files(msg_root: Path, langs: Sequence[str]) -> Tuple[List[str],List[str]]:
    names=set()
    for lang in langs:
        p=msg_root/lang
        if p.is_dir():
            names.update(x.name for x in p.glob("*.msbt"))
    direct=sorted(names)
    dats=[]
    for n in ("BMsg.dat","FMsg.dat"):
        if any((msg_root/l/n).is_file() for l in langs): dats.append(n)
    return direct,dats


def read_existing_tr(csv_path: Path) -> Dict[Tuple[str,str],str]:
    if not csv_path.exists(): return {}
    result={}
    try:
        with csv_path.open("r",encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            required={"AltDosya","Etiket","TR"}
            missing=required-set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"eksik sütun(lar): {', '.join(sorted(missing))}")
            for lineno,r in enumerate(reader,2):
                key=(r.get("AltDosya", ""),r.get("Etiket", ""))
                if key in result:
                    raise ValueError(f"yinelenen anahtar (CSV satırı {lineno}): {key}")
                result[key]=r.get("TR","")
    except Exception as ex:
        # Never silently discard an existing translation: export with an empty
        # preservation map could otherwise overwrite all TR cells.
        raise ValueError(f"Mevcut TR CSV güvenle okunamadı: {csv_path}: {ex}") from ex
    return result


def write_csv(path: Path, rows: List[Dict[str,str]], langs: Sequence[str], preserve_tr: bool=True) -> None:
    old = read_existing_tr(path) if preserve_tr else {}
    fields=["AltDosya","Etiket"] + list(langs) + ["TR"]
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            key=(r.get("AltDosya",""),r.get("Etiket",""))
            r["TR"] = old.get(key,r.get("TR",""))
            w.writerow({k:r.get(k,"") for k in fields})


def export_project(msg_root: Path, csv_dir: Path, preserve_tr: bool=True, progress=print) -> Dict[str,int]:
    msg_root=Path(msg_root);csv_dir=Path(csv_dir)
    langs=discover_languages(msg_root)
    if not langs: raise ValueError("Msg klasöründe EU_* dil klasörü bulunamadı")
    directs,dats=message_files(msg_root,langs)
    counts={}
    for fname in directs:
        per_lang={}
        order=[]; seen=set()
        for lang in langs:
            p=msg_root/lang/fname
            if not p.exists(): continue
            msbt=MSBT(p.read_bytes())
            m={}
            for i in range(msbt.text_count):
                k=msbt.key_for_index(i)
                m[k]=msbt.render_index(i)
                if k not in seen: seen.add(k);order.append(k)
            per_lang[lang]=m
        rows=[]
        for k in order:
            r={"AltDosya":"","Etiket":k,"TR":""}
            for lang in langs:r[lang]=per_lang.get(lang,{}).get(k,"")
            rows.append(r)
        out=csv_dir/(Path(fname).stem+".csv")
        write_csv(out,rows,langs,preserve_tr)
        counts[out.name]=len(rows);progress(f"CSV: {out.name} ({len(rows)} satır)")
    for fname in dats:
        per_lang={};order=[];seen=set()
        for lang in langs:
            p=msg_root/lang/fname
            if not p.exists():continue
            bg=BG4(p.read_bytes()); lm={}
            for entry in sorted(bg.valid_entries,key=lambda e:e.name_index):
                msbt=MSBT(entry.data)
                for i in range(msbt.text_count):
                    key=(entry.name or "",msbt.key_for_index(i))
                    lm[key]=msbt.render_index(i)
                    if key not in seen:seen.add(key);order.append(key)
            per_lang[lang]=lm
        rows=[]
        for sub,k in order:
            r={"AltDosya":sub,"Etiket":k,"TR":""}
            for lang in langs:r[lang]=per_lang.get(lang,{}).get((sub,k),"")
            rows.append(r)
        out=csv_dir/(Path(fname).stem+".csv")
        write_csv(out,rows,langs,preserve_tr)
        counts[out.name]=len(rows);progress(f"CSV: {out.name} ({len(rows)} satır)")
    return counts


def load_csv_map(path: Path) -> Dict[Tuple[str,str],Dict[str,str]]:
    result={}
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        required={"AltDosya","Etiket","TR"}
        missing=required-set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: eksik sütun(lar): {', '.join(sorted(missing))}")
        for lineno,r in enumerate(reader,2):
            key=(r.get("AltDosya", ""),r.get("Etiket", ""))
            if key in result:
                raise ValueError(f"{path.name}: yinelenen anahtar (CSV satırı {lineno}): {key}")
            result[key]=r
    return result


def seed_tr(csv_dir: Path, source_lang: str="EU_en", only_blank: bool=True, progress=print) -> int:
    n=0
    for p in sorted(Path(csv_dir).glob("*.csv")):
        with p.open("r",encoding="utf-8-sig",newline="") as f:
            rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else []
        if not rows or source_lang not in fields or "TR" not in fields: continue
        changed=0
        for r in rows:
            if (not only_blank) or not r.get("TR",""):
                r["TR"]=r.get(source_lang,"");changed+=1
        with p.open("w",encoding="utf-8-sig",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        n+=changed;progress(f"TR dolduruldu: {p.name} ({changed})")
    return n


def apply_csv_to_msbt(msbt: MSBT, rows: Dict[Tuple[str,str],Dict[str,str]], subfile: str, source_lang: str,
                      allow_tag_changes: bool, warnings: List[str]) -> int:
    changed=0
    for i in range(msbt.text_count):
        key=msbt.key_for_index(i)
        row=rows.get((subfile,key))
        if not row: continue
        tr=row.get("TR","")
        if tr == "": continue
        src=msbt.render_index(i)
        if not allow_tag_changes and tag_signature(src)!=tag_signature(tr):
            warnings.append(f"{subfile or '(ana)'} / {key}: kontrol kodları kaynakla uyuşmuyor")
            continue
        if not allow_tag_changes and special_glyph_signature(src)!=special_glyph_signature(tr):
            warnings.append(f"{subfile or '(ana)'} / {key}: düğme/özel glif dizisi kaynakla uyuşmuyor")
            continue
        if tr != src:
            msbt.replace_index(i,tr);changed+=1
    return changed


def csv_project_check(csv_dir: Path, source_lang: str="EU_en") -> Tuple[int,List[str]]:
    """Static CSV safety check that does not require extracted game binaries."""
    total=0; problems=[]
    for path in sorted(Path(csv_dir).glob("*.csv")):
        try:
            with path.open("r",encoding="utf-8-sig",newline="") as f:
                reader=csv.DictReader(f)
                required={"AltDosya","Etiket",source_lang,"TR"}
                missing=required-set(reader.fieldnames or [])
                if missing:
                    problems.append(f"{path.name}: eksik sütun(lar): {', '.join(sorted(missing))}")
                    continue
                seen=set()
                for lineno,r in enumerate(reader,2):
                    total+=1
                    key=(r.get("AltDosya",""),r.get("Etiket",""))
                    if key in seen:
                        problems.append(f"{path.name}:{lineno}: yinelenen anahtar: {key}")
                    seen.add(key)
                    tr=r.get("TR",""); src=r.get(source_lang,"")
                    if tr=="": problems.append(f"{path.name}:{lineno}: TR boş")
                    if tag_signature(src)!=tag_signature(tr):
                        problems.append(f"{path.name}:{lineno}: kontrol kodu dizisi uyuşmuyor")
                    if special_glyph_signature(src)!=special_glyph_signature(tr):
                        problems.append(f"{path.name}:{lineno}: düğme/özel glif dizisi uyuşmuyor")
                    for endian in ("<",">"):
                        try:
                            if render_msbt_message(parse_msbt_message(tr,endian),endian)!=tr:
                                problems.append(f"{path.name}:{lineno}: MSBT parse/render kayıplı ({endian})")
                        except Exception as ex:
                            problems.append(f"{path.name}:{lineno}: MSBT parse hatası ({endian}): {ex}")
        except Exception as ex:
            problems.append(f"{path.name}: CSV okuma hatası: {ex}")
    return total,problems


def build_project(msg_root: Path, csv_dir: Path, output_root: Path, base_lang: str="EU_en", target_slot: str="EU_en",
                  allow_tag_changes: bool=False, patch_fonts: bool=True, progress=print) -> Dict[str,object]:
    msg_root=Path(msg_root);csv_dir=Path(csv_dir);output_root=Path(output_root)
    if not (msg_root/base_lang).is_dir(): raise ValueError(f"Temel dil klasörü yok: {base_lang}")
    build_msg=output_root/"Msg"
    if build_msg.exists(): shutil.rmtree(build_msg)
    shutil.copytree(msg_root,build_msg)
    if target_slot!=base_lang:
        if (build_msg/target_slot).exists(): shutil.rmtree(build_msg/target_slot)
        shutil.copytree(build_msg/base_lang,build_msg/target_slot)
    target=build_msg/target_slot
    directs,dats=message_files(msg_root,[base_lang])
    changed=0;warnings=[];files_changed=[]
    for fname in directs:
        cp=csv_dir/(Path(fname).stem+".csv")
        if not cp.exists():continue
        rows=load_csv_map(cp)
        src=msg_root/base_lang/fname
        msbt=MSBT(src.read_bytes())
        c=apply_csv_to_msbt(msbt,rows,"",base_lang,allow_tag_changes,warnings)
        if c:
            (target/fname).write_bytes(msbt.to_bytes());changed+=c;files_changed.append(fname)
        progress(f"Build {fname}: {c} çeviri")
    for fname in dats:
        cp=csv_dir/(Path(fname).stem+".csv")
        if not cp.exists():continue
        rows=load_csv_map(cp)
        bg=BG4((msg_root/base_lang/fname).read_bytes())
        ctot=0
        for e in bg.valid_entries:
            msbt=MSBT(e.data)
            c=apply_csv_to_msbt(msbt,rows,e.name or "",base_lang,allow_tag_changes,warnings)
            if c:
                e.data=msbt.to_bytes();ctot+=c
        if ctot:
            (target/fname).write_bytes(bg.to_bytes());changed+=ctot;files_changed.append(fname)
        progress(f"Build {fname}: {ctot} çeviri")
    font_info=[]
    if patch_fonts:
        for src in sorted((msg_root/base_lang).glob("*.bffnt")):
            dst=target/src.name
            try:
                before,after=patch_font_file(src,dst)
                font_info.append((src.name,"".join(before),"".join(after)))
                progress(f"Font {src.name}: +{''.join(before) if before else 'zaten tam'}")
            except Exception as ex:
                warnings.append(f"Font {src.name}: {ex}")
    report=output_root/"build_report.txt"
    report.write_text(
        "MLSS Türkçe build raporu\n"+
        f"Temel dil: {base_lang}\nHedef slot: {target_slot}\nDeğiştirilen metin: {changed}\n"+
        f"Değiştirilen dosyalar: {', '.join(files_changed) if files_changed else '(yok)'}\n\n"+
        "Uyarılar:\n"+("\n".join(warnings) if warnings else "Yok")+"\n\nFontlar:\n"+
        "\n".join(f"{a}: önce eksik=[{b}] sonra eksik=[{c}]" for a,b,c in font_info),
        encoding="utf-8")
    return {"changed":changed,"warnings":warnings,"files":files_changed,"font_info":font_info,"output":build_msg}


def font_report(msg_root: Path, out_csv: Path, progress=print) -> List[Dict[str,str]]:
    rows=[]
    for p in sorted(Path(msg_root).rglob("*.bffnt")):
        try:
            f=BFFNT(p.read_bytes()); missing="".join(f.missing_turkish())
            rows.append({"Dosya":str(p.relative_to(msg_root)),"Eksik_TR":missing,"Glyph_Sayisi":str(len(f.glyph_map)),"Format":hex(f.pixel_format)})
        except Exception as ex:
            rows.append({"Dosya":str(p.relative_to(msg_root)),"Eksik_TR":"HATA","Glyph_Sayisi":"","Format":str(ex)})
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open("w",encoding="utf-8-sig",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=["Dosya","Eksik_TR","Glyph_Sayisi","Format"]);w.writeheader();w.writerows(rows)
    progress(f"Font raporu: {out_csv}")
    return rows


def roundtrip_check(msg_root: Path, lang: str="EU_en") -> List[str]:
    problems=[]
    root=Path(msg_root)/lang
    for p in sorted(root.glob("*.msbt")):
        try:
            b=MSBT(p.read_bytes()).to_bytes()
            if b!=p.read_bytes():problems.append(f"MSBT byte farkı: {p.name}")
        except Exception as ex:problems.append(f"MSBT hata {p.name}: {ex}")
    for p in [root/"BMsg.dat",root/"FMsg.dat"]:
        if not p.exists():continue
        try:
            bg=BG4(p.read_bytes())
            b=bg.to_bytes()
            if b!=p.read_bytes():problems.append(f"BG4 byte farkı: {p.name}")
            for e in bg.valid_entries:
                mb=MSBT(e.data).to_bytes()
                if mb!=e.data: problems.append(f"{p.name}/{e.name}: MSBT byte farkı");break
        except Exception as ex:problems.append(f"BG4 hata {p.name}: {ex}")
    return problems


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description="Mario & Luigi Superstar Saga 3DS çok-dilli CSV çeviri aracı")
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("unpack",help="ZIP içindeki Msg klasörünü güvenli şekilde çıkar")
    p.add_argument("zip_path",type=Path);p.add_argument("dest_root",type=Path)
    p=sub.add_parser("export",help="Dil dosyalarını yan yana CSV'lere çıkar")
    p.add_argument("msg_root",type=Path);p.add_argument("csv_dir",type=Path);p.add_argument("--overwrite-tr",action="store_true")
    p=sub.add_parser("seed-tr",help="TR sütununu bir kaynak dille doldur")
    p.add_argument("csv_dir",type=Path);p.add_argument("--from-lang",default="EU_en");p.add_argument("--overwrite",action="store_true")
    p=sub.add_parser("build",help="TR sütunundan drop-in Msg klasörü oluştur")
    p.add_argument("msg_root",type=Path);p.add_argument("csv_dir",type=Path);p.add_argument("output_root",type=Path)
    p.add_argument("--base",default="EU_en");p.add_argument("--slot",default="EU_en");p.add_argument("--allow-tag-changes",action="store_true");p.add_argument("--no-font-patch",action="store_true")
    p=sub.add_parser("font-report",help="BFFNT Türkçe karakter kapsam raporu")
    p.add_argument("msg_root",type=Path);p.add_argument("out_csv",type=Path)
    p=sub.add_parser("csv-check",help="CSV şeması/kod/glif/MSBT parse teknik kontrolü")
    p.add_argument("csv_dir",type=Path);p.add_argument("--source-lang",default="EU_en")
    p=sub.add_parser("check",help="MSBT/BG4 byte-identik roundtrip testi")
    p.add_argument("msg_root",type=Path);p.add_argument("--lang",default="EU_en")
    a=ap.parse_args(argv)
    try:
        if a.cmd=="unpack": extract_msg_from_zip(a.zip_path,a.dest_root)
        elif a.cmd=="export": export_project(a.msg_root,a.csv_dir,not a.overwrite_tr)
        elif a.cmd=="seed-tr": seed_tr(a.csv_dir,a.from_lang,not a.overwrite)
        elif a.cmd=="build":
            r=build_project(a.msg_root,a.csv_dir,a.output_root,a.base,a.slot,a.allow_tag_changes,not a.no_font_patch)
            print(f"Tamamlandı: {r['changed']} metin; çıktı: {r['output']}")
            if r['warnings']:
                print(f"UYARI: {len(r['warnings'])} satır build_report.txt içinde")
        elif a.cmd=="font-report": font_report(a.msg_root,a.out_csv)
        elif a.cmd=="csv-check":
            total,problems=csv_project_check(a.csv_dir,a.source_lang)
            if problems:
                print(f"CSV teknik kontrolü: {len(problems)} sorun / {total} satır")
                for x in problems: print(" -",x)
                return 2
            print(f"CSV teknik kontrolü başarılı: {total} satır; şema, kontrol kodu, özel glif ve MSBT parse/render temiz.")
        elif a.cmd=="check":
            problems=roundtrip_check(a.msg_root,a.lang)
            if problems:
                print("Roundtrip sorunları:")
                for x in problems:print(" -",x)
                return 2
            print("Roundtrip testi başarılı: MSBT ve BG4 dosyaları byte-identik yeniden üretildi.")
        return 0
    except Exception as ex:
        print(f"HATA: {ex}",file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
