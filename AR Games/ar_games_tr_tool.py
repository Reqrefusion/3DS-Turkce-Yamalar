#!/usr/bin/env python3
"""AR Games (Nintendo 3DS) Turkish localization / LayeredFS helper.

Tested against: CTR-N-HARP (EUR), Title ID 0004001000022E00.
No third-party Python packages are required.

Commands
--------
  romfs-extract CXI OUT_ROMFS
  csv-extract   ROMFS OUT.csv
  validate      ROMFS translations.csv
  inject        BASE.msbt translations.csv OUT.msbt
  patch         ROMFS translations.csv OUT_DIR [--target EU_English | --all-eu]

CSV control tokens are reversible and MUST be kept verbatim in translations:
  [[C:GGGG:IIII:HEX]]  MSBT control/open tag (0x000E)
  [[E:GGGG:IIII]]      MSBT close tag (0x000F)
Literal newlines are stored inside quoted CSV cells.
"""
from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

TITLE_ID = "0004001000022E00"
LANGS = [
    ("EU_English", "English"),
    ("EU_Dutch", "Dutch"),
    ("EU_French", "French"),
    ("EU_German", "German"),
    ("EU_Italian", "Italian"),
    ("EU_Portuguese", "Portuguese"),
    ("EU_Russian", "Russian"),
    ("EU_Spanish", "Spanish"),
]
CTRL_RE = re.compile(
    r"\[\[C:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4}):([0-9A-Fa-f]*)\]\]"
    r"|\[\[E:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4})\]\]"
)
ANY_CTRL_RE = re.compile(r"\[\[(?:C|E):[^\]]+\]\]")


def align(v: int, a: int) -> int:
    return (v + a - 1) & ~(a - 1)


def u16(b: bytes, o: int, e: str) -> int:
    return struct.unpack_from(e + "H", b, o)[0]


def u32(b: bytes, o: int, e: str = "<") -> int:
    return struct.unpack_from(e + "I", b, o)[0]


def u64(b: bytes, o: int, e: str = "<") -> int:
    return struct.unpack_from(e + "Q", b, o)[0]


def p16(v: int, e: str) -> bytes:
    return struct.pack(e + "H", v)


def p32(v: int, e: str) -> bytes:
    return struct.pack(e + "I", v)


def get_endian(b: bytes) -> str:
    bom = b[8:10]
    if bom == b"\xff\xfe":
        return "<"
    if bom == b"\xfe\xff":
        return ">"
    raise ValueError(f"Unsupported BOM: {bom.hex()}")


# ---------------------------------------------------------------------------
# NCCH/CXI + RomFS extractor
# ---------------------------------------------------------------------------
class RomFS:
    """Minimal read-only 3DS RomFS (IVFC Level 3) walker."""

    def __init__(self, blob: bytes, base: int):
        self.b = blob
        self.base = base
        if blob[base : base + 4] != b"IVFC":
            raise ValueError(
                "RomFS does not start with IVFC. The CXI may be encrypted; "
                "decrypt/dump it first."
            )
        master = u32(blob, base + 0x08)
        l3_size = u64(blob, base + 0x44)
        l3_bs = 1 << u32(blob, base + 0x4C)
        # Physical IVFC layout: header + aligned master hash, then aligned L3.
        self.l3 = base + align(0x5C + align(master, 0x20), l3_bs)
        self.l3_size = l3_size
        h = self.l3
        if u32(blob, h) != 0x28:
            raise ValueError(f"Invalid RomFS Level 3 header at {h:#x}")
        vals = struct.unpack_from("<10I", blob, h)
        (
            _,
            self.dir_hash_off,
            self.dir_hash_len,
            self.dir_meta_off,
            self.dir_meta_len,
            self.file_hash_off,
            self.file_hash_len,
            self.file_meta_off,
            self.file_meta_len,
            self.file_data_off,
        ) = vals
        self.dir_meta = h + self.dir_meta_off
        self.file_meta = h + self.file_meta_off
        self.file_data = h + self.file_data_off

    def dirent(self, off: int):
        p = self.dir_meta + off
        parent, sib, child, first_file, hash_next, name_len = struct.unpack_from(
            "<6I", self.b, p
        )
        name = (
            self.b[p + 0x18 : p + 0x18 + name_len].decode("utf-16le")
            if name_len
            else ""
        )
        return parent, sib, child, first_file, hash_next, name

    def fileent(self, off: int):
        p = self.file_meta + off
        parent, sib = struct.unpack_from("<II", self.b, p)
        data_off, size = struct.unpack_from("<QQ", self.b, p + 8)
        hash_next, name_len = struct.unpack_from("<II", self.b, p + 0x18)
        name = (
            self.b[p + 0x20 : p + 0x20 + name_len].decode("utf-16le")
            if name_len
            else ""
        )
        return parent, sib, data_off, size, hash_next, name

    def walk(self):
        seen_dirs: set[int] = set()
        seen_files: set[int] = set()

        def rec(dir_off: int, path: Path):
            while dir_off != 0xFFFFFFFF:
                if dir_off in seen_dirs:
                    return
                seen_dirs.add(dir_off)
                _, sibling, child, first_file, _, name = self.dirent(dir_off)
                cur = path / name if name else path

                file_off = first_file
                while file_off != 0xFFFFFFFF:
                    if file_off in seen_files:
                        break
                    seen_files.add(file_off)
                    _, file_sibling, data_off, size, _, file_name = self.fileent(file_off)
                    yield cur / file_name, self.file_data + data_off, size
                    file_off = file_sibling

                if child != 0xFFFFFFFF:
                    yield from rec(child, cur)
                dir_off = sibling

        yield from rec(0, Path("."))


def ncch_romfs(blob: bytes) -> tuple[int, int]:
    if blob[0x100:0x104] != b"NCCH":
        raise ValueError("Input is not an NCCH/CXI image")
    media_unit = 0x200
    romfs_off = u32(blob, 0x1B0) * media_unit
    romfs_size = u32(blob, 0x1B4) * media_unit
    if not romfs_off or not romfs_size:
        raise ValueError("NCCH has no RomFS")
    return romfs_off, romfs_size


def extract_romfs(cxi: Path, out: Path) -> None:
    blob = cxi.read_bytes()
    roff, rsize = ncch_romfs(blob)
    romfs = RomFS(blob, roff)
    files = list(romfs.walk())
    for rel, off, size in files:
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob[off : off + size])
    print(
        f"OK: {len(files)} RomFS files extracted; "
        f"NCCH RomFS={roff:#x}/{rsize:#x}, L3={romfs.l3:#x} -> {out}"
    )


# ---------------------------------------------------------------------------
# MSBT reader/writer
# ---------------------------------------------------------------------------
@dataclass
class Section:
    magic: str
    raw: bytes
    data: bytes


class MSBT:
    def __init__(self, blob: bytes):
        if blob[:8] != b"MsgStdBn":
            raise ValueError("Not an MSBT (MsgStdBn) file")
        self.blob = blob
        self.e = get_endian(blob)
        self.encoding = blob[0x0C]
        self.version = blob[0x0D]
        self.section_count = u16(blob, 0x0E, self.e)
        self.header = bytearray(blob[:0x20])
        self.sections: list[Section] = []
        pos = 0x20
        for _ in range(self.section_count):
            magic = blob[pos : pos + 4].decode("ascii")
            size = u32(blob, pos + 4, self.e)
            end = pos + 0x10 + size
            next_pos = align(end, 0x10)
            self.sections.append(
                Section(magic, blob[pos:next_pos], blob[pos + 0x10 : end])
            )
            pos = next_pos
        self.labels = self._parse_labels()
        self.text_raw = self._parse_txt2_raw()
        self.texts = [decode_msbt_text(x, self.e, self.encoding) for x in self.text_raw]
        self.styles = self._parse_tsy1()

    def _parse_labels(self) -> dict[int, str]:
        sec = next(s for s in self.sections if s.magic == "LBL1")
        d = sec.data
        groups = u32(d, 0, self.e)
        out: dict[int, str] = {}
        for gi in range(groups):
            n = u32(d, 4 + gi * 8, self.e)
            off = u32(d, 8 + gi * 8, self.e)
            p = off
            for _ in range(n):
                ln = d[p]
                p += 1
                name = d[p : p + ln].decode("ascii")
                p += ln
                idx = u32(d, p, self.e)
                p += 4
                out[idx] = name
        return out

    def _parse_txt2_raw(self) -> list[bytes]:
        sec = next(s for s in self.sections if s.magic == "TXT2")
        d = sec.data
        n = u32(d, 0, self.e)
        offsets = [u32(d, 4 + i * 4, self.e) for i in range(n)]
        out = []
        for i, off in enumerate(offsets):
            end = offsets[i + 1] if i + 1 < n else len(d)
            out.append(cut_msbt_string(d[off:end], self.e, self.encoding))
        return out

    def _parse_tsy1(self) -> list[int]:
        sec = next((s for s in self.sections if s.magic == "TSY1"), None)
        if not sec:
            return [0xFFFFFFFF] * len(self.texts)
        if len(sec.data) % 4:
            raise ValueError("Invalid TSY1 size")
        vals = [u32(sec.data, i, self.e) for i in range(0, len(sec.data), 4)]
        if len(vals) != len(self.texts):
            raise ValueError("TSY1 count differs from TXT2 count")
        return vals

    def rebuild_with_texts(self, token_texts: list[str]) -> bytes:
        if len(token_texts) != len(self.texts):
            raise ValueError("Text count mismatch")
        encoded = [encode_msbt_text(t, self.e, self.encoding) for t in token_texts]
        n = len(encoded)
        data = bytearray(p32(n, self.e))
        base = 4 + 4 * n
        cur = base
        for x in encoded:
            data += p32(cur, self.e)
            cur += len(x)
        for x in encoded:
            data += x

        output_sections: list[bytes] = []
        for sec in self.sections:
            if sec.magic != "TXT2":
                output_sections.append(sec.raw)
                continue
            hdr = bytearray(sec.raw[:0x10])
            hdr[4:8] = p32(len(data), self.e)
            raw = bytes(hdr) + bytes(data)
            raw += b"\xAB" * (align(len(raw), 0x10) - len(raw))
            output_sections.append(raw)

        out = bytearray(self.header)
        for section in output_sections:
            out += section
        # File size in MSBT header.
        out[0x12:0x16] = p32(len(out), self.e)
        return bytes(out)


def cut_msbt_string(raw: bytes, e: str, encoding: int) -> bytes:
    if encoding != 1:
        raise NotImplementedError("This helper currently supports UTF-16 MSBT only")
    p = 0
    while p + 2 <= len(raw):
        c = u16(raw, p, e)
        if c == 0:
            return raw[: p + 2]
        if c == 0x000E:
            if p + 8 > len(raw):
                raise ValueError("Truncated MSBT control tag")
            plen = u16(raw, p + 6, e)
            p += 8 + plen
        elif c == 0x000F:
            p += 6
        else:
            p += 2
    raise ValueError("MSBT string has no terminator")


def decode_msbt_text(raw: bytes, e: str, encoding: int) -> str:
    if encoding != 1:
        raise NotImplementedError("Only UTF-16 MSBT is supported")
    out: list[str] = []
    chars: list[int] = []

    def flush() -> None:
        if not chars:
            return
        bb = b"".join(p16(c, e) for c in chars)
        out.append(
            bb.decode("utf-16le" if e == "<" else "utf-16be", "surrogatepass")
        )
        chars.clear()

    p = 0
    while p + 2 <= len(raw):
        c = u16(raw, p, e)
        if c == 0:
            flush()
            break
        if c == 0x000E:
            flush()
            group = u16(raw, p + 2, e)
            idx = u16(raw, p + 4, e)
            plen = u16(raw, p + 6, e)
            params = raw[p + 8 : p + 8 + plen]
            out.append(f"[[C:{group:04X}:{idx:04X}:{params.hex().upper()}]]")
            p += 8 + plen
        elif c == 0x000F:
            flush()
            group = u16(raw, p + 2, e)
            idx = u16(raw, p + 4, e)
            out.append(f"[[E:{group:04X}:{idx:04X}]]")
            p += 6
        else:
            chars.append(c)
            p += 2
    return "".join(out)


def encode_msbt_text(text: str, e: str, encoding: int) -> bytes:
    if encoding != 1:
        raise NotImplementedError("Only UTF-16 MSBT is supported")
    out = bytearray()
    pos = 0
    codec = "utf-16le" if e == "<" else "utf-16be"
    for m in CTRL_RE.finditer(text):
        out += text[pos : m.start()].encode(codec, "surrogatepass")
        if m.group(1) is not None:
            group = int(m.group(1), 16)
            idx = int(m.group(2), 16)
            params = bytes.fromhex(m.group(3))
            out += (
                p16(0x000E, e)
                + p16(group, e)
                + p16(idx, e)
                + p16(len(params), e)
                + params
            )
        else:
            group = int(m.group(4), 16)
            idx = int(m.group(5), 16)
            out += p16(0x000F, e) + p16(group, e) + p16(idx, e)
        pos = m.end()
    out += text[pos:].encode(codec, "surrogatepass")
    out += p16(0, e)
    return bytes(out)


# ---------------------------------------------------------------------------
# MSBP style metadata + CSV
# ---------------------------------------------------------------------------
def parse_sectioned(blob: bytes, magic8: bytes) -> tuple[str, dict[str, bytes]]:
    if blob[:8] != magic8:
        raise ValueError(f"Expected {magic8!r}")
    e = get_endian(blob)
    count = u16(blob, 0x0E, e)
    out: dict[str, bytes] = {}
    pos = 0x20
    for _ in range(count):
        magic = blob[pos : pos + 4].decode("ascii")
        size = u32(blob, pos + 4, e)
        out[magic] = blob[pos + 0x10 : pos + 0x10 + size]
        pos = align(pos + 0x10 + size, 0x10)
    return e, out


def read_styles(msbp_path: Path) -> list[tuple[int, int, int, int]]:
    e, secs = parse_sectioned(msbp_path.read_bytes(), b"MsgPrjBn")
    syl = secs.get("SYL3")
    if not syl:
        return []
    count = u32(syl, 0, e)
    if 4 + count * 16 > len(syl):
        raise ValueError("Invalid SYL3 section")
    return [struct.unpack_from(e + "4I", syl, 4 + i * 16) for i in range(count)]


def load_languages(romfs: Path) -> dict[str, MSBT]:
    result: dict[str, MSBT] = {}
    for folder, name in LANGS:
        path = romfs / "message" / folder / "AR_ACT.msbt"
        if path.exists():
            result[name] = MSBT(path.read_bytes())
    if not result:
        raise FileNotFoundError("No message/EU_*/AR_ACT.msbt files found")
    return result


def visible_text(t: str) -> str:
    return ANY_CTRL_RE.sub("", t)


def text_metrics(t: str) -> tuple[int, int, int]:
    v = visible_text(t)
    lines = v.split("\n")
    return (
        len(v.replace("\n", "")),
        max((len(x) for x in lines), default=0),
        max(1, len(lines)),
    )


def control_signature(t: str) -> list[str]:
    return ANY_CTRL_RE.findall(t)


def csv_extract(romfs: Path, outcsv: Path) -> None:
    langs = load_languages(romfs)
    base = langs.get("English") or next(iter(langs.values()))
    labels = base.labels
    for name, msbt in langs.items():
        if msbt.labels != labels:
            raise ValueError(f"LBL1 label map differs for {name}")
        if len(msbt.texts) != len(base.texts):
            raise ValueError(f"TXT2 count differs for {name}")

    styles: list[tuple[int, int, int, int]] = []
    msbp = romfs / "message" / "EU_English" / "CPLAY_NCL_AR_ACT.msbp"
    if msbp.exists():
        styles = read_styles(msbp)

    language_columns = [name for _, name in LANGS if name in langs]
    fields = [
        "Index",
        "Label",
        "StyleIndex",
        "RegionWidth",
        "StyleLineLimit",
        "FontIndex",
        *language_columns,
        "Turkish",
        "SoftMaxChars",
        "SoftMaxLineChars",
        "MaxExistingLines",
        "TurkishChars",
        "TurkishMaxLineChars",
        "LengthStatus",
        "TranslatorNote",
    ]
    outcsv.parent.mkdir(parents=True, exist_ok=True)
    with outcsv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL)
        w.writeheader()
        for i in range(len(base.texts)):
            row: dict[str, str | int] = {"Index": i, "Label": labels.get(i, "")}
            vals = []
            for _, name in LANGS:
                if name in langs:
                    t = langs[name].texts[i]
                    row[name] = t
                    vals.append(t)

            sid = base.styles[i] if i < len(base.styles) else 0xFFFFFFFF
            row["StyleIndex"] = "" if sid == 0xFFFFFFFF else sid
            if sid != 0xFFFFFFFF and sid < len(styles):
                width, lines, font, _color = styles[sid]
                row["RegionWidth"] = width
                row["StyleLineLimit"] = lines
                row["FontIndex"] = font
            else:
                row["RegionWidth"] = row["StyleLineLimit"] = row["FontIndex"] = ""

            ms = [text_metrics(x) for x in vals]
            row["Turkish"] = ""
            row["SoftMaxChars"] = max((x[0] for x in ms), default=0)
            row["SoftMaxLineChars"] = max((x[1] for x in ms), default=0)
            row["MaxExistingLines"] = max((x[2] for x in ms), default=1)
            row["TurkishChars"] = ""
            row["TurkishMaxLineChars"] = ""
            row["LengthStatus"] = ""
            row["TranslatorNote"] = ""
            w.writerow(row)
    print(f"OK: {len(base.texts)} messages / {len(language_columns)} languages -> {outcsv}")


def read_csv_rows(csvpath: Path) -> list[dict[str, str]]:
    with csvpath.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_turkish(csvpath: Path, base: MSBT) -> list[str]:
    rows = read_csv_rows(csvpath)
    by_idx: dict[int, dict[str, str]] = {}
    for row in rows:
        try:
            idx = int(row["Index"])
        except Exception as exc:
            raise ValueError("Every CSV row needs a numeric Index") from exc
        if idx in by_idx:
            raise ValueError(f"Duplicate CSV Index={idx}")
        by_idx[idx] = row

    texts: list[str] = []
    for i, source in enumerate(base.texts):
        if i not in by_idx:
            raise ValueError(f"Missing CSV row Index={i}")
        row = by_idx[i]
        tr = row.get("Turkish", "")
        # The source contains 26 intentionally empty slots. Keep those empty.
        if source and not tr:
            raise ValueError(
                f"Turkish is empty at Index={i}, Label={row.get('Label', '')!r}"
            )
        if not source and tr:
            raise ValueError(
                f"Index={i} is empty in the source but Turkish is not empty; "
                "do not populate unused TXT2 slots"
            )
        texts.append(tr)
    return texts


def validate(romfs: Path, csvpath: Path, quiet: bool = False) -> list[str]:
    langs = load_languages(romfs)
    base = langs.get("English") or next(iter(langs.values()))
    rows = read_csv_rows(csvpath)
    if len(rows) != len(base.texts):
        raise ValueError(f"CSV rows={len(rows)}, MSBT texts={len(base.texts)}")
    turkish = read_turkish(csvpath, base)

    issues: list[str] = []
    for i, (src, tr) in enumerate(zip(base.texts, turkish)):
        row = rows[i]
        try:
            if int(row["Index"]) != i:
                issues.append(f"Index order differs at physical CSV row {i}")
        except Exception:
            issues.append(f"Invalid Index at physical CSV row {i}")
        label = base.labels.get(i, "")
        if row.get("Label", "") != label:
            issues.append(f"Index {i}: Label differs ({row.get('Label')!r} != {label!r})")
        if control_signature(src) != control_signature(tr):
            issues.append(f"Index {i} {label}: MSBT control-tag sequence differs")
        # Round-trip the exact Turkish token stream through the MSBT encoder/decoder.
        rt = decode_msbt_text(encode_msbt_text(tr, base.e, base.encoding), base.e, base.encoding)
        if rt != tr:
            issues.append(f"Index {i} {label}: UTF-16/control-token round-trip differs")

    # Build + reparse an entire MSBT to catch offsets/alignment/count errors.
    rebuilt = base.rebuild_with_texts(turkish)
    reparsed = MSBT(rebuilt)
    if reparsed.labels != base.labels:
        issues.append("Rebuilt MSBT LBL1 map differs")
    if reparsed.texts != turkish:
        issues.append("Rebuilt MSBT TXT2 text differs after reparsing")
    if len(reparsed.sections) != len(base.sections):
        issues.append("Rebuilt MSBT section count differs")
    # All non-TXT2 sections must remain byte-for-byte unchanged.
    for old, new in zip(base.sections, reparsed.sections):
        if old.magic != "TXT2" and old.raw != new.raw:
            issues.append(f"Non-TXT2 section changed: {old.magic}")

    if issues:
        if not quiet:
            print("VALIDATION FAILED:")
            for issue in issues:
                print(" -", issue)
        return issues

    if not quiet:
        statuses = {"OK": 0, "KONTROL": 0, "BOŞ": 0, "OTHER": 0}
        for row in rows:
            status = row.get("LengthStatus", "")
            statuses[status if status in statuses else "OTHER"] += 1
        print(
            "OK: validation passed; "
            f"{len(turkish)} messages, {sum(bool(x) for x in turkish)} translated, "
            f"control tags preserved, MSBT rebuild reparses cleanly. "
            f"CSV status: {statuses}"
        )
    return []


def inject(base_msbt: Path, csvpath: Path, out: Path) -> None:
    base = MSBT(base_msbt.read_bytes())
    turkish = read_turkish(csvpath, base)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base.rebuild_with_texts(turkish))
    # Verify the output we just wrote.
    check = MSBT(out.read_bytes())
    if check.texts != turkish or check.labels != base.labels:
        raise RuntimeError("Post-write MSBT verification failed")
    print(f"OK: injected {sum(bool(x) for x in turkish)} Turkish strings -> {out}")


def patch(
    romfs: Path,
    csvpath: Path,
    outdir: Path,
    target: str,
    all_eu: bool,
    title_id: str,
) -> None:
    issues = validate(romfs, csvpath, quiet=True)
    if issues:
        raise ValueError("Validation failed before patching: " + "; ".join(issues[:5]))

    folders = [x[0] for x in LANGS] if all_eu else [target]
    valid_folders = {x[0] for x in LANGS}
    for folder in folders:
        if folder not in valid_folders:
            raise ValueError(f"Unknown EU language folder: {folder}")

    patch_root = outdir / "luma" / "titles" / title_id / "romfs" / "message"
    written = []
    for folder in folders:
        src = romfs / "message" / folder / "AR_ACT.msbt"
        if not src.exists():
            continue
        base = MSBT(src.read_bytes())
        turkish = read_turkish(csvpath, base)
        dest = patch_root / folder / "AR_ACT.msbt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base.rebuild_with_texts(turkish))
        # Full post-write semantic verification.
        chk = MSBT(dest.read_bytes())
        if chk.texts != turkish or chk.labels != base.labels:
            raise RuntimeError(f"Post-write verification failed: {dest}")
        written.append(dest)

    if not written:
        raise FileNotFoundError("No target AR_ACT.msbt was found to patch")

    mode = "all 8 EU locale folders" if all_eu else target
    (outdir / "README_TR.txt").write_text(
        "AR Games (CTR-N-HARP) Türkçe LayeredFS yaması\n"
        f"Title ID: {title_id}\n\n"
        "Kurulum:\n"
        "1. Paketteki 'luma' klasörünü SD kartın kök diziniyle birleştirin.\n"
        "2. Luma3DS yapılandırmasında 'Enable game patching' açık olsun.\n"
        f"3. Bu paket {mode} için AR_ACT.msbt dosyasını Türkçeleştirir.\n"
        + (
            "4. Tüm EU dil klasörleri yamalı olduğu için sistem dili fark etmez (desteklenen EU dilleri içinde).\n"
            if all_eu
            else "4. Varsayılan paket EU_English'i yamalar; oyunun İngilizce mesaj klasörünü kullanmasını sağlayın.\n"
        )
        + "\nNot: ğ/Ğ, ş/Ş, ı/İ gibi Türkçe glifleri gerçek cihazda/Azahar'da görsel olarak test edin.\n",
        encoding="utf-8",
    )
    print(f"OK: LayeredFS patch ({mode}) -> {outdir}; files={len(written)}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AR Games 3DS MSBT Turkish localization + LayeredFS helper"
    )
    sp = ap.add_subparsers(dest="cmd", required=True)

    p = sp.add_parser("romfs-extract", help="Extract an unencrypted CXI RomFS")
    p.add_argument("cxi", type=Path)
    p.add_argument("out_romfs", type=Path)

    p = sp.add_parser("csv-extract", help="Export all EU languages side-by-side")
    p.add_argument("romfs", type=Path)
    p.add_argument("csv", type=Path)

    p = sp.add_parser("validate", help="Validate Turkish CSV and MSBT round-trip")
    p.add_argument("romfs", type=Path)
    p.add_argument("csv", type=Path)

    p = sp.add_parser("inject", help="Inject Turkish column into one base MSBT")
    p.add_argument("base_msbt", type=Path)
    p.add_argument("csv", type=Path)
    p.add_argument("out", type=Path)

    p = sp.add_parser("patch", help="Build an SD-ready Luma3DS LayeredFS tree")
    p.add_argument("romfs", type=Path)
    p.add_argument("csv", type=Path)
    p.add_argument("outdir", type=Path)
    p.add_argument("--target", default="EU_English")
    p.add_argument("--all-eu", action="store_true")
    p.add_argument("--title-id", default=TITLE_ID)

    ns = ap.parse_args()
    try:
        if ns.cmd == "romfs-extract":
            extract_romfs(ns.cxi, ns.out_romfs)
        elif ns.cmd == "csv-extract":
            csv_extract(ns.romfs, ns.csv)
        elif ns.cmd == "validate":
            issues = validate(ns.romfs, ns.csv)
            if issues:
                raise SystemExit(2)
        elif ns.cmd == "inject":
            inject(ns.base_msbt, ns.csv, ns.out)
        elif ns.cmd == "patch":
            patch(ns.romfs, ns.csv, ns.outdir, ns.target, ns.all_eu, ns.title_id)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
