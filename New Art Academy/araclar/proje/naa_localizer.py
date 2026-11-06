#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""New Art Academy (3DS) STB localization helper.

Supports the STBL 1.1 UTF-8/string-character-offset format used by most game
text and the older STBL 1.0 single-byte format used by materialslibrary.

This tool does not modify the original ROM/ZIP. It creates replacement files
with the same RomFS paths so they can be used as a LayeredFS patch.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import zipfile

try:
    from font_tool import build_font_patch_from_reader, CFNAError
except ImportError:
    build_font_patch_from_reader = None
    class CFNAError(Exception):
        pass

MAGIC = b"STBL"
TEXT_TAG_RE = re.compile(r"\[[^\]]*\]")
PRINTF_RE = re.compile(r"%(?:[-+0 #]*\d*(?:\.\d+)?)?[A-Za-z%]")
LANG_IMAGE_RE = re.compile(r"(^|[-_])(en|eng|english)([-_.]|$)", re.I)
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif", ".mpo"}
EXTRA_TEXT_FILES = ["common/credits.txt", "common/credits/credits.txt"]
EXTRA_IMAGE_FILES = ["bitmaps/frontend/new.png"]  # contains the visible word NEW

# RomFS suffix -> translation table column/display name.
REFERENCE_LANGS = [
    ("en", "source_en", "English"),
    ("fr", "source_fr", "Français"),
    ("ge", "source_de", "Deutsch"),
    ("sp", "source_es", "Español"),
    ("it", "source_it", "Italiano"),
    ("du", "source_nl", "Nederlands"),
    ("po", "source_pt", "Português"),
    ("ru", "source_ru", "Русский"),
]

# STBL 1.0 uses a Western single-byte encoding. For real Turkish glyphs,
# fontmap mode encodes six Turkish-only letters through unused CP1252
# placeholders. font_tool.py repoints those placeholder code points to the
# native Turkish glyphs already present in the game's two main CFNA fonts.
TR_FONTMAP_ENCODE = str.maketrans({
    "Ğ": "Ð", "ğ": "ð", "İ": "Ý", "ı": "ÿ", "Ş": "Þ", "ş": "þ",
})
TR_ANSI_FALLBACK = str.maketrans({
    "Ğ": "G", "ğ": "g", "İ": "I", "ı": "i", "Ş": "S", "ş": "s",
})


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def p32(buf: bytearray, off: int, value: int) -> None:
    struct.pack_into("<I", buf, off, value)


class StbError(Exception):
    pass


class STB:
    def __init__(self, raw: bytes, path: str = ""):
        self.raw = raw
        self.path = path
        if len(raw) < 24 or raw[:4] != MAGIC:
            raise StbError(f"{path}: STBL başlığı bulunamadı")
        self.version = u32(raw, 4)
        if self.version == 0x101:
            self.kind = "1.1"
            self.encoding_id = u32(raw, 0x0C)  # 1=UTF-8, 2=UTF-16LE (Russian)
            self.lang_id = u32(raw, 0x10)
            self.count = u32(raw, 0x14)
            self.offset_start = 0x20
            self.data_start = self.offset_start + self.count * 4
            if self.data_start > len(raw):
                raise StbError(f"{path}: bozuk STB 1.1 ofset tablosu")
            char_count = u32(raw, 0x18)
            utf8_bytes = u32(raw, 0x1C)
            data = raw[self.data_start:]
            try:
                if self.encoding_id == 1:
                    if utf8_bytes and utf8_bytes != len(data):
                        raise StbError(f"{path}: STB 1.1 UTF-8 veri boyutu uyuşmuyor")
                    text_pool = data.decode("utf-8")
                elif self.encoding_id == 2:
                    if char_count and char_count * 2 != len(data):
                        raise StbError(f"{path}: STB 1.1 UTF-16LE veri boyutu uyuşmuyor")
                    text_pool = data.decode("utf-16le")
                    if utf8_bytes and utf8_bytes != len(text_pool.encode("utf-8")):
                        raise StbError(f"{path}: STB 1.1 UTF-16/UTF-8 uzunluk alanı uyuşmuyor")
                else:
                    raise StbError(f"{path}: bilinmeyen STB 1.1 metin kodlaması {self.encoding_id}")
            except UnicodeDecodeError as e:
                raise StbError(f"{path}: metin çözülemedi: {e}") from e
            if char_count and char_count != len(text_pool):
                raise StbError(f"{path}: STB 1.1 karakter sayısı uyuşmuyor")
            offsets = struct.unpack_from(f"<{self.count}I", raw, self.offset_start) if self.count else ()
            strings = []
            for idx, off in enumerate(offsets):
                if off > len(text_pool):
                    raise StbError(f"{path}: string {idx} ofseti sınır dışında")
                end = text_pool.find("\0", off)
                if end < 0:
                    raise StbError(f"{path}: string {idx} sonlandırıcısı yok")
                strings.append(text_pool[off:end])
            self.strings = strings
        elif self.version == 0x100:
            self.kind = "1.0"
            self.encoding_id = 0
            self.lang_id = u32(raw, 0x0C)
            self.count = u32(raw, 0x10)
            self.offset_start = 0x18
            self.data_start = self.offset_start + self.count * 4
            if self.data_start > len(raw):
                raise StbError(f"{path}: bozuk STB 1.0 ofset tablosu")
            expected_bytes = u32(raw, 0x14)
            data = raw[self.data_start:]
            if expected_bytes and expected_bytes != len(data):
                raise StbError(f"{path}: STB 1.0 veri boyutu uyuşmuyor")
            offsets = struct.unpack_from(f"<{self.count}I", raw, self.offset_start) if self.count else ()
            strings = []
            for idx, off in enumerate(offsets):
                if off > len(data):
                    raise StbError(f"{path}: string {idx} ofseti sınır dışında")
                end = data.find(b"\0", off)
                if end < 0:
                    raise StbError(f"{path}: string {idx} sonlandırıcısı yok")
                try:
                    strings.append(data[off:end].decode("cp1252"))
                except UnicodeDecodeError as e:
                    raise StbError(f"{path}: CP1252 çözülemedi: {e}") from e
            self.strings = strings
        else:
            raise StbError(f"{path}: desteklenmeyen STBL sürümü 0x{self.version:08X}")

    def rebuild(self, strings: list[str], v100_mode: str = "transliterate") -> tuple[bytes, list[str]]:
        if len(strings) != self.count:
            raise StbError(f"{self.path}: string sayısı değişemez ({len(strings)} != {self.count})")
        warnings: list[str] = []
        if any("\0" in s for s in strings):
            raise StbError(f"{self.path}: çeviri içinde NUL (\\0) kullanılamaz")

        if self.kind == "1.1":
            offsets = []
            pool_parts = []
            char_pos = 0
            for s in strings:
                offsets.append(char_pos)
                part = s + "\0"
                pool_parts.append(part)
                char_pos += len(part)
            pool_text = "".join(pool_parts)
            if getattr(self, "encoding_id", 1) == 2:
                data = pool_text.encode("utf-16le")
            else:
                data = pool_text.encode("utf-8")
            header = bytearray(self.raw[:0x20])
            p32(header, 0x14, len(strings))
            p32(header, 0x18, len(pool_text))
            # This header field is the UTF-8 byte count even when on-disk text is UTF-16LE.
            p32(header, 0x1C, len(pool_text.encode("utf-8")))
            table = struct.pack(f"<{len(offsets)}I", *offsets) if offsets else b""
            return bytes(header) + table + data, warnings

        # STB 1.0 offsets are raw byte offsets and strings use CP1252 in this game.
        offsets = []
        chunks = []
        byte_pos = 0
        for idx, s in enumerate(strings):
            out_s = s
            try:
                enc = out_s.encode("cp1252")
            except UnicodeEncodeError:
                if v100_mode == "strict":
                    raise StbError(
                        f"{self.path} #{idx}: STB 1.0 CP1252 Türkçe karakteri kodlayamıyor. "
                        "Varsayılan --v100-mode fontmap kullanın veya transliterate seçin."
                    )
                if v100_mode == "utf8":
                    enc = out_s.encode("utf-8")
                    warnings.append(
                        f"{self.path} #{idx}: STB 1.0 için deneysel UTF-8 yazıldı; oyunda glif/kodlama testi gerekir."
                    )
                elif v100_mode == "fontmap":
                    fixed = out_s.translate(TR_FONTMAP_ENCODE)
                    try:
                        enc = fixed.encode("cp1252")
                    except UnicodeEncodeError as e:
                        raise StbError(
                            f"{self.path} #{idx}: fontmap sonrasında CP1252 dışında karakter var "
                            f"({e.object[e.start:e.end]!r})"
                        ) from e
                    if fixed != out_s:
                        warnings.append(
                            f"{self.path} #{idx}: STB 1.0 Türkçe harfleri font alias kodlarıyla yazıldı "
                            "(Ð/ð/Ý/ÿ/Þ/þ); patch_romfs/fonts içindeki Türkçe CFNA yaması gerekir."
                        )
                else:
                    fixed = out_s.translate(TR_ANSI_FALLBACK)
                    try:
                        enc = fixed.encode("cp1252")
                    except UnicodeEncodeError as e:
                        raise StbError(
                            f"{self.path} #{idx}: CP1252 dışında karakter var ({e.object[e.start:e.end]!r})"
                        ) from e
                    if fixed != out_s:
                        warnings.append(
                            f"{self.path} #{idx}: STB 1.0 uyumluluğu için Ğ/ğ/İ/ı/Ş/ş sadeleştirildi."
                        )
            offsets.append(byte_pos)
            chunk = enc + b"\0"
            chunks.append(chunk)
            byte_pos += len(chunk)
        data = b"".join(chunks)
        header = bytearray(self.raw[:0x18])
        p32(header, 0x10, len(strings))
        p32(header, 0x14, len(data))
        table = struct.pack(f"<{len(offsets)}I", *offsets) if offsets else b""
        return bytes(header) + table + data, warnings


class SourceFS:
    def __init__(self, source: str | os.PathLike[str]):
        self.path = Path(source)
        self.zip: zipfile.ZipFile | None = None
        if self.path.is_file() and self.path.suffix.lower() == ".zip":
            self.zip = zipfile.ZipFile(self.path, "r")
        elif not self.path.is_dir():
            raise FileNotFoundError(f"Kaynak bulunamadı: {self.path}")

    def close(self):
        if self.zip:
            self.zip.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def names(self) -> list[str]:
        if self.zip:
            return [n for n in self.zip.namelist() if not n.endswith("/")]
        return [p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file()]

    def read(self, rel: str) -> bytes:
        rel = PurePosixPath(rel).as_posix()
        if self.zip:
            return self.zip.read(rel)
        return (self.path / Path(rel)).read_bytes()

    def copy_to(self, rel: str, root: Path) -> Path:
        dest = root / Path(PurePosixPath(rel).as_posix())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.read(rel))
        return dest


def escape_text(s: str) -> str:
    out = []
    for ch in s:
        if ch == "\\": out.append("\\\\")
        elif ch == "\n": out.append("\\n")
        elif ch == "\r": out.append("\\r")
        elif ch == "\t": out.append("\\t")
        elif ch == "\0": out.append("\\0")
        else: out.append(ch)
    return "".join(out)


def unescape_text(s: str) -> str:
    out = []
    i = 0
    mapping = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\"}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in mapping:
                out.append(mapping[nxt]); i += 2; continue
        out.append(s[i]); i += 1
    return "".join(out)


def sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def discover_en_stb(names: list[str]) -> list[str]:
    return sorted(n for n in names if n.lower().endswith("-en.stb"))


def discover_lang_images(names: list[str]) -> list[str]:
    name_set = set(names)
    out = []
    for n in names:
        ext = Path(n).suffix.lower()
        if ext in IMAGE_EXTS and LANG_IMAGE_RE.search(Path(n).name):
            out.append(n)
    out.extend(n for n in EXTRA_IMAGE_FILES if n in name_set and n not in out)
    return sorted(out)


def decode_text_lines(raw: bytes, rel: str):
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig" if bom else "utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"{rel}: UTF-8 metin dosyası çözülemedi: {e}") from e
    sep = "\r\n" if "\r\n" in text else "\n"
    return text.split(sep), sep, bom


def export_tsv(source: SourceFS, out_tsv: Path) -> tuple[int, int]:
    """Export English rows with every available official language beside them.

    The build step still uses source_en + tr; source_fr/source_de/... are read-only
    reference columns and can safely remain in the TSV.
    """
    names = source.names()
    name_set = set(names)
    files = discover_en_stb(names)
    rows = []
    total = 0
    ref_columns = [col for _suffix, col, _display in REFERENCE_LANGS]

    for rel in files:
        en_stb = STB(source.read(rel), rel)
        base = rel[:-7]  # remove -en.stb
        refs: dict[str, STB | None] = {}
        for suffix, col, _display in REFERENCE_LANGS:
            ref_rel = base + f"-{suffix}.stb"
            if ref_rel not in name_set:
                refs[col] = None
                continue
            ref_stb = STB(source.read(ref_rel), ref_rel)
            if ref_stb.count != en_stb.count:
                raise StbError(
                    f"{rel}: {suffix} satır sayısı İngilizce ile uyuşmuyor "
                    f"({ref_stb.count} != {en_stb.count})"
                )
            refs[col] = ref_stb

        for idx, text in enumerate(en_stb.strings):
            row = {
                "file": rel,
                "id": str(idx),
                "format": f"STB{en_stb.kind}",
                "tr": "",
                "source_sha1": sha1_text(text),
                "notes": "",
            }
            for col in ref_columns:
                stb = refs.get(col)
                row[col] = escape_text(stb.strings[idx]) if stb is not None else ""
            rows.append(row)
            total += 1

    for rel in EXTRA_TEXT_FILES:
        if rel not in name_set:
            continue
        lines, _sep, _bom = decode_text_lines(source.read(rel), rel)
        for idx, text in enumerate(lines):
            row = {
                "file": rel,
                "id": str(idx),
                "format": "TXTLINE",
                "tr": "",
                "source_sha1": sha1_text(text),
                "notes": "Credits için resmi diğer dil dosyası yok; yalnız İngilizce kaynak mevcut.",
            }
            for col in ref_columns:
                row[col] = escape_text(text) if col == "source_en" else ""
            rows.append(row)
            total += 1

    fields = ["file", "id", "format"] + ref_columns + ["tr", "source_sha1", "notes"]
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    with out_tsv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader(); w.writerows(rows)
    return len(files) + sum(1 for x in EXTRA_TEXT_FILES if x in name_set), total


def read_translation_tsv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    required = {"file", "id", "source_en", "tr"}
    if not rows and path.stat().st_size:
        raise ValueError("Çeviri TSV dosyası okunamadı")
    if rows and not required.issubset(rows[0].keys()):
        raise ValueError(f"TSV sütunları eksik. Gerekli: {sorted(required)}")
    return rows


def validate_tokens(src: str, tr: str) -> list[str]:
    issues = []
    src_tags, tr_tags = TEXT_TAG_RE.findall(src), TEXT_TAG_RE.findall(tr)
    if src_tags != tr_tags:
        issues.append(f"etiketler farklı: EN={src_tags} TR={tr_tags}")
    src_fmt = [x for x in PRINTF_RE.findall(src) if x != "%%"]
    tr_fmt = [x for x in PRINTF_RE.findall(tr) if x != "%%"]
    if src_fmt != tr_fmt:
        issues.append(f"format belirteçleri farklı: EN={src_fmt} TR={tr_fmt}")
    return issues


def build_patch(source: SourceFS, tsv: Path, out_root: Path, images_dir: Path | None,
                require_complete: bool, strict_tags: bool, v100_mode: str,
                turkish_fonts: bool = True) -> tuple[int, int, list[str]]:
    rows = read_translation_tsv(tsv)
    grouped: dict[str, dict[int, dict[str, str]]] = {}
    for row in rows:
        rel = PurePosixPath(row["file"]).as_posix()
        try: idx = int(row["id"])
        except ValueError: raise ValueError(f"Geçersiz id: {row['id']!r}")
        if idx in grouped.setdefault(rel, {}):
            raise ValueError(f"Tekrarlanan satır: {rel} #{idx}")
        grouped[rel][idx] = row

    source_names = source.names()
    source_files = discover_en_stb(source_names)
    text_files = [x for x in EXTRA_TEXT_FILES if x in source_names]
    translatable = set(source_files) | set(text_files)
    unknown = sorted(set(grouped) - translatable)
    if unknown:
        raise ValueError(f"TSV içinde kaynakta bulunmayan çeviri dosyası var: {unknown[:5]}")

    out_root.mkdir(parents=True, exist_ok=True)
    warnings = []
    translated_count = 0
    built_files = 0
    for rel in source_files:
        original = STB(source.read(rel), rel)
        mapping = grouped.get(rel, {})
        if set(mapping) != set(range(original.count)):
            missing = sorted(set(range(original.count)) - set(mapping))[:10]
            extra = sorted(set(mapping) - set(range(original.count)))[:10]
            raise ValueError(f"{rel}: satır/id kümesi uyuşmuyor; eksik={missing} fazla={extra}")
        new_strings = []
        for idx, src in enumerate(original.strings):
            row = mapping[idx]
            tsv_src = unescape_text(row.get("source_en", ""))
            if tsv_src != src:
                raise ValueError(f"{rel} #{idx}: kaynak İngilizce değişmiş; yeniden extract yapın")
            if row.get("source_sha1") and row["source_sha1"] != sha1_text(src):
                raise ValueError(f"{rel} #{idx}: kaynak hash uyuşmuyor")
            tr_raw = row.get("tr", "")
            if tr_raw.strip() == "":
                if require_complete:
                    raise ValueError(f"{rel} #{idx}: Türkçe çeviri boş")
                tr = src
            else:
                tr = unescape_text(tr_raw)
                translated_count += 1
                issues = validate_tokens(src, tr)
                if issues:
                    msg = f"{rel} #{idx}: " + "; ".join(issues)
                    if strict_tags: raise ValueError(msg)
                    warnings.append(msg)
            new_strings.append(tr)
        built, stb_warn = original.rebuild(new_strings, v100_mode=v100_mode)
        warnings.extend(stb_warn)
        dest = out_root / Path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(built)
        # round-trip parse verifies format and count
        check = STB(built, rel)
        if len(check.strings) != len(new_strings):
            raise StbError(f"{rel}: yeniden oluşturma doğrulaması başarısız")
        built_files += 1

    # UTF-8 credits text files (line-by-line entries in the same TSV).
    for rel in text_files:
        original_raw = source.read(rel)
        original_lines, sep, bom = decode_text_lines(original_raw, rel)
        mapping = grouped.get(rel, {})
        if set(mapping) != set(range(len(original_lines))):
            missing = sorted(set(range(len(original_lines))) - set(mapping))[:10]
            extra = sorted(set(mapping) - set(range(len(original_lines))))[:10]
            raise ValueError(f"{rel}: TXTLINE satır/id kümesi uyuşmuyor; eksik={missing} fazla={extra}")
        new_lines = []
        for idx, src_line in enumerate(original_lines):
            row = mapping[idx]
            tsv_src = unescape_text(row.get("source_en", ""))
            if tsv_src != src_line:
                raise ValueError(f"{rel} #{idx}: kaynak kredi satırı değişmiş; yeniden extract yapın")
            if row.get("source_sha1") and row["source_sha1"] != sha1_text(src_line):
                raise ValueError(f"{rel} #{idx}: kaynak hash uyuşmuyor")
            tr_raw = row.get("tr", "")
            if tr_raw.strip() == "":
                if require_complete and src_line.strip():
                    raise ValueError(f"{rel} #{idx}: Türkçe çeviri boş")
                tr_line = src_line
            else:
                tr_line = unescape_text(tr_raw)
                translated_count += 1
                issues = validate_tokens(src_line, tr_line)
                if issues:
                    msg = f"{rel} #{idx}: " + "; ".join(issues)
                    if strict_tags: raise ValueError(msg)
                    warnings.append(msg)
            if "\n" in tr_line or "\r" in tr_line:
                raise ValueError(f"{rel} #{idx}: TXTLINE çevirisinde satır sonu kullanmayın; ayrı satırları ayrı çevirin")
            new_lines.append(tr_line)
        text_out = sep.join(new_lines)
        raw_out = text_out.encode("utf-8-sig" if bom else "utf-8")
        dest = out_root / Path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw_out)
        built_files += 1

    if images_dir and images_dir.exists():
        for p in images_dir.rglob("*"):
            if not p.is_file() or p.name.startswith("README") or p.name.startswith("."):
                continue
            rel = p.relative_to(images_dir)
            dest = out_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)

    font_files = 0
    if turkish_fonts:
        if build_font_patch_from_reader is None:
            raise ValueError("font_tool.py bulunamadı; Türkçe font yaması üretilemiyor")
        font_files, font_notes = build_font_patch_from_reader(source.read, set(source_names), out_root)
        (out_root / "_turkish_font_patch.txt").write_text(
            "New Art Academy Türkçe font yaması\n"
            "==================================\n"
            "STB1.0 aliasları: Ð→Ğ, ð→ğ, Ý→İ, ÿ→ı, Þ→Ş, þ→ş\n\n"
            + "\n".join(font_notes) + "\n", encoding="utf-8"
        )

    manifest = out_root / "_naa_patch_manifest.txt"
    manifest.write_text(
        f"Replacement text files: {built_files}\nTurkish font files: {font_files}\nTranslated rows: {translated_count}\n"
        f"Blank rows kept as English: {max(0, len(rows)-translated_count)}\nWarnings: {len(warnings)}\n",
        encoding="utf-8"
    )
    if warnings:
        (out_root / "_naa_build_warnings.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")
    return built_files, translated_count, warnings


def copy_reference_assets(source: SourceFS, root: Path) -> tuple[int, int, int]:
    names = source.names()
    lang_suffixes = {suffix for suffix, _col, _display in REFERENCE_LANGS}
    stb_files = sorted(
        n for n in names
        if n.lower().endswith(".stb")
        and any(n.lower().endswith(f"-{suffix}.stb") for suffix in lang_suffixes)
    )
    lang_root = root / "language_files"
    for rel in stb_files:
        source.copy_to(rel, lang_root)
    credit_files = [x for x in EXTRA_TEXT_FILES if x in names]
    for rel in credit_files:
        source.copy_to(rel, lang_root)

    refs = sorted(n for n in names if n.lower().endswith(".tsv"))
    ref_root = root / "reference_tsv"
    for rel in refs:
        source.copy_to(rel, ref_root)

    images = discover_lang_images(names)
    img_root = root / "images_to_translate"
    for rel in images:
        source.copy_to(rel, img_root)
    manifest = root / "images_manifest.tsv"
    with manifest.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["original_path", "edited_copy_path", "reason"])
        for rel in images:
            w.writerow([rel, rel, "English-language image/screenshot; edit text and keep dimensions/format/path"])
    return len(stb_files) + len(credit_files), len(refs), len(images)


def cmd_extract(args):
    with SourceFS(args.source) as src:
        files, rows = export_tsv(src, Path(args.tsv))
        print(f"OK: {files} çeviri kaynağı (43 STB + varsa ek TXT), {rows} metin satırı -> {args.tsv}")
        if args.assets:
            a,b,c = copy_reference_assets(src, Path(args.assets))
            print(f"OK: kaynak paketlendi: {a} çok-dilli STB/metin dosyası, {b} TSV referansı, {c} İngilizce görsel")


def cmd_build(args):
    with SourceFS(args.source) as src:
        files, translated, warnings = build_patch(
            src, Path(args.tsv), Path(args.out), Path(args.images) if args.images else None,
            args.require_complete, args.strict_tags, args.v100_mode, not args.no_turkish_fonts
        )
    print(f"OK: {files} yama dosyası üretildi; {translated} satır Türkçe kullanıldı -> {args.out}")
    if warnings:
        print(f"UYARI: {len(warnings)} uyarı var. {Path(args.out) / '_naa_build_warnings.txt'} dosyasına bakın.")


def cmd_verify(args):
    count = 0
    with SourceFS(args.source) as src:
        for rel in discover_en_stb(src.names()):
            stb = STB(src.read(rel), rel)
            print(f"{rel}\tSTB{stb.kind}\tlang={stb.lang_id}\tstrings={stb.count}")
            count += 1
    print(f"OK: {count} İngilizce STB doğrulandı")


def make_parser():
    p = argparse.ArgumentParser(description="New Art Academy 3DS Türkçe yerelleştirme / STB yama aracı")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="İngilizce STB metinlerini yan yana çeviri TSV'sine çıkar")
    e.add_argument("source", help="RomFS klasörü veya romfs.zip")
    e.add_argument("--tsv", default="translations_tr.tsv", help="çıktı TSV")
    e.add_argument("--assets", help="language_files/reference_tsv/images_to_translate kopyalanacak paket kökü")
    e.set_defaults(func=cmd_extract)

    b = sub.add_parser("build", help="Çevirileri STB'lere geri yazıp RomFS yama ağacı üret")
    b.add_argument("source", help="orijinal RomFS klasörü veya romfs.zip")
    b.add_argument("tsv", help="translations_tr.tsv")
    b.add_argument("--out", default="patch_romfs", help="çıktı RomFS yama klasörü")
    b.add_argument("--images", default="images_edited", help="düzenlenmiş görsellerin kökü; aynı RomFS yollarını koruyun")
    b.add_argument("--require-complete", action="store_true", help="boş TR satırı varsa dur")
    b.add_argument("--strict-tags", action="store_true", help="[f2]/[] gibi etiketler değişmişse dur")
    b.add_argument("--v100-mode", choices=["fontmap", "transliterate", "strict", "utf8"], default="fontmap",
                   help="STB 1.0 Türkçe harf davranışı (varsayılan: fontmap; gerçek Türkçe glif için font yamasıyla birlikte)")
    b.add_argument("--no-turkish-fonts", action="store_true",
                   help="CFNA Türkçe font alias yamasını patch_romfs/fonts altına ekleme")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("verify", help="STB biçimlerini ve string sayılarını doğrula")
    v.add_argument("source")
    v.set_defaults(func=cmd_verify)
    return p


def main():
    p = make_parser(); args = p.parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, StbError, zipfile.BadZipFile, KeyError) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
