#!/usr/bin/env python3
"""
Monster Hunter 4 / 4U (3DS) MT Framework ARC + LMD text translation helper.

No third-party dependencies.

Commands:
  export INPUT PROJECT [--lang eng]
  inject INPUT PROJECT OUTPUT_DIR
  inject-xlsx INPUT WORKBOOK.xlsx OUTPUT_DIR
  inject-csv INPUT TRANSLATIONS.csv OUTPUT_DIR
  verify INPUT [--lang eng]
  stats INPUT [--lang eng]

INPUT may be a RomFS directory or a .zip containing the RomFS/language folders.
The export format uses JSON with {original, translation}; leave translation null
for untranslated strings. Injection writes only changed .arc files to OUTPUT_DIR,
keeping the same relative paths as INPUT.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import struct
import sys
import zipfile
import zlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

ARC_MAGIC = b"ARC\x00"
LMD_MAGIC = b"lmd\x00"
ARC_HEADER_SIZE = 12
ARC_ENTRY_SIZE = 80
ARC_DATA_ALIGNMENT = 32
LMD_HEADER_MIN = 0x24


class ToolError(Exception):
    pass


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def norm_rel(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


def utf16_units(text: str) -> int:
    return len(text.encode("utf-16le")) // 2


@dataclass
class ArcEntry:
    name_raw: bytes
    type_hash: int
    compressed_size: int
    size_flags: int
    offset: int
    compressed_data: bytes

    @property
    def name(self) -> str:
        return self.name_raw.split(b"\x00", 1)[0].decode("ascii", "replace")

    @property
    def uncompressed_size(self) -> int:
        # The upper 3 bits are flags in this ARC variant. Preserve them.
        return self.size_flags & 0x1FFFFFFF

    @property
    def high_flags(self) -> int:
        return self.size_flags & 0xE0000000

    def decompress(self) -> bytes:
        try:
            data = zlib.decompress(self.compressed_data)
        except zlib.error as e:
            raise ToolError(f"ARC entry is not valid zlib data: {self.name}: {e}") from e
        expected = self.uncompressed_size
        if expected and len(data) != expected:
            raise ToolError(
                f"Uncompressed size mismatch for {self.name}: header={expected}, actual={len(data)}"
            )
        return data


@dataclass
class ArcFile:
    version: int
    unknown: int
    entries: List[ArcEntry]

    @classmethod
    def parse(cls, data: bytes) -> "ArcFile":
        if len(data) < ARC_HEADER_SIZE or data[:4] != ARC_MAGIC:
            raise ToolError("Not an ARC file (missing ARC\\0 magic)")
        magic, version, count, unknown = struct.unpack_from("<4sHHI", data, 0)
        table_end = ARC_HEADER_SIZE + count * ARC_ENTRY_SIZE
        if table_end > len(data):
            raise ToolError("ARC entry table runs past end of file")
        entries: List[ArcEntry] = []
        for i in range(count):
            base = ARC_HEADER_SIZE + i * ARC_ENTRY_SIZE
            name_raw = data[base : base + 64]
            type_hash, csize, size_flags, offset = struct.unpack_from("<IIII", data, base + 64)
            if offset + csize > len(data):
                raise ToolError(f"ARC entry {i} points outside file")
            entries.append(
                ArcEntry(
                    name_raw=name_raw,
                    type_hash=type_hash,
                    compressed_size=csize,
                    size_flags=size_flags,
                    offset=offset,
                    compressed_data=data[offset : offset + csize],
                )
            )
        return cls(version=version, unknown=unknown, entries=entries)

    def build(self, replacements: Optional[Dict[int, bytes]] = None) -> bytes:
        """Rebuild ARC. replacements maps entry index -> uncompressed bytes.

        Unchanged entries keep their original compressed stream byte-for-byte.
        Changed entries are zlib-compressed with the normal level-6 stream used by
        the supplied files (78 9C header).
        """
        replacements = replacements or {}
        count = len(self.entries)
        data_start = align_up(ARC_HEADER_SIZE + count * ARC_ENTRY_SIZE, ARC_DATA_ALIGNMENT)
        out = bytearray(data_start)
        struct.pack_into("<4sHHI", out, 0, ARC_MAGIC, self.version, count, self.unknown)

        cursor = data_start
        payloads: List[Tuple[bytes, int, int]] = []  # compressed, usize, size_flags
        for i, entry in enumerate(self.entries):
            if i in replacements:
                raw = replacements[i]
                comp = zlib.compress(raw, level=6)
                usize = len(raw)
                if usize > 0x1FFFFFFF:
                    raise ToolError(f"Entry too large after patching: {entry.name}")
                size_flags = entry.high_flags | usize
            else:
                comp = entry.compressed_data
                usize = entry.uncompressed_size
                size_flags = entry.size_flags
            payloads.append((comp, usize, size_flags))

        for i, (entry, payload) in enumerate(zip(self.entries, payloads)):
            comp, usize, size_flags = payload
            base = ARC_HEADER_SIZE + i * ARC_ENTRY_SIZE
            out[base : base + 64] = entry.name_raw
            struct.pack_into(
                "<IIII",
                out,
                base + 64,
                entry.type_hash,
                len(comp),
                size_flags,
                cursor,
            )
            out.extend(comp)
            cursor += len(comp)

        return bytes(out)


@dataclass
class LmdString:
    index: int
    offset: int
    units: int
    text: str


@dataclass
class LmdFile:
    raw: bytes
    string_count: int
    table_offset: int
    name_offset: int
    pool_offset: int
    strings: List[LmdString]
    name: str

    @classmethod
    def parse(cls, raw: bytes) -> "LmdFile":
        if len(raw) < LMD_HEADER_MIN or raw[:4] != LMD_MAGIC:
            raise ToolError("Not an LMD file")
        string_count = struct.unpack_from("<I", raw, 0x10)[0]
        table_offset = struct.unpack_from("<I", raw, 0x1C)[0]
        name_offset = struct.unpack_from("<I", raw, 0x20)[0]
        pool_offset = table_offset + string_count * 12
        if table_offset < LMD_HEADER_MIN or pool_offset > len(raw):
            raise ToolError("Invalid LMD string table bounds")
        if name_offset < pool_offset or name_offset > len(raw):
            raise ToolError("Invalid LMD name/tail offset")

        strings: List[LmdString] = []
        for i in range(string_count):
            pos = table_offset + i * 12
            offset, n1, n2 = struct.unpack_from("<III", raw, pos)
            if n1 != n2:
                raise ToolError(f"LMD string {i} has inconsistent lengths {n1}/{n2}")
            end = offset + n1 * 2
            if offset < pool_offset or end > name_offset:
                raise ToolError(f"LMD string {i} points outside string pool")
            try:
                text = raw[offset:end].decode("utf-16le")
            except UnicodeDecodeError as e:
                raise ToolError(f"Invalid UTF-16LE in LMD string {i}: {e}") from e
            strings.append(LmdString(i, offset, n1, text))

        if string_count:
            first = strings[0].offset
            if first != pool_offset:
                raise ToolError(
                    f"Unexpected LMD pool start: table implies 0x{pool_offset:X}, first string is 0x{first:X}"
                )

        tail = raw[name_offset:]
        name_bytes = tail.split(b"\x00", 1)[0]
        name = name_bytes.decode("ascii", "replace")
        return cls(raw, string_count, table_offset, name_offset, pool_offset, strings, name)

    def rebuild(self, translations: Dict[int, str]) -> bytes:
        # Metadata through the string record table is preserved. We rewrite the
        # record offsets/lengths and the UTF-16LE pool. Each string record is
        # 4-byte aligned in the supplied MH4 files.
        out = bytearray(self.raw[: self.pool_offset])
        cursor = self.pool_offset

        for item in self.strings:
            text = translations.get(item.index, item.text)
            if not isinstance(text, str):
                raise ToolError(f"Translation for string {item.index} is not text")
            encoded = text.encode("utf-16le")
            units = len(encoded) // 2
            record = self.table_offset + item.index * 12
            struct.pack_into("<III", out, record, cursor, units, units)
            out.extend(encoded)
            out.extend(b"\x00\x00")
            cursor += len(encoded) + 2
            pad = (-cursor) % 4
            if pad:
                out.extend(b"\x00" * pad)
                cursor += pad

        new_name_offset = len(out)
        struct.pack_into("<I", out, 0x20, new_name_offset)
        out.extend(self.raw[self.name_offset :])
        return bytes(out)


class InputSource:
    def __init__(self, path: Path):
        self.path = path
        self.is_zip = path.is_file() and path.suffix.lower() == ".zip"
        if not self.is_zip and not path.is_dir():
            raise ToolError("INPUT must be a directory or .zip file")

    def iter_arc_names(self, lang: Optional[str] = None) -> Iterator[str]:
        lang = lang.lower() if lang else None
        if self.is_zip:
            with zipfile.ZipFile(self.path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".arc"):
                        continue
                    name = norm_rel(info.filename)
                    if lang and not _path_matches_lang(name, lang):
                        continue
                    yield name
        else:
            for p in sorted(self.path.rglob("*.arc")):
                rel = norm_rel(str(p.relative_to(self.path)))
                if lang and not _path_matches_lang(rel, lang):
                    continue
                yield rel

    def read(self, rel_name: str) -> bytes:
        rel_name = norm_rel(rel_name)
        if self.is_zip:
            with zipfile.ZipFile(self.path, "r") as zf:
                try:
                    return zf.read(rel_name)
                except KeyError:
                    # ZIP may use a leading ./ or different slash normalization.
                    lookup = {norm_rel(n): n for n in zf.namelist()}
                    real = lookup.get(rel_name)
                    if real is None:
                        raise ToolError(f"File not found in ZIP: {rel_name}")
                    return zf.read(real)
        p = self.path.joinpath(*PurePosixPath(rel_name).parts)
        return p.read_bytes()


def _path_matches_lang(rel: str, lang: str) -> bool:
    parts = [p.lower() for p in PurePosixPath(rel).parts]
    return lang in parts


def make_json_path(project: Path, arc_rel: str) -> Path:
    p = PurePosixPath(arc_rel)
    return project / "texts" / Path(*p.parts[:-1]) / (p.name + ".json")


def export_project(input_path: Path, project: Path, lang: Optional[str]) -> None:
    source = InputSource(input_path)
    project.mkdir(parents=True, exist_ok=True)
    (project / "texts").mkdir(parents=True, exist_ok=True)

    manifest = {
        "format": "mh4-lmd-translation-project-v1",
        "input": input_path.name,
        "language_filter": lang,
        "arcs": [],
    }
    arc_count = lmd_count = string_count = 0

    for rel in source.iter_arc_names(lang):
        data = source.read(rel)
        arc = ArcFile.parse(data)
        lmd_entries = []
        for idx, entry in enumerate(arc.entries):
            raw = entry.decompress()
            if raw[:4] != LMD_MAGIC:
                continue
            lmd = LmdFile.parse(raw)
            lmd_entries.append(
                {
                    "entry_index": idx,
                    "entry_name": entry.name,
                    "lmd_name": lmd.name,
                    "strings": [
                        {
                            "id": s.index,
                            "original": s.text,
                            "translation": None,
                        }
                        for s in lmd.strings
                    ],
                }
            )
            lmd_count += 1
            string_count += lmd.string_count

        if lmd_entries:
            arc_doc = {
                "format": "mh4-lmd-arc-v1",
                "arc": rel,
                "lmd_entries": lmd_entries,
            }
            jp = make_json_path(project, rel)
            jp.parent.mkdir(parents=True, exist_ok=True)
            jp.write_text(json.dumps(arc_doc, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest["arcs"].append(rel)
            arc_count += 1

    (project / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Export complete: {arc_count} ARC, {lmd_count} LMD, {string_count} strings")
    print(f"Project: {project}")


def load_project(project: Path) -> dict:
    mp = project / "manifest.json"
    if not mp.exists():
        raise ToolError(f"manifest.json not found in project: {project}")
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    if manifest.get("format") != "mh4-lmd-translation-project-v1":
        raise ToolError("Unsupported or invalid project manifest")
    return manifest


def inject_project(input_path: Path, project: Path, output_dir: Path) -> None:
    source = InputSource(input_path)
    manifest = load_project(project)
    output_dir.mkdir(parents=True, exist_ok=True)
    patched_arc_count = patched_lmd_count = patched_string_count = 0

    for rel in manifest.get("arcs", []):
        rel = norm_rel(rel)
        jp = make_json_path(project, rel)
        if not jp.exists():
            raise ToolError(f"Missing project JSON: {jp}")
        doc = json.loads(jp.read_text(encoding="utf-8"))
        if norm_rel(doc.get("arc", "")) != rel:
            raise ToolError(f"ARC path mismatch in {jp}")

        arc_data = source.read(rel)
        arc = ArcFile.parse(arc_data)
        replacements: Dict[int, bytes] = {}
        arc_changes = 0

        for ldoc in doc.get("lmd_entries", []):
            idx = int(ldoc["entry_index"])
            if idx < 0 or idx >= len(arc.entries):
                raise ToolError(f"Entry index out of range in {jp}: {idx}")
            entry = arc.entries[idx]
            if entry.name != ldoc.get("entry_name"):
                raise ToolError(
                    f"Entry name mismatch for {rel} index {idx}: source={entry.name!r}, project={ldoc.get('entry_name')!r}"
                )
            lmd = LmdFile.parse(entry.decompress())
            rows = ldoc.get("strings", [])
            if len(rows) != lmd.string_count:
                raise ToolError(
                    f"String count mismatch in {rel}/{entry.name}: source={lmd.string_count}, project={len(rows)}"
                )

            translations: Dict[int, str] = {}
            for row in rows:
                sid = int(row["id"])
                if sid < 0 or sid >= lmd.string_count:
                    raise ToolError(f"Invalid string id {sid} in {jp}")
                # Protect against accidentally applying a project to a different base file.
                if row.get("original") != lmd.strings[sid].text:
                    raise ToolError(
                        f"Original text mismatch in {rel}/{entry.name} string {sid}; use the same base RomFS that was exported."
                    )
                tr = row.get("translation", None)
                if tr is not None:
                    if not isinstance(tr, str):
                        raise ToolError(f"translation must be string or null: {rel}/{entry.name} #{sid}")
                    if tr != lmd.strings[sid].text:
                        translations[sid] = tr

            if translations:
                replacements[idx] = lmd.rebuild(translations)
                arc_changes += len(translations)
                patched_lmd_count += 1
                patched_string_count += len(translations)

        if replacements:
            patched = arc.build(replacements)
            # Parse/decompress every entry as a structural sanity check before writing.
            checked = ArcFile.parse(patched)
            for e in checked.entries:
                _ = e.decompress()
            out_path = output_dir.joinpath(*PurePosixPath(rel).parts)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(patched)
            patched_arc_count += 1
            print(f"patched {rel}: {arc_changes} strings")

    print(
        f"Injection complete: {patched_arc_count} ARC, {patched_lmd_count} LMD, {patched_string_count} translated strings"
    )
    print(f"Changed ARC files written under: {output_dir}")


XLSX_PART_DELIM = "⟪parça⟫"


def _xlsx_col_index(cell_ref: str) -> int:
    letters = []
    for ch in cell_ref:
        if ch.isalpha():
            letters.append(ch.upper())
        else:
            break
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return max(0, n - 1)


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> List[str]:
    name = "xl/sharedStrings.xml"
    if name not in zf.namelist():
        return []
    root = ET.fromstring(zf.read(name))
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    return ["".join(t.text or "" for t in si.iter(ns + "t")) for si in root.findall(ns + "si")]


def _xlsx_workbook_sheets(zf: zipfile.ZipFile) -> List[Tuple[str, str]]:
    main_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    pkg_ns = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall(pkg_ns + "Relationship")}
    out: List[Tuple[str, str]] = []
    sheets = wb.find(main_ns + "sheets")
    if sheets is None:
        return out
    for sh in sheets:
        name = sh.attrib.get("name", "")
        rid = sh.attrib.get(rel_ns + "id", "")
        target = relmap.get(rid, "").replace("\\", "/")
        if not target:
            continue
        if target.startswith("/"):
            path = target.lstrip("/")
        elif target.startswith("xl/"):
            path = target
        else:
            path = "xl/" + target.lstrip("/")
        out.append((name, path))
    return out


def xlsx_translation_sheet_names(path: Path) -> List[str]:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [name for name, _ in _xlsx_workbook_sheets(zf)]
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as e:
        raise ToolError(f"Cannot read XLSX workbook: {path}: {e}") from e
    out = [n for n in names if n == "Çeviri" or n.startswith("Çeviri ")]
    if not out:
        raise ToolError("No translation worksheet found (expected Çeviri / Çeviri 2 / ...)")
    return out


def iter_xlsx_rows(path: Path, sheet_name: str) -> Iterator[Dict[str, str]]:
    try:
        zf = zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile) as e:
        raise ToolError(f"Cannot open XLSX: {path}: {e}") from e
    with zf:
        shared = _xlsx_shared_strings(zf)
        sheet_map = dict(_xlsx_workbook_sheets(zf))
        sheet_path = sheet_map.get(sheet_name)
        if not sheet_path:
            raise ToolError(f"Worksheet not found in XLSX: {sheet_name!r}")
        main_ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        headers: Optional[List[str]] = None
        with zf.open(sheet_path, "r") as fp:
            for _, elem in ET.iterparse(fp, events=("end",)):
                if elem.tag != main_ns + "row":
                    continue
                vals: Dict[int, str] = {}
                for c in elem.findall(main_ns + "c"):
                    idx = _xlsx_col_index(c.attrib.get("r", "A1"))
                    ctype = c.attrib.get("t")
                    value = ""
                    if ctype == "inlineStr":
                        is_el = c.find(main_ns + "is")
                        if is_el is not None:
                            value = "".join(t.text or "" for t in is_el.iter(main_ns + "t"))
                    else:
                        v = c.find(main_ns + "v")
                        raw = "" if v is None or v.text is None else v.text
                        if ctype == "s" and raw:
                            try:
                                value = shared[int(raw)]
                            except (ValueError, IndexError) as e:
                                raise ToolError(f"Invalid shared string index in XLSX: {raw}") from e
                        else:
                            value = raw
                    vals[idx] = value
                if headers is None:
                    if vals:
                        max_col = max(vals)
                        headers = [vals.get(i, "") for i in range(max_col + 1)]
                elif vals:
                    yield {headers[i]: vals.get(i, "") for i in range(len(headers)) if headers[i]}
                elem.clear()


def inject_csv(input_path: Path, csv_path: Path, output_dir: Path) -> None:
    required = {"ARC", "LMD", "Mesaj ID", "English", "Türkçe", "Parça sayısı", "English IDler", "EntryIndex", "EntryName"}
    by_arc: Dict[str, Dict[Tuple[int, str], List[dict]]] = {}
    translated_messages = 0

    try:
        fp = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as e:
        raise ToolError(f"Cannot open CSV: {csv_path}: {e}") from e
    with fp:
        sample = fp.read(65536)
        fp.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fp, dialect=dialect)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ToolError("CSV is missing columns: " + ", ".join(sorted(missing)))
        for row_num, row in enumerate(reader, start=2):
            tr = row.get("Türkçe", "") or ""
            if tr == "":
                continue
            where = f"CSV row {row_num}"
            rel = norm_rel(row.get("ARC", "") or "")
            try:
                entry_index = int(row.get("EntryIndex", "") or "")
                part_count = int(row.get("Parça sayısı", "") or "")
                ids = [int(x) for x in (row.get("English IDler", "") or "").split(",") if x != ""]
            except ValueError as e:
                raise ToolError(f"Invalid numeric metadata at {where}") from e
            if not rel or len(ids) != part_count or part_count < 1:
                raise ToolError(f"Invalid metadata at {where}")
            parts = tr.split(XLSX_PART_DELIM)
            if len(parts) != part_count:
                raise ToolError(
                    f"Türkçe parça sayısı yanlış at {where}: expected {part_count}, got {len(parts)}. "
                    f"Use {XLSX_PART_DELIM} exactly between parts."
                )
            rec = {
                "where": where,
                "lmd_name": row.get("LMD", "") or "",
                "english": row.get("English", "") or "",
                "ids": ids,
                "parts": parts,
            }
            key = (entry_index, row.get("EntryName", "") or "")
            by_arc.setdefault(rel, {}).setdefault(key, []).append(rec)
            translated_messages += 1

    if translated_messages == 0:
        print("No non-empty Turkish translations found in the Türkçe column.")
        return

    source = InputSource(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    patched_arc_count = patched_lmd_count = patched_string_count = 0

    for rel, entries in by_arc.items():
        arc = ArcFile.parse(source.read(rel))
        replacements: Dict[int, bytes] = {}
        arc_changes = 0
        for (entry_index, entry_name), records in entries.items():
            if entry_index < 0 or entry_index >= len(arc.entries):
                raise ToolError(f"Entry index out of range: {rel} #{entry_index}")
            entry = arc.entries[entry_index]
            if entry.name != entry_name:
                raise ToolError(f"Entry name mismatch for {rel} index {entry_index}: source={entry.name!r}, CSV={entry_name!r}")
            lmd = LmdFile.parse(entry.decompress())
            translations: Dict[int, str] = {}
            for rec in records:
                if rec["lmd_name"] and rec["lmd_name"] != lmd.name:
                    raise ToolError(f"LMD name mismatch at {rec['where']}: source={lmd.name!r}, CSV={rec['lmd_name']!r}")
                try:
                    original = XLSX_PART_DELIM.join(lmd.strings[sid].text for sid in rec["ids"])
                except IndexError as e:
                    raise ToolError(f"String ID out of range at {rec['where']}") from e
                if original != rec["english"]:
                    raise ToolError(f"English/base text mismatch at {rec['where']}; use the same original RomFS and unmodified metadata columns.")
                for sid, part in zip(rec["ids"], rec["parts"]):
                    old = translations.get(sid)
                    if old is not None and old != part:
                        raise ToolError(f"Conflicting translations for string {sid} in {rel}/{entry.name}")
                    if part != lmd.strings[sid].text:
                        translations[sid] = part
            if translations:
                replacements[entry_index] = lmd.rebuild(translations)
                arc_changes += len(translations)
                patched_lmd_count += 1
                patched_string_count += len(translations)

        if replacements:
            patched = arc.build(replacements)
            checked = ArcFile.parse(patched)
            for e in checked.entries:
                _ = e.decompress()
            out_path = output_dir.joinpath(*PurePosixPath(rel).parts)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(patched)
            patched_arc_count += 1
            print(f"patched {rel}: {arc_changes} strings")

    print(f"CSV injection complete: {patched_arc_count} ARC, {patched_lmd_count} LMD, {patched_string_count} translated strings from {translated_messages} messages")
    print(f"Changed ARC files written under: {output_dir}")


def inject_xlsx(input_path: Path, workbook: Path, output_dir: Path) -> None:
    required = {"ARC", "LMD", "Mesaj ID", "English", "Türkçe", "Parça sayısı", "English IDler", "EntryIndex", "EntryName"}
    by_arc: Dict[str, Dict[Tuple[int, str], List[dict]]] = {}
    translated_messages = 0

    for sheet_name in xlsx_translation_sheet_names(workbook):
        first = True
        for row_num, row in enumerate(iter_xlsx_rows(workbook, sheet_name), start=2):
            if first:
                missing = required.difference(row.keys())
                if missing:
                    raise ToolError(f"XLSX sheet {sheet_name!r} is missing columns: " + ", ".join(sorted(missing)))
                first = False
            tr = row.get("Türkçe", "")
            if tr == "":
                continue
            where = f"{sheet_name}!{row_num}"
            rel = norm_rel(row.get("ARC", ""))
            try:
                entry_index = int(row.get("EntryIndex", ""))
                part_count = int(row.get("Parça sayısı", ""))
                ids = [int(x) for x in row.get("English IDler", "").split(",") if x != ""]
            except ValueError as e:
                raise ToolError(f"Invalid numeric metadata at XLSX {where}") from e
            if not rel or len(ids) != part_count or part_count < 1:
                raise ToolError(f"Invalid metadata at XLSX {where}")
            parts = tr.split(XLSX_PART_DELIM)
            if len(parts) != part_count:
                raise ToolError(
                    f"Türkçe parça sayısı yanlış, XLSX {where}: expected {part_count}, got {len(parts)}. "
                    f"Use {XLSX_PART_DELIM} exactly between parts."
                )
            rec = {
                "where": where,
                "lmd_name": row.get("LMD", ""),
                "english": row.get("English", ""),
                "ids": ids,
                "parts": parts,
            }
            key = (entry_index, row.get("EntryName", ""))
            by_arc.setdefault(rel, {}).setdefault(key, []).append(rec)
            translated_messages += 1

    if translated_messages == 0:
        print("No non-empty Turkish translations found in the Türkçe column.")
        return

    source = InputSource(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    patched_arc_count = patched_lmd_count = patched_string_count = 0

    for rel, entries in by_arc.items():
        arc = ArcFile.parse(source.read(rel))
        replacements: Dict[int, bytes] = {}
        arc_changes = 0
        for (entry_index, entry_name), records in entries.items():
            if entry_index < 0 or entry_index >= len(arc.entries):
                raise ToolError(f"Entry index out of range: {rel} #{entry_index}")
            entry = arc.entries[entry_index]
            if entry.name != entry_name:
                raise ToolError(f"Entry name mismatch for {rel} index {entry_index}: source={entry.name!r}, XLSX={entry_name!r}")
            lmd = LmdFile.parse(entry.decompress())
            translations: Dict[int, str] = {}
            for rec in records:
                if rec["lmd_name"] and rec["lmd_name"] != lmd.name:
                    raise ToolError(f"LMD name mismatch at XLSX {rec['where']}: source={lmd.name!r}, XLSX={rec['lmd_name']!r}")
                try:
                    original = XLSX_PART_DELIM.join(lmd.strings[sid].text for sid in rec["ids"])
                except IndexError as e:
                    raise ToolError(f"String ID out of range at XLSX {rec['where']}") from e
                if original != rec["english"]:
                    raise ToolError(f"English/base text mismatch at XLSX {rec['where']}; use the same original RomFS and unmodified metadata columns.")
                for sid, part in zip(rec["ids"], rec["parts"]):
                    old = translations.get(sid)
                    if old is not None and old != part:
                        raise ToolError(f"Conflicting translations for string {sid} in {rel}/{entry.name}")
                    if part != lmd.strings[sid].text:
                        translations[sid] = part
            if translations:
                replacements[entry_index] = lmd.rebuild(translations)
                arc_changes += len(translations)
                patched_lmd_count += 1
                patched_string_count += len(translations)

        if replacements:
            patched = arc.build(replacements)
            checked = ArcFile.parse(patched)
            for e in checked.entries:
                _ = e.decompress()
            out_path = output_dir.joinpath(*PurePosixPath(rel).parts)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(patched)
            patched_arc_count += 1
            print(f"patched {rel}: {arc_changes} strings")

    print(f"XLSX injection complete: {patched_arc_count} ARC, {patched_lmd_count} LMD, {patched_string_count} translated strings from {translated_messages} messages")
    print(f"Changed ARC files written under: {output_dir}")


def verify_input(input_path: Path, lang: Optional[str]) -> None:
    source = InputSource(input_path)
    arcs = entries = lmds = strings = 0
    for rel in source.iter_arc_names(lang):
        arc = ArcFile.parse(source.read(rel))
        arcs += 1
        for entry in arc.entries:
            raw = entry.decompress()
            entries += 1
            if raw[:4] == LMD_MAGIC:
                lmd = LmdFile.parse(raw)
                lmds += 1
                strings += lmd.string_count
    print(f"OK: {arcs} ARC, {entries} entries, {lmds} LMD, {strings} strings")


def stats_input(input_path: Path, lang: Optional[str]) -> None:
    source = InputSource(input_path)
    arcs = entries = lmds = strings = 0
    langs = set()
    for rel in source.iter_arc_names(lang):
        parts = PurePosixPath(rel).parts
        if parts:
            langs.add(parts[0])
        arc = ArcFile.parse(source.read(rel))
        arcs += 1
        entries += len(arc.entries)
        for entry in arc.entries:
            try:
                raw = entry.decompress()
            except ToolError:
                continue
            if raw[:4] == LMD_MAGIC:
                lmd = LmdFile.parse(raw)
                lmds += 1
                strings += lmd.string_count
    print(f"ARC files: {arcs}")
    print(f"ARC entries: {entries}")
    print(f"LMD files: {lmds}")
    print(f"Strings: {strings}")
    if langs:
        print("Top-level folders: " + ", ".join(sorted(langs)))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MH4/MH4U 3DS ARC+LMD translation extractor/injector"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ex = sub.add_parser("export", help="extract LMD strings into editable JSON")
    ex.add_argument("input", type=Path, help="RomFS directory or ZIP")
    ex.add_argument("project", type=Path, help="output translation project directory")
    ex.add_argument("--lang", default=None, help="optional language folder filter, e.g. eng")

    inj = sub.add_parser("inject", help="inject translated JSON back into ARC files")
    inj.add_argument("input", type=Path, help="original RomFS directory or ZIP used as base")
    inj.add_argument("project", type=Path, help="translation project directory")
    inj.add_argument("output", type=Path, help="output directory for changed ARC files")

    injx = sub.add_parser("inject-xlsx", help="inject the Türkçe column from the side-by-side XLSX workbook")
    injx.add_argument("input", type=Path, help="original RomFS directory or ZIP used as base")
    injx.add_argument("workbook", type=Path, help="MH4_Ceviri_Yan_Yana.xlsx")
    injx.add_argument("output", type=Path, help="output directory for changed ARC files")

    injc = sub.add_parser("inject-csv", help="inject the Türkçe column from the side-by-side UTF-8 CSV")
    injc.add_argument("input", type=Path, help="original RomFS directory or ZIP used as base")
    injc.add_argument("csv", type=Path, help="MH4_Ceviri_Yan_Yana.csv")
    injc.add_argument("output", type=Path, help="output directory for changed ARC files")

    ver = sub.add_parser("verify", help="verify ARC/LMD structures")
    ver.add_argument("input", type=Path)
    ver.add_argument("--lang", default=None)

    st = sub.add_parser("stats", help="show ARC/LMD/text counts")
    st.add_argument("input", type=Path)
    st.add_argument("--lang", default=None)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "export":
            export_project(args.input, args.project, args.lang)
        elif args.cmd == "inject":
            inject_project(args.input, args.project, args.output)
        elif args.cmd == "inject-xlsx":
            inject_xlsx(args.input, args.workbook, args.output)
        elif args.cmd == "inject-csv":
            inject_csv(args.input, args.csv, args.output)
        elif args.cmd == "verify":
            verify_input(args.input, args.lang)
        elif args.cmd == "stats":
            stats_input(args.input, args.lang)
        else:
            raise ToolError("Unknown command")
        return 0
    except (ToolError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
