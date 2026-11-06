#!/usr/bin/env python3
"""Luigi's Mansion 2 / Dark Moon NLOC multilingual CSV + reinjection tool.

Designed for the 3DS European build and LayeredFS-style patches.
Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import sys
import zipfile
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

LANGUAGES = [
    "english", "ukenglish", "french", "nafrench", "german", "italian",
    "spanish", "naspanish", "dutch", "portuguese", "russian", "japanese",
]
SCOPES = ["fe", "tweaker"]
TEXT_COLUMNS = LANGUAGES + ["turkish_current", "turkish_final"]
TAG_RE = re.compile(r"\{[^{}]*\}")
PARAM_RE = re.compile(r"\{\d+\}")
ZLIB_HEADER_RE = re.compile(b"\x78[\x01\x5e\x9c\xda]")


class ToolError(RuntimeError):
    pass


class Source:
    """Read from either a directory or a ZIP without extracting it."""
    def __init__(self, path: os.PathLike | str):
        self.path = Path(path)
        if not self.path.exists():
            raise ToolError(f"Source not found: {self.path}")
        self._zip = zipfile.ZipFile(self.path, "r") if self.path.is_file() else None
        if self._zip:
            self._names = [n for n in self._zip.namelist() if not n.endswith("/")]
        else:
            self._names = [p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file()]

    def close(self):
        if self._zip:
            self._zip.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    @property
    def names(self) -> List[str]:
        return list(self._names)

    def read(self, name: str) -> bytes:
        if self._zip:
            return self._zip.read(name)
        return (self.path / PurePosixPath(name)).read_bytes()

    def find_suffix(self, suffix: str) -> Optional[str]:
        suffix = suffix.replace("\\", "/").lstrip("/")
        matches = [n for n in self._names if n == suffix or n.endswith("/" + suffix)]
        if not matches:
            return None
        # Prefer the shallowest path, then shortest.
        matches.sort(key=lambda n: (n.count("/"), len(n), n))
        return matches[0]

    def find_all_suffix(self, suffix: str) -> List[str]:
        suffix = suffix.replace("\\", "/").lstrip("/")
        return [n for n in self._names if n == suffix or n.endswith("/" + suffix)]


@dataclass
class Nloc:
    version: int
    lang_hash: int
    flag: int
    rows: Dict[int, str]
    offsets: Dict[int, int]
    table_order: List[int]
    nloc_offset: int
    wrapper_prefix: bytes
    wrapper_payload_size: int


def _decode_ucs2(blob: bytes, pos: int, endian: str) -> str:
    chars: List[str] = []
    fmt = endian + "H"
    while pos + 2 <= len(blob):
        cp = struct.unpack_from(fmt, blob, pos)[0]
        pos += 2
        if cp == 0:
            break
        chars.append(chr(cp))
    return "".join(chars)


def parse_nloc_data(blob: bytes) -> Nloc:
    nloc_offset = blob.find(b"NLOC")
    if nloc_offset < 0:
        raise ToolError("NLOC signature not found")
    if len(blob) < nloc_offset + 20:
        raise ToolError("Truncated NLOC header")

    # Luigi's Mansion 2 stores this header little-endian. The flag is 0 in LMDM.
    magic, version, lang_hash, count, flag = struct.unpack_from("<4sIIII", blob, nloc_offset)
    if magic != b"NLOC":
        raise ToolError("Bad NLOC magic")
    endian = "<" if flag == 0 else ">"
    base = nloc_offset + 20 + count * 8
    if base > len(blob):
        raise ToolError("NLOC string table extends beyond file")

    rows: Dict[int, str] = {}
    offsets: Dict[int, int] = {}
    table_order: List[int] = []
    for i in range(count):
        h, rel_units = struct.unpack_from(endian + "II", blob, nloc_offset + 20 + i * 8)
        pos = base + rel_units * 2  # offsets are 16-bit code-unit offsets
        if pos > len(blob):
            raise ToolError(f"String offset out of range for ID {h:08X}")
        rows[h] = _decode_ucs2(blob, pos, endian)
        offsets[h] = rel_units
        table_order.append(h)

    wrapper_prefix = blob[:nloc_offset]
    wrapper_payload_size = 0
    if nloc_offset == 16 and len(wrapper_prefix) >= 8:
        wrapper_payload_size = struct.unpack_from("<I", wrapper_prefix, 4)[0]
    return Nloc(version, lang_hash, flag, rows, offsets, table_order,
                nloc_offset, wrapper_prefix, wrapper_payload_size)


def encode_nloc(template: Nloc, texts: Mapping[int, str]) -> bytes:
    missing = [h for h in template.table_order if h not in texts]
    extra = [h for h in texts if h not in template.rows]
    if missing:
        raise ToolError(f"Missing {len(missing)} message IDs; first: {missing[0]:08X}")
    if extra:
        # Extra rows are harmless to CSV editing, but cannot be inserted without changing table structure.
        pass

    endian = "<" if template.flag == 0 else ">"
    enc = "utf-16le" if endian == "<" else "utf-16be"

    # Keep the original hash-sorted table order. Strings are repacked sequentially.
    data = bytearray()
    rels: Dict[int, int] = {}
    for h in template.table_order:
        # Offsets are measured in 16-bit code units.
        rels[h] = len(data) // 2
        s = texts[h]
        try:
            raw = s.encode(enc)
        except UnicodeEncodeError as e:
            raise ToolError(f"Cannot encode ID {h:08X}: {e}") from e
        data.extend(raw)
        data.extend(b"\x00\x00")

    out = bytearray()
    # Header is LE in LMDM, matching the original implementation.
    out.extend(struct.pack("<4sIIII", b"NLOC", template.version, template.lang_hash,
                           len(template.table_order), template.flag))
    for h in template.table_order:
        out.extend(struct.pack(endian + "II", h, rels[h]))
    out.extend(data)
    return bytes(out)


def wrap_data(template_blob: bytes, new_nloc: bytes) -> bytes:
    nloc_offset = template_blob.find(b"NLOC")
    if nloc_offset < 0:
        raise ToolError("Template has no NLOC")
    if nloc_offset == 0:
        return new_nloc
    if nloc_offset != 16:
        # Generic fallback: preserve prefix and append; no archive-size metadata known.
        return template_blob[:nloc_offset] + new_nloc

    prefix = bytearray(template_blob[:16])
    struct.pack_into("<I", prefix, 4, len(new_nloc))
    out = prefix + new_nloc
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def update_dict(template_dict: bytes, payload_size: int, data_file_size: int) -> bytes:
    """Update the size fields in the 193-byte .dict companion used by LM2 archives."""
    if len(template_dict) < 0x90:
        raise ToolError(".dict template is unexpectedly short")
    out = bytearray(template_dict)
    # Confirm expected structure before patching fixed offsets.
    if out[-13:] != b".data\x00.debug\x00":
        raise ToolError("Unrecognized .dict layout (missing .data/.debug trailer)")
    # These are 32-bit fields. 0x68 stores the unpadded payload length;
    # 0x74 and 0x84 store the complete .data file length.
    # (The previous implementation incorrectly wrote 64-bit values at
    # 0x78/0x88, leaving the real file-size fields unchanged.)
    struct.pack_into("<I", out, 0x68, payload_size)
    struct.pack_into("<I", out, 0x74, data_file_size)
    struct.pack_into("<I", out, 0x84, data_file_size)
    return bytes(out)


def read_nloc_member(src: Source, scope: str, lang: str) -> Tuple[str, bytes, Nloc]:
    name = src.find_suffix(f"{scope}/{lang}.data")
    if not name:
        raise ToolError(f"Could not find {scope}/{lang}.data in {src.path}")
    blob = src.read(name)
    return name, blob, parse_nloc_data(blob)


def _ordered_ids(english: Nloc) -> List[int]:
    # Physical string order is much closer to the game's logical/dialogue order.
    return sorted(english.rows, key=lambda h: (english.offsets.get(h, 0), h))


def extract_scope(game: Source, patch: Optional[Source], scope: str) -> Tuple[List[dict], dict]:
    langs: Dict[str, Nloc] = {}
    member_names: Dict[str, str] = {}
    for lang in LANGUAGES:
        name = game.find_suffix(f"{scope}/{lang}.data")
        if not name:
            continue
        nloc = parse_nloc_data(game.read(name))
        langs[lang] = nloc
        member_names[lang] = name
    if "english" not in langs:
        raise ToolError(f"No English NLOC found for scope {scope}")

    idset = set(langs["english"].rows)
    mismatch = {lang: len(set(n.rows) ^ idset) for lang, n in langs.items() if set(n.rows) != idset}
    if mismatch:
        raise ToolError(f"Language ID sets differ in {scope}: {mismatch}")

    tr_current: Dict[int, str] = {}
    patch_member = None
    if patch:
        patch_member = patch.find_suffix(f"{scope}/english.data")
        if patch_member:
            tr = parse_nloc_data(patch.read(patch_member))
            tr_current = tr.rows
            if set(tr_current) != idset:
                raise ToolError(f"Patch Turkish/English ID set differs in {scope}")

    rows = []
    for idx, h in enumerate(_ordered_ids(langs["english"]), 1):
        row = {
            "row": idx,
            "scope": scope,
            "id": f"{h:08X}",
        }
        for lang in LANGUAGES:
            row[lang] = langs[lang].rows.get(h, "") if lang in langs else ""
        row["turkish_current"] = tr_current.get(h, "")
        row["turkish_final"] = tr_current.get(h, "")
        row["status"] = ""
        row["reason"] = ""
        row["creative_flag"] = ""
        row["font_missing"] = ""
        row["notes"] = ""
        rows.append(row)

    meta = {
        "scope": scope,
        "rows": len(rows),
        "languages": list(langs),
        "members": member_names,
        "patch_member": patch_member,
        "language_hashes": {lang: f"{n.lang_hash:08X}" for lang, n in langs.items()},
    }
    return rows, meta


def write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["row", "scope", "id"] + LANGUAGES + [
        "turkish_current", "turkish_final", "status", "reason",
        "creative_flag", "font_missing", "notes"
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)


def read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cmd_export(args) -> int:
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    all_meta = {}
    with Source(args.game) as game:
        patch_ctx = Source(args.patch) if args.patch else None
        try:
            for scope in SCOPES:
                try:
                    rows, meta = extract_scope(game, patch_ctx, scope)
                except ToolError as e:
                    if args.skip_missing:
                        print(f"[skip] {scope}: {e}", file=sys.stderr)
                        continue
                    raise
                write_csv(outdir / f"{scope}_multilang.csv", rows)
                all_meta[scope] = meta
                print(f"Exported {len(rows)} rows -> {outdir / f'{scope}_multilang.csv'}")
        finally:
            if patch_ctx:
                patch_ctx.close()
    (outdir / "export_meta.json").write_text(json.dumps(all_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


def _extract_markup_signature(s: str) -> Tuple[List[str], List[str], int]:
    """Return structural control tags, numbered placeholders and layout-break count.

    {p} is a translator-controlled page/line-flow break in this title, so a changed
    count is useful to review but is not treated as a runtime-structure error.
    Numbered placeholders such as {0} are checked separately.
    """
    tags = TAG_RE.findall(s)
    params = PARAM_RE.findall(s)
    layout_breaks = sum(1 for t in tags if t == "{p}")
    # Color spans may legitimately be re-segmented by a localization (for example
    # when interference/glitch effects split a word differently). Compare only
    # non-color structural tags; color balance is validated independently.
    structural = [t for t in tags if t != "{p}" and not PARAM_RE.fullmatch(t)
                  and not t.startswith("{clr:")]
    return structural, params, layout_breaks


def audit_rows(rows: List[dict], target_col: str = "turkish_final") -> List[dict]:
    report = []
    for r in rows:
        en = r.get("english", "")
        tr = r.get(target_col, "")
        en_tags, en_params, en_breaks = _extract_markup_signature(en)
        tr_tags, tr_params, tr_breaks = _extract_markup_signature(tr)
        issues = []
        if Counter(en_params) != Counter(tr_params):
            issues.append("placeholder_mismatch")
        if Counter(en_tags) != Counter(tr_tags):
            issues.append("control_tag_mismatch")
        tr_all_tags = TAG_RE.findall(tr)
        color_opens = sum(1 for x in tr_all_tags if x.startswith("{clr:") and x != "{clr:pop}")
        color_pops = sum(1 for x in tr_all_tags if x == "{clr:pop}")
        if color_opens != color_pops:
            issues.append("unbalanced_color_tags")
        if en_breaks != tr_breaks:
            issues.append("layout_break_difference")
        if tr == "" and en != "":
            issues.append("empty_translation")
        if tr == en and en.strip() and not re.fullmatch(r"[\d\W_]+", TAG_RE.sub("", en)):
            issues.append("same_as_english")
        if issues:
            report.append({"scope": r.get("scope",""), "id": r.get("id",""),
                           "issues": ";".join(issues), "english": en, target_col: tr})
    return report


def cmd_audit(args) -> int:
    rows = read_csv(Path(args.csv))
    issues = audit_rows(rows, args.column)
    out = Path(args.output)
    fields = ["scope", "id", "issues", "english", args.column]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(issues)
    print(f"Audit: {len(issues)} flagged rows -> {out}")
    return 0


def _zlib_streams(blob: bytes) -> Iterable[Tuple[int, bytes]]:
    seen = set()
    for m in ZLIB_HEADER_RE.finditer(blob):
        off = m.start()
        if off in seen:
            continue
        seen.add(off)
        try:
            dz = zlib.decompressobj()
            dec = dz.decompress(blob[off:]) + dz.flush()
            consumed = len(blob[off:]) - len(dz.unused_data)
            if consumed > 2:
                yield off, dec
        except zlib.error:
            continue


def parse_font_descriptions(bundle: bytes) -> Dict[str, set[int]]:
    fonts: Dict[str, set[int]] = {}
    for _, dec in _zlib_streams(bundle):
        if b"NLG Font Description File" not in dec:
            continue
        txt = dec.decode("latin1", "ignore")
        for part in re.split(r'(?=Font ")', txt):
            fm = re.search(r'Font "([^"]+)"', part)
            if not fm:
                continue
            name = fm.group(1)
            cps: set[int] = set()
            for line in part.splitlines():
                gm = re.match(r"Glyph (.+?) Width\s", line)
                if not gm:
                    continue
                tok = gm.group(1)
                # Literal single-character tokens (including digits) mean that character.
                # Multi-digit numeric tokens are Unicode code points.
                if len(tok) == 1:
                    cps.add(ord(tok))
                elif tok.isdigit():
                    cps.add(int(tok))
            fonts[name] = cps
    return fonts


def visible_text(s: str) -> str:
    return TAG_RE.sub("", s)


def font_issues(game: Source, csv_rows: Sequence[dict], column: str) -> Tuple[List[dict], dict]:
    member = game.find_suffix("fe/febundlefonts_res.data")
    if not member:
        raise ToolError("Could not find fe/febundlefonts_res.data")
    fonts = parse_font_descriptions(game.read(member))
    if not fonts:
        raise ToolError("Could not parse English font descriptions")
    coverage = set().union(*fonts.values())

    occurrences: Dict[int, int] = Counter()
    examples: Dict[int, List[str]] = defaultdict(list)
    row_issues = []
    for r in csv_rows:
        text = visible_text(r.get(column, ""))
        missing = sorted({ord(c) for c in text if ord(c) not in coverage and c not in "\r\n\t"})
        if missing:
            for cp in missing:
                occurrences[cp] += text.count(chr(cp))
                if len(examples[cp]) < 5:
                    examples[cp].append(f"{r.get('scope','')}:{r.get('id','')} {r.get(column,'')[:180]}")
            row_issues.append({
                "scope": r.get("scope", ""), "id": r.get("id", ""),
                "missing": " ".join(f"U+{cp:04X} {chr(cp)}" for cp in missing),
                "text": r.get(column, "")
            })
    summary = {
        "font_bundle_member": member,
        "fonts": {name: len(cps) for name, cps in fonts.items()},
        "missing_characters": [
            {"codepoint": f"U+{cp:04X}", "char": chr(cp), "occurrences": occurrences[cp],
             "examples": examples[cp]}
            for cp in sorted(occurrences)
        ]
    }
    return row_issues, summary


def cmd_font_check(args) -> int:
    rows = read_csv(Path(args.csv))
    if args.font_patch_dir:
        font_path = Path(args.font_patch_dir) / "febundlefonts_res.data"
        if not font_path.exists():
            raise ToolError(f"Patched font not found: {font_path}")
        fonts = parse_font_descriptions(font_path.read_bytes())
        if not fonts:
            raise ToolError("Could not parse patched English font descriptions")
        coverage = set().union(*fonts.values())
        occurrences: Dict[int, int] = Counter()
        examples: Dict[int, List[str]] = defaultdict(list)
        issues = []
        for r in rows:
            text = visible_text(r.get(args.column, ""))
            missing = sorted({ord(c) for c in text if ord(c) not in coverage and c not in "\r\n\t"})
            if missing:
                for cp in missing:
                    occurrences[cp] += text.count(chr(cp))
                    if len(examples[cp]) < 5:
                        examples[cp].append(f"{r.get('scope','')}:{r.get('id','')} {r.get(args.column,'')[:180]}")
                issues.append({
                    "scope": r.get("scope", ""), "id": r.get("id", ""),
                    "missing": " ".join(f"U+{cp:04X} {chr(cp)}" for cp in missing),
                    "text": r.get(args.column, "")
                })
        summary = {
            "font_bundle_member": str(font_path),
            "fonts": {name: len(cps) for name, cps in fonts.items()},
            "missing_characters": [
                {"codepoint": f"U+{cp:04X}", "char": chr(cp), "occurrences": occurrences[cp],
                 "examples": examples[cp]} for cp in sorted(occurrences)
            ]
        }
    else:
        with Source(args.game) as game:
            issues, summary = font_issues(game, rows, args.column)
    out = Path(args.output)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scope", "id", "missing", "text"])
        w.writeheader(); w.writerows(issues)
    j = out.with_suffix(".json")
    j.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Font check: {len(issues)} rows contain unsupported glyphs -> {out}")
    for x in summary["missing_characters"]:
        print(f"  {x['codepoint']} {x['char']!r}: {x['occurrences']} occurrence(s)")
    return 0


def _csv_text_map(csv_path: Path, column: str) -> Dict[int, str]:
    rows = read_csv(csv_path)
    out: Dict[int, str] = {}
    for r in rows:
        try:
            h = int(r["id"], 16)
        except Exception as e:
            raise ToolError(f"Bad ID in {csv_path}: {r.get('id')!r}") from e
        if column not in r:
            raise ToolError(f"Column {column!r} not found in {csv_path}")
        out[h] = r[column]
    return out


def inject_pair(template_data: bytes, template_dict: bytes, texts: Mapping[int, str]) -> Tuple[bytes, bytes]:
    nloc = parse_nloc_data(template_data)
    if set(nloc.rows) - set(texts):
        missing = set(nloc.rows) - set(texts)
        raise ToolError(f"CSV lacks {len(missing)} IDs required by template")
    new_nloc = encode_nloc(nloc, texts)
    new_data = wrap_data(template_data, new_nloc)
    new_dict = update_dict(template_dict, len(new_nloc), len(new_data))
    # Verify immediately by re-parsing.
    check = parse_nloc_data(new_data)
    for h in nloc.rows:
        if check.rows[h] != texts[h]:
            raise ToolError(f"Post-build verification failed at {h:08X}")
    return new_data, new_dict


def _load_existing_patch_files(src: Source) -> Dict[str, bytes]:
    return {name: src.read(name) for name in src.names}


def _patch_prefix_from_base(base: Source) -> str:
    # Find .../romfs/art/fe/english.data and keep prefix through art/.
    m = base.find_suffix("fe/english.data")
    if m and "/fe/english.data" in m:
        return m[: -len("fe/english.data")]
    return "0004000000076500/romfs/art/"


def cmd_build_patch(args) -> int:
    csv_dir = Path(args.csv_dir)
    output = Path(args.output)
    with Source(args.game) as game, Source(args.base_patch) as base:
        files = _load_existing_patch_files(base)
        prefix = _patch_prefix_from_base(base)
        for scope in SCOPES:
            csv_path = csv_dir / f"{scope}_multilang.csv"
            if not csv_path.exists():
                print(f"[skip] no {csv_path.name}")
                continue
            texts = _csv_text_map(csv_path, args.column)
            for target_lang in ("english", "ukenglish"):
                data_name = game.find_suffix(f"{scope}/{target_lang}.data")
                dict_name = game.find_suffix(f"{scope}/{target_lang}.dict")
                if not data_name or not dict_name:
                    raise ToolError(f"Missing original {scope}/{target_lang}.data/.dict")
                new_data, new_dict = inject_pair(game.read(data_name), game.read(dict_name), texts)
                out_data = f"{prefix}{scope}/{target_lang}.data"
                out_dict = f"{prefix}{scope}/{target_lang}.dict"
                files[out_data] = new_data
                files[out_dict] = new_dict
                print(f"Built {out_data} ({len(new_data)} bytes)")

        # Include the Turkish glyph patch when supplied. In this packaged tool,
        # font_patch/ next to the script is auto-detected for convenience.
        font_patch_dir = Path(args.font_patch_dir) if args.font_patch_dir else Path(__file__).resolve().parent / "font_patch"
        if font_patch_dir.exists():
            for fn in ("febundlefonts_res.data", "febundlefonts_res.dict"):
                fp = font_patch_dir / fn
                if not fp.exists():
                    raise ToolError(f"Font patch directory is incomplete: missing {fp}")
                out_name = f"{prefix}fe/{fn}"
                files[out_name] = fp.read_bytes()
                print(f"Included {out_name} ({len(files[out_name])} bytes)")

    output.parent.mkdir(parents=True, exist_ok=True)
    compression = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(output, "w", compression=compression, compresslevel=9) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    print(f"Patch ZIP -> {output}")
    return 0


def cmd_verify(args) -> int:
    with Source(args.patch) as patch:
        results = []
        for scope in SCOPES:
            for lang in ("english", "ukenglish"):
                dn = patch.find_suffix(f"{scope}/{lang}.data")
                qn = patch.find_suffix(f"{scope}/{lang}.dict")
                if not dn or not qn:
                    continue
                data = patch.read(dn); dct = patch.read(qn); n = parse_nloc_data(data)
                payload = struct.unpack_from("<I", data, 4)[0] if data.find(b"NLOC") == 16 else len(data)-data.find(b"NLOC")
                d_payload = struct.unpack_from("<I", dct, 0x68)[0]
                d_size1 = struct.unpack_from("<I", dct, 0x74)[0]
                d_size2 = struct.unpack_from("<I", dct, 0x84)[0]
                ok = payload == d_payload and len(data) == d_size1 == d_size2 and len(n.rows) > 0
                results.append((scope, lang, len(n.rows), payload, len(data), ok))
        for r in results:
            print(f"{r[0]}/{r[1]} rows={r[2]} payload={r[3]} file={r[4]} {'OK' if r[5] else 'FAIL'}")
        if not results or not all(r[5] for r in results):
            return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Luigi's Mansion 2 NLOC multilingual CSV/reinjection tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("export", help="Export all official languages side-by-side to CSV")
    s.add_argument("--game", required=True, help="Original game ZIP or extracted root")
    s.add_argument("--patch", help="Current Turkish patch ZIP/root; English slot is treated as Turkish")
    s.add_argument("--output-dir", required=True)
    s.add_argument("--skip-missing", action="store_true")
    s.set_defaults(func=cmd_export)

    s = sub.add_parser("audit", help="Check placeholders/tags and obvious untranslated rows")
    s.add_argument("--csv", required=True)
    s.add_argument("--column", default="turkish_final")
    s.add_argument("--output", required=True)
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("font-check", help="Check target text against the English LM2 font glyph coverage")
    s.add_argument("--game", required=True)
    s.add_argument("--csv", required=True)
    s.add_argument("--column", default="turkish_final")
    s.add_argument("--output", required=True)
    s.add_argument("--font-patch-dir", help="Directory containing patched febundlefonts_res.data/.dict; use this to verify Turkish glyph coverage")
    s.set_defaults(func=cmd_font_check)

    s = sub.add_parser("build-patch", help="Inject CSV target text and build a LayeredFS patch ZIP")
    s.add_argument("--game", required=True, help="Original game ZIP/root")
    s.add_argument("--base-patch", required=True, help="Existing Turkish patch ZIP/root (credits etc. preserved)")
    s.add_argument("--csv-dir", required=True, help="Directory containing fe_multilang.csv/tweaker_multilang.csv")
    s.add_argument("--column", default="turkish_final")
    s.add_argument("--output", required=True)
    s.add_argument("--font-patch-dir", help="Directory containing patched febundlefonts_res.data/.dict. If omitted, font_patch/ next to this script is auto-detected.")
    s.set_defaults(func=cmd_build_patch)

    s = sub.add_parser("verify", help="Verify NLOC and .dict sizes in a generated patch")
    s.add_argument("--patch", required=True)
    s.set_defaults(func=cmd_verify)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ToolError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
