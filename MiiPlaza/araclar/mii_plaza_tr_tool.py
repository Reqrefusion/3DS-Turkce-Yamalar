#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StreetPass Mii Plaza (CTR-N-HMEP / EUR) Turkish localization helper.

Pure-Python workflow:
  1) extract  : CXI (or a ZIP containing one) -> RomFS directory
  2) export   : all EU MEET.msbt languages -> one UTF-8-SIG CSV + Turkish column
  3) build    : Turkish CSV -> Luma3DS LayeredFS tree; optionally patch the font
  4) validate : check tags, line counts and rendered-width hints before build

No Nintendo SDK or Kuriimu dependency is required. The CXI extractor expects a
*decrypted/plaintext RomFS*. If the Level-3 RomFS header cannot be found, dump a
decrypted CXI/RomFS with GodMode9 first.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

U32_NONE = 0xFFFFFFFF
LANG_FOLDERS = [
    ("EU_English", "English"),
    ("EU_French", "French"),
    ("EU_German", "German"),
    ("EU_Spanish", "Spanish"),
    ("EU_Italian", "Italian"),
    ("EU_Dutch", "Dutch"),
    ("EU_Portuguese", "Portuguese"),
    ("EU_Russian", "Russian"),
]
LANG_DISPLAY = dict(LANG_FOLDERS)
DISPLAY_FOLDER = {v: k for k, v in LANG_FOLDERS}
TOKEN_RE = re.compile(r"\[\[(TAG|/TAG):(\d+):(\d+)(?::([0-9A-Fa-f]*))?\]\]|\[\[CHR:([0-9A-Fa-f]{4,6})\]\]")


def align(value: int, boundary: int) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def safe_name(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_")


# ---------------------------------------------------------------------------
# Nintendo LZ11
# ---------------------------------------------------------------------------

def lz11_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x11:
        raise ValueError("Dosya LZ11 (0x11) değil.")
    size = int.from_bytes(data[1:4], "little")
    pos = 4
    if size == 0:
        size = int.from_bytes(data[pos:pos+4], "little")
        pos += 4
    out = bytearray()
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not (flags & (1 << bit)):
                out.append(data[pos])
                pos += 1
                continue
            b1 = data[pos]
            hi = b1 >> 4
            if hi == 0:
                b2, b3 = data[pos+1], data[pos+2]
                pos += 3
                length = ((b1 & 0xF) << 4 | (b2 >> 4)) + 0x11
                disp = ((b2 & 0xF) << 8 | b3) + 1
            elif hi == 1:
                b2, b3, b4 = data[pos+1], data[pos+2], data[pos+3]
                pos += 4
                length = ((b1 & 0xF) << 12 | b2 << 4 | (b3 >> 4)) + 0x111
                disp = ((b3 & 0xF) << 8 | b4) + 1
            else:
                b2 = data[pos+1]
                pos += 2
                length = hi + 1
                disp = ((b1 & 0xF) << 8 | b2) + 1
            if disp > len(out):
                raise ValueError("Bozuk LZ11 geri başvuru mesafesi.")
            for _ in range(length):
                out.append(out[-disp])
                if len(out) >= size:
                    break
    return bytes(out)


def lz11_store(data: bytes) -> bytes:
    """Valid LZ11 stream using literal-only groups. Bigger, but very robust."""
    n = len(data)
    if n < 0x1000000:
        out = bytearray([0x11]) + n.to_bytes(3, "little")
    else:
        out = bytearray([0x11, 0, 0, 0]) + n.to_bytes(4, "little")
    for i in range(0, n, 8):
        out.append(0x00)
        out.extend(data[i:i+8])
    return bytes(out)


# ---------------------------------------------------------------------------
# CXI/NCCH and 3DS RomFS extraction
# ---------------------------------------------------------------------------

def read_cxi_bytes(path: Path) -> Tuple[bytes, str]:
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path, "r") as zf:
            members = [n for n in zf.namelist() if n.lower().endswith(".cxi")]
            if len(members) != 1:
                raise ValueError(f"ZIP içinde tam bir CXI bekleniyordu; bulunan: {len(members)}")
            return zf.read(members[0]), members[0]
    return path.read_bytes(), path.name


def ncch_program_id(cxi: bytes) -> int:
    if len(cxi) < 0x200 or cxi[0x100:0x104] != b"NCCH":
        raise ValueError("Geçerli bir NCCH/CXI başlığı bulunamadı.")
    return struct.unpack_from("<Q", cxi, 0x118)[0]


def ncch_product_code(cxi: bytes) -> str:
    return cxi[0x150:0x160].split(b"\0", 1)[0].decode("ascii", "replace")


def extract_romfs_from_cxi(cxi: bytes, out_dir: Path) -> Dict[str, str]:
    if cxi[0x100:0x104] != b"NCCH":
        raise ValueError("NCCH/CXI sihri bulunamadı.")
    rom_units, rom_size_units = struct.unpack_from("<II", cxi, 0x1B0)
    rom_off, rom_size = rom_units * 0x200, rom_size_units * 0x200
    rom = cxi[rom_off:rom_off + rom_size]
    if len(rom) < 0x1028 or rom[:4] != b"IVFC":
        raise ValueError("RomFS/IVFC bulunamadı.")
    # On 3DS RomFS the actual Level-3 filesystem starts at physical +0x1000.
    l3 = rom[0x1000:]
    if len(l3) < 0x28 or struct.unpack_from("<I", l3, 0)[0] != 0x28:
        raise ValueError(
            "RomFS Level-3 başlığı okunamadı. CXI büyük olasılıkla şifreli; "
            "GodMode9 ile decrypted CXI/RomFS dökümü kullanın."
        )
    hdr = struct.unpack_from("<10I", l3, 0)
    _, dho, dhl, dmo, dml, fho, fhl, fmo, fml, fdo = hdr
    dmeta = l3[dmo:dmo+dml]
    fmeta = l3[fmo:fmo+fml]
    if not dmeta or not fmeta:
        raise ValueError("RomFS metadata tabloları geçersiz.")

    def dentry(off: int):
        parent, sibling, child, first_file, hnext, nlen = struct.unpack_from("<6I", dmeta, off)
        name = dmeta[off+0x18:off+0x18+nlen].decode("utf-16le") if nlen else ""
        return parent, sibling, child, first_file, hnext, nlen, name

    def fentry(off: int):
        parent, sibling = struct.unpack_from("<II", fmeta, off)
        data_off, data_len = struct.unpack_from("<QQ", fmeta, off+8)
        hnext, nlen = struct.unpack_from("<II", fmeta, off+0x18)
        name = fmeta[off+0x20:off+0x20+nlen].decode("utf-16le") if nlen else ""
        return parent, sibling, data_off, data_len, hnext, nlen, name

    out_dir.mkdir(parents=True, exist_ok=True)
    seen_d, seen_f = set(), set()
    file_count = 0

    def walk(doff: int, parent_path: Path):
        nonlocal file_count
        if doff in seen_d:
            return
        seen_d.add(doff)
        _, _, child, first_file, _, _, name = dentry(doff)
        here = parent_path / name if name else parent_path
        here.mkdir(parents=True, exist_ok=True)
        fo = first_file
        while fo != U32_NONE:
            if fo in seen_f:
                break
            seen_f.add(fo)
            _, sibling, data_off, data_len, _, _, fname = fentry(fo)
            start = fdo + data_off
            payload = l3[start:start+data_len]
            (here / fname).write_bytes(payload)
            file_count += 1
            fo = sibling
        co = child
        while co != U32_NONE:
            sibling = dentry(co)[1]
            walk(co, here)
            co = sibling

    walk(0, out_dir)
    tid = ncch_program_id(cxi)
    return {
        "title_id": f"{tid:016X}",
        "product_code": ncch_product_code(cxi),
        "files": str(file_count),
        "romfs_offset": f"0x{rom_off:X}",
    }


# ---------------------------------------------------------------------------
# MSBT v3 read/write
# ---------------------------------------------------------------------------
@dataclass
class Section:
    tag: str
    pos: int
    data_pos: int
    size: int
    raw_header: bytes
    raw_data: bytes


def msbt_sections(blob: bytes) -> List[Section]:
    if blob[:8] != b"MsgStdBn":
        raise ValueError("MSBT sihri MsgStdBn bulunamadı.")
    count = struct.unpack_from("<H", blob, 0x0E)[0]
    pos = 0x20
    sections = []
    for _ in range(count):
        tag = blob[pos:pos+4].decode("ascii", "strict")
        size = struct.unpack_from("<I", blob, pos+4)[0]
        sections.append(Section(tag, pos, pos+0x10, size, blob[pos:pos+0x10], blob[pos+0x10:pos+0x10+size]))
        pos = align(pos + 0x10 + size, 0x10)
    return sections


def escape_char(ch: str) -> str:
    cp = ord(ch)
    if 0xE000 <= cp <= 0xF8FF:
        return f"[[CHR:{cp:04X}]]"
    return ch


def decode_msbt_string(raw: bytes) -> str:
    pos = 0
    out: List[str] = []
    normal = bytearray()

    def flush():
        if normal:
            s = normal.decode("utf-16le", "surrogatepass")
            out.extend(escape_char(ch) for ch in s)
            normal.clear()

    while pos + 2 <= len(raw):
        u = struct.unpack_from("<H", raw, pos)[0]
        if u == 0:
            break
        if u == 0x000E:
            flush()
            group, typ, size = struct.unpack_from("<HHH", raw, pos+2)
            extra = raw[pos+8:pos+8+size]
            out.append(f"[[TAG:{group}:{typ}:{extra.hex().upper()}]]")
            pos += 8 + size
        elif u == 0x000F:
            flush()
            group, typ = struct.unpack_from("<HH", raw, pos+2)
            out.append(f"[[/TAG:{group}:{typ}]]")
            pos += 6
        else:
            # Preserve a surrogate pair as normal UTF-16.
            if 0xD800 <= u <= 0xDBFF and pos + 4 <= len(raw):
                normal.extend(raw[pos:pos+4])
                pos += 4
            else:
                normal.extend(raw[pos:pos+2])
                pos += 2
    flush()
    return "".join(out)


def encode_msbt_string(text: str) -> bytes:
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(text):
        out.extend(text[pos:m.start()].encode("utf-16le", "surrogatepass"))
        token = m.group(0)
        if token.startswith("[[CHR:"):
            cp = int(m.group(5), 16)
            out.extend(chr(cp).encode("utf-16le"))
        else:
            kind = m.group(1)
            group, typ = int(m.group(2)), int(m.group(3))
            if kind == "TAG":
                extra = bytes.fromhex(m.group(4) or "")
                out.extend(struct.pack("<HHHH", 0x000E, group, typ, len(extra)))
                out.extend(extra)
            else:
                out.extend(struct.pack("<HHH", 0x000F, group, typ))
        pos = m.end()
    out.extend(text[pos:].encode("utf-16le", "surrogatepass"))
    out.extend(b"\x00\x00")
    return bytes(out)


def parse_msbt(path: Path) -> Tuple[Dict[int, str], List[str], bytes]:
    blob = path.read_bytes()
    sec = {s.tag: s for s in msbt_sections(blob)}
    if "LBL1" not in sec or "TXT2" not in sec:
        raise ValueError(f"{path}: LBL1/TXT2 yok")

    # LBL1 labels are hash-bucketed, but each record stores the TXT2 index.
    d = sec["LBL1"].raw_data
    group_count = struct.unpack_from("<I", d, 0)[0]
    labels: Dict[int, str] = {}
    for i in range(group_count):
        n, off = struct.unpack_from("<II", d, 4 + i*8)
        q = off
        for _ in range(n):
            ln = d[q]
            q += 1
            label = d[q:q+ln].decode("ascii")
            q += ln
            idx = struct.unpack_from("<I", d, q)[0]
            q += 4
            labels[idx] = label

    t = sec["TXT2"].raw_data
    count = struct.unpack_from("<I", t, 0)[0]
    offsets = list(struct.unpack_from(f"<{count}I", t, 4))
    texts: List[str] = []
    for i, off in enumerate(offsets):
        end = offsets[i+1] if i+1 < count else len(t)
        texts.append(decode_msbt_string(t[off:end]))
    return labels, texts, blob


def rebuild_msbt(base_blob: bytes, texts: List[str]) -> bytes:
    sections = msbt_sections(base_blob)
    txt_sec = next((s for s in sections if s.tag == "TXT2"), None)
    if txt_sec is None:
        raise ValueError("TXT2 bölümü yok")
    # Build TXT2 payload.
    encoded = [encode_msbt_string(s) for s in texts]
    base_off = 4 + 4 * len(encoded)
    offsets = []
    cur = base_off
    for item in encoded:
        offsets.append(cur)
        cur += len(item)
    payload = bytearray(struct.pack("<I", len(encoded)))
    payload.extend(struct.pack(f"<{len(offsets)}I", *offsets))
    for item in encoded:
        payload.extend(item)

    out = bytearray(base_blob[:0x20])
    for s in sections:
        data = bytes(payload) if s.tag == "TXT2" else s.raw_data
        hdr = bytearray(s.raw_header)
        struct.pack_into("<I", hdr, 4, len(data))
        out.extend(hdr)
        out.extend(data)
        while len(out) % 0x10:
            out.append(0xAB)
    struct.pack_into("<I", out, 0x12, len(out))
    return bytes(out)


# ---------------------------------------------------------------------------
# BCFNT width reader + Turkish glyph patch
# ---------------------------------------------------------------------------
@dataclass
class FontInfo:
    char_to_index: Dict[int, int]
    widths: Dict[int, Tuple[int, int, int]]
    default_char_width: int


def parse_bcfnt(font_blob: bytes) -> FontInfo:
    if font_blob[:4] not in (b"CFNT", b"CFNU"):
        raise ValueError("BCFNT/CFNT sihri yok")
    finf = font_blob.find(b"FINF")
    if finf < 0:
        raise ValueError("FINF bulunamadı")
    default_char_width = font_blob[finf + 0x0E]
    char_map: Dict[int, int] = {}
    for pos in [i for i in range(len(font_blob)) if font_blob.startswith(b"CMAP", i)]:
        _, size, start, end, typ, reserved, nxt = struct.unpack_from("<4sI4HI", font_blob, pos)
        q = pos + 0x14
        if typ == 0:
            idx0 = struct.unpack_from("<H", font_blob, q)[0]
            for cp in range(start, end+1):
                char_map[cp] = idx0 + cp - start
        elif typ == 1:
            for cp in range(start, end+1):
                idx = struct.unpack_from("<H", font_blob, q + 2*(cp-start))[0]
                if idx != 0xFFFF:
                    char_map[cp] = idx
        elif typ == 2:
            count = struct.unpack_from("<H", font_blob, q)[0]
            q += 2
            for k in range(count):
                cp, idx = struct.unpack_from("<HH", font_blob, q + 4*k)
                char_map[cp] = idx

    widths: Dict[int, Tuple[int, int, int]] = {}
    for pos in [i for i in range(len(font_blob)) if font_blob.startswith(b"CWDH", i)]:
        _, size, start, end, nxt = struct.unpack_from("<4sI2HI", font_blob, pos)
        q = pos + 0x10
        for idx in range(start, end+1):
            left = struct.unpack_from("<b", font_blob, q)[0]
            glyphw = font_blob[q+1]
            charw = font_blob[q+2]
            widths[idx] = (left, glyphw, charw)
            q += 3
    return FontInfo(char_map, widths, default_char_width)


def visible_text(text: str) -> str:
    text = re.sub(r"\[\[(?:/?TAG):[^\]]*\]\]", "", text)
    text = re.sub(r"\[\[CHR:([0-9A-Fa-f]{4,6})\]\]", lambda m: chr(int(m.group(1), 16)), text)
    return text


def tag_signature(text: str) -> List[str]:
    return [m.group(0) for m in re.finditer(r"\[\[(?:/?TAG):[^\]]*\]\]|\[\[CHR:[0-9A-Fa-f]{4,6}\]\]", text)]


def text_line_widths(text: str, font: Optional[FontInfo], turkish_fallback: bool = False) -> List[int]:
    vis = visible_text(text)
    lines = vis.split("\n")
    if not font:
        return [len(line) for line in lines]
    fallback_chars = {
        ord("Ğ"): ord("G"), ord("ğ"): ord("g"), ord("İ"): ord("I"), ord("ı"): ord("i"),
        ord("Ş"): ord("S"), ord("ş"): ord("s"),
    }
    result = []
    for line in lines:
        total = 0
        for ch in line:
            cp = ord(ch)
            idx = font.char_to_index.get(cp)
            if idx is None and turkish_fallback and cp in fallback_chars:
                idx = font.char_to_index.get(fallback_chars[cp])
            if idx is None:
                total += font.default_char_width
            else:
                total += font.widths.get(idx, (0, 0, font.default_char_width))[2]
        result.append(total)
    return result


def _morton8(x: int, y: int) -> int:
    return ((x & 1) | ((y & 1) << 1) | ((x & 2) << 1) | ((y & 2) << 2) | ((x & 4) << 2) | ((y & 4) << 3))


def _decode_la4_glyph(blob: bytes, tglp: int, glyph_index: int) -> Tuple[List[List[int]], List[List[int]]]:
    cell_w, cell_h, baseline, max_w = struct.unpack_from("<4B", blob, tglp+8)
    sheet_size = struct.unpack_from("<I", blob, tglp+0x0C)[0]
    sheet_count, fmt, cols, rows, sheet_w, sheet_h = struct.unpack_from("<6H", blob, tglp+0x10)
    data_ptr = struct.unpack_from("<I", blob, tglp+0x1C)[0]
    if fmt != 9 or sheet_w != 64 or cols != 1:
        raise ValueError("Bu otomatik font yamacısı yalnızca beklenen LA4/64px Mii Plaza font düzenini destekliyor.")
    per_sheet = cols * rows
    sheet = glyph_index // per_sheet
    slot = glyph_index % per_sheet
    if sheet >= sheet_count:
        raise ValueError("Glyph index sheet dışında")
    y0 = (slot // cols) * (sheet_h // rows)
    x0 = (slot % cols) * (sheet_w // cols)
    lum = [[0]*64 for _ in range(64)]
    alp = [[0]*64 for _ in range(64)]
    raw = blob[data_ptr + sheet*sheet_size:data_ptr + (sheet+1)*sheet_size]
    tiles_per_row = sheet_w // 8
    for yy in range(64):
        y = y0 + yy
        for xx in range(64):
            x = x0 + xx
            tile = (y//8) * tiles_per_row + (x//8)
            v = raw[tile*64 + _morton8(x & 7, y & 7)]
            lum[yy][xx] = (v >> 4) & 0xF
            alp[yy][xx] = v & 0xF
    return lum, alp


def _write_la4_glyph(buf: bytearray, tglp: int, glyph_index: int, lum, alp):
    sheet_size = struct.unpack_from("<I", buf, tglp+0x0C)[0]
    sheet_count, fmt, cols, rows, sheet_w, sheet_h = struct.unpack_from("<6H", buf, tglp+0x10)
    data_ptr = struct.unpack_from("<I", buf, tglp+0x1C)[0]
    per_sheet = cols * rows
    sheet = glyph_index // per_sheet
    slot = glyph_index % per_sheet
    y0 = (slot // cols) * (sheet_h // rows)
    x0 = (slot % cols) * (sheet_w // cols)
    tiles_per_row = sheet_w // 8
    for yy in range(64):
        y = y0 + yy
        for xx in range(64):
            x = x0 + xx
            tile = (y//8) * tiles_per_row + (x//8)
            p = data_ptr + sheet*sheet_size + tile*64 + _morton8(x & 7, y & 7)
            buf[p] = ((lum[yy][xx] & 0xF) << 4) | (alp[yy][xx] & 0xF)


def _bbox(mask, threshold=1):
    pts = [(x,y) for y,row in enumerate(mask) for x,v in enumerate(row) if v >= threshold]
    if not pts:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs)+1, max(ys)+1


def _copy_pair(lum, alp):
    return [r[:] for r in lum], [r[:] for r in alp]


def _overlay(dst_l, dst_a, src_l, src_a, dx=0, dy=0, src_box=None):
    if src_box is None:
        src_box = (0,0,64,64)
    x0,y0,x1,y1 = src_box
    for sy in range(y0,y1):
        ty = sy + dy
        if not (0 <= ty < 64): continue
        for sx in range(x0,x1):
            tx = sx + dx
            if not (0 <= tx < 64): continue
            # Max-composite works well for monochrome outlined glyph layers.
            dst_a[ty][tx] = max(dst_a[ty][tx], src_a[sy][sx])
            dst_l[ty][tx] = max(dst_l[ty][tx], src_l[sy][sx])


def _erase_box(lum, alp, box):
    x0,y0,x1,y1 = box
    for y in range(max(0,y0), min(64,y1)):
        for x in range(max(0,x0), min(64,x1)):
            lum[y][x] = 0; alp[y][x] = 0


def _draw_breve(lum, alp, cx: int, top: int, width: int):
    # A small U-shaped breve. Two thicknesses reproduce the font's light face + dark outline.
    # Coordinates are generated analytically to avoid Pillow dependency.
    half = max(4, width // 2)
    for x in range(cx-half, cx+half+1):
        if not (0 <= x < 64): continue
        norm = abs(x-cx) / max(1, half)
        y = int(round(top + 4 * (1 - norm*norm)))  # lower in the middle => U shape
        for yy in range(y-2, y+3):
            if 0 <= yy < 64:
                alp[yy][x] = max(alp[yy][x], 15)
        for yy in range(y-1, y+2):
            if 0 <= yy < 64:
                lum[yy][x] = max(lum[yy][x], 15)


def patch_turkish_font(decompressed: bytes) -> bytes:
    info = parse_bcfnt(decompressed)
    needed = "ĞğİıŞş"
    if all(ord(ch) in info.char_to_index for ch in needed):
        return decompressed

    tglp = decompressed.find(b"TGLP")
    cwdh = decompressed.find(b"CWDH")
    cmap_positions = [i for i in range(len(decompressed)) if decompressed.startswith(b"CMAP", i)]
    finf = decompressed.find(b"FINF")
    if min(tglp, cwdh, finf) < 0 or not cmap_positions:
        raise ValueError("Font blokları bulunamadı")
    sheet_size = struct.unpack_from("<I", decompressed, tglp+0x0C)[0]
    sheet_count = struct.unpack_from("<H", decompressed, tglp+0x10)[0]
    rows = struct.unpack_from("<H", decompressed, tglp+0x16)[0]
    cols = struct.unpack_from("<H", decompressed, tglp+0x14)[0]
    capacity = sheet_count * rows * cols
    max_index = max(info.char_to_index.values())
    first_new = max_index + 1
    need_count = len(needed)
    extra_slots = first_new + need_count - capacity
    add_sheets = max(0, (extra_slots + rows*cols - 1) // (rows*cols))

    # Insert blank sheet(s) immediately before CWDH. This keeps texture data contiguous.
    insertion = b"\x00" * (sheet_size * add_sheets)
    buf = bytearray(decompressed[:cwdh] + insertion + decompressed[cwdh:])
    new_cwdh_pos = cwdh + len(insertion)
    # TGLP metadata
    struct.pack_into("<I", buf, tglp+4, struct.unpack_from("<I", decompressed, tglp+4)[0] + len(insertion))
    struct.pack_into("<H", buf, tglp+0x10, sheet_count + add_sheets)

    # Existing source glyphs can still be decoded from the shifted buffer because TGLP data didn't move.
    current_info = parse_bcfnt(bytes(buf))
    src_idx = {ch: current_info.char_to_index[ord(ch)] for ch in "GgIiSsCcÇç"}
    glyph = {ch: _decode_la4_glyph(bytes(buf), tglp, idx) for ch, idx in src_idx.items()}

    made = {}
    # Ğ / ğ
    for outch, basech, top in [("Ğ","G",5),("ğ","g",14)]:
        l,a = _copy_pair(*glyph[basech])
        bb = _bbox(a) or (0,0,40,50)
        cx = (bb[0]+bb[2])//2
        _draw_breve(l,a,cx,top,max(10,(bb[2]-bb[0])//2))
        made[outch]=(l,a)
    # dotless ı: remove upper dot from i.
    l,a = _copy_pair(*glyph["i"])
    bb = _bbox(a)
    if bb:
        # Stem starts roughly below the upper third; remove the isolated top component area.
        _erase_box(l,a,(0,0,64,24))
    made["ı"]=(l,a)
    # dotted İ: this font's lowercase i has no reliably separable dot, so
    # draw a small native-looking dot above I instead of copying one.
    l,a = _copy_pair(*glyph["I"])
    ib = _bbox(a) or (10,10,20,52)
    cx = (ib[0] + ib[2]) // 2
    cy = max(5, ib[1] - 6)
    for yy in range(max(0, cy-3), min(64, cy+4)):
        for xx in range(max(0, cx-3), min(64, cx+4)):
            d2 = (xx-cx)*(xx-cx) + (yy-cy)*(yy-cy)
            if d2 <= 9:
                a[yy][xx] = 15
                l[yy][xx] = max(l[yy][xx], 8)
            if d2 <= 4:
                l[yy][xx] = 15
    made["İ"]=(l,a)
    # Ş / ş: take cedilla from Ç/ç bottom and put beneath S/s.
    for outch, basech, cedch, refbase in [("Ş","S","Ç","C"),("ş","s","ç","c")]:
        l,a = _copy_pair(*glyph[basech])
        cl,ca = glyph[cedch]
        base_ref_a = glyph[refbase][1]
        rb = _bbox(base_ref_a) or (0,0,40,50)
        ced_box = (0, max(0, rb[3]-1), 64, 64)
        sb = _bbox(a) or (0,0,40,50)
        cb = _bbox([[v if y >= ced_box[1] else 0 for v in row] for y,row in enumerate(ca)])
        if cb:
            ccenter=(cb[0]+cb[2])//2; scenter=(sb[0]+sb[2])//2
            desired_top=min(63, sb[3]-1)
            _overlay(l,a,cl,ca,scenter-ccenter,desired_top-cb[1],cb)
        made[outch]=(l,a)

    # Write new glyph pixels, including into formerly-unused slots of the old final sheet.
    new_map = {}
    for j,ch in enumerate(needed):
        idx = first_new + j
        _write_la4_glyph(buf, tglp, idx, *made[ch])
        new_map[ord(ch)] = idx

    # Rebuild CWDH with 6 added width records. It is after the inserted texture sheets.
    old_cwdh_size = struct.unpack_from("<I", buf, new_cwdh_pos+4)[0]
    start_idx, end_idx = struct.unpack_from("<HH", buf, new_cwdh_pos+8)
    old_records = bytearray(buf[new_cwdh_pos+0x10:new_cwdh_pos+0x10+(end_idx-start_idx+1)*3])
    source_width_chars = {"Ğ":"G","ğ":"g","İ":"I","ı":"i","Ş":"S","ş":"s"}
    for ch in needed:
        src = current_info.char_to_index[ord(source_width_chars[ch])]
        old_records.extend(bytes((current_info.widths[src][0] & 0xFF, current_info.widths[src][1], current_info.widths[src][2])))
    new_cwdh_size = align(0x10 + len(old_records), 4)
    cwdh_block = bytearray(new_cwdh_size)
    cwdh_block[:0x10] = buf[new_cwdh_pos:new_cwdh_pos+0x10]
    struct.pack_into("<I", cwdh_block, 4, new_cwdh_size)
    struct.pack_into("<H", cwdh_block, 0x0A, first_new + need_count - 1)
    struct.pack_into("<I", cwdh_block, 0x0C, 0)
    cwdh_block[0x10:0x10+len(old_records)] = old_records

    # Parse original (shifted) CMAP blocks and rebuild them. Extend final scan map.
    shifted_cmaps = [p + len(insertion) for p in cmap_positions]
    cmap_blocks = []
    for p in shifted_cmaps:
        sz = struct.unpack_from("<I", buf, p+4)[0]
        cmap_blocks.append(bytearray(buf[p:p+sz]))
    last = cmap_blocks[-1]
    typ = struct.unpack_from("<H", last, 0x0C)[0]
    if typ != 2:
        raise ValueError("Son CMAP scan tipi değil; otomatik font yaması durduruldu.")
    count = struct.unpack_from("<H", last, 0x14)[0]
    pairs = [struct.unpack_from("<HH", last, 0x16+4*i) for i in range(count)]
    pairs.extend(new_map.items())
    pairs = sorted(dict(pairs).items())
    new_last_size = align(0x16 + 4*len(pairs), 4)
    new_last = bytearray(new_last_size)
    new_last[:0x14] = last[:0x14]
    struct.pack_into("<I", new_last, 4, new_last_size)
    struct.pack_into("<H", new_last, 0x14, len(pairs))
    q=0x16
    for cp,idx in pairs:
        struct.pack_into("<HH", new_last, q, cp, idx); q+=4
    cmap_blocks[-1]=new_last

    # Reassemble from start through TGLP, then new CWDH + all CMAPs.
    prefix = bytearray(buf[:new_cwdh_pos])
    rebuilt = prefix + cwdh_block
    new_cmap_positions=[]
    for block in cmap_blocks:
        new_cmap_positions.append(len(rebuilt))
        rebuilt.extend(block)
    # Fix CMAP chain pointers (pointers target block + 8).
    for i,p in enumerate(new_cmap_positions):
        nxt = new_cmap_positions[i+1] + 8 if i+1 < len(new_cmap_positions) else 0
        struct.pack_into("<I", rebuilt, p+0x10, nxt)
    # FINF pointers: CWDH/CMAP point to section + 8.
    struct.pack_into("<I", rebuilt, finf+0x14, new_cwdh_pos + 8)
    struct.pack_into("<I", rebuilt, finf+0x18, new_cmap_positions[0] + 8)
    # Overall file size.
    struct.pack_into("<I", rebuilt, 0x0C, len(rebuilt))

    check = parse_bcfnt(bytes(rebuilt))
    missing = [ch for ch in needed if ord(ch) not in check.char_to_index]
    if missing:
        raise ValueError("Font yaması doğrulanamadı: " + "".join(missing))
    return bytes(rebuilt)


# ---------------------------------------------------------------------------
# CSV export / validation / LayeredFS build
# ---------------------------------------------------------------------------

def locate_font(romfs: Path) -> Optional[FontInfo]:
    p = romfs / "font" / "MEET_edge.lz77"
    if not p.exists():
        return None
    try:
        return parse_bcfnt(lz11_decompress(p.read_bytes()))
    except Exception as exc:
        print(f"[uyarı] Font ölçüleri okunamadı: {exc}", file=sys.stderr)
        return None


def load_languages(romfs: Path):
    result = {}
    reference_labels = None
    for folder, display in LANG_FOLDERS:
        p = romfs / "message" / folder / "MEET.msbt"
        if not p.exists():
            continue
        labels, texts, blob = parse_msbt(p)
        if reference_labels is None:
            reference_labels = labels
        elif labels != reference_labels:
            raise ValueError(f"Etiket tablosu {folder} içinde diğer dillerle eşleşmiyor.")
        result[display] = (folder, labels, texts, blob)
    if not result:
        raise ValueError("message/EU_*/MEET.msbt bulunamadı")
    return result


def export_csv(romfs: Path, csv_path: Path):
    langs = load_languages(romfs)
    if "English" not in langs:
        raise ValueError("EU_English referansı gerekli")
    font = locate_font(romfs)
    labels = langs["English"][1]
    count = len(langs["English"][2])
    fieldnames = ["Index", "Label"] + [d for _, d in LANG_FOLDERS if d in langs] + [
        "Turkish", "TR_Notes", "Ref_MaxLines", "Ref_MaxLinePx", "Ref_MaxUtf16Bytes"
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for i in range(count):
            row = {"Index": i, "Label": labels.get(i, f"__index_{i}")}
            ref_lines = 1
            ref_px = 0
            ref_bytes = 0
            for _, display in LANG_FOLDERS:
                if display not in langs:
                    continue
                text = langs[display][2][i]
                row[display] = text
                ref_lines = max(ref_lines, len(visible_text(text).split("\n")))
                widths = text_line_widths(text, font)
                ref_px = max(ref_px, max(widths) if widths else 0)
                ref_bytes = max(ref_bytes, len(encode_msbt_string(text)))
            row["Turkish"] = ""
            row["TR_Notes"] = ""
            row["Ref_MaxLines"] = ref_lines
            row["Ref_MaxLinePx"] = ref_px
            row["Ref_MaxUtf16Bytes"] = ref_bytes
            w.writerow(row)
    print(f"CSV yazıldı: {csv_path} ({count} satır, {len(langs)} referans dil)")


def read_translation_csv(csv_path: Path) -> List[dict]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "Turkish" not in rows[0] or "Label" not in rows[0]:
        raise ValueError("CSV'de Label ve Turkish sütunları gerekli")
    return rows


def validate_rows(romfs: Path, rows: List[dict], target_display="English") -> List[str]:
    langs = load_languages(romfs)
    if target_display not in langs:
        raise ValueError(f"Hedef dil yok: {target_display}")
    font = locate_font(romfs)
    _, labels, base_texts, _ = langs[target_display]
    issues=[]
    for row in rows:
        try: i=int(row["Index"])
        except Exception:
            issues.append(f"Index geçersiz: {row.get('Index')}"); continue
        if i < 0 or i >= len(base_texts):
            issues.append(f"{i}: aralık dışında"); continue
        if row.get("Label") != labels.get(i):
            issues.append(f"{i}: Label uyuşmuyor ({row.get('Label')} != {labels.get(i)})")
        tr=row.get("Turkish", "")
        if not tr:
            continue
        base=row.get(target_display, base_texts[i])
        if tag_signature(tr) != tag_signature(base):
            # Order matters for control flow; deliberately strict.
            issues.append(f"{i} {labels.get(i)}: TAG/CHR dizisi hedef dille birebir aynı değil")
        ref_lines=int(row.get("Ref_MaxLines") or 999)
        tr_lines=len(visible_text(tr).split("\n"))
        if tr_lines > ref_lines:
            issues.append(f"{i} {labels.get(i)}: satır sayısı {tr_lines}>{ref_lines}")
        ref_px=int(row.get("Ref_MaxLinePx") or 0)
        tw=max(text_line_widths(tr,font,turkish_fallback=True) or [0])
        # Ref_MaxLinePx is the widest *observed official translation*, not the
        # actual CLYT text-pane boundary. A percentage-only rule is too harsh
        # for very short one-line choices: e.g. Turkish Evet/Hayır can be a
        # few font-design units wider than every shipped language while still
        # occupying only a small fraction of the real choice pane. Keep the
        # conservative +8% rule generally, but give tiny 1-line controls a
        # 150-design-unit floor. Longer labels still use the strict reference.
        width_limit=int(ref_px*1.08)+2 if ref_px else 0
        if ref_lines == 1 and ref_px and ref_px <= 110:
            width_limit=max(width_limit,150)
        if ref_px and tw > width_limit:
            issues.append(f"{i} {labels.get(i)}: yaklaşık satır genişliği {tw}px > güvenli referans {width_limit}px (resmî max {ref_px}px)")
    return issues


def build_layeredfs(romfs: Path, csv_path: Path, out_root: Path, target_folder: str, patch_font_flag: bool, title_id: str, all_languages: bool=False):
    rows=read_translation_csv(csv_path)
    issues=validate_rows(romfs,rows,LANG_DISPLAY.get(target_folder,target_folder))
    if issues:
        print(f"[uyarı] {len(issues)} QA bulgusu var; ilk 40:", file=sys.stderr)
        for x in issues[:40]: print("  -",x,file=sys.stderr)
    base_path=romfs/"message"/target_folder/"MEET.msbt"
    labels, base_texts, base_blob=parse_msbt(base_path)
    tr_texts=base_texts[:]
    filled=0
    by_index={int(r["Index"]):r for r in rows if str(r.get("Index","")).isdigit()}
    for i in range(len(tr_texts)):
        row=by_index.get(i)
        if not row: continue
        tr=row.get("Turkish","")
        if tr != "":
            tr_texts[i]=tr; filled+=1
    patched=rebuild_msbt(base_blob,tr_texts)
    targets=[f for f,_ in LANG_FOLDERS] if all_languages else [target_folder]
    for folder in targets:
        dest=out_root/"luma"/"titles"/title_id/"romfs"/"message"/folder/"MEET.msbt"
        dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(patched)
        print(f"MSBT: {dest} ({filled}/{len(tr_texts)} Turkish hücre kullanıldı)")
    if patch_font_flag:
        src=romfs/"font"/"MEET_edge.lz77"
        decomp=lz11_decompress(src.read_bytes())
        patched_font=patch_turkish_font(decomp)
        packed=lz11_store(patched_font)
        fdest=out_root/"luma"/"titles"/title_id/"romfs"/"font"/"MEET_edge.lz77"
        fdest.parent.mkdir(parents=True,exist_ok=True); fdest.write_bytes(packed)
        print(f"Font: {fdest} (ĞğİıŞş eklendi)")
    readme=out_root/"README_LAYEREDFS.txt"
    locale_text="EU_English, EU_French, EU_German, EU_Spanish, EU_Italian, EU_Dutch, EU_Portuguese, EU_Russian" if all_languages else target_folder
    readme.write_text(
        f"StreetPass Mii Plaza Türkçe LayeredFS\n"
        f"Title ID: {title_id}\n"
        f"Yamalanan dil klasörleri: {locale_text}\n\n"
        f"SD kart köküne bu klasördeki 'luma' klasörünü kopyalayın.\n"
        f"Luma3DS yapılandırmasında Enable game patching açık olmalıdır.\n",
        encoding="utf-8"
    )


def command_extract(args):
    data,name=read_cxi_bytes(Path(args.input))
    out=Path(args.out)
    if out.exists() and args.clean:
        shutil.rmtree(out)
    meta=extract_romfs_from_cxi(data,out/"romfs")
    (out/"title_id.txt").write_text(meta["title_id"]+"\n",encoding="ascii")
    (out/"metadata.txt").write_text("\n".join(f"{k}={v}" for k,v in meta.items())+"\n",encoding="utf-8")
    print(f"{name}: {meta['product_code']} / {meta['title_id']} / {meta['files']} RomFS dosyası")
    print(f"Çıktı: {out/'romfs'}")


def command_export(args):
    export_csv(Path(args.romfs),Path(args.csv))


def command_validate(args):
    rows=read_translation_csv(Path(args.csv))
    target=LANG_DISPLAY.get(args.target,args.target)
    issues=validate_rows(Path(args.romfs),rows,target)
    if not issues:
        print("QA: sorun bulunmadı.")
        return
    print(f"QA: {len(issues)} bulgu")
    for x in issues: print(x)
    sys.exit(2)


def command_build(args):
    tid=args.title_id
    if not tid:
        possible=Path(args.romfs).parent/"title_id.txt"
        if possible.exists(): tid=possible.read_text().strip()
    if not tid:
        tid="0004001000022800"
    if not re.fullmatch(r"[0-9A-Fa-f]{16}",tid):
        raise ValueError("Title ID 16 hex karakter olmalı")
    build_layeredfs(Path(args.romfs),Path(args.csv),Path(args.out),args.target,args.patch_font,tid.upper(),args.all_languages)


def main():
    ap=argparse.ArgumentParser(description="StreetPass Mii Plaza çok-dilli CSV / Türkçe LayeredFS aracı")
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("extract",help="CXI/ZIP -> RomFS çıkar")
    p.add_argument("input"); p.add_argument("--out",default="mii_work"); p.add_argument("--clean",action="store_true"); p.set_defaults(func=command_extract)
    p=sub.add_parser("export",help="RomFS -> tüm diller yan yana CSV")
    p.add_argument("romfs"); p.add_argument("--csv",default="mii_plaza_tr.csv"); p.set_defaults(func=command_export)
    p=sub.add_parser("validate",help="Türkçe sütun için TAG/ölçü QA")
    p.add_argument("romfs"); p.add_argument("csv"); p.add_argument("--target",default="EU_English",choices=[f for f,_ in LANG_FOLDERS]); p.set_defaults(func=command_validate)
    p=sub.add_parser("build",help="CSV -> Luma3DS LayeredFS ağacı")
    p.add_argument("romfs"); p.add_argument("csv"); p.add_argument("--out",default="mii_plaza_tr_patch"); p.add_argument("--target",default="EU_English",choices=[f for f,_ in LANG_FOLDERS]); p.add_argument("--title-id",default=None); p.add_argument("--patch-font",action="store_true"); p.add_argument("--all-languages",action="store_true",help="Aynı doğrulanmış Türkçe MSBT'yi sekiz Avrupa dil klasörüne de yaz"); p.set_defaults(func=command_build)
    args=ap.parse_args()
    args.func(args)

if __name__=="__main__":
    main()
