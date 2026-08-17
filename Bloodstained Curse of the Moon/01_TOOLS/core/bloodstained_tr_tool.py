#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bloodstained: Curse of the Moon (Nintendo 3DS) translation helper.

Supports the Inti Creates containers found in the supplied European release:
  * *.ttb     : UTF-8 text tables (cipher key: txt20170401)
  * *.osbctr  : N3DS RGBA4444 image resources (cipher key: obj90210)
  * BMPFont.bfbctr: font container codepoint presence check (key: bft90210)

No game executable/code patching is performed. The build command creates only
modified files, suitable for a Luma3DS LayeredFS romfs override.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Tuple

MASK64 = (1 << 64) - 1
BASE_KEY = 0xA1B34F58CAD705B2
TTB_KEY = "txt20170401"
OSB_KEY = "obj90210"
FONT_KEY = "bft90210"

EMOJI_RE = re.compile(r"<emoji/[^>]+>")
PRINTF_RE = re.compile(r"%(?:\d+\$)?[-+#0 ']*\d*(?:\.\d+)?[hlLzjt]*[diuoxXfFeEgGaAcspn%]")


def _initial_key(key_string: str) -> int:
    key = BASE_KEY
    for ch in key_string:
        key = ((key + ord(ch)) * 141) & MASK64
    return key


def decrypt_bytes(data: bytes, key_string: str) -> bytes:
    """Decrypt an Inti Creates stream. Key feedback uses the encrypted byte."""
    key = _initial_key(key_string)
    out = bytearray(len(data))
    for i, encrypted in enumerate(data):
        out[i] = encrypted ^ ((key >> (i & 0x1F)) & 0xFF)
        key = ((key + encrypted) * 141) & MASK64
    return bytes(out)


def encrypt_bytes(data: bytes, key_string: str) -> bytes:
    """Encrypt an Inti Creates stream. Key feedback uses the generated cipher byte."""
    key = _initial_key(key_string)
    out = bytearray(len(data))
    for i, plain in enumerate(data):
        encrypted = plain ^ ((key >> (i & 0x1F)) & 0xFF)
        out[i] = encrypted
        key = ((key + encrypted) * 141) & MASK64
    return bytes(out)


def unpack_container(path: Path, key_string: str) -> bytes:
    encrypted = path.read_bytes()
    dec = decrypt_bytes(encrypted, key_string)
    if len(dec) < 6:
        raise ValueError(f"Container too small: {path}")
    expected_size = struct.unpack_from("<I", dec, 0)[0]
    raw = zlib.decompress(dec[4:])
    if len(raw) != expected_size:
        raise ValueError(f"Size mismatch in {path}: expected {expected_size}, got {len(raw)}")
    return raw


def pack_container(raw: bytes, key_string: str) -> bytes:
    payload = struct.pack("<I", len(raw)) + zlib.compress(raw, level=9)
    return encrypt_bytes(payload, key_string)


class TtbTable:
    def __init__(self, raw: bytes):
        self.raw = raw
        if len(raw) < 8:
            raise ValueError("TTB is too small")
        self.header_size, self.record_size = struct.unpack_from("<II", raw, 0)
        if self.header_size != 8 or self.record_size != 16:
            raise ValueError(
                f"Unexpected TTB layout: header={self.header_size}, record={self.record_size}"
            )

        records: List[List[int]] = []
        pos = self.header_size
        min_string_offset = len(raw)
        while pos + self.record_size <= min_string_offset:
            vals = list(struct.unpack_from("<IIII", raw, pos))
            string_offset = vals[3]
            if not (pos + self.record_size <= string_offset < len(raw)):
                break
            records.append(vals)
            min_string_offset = min(min_string_offset, string_offset)
            pos += self.record_size
            if pos == min_string_offset:
                break

        if not records:
            raise ValueError("Could not infer TTB records")
        if pos != min_string_offset:
            raise ValueError(
                f"TTB record/string boundary is inconsistent: records end 0x{pos:X}, strings start 0x{min_string_offset:X}"
            )

        self.records = records
        self.string_start = min_string_offset
        self.offset_to_text: Dict[int, str] = {}
        for rec in records:
            off = rec[3]
            if off in self.offset_to_text:
                continue
            end = raw.find(b"\0", off)
            if end < 0:
                raise ValueError(f"Missing NUL terminator at 0x{off:X}")
            self.offset_to_text[off] = raw[off:end].decode("utf-8")

        self.slot_offsets = sorted(self.offset_to_text)

    def text_for_record(self, index: int) -> str:
        return self.offset_to_text[self.records[index][3]]

    def build(self, translations: Dict[int, str]) -> bytes:
        # Preserve the original physical order of text slots. This is not
        # required for lookup, but minimizes structural changes.
        slot_to_records: Dict[int, List[int]] = {}
        for i, rec in enumerate(self.records):
            slot_to_records.setdefault(rec[3], []).append(i)

        # If multiple records ever share one slot and only some are translated,
        # all shared records must agree. Supplied game files currently have no
        # shared offsets, but this keeps the writer safe.
        slot_text: Dict[int, str] = {}
        for old_off in self.slot_offsets:
            indices = slot_to_records[old_off]
            candidates = [translations[i] for i in indices if i in translations]
            if candidates and any(c != candidates[0] for c in candidates):
                raise ValueError(f"Conflicting translations for shared text offset 0x{old_off:X}")
            slot_text[old_off] = candidates[0] if candidates else self.offset_to_text[old_off]

        out = bytearray(self.string_start)
        out[: self.header_size] = struct.pack("<II", self.header_size, self.record_size)

        new_offsets: Dict[int, int] = {}
        for old_off in self.slot_offsets:
            new_offsets[old_off] = len(out)
            out.extend(slot_text[old_off].encode("utf-8"))
            out.append(0)

        for i, rec in enumerate(self.records):
            hash_value, left, right, old_off = rec
            struct.pack_into(
                "<IIII",
                out,
                self.header_size + i * self.record_size,
                hash_value,
                left,
                right,
                new_offsets[old_off],
            )
        return bytes(out)


def load_ttb(path: Path) -> TtbTable:
    return TtbTable(unpack_container(path, TTB_KEY))


def write_ttb(path: Path, table: TtbTable, translations: Dict[int, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pack_container(table.build(translations), TTB_KEY))


def _language_hint(text: str) -> str:
    if not text:
        return "empty"
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text):
        return "ja/mixed"
    # Rough hint only; the table contains multiple Western languages.
    if re.search(r"[A-Za-z]", text):
        return "latin"
    return "other"


def extract_ttb_csv(romfs: Path, output_csv: Path) -> None:
    rows = []
    for path in sorted(romfs.glob("*.ttb")):
        table = load_ttb(path)
        for index, rec in enumerate(table.records):
            rows.append(
                {
                    "file": path.name,
                    "index": index,
                    "hash": f"{rec[0]:08X}",
                    "language_hint": _language_hint(table.text_for_record(index)),
                    "original": table.text_for_record(index),
                    "translation_tr": "",
                }
            )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "index", "hash", "language_hint", "original", "translation_tr"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Extracted {len(rows)} TTB records -> {output_csv}")


def load_translation_csv(csv_path: Path) -> Dict[Tuple[str, int], Tuple[str, str]]:
    result: Dict[Tuple[str, int], Tuple[str, str]] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"file", "index", "original", "translation_tr"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain columns: {', '.join(sorted(required))}")
        for row in reader:
            tr = row.get("translation_tr", "")
            if tr == "":
                continue
            key = (row["file"], int(row["index"]))
            result[key] = (row.get("original", ""), tr)
    return result


def validate_translation(original: str, translated: str) -> List[str]:
    warnings = []
    if EMOJI_RE.findall(original) != EMOJI_RE.findall(translated):
        warnings.append("emoji/control tokens changed")
    if PRINTF_RE.findall(original) != PRINTF_RE.findall(translated):
        warnings.append("printf-style format tokens changed")
    # A NUL would truncate the stored UTF-8 string.
    if "\0" in translated:
        warnings.append("translation contains NUL")
    return warnings


def build_layeredfs(romfs: Path, translation_csv: Path, output_romfs: Path) -> None:
    translations = load_translation_csv(translation_csv)
    grouped: Dict[str, Dict[int, Tuple[str, str]]] = {}
    for (filename, index), pair in translations.items():
        grouped.setdefault(filename, {})[index] = pair

    output_romfs.mkdir(parents=True, exist_ok=True)
    modified_files = 0
    changed_strings = 0
    warning_count = 0

    for filename, entries in sorted(grouped.items()):
        source = romfs / filename
        if not source.exists():
            raise FileNotFoundError(f"Missing source TTB: {source}")
        table = load_ttb(source)
        patches: Dict[int, str] = {}
        for index, (csv_original, translated) in sorted(entries.items()):
            if not (0 <= index < len(table.records)):
                raise IndexError(f"{filename}: record {index} does not exist")
            actual = table.text_for_record(index)
            if csv_original != actual:
                raise ValueError(
                    f"{filename}[{index}] original text mismatch. Refusing to patch the wrong game/version."
                )
            warnings = validate_translation(actual, translated)
            if warnings:
                warning_count += len(warnings)
                print(f"WARNING {filename}[{index}]: {', '.join(warnings)}", file=sys.stderr)
            patches[index] = translated

        if patches:
            write_ttb(output_romfs / filename, table, patches)
            modified_files += 1
            changed_strings += len(patches)

    print(
        f"Built LayeredFS romfs override: {modified_files} files, {changed_strings} translated strings"
        + (f", {warning_count} warnings" if warning_count else "")
        + f" -> {output_romfs}"
    )


def verify_ttb_dir(romfs: Path) -> None:
    count = 0
    for path in sorted(romfs.glob("*.ttb")):
        table = load_ttb(path)
        # Round-trip logical content with no translations.
        rebuilt_raw = table.build({})
        reparsed = TtbTable(rebuilt_raw)
        if len(reparsed.records) != len(table.records):
            raise ValueError(f"Record-count round-trip failed for {path.name}")
        for i in range(len(table.records)):
            if reparsed.text_for_record(i) != table.text_for_record(i):
                raise ValueError(f"Text round-trip failed for {path.name}[{i}]")
        count += 1
    print(f"Verified {count} TTB files successfully")


# --- OSBCTR image helpers -------------------------------------------------

def _morton8(x: int, y: int) -> int:
    # x bits in even positions, y bits in odd positions.
    return (
        (x & 1)
        | ((y & 1) << 1)
        | ((x & 2) << 1)
        | ((y & 2) << 2)
        | ((x & 4) << 2)
        | ((y & 4) << 3)
    )


def parse_osb(raw: bytes):
    if len(raw) < 44:
        raise ValueError("OSB is too small")
    h = list(struct.unpack_from("<11I", raw, 0))
    node_offset, data_size, fmt, width, height, data_offset, post_size, post_offset, unk1, unk2, unk3 = h
    if data_offset + data_size > len(raw) or post_offset + post_size > len(raw):
        raise ValueError("OSB offsets are out of range")
    return h


def decode_osb_rgba4444(raw: bytes):
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow is required for OSB PNG commands") from e

    h = parse_osb(raw)
    _, data_size, fmt, width, height, data_offset, *_ = h
    if fmt != 4:
        raise NotImplementedError(f"Only OSB format 4 (RGBA4444) is supported; found format {fmt}")
    if width % 8 or height % 8:
        raise ValueError("3DS OSB dimensions must be multiples of 8")
    expected = width * height * 2
    if data_size != expected:
        raise ValueError(f"Unexpected RGBA4444 data size: expected {expected}, got {data_size}")
    img_data = raw[data_offset : data_offset + data_size]
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    tiles_per_row = width // 8
    for y in range(height):
        sy = height - 1 - y  # N3DS CtrTransformation.YFlip
        for x in range(width):
            encoded_index = ((sy // 8) * tiles_per_row + (x // 8)) * 64 + _morton8(x & 7, sy & 7)
            v = struct.unpack_from("<H", img_data, encoded_index * 2)[0]
            a = (v & 0xF) * 17
            b = ((v >> 4) & 0xF) * 17
            g = ((v >> 8) & 0xF) * 17
            r = ((v >> 12) & 0xF) * 17
            pixels[x, y] = (r, g, b, a)
    return image


def encode_osb_rgba4444(image) -> bytes:
    width, height = image.size
    if width % 8 or height % 8:
        raise ValueError("3DS OSB dimensions must be multiples of 8")
    image = image.convert("RGBA")
    pixels = image.load()
    out = bytearray(width * height * 2)
    tiles_per_row = width // 8
    for y in range(height):
        sy = height - 1 - y
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Quantize to the nearest 4-bit value.
            rn = (r + 8) // 17
            gn = (g + 8) // 17
            bn = (b + 8) // 17
            an = (a + 8) // 17
            rn = min(15, rn); gn = min(15, gn); bn = min(15, bn); an = min(15, an)
            v = (rn << 12) | (gn << 8) | (bn << 4) | an
            encoded_index = ((sy // 8) * tiles_per_row + (x // 8)) * 64 + _morton8(x & 7, sy & 7)
            struct.pack_into("<H", out, encoded_index * 2, v)
    return bytes(out)


def extract_osb_pngs(romfs: Path, output_dir: Path, english_only: bool = True) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = "*_en.osbctr" if english_only else "*.osbctr"
    count = 0
    for path in sorted(romfs.glob(pattern)):
        try:
            raw = unpack_container(path, OSB_KEY)
            h = parse_osb(raw)
            if h[2] != 4:
                continue
            image = decode_osb_rgba4444(raw)
            image.save(output_dir / (path.stem + ".png"))
            count += 1
        except Exception as e:
            print(f"WARNING: {path.name}: {e}", file=sys.stderr)
    print(f"Extracted {count} OSBCTR atlas images -> {output_dir}")


def inject_osb_png(source_osb: Path, png_path: Path, output_osb: Path) -> None:
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow is required for OSB PNG commands") from e
    raw = bytearray(unpack_container(source_osb, OSB_KEY))
    h = parse_osb(raw)
    _, data_size, fmt, width, height, data_offset, post_size, post_offset, *_ = h
    if fmt != 4:
        raise NotImplementedError("Only RGBA4444 OSB files are supported")
    with Image.open(png_path) as image:
        if image.size != (width, height):
            raise ValueError(f"PNG must remain {width}x{height}; got {image.size[0]}x{image.size[1]}")
        encoded = encode_osb_rgba4444(image)
    if len(encoded) != data_size:
        raise ValueError("Encoded image size changed unexpectedly")
    raw[data_offset : data_offset + data_size] = encoded
    output_osb.parent.mkdir(parents=True, exist_ok=True)
    output_osb.write_bytes(pack_container(bytes(raw), OSB_KEY))
    print(f"Injected {png_path.name} -> {output_osb}")


def osb_roundtrip_test(romfs: Path) -> None:
    count = 0
    for path in sorted(romfs.glob("*_en.osbctr")):
        raw = unpack_container(path, OSB_KEY)
        h = parse_osb(raw)
        if h[2] != 4:
            continue
        image = decode_osb_rgba4444(raw)
        encoded = encode_osb_rgba4444(image)
        data = raw[h[5] : h[5] + h[1]]
        if encoded != data:
            raise ValueError(f"OSB pixel round-trip failed for {path.name}")
        count += 1
    print(f"Verified exact RGBA4444 pixel round-trip for {count} English OSBCTR files")


def font_check(font_path: Path) -> None:
    raw = unpack_container(font_path, FONT_KEY)
    chars = "çğıİöşüÇĞÖŞÜ"
    missing = []
    print(f"Font container: {font_path.name}; decompressed size={len(raw)} bytes")
    for ch in chars:
        needle = struct.pack("<I", ord(ch))
        positions = []
        start = 0
        while True:
            pos = raw.find(needle, start)
            if pos < 0:
                break
            positions.append(pos)
            start = pos + 1
        if positions:
            print(f"  {ch} U+{ord(ch):04X}: present (first offset 0x{positions[0]:X})")
        else:
            print(f"  {ch} U+{ord(ch):04X}: MISSING")
            missing.append(ch)
    if missing:
        raise SystemExit("Missing Turkish codepoints: " + "".join(missing))
    print("All checked Turkish codepoints are present in the font container.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bloodstained COTM 3DS Turkish translation helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract-text", help="Extract all TTB records to UTF-8 CSV")
    p.add_argument("romfs", type=Path)
    p.add_argument("csv", type=Path)

    p = sub.add_parser("build", help="Build only translated TTBs into a LayeredFS romfs override")
    p.add_argument("romfs", type=Path)
    p.add_argument("csv", type=Path)
    p.add_argument("output_romfs", type=Path)

    p = sub.add_parser("verify-text", help="Verify TTB parsing/rebuild logic")
    p.add_argument("romfs", type=Path)

    p = sub.add_parser("extract-osb", help="Extract English OSBCTR RGBA4444 atlases to PNG")
    p.add_argument("romfs", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--all", action="store_true", help="Try all .osbctr files, not only *_en.osbctr")

    p = sub.add_parser("inject-osb", help="Put an edited same-size PNG back into one OSBCTR")
    p.add_argument("source_osb", type=Path)
    p.add_argument("png", type=Path)
    p.add_argument("output_osb", type=Path)

    p = sub.add_parser("verify-osb", help="Verify exact English OSB pixel decode/encode round-trip")
    p.add_argument("romfs", type=Path)

    p = sub.add_parser("font-check", help="Check Turkish Unicode codepoints in BMPFont.bfbctr")
    p.add_argument("font", type=Path)

    args = parser.parse_args()
    if args.cmd == "extract-text":
        extract_ttb_csv(args.romfs, args.csv)
    elif args.cmd == "build":
        build_layeredfs(args.romfs, args.csv, args.output_romfs)
    elif args.cmd == "verify-text":
        verify_ttb_dir(args.romfs)
    elif args.cmd == "extract-osb":
        extract_osb_pngs(args.romfs, args.output_dir, english_only=not args.all)
    elif args.cmd == "inject-osb":
        inject_osb_png(args.source_osb, args.png, args.output_osb)
    elif args.cmd == "verify-osb":
        osb_roundtrip_test(args.romfs)
    elif args.cmd == "font-check":
        font_check(args.font)


if __name__ == "__main__":
    main()
