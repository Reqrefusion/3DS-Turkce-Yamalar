#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Star Fox 64 3D - MSBT Türkçe Çeviri Aracı

Standart kütüphane dışında bağımlılık gerektirmez.
- Resources.zip veya Resources klasörünü analiz eder.
- MSBT içindeki LBL1/TXT2 metinlerini TSV'ye çıkarır.
- MSBT kontrol kodlarını {{MSBT:HEX}} tokenlarıyla korur.
- Çeviri TSV'sini geri uygular ve yeni Resources_TR.zip üretir.
- Parametresiz çalıştırılırsa Tkinter GUI açılır.

Bu araç label/attribute yapılarını değiştirmez; yalnızca TXT2 bölümünü yeniden kurar.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

MAGIC = b"MsgStdBn"
TAG_RE = re.compile(r"\{\{MSBT:([0-9A-Fa-f]+)\}\}")
NUL_TOKEN = "{{NUL}}"
EMPTY_TOKEN = "{{EMPTY}}"


class MSBTError(Exception):
    pass


@dataclass
class Section:
    tag: str
    header: bytes
    data: bytes
    padding: bytes


@dataclass
class Entry:
    index: int
    label: str
    raw: bytes
    text: str


@dataclass
class MSBTFile:
    path: str
    source_bytes: bytes
    endian: str
    encoding_byte: int
    section_count: int
    sections: List[Section]
    labels: Dict[int, str]
    entries: List[Entry]
    header: bytes

    @property
    def codec(self) -> str:
        if self.encoding_byte == 0:
            return "utf-8"
        return "utf-16le" if self.endian == "<" else "utf-16be"


@dataclass
class ResourceSource:
    source_path: Path
    root: Path
    temp_dir: Optional[tempfile.TemporaryDirectory] = None
    files: List[Path] = field(default_factory=list)

    def close(self) -> None:
        if self.temp_dir is not None:
            self.temp_dir.cleanup()
            self.temp_dir = None


# ----------------------------- Binary helpers -----------------------------

def _u16(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + "H", data, off)[0]


def _u32(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + "I", data, off)[0]


def _p32(value: int, endian: str) -> bytes:
    return struct.pack(endian + "I", value)


def _align16(value: int) -> int:
    return (value + 15) & ~15


def _decode_ascii(data: bytes) -> str:
    return data.decode("ascii", errors="replace")


# ----------------------------- MSBT parsing -----------------------------

def parse_msbt_bytes(data: bytes, path: str = "<memory>") -> MSBTFile:
    if len(data) < 32 or data[:8] != MAGIC:
        raise MSBTError(f"{path}: geçerli bir MSBT (MsgStdBn) değil")

    bom = data[8:10]
    if bom == b"\xff\xfe":
        endian = "<"
    elif bom == b"\xfe\xff":
        endian = ">"
    else:
        raise MSBTError(f"{path}: bilinmeyen byte-order mark: {bom.hex()}")

    encoding_byte = data[12]
    if encoding_byte not in (0, 1):
        raise MSBTError(f"{path}: desteklenmeyen MSBT encoding değeri: {encoding_byte}")

    section_count = _u16(data, 14, endian)
    declared_size = _u32(data, 18, endian)
    if declared_size != len(data):
        raise MSBTError(
            f"{path}: header dosya boyutu {declared_size}, gerçek boyut {len(data)}"
        )

    sections: List[Section] = []
    pos = 32
    for section_i in range(section_count):
        if pos + 16 > len(data):
            raise MSBTError(f"{path}: bölüm {section_i} header'ı dosya dışında")
        tag_bytes = data[pos : pos + 4]
        try:
            tag = tag_bytes.decode("ascii")
        except UnicodeDecodeError as exc:
            raise MSBTError(f"{path}: geçersiz bölüm etiketi {tag_bytes!r}") from exc
        size = _u32(data, pos + 4, endian)
        data_start = pos + 16
        data_end = data_start + size
        if data_end > len(data):
            raise MSBTError(f"{path}: {tag} bölümü dosya sınırını aşıyor")
        next_pos = _align16(data_end)
        if next_pos > len(data):
            next_pos = len(data)
        sections.append(
            Section(
                tag=tag,
                header=data[pos : pos + 16],
                data=data[data_start:data_end],
                padding=data[data_end:next_pos],
            )
        )
        pos = next_pos

    labels: Dict[int, str] = {}
    for sec in sections:
        if sec.tag != "LBL1":
            continue
        blob = sec.data
        if len(blob) < 4:
            raise MSBTError(f"{path}: LBL1 çok kısa")
        group_count = _u32(blob, 0, endian)
        table_end = 4 + group_count * 8
        if table_end > len(blob):
            raise MSBTError(f"{path}: LBL1 grup tablosu bozuk")
        for gi in range(group_count):
            count = _u32(blob, 4 + gi * 8, endian)
            offset = _u32(blob, 8 + gi * 8, endian)
            p = offset
            for _ in range(count):
                if p >= len(blob):
                    raise MSBTError(f"{path}: LBL1 label offseti bozuk")
                n = blob[p]
                p += 1
                if p + n + 4 > len(blob):
                    raise MSBTError(f"{path}: LBL1 label kaydı bozuk")
                label = _decode_ascii(blob[p : p + n])
                p += n
                index = _u32(blob, p, endian)
                p += 4
                labels[index] = label
        break

    txt2 = next((s for s in sections if s.tag == "TXT2"), None)
    if txt2 is None:
        raise MSBTError(f"{path}: TXT2 bölümü bulunamadı")

    blob = txt2.data
    if len(blob) < 4:
        raise MSBTError(f"{path}: TXT2 çok kısa")
    count = _u32(blob, 0, endian)
    offsets_end = 4 + count * 4
    if offsets_end > len(blob):
        raise MSBTError(f"{path}: TXT2 offset tablosu bozuk")
    offsets = [_u32(blob, 4 + i * 4, endian) for i in range(count)]

    entries: List[Entry] = []
    for i, off in enumerate(offsets):
        nxt = offsets[i + 1] if i + 1 < count else len(blob)
        if off < offsets_end or nxt < off or nxt > len(blob):
            raise MSBTError(f"{path}: TXT2 metin offseti bozuk (index {i})")
        raw = blob[off:nxt]
        text = raw_to_markup(raw, endian, encoding_byte)
        entries.append(Entry(i, labels.get(i, f"#{i}"), raw, text))

    return MSBTFile(
        path=path,
        source_bytes=data,
        endian=endian,
        encoding_byte=encoding_byte,
        section_count=section_count,
        sections=sections,
        labels=labels,
        entries=entries,
        header=data[:32],
    )


def parse_msbt(path: Path) -> MSBTFile:
    return parse_msbt_bytes(path.read_bytes(), str(path))


# ----------------------------- Control-code safe text -----------------------------

def _decode_normal_bytes(buf: bytes, endian: str, encoding_byte: int) -> str:
    if not buf:
        return ""
    codec = "utf-8" if encoding_byte == 0 else ("utf-16le" if endian == "<" else "utf-16be")
    try:
        return buf.decode(codec)
    except UnicodeDecodeError as exc:
        raise MSBTError(f"Metin Unicode olarak çözülemedi: {exc}") from exc


def raw_to_markup(raw: bytes, endian: str, encoding_byte: int) -> str:
    """TXT2 tek girişini güvenli, düzenlenebilir metne çevirir."""
    if encoding_byte == 0:
        # Star Fox 64 3D dosyaları UTF-16LE. UTF-8 için kontrol kodu ayrıştırmak
        # oyunlara göre değişebildiğinden güvenli olarak sadece null sonlandırıcıyı ele al.
        body = raw[:-1] if raw.endswith(b"\x00") else raw
        return body.decode("utf-8", errors="strict")

    if len(raw) % 2:
        raise MSBTError("UTF-16 TXT2 girdisinin byte sayısı tek")

    out: List[str] = []
    normal = bytearray()
    p = 0

    def flush() -> None:
        nonlocal normal
        if normal:
            out.append(_decode_normal_bytes(bytes(normal), endian, encoding_byte))
            normal.clear()

    while p + 2 <= len(raw):
        cu = _u16(raw, p, endian)

        # Terminal NUL: TXT2 entry'nin sonundaki null metne dahil edilmez.
        if cu == 0 and p + 2 == len(raw):
            flush()
            p += 2
            break

        if cu == 0:
            flush()
            out.append(NUL_TOKEN)
            p += 2
            continue

        if cu == 0x000E:
            # MSBT start/control tag: marker + group(u16) + type(u16) + data_len(u16) + data
            if p + 8 > len(raw):
                raise MSBTError("Kesik MSBT kontrol kodu (0x000E)")
            param_len = _u16(raw, p + 6, endian)
            end = p + 8 + param_len
            if end > len(raw):
                raise MSBTError("MSBT kontrol kodunun payload uzunluğu dosyayı aşıyor")
            flush()
            tag_bytes = raw[p:end]
            out.append("{{MSBT:" + tag_bytes.hex().upper() + "}}")
            p = end
            continue

        if cu == 0x000F:
            # Standart MSBT end tag: marker + group(u16) + type(u16)
            if p + 6 > len(raw):
                raise MSBTError("Kesik MSBT bitiş kontrol kodu (0x000F)")
            flush()
            tag_bytes = raw[p : p + 6]
            out.append("{{MSBT:" + tag_bytes.hex().upper() + "}}")
            p += 6
            continue

        normal.extend(raw[p : p + 2])
        p += 2

    flush()
    return "".join(out)


def extract_tag_sequence(markup: str) -> List[str]:
    return [m.group(1).upper() for m in TAG_RE.finditer(markup)]


def markup_to_raw(markup: str, endian: str, encoding_byte: int, original_markup: Optional[str] = None) -> bytes:
    if markup == EMPTY_TOKEN:
        markup = ""

    if original_markup is not None:
        expected = extract_tag_sequence(original_markup)
        actual = extract_tag_sequence(markup)
        if actual != expected:
            raise MSBTError(
                "Kontrol kodları değişmiş. {{MSBT:...}} tokenlarını silmeyin, eklemeyin "
                "ve kendi aralarındaki sıralarını bozmayın."
            )

    if encoding_byte == 0:
        if TAG_RE.search(markup):
            raise MSBTError("UTF-8 MSBT için kontrol kodu enjeksiyonu desteklenmiyor")
        return markup.replace(NUL_TOKEN, "\x00").encode("utf-8") + b"\x00"

    codec = "utf-16le" if endian == "<" else "utf-16be"
    out = bytearray()
    pos = 0
    for m in TAG_RE.finditer(markup):
        text_part = markup[pos : m.start()]
        if NUL_TOKEN in text_part:
            chunks = text_part.split(NUL_TOKEN)
            for ci, chunk in enumerate(chunks):
                out.extend(chunk.encode(codec))
                if ci != len(chunks) - 1:
                    out.extend(b"\x00\x00")
        else:
            out.extend(text_part.encode(codec))

        hexdata = m.group(1)
        if len(hexdata) % 2:
            raise MSBTError("MSBT token hex uzunluğu tek")
        try:
            tag = bytes.fromhex(hexdata)
        except ValueError as exc:
            raise MSBTError("MSBT tokenı geçersiz hex içeriyor") from exc
        out.extend(tag)
        pos = m.end()

    tail = markup[pos:]
    if NUL_TOKEN in tail:
        chunks = tail.split(NUL_TOKEN)
        for ci, chunk in enumerate(chunks):
            out.extend(chunk.encode(codec))
            if ci != len(chunks) - 1:
                out.extend(b"\x00\x00")
    else:
        out.extend(tail.encode(codec))

    out.extend(b"\x00\x00")
    return bytes(out)


# ----------------------------- Rebuilding -----------------------------

def rebuild_msbt(msbt: MSBTFile, translations: Dict[int, str]) -> bytes:
    new_raw: List[bytes] = []
    for ent in msbt.entries:
        tr = translations.get(ent.index, ent.text)
        new_raw.append(markup_to_raw(tr, msbt.endian, msbt.encoding_byte, ent.text))

    count = len(new_raw)
    table_len = 4 + count * 4
    offsets: List[int] = []
    cursor = table_len
    for raw in new_raw:
        offsets.append(cursor)
        cursor += len(raw)

    txt_data = bytearray()
    txt_data.extend(_p32(count, msbt.endian))
    for off in offsets:
        txt_data.extend(_p32(off, msbt.endian))
    for raw in new_raw:
        txt_data.extend(raw)

    out = bytearray(msbt.header)
    for sec in msbt.sections:
        if sec.tag == "TXT2":
            header = bytearray(sec.header)
            header[4:8] = _p32(len(txt_data), msbt.endian)
            out.extend(header)
            out.extend(txt_data)
            pad_len = (-len(out)) % 16
            if pad_len:
                pad_byte = sec.padding[:1] or b"\xAB"
                out.extend(pad_byte * pad_len)
        else:
            out.extend(sec.header)
            out.extend(sec.data)
            out.extend(sec.padding)

    out[18:22] = _p32(len(out), msbt.endian)
    return bytes(out)


# ----------------------------- Resource input/output -----------------------------

def open_resource_source(path: Path) -> ResourceSource:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    if path.is_dir():
        root = path
        rs = ResourceSource(path, root)
    elif zipfile.is_zipfile(path):
        td = tempfile.TemporaryDirectory(prefix="sf64_3d_resources_")
        root = Path(td.name)
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(root)
        rs = ResourceSource(path, root, td)
    else:
        raise MSBTError("Kaynak bir klasör veya ZIP olmalı")

    rs.files = sorted([p for p in root.rglob("*") if p.is_file()])
    return rs


def rel_key(rs: ResourceSource, path: Path) -> str:
    return path.relative_to(rs.root).as_posix()


def find_msbt_files(rs: ResourceSource) -> List[Path]:
    return [p for p in rs.files if p.suffix.lower() == ".msbt"]


def write_patched_zip(
    rs: ResourceSource,
    output_zip: Path,
    patches: Dict[str, Dict[int, str]],
) -> Tuple[int, int]:
    output_zip = output_zip.expanduser().resolve()
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    modified = 0
    total = 0

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in rs.files:
            key = rel_key(rs, p)
            data = p.read_bytes()
            if key in patches:
                msbt = parse_msbt_bytes(data, key)
                data = rebuild_msbt(msbt, patches[key])
                modified += 1
            zf.writestr(key, data)
            total += 1
    return modified, total


# ----------------------------- TSV workflow -----------------------------

def export_tsv(rs: ResourceSource, output: Path, selected_keys: Optional[Sequence[str]] = None) -> int:
    selected = set(selected_keys) if selected_keys else None
    count = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(["file", "index", "label", "original", "translation"])
        for p in find_msbt_files(rs):
            key = rel_key(rs, p)
            if selected is not None and key not in selected:
                continue
            msbt = parse_msbt(p)
            for ent in msbt.entries:
                w.writerow([key, ent.index, ent.label, ent.text, ent.text])
                count += 1
    return count


def import_tsv(path: Path) -> Dict[str, Dict[int, str]]:
    patches: Dict[str, Dict[int, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        required = {"file", "index", "label", "original", "translation"}
        if not r.fieldnames or not required.issubset(set(r.fieldnames)):
            raise MSBTError("TSV başlıkları eksik: file, index, label, original, translation")
        for row_no, row in enumerate(r, start=2):
            key = (row.get("file") or "").strip()
            if not key:
                continue
            try:
                idx = int(row.get("index") or "")
            except ValueError as exc:
                raise MSBTError(f"TSV satır {row_no}: index sayı değil") from exc
            original = row.get("original") or ""
            tr = row.get("translation")
            if tr is None:
                tr = original
            # Boş hücre = orijinali koru. Bilerek boşaltmak için {{EMPTY}}.
            if tr == "":
                tr = original
            if extract_tag_sequence(tr) != extract_tag_sequence(original):
                raise MSBTError(
                    f"TSV satır {row_no} ({key} / {idx}): MSBT kontrol tokenları değişmiş"
                )
            patches.setdefault(key, {})[idx] = tr
    return patches


# ----------------------------- Language guess -----------------------------
_STOPWORDS = {
    "EN": {"the", "and", "you", "your", "is", "are", "to", "of", "for", "with", "this", "that", "we", "need", "press", "mission", "game", "fox"},
    "DE": {"der", "die", "das", "und", "ist", "sind", "zu", "von", "mit", "für", "nicht", "wir", "euch", "eine", "einen", "drücken", "mission"},
    "FR": {"le", "la", "les", "de", "des", "et", "est", "vous", "pour", "avec", "une", "un", "nous", "pas", "appuyez", "mission"},
    "IT": {"il", "lo", "la", "gli", "le", "di", "e", "è", "per", "con", "una", "un", "noi", "non", "premi", "missione"},
    "ES": {"el", "la", "los", "las", "de", "y", "es", "para", "con", "una", "un", "nos", "no", "pulsa", "misión", "ayuda"},
}


def guess_language(msbt: MSBTFile) -> str:
    corpus = " ".join(e.text for e in msbt.entries[: min(250, len(msbt.entries))])
    # Tokenları çıkar.
    corpus = TAG_RE.sub(" ", corpus)
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", corpus):
        return "JA"
    words = re.findall(r"[A-Za-zÀ-ÿ]+", corpus.lower())
    scores = {lang: 0 for lang in _STOPWORDS}
    for word in words:
        for lang, sw in _STOPWORDS.items():
            if word in sw:
                scores[lang] += 1
    # Ayırt edici karakterlere küçük bonuslar.
    if re.search(r"[ñ¿¡]", corpus.lower()): scores["ES"] += 8
    if re.search(r"[äöüß]", corpus.lower()): scores["DE"] += 8
    if re.search(r"[àâçéèêëîïôùûœ]", corpus.lower()): scores["FR"] += 5
    if re.search(r"[ìò]", corpus.lower()): scores["IT"] += 4
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "?"


def sample_text(msbt: MSBTFile, limit: int = 90) -> str:
    for ent in msbt.entries:
        s = TAG_RE.sub("", ent.text).replace("\n", " ").strip()
        s = " ".join(s.split())
        if s:
            return s[:limit]
    return ""


# ----------------------------- Validation / analysis -----------------------------

def analyze_source(rs: ResourceSource) -> List[dict]:
    rows = []
    for p in find_msbt_files(rs):
        key = rel_key(rs, p)
        msbt = parse_msbt(p)
        rows.append(
            {
                "file": key,
                "entries": len(msbt.entries),
                "language": guess_language(msbt),
                "sample": sample_text(msbt),
                "size": p.stat().st_size,
            }
        )
    return rows


def self_test_source(rs: ResourceSource) -> Tuple[int, List[str]]:
    """Değişiklik yokken rebuild'in byte-byte aynı olduğunu doğrular."""
    ok = 0
    errors: List[str] = []
    for p in find_msbt_files(rs):
        key = rel_key(rs, p)
        try:
            msbt = parse_msbt(p)
            rebuilt = rebuild_msbt(msbt, {})
            if rebuilt != p.read_bytes():
                errors.append(f"{key}: yeniden paketleme binary-identical değil")
            else:
                ok += 1
        except Exception as exc:
            errors.append(f"{key}: {exc}")
    return ok, errors


# ----------------------------- CLI -----------------------------

def cmd_analyze(args: argparse.Namespace) -> int:
    rs = open_resource_source(Path(args.source))
    try:
        rows = analyze_source(rs)
        print(f"MSBT sayısı: {len(rows)}")
        print(f"{'Dosya':32} {'Adet':>6} {'Dil':>4}  Örnek")
        print("-" * 110)
        for row in rows:
            print(f"{row['file'][:32]:32} {row['entries']:6d} {row['language']:>4}  {row['sample']}")
        return 0
    finally:
        rs.close()


def cmd_export(args: argparse.Namespace) -> int:
    rs = open_resource_source(Path(args.source))
    try:
        selected = None
        if args.lang:
            wanted = args.lang.upper()
            selected = [r["file"] for r in analyze_source(rs) if r["language"] == wanted]
            if not selected:
                raise MSBTError(f"'{wanted}' dilinde dosya bulunamadı")
        n = export_tsv(rs, Path(args.output), selected)
        print(f"{n} metin dışa aktarıldı: {args.output}")
        return 0
    finally:
        rs.close()


def cmd_build(args: argparse.Namespace) -> int:
    rs = open_resource_source(Path(args.source))
    try:
        patches = import_tsv(Path(args.tsv))
        # Kaynak dosyalar ve indeksler gerçekten var mı kontrol et.
        available = {rel_key(rs, p): p for p in find_msbt_files(rs)}
        for key, trans in patches.items():
            if key not in available:
                raise MSBTError(f"TSV kaynakta olmayan dosya içeriyor: {key}")
            msbt = parse_msbt(available[key])
            for idx, tr in trans.items():
                if idx < 0 or idx >= len(msbt.entries):
                    raise MSBTError(f"{key}: geçersiz index {idx}")
                # Original referansı TSV'de ayrıca doğrulanıyor; burada kontrol kodu validasyonu rebuild'de.
        modified, total = write_patched_zip(rs, Path(args.output), patches)
        print(f"Hazır: {args.output} | yama uygulanan MSBT: {modified} | toplam dosya: {total}")
        return 0
    finally:
        rs.close()


def cmd_test(args: argparse.Namespace) -> int:
    rs = open_resource_source(Path(args.source))
    try:
        ok, errors = self_test_source(rs)
        print(f"Binary-identical test: {ok} MSBT başarılı")
        for err in errors:
            print("HATA:", err)
        return 1 if errors else 0
    finally:
        rs.close()


# ----------------------------- Tkinter GUI -----------------------------

def launch_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        print("Tkinter açılamadı:", exc, file=sys.stderr)
        return 2

    class App(tk.Tk):
        def __init__(self) -> None:
            super().__init__()
            self.title("Star Fox 64 3D - Türkçe MSBT Aracı")
            self.geometry("1180x760")
            self.minsize(900, 600)
            self.rs: Optional[ResourceSource] = None
            self.rows: Dict[str, dict] = {}
            self.patches: Dict[str, Dict[int, str]] = {}
            self.current_msbt: Optional[MSBTFile] = None
            self.current_key: Optional[str] = None
            self.current_entry_index: Optional[int] = None
            self._build_ui()

        def _build_ui(self) -> None:
            top = ttk.Frame(self, padding=8)
            top.pack(fill="x")
            ttk.Button(top, text="Resources ZIP/Klasör Aç", command=self.open_source).pack(side="left")
            ttk.Button(top, text="Seçili dosyaları TSV'ye aktar", command=self.export_selected).pack(side="left", padx=6)
            ttk.Button(top, text="TSV içe aktar", command=self.import_translation).pack(side="left")
            ttk.Button(top, text="Yama ZIP'i oluştur", command=self.build_zip).pack(side="left", padx=6)
            ttk.Button(top, text="Binary test", command=self.binary_test).pack(side="left")

            self.status = tk.StringVar(value="Resources.zip açarak başlayın.")
            ttk.Label(self, textvariable=self.status, padding=(8, 0, 8, 6)).pack(fill="x")

            paned = ttk.Panedwindow(self, orient="vertical")
            paned.pack(fill="both", expand=True, padx=8, pady=(0, 8))

            files_frame = ttk.Labelframe(paned, text="MSBT dosyaları", padding=6)
            paned.add(files_frame, weight=2)
            self.file_tree = ttk.Treeview(
                files_frame,
                columns=("entries", "lang", "sample"),
                show="tree headings",
                selectmode="extended",
            )
            self.file_tree.heading("#0", text="Dosya")
            self.file_tree.heading("entries", text="Metin")
            self.file_tree.heading("lang", text="Dil tahmini")
            self.file_tree.heading("sample", text="Örnek")
            self.file_tree.column("#0", width=180, stretch=False)
            self.file_tree.column("entries", width=70, anchor="e", stretch=False)
            self.file_tree.column("lang", width=90, anchor="center", stretch=False)
            self.file_tree.column("sample", width=700)
            y1 = ttk.Scrollbar(files_frame, orient="vertical", command=self.file_tree.yview)
            self.file_tree.configure(yscrollcommand=y1.set)
            self.file_tree.pack(side="left", fill="both", expand=True)
            y1.pack(side="right", fill="y")
            self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)

            edit_frame = ttk.Labelframe(paned, text="Metin düzenleyici", padding=6)
            paned.add(edit_frame, weight=3)

            left = ttk.Frame(edit_frame)
            left.pack(side="left", fill="both", expand=True)
            self.entry_tree = ttk.Treeview(left, columns=("label", "preview"), show="headings", selectmode="browse")
            self.entry_tree.heading("label", text="Label")
            self.entry_tree.heading("preview", text="Metin")
            self.entry_tree.column("label", width=180, stretch=False)
            self.entry_tree.column("preview", width=470)
            y2 = ttk.Scrollbar(left, orient="vertical", command=self.entry_tree.yview)
            self.entry_tree.configure(yscrollcommand=y2.set)
            self.entry_tree.pack(side="left", fill="both", expand=True)
            y2.pack(side="right", fill="y")
            self.entry_tree.bind("<<TreeviewSelect>>", self.on_entry_select)

            right = ttk.Frame(edit_frame, padding=(8, 0, 0, 0))
            right.pack(side="right", fill="both", expand=True)
            ttk.Label(right, text="Çeviri ({{MSBT:...}} tokenlarını silmeyin):").pack(anchor="w")
            self.editor = tk.Text(right, wrap="word", undo=True, height=12)
            self.editor.pack(fill="both", expand=True, pady=(4, 6))
            buttons = ttk.Frame(right)
            buttons.pack(fill="x")
            ttk.Button(buttons, text="Bu metni kaydet", command=self.save_current_entry).pack(side="left")
            ttk.Button(buttons, text="Orijinale döndür", command=self.reset_current_entry).pack(side="left", padx=6)
            ttk.Label(buttons, text="Boş bırakmak için {{EMPTY}}").pack(side="right")

        def set_status(self, text: str) -> None:
            self.status.set(text)
            self.update_idletasks()

        def open_source(self) -> None:
            path = filedialog.askopenfilename(
                title="Resources.zip seç",
                filetypes=[("ZIP", "*.zip"), ("Tüm dosyalar", "*.*")],
            )
            if not path:
                path = filedialog.askdirectory(title="Veya Resources klasörü seç")
            if not path:
                return
            try:
                if self.rs:
                    self.rs.close()
                self.set_status("Dosyalar analiz ediliyor...")
                self.rs = open_resource_source(Path(path))
                rows = analyze_source(self.rs)
                self.rows = {r["file"]: r for r in rows}
                self.file_tree.delete(*self.file_tree.get_children())
                for r in rows:
                    self.file_tree.insert("", "end", iid=r["file"], text=r["file"], values=(r["entries"], r["language"], r["sample"]))
                self.entry_tree.delete(*self.entry_tree.get_children())
                self.editor.delete("1.0", "end")
                self.current_msbt = None
                self.current_key = None
                self.patches = {}
                self.set_status(f"{len(rows)} MSBT bulundu. Dosyaları seçip TSV'ye aktarabilirsiniz.")
            except Exception as exc:
                messagebox.showerror("Hata", str(exc))
                self.set_status("Açma başarısız.")

        def selected_keys(self) -> List[str]:
            return list(self.file_tree.selection())

        def on_file_select(self, _event=None) -> None:
            if not self.rs:
                return
            sels = self.selected_keys()
            if len(sels) != 1:
                return
            key = sels[0]
            try:
                path = self.rs.root / Path(key)
                msbt = parse_msbt(path)
                self.current_msbt = msbt
                self.current_key = key
                self.current_entry_index = None
                self.entry_tree.delete(*self.entry_tree.get_children())
                patch = self.patches.get(key, {})
                for ent in msbt.entries:
                    text = patch.get(ent.index, ent.text)
                    preview = TAG_RE.sub("<TAG>", text).replace("\n", " ↵ ")
                    self.entry_tree.insert("", "end", iid=str(ent.index), values=(ent.label, preview[:180]))
                self.editor.delete("1.0", "end")
                self.set_status(f"{key}: {len(msbt.entries)} metin")
            except Exception as exc:
                messagebox.showerror("Hata", str(exc))

        def on_entry_select(self, _event=None) -> None:
            if not self.current_msbt or not self.current_key:
                return
            sel = self.entry_tree.selection()
            if not sel:
                return
            idx = int(sel[0])
            self.current_entry_index = idx
            ent = self.current_msbt.entries[idx]
            text = self.patches.get(self.current_key, {}).get(idx, ent.text)
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", text)

        def save_current_entry(self) -> None:
            if self.current_msbt is None or self.current_key is None or self.current_entry_index is None:
                return
            idx = self.current_entry_index
            ent = self.current_msbt.entries[idx]
            tr = self.editor.get("1.0", "end-1c")
            if tr == "":
                tr = ent.text
            try:
                # Sadece doğrulama için encode et.
                markup_to_raw(tr, self.current_msbt.endian, self.current_msbt.encoding_byte, ent.text)
                self.patches.setdefault(self.current_key, {})[idx] = tr
                preview = TAG_RE.sub("<TAG>", tr).replace("\n", " ↵ ")
                self.entry_tree.item(str(idx), values=(ent.label, preview[:180]))
                self.set_status(f"Kaydedildi: {self.current_key} / {ent.label}")
            except Exception as exc:
                messagebox.showerror("Kontrol kodu hatası", str(exc))

        def reset_current_entry(self) -> None:
            if self.current_msbt is None or self.current_key is None or self.current_entry_index is None:
                return
            idx = self.current_entry_index
            ent = self.current_msbt.entries[idx]
            self.patches.get(self.current_key, {}).pop(idx, None)
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", ent.text)
            preview = TAG_RE.sub("<TAG>", ent.text).replace("\n", " ↵ ")
            self.entry_tree.item(str(idx), values=(ent.label, preview[:180]))

        def export_selected(self) -> None:
            if not self.rs:
                messagebox.showinfo("Bilgi", "Önce Resources.zip açın.")
                return
            keys = self.selected_keys()
            if not keys:
                messagebox.showinfo("Bilgi", "En az bir MSBT dosyası seçin.")
                return
            out = filedialog.asksaveasfilename(
                title="TSV kaydet",
                defaultextension=".tsv",
                filetypes=[("TSV", "*.tsv")],
                initialfile="starfox64_3d_ceviri.tsv",
            )
            if not out:
                return
            try:
                n = export_tsv(self.rs, Path(out), keys)
                self.set_status(f"{n} metin TSV'ye aktarıldı: {out}")
                messagebox.showinfo("Tamam", f"{n} metin dışa aktarıldı.\n\ntranslation sütununu Türkçeye çevirin.")
            except Exception as exc:
                messagebox.showerror("Hata", str(exc))

        def import_translation(self) -> None:
            if not self.rs:
                messagebox.showinfo("Bilgi", "Önce Resources.zip açın.")
                return
            path = filedialog.askopenfilename(title="Çeviri TSV seç", filetypes=[("TSV", "*.tsv"), ("Tüm dosyalar", "*.*")])
            if not path:
                return
            try:
                imported = import_tsv(Path(path))
                # Kaynakla kontrol et ve GUI patchlerine ekle.
                available = {rel_key(self.rs, p): p for p in find_msbt_files(self.rs)}
                for key, trans in imported.items():
                    if key not in available:
                        raise MSBTError(f"TSV'deki dosya Resources içinde yok: {key}")
                    msbt = parse_msbt(available[key])
                    for idx, tr in trans.items():
                        if idx >= len(msbt.entries):
                            raise MSBTError(f"{key}: index {idx} yok")
                        markup_to_raw(tr, msbt.endian, msbt.encoding_byte, msbt.entries[idx].text)
                    self.patches.setdefault(key, {}).update(trans)
                self.set_status(f"TSV içe aktarıldı: {sum(len(v) for v in imported.values())} satır")
                # Tek dosya açıksa görünümü yenile.
                if self.current_key and self.current_key in imported:
                    self.on_file_select()
            except Exception as exc:
                messagebox.showerror("İçe aktarma hatası", str(exc))

        def build_zip(self) -> None:
            if not self.rs:
                messagebox.showinfo("Bilgi", "Önce Resources.zip açın.")
                return
            if self.current_entry_index is not None:
                # Editörde unutulan değişiklik varsa kullanıcı açıkça kaydetsin; sessizce almıyoruz.
                pass
            out = filedialog.asksaveasfilename(
                title="Yamalı ZIP kaydet",
                defaultextension=".zip",
                filetypes=[("ZIP", "*.zip")],
                initialfile="Resources_TR.zip",
            )
            if not out:
                return
            try:
                modified, total = write_patched_zip(self.rs, Path(out), self.patches)
                self.set_status(f"Yama hazır: {out}")
                messagebox.showinfo("Tamam", f"Yama ZIP'i oluşturuldu.\nDeğiştirilen MSBT: {modified}\nToplam dosya: {total}")
            except Exception as exc:
                messagebox.showerror("Paketleme hatası", str(exc))

        def binary_test(self) -> None:
            if not self.rs:
                messagebox.showinfo("Bilgi", "Önce Resources.zip açın.")
                return
            try:
                self.set_status("Binary-identical test çalışıyor...")
                ok, errors = self_test_source(self.rs)
                if errors:
                    messagebox.showerror("Test başarısız", f"{ok} başarılı.\n\n" + "\n".join(errors[:10]))
                else:
                    messagebox.showinfo("Test başarılı", f"{ok} MSBT dosyasının tamamı byte-byte aynı yeniden üretildi.")
                self.set_status(f"Binary test: {ok} başarılı, {len(errors)} hata")
            except Exception as exc:
                messagebox.showerror("Test hatası", str(exc))

        def destroy(self) -> None:
            if self.rs:
                self.rs.close()
            super().destroy()

    App().mainloop()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Star Fox 64 3D MSBT Türkçe çeviri/enjeksiyon aracı")
    sub = p.add_subparsers(dest="command")

    pa = sub.add_parser("analyze", help="Resources içindeki MSBT dosyalarını listele")
    pa.add_argument("source", help="Resources.zip veya klasör")
    pa.set_defaults(func=cmd_analyze)

    pe = sub.add_parser("export", help="MSBT metinlerini TSV'ye çıkar")
    pe.add_argument("source", help="Resources.zip veya klasör")
    pe.add_argument("output", help="Çıkış .tsv")
    pe.add_argument("--lang", choices=["EN", "DE", "FR", "IT", "ES", "JA", "en", "de", "fr", "it", "es", "ja"], help="Sadece tahmin edilen dili aktar")
    pe.set_defaults(func=cmd_export)

    pb = sub.add_parser("build", help="TSV çevirisini Resources ZIP'e geri enjekte et")
    pb.add_argument("source", help="Orijinal Resources.zip veya klasör")
    pb.add_argument("tsv", help="Düzenlenmiş .tsv")
    pb.add_argument("output", help="Çıkış Resources_TR.zip")
    pb.set_defaults(func=cmd_build)

    pt = sub.add_parser("test", help="Parser/rebuilder byte-byte güvenlik testi")
    pt.add_argument("source", help="Resources.zip veya klasör")
    pt.set_defaults(func=cmd_test)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        return launch_gui()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        return launch_gui()
    try:
        return int(args.func(args))
    except (MSBTError, FileNotFoundError, zipfile.BadZipFile) as exc:
        print("HATA:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
