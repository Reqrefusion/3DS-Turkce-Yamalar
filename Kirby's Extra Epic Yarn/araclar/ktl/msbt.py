from __future__ import annotations
import re, struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

CTRL_RE = re.compile(r"\{\{CTRL\|([0-9A-Fa-f]{4})\|([0-9A-Fa-f]{4})\|([0-9A-Fa-f]*)\}\}")

@dataclass
class Section:
    magic: str
    header_offset: int
    data_offset: int
    size: int

@dataclass
class MsbtFile:
    raw: bytes
    endian: str
    encoding: int
    labels: List[str]
    texts: List[str]
    sections: Dict[str, Section]

    @staticmethod
    def from_bytes(raw: bytes) -> "MsbtFile":
        if raw[:8] != b"MsgStdBn":
            raise ValueError("MSBT magic bulunamadı")
        bom = raw[8:10]
        if bom == b"\xff\xfe":
            endian = "<"
            codec = "utf-16le"
        elif bom == b"\xfe\xff":
            endian = ">"
            codec = "utf-16be"
        else:
            raise ValueError(f"Bilinmeyen MSBT BOM: {bom.hex()}")
        encoding = raw[12]
        if encoding != 1:
            raise ValueError(f"Bu araç şu anda UTF-16 MSBT bekliyor (encoding={encoding})")

        sections: Dict[str, Section] = {}
        off = 0x20
        while off + 16 <= len(raw):
            magic_b = raw[off:off+4]
            try:
                magic = magic_b.decode("ascii")
            except UnicodeDecodeError:
                break
            if not magic.strip("\x00"):
                break
            size = struct.unpack_from(endian + "I", raw, off + 4)[0]
            if off + 16 + size > len(raw):
                raise ValueError(f"Bozuk bölüm: {magic}")
            sections[magic] = Section(magic, off, off + 16, size)
            off = (off + 16 + size + 15) & ~15

        if "LBL1" not in sections or "TXT2" not in sections:
            raise ValueError("MSBT içinde LBL1/TXT2 bölümü yok")

        lbl = sections["LBL1"]
        d = lbl.data_offset
        group_count = struct.unpack_from(endian + "I", raw, d)[0]
        label_map: Dict[int, str] = {}
        for gi in range(group_count):
            count, rel = struct.unpack_from(endian + "II", raw, d + 4 + gi * 8)
            pos = d + rel
            for _ in range(count):
                ln = raw[pos]
                pos += 1
                name = raw[pos:pos+ln].decode("utf-8")
                pos += ln
                idx = struct.unpack_from(endian + "I", raw, pos)[0]
                pos += 4
                label_map[idx] = name

        txt = sections["TXT2"]
        td = txt.data_offset
        count = struct.unpack_from(endian + "I", raw, td)[0]
        offsets = struct.unpack_from(endian + f"{count}I", raw, td + 4)
        texts: List[str] = []
        for i in range(count):
            start = td + offsets[i]
            end = td + (offsets[i+1] if i + 1 < count else txt.size)
            texts.append(_decode_message(raw[start:end], endian, codec))

        labels = [label_map.get(i, f"__INDEX_{i:04d}") for i in range(count)]
        return MsbtFile(raw, endian, encoding, labels, texts, sections)

    @staticmethod
    def from_path(path: str | Path) -> "MsbtFile":
        return MsbtFile.from_bytes(Path(path).read_bytes())

    def to_bytes(self, new_texts: List[str]) -> bytes:
        if len(new_texts) != len(self.texts):
            raise ValueError(f"Metin sayısı değişemez: {len(new_texts)} != {len(self.texts)}")
        txt = self.sections["TXT2"]
        codec = "utf-16le" if self.endian == "<" else "utf-16be"

        encoded = [_encode_message(t, self.endian, codec) for t in new_texts]
        count = len(encoded)
        table_size = 4 + 4 * count
        offsets: List[int] = []
        pos = table_size
        for b in encoded:
            offsets.append(pos)
            pos += len(b)
        payload = bytearray()
        payload += struct.pack(self.endian + "I", count)
        payload += struct.pack(self.endian + f"{count}I", *offsets)
        for b in encoded:
            payload += b

        old_start = txt.header_offset
        old_end_aligned = (txt.header_offset + 16 + txt.size + 15) & ~15
        sec_header = bytearray(self.raw[txt.header_offset:txt.data_offset])
        struct.pack_into(self.endian + "I", sec_header, 4, len(payload))
        new_section = sec_header + payload
        new_section += b"\x00" * ((16 - (len(new_section) % 16)) % 16)

        out = bytearray(self.raw[:old_start])
        out += new_section
        out += self.raw[old_end_aligned:]
        # File size is stored at 0x12 for MsgStdBn v3 used here.
        struct.pack_into(self.endian + "I", out, 0x12, len(out))
        return bytes(out)


def _decode_message(raw: bytes, endian: str, codec: str) -> str:
    out: List[str] = []
    pos = 0
    while pos + 2 <= len(raw):
        u = struct.unpack_from(endian + "H", raw, pos)[0]
        if u == 0:
            break
        if u == 0x000E:
            if pos + 8 > len(raw):
                raise ValueError("Kesik MSBT kontrol kodu")
            group, typ, size = struct.unpack_from(endian + "HHH", raw, pos + 2)
            end = pos + 8 + size
            if end > len(raw):
                raise ValueError("Geçersiz MSBT kontrol kodu uzunluğu")
            data = raw[pos+8:end]
            out.append(f"{{{{CTRL|{group:04X}|{typ:04X}|{data.hex().upper()}}}}}")
            pos = end
            continue
        # Preserve any unusual non-text code unit losslessly.
        if u < 0x20 and u not in (9, 10, 13):
            out.append(f"{{{{U16|{u:04X}}}}}")
            pos += 2
            continue
        out.append(raw[pos:pos+2].decode(codec, errors="strict"))
        pos += 2
    return "".join(out)


def _encode_message(text: str, endian: str, codec: str) -> bytes:
    out = bytearray()
    pos = 0
    token_re = re.compile(r"\{\{CTRL\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]*\}\}|\{\{U16\|[0-9A-Fa-f]{4}\}\}")
    for m in token_re.finditer(text):
        out += text[pos:m.start()].encode(codec)
        token = m.group(0)
        if token.startswith("{{CTRL|"):
            cm = CTRL_RE.fullmatch(token)
            assert cm
            group = int(cm.group(1), 16)
            typ = int(cm.group(2), 16)
            data = bytes.fromhex(cm.group(3))
            out += struct.pack(endian + "HHHH", 0x000E, group, typ, len(data))
            out += data
        else:
            u = int(token[6:10], 16)
            out += struct.pack(endian + "H", u)
        pos = m.end()
    out += text[pos:].encode(codec)
    out += struct.pack(endian + "H", 0)
    return bytes(out)


def control_tokens(text: str) -> List[str]:
    return re.findall(r"\{\{CTRL\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]*\}\}", text)
