#!/usr/bin/env python3
"""Extract and inject text in Kingdom Hearts 3D message.rbin archives.

The RBIN/CTD structures are based on the Apache-2.0 licensed OpenKh project.
See THIRD_PARTY_NOTICES.md.

This tool is intentionally conservative:
* archive hashes and filenames are preserved;
* untouched CTD entries are copied byte-for-byte;
* an entirely blank translation column produces an identical RBIN;
* unsupported characters cause an error instead of silent data loss.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import re
import shutil
import struct
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


CRAR_MAGIC = b"CRAR"
CTD_MAGIC = b"@CTD"
RBIN_HEADER_SIZE = 0x20
RBIN_ENTRY_SIZE = 0x10
CTD_HEADER_SIZE = 0x20
CTD_MESSAGE_SIZE = 0x08
CTD_LAYOUT_SIZE = 0x14
EMPTY_SENTINEL = "[[EMPTY]]"


class FormatError(ValueError):
    pass


def align(value: int, boundary: int = 16) -> int:
    return (value + boundary - 1) & ~(boundary - 1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class RbinEntry:
    index: int
    entry_offset: int
    hash_value: int
    name_offset: int
    info: int
    data_offset: int
    name: str
    occurrence: int = 0

    @property
    def size(self) -> int:
        return self.info & 0x7FFFFFFF

    @property
    def compressed(self) -> bool:
        return bool(self.info & 0x80000000)


@dataclass
class RbinArchive:
    raw: bytes
    version: int
    data_offset: int
    mount_point: str
    entries: List[RbinEntry]


@dataclass
class CtdMessage:
    index: int
    message_id: int
    layout_index: int
    wait_frames: int
    data: bytes


@dataclass
class CtdFile:
    raw: bytes
    version: int
    file_id: int
    layout_count: int
    message_count: int
    message_offset: int
    layout_offset: int
    text_offset: int
    unknown_1c: int
    layouts: bytes
    messages: List[CtdMessage]


@dataclass
class LanguageMessage:
    index: int
    message_id: int
    layout_index: int
    wait_frames: int
    text: str


@dataclass
class LanguageCtd:
    entry_index: int
    entry_hash: int
    ctd_name: str
    ctd_file_id: int
    messages: List[LanguageMessage]


def read_c_string(data: bytes, offset: int) -> str:
    if not 0 <= offset < len(data):
        raise FormatError(f"String offset is outside the file: 0x{offset:X}")
    end = data.find(b"\0", offset)
    if end < 0:
        raise FormatError(f"Unterminated string at 0x{offset:X}")
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise FormatError(f"Non-ASCII RBIN filename at 0x{offset:X}") from exc


def parse_rbin(path: Path) -> RbinArchive:
    raw = path.read_bytes()
    if len(raw) < RBIN_HEADER_SIZE or raw[:4] != CRAR_MAGIC:
        raise FormatError(f"{path} is not a CRAR/RBIN file")

    _magic, version, count, data_offset, _reserved = struct.unpack_from(
        "<4sHHII", raw, 0
    )
    mount_point = raw[0x10:0x20].split(b"\0", 1)[0].decode("ascii", "replace")
    toc_end = RBIN_HEADER_SIZE + count * RBIN_ENTRY_SIZE
    if toc_end > len(raw) or data_offset < toc_end or data_offset > len(raw):
        raise FormatError("Invalid RBIN table or data offset")

    entries: List[RbinEntry] = []
    occurrences: Dict[str, int] = defaultdict(int)
    for index in range(count):
        entry_offset = RBIN_HEADER_SIZE + index * RBIN_ENTRY_SIZE
        hash_value, name_offset, info, file_offset = struct.unpack_from(
            "<IIII", raw, entry_offset
        )
        # NameOffset is relative to the NameOffset field itself.
        name_pos = entry_offset + 4 + name_offset
        name = read_c_string(raw, name_pos)
        occurrences[name] += 1
        entry = RbinEntry(
            index=index,
            entry_offset=entry_offset,
            hash_value=hash_value,
            name_offset=name_offset,
            info=info,
            data_offset=file_offset,
            name=name,
            occurrence=occurrences[name],
        )
        if entry.data_offset + entry.size > len(raw):
            raise FormatError(f"RBIN entry {index} ({name}) extends past EOF")
        entries.append(entry)

    return RbinArchive(raw, version, data_offset, mount_point, entries)


def entry_bytes(archive: RbinArchive, entry: RbinEntry) -> bytes:
    return archive.raw[entry.data_offset : entry.data_offset + entry.size]


def parse_ctd(data: bytes, label: str = "CTD") -> CtdFile:
    if len(data) < CTD_HEADER_SIZE or data[:4] != CTD_MAGIC:
        raise FormatError(f"{label} is not a @CTD file")

    (
        _magic,
        version,
        file_id,
        layout_count,
        message_count,
        message_offset,
        layout_offset,
        text_offset,
        unknown_1c,
    ) = struct.unpack_from("<4sIIHHIIII", data, 0)

    table_end = message_offset + message_count * CTD_MESSAGE_SIZE
    layouts_end = layout_offset + layout_count * CTD_LAYOUT_SIZE
    if not (
        CTD_HEADER_SIZE <= message_offset <= table_end <= len(data)
        and table_end <= layout_offset <= layouts_end <= text_offset <= len(data)
    ):
        raise FormatError(f"{label} has invalid CTD section offsets")

    messages: List[CtdMessage] = []
    previous_string_offset = text_offset
    string_page = text_offset & ~0xFFFF
    for index in range(message_count):
        record_offset = message_offset + index * CTD_MESSAGE_SIZE
        message_id, string_offset_low, packed_meta = struct.unpack_from(
            "<IHH", data, record_offset
        )
        string_offset = string_page | string_offset_low
        while string_offset < previous_string_offset:
            string_offset += 0x10000
        string_page = string_offset & ~0xFFFF
        previous_string_offset = string_offset
        layout_index = packed_meta >> 4
        wait_frames = packed_meta & 0xF
        if not text_offset <= string_offset < len(data):
            raise FormatError(
                f"{label} message {index} has invalid text offset 0x{string_offset:X}"
            )
        end = string_offset
        while end + 2 <= len(data) and data[end : end + 2] != b"\0\0":
            end += 2
        if end + 2 > len(data):
            raise FormatError(f"{label} message {index} is not null-terminated")
        messages.append(
            CtdMessage(index, message_id, layout_index, wait_frames, data[string_offset:end])
        )

    layouts = data[layout_offset:layouts_end]
    return CtdFile(
        raw=data,
        version=version,
        file_id=file_id,
        layout_count=layout_count,
        message_count=message_count,
        message_offset=message_offset,
        layout_offset=layout_offset,
        text_offset=text_offset,
        unknown_1c=unknown_1c,
        layouts=layouts,
        messages=messages,
    )


def decode_ctd_text(data: bytes) -> str:
    try:
        return data.decode("utf-16le")
    except UnicodeDecodeError as exc:
        raise FormatError(f"Invalid UTF-16LE text at byte {exc.start}") from exc


TURKISH_ASCII = str.maketrans({"ğ": "g", "Ğ": "G", "ş": "s", "Ş": "S", "ı": "i", "İ": "I"})


def encode_ctd_text(text: str, turkish_ascii: bool = False) -> bytes:
    if turkish_ascii:
        text = text.translate(TURKISH_ASCII)
    if "\0" in text:
        raise FormatError("NUL cannot appear inside a CTD message")
    try:
        return text.encode("utf-16le")
    except UnicodeEncodeError as exc:
        raise FormatError(f"Text cannot be encoded as UTF-16LE near character {exc.start}") from exc


def rebuild_ctd(ctd: CtdFile, replacements: Dict[int, bytes]) -> bytes:
    if not replacements:
        return ctd.raw

    text_offset = ctd.text_offset
    text_blob = bytearray()
    output = bytearray(ctd.raw[:text_offset])

    for message in ctd.messages:
        message_data = replacements.get(message.index, message.data)
        string_offset = text_offset + len(text_blob)
        struct.pack_into("<H", output, ctd.message_offset + message.index * CTD_MESSAGE_SIZE + 4, string_offset & 0xFFFF)
        text_blob.extend(message_data)
        text_blob.extend(b"\0\0")

    output.extend(text_blob)
    return bytes(output)


CSV_FIELDS = [
    "rbin_index",
    "rbin_hash",
    "ctd_name",
    "ctd_occurrence",
    "language_hint",
    "ctd_file_id",
    "message_index",
    "message_id",
    "layout_index",
    "wait_frames",
    "source_text",
    "translation",
]


ALIGNED_CSV_FIELDS = [
    "target_language",
    "target_rbin_indices",
    "target_rbin_hashes",
    "target_message_indices",
    "ctd_name",
    "ctd_file_id",
    "message_id",
    "layout_index",
    "wait_frames",
    "source_fr",
    "source_en",
    "source_de",
    "match_status",
    "target_variant_count",
    "translation",
]


ALIGNED_REQUIRED_FIELDS = [
    "target_language",
    "target_rbin_indices",
    "target_rbin_hashes",
    "target_message_indices",
    "ctd_name",
    "ctd_file_id",
    "message_id",
    "translation",
]


TRANSLATION_LANGUAGES = ("fr", "en", "de")


LANGUAGE_WORDS = {
    "fr": set(
        "le la les de des du un une et est sont que qui dans pour pas vous avec ce cette "
        "je il elle nous votre au aux en sur mais mon ton son ne plus ça oui où très tout tous "
        "utilisé vaincre terrasse visite visiter quitter".split()
    ),
    "en": set(
        "the and is are a an to of you your in for with this that not it he she we they on but "
        "from have has what yes all used defeat visit leave".split()
    ),
    "de": set(
        "der die das und ist sind ein eine einer nicht mit ich sie zu den von auf für was ja im "
        "dem aber wir er es ihr besiege besuchen verlassen".split()
    ),
}


def language_scores(texts: Iterable[str]) -> Tuple[Dict[str, int], bool]:
    text = "\n".join(texts).lower()
    has_japanese = any(
        "\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff"
        for char in text
    )
    tokens = Counter(re.findall(r"[a-zà-ÿœ]+", text))
    scores = {
        language: sum(tokens[word] for word in words)
        for language, words in LANGUAGE_WORDS.items()
    }
    scores["fr"] += sum(text.count(char) * 3 for char in "éèêëàâùûîïôçœ")
    scores["de"] += sum(text.count(char) * 3 for char in "äöüß")
    return scores, has_japanese


def detect_language(texts: Iterable[str]) -> str:
    scores, has_japanese = language_scores(texts)
    if has_japanese:
        return "ja"
    best = max(scores, key=scores.get)
    return best if scores[best] else "unknown"


def language_ctds_from_rbin(rbin_path: Path) -> List[LanguageCtd]:
    archive = parse_rbin(rbin_path)
    result: List[LanguageCtd] = []
    for entry in archive.entries:
        if not entry.name.lower().endswith(".ctd"):
            continue
        if entry.compressed:
            raise FormatError(
                f"Compressed CTD entry is not supported: #{entry.index} {entry.name}"
            )
        ctd = parse_ctd(entry_bytes(archive, entry), f"#{entry.index} {entry.name}")
        result.append(
            LanguageCtd(
                entry_index=entry.index,
                entry_hash=entry.hash_value,
                ctd_name=entry.name,
                ctd_file_id=ctd.file_id,
                messages=[
                    LanguageMessage(
                        index=message.index,
                        message_id=message.message_id,
                        layout_index=message.layout_index,
                        wait_frames=message.wait_frames,
                        text=decode_ctd_text(message.data),
                    )
                    for message in ctd.messages
                ],
            )
        )
    return result


def language_ctds_from_legacy_csv(csv_path: Path) -> List[LanguageCtd]:
    required = [
        "rbin_index",
        "rbin_hash",
        "ctd_name",
        "ctd_file_id",
        "message_index",
        "message_id",
        "layout_index",
        "wait_frames",
        "source_text",
    ]
    grouped: Dict[Tuple[int, int, str, int], List[LanguageMessage]] = defaultdict(list)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [field for field in required if field not in (reader.fieldnames or [])]
        if missing:
            raise FormatError(f"CSV is missing columns: {', '.join(missing)}")
        for row_number, row in enumerate(reader, start=2):
            try:
                key = (
                    int(row["rbin_index"], 10),
                    int(row["rbin_hash"], 0),
                    row["ctd_name"],
                    int(row["ctd_file_id"], 0),
                )
                message = LanguageMessage(
                    index=int(row["message_index"], 10),
                    message_id=int(row["message_id"], 0),
                    layout_index=int(row["layout_index"], 10),
                    wait_frames=int(row["wait_frames"], 10),
                    text=row["source_text"],
                )
            except ValueError as exc:
                raise FormatError(f"Invalid numeric field at CSV row {row_number}") from exc
            grouped[key].append(message)

    result: List[LanguageCtd] = []
    for (entry_index, entry_hash, ctd_name, ctd_file_id), messages in grouped.items():
        messages.sort(key=lambda message: message.index)
        if len({message.index for message in messages}) != len(messages):
            raise FormatError(f"Duplicate message index in RBIN entry {entry_index}")
        result.append(
            LanguageCtd(
                entry_index=entry_index,
                entry_hash=entry_hash,
                ctd_name=ctd_name,
                ctd_file_id=ctd_file_id,
                messages=messages,
            )
        )
    result.sort(key=lambda item: item.entry_index)
    return result


def assign_group_languages(items: List[LanguageCtd]) -> Dict[str, List[LanguageCtd]]:
    scored: List[Tuple[LanguageCtd, Dict[str, int], bool]] = []
    for item in items:
        scores, has_japanese = language_scores(message.text for message in item.messages)
        scored.append((item, scores, has_japanese))

    assigned: Dict[str, List[LanguageCtd]] = defaultdict(list)

    # Normal localized CTDs occur in a three-file set.  Treat the language
    # assignment as a one-to-one problem so short English files cannot be
    # mistaken for French merely because they contain a loanword.
    if len(scored) == 3 and not any(has_japanese for _item, _scores, has_japanese in scored):
        best_languages: Optional[Tuple[str, ...]] = None
        best_score = -1
        for languages in itertools.permutations(TRANSLATION_LANGUAGES):
            score = sum(scored[index][1][language] for index, language in enumerate(languages))
            if score > best_score:
                best_score = score
                best_languages = languages
        if best_languages is not None and best_score > 0:
            for (item, _scores, _has_japanese), language in zip(scored, best_languages):
                assigned[language].append(item)
        return assigned

    # A small number of archive groups contain duplicate regional variants.
    # Keep every confidently identified copy so one Turkish cell can update
    # all target-language copies of the same message ID.
    for item, scores, has_japanese in scored:
        if has_japanese:
            continue
        language = max(scores, key=scores.get)
        if scores[language] > 0:
            assigned[language].append(item)
    return assigned


def message_map(items: List[LanguageCtd]) -> Dict[int, List[Tuple[LanguageCtd, LanguageMessage]]]:
    result: Dict[int, List[Tuple[LanguageCtd, LanguageMessage]]] = defaultdict(list)
    for item in sorted(items, key=lambda value: value.entry_index):
        seen: set[int] = set()
        for message in item.messages:
            if message.message_id in seen:
                raise FormatError(
                    f"Duplicate message ID 0x{message.message_id:08X} in RBIN entry "
                    f"{item.entry_index} ({item.ctd_name})"
                )
            seen.add(message.message_id)
            result[message.message_id].append((item, message))
    return result


def write_aligned_csv(
    ctds: List[LanguageCtd], csv_path: Path, target_language: str = "fr"
) -> Tuple[int, int, int, int, int]:
    if target_language not in TRANSLATION_LANGUAGES:
        raise FormatError(f"Unsupported target language: {target_language}")

    grouped: Dict[Tuple[str, int], List[LanguageCtd]] = defaultdict(list)
    for item in ctds:
        grouped[(item.ctd_name, item.ctd_file_id)].append(item)

    prepared_groups = []
    for key, items in grouped.items():
        assigned = assign_group_languages(items)
        targets = assigned.get(target_language, [])
        if targets:
            prepared_groups.append((min(item.entry_index for item in targets), key, assigned))
    prepared_groups.sort(key=lambda value: value[0])

    group_count = 0
    row_count = 0
    complete_count = 0
    missing_en = 0
    missing_de = 0
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=ALIGNED_CSV_FIELDS, quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for _first_index, (ctd_name, ctd_file_id), assigned in prepared_groups:
            maps = {
                language: message_map(assigned.get(language, []))
                for language in TRANSLATION_LANGUAGES
            }
            target_map = maps[target_language]
            ordered_message_ids: List[int] = []
            seen_ids: set[int] = set()
            for target in sorted(assigned[target_language], key=lambda value: value.entry_index):
                for message in target.messages:
                    if message.message_id not in seen_ids:
                        seen_ids.add(message.message_id)
                        ordered_message_ids.append(message.message_id)

            group_count += 1
            for message_id in ordered_message_ids:
                target_records = target_map[message_id]
                representative = target_records[0][1]
                present = [language for language in TRANSLATION_LANGUAGES if message_id in maps[language]]
                missing = [language for language in TRANSLATION_LANGUAGES if language not in present]
                match_status = "matched_fr_en_de" if not missing else "missing_" + "_".join(missing)
                if "en" in missing:
                    missing_en += 1
                if "de" in missing:
                    missing_de += 1
                if not missing:
                    complete_count += 1

                def source_text(language: str) -> str:
                    records = maps[language].get(message_id, [])
                    return records[0][1].text if records else ""

                writer.writerow(
                    {
                        "target_language": target_language,
                        "target_rbin_indices": "|".join(
                            str(item.entry_index) for item, _message in target_records
                        ),
                        "target_rbin_hashes": "|".join(
                            f"0x{item.entry_hash:08X}" for item, _message in target_records
                        ),
                        "target_message_indices": "|".join(
                            str(message.index) for _item, message in target_records
                        ),
                        "ctd_name": ctd_name,
                        "ctd_file_id": f"0x{ctd_file_id:08X}",
                        "message_id": f"0x{message_id:08X}",
                        "layout_index": representative.layout_index,
                        "wait_frames": representative.wait_frames,
                        "source_fr": source_text("fr"),
                        "source_en": source_text("en"),
                        "source_de": source_text("de"),
                        "match_status": match_status,
                        "target_variant_count": len(target_records),
                        "translation": "",
                    }
                )
                row_count += 1
    return group_count, row_count, complete_count, missing_en, missing_de


def export_aligned_csv(
    rbin_path: Path, csv_path: Path, target_language: str = "fr"
) -> Tuple[int, int, int, int, int]:
    return write_aligned_csv(language_ctds_from_rbin(rbin_path), csv_path, target_language)


def align_legacy_csv(
    source_csv_path: Path, output_csv_path: Path, target_language: str = "fr"
) -> Tuple[int, int, int, int, int]:
    return write_aligned_csv(
        language_ctds_from_legacy_csv(source_csv_path), output_csv_path, target_language
    )


def export_csv(
    rbin_path: Path, csv_path: Path, language_filter: Optional[str] = None
) -> Tuple[int, int]:
    archive = parse_rbin(rbin_path)
    ctd_count = 0
    message_count = 0
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for entry in archive.entries:
            if not entry.name.lower().endswith(".ctd"):
                continue
            if entry.compressed:
                raise FormatError(
                    f"Compressed CTD entry is not supported: #{entry.index} {entry.name}"
                )
            ctd = parse_ctd(entry_bytes(archive, entry), f"#{entry.index} {entry.name}")
            decoded_messages = [decode_ctd_text(message.data) for message in ctd.messages]
            language_hint = detect_language(decoded_messages)
            if language_filter and language_hint != language_filter:
                continue
            ctd_count += 1
            for message, decoded_text in zip(ctd.messages, decoded_messages):
                writer.writerow(
                    {
                        "rbin_index": entry.index,
                        "rbin_hash": f"0x{entry.hash_value:08X}",
                        "ctd_name": entry.name,
                        "ctd_occurrence": entry.occurrence,
                        "language_hint": language_hint,
                        "ctd_file_id": f"0x{ctd.file_id:08X}",
                        "message_index": message.index,
                        "message_id": f"0x{message.message_id:08X}",
                        "layout_index": message.layout_index,
                        "wait_frames": message.wait_frames,
                        "source_text": decoded_text,
                        "translation": "",
                    }
                )
                message_count += 1
    return ctd_count, message_count


@dataclass
class CsvTranslation:
    entry_index: int
    message_index: int
    entry_hash: int
    ctd_name: str
    ctd_file_id: int
    message_id: int
    translation: str
    row_number: int


def load_translations(csv_path: Path) -> Dict[Tuple[int, int], CsvTranslation]:
    translations: Dict[Tuple[int, int], CsvTranslation] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = set(reader.fieldnames or [])
        is_legacy = set(CSV_FIELDS).issubset(fieldnames)
        is_aligned = set(ALIGNED_REQUIRED_FIELDS).issubset(fieldnames)
        if not is_legacy and not is_aligned:
            missing_legacy = [field for field in CSV_FIELDS if field not in fieldnames]
            missing_aligned = [
                field for field in ALIGNED_REQUIRED_FIELDS if field not in fieldnames
            ]
            raise FormatError(
                "CSV is neither a legacy export nor an aligned export. "
                f"Missing legacy columns: {', '.join(missing_legacy)}; "
                f"missing aligned columns: {', '.join(missing_aligned)}"
            )

        for row_number, row in enumerate(reader, start=2):
            translation = row["translation"]
            if translation == "":
                continue
            try:
                if is_legacy:
                    items = [
                        CsvTranslation(
                            entry_index=int(row["rbin_index"], 10),
                            message_index=int(row["message_index"], 10),
                            entry_hash=int(row["rbin_hash"], 0),
                            ctd_name=row["ctd_name"],
                            ctd_file_id=int(row["ctd_file_id"], 0),
                            message_id=int(row["message_id"], 0),
                            translation=translation,
                            row_number=row_number,
                        )
                    ]
                else:
                    entry_indices = row["target_rbin_indices"].split("|")
                    entry_hashes = row["target_rbin_hashes"].split("|")
                    message_indices = row["target_message_indices"].split("|")
                    if not entry_indices or any(value == "" for value in entry_indices):
                        raise FormatError(f"Aligned CSV row {row_number} has no target entry")
                    if not (
                        len(entry_indices) == len(entry_hashes) == len(message_indices)
                    ):
                        raise FormatError(
                            f"Aligned CSV row {row_number} has mismatched target lists"
                        )
                    items = [
                        CsvTranslation(
                            entry_index=int(entry_index, 10),
                            message_index=int(message_index, 10),
                            entry_hash=int(entry_hash, 0),
                            ctd_name=row["ctd_name"],
                            ctd_file_id=int(row["ctd_file_id"], 0),
                            message_id=int(row["message_id"], 0),
                            translation=translation,
                            row_number=row_number,
                        )
                        for entry_index, entry_hash, message_index in zip(
                            entry_indices, entry_hashes, message_indices
                        )
                    ]
            except ValueError as exc:
                raise FormatError(f"Invalid numeric field at CSV row {row_number}") from exc

            for item in items:
                key = (item.entry_index, item.message_index)
                if key in translations:
                    raise FormatError(
                        f"Duplicate translation key at CSV row {row_number}: {key}"
                    )
                translations[key] = item
    return translations


def inject_csv(
    rbin_path: Path,
    csv_path: Path,
    output_path: Path,
    turkish_ascii: bool = False,
) -> Tuple[int, int]:
    archive = parse_rbin(rbin_path)
    translations = load_translations(csv_path)
    if not translations:
        if rbin_path.resolve() == output_path.resolve():
            return 0, 0
        shutil.copyfile(rbin_path, output_path)
        return 0, 0

    by_entry: Dict[int, Dict[int, CsvTranslation]] = defaultdict(dict)
    for (entry_index, message_index), item in translations.items():
        by_entry[entry_index][message_index] = item

    unknown_entries = sorted(set(by_entry) - set(range(len(archive.entries))))
    if unknown_entries:
        raise FormatError(f"CSV refers to missing RBIN entries: {unknown_entries}")

    replacement_files: Dict[int, bytes] = {}
    changed_messages = 0
    for entry_index, message_rows in by_entry.items():
        entry = archive.entries[entry_index]
        if entry.compressed:
            raise FormatError(f"Cannot modify compressed entry #{entry.index} {entry.name}")
        if not entry.name.lower().endswith(".ctd"):
            raise FormatError(f"CSV entry #{entry.index} is not CTD: {entry.name}")
        ctd = parse_ctd(entry_bytes(archive, entry), f"#{entry.index} {entry.name}")
        replacements: Dict[int, bytes] = {}
        for message_index, item in message_rows.items():
            if item.entry_hash != entry.hash_value or item.ctd_name != entry.name:
                raise FormatError(f"CSV row {item.row_number} does not match the source RBIN")
            if item.ctd_file_id != ctd.file_id:
                raise FormatError(f"CSV row {item.row_number} has a mismatched CTD file ID")
            if not 0 <= message_index < len(ctd.messages):
                raise FormatError(f"CSV row {item.row_number} has an invalid message index")
            message = ctd.messages[message_index]
            if item.message_id != message.message_id:
                raise FormatError(f"CSV row {item.row_number} has a mismatched message ID")
            text = "" if item.translation == EMPTY_SENTINEL else item.translation
            try:
                replacements[message_index] = encode_ctd_text(text, turkish_ascii)
            except FormatError as exc:
                raise FormatError(f"CSV row {item.row_number}: {exc}") from exc
            changed_messages += 1
        replacement_files[entry_index] = rebuild_ctd(ctd, replacements)

    header = bytearray(archive.raw[: archive.data_offset])
    payload = bytearray()
    current_offset = archive.data_offset
    for entry in archive.entries:
        aligned_offset = align(current_offset)
        if aligned_offset > current_offset:
            payload.extend(b"\0" * (aligned_offset - current_offset))
        current_offset = aligned_offset
        file_data = replacement_files.get(entry.index, entry_bytes(archive, entry))
        info = (entry.info & 0x80000000) | len(file_data)
        struct.pack_into("<I", header, entry.entry_offset + 8, info)
        struct.pack_into("<I", header, entry.entry_offset + 12, current_offset)
        payload.extend(file_data)
        current_offset += len(file_data)

    final_size = align(current_offset)
    if final_size > current_offset:
        payload.extend(b"\0" * (final_size - current_offset))
    output_path.write_bytes(header + payload)
    return len(replacement_files), changed_messages


def analyze(rbin_path: Path) -> None:
    archive = parse_rbin(rbin_path)
    ctd_entries = [entry for entry in archive.entries if entry.name.lower().endswith(".ctd")]
    total_messages = 0
    total_layouts = 0
    invalid: List[str] = []
    for entry in ctd_entries:
        if entry.compressed:
            invalid.append(f"#{entry.index} {entry.name}: compressed")
            continue
        try:
            ctd = parse_ctd(entry_bytes(archive, entry), f"#{entry.index} {entry.name}")
            total_messages += ctd.message_count
            total_layouts += ctd.layout_count
        except FormatError as exc:
            invalid.append(str(exc))
    duplicate_names = Counter(entry.name for entry in archive.entries)
    print(f"File: {rbin_path}")
    print(f"SHA-256: {sha256(rbin_path)}")
    print(f"RBIN version: {archive.version}")
    print(f"Mount point: {archive.mount_point}")
    print(f"Entries: {len(archive.entries)}")
    print(f"Compressed entries: {sum(entry.compressed for entry in archive.entries)}")
    print(f"CTD entries: {len(ctd_entries)}")
    print(f"Messages: {total_messages}")
    print(f"Layouts: {total_layouts}")
    print(f"Repeated filenames: {sum(count > 1 for count in duplicate_names.values())}")
    if invalid:
        print("Warnings:")
        for warning in invalid:
            print(f"  - {warning}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export/import Kingdom Hearts 3D message.rbin CTD text"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="show archive statistics")
    analyze_parser.add_argument("rbin", type=Path)

    export_parser = subparsers.add_parser("export", help="export all CTD messages to CSV")
    export_parser.add_argument("rbin", type=Path)
    export_parser.add_argument("csv", type=Path)
    export_parser.add_argument(
        "--language",
        choices=("fr", "en", "de", "ja", "unknown"),
        help="export only CTDs heuristically identified as this source language",
    )

    aligned_parser = subparsers.add_parser(
        "export-aligned", help="export French, English, and German text side by side"
    )
    aligned_parser.add_argument("rbin", type=Path)
    aligned_parser.add_argument("csv", type=Path)
    aligned_parser.add_argument(
        "--target-language",
        choices=TRANSLATION_LANGUAGES,
        default="fr",
        help="language slot that receives the Turkish translation (default: fr)",
    )

    align_parser = subparsers.add_parser(
        "align", help="convert an existing all-language export to aligned CSV"
    )
    align_parser.add_argument("source_csv", type=Path)
    align_parser.add_argument("output_csv", type=Path)
    align_parser.add_argument(
        "--target-language",
        choices=TRANSLATION_LANGUAGES,
        default="fr",
        help="language slot that receives the Turkish translation (default: fr)",
    )

    inject_parser = subparsers.add_parser("inject", help="inject CSV translations into a new RBIN")
    inject_parser.add_argument("rbin", type=Path)
    inject_parser.add_argument("csv", type=Path)
    inject_parser.add_argument("output", type=Path)
    inject_parser.add_argument(
        "--turkish-ascii",
        action="store_true",
        help="replace ğ/Ğ ş/Ş ı/İ with ASCII g/G s/S i/I",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            analyze(args.rbin)
        elif args.command == "export":
            ctd_count, message_count = export_csv(args.rbin, args.csv, args.language)
            print(f"Exported {message_count} messages from {ctd_count} CTD files to {args.csv}")
        elif args.command == "export-aligned":
            groups, rows, complete, missing_en, missing_de = export_aligned_csv(
                args.rbin, args.csv, args.target_language
            )
            print(
                f"Exported {rows} aligned messages from {groups} CTD groups to {args.csv} "
                f"({complete} complete, {missing_en} missing EN, {missing_de} missing DE)"
            )
        elif args.command == "align":
            groups, rows, complete, missing_en, missing_de = align_legacy_csv(
                args.source_csv, args.output_csv, args.target_language
            )
            print(
                f"Aligned {rows} messages from {groups} CTD groups to {args.output_csv} "
                f"({complete} complete, {missing_en} missing EN, {missing_de} missing DE)"
            )
        elif args.command == "inject":
            file_count, message_count = inject_csv(
                args.rbin, args.csv, args.output, args.turkish_ascii
            )
            print(
                f"Injected {message_count} translations into {file_count} CTD files: "
                f"{args.output}"
            )
    except (OSError, FormatError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
