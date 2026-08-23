#!/usr/bin/env python3
"""Full Professor Layton 5 PlainFA + XSCR translation toolkit.

This module adds the outer lt5_uk.fa archive layer to layton_xs_tool.py.
It keeps all non-text members opaque and byte-identical while allowing XSCR
projects to be exported from, and injected directly into, the archive.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Mapping, Sequence

import layton_xs_tool as xs


TOOL_VERSION = "2.0.0"
PLAINFA_MANIFEST_FORMAT = "level5-plainfa-manifest"
PLAINFA_MANIFEST_VERSION = 1
PLAINFA_HEADER_SIZE = 0x10
PLAINFA_ENTRY_SIZE = 0x50
PLAINFA_NAME_SIZE = 0x40
LT5_UK_EXPECTED_FILE_COUNT = 0x08F7
COPY_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class PlainFaEntry:
    index: int
    path: str
    filename_raw: bytes
    offset: int
    size: int
    reserved: bytes


def hash_stream(stream: BinaryIO, size: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = size
    while remaining is None or remaining > 0:
        request = COPY_CHUNK_SIZE if remaining is None else min(COPY_CHUNK_SIZE, remaining)
        block = stream.read(request)
        if not block:
            break
        digest.update(block)
        if remaining is not None:
            remaining -= len(block)
    if remaining not in (None, 0):
        raise xs.XsError("Dosya/veri aralığı SHA-256 sırasında erken bitti.")
    return digest.hexdigest()


def hash_path(path: Path) -> str:
    with path.open("rb") as stream:
        return hash_stream(stream)


def copy_exact(source: BinaryIO, destination: BinaryIO, size: int) -> None:
    remaining = size
    while remaining:
        block = source.read(min(COPY_CHUNK_SIZE, remaining))
        if not block:
            raise xs.XsError("Arşiv üyesi kopyalanırken kaynak erken bitti.")
        destination.write(block)
        remaining -= len(block)


def normalize_member_name(name: str) -> str:
    candidate = name.replace("\\", "/")
    if "\0" in candidate or not candidate:
        raise xs.XsError(f"Geçersiz PlainFA üye yolu: {name!r}.")
    if candidate.startswith("/") or (len(candidate) >= 2 and candidate[1] == ":"):
        raise xs.XsError(f"Mutlak PlainFA üye yolu reddedildi: {name!r}.")
    parts = PurePosixPath(candidate).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise xs.XsError(f"Güvensiz PlainFA üye yolu: {name!r}.")
    return PurePosixPath(*parts).as_posix()


def decode_member_name(raw: bytes, entry_index: int) -> str:
    encoded = raw.split(b"\0", 1)[0]
    if not encoded:
        raise xs.XsError(f"PlainFA kayıt {entry_index}: boş dosya adı.")
    try:
        decoded = encoded.decode("cp932")
    except UnicodeDecodeError as exc:
        raise xs.XsError(
            f"PlainFA kayıt {entry_index}: dosya adı CP932 olarak çözülemiyor."
        ) from exc
    return normalize_member_name(decoded)


def safe_output_member(root: Path, member_name: str) -> Path:
    normalized = normalize_member_name(member_name)
    root_resolved = root.resolve()
    destination = root.joinpath(*PurePosixPath(normalized).parts)
    parent_resolved = destination.parent.resolve()
    try:
        parent_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise xs.XsError(f"Arşiv yolu hedef klasörün dışına çıkıyor: {member_name}") from exc
    if destination.is_symlink():
        raise xs.XsError(f"Sembolik bağlantı hedefi reddedildi: {destination}")
    return destination


class PlainFaArchive:
    def __init__(
        self,
        source_path: Path,
        actual_size: int,
        reported_size: int,
        header_reserved: bytes,
        entries: list[PlainFaEntry],
    ) -> None:
        self.source_path = source_path
        self.actual_size = actual_size
        self.reported_size = reported_size
        self.header_reserved = header_reserved
        self.entries = entries
        self.table_end = PLAINFA_HEADER_SIZE + len(entries) * PLAINFA_ENTRY_SIZE

    @classmethod
    def open(cls, source_path: Path) -> "PlainFaArchive":
        if not source_path.is_file():
            raise xs.XsError(f"PlainFA arşivi bulunamadı: {source_path}")
        actual_size = source_path.stat().st_size
        if actual_size < PLAINFA_HEADER_SIZE:
            raise xs.XsError("Dosya PlainFA başlığı için fazla kısa.")
        with source_path.open("rb") as stream:
            header = stream.read(PLAINFA_HEADER_SIZE)
            file_count, reported_size, header_reserved = struct.unpack("<II8s", header)
            if file_count > 1_000_000:
                raise xs.XsError(f"Makul olmayan PlainFA dosya sayısı: {file_count}.")
            table_end = PLAINFA_HEADER_SIZE + file_count * PLAINFA_ENTRY_SIZE
            if table_end > actual_size:
                raise xs.XsError(
                    f"PlainFA kayıt tablosu dosyanın dışında: 0x{table_end:X}/0x{actual_size:X}."
                )
            entries: list[PlainFaEntry] = []
            for index in range(file_count):
                raw_entry = stream.read(PLAINFA_ENTRY_SIZE)
                if len(raw_entry) != PLAINFA_ENTRY_SIZE:
                    raise xs.XsError(f"PlainFA kayıt {index} eksik.")
                offset, size, reserved, filename_raw = struct.unpack("<II8s64s", raw_entry)
                path = decode_member_name(filename_raw, index)
                if offset < table_end:
                    raise xs.XsError(
                        f"PlainFA kayıt {index} ({path}) veri tablosuyla çakışıyor: 0x{offset:X}."
                    )
                if offset + size > actual_size:
                    raise xs.XsError(
                        f"PlainFA kayıt {index} ({path}) arşiv sınırını aşıyor: "
                        f"0x{offset:X}+0x{size:X}>0x{actual_size:X}."
                    )
                entries.append(
                    PlainFaEntry(index, path, filename_raw, offset, size, reserved)
                )
        archive = cls(source_path, actual_size, reported_size, header_reserved, entries)
        archive.assert_rewritable()
        return archive

    def assert_rewritable(self) -> None:
        duplicates = [path for path, count in Counter(e.path for e in self.entries).items() if count > 1]
        if duplicates:
            raise xs.XsError(
                "PlainFA içinde yinelenen yollar güvenli yeniden paketlemeyi engelliyor: "
                + ", ".join(duplicates[:8])
            )
        physical = sorted(
            (entry for entry in self.entries if entry.size > 0),
            key=lambda entry: (entry.offset, entry.index),
        )
        previous: PlainFaEntry | None = None
        previous_end = self.table_end
        for entry in physical:
            if entry.offset < previous_end:
                assert previous is not None
                raise xs.XsError(
                    f"PlainFA veri üyeleri çakışıyor: {previous.path} ve {entry.path}."
                )
            previous = entry
            previous_end = entry.offset + entry.size

    def by_path(self) -> dict[str, PlainFaEntry]:
        return {entry.path: entry for entry in self.entries}

    def open_entry(self, entry: PlainFaEntry) -> BinaryIO:
        stream = self.source_path.open("rb")
        stream.seek(entry.offset)
        return stream

    def read_entry(self, entry: PlainFaEntry) -> bytes:
        with self.open_entry(entry) as stream:
            data = stream.read(entry.size)
        if len(data) != entry.size:
            raise xs.XsError(f"PlainFA üyesi erken bitti: {entry.path}")
        return data

    def hash_entry(self, entry: PlainFaEntry) -> str:
        with self.open_entry(entry) as stream:
            return hash_stream(stream, entry.size)

    def read_range(self, offset: int, size: int) -> bytes:
        if offset < 0 or size < 0 or offset + size > self.actual_size:
            raise xs.XsError("PlainFA aralık okuması dosya sınırının dışında.")
        with self.source_path.open("rb") as stream:
            stream.seek(offset)
            data = stream.read(size)
        if len(data) != size:
            raise xs.XsError("PlainFA aralık okuması erken bitti.")
        return data

    def physical_layout(self) -> tuple[list[tuple[PlainFaEntry, bytes]], bytes]:
        ordered = sorted(self.entries, key=lambda entry: (entry.offset, entry.index))
        cursor = self.table_end
        layout: list[tuple[PlainFaEntry, bytes]] = []
        for entry in ordered:
            if entry.offset < cursor:
                if entry.size == 0 and entry.offset == cursor:
                    gap = b""
                else:
                    raise xs.XsError(f"PlainFA fiziksel yerleşimi çakışıyor: {entry.path}")
            else:
                gap = self.read_range(cursor, entry.offset - cursor)
            layout.append((entry, gap))
            cursor = max(cursor, entry.offset + entry.size)
        trailing = self.read_range(cursor, self.actual_size - cursor)
        return layout, trailing

    def summary(self) -> dict[str, object]:
        extensions = Counter(
            (PurePosixPath(entry.path).suffix.lower() or "[uzantısız]")
            for entry in self.entries
        )
        roots = Counter(PurePosixPath(entry.path).parts[0] for entry in self.entries)
        total_payload = sum(entry.size for entry in self.entries)
        return {
            "tool_version": TOOL_VERSION,
            "format": "Level-5 PlainFA",
            "archive": str(self.source_path),
            "actual_size": self.actual_size,
            "reported_size": self.reported_size,
            "file_count": len(self.entries),
            "lt5_uk_signature": len(self.entries) == LT5_UK_EXPECTED_FILE_COUNT,
            "table_end": self.table_end,
            "payload_bytes": total_payload,
            "non_payload_bytes": self.actual_size - total_payload,
            "extensions": dict(sorted(extensions.items())),
            "top_level_paths": dict(sorted(roots.items())),
            "header_reserved_hex": self.header_reserved.hex(),
        }


Replacement = bytes | Path


def replacement_size(value: Replacement) -> int:
    return len(value) if isinstance(value, bytes) else value.stat().st_size


def write_replacement(value: Replacement, destination: BinaryIO) -> None:
    if isinstance(value, bytes):
        destination.write(value)
        return
    if value.is_symlink() or not value.is_file():
        raise xs.XsError(f"Geçersiz değiştirme dosyası: {value}")
    with value.open("rb") as source:
        shutil.copyfileobj(source, destination, COPY_CHUNK_SIZE)


def prepare_output(output: Path, force: bool) -> tuple[Path, Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not force:
        raise xs.XsError(f"Çıktı zaten var; üzerine yazmak için --force kullanın: {output}")
    handle = tempfile.NamedTemporaryFile(
        prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    return output, temporary


def finalize_output(temporary: Path, output: Path) -> None:
    os.replace(temporary, output)


def rebuild_archive(
    archive: PlainFaArchive,
    output: Path,
    replacements: Mapping[str, Replacement],
    *,
    preserve_layout: bool = True,
    force: bool = False,
) -> None:
    unknown = sorted(set(replacements) - set(archive.by_path()))
    if unknown:
        raise xs.XsError("Arşivde olmayan değiştirme yolları: " + ", ".join(unknown[:8]))
    if output.resolve() == archive.source_path.resolve():
        raise xs.XsError("Kaynak arşivin üzerine doğrudan yazılmaz; ayrı bir çıktı yolu seçin.")
    final_path, temporary = prepare_output(output, force)
    try:
        offsets: dict[int, int] = {}
        sizes: dict[int, int] = {}
        layout, trailing = archive.physical_layout()
        if not preserve_layout:
            layout = [(entry, b"") for entry in archive.entries]
            trailing = b""

        with temporary.open("w+b") as destination, archive.source_path.open("rb") as source:
            destination.write(b"\0" * archive.table_end)
            for entry, gap in layout:
                destination.write(gap)
                offsets[entry.index] = destination.tell()
                replacement = replacements.get(entry.path)
                if replacement is None:
                    source.seek(entry.offset)
                    copy_exact(source, destination, entry.size)
                    sizes[entry.index] = entry.size
                else:
                    sizes[entry.index] = replacement_size(replacement)
                    write_replacement(replacement, destination)
            destination.write(trailing)
            final_size = destination.tell()
            if final_size > 0xFFFFFFFF:
                raise xs.XsError("PlainFA çıktısı 32 bit boyut sınırını aştı.")
            destination.seek(0)
            destination.write(
                struct.pack(
                    "<II8s", len(archive.entries), final_size, archive.header_reserved
                )
            )
            for entry in archive.entries:
                destination.write(
                    struct.pack(
                        "<II8s64s",
                        offsets[entry.index],
                        sizes[entry.index],
                        entry.reserved,
                        entry.filename_raw,
                    )
                )
        verified = PlainFaArchive.open(temporary)
        if len(verified.entries) != len(archive.entries):
            raise xs.XsError("Yeniden paketlenen PlainFA kayıt sayısı değişti.")
        finalize_output(temporary, final_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def manifest_for_archive(archive: PlainFaArchive) -> dict[str, object]:
    layout, trailing = archive.physical_layout()
    entries = []
    for entry in archive.entries:
        entries.append(
            {
                "index": entry.index,
                "path": entry.path,
                "filename_raw_b64": base64.b64encode(entry.filename_raw).decode("ascii"),
                "offset": entry.offset,
                "size": entry.size,
                "reserved_b64": base64.b64encode(entry.reserved).decode("ascii"),
                "sha256": archive.hash_entry(entry),
            }
        )
    return {
        "format": PLAINFA_MANIFEST_FORMAT,
        "version": PLAINFA_MANIFEST_VERSION,
        "tool_version": TOOL_VERSION,
        "source_name": archive.source_path.name,
        "source_sha256": hash_path(archive.source_path),
        "actual_size": archive.actual_size,
        "reported_size": archive.reported_size,
        "header_reserved_b64": base64.b64encode(archive.header_reserved).decode("ascii"),
        "entries": entries,
        "physical_layout": [
            {
                "entry_index": entry.index,
                "gap_before_b64": base64.b64encode(gap).decode("ascii"),
            }
            for entry, gap in layout
        ],
        "trailing_b64": base64.b64encode(trailing).decode("ascii"),
    }


def read_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise xs.XsError(f"PlainFA manifesti okunamadı: {path}: {exc}") from exc
    if value.get("format") != PLAINFA_MANIFEST_FORMAT:
        raise xs.XsError("Desteklenmeyen PlainFA manifest biçimi.")
    if value.get("version") != PLAINFA_MANIFEST_VERSION:
        raise xs.XsError("Desteklenmeyen PlainFA manifest sürümü.")
    return value


def decode_manifest_bytes(value: object, field: str, expected: int | None = None) -> bytes:
    if not isinstance(value, str):
        raise xs.XsError(f"Manifest alanı metin değil: {field}")
    try:
        result = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise xs.XsError(f"Manifest base64 alanı bozuk: {field}") from exc
    if expected is not None and len(result) != expected:
        raise xs.XsError(f"Manifest alan boyutu yanlış: {field}")
    return result


def pack_from_manifest(
    input_root: Path,
    manifest_path: Path,
    output: Path,
    *,
    preserve_layout: bool,
    force: bool,
) -> None:
    manifest = read_manifest(manifest_path)
    raw_entries = manifest.get("entries")
    raw_layout = manifest.get("physical_layout")
    if not isinstance(raw_entries, list) or not isinstance(raw_layout, list):
        raise xs.XsError("PlainFA manifest kayıtları eksik.")

    entries: list[PlainFaEntry] = []
    sources: dict[int, Path] = {}
    for expected_index, item in enumerate(raw_entries):
        if not isinstance(item, dict) or item.get("index") != expected_index:
            raise xs.XsError("PlainFA manifest kayıt sırası bozuk.")
        path = normalize_member_name(str(item.get("path", "")))
        filename_raw = decode_manifest_bytes(
            item.get("filename_raw_b64"), f"entries[{expected_index}].filename", PLAINFA_NAME_SIZE
        )
        reserved = decode_manifest_bytes(
            item.get("reserved_b64"), f"entries[{expected_index}].reserved", 8
        )
        source = safe_output_member(input_root, path)
        if source.is_symlink() or not source.is_file():
            raise xs.XsError(f"Çıkarılmış PlainFA üyesi eksik: {source}")
        entries.append(
            PlainFaEntry(
                expected_index,
                path,
                filename_raw,
                int(item.get("offset", 0)),
                int(item.get("size", 0)),
                reserved,
            )
        )
        sources[expected_index] = source

    if output.exists() and not force:
        raise xs.XsError(f"Çıktı zaten var; üzerine yazmak için --force kullanın: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        offsets: dict[int, int] = {}
        sizes: dict[int, int] = {}
        if preserve_layout:
            order: list[tuple[PlainFaEntry, bytes]] = []
            seen: set[int] = set()
            for position, item in enumerate(raw_layout):
                if not isinstance(item, dict):
                    raise xs.XsError("PlainFA fiziksel yerleşim kaydı bozuk.")
                entry_index = int(item.get("entry_index", -1))
                if entry_index < 0 or entry_index >= len(entries) or entry_index in seen:
                    raise xs.XsError("PlainFA fiziksel yerleşim sırası bozuk.")
                seen.add(entry_index)
                gap = decode_manifest_bytes(
                    item.get("gap_before_b64"), f"physical_layout[{position}].gap"
                )
                order.append((entries[entry_index], gap))
            if len(seen) != len(entries):
                raise xs.XsError("PlainFA fiziksel yerleşiminde eksik kayıt var.")
            trailing = decode_manifest_bytes(manifest.get("trailing_b64"), "trailing")
        else:
            order = [(entry, b"") for entry in entries]
            trailing = b""

        table_end = PLAINFA_HEADER_SIZE + len(entries) * PLAINFA_ENTRY_SIZE
        with temporary.open("w+b") as destination:
            destination.write(b"\0" * table_end)
            for entry, gap in order:
                destination.write(gap)
                offsets[entry.index] = destination.tell()
                source = sources[entry.index]
                sizes[entry.index] = source.stat().st_size
                with source.open("rb") as input_stream:
                    shutil.copyfileobj(input_stream, destination, COPY_CHUNK_SIZE)
            destination.write(trailing)
            final_size = destination.tell()
            if final_size > 0xFFFFFFFF:
                raise xs.XsError("PlainFA çıktısı 32 bit boyut sınırını aştı.")
            header_reserved = decode_manifest_bytes(
                manifest.get("header_reserved_b64"), "header_reserved", 8
            )
            destination.seek(0)
            destination.write(struct.pack("<II8s", len(entries), final_size, header_reserved))
            for entry in entries:
                destination.write(
                    struct.pack(
                        "<II8s64s",
                        offsets[entry.index],
                        sizes[entry.index],
                        entry.reserved,
                        entry.filename_raw,
                    )
                )
        PlainFaArchive.open(temporary)
        finalize_output(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def create_archive_from_directory(input_root: Path, output: Path, *, force: bool) -> None:
    if not input_root.is_dir():
        raise xs.XsError(f"PlainFA kaynak klasörü bulunamadı: {input_root}")
    members: list[tuple[str, Path, bytes]] = []
    for path in input_root.rglob("*"):
        if not path.is_file() or path.name == ".layton5_fa_manifest.json":
            continue
        if path.is_symlink():
            raise xs.XsError(f"Sembolik bağlantı üyesi reddedildi: {path}")
        relative = normalize_member_name(path.relative_to(input_root).as_posix())
        encoded = relative.encode("cp932")
        if len(encoded) >= PLAINFA_NAME_SIZE:
            raise xs.XsError(f"PlainFA iç yolu 63 baytı aşıyor: {relative}")
        filename_raw = encoded + b"\0" * (PLAINFA_NAME_SIZE - len(encoded))
        members.append((relative, path, filename_raw))
    members.sort(key=lambda item: item[0])
    if not members:
        raise xs.XsError("PlainFA oluşturmak için kaynak klasörde dosya yok.")
    if len(members) > 1_000_000:
        raise xs.XsError("PlainFA oluşturmak için fazla dosya var.")

    final_path, temporary = prepare_output(output, force)
    try:
        table_end = PLAINFA_HEADER_SIZE + len(members) * PLAINFA_ENTRY_SIZE
        entries: list[tuple[int, int, bytes, bytes]] = []
        with temporary.open("w+b") as destination:
            destination.write(b"\0" * table_end)
            for _relative, source_path, filename_raw in members:
                offset = destination.tell()
                size = source_path.stat().st_size
                with source_path.open("rb") as source:
                    shutil.copyfileobj(source, destination, COPY_CHUNK_SIZE)
                entries.append((offset, size, b"\0" * 8, filename_raw))
            final_size = destination.tell()
            if final_size > 0xFFFFFFFF:
                raise xs.XsError("PlainFA çıktısı 32 bit boyut sınırını aştı.")
            destination.seek(0)
            destination.write(struct.pack("<II8s", len(entries), final_size, b"\0" * 8))
            for entry in entries:
                destination.write(struct.pack("<II8s64s", *entry))
        PlainFaArchive.open(temporary)
        finalize_output(temporary, final_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def normalized_prefix(prefix: str) -> str:
    value = normalize_member_name(prefix).rstrip("/")
    return value + "/"


def xs_entries_in_archive(
    archive: PlainFaArchive, prefix: str
) -> list[tuple[str, PlainFaEntry]]:
    base = normalized_prefix(prefix)
    result = []
    for entry in archive.entries:
        if entry.path.startswith(base) and entry.path.lower().endswith(".xs"):
            relative = entry.path[len(base) :]
            result.append((relative, entry))
    return sorted(result)


def make_project_from_archive(
    archive: PlainFaArchive,
    prefix: str,
    *,
    kup_root: Path | None = None,
    allow_source_mismatch: bool = False,
) -> tuple[xs.TranslationProject, dict[str, object]]:
    files: dict[str, xs.ProjectFile] = {}
    texts: dict[str, list[xs.ProjectText]] = {}
    missing_kup: list[str] = []
    recovered_kup: list[str] = []
    mismatches: list[dict[str, str]] = []
    missing_ids: list[dict[str, str]] = []
    extra_ids: list[dict[str, str]] = []
    control_warnings: list[dict[str, object]] = []
    text_count = 0
    translated_count = 0
    selected = xs_entries_in_archive(archive, prefix)
    if not selected:
        raise xs.XsError(f"PlainFA içinde {prefix!r} altında XS bulunamadı.")

    for relative, entry in selected:
        raw = archive.read_entry(entry)
        parsed = xs.XsFile.from_bytes(raw, entry.path)
        digest = xs.sha256_bytes(raw)
        records = parsed.text_records(entry.path)
        files[relative] = xs.ProjectFile(relative, digest, len(records))
        kup_entries: dict[str, tuple[str, str]] = {}
        if kup_root is not None:
            dummy_source = kup_root / Path(relative)
            kup_path = xs.find_kup(kup_root, relative, dummy_source)
            if kup_path is None:
                missing_kup.append(relative)
            else:
                kup_entries, recovered = xs.parse_kup(kup_path)
                if recovered:
                    recovered_kup.append(relative)
        rows: list[xs.ProjectText] = []
        record_ids = {record.text_id for record in records}
        for record in records:
            original = record.original
            translation = original
            if kup_entries:
                kup_value = kup_entries.get(record.text_id)
                if kup_value is None:
                    missing_ids.append({"file": relative, "id": record.text_id})
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
                before_codes = xs.control_codes(original)
                after_codes = xs.control_codes(translation)
                if before_codes != after_codes:
                    control_warnings.append(
                        {
                            "file": relative,
                            "id": record.text_id,
                            "original_codes": before_codes,
                            "translation_codes": after_codes,
                        }
                    )
            rows.append(
                xs.ProjectText(
                    relative,
                    digest,
                    record.text_id,
                    record.offset,
                    original,
                    translation,
                )
            )
            text_count += 1
        texts[relative] = rows
        for extra_id in sorted(set(kup_entries) - record_ids):
            extra_ids.append({"file": relative, "id": extra_id})

    if mismatches and not allow_source_mismatch:
        first = mismatches[0]
        raise xs.XsError(
            f"KUP kaynağı arşivdeki XS ile uyuşmuyor: {first['file']} {first['id']}."
        )
    report: dict[str, object] = {
        "tool_version": TOOL_VERSION,
        "archive": str(archive.source_path),
        "xs_prefix": prefix,
        "xs_files": len(selected),
        "texts": text_count,
        "translated_texts": translated_count,
        "missing_kup_files": missing_kup,
        "recovered_kup_files": recovered_kup,
        "source_mismatches": mismatches,
        "missing_kup_ids": missing_ids,
        "extra_kup_ids": extra_ids,
        "control_code_warnings": control_warnings,
    }
    return xs.TranslationProject(files, texts), report


def verify_archive_rebuild(
    source: PlainFaArchive,
    output: PlainFaArchive,
    replacements: Mapping[str, Replacement],
) -> None:
    if len(source.entries) != len(output.entries):
        raise xs.XsError("PlainFA doğrulamasında kayıt sayısı değişti.")
    if source.header_reserved != output.header_reserved:
        raise xs.XsError("PlainFA başlık ayrılmış alanı değişti.")
    for before, after in zip(source.entries, output.entries):
        if (
            before.path != after.path
            or before.filename_raw != after.filename_raw
            or before.reserved != after.reserved
        ):
            raise xs.XsError(f"PlainFA kayıt metadatası değişti: {before.path}")
        if before.path not in replacements and source.hash_entry(before) != output.hash_entry(after):
            raise xs.XsError(f"Değiştirilmemiş PlainFA üyesi farklılaştı: {before.path}")


def inject_project_into_archive(
    archive: PlainFaArchive,
    project: xs.TranslationProject,
    output_path: Path,
    *,
    prefix: str,
    compression: str,
    encoding_policy: str,
    ignore_source_hash: bool,
    force: bool,
) -> dict[str, object]:
    selected = xs_entries_in_archive(archive, prefix)
    archive_paths = {relative for relative, _ in selected}
    missing_archive = sorted(set(project.files) - archive_paths)
    if missing_archive:
        raise xs.XsError(
            "Projede olup lt5_uk.fa içinde bulunmayan XS dosyaları var: "
            + ", ".join(missing_archive[:8])
        )

    replacements: dict[str, bytes] = {}
    expected_by_member: dict[str, dict[str, str]] = {}
    encoding_changes: list[dict[str, str]] = []
    control_warnings: list[dict[str, object]] = []
    missing_project: list[str] = []
    applied = 0
    unchanged = 0

    for relative, entry in selected:
        raw = archive.read_entry(entry)
        parsed = xs.XsFile.from_bytes(raw, entry.path)
        file_entry = project.files.get(relative)
        if file_entry is None:
            if parsed.text_records(entry.path):
                missing_project.append(relative)
            continue
        digest = xs.sha256_bytes(raw)
        if digest != file_entry.source_sha256 and not ignore_source_hash:
            raise xs.XsError(
                f"{relative}: arşivdeki temiz XS SHA-256 değeri projeyle uyuşmuyor."
            )
        translations = project.translations_for(relative)
        rebuilt, expected, changes = parsed.rebuild(
            translations,
            compression=compression,
            encoding_policy=encoding_policy,
        )
        original_records = parsed.text_records(entry.path)
        for record in original_records:
            if expected[record.text_id] == record.original:
                unchanged += 1
            else:
                applied += 1
        for change in changes:
            encoding_changes.append({"file": relative, **change})
        for row in project.texts.get(relative, []):
            before_codes = xs.control_codes(row.original)
            after_codes = xs.control_codes(row.translation)
            if before_codes != after_codes:
                control_warnings.append(
                    {
                        "file": relative,
                        "id": row.text_id,
                        "original_codes": before_codes,
                        "translation_codes": after_codes,
                    }
                )
        if rebuilt != raw:
            replacements[entry.path] = rebuilt
            expected_by_member[entry.path] = expected

    rebuild_archive(archive, output_path, replacements, preserve_layout=True, force=force)
    output = PlainFaArchive.open(output_path)
    verify_archive_rebuild(archive, output, replacements)
    output_by_path = output.by_path()
    for member_path, expected in expected_by_member.items():
        parsed = xs.XsFile.from_bytes(output.read_entry(output_by_path[member_path]), member_path)
        records = parsed.text_records(member_path)
        actual = {record.text_id: record.original for record in records}
        if actual != expected:
            raise xs.XsError(f"Arşiv içi XSCR doğrulaması başarısız: {member_path}")

    return {
        "tool_version": TOOL_VERSION,
        "source_archive": str(archive.source_path),
        "output_archive": str(output_path),
        "source_sha256": hash_path(archive.source_path),
        "output_sha256": hash_path(output_path),
        "archive_entries": len(archive.entries),
        "xs_files_seen": len(selected),
        "xs_files_rebuilt": len(replacements),
        "translated_texts_applied": applied,
        "unchanged_texts": unchanged,
        "missing_project_files": missing_project,
        "encoding_changes": encoding_changes,
        "control_code_warnings": control_warnings,
        "compression": compression,
        "encoding_policy": encoding_policy,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def command_fa_info(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    result = archive.summary()
    if args.detailed:
        result["entries"] = [
            {
                "index": entry.index,
                "path": entry.path,
                "offset": entry.offset,
                "size": entry.size,
                "sha256": archive.hash_entry(entry),
            }
            for entry in archive.entries
        ]
    if args.report:
        write_json(args.report, result)
    return result


def command_fa_verify(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    report = archive.summary()
    warnings: list[str] = []
    if archive.reported_size != archive.actual_size:
        warnings.append(
            f"Başlıktaki boyut {archive.reported_size}, gerçek boyut {archive.actual_size}."
        )
    if any(archive.header_reserved):
        warnings.append("Başlık ayrılmış alanı sıfır değil; veri korunacaktır.")
    reserved_entries = sum(1 for entry in archive.entries if any(entry.reserved))
    if reserved_entries:
        warnings.append(f"{reserved_entries} kaydın ayrılmış alanı sıfır değil; veri korunacaktır.")
    xs_errors: list[dict[str, str]] = []
    xs_valid = 0
    if args.deep_xs:
        prefix = args.prefix
        for relative, entry in xs_entries_in_archive(archive, prefix):
            try:
                xs.XsFile.from_bytes(archive.read_entry(entry), entry.path)
                xs_valid += 1
            except xs.XsError as exc:
                xs_errors.append({"file": relative, "error": str(exc)})
    report.update(
        {
            "warnings": warnings,
            "deep_xs_checked": bool(args.deep_xs),
            "valid_xs_files": xs_valid,
            "xs_errors": xs_errors,
        }
    )
    if args.report:
        write_json(args.report, report)
    if xs_errors:
        raise xs.XsError(f"{len(xs_errors)} XSCR dosyası doğrulanamadı; rapora bakın.")
    return report


def command_fa_extract(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    if args.output.exists() and any(args.output.iterdir()) and not args.force:
        raise xs.XsError(
            f"Çıkarma klasörü boş değil; mevcut dosyaları korumak için işlem durdu: {args.output}"
        )
    args.output.mkdir(parents=True, exist_ok=True)
    for entry in archive.entries:
        destination = safe_output_member(args.output, entry.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not args.force:
            raise xs.XsError(f"Çıkarma hedefi zaten var: {destination}")
        with archive.open_entry(entry) as source, destination.open("wb") as output:
            copy_exact(source, output, entry.size)
    manifest_path = args.output / ".layton5_fa_manifest.json"
    write_json(manifest_path, manifest_for_archive(archive))
    report = {
        "tool_version": TOOL_VERSION,
        "archive": str(args.archive),
        "output": str(args.output),
        "files_extracted": len(archive.entries),
        "manifest": str(manifest_path),
    }
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_pack(args: argparse.Namespace) -> dict[str, object]:
    manifest = args.manifest or args.input / ".layton5_fa_manifest.json"
    pack_from_manifest(
        args.input,
        manifest,
        args.output,
        preserve_layout=args.layout == "preserve",
        force=args.force,
    )
    archive = PlainFaArchive.open(args.output)
    report = archive.summary()
    report.update(
        {
            "input": str(args.input),
            "manifest": str(manifest),
            "output_sha256": hash_path(args.output),
            "layout": args.layout,
        }
    )
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_create(args: argparse.Namespace) -> dict[str, object]:
    create_archive_from_directory(args.input, args.output, force=args.force)
    archive = PlainFaArchive.open(args.output)
    report = archive.summary()
    report.update(
        {
            "input": str(args.input),
            "output_sha256": hash_path(args.output),
            "layout": "compact-sorted",
        }
    )
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_replace(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    if not args.replacements.is_dir():
        raise xs.XsError(f"Değiştirme klasörü bulunamadı: {args.replacements}")
    replacements: dict[str, Path] = {}
    known = archive.by_path()
    for path in args.replacements.rglob("*"):
        if not path.is_file() or path.name == ".layton5_fa_manifest.json":
            continue
        if path.is_symlink():
            raise xs.XsError(f"Sembolik bağlantı değiştirme dosyası reddedildi: {path}")
        relative = normalize_member_name(path.relative_to(args.replacements).as_posix())
        if relative not in known:
            raise xs.XsError(f"Değiştirme klasöründeki yol arşivde yok: {relative}")
        replacements[relative] = path
    if not replacements:
        raise xs.XsError("Değiştirme klasöründe arşivle eşleşen dosya yok.")
    rebuild_archive(
        archive,
        args.output,
        replacements,
        preserve_layout=args.layout == "preserve",
        force=args.force,
    )
    output = PlainFaArchive.open(args.output)
    verify_archive_rebuild(archive, output, replacements)
    report = {
        "tool_version": TOOL_VERSION,
        "source_archive": str(args.archive),
        "output_archive": str(args.output),
        "replaced_files": sorted(replacements),
        "source_sha256": hash_path(args.archive),
        "output_sha256": hash_path(args.output),
        "layout": args.layout,
    }
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_export_text(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    project, report = make_project_from_archive(archive, args.prefix)
    xs.write_project(project, args.project)
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_migrate_kup(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    project, report = make_project_from_archive(
        archive,
        args.prefix,
        kup_root=args.kup_root,
        allow_source_mismatch=args.allow_source_mismatch,
    )
    xs.write_project(project, args.project)
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_inject_text(args: argparse.Namespace) -> dict[str, object]:
    archive = PlainFaArchive.open(args.archive)
    project = xs.read_project(args.project)
    report = inject_project_into_archive(
        archive,
        project,
        args.output,
        prefix=args.prefix,
        compression=args.compression,
        encoding_policy=args.encoding_policy,
        ignore_source_hash=args.ignore_source_hash,
        force=args.force,
    )
    if args.report:
        write_json(args.report, report)
    return report


def command_fa_diff(args: argparse.Namespace) -> dict[str, object]:
    left = PlainFaArchive.open(args.left)
    right = PlainFaArchive.open(args.right)
    left_map = left.by_path()
    right_map = right.by_path()
    added = sorted(set(right_map) - set(left_map))
    removed = sorted(set(left_map) - set(right_map))
    changed = []
    layout_changed = []
    for path in sorted(set(left_map) & set(right_map)):
        before, after = left_map[path], right_map[path]
        before_hash = left.hash_entry(before)
        after_hash = right.hash_entry(after)
        if before_hash != after_hash:
            changed.append(
                {
                    "path": path,
                    "before_size": before.size,
                    "after_size": after.size,
                    "before_sha256": before_hash,
                    "after_sha256": after_hash,
                }
            )
        if before.offset != after.offset:
            layout_changed.append(
                {"path": path, "before_offset": before.offset, "after_offset": after.offset}
            )
    report = {
        "tool_version": TOOL_VERSION,
        "left": str(args.left),
        "right": str(args.right),
        "added": added,
        "removed": removed,
        "changed": changed,
        "layout_changed": layout_changed,
        "header_reserved_changed": left.header_reserved != right.header_reserved,
    }
    if args.report:
        write_json(args.report, report)
    return report


def _encode_plainfa_name(name: str) -> bytes:
    encoded = normalize_member_name(name).encode("cp932")
    if len(encoded) >= PLAINFA_NAME_SIZE:
        raise xs.XsError("Sentetik PlainFA üye adı fazla uzun.")
    return encoded + b"\0" * (PLAINFA_NAME_SIZE - len(encoded))


def create_synthetic_plainfa(path: Path) -> None:
    members = [
        ("txt/uk/00/a.xs", xs._synthetic_xs()),
        ("asset/raw.bin", bytes(range(64))),
        ("txt/uk/00/b.xs", xs._synthetic_xs()),
        ("empty.dat", b""),
    ]
    reserved_header = b"HDRTEST!"
    reserved_entries = [b"ENTRY%03d" % index for index in range(len(members))]
    table_end = PLAINFA_HEADER_SIZE + len(members) * PLAINFA_ENTRY_SIZE
    gaps = [b"\xA5\0\xA5", b"\0" * 5, b"LAYTON", b""]
    output = bytearray(b"\0" * table_end)
    entries = []
    for index, ((name, payload), gap) in enumerate(zip(members, gaps)):
        output.extend(gap)
        offset = len(output)
        output.extend(payload)
        entries.append((offset, len(payload), reserved_entries[index], _encode_plainfa_name(name)))
    output.extend(b"TRAIL")
    struct.pack_into("<II8s", output, 0, len(entries), len(output), reserved_header)
    for index, entry in enumerate(entries):
        struct.pack_into("<II8s64s", output, PLAINFA_HEADER_SIZE + index * PLAINFA_ENTRY_SIZE, *entry)
    path.write_bytes(bytes(output))


def command_selftest(_args: argparse.Namespace) -> dict[str, object]:
    xs_result = xs.command_selftest(argparse.Namespace())
    with tempfile.TemporaryDirectory() as directory_name:
        directory = Path(directory_name)
        source_path = directory / "source.fa"
        extract_root = directory / "extracted"
        rebuilt_path = directory / "rebuilt.fa"
        replaced_path = directory / "replaced.fa"
        create_synthetic_plainfa(source_path)
        source = PlainFaArchive.open(source_path)
        extract_root.mkdir()
        for entry in source.entries:
            destination = safe_output_member(extract_root, entry.path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_entry(entry))
        manifest_path = extract_root / ".layton5_fa_manifest.json"
        write_json(manifest_path, manifest_for_archive(source))
        pack_from_manifest(
            extract_root, manifest_path, rebuilt_path, preserve_layout=True, force=False
        )
        if source_path.read_bytes() != rebuilt_path.read_bytes():
            raise xs.XsError("PlainFA çıkar/paketle öz sınaması bayt düzeyinde başarısız.")
        replacement = b"replacement payload that is longer than the original"
        rebuild_archive(
            source,
            replaced_path,
            {"asset/raw.bin": replacement},
            preserve_layout=True,
            force=False,
        )
        replaced = PlainFaArchive.open(replaced_path)
        verify_archive_rebuild(source, replaced, {"asset/raw.bin": replacement})
        if replaced.read_entry(replaced.by_path()["asset/raw.bin"]) != replacement:
            raise xs.XsError("PlainFA değiştirme öz sınaması başarısız.")
    return {
        "tool_version": TOOL_VERSION,
        "selftest": "passed",
        "xs_selftest": xs_result,
        "plainfa_roundtrip": "byte-identical",
        "plainfa_replacement": "verified",
    }


def add_common_report(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--report", type=Path)


def add_output_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--force", action="store_true", help="Var olan çıktı dosyasının üzerine yaz.")
    add_common_report(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Professor Layton 5 lt5_uk.fa (PlainFA) arşivi ve XSCR metinleri için "
            "uçtan uca araç. Eski XS komutları için: layton5_tool.py xs <komut>"
        )
    )
    parser.add_argument("--version", action="version", version=TOOL_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("fa-info", help="PlainFA başlığını ve dosya ağacı özetini göster.")
    info.add_argument("archive", type=Path)
    info.add_argument("--detailed", action="store_true")
    add_common_report(info)
    info.set_defaults(handler=command_fa_info)

    verify = sub.add_parser("fa-verify", help="PlainFA ve isteğe bağlı iç XSCR'leri doğrula.")
    verify.add_argument("archive", type=Path)
    verify.add_argument("--deep-xs", action="store_true")
    verify.add_argument("--prefix", default="txt/uk")
    add_common_report(verify)
    verify.set_defaults(handler=command_fa_verify)

    extract = sub.add_parser("fa-extract", help="PlainFA'yı güvenli biçimde çıkar ve manifest yaz.")
    extract.add_argument("archive", type=Path)
    extract.add_argument("output", type=Path)
    add_output_flags(extract)
    extract.set_defaults(handler=command_fa_extract)

    pack = sub.add_parser("fa-pack", help="Çıkarılmış ağaç ve manifestten PlainFA oluştur.")
    pack.add_argument("input", type=Path)
    pack.add_argument("output", type=Path)
    pack.add_argument("--manifest", type=Path)
    pack.add_argument("--layout", choices=["preserve", "compact"], default="preserve")
    add_output_flags(pack)
    pack.set_defaults(handler=command_fa_pack)

    create = sub.add_parser(
        "fa-create", help="Bir klasör ağacından sıralı ve kompakt yeni PlainFA oluştur."
    )
    create.add_argument("input", type=Path)
    create.add_argument("output", type=Path)
    add_output_flags(create)
    create.set_defaults(handler=command_fa_create)

    replace = sub.add_parser("fa-replace", help="Klasördeki eşleşen üyeleri arşive geri koy.")
    replace.add_argument("archive", type=Path)
    replace.add_argument("replacements", type=Path)
    replace.add_argument("output", type=Path)
    replace.add_argument("--layout", choices=["preserve", "compact"], default="preserve")
    add_output_flags(replace)
    replace.set_defaults(handler=command_fa_replace)

    export_text = sub.add_parser(
        "fa-export-text", help="XSCR metinlerini FA içinden doğrudan JSONL/CSV'ye çıkar."
    )
    export_text.add_argument("archive", type=Path)
    export_text.add_argument("project", type=Path)
    export_text.add_argument("--prefix", default="txt/uk")
    add_common_report(export_text)
    export_text.set_defaults(handler=command_fa_export_text)

    migrate = sub.add_parser(
        "fa-migrate-kup", help="KUP çevirilerini temiz FA içindeki XS'lerle eşleyerek projeye taşı."
    )
    migrate.add_argument("archive", type=Path)
    migrate.add_argument("kup_root", type=Path)
    migrate.add_argument("project", type=Path)
    migrate.add_argument("--prefix", default="txt/uk")
    migrate.add_argument("--allow-source-mismatch", action="store_true")
    add_common_report(migrate)
    migrate.set_defaults(handler=command_fa_migrate_kup)

    inject = sub.add_parser(
        "fa-inject-text", help="Çeviri projesini doğrudan temiz lt5_uk.fa içine enjekte et."
    )
    inject.add_argument("archive", type=Path)
    inject.add_argument("project", type=Path)
    inject.add_argument("output", type=Path)
    inject.add_argument("--prefix", default="txt/uk")
    inject.add_argument(
        "--compression", choices=["original", "lz10", "none"], default="original"
    )
    inject.add_argument(
        "--encoding-policy", choices=["strict", "turkish-ascii"], default="strict"
    )
    inject.add_argument("--ignore-source-hash", action="store_true")
    add_output_flags(inject)
    inject.set_defaults(handler=command_fa_inject_text)

    diff = sub.add_parser("fa-diff", help="İki PlainFA arşivini üye ve yerleşim düzeyinde karşılaştır.")
    diff.add_argument("left", type=Path)
    diff.add_argument("right", type=Path)
    add_common_report(diff)
    diff.set_defaults(handler=command_fa_diff)

    selftest = sub.add_parser("selftest", help="XSCR ve PlainFA dahili testlerini çalıştır.")
    selftest.set_defaults(handler=command_selftest)
    return parser


def compact_report(report: Mapping[str, object]) -> dict[str, object]:
    display = dict(report)
    for key, value in list(display.items()):
        if isinstance(value, list) and len(value) > 20:
            display[key] = value[:5]
            display[f"{key}_count"] = len(value)
            display[f"{key}_note"] = "İlk 5 kayıt gösteriliyor; tam liste rapor dosyasındadır."
        elif isinstance(value, dict) and len(value) > 40:
            display[key] = dict(list(value.items())[:20])
            display[f"{key}_count"] = len(value)
            display[f"{key}_note"] = "İlk 20 kayıt gösteriliyor."
    return display


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "xs":
        return xs.main(arguments[1:])
    parser = build_parser()
    args = parser.parse_args(arguments)
    try:
        report = args.handler(args)
    except (xs.XsError, OSError, ValueError, KeyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(compact_report(report), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
