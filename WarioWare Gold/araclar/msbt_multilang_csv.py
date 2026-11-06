#!/usr/bin/env python3
"""Direct MSBT -> multilingual CSV exporter.

No XMSBT/XML intermediary is used. LBL1 labels are matched by name; TXT2
strings are read by their offset ranges, so embedded NUL/control payloads do
not truncate text.

WarioWare Gold-oriented defaults are provided, but the MSBT parser itself is
generic for ordinary LBL1/TXT2 Nintendo MSBT files.
"""
from __future__ import annotations

import argparse
import csv
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class MSBT:
    path: Path
    endian: str
    encoding: int
    sections: Dict[str, bytes]
    labels: Dict[str, int]
    label_order: List[str]
    texts: List[bytes]


def _u16(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + "H", data, off)[0]


def _u32(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from(endian + "I", data, off)[0]


def parse_msbt(path: Path) -> MSBT:
    data = path.read_bytes()
    if len(data) < 0x20 or data[:8] != b"MsgStdBn":
        raise ValueError(f"Not an MSBT: {path}")

    bom = data[8:10]
    if bom == b"\xff\xfe":
        endian = "<"
    elif bom == b"\xfe\xff":
        endian = ">"
    else:
        raise ValueError(f"Unknown byte order marker {bom.hex()} in {path}")

    encoding = data[0x0C]
    section_count = _u16(data, 0x0E, endian)
    declared_size = _u32(data, 0x12, endian)
    if declared_size != len(data):
        raise ValueError(
            f"Declared file size {declared_size} != actual {len(data)} in {path}"
        )

    sections: Dict[str, bytes] = {}
    pos = 0x20
    for _ in range(section_count):
        if pos + 0x10 > len(data):
            raise ValueError(f"Section header outside file in {path}")
        magic = data[pos : pos + 4].decode("ascii", "strict")
        size = _u32(data, pos + 4, endian)
        start = pos + 0x10
        end = start + size
        if end > len(data):
            raise ValueError(f"Section {magic} outside file in {path}")
        sections[magic] = data[start:end]
        pos = (end + 0x0F) & ~0x0F

    if "TXT2" not in sections:
        raise ValueError(f"TXT2 section missing in {path}")

    labels: Dict[str, int] = {}
    label_pairs: List[Tuple[str, int]] = []
    if "LBL1" in sections:
        s = sections["LBL1"]
        group_count = _u32(s, 0, endian)
        group_table_end = 4 + group_count * 8
        if group_table_end > len(s):
            raise ValueError(f"Invalid LBL1 group table in {path}")
        groups = [
            (_u32(s, 4 + i * 8, endian), _u32(s, 8 + i * 8, endian))
            for i in range(group_count)
        ]
        for count, offset in groups:
            p = offset
            for _ in range(count):
                if p >= len(s):
                    raise ValueError(f"Invalid LBL1 label offset in {path}")
                name_len = s[p]
                p += 1
                if p + name_len + 4 > len(s):
                    raise ValueError(f"Truncated LBL1 label in {path}")
                name = s[p : p + name_len].decode("ascii", "strict")
                p += name_len
                index = _u32(s, p, endian)
                p += 4
                if name in labels:
                    raise ValueError(f"Duplicate label {name!r} in {path}")
                labels[name] = index
                label_pairs.append((name, index))

    s = sections["TXT2"]
    text_count = _u32(s, 0, endian)
    if 4 + text_count * 4 > len(s):
        raise ValueError(f"Invalid TXT2 offset table in {path}")
    offsets = [_u32(s, 4 + i * 4, endian) for i in range(text_count)]
    if offsets != sorted(offsets):
        raise ValueError(f"TXT2 offsets are not sorted in {path}")

    texts: List[bytes] = []
    for i, start in enumerate(offsets):
        end = offsets[i + 1] if i + 1 < text_count else len(s)
        if start > end or end > len(s):
            raise ValueError(f"Invalid TXT2 string range {i} in {path}")
        texts.append(s[start:end])

    for name, idx in label_pairs:
        if idx >= len(texts):
            raise ValueError(f"Label {name!r} points outside TXT2 in {path}")

    # Stable human-friendly order: text index first, then label name.
    label_order = [name for name, _ in sorted(label_pairs, key=lambda x: (x[1], x[0]))]
    return MSBT(path, endian, encoding, sections, labels, label_order, texts)


def render_text(msbt: MSBT, raw: bytes) -> str:
    """Render TXT2 bytes safely for CSV without losing MSBT control payloads.

    UTF-16 control tags of the common MSBT form are represented as:
        <MSBT:0001:0008:0000140000FFFFFFFF>
    where the two 16-bit fields are group/type and the final part is the exact
    payload bytes in file byte order. Newlines are shown as literal \\n so each
    message stays on one physical CSV record.
    """
    # Remove only the final string terminator. Internal NULs are preserved.
    term = b"\x00\x00" if msbt.endian == "<" else b"\x00\x00"
    if msbt.encoding == 1 and len(raw) >= 2 and raw[-2:] == term:
        raw = raw[:-2]
    elif msbt.encoding == 0 and raw.endswith(b"\x00"):
        raw = raw[:-1]

    if msbt.encoding == 0:  # UTF-8 MSBT variant; conservative byte escaping.
        out: List[str] = []
        i = 0
        while i < len(raw):
            b = raw[i]
            if b == 0x0A:
                out.append(r"\n")
                i += 1
            elif b == 0x0D:
                out.append(r"\r")
                i += 1
            elif b == 0x09:
                out.append(r"\t")
                i += 1
            elif b < 0x20 or b == 0x7F:
                out.append(f"\\x{b:02X}")
                i += 1
            else:
                # Decode the longest valid UTF-8 sequence starting here.
                for n in (4, 3, 2, 1):
                    try:
                        chunk = raw[i : i + n]
                        text = chunk.decode("utf-8")
                        if text and len(chunk) == n:
                            out.append(text)
                            i += n
                            break
                    except UnicodeDecodeError:
                        pass
                else:
                    out.append(f"\\x{b:02X}")
                    i += 1
        return "".join(out)

    if msbt.encoding != 1:
        return "<RAW:" + raw.hex().upper() + ">"

    codec = "utf-16-le" if msbt.endian == "<" else "utf-16-be"
    out: List[str] = []
    i = 0
    while i + 2 <= len(raw):
        code = _u16(raw, i, msbt.endian)

        # Standard MSBT inline control: 0x000E, group, type, payload byte size,
        # followed by that many raw bytes. Do not decode payload as characters.
        if code == 0x000E and i + 8 <= len(raw):
            group = _u16(raw, i + 2, msbt.endian)
            typ = _u16(raw, i + 4, msbt.endian)
            payload_len = _u16(raw, i + 6, msbt.endian)
            p0 = i + 8
            p1 = p0 + payload_len
            if p1 <= len(raw):
                payload = raw[p0:p1].hex().upper()
                out.append(f"<MSBT:{group:04X}:{typ:04X}:{payload}>")
                i = p1
                continue

        if code == 0x000A:
            out.append(r"\n")
        elif code == 0x000D:
            out.append(r"\r")
        elif code == 0x0009:
            out.append(r"\t")
        elif code == 0x0000:
            out.append(r"\0")
        elif code == 0x005C:
            out.append(r"\\")
        elif code < 0x20 or 0xD800 <= code <= 0xDFFF or code in (0xFFFE, 0xFFFF):
            out.append(f"\\u{code:04X}")
        else:
            unit = raw[i : i + 2]
            try:
                out.append(unit.decode(codec, "strict"))
            except UnicodeDecodeError:
                out.append(f"\\u{code:04X}")
        i += 2

    if i < len(raw):
        out.append(f"\\x{raw[i]:02X}")
    return "".join(out)


def text_by_label(msbt: MSBT) -> Dict[str, str]:
    return {
        label: render_text(msbt, msbt.texts[index])
        for label, index in msbt.labels.items()
    }


def default_language_roots(game_root: Path) -> Dict[str, Path]:
    msg = game_root / "Message"
    patch_candidates = list(game_root.glob("T*patch/*/romfs/Message/EU/EUen"))
    if len(patch_candidates) != 1:
        raise ValueError(
            f"Expected exactly one Turkish patch EUen root, found {len(patch_candidates)}"
        )
    return {
        "TR": patch_candidates[0],
        "EUen": msg / "EU" / "EUen",
        "USen": msg / "US" / "USen",
        "EUfr": msg / "EU" / "EUfr",
        "USfr": msg / "US" / "USfr",
        "EUde": msg / "EU" / "EUde",
        "EUit": msg / "EU" / "EUit",
        "EUes": msg / "EU" / "EUes",
        "USes": msg / "US" / "USes",
        "JPja": msg / "JP" / "JPja",
    }


def export_all(game_root: Path, out_root: Path) -> Tuple[int, int, List[dict]]:
    roots = default_language_roots(game_root)
    tr_root = roots["TR"]
    rel_files = sorted(p.relative_to(tr_root) for p in tr_root.rglob("*.msbt"))
    if not rel_files:
        raise ValueError("No Turkish patch MSBT files found")

    out_root.mkdir(parents=True, exist_ok=True)
    manifest: List[dict] = []
    total_rows = 0

    columns = list(roots.keys())
    for rel in rel_files:
        parsed: Dict[str, MSBT] = {}
        rendered: Dict[str, Dict[str, str]] = {}
        missing_files: List[str] = []

        for lang, root in roots.items():
            p = root / rel
            if not p.exists():
                missing_files.append(lang)
                continue
            m = parse_msbt(p)
            parsed[lang] = m
            rendered[lang] = text_by_label(m)

        # Primary order comes from TR, then append labels that only occur elsewhere.
        order: List[str] = []
        seen = set()
        if "TR" in parsed:
            for label in parsed["TR"].label_order:
                if label not in seen:
                    seen.add(label); order.append(label)
        for lang in columns:
            if lang in parsed:
                for label in parsed[lang].label_order:
                    if label not in seen:
                        seen.add(label); order.append(label)

        out = out_root / rel.with_suffix(".csv")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)
            w.writerow(["Label"] + columns)
            for label in order:
                w.writerow([label] + [rendered.get(lang, {}).get(label, "") for lang in columns])

        tr_labels = set(parsed.get("TR", MSBT(Path(),"<",1,{}, {}, [], [])).labels)
        mismatch_langs = []
        for lang, m in parsed.items():
            if lang != "TR" and set(m.labels) != tr_labels:
                mismatch_langs.append(lang)

        manifest.append({
            "MSBT": rel.as_posix(),
            "Rows": len(order),
            "TR_Texts": len(parsed["TR"].texts) if "TR" in parsed else 0,
            "TR_Labels": len(parsed["TR"].labels) if "TR" in parsed else 0,
            "Missing_Files": ";".join(missing_files),
            "Label_Set_Differs": ";".join(mismatch_langs),
        })
        total_rows += len(order)

    with (out_root / "_manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys()), quoting=csv.QUOTE_ALL)
        w.writeheader(); w.writerows(manifest)

    return len(rel_files), total_rows, manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("game_root", type=Path, help="Extracted 'Warioware 3ds' directory")
    ap.add_argument("output", type=Path, help="Output directory for per-MSBT CSV files")
    args = ap.parse_args()
    nfiles, nrows, manifest = export_all(args.game_root, args.output)
    diffs = sum(bool(x["Label_Set_Differs"]) for x in manifest)
    missing = sum(bool(x["Missing_Files"]) for x in manifest)
    print(f"CSV files: {nfiles}")
    print(f"Total comparison rows: {nrows}")
    print(f"Files with missing language file: {missing}")
    print(f"Files with differing label sets: {diffs}")


if __name__ == "__main__":
    main()
