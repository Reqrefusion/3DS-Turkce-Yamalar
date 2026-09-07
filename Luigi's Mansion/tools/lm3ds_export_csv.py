#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Luigi's Mansion (3DS / EUR) localization + font CSV exporter.

Designed for the EUR GREZZO GMSG variant used by Luigi's Mansion (CTR-P-BGNP).
Unlike the Japanese GMSG variant, normal EU text is UTF-8 bytes while control
codes are binary structures introduced by byte 0x7F and aligned to 16/32 bits.

Examples:
  python lm3ds_export_csv.py --original "game.zip" --patch "turkish_patch.zip" --out csv_out
  python lm3ds_export_csv.py --original extracted_romfs --patch extracted_patch --out csv_out

Outputs:
  <gmsg filename>.csv       Languages side-by-side (e.g. main.gmsg.csv)
  <gmsg filename>.qa.csv    Turkish-vs-English structural QA
  <gzf filename>.csv        Font glyph table (e.g. location.gzf.csv)
  font_summary.csv          Turkish glyph coverage summary
  export_summary.txt        Short run summary

CSV files are UTF-8 with BOM so Turkish characters open cleanly in Excel.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import struct
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Tuple

TURKISH_GLYPHS = "çÇğĞıİöÖşŞüÜ"
PREFERRED_LANG_ORDER = ["English", "Dutch", "French", "German", "Italian", "Spanish", "Turkish"]


class Source:
    """Read files from either a directory tree or a ZIP without extracting it."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self.is_zip = self.path.is_file() and zipfile.is_zipfile(self.path)
        self._zip: Optional[zipfile.ZipFile] = zipfile.ZipFile(self.path, "r") if self.is_zip else None
        if self.is_zip:
            self._names = [self._norm(n) for n in self._zip.namelist() if not n.endswith("/")]
        elif self.path.is_dir():
            self._names = [self._norm(str(p.relative_to(self.path))) for p in self.path.rglob("*") if p.is_file()]
        else:
            raise ValueError(f"Not a directory or ZIP: {self.path}")

    @staticmethod
    def _norm(name: str) -> str:
        return str(PurePosixPath(name.replace("\\", "/"))).lstrip("./")

    def names(self) -> List[str]:
        return list(self._names)

    def read(self, name: str) -> bytes:
        name = self._norm(name)
        if self.is_zip:
            assert self._zip is not None
            # Preserve original archive spelling by matching normalized path.
            for raw in self._zip.namelist():
                if self._norm(raw) == name:
                    return self._zip.read(raw)
            raise KeyError(name)
        return (self.path / Path(name)).read_bytes()

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def __enter__(self) -> "Source":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def find_region_eu_prefix(src: Source) -> str:
    """Return path prefix ending at Region_EU, regardless of outer ZIP folder."""
    candidates = []
    for name in src.names():
        parts = PurePosixPath(name).parts
        for i, part in enumerate(parts):
            if part == "Region_EU":
                candidates.append("/".join(parts[: i + 1]))
                break
    if not candidates:
        raise FileNotFoundError(f"Region_EU was not found in {src.path}")
    # Prefer the shortest prefix (normally romfs/Region_EU).
    return sorted(set(candidates), key=lambda s: (len(PurePosixPath(s).parts), len(s)))[0]


@dataclass
class GmsgEntry:
    msg_id: int
    unknown: int
    offset: int
    length: int
    text: str
    controls: List[Tuple[int, ...]]


def _align(pos: int, alignment: int) -> int:
    return pos + ((-pos) % alignment)


def decode_eu_gmsg_text(raw: bytes) -> Tuple[str, List[Tuple[int, ...]]]:
    """
    Decode one EUR GMSG entry.

    EU strings are UTF-8 bytes plus binary controls. 0x7F is a one-byte marker;
    the following command is aligned to 2 bytes. Commands carrying uint32
    parameters then align their payload to 4 bytes.
    """
    out: List[str] = []
    controls: List[Tuple[int, ...]] = []
    pos = 0

    while pos < len(raw):
        marker = raw.find(b"\x7f", pos)
        if marker < 0:
            if pos < len(raw):
                out.append(raw[pos:].decode("utf-8", errors="strict"))
            break

        if marker > pos:
            out.append(raw[pos:marker].decode("utf-8", errors="strict"))

        cur = _align(marker + 1, 2)
        if cur + 2 > len(raw):
            raise ValueError(f"Truncated GMSG control at +0x{marker:X}")
        cmd = struct.unpack_from("<H", raw, cur)[0]
        cur += 2

        if cmd == 0x00:  # end
            controls.append((cmd,))
            break
        if cmd == 0x01:  # line break
            controls.append((cmd,))
            out.append("<br>")
            pos = cur
            continue
        if cmd == 0x02:  # page/section break
            controls.append((cmd,))
            out.append("<hr>")
            pos = cur
            continue

        # Commands with aligned uint32 payloads.
        if cmd in (0x08, 0x0E, 0x0F, 0x15, 0x19):
            cur = _align(cur, 4)
            count = 2 if cmd == 0x19 else 1
            if cur + count * 4 > len(raw):
                raise ValueError(f"Truncated GMSG command 0x{cmd:04X}")
            vals = tuple(struct.unpack_from("<I", raw, cur + i * 4)[0] for i in range(count))
            cur += count * 4
            controls.append((cmd, *vals))

            if cmd == 0x15:  # text color
                out.append("</color>" if vals[0] == 0xFFFFFFFF else f"<color={vals[0]:04X}>")
            else:
                out.append("[%04X:%s]" % (cmd, ",".join(f"{v:08X}" for v in vals)))
            pos = cur
            continue

        if cmd == 0x11:  # 16-bit message/reference parameter
            if cur + 2 > len(raw):
                raise ValueError("Truncated GMSG command 0x0011")
            val = struct.unpack_from("<H", raw, cur)[0]
            cur += 2
            controls.append((cmd, val))
            out.append(f"[0011:{val:04X}]")
            pos = cur
            continue

        # Fail loudly rather than silently corrupting a new/unknown format.
        context = raw[max(0, marker - 12): min(len(raw), marker + 24)].hex(" ")
        raise ValueError(f"Unknown GMSG command 0x{cmd:04X} near +0x{marker:X}: {context}")

    return "".join(out), controls


def parse_gmsg(data: bytes) -> Dict[int, GmsgEntry]:
    if len(data) < 0x14 or data[:4] != b"GMSG":
        raise ValueError("Not a GMSG file")
    entry_count, table_offset = struct.unpack_from("<II", data, 0x0C)
    if table_offset + entry_count * 0x10 > len(data):
        raise ValueError("Invalid GMSG entry table")

    rows: Dict[int, GmsgEntry] = {}
    for i in range(entry_count):
        msg_id, unknown, offset, length = struct.unpack_from("<4I", data, table_offset + i * 0x10)
        if offset + length > len(data):
            raise ValueError(f"GMSG entry 0x{msg_id:X} points outside file")
        text, controls = decode_eu_gmsg_text(data[offset: offset + length])
        rows[msg_id] = GmsgEntry(msg_id, unknown, offset, length, text, controls)
    return rows


@dataclass
class GzfGlyph:
    codepoint: int
    char: str
    height: int
    image_id: int
    advance: int
    left: int
    top: int

    @property
    def usable(self) -> bool:
        # For normal letters in these fonts, zero height/advance means an effectively blank glyph.
        return self.height > 0 and self.advance > 0


def parse_gzf(data: bytes) -> Tuple[dict, List[GzfGlyph]]:
    if len(data) < 0x30 or data[:4] != b"GZFX":
        raise ValueError("Not a GZFX font")

    version, image_header_offset, image_len, entry_len, unk1 = struct.unpack_from("<IHHHH", data, 0x04)
    image_count, entry_count, unk2, image_format = struct.unpack_from("<IIII", data, 0x10)
    font_size, unk4, unk5, tile_width, tile_height, unk8, unk9 = struct.unpack_from("<HHHHHHI", data, 0x20)

    if image_len != 0x08 or entry_len != 0x0C:
        raise ValueError(f"Unexpected GZF record sizes: image={image_len}, entry={entry_len}")

    entry_offset = image_header_offset + image_count * image_len
    if entry_offset + entry_count * entry_len > len(data):
        raise ValueError("Invalid GZF entry table")

    glyphs: List[GzfGlyph] = []
    for i in range(entry_count):
        cp, height, image_id, advance, left, top = struct.unpack_from("<IHHHBB", data, entry_offset + i * entry_len)
        try:
            ch = chr(cp)
        except ValueError:
            ch = ""
        glyphs.append(GzfGlyph(cp, ch, height, image_id, advance, left, top))

    header = {
        "version": version,
        "image_header_offset": image_header_offset,
        "image_record_length": image_len,
        "entry_record_length": entry_len,
        "image_count": image_count,
        "entry_count": entry_count,
        "image_format": image_format,
        "font_size": font_size,
        "unk4": unk4,
        "unk5": unk5,
        "tile_width": tile_width,
        "tile_height": tile_height,
        "unk1": unk1,
        "unk2": unk2,
        "unk8": unk8,
        "unk9": unk9,
    }
    return header, glyphs


def write_csv(path: Path, header: Iterable[str], rows: Iterable[Iterable[object]], delimiter: str = ",") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
        w.writerow(list(header))
        for row in rows:
            w.writerow(list(row))


def language_gmsg_map(src: Source, region_prefix: str) -> Dict[str, Dict[str, str]]:
    """language -> basename -> archive/relative path"""
    result: Dict[str, Dict[str, str]] = {}
    prefix_parts = PurePosixPath(region_prefix).parts
    plen = len(prefix_parts)
    for name in src.names():
        parts = PurePosixPath(name).parts
        if len(parts) != plen + 2:
            continue
        if tuple(parts[:plen]) != tuple(prefix_parts):
            continue
        language, filename = parts[plen], parts[plen + 1]
        if filename.lower().endswith(".gmsg"):
            result.setdefault(language, {})[filename] = name
    return result


def region_root_gzf_map(src: Source, region_prefix: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    prefix_parts = PurePosixPath(region_prefix).parts
    plen = len(prefix_parts)
    for name in src.names():
        parts = PurePosixPath(name).parts
        if len(parts) == plen + 1 and tuple(parts[:plen]) == tuple(prefix_parts):
            fn = parts[-1]
            if fn.lower().endswith(".gzf"):
                result[fn] = name
    return result


def critical_controls(ctrls: List[Tuple[int, ...]]) -> List[Tuple[int, ...]]:
    # Line/page breaks and terminators are allowed to move/change in translation.
    return [c for c in ctrls if c[0] not in (0x00, 0x01, 0x02)]


def export_all(original_path: str, patch_path: Optional[str], out_dir: str, delimiter: str = ",") -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "gmsg_files": [],
        "font_files": [],
        "languages": [],
        "warnings": [],
    }

    with Source(original_path) as original:
        orig_region = find_region_eu_prefix(original)
        orig_gmsgs = language_gmsg_map(original, orig_region)
        gzfs = region_root_gzf_map(original, orig_region)

        patch = Source(patch_path) if patch_path else None
        try:
            patch_gmsgs: Dict[str, Dict[str, str]] = {}
            patch_region = None
            if patch:
                patch_region = find_region_eu_prefix(patch)
                patch_gmsgs = language_gmsg_map(patch, patch_region)

            # Discover all source GMSG basenames.
            filenames = sorted({fn for mp in orig_gmsgs.values() for fn in mp})
            if patch_gmsgs:
                filenames = sorted(set(filenames) | {fn for mp in patch_gmsgs.values() for fn in mp})

            original_languages = set(orig_gmsgs)
            languages = [l for l in PREFERRED_LANG_ORDER if l in original_languages or l == "Dutch"]
            for l in sorted(original_languages):
                if l not in languages:
                    languages.append(l)
            if patch:
                if "Turkish" not in languages:
                    languages.append("Turkish")
            summary["languages"] = languages

            for filename in filenames:
                parsed_by_lang: Dict[str, Dict[int, GmsgEntry]] = {}
                for lang, files in orig_gmsgs.items():
                    if filename in files:
                        parsed_by_lang[lang] = parse_gmsg(original.read(files[filename]))

                # User patch replaces English assets; expose it as Turkish.
                if patch:
                    tr_path = patch_gmsgs.get("English", {}).get(filename)
                    if tr_path:
                        parsed_by_lang["Turkish"] = parse_gmsg(patch.read(tr_path))
                    else:
                        summary["warnings"].append(f"Patch has no English/{filename}; Turkish column left empty")

                all_ids = sorted({msg_id for rows in parsed_by_lang.values() for msg_id in rows})
                csv_rows = []
                for msg_id in all_ids:
                    row = [f"0x{msg_id:04X}"]
                    for lang in languages:
                        entry = parsed_by_lang.get(lang, {}).get(msg_id)
                        row.append(entry.text if entry else "")
                    csv_rows.append(row)

                gmsg_csv = out / f"{filename}.csv"
                write_csv(gmsg_csv, ["ID", *languages], csv_rows, delimiter)
                summary["gmsg_files"].append(str(gmsg_csv))

                # Structural QA for Turkish patch vs original English.
                if "English" in parsed_by_lang and "Turkish" in parsed_by_lang:
                    en = parsed_by_lang["English"]
                    tr = parsed_by_lang["Turkish"]
                    qa_rows = []
                    for msg_id in sorted(set(en) | set(tr)):
                        ee, tt = en.get(msg_id), tr.get(msg_id)
                        if ee and tt:
                            crit_match = critical_controls(ee.controls) == critical_controls(tt.controls)
                            exact_same = ee.text == tt.text
                            tr_chars = "".join(sorted({c for c in tt.text if c in TURKISH_GLYPHS}))
                            qa_rows.append([
                                f"0x{msg_id:04X}",
                                "YES" if crit_match else "NO",
                                "YES" if exact_same else "NO",
                                tr_chars,
                                ee.text,
                                tt.text,
                                repr(critical_controls(ee.controls)),
                                repr(critical_controls(tt.controls)),
                            ])
                        else:
                            qa_rows.append([
                                f"0x{msg_id:04X}", "MISSING", "NO", "",
                                ee.text if ee else "", tt.text if tt else "", "", ""
                            ])
                    qa_csv = out / f"{filename}.qa.csv"
                    write_csv(
                        qa_csv,
                        ["ID", "CriticalControlsMatch", "ExactSameAsEnglish", "TurkishSpecialChars",
                         "English", "Turkish", "EnglishCriticalControls", "TurkishCriticalControls"],
                        qa_rows,
                        delimiter,
                    )
                    summary["gmsg_files"].append(str(qa_csv))

            # Font glyph tables.
            font_summary_rows = []
            for filename, relpath in sorted(gzfs.items()):
                header, glyphs = parse_gzf(original.read(relpath))
                by_char = {g.char: g for g in glyphs}
                font_rows = []
                for g in glyphs:
                    try:
                        uname = unicodedata.name(g.char) if g.char else ""
                    except ValueError:
                        uname = ""
                    turkish_required = g.char in TURKISH_GLYPHS
                    if not turkish_required:
                        tr_status = ""
                    else:
                        tr_status = "OK" if g.usable else "BLANK_METRICS"
                    display_char = g.char
                    if g.codepoint < 0x20 or g.codepoint == 0x7F:
                        display_char = f"<U+{g.codepoint:04X}>"
                    font_rows.append([
                        f"U+{g.codepoint:04X}", display_char, uname,
                        g.height, g.advance, g.left, g.top, g.image_id,
                        "YES" if g.usable else "NO",
                        "YES" if turkish_required else "NO", tr_status,
                    ])

                font_csv = out / f"{filename}.csv"
                write_csv(
                    font_csv,
                    ["Codepoint", "Character", "UnicodeName", "Height", "Advance", "Left", "Top", "ImageID",
                     "UsableGlyph", "TurkishRequired", "TurkishStatus"],
                    font_rows,
                    delimiter,
                )
                summary["font_files"].append(str(font_csv))

                for c in TURKISH_GLYPHS:
                    g = by_char.get(c)
                    status = "MISSING" if g is None else ("OK" if g.usable else "BLANK_METRICS")
                    font_summary_rows.append([
                        filename, header["font_size"], header["entry_count"], header["image_format"],
                        f"U+{ord(c):04X}", c, status,
                        "" if g is None else g.height,
                        "" if g is None else g.advance,
                    ])

            font_summary_csv = out / "font_summary.csv"
            write_csv(
                font_summary_csv,
                ["FontFile", "FontSize", "EntryCount", "ImageFormat", "Codepoint", "Character", "Status", "Height", "Advance"],
                font_summary_rows,
                delimiter,
            )
            summary["font_files"].append(str(font_summary_csv))

            # Human-readable summary.
            lines = [
                "Luigi's Mansion 3DS EUR export summary",
                f"Original: {original_path}",
                f"Patch: {patch_path or '(none)'}",
                f"Region root: {orig_region}",
                f"Languages: {', '.join(languages)}",
                "",
                "GMSG outputs:",
                *[f"  - {Path(x).name}" for x in summary["gmsg_files"]],
                "",
                "Font outputs:",
                *[f"  - {Path(x).name}" for x in summary["font_files"]],
            ]
            if "Dutch" in languages and "Dutch" not in orig_gmsgs:
                lines += ["", "Note: the EUR dump has no Dutch/main.gmsg; Dutch cells are therefore blank."]
            if summary["warnings"]:
                lines += ["", "Warnings:", *[f"  - {w}" for w in summary["warnings"]]]
            (out / "export_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

        finally:
            if patch:
                patch.close()

    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Export Luigi's Mansion 3DS EUR translations/fonts to CSV")
    ap.add_argument("--original", required=True, help="Original EUR game ZIP or extracted directory")
    ap.add_argument("--patch", help="Turkish patch ZIP or extracted directory (its English folder is treated as Turkish)")
    ap.add_argument("--out", default="lm3ds_csv", help="Output directory (default: lm3ds_csv)")
    ap.add_argument("--delimiter", default=",", choices=[",", ";", "\t"], help="CSV delimiter")
    args = ap.parse_args()

    try:
        summary = export_all(args.original, args.patch, args.out, args.delimiter)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Done. GMSG CSVs: {len(summary['gmsg_files'])}, font CSVs: {len(summary['font_files'])}")
    print(f"Output: {Path(args.out).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
