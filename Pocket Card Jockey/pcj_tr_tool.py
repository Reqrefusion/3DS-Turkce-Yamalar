#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Pocket Card Jockey 3DS message/UI/Pawn text extractor and rebuild utility.

The tool handles the game's encrypted message tables and its
GARC -> LZ11 -> DARC -> BCLYT nesting, exports text to UTF-8 CSV, and rebuilds
only the archives selected for editing. It also scans compact Pawn/AMX scripts,
exports embedded string literals, and writes same-capacity edits back without
changing AMX addresses.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
from pathlib import Path


class FormatError(ValueError):
    pass


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


MESSAGE_KEY_BASE = 0x7C89
MESSAGE_KEY_STEP = 0x2983


def rol16(value: int, count: int) -> int:
    count %= 16
    return ((value << count) | (value >> (16 - count))) & 0xFFFF


def crypt_message_units(units: tuple[int, ...] | list[int], entry_index: int) -> tuple[int, ...]:
    """Encrypt or decrypt one Game Freak message entry (XOR is symmetric)."""
    key = (MESSAGE_KEY_BASE + entry_index * MESSAGE_KEY_STEP) & 0xFFFF
    output = []
    for value in units:
        output.append(value ^ key)
        key = rol16(key, 3)
    return tuple(output)


def parse_message_table(data: bytes) -> dict:
    """Parse the encrypted multi-section message format used in a/0/0/0."""
    if len(data) < 16:
        raise FormatError("truncated message table")
    section_count, entry_count, largest_section, unknown = struct.unpack_from("<HHII", data)
    if not (1 <= section_count <= 8) or entry_count > 0xFFFF:
        raise FormatError("not a supported message table")
    header_size = 12 + 4 * section_count
    if header_size > len(data):
        raise FormatError("truncated message section offsets")
    section_offsets = list(struct.unpack_from(f"<{section_count}I", data, 12))
    if section_offsets[0] != header_size or section_offsets != sorted(section_offsets):
        raise FormatError("invalid message section offsets")

    sections = []
    for section_index, base in enumerate(section_offsets):
        if base + 4 + 8 * entry_count > len(data):
            raise FormatError("truncated message entry table")
        section_size = u32(data, base)
        expected_end = section_offsets[section_index + 1] if section_index + 1 < section_count else len(data)
        if section_size < 4 + 8 * entry_count or base + section_size != expected_end:
            raise FormatError("invalid message section size")
        entries = []
        for entry_index in range(entry_count):
            record = base + 4 + 8 * entry_index
            relative_offset = u32(data, record)
            length, flags = struct.unpack_from("<HH", data, record + 4)
            start = base + relative_offset
            end = start + 2 * length
            if relative_offset < 4 + 8 * entry_count or end > base + section_size:
                raise FormatError("invalid encrypted message range")
            encrypted = struct.unpack_from(f"<{length}H", data, start) if length else ()
            entries.append({
                "offset": relative_offset,
                "length": length,
                "flags": flags,
                "encrypted": tuple(encrypted),
                "units": crypt_message_units(encrypted, entry_index),
            })
        sections.append({"offset": base, "size": section_size, "entries": entries})

    if largest_section != max(section["size"] for section in sections):
        raise FormatError("message largest-section field is inconsistent")
    return {
        "section_count": section_count,
        "entry_count": entry_count,
        "largest_section": largest_section,
        "unknown": unknown,
        "sections": sections,
    }


def rebuild_message_table(parsed: dict, replacements: dict[tuple[int, int], tuple[int, ...]]) -> bytes:
    unknown = set(replacements)
    section_blobs = []
    for section_index, section in enumerate(parsed["sections"]):
        entry_count = parsed["entry_count"]
        rebuilt = bytearray(4 + 8 * entry_count)
        for entry_index, entry in enumerate(section["entries"]):
            key = (section_index, entry_index)
            units = replacements.get(key, entry["units"])
            unknown.discard(key)
            if len(units) > 0xFFFF:
                raise FormatError("translated message is longer than 65535 UTF-16 code units")
            relative_offset = len(rebuilt)
            encrypted = crypt_message_units(units, entry_index)
            rebuilt += struct.pack(f"<{len(encrypted)}H", *encrypted)
            struct.pack_into(
                "<IHH", rebuilt, 4 + 8 * entry_index,
                relative_offset, len(units), entry["flags"],
            )
        while len(rebuilt) % 4:
            rebuilt.append(0)
        struct.pack_into("<I", rebuilt, 0, len(rebuilt))
        section_blobs.append(bytes(rebuilt))
    if unknown:
        raise FormatError(f"unknown message section/entry pairs: {sorted(unknown)}")

    section_count = parsed["section_count"]
    header_size = 12 + 4 * section_count
    offsets = []
    pos = header_size
    for section in section_blobs:
        offsets.append(pos)
        pos += len(section)
    output = bytearray(struct.pack(
        "<HHII", section_count, parsed["entry_count"],
        max(len(section) for section in section_blobs), parsed["unknown"],
    ))
    output += struct.pack(f"<{section_count}I", *offsets)
    output += b"".join(section_blobs)

    check = parse_message_table(bytes(output))
    for key, expected in replacements.items():
        section_index, entry_index = key
        if check["sections"][section_index]["entries"][entry_index]["units"] != expected:
            raise FormatError("rebuilt encrypted message verification failed")
    return bytes(output)


def strip_message_padding(units: tuple[int, ...]) -> tuple[int, ...]:
    end = len(units)
    while end and units[end - 1] == 0:
        end -= 1
    return units[:end]


def escape_message_units(units: tuple[int, ...]) -> str:
    """Make control codes safe and legible in a one-line CSV cell."""
    output = []
    for value in strip_message_padding(units):
        if value == 0:
            output.append(r"\0")
        elif value == 9:
            output.append(r"\t")
        elif value == 10:
            output.append(r"\n")
        elif value == 13:
            output.append(r"\r")
        elif value == 0x5C:
            output.append(r"\\")
        elif 0x20 <= value <= 0x7E:
            output.append(chr(value))
        else:
            output.append(f"\\u{value:04X}")
    return "".join(output)


def unescape_message_text(text: str) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Decode CSV escapes and return UTF-16 units plus protected control tokens."""
    characters = []
    protected = []
    pos = 0
    while pos < len(text):
        char = text[pos]
        if char != "\\":
            characters.append(char)
            pos += 1
            continue
        if pos + 1 >= len(text):
            raise FormatError("message text ends with an incomplete backslash escape")
        kind = text[pos + 1]
        if kind == "\\":
            characters.append("\\")
            pos += 2
        elif kind == "n":
            characters.append("\n")
            pos += 2
        elif kind == "r":
            characters.append("\r")
            pos += 2
        elif kind == "t":
            characters.append("\t")
            pos += 2
        elif kind == "0":
            characters.append("\0")
            protected.append(r"\0")
            pos += 2
        elif kind == "u":
            token = text[pos:pos + 6]
            if len(token) != 6 or not re.fullmatch(r"\\u[0-9A-Fa-f]{4}", token):
                raise FormatError(f"invalid Unicode escape near: {text[pos:pos + 12]!r}")
            characters.append(chr(int(token[2:], 16)))
            protected.append(token.upper())
            pos += 6
        else:
            raise FormatError(f"unsupported message escape: \\{kind}")
    encoded = "".join(characters).encode("utf-16le")
    units = struct.unpack(f"<{len(encoded) // 2}H", encoded) if encoded else ()
    return tuple(units), tuple(protected)


def terminate_message_units(units: tuple[int, ...]) -> tuple[int, ...]:
    output = list(units)
    output.append(0)
    if len(output) % 2:
        output.append(0)
    return tuple(output)


AMX_HEADER_FORMAT = "<IHBBHH12I"
AMX_HEADER_SIZE = struct.calcsize(AMX_HEADER_FORMAT)
AMX_MAGIC_32 = 0xF1E0
AMX_FLAG_COMPACT = 0x04


def parse_amx_header(data: bytes) -> dict:
    """Parse the 32-bit Pawn 3.x AMX header used by Pocket Card Jockey."""
    if len(data) < AMX_HEADER_SIZE:
        raise FormatError("truncated AMX header")
    values = struct.unpack_from(AMX_HEADER_FORMAT, data)
    size, magic, file_version, amx_version, flags, defsize, *offsets = values
    (
        cod,
        dat,
        hea,
        stp,
        cip,
        publics,
        natives,
        libraries,
        pubvars,
        tags,
        nametable,
        overlays,
    ) = offsets
    if magic != AMX_MAGIC_32:
        raise FormatError("not a supported 32-bit AMX file")
    if defsize != 8:
        raise FormatError(f"unsupported AMX definition size: {defsize}")
    if not (AMX_HEADER_SIZE <= cod <= size <= len(data)):
        raise FormatError("invalid AMX image size/code offset")
    if not (cod <= dat <= hea <= stp):
        raise FormatError("invalid AMX segment offsets")
    if (hea - cod) % 4:
        raise FormatError("AMX code/data image is not cell-aligned")

    # In Pawn 3.x bit 2 means compact encoding. Pawn 4.x reused the bit for
    # NOCHECKS, so size < hea is also required before treating it as compact.
    compact = bool(flags & AMX_FLAG_COMPACT) and size < hea
    if not compact and size < hea:
        raise FormatError("AMX image is shorter than its expanded data")
    return {
        "size": size,
        "magic": magic,
        "file_version": file_version,
        "amx_version": amx_version,
        "flags": flags,
        "defsize": defsize,
        "cod": cod,
        "dat": dat,
        "hea": hea,
        "stp": stp,
        "cip": cip,
        "publics": publics,
        "natives": natives,
        "libraries": libraries,
        "pubvars": pubvars,
        "tags": tags,
        "nametable": nametable,
        "overlays": overlays,
        "compact": compact,
    }


def amx_decode_compact_cells(encoded: bytes, expected_size: int) -> bytes:
    """Expand Pawn's signed, big-endian 7-bit compact cell encoding."""
    cells = bytearray()
    pos = 0
    while pos < len(encoded):
        groups = []
        while True:
            if pos >= len(encoded):
                raise FormatError("truncated compact AMX cell")
            value = encoded[pos]
            pos += 1
            groups.append(value)
            if len(groups) > 5:
                raise FormatError("compact AMX cell is wider than 32 bits")
            if not (value & 0x80):
                break

        cell = 0
        for value in groups:
            cell = (cell << 7) | (value & 0x7F)
        bit_count = 7 * len(groups)
        if groups[0] & 0x40:
            cell -= 1 << bit_count
        cells += (cell & 0xFFFFFFFF).to_bytes(4, "little")
        if len(cells) > expected_size:
            raise FormatError("compact AMX expands beyond its declared size")
    if len(cells) != expected_size:
        raise FormatError(
            f"compact AMX expanded to {len(cells)} bytes, expected {expected_size}"
        )
    return bytes(cells)


def amx_encode_compact_cells(expanded: bytes) -> bytes:
    """Encode 32-bit cells exactly like the Pawn 3.x compiler."""
    if len(expanded) % 4:
        raise FormatError("expanded AMX cells are not 4-byte aligned")
    output = bytearray()
    for pos in range(0, len(expanded), 4):
        value = int.from_bytes(expanded[pos:pos + 4], "little")
        groups = []
        for _ in range(5):
            groups.append(value & 0x7F)
            value >>= 7

        count = 5
        while count > 1 and groups[count - 1] == 0 and not (groups[count - 2] & 0x40):
            count -= 1
        if count == 5 and groups[count - 1] == 0x0F and groups[count - 2] & 0x40:
            count -= 1
        while count > 1 and groups[count - 1] == 0x7F and groups[count - 2] & 0x40:
            count -= 1

        for index in range(count - 1, -1, -1):
            output.append(groups[index] | (0x80 if index else 0))
    return bytes(output)


def expand_amx(data: bytes) -> tuple[dict, bytes]:
    """Return an AMX header and a header+code+data expanded image."""
    header = parse_amx_header(data)
    if header["compact"]:
        segment = amx_decode_compact_cells(
            data[header["cod"]:header["size"]], header["hea"] - header["cod"]
        )
        expanded = data[:header["cod"]] + segment
    else:
        expanded = data[:header["hea"]]
    if len(expanded) != header["hea"]:
        raise FormatError("expanded AMX size does not match HEA")
    return header, expanded


def rebuild_amx(original: bytes, expanded: bytes) -> bytes:
    """Rebuild a possibly compact AMX and preserve any appended debug data."""
    header = parse_amx_header(original)
    if len(expanded) != header["hea"]:
        raise FormatError("edited AMX image size changed")
    if expanded[:header["cod"]] != original[:header["cod"]]:
        raise FormatError("AMX header/name tables were unexpectedly modified")

    if header["compact"]:
        body = amx_encode_compact_cells(expanded[header["cod"]:header["hea"]])
        image = bytearray(expanded[:header["cod"]] + body)
    else:
        image = bytearray(expanded)
    struct.pack_into("<I", image, 0, len(image))
    rebuilt = bytes(image) + original[header["size"]:]

    check_header, check_expanded = expand_amx(rebuilt)
    expected_expanded = bytearray(expanded)
    struct.pack_into("<I", expected_expanded, 0, len(image))
    if check_header["size"] != len(image) or check_expanded != bytes(expected_expanded):
        raise FormatError("rebuilt AMX verification failed")
    return rebuilt


def looks_like_amx_text(text: str) -> bool:
    """Reject numeric tables that merely resemble short Pawn strings."""
    letters = [char for char in text if char.isalpha()]
    if len(text) < 2 or len(letters) < 2:
        return False
    if any(ord(char) > 127 and char.isalpha() for char in text):
        return True
    if any(char.isspace() for char in text):
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,}", text):
        return True
    if re.search(r"%[-+0-9.*]*[A-Za-z]", text):
        return True
    return False


def classify_amx_text(text: str) -> str:
    stripped = text.strip()
    if (
        "\n" in text
        or "%" in text
        or stripped.startswith("@")
        or re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", stripped)
        or re.fullmatch(r"[A-Z0-9_ ]+", stripped)
    ):
        return "debug_or_internal"
    return "candidate"


def find_amx_strings(expanded: bytes, header: dict) -> list[dict]:
    """Find high-confidence unpacked Unicode strings in the AMX data segment."""
    cell_count = (header["hea"] - header["dat"]) // 4
    cells = struct.unpack_from(f"<{cell_count}I", expanded, header["dat"])
    strings = []
    for start in range(cell_count):
        if start and cells[start - 1] != 0:
            continue
        pos = start
        characters = []
        while pos < cell_count and cells[pos] != 0:
            value = cells[pos]
            if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
                break
            character = chr(value)
            if not character.isprintable() and character not in "\r\n\t":
                break
            characters.append(character)
            pos += 1
        if pos >= cell_count or cells[pos] != 0:
            continue
        text = "".join(characters)
        if not looks_like_amx_text(text):
            continue
        strings.append({
            "data_offset": start * 4,
            "storage": "unpacked32",
            "encoding": "unicode_cells",
            "text": text,
            "capacity": len(characters),
            "classification": classify_amx_text(text),
        })
    return strings


def read_amx_unpacked_string(expanded: bytes, header: dict, data_offset: int) -> str:
    if data_offset < 0 or data_offset % 4:
        raise FormatError("AMX data offset is not a non-negative cell offset")
    absolute = header["dat"] + data_offset
    if absolute >= header["hea"]:
        raise FormatError("AMX string offset lies outside the data segment")
    characters = []
    while absolute < header["hea"]:
        value = u32(expanded, absolute)
        absolute += 4
        if value == 0:
            return "".join(characters)
        if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            raise FormatError("AMX string contains an invalid Unicode cell")
        characters.append(chr(value))
    raise FormatError("unterminated AMX string")


def patch_amx_unpacked_string(
    expanded: bytes, header: dict, data_offset: int, capacity: int, translation: str
) -> bytes:
    if "\0" in translation:
        raise FormatError("AMX translations cannot contain NUL characters")
    if len(translation) > capacity:
        raise FormatError(
            f"AMX translation has {len(translation)} characters; capacity is {capacity}"
        )
    if any(0xD800 <= ord(char) <= 0xDFFF for char in translation):
        raise FormatError("AMX translation contains an invalid Unicode surrogate")
    absolute = header["dat"] + data_offset
    end = absolute + (capacity + 1) * 4
    if data_offset < 0 or data_offset % 4 or end > header["hea"]:
        raise FormatError("AMX string range lies outside the data segment")
    output = bytearray(expanded)
    values = [ord(char) for char in translation]
    values += [0] * (capacity + 1 - len(values))
    for index, value in enumerate(values):
        struct.pack_into("<I", output, absolute + 4 * index, value)
    return bytes(output)


def lz11_decompress(data: bytes) -> bytes:
    if len(data) < 4 or data[0] != 0x11:
        raise FormatError("not an LZ11 stream")
    out_size = int.from_bytes(data[1:4], "little")
    pos = 4
    if out_size == 0:
        if len(data) < 8:
            raise FormatError("truncated extended LZ11 header")
        out_size = int.from_bytes(data[4:8], "little")
        pos = 8

    out = bytearray()
    while len(out) < out_size:
        if pos >= len(data):
            raise FormatError("truncated LZ11 flag byte")
        flags = data[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if len(out) >= out_size:
                break
            if not (flags & (1 << bit)):
                if pos >= len(data):
                    raise FormatError("truncated LZ11 literal")
                out.append(data[pos])
                pos += 1
                continue

            if pos >= len(data):
                raise FormatError("truncated LZ11 match")
            b1 = data[pos]
            pos += 1
            indicator = b1 >> 4
            if indicator == 0:
                if pos + 1 >= len(data):
                    raise FormatError("truncated 3-byte LZ11 match")
                b2, b3 = data[pos], data[pos + 1]
                pos += 2
                length = ((b1 & 0x0F) << 4 | b2 >> 4) + 0x11
                disp = ((b2 & 0x0F) << 8 | b3) + 1
            elif indicator == 1:
                if pos + 2 >= len(data):
                    raise FormatError("truncated 4-byte LZ11 match")
                b2, b3, b4 = data[pos], data[pos + 1], data[pos + 2]
                pos += 3
                length = ((b1 & 0x0F) << 12 | b2 << 4 | b3 >> 4) + 0x111
                disp = ((b3 & 0x0F) << 8 | b4) + 1
            else:
                if pos >= len(data):
                    raise FormatError("truncated 2-byte LZ11 match")
                b2 = data[pos]
                pos += 1
                length = indicator + 1
                disp = ((b1 & 0x0F) << 8 | b2) + 1

            if disp > len(out):
                raise FormatError("invalid LZ11 back-reference")
            for _ in range(length):
                if len(out) >= out_size:
                    break
                out.append(out[-disp])
    return bytes(out)


def lz11_compress(data: bytes) -> bytes:
    """Create a valid (not necessarily optimal) Nintendo LZ11 stream."""
    size = len(data)
    out = bytearray(b"\x11")
    if size < 0x1000000:
        out += size.to_bytes(3, "little")
    else:
        out += b"\0\0\0" + size.to_bytes(4, "little")

    pos = 0
    while pos < size:
        flags = 0
        blocks: list[bytes] = []
        for block_index in range(8):
            if pos >= size:
                break
            match_pos = -1
            match_len = 0
            max_len = min(0x10110, size - pos)
            if max_len >= 3:
                window_start = max(0, pos - 0x1000)
                match_pos = data.rfind(data[pos:pos + 3], window_start, pos)
                if match_pos >= 0:
                    match_len = 3
                    while (
                        match_len < max_len
                        and data[match_pos + match_len] == data[pos + match_len]
                    ):
                        match_len += 1

            if match_len < 3:
                blocks.append(data[pos:pos + 1])
                pos += 1
                continue

            flags |= 1 << (7 - block_index)
            disp = pos - match_pos - 1
            if match_len <= 0x10:
                blocks.append(bytes((((match_len - 1) << 4) | (disp >> 8), disp & 0xFF)))
            elif match_len <= 0x110:
                count = match_len - 0x11
                blocks.append(bytes((
                    count >> 4,
                    ((count & 0x0F) << 4) | (disp >> 8),
                    disp & 0xFF,
                )))
            else:
                count = match_len - 0x111
                blocks.append(bytes((
                    0x10 | (count >> 12),
                    (count >> 4) & 0xFF,
                    ((count & 0x0F) << 4) | (disp >> 8),
                    disp & 0xFF,
                )))
            pos += match_len
        out.append(flags)
        for block in blocks:
            out += block
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def parse_garc(data: bytes) -> dict:
    if len(data) < 0x40 or data[:4] != b"CRAG":
        raise FormatError("not a little-endian GARC/CRAG file")
    header_size = u32(data, 4)
    if header_size < 0x1C or data[header_size:header_size + 4] != b"OTAF":
        raise FormatError("unsupported GARC header")

    fato = header_size
    fato_size = u32(data, fato + 4)
    node_count = u16(data, fato + 8)
    padding = u16(data, fato + 10)
    offsets = [u32(data, fato + 12 + 4 * i) for i in range(node_count)]

    fatb = fato + fato_size
    if data[fatb:fatb + 4] != b"BTAF":
        raise FormatError("missing FATB/BTAF section")
    fatb_size = u32(data, fatb + 4)
    fatb_count = u32(data, fatb + 8)
    entry_base = fatb + 12

    fimg = fatb + fatb_size
    if data[fimg:fimg + 4] != b"BMIF":
        raise FormatError("missing FIMG/BMIF section")
    data_offset = u32(data, 0x10)
    if data_offset != fimg + u32(data, fimg + 4):
        raise FormatError("inconsistent GARC data offset")

    nodes = []
    total_members = 0
    for node_index, rel in enumerate(offsets):
        pos = entry_base + rel
        bit_vector = u32(data, pos)
        pos += 4
        members = []
        for slot in range(32):
            if not (bit_vector & (1 << slot)):
                continue
            start, end, length = struct.unpack_from("<III", data, pos)
            pos += 12
            if start + length > len(data) - data_offset or end < start + length:
                raise FormatError(f"invalid member range in node {node_index}")
            raw = data[data_offset + start:data_offset + start + length]
            members.append({
                "slot": slot,
                "start": start,
                "end": end,
                "length": length,
                "raw": raw,
            })
            total_members += 1
        nodes.append({"index": node_index, "bit_vector": bit_vector, "members": members})

    return {
        "header": {
            "header_size": header_size,
            "bom": u16(data, 8),
            "version": u16(data, 10),
            "section_count": u32(data, 12),
            "data_offset": data_offset,
            "file_length": u32(data, 0x14),
            "largest_file": u32(data, 0x18),
            "fato_padding": padding,
            "fatb_count": fatb_count,
            "fimg_data_size": u32(data, fimg + 8),
        },
        "nodes": nodes,
        "member_count": total_members,
    }


def read_utf16z(data: bytes, off: int) -> str:
    end = off
    while end + 1 < len(data) and data[end:end + 2] != b"\0\0":
        end += 2
    if end + 1 >= len(data):
        raise FormatError("unterminated DARC name")
    return data[off:end].decode("utf-16le")


def parse_darc(data: bytes, base: int) -> list[dict]:
    if data[base:base + 4] != b"darc" or base + 0x1C > len(data):
        raise FormatError("not a DARC archive")
    bom, header_len, _unknown, _version = struct.unpack_from("<4H", data, base + 4)
    file_len, table_off, table_len, _data_off = struct.unpack_from("<4I", data, base + 12)
    if bom != 0xFEFF or header_len != 0x1C or base + file_len > len(data):
        raise FormatError("unsupported DARC header")
    table = base + table_off
    root = struct.unpack_from("<III", data, table)
    entry_count = root[2]
    names = table + 12 * entry_count
    if entry_count < 1 or names > base + file_len or table_len < 12 * entry_count:
        raise FormatError("invalid DARC table")

    entries = []
    for index in range(entry_count):
        name_info, data_off, data_len = struct.unpack_from("<III", data, table + 12 * index)
        is_dir = bool(name_info >> 24)
        name_off = name_info & 0xFFFFFF
        name = read_utf16z(data, names + name_off)
        entries.append({
            "index": index,
            "name": name,
            "is_dir": is_dir,
            "data_offset": data_off,
            "data_length": data_len,
        })

    files = []
    stack: list[tuple[int, tuple[str, ...]]] = [(entry_count, ())]
    for entry in entries[1:]:
        while stack and entry["index"] >= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else ()
        name = entry["name"]
        if entry["is_dir"] and name in {"", "."}:
            continue
        if not name or name == ".." or "/" in name or "\\" in name:
            raise FormatError("unsafe DARC path")
        if entry["is_dir"]:
            stack.append((entry["data_length"], parent + (name,)))
            continue
        start = base + entry["data_offset"]
        end = start + entry["data_length"]
        if start < base or end > base + file_len:
            raise FormatError("invalid DARC file range")
        files.append({**entry, "parts": parent + (name,), "data": data[start:end]})
    return files


def parse_bclyt_texts(data: bytes) -> list[dict]:
    if len(data) < 20 or data[:4] != b"CLYT" or u16(data, 4) != 0xFEFF:
        raise FormatError("not a supported little-endian BCLYT file")
    header_size = u16(data, 6)
    file_size = u32(data, 12)
    section_count = u16(data, 16)
    if header_size < 20 or file_size > len(data):
        raise FormatError("invalid BCLYT header")

    texts = []
    pos = header_size
    for section_index in range(section_count):
        if pos + 8 > file_size:
            raise FormatError("truncated BCLYT section table")
        magic, section_size = struct.unpack_from("<4sI", data, pos)
        if section_size < 8 or pos + section_size > file_size:
            raise FormatError("invalid BCLYT section size")
        if magic == b"txt1":
            if section_size < 116:
                raise FormatError("unsupported short BCLYT txt1 section")
            pane = data[pos + 12:pos + 36].split(b"\0", 1)[0].decode("ascii", "replace")
            capacity, text_length = struct.unpack_from("<HH", data, pos + 76)
            text_offset = u32(data, pos + 88)
            if text_length == 0:
                text = ""
            else:
                if text_offset + text_length > section_size or text_length % 2:
                    raise FormatError("invalid BCLYT text range")
                encoded = data[pos + text_offset:pos + text_offset + text_length]
                if not encoded.endswith(b"\0\0"):
                    raise FormatError("unterminated BCLYT text")
                text = encoded[:-2].decode("utf-16le")
            texts.append({
                "section": section_index,
                "pane": pane,
                "text": text,
                "capacity_bytes": capacity,
                "length_bytes": text_length,
                "text_offset": text_offset,
            })
        pos += section_size
    if pos != file_size:
        raise FormatError("BCLYT sections do not match declared file size")
    return texts


def patch_bclyt(data: bytes, translations: dict[int, str]) -> bytes:
    original_texts = {row["section"]: row for row in parse_bclyt_texts(data)}
    unknown = set(translations) - set(original_texts)
    if unknown:
        raise FormatError(f"unknown BCLYT text section(s): {sorted(unknown)}")

    header_size = u16(data, 6)
    section_count = u16(data, 16)
    output = bytearray(data[:header_size])
    pos = header_size
    for section_index in range(section_count):
        section_size = u32(data, pos + 4)
        section = bytearray(data[pos:pos + section_size])
        if section_index in translations:
            new_text = translations[section_index]
            if "\0" in new_text:
                raise FormatError("BCLYT translations cannot contain NUL characters")
            encoded = new_text.encode("utf-16le") + b"\0\0"
            if len(encoded) > 0xFFFF:
                raise FormatError("BCLYT translation is too long for a 16-bit length field")
            while len(section) % 4:
                section.append(0)
            text_offset = len(section)
            section += encoded
            while len(section) % 4:
                section.append(0)
            old_capacity = u16(section, 76)
            struct.pack_into("<HH", section, 76, max(old_capacity, len(encoded)), len(encoded))
            struct.pack_into("<I", section, 88, text_offset)
            struct.pack_into("<I", section, 4, len(section))
        output += section
        pos += section_size
    struct.pack_into("<I", output, 12, len(output))

    check = {row["section"]: row["text"] for row in parse_bclyt_texts(bytes(output))}
    for section_index, expected in translations.items():
        if check[section_index] != expected:
            raise FormatError("BCLYT text verification failed")
    return bytes(output)


def patch_darc_files(decoded: bytes, replacements: dict[str, bytes]) -> bytes:
    base = decoded.find(b"darc")
    if base < 0:
        raise FormatError("member does not contain a DARC archive")
    files = parse_darc(decoded, base)
    available = {"/".join(entry["parts"]): entry for entry in files}
    missing = set(replacements) - set(available)
    if missing:
        raise FormatError(f"DARC paths not found: {sorted(missing)}")

    table_off = u32(decoded, base + 16)
    data_off = u32(decoded, base + 24)
    darc_len = u32(decoded, base + 12)
    darc = decoded[base:base + darc_len]
    metadata = bytearray(darc[:data_off])
    rebuilt = bytearray(metadata)
    for file_index, entry in enumerate(files):
        if file_index:
            while len(rebuilt) % 0x20:
                rebuilt.append(0)
        relative = "/".join(entry["parts"])
        file_data = replacements.get(relative, entry["data"])
        entry_pos = table_off + 12 * entry["index"]
        struct.pack_into("<II", rebuilt, entry_pos + 4, len(rebuilt), len(file_data))
        rebuilt += file_data
    struct.pack_into("<I", rebuilt, 12, len(rebuilt))
    return decoded[:base] + bytes(rebuilt) + decoded[base + darc_len:]


def safe_stem(relative: Path) -> str:
    return "__".join(relative.parts)


def unpack_one(source: Path, output: Path, relative: Path) -> dict:
    raw_garc = source.read_bytes()
    parsed = parse_garc(raw_garc)
    arc_dir = output / safe_stem(relative)
    arc_dir.mkdir(parents=True, exist_ok=True)
    manifest_nodes = []

    for node in parsed["nodes"]:
        manifest_members = []
        for member in node["members"]:
            raw = member.pop("raw")
            compressed = False
            decoded = raw
            if raw.startswith(b"\x11"):
                try:
                    decoded = lz11_decompress(raw)
                    compressed = True
                except FormatError:
                    # A normal binary member may coincidentally begin with 0x11.
                    decoded = raw
            filename = f"node_{node['index']:04d}_slot_{member['slot']:02d}.bin"
            (arc_dir / filename).write_bytes(decoded)
            inner_files = []
            darc_offset = decoded.find(b"darc")
            if darc_offset >= 0:
                inner_root = arc_dir / (filename + ".inner")
                for inner in parse_darc(decoded, darc_offset):
                    inner_path = inner_root.joinpath(*inner.pop("parts"))
                    inner_path.parent.mkdir(parents=True, exist_ok=True)
                    inner_data = inner.pop("data")
                    inner_path.write_bytes(inner_data)
                    inner_files.append({
                        **inner,
                        "file": inner_path.relative_to(arc_dir).as_posix(),
                        "sha256": sha256(inner_data),
                    })
            manifest_members.append({
                **member,
                "file": filename,
                "compressed_lz11": compressed,
                "stored_sha256": sha256(raw),
                "decoded_sha256": sha256(decoded),
                "decoded_size": len(decoded),
                "magic_hex": decoded[:16].hex(" "),
                "darc_offset": darc_offset if darc_offset >= 0 else None,
                "inner_files": inner_files,
            })
        manifest_nodes.append({
            "index": node["index"],
            "bit_vector": node["bit_vector"],
            "members": manifest_members,
        })

    manifest = {
        "format": "pcj-garc-manifest-v1",
        "source": relative.as_posix(),
        "source_sha256": sha256(raw_garc),
        "source_size": len(raw_garc),
        "header": parsed["header"],
        "member_count": parsed["member_count"],
        "nodes": manifest_nodes,
    }
    (arc_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"archive": relative.as_posix(), "directory": arc_dir.name, "members": parsed["member_count"]}


def build_garc(source_data: bytes, replacements: dict[tuple[int, int], bytes]) -> bytes:
    parsed = parse_garc(source_data)
    unknown = set(replacements)
    nodes_out = []
    data_out = bytearray()
    largest = 0
    for node in parsed["nodes"]:
        members_out = []
        for member in node["members"]:
            key = (node["index"], member["slot"])
            raw = member["raw"]
            if key in replacements:
                replacement = replacements[key]
                compressed = False
                if raw.startswith(b"\x11"):
                    try:
                        lz11_decompress(raw)
                        compressed = True
                    except FormatError:
                        pass
                raw = lz11_compress(replacement) if compressed else replacement
                unknown.discard(key)
            while len(data_out) % 4:
                data_out.append(0xFF)
            start = len(data_out)
            data_out += raw
            length = len(raw)
            while len(data_out) % 4:
                data_out.append(0xFF)
            end = len(data_out)
            largest = max(largest, length)
            members_out.append((member["slot"], start, end, length))
        nodes_out.append((node["bit_vector"], members_out))
    if unknown:
        raise FormatError(f"GARC member(s) not found: {sorted(unknown)}")

    fato_offsets = []
    fatb_entries = bytearray()
    for bit_vector, members in nodes_out:
        fato_offsets.append(len(fatb_entries))
        fatb_entries += struct.pack("<I", bit_vector)
        for _slot, start, end, length in members:
            fatb_entries += struct.pack("<III", start, end, length)

    node_count = len(nodes_out)
    fato = bytearray(b"OTAF")
    fato += struct.pack("<IHH", 12 + 4 * node_count, node_count, parsed["header"]["fato_padding"])
    fato += b"".join(struct.pack("<I", off) for off in fato_offsets)

    fatb = bytearray(b"BTAF")
    fatb += struct.pack("<II", 12 + len(fatb_entries), node_count)
    fatb += fatb_entries

    fimg = bytearray(b"BMIF") + struct.pack("<II", 12, len(data_out))
    data_offset = 0x1C + len(fato) + len(fatb) + len(fimg)
    total_size = data_offset + len(data_out)
    header = struct.pack(
        "<4sIHHIIII",
        b"CRAG",
        0x1C,
        parsed["header"]["bom"],
        parsed["header"]["version"],
        parsed["header"]["section_count"],
        data_offset,
        total_size,
        largest,
    )
    result = header + bytes(fato) + bytes(fatb) + bytes(fimg) + bytes(data_out)
    parse_garc(result)
    return result


def cmd_unpack_all(args: argparse.Namespace) -> None:
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        relative = path.relative_to(source)
        try:
            rows.append(unpack_one(path, output, relative))
        except FormatError as exc:
            print(f"SKIP {relative}: {exc}")
    (output / "index.json").write_text(
        json.dumps({"format": "pcj-garc-index-v1", "archives": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(rows)} GARC archives to {output}")


CSV_FIELDS = (
    "apply",
    "archive",
    "member",
    "bclyt",
    "section",
    "pane",
    "source_text",
    "translation",
    "capacity_bytes",
)


def export_csv(project: Path, output: Path, latin_only: bool = False) -> int:
    rows = []
    for manifest_path in sorted(project.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        archive = manifest["source"]
        archive_dir = manifest_path.parent
        for bclyt_path in sorted(archive_dir.rglob("*.bclyt")):
            relative = bclyt_path.relative_to(archive_dir)
            if len(relative.parts) < 2 or not relative.parts[0].endswith(".bin.inner"):
                continue
            member = relative.parts[0][:-len(".inner")]
            bclyt = Path(*relative.parts[1:]).as_posix()
            for entry in parse_bclyt_texts(bclyt_path.read_bytes()):
                if entry["text"] == "":
                    continue
                if latin_only and not re.search(r"[A-Za-z]", entry["text"]):
                    continue
                rows.append({
                    "apply": "",
                    "archive": archive,
                    "member": member,
                    "bclyt": bclyt,
                    "section": entry["section"],
                    "pane": entry["pane"],
                    "source_text": entry["text"],
                    "translation": "",
                    "capacity_bytes": entry["capacity_bytes"],
                })
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def cmd_export_csv(args: argparse.Namespace) -> None:
    count = export_csv(args.project.resolve(), args.output.resolve(), args.latin_only)
    print(f"Exported {count} non-empty BCLYT text panes to {args.output.resolve()}")


def cmd_prepare(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    extracted = project / "extracted"
    cmd_unpack_all(argparse.Namespace(source=args.source, output=extracted))
    count = export_csv(extracted, project / "translations.csv")
    latin_count = export_csv(extracted, project / "translations_latin.csv", latin_only=True)
    print(
        f"Created translation project with {count} total rows / {latin_count} Latin-text rows at {project}"
    )


MESSAGE_CSV_FIELDS = (
    "apply",
    "archive",
    "member",
    "section",
    "entry",
    "source_text",
    "translation",
    "flags",
    "notes",
)


def message_has_ascii_text(parsed: dict) -> bool:
    """Reject table-shaped binary data that decrypts to no English text."""
    return any(
        any(0x41 <= value <= 0x5A or 0x61 <= value <= 0x7A for value in entry["units"])
        for section in parsed["sections"]
        for entry in section["entries"]
    )


def iter_message_tables(project: Path):
    for manifest_path in sorted(project.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        archive_dir = manifest_path.parent
        for node in manifest.get("nodes", []):
            for member in node.get("members", []):
                member_path = archive_dir / member["file"]
                try:
                    parsed = parse_message_table(member_path.read_bytes())
                except FormatError:
                    continue
                if not message_has_ascii_text(parsed):
                    continue
                yield {
                    "archive": manifest["source"],
                    "archive_dir": archive_dir,
                    "manifest": manifest,
                    "member": member["file"],
                    "member_manifest": member,
                    "parsed": parsed,
                }


def export_message_csv(project: Path, output: Path, latin_only: bool = False) -> dict:
    rows = []
    tables = 0
    raw_section_entries = 0
    for table in iter_message_tables(project):
        tables += 1
        parsed = table["parsed"]
        raw_section_entries += parsed["section_count"] * parsed["entry_count"]
        for entry_index in range(parsed["entry_count"]):
            entries = [
                section["entries"][entry_index]
                for section in parsed["sections"]
            ]
            if all(entry["units"] == entries[0]["units"] for entry in entries[1:]):
                variants = [("all", entries[0])]
            else:
                variants = [(str(index), entry) for index, entry in enumerate(entries)]
            for section_selector, entry in variants:
                units = strip_message_padding(entry["units"])
                if not units:
                    continue
                if latin_only and not any(
                    0x41 <= value <= 0x5A or 0x61 <= value <= 0x7A for value in units
                ):
                    continue
                if section_selector == "all":
                    flags = "/".join(str(item["flags"]) for item in entries)
                else:
                    flags = str(entry["flags"])
                rows.append({
                    "apply": "",
                    "archive": table["archive"],
                    "member": table["member"],
                    "section": section_selector,
                    "entry": entry_index,
                    "source_text": escape_message_units(entry["units"]),
                    "translation": "",
                    "flags": flags,
                    "notes": "",
                })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MESSAGE_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "table_count": tables,
        "raw_section_entry_count": raw_section_entries,
        "row_count": len(rows),
    }


def cmd_msg_export_csv(args: argparse.Namespace) -> None:
    result = export_message_csv(
        args.project.resolve(), args.output.resolve(), args.latin_only
    )
    print(
        f"Exported {result['row_count']} message rows from "
        f"{result['table_count']} encrypted tables to {args.output.resolve()}"
    )


def cmd_msg_prepare(args: argparse.Namespace) -> None:
    project = args.project.resolve()
    extracted = project / "extracted"
    source_root = args.source.resolve()
    relative_archive = Path("0/0/0")
    archive_path = source_root / relative_archive
    if not archive_path.is_file():
        raise FormatError(f"main message GARC not found: {archive_path}")
    extracted.mkdir(parents=True, exist_ok=True)
    archive_row = unpack_one(archive_path, extracted, relative_archive)
    (extracted / "index.json").write_text(
        json.dumps(
            {"format": "pcj-garc-index-v1", "archives": [archive_row]}, indent=2
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Extracted main message GARC to {extracted}")
    all_result = export_message_csv(extracted, project / "messages.csv")
    latin_result = export_message_csv(
        extracted, project / "messages_latin.csv", latin_only=True
    )
    manifest = {
        "format": "pcj-message-project-v1",
        "cipher": {
            "initial_key": f"0x{MESSAGE_KEY_BASE:04X}",
            "entry_step": f"0x{MESSAGE_KEY_STEP:04X}",
            "key_rotation_bits": 3,
        },
        "table_count": all_result["table_count"],
        "raw_section_entry_count": all_result["raw_section_entry_count"],
        "csv_row_count": all_result["row_count"],
        "latin_csv_row_count": latin_result["row_count"],
    }
    (project / "message_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Created message project with {all_result['table_count']} encrypted tables, "
        f"{all_result['row_count']} editable rows and {latin_result['row_count']} "
        f"Latin-text rows at {project}"
    )


def cmd_msg_build(args: argparse.Namespace) -> None:
    source_root = args.source.resolve()
    project = args.project.resolve()
    extracted = project / "extracted"
    csv_path = args.csv.resolve()
    output_root = args.output.resolve()
    if source_root == output_root:
        raise SystemExit("Refusing to overwrite the source directory; choose another output directory")

    selected = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = set(MESSAGE_CSV_FIELDS) - set(reader.fieldnames or ())
        if missing_columns:
            raise FormatError(f"message CSV is missing columns: {sorted(missing_columns)}")
        for line_number, row in enumerate(reader, 2):
            if enabled(row["apply"]):
                row["line_number"] = line_number
                selected.append(row)
    if not selected:
        print("No message rows are marked for application; nothing was built")
        return

    grouped: dict[str, dict[str, list[dict]]] = {}
    for row in selected:
        grouped.setdefault(row["archive"], {}).setdefault(row["member"], []).append(row)

    changed_rows = 0
    changed_variants = 0
    for archive, members in sorted(grouped.items()):
        relative_archive = safe_relative_path(archive)
        archive_dir = extracted / safe_stem(relative_archive)
        manifest_path = archive_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FormatError(f"project manifest not found for {archive}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source") != archive:
            raise FormatError(f"project manifest/source mismatch for {archive}")
        member_manifests = {
            member["file"]: member
            for node in manifest.get("nodes", [])
            for member in node.get("members", [])
        }

        garc_replacements: dict[tuple[int, int], bytes] = {}
        for member_name, rows in sorted(members.items()):
            match = re.fullmatch(r"node_(\d+)_slot_(\d+)\.bin", member_name)
            if not match:
                raise FormatError(f"invalid member name in message CSV: {member_name}")
            member_manifest = member_manifests.get(member_name)
            if member_manifest is None:
                raise FormatError(f"message member is not present in project: {member_name}")
            member_path = archive_dir / member_name
            original_member = member_path.read_bytes()
            if sha256(original_member) != member_manifest.get("decoded_sha256"):
                raise FormatError(f"extracted message member hash changed: {archive}/{member_name}")
            parsed = parse_message_table(original_member)
            if not message_has_ascii_text(parsed):
                raise FormatError(f"member is not recognized as an English message table: {member_name}")

            replacements: dict[tuple[int, int], tuple[int, ...]] = {}
            for row in rows:
                try:
                    entry_index = int(row["entry"], 0)
                except ValueError as exc:
                    raise FormatError(
                        f"CSV line {row['line_number']}: invalid message entry number"
                    ) from exc
                if not 0 <= entry_index < parsed["entry_count"]:
                    raise FormatError(
                        f"CSV line {row['line_number']}: message entry does not exist"
                    )
                selector = row["section"].strip().casefold()
                if selector == "all":
                    section_indices = list(range(parsed["section_count"]))
                else:
                    try:
                        section_indices = [int(selector, 0)]
                    except ValueError as exc:
                        raise FormatError(
                            f"CSV line {row['line_number']}: invalid message section"
                        ) from exc
                if any(not 0 <= index < parsed["section_count"] for index in section_indices):
                    raise FormatError(
                        f"CSV line {row['line_number']}: message section does not exist"
                    )
                current_texts = [
                    escape_message_units(
                        parsed["sections"][index]["entries"][entry_index]["units"]
                    )
                    for index in section_indices
                ]
                if any(text != row["source_text"] for text in current_texts):
                    raise FormatError(
                        f"CSV line {row['line_number']}: source message no longer matches project"
                    )
                _source_units, source_controls = unescape_message_text(row["source_text"])
                translated_units, translated_controls = unescape_message_text(row["translation"])
                if source_controls != translated_controls:
                    raise FormatError(
                        f"CSV line {row['line_number']}: preserve every \\uXXXX and \\0 "
                        "token from source_text, in the same order"
                    )
                translated_units = terminate_message_units(translated_units)
                for section_index in section_indices:
                    key = (section_index, entry_index)
                    previous = replacements.get(key)
                    if previous is not None and previous != translated_units:
                        raise FormatError(
                            f"CSV line {row['line_number']}: conflicting duplicate message row"
                        )
                    replacements[key] = translated_units
                changed_rows += 1
                changed_variants += len(section_indices)

            rebuilt_member = rebuild_message_table(parsed, replacements)
            verified = parse_message_table(rebuilt_member)
            for key, expected in replacements.items():
                section_index, entry_index = key
                actual = verified["sections"][section_index]["entries"][entry_index]["units"]
                if actual != expected:
                    raise FormatError("rebuilt message table verification failed")
            garc_replacements[(int(match.group(1)), int(match.group(2)))] = rebuilt_member

        source_path = source_root / relative_archive
        if not source_path.is_file():
            raise FormatError(f"source GARC not found: {source_path}")
        source_data = source_path.read_bytes()
        if sha256(source_data) != manifest.get("source_sha256"):
            raise FormatError(f"source GARC hash changed since extraction: {archive}")
        rebuilt = build_garc(source_data, garc_replacements)
        output_path = output_root / relative_archive
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(rebuilt)
        print(f"Built {output_path}")

    print(
        f"Applied {changed_rows} message row(s) to {changed_variants} section variant(s) "
        f"in {len(grouped)} GARC archive(s)"
    )


def enabled(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "x", "yes", "true", "evet"}


AMX_CSV_FIELDS = (
    "apply",
    "file",
    "data_offset",
    "storage",
    "encoding",
    "classification",
    "source_text",
    "translation",
    "capacity",
)


def safe_relative_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise FormatError(f"unsafe relative path: {value}")
    return relative


def cmd_amx_prepare(args: argparse.Namespace) -> None:
    source_root = args.source.resolve()
    project = args.project.resolve()
    if not source_root.is_dir():
        raise FormatError(f"AMX source directory not found: {source_root}")

    paths = sorted(
        path for path in source_root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".amx"
    )
    if not paths:
        raise FormatError(f"no .amx files found below {source_root}")

    files = []
    csv_rows = []
    skipped = 0
    for path in paths:
        relative = path.relative_to(source_root).as_posix()
        raw = path.read_bytes()
        try:
            header, expanded = expand_amx(raw)
            strings = find_amx_strings(expanded, header)
        except FormatError as exc:
            print(f"SKIP {relative}: {exc}")
            skipped += 1
            continue
        files.append({
            "file": relative,
            "sha256": sha256(raw),
            "stored_size": len(raw),
            "image_size": header["size"],
            "expanded_size": header["hea"],
            "trailer_size": len(raw) - header["size"],
            "file_version": header["file_version"],
            "amx_version": header["amx_version"],
            "flags": header["flags"],
            "compact": header["compact"],
            "strings": strings,
        })
        for entry in strings:
            csv_rows.append({
                "apply": "",
                "file": relative,
                "data_offset": entry["data_offset"],
                "storage": entry["storage"],
                "encoding": entry["encoding"],
                "classification": entry["classification"],
                "source_text": entry["text"],
                "translation": "",
                "capacity": entry["capacity"],
            })

    project.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "pcj-amx-project-v1",
        "source_file_count": len(paths),
        "parsed_file_count": len(files),
        "skipped_file_count": skipped,
        "string_count": len(csv_rows),
        "files": files,
    }
    (project / "amx_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    csv_path = project / "amx_translations.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AMX_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)

    candidates = sum(row["classification"] == "candidate" for row in csv_rows)
    print(
        f"Parsed {len(files)} AMX files and exported {len(csv_rows)} strings "
        f"({candidates} display candidates) to {csv_path}"
    )


def cmd_amx_build(args: argparse.Namespace) -> None:
    source_root = args.source.resolve()
    project = args.project.resolve()
    csv_path = args.csv.resolve()
    output_root = args.output.resolve()
    if source_root == output_root:
        raise SystemExit("Refusing to overwrite the source directory; choose another output directory")

    manifest_path = project / "amx_manifest.json"
    if not manifest_path.is_file():
        raise FormatError(f"AMX project manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "pcj-amx-project-v1":
        raise FormatError("unsupported AMX project manifest")
    manifest_files = {entry["file"]: entry for entry in manifest.get("files", [])}

    selected = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = set(AMX_CSV_FIELDS) - set(reader.fieldnames or ())
        if missing_columns:
            raise FormatError(f"AMX translation CSV is missing columns: {sorted(missing_columns)}")
        for line_number, row in enumerate(reader, 2):
            if enabled(row["apply"]):
                row["line_number"] = line_number
                selected.append(row)
    if not selected:
        print("No AMX rows are marked for application; nothing was built")
        return

    grouped: dict[str, list[dict]] = {}
    for row in selected:
        grouped.setdefault(row["file"], []).append(row)

    changed = 0
    for relative_string, rows in sorted(grouped.items()):
        relative = safe_relative_path(relative_string)
        file_manifest = manifest_files.get(relative_string)
        if file_manifest is None:
            raise FormatError(f"AMX file is not present in the project manifest: {relative_string}")
        source_path = source_root / relative
        if not source_path.is_file():
            raise FormatError(f"source AMX not found: {source_path}")
        original = source_path.read_bytes()
        if sha256(original) != file_manifest.get("sha256"):
            raise FormatError(f"source AMX hash changed since extraction: {relative_string}")
        header, expanded = expand_amx(original)

        known = {
            (entry["data_offset"], entry["storage"], entry["encoding"]): entry
            for entry in file_manifest.get("strings", [])
        }
        parsed_rows = []
        seen_offsets = set()
        for row in rows:
            try:
                data_offset = int(row["data_offset"], 0)
                capacity = int(row["capacity"], 0)
            except ValueError as exc:
                raise FormatError(
                    f"CSV line {row['line_number']}: invalid AMX offset/capacity"
                ) from exc
            key = (data_offset, row["storage"], row["encoding"])
            entry = known.get(key)
            if entry is None:
                raise FormatError(
                    f"CSV line {row['line_number']}: AMX string is not in the project manifest"
                )
            if data_offset in seen_offsets:
                raise FormatError(
                    f"CSV line {row['line_number']}: duplicate AMX string offset {data_offset}"
                )
            seen_offsets.add(data_offset)
            if row["storage"] != "unpacked32" or row["encoding"] != "unicode_cells":
                raise FormatError(
                    f"CSV line {row['line_number']}: unsupported AMX string storage"
                )
            if capacity != entry["capacity"] or row["source_text"] != entry["text"]:
                raise FormatError(
                    f"CSV line {row['line_number']}: source text/capacity does not match project"
                )
            current = read_amx_unpacked_string(expanded, header, data_offset)
            if current != row["source_text"]:
                raise FormatError(
                    f"CSV line {row['line_number']}: source string no longer matches the AMX"
                )
            parsed_rows.append((row, data_offset, capacity))

        edited = expanded
        for row, data_offset, capacity in parsed_rows:
            try:
                edited = patch_amx_unpacked_string(
                    edited, header, data_offset, capacity, row["translation"]
                )
            except FormatError as exc:
                raise FormatError(f"CSV line {row['line_number']}: {exc}") from exc
            changed += 1

        rebuilt = rebuild_amx(original, edited)
        check_header, check_expanded = expand_amx(rebuilt)
        for row, data_offset, _capacity in parsed_rows:
            if read_amx_unpacked_string(check_expanded, check_header, data_offset) != row["translation"]:
                raise FormatError(
                    f"CSV line {row['line_number']}: rebuilt AMX text verification failed"
                )
        output_path = output_root / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(rebuilt)
        print(f"Built {output_path}")
    print(f"Applied {changed} AMX string edit(s) in {len(grouped)} file(s)")


def cmd_build(args: argparse.Namespace) -> None:
    source_root = args.source.resolve()
    project = args.project.resolve()
    csv_path = args.csv.resolve()
    output_root = args.output.resolve()
    if source_root == output_root:
        raise SystemExit("Refusing to overwrite the source directory; choose another output directory")

    selected = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = set(CSV_FIELDS) - set(reader.fieldnames or ())
        if missing_columns:
            raise FormatError(f"translation CSV is missing columns: {sorted(missing_columns)}")
        for line_number, row in enumerate(reader, 2):
            if enabled(row["apply"]):
                row["line_number"] = line_number
                selected.append(row)
    if not selected:
        print("No rows are marked for application; nothing was built")
        return

    grouped: dict[str, dict[str, dict[str, list[dict]]]] = {}
    for row in selected:
        grouped.setdefault(row["archive"], {}).setdefault(row["member"], {}).setdefault(
            row["bclyt"], []
        ).append(row)

    changed_panes = 0
    for archive, members in sorted(grouped.items()):
        relative_archive = Path(archive)
        archive_dir = project / safe_stem(relative_archive)
        manifest_path = archive_dir / "manifest.json"
        if not manifest_path.is_file():
            raise FormatError(f"project manifest not found for {archive}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source") != archive:
            raise FormatError(f"project manifest/source mismatch for {archive}")

        garc_replacements: dict[tuple[int, int], bytes] = {}
        for member, layouts in members.items():
            match = re.fullmatch(r"node_(\d+)_slot_(\d+)\.bin", member)
            if not match:
                raise FormatError(f"invalid member name in CSV: {member}")
            decoded_path = archive_dir / member
            decoded = decoded_path.read_bytes()
            darc_replacements = {}
            for bclyt, rows in layouts.items():
                layout_path = archive_dir / (member + ".inner") / Path(bclyt)
                layout_data = layout_path.read_bytes()
                current = {entry["section"]: entry for entry in parse_bclyt_texts(layout_data)}
                translations = {}
                for row in rows:
                    section = int(row["section"])
                    if section not in current:
                        raise FormatError(
                            f"CSV line {row['line_number']}: section {section} no longer exists"
                        )
                    entry = current[section]
                    if entry["pane"] != row["pane"] or entry["text"] != row["source_text"]:
                        raise FormatError(
                            f"CSV line {row['line_number']}: source text/pane does not match project"
                        )
                    translations[section] = row["translation"]
                    changed_panes += 1
                darc_replacements[bclyt] = patch_bclyt(layout_data, translations)
            patched_member = patch_darc_files(decoded, darc_replacements)
            garc_replacements[(int(match.group(1)), int(match.group(2)))] = patched_member

        source_path = source_root / relative_archive
        if not source_path.is_file():
            raise FormatError(f"source GARC not found: {source_path}")
        source_data = source_path.read_bytes()
        if sha256(source_data) != manifest.get("source_sha256"):
            raise FormatError(f"source GARC hash changed since extraction: {archive}")
        rebuilt = build_garc(source_data, garc_replacements)
        output_path = output_root / relative_archive
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(rebuilt)
        print(f"Built {output_path}")
    print(f"Applied {changed_panes} text pane translation(s) in {len(grouped)} GARC archive(s)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    unpack_all = sub.add_parser("unpack-all", help="extract every GARC below a directory")
    unpack_all.add_argument("source", type=Path)
    unpack_all.add_argument("output", type=Path)
    unpack_all.set_defaults(func=cmd_unpack_all)
    export = sub.add_parser("export-csv", help="export editable BCLYT texts from an extracted project")
    export.add_argument("project", type=Path)
    export.add_argument("output", type=Path)
    export.add_argument("--latin-only", action="store_true", help="include only rows containing A-Z letters")
    export.set_defaults(func=cmd_export_csv)
    prepare = sub.add_parser("prepare", help="extract GARCs and create translations.csv")
    prepare.add_argument("source", type=Path)
    prepare.add_argument("project", type=Path)
    prepare.set_defaults(func=cmd_prepare)
    build = sub.add_parser("build", help="apply marked CSV rows and rebuild changed GARC archives")
    build.add_argument("source", type=Path, help="original directory containing the GARC tree")
    build.add_argument("project", type=Path, help="extracted project directory")
    build.add_argument("csv", type=Path, help="edited translations.csv")
    build.add_argument("output", type=Path, help="output root for changed GARC files")
    build.set_defaults(func=cmd_build)
    msg_prepare = sub.add_parser(
        "msg-prepare", help="extract the main message GARC and create editable CSV files"
    )
    msg_prepare.add_argument("source", type=Path, help="original directory containing the GARC tree")
    msg_prepare.add_argument("project", type=Path, help="message translation project directory")
    msg_prepare.set_defaults(func=cmd_msg_prepare)
    msg_export = sub.add_parser(
        "msg-export-csv", help="export encrypted messages from an extracted GARC project"
    )
    msg_export.add_argument("project", type=Path, help="directory produced by unpack-all")
    msg_export.add_argument("output", type=Path, help="output CSV file")
    msg_export.add_argument(
        "--latin-only", action="store_true", help="include only rows containing A-Z letters"
    )
    msg_export.set_defaults(func=cmd_msg_export_csv)
    msg_build = sub.add_parser(
        "msg-build", help="apply marked CSV rows and rebuild encrypted message GARCs"
    )
    msg_build.add_argument("source", type=Path, help="original directory containing the GARC tree")
    msg_build.add_argument("project", type=Path, help="message project produced by msg-prepare")
    msg_build.add_argument("csv", type=Path, help="edited messages.csv")
    msg_build.add_argument("output", type=Path, help="output root for changed GARC files")
    msg_build.set_defaults(func=cmd_msg_build)
    amx_prepare = sub.add_parser(
        "amx-prepare", help="scan Pawn/AMX files and create an editable CSV project"
    )
    amx_prepare.add_argument("source", type=Path, help="directory containing .amx files")
    amx_prepare.add_argument("project", type=Path, help="AMX translation project directory")
    amx_prepare.set_defaults(func=cmd_amx_prepare)
    amx_build = sub.add_parser(
        "amx-build", help="apply marked CSV rows and rebuild changed Pawn/AMX files"
    )
    amx_build.add_argument("source", type=Path, help="original directory containing .amx files")
    amx_build.add_argument("project", type=Path, help="AMX translation project directory")
    amx_build.add_argument("csv", type=Path, help="edited amx_translations.csv")
    amx_build.add_argument("output", type=Path, help="output root for changed AMX files")
    amx_build.set_defaults(func=cmd_amx_build)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
