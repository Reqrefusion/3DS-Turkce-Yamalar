#!/usr/bin/env python3
"""Inspect and patch Kingdom Hearts 3D BCFNT fonts for Turkish glyphs.

The patch keeps every original glyph and appends six new glyph records for
Ğ/ğ, İ/ı and Ş/ş.  Their bitmap shapes are derived from the font's existing
G/g, I/i, S/s and C/c-with-cedilla glyphs so the result follows the original
font style.  BCFNT texture format 0x0B is Nintendo 3DS tiled A4.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import kh3d_message_tool as message_tool


CFNT_MAGIC = b"CFNT"
FINF_MAGIC = b"FINF"
TGLP_MAGIC = b"TGLP"
CWDH_MAGIC = b"CWDH"
CMAP_MAGIC = b"CMAP"
A4_FORMAT = 0x000B
TURKISH_CHARACTERS = "ĞğİıŞş"


@dataclass
class GlyphWidth:
    left: int
    glyph_width: int
    char_width: int


@dataclass
class WidthSection:
    offset: int
    start_index: int
    end_index: int
    next_data_offset: int


@dataclass
class MapSection:
    offset: int
    code_start: int
    code_end: int
    method: int
    next_data_offset: int


@dataclass
class Bcfnt:
    raw: bytes
    finf_offset: int
    tglp_offset: int
    sheet_data_offset: int
    sheet_size: int
    sheet_count: int
    sheet_format: int
    columns: int
    rows: int
    sheet_width: int
    sheet_height: int
    cell_width: int
    cell_height: int
    baseline: int
    char_map: Dict[int, int]
    widths: Dict[int, GlyphWidth]
    width_sections: List[WidthSection]
    map_sections: List[MapSection]
    block_count: int


class FontError(ValueError):
    pass


def align4(value: int) -> int:
    return (value + 3) & ~3


def parse_bcfnt(data: bytes, label: str = "BCFNT") -> Bcfnt:
    if len(data) < 0x34 or data[:4] != CFNT_MAGIC:
        raise FontError(f"{label} is not a CFNT/BCFNT file")
    if data[4:6] != b"\xff\xfe":
        raise FontError(f"{label} is not little-endian BCFNT")
    header_size = struct.unpack_from("<H", data, 6)[0]
    file_size, block_count = struct.unpack_from("<II", data, 12)
    if file_size != len(data):
        raise FontError(f"{label} has a mismatched file size")

    finf_offset = header_size
    if data[finf_offset : finf_offset + 4] != FINF_MAGIC:
        raise FontError(f"{label} has no FINF section")
    finf_data = finf_offset + 8
    tglp_data, cwdh_data, cmap_data = struct.unpack_from("<III", data, finf_data + 8)
    tglp_offset = tglp_data - 8
    if data[tglp_offset : tglp_offset + 4] != TGLP_MAGIC:
        raise FontError(f"{label} has an invalid TGLP pointer")

    tglp = tglp_offset + 8
    cell_width, cell_height, baseline, _max_char_width = struct.unpack_from(
        "<BBBB", data, tglp
    )
    sheet_size, sheet_count, sheet_format, columns, rows, sheet_width, sheet_height, sheet_data_offset = struct.unpack_from(
        "<IHHHHHHI", data, tglp + 4
    )
    if sheet_data_offset + sheet_size * sheet_count > len(data):
        raise FontError(f"{label} texture data extends past EOF")

    widths: Dict[int, GlyphWidth] = {}
    width_sections: List[WidthSection] = []
    next_data = cwdh_data
    visited = set()
    while next_data:
        offset = next_data - 8
        if offset in visited or data[offset : offset + 4] != CWDH_MAGIC:
            raise FontError(f"{label} has an invalid CWDH chain")
        visited.add(offset)
        section_size = struct.unpack_from("<I", data, offset + 4)[0]
        start_index, end_index, next_data = struct.unpack_from("<HHI", data, offset + 8)
        count = end_index - start_index + 1
        if end_index < start_index or 16 + count * 3 > section_size:
            raise FontError(f"{label} has an invalid CWDH range")
        for index in range(count):
            left, glyph_width, char_width = struct.unpack_from(
                "<bBB", data, offset + 16 + index * 3
            )
            widths[start_index + index] = GlyphWidth(left, glyph_width, char_width)
        width_sections.append(
            WidthSection(offset, start_index, end_index, next_data)
        )

    char_map: Dict[int, int] = {}
    map_sections: List[MapSection] = []
    next_data = cmap_data
    visited.clear()
    while next_data:
        offset = next_data - 8
        if offset in visited or data[offset : offset + 4] != CMAP_MAGIC:
            raise FontError(f"{label} has an invalid CMAP chain")
        visited.add(offset)
        section_size = struct.unpack_from("<I", data, offset + 4)[0]
        code_start, code_end, method, _reserved, next_data = struct.unpack_from(
            "<HHHHI", data, offset + 8
        )
        payload = offset + 20
        if method == 0:
            if section_size < 22:
                raise FontError(f"{label} has a short direct CMAP")
            base_index = struct.unpack_from("<H", data, payload)[0]
            for codepoint in range(code_start, code_end + 1):
                char_map[codepoint] = base_index + codepoint - code_start
        elif method == 1:
            count = code_end - code_start + 1
            if code_end < code_start or 20 + count * 2 > section_size:
                raise FontError(f"{label} has a short table CMAP")
            for index in range(count):
                glyph_index = struct.unpack_from("<H", data, payload + index * 2)[0]
                if glyph_index != 0xFFFF:
                    char_map[code_start + index] = glyph_index
        elif method == 2:
            pair_count = struct.unpack_from("<H", data, payload)[0]
            if 22 + pair_count * 4 > section_size:
                raise FontError(f"{label} has a short scan CMAP")
            for index in range(pair_count):
                codepoint, glyph_index = struct.unpack_from(
                    "<HH", data, payload + 2 + index * 4
                )
                char_map[codepoint] = glyph_index
        else:
            raise FontError(f"{label} uses unsupported CMAP method {method}")
        map_sections.append(MapSection(offset, code_start, code_end, method, next_data))

    if not width_sections or not map_sections:
        raise FontError(f"{label} has no glyph width or character map data")
    return Bcfnt(
        raw=data,
        finf_offset=finf_offset,
        tglp_offset=tglp_offset,
        sheet_data_offset=sheet_data_offset,
        sheet_size=sheet_size,
        sheet_count=sheet_count,
        sheet_format=sheet_format,
        columns=columns,
        rows=rows,
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        cell_width=cell_width,
        cell_height=cell_height,
        baseline=baseline,
        char_map=char_map,
        widths=widths,
        width_sections=width_sections,
        map_sections=map_sections,
        block_count=block_count,
    )


def morton8(x: int, y: int) -> int:
    result = 0
    for bit in range(3):
        result |= ((x >> bit) & 1) << (bit * 2)
        result |= ((y >> bit) & 1) << (bit * 2 + 1)
    return result


def a4_pixel_location(font: Bcfnt, x: int, y: int) -> Tuple[int, bool]:
    if not (0 <= x < font.sheet_width and 0 <= y < font.sheet_height):
        raise FontError(f"Texture coordinate outside sheet: ({x}, {y})")
    tiles_per_row = font.sheet_width // 8
    tile_index = (y // 8) * tiles_per_row + (x // 8)
    pixel_index = tile_index * 64 + morton8(x & 7, y & 7)
    return font.sheet_data_offset + pixel_index // 2, bool(pixel_index & 1)


def get_a4_pixel(data: bytes, font: Bcfnt, x: int, y: int) -> int:
    offset, high = a4_pixel_location(font, x, y)
    value = data[offset]
    return value >> 4 if high else value & 0x0F


def set_a4_pixel(data: bytearray, font: Bcfnt, x: int, y: int, alpha: int) -> None:
    offset, high = a4_pixel_location(font, x, y)
    alpha &= 0x0F
    if high:
        data[offset] = (data[offset] & 0x0F) | (alpha << 4)
    else:
        data[offset] = (data[offset] & 0xF0) | alpha


def glyph_origin(font: Bcfnt, glyph_index: int) -> Tuple[int, int]:
    capacity = font.columns * font.rows * font.sheet_count
    if not 0 <= glyph_index < capacity:
        raise FontError(
            f"Glyph index {glyph_index} exceeds texture capacity {capacity}"
        )
    cells_per_sheet = font.columns * font.rows
    sheet_index = glyph_index // cells_per_sheet
    local_index = glyph_index % cells_per_sheet
    if sheet_index:
        raise FontError("Multi-sheet font patching is not implemented")
    x = (local_index % font.columns) * (font.cell_width + 1) + 1
    y = (local_index // font.columns) * (font.cell_height + 1) + 1
    return x, y


def read_glyph(data: bytes, font: Bcfnt, glyph_index: int) -> List[List[int]]:
    origin_x, origin_y = glyph_origin(font, glyph_index)
    return [
        [
            get_a4_pixel(data, font, origin_x + x, origin_y + y)
            for x in range(font.cell_width)
        ]
        for y in range(font.cell_height)
    ]


def write_glyph(
    data: bytearray, font: Bcfnt, glyph_index: int, pixels: List[List[int]]
) -> None:
    origin_x, origin_y = glyph_origin(font, glyph_index)
    for y in range(font.cell_height):
        for x in range(font.cell_width):
            set_a4_pixel(data, font, origin_x + x, origin_y + y, pixels[y][x])


def nonzero_bbox(pixels: List[List[int]]) -> Tuple[int, int, int, int]:
    points = [
        (x, y)
        for y, row in enumerate(pixels)
        for x, value in enumerate(row)
        if value
    ]
    if not points:
        raise FontError("Cannot derive an accent from an empty glyph")
    return (
        min(x for x, _y in points),
        min(y for _x, y in points),
        max(x for x, _y in points),
        max(y for _x, y in points),
    )


def accent_gap(pixels: List[List[int]]) -> int:
    occupied = [any(row) for row in pixels]
    first = next((index for index, value in enumerate(occupied) if value), 0)
    for index in range(first + 1, len(occupied) - 1):
        if not occupied[index] and any(occupied[index + 1 :]):
            return index
    return max(1, len(occupied) // 3)


def remove_top_accent(pixels: List[List[int]]) -> List[List[int]]:
    result = [row[:] for row in pixels]
    gap = accent_gap(result)
    for y in range(gap + 1):
        result[y] = [0] * len(result[y])
    return result


def extract_top_accent(pixels: List[List[int]]) -> List[Tuple[int, int, int]]:
    gap = accent_gap(pixels)
    return [
        (x, y, value)
        for y in range(gap)
        for x, value in enumerate(pixels[y])
        if value
    ]


def add_centered_dot(
    base: List[List[int]], dot_source: List[List[int]]
) -> List[List[int]]:
    result = [row[:] for row in base]
    dot = extract_top_accent(dot_source)
    if not dot:
        raise FontError("The source i glyph has no separate dot")
    dot_min_x = min(x for x, _y, _value in dot)
    dot_max_x = max(x for x, _y, _value in dot)
    dot_min_y = min(y for _x, y, _value in dot)
    dot_max_y = max(y for _x, y, _value in dot)
    base_min_x, base_min_y, base_max_x, _base_max_y = nonzero_bbox(base)
    dot_width = dot_max_x - dot_min_x + 1
    dot_height = dot_max_y - dot_min_y + 1
    center_x = (base_min_x + base_max_x) // 2
    start_x = center_x - dot_width // 2
    start_y = max(0, base_min_y - dot_height - 1)
    for x, y, value in dot:
        target_x = start_x + x - dot_min_x
        target_y = start_y + y - dot_min_y
        if 0 <= target_x < len(result[0]) and 0 <= target_y < len(result):
            result[target_y][target_x] = max(result[target_y][target_x], value)
    return result


def add_breve(pixels: List[List[int]]) -> List[List[int]]:
    result = [row[:] for row in pixels]
    min_x, min_y, max_x, _max_y = nonzero_bbox(result)
    available = max(2, min_y)
    width = min(7, max(3, (max_x - min_x + 1) // 2))
    if width % 2 == 0:
        width += 1
    width = min(width, max_x - min_x + 1)
    center_x = (min_x + max_x) // 2
    start_x = center_x - width // 2
    bottom_y = min_y - 1
    top_y = max(0, bottom_y - 1)
    if available <= 2:
        top_y = 0
        bottom_y = 1
    for index in range(width):
        x = start_x + index
        if not 0 <= x < len(result[0]):
            continue
        distance = min(index, width - index - 1)
        y = top_y if distance == 0 else bottom_y
        result[y][x] = 15 if distance else 12
    return result


def add_cedilla(
    target: List[List[int]], plain_c: List[List[int]], cedilla_c: List[List[int]]
) -> List[List[int]]:
    result = [row[:] for row in target]
    _min_x, _min_y, _max_x, plain_bottom = nonzero_bbox(plain_c)
    for y in range(min(len(result), plain_bottom + 1), len(result)):
        for x in range(len(result[y])):
            if cedilla_c[y][x]:
                result[y][x] = max(result[y][x], cedilla_c[y][x])
    return result


def build_turkish_glyphs(
    data: bytes, font: Bcfnt
) -> Dict[str, Tuple[List[List[int]], GlyphWidth]]:
    required = "GgSsIiCcÇçÏ"
    missing = [character for character in required if ord(character) not in font.char_map]
    if missing:
        raise FontError(f"font has no base glyphs for: {''.join(missing)}")

    glyphs = {
        character: read_glyph(data, font, font.char_map[ord(character)])
        for character in required
    }

    capital_i_dotted_base = remove_top_accent(glyphs["Ï"])
    turkish = {
        "Ğ": add_breve(glyphs["G"]),
        "ğ": add_breve(glyphs["g"]),
        "İ": add_centered_dot(capital_i_dotted_base, glyphs["i"]),
        "ı": remove_top_accent(glyphs["i"]),
        "Ş": add_cedilla(glyphs["S"], glyphs["C"], glyphs["Ç"]),
        "ş": add_cedilla(glyphs["s"], glyphs["c"], glyphs["ç"]),
    }
    width_source = {"Ğ": "G", "ğ": "g", "İ": "I", "ı": "i", "Ş": "S", "ş": "s"}
    return {
        character: (
            pixels,
            font.widths[font.char_map[ord(width_source[character])]],
        )
        for character, pixels in turkish.items()
    }


def patch_bcfnt(data: bytes, label: str) -> Tuple[bytes, List[str]]:
    font = parse_bcfnt(data, label)
    missing_characters = [
        character for character in TURKISH_CHARACTERS if ord(character) not in font.char_map
    ]
    if not missing_characters:
        return data, []
    if font.sheet_format != A4_FORMAT or font.sheet_count != 1:
        raise FontError(
            f"{label} uses unsupported texture format/sheet count "
            f"({font.sheet_format}, {font.sheet_count})"
        )

    generated = build_turkish_glyphs(data, font)
    max_glyph_index = max(font.widths)
    new_indices = {
        character: max_glyph_index + index + 1
        for index, character in enumerate(missing_characters)
    }
    if max(new_indices.values()) >= font.columns * font.rows:
        raise FontError(f"{label} has no room for Turkish glyphs in its texture")

    output = bytearray(data)
    for character, glyph_index in new_indices.items():
        write_glyph(output, font, glyph_index, generated[character][0])

    while len(output) % 4:
        output.append(0)
    new_cwdh_offset = len(output)
    cwdh_size = align4(16 + len(missing_characters) * 3)
    cwdh = bytearray(cwdh_size)
    struct.pack_into(
        "<4sIHHI",
        cwdh,
        0,
        CWDH_MAGIC,
        cwdh_size,
        min(new_indices.values()),
        max(new_indices.values()),
        0,
    )
    for index, character in enumerate(missing_characters):
        width = generated[character][1]
        struct.pack_into(
            "<bBB", cwdh, 16 + index * 3, width.left, width.glyph_width, width.char_width
        )
    struct.pack_into(
        "<I", output, font.width_sections[-1].offset + 12, new_cwdh_offset + 8
    )
    output.extend(cwdh)

    new_cmap_offset = len(output)
    cmap_size = align4(22 + len(missing_characters) * 4)
    cmap = bytearray(cmap_size)
    struct.pack_into(
        "<4sIHHHHIH",
        cmap,
        0,
        CMAP_MAGIC,
        cmap_size,
        0,
        0xFFFF,
        2,
        0,
        0,
        len(missing_characters),
    )
    for index, character in enumerate(sorted(missing_characters, key=ord)):
        struct.pack_into(
            "<HH", cmap, 22 + index * 4, ord(character), new_indices[character]
        )
    struct.pack_into(
        "<I", output, font.map_sections[-1].offset + 16, new_cmap_offset + 8
    )
    output.extend(cmap)

    struct.pack_into("<I", output, 12, len(output))
    struct.pack_into("<I", output, 16, font.block_count + 2)
    patched = bytes(output)
    verified = parse_bcfnt(patched, label)
    still_missing = [
        character for character in missing_characters if ord(character) not in verified.char_map
    ]
    if still_missing:
        raise FontError(f"{label} patch verification failed: {''.join(still_missing)}")
    return patched, missing_characters


def rebuild_rbin(
    archive: message_tool.RbinArchive, replacements: Dict[int, bytes]
) -> bytes:
    header = bytearray(archive.raw[: archive.data_offset])
    payload = bytearray()
    current_offset = archive.data_offset
    for entry in archive.entries:
        aligned_offset = message_tool.align(current_offset)
        payload.extend(b"\0" * (aligned_offset - current_offset))
        current_offset = aligned_offset
        file_data = replacements.get(entry.index, message_tool.entry_bytes(archive, entry))
        info = (entry.info & 0x80000000) | len(file_data)
        struct.pack_into("<I", header, entry.entry_offset + 8, info)
        struct.pack_into("<I", header, entry.entry_offset + 12, current_offset)
        payload.extend(file_data)
        current_offset += len(file_data)
    final_size = message_tool.align(current_offset)
    payload.extend(b"\0" * (final_size - current_offset))
    return bytes(header + payload)


def analyze_font_rbin(path: Path) -> None:
    archive = message_tool.parse_rbin(path)
    print(f"File: {path}")
    print(f"SHA-256: {message_tool.sha256(path)}")
    print(f"Entries: {len(archive.entries)}")
    for entry in archive.entries:
        raw = message_tool.entry_bytes(archive, entry)
        if not entry.name.lower().endswith(".bcfnt"):
            print(f"{entry.name}: not BCFNT")
            continue
        font = parse_bcfnt(raw, entry.name)
        supported = "".join(
            character for character in TURKISH_CHARACTERS if ord(character) in font.char_map
        )
        missing = "".join(
            character for character in TURKISH_CHARACTERS if ord(character) not in font.char_map
        )
        has_bases = all(ord(character) in font.char_map for character in "GgSsIiCcÇçÏ")
        print(
            f"{entry.name}: glyphs={len(font.widths)}, map={len(font.char_map)}, "
            f"Turkish={supported or '-'}, missing={missing or '-'}, "
            f"patchable={'yes' if has_bases else 'no'}"
        )


def patch_font_rbin(source: Path, output: Path) -> Tuple[List[str], int]:
    archive = message_tool.parse_rbin(source)
    replacements: Dict[int, bytes] = {}
    patched_fonts: List[str] = []
    added_glyphs = 0
    for entry in archive.entries:
        if not entry.name.lower().endswith(".bcfnt"):
            continue
        raw = message_tool.entry_bytes(archive, entry)
        try:
            patched, added = patch_bcfnt(raw, entry.name)
        except FontError as exc:
            # Fonts without a Latin alphabet (numeral/menu display fonts) do
            # not render translated prose and are intentionally left intact.
            if "base glyphs" in str(exc):
                continue
            raise
        if added:
            replacements[entry.index] = patched
            patched_fonts.append(entry.name)
            added_glyphs += len(added)
    if not replacements:
        if source.resolve() != output.resolve():
            shutil.copyfile(source, output)
        return [], 0
    output.write_bytes(rebuild_rbin(archive, replacements))

    verified_archive = message_tool.parse_rbin(output)
    for entry in verified_archive.entries:
        if entry.name in patched_fonts:
            font = parse_bcfnt(message_tool.entry_bytes(verified_archive, entry), entry.name)
            missing = [
                character
                for character in TURKISH_CHARACTERS
                if ord(character) not in font.char_map
            ]
            if missing:
                raise FontError(
                    f"Output verification failed for {entry.name}: {''.join(missing)}"
                )
    return patched_fonts, added_glyphs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or patch Kingdom Hearts 3D font.rbin Turkish glyphs"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="show Turkish coverage")
    analyze_parser.add_argument("font_rbin", type=Path)
    patch_parser = subparsers.add_parser("patch", help="add missing Turkish glyphs")
    patch_parser.add_argument("font_rbin", type=Path)
    patch_parser.add_argument("output", type=Path)
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            analyze_font_rbin(args.font_rbin)
        elif args.command == "patch":
            fonts, glyphs = patch_font_rbin(args.font_rbin, args.output)
            print(
                f"Patched {len(fonts)} fonts / added {glyphs} glyph records: "
                f"{', '.join(fonts) if fonts else 'already complete'}"
            )
            print(f"Output: {args.output}")
    except (OSError, FontError, message_tool.FormatError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
