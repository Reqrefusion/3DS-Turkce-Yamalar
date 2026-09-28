#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import shutil
import struct
import sys
import tempfile
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Optional, Tuple

LANGS = ("eng", "fre", "ger", "ita", "spa")
LANG_DIR = {x: "_" + x for x in LANGS}
ARC_MAGIC = b"ARC\x00"
GMD_MAGIC = b"GMD\x00"
TEX_MAGIC = b"TEX\x00"
ARC_TABLE_OFFSET = 12
ARC_ENTRY_SIZE = 80
ARC_DATA_OFFSET = 0x8000


def log(msg: str) -> None:
    print(msg, flush=True)


class ToolError(RuntimeError):
    pass


@dataclass
class ArcEntry:
    index: int
    name_raw: bytes
    name: str
    type_hash: int
    compressed_size: int
    size_flags: int
    data_offset: int
    compressed: bytes


class ArcFile:
    def __init__(self, data: bytes):
        if len(data) < ARC_TABLE_OFFSET or data[:4] != ARC_MAGIC:
            raise ToolError("Geçerli bir MT Framework ARC dosyası değil.")
        self.original = data
        self.header = bytearray(data[:ARC_TABLE_OFFSET])
        self.arc_marker, self.file_count = struct.unpack_from("<HH", data, 4)
        self.entries: List[ArcEntry] = []
        table_end = ARC_TABLE_OFFSET + self.file_count * ARC_ENTRY_SIZE
        if table_end > len(data):
            raise ToolError("ARC dosya tablosu bozuk veya eksik.")
        for i in range(self.file_count):
            off = ARC_TABLE_OFFSET + i * ARC_ENTRY_SIZE
            name_raw = data[off:off + 64]
            name = name_raw.split(b"\0", 1)[0].decode("ascii", "replace")
            type_hash, csize, size_flags, data_off = struct.unpack_from("<IIII", data, off + 64)
            if data_off + csize > len(data):
                raise ToolError(f"ARC öğesi dosya dışına taşıyor: {i} {name}")
            self.entries.append(
                ArcEntry(i, name_raw, name, type_hash, csize, size_flags, data_off,
                         data[data_off:data_off + csize])
            )

    def unpack(self, index: int) -> bytes:
        e = self.entries[index]
        try:
            return zlib.decompress(e.compressed)
        except zlib.error as exc:
            raise ToolError(f"ARC öğesi açılamadı: {index} {e.name}: {exc}") from exc

    def rebuild(self, replacements: Dict[int, bytes]) -> bytes:
        if not replacements:
            return self.original

        table = bytearray(self.original[:ARC_DATA_OFFSET])
        if len(table) < ARC_DATA_OFFSET:
            table.extend(b"\0" * (ARC_DATA_OFFSET - len(table)))
        payloads: List[bytes] = []
        cursor = ARC_DATA_OFFSET

        for e in self.entries:
            if e.index in replacements:
                raw = replacements[e.index]
                comp = zlib.compress(raw, 6)
                size_flags = (e.size_flags & 0xF0000000) | (len(raw) & 0x0FFFFFFF)
            else:
                comp = e.compressed
                size_flags = e.size_flags

            off = ARC_TABLE_OFFSET + e.index * ARC_ENTRY_SIZE
            struct.pack_into("<I", table, off + 68, len(comp))
            struct.pack_into("<I", table, off + 72, size_flags)
            struct.pack_into("<I", table, off + 76, cursor)
            payloads.append(comp)
            cursor += len(comp)

        return bytes(table) + b"".join(payloads)


class GmdFile:
    def __init__(self, data: bytes):
        if len(data) < 33 or data[:4] != GMD_MAGIC:
            raise ToolError("Geçerli bir GMD değil.")
        self.original = data
        (self.marker, self.language_id, self.key_count, self.value_count,
         self.keys_size, self.values_size, self.name_len) = struct.unpack_from("<7I", data, 4)
        pos = 32
        self.name_bytes = data[pos:pos + self.name_len]
        pos += self.name_len
        if pos >= len(data) or data[pos] != 0:
            raise ToolError("GMD ad sonlandırıcısı bulunamadı.")
        pos += 1
        self.lookup_offset = pos
        self.lookup = data[pos:pos + self.key_count * 8]
        if len(self.lookup) != self.key_count * 8:
            raise ToolError("GMD lookup tablosu eksik.")
        pos += self.key_count * 8
        self.keys_offset = pos
        self.keys_blob = data[pos:pos + self.keys_size]
        pos += self.keys_size
        self.values_offset = pos
        self.values_blob = data[pos:pos + self.values_size]
        pos += self.values_size
        if pos != len(data):
            raise ToolError("GMD boyutu beklenen yapıyla uyuşmuyor.")

        self.name = self.name_bytes.decode("utf-8")
        self.keys = self._split_zero_strings(self.keys_blob, self.key_count, "anahtar")
        self.values = self._split_zero_strings(self.values_blob, self.value_count, "değer")
        self.key_texts = [x.decode("utf-8") for x in self.keys]
        self.value_texts = [x.decode("utf-8") for x in self.values]

        self.value_to_key: Dict[int, str] = {}
        for key_index in range(self.key_count):
            value_index = struct.unpack_from("<I", self.lookup, key_index * 8)[0]
            if value_index >= self.value_count:
                raise ToolError("GMD lookup değeri sınır dışında.")
            if value_index in self.value_to_key:
                # Bu oyunun dosyalarında görülmüyor; yine de kaybı önlemek için birleştir.
                self.value_to_key[value_index] += " | " + self.key_texts[key_index]
            else:
                self.value_to_key[value_index] = self.key_texts[key_index]

    @staticmethod
    def _split_zero_strings(blob: bytes, expected: int, label: str) -> List[bytes]:
        parts = blob.split(b"\0")
        if parts and parts[-1] == b"":
            parts.pop()
        if len(parts) != expected:
            raise ToolError(f"GMD {label} sayısı uyuşmuyor: {len(parts)} != {expected}")
        return parts

    def rebuild_values(self, new_values: List[str]) -> bytes:
        if len(new_values) != self.value_count:
            raise ToolError("GMD yeni değer sayısı uyuşmuyor.")
        enc = [x.encode("utf-8") for x in new_values]
        new_blob = b"\0".join(enc) + b"\0"
        out = bytearray(self.original[:self.values_offset])
        struct.pack_into("<I", out, 0x18, len(new_blob))
        out.extend(new_blob)
        return bytes(out)


@dataclass
class TexInfo:
    width: int
    height: int
    fmt: int
    packed: int


def _morton8(x: int, y: int) -> int:
    r = 0
    for i in range(3):
        r |= ((x >> i) & 1) << (2 * i)
        r |= ((y >> i) & 1) << (2 * i + 1)
    return r




def _etc1_scramble(width: int, height: int) -> List[int]:
    """Nintendo 3DS ETC1/ETC1A4 4x4 blok sıralaması."""
    if width % 4 or height % 4:
        raise ToolError(f"ETC1A4 boyutu 4 piksele hizalı değil: {width}x{height}")
    count = (width // 4) * (height // 4)
    out = [0] * count
    base_acc = row_acc = base_num = row_num = 0
    for tile in range(count):
        if tile % (width // 4) == 0 and tile > 0:
            if row_acc < 1:
                row_acc += 1
                row_num += 2
                base_num = row_num
            else:
                row_acc = 0
                base_num -= 2
                row_num = base_num
        out[tile] = base_num
        if base_acc < 1:
            base_acc += 1
            base_num += 1
        else:
            base_acc = 0
            base_num += 3
    return out


def _decode_etc1a4_alpha(raw: bytes, width: int, height: int) -> bytes:
    scramble = _etc1_scramble(width, height)
    blocks_x = width // 4
    out = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            tile = (y // 4) * blocks_x + (x // 4)
            source_block = scramble[tile]
            k = (x & 3) * 4 + (y & 3)
            b = raw[source_block * 16 + k // 2]
            nibble = ((b >> 4) & 0x0F) if (k & 1) else (b & 0x0F)
            out[y * width + x] = nibble * 17
    return bytes(out)


def _replace_etc1a4_alpha(raw: bytes, width: int, height: int, alpha: bytes) -> bytes:
    """ETC1 renk bloklarını aynen korur; yalnız 4-bit alpha nibbles değişir."""
    if len(alpha) != width * height:
        raise ToolError("ETC1A4 alpha boyutu uyuşmuyor.")
    scramble = _etc1_scramble(width, height)
    blocks_x = width // 4
    out = bytearray(raw)
    for y in range(height):
        for x in range(width):
            tile = (y // 4) * blocks_x + (x // 4)
            source_block = scramble[tile]
            k = (x & 3) * 4 + (y & 3)
            off = source_block * 16 + k // 2
            nibble = max(0, min(15, (int(alpha[y * width + x]) + 8) // 17))
            if k & 1:
                out[off] = (out[off] & 0x0F) | (nibble << 4)
            else:
                out[off] = (out[off] & 0xF0) | nibble
    return bytes(out)


def parse_tex_info(data: bytes) -> TexInfo:
    if len(data) < 16 or data[:4] != TEX_MAGIC:
        raise ToolError("Geçerli bir TEX değil.")
    packed = struct.unpack_from("<I", data, 8)[0]
    mip_count = packed & 0x3F
    width = (packed & 0x0007FFC0) >> 6
    height = (packed & 0xFFF80000) >> 19
    fmt = data[0x0D]
    if mip_count != 1:
        raise ToolError(f"Bu araç yalnız bu paketteki tek mip TEX yapısını destekliyor: {mip_count}")
    if fmt not in (3, 12):
        raise ToolError(f"Bu pakette beklenmeyen TEX biçimi: {fmt}")
    expected = 16 + width * height * (4 if fmt == 3 else 1)
    if len(data) != expected:
        raise ToolError(f"TEX veri boyutu uyuşmuyor: {len(data)} != {expected}")
    return TexInfo(width, height, fmt, packed)


def require_pillow():
    try:
        from PIL import Image
        return Image
    except Exception as exc:
        raise ToolError(
            "PNG işlemleri için Pillow gerekli. KURULUM.bat çalıştırın veya 'py -m pip install Pillow' kullanın."
        ) from exc


def tex_to_png_bytes(data: bytes) -> bytes:
    Image = require_pillow()
    info = parse_tex_info(data)
    raw = data[16:]
    tiles_x = (info.width + 7) // 8

    if info.fmt == 3:
        out = bytearray(info.width * info.height * 4)
        for y in range(info.height):
            for x in range(info.width):
                src = (((y // 8) * tiles_x + (x // 8)) * 64 + _morton8(x & 7, y & 7)) * 4
                dst = (y * info.width + x) * 4
                out[dst:dst + 4] = raw[src:src + 4]
        img = Image.frombytes("RGBA", (info.width, info.height), bytes(out))
    else:
        # Format 12 bu oyunda düz A8 değil Nintendo 3DS ETC1A4'tür.
        # PNG'ye yalnız alpha maskesini beyaz RGBA olarak çıkarıyoruz.
        alpha = _decode_etc1a4_alpha(raw, info.width, info.height)
        rgba = bytearray(info.width * info.height * 4)
        for i, a in enumerate(alpha):
            p = i * 4
            rgba[p:p + 4] = bytes((255, 255, 255, a))
        img = Image.frombytes("RGBA", (info.width, info.height), bytes(rgba))

    bio = io.BytesIO()
    img.save(bio, format="PNG", optimize=False)
    return bio.getvalue()


def png_to_tex_bytes(png_path: Path, original_tex: bytes) -> bytes:
    Image = require_pillow()
    info = parse_tex_info(original_tex)
    with Image.open(png_path) as src:
        img = src.convert("RGBA")
        if img.size != (info.width, info.height):
            raise ToolError(
                f"PNG boyutu değişmiş: {png_path} -> {img.size[0]}x{img.size[1]}, "
                f"beklenen {info.width}x{info.height}"
            )
        pixels = img.tobytes()

    tiles_x = (info.width + 7) // 8
    if info.fmt == 3:
        raw = bytearray(info.width * info.height * 4)
        for y in range(info.height):
            for x in range(info.width):
                dst = (((y // 8) * tiles_x + (x // 8)) * 64 + _morton8(x & 7, y & 7)) * 4
                src_off = (y * info.width + x) * 4
                raw[dst:dst + 4] = pixels[src_off:src_off + 4]
    else:
        alpha = bytearray(info.width * info.height)
        for y in range(info.height):
            for x in range(info.width):
                src_off = (y * info.width + x) * 4
                r, g, b, a = pixels[src_off:src_off + 4]
                # Çıkarılan dosyalarda maske alpha kanalındadır. Tam opak bir gri görsel
                # düzenlendiyse parlaklığı alpha olarak da kabul et.
                if a == 255 and not (r == 255 and g == 255 and b == 255):
                    a = (int(r) * 299 + int(g) * 587 + int(b) * 114 + 500) // 1000
                alpha[y * info.width + x] = a
        # ETC1 renk bloklarını değiştirmeden yalnız alpha nibbles'ını güncelle.
        raw = _replace_etc1a4_alpha(original_tex[16:], info.width, info.height, bytes(alpha))

    return original_tex[:16] + bytes(raw)


def images_equal(path_a: Path, path_b: Path) -> bool:
    if not path_a.exists() or not path_b.exists():
        return False
    if path_a.read_bytes() == path_b.read_bytes():
        return True
    Image = require_pillow()
    try:
        with Image.open(path_a) as a, Image.open(path_b) as b:
            aa = a.convert("RGBA")
            bb = b.convert("RGBA")
            return aa.size == bb.size and aa.tobytes() == bb.tobytes()
    except Exception:
        return False


def safe_slug(internal_name: str) -> str:
    leaf = internal_name.replace("/", "\\").split("\\")[-1]
    leaf = re.sub(r"(?i)(?:_eng|_fre|_fra|_ger|_ita|_spa)(?=_|$)", "", leaf)
    leaf = re.sub(r"[^A-Za-z0-9._-]+", "_", leaf).strip("._-")
    leaf = re.sub(r"_+", "_", leaf)
    return (leaf or "asset")[:90]


class SourceSet:
    """Reads source language trees from a folder or ZIP without changing their layout."""

    def __init__(self, source: Path):
        self.source = source
        self.zip: Optional[zipfile.ZipFile] = None
        self.root: Optional[Path] = None
        self.zip_prefix = ""

        if source.is_file() and source.suffix.lower() == ".zip":
            self.zip = zipfile.ZipFile(source, "r")
            names = [n for n in self.zip.namelist() if not n.endswith("/")]
            prefixes = []
            for n in names:
                parts = PurePosixPath(n).parts
                for i, part in enumerate(parts):
                    if part in LANG_DIR.values():
                        prefixes.append("/".join(parts[:i]))
                        break
            if not prefixes:
                raise ToolError("ZIP içinde _eng/_fre/_ger/_ita/_spa klasörleri bulunamadı.")
            # En sık kullanılan ortak öneki seç.
            from collections import Counter
            self.zip_prefix = Counter(prefixes).most_common(1)[0][0]
        elif source.is_dir():
            if all((source / LANG_DIR[x]).is_dir() for x in LANGS):
                self.root = source
            else:
                found = None
                for d in source.rglob("_eng"):
                    if d.is_dir():
                        parent = d.parent
                        if all((parent / LANG_DIR[x]).is_dir() for x in LANGS):
                            found = parent
                            break
                if found is None:
                    raise ToolError("Kaynak klasörde beş dil klasörü birlikte bulunamadı.")
                self.root = found
        else:
            raise ToolError("Kaynak bir klasör veya .zip olmalı.")

    def close(self) -> None:
        if self.zip is not None:
            self.zip.close()

    def _zip_name(self, lang: str, rel: str) -> str:
        parts = []
        if self.zip_prefix:
            parts.append(self.zip_prefix.strip("/"))
        parts.append(LANG_DIR[lang])
        parts.append(rel.replace("\\", "/").lstrip("/"))
        return "/".join(parts)

    def read(self, lang: str, rel: str) -> bytes:
        if self.zip is not None:
            name = self._zip_name(lang, rel)
            try:
                return self.zip.read(name)
            except KeyError as exc:
                raise ToolError(f"ZIP içinde dosya bulunamadı: {name}") from exc
        assert self.root is not None
        p = self.root / LANG_DIR[lang] / Path(rel)
        if not p.is_file():
            raise ToolError(f"Dosya bulunamadı: {p}")
        return p.read_bytes()

    def arc_relpaths(self, lang: str) -> List[str]:
        if self.zip is not None:
            prefix = self._zip_name(lang, "")
            if not prefix.endswith("/"):
                prefix += "/"
            out = []
            for n in self.zip.namelist():
                if n.startswith(prefix) and n.lower().endswith(".arc") and not n.endswith("/"):
                    out.append(n[len(prefix):])
            return sorted(set(out))
        assert self.root is not None
        base = self.root / LANG_DIR[lang]
        return sorted(p.relative_to(base).as_posix() for p in base.rglob("*.arc"))

    def all_relpaths(self, lang: str) -> List[str]:
        if self.zip is not None:
            prefix = self._zip_name(lang, "")
            if not prefix.endswith("/"):
                prefix += "/"
            return sorted(
                n[len(prefix):] for n in self.zip.namelist()
                if n.startswith(prefix) and not n.endswith("/")
            )
        assert self.root is not None
        base = self.root / LANG_DIR[lang]
        return sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())


def load_arc_set(src: SourceSet, rel: str) -> Dict[str, ArcFile]:
    return {lang: ArcFile(src.read(lang, rel)) for lang in LANGS}


def validate_cross_language_arc(rel: str, arcs: Dict[str, ArcFile]) -> None:
    counts = {lang: len(a.entries) for lang, a in arcs.items()}
    if len(set(counts.values())) != 1:
        raise ToolError(f"ARC öğe sayıları eşleşmiyor: {rel}: {counts}")
    count = next(iter(counts.values()))
    for i in range(count):
        sigs = {}
        for lang, arc in arcs.items():
            raw = arc.unpack(i)
            sigs[lang] = raw[:4]
        if len(set(sigs.values())) != 1:
            raise ToolError(f"ARC öğe türleri diller arasında eşleşmiyor: {rel} entry {i}: {sigs}")
        if next(iter(sigs.values())) == GMD_MAGIC:
            gm = {lang: GmdFile(arcs[lang].unpack(i)) for lang in LANGS}
            first = gm["eng"]
            for lang in LANGS[1:]:
                other = gm[lang]
                if other.key_texts != first.key_texts or other.key_count != first.key_count \
                        or other.value_count != first.value_count:
                    raise ToolError(f"GMD anahtar yapısı eşleşmiyor: {rel} entry {i}, {lang}")


def extract_texts(src: SourceSet, workspace: Path) -> Tuple[int, int]:
    out_root = workspace / "texts"
    out_root.mkdir(parents=True, exist_ok=True)
    arc_count = 0
    row_count = 0

    for rel in src.arc_relpaths("eng"):
        arcs = load_arc_set(src, rel)
        has_gmd = False
        rows = []
        entry_count = len(arcs["eng"].entries)
        if any(len(arcs[x].entries) != entry_count for x in LANGS):
            raise ToolError(f"ARC yapısı diller arasında eşleşmiyor: {rel}")

        for entry_index in range(entry_count):
            raws = {lang: arcs[lang].unpack(entry_index) for lang in LANGS}
            if raws["eng"][:4] != GMD_MAGIC:
                continue
            if any(raws[x][:4] != GMD_MAGIC for x in LANGS):
                raise ToolError(f"GMD öğesi diller arasında eşleşmiyor: {rel} entry {entry_index}")
            has_gmd = True
            gm = {lang: GmdFile(raws[lang]) for lang in LANGS}
            first = gm["eng"]
            for lang in LANGS[1:]:
                if gm[lang].key_texts != first.key_texts or gm[lang].value_count != first.value_count:
                    raise ToolError(f"GMD anahtar/değer yapısı eşleşmiyor: {rel} entry {entry_index}")
            for value_index in range(first.value_count):
                row = {
                    "arc_entry": entry_index,
                    "gmd": first.name,
                    "value_index": value_index,
                    "key": first.value_to_key.get(value_index, ""),
                }
                for lang in LANGS:
                    row[lang] = gm[lang].value_texts[value_index]
                row["tur"] = row["eng"]
                rows.append(row)

        if not has_gmd:
            continue

        csv_path = out_root / (rel + ".csv")
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        # Yeniden çıkarma yapılırsa kullanıcının tur sütunundaki mevcut çevirilerini koru.
        old_tur = {}
        if csv_path.exists():
            try:
                with csv_path.open("r", encoding="utf-8-sig", newline="") as oldf:
                    for oldrow in csv.DictReader(oldf):
                        old_tur[(int(oldrow["arc_entry"]), int(oldrow["value_index"]))] = oldrow.get("tur", "")
            except Exception:
                old_tur = {}
        for row in rows:
            k = (int(row["arc_entry"]), int(row["value_index"]))
            if k in old_tur:
                row["tur"] = old_tur[k]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["arc_entry", "gmd", "value_index", "key", *LANGS, "tur"],
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            writer.writerows(rows)
        arc_count += 1
        row_count += len(rows)
        log(f"[metin] {rel} -> {csv_path.relative_to(workspace)} ({len(rows)} satır)")

    return arc_count, row_count


def extract_images(src: SourceSet, workspace: Path) -> Tuple[int, int]:
    out_root = workspace / "images"
    out_root.mkdir(parents=True, exist_ok=True)
    arc_count = 0
    asset_count = 0

    for rel in src.arc_relpaths("eng"):
        arcs = load_arc_set(src, rel)
        entry_count = len(arcs["eng"].entries)
        if any(len(arcs[x].entries) != entry_count for x in LANGS):
            raise ToolError(f"ARC yapısı diller arasında eşleşmiyor: {rel}")

        tex_indices = []
        for i in range(entry_count):
            raw = arcs["eng"].unpack(i)
            if raw[:4] == TEX_MAGIC:
                tex_indices.append(i)
        if not tex_indices:
            continue

        arc_dir = out_root / rel
        arc_dir.mkdir(parents=True, exist_ok=True)
        meta_rows = []
        for i in tex_indices:
            info_ref = parse_tex_info(arcs["eng"].unpack(i))
            names = {lang: arcs[lang].entries[i].name for lang in LANGS}
            slug = safe_slug(names["eng"])
            stem = f"{i:03d}_{slug}"
            for lang in LANGS:
                raw = arcs[lang].unpack(i)
                if raw[:4] != TEX_MAGIC:
                    raise ToolError(f"TEX öğesi diller arasında eşleşmiyor: {rel} entry {i}")
                info = parse_tex_info(raw)
                if (info.width, info.height, info.fmt) != (info_ref.width, info_ref.height, info_ref.fmt):
                    raise ToolError(f"TEX özellikleri diller arasında eşleşmiyor: {rel} entry {i}")
                png_path = arc_dir / f"{stem}.{lang}.png"
                if not png_path.exists():
                    png_path.write_bytes(tex_to_png_bytes(raw))
            eng_png = arc_dir / f"{stem}.eng.png"
            tur_png = arc_dir / f"{stem}.tur.png"
            # Mevcut Türkçe düzenlemeyi yeniden çıkarma sırasında ezme.
            if not tur_png.exists():
                shutil.copyfile(eng_png, tur_png)
            meta = {
                "arc_entry": i,
                "asset": stem,
                "width": info_ref.width,
                "height": info_ref.height,
                "format": "RGBA" if info_ref.fmt == 3 else "ALPHA",
            }
            for lang in LANGS:
                meta[lang + "_name"] = names[lang]
            meta_rows.append(meta)
            asset_count += 1

        with (arc_dir / "assets.csv").open("w", encoding="utf-8-sig", newline="") as f:
            fields = ["arc_entry", "asset", "width", "height", "format"] + [x + "_name" for x in LANGS]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(meta_rows)
        arc_count += 1
        log(f"[resim] {rel} -> {len(tex_indices)} görsel")

    return arc_count, asset_count


def read_text_changes(workspace: Path) -> Dict[str, Dict[int, Dict[int, str]]]:
    root = workspace / "texts"
    changes: Dict[str, Dict[int, Dict[int, str]]] = {}
    if not root.is_dir():
        return changes
    for csv_path in root.rglob("*.arc.csv"):
        rel = csv_path.relative_to(root).as_posix()
        rel_arc = rel[:-4]  # .csv kaldır, .arc kalsın
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            required = {"arc_entry", "value_index", "eng", "tur"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ToolError(f"CSV sütunları eksik: {csv_path}")
            for row in reader:
                tur = row.get("tur", "")
                eng = row.get("eng", "")
                if tur == eng:
                    continue
                ei = int(row["arc_entry"])
                vi = int(row["value_index"])
                changes.setdefault(rel_arc, {}).setdefault(ei, {})[vi] = tur
    return changes


def read_image_changes(workspace: Path) -> Dict[str, Dict[int, Path]]:
    root = workspace / "images"
    changes: Dict[str, Dict[int, Path]] = {}
    if not root.is_dir():
        return changes
    for arc_dir in root.rglob("*.arc"):
        if not arc_dir.is_dir():
            continue
        rel_arc = arc_dir.relative_to(root).as_posix()
        for tur_png in arc_dir.glob("*.tur.png"):
            m = re.match(r"^(\d+)_.*\.tur\.png$", tur_png.name, re.IGNORECASE)
            if not m:
                continue
            idx = int(m.group(1))
            eng_png = tur_png.with_name(tur_png.name[:-8] + ".eng.png")
            if images_equal(tur_png, eng_png):
                continue
            changes.setdefault(rel_arc, {})[idx] = tur_png
    return changes


# --- Türkçe GFD/ETC1A4 font desteği ---
_TURKISH_FONT_TARGETS = "ÇçĞğİıÖöŞşÜüâîû“"
# V3: Türkçe glifler renderer'ın zaten kullandığı Latin sayfa-0 üzerinde tutulur.
# Ç/ç hücreleri aynı yerde kalır ama görünür cedilla maskesi düzeltilir. Yeni glifler
# yalnız Türkçede kullanılmayan mevcut Latin hücrelerine yazılır; descriptor sayısı
# değişmez. Böylece hem boş-glif sorunu hem de baseline kaymaları önlenir.
_TURKISH_FONT_MISSING = "ĞğİıÖöŞşÜü“"
_TURKISH_FONT_DONOR_CPS = [
    0x00C0, 0x00C8, 0x00C9, 0x00CA, 0x00CE, 0x00D4, 0x00E0, 0x00EA,
    0x00EB, 0x00EF, 0x00F4, 0x00F9, 0x0153, 0x2010, 0x2015, 0x2163,
]


def _parse_gfd_font(data: bytes):
    if len(data) < 0x38 or data[:4] != b"GFD\x00":
        raise ToolError("Geçerli bir GFD font tanımı değil.")
    font_size = struct.unpack_from("<I", data, 0x14)[0]
    page_count = struct.unpack_from("<I", data, 0x18)[0]
    count = struct.unpack_from("<I", data, 0x1C)[0]
    end = 0x38 + count * 16
    if end != len(data):
        raise ToolError(f"Beklenmeyen GFD boyutu: {len(data)} != {end}")
    desc = [struct.unpack_from("<8H", data, 0x38 + i * 16) for i in range(count)]
    return font_size, page_count, desc


def _rebuild_gfd_font(data: bytes, desc) -> bytes:
    out = bytearray(data[:0x38])
    struct.pack_into("<I", out, 0x1C, len(desc))
    for d in sorted(desc, key=lambda x: x[6]):
        out += struct.pack("<8H", *d)
    return bytes(out)


def _font_page_base(gfd_index: int) -> int:
    try:
        return {2: 0, 5: 3, 9: 6}[gfd_index]
    except KeyError as exc:
        raise ToolError(f"Bilinmeyen font GFD entry: {gfd_index}") from exc


def _font_alpha_image(tex: bytes):
    Image = require_pillow()
    info = parse_tex_info(tex)
    if info.fmt != 12:
        raise ToolError("Font TEX biçimi ETC1A4 (12) değil.")
    alpha = _decode_etc1a4_alpha(tex[16:], info.width, info.height)
    return Image.frombytes("L", (info.width, info.height), alpha)


def _font_tex_with_alpha(original_tex: bytes, alpha_img) -> bytes:
    info = parse_tex_info(original_tex)
    if alpha_img.size != (info.width, info.height):
        raise ToolError("Font atlası boyutu değişmiş.")
    raw = _replace_etc1a4_alpha(
        original_tex[16:], info.width, info.height, alpha_img.convert("L").tobytes()
    )
    return original_tex[:16] + raw


def _font_crop_glyph(arc: ArcFile, gfd_index: int, ch: str):
    font_size, _pages, desc = _parse_gfd_font(arc.unpack(gfd_index))
    mapping = {d[6]: d for d in desc}
    cp = ord(ch)
    if cp not in mapping:
        raise ToolError(f"Kaynak fontta glif yok: {ch} U+{cp:04X}")
    d = mapping[cp]
    tex = arc.unpack(_font_page_base(gfd_index) + d[0])
    atlas = _font_alpha_image(tex)
    return atlas.crop((d[2], d[3], d[2] + d[1], d[3] + font_size)), d


def _font_shift_mask(mask, dy: int):
    Image = require_pillow()
    out = Image.new("L", mask.size, 0)
    out.paste(mask, (0, dy))
    return out


def _font_add_breve(mask, lowercase: bool = False, xheight_top: Optional[int] = None):
    """Draw a symmetric, two-row breve above the unchanged G/g body."""
    out = mask.copy()
    p = out.load()
    w, h = out.size
    bbox = mask.getbbox()
    top = bbox[1] if bbox else (7 if lowercase else 3)
    y0 = max(0, top - 3)
    cx = (w - 1) // 2
    pts = [(cx - 2, y0, 221), (cx + 2, y0, 221),
           (cx - 2, y0 + 1, 187), (cx + 2, y0 + 1, 187),
           (cx - 1, y0 + 2, 204), (cx, y0 + 2, 255),
           (cx + 1, y0 + 2, 204)]
    for x, y, a in pts:
        if 0 <= x < w and 0 <= y < h:
            p[x, y] = max(p[x, y], a)
    return out


def _font_add_i_dot(mask):
    """Büyük İ için kompakt nokta; I gövdesinin genişliği ve baseline'ı değişmez."""
    out = mask.copy()
    p = out.load()
    w, h = out.size
    bbox = mask.getbbox()
    top = bbox[1] if bbox else 3
    y0 = max(0, top - 3)
    cx = (w - 1) // 2
    pts = [(cx, y0, 255), (cx, y0 + 1, 255)]
    if w >= 5:
        pts += [(max(0, cx - 1), y0 + 1, 170), (min(w - 1, cx + 1), y0 + 1, 170)]
    for x, y, a in pts:
        if 0 <= y < h:
            p[x, y] = max(p[x, y], a)
    return out


def _font_dotless_i(mask, xheight_top: Optional[int] = None):
    """Noktasız ı: yalnız üst nokta bileşenini temizler, gövde yüksekliğini korur."""
    out = mask.copy()
    pix = out.load()
    w, h = out.size
    if xheight_top is None:
        xheight_top = 7 if h >= 16 else 6
    for y in range(max(0, min(h, xheight_top))):
        for x in range(w):
            pix[x, y] = 0
    return out


def _font_add_cedilla_inline(mask):
    """Reserve two baseline rows for a connected, curved cedilla."""
    out = _font_shift_mask(mask, -2)
    p = out.load()
    w, h = out.size
    cx = (w - 1) // 2
    # The extra row gives the hook an actual curve at 14 and 16 px.
    for x, y, a in ((cx, h - 3, 204), (cx, h - 2, 255),
                    (min(w - 1, cx + 1), h - 2, 187),
                    (cx, h - 1, 187), (max(0, cx - 1), h - 1, 255),
                    (max(0, cx - 2), h - 1, 136)):
        p[x, y] = max(p[x, y], a)
    return out


def _font_mirror_shape_in_place(mask):
    """Tırnak şeklini kendi bbox'ı içinde aynalar; hücrenin öbür ucuna taşımaz."""
    Image = require_pillow()
    bbox = mask.getbbox()
    if bbox is None:
        return mask.copy()
    shape = mask.crop(bbox).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    out = Image.new("L", mask.size, 0)
    out.paste(shape, (bbox[0], bbox[1]))
    return out


def _font_xheight_top(arc: ArcFile, gfd_index: int) -> int:
    tops = []
    for ch in "acenorsuvxz":
        try:
            im, _d = _font_crop_glyph(arc, gfd_index, ch)
        except ToolError:
            continue
        b = im.getbbox()
        if b is not None:
            tops.append(b[1])
    if not tops:
        fs, _p, _d = _parse_gfd_font(arc.unpack(gfd_index))
        return 7 if fs >= 16 else 6
    tops.sort()
    return tops[len(tops) // 2]


def _font_generated(base_mask, ch: str, xheight_top: Optional[int] = None):
    if ch == "Ğ":
        return _font_add_breve(base_mask, False, xheight_top)
    if ch == "ğ":
        return _font_add_breve(base_mask, True, xheight_top)
    if ch == "İ":
        return _font_add_i_dot(base_mask)
    if ch == "ı":
        return _font_dotless_i(base_mask, xheight_top)
    if ch in ("Ç", "ç", "Ş", "ş"):
        return _font_add_cedilla_inline(base_mask)
    if ch == "“":
        return _font_mirror_shape_in_place(base_mask)
    raise ToolError(f"Üretilemeyen font karakteri: {ch}")

def _font_find_slot(desc, page: int, width: int, font_size: int, texw: int, texh: int):
    byrow = {}
    for d in desc:
        if d[0] == page:
            byrow.setdefault(d[3], []).append((d[2], d[2] + d[1]))
    ys = sorted(byrow)
    diffs = [b - a for a, b in zip(ys, ys[1:]) if b > a]
    pitch = min(diffs) if diffs else font_size + 5
    candidates = list(ys)
    y = ys[-1] + pitch if ys else 0
    while y + font_size <= texh:
        candidates.append(y)
        y += pitch
    for y in candidates:
        if y + font_size > texh:
            continue
        intervals = sorted(byrow.get(y, []))
        x = 0
        for a, b in intervals:
            if x + width <= a:
                return x, y
            x = max(x, b + 1)
        if x + width <= texw:
            return x, y
    raise ToolError("Font atlasında Türkçe glifler için boş alan bulunamadı.")


def _patch_one_gfd_font(base_arc: ArcFile, fre_arc: ArcFile, ger_arc: ArcFile, gfd_index: int):
    """V6: Latin sayfa-0, sabit advance/genişlik ve gerçek aksan/cedilla hizası."""
    font_size, pages, desc = _parse_gfd_font(fre_arc.unpack(gfd_index))
    base_fs, base_pages, _base_desc = _parse_gfd_font(base_arc.unpack(gfd_index))
    if (font_size, pages) != (base_fs, base_pages):
        raise ToolError("Dil fontlarının boyut/sayfa yapısı eşleşmiyor.")

    tex_base = _font_page_base(gfd_index)
    atlases = [_font_alpha_image(fre_arc.unpack(tex_base + p)) for p in range(pages)]
    mapping = {d[6]: d for d in desc}
    xheight_top = _font_xheight_top(fre_arc, gfd_index)
    Image = require_pillow()

    # Ç/ç mevcut hücrelerinde kalır; yalnız görünür cedilla kuyruğu eklenir.
    for ch, base_ch in (("Ç", "C"), ("ç", "c")):
        td = mapping.get(ord(ch))
        if td is None or td[0] != 0:
            continue
        base_mask, _ = _font_crop_glyph(fre_arc, gfd_index, base_ch)
        fixed = _font_generated(base_mask, ch, xheight_top)
        atlases[0].paste(Image.new("L", (td[1], font_size), 0), (td[2], td[3]))
        if fixed.width > td[1]:
            fixed = fixed.crop((0, 0, td[1], font_size))
        atlases[0].paste(fixed, (td[2], td[3]))

    donors = [mapping[cp] for cp in _TURKISH_FONT_DONOR_CPS
              if cp in mapping and mapping[cp][0] == 0]

    exact = {
        "Ö": (ger_arc, "Ö"), "ö": (ger_arc, "ö"),
        "Ü": (ger_arc, "Ü"), "ü": (ger_arc, "ü"),
    }
    bases = {"Ğ": "G", "ğ": "g", "İ": "I", "ı": "i",
             "Ş": "S", "ş": "s", "“": "”"}

    items = []
    for ch in _TURKISH_FONT_MISSING:
        if ord(ch) in mapping:
            continue
        if ch in exact:
            source_arc, source_ch = exact[ch]
            mask, template = _font_crop_glyph(source_arc, gfd_index, source_ch)
        else:
            base_ch = bases[ch]
            mask, template = _font_crop_glyph(fre_arc, gfd_index, base_ch)
            mask = _font_generated(mask, ch, xheight_top)
        items.append((ch, mask, template))

    remaining = list(donors)
    replaced = {}
    for ch, mask, template in sorted(items, key=lambda z: z[2][1], reverse=True):
        fits = sorted((d for d in remaining if d[1] >= template[1]),
                      key=lambda d: (d[1], d[6]))
        if not fits:
            raise ToolError(f"Latin font atlasında {ch} için güvenli donor yuva bulunamadı.")
        donor = fits[0]
        remaining.remove(donor)
        x, y = donor[2], donor[3]
        atlases[0].paste(Image.new("L", (donor[1], font_size), 0), (x, y))
        if mask.width > template[1]:
            mask = mask.crop((0, 0, template[1], font_size))
        atlases[0].paste(mask, (x, y))
        nd = (0, template[1], x, y, template[4], template[5], ord(ch), template[7])
        replaced[donor[6]] = nd

    new_desc = [replaced.get(d[6], d) for d in desc]
    cps = [d[6] for d in new_desc]
    if len(cps) != len(set(cps)):
        raise ToolError("Türkçe font descriptor kodları çakıştı.")

    new_map = {d[6]: d for d in new_desc}
    pairs = {"Ç": "C", "ç": "c", "Ğ": "G", "ğ": "g", "İ": "I", "ı": "i", "Ş": "S", "ş": "s", "“": "”"}
    for ch in _TURKISH_FONT_TARGETS:
        d = new_map.get(ord(ch))
        if d is None:
            raise ToolError(f"Türkçe glif descriptor eksik: {ch}")
        if d[0] != 0:
            raise ToolError(f"Türkçe glif Latin sayfa 0 dışında kaldı: {ch}")
        crop = atlases[0].crop((d[2], d[3], d[2] + d[1], d[3] + font_size))
        if crop.getbbox() is None:
            raise ToolError(f"Türkçe glif atlas hücresi boş: {ch}")
        if ch in pairs and ord(pairs[ch]) in new_map:
            bd = new_map[ord(pairs[ch])]
            if ch != "“" and (d[4], d[5]) != (bd[4], bd[5]):
                raise ToolError(f"Türkçe glif metriği gövdeden sapmış: {ch}")

    ddot = new_map.get(ord("ı"))
    if ddot is not None:
        c = atlases[0].crop((ddot[2], ddot[3], ddot[2] + ddot[1], ddot[3] + font_size))
        b = c.getbbox()
        if b and b[1] < max(0, xheight_top - 1):
            raise ToolError("Noktasız ı üstünde artık nokta/piksel kaldı.")
    oq = new_map.get(ord("“")); cq = new_map.get(ord("”"))
    if oq is not None and cq is not None:
        oc = atlases[0].crop((oq[2], oq[3], oq[2] + oq[1], oq[3] + font_size)).getbbox()
        if oc and oc[0] > (oq[1] // 2):
            raise ToolError("Açılış tırnağı hücrenin sağ tarafına kaymış.")

    # V6 görsel sınır kontrolleri: cedilla son satıra inmeli, breve gövdenin üstünde kalmalı.
    for ch in "ÇçŞş":
        d = new_map[ord(ch)]
        c = atlases[0].crop((d[2], d[3], d[2] + d[1], d[3] + font_size))
        if not any(c.getpixel((x, font_size - 1)) > 0 for x in range(c.width)):
            raise ToolError(f"Cedilla kuyruğu alt satıra inmiyor: {ch}")
    for ch, base_ch in (("Ğ", "G"), ("ğ", "g"), ("İ", "I")):
        d = new_map[ord(ch)]; b = new_map[ord(base_ch)]
        c = atlases[0].crop((d[2], d[3], d[2] + d[1], d[3] + font_size))
        bc = atlases[0].crop((b[2], b[3], b[2] + b[1], b[3] + font_size))
        cb = c.getbbox(); bb = bc.getbbox()
        if cb is None or bb is None or cb[1] >= bb[1]:
            raise ToolError(f"Üst işaret gövdeden ayrışmıyor: {ch}")

    repl = {}
    for p, atlas in enumerate(atlases):
        idx = tex_base + p
        repl[idx] = _font_tex_with_alpha(fre_arc.unpack(idx), atlas)
    repl[gfd_index] = _rebuild_gfd_font(base_arc.unpack(gfd_index), new_desc)
    return repl

def _font_used_output_chars(out_lang: Path):
    used = set()
    for arc_path in out_lang.rglob("*.arc"):
        arc = ArcFile(arc_path.read_bytes())
        for i in range(len(arc.entries)):
            raw = arc.unpack(i)
            if raw[:4] == GMD_MAGIC:
                gmd = GmdFile(raw)
                for text in gmd.value_texts:
                    used.update(text)
    return used

def apply_turkish_font_fix(src: SourceSet, out_lang: Path) -> None:
    """Build çıktısındaki dört GFD fontunu Türkçe metinlerin kullandığı tüm gliflerle günceller."""
    menu_rel = "_GUI/_font/menu.arc"
    common_rel = "_GUI/_font/common.arc"
    menu_path = out_lang / Path(menu_rel)
    common_path = out_lang / Path(common_rel)
    if not menu_path.is_file() or not common_path.is_file():
        raise ToolError("Font ARC dosyaları build çıktısında bulunamadı.")

    used_chars = _font_used_output_chars(out_lang)
    donor_used = [chr(cp) for cp in _TURKISH_FONT_DONOR_CPS if chr(cp) in used_chars]
    if donor_used:
        raise ToolError("Font donor karakterleri Türkçe metinde kullanılıyor: " + "".join(donor_used))

    menu = ArcFile(menu_path.read_bytes())
    fre = ArcFile(src.read("fre", menu_rel))
    ger = ArcFile(src.read("ger", menu_rel))
    replacements = {}
    for gi in (2, 5, 9):
        replacements.update(_patch_one_gfd_font(menu, fre, ger, gi))
    menu_path.write_bytes(menu.rebuild(replacements))

    patched_menu = ArcFile(menu_path.read_bytes())
    common = ArcFile(common_path.read_bytes())
    common_path.write_bytes(common.rebuild({
        0: patched_menu.unpack(0),
        1: patched_menu.unpack(1),
        2: patched_menu.unpack(2),
    }))

    # Son kontrol: geçerli Türkçe metinlerde gereken tüm ek glifler dört GFD'de bulunmalı.
    for arc_path, gi in [(menu_path, 2), (menu_path, 5), (menu_path, 9), (common_path, 2)]:
        a = ArcFile(arc_path.read_bytes())
        _fs, _pages, d = _parse_gfd_font(a.unpack(gi))
        mp = {x[6]: x for x in d}
        missing = [c for c in _TURKISH_FONT_TARGETS if ord(c) not in mp]
        if missing:
            raise ToolError("Font düzeltmesi eksik kaldı: " + "".join(missing))
        for c in _TURKISH_FONT_TARGETS:
            dd = mp[ord(c)]
            if dd[0] != 0:
                raise ToolError(f"Türkçe glif Latin sayfa 0 dışında: {c}")
            tex = a.unpack(_font_page_base(gi) + dd[0])
            atlas = _font_alpha_image(tex)
            if atlas.crop((dd[2], dd[3], dd[2] + dd[1], dd[3] + _fs)).getbbox() is None:
                raise ToolError(f"Türkçe glif atlas hücresi boş: {c}")
    log("[font] Türkçe GFD/ETC1A4 V6 metrik-hizalı glifleri uygulandı: " + _TURKISH_FONT_TARGETS)


def build_turkish(src: SourceSet, workspace: Path, output: Path, base_lang: str = "eng") -> Tuple[int, int, int]:
    if base_lang not in LANGS:
        raise ToolError(f"Geçersiz temel dil: {base_lang}")
    text_changes = read_text_changes(workspace)
    image_changes = read_image_changes(workspace)

    out_lang = output / LANG_DIR[base_lang]
    if out_lang.exists():
        shutil.rmtree(out_lang)
    out_lang.mkdir(parents=True, exist_ok=True)

    changed_arcs = 0
    changed_gmd_entries = 0
    changed_tex_entries = 0

    for rel in src.all_relpaths(base_lang):
        raw_file = src.read(base_lang, rel)
        out_path = out_lang / Path(rel)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not rel.lower().endswith(".arc"):
            out_path.write_bytes(raw_file)
            continue

        arc = ArcFile(raw_file)
        replacements: Dict[int, bytes] = {}

        for entry_index, per_value in text_changes.get(rel, {}).items():
            if entry_index >= len(arc.entries):
                raise ToolError(f"CSV ARC entry sınır dışında: {rel} -> {entry_index}")
            gmd_raw = arc.unpack(entry_index)
            if gmd_raw[:4] != GMD_MAGIC:
                raise ToolError(f"CSV GMD olmayan öğeyi hedefliyor: {rel} -> {entry_index}")
            gmd = GmdFile(gmd_raw)
            vals = list(gmd.value_texts)
            for value_index, text in per_value.items():
                if value_index >= len(vals):
                    raise ToolError(f"CSV GMD value_index sınır dışında: {rel} -> {entry_index}/{value_index}")
                vals[value_index] = text
            replacements[entry_index] = gmd.rebuild_values(vals)
            changed_gmd_entries += 1

        for entry_index, png_path in image_changes.get(rel, {}).items():
            if entry_index >= len(arc.entries):
                raise ToolError(f"PNG ARC entry sınır dışında: {rel} -> {entry_index}")
            tex_raw = arc.unpack(entry_index)
            if tex_raw[:4] != TEX_MAGIC:
                raise ToolError(f"PNG TEX olmayan öğeyi hedefliyor: {rel} -> {entry_index}")
            replacements[entry_index] = png_to_tex_bytes(png_path, tex_raw)
            changed_tex_entries += 1

        if replacements:
            out_path.write_bytes(arc.rebuild(replacements))
            changed_arcs += 1
            log(f"[build] değişti: {rel} ({len(replacements)} öğe)")
        else:
            out_path.write_bytes(raw_file)

    if base_lang == "eng":
        apply_turkish_font_fix(src, out_lang)

    # Workspace'te kaynağa ait olmayan bir ARC hedeflenmişse sessizce atlama.
    source_arcs = set(src.arc_relpaths(base_lang))
    unknown = (set(text_changes) | set(image_changes)) - source_arcs
    if unknown:
        raise ToolError("Workspace içinde kaynakta bulunmayan ARC hedefleri var: " + ", ".join(sorted(unknown)[:10]))

    return changed_arcs, changed_gmd_entries, changed_tex_entries


def verify_source(src: SourceSet) -> Tuple[int, int, int, int]:
    rels = {lang: src.arc_relpaths(lang) for lang in LANGS}
    if any(rels[x] != rels["eng"] for x in LANGS[1:]):
        raise ToolError("Beş dilin ARC dosya listeleri birebir eşleşmiyor.")
    arc_total = len(rels["eng"])
    gmd_total = 0
    tex_total = 0
    gfd_total = 0
    for n, rel in enumerate(rels["eng"], 1):
        arcs = load_arc_set(src, rel)
        validate_cross_language_arc(rel, arcs)
        for i in range(len(arcs["eng"].entries)):
            sig = arcs["eng"].unpack(i)[:4]
            if sig == GMD_MAGIC:
                GmdFile(arcs["eng"].unpack(i))
                gmd_total += 1
            elif sig == TEX_MAGIC:
                parse_tex_info(arcs["eng"].unpack(i))
                tex_total += 1
            elif sig == b"GFD\x00":
                gfd_total += 1
        if n % 50 == 0 or n == arc_total:
            log(f"[kontrol] {n}/{arc_total} ARC")
    return arc_total, gmd_total, tex_total, gfd_total


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Street Fighter 3DS dil ARC/GMD/TEX çıkarma ve geri yazma aracı"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("check", help="Kaynak dilleri ve dosya yapılarını kontrol et")
    q.add_argument("source", type=Path)

    q = sub.add_parser("extract-texts", help="GMD metinlerini ARC bazında CSV'ye çıkar")
    q.add_argument("source", type=Path)
    q.add_argument("workspace", type=Path)

    q = sub.add_parser("extract-images", help="TEX görsellerini ARC bazında PNG'ye çıkar")
    q.add_argument("source", type=Path)
    q.add_argument("workspace", type=Path)

    q = sub.add_parser("extract-all", help="Metin ve görselleri birlikte çıkar")
    q.add_argument("source", type=Path)
    q.add_argument("workspace", type=Path)

    q = sub.add_parser("build", help="tur sütunu ve tur.png dosyalarını mevcut ARC'lere geri yaz")
    q.add_argument("source", type=Path)
    q.add_argument("workspace", type=Path)
    q.add_argument("output", type=Path)
    q.add_argument("--base-lang", choices=LANGS, default="eng")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = make_parser().parse_args(argv)
    src = None
    try:
        src = SourceSet(args.source)
        if args.cmd == "check":
            a, g, t, f = verify_source(src)
            log(f"OK: {a} ARC, temel dilde {g} GMD, {t} TEX, {f} GFD.")
        elif args.cmd == "extract-texts":
            a, r = extract_texts(src, args.workspace)
            log(f"Bitti: {a} ARC için CSV, toplam {r} metin satırı.")
        elif args.cmd == "extract-images":
            a, n = extract_images(src, args.workspace)
            log(f"Bitti: {a} ARC klasöründe {n} görsel varlığı.")
        elif args.cmd == "extract-all":
            a, r = extract_texts(src, args.workspace)
            ia, n = extract_images(src, args.workspace)
            log(f"Bitti: {a} metin ARC / {r} satır; {ia} görsel ARC / {n} görsel.")
        elif args.cmd == "build":
            a, g, t = build_turkish(src, args.workspace, args.output, args.base_lang)
            log(f"Bitti: {a} ARC değişti; {g} GMD ve {t} TEX öğesi güncellendi.")
            log(f"Çıktı: {args.output / LANG_DIR[args.base_lang]}")
        return 0
    except ToolError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2
    finally:
        if src is not None:
            src.close()


if __name__ == "__main__":
    raise SystemExit(main())
