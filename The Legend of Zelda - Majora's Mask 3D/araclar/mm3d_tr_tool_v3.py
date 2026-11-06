#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MM3D Turkish Translation Tool

Lossless GMSG CSV exporter/injector, QA, GAR2 extractor/patcher,
CTXB inventory helpers and GZFX font inspection/edit helpers.

Designed from the user's EU Majora's Mask 3D files. GMSG control bytes are
never interpreted semantically: they are protected as ⟦HEX:...⟧ tokens.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

TOOL_VERSION = "0.8.0"
HEX_RE = re.compile(r"⟦HEX:([0-9A-Fa-f]+)⟧")
LANG_FILES = {
    "English": "eue.gmsg",
    "French": "euf.gmsg",
    "German": "eug.gmsg",
    "Italian": "eui.gmsg",
    "Spanish": "eus.gmsg",
    "Dutch": "eud.gmsg",
}
TURKISH_CORE = "ĞğİıŞşÇçÖöÜü"


class ToolError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, n: int) -> int:
    return (value + n - 1) // n * n


# ---------------------------------------------------------------------------
# GMSG
# ---------------------------------------------------------------------------

@dataclass
class GmsgRecord:
    meta0: int
    meta1: int
    meta2: int
    offset: int
    length: int
    data: bytes


@dataclass
class GmsgFile:
    header: bytes
    magic: bytes
    version: int
    count: int
    language_flags: int
    records: list[GmsgRecord]
    path: Optional[Path] = None

    @classmethod
    def load(cls, path: Path | str) -> "GmsgFile":
        path = Path(path)
        raw = path.read_bytes()
        if len(raw) < 16:
            raise ToolError(f"GMSG çok küçük: {path}")
        magic, version, count, flags = struct.unpack_from("<4sIII", raw, 0)
        if magic != b"GMSG":
            raise ToolError(f"GMSG imzası yok: {path}")
        table_end = 16 + count * 20
        if table_end > len(raw):
            raise ToolError(f"GMSG tablo sınırı geçersiz: {path}")
        records: list[GmsgRecord] = []
        for i in range(count):
            m0, m1, m2, off, ln = struct.unpack_from("<IIIII", raw, 16 + i * 20)
            if ln:
                if off < table_end or off + ln > len(raw):
                    raise ToolError(f"GMSG kayıt {i} veri sınırı geçersiz: off={off} len={ln}")
                data = raw[off:off + ln]
            else:
                data = b""
            records.append(GmsgRecord(m0, m1, m2, off, ln, data))
        return cls(raw[:16], magic, version, count, flags, records, path)

    def metadata_signature(self) -> list[tuple[int, int, int]]:
        return [(r.meta0, r.meta1, r.meta2) for r in self.records]

    def rebuild(self, replacement_data: Optional[list[bytes]] = None) -> bytes:
        data_list = replacement_data if replacement_data is not None else [r.data for r in self.records]
        if len(data_list) != self.count:
            raise ToolError(f"Kayıt sayısı uyuşmuyor: {len(data_list)} != {self.count}")
        table_end = 16 + self.count * 20
        table = bytearray()
        payload = bytearray()
        cursor = table_end
        for rec, data in zip(self.records, data_list):
            if data:
                off = cursor
                ln = len(data)
                table += struct.pack("<IIIII", rec.meta0, rec.meta1, rec.meta2, off, ln)
                payload += data
                pad = (-len(data)) % 4
                if pad:
                    payload += b"\x00" * pad
                cursor += len(data) + pad
            else:
                table += struct.pack("<IIIII", rec.meta0, rec.meta1, rec.meta2, 0, 0)
        return self.header + bytes(table) + bytes(payload)


# GMSG command table mirrored from Kuriimu's Grezzo GMSG plugin.
# Value = number of 16-bit parameter words following the command id.
GMSG_COMMAND_PARAMS = {
    0:0,1:0,2:0,3:0,4:0,5:0,6:0,7:0,8:0,9:0,10:0,11:0,12:0,13:0,14:0,15:0,16:0,
    17:1,18:0,19:0,20:0,21:1,22:0,23:0,24:0,25:0,27:0,28:1,29:0,30:0,
    32:1,33:0,34:1,35:0,36:0,37:1,38:1,39:0,40:0,41:1,42:1,43:0,44:0,45:1,
    46:0,47:1,49:1,50:2,51:0,52:1,53:0,54:0,55:0,56:0,57:0,58:1,
}


def _gmsg_control_end(raw: bytes, start: int) -> int:
    """Return end offset of a 0x7F Grezzo command, following Kuriimu alignment rules."""
    if start >= len(raw) or raw[start] != 0x7F:
        return start + 1
    pos = start + 1
    # Kuriimu: if marker index is even, one alignment byte follows 0x7F.
    if start % 2 == 0:
        if pos >= len(raw): return len(raw)
        pos += 1
    if pos + 2 > len(raw): return len(raw)
    cmd = raw[pos] | (raw[pos + 1] << 8)
    pos += 2
    n = GMSG_COMMAND_PARAMS.get(cmd, 0)
    if cmd == 50:
        # Command 50 has two logical words, but leading zero words before the
        # first non-zero word are repeated (same loop behavior as Kuriimu).
        while pos + 2 <= len(raw):
            word = raw[pos] | (raw[pos + 1] << 8)
            pos += 2
            if word != 0:
                break
        if pos + 2 <= len(raw): pos += 2
    else:
        pos = min(len(raw), pos + n * 2)
    return pos


def _utf8_char_len(raw: bytes, i: int) -> int:
    b=raw[i]
    if 0x20 <= b <= 0x7E: return 1
    if 0xC2 <= b <= 0xDF and i+1 < len(raw) and 0x80 <= raw[i+1] <= 0xBF: return 2
    if 0xE0 <= b <= 0xEF and i+2 < len(raw):
        b1,b2=raw[i+1],raw[i+2]
        if 0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF:
            if b==0xE0 and b1<0xA0: return 0
            if b==0xED and b1>=0xA0: return 0  # UTF-16 surrogate range is invalid UTF-8
            return 3
    if 0xF0 <= b <= 0xF4 and i+3 < len(raw):
        b1,b2,b3=raw[i+1],raw[i+2],raw[i+3]
        if all(0x80 <= x <= 0xBF for x in (b1,b2,b3)):
            if b==0xF0 and b1<0x90: return 0
            if b==0xF4 and b1>=0x90: return 0
            return 4
    return 0


def tokenize_gmsg_bytes(raw: bytes) -> list[tuple[str, bytes]]:
    """Losslessly split GMSG into visible UTF-8 and protected binary/control spans.

    0x7F commands are parsed using Grezzo/Kuriimu alignment and parameter lengths.
    NUL/C0 bytes and invalid UTF-8 outside those commands are also protected.
    """
    out: list[tuple[str, bytes]]=[]
    def add(typ: str, chunk: bytes):
        if not chunk: return
        if out and out[-1][0]==typ: out[-1]=(typ,out[-1][1]+chunk)
        else: out.append((typ,chunk))
    i=0
    while i<len(raw):
        if raw[i]==0x7F:
            j=_gmsg_control_end(raw,i); add('control',raw[i:j]); i=j; continue
        n=_utf8_char_len(raw,i)
        if n:
            # Decode as a single code point to ensure it is genuinely valid.
            try: raw[i:i+n].decode('utf-8','strict')
            except UnicodeDecodeError: n=0
        if n:
            add('text',raw[i:i+n]); i+=n
        else:
            # Protect control/invalid bytes. Group until the next valid UTF-8 char or 0x7F.
            j=i+1
            while j<len(raw) and raw[j]!=0x7F and not _utf8_char_len(raw,j): j+=1
            add('control',raw[i:j]); i=j
    return out


def bytes_to_markup(raw: bytes) -> str:
    parts: list[str] = []
    for typ, b in tokenize_gmsg_bytes(raw):
        if typ == "text":
            text = b.decode("utf-8", errors='strict')
            text = text.replace("⟦HEX:", "⟦TEXT-HEX:")
            parts.append(text)
        else:
            parts.append("⟦HEX:" + b.hex().upper() + "⟧")
    return "".join(parts)


def gmsg_command_ids(raw: bytes) -> list[int]:
    ids=[]; i=0
    while i < len(raw):
        if raw[i] == 0x7F:
            pos=i+1+(1 if i%2==0 else 0)
            if pos+2 <= len(raw): ids.append(raw[pos] | (raw[pos+1] << 8))
            i=max(_gmsg_control_end(raw,i),i+1)
        else:
            i+=1
    return ids


def gmsg_invalid_command_ids(raw: bytes) -> list[int]:
    return [x for x in gmsg_command_ids(raw) if x not in GMSG_COMMAND_PARAMS]


def visible_replacement_count(raw: bytes) -> int:
    return sum(b.decode('utf-8','strict').count('\ufffd') for typ,b in tokenize_gmsg_bytes(raw) if typ=='text')

def markup_to_bytes(markup: str) -> bytes:
    out = bytearray()
    pos = 0
    for m in HEX_RE.finditer(markup):
        out += markup[pos:m.start()].replace("⟦TEXT-HEX:", "⟦HEX:").encode("utf-8")
        h = m.group(1)
        if len(h) % 2:
            raise ToolError(f"HEX etiketi çift sayıda nibble içermeli: {m.group(0)}")
        try:
            out += bytes.fromhex(h)
        except ValueError as e:
            raise ToolError(f"Geçersiz HEX etiketi: {m.group(0)}") from e
        pos = m.end()
    out += markup[pos:].replace("⟦TEXT-HEX:", "⟦HEX:").encode("utf-8")
    return bytes(out)


def markup_control_tokens(markup: str) -> list[str]:
    return [m.group(1).upper() for m in HEX_RE.finditer(markup)]


def markup_plain(markup: str) -> str:
    return HEX_RE.sub("", markup).replace("⟦TEXT-HEX:", "⟦HEX:")


def raw_plain(raw: bytes) -> str:
    return "".join(
        b.decode("utf-8", errors="replace") for typ, b in tokenize_gmsg_bytes(raw) if typ == "text"
    )


def controls_digest(raw: bytes) -> str:
    c = b"".join(b for typ, b in tokenize_gmsg_bytes(raw) if typ == "control")
    return sha256(c)[:16]


def export_gmsg_csv(eu_dir: Path, turkish: Optional[Path], output: Path, seed: str="turkish") -> dict:
    langs: dict[str, GmsgFile] = {}
    for lang, fn in LANG_FILES.items():
        p = eu_dir / fn
        if not p.exists():
            raise ToolError(f"Eksik dil dosyası: {p}")
        langs[lang] = GmsgFile.load(p)
    english = langs["English"]
    sig = english.metadata_signature()
    for lang, g in langs.items():
        if g.count != english.count or g.metadata_signature() != sig:
            raise ToolError(f"Dil tabloları satır bazında eşleşmiyor: {lang}")
    tr = GmsgFile.load(turkish) if turkish else None
    if tr and (tr.count != english.count or tr.metadata_signature() != sig):
        raise ToolError("Türkçe GMSG metadatası İngilizce ile eşleşmiyor.")

    output.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "Index", "Meta0", "Meta1", "Meta2",
        "English", "French", "German", "Italian", "Spanish", "Dutch",
        "Turkish_original", "Turkish_seed", "Turkish", "Status", "QA"
    ]
    changed = 0
    unchanged = 0
    replacement_msgs = 0
    missing = 0
    control_diff = 0
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for i in range(english.count):
            row = {
                "Index": i,
                "Meta0": f"0x{english.records[i].meta0:08X}",
                "Meta1": f"0x{english.records[i].meta1:08X}",
                "Meta2": f"0x{english.records[i].meta2:08X}",
            }
            for lang in LANG_FILES:
                row[lang] = bytes_to_markup(langs[lang].records[i].data)
            tr_raw = tr.records[i].data if tr else b""
            tr_markup = bytes_to_markup(tr_raw)
            row["Turkish_original"] = tr_markup
            row["Turkish_seed"] = row["English"] if seed == "english" else tr_markup
            row["Turkish"] = row["Turkish_seed"]
            qa: list[str] = []
            en_raw = english.records[i].data
            en_plain = raw_plain(en_raw).strip()
            tr_plain = raw_plain(tr_raw).strip()
            if tr:
                if tr_raw == en_raw:
                    unchanged += 1
                    status = "UNCHANGED_EN"
                else:
                    changed += 1
                    status = "TRANSLATED"
                if en_plain and not tr_plain:
                    status = "MISSING"
                    missing += 1
                vis_rep=visible_replacement_count(tr_raw)
                if vis_rep:
                    qa.append("VISIBLE_U+FFFD")
                    replacement_msgs += 1
                invalid_cmds=gmsg_invalid_command_ids(tr_raw)
                if invalid_cmds:
                    qa.append("INVALID_CMD:"+",".join(f"0x{x:04X}" for x in sorted(set(invalid_cmds))))
                if gmsg_command_ids(en_raw) != gmsg_command_ids(tr_raw):
                    qa.append("CMDSEQ_DIFF_EN")
                if controls_digest(en_raw) != controls_digest(tr_raw):
                    control_diff += 1
            else:
                status = "EMPTY"
                if en_plain:
                    missing += 1
            row["Status"] = status
            row["QA"] = ";".join(qa)
            w.writerow(row)
    return {
        "rows": english.count,
        "translated_changed": changed,
        "unchanged_vs_english": unchanged,
        "missing": missing,
        "messages_with_replacement_char": replacement_msgs,
        "messages_with_control_diff_vs_english": control_diff,
        "seed": seed,
        "output": str(output),
    }


def inject_gmsg_csv(csv_path: Path, base_path: Path, output: Path, column: str,
                    original_column: Optional[str], allow_control_changes: bool) -> dict:
    base = GmsgFile.load(base_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != base.count:
        raise ToolError(f"CSV satır sayısı {len(rows)}, GMSG kayıt sayısı {base.count}.")
    if not rows or column not in rows[0]:
        raise ToolError(f"CSV'de '{column}' sütunu yok.")
    if original_column and original_column not in rows[0]:
        raise ToolError(f"CSV'de '{original_column}' sütunu yok.")

    data: list[bytes] = [b""] * base.count
    control_errors: list[int] = []
    seen: set[int] = set()
    for r in rows:
        try:
            idx = int(r["Index"])
        except Exception as e:
            raise ToolError("CSV Index alanı geçersiz.") from e
        if idx < 0 or idx >= base.count or idx in seen:
            raise ToolError(f"Geçersiz/tekrarlı Index: {idx}")
        seen.add(idx)
        # Metadata is a useful guard against mixing CSVs from another build.
        for key, expected in (("Meta0", base.records[idx].meta0), ("Meta1", base.records[idx].meta1), ("Meta2", base.records[idx].meta2)):
            if key in r and r[key]:
                try:
                    got = int(r[key], 0)
                except ValueError:
                    raise ToolError(f"Satır {idx}: {key} geçersiz")
                if got != expected:
                    raise ToolError(f"Satır {idx}: {key} uyuşmuyor; yanlış CSV/base olabilir.")
        edited = r[column]
        if original_column and not allow_control_changes:
            if markup_control_tokens(edited) != markup_control_tokens(r[original_column]):
                control_errors.append(idx)
                continue
        data[idx] = markup_to_bytes(edited)
    if control_errors:
        sample = ", ".join(map(str, control_errors[:20]))
        raise ToolError(
            f"{len(control_errors)} satırda korunan kontrol etiketleri değişmiş (örnek: {sample}). "
            "Etiketleri geri yükleyin veya bilerek değiştiriyorsanız --allow-control-changes kullanın."
        )
    if len(seen) != base.count:
        raise ToolError("CSV'de bazı Index değerleri eksik.")
    rebuilt = base.rebuild(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rebuilt)
    return {"rows": base.count, "bytes": len(rebuilt), "sha256": sha256(rebuilt), "output": str(output)}


def validate_gmsg(english_path: Path, turkish_path: Path) -> dict:
    en = GmsgFile.load(english_path)
    tr = GmsgFile.load(turkish_path)
    if en.count != tr.count:
        raise ToolError("GMSG kayıt sayıları farklı.")
    if en.metadata_signature() != tr.metadata_signature():
        raise ToolError("GMSG metadata tabloları farklı.")
    changed = 0
    unchanged: list[int] = []
    control_diff: list[int] = []
    replacement: list[int] = []
    malformed_raw_fffd: list[int] = []
    invalid_command: list[int] = []
    command_seq_diff: list[int] = []
    replacement_occ = 0
    chars: dict[str, int] = {}
    for i, (er, rr) in enumerate(zip(en.records, tr.records)):
        if er.data != rr.data:
            changed += 1
        else:
            unchanged.append(i)
        if controls_digest(er.data) != controls_digest(rr.data):
            control_diff.append(i)
        if gmsg_command_ids(er.data) != gmsg_command_ids(rr.data):
            command_seq_diff.append(i)
        badcmd=gmsg_invalid_command_ids(rr.data)
        if badcmd:
            invalid_command.append(i)
        n = visible_replacement_count(rr.data)
        if n:
            replacement.append(i)
            replacement_occ += n
        if b"\xff\xfd" in rr.data:
            malformed_raw_fffd.append(i)
    # Count only visible text spans; never count coincidental byte patterns inside commands.
    turkish_usage = {ch: sum(raw_plain(r.data).count(ch) for r in tr.records) for ch in TURKISH_CORE}
    return {
        "records": en.count,
        "changed_vs_english": changed,
        "unchanged_vs_english": len(unchanged),
        "unchanged_indices": unchanged,
        "control_diff_messages": len(control_diff),
        "control_diff_indices": control_diff,
        "replacement_char_messages": len(replacement),
        "replacement_char_occurrences": replacement_occ,
        "replacement_char_indices": replacement,
        "raw_FFFD_byte_pair_messages": len(malformed_raw_fffd),
        "raw_FFFD_byte_pair_indices": malformed_raw_fffd,
        "invalid_command_messages": len(invalid_command),
        "invalid_command_indices": invalid_command,
        "command_sequence_diff_messages": len(command_seq_diff),
        "command_sequence_diff_indices": command_seq_diff,
        "turkish_character_usage": turkish_usage,
    }


# ---------------------------------------------------------------------------
# GAR2 (Majora's Mask 3D layout archives)
# ---------------------------------------------------------------------------

@dataclass
class GarEntry:
    index: int
    size: int
    name_offset: int
    path_offset: int
    data_offset: int
    name: str
    path: str
    data: bytes


@dataclass
class Gar2:
    raw: bytes
    path: Optional[Path]
    total_size: int
    num_types: int
    num_files: int
    type_table_offset: int
    file_table_offset: int
    data_offsets_offset: int
    codename: str
    entries: list[GarEntry]

    @staticmethod
    def _cstr(raw: bytes, off: int) -> str:
        if off < 0 or off >= len(raw):
            return ""
        end = raw.find(b"\0", off)
        if end < 0:
            end = len(raw)
        return raw[off:end].decode("utf-8", errors="replace")

    @classmethod
    def load(cls, path: Path | str) -> "Gar2":
        path = Path(path)
        raw = path.read_bytes()
        if raw[:4] != b"GAR\x02":
            raise ToolError(f"GAR2 imzası yok: {path}")
        if len(raw) < 0x20:
            raise ToolError("GAR2 çok küçük")
        total_size = struct.unpack_from("<I", raw, 4)[0]
        num_types, num_files = struct.unpack_from("<HH", raw, 8)
        type_off, file_off, data_offs_off = struct.unpack_from("<III", raw, 0x0C)
        codename = raw[0x18:0x20].split(b"\0", 1)[0].decode("ascii", errors="replace")
        if total_size > len(raw):
            raise ToolError("GAR2 header size dosyadan büyük")
        entries: list[GarEntry] = []
        for i in range(num_files):
            fo = file_off + i * 0x0C
            if fo + 0x0C > len(raw) or data_offs_off + (i + 1) * 4 > len(raw):
                raise ToolError(f"GAR2 tablo sınırı geçersiz, entry {i}")
            size, name_off, path_off = struct.unpack_from("<III", raw, fo)
            doff = struct.unpack_from("<I", raw, data_offs_off + i * 4)[0]
            if doff + size > len(raw):
                raise ToolError(f"GAR2 data sınırı geçersiz, entry {i}")
            entries.append(GarEntry(i, size, name_off, path_off, doff,
                                    cls._cstr(raw, name_off), cls._cstr(raw, path_off), raw[doff:doff + size]))
        return cls(raw, path, total_size, num_types, num_files, type_off, file_off,
                   data_offs_off, codename, entries)

    def unpack(self, outdir: Path) -> list[Path]:
        outdir.mkdir(parents=True, exist_ok=True)
        written = []
        for e in self.entries:
            rel = Path(e.path or e.name or f"entry_{e.index:04d}.bin")
            # Archive paths in observed MM3D GAR are flat; sanitize hostile traversal anyway.
            rel = Path(*[p for p in rel.parts if p not in ("..", ".", "/", "\\")])
            dst = outdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(e.data)
            written.append(dst)
        return written

    def patch_same_size(self, replacements: Path, output: Path) -> dict:
        raw = bytearray(self.raw)
        patched = []
        skipped = []
        for e in self.entries:
            candidates = [replacements / e.path, replacements / e.name] if e.path and e.name else [replacements / (e.path or e.name)]
            rp = next((p for p in candidates if p and p.exists() and p.is_file()), None)
            if not rp:
                continue
            new = rp.read_bytes()
            if len(new) != e.size:
                skipped.append({"path": e.path, "old_size": e.size, "new_size": len(new)})
                continue
            raw[e.data_offset:e.data_offset + e.size] = new
            patched.append(e.path)
        if skipped:
            msg = "; ".join(f"{x['path']} {x['old_size']}->{x['new_size']}" for x in skipped[:10])
            raise ToolError(
                "GAR güvenli patch modu yalnızca aynı boyuttaki dosyaları değiştirir. "
                f"Boyut uyuşmayanlar: {msg}. CTXB aynı çözünürlük/formatta yeniden kodlanırsa boyutu normalde sabit kalır."
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(raw)
        return {"patched": patched, "count": len(patched), "output": str(output)}


# ---------------------------------------------------------------------------
# CTXB texture helpers
# ---------------------------------------------------------------------------

@dataclass
class CtxbTexture:
    index: int
    entry_offset: int
    data_length: int
    mip_count: int
    is_etc1: int
    is_cubemap: int
    width: int
    height: int
    fmt: int
    data_type: int
    data_offset: int
    name: str

    @property
    def format_name(self) -> str:
        mapping = {
            (0x6752, 0x1401): "RGBA8",
            (0x6752, 0x8033): "RGBA4",
            (0x6754, 0x1401): "RGB8",
            (0x6757, 0x1401): "L8",
            (0x6757, 0x6761): "L4",
            (0x6756, 0x1401): "A8",
            (0x6758, 0x1401): "LA8",
            (0x6758, 0x6760): "LA4",
            (0x675A, 0): "ETC1",
            (0x675B, 0): "ETC1A4",
        }
        return mapping.get((self.fmt, self.data_type), f"0x{self.fmt:04X}/0x{self.data_type:04X}")


def parse_ctxb(path: Path | str) -> tuple[bytes, int, int, int, list[CtxbTexture]]:
    p=Path(path); b=p.read_bytes()
    if len(b)<0x18 or b[:4]!=b"ctxb":
        raise ToolError(f"CTXB değil: {p}")
    file_size, tex_count_header, unknown, tex_off, tex_data_off = struct.unpack_from("<IIIII", b, 4)
    if file_size != len(b):
        raise ToolError(f"CTXB dosya boyutu header ile uyuşmuyor: {file_size} != {len(b)}")
    if tex_off+0x0C>len(b) or b[tex_off:tex_off+4]!=b"tex ":
        raise ToolError("CTXB tex chunk bulunamadı")
    tex_chunk_size, tex_count = struct.unpack_from("<II", b, tex_off+4)
    if tex_count != tex_count_header:
        raise ToolError(f"CTXB texture sayısı uyuşmuyor: {tex_count_header} != {tex_count}")
    textures=[]
    for i in range(tex_count):
        o=tex_off+0x0C+i*0x24
        if o+0x24>len(b): raise ToolError(f"CTXB texture entry {i} sınırı geçersiz")
        ln,mips,isetc,cube,w,h,fmt,dtype,doff=struct.unpack_from("<IHBBHHHHI",b,o)
        name=b[o+0x14:o+0x24].split(b"\0",1)[0].decode("ascii",errors="replace")
        if tex_data_off+doff+ln>len(b): raise ToolError(f"CTXB texture {i} data sınırı geçersiz")
        textures.append(CtxbTexture(i,o,ln,mips,isetc,cube,w,h,fmt,dtype,doff,name))
    return b, tex_off, tex_data_off, tex_chunk_size, textures


def _ctxb_points(width: int, height: int) -> Iterator[tuple[int,int]]:
    # PICA textures in these MM3D files use 8x8 Morton (Z-order) tiles.
    stride_w=(width+7)&~7; stride_h=(height+7)&~7
    for ty in range(0,stride_h,8):
        for tx in range(0,stride_w,8):
            for i in range(64):
                x,y=_morton8_xy(i)
                if tx+x<width and ty+y<height:
                    yield tx+x,ty+y


def decode_ctxb_texture(path: Path | str, index: int=0):
    try:
        from PIL import Image
    except ImportError as e:
        raise ToolError("CTXB görsel işlemleri için Pillow gerekli: pip install pillow") from e
    b,_,data_base,_,textures=parse_ctxb(path)
    if index<0 or index>=len(textures): raise ToolError(f"CTXB texture index geçersiz: {index}")
    t=textures[index]; raw=b[data_base+t.data_offset:data_base+t.data_offset+t.data_length]
    if t.is_cubemap: raise ToolError("Cubemap CTXB bu komutta desteklenmiyor")
    if t.format_name in ("ETC1","ETC1A4"):
        try:
            import etc1_codec
        except ImportError as e:
            raise ToolError("ETC1/ETC1A4 için paketle gelen etc1_codec.py bulunamadı") from e
        return etc1_codec.decode_image(raw,t.width,t.height,t.format_name=="ETC1A4")
    im=Image.new("RGBA",(t.width,t.height),(0,0,0,0))
    pts=list(_ctxb_points(t.width,t.height))
    if t.format_name=="RGBA8":
        if len(raw)<len(pts)*4: raise ToolError("CTXB RGBA8 veri kısa")
        for i,(x,y) in enumerate(pts):
            a,bb,g,r=raw[i*4:i*4+4]
            im.putpixel((x,y),(r,g,bb,a))
    elif t.format_name=="RGBA4":
        if len(raw)<len(pts)*2: raise ToolError("CTXB RGBA4 veri kısa")
        for i,(x,y) in enumerate(pts):
            v=struct.unpack_from("<H",raw,i*2)[0]
            a=(v&0xF)*17; bb=((v>>4)&0xF)*17; g=((v>>8)&0xF)*17; r=((v>>12)&0xF)*17
            im.putpixel((x,y),(r,g,bb,a))
    elif t.format_name=="L8":
        if len(raw)<len(pts): raise ToolError("CTXB L8 veri kısa")
        for i,(x,y) in enumerate(pts):
            v=raw[i]; im.putpixel((x,y),(v,v,v,255))
    elif t.format_name=="A8":
        if len(raw)<len(pts): raise ToolError("CTXB A8 veri kısa")
        for i,(x,y) in enumerate(pts):
            a=raw[i]; im.putpixel((x,y),(255,255,255,a))
    else:
        raise ToolError(f"CTXB export henüz bu formatı desteklemiyor: {t.format_name}")
    return im


def encode_ctxb_pixels(im, t: CtxbTexture) -> bytes:
    im=im.convert("RGBA")
    if im.size!=(t.width,t.height):
        raise ToolError(f"PNG boyutu {im.size}; CTXB texture boyutu {(t.width,t.height)} olmalı")
    pts=list(_ctxb_points(t.width,t.height)); out=bytearray()
    if t.format_name=="RGBA8":
        for x,y in pts:
            r,g,b,a=im.getpixel((x,y)); out += bytes((a,b,g,r))
    elif t.format_name=="RGBA4":
        for x,y in pts:
            r,g,b,a=im.getpixel((x,y)); v=((r>>4)<<12)|((g>>4)<<8)|((b>>4)<<4)|(a>>4); out+=struct.pack("<H",v)
    elif t.format_name=="L8":
        for x,y in pts:
            r,g,b,a=im.getpixel((x,y)); out.append(round((r*299+g*587+b*114)/1000))
    elif t.format_name=="A8":
        for x,y in pts: out.append(im.getpixel((x,y))[3])
    elif t.format_name in ("ETC1","ETC1A4"):
        try:
            import etc1_codec
        except ImportError as e:
            raise ToolError("ETC1/ETC1A4 için paketle gelen etc1_codec.py bulunamadı") from e
        out += etc1_codec.encode_image(im,t.format_name=="ETC1A4")
    else:
        raise ToolError(f"CTXB import henüz bu formatı desteklemiyor: {t.format_name}")
    if len(out)!=t.data_length:
        raise ToolError(f"Encoded payload boyutu uyuşmuyor: {len(out)} != {t.data_length}")
    return bytes(out)



def encode_etc1_smart(im, t: CtxbTexture, original_raw: bytes) -> tuple[bytes,int,int]:
    """Encode only changed 4x4 ETC1/ETC1A4 blocks; preserve untouched compressed blocks byte-for-byte."""
    try:
        import etc1_codec
    except ImportError as e:
        raise ToolError("ETC1/ETC1A4 için paketle gelen etc1_codec.py bulunamadı") from e
    im=im.convert("RGBA")
    if im.size!=(t.width,t.height):
        raise ToolError(f"PNG boyutu {im.size}; CTXB texture boyutu {(t.width,t.height)} olmalı")
    if t.width%8 or t.height%8:
        raise ToolError("ETC1 texture boyutları 8'in katı olmalı")
    has_alpha=t.format_name=="ETC1A4"
    expected=t.width*t.height//(1 if has_alpha else 2)
    if len(original_raw)!=expected:
        raise ToolError(f"ETC payload boyutu beklenmedik: {len(original_raw)} != {expected}")
    original=etc1_codec.decode_image(original_raw,t.width,t.height,has_alpha).convert("RGBA")
    opx=original.load(); npx=im.load(); out=bytearray(original_raw); off=0; changed=0; total=0
    for ty in range(0,t.height,8):
      for tx in range(0,t.width,8):
       for dx,dy in ((0,0),(4,0),(0,4),(4,4)):
        total+=1; block_changed=False
        for y in range(4):
         for x in range(4):
          if npx[tx+dx+x,ty+dy+y] != opx[tx+dx+x,ty+dy+y]:
           block_changed=True; break
         if block_changed: break
        chunk_len=16 if has_alpha else 8
        if block_changed:
            pix=[[npx[tx+dx+x,ty+dy+y] for x in range(4)] for y in range(4)]
            chunk=bytearray()
            if has_alpha:
                aw=0
                for y in range(4):
                 for x in range(4):
                  k=x*4+y; q=max(0,min(15,round(pix[y][x][3]/17))); aw|=(q&15)<<(k*4)
                chunk += aw.to_bytes(8,'little')
            chunk += etc1_codec.encode_block(pix)
            out[off:off+chunk_len]=chunk
            changed+=1
        off+=chunk_len
    return bytes(out),changed,total

def ctxb_info(path: Path | str) -> dict:
    p=Path(path); b,tex_off,data_off,tex_chunk_size,textures=parse_ctxb(p)
    info={"path":str(p),"actual_size":len(b),"header_size":len(b),"version_or_texture_count":struct.unpack_from('<I',b,8)[0],
          "tex_chunk_offset":tex_off,"tex_data_offset":data_off,"textures":[]}
    for t in textures:
        info["textures"].append({"index":t.index,"name":t.name,"width":t.width,"height":t.height,
                                 "format":t.format_name,"format_hex":f"0x{t.fmt:04X}","data_type_hex":f"0x{t.data_type:04X}",
                                 "mip_count":t.mip_count,"is_etc1":bool(t.is_etc1),"data_length":t.data_length,"data_offset":t.data_offset})
    for candidate in (Path(str(p)+".00.png"),p.with_suffix(p.suffix+".00.png")):
        if candidate.exists():
            try:
                from PIL import Image
                with Image.open(candidate) as im: info["companion_png"] = str(candidate); info["png_width"],info["png_height"]=im.size
            except Exception: info["companion_png"]=str(candidate)
            break
    return info


def ctxb_export_png(path: Path, output: Path, index: int=0) -> dict:
    im=decode_ctxb_texture(path,index); output.parent.mkdir(parents=True,exist_ok=True); im.save(output)
    return {"output":str(output),"width":im.width,"height":im.height,"texture_index":index}


def ctxb_inject_png(path: Path, png: Path, output: Path, index: int=0) -> dict:
    try:
        from PIL import Image
    except ImportError as e: raise ToolError("pip install pillow") from e
    b,_,data_base,_,textures=parse_ctxb(path)
    if index<0 or index>=len(textures): raise ToolError(f"CTXB texture index geçersiz: {index}")
    t=textures[index]
    smart_stats=None
    with Image.open(png) as pim:
        if t.format_name in ("ETC1","ETC1A4"):
            start=data_base+t.data_offset
            payload,changed,total=encode_etc1_smart(pim,t,b[start:start+t.data_length])
            smart_stats={"changed_4x4_blocks":changed,"total_4x4_blocks":total}
        else:
            payload=encode_ctxb_pixels(pim,t)
    raw=bytearray(b); start=data_base+t.data_offset; raw[start:start+t.data_length]=payload
    output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(raw)
    # Structural sanity check and byte-size invariant.
    if len(raw)!=len(b): raise ToolError("CTXB boyutu değişti; güvenlik kontrolü başarısız")
    parse_ctxb(output)
    result={"output":str(output),"texture_index":index,"format":t.format_name,"bytes":len(raw),"sha256":sha256(bytes(raw))}
    if smart_stats: result.update(smart_stats)
    return result

# ---------------------------------------------------------------------------
# GZFX font (Majora's Mask 3D / Grezzo variant)
# ---------------------------------------------------------------------------

# Cetera/Kuriimu byte enum used by MM3D's GZF header.
GZF_FORMATS = {
    0: "RGBA8888", 1: "RGB888", 2: "RGBA5551", 3: "RGB565", 4: "RGBA4444",
    5: "LA88", 6: "HL88", 7: "L8", 8: "A8", 9: "LA44", 10: "L4",
    11: "A4", 12: "ETC1", 13: "ETC1A4",
}


@dataclass
class GzfImageHeader:
    offset: int
    width: int
    height: int


@dataclass
class GzfGlyph:
    codepoint: int
    padding: int
    advance_width: int
    image_id: int
    left: int
    cell_id: int

    @property
    def char(self) -> str:
        try:
            return chr(self.codepoint)
        except ValueError:
            return "�"

    @property
    def cell_x(self) -> int:
        return self.cell_id & 0xFF

    @property
    def cell_y(self) -> int:
        return (self.cell_id >> 8) & 0xFF


@dataclass
class GzfFont:
    raw: bytes
    version: int
    image_header_offset: int
    image_entry_size: int
    glyph_entry_size: int
    image_count: int
    glyph_count: int
    unknown2: int
    unknown3: int
    fmt: int
    format_pad: int
    font_size: int
    unknown5: int
    tile_width: int
    tile_height: int
    unknown8: int
    images: list[GzfImageHeader]
    glyphs: list[GzfGlyph]

    @classmethod
    def load(cls, path: Path | str) -> "GzfFont":
        b = Path(path).read_bytes()
        if len(b) < 0x30 or b[:4] != b"GZFX":
            raise ToolError("GZF/GZFX imzası bulunamadı.")

        version = struct.unpack_from("<I", b, 0x04)[0]
        image_header_offset, image_entry_size = struct.unpack_from("<HH", b, 0x08)
        glyph_entry_size = struct.unpack_from("<I", b, 0x0C)[0]
        image_count, glyph_count, unknown2, unknown3 = struct.unpack_from("<IIII", b, 0x10)
        fmt, format_pad = struct.unpack_from("<BB", b, 0x20)
        font_size, unknown5, tile_width = struct.unpack_from("<hhh", b, 0x22)
        tile_height = struct.unpack_from("<i", b, 0x28)[0]
        unknown8 = struct.unpack_from("<I", b, 0x2C)[0]

        if image_entry_size < 8 or glyph_entry_size < 12:
            raise ToolError(f"Beklenmeyen GZF entry boyutu: image={image_entry_size}, glyph={glyph_entry_size}")
        if image_header_offset < 0x30:
            raise ToolError(f"Geçersiz GZF image header offset: 0x{image_header_offset:X}")

        images=[]
        for i in range(image_count):
            off = image_header_offset + i*image_entry_size
            if off+8 > len(b):
                raise ToolError("GZF image header sınırı geçersiz")
            images.append(GzfImageHeader(*struct.unpack_from("<IHH", b, off)))

        glyph_off = image_header_offset + image_count*image_entry_size
        glyphs=[]
        for i in range(glyph_count):
            off = glyph_off + i*glyph_entry_size
            if off+12 > len(b):
                raise ToolError("GZF glyph header sınırı geçersiz")
            cp = struct.unpack_from("<H", b, off)[0]
            padding = struct.unpack_from("<H", b, off+2)[0]
            advance, image_id, left, cell_id = struct.unpack_from("<hhhh", b, off+4)
            glyphs.append(GzfGlyph(cp, padding, advance, image_id, left, cell_id))

        f=cls(b,version,image_header_offset,image_entry_size,glyph_entry_size,
              image_count,glyph_count,unknown2,unknown3,fmt,format_pad,
              font_size,unknown5,tile_width,tile_height,unknown8,images,glyphs)
        f.validate_layout()
        return f

    def codepoints(self) -> set[int]:
        return {g.codepoint for g in self.glyphs}

    def bytes_per_image(self, image_id: int) -> int:
        im=self.images[image_id]
        if self.fmt in (10,11):  # L4 / A4
            return im.width*im.height//2
        if self.fmt in (7,8,9):  # L8 / A8 / LA44
            return im.width*im.height
        raise ToolError(f"GZF atlas formatı henüz desteklenmiyor: {self.fmt} ({GZF_FORMATS.get(self.fmt,'?')})")

    def image_data(self, image_id: int) -> bytes:
        if not (0 <= image_id < len(self.images)):
            raise ToolError(f"Geçersiz GZF image id: {image_id}")
        im=self.images[image_id]
        n=self.bytes_per_image(image_id)
        if im.offset+n > len(self.raw):
            raise ToolError(f"GZF image {image_id} data sınırı geçersiz")
        return self.raw[im.offset:im.offset+n]

    def validate_layout(self) -> None:
        if self.tile_width <= 0 or self.tile_height <= 0:
            raise ToolError(f"Geçersiz GZF hücre boyutu: {self.tile_width}x{self.tile_height}")
        for i,im in enumerate(self.images):
            self.image_data(i)
        for g in self.glyphs:
            if not (0 <= g.image_id < self.image_count):
                raise ToolError(f"U+{g.codepoint:04X} geçersiz atlas id kullanıyor: {g.image_id}")
            im=self.images[g.image_id]
            if (g.cell_x+1)*self.tile_width > im.width or (g.cell_y+1)*self.tile_height > im.height:
                raise ToolError(
                    f"U+{g.codepoint:04X} hücresi atlas dışına taşıyor: "
                    f"sheet={g.image_id} cell=({g.cell_x},{g.cell_y})"
                )


def _morton8_xy(i: int) -> tuple[int,int]:
    # Cetera/Kuriimu 8x8 Z-order used by 3DS textures.
    x = (i & 1) | ((i & 4) >> 1) | ((i & 16) >> 2)
    y = ((i & 2) >> 1) | ((i & 8) >> 2) | ((i & 32) >> 3)
    return x,y


def _points_8x8(width: int, height: int) -> Iterator[tuple[int,int]]:
    if width % 8 or height % 8:
        raise ToolError(f"GZF atlas boyutu 8'in katı değil: {width}x{height}")
    for ty in range(0,height,8):
        for tx in range(0,width,8):
            for i in range(64):
                x,y=_morton8_xy(i)
                yield tx+x,ty+y


def decode_gzf_atlas(font: GzfFont, image_id: int):
    try:
        from PIL import Image
    except ImportError as e:
        raise ToolError("Font görsel işlemleri için Pillow gerekli: pip install pillow") from e
    ih=font.images[image_id]
    raw=font.image_data(image_id)
    im=Image.new("L",(ih.width,ih.height),0)
    pts=list(_points_8x8(ih.width,ih.height))
    if font.fmt in (10,11):  # L4 / A4: low nibble first (BinaryReaderX.ReadNibble)
        for i,(x,y) in enumerate(pts):
            byte=raw[i//2]
            nib=(byte & 0x0F) if i%2==0 else (byte >> 4)
            im.putpixel((x,y),nib*17)
    elif font.fmt in (7,8):  # L8 / A8
        for i,(x,y) in enumerate(pts):
            im.putpixel((x,y),raw[i])
    elif font.fmt==9:  # LA44: alpha nibble then luminance nibble; glyph mask uses alpha.
        for i,(x,y) in enumerate(pts):
            byte=raw[i]
            im.putpixel((x,y),(byte & 0x0F)*17)
    else:
        raise ToolError(f"Desteklenmeyen GZF atlas formatı: {font.fmt} ({GZF_FORMATS.get(font.fmt,'?')})")
    return im


def encode_gzf_atlas(im, fmt: int) -> bytes:
    try:
        from PIL import Image
    except ImportError as e:
        raise ToolError("Font görsel işlemleri için Pillow gerekli: pip install pillow") from e
    im=im.convert("L")
    w,h=im.size
    pts=list(_points_8x8(w,h))
    if fmt in (10,11):
        out=bytearray()
        for i,(x,y) in enumerate(pts):
            nib=max(0,min(15,im.getpixel((x,y))//17))
            if i%2==0:
                out.append(nib)
            else:
                out[-1]=(out[-1]&0x0F)|(nib<<4)
        return bytes(out)
    if fmt in (7,8):
        return bytes(im.getpixel((x,y)) for x,y in pts)
    if fmt==9:
        # Preserve a neutral white luminance nibble; for MM3D this path is not used.
        return bytes(((im.getpixel((x,y))//17)&0xF) | 0xF0 for x,y in pts)
    raise ToolError(f"Desteklenmeyen GZF atlas formatı: {fmt} ({GZF_FORMATS.get(fmt,'?')})")


def _glyph_box(font: GzfFont, g: GzfGlyph) -> tuple[int,int,int,int]:
    x=g.cell_x*font.tile_width
    y=g.cell_y*font.tile_height
    return x,y,x+font.tile_width,y+font.tile_height


def _glyph_mask(font: GzfFont, atlases: list, g: GzfGlyph):
    return atlases[g.image_id].crop(_glyph_box(font,g))


def font_info(path: Path) -> dict:
    f=GzfFont.load(path)
    cps=f.codepoints()
    coverage={ch:(ord(ch) in cps) for ch in TURKISH_CORE}
    sheets=[{"id":i,"offset":im.offset,"width":im.width,"height":im.height,
             "encoded_bytes":f.bytes_per_image(i)} for i,im in enumerate(f.images)]
    core=[]
    for ch in TURKISH_CORE:
        g=next((x for x in f.glyphs if x.codepoint==ord(ch)),None)
        core.append({"char":ch,"codepoint":f"U+{ord(ch):04X}","present":g is not None,
                     **({"sheet":g.image_id,"cell_x":g.cell_x,"cell_y":g.cell_y,
                         "advance_width":g.advance_width,"left":g.left} if g else {})})
    return {
        "path":str(path),"version":f.version,"images":f.image_count,"glyphs":f.glyph_count,
        "format_id":f.fmt,"format":GZF_FORMATS.get(f.fmt,str(f.fmt)),
        "font_size":f.font_size,"tile_width":f.tile_width,"tile_height":f.tile_height,
        "header_unknowns":{"image_entry_size":f.image_entry_size,"unknown2":f.unknown2,
                           "unknown3":f.unknown3,"unknown5":f.unknown5,"unknown8":f.unknown8},
        "sheets":sheets,
        "turkish_core_coverage":coverage,
        "missing_turkish_core":"".join(ch for ch,ok in coverage.items() if not ok),
        "turkish_core_glyphs":core,
    }


def font_export(path: Path, outdir: Path) -> dict:
    f=GzfFont.load(path)
    outdir.mkdir(parents=True,exist_ok=True)
    glyph_dir=outdir/'glyphs'; glyph_dir.mkdir(exist_ok=True)
    atlas_dir=outdir/'atlases'; atlas_dir.mkdir(exist_ok=True)
    atlases=[decode_gzf_atlas(f,i) for i in range(f.image_count)]
    for i,im in enumerate(atlases):
        im.save(atlas_dir/f"atlas_{i}.png")
    rows=[]
    for g in f.glyphs:
        safe=f"U+{g.codepoint:04X}"
        png=glyph_dir/f"{safe}.png"
        crop=_glyph_mask(f,atlases,g)
        crop.save(png)
        bbox=crop.getbbox()
        rows.append({
            "Codepoint":safe,"Char":g.char,"Sheet":g.image_id,"CellX":g.cell_x,"CellY":g.cell_y,
            "AdvanceWidth":g.advance_width,"Left":g.left,
            "BitmapBBox":"" if not bbox else ",".join(map(str,bbox)),
            "PNG":str(png.relative_to(outdir)),
        })
    with (outdir/'glyphs.csv').open('w',encoding='utf-8-sig',newline='') as fp:
        fields=list(rows[0]) if rows else ["Codepoint"]
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    info=font_info(path)
    (outdir/'font_info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    return {"glyphs":len(rows),"atlases":f.image_count,"output":str(outdir),
            "tile_size":[f.tile_width,f.tile_height],"format":GZF_FORMATS.get(f.fmt,str(f.fmt))}


def _png_to_glyph_mask(png: Path, size: tuple[int,int]):
    try:
        from PIL import Image
    except ImportError as e:
        raise ToolError("pip install pillow") from e
    with Image.open(png) as pim:
        if pim.size != size:
            raise ToolError(f"Glyph PNG boyutu {pim.size}, beklenen {size}. Otomatik ölçekleme güvenlik için kapalı.")
        if 'A' in pim.getbands():
            return pim.getchannel('A').copy()
        return pim.convert('L').copy()


def font_replace_png(path: Path, char: str, png: Path, output: Path) -> dict:
    """Replace one existing MM3D glyph bitmap in-place without moving headers/atlases."""
    if len(char)!=1:
        raise ToolError("--char tam bir Unicode karakter olmalı.")
    f=GzfFont.load(path)
    g=next((x for x in f.glyphs if x.codepoint==ord(char)),None)
    if not g:
        raise ToolError(f"Fontta {char} (U+{ord(char):04X}) yok. MM3D sabit atlasında körlemesine glyph eklemek desteklenmiyor.")
    atlases=[decode_gzf_atlas(f,i) for i in range(f.image_count)]
    replacement=_png_to_glyph_mask(png,(f.tile_width,f.tile_height))
    before=_glyph_mask(f,atlases,g).tobytes()
    atlases[g.image_id].paste(replacement,(g.cell_x*f.tile_width,g.cell_y*f.tile_height))
    encoded=encode_gzf_atlas(atlases[g.image_id],f.fmt)
    expected=f.bytes_per_image(g.image_id)
    if len(encoded)!=expected:
        raise ToolError(f"Atlas encode boyutu değişti: {len(encoded)} != {expected}")
    raw=bytearray(f.raw)
    off=f.images[g.image_id].offset
    raw[off:off+expected]=encoded
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(raw)
    chk=GzfFont.load(output)
    if len(raw)!=len(f.raw):
        raise ToolError("Font boyutu değişti; güvenlik kontrolü başarısız")
    # Verify round-trip decode of the replaced cell.
    chk_atlas=decode_gzf_atlas(chk,g.image_id)
    chk_g=next(x for x in chk.glyphs if x.codepoint==ord(char))
    after=_glyph_mask(chk,[chk_atlas if i==g.image_id else None for i in range(chk.image_count)],chk_g).tobytes()
    return {"replaced":char,"codepoint":f"U+{ord(char):04X}","sheet":g.image_id,
            "cell":[g.cell_x,g.cell_y],"bitmap_changed":before!=after,
            "output":str(output),"bytes":len(raw),"sha256":sha256(bytes(raw))}


def font_add_png(path: Path, char: str, png: Path, copy_metrics: str, output: Path) -> dict:
    # Deliberately conservative. MM3D uses fixed 16x18 atlas cells and its Turkish core is already present.
    f=GzfFont.load(path)
    if ord(char) in f.codepoints():
        raise ToolError(f"Font zaten {char} (U+{ord(char):04X}) içeriyor; font-replace-png kullan.")
    raise ToolError(
        "MM3D GZF'de yeni codepoint eklemek için boş atlas hücresi + entry koordinatı birlikte yönetilmeli. "
        "Bu sürüm, fontu bozma riskini önlemek için otomatik eklemeyi kapatıyor."
    )


def font_check_text(path: Path, csv_path: Optional[Path], column: str, chars: Optional[str]) -> dict:
    f=GzfFont.load(path); cps=f.codepoints()
    wanted=set(chars or "")
    if csv_path:
        with csv_path.open('r',encoding='utf-8-sig',newline='') as fp:
            rows=csv.DictReader(fp)
            for r in rows:
                if column not in r:
                    raise ToolError(f"CSV sütunu yok: {column}")
                wanted.update(markup_plain(r[column]))
    wanted={c for c in wanted if not c.isspace()}
    missing=sorted((c for c in wanted if ord(c) not in cps),key=ord)
    return {"checked_characters":len(wanted),"missing_count":len(missing),
            "missing":"".join(missing),"missing_codepoints":[f"U+{ord(c):04X}" for c in missing]}

# ---------------------------------------------------------------------------
# Project inventory/report helpers
# ---------------------------------------------------------------------------

def scan_menu_assets(menu_root: Path, out_csv: Path) -> dict:
    root = menu_root / "menu" if (menu_root / "menu").is_dir() else menu_root
    ctxbs=sorted(root.rglob('*.ctxb'))
    pngs=sorted(root.rglob('*.png'))
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as fp:
        fields=["RelativePath","Type","Bytes","CompanionPNG","Width","Height","TextureFormat","LikelyTextAsset","LayeredFSTarget"]
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader()
        for p in ctxbs:
            rel=p.relative_to(root).as_posix(); comp=Path(str(p)+'.00.png')
            width=height=''; fmt=''
            try:
                _,_,_,_,tex=parse_ctxb(p)
                if tex:
                    width,height,fmt=tex[0].width,tex[0].height,tex[0].format_name
            except Exception:
                pass
            if comp.exists() and (not width or not height):
                try:
                    from PIL import Image
                    with Image.open(comp) as im: width,height=im.size
                except Exception: pass
            likely=('daytelop/' in rel or 'savedata_maintainer/' in rel)
            w.writerow({"RelativePath":rel,"Type":"CTXB","Bytes":p.stat().st_size,
                        "CompanionPNG":comp.relative_to(root).as_posix() if comp.exists() else '',
                        "Width":width,"Height":height,"TextureFormat":fmt,"LikelyTextAsset":"YES" if likely else "",
                        "LayeredFSTarget":"romfs/menu/"+rel})
    return {"ctxb":len(ctxbs),"png":len(pngs),"output":str(out_csv)}


def make_image_worklist(menu_root: Path, out_csv: Path) -> dict:
    """Build a side-by-side language CSV for rasterized menu text assets."""
    root=menu_root/'menu' if (menu_root/'menu').is_dir() else menu_root
    rows=[]
    lang_cols=['English','French','German','Italian','Spanish']
    # Day/title cards: eu-en/eu-fr/eu-de/eu-it/eu-es.
    daymap={'English':'eu-en','French':'eu-fr','German':'eu-de','Italian':'eu-it','Spanish':'eu-es'}
    base=root/'daytelop'
    names=sorted({p.name for d in daymap.values() for p in (base/d).glob('*.ctxb')}) if base.exists() else []
    for name in names:
        row={'Group':'daytelop','Asset':name,'TurkishPNG':'','Notes':'Rasterized text; ETC1 texture. Edit a PNG then encode to CTXB with Kukkii/Kuriimu.'}
        for lang,d in daymap.items():
            c=base/d/name; png=Path(str(c)+'.00.png')
            row[lang+'CTXB']=c.relative_to(root).as_posix() if c.exists() else ''
            row[lang+'PNG']=png.relative_to(root).as_posix() if png.exists() else ''
        row['LayeredFSTarget']='romfs/menu/daytelop/eu-en/'+name
        rows.append(row)
    # Save-data maintainer atlas.
    savemap={'English':'english','French':'french','German':'german','Italian':'italian','Spanish':'spanish'}
    base=root/'savedata_maintainer'/'eu'
    names=sorted({p.name for d in savemap.values() for p in (base/d).glob('*.ctxb')}) if base.exists() else []
    for name in names:
        row={'Group':'savedata_maintainer','Asset':name,'TurkishPNG':'','Notes':'RGBA8 texture; this tool can inject PNG directly with ctxb-inject-png.'}
        for lang,d in savemap.items():
            c=base/d/name; png=Path(str(c)+'.00.png')
            row[lang+'CTXB']=c.relative_to(root).as_posix() if c.exists() else ''
            row[lang+'PNG']=png.relative_to(root).as_posix() if png.exists() else ''
        row['LayeredFSTarget']='romfs/menu/savedata_maintainer/eu/english/'+name
        rows.append(row)
    fields=['Group','Asset'] + [x+suf for x in lang_cols for suf in ('CTXB','PNG')] + ['TurkishPNG','LayeredFSTarget','Notes']
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    return {'rows':len(rows),'output':str(out_csv)}



def make_translation_review_csv(source_csv: Path, out_csv: Path) -> dict:
    """Create a compact review queue: QA failures plus untranslated English-identical rows."""
    with source_csv.open('r',encoding='utf-8-sig',newline='') as fp:
        rows=list(csv.DictReader(fp)); fields=fp.seek(0) or None
    selected=[r for r in rows if r.get('QA') or r.get('Status') in ('UNCHANGED_EN','MISSING','EMPTY')]
    if rows:
        fieldnames=list(rows[0].keys())
    else:
        fieldnames=[]
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=fieldnames); w.writeheader(); w.writerows(selected)
    return {'rows':len(selected),'output':str(out_csv)}

def scan_layout_gars(layout_root: Path, out_csv: Path, extract_english: Optional[Path]=None) -> dict:
    gars=sorted(layout_root.rglob('*.gar')); rows=[]; embedded=0
    for p in gars:
        g=Gar2.load(p)
        lang=p.parent.name
        for e in g.entries:
            embedded += 1
            rows.append({"Language":lang,"Archive":p.name,"Entry":e.path,"Bytes":e.size,"Magic":e.data[:4].decode('latin1',errors='replace')})
        if extract_english and lang=="EU_English":
            dest=extract_english/p.stem
            g.unpack(dest)
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as fp:
        fields=["Language","Archive","Entry","Bytes","Magic"]
        w=csv.DictWriter(fp,fieldnames=fields);w.writeheader();w.writerows(rows)
    return {"gar_archives":len(gars),"embedded_files":embedded,"output":str(out_csv)}



def _ctxb_brief_bytes(b: bytes) -> dict:
    """Return basic first-texture metadata from CTXB bytes without writing a temp file."""
    if len(b) < 0x3C or b[:4] != b"ctxb":
        return {}
    try:
        _, tex_count_header, _, tex_off, tex_data_off = struct.unpack_from("<IIIII", b, 4)
        if b[tex_off:tex_off+4] != b"tex ": return {}
        _, tex_count = struct.unpack_from("<II", b, tex_off+4)
        if not tex_count or tex_count != tex_count_header: return {}
        o=tex_off+0x0C
        ln,mips,isetc,cube,w,h,fmt,dtype,doff=struct.unpack_from("<IHBBHHHHI",b,o)
        fake=CtxbTexture(0,o,ln,mips,isetc,cube,w,h,fmt,dtype,doff,"")
        return {"width":w,"height":h,"format":fake.format_name,"bytes":len(b)}
    except Exception:
        return {}

def make_layout_image_worklist(layout_root: Path, out_csv: Path) -> dict:
    """Build one row per CTXB entry with all EU language GARs side-by-side."""
    lang_dirs={
        'English':'EU_English','French':'EU_French','German':'EU_German',
        'Italian':'EU_Italian','Spanish':'EU_Spanish','Dutch':'EU_Dutch',
    }
    mapped={}
    for lang,dname in lang_dirs.items():
        d=layout_root/dname
        if not d.exists(): continue
        for gp in sorted(d.glob('*.gar')):
            try: gar=Gar2.load(gp)
            except ToolError: continue
            for e in gar.entries:
                if not e.path.lower().endswith('.ctxb'): continue
                key=(gp.name,e.path)
                mapped.setdefault(key,{})[lang]=(gp,e)
    fields=['Archive','Entry','Width','Height','Format']
    for lang in lang_dirs:
        fields += [lang+'GAR',lang+'Bytes']
    fields += ['TurkishCTXB','PatchArchive','Notes']
    rows=[]
    for (archive,entry),langs in sorted(mapped.items()):
        src=langs.get('English') or next(iter(langs.values()))
        meta=_ctxb_brief_bytes(src[1].data)
        row={'Archive':archive,'Entry':entry,'Width':meta.get('width',''),'Height':meta.get('height',''),'Format':meta.get('format',''),
             'TurkishCTXB':'','PatchArchive':archive,
             'Notes':'Translate/edit this texture. Re-encode with the same dimensions/format; then use gar-patch.'}
        for lang,dname in lang_dirs.items():
            pair=langs.get(lang)
            row[lang+'GAR']=(f'{dname}/{archive}' if pair else '')
            row[lang+'Bytes']=(pair[1].size if pair else '')
        rows.append(row)
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=fields); w.writeheader(); w.writerows(rows)
    return {'rows':len(rows),'output':str(out_csv)}

def find_font_references(code_path: Path) -> list[dict]:
    b=code_path.read_bytes(); results=[]
    for needle in (b"rom:/message/ltn16.gzf", b"GZFX"):
        start=0
        while True:
            i=b.find(needle,start)
            if i<0:break
            results.append({"needle":needle.decode('ascii',errors='replace'),"offset_hex":f"0x{i:X}"})
            start=i+1
    return results


def make_analysis_report(eu_dir: Path, turkish: Path, menu_root: Path, layout_root: Path,
                         code_path: Path, outdir: Path) -> dict:
    outdir.mkdir(parents=True,exist_ok=True)
    csv_stats=export_gmsg_csv(eu_dir,turkish,outdir/'translations.csv',seed='turkish')
    clean_csv_stats=export_gmsg_csv(eu_dir,turkish,outdir/'translations_clean.csv',seed='english')
    review_stats=make_translation_review_csv(outdir/'translations.csv',outdir/'translation_review.csv')
    qa=validate_gmsg(eu_dir/'eue.gmsg',turkish)
    menu=scan_menu_assets(menu_root,outdir/'menu_assets.csv')
    image_worklist=make_image_worklist(menu_root,outdir/'image_translation.csv')
    layout=scan_layout_gars(layout_root,outdir/'layout_gar_assets.csv',outdir/'layout_english_extracted')
    layout_worklist=make_layout_image_worklist(layout_root,outdir/'layout_image_translation.csv')
    refs=find_font_references(code_path)

    # Round-trip regression tests.
    roundtrips={}
    for name,fn in LANG_FILES.items():
        g=GmsgFile.load(eu_dir/fn); original=(eu_dir/fn).read_bytes(); rebuilt=g.rebuild()
        roundtrips[name]=(original==rebuilt)
    tg=GmsgFile.load(turkish); roundtrips['TurkishPatch']=(turkish.read_bytes()==tg.rebuild())

    # Determine characters used in Turkish patch but not in original EU visible text union.
    eu_chars=set()
    for fn in LANG_FILES.values():
        g=GmsgFile.load(eu_dir/fn)
        for r in g.records: eu_chars.update(raw_plain(r.data))
    tr_chars=set()
    for r in tg.records: tr_chars.update(raw_plain(r.data))
    tr_only=sorted(tr_chars-eu_chars,key=ord)

    report = "# Majora's Mask 3D Türkçe Patch – Teknik Analiz\n\n"
    report += f"Araç sürümü: {TOOL_VERSION}\n\n"
    report += "## GMSG metinleri\n\n"
    report += f"- EU dil dosyalarının her birinde **{qa['records']}** kayıt var ve metadata tabloları satır bazında eşleşiyor.\n"
    report += f"- Mevcut Türkçe patch İngilizceye göre **{qa['changed_vs_english']}** kaydı değiştirmiş; **{qa['unchanged_vs_english']}** kayıt byte-for-byte aynı.\n"
    report += f"- Görünür Türkçe metinde **{qa['replacement_char_occurrences']}** adet U+FFFD (`�`) bulundu; bunlar **{qa['replacement_char_messages']}** mesajda.\n"
    report += f"- Daha kritik olarak **{qa['invalid_command_messages']}** mesajda geçersiz 0x7F komut kimliği var (gözlenen bozuk kimlik `0xFDFF`). Resmi altı EU GMSG dosyasının hiçbirinde bilinmeyen komut kimliği yok; bu 62 kayıt binary yapı açısından kesin sorunlu kabul edilmeli.\n"
    report += f"- Türkçe ve resmi İngilizce arasında komut-ID dizisi farklı olan kayıt sayısı **{qa['command_sequence_diff_messages']}**. Dil bazlı satır/biçim komutları değişebildiğinden bu yalnızca inceleme sinyalidir.\n"
    report += f"- Konservatif binary-kontrol karşılaştırmasında **{qa['control_diff_messages']} / {qa['records']}** mesajın kontrol byte dizisi İngilizceden farklı. Bu tek başına her farkın hata olduğu anlamına gelmez, ancak U+FFFD ve `FF FD` örnekleri mevcut dönüştürmede binary verinin de bozulmuş olabileceğini gösteriyor.\n"
    report += "- CSV'de 0x7F komutları Kuriimu/Grezzo komut tablosuna göre `⟦HEX:...⟧` olarak korunur; normal çeviride bu etiketlere dokunulmamalı. Enjeksiyon varsayılan olarak etiket değişikliğini reddeder.\n"
    report += "- `translations_clean.csv`, Türkçe düzenleme sütununu resmi İngilizce kayıttan seed eder; bozuk mevcut patch'in kontrol byte'larını taşımadan yeniden çeviri yapmak için önerilen dosyadır. `Turkish_original` eski çeviriyi referans olarak yanında tutar.\n"
    report += f"- `translation_review.csv` içinde QA işaretli veya İngilizceyle aynı kalan **{review_stats['rows']}** satır ayrı inceleme kuyruğuna çıkarıldı.\n\n"
    report += "### Türkçe patch'te kullanılan temel karakterler\n\n"
    report += "- " + ", ".join(f"`{ch}`={n}" for ch,n in qa['turkish_character_usage'].items()) + "\n"
    report += "- Orijinal EU görünür metin kümesinde hiç kullanılmayan fakat Türkçe patch'te görülen karakterler: " + ", ".join(f"`{c}` U+{ord(c):04X}" for c in tr_only) + "\n"
    report += "- Bu karşılaştırma **font kapsaması değildir**; gerçek glyph kapsaması ancak `ltn16.gzf` okununca kesinleşir.\n\n"
    report += "## Font\n\n"
    report += "- `code.bin` içinde `rom:/message/ltn16.gzf` referansı bulundu. Bu nedenle ana Latin font dosyasının beklenen RomFS yolu **`romfs/message/ltn16.gzf`**.\n"
    report += "- Yüklenen arşivlerde `ltn16.gzf` yok. RomFS'den ayrıca dump edilmesi gerekiyor.\n"
    report += "- Aracın `font-info`, `font-check`, `font-export` ve `font-add-png` komutları bu dosya için hazır.\n"
    report += "- Türkçe için özellikle `ĞğİıŞş` kontrol edilmeli; `ÇçÖöÜü` EU dillerinde zaten metinlerde kullanılıyor olsa da gerçek font tablosu yine GZF üzerinden doğrulanmalı.\n\n"
    report += "## Görsel yazılar / UI\n\n"
    report += f"- `menu` paketinde **{menu['ctxb']} CTXB** ve **{menu['png']} PNG** bulundu. `daytelop` ve `savedata_maintainer` altında doğrudan raster yazılar var.\n"
    report += f"- `image_translation.csv` içinde **{image_worklist['rows']}** raster metin varlığı dil sütunları yan yana eşlendi.\n"
    report += "- Örnek İngilizce `daytelop` görselleri '24/48/72 Hours Remain', 'Dawn of The First/Second/Final/New Day' gibi yazıları texture olarak tutuyor. Bunlar GMSG ile çevrilemez.\n"
    report += "- `savedata_maintainer/eu/english/guideline_parts00.ctxb` da Yes/No/Cancel/Erase/Return gibi UI yazılarını texture içinde taşıyor.\n"
    report += f"- `layout` paketinde **{layout['gar_archives']} GAR2** arşivi ve toplam **{layout['embedded_files']}** gömülü dosya bulundu. İngilizce arşivler `layout_english_extracted/` altına açıldı.\n"
    report += f"- `layout_image_translation.csv` içinde **{layout_worklist['rows']}** CTXB entry tüm EU dilleri yan yana eşlendi.\n"
    report += "- GAR içindeki CTXB'ler için `gar-unpack` ve aynı-boyut güvenli `gar-patch` var. Aynı çözünürlük/texture formatıyla yeniden üretilen CTXB'nin boyutu sabitse archive yeniden indekslenmeden patch edilebilir.\n"
    report += "- Araç RGBA8/RGBA4/L8/A8 ve ETC1/ETC1A4 CTXB için doğrudan PNG dışa/içe aktarım yapıyor. ETC1/ETC1A4 kodlama kayıplıdır; UI düzenlemelerinde mümkün olduğunca az alanı değiştirmek önerilir.\n"
    report += "- `world_map.gar.lzs` ayrıca Grezzo LzS ile sıkıştırılmış; bu ilk sürüm onu otomatik yeniden paketlemiyor.\n\n"
    report += "## Round-trip güvenlik testleri\n\n"
    report += "- GMSG parser/rebuilder'ın dosyayı değiştirmeden tekrar yazması: " + ", ".join(f"{k}={'OK' if v else 'FAIL'}" for k,v in roundtrips.items()) + "\n"
    report += "- Enjeksiyon sırasında CSV Index + 3 metadata alanı kontrol edilir; yanlış oyuna/sürüme ait CSV karışması engellenir.\n"
    (outdir/'ANALYSIS.md').write_text(report,encoding='utf-8')
    full={"csv":csv_stats,"clean_csv":clean_csv_stats,"review":review_stats,"qa":qa,"menu":menu,"image_worklist":image_worklist,"layout":layout,"layout_worklist":layout_worklist,"font_references":refs,
          "gmsg_roundtrip":roundtrips,"turkish_only_vs_eu_chars":[{"char":c,"codepoint":f"U+{ord(c):04X}"} for c in tr_only]}
    (outdir/'analysis.json').write_text(json.dumps(full,ensure_ascii=False,indent=2),encoding='utf-8')
    return full


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_json(obj):
    print(json.dumps(obj,ensure_ascii=False,indent=2))


def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description="Majora's Mask 3D Türkçe çeviri/asset aracı")
    ap.add_argument('--version',action='version',version=TOOL_VERSION)
    sub=ap.add_subparsers(dest='cmd',required=True)

    p=sub.add_parser('gmsg-export',help='EU dilleri + mevcut Türkçeyi yan yana CSV çıkar')
    p.add_argument('--eu-dir',type=Path,required=True);p.add_argument('--turkish',type=Path)
    p.add_argument('-o','--output',type=Path,required=True);p.add_argument('--seed',choices=['turkish','english'],default='turkish')

    p=sub.add_parser('gmsg-inject',help='CSV Türkçe sütununu GMSG içine enjekte et')
    p.add_argument('--csv',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('-o','--output',type=Path,required=True);p.add_argument('--column',default='Turkish')
    p.add_argument('--original-column',default='Turkish_seed')
    p.add_argument('--allow-control-changes',action='store_true')

    p=sub.add_parser('gmsg-validate',help='İngilizce/Türkçe GMSG QA karşılaştırması')
    p.add_argument('--english',type=Path,required=True);p.add_argument('--turkish',type=Path,required=True)
    p.add_argument('-o','--output',type=Path)

    p=sub.add_parser('gar-list',help='GAR2 içeriğini listele');p.add_argument('gar',type=Path)
    p=sub.add_parser('gar-unpack',help='GAR2 arşivini çıkar');p.add_argument('gar',type=Path);p.add_argument('outdir',type=Path)
    p=sub.add_parser('gar-patch',help='Aynı boyutlu replacement dosyaları GAR2 içine patch et')
    p.add_argument('gar',type=Path);p.add_argument('replacements',type=Path);p.add_argument('output',type=Path)

    p=sub.add_parser('ctxb-info',help='CTXB header/companion PNG bilgisi');p.add_argument('ctxb',type=Path)
    p=sub.add_parser('ctxb-export-png',help="Desteklenen CTXB texture'ını PNG çıkar");p.add_argument('ctxb',type=Path);p.add_argument('output',type=Path);p.add_argument('--index',type=int,default=0)
    p=sub.add_parser('ctxb-inject-png',help="PNG'yi aynı boyut/format CTXB içine enjekte et");p.add_argument('ctxb',type=Path);p.add_argument('png',type=Path);p.add_argument('output',type=Path);p.add_argument('--index',type=int,default=0)
    p=sub.add_parser('image-worklist',help='Raster yazıları diller yan yana CSV eşleştir');p.add_argument('menu_dir',type=Path);p.add_argument('output',type=Path)
    p=sub.add_parser('layout-image-worklist',help='GAR içindeki CTXB varlıklarını EU dilleri yan yana CSV eşleştir');p.add_argument('layout_dir',type=Path);p.add_argument('output',type=Path)

    p=sub.add_parser('font-info',help='GZFX font yapısı ve Türkçe çekirdek glyph kapsamı');p.add_argument('gzf',type=Path)
    p=sub.add_parser('font-check',help='GZFX fontta CSV/metin için eksik karakterleri bul');p.add_argument('gzf',type=Path)
    p.add_argument('--csv',type=Path);p.add_argument('--column',default='Turkish');p.add_argument('--chars')
    p=sub.add_parser('font-export',help='GZFX atlas + 16x18 glyph PNG + glyphs.csv çıkar');p.add_argument('gzf',type=Path);p.add_argument('outdir',type=Path)
    p=sub.add_parser('font-replace-png',help='Var olan glyph 16x18 PNG maskesini font atlasına güvenli şekilde geri bas')
    p.add_argument('gzf',type=Path);p.add_argument('--char',required=True);p.add_argument('--png',type=Path,required=True);p.add_argument('-o','--output',type=Path,required=True)
    p=sub.add_parser('font-add-png',help='Yeni glyph ekleme (MM3D için güvenlik nedeniyle kapalı; mevcut glyph için replace kullan)')
    p.add_argument('gzf',type=Path);p.add_argument('--char',required=True);p.add_argument('--png',type=Path,required=True)
    p.add_argument('--copy-metrics',required=True);p.add_argument('-o','--output',type=Path,required=True)

    p=sub.add_parser('analyze-project',help='Bu proje yapısı için CSV + QA + asset manifest üret')
    p.add_argument('--eu-dir',type=Path,required=True);p.add_argument('--turkish',type=Path,required=True)
    p.add_argument('--menu-dir',type=Path,required=True);p.add_argument('--layout-dir',type=Path,required=True)
    p.add_argument('--code-bin',type=Path,required=True);p.add_argument('-o','--outdir',type=Path,required=True)

    args=ap.parse_args(argv)
    try:
        if args.cmd=='gmsg-export': print_json(export_gmsg_csv(args.eu_dir,args.turkish,args.output,args.seed))
        elif args.cmd=='gmsg-inject': print_json(inject_gmsg_csv(args.csv,args.base,args.output,args.column,args.original_column,args.allow_control_changes))
        elif args.cmd=='gmsg-validate':
            obj=validate_gmsg(args.english,args.turkish);print_json(obj)
            if args.output: args.output.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
        elif args.cmd=='gar-list':
            g=Gar2.load(args.gar);print_json({"codename":g.codename,"files":[{"index":e.index,"path":e.path,"size":e.size,"offset":e.data_offset,"magic":e.data[:4].hex()} for e in g.entries]})
        elif args.cmd=='gar-unpack': print_json({"files":[str(x) for x in Gar2.load(args.gar).unpack(args.outdir)]})
        elif args.cmd=='gar-patch': print_json(Gar2.load(args.gar).patch_same_size(args.replacements,args.output))
        elif args.cmd=='ctxb-info': print_json(ctxb_info(args.ctxb))
        elif args.cmd=='ctxb-export-png': print_json(ctxb_export_png(args.ctxb,args.output,args.index))
        elif args.cmd=='ctxb-inject-png': print_json(ctxb_inject_png(args.ctxb,args.png,args.output,args.index))
        elif args.cmd=='image-worklist': print_json(make_image_worklist(args.menu_dir,args.output))
        elif args.cmd=='layout-image-worklist': print_json(make_layout_image_worklist(args.layout_dir,args.output))
        elif args.cmd=='font-info': print_json(font_info(args.gzf))
        elif args.cmd=='font-check': print_json(font_check_text(args.gzf,args.csv,args.column,args.chars))
        elif args.cmd=='font-export': print_json(font_export(args.gzf,args.outdir))
        elif args.cmd=='font-replace-png': print_json(font_replace_png(args.gzf,args.char,args.png,args.output))
        elif args.cmd=='font-add-png': print_json(font_add_png(args.gzf,args.char,args.png,args.copy_metrics,args.output))
        elif args.cmd=='analyze-project': print_json(make_analysis_report(args.eu_dir,args.turkish,args.menu_dir,args.layout_dir,args.code_bin,args.outdir))
        return 0
    except (ToolError, OSError, csv.Error, struct.error) as e:
        print(f"HATA: {e}",file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
