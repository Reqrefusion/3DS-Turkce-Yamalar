#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fire Emblem Awakening (3DS) message .bin.lz extractor/injector.

- Nintendo LZ11 decompress/compress
- Parses the game's MESS_ARCHIVE message format
- Extracts F/G/I/S/U strings side-by-side to one UTF-8 CSV per game file
- Can import an older Turkish U patch into the TR columns
- Injects a chosen CSV column (e.g. TR) into a chosen language slot (e.g. U)

No third-party Python packages are required.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import struct
import sys
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

LANGS = ("F", "G", "I", "S", "U")
LANG_NAMES = {
    "F": "French",
    "G": "German",
    "I": "Italian",
    "S": "Spanish",
    "U": "English",
}
CSV_COLUMNS = ["index", "key", "F", "G", "I", "S", "U", "TR"]


class ToolError(Exception):
    pass


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _align4(buf: bytearray) -> None:
    while len(buf) & 3:
        buf.append(0)


def decode_hash_u_name(name: str) -> str:
    """Turn names like #U30a2#U30ba... into readable Unicode for display only."""
    def repl(m: re.Match[str]) -> str:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return m.group(0)
    return re.sub(r"#U([0-9A-Fa-f]{4,6})", repl, name)


# ----------------------------- LZ11 ---------------------------------

def lz11_decompress(data: bytes) -> bytes:
    if len(data) < 4 or data[0] != 0x11:
        raise ToolError("Dosya Nintendo LZ11 (0x11) değil.")

    out_size = data[1] | (data[2] << 8) | (data[3] << 16)
    pos = 4
    if out_size == 0:
        if len(data) < 8:
            raise ToolError("Bozuk LZ11 başlığı.")
        out_size = int.from_bytes(data[4:8], "little")
        pos = 8

    out = bytearray()
    n = len(data)

    while len(out) < out_size:
        if pos >= n:
            raise ToolError("LZ11 akışı beklenmeden bitti.")
        flags = data[pos]
        pos += 1

        for bit in range(7, -1, -1):
            if len(out) >= out_size:
                break

            if not (flags & (1 << bit)):
                if pos >= n:
                    raise ToolError("LZ11 literal verisi eksik.")
                out.append(data[pos])
                pos += 1
                continue

            if pos >= n:
                raise ToolError("LZ11 eşleşme verisi eksik.")
            b1 = data[pos]
            pos += 1
            indicator = b1 >> 4

            if indicator == 0:
                if pos + 2 > n:
                    raise ToolError("LZ11 kısa eşleşme verisi eksik.")
                b2, b3 = data[pos], data[pos + 1]
                pos += 2
                length = (((b1 & 0x0F) << 4) | (b2 >> 4)) + 0x11
                disp = (((b2 & 0x0F) << 8) | b3) + 1
            elif indicator == 1:
                if pos + 3 > n:
                    raise ToolError("LZ11 uzun eşleşme verisi eksik.")
                b2, b3, b4 = data[pos], data[pos + 1], data[pos + 2]
                pos += 3
                length = (((b1 & 0x0F) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                disp = (((b3 & 0x0F) << 8) | b4) + 1
            else:
                if pos >= n:
                    raise ToolError("LZ11 eşleşme verisi eksik.")
                b2 = data[pos]
                pos += 1
                length = indicator + 1
                disp = (((b1 & 0x0F) << 8) | b2) + 1

            if disp <= 0 or disp > len(out):
                raise ToolError(f"Geçersiz LZ11 geri uzaklığı: {disp}")

            for _ in range(length):
                out.append(out[-disp])
                if len(out) >= out_size:
                    break

    return bytes(out)


def lz11_compress(data: bytes, max_candidates: int = 64) -> bytes:
    """Greedy LZ11 compressor, optimized for correctness and reasonable speed."""
    size = len(data)
    if size <= 0xFFFFFF:
        out = bytearray(b"\x11" + size.to_bytes(3, "little"))
    else:
        out = bytearray(b"\x11\x00\x00\x00" + size.to_bytes(4, "little"))

    history: Dict[bytes, deque[int]] = defaultdict(deque)
    pos = 0

    def add_history(i: int) -> None:
        if i + 2 >= size:
            return
        key = data[i:i + 3]
        q = history[key]
        q.append(i)
        min_pos = i - 0x1000
        while q and q[0] < min_pos:
            q.popleft()
        # Keep memory bounded for pathological repetitive files.
        while len(q) > 256:
            q.popleft()

    while pos < size:
        flag_pos = len(out)
        out.append(0)
        flags = 0

        for token in range(8):
            if pos >= size:
                break

            best_len = 0
            best_disp = 0

            if pos + 2 < size:
                key = data[pos:pos + 3]
                q = history.get(key)
                if q:
                    min_pos = max(0, pos - 0x1000)
                    checked = 0
                    max_len = min(0x10110, size - pos)

                    for cand in reversed(q):
                        if cand < min_pos:
                            break
                        disp = pos - cand
                        if not (1 <= disp <= 0x1000):
                            continue

                        checked += 1
                        length = 3
                        # Overlap is valid in LZ11, therefore compare against
                        # already-known source positions using displacement.
                        while length < max_len and data[pos + length] == data[pos + length - disp]:
                            length += 1

                        if length > best_len:
                            best_len = length
                            best_disp = disp
                            if length == max_len:
                                break
                        if checked >= max_candidates:
                            break

            if best_len >= 3:
                flags |= 1 << (7 - token)
                disp_code = best_disp - 1
                length = best_len

                if length <= 0x10:
                    out.append(((length - 1) << 4) | ((disp_code >> 8) & 0x0F))
                    out.append(disp_code & 0xFF)
                elif length <= 0x110:
                    x = length - 0x11
                    out.append((x >> 4) & 0x0F)
                    out.append(((x & 0x0F) << 4) | ((disp_code >> 8) & 0x0F))
                    out.append(disp_code & 0xFF)
                else:
                    x = length - 0x111
                    out.append(0x10 | ((x >> 12) & 0x0F))
                    out.append((x >> 4) & 0xFF)
                    out.append(((x & 0x0F) << 4) | ((disp_code >> 8) & 0x0F))
                    out.append(disp_code & 0xFF)

                start = pos
                pos += length
                for i in range(start, pos):
                    add_history(i)
            else:
                out.append(data[pos])
                add_history(pos)
                pos += 1

        out[flag_pos] = flags

    return bytes(out)


# ------------------------- Message archive ---------------------------

@dataclass
class MessageArchive:
    raw: bytes
    header: bytes
    text_section_size: int
    count: int
    value_offsets: List[int]
    key_offsets: List[int]
    text_prefix: bytes
    key_block: bytes
    values: List[str]
    keys: List[str]
    key_raw: List[bytes]


def _read_utf16z(data: bytes, pos: int, end_limit: int) -> str:
    end = pos
    while end + 1 < end_limit:
        if data[end:end + 2] == b"\x00\x00":
            try:
                return data[pos:end].decode("utf-16le")
            except UnicodeDecodeError as e:
                raise ToolError(f"UTF-16LE metin çözülemedi (0x{pos:X}): {e}") from e
        end += 2
    raise ToolError(f"UTF-16LE sonlandırıcı bulunamadı (0x{pos:X}).")


def parse_message_archive(raw: bytes) -> MessageArchive:
    if len(raw) < 0x20:
        raise ToolError("Mesaj arşivi çok küçük.")

    total_size, text_size, _unknown, count = struct.unpack_from("<4I", raw, 0)
    if total_size != len(raw):
        raise ToolError(f"İç boyut uyuşmuyor: header={total_size}, gerçek={len(raw)}")

    table_start = 0x20 + text_size
    table_end = table_start + count * 8
    if not (0x20 <= table_start <= table_end <= len(raw)):
        raise ToolError("Mesaj offset tablosu dosya sınırlarının dışında.")

    value_offsets: List[int] = []
    key_offsets: List[int] = []
    for i in range(count):
        vo, ko = struct.unpack_from("<II", raw, table_start + i * 8)
        value_offsets.append(vo)
        key_offsets.append(ko)

    first_value_offset = value_offsets[0] if count else text_size
    if first_value_offset > text_size:
        raise ToolError("İlk metin offset'i metin bölümünün dışında.")

    key_base = table_end
    text_prefix = raw[0x20:0x20 + first_value_offset]
    key_block = raw[key_base:]

    values: List[str] = []
    keys: List[str] = []
    key_raw: List[bytes] = []

    for i in range(count):
        value_pos = 0x20 + value_offsets[i]
        if not (0x20 <= value_pos < table_start):
            raise ToolError(f"#{i} metin offset'i geçersiz.")
        values.append(_read_utf16z(raw, value_pos, table_start))

        key_pos = key_base + key_offsets[i]
        if not (key_base <= key_pos < len(raw)):
            raise ToolError(f"#{i} anahtar offset'i geçersiz.")
        key_end = raw.find(b"\x00", key_pos)
        if key_end < 0:
            raise ToolError(f"#{i} anahtar sonlandırıcısı bulunamadı.")
        kb = raw[key_pos:key_end]
        key_raw.append(kb)
        try:
            keys.append(kb.decode("cp932"))
        except UnicodeDecodeError:
            # Display-only fallback; injection never depends on re-encoding the key.
            keys.append(kb.decode("cp932", errors="backslashreplace"))

    return MessageArchive(
        raw=raw,
        header=raw[:0x20],
        text_section_size=text_size,
        count=count,
        value_offsets=value_offsets,
        key_offsets=key_offsets,
        text_prefix=text_prefix,
        key_block=key_block,
        values=values,
        keys=keys,
        key_raw=key_raw,
    )


def rebuild_message_archive(template: MessageArchive, values: List[str]) -> bytes:
    if len(values) != template.count:
        raise ToolError(f"Metin sayısı uyuşmuyor: {len(values)} != {template.count}")

    text = bytearray(template.text_prefix)
    new_value_offsets: List[int] = []

    for i, value in enumerate(values):
        if "\x00" in value:
            raise ToolError(f"#{i} metninde NUL (U+0000) karakteri var; desteklenmiyor.")
        new_value_offsets.append(len(text))
        text.extend(value.encode("utf-16le"))
        text.extend(b"\x00\x00")
        _align4(text)

    header = bytearray(template.header)
    struct.pack_into("<I", header, 4, len(text))

    table = bytearray()
    for vo, ko in zip(new_value_offsets, template.key_offsets):
        table.extend(struct.pack("<II", vo, ko))

    rebuilt = bytearray(header)
    rebuilt.extend(text)
    rebuilt.extend(table)
    rebuilt.extend(template.key_block)
    struct.pack_into("<I", rebuilt, 0, len(rebuilt))
    return bytes(rebuilt)


# ---------------------------- Sources --------------------------------

class SourceBase:
    root_prefix: str

    def list_files(self) -> List[str]:
        raise NotImplementedError

    def read(self, lang: str, rel: str) -> bytes:
        raise NotImplementedError


class ZipSource(SourceBase):
    def __init__(self, path: Path):
        self.path = path
        self.zf = zipfile.ZipFile(path, "r")
        self.root_prefix = self._detect_root()

    def _detect_root(self) -> str:
        names = [n for n in self.zf.namelist() if not n.endswith("/")]
        candidates: Dict[str, set[str]] = defaultdict(set)
        for n in names:
            pp = PurePosixPath(n)
            parts = pp.parts
            for idx, part in enumerate(parts[:-1]):
                if part in LANGS:
                    root = "/".join(parts[:idx])
                    candidates[root].add(part)
        valid = [root for root, langs in candidates.items() if set(LANGS).issubset(langs)]
        if not valid:
            raise ToolError("ZIP içinde F/G/I/S/U dil klasörleri bulunamadı.")
        # Prefer the deepest/specific root, then shortest textual representation.
        valid.sort(key=lambda x: (-len(PurePosixPath(x).parts), len(x)))
        return valid[0]

    def _name(self, lang: str, rel: str) -> str:
        return "/".join(x for x in (self.root_prefix, lang, rel) if x)

    def list_files(self) -> List[str]:
        sets = []
        for lang in LANGS:
            prefix = self._name(lang, "")
            if prefix and not prefix.endswith("/"):
                prefix += "/"
            s = set()
            for n in self.zf.namelist():
                if n.endswith("/") or not n.startswith(prefix):
                    continue
                rel = n[len(prefix):]
                if rel.lower().endswith(".bin.lz"):
                    s.add(rel)
            sets.append(s)
        common = set.intersection(*sets)
        union = set.union(*sets)
        if common != union:
            missing = {lang: len(union - sets[i]) for i, lang in enumerate(LANGS)}
            raise ToolError(f"Dil klasörlerinde dosya listeleri aynı değil: {missing}")
        return sorted(common)

    def read(self, lang: str, rel: str) -> bytes:
        return self.zf.read(self._name(lang, rel))

    def close(self) -> None:
        self.zf.close()


class DirSource(SourceBase):
    def __init__(self, path: Path):
        self.input_path = path
        self.base = self._detect_base(path)
        self.root_prefix = ""

    @staticmethod
    def _has_langs(p: Path) -> bool:
        return all((p / l).is_dir() for l in LANGS)

    def _detect_base(self, path: Path) -> Path:
        if self._has_langs(path):
            return path
        children = [p for p in path.iterdir() if p.is_dir()] if path.is_dir() else []
        valid = [p for p in children if self._has_langs(p)]
        if len(valid) == 1:
            return valid[0]
        raise ToolError("Klasör içinde F/G/I/S/U dil klasörleri bulunamadı.")

    def list_files(self) -> List[str]:
        sets = []
        for lang in LANGS:
            root = self.base / lang
            s = {p.relative_to(root).as_posix() for p in root.rglob("*.bin.lz") if p.is_file()}
            sets.append(s)
        common = set.intersection(*sets)
        union = set.union(*sets)
        if common != union:
            missing = {lang: len(union - sets[i]) for i, lang in enumerate(LANGS)}
            raise ToolError(f"Dil klasörlerinde dosya listeleri aynı değil: {missing}")
        return sorted(common)

    def read(self, lang: str, rel: str) -> bytes:
        return (self.base / lang / Path(rel)).read_bytes()

    def close(self) -> None:
        pass


def open_source(path: Path) -> SourceBase:
    if path.is_file() and path.suffix.lower() == ".zip":
        return ZipSource(path)
    if path.is_dir():
        return DirSource(path)
    raise ToolError("Kaynak ZIP veya klasör bulunamadı.")


def parse_lz_message(blob: bytes) -> MessageArchive:
    return parse_message_archive(lz11_decompress(blob))


def parse_any_message_blob(blob: bytes) -> MessageArchive:
    """Parse normal LZ11, FE 0x13+LZ11 wrapped, or already-decompressed archives."""
    if blob and blob[0] == 0x11:
        return parse_message_archive(lz11_decompress(blob))
    if len(blob) >= 8 and blob[0] == 0x13 and blob[4] == 0x11:
        return parse_message_archive(lz11_decompress(blob[4:]))
    return parse_message_archive(blob)


def csv_rel_for_game_file(rel: str) -> str:
    """Example: sub/Menu.bin.lz -> sub/Menu.csv"""
    low = rel.lower()
    if low.endswith(".bin.lz"):
        return rel[:-7] + ".csv"
    return rel + ".csv"


class TurkishPatchSource:
    """Read a Turkish patch that contains only the U language tree."""
    def __init__(self, path: Path):
        self.path = path
        self.zf: Optional[zipfile.ZipFile] = None
        self.base: Optional[Path] = None
        self.names: Dict[str, str] = {}

        if path.is_file() and path.suffix.lower() == ".zip":
            self.zf = zipfile.ZipFile(path, "r")
            self._index_zip()
        elif path.is_dir():
            self._index_dir()
        else:
            raise ToolError("Türkçe yama ZIP veya klasör bulunamadı.")

    def _index_zip(self) -> None:
        assert self.zf is not None
        candidates: Dict[str, Dict[str, str]] = defaultdict(dict)
        for n in self.zf.namelist():
            if n.endswith("/") or not n.lower().endswith(".bin.lz"):
                continue
            parts = PurePosixPath(n).parts
            for idx, part in enumerate(parts[:-1]):
                if part == "U":
                    root = "/".join(parts[:idx + 1])
                    rel = "/".join(parts[idx + 1:])
                    candidates[root][rel] = n
        if not candidates:
            raise ToolError("Türkçe yama ZIP'inde U klasörü bulunamadı.")
        root, mapping = max(candidates.items(), key=lambda kv: len(kv[1]))
        self.names = mapping

    def _index_dir(self) -> None:
        path = self.path
        possible: List[Path] = []
        if path.name == "U" and path.is_dir():
            possible.append(path)
        if (path / "U").is_dir():
            possible.append(path / "U")
        if path.is_dir():
            for child in path.iterdir():
                if child.is_dir() and (child / "U").is_dir():
                    possible.append(child / "U")
        if not possible:
            raise ToolError("Türkçe yama klasöründe U klasörü bulunamadı.")
        self.base = max(possible, key=lambda x: sum(1 for _ in x.rglob("*.bin.lz")))
        self.names = {p.relative_to(self.base).as_posix(): str(p) for p in self.base.rglob("*.bin.lz") if p.is_file()}

    def has(self, rel: str) -> bool:
        return rel in self.names

    def read(self, rel: str) -> bytes:
        name = self.names[rel]
        if self.zf is not None:
            return self.zf.read(name)
        return Path(name).read_bytes()

    def close(self) -> None:
        if self.zf is not None:
            self.zf.close()


def align_patch_values(base: MessageArchive, patch: MessageArchive) -> Tuple[List[str], int]:
    """Align patch text by raw message key, preserving duplicate-key occurrence order."""
    by_key: Dict[bytes, deque[str]] = defaultdict(deque)
    for key, value in zip(patch.key_raw, patch.values):
        by_key[key].append(value)
    out: List[str] = []
    matched = 0
    for key in base.key_raw:
        q = by_key.get(key)
        if q:
            out.append(q.popleft())
            matched += 1
        else:
            out.append("")
    return out, matched


# ----------------------------- Extract --------------------------------

def command_extract(args: argparse.Namespace) -> int:
    src_path = Path(args.source)
    out_dir = Path(args.output)
    csv_root = out_dir / "csv"
    csv_root.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"

    source = open_source(src_path)
    tr_patch = TurkishPatchSource(Path(args.tr_patch)) if args.tr_patch else None
    try:
        files = source.list_files()
        rows = 0
        tr_rows = 0
        tr_files = 0
        file_meta = []

        for file_no, rel in enumerate(files, 1):
            parsed: Dict[str, MessageArchive] = {}
            for lang in LANGS:
                parsed[lang] = parse_any_message_blob(source.read(lang, rel))

            counts = {parsed[l].count for l in LANGS}
            if len(counts) != 1:
                raise ToolError(f"{rel}: diller arasında kayıt sayısı farklı.")

            count = parsed["U"].count
            base_keys = parsed["U"].key_raw
            for lang in LANGS:
                if parsed[lang].key_raw != base_keys:
                    raise ToolError(f"{rel}: {lang} anahtar sırası diğer dillerle uyuşmuyor.")

            tr_values = [""] * count
            tr_source_records = 0
            if tr_patch is not None and tr_patch.has(rel):
                patch_archive = parse_any_message_blob(tr_patch.read(rel))
                tr_values, tr_source_records = align_patch_values(parsed["U"], patch_archive)
                tr_rows += tr_source_records
                tr_files += 1

            csv_rel = csv_rel_for_game_file(rel)
            csv_path = csv_root / Path(csv_rel)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                for i in range(count):
                    writer.writerow({
                        "index": i,
                        "key": parsed["U"].keys[i],
                        "F": parsed["F"].values[i],
                        "G": parsed["G"].values[i],
                        "I": parsed["I"].values[i],
                        "S": parsed["S"].values[i],
                        "U": parsed["U"].values[i],
                        "TR": tr_values[i],
                    })
                    rows += 1

            file_meta.append({
                "file": rel,
                "display_file": decode_hash_u_name(rel),
                "csv": "csv/" + PurePosixPath(csv_rel).as_posix(),
                "records": count,
                "tr_imported": tr_source_records,
            })
            if args.verbose and (file_no % 50 == 0 or file_no == len(files)):
                print(f"[extract] {file_no}/{len(files)} dosya, {rows} satır")

        manifest = {
            "tool": "fea_lang_tool",
            "format_version": 2,
            "csv_mode": "per_file",
            "source": src_path.name,
            "root_prefix": getattr(source, "root_prefix", ""),
            "languages": LANG_NAMES,
            "file_count": len(files),
            "row_count": rows,
            "csv_root": "csv",
            "turkish_patch": Path(args.tr_patch).name if args.tr_patch else None,
            "turkish_file_count": tr_files if tr_patch is not None else 0,
            "turkish_row_count": tr_rows if tr_patch is not None else 0,
            "files": file_meta,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"Tamam: {len(files)} dosya / {rows} metin ayrı CSV'lere çıkarıldı.")
        print(f"CSV klasörü: {csv_root}")
        if tr_patch is not None:
            print(f"Eski Türkçe yamadan: {tr_files} dosya / {tr_rows} kayıt TR sütununa aktarıldı.")
        print("TR sütunlarını düzenle. index/key sütunlarını değiştirme.")
        return 0
    finally:
        source.close()
        if tr_patch is not None:
            tr_patch.close()


# ----------------------------- Inject ---------------------------------

def load_translation_csv(path: Path, column: str) -> Tuple[Dict[Tuple[str, int], Dict[str, str]], List[str]]:
    """Legacy v1 single-CSV loader."""
    rows: Dict[Tuple[str, int], Dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if not reader.fieldnames:
            raise ToolError("CSV başlığı yok.")
        fields = reader.fieldnames
        required = {"file", "index", "key", column}
        missing = required - set(fields)
        if missing:
            raise ToolError(f"CSV sütunları eksik: {', '.join(sorted(missing))}")

        for line_no, row in enumerate(reader, 2):
            rel = row.get("file", "")
            try:
                idx = int(row.get("index", ""))
            except ValueError as e:
                raise ToolError(f"CSV satır {line_no}: index sayı değil.") from e
            k = (rel, idx)
            if k in rows:
                raise ToolError(f"CSV'de yinelenen kayıt: {rel} #{idx}")
            rows[k] = row
    return rows, fields


def load_translation_project(path: Path, column: str) -> Tuple[Dict[Tuple[str, int], Dict[str, str]], List[str]]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ToolError("Proje klasöründe manifest.json bulunamadı.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ToolError(f"manifest.json okunamadı: {e}") from e
    if manifest.get("format_version") != 2 or manifest.get("csv_mode") != "per_file":
        raise ToolError("Bu proje ayrı-CSV formatında değil (format_version 2 bekleniyor).")

    rows: Dict[Tuple[str, int], Dict[str, str]] = {}
    common_fields: Optional[List[str]] = None
    for meta in manifest.get("files", []):
        rel = meta.get("file", "")
        csv_rel = meta.get("csv", "")
        if not rel or not csv_rel:
            raise ToolError("Manifest dosya kaydı eksik.")
        csv_path = path / Path(csv_rel)
        if not csv_path.is_file():
            raise ToolError(f"CSV bulunamadı: {csv_rel}")
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            if not reader.fieldnames:
                raise ToolError(f"CSV başlığı yok: {csv_rel}")
            fields = reader.fieldnames
            required = {"index", "key", column}
            missing = required - set(fields)
            if missing:
                raise ToolError(f"{csv_rel}: CSV sütunları eksik: {', '.join(sorted(missing))}")
            if common_fields is None:
                common_fields = list(fields)
            for line_no, row in enumerate(reader, 2):
                try:
                    idx = int(row.get("index", ""))
                except ValueError as e:
                    raise ToolError(f"{csv_rel} satır {line_no}: index sayı değil.") from e
                k = (rel, idx)
                if k in rows:
                    raise ToolError(f"Projede yinelenen kayıt: {rel} #{idx}")
                rows[k] = row
    return rows, common_fields or []


def load_translation_input(path: Path, column: str) -> Tuple[Dict[Tuple[str, int], Dict[str, str]], List[str]]:
    if path.is_dir():
        return load_translation_project(path, column)
    if path.is_file() and path.suffix.lower() == ".csv":
        return load_translation_csv(path, column)
    raise ToolError("Çeviri girdisi proje klasörü veya eski tek CSV olmalı.")


def build_patched_blob(
    original_blob: bytes,
    rel: str,
    csv_rows: Dict[Tuple[str, int], Dict[str, str]],
    column: str,
    fallback_column: str,
    blank_is_empty: bool,
) -> Tuple[bytes, int]:
    archive = parse_lz_message(original_blob)
    new_values = list(archive.values)
    changed = 0

    for i in range(archive.count):
        row = csv_rows.get((rel, i))
        if row is None:
            raise ToolError(f"CSV kaydı eksik: {rel} #{i}")

        csv_key = row.get("key", "")
        if csv_key and csv_key != archive.keys[i]:
            raise ToolError(f"Anahtar uyuşmuyor: {rel} #{i}\nCSV: {csv_key}\nDosya: {archive.keys[i]}")

        value = row.get(column, "")
        if value == "" and not blank_is_empty:
            if fallback_column in row:
                value = row.get(fallback_column, "")
            else:
                value = archive.values[i]

        if value != archive.values[i]:
            new_values[i] = value
            changed += 1

    if changed == 0:
        return original_blob, 0

    rebuilt = rebuild_message_archive(archive, new_values)
    # Internal round-trip sanity check before compression.
    check = parse_message_archive(rebuilt)
    if check.values != new_values or check.key_raw != archive.key_raw:
        raise ToolError(f"İç doğrulama başarısız: {rel}")

    packed = lz11_compress(rebuilt)
    if lz11_decompress(packed) != rebuilt:
        raise ToolError(f"LZ11 doğrulama başarısız: {rel}")
    return packed, changed


def clone_zipinfo(info: zipfile.ZipInfo) -> zipfile.ZipInfo:
    zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    zi.compress_type = info.compress_type
    zi.comment = info.comment
    zi.extra = info.extra
    zi.internal_attr = info.internal_attr
    zi.external_attr = info.external_attr
    zi.create_system = info.create_system
    zi.create_version = info.create_version
    zi.extract_version = info.extract_version
    zi.flag_bits = info.flag_bits
    return zi


def inject_zip(
    source_path: Path,
    out_path: Path,
    target: str,
    csv_rows: Dict[Tuple[str, int], Dict[str, str]],
    column: str,
    fallback: str,
    blank_is_empty: bool,
    verbose: bool,
) -> Tuple[int, int]:
    source = ZipSource(source_path)
    files = source.list_files()
    target_names = {source._name(target, rel): rel for rel in files}
    changed_files = 0
    changed_strings = 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_path, "r") as zin, zipfile.ZipFile(out_path, "w") as zout:
        for idx, info in enumerate(zin.infolist(), 1):
            data = zin.read(info.filename) if not info.is_dir() else b""
            rel = target_names.get(info.filename)
            if rel is not None:
                patched, c = build_patched_blob(data, rel, csv_rows, column, fallback, blank_is_empty)
                data = patched
                if c:
                    changed_files += 1
                    changed_strings += c
            zout.writestr(clone_zipinfo(info), data)
            if verbose and idx % 500 == 0:
                print(f"[inject] ZIP {idx}/{len(zin.infolist())}")

    source.close()
    return changed_files, changed_strings


def inject_dir(
    source_path: Path,
    out_path: Path,
    target: str,
    csv_rows: Dict[Tuple[str, int], Dict[str, str]],
    column: str,
    fallback: str,
    blank_is_empty: bool,
    verbose: bool,
) -> Tuple[int, int]:
    source = DirSource(source_path)
    files = source.list_files()
    if out_path.exists():
        if out_path.resolve() == source_path.resolve():
            raise ToolError("Çıktı klasörü kaynak klasörle aynı olamaz.")
        shutil.rmtree(out_path)
    shutil.copytree(source_path, out_path)

    # Mirror the detected language base relative to source_path.
    base_rel = source.base.relative_to(source_path)
    out_base = out_path / base_rel

    changed_files = 0
    changed_strings = 0
    for no, rel in enumerate(files, 1):
        src_file = source.base / target / Path(rel)
        out_file = out_base / target / Path(rel)
        original = src_file.read_bytes()
        patched, c = build_patched_blob(original, rel, csv_rows, column, fallback, blank_is_empty)
        if c:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(patched)
            changed_files += 1
            changed_strings += c
        if verbose and (no % 50 == 0 or no == len(files)):
            print(f"[inject] {no}/{len(files)} dosya")

    source.close()
    return changed_files, changed_strings


def command_inject(args: argparse.Namespace) -> int:
    source_path = Path(args.source)
    translations_path = Path(args.translations)
    out_path = Path(args.output)
    target = args.target.upper()
    column = args.column
    fallback = args.fallback

    if target not in LANGS:
        raise ToolError(f"Geçersiz hedef dil slotu: {target}. Seçenekler: {', '.join(LANGS)}")
    rows, fields = load_translation_input(translations_path, column)
    if fallback not in fields:
        raise ToolError(f"Fallback sütunu CSV'de yok: {fallback}")

    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        if out_path.suffix.lower() != ".zip":
            raise ToolError("ZIP kaynak için çıktı .zip olmalı.")
        changed_files, changed_strings = inject_zip(
            source_path, out_path, target, rows, column, fallback, args.blank_is_empty, args.verbose
        )
    elif source_path.is_dir():
        changed_files, changed_strings = inject_dir(
            source_path, out_path, target, rows, column, fallback, args.blank_is_empty, args.verbose
        )
    else:
        raise ToolError("Kaynak ZIP veya klasör bulunamadı.")

    print(f"Tamam: {changed_strings} metin / {changed_files} dosya değiştirildi.")
    print(f"Hedef slot: {target} ({LANG_NAMES[target]})")
    print(f"Çıktı: {out_path}")
    return 0


# ------------------------------ Verify --------------------------------

def command_verify(args: argparse.Namespace) -> int:
    src = open_source(Path(args.source))
    try:
        files = src.list_files()
        total_records = 0
        for no, rel in enumerate(files, 1):
            parsed = {lang: parse_lz_message(src.read(lang, rel)) for lang in LANGS}
            counts = {x.count for x in parsed.values()}
            if len(counts) != 1:
                raise ToolError(f"{rel}: kayıt sayıları uyuşmuyor.")
            base_keys = parsed["U"].key_raw
            if any(parsed[l].key_raw != base_keys for l in LANGS):
                raise ToolError(f"{rel}: anahtarlar diller arasında uyuşmuyor.")
            total_records += parsed["U"].count
            if args.verbose and (no % 50 == 0 or no == len(files)):
                print(f"[verify] {no}/{len(files)}")
        print(f"Doğrulama başarılı: {len(files)} dosya / {total_records} kayıt.")
        return 0
    finally:
        src.close()


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="fea_lang_tool.py",
        description="Fire Emblem Awakening 3DS .bin.lz çok-dilli metin çıkarma/enjekte aracı",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="F/G/I/S/U metinlerini dosya başına ayrı CSV'lere çıkar")
    e.add_argument("source", help="m.zip veya F/G/I/S/U içeren klasör")
    e.add_argument("output", help="Proje çıktı klasörü")
    e.add_argument("--tr-patch", help="Eski Türkçe yama ZIP/klasörü; U metinlerini TR sütunlarına aktarır")
    e.add_argument("-v", "--verbose", action="store_true", help="İlerlemeyi göster")
    e.set_defaults(func=command_extract)

    i = sub.add_parser("inject", help="Projedeki ayrı CSV'leri seçilen dil slotuna enjekte et")
    i.add_argument("source", help="Orijinal m.zip veya F/G/I/S/U içeren klasör")
    i.add_argument("translations", help="extract ile oluşan proje klasörü (veya eski translations.csv)")
    i.add_argument("--target", default="U", help="Yazılacak oyun dil slotu: F/G/I/S/U (varsayılan U)")
    i.add_argument("--column", default="TR", help="Enjekte edilecek CSV sütunu (varsayılan TR)")
    i.add_argument("--fallback", default="U", help="Çeviri boşsa kullanılacak CSV sütunu (varsayılan U)")
    i.add_argument("--blank-is-empty", action="store_true", help="Boş hücreyi fallback yerine gerçekten boş metin olarak yaz")
    i.add_argument("--output", "-o", required=True, help="Çıktı .zip veya klasör")
    i.add_argument("-v", "--verbose", action="store_true", help="İlerlemeyi göster")
    i.set_defaults(func=command_inject)

    v = sub.add_parser("verify", help="Kaynak dil dosyalarını ve eşleşmeleri doğrula")
    v.add_argument("source", help="m.zip veya F/G/I/S/U içeren klasör")
    v.add_argument("-v", "--verbose", action="store_true", help="İlerlemeyi göster")
    v.set_defaults(func=command_verify)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ToolError, zipfile.BadZipFile, OSError) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
