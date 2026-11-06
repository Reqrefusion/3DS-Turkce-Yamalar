from __future__ import annotations
import re, struct
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple

_TOKEN_RE = re.compile(r"\{\{(?:CTRL|U16)\|.*?\}\}")

def _endian(data: bytes) -> str:
    if data[:4] != b"FFNT" or data[4:6] not in (b"\xff\xfe", b"\xfe\xff"):
        raise ValueError("Geçerli BFFNT/FFNT başlığı bulunamadı")
    return "<" if data[4:6] == b"\xff\xfe" else ">"

def cmap_from_bffnt(data: bytes) -> Dict[int, int]:
    endian = _endian(data)
    candidates = [i for i in range(0, len(data)-20) if data.startswith(b"CMAP", i)]
    cmap: Dict[int, int] = {}
    for off in candidates:
        try:
            size = struct.unpack_from(endian + "I", data, off + 4)[0]
            if size < 20 or off + size > len(data):
                continue
            begin, end, method, _reserved, _next = struct.unpack_from(endian + "HHHHI", data, off + 8)
            p = off + 20
            if method == 0:
                idx0 = struct.unpack_from(endian + "H", data, p)[0]
                for cp in range(begin, end + 1):
                    cmap[cp] = idx0 + (cp - begin)
            elif method == 1:
                count = end - begin + 1
                if p + count * 2 > off + size:
                    continue
                vals = struct.unpack_from(endian + f"{count}H", data, p)
                for cp, idx in zip(range(begin, end + 1), vals):
                    if idx != 0xFFFF:
                        cmap[cp] = idx
            elif method == 2:
                count = struct.unpack_from(endian + "H", data, p)[0]
                p += 2
                if p + count * 4 > off + size:
                    continue
                for _ in range(count):
                    cp, idx = struct.unpack_from(endian + "HH", data, p)
                    p += 4
                    cmap[cp] = idx
        except (struct.error, ValueError):
            continue
    if not cmap:
        raise ValueError("BFFNT içinde okunabilir CMAP bulunamadı")
    return cmap

def glyph_widths_from_bffnt(data: bytes) -> Dict[int, Tuple[int,int,int]]:
    endian = _endian(data)
    widths: Dict[int, Tuple[int,int,int]] = {}
    candidates = [i for i in range(0, len(data)-16) if data.startswith(b"CWDH", i)]
    for off in candidates:
        try:
            size = struct.unpack_from(endian+"I", data, off+4)[0]
            if size < 16 or off + size > len(data): continue
            start, end = struct.unpack_from(endian+"HH", data, off+8)
            p = off+16
            for idx in range(start,end+1):
                if p+3 > off+size: break
                left = struct.unpack_from("b", data, p)[0]
                glyph = data[p+1]
                advance = data[p+2]
                widths[idx] = (left,glyph,advance)
                p += 3
        except (struct.error, ValueError):
            continue
    if not widths:
        raise ValueError("BFFNT içinde okunabilir CWDH bulunamadı")
    return widths

def char_advance_widths(data: bytes) -> Dict[int,int]:
    cmap = cmap_from_bffnt(data)
    glyphs = glyph_widths_from_bffnt(data)
    return {cp:glyphs[idx][2] for cp,idx in cmap.items() if idx in glyphs}

def clean_rendered_text(text: str) -> str:
    return _TOKEN_RE.sub("", text or "")

def text_line_widths(text: str, advances: Dict[int,int]) -> list[int]:
    lines=(text or "").splitlines() or [""]
    return [sum(advances.get(ord(ch),0) for ch in clean_rendered_text(line)) for line in lines]

def missing_chars(font_path: str | Path, texts: Iterable[str]) -> Set[str]:
    cmap = cmap_from_bffnt(Path(font_path).read_bytes())
    missing: Set[str] = set()
    for text in texts:
        clean = clean_rendered_text(text)
        for ch in clean:
            if ch in "\r\n\t":
                continue
            cp = ord(ch)
            if cp >= 0x20 and cp not in cmap:
                missing.add(ch)
    return missing
