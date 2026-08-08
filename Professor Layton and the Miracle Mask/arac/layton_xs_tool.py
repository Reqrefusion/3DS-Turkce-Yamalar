#!/usr/bin/env python3
"""Professor Layton 3DS XSCR text export/import utility.

The tool is intentionally dependency-free.  It reads the Level-5 XSCR
container used by Professor Layton and the Miracle Mask, exports a stable
UTF-8 translation project, imports old Kuriimu .kup files, and writes rebuilt
.xs files without Kuriimu's cascading string-offset bug.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import struct
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


TOOL_VERSION = "1.0.0"
PROJECT_FORMAT = "layton-xs-project"
PROJECT_VERSION = 1
TEXT_ENCODING = "cp932"
AUXILIARY_DIRS = {"org", "tr", "en", "backup", "bak"}


class XsError(Exception):
    """Raised for malformed or unsupported XSCR data."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align4(buffer: bytearray) -> None:
    buffer.extend(b"\0" * ((-len(buffer)) & 3))


def lz10_decompress(payload: bytes, output_size: int) -> tuple[bytes, int]:
    """Decompress Level-5's headerless LZ10 payload.

    Returns (decompressed_bytes, compressed_bytes_consumed).  Returning the
    consumed length lets the XSCR reader distinguish compressed bytes from
    the four-byte alignment padding that follows a section.
    """

    output = bytearray()
    cursor = 0
    while len(output) < output_size:
        if cursor >= len(payload):
            raise XsError("LZ10 verisi beklenenden erken bitti (bayrak eksik).")
        flags = payload[cursor]
        cursor += 1
        for bit in range(7, -1, -1):
            if len(output) >= output_size:
                break
            if flags & (1 << bit):
                if cursor + 2 > len(payload):
                    raise XsError("LZ10 verisi beklenenden erken bitti (eşleşme eksik).")
                first, second = payload[cursor], payload[cursor + 1]
                cursor += 2
                length = (first >> 4) + 3
                distance = (((first & 0x0F) << 8) | second) + 1
                if distance > len(output):
                    raise XsError(
                        f"Geçersiz LZ10 geri başvurusu: mesafe={distance}, "
                        f"üretilen={len(output)}."
                    )
                for _ in range(length):
                    output.append(output[-distance])
                    if len(output) == output_size:
                        break
            else:
                if cursor >= len(payload):
                    raise XsError("LZ10 verisi beklenenden erken bitti (ham bayt eksik).")
                output.append(payload[cursor])
                cursor += 1
    return bytes(output), cursor


def _match_length(data: bytes, position: int, candidate: int, maximum: int) -> int:
    length = 0
    while length < maximum and data[candidate + length] == data[position + length]:
        length += 1
    return length


def lz10_compress(data: bytes) -> bytes:
    """Compress bytes to a valid headerless LZ10 stream.

    This is a small greedy encoder.  It favors correctness and deterministic
    output over maximum compression ratio.
    """

    if not data:
        return b""

    output = bytearray()
    position = 0
    positions_by_prefix: dict[bytes, list[int]] = {}

    def remember(start: int, end: int) -> None:
        for index in range(start, min(end, len(data))):
            if index + 3 <= len(data):
                key = data[index : index + 3]
                positions_by_prefix.setdefault(key, []).append(index)

    while position < len(data):
        flag_index = len(output)
        output.append(0)
        flags = 0
        for block in range(8):
            if position >= len(data):
                break

            best_length = 0
            best_distance = 0
            maximum = min(18, len(data) - position)
            if maximum >= 3:
                key = data[position : position + 3]
                candidates = positions_by_prefix.get(key, [])
                lower_bound = max(0, position - 0x1000)
                for candidate in reversed(candidates):
                    if candidate < lower_bound:
                        break
                    distance = position - candidate
                    if distance <= 0 or distance > 0x1000:
                        continue
                    length = _match_length(data, position, candidate, maximum)
                    if length > best_length:
                        best_length = length
                        best_distance = distance
                        if length == maximum:
                            break

            old_position = position
            if best_length >= 3:
                flags |= 1 << (7 - block)
                encoded_distance = best_distance - 1
                output.append(((best_length - 3) << 4) | (encoded_distance >> 8))
                output.append(encoded_distance & 0xFF)
                position += best_length
            else:
                output.append(data[position])
                position += 1
            remember(old_position, position)
        output[flag_index] = flags
    return bytes(output)


def rle_decompress(payload: bytes, output_size: int) -> tuple[bytes, int]:
    """Read Nintendo/Level-5 RLE payloads (method 4)."""

    output = bytearray()
    cursor = 0
    while len(output) < output_size:
        if cursor >= len(payload):
            raise XsError("RLE verisi beklenenden erken bitti.")
        control = payload[cursor]
        cursor += 1
        if control & 0x80:
            length = (control & 0x7F) + 3
            if cursor >= len(payload):
                raise XsError("RLE tekrar baytı eksik.")
            output.extend(bytes([payload[cursor]]) * length)
            cursor += 1
        else:
            length = (control & 0x7F) + 1
            if cursor + length > len(payload):
                raise XsError("RLE ham bloğu eksik.")
            output.extend(payload[cursor : cursor + length])
            cursor += length
    if len(output) != output_size:
        raise XsError("RLE bloğu bildirilen boyutu aştı.")
    return bytes(output), cursor


def rle_compress(data: bytes) -> bytes:
    """Create a Nintendo/Level-5 RLE payload."""

    output = bytearray()
    position = 0
    while position < len(data):
        run_length = 1
        while (
            position + run_length < len(data)
            and data[position + run_length] == data[position]
            and run_length < 130
        ):
            run_length += 1
        if run_length >= 3:
            output.append(0x80 | (run_length - 3))
            output.append(data[position])
            position += run_length
            continue

        raw_start = position
        position += run_length
        while position < len(data) and position - raw_start < 128:
            following_run = 1
            while (
                position + following_run < len(data)
                and data[position + following_run] == data[position]
                and following_run < 3
            ):
                following_run += 1
            if following_run >= 3:
                break
            position += following_run
        raw_length = position - raw_start
        output.append(raw_length - 1)
        output.extend(data[raw_start:position])
    return bytes(output)


class _HuffmanNode:
    def __init__(
        self,
        *,
        frequency: int = 0,
        symbol: int = 0,
        children: tuple["_HuffmanNode", "_HuffmanNode"] | None = None,
    ) -> None:
        self.frequency = frequency
        self.code = symbol
        self.children = children

    @property
    def is_leaf(self) -> bool:
        return self.children is None

    def collect_codes(self, prefix: str, output: dict[int, str]) -> None:
        if self.children is None:
            output[self.code] = prefix
            return
        self.children[0].collect_codes(prefix + "0", output)
        self.children[1].collect_codes(prefix + "1", output)


def huffman_compress(data: bytes, bits_per_symbol: int) -> bytes:
    """Create Level-5's compact Huffman-4/Huffman-8 payload."""

    if bits_per_symbol == 8:
        symbols = list(data)
    elif bits_per_symbol == 4:
        symbols = [nibble for byte in data for nibble in (byte & 0x0F, byte >> 4)]
    else:
        raise XsError(f"Geçersiz Huffman sembol genişliği: {bits_per_symbol}.")
    if not symbols:
        return b"\0\0"

    frequencies: dict[int, int] = {}
    for symbol in symbols:
        frequencies[symbol] = frequencies.get(symbol, 0) + 1
    pending = [
        _HuffmanNode(frequency=frequency, symbol=symbol)
        for symbol, frequency in frequencies.items()
    ]
    if len(pending) == 1:
        pending.append(_HuffmanNode(symbol=(symbols[0] + 1) & 0xFF))

    while len(pending) > 1:
        pending = sorted(pending, key=lambda node: node.frequency)
        left, right = pending[0], pending[1]
        parent = _HuffmanNode(
            frequency=left.frequency + right.frequency,
            children=(left, right),
        )
        pending = pending[2:] + [parent]
    root = pending[0]

    internal_nodes: list[_HuffmanNode] = []
    pending_internal = [root]
    while pending_internal:
        selected_index = min(
            range(len(pending_internal)),
            key=lambda index: pending_internal[index].code - index,
        )
        node = pending_internal.pop(selected_index)
        node.code = (len(internal_nodes) - node.code) & 0xFF
        internal_nodes.append(node)
        assert node.children is not None
        for child in reversed(node.children):
            if not child.is_leaf:
                child.code = len(internal_nodes) & 0xFF
                pending_internal.append(child)

    if len(internal_nodes) > 0xFF:
        raise XsError("Huffman ağacı Level-5 sınırını aştı.")
    codes: dict[int, str] = {}
    root.collect_codes("", codes)

    output = bytearray([len(internal_nodes)])
    serialized_nodes = [root]
    for node in internal_nodes:
        assert node.children is not None
        serialized_nodes.extend(node.children)
    for node in serialized_nodes:
        code = node.code
        if node.children is not None:
            if node.children[0].is_leaf:
                code |= 0x80
            if node.children[1].is_leaf:
                code |= 0x40
        output.append(code)

    word = 0
    bit_count = 0
    for symbol in symbols:
        for bit in codes[symbol]:
            word = (word << 1) | (bit == "1")
            bit_count += 1
            if bit_count == 32:
                output.extend(struct.pack("<I", word))
                word = 0
                bit_count = 0
    if bit_count:
        output.extend(struct.pack("<I", word << (32 - bit_count)))
    return bytes(output)


def huffman_decompress(
    payload: bytes, output_size: int, bits_per_symbol: int
) -> tuple[bytes, int]:
    """Read Level-5's compact Huffman-4/Huffman-8 payload."""

    if bits_per_symbol not in (4, 8):
        raise XsError(f"Geçersiz Huffman sembol genişliği: {bits_per_symbol}.")
    if len(payload) < 2:
        raise XsError("Huffman başlığı eksik.")
    tree_size = payload[0]
    tree_root = payload[1]
    tree_end = 2 + tree_size * 2
    if tree_end > len(payload):
        raise XsError("Huffman ağacı eksik.")
    tree = payload[2:tree_end]
    cursor = tree_end
    symbols_needed = output_size * 8 // bits_per_symbol
    symbols = bytearray()
    node = tree_root
    tree_position = 0
    code_word = 0
    bit_index = 32

    while len(symbols) < symbols_needed:
        if bit_index == 32:
            if cursor + 4 > len(payload):
                raise XsError("Huffman bit akışı beklenenden erken bitti.")
            code_word = struct.unpack_from("<I", payload, cursor)[0]
            cursor += 4
            bit_index = 0
        bit = (code_word >> (31 - bit_index)) & 1
        bit_index += 1

        tree_position += (node & 0x3F) * 2 + 2
        direction = 2 if bit == 0 else 1
        leaf = bool((node >> (5 + direction)) & 1)
        child_index = tree_position - direction
        if child_index < 0 or child_index >= len(tree):
            raise XsError("Huffman ağacında geçersiz çocuk ofseti.")
        node = tree[child_index]
        if leaf:
            symbols.append(node)
            node = tree_root
            tree_position = 0

    if bits_per_symbol == 8:
        return bytes(symbols), cursor
    if any(symbol > 0x0F for symbol in symbols):
        raise XsError("Huffman-4 akışında 4 bitten büyük sembol bulundu.")
    output = bytes(
        symbols[index] | (symbols[index + 1] << 4)
        for index in range(0, len(symbols), 2)
    )
    return output, cursor


def unpack_level5_container(blob: bytes, offset: int, limit: int) -> tuple[bytes, int, int]:
    if offset < 0 or offset + 4 > limit or limit > len(blob):
        raise XsError(f"Geçersiz Level-5 bölüm sınırı: 0x{offset:X}..0x{limit:X}.")
    size_and_method = struct.unpack_from("<I", blob, offset)[0]
    output_size = size_and_method >> 3
    method = size_and_method & 7
    payload = blob[offset + 4 : limit]

    if method == 0:
        if len(payload) < output_size:
            raise XsError("Sıkıştırılmamış bölüm bildirilen boyuttan kısa.")
        return payload[:output_size], method, output_size
    if method == 1:
        output, consumed = lz10_decompress(payload, output_size)
        return output, method, consumed
    if method == 4:
        output, consumed = rle_decompress(payload, output_size)
        return output, method, consumed
    if method == 2:
        output, consumed = huffman_decompress(payload, output_size, 4)
        return output, method, consumed
    if method == 3:
        output, consumed = huffman_decompress(payload, output_size, 8)
        return output, method, consumed
    raise XsError(f"Bilinmeyen Level-5 sıkıştırma yöntemi: {method}.")


def pack_level5_container(data: bytes, method: int) -> bytes:
    if len(data) > 0x1FFFFFFF:
        raise XsError("Level-5 bölümü için veri fazla büyük.")
    if method == 0:
        payload = data
    elif method == 1:
        payload = lz10_compress(data)
    elif method == 2:
        payload = huffman_compress(data, 4)
    elif method == 3:
        payload = huffman_compress(data, 8)
    elif method == 4:
        payload = rle_compress(data)
    else:
        raise XsError(f"Bilinmeyen Level-5 sıkıştırma yöntemi: {method}.")
    return struct.pack("<I", (len(data) << 3) | method) + payload


@dataclass(frozen=True)
class TextRecord:
    text_id: str
    offset: int
    original: str
    original_bytes: bytes
    entry_indices: tuple[int, ...]


@dataclass
class XsFile:
    raw_file: bytes
    table0_count: int
    table0_offset_words: int
    table1_count: int
    table1_offset_words: int
    string_offset_words: int
    prefix: bytes
    table0: bytes
    entries: list[tuple[int, int]]
    string_blob: bytes
    methods: tuple[int, int, int]
    section_padding: tuple[bytes, bytes, bytes]

    @classmethod
    def from_bytes(cls, raw_file: bytes, source: str = "<bytes>") -> "XsFile":
        if len(raw_file) < 20:
            raise XsError(f"{source}: dosya XSCR başlığı için fazla kısa.")
        magic, table0_count, table0_offset, table1_count, table1_offset, string_offset = (
            struct.unpack_from("<4sHHiII", raw_file, 0)
        )
        if magic != b"XSCR":
            raise XsError(f"{source}: XSCR imzası bulunamadı.")
        if table0_count < 0 or table1_count < 0:
            raise XsError(f"{source}: negatif tablo sayısı bulundu.")

        table0_pos = table0_offset * 4
        table1_pos = table1_offset * 4
        string_pos = string_offset * 4
        if not (20 <= table0_pos < table1_pos < string_pos <= len(raw_file) - 4):
            raise XsError(
                f"{source}: bölüm ofsetleri geçersiz: "
                f"{table0_pos}, {table1_pos}, {string_pos}."
            )

        table0, method0, consumed0 = unpack_level5_container(raw_file, table0_pos, table1_pos)
        table1, method1, consumed1 = unpack_level5_container(raw_file, table1_pos, string_pos)
        strings, method2, consumed2 = unpack_level5_container(raw_file, string_pos, len(raw_file))

        expected_table0 = table0_count * 8
        expected_table1 = table1_count * 8
        if len(table0) != expected_table0:
            raise XsError(
                f"{source}: tablo 0 boyutu {len(table0)}, beklenen {expected_table0}."
            )
        if len(table1) != expected_table1:
            raise XsError(
                f"{source}: tablo 1 boyutu {len(table1)}, beklenen {expected_table1}."
            )

        entries = [
            struct.unpack_from("<iI", table1, index * 8)
            for index in range(table1_count)
        ]
        pad0_start = table0_pos + 4 + consumed0
        pad1_start = table1_pos + 4 + consumed1
        pad2_start = string_pos + 4 + consumed2
        padding = (
            raw_file[pad0_start:table1_pos],
            raw_file[pad1_start:string_pos],
            raw_file[pad2_start:],
        )
        for section_index, pad in enumerate(padding):
            if any(pad):
                raise XsError(
                    f"{source}: bölüm {section_index} sonrasında bilinmeyen sıfır dışı veri var."
                )

        instance = cls(
            raw_file=raw_file,
            table0_count=table0_count,
            table0_offset_words=table0_offset,
            table1_count=table1_count,
            table1_offset_words=table1_offset,
            string_offset_words=string_offset,
            prefix=raw_file[20:table0_pos],
            table0=table0,
            entries=entries,
            string_blob=strings,
            methods=(method0, method1, method2),
            section_padding=padding,
        )
        instance.text_records(source)
        return instance

    @classmethod
    def read(cls, path: Path) -> "XsFile":
        return cls.from_bytes(path.read_bytes(), str(path))

    def text_records(self, source: str = "<XSCR>") -> list[TextRecord]:
        references: dict[int, list[int]] = {}
        order: list[int] = []
        for entry_index, (identifier, value) in enumerate(self.entries):
            if identifier != 0x18:
                continue
            if value not in references:
                references[value] = []
                order.append(value)
            references[value].append(entry_index)

        records: list[TextRecord] = []
        for number, offset in enumerate(order):
            if offset >= len(self.string_blob):
                raise XsError(
                    f"{source}: text{number:06d} ofseti metin tablosunun dışında: "
                    f"0x{offset:X}/0x{len(self.string_blob):X}."
                )
            end = self.string_blob.find(b"\0", offset)
            if end < 0:
                raise XsError(f"{source}: text{number:06d} NUL ile sonlanmıyor.")
            raw = self.string_blob[offset:end]
            try:
                decoded = raw.decode(TEXT_ENCODING)
            except UnicodeDecodeError as exc:
                raise XsError(
                    f"{source}: text{number:06d} CP932 olarak çözülemiyor: {exc}."
                ) from exc
            records.append(
                TextRecord(
                    text_id=f"text{number:06d}",
                    offset=offset,
                    original=decoded,
                    original_bytes=raw,
                    entry_indices=tuple(references[offset]),
                )
            )
        return records

    def _compression_methods(self, compression: str) -> tuple[int, int, int]:
        if compression == "lz10":
            return (1, 1, 1)
        if compression == "none":
            return (0, 0, 0)
        if compression == "original":
            return self.methods
        raise XsError(f"Bilinmeyen sıkıştırma seçeneği: {compression}.")

    def rebuild(
        self,
        translations: Mapping[str, str],
        *,
        compression: str = "lz10",
        encoding_policy: str = "strict",
    ) -> tuple[bytes, dict[str, str], list[dict[str, str]]]:
        records = self.text_records()
        expected_ids = {record.text_id for record in records}
        unknown = sorted(set(translations) - expected_ids)
        if unknown:
            raise XsError(f"Projede XS dosyasında olmayan kimlikler var: {', '.join(unknown[:8])}.")

        entries = list(self.entries)
        strings = bytearray(self.string_blob)
        normalized: dict[str, str] = {}
        encoding_changes: list[dict[str, str]] = []

        for record in records:
            requested = translations.get(record.text_id, record.original)
            if "\0" in requested:
                raise XsError(f"{record.text_id}: çeviri NUL karakteri içeriyor.")
            normalized_text, encoded, changes = encode_translation(requested, encoding_policy)
            normalized[record.text_id] = normalized_text
            for before, after in changes:
                encoding_changes.append(
                    {"id": record.text_id, "before": before, "after": after}
                )

            if normalized_text == record.original and encoded == record.original_bytes:
                new_offset = record.offset
            else:
                new_offset = len(strings)
                if new_offset > 0xFFFFFFFF:
                    raise XsError("Metin tablosu 32 bit ofset sınırını aştı.")
                strings.extend(encoded)
                strings.append(0)
            for entry_index in record.entry_indices:
                identifier, _ = entries[entry_index]
                entries[entry_index] = (identifier, new_offset)

        table1 = b"".join(struct.pack("<iI", identifier, value) for identifier, value in entries)
        methods = self._compression_methods(compression)

        output = bytearray(b"\0" * 20)
        output.extend(self.prefix)
        if len(output) != self.table0_offset_words * 4:
            raise XsError("Başlık ile tablo 0 arasındaki veri korunamadı.")
        output.extend(pack_level5_container(self.table0, methods[0]))
        align4(output)
        table1_offset_words = len(output) // 4
        output.extend(pack_level5_container(table1, methods[1]))
        align4(output)
        string_offset_words = len(output) // 4
        output.extend(pack_level5_container(bytes(strings), methods[2]))
        align4(output)

        struct.pack_into(
            "<4sHHiII",
            output,
            0,
            b"XSCR",
            self.table0_count,
            self.table0_offset_words,
            self.table1_count,
            table1_offset_words,
            string_offset_words,
        )
        return bytes(output), normalized, encoding_changes


TURKISH_ASCII_MAP = str.maketrans(
    {
        "Ç": "C",
        "ç": "c",
        "Ğ": "G",
        "ğ": "g",
        "İ": "I",
        "ı": "i",
        "Ö": "O",
        "ö": "o",
        "Ş": "S",
        "ş": "s",
        "Ü": "U",
        "ü": "u",
        "Â": "A",
        "â": "a",
        "Î": "I",
        "î": "i",
        "Û": "U",
        "û": "u",
    }
)


PUNCTUATION_ASCII_MAP = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "–": "-",
        "—": "-",
        "…": "...",
        " ": " ",
    }
)
CONTROL_CODE_PATTERN = re.compile(r"<[^>\n]+>")


def control_codes(text: str) -> list[str]:
    return CONTROL_CODE_PATTERN.findall(text)


def encode_translation(text: str, policy: str) -> tuple[str, bytes, list[tuple[str, str]]]:
    if policy == "strict":
        try:
            return text, text.encode(TEXT_ENCODING), []
        except UnicodeEncodeError as exc:
            problem = text[exc.start : exc.end]
            raise XsError(
                f"CP932 ile kodlanamayan karakter {problem!r}; "
                "Türkçe font yaması yoksa --encoding-policy turkish-ascii kullanın."
            ) from exc

    if policy != "turkish-ascii":
        raise XsError(f"Bilinmeyen kodlama ilkesi: {policy}.")

    translated = text.translate(TURKISH_ASCII_MAP)
    changes: list[tuple[str, str]] = []
    if translated != text:
        for before, after in zip(text, translated):
            if before != after:
                changes.append((before, after))

    result: list[str] = []
    for character in translated:
        try:
            character.encode(TEXT_ENCODING)
            result.append(character)
            continue
        except UnicodeEncodeError:
            pass
        punctuation = character.translate(PUNCTUATION_ASCII_MAP)
        if punctuation != character:
            replacement = punctuation
        else:
            decomposed = unicodedata.normalize("NFKD", character)
            replacement = decomposed.encode("ascii", "ignore").decode("ascii")
        if not replacement:
            raise XsError(
                f"{character!r} karakteri CP932 için güvenli biçimde dönüştürülemiyor."
            )
        replacement.encode(TEXT_ENCODING)
        result.append(replacement)
        changes.append((character, replacement))
    normalized = "".join(result)
    return normalized, normalized.encode(TEXT_ENCODING), changes


@dataclass
class ProjectFile:
    path: str
    source_sha256: str
    string_count: int


@dataclass
class ProjectText:
    path: str
    source_sha256: str
    text_id: str
    offset: int
    original: str
    translation: str


@dataclass
class TranslationProject:
    files: dict[str, ProjectFile]
    texts: dict[str, list[ProjectText]]

    def translations_for(self, path: str) -> dict[str, str]:
        return {row.text_id: row.translation for row in self.texts.get(path, [])}


def collect_xs_files(source: Path, include_auxiliary: bool = False) -> list[tuple[str, Path]]:
    if source.is_file():
        if source.suffix.lower() != ".xs":
            raise XsError(f"XS dosyası bekleniyordu: {source}")
        return [(source.name, source)]
    if not source.is_dir():
        raise XsError(f"Kaynak bulunamadı: {source}")

    result: list[tuple[str, Path]] = []
    for path in source.rglob("*.xs"):
        relative = path.relative_to(source)
        if not include_auxiliary and any(
            part.lower() in AUXILIARY_DIRS for part in relative.parts[:-1]
        ):
            continue
        result.append((relative.as_posix(), path))
    return sorted(result)


def _decode_kup_text(value: str) -> str:
    # Some hand-edited files in the supplied archive contain "&gt>" instead
    # of "&gt;".  Repair only the five XML entities before decoding them.
    value = re.sub(r"&(lt|gt|amp|quot|apos)>", r"&\1;", value)
    return html.unescape(value)


def _recover_kup_entries(text: str, path: Path) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    entry_pattern = re.compile(
        r'<entry\b[^>]*\bname="([^"]+)"[^>]*>(.*?)</entry>', re.DOTALL
    )
    for match in entry_pattern.finditer(text):
        text_id, body = match.groups()
        original_match = re.search(r"<original>(.*?)</original>", body, re.DOTALL)
        edited_match = re.search(r"<edited>(.*?)</edited>", body, re.DOTALL)
        if original_match is None:
            raise XsError(f"KUP kurtarmada original alanı bulunamadı: {path} {text_id}")
        original = _decode_kup_text(original_match.group(1))
        edited = original if edited_match is None else _decode_kup_text(edited_match.group(1))
        if text_id in entries:
            raise XsError(f"KUP içinde yinelenen kimlik {text_id}: {path}")
        entries[text_id] = (original, edited)
    if not entries:
        raise XsError(f"KUP kurtarma ayrıştırıcısı hiçbir girdi bulamadı: {path}")
    return entries


def parse_kup(path: Path) -> tuple[dict[str, tuple[str, str]], bool]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise XsError(f"KUP okunamadı ({path}): {exc}") from exc
        return _recover_kup_entries(text, path), True
    except OSError as exc:
        raise XsError(f"KUP okunamadı ({path}): {exc}") from exc
    entries: dict[str, tuple[str, str]] = {}
    for entry in root.findall("./entries/entry"):
        text_id = entry.get("name")
        if not text_id:
            raise XsError(f"KUP girdisinde ad eksik: {path}")
        if text_id in entries:
            raise XsError(f"KUP içinde yinelenen kimlik {text_id}: {path}")
        original = entry.findtext("original") or ""
        edited = entry.findtext("edited")
        entries[text_id] = (original, original if edited is None else edited)
    return entries, False


def find_kup(kup_root: Path, relative_xs: str, source_path: Path) -> Path | None:
    relative = Path(relative_xs)
    candidates = [
        kup_root / (relative.as_posix() + ".kup"),
        kup_root / relative.parent / "tr" / (relative.name + ".kup"),
        source_path.with_name(source_path.name + ".kup"),
        source_path.parent / "tr" / (source_path.name + ".kup"),
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def make_project(
    source: Path,
    *,
    kup_root: Path | None = None,
    include_auxiliary: bool = False,
    allow_source_mismatch: bool = False,
) -> tuple[TranslationProject, dict[str, object]]:
    files: dict[str, ProjectFile] = {}
    texts: dict[str, list[ProjectText]] = {}
    missing_kup: list[str] = []
    mismatches: list[dict[str, str]] = []
    missing_kup_ids: list[dict[str, str]] = []
    extra_kup_ids: list[dict[str, str]] = []
    recovered_kup_files: list[str] = []
    control_code_warnings: list[dict[str, object]] = []
    translated_count = 0
    text_count = 0

    xs_files = collect_xs_files(source, include_auxiliary)
    if not xs_files:
        raise XsError(f"XS dosyası bulunamadı: {source}")

    for relative, path in xs_files:
        raw = path.read_bytes()
        xs = XsFile.from_bytes(raw, str(path))
        digest = sha256_bytes(raw)
        records = xs.text_records(str(path))
        files[relative] = ProjectFile(relative, digest, len(records))

        kup_entries: dict[str, tuple[str, str]] = {}
        if kup_root is not None:
            kup_path = find_kup(kup_root, relative, path)
            if kup_path is None:
                missing_kup.append(relative)
            else:
                kup_entries, recovered = parse_kup(kup_path)
                if recovered:
                    recovered_kup_files.append(relative)

        rows: list[ProjectText] = []
        record_ids = {record.text_id for record in records}
        for record in records:
            original = record.original
            translation = original
            if kup_entries:
                kup_value = kup_entries.get(record.text_id)
                if kup_value is None:
                    missing_kup_ids.append({"file": relative, "id": record.text_id})
                else:
                    kup_original, translation = kup_value
                    if kup_original != original:
                        mismatches.append(
                            {
                                "file": relative,
                                "id": record.text_id,
                                "xs_original": original,
                                "kup_original": kup_original,
                            }
                        )
            if translation != original:
                translated_count += 1
                original_codes = control_codes(original)
                translation_codes = control_codes(translation)
                if original_codes != translation_codes:
                    control_code_warnings.append(
                        {
                            "file": relative,
                            "id": record.text_id,
                            "original_codes": original_codes,
                            "translation_codes": translation_codes,
                        }
                    )
            rows.append(
                ProjectText(
                    path=relative,
                    source_sha256=digest,
                    text_id=record.text_id,
                    offset=record.offset,
                    original=original,
                    translation=translation,
                )
            )
            text_count += 1
        texts[relative] = rows

        for extra_id in sorted(set(kup_entries) - record_ids):
            extra_kup_ids.append({"file": relative, "id": extra_id})

    if mismatches and not allow_source_mismatch:
        first = mismatches[0]
        raise XsError(
            f"KUP kaynağı XS ile uyuşmuyor: {first['file']} {first['id']}. "
            "Doğru orijinal dosyayı kullanın veya bilinçli olarak "
            "--allow-source-mismatch ekleyin."
        )

    report: dict[str, object] = {
        "tool_version": TOOL_VERSION,
        "files": len(files),
        "texts": text_count,
        "translated_texts": translated_count,
        "missing_kup_files": missing_kup,
        "source_mismatches": mismatches,
        "missing_kup_ids": missing_kup_ids,
        "extra_kup_ids": extra_kup_ids,
        "recovered_kup_files": recovered_kup_files,
        "control_code_warnings": control_code_warnings,
    }
    return TranslationProject(files, texts), report


def write_project(project: TranslationProject, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".csv":
        with destination.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "file",
                    "source_sha256",
                    "id",
                    "offset",
                    "original",
                    "translation",
                ],
            )
            writer.writeheader()
            for path in sorted(project.texts):
                for row in project.texts[path]:
                    writer.writerow(
                        {
                            "file": row.path,
                            "source_sha256": row.source_sha256,
                            "id": row.text_id,
                            "offset": row.offset,
                            "original": row.original,
                            "translation": row.translation,
                        }
                    )
        return

    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        metadata = {
            "kind": "project",
            "format": PROJECT_FORMAT,
            "version": PROJECT_VERSION,
            "tool_version": TOOL_VERSION,
            "encoding": TEXT_ENCODING,
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
        handle.write(json.dumps(metadata, ensure_ascii=False) + "\n")
        for path in sorted(project.files):
            file_entry = project.files[path]
            handle.write(
                json.dumps(
                    {
                        "kind": "file",
                        "file": path,
                        "source_sha256": file_entry.source_sha256,
                        "string_count": file_entry.string_count,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            for row in project.texts.get(path, []):
                handle.write(
                    json.dumps(
                        {
                            "kind": "text",
                            "file": row.path,
                            "id": row.text_id,
                            "offset": row.offset,
                            "original": row.original,
                            "translation": row.translation,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )


def read_project(path: Path) -> TranslationProject:
    if path.suffix.lower() == ".csv":
        files: dict[str, ProjectFile] = {}
        texts: dict[str, list[ProjectText]] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"file", "source_sha256", "id", "offset", "original", "translation"}
            if not required.issubset(reader.fieldnames or []):
                raise XsError(f"CSV sütunları eksik: {path}")
            for line_number, row in enumerate(reader, start=2):
                relative = row["file"]
                try:
                    offset = int(row["offset"])
                except ValueError as exc:
                    raise XsError(f"CSV satır {line_number}: ofset sayı değil.") from exc
                project_row = ProjectText(
                    path=relative,
                    source_sha256=row["source_sha256"],
                    text_id=row["id"],
                    offset=offset,
                    original=row["original"],
                    translation=row["translation"],
                )
                texts.setdefault(relative, []).append(project_row)
                files.setdefault(
                    relative,
                    ProjectFile(relative, row["source_sha256"], 0),
                )
        for relative, file_entry in list(files.items()):
            files[relative] = ProjectFile(
                relative, file_entry.source_sha256, len(texts.get(relative, []))
            )
        return TranslationProject(files, texts)

    files = {}
    texts: dict[str, list[ProjectText]] = {}
    metadata_seen = False
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise XsError(f"JSONL satır {line_number} bozuk: {exc}") from exc
            kind = value.get("kind")
            if kind == "project":
                if metadata_seen:
                    raise XsError("JSONL içinde birden fazla proje başlığı var.")
                metadata_seen = True
                if value.get("format") != PROJECT_FORMAT or value.get("version") != PROJECT_VERSION:
                    raise XsError("Desteklenmeyen proje biçimi veya sürümü.")
            elif kind == "file":
                relative = value["file"]
                if relative in files:
                    raise XsError(f"JSONL içinde yinelenen dosya: {relative}")
                files[relative] = ProjectFile(
                    relative,
                    value["source_sha256"],
                    int(value["string_count"]),
                )
            elif kind == "text":
                relative = value["file"]
                texts.setdefault(relative, []).append(
                    ProjectText(
                        path=relative,
                        source_sha256="",
                        text_id=value["id"],
                        offset=int(value["offset"]),
                        original=value["original"],
                        translation=value["translation"],
                    )
                )
            else:
                raise XsError(f"JSONL satır {line_number}: bilinmeyen kayıt türü {kind!r}.")
    if not metadata_seen:
        raise XsError("JSONL proje başlığı bulunamadı.")
    for relative, rows in texts.items():
        if relative not in files:
            raise XsError(f"Metin kaydı için dosya başlığı yok: {relative}")
        seen_ids: set[str] = set()
        for row in rows:
            if row.text_id in seen_ids:
                raise XsError(f"Projede yinelenen kimlik: {relative} {row.text_id}")
            seen_ids.add(row.text_id)
        if len(rows) != files[relative].string_count:
            raise XsError(
                f"{relative}: proje {len(rows)} metin içeriyor; "
                f"dosya başlığı {files[relative].string_count} diyor."
            )
    return TranslationProject(files, texts)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_export(args: argparse.Namespace) -> dict[str, object]:
    project, report = make_project(
        args.source,
        include_auxiliary=args.include_auxiliary,
    )
    write_project(project, args.project)
    if args.report:
        write_json(args.report, report)
    return report


def command_migrate_kup(args: argparse.Namespace) -> dict[str, object]:
    project, report = make_project(
        args.source,
        kup_root=args.kup_root,
        include_auxiliary=args.include_auxiliary,
        allow_source_mismatch=args.allow_source_mismatch,
    )
    write_project(project, args.project)
    if args.report:
        write_json(args.report, report)
    return report


def command_inject(args: argparse.Namespace) -> dict[str, object]:
    project = read_project(args.project)
    xs_files = collect_xs_files(args.source, args.include_auxiliary)
    source_is_file = args.source.is_file()
    output_is_file = source_is_file and args.output.suffix.lower() == ".xs"
    source_paths = {relative for relative, _ in xs_files}
    project_paths = set(project.files)
    missing_source_files = sorted(project_paths - source_paths)
    missing_project_files: list[str] = []
    if missing_source_files:
        raise XsError(
            "Projede olup kaynakta bulunmayan XS dosyaları var: "
            + ", ".join(missing_source_files[:8])
        )

    output_files = 0
    applied = 0
    unchanged = 0
    encoding_changes: list[dict[str, str]] = []
    control_code_warnings: list[dict[str, object]] = []

    for relative, source_path in xs_files:
        raw = source_path.read_bytes()
        xs = XsFile.from_bytes(raw, str(source_path))
        file_entry = project.files.get(relative)
        if file_entry is None:
            if xs.text_records(str(source_path)):
                missing_project_files.append(relative)
            translations: dict[str, str] = {}
        else:
            digest = sha256_bytes(raw)
            if digest != file_entry.source_sha256 and not args.ignore_source_hash:
                raise XsError(
                    f"{relative}: kaynak SHA-256 projeyle uyuşmuyor. "
                    "Doğru temiz XS dosyasını kullanın veya bilinçli olarak "
                    "--ignore-source-hash ekleyin."
                )
            translations = project.translations_for(relative)
            for row in project.texts.get(relative, []):
                original_codes = control_codes(row.original)
                translation_codes = control_codes(row.translation)
                if original_codes != translation_codes:
                    control_code_warnings.append(
                        {
                            "file": relative,
                            "id": row.text_id,
                            "original_codes": original_codes,
                            "translation_codes": translation_codes,
                        }
                    )

        rebuilt, expected, file_encoding_changes = xs.rebuild(
            translations,
            compression=args.compression,
            encoding_policy=args.encoding_policy,
        )
        for change in file_encoding_changes:
            encoding_changes.append({"file": relative, **change})

        if output_is_file:
            destination = args.output
        else:
            destination = args.output / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(rebuilt)

        parsed = XsFile.from_bytes(rebuilt, str(destination))
        parsed_records = parsed.text_records(str(destination))
        original_records = xs.text_records(str(source_path))
        if parsed.table0 != xs.table0:
            raise XsError(f"{relative}: doğrulamada tablo 0 değişti.")
        if len(parsed.entries) != len(xs.entries):
            raise XsError(f"{relative}: doğrulamada tablo 1 sayısı değişti.")
        for before, after in zip(xs.entries, parsed.entries):
            if before[0] != after[0] or (before[0] != 0x18 and before[1] != after[1]):
                raise XsError(f"{relative}: metin dışı komut verisi değişti.")
        if len(parsed_records) != len(original_records):
            raise XsError(f"{relative}: doğrulamada benzersiz metin sayısı değişti.")
        for record in parsed_records:
            wanted = expected[record.text_id]
            if record.original != wanted:
                raise XsError(
                    f"{relative} {record.text_id}: doğrulama başarısız; "
                    f"beklenen {wanted!r}, okunan {record.original!r}."
                )
            if wanted == original_records[int(record.text_id[4:])].original:
                unchanged += 1
            else:
                applied += 1
        output_files += 1

    report: dict[str, object] = {
        "tool_version": TOOL_VERSION,
        "source_files": len(xs_files),
        "output_files": output_files,
        "translated_texts_applied": applied,
        "unchanged_texts": unchanged,
        "missing_project_files": missing_project_files,
        "encoding_changes": encoding_changes,
        "control_code_warnings": control_code_warnings,
        "compression": args.compression,
        "encoding_policy": args.encoding_policy,
    }
    if args.report:
        write_json(args.report, report)
    return report


def verify_one(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    xs = XsFile.from_bytes(raw, str(path))
    records = xs.text_records(str(path))
    return {
        "file": str(path),
        "sha256": sha256_bytes(raw),
        "table0_entries": xs.table0_count,
        "table1_entries": xs.table1_count,
        "texts": len(records),
        "compression_methods": list(xs.methods),
    }


def command_verify(args: argparse.Namespace) -> dict[str, object]:
    xs_files = collect_xs_files(args.source, args.include_auxiliary)
    if not xs_files:
        raise XsError(f"XS dosyası bulunamadı: {args.source}")
    files = [verify_one(path) for _, path in xs_files]
    method_sets: dict[str, int] = {}
    total_texts = 0
    for item in files:
        key = "/".join(str(value) for value in item["compression_methods"])
        method_sets[key] = method_sets.get(key, 0) + 1
        total_texts += int(item["texts"])
    report: dict[str, object] = {
        "tool_version": TOOL_VERSION,
        "valid_files": len(files),
        "texts": total_texts,
        "compression_method_sets": method_sets,
        "files": files if args.detailed else [],
    }
    if args.report:
        write_json(args.report, report)
    return report


def _synthetic_xs() -> bytes:
    table0 = struct.pack("<hhI", 7, 3, 0)
    strings = b"Hello\0World\0"
    entries = b"".join(
        [
            struct.pack("<iI", 0x18, 0),
            struct.pack("<iI", 0x44, 123456),
            struct.pack("<iI", 0x18, 6),
            struct.pack("<iI", 0x18, 0),
        ]
    )
    output = bytearray(b"\0" * 20)
    output.extend(pack_level5_container(table0, 1))
    align4(output)
    table1_offset = len(output) // 4
    output.extend(pack_level5_container(entries, 1))
    align4(output)
    string_offset = len(output) // 4
    output.extend(pack_level5_container(strings, 1))
    align4(output)
    struct.pack_into("<4sHHiII", output, 0, b"XSCR", 1, 5, 4, table1_offset, string_offset)
    return bytes(output)


def command_selftest(_args: argparse.Namespace) -> dict[str, object]:
    random_source = random.Random(0x58534352)
    samples = [
        b"",
        b"a",
        b"abc",
        b"A" * 4097,
        bytes(range(256)) * 4,
        bytes(random_source.randrange(256) for _ in range(8192)),
    ]
    for sample in samples:
        packed = lz10_compress(sample)
        unpacked, consumed = lz10_decompress(packed, len(sample))
        if unpacked != sample or consumed != len(packed):
            raise XsError("LZ10 öz sınaması başarısız.")

    source = XsFile.from_bytes(_synthetic_xs(), "<synthetic>")
    rebuilt, expected, _ = source.rebuild(
        {
            "text000000": "This is considerably longer than Hello",
            "text000001": "Dunya",
        },
        compression="lz10",
    )
    output = XsFile.from_bytes(rebuilt, "<synthetic-output>")
    values = {record.text_id: record.original for record in output.text_records()}
    if values != expected:
        raise XsError("XSCR yeniden oluşturma öz sınaması başarısız.")
    if output.entries[1] != source.entries[1]:
        raise XsError("XSCR metin dışı veri öz sınamada değişti.")
    if output.entries[0][1] != output.entries[3][1]:
        raise XsError("Yinelenen metin işaretçileri öz sınamada ayrıştı.")
    return {"tool_version": TOOL_VERSION, "selftest": "passed", "samples": len(samples)}


def path_argument(value: str) -> Path:
    return Path(value).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Level-5 XSCR metinlerini dışa aktarır ve güvenli biçimde yeniden enjekte eder."
    )
    parser.add_argument("--version", action="version", version=TOOL_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export", help="XS/XS dizinini UTF-8 JSONL veya CSV projesine aktar."
    )
    export_parser.add_argument("source", type=path_argument)
    export_parser.add_argument("project", type=path_argument)
    export_parser.add_argument("--include-auxiliary", action="store_true")
    export_parser.add_argument("--report", type=path_argument)
    export_parser.set_defaults(handler=command_export)

    migrate_parser = subparsers.add_parser(
        "migrate-kup", help="Eski Kuriimu .kup çevirilerini yeni projeye taşı."
    )
    migrate_parser.add_argument("source", type=path_argument)
    migrate_parser.add_argument("kup_root", type=path_argument)
    migrate_parser.add_argument("project", type=path_argument)
    migrate_parser.add_argument("--include-auxiliary", action="store_true")
    migrate_parser.add_argument("--allow-source-mismatch", action="store_true")
    migrate_parser.add_argument("--report", type=path_argument)
    migrate_parser.set_defaults(handler=command_migrate_kup)

    inject_parser = subparsers.add_parser(
        "inject", help="JSONL/CSV projesini temiz XS dosyalarına enjekte et."
    )
    inject_parser.add_argument("source", type=path_argument)
    inject_parser.add_argument("project", type=path_argument)
    inject_parser.add_argument("output", type=path_argument)
    inject_parser.add_argument(
        "--compression", choices=["lz10", "none", "original"], default="lz10"
    )
    inject_parser.add_argument(
        "--encoding-policy", choices=["strict", "turkish-ascii"], default="strict"
    )
    inject_parser.add_argument("--ignore-source-hash", action="store_true")
    inject_parser.add_argument("--include-auxiliary", action="store_true")
    inject_parser.add_argument("--report", type=path_argument)
    inject_parser.set_defaults(handler=command_inject)

    verify_parser = subparsers.add_parser("verify", help="XS dosyalarının yapısını doğrula.")
    verify_parser.add_argument("source", type=path_argument)
    verify_parser.add_argument("--include-auxiliary", action="store_true")
    verify_parser.add_argument("--detailed", action="store_true")
    verify_parser.add_argument("--report", type=path_argument)
    verify_parser.set_defaults(handler=command_verify)

    selftest_parser = subparsers.add_parser("selftest", help="Dahili kodlayıcı testlerini çalıştır.")
    selftest_parser.set_defaults(handler=command_selftest)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        report = args.handler(args)
    except (XsError, OSError, KeyError, ValueError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    display_report = dict(report)
    for key, value in list(display_report.items()):
        if isinstance(value, list) and len(value) > 20:
            display_report[key] = value[:5]
            display_report[f"{key}_count"] = len(value)
            display_report[f"{key}_note"] = "İlk 5 kayıt gösteriliyor; tam liste rapor dosyasındadır."
    print(json.dumps(display_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
