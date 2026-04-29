#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMes / MSBT safe packager.

Why this exists:
- TXT2 text must be rebuilt from JSON tokenized_text, not from raw_full_hex.
- FMes.bin offsets must be cumulative for every slot, including empty slots.
- MSBT TXT2 entries are delimited by TXT2 offsets, not by the first U+0000 code unit.
  Some menu rows contain an internal U+0000 between options; old scripts truncated them.
- Non-TXT2 MSBT sections (LBL1/ATR1/TSY1/etc.) are preserved byte-for-byte.

Only the Python standard library is required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

CTRL_TAG_RE = re.compile(r"<C:([0-9A-Fa-f]{4}),([0-9A-Fa-f]{4}),([0-9A-Fa-f]*)>")
U_TOKEN_RE = re.compile(r"<U:([0-9A-Fa-f]{4})>")
B_TOKEN_RE = re.compile(r"<B:([0-9A-Fa-f]{2})>")
TOKEN_RE = re.compile(r"(<C:[^>]*>|<U:[0-9A-Fa-f]{4}>|<B:[0-9A-Fa-f]{2}>)")

class FmesError(RuntimeError):
    pass

@dataclass(frozen=True)
class Slot:
    index: int
    offset: int
    size: int

@dataclass
class Section:
    sig: str
    offset: int
    size: int
    header: bytes
    body: bytes
    padding: bytes
    raw_blob: bytes

@dataclass
class Msbt:
    data: bytes
    endian: str
    encoding: int
    version: int
    section_count: int
    file_size: int
    sections: List[Section]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_file_or_zip(path: str) -> bytes:
    # Plain path only. ZIP access is handled by self-test routines.
    return Path(path).read_bytes()

def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def read_index(bin_data: bytes) -> Tuple[bytes, List[Slot]]:
    if len(bin_data) < 16:
        raise FmesError("FMes.bin too small")
    count = struct.unpack_from("<H", bin_data, 2)[0]
    expected = 16 + count * 8
    if len(bin_data) != expected:
        raise FmesError(f"FMes.bin size mismatch: count={count} expected={expected} actual={len(bin_data)}")
    header = bin_data[:16]
    slots: List[Slot] = []
    for i in range(count):
        off, size = struct.unpack_from("<II", bin_data, 16 + i * 8)
        slots.append(Slot(i, off, size))
    return header, slots

def validate_index(bin_data: bytes, dat_data: bytes) -> Dict[str, Any]:
    header, slots = read_index(bin_data)
    cursor = 0
    issues: List[Dict[str, Any]] = []
    prev_off = -1
    for s in slots:
        if s.offset < prev_off:
            issues.append({"type": "offset_decreased", "slot": s.index, "offset": s.offset, "previous": prev_off})
        prev_off = s.offset
        if s.offset != cursor:
            issues.append({"type": "not_cumulative", "slot": s.index, "offset": s.offset, "expected": cursor, "size": s.size})
        if s.size:
            if s.offset + s.size > len(dat_data):
                issues.append({"type": "payload_out_of_range", "slot": s.index, "offset": s.offset, "size": s.size, "dat_len": len(dat_data)})
            cursor += s.size
    if cursor != len(dat_data):
        issues.append({"type": "dat_length_mismatch", "computed_end": cursor, "dat_len": len(dat_data)})
    return {
        "slot_count": len(slots),
        "nonempty_slots": sum(1 for s in slots if s.size),
        "empty_slots": sum(1 for s in slots if not s.size),
        "dat_len": len(dat_data),
        "computed_end": cursor,
        "issues": issues,
    }

def parse_msbt(data: bytes, strict: bool = True) -> Msbt:
    if data[:8] != b"MsgStdBn":
        raise FmesError("Not an MSBT: missing MsgStdBn magic")
    bom = data[8:10]
    if bom == b"\xff\xfe":
        endian = "<"
    elif bom == b"\xfe\xff":
        endian = ">"
    else:
        raise FmesError(f"Unsupported MSBT BOM: {bom.hex()}")
    encoding = data[0x0C]
    version = data[0x0D]
    section_count = struct.unpack_from(endian + "H", data, 0x0E)[0]
    file_size = struct.unpack_from(endian + "I", data, 0x12)[0]
    if strict and file_size != len(data):
        raise FmesError(f"MSBT header file_size={file_size}, actual={len(data)}")
    off = 0x20
    sections: List[Section] = []
    for _ in range(section_count):
        if off + 16 > len(data):
            raise FmesError("MSBT section header out of range")
        sig = data[off:off+4].decode("ascii", errors="replace")
        size = struct.unpack_from(endian + "I", data, off + 4)[0]
        body_start = off + 16
        body_end = body_start + size
        if body_end > len(data):
            raise FmesError(f"MSBT section {sig} body out of range")
        next_off = (body_end + 0xF) & ~0xF
        if next_off > len(data):
            next_off = len(data)
        header = data[off:off+16]
        body = data[body_start:body_end]
        padding = data[body_end:next_off]
        raw_blob = data[off:next_off]
        sections.append(Section(sig, off, size, header, body, padding, raw_blob))
        off = next_off
    if strict and off != len(data):
        # Official files normally end exactly on the final aligned section.
        raise FmesError(f"MSBT trailing bytes not accounted for: parsed_end={off}, len={len(data)}")
    return Msbt(data, endian, encoding, version, section_count, file_size, sections)

def find_section(msbt: Msbt, sig: str) -> Section:
    matches = [s for s in msbt.sections if s.sig == sig]
    if not matches:
        raise FmesError(f"MSBT has no {sig} section")
    if len(matches) > 1:
        raise FmesError(f"MSBT has multiple {sig} sections")
    return matches[0]

def txt2_raw_entries(msbt: Msbt) -> List[bytes]:
    txt = find_section(msbt, "TXT2")
    body = txt.body
    if len(body) < 4:
        raise FmesError("TXT2 too small")
    count = struct.unpack_from(msbt.endian + "I", body, 0)[0]
    table_end = 4 + 4 * count
    if len(body) < table_end:
        raise FmesError("TXT2 offset table out of range")
    offsets = [struct.unpack_from(msbt.endian + "I", body, 4 + i * 4)[0] for i in range(count)]
    prev = table_end
    raws: List[bytes] = []
    for i, start in enumerate(offsets):
        end = offsets[i+1] if i + 1 < count else len(body)
        if start < table_end or start > len(body) or end < start or end > len(body):
            raise FmesError(f"TXT2 bad offset at entry {i}: start={start} end={end} body={len(body)} table_end={table_end}")
        if start < prev:
            raise FmesError(f"TXT2 offsets are not monotonic at entry {i}")
        prev = start
        raws.append(body[start:end])
    return raws

def _codec(endian: str) -> str:
    return "utf-16le" if endian == "<" else "utf-16be"

def _u16(endian: str, value: int) -> bytes:
    return struct.pack(endian + "H", value)

def decode_raw_text(raw: bytes, endian: str, escape_controls: bool = True) -> str:
    """Decode one TXT2 entry raw slice.

    Important: TXT2 offsets, not the first U+0000, delimit entries.
    Therefore only one trailing U+0000 at the very end is stripped as the terminator.
    Internal U+0000 values are preserved as <U:0000>.
    """
    marker = _u16(endian, 0x000E)
    zero = _u16(endian, 0x0000)
    body = raw[:-2] if raw.endswith(zero) else raw
    out: List[str] = []
    i = 0
    codec = _codec(endian)
    while i < len(body):
        if i + 8 <= len(body) and body[i:i+2] == marker:
            group, typ, size = struct.unpack_from(endian + "HHH", body, i + 2)
            params_start = i + 8
            params_end = params_start + size
            if params_end > len(body):
                raise FmesError(f"Control tag overruns TXT2 entry at byte {i}")
            params = body[params_start:params_end]
            out.append(f"<C:{group:04X},{typ:04X},{params.hex().upper()}>")
            i = params_end
            continue
        if i + 2 <= len(body):
            cp = struct.unpack_from(endian + "H", body, i)[0]
            if escape_controls and (cp < 0x20 or cp == 0xFFFD):
                out.append(f"<U:{cp:04X}>")
            else:
                out.append(body[i:i+2].decode(codec, errors="replace"))
            i += 2
        else:
            out.append(f"<B:{body[i]:02X}>")
            i += 1
    return "".join(out)

def encode_tokenized_text(text: str, endian: str) -> bytes:
    codec = _codec(endian)
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            out.extend(text[pos:m.start()].encode(codec))
        tok = m.group(1)
        if tok.startswith("<C:"):
            cm = CTRL_TAG_RE.fullmatch(tok)
            if not cm:
                raise FmesError(f"Invalid control tag: {tok}")
            param_hex = cm.group(3)
            if len(param_hex) % 2:
                raise FmesError(f"Control tag param hex must have even length: {tok}")
            params = bytes.fromhex(param_hex) if param_hex else b""
            out.extend(struct.pack(endian + "HHHH", 0x000E, int(cm.group(1), 16), int(cm.group(2), 16), len(params)))
            out.extend(params)
        elif tok.startswith("<U:"):
            um = U_TOKEN_RE.fullmatch(tok)
            if not um:
                raise FmesError(f"Invalid U token: {tok}")
            out.extend(struct.pack(endian + "H", int(um.group(1), 16)))
        elif tok.startswith("<B:"):
            bm = B_TOKEN_RE.fullmatch(tok)
            if not bm:
                raise FmesError(f"Invalid B token: {tok}")
            out.append(int(bm.group(1), 16))
        pos = m.end()
    if pos < len(text):
        out.extend(text[pos:].encode(codec))
    # Always append exactly one terminating U+0000.
    out.extend(_u16(endian, 0x0000))
    return bytes(out)

def build_txt2_body(raws: List[bytes], endian: str) -> bytes:
    cursor = 4 + 4 * len(raws)
    out = bytearray(struct.pack(endian + "I", len(raws)))
    for raw in raws:
        out.extend(struct.pack(endian + "I", cursor))
        cursor += len(raw)
    for raw in raws:
        out.extend(raw)
    return bytes(out)

def replace_txt2(msbt_data: bytes, raws: List[bytes]) -> bytes:
    msbt = parse_msbt(msbt_data, strict=True)
    old_raws = txt2_raw_entries(msbt)
    if len(raws) != len(old_raws):
        raise FmesError(f"TXT2 entry count mismatch: old={len(old_raws)} new={len(raws)}")
    new_txt_body = build_txt2_body(raws, msbt.endian)
    rebuilt = bytearray(msbt_data[:0x20])
    for sec in msbt.sections:
        if sec.sig == "TXT2":
            hdr = bytearray(sec.header)
            struct.pack_into(msbt.endian + "I", hdr, 4, len(new_txt_body))
            blob = bytes(hdr) + new_txt_body
            blob += b"\x00" * ((-len(blob)) % 0x10)
            rebuilt.extend(blob)
        else:
            rebuilt.extend(sec.raw_blob)
    struct.pack_into(msbt.endian + "I", rebuilt, 0x12, len(rebuilt))
    return bytes(rebuilt)

def extract_json_from_container(bin_data: bytes, dat_data: bytes) -> Dict[str, Dict[str, Dict[str, Any]]]:
    _header, slots = read_index(bin_data)
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for s in slots:
        if not s.size:
            continue
        payload = dat_data[s.offset:s.offset+s.size]
        msbt = parse_msbt(payload, strict=True)
        entries: Dict[str, Dict[str, Any]] = {}
        for idx, raw in enumerate(txt2_raw_entries(msbt)):
            text = decode_raw_text(raw, msbt.endian, escape_controls=True)
            entries[str(idx)] = {
                "text": text,
                "tokenized_text": text,
                "original_text": text,
                "original_tokenized_text": text,
                "raw_full_hex": raw.hex().upper(),
            }
        out[f"{s.index:04d}.msbt"] = entries
    return out

def entry_token(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if not isinstance(obj, dict):
        raise FmesError(f"Unsupported JSON entry type: {type(obj)}")
    return str(obj.get("tokenized_text", obj.get("text", "")))

def rebuild_msbt_from_entries(msbt_payload: bytes, entries: Optional[Dict[str, Any]]) -> Tuple[bytes, Dict[str, Any]]:
    msbt = parse_msbt(msbt_payload, strict=True)
    old_raws = txt2_raw_entries(msbt)
    if entries is None:
        return msbt_payload, {"entry_count": len(old_raws), "changed_entries": 0, "raw_full_hex_ignored": 0}
    if len(entries) != len(old_raws):
        raise FmesError(f"JSON entry count mismatch for MSBT: json={len(entries)} msbt={len(old_raws)}")
    raws: List[bytes] = []
    changed_entries = 0
    raw_full_hex_ignored = 0
    for i, old_raw in enumerate(old_raws):
        key = str(i)
        if key not in entries:
            raise FmesError(f"JSON missing entry {key}")
        obj = entries[key]
        if isinstance(obj, dict) and "raw_full_hex" in obj:
            raw_full_hex_ignored += 1
        raw = encode_tokenized_text(entry_token(obj), msbt.endian)
        if raw != old_raw:
            changed_entries += 1
        raws.append(raw)
    return replace_txt2(msbt_payload, raws), {
        "entry_count": len(old_raws),
        "changed_entries": changed_entries,
        "raw_full_hex_ignored": raw_full_hex_ignored,
    }

def build_container_from_json(
    base_bin: bytes,
    base_dat: bytes,
    all_json: Dict[str, Dict[str, Any]],
) -> Tuple[bytes, bytes, Dict[str, Any]]:
    header, slots = read_index(base_bin)
    validation = validate_index(base_bin, base_dat)
    input_index_issues = validation["issues"]
    new_dat = bytearray()
    records: List[Tuple[int, int]] = []
    msbt_reports: Dict[str, Any] = {}
    for s in slots:
        current_off = len(new_dat)
        if s.size == 0:
            # Critical FMes rule observed in all official EU languages:
            # even empty slots must point at the current cumulative DAT offset.
            records.append((current_off, 0))
            continue
        payload = base_dat[s.offset:s.offset+s.size]
        key = f"{s.index:04d}.msbt"
        rebuilt, rep = rebuild_msbt_from_entries(payload, all_json.get(key))
        records.append((current_off, len(rebuilt)))
        new_dat.extend(rebuilt)
        msbt_reports[key] = rep
    out_bin = bytearray(header)
    for off, size in records:
        out_bin.extend(struct.pack("<II", off, size))
    report = {
        "input_index_issue_count": len(input_index_issues),
        "input_index_issues_first20": input_index_issues[:20],
        "slot_count": len(slots),
        "nonempty_slots": sum(1 for s in slots if s.size),
        "empty_slots": sum(1 for s in slots if not s.size),
        "output_dat_len": len(new_dat),
        "msbt_changed_files": sum(1 for r in msbt_reports.values() if r["changed_entries"]),
        "entry_count": sum(r["entry_count"] for r in msbt_reports.values()),
        "changed_entries": sum(r["changed_entries"] for r in msbt_reports.values()),
        "raw_full_hex_ignored": sum(r["raw_full_hex_ignored"] for r in msbt_reports.values()),
        "per_msbt": msbt_reports,
    }
    return bytes(out_bin), bytes(new_dat), report

def compare_json_to_container(
    base_bin: bytes,
    base_dat: bytes,
    out_bin: bytes,
    out_dat: bytes,
    all_json: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    _h_base, base_slots = read_index(base_bin)
    _h_out, out_slots = read_index(out_bin)
    if len(base_slots) != len(out_slots):
        raise FmesError("Output slot count differs from base")
    mismatches: List[Dict[str, Any]] = []
    non_txt2_diffs: List[Dict[str, Any]] = []
    for bslot, oslot in zip(base_slots, out_slots):
        if bslot.size == 0:
            continue
        key = f"{bslot.index:04d}.msbt"
        if key not in all_json:
            continue
        b_payload = base_dat[bslot.offset:bslot.offset+bslot.size]
        o_payload = out_dat[oslot.offset:oslot.offset+oslot.size]
        b_msbt = parse_msbt(b_payload, strict=True)
        o_msbt = parse_msbt(o_payload, strict=True)
        # Non-TXT2 sections must be byte-for-byte identical.
        b_secs = {s.sig: s.raw_blob for s in b_msbt.sections}
        o_secs = {s.sig: s.raw_blob for s in o_msbt.sections}
        for sig, raw in b_secs.items():
            if sig == "TXT2":
                continue
            if raw != o_secs.get(sig):
                non_txt2_diffs.append({"msbt": key, "section": sig})
        o_raws = txt2_raw_entries(o_msbt)
        for idx, obj in all_json[key].items():
            i = int(idx)
            expected = encode_tokenized_text(entry_token(obj), o_msbt.endian)
            if expected != o_raws[i]:
                mismatches.append({
                    "msbt": key,
                    "entry": i,
                    "expected_sha256": sha256_bytes(expected),
                    "actual_sha256": sha256_bytes(o_raws[i]),
                    "expected_preview": entry_token(obj)[:160],
                    "actual_preview": decode_raw_text(o_raws[i], o_msbt.endian)[:160],
                })
                if len(mismatches) >= 200:
                    break
        if len(mismatches) >= 200:
            break
    idx_report = validate_index(out_bin, out_dat)
    return {
        "json_vs_output_mismatch_count": len(mismatches),
        "json_vs_output_mismatches_first200": mismatches,
        "non_txt2_diff_count": len(non_txt2_diffs),
        "non_txt2_diffs_first200": non_txt2_diffs[:200],
        "output_index": idx_report,
    }

def export_json_cmd(args: argparse.Namespace) -> None:
    bin_data = Path(args.bin).read_bytes()
    dat_data = Path(args.dat).read_bytes()
    obj = extract_json_from_container(bin_data, dat_data)
    out = Path(args.out_json)
    write_json(out, obj)
    if args.per_msbt_dir:
        per = Path(args.per_msbt_dir)
        per.mkdir(parents=True, exist_ok=True)
        for key, entries in obj.items():
            write_json(per / f"{key}.json", {key: entries})

def build_cmd(args: argparse.Namespace) -> None:
    base_bin = Path(args.base_bin).read_bytes()
    base_dat = Path(args.base_dat).read_bytes()
    all_json = json.loads(Path(args.json).read_text(encoding="utf-8"))
    out_bin, out_dat, build_report = build_container_from_json(base_bin, base_dat, all_json)
    verify_report = compare_json_to_container(base_bin, base_dat, out_bin, out_dat, all_json)
    report = {
        "build": build_report,
        "verify": verify_report,
        "output_bin_sha256": sha256_bytes(out_bin),
        "output_dat_sha256": sha256_bytes(out_dat),
    }
    if verify_report["json_vs_output_mismatch_count"] or verify_report["non_txt2_diff_count"] or verify_report["output_index"]["issues"]:
        if not args.allow_failed_verify:
            raise FmesError("Verification failed; output not written. Use --allow-failed-verify only for debugging.")
    Path(args.out_bin).write_bytes(out_bin)
    Path(args.out_dat).write_bytes(out_dat)
    if args.report:
        write_json(Path(args.report), report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

def verify_cmd(args: argparse.Namespace) -> None:
    bin_data = Path(args.bin).read_bytes()
    dat_data = Path(args.dat).read_bytes()
    report: Dict[str, Any] = {
        "index": validate_index(bin_data, dat_data),
        "bin_sha256": sha256_bytes(bin_data),
        "dat_sha256": sha256_bytes(dat_data),
    }
    # Decode/re-encode every TXT2 raw and verify exact raw preservation.
    _h, slots = read_index(bin_data)
    raw_mismatches: List[Dict[str, Any]] = []
    section_errors: List[Dict[str, Any]] = []
    entry_count = 0
    for s in slots:
        if not s.size:
            continue
        payload = dat_data[s.offset:s.offset+s.size]
        try:
            msbt = parse_msbt(payload, strict=True)
            for idx, raw in enumerate(txt2_raw_entries(msbt)):
                entry_count += 1
                recoded = encode_tokenized_text(decode_raw_text(raw, msbt.endian), msbt.endian)
                if raw != recoded:
                    raw_mismatches.append({"msbt": f"{s.index:04d}.msbt", "entry": idx})
        except Exception as e:
            section_errors.append({"msbt": f"{s.index:04d}.msbt", "error": str(e)})
    report["entry_count"] = entry_count
    report["decode_reencode_raw_mismatch_count"] = len(raw_mismatches)
    report["decode_reencode_raw_mismatches_first200"] = raw_mismatches[:200]
    report["msbt_parse_error_count"] = len(section_errors)
    report["msbt_parse_errors_first200"] = section_errors[:200]
    if args.json:
        all_json = json.loads(Path(args.json).read_text(encoding="utf-8"))
        # Compare JSON against itself using this container as both base and output; non-TXT is irrelevant here.
        json_mismatches = []
        _h, slots = read_index(bin_data)
        for s in slots:
            if not s.size:
                continue
            key = f"{s.index:04d}.msbt"
            if key not in all_json:
                continue
            msbt = parse_msbt(dat_data[s.offset:s.offset+s.size], strict=True)
            raws = txt2_raw_entries(msbt)
            for idx, obj in all_json[key].items():
                expected = encode_tokenized_text(entry_token(obj), msbt.endian)
                if expected != raws[int(idx)]:
                    json_mismatches.append({"msbt": key, "entry": int(idx), "preview": entry_token(obj)[:160]})
                    if len(json_mismatches) >= 200:
                        break
            if len(json_mismatches) >= 200:
                break
        report["json_vs_container_mismatch_count"] = len(json_mismatches)
        report["json_vs_container_mismatches_first200"] = json_mismatches
    if args.report:
        write_json(Path(args.report), report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

def _zip_read(z: zipfile.ZipFile, path: str) -> bytes:
    try:
        return z.read(path)
    except KeyError:
        raise FmesError(f"Missing in ZIP: {path}")

def selftest_cmd(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"official_languages": {}, "package_tests": {}, "bugs_caught": {}}
    # Official FMes test set.
    with zipfile.ZipFile(args.message_zip) as z:
        langs = sorted({n.split("/")[1] for n in z.namelist() if n.startswith("Message/EU_") and len(n.split("/")) > 2})
        for lang in langs:
            b = _zip_read(z, f"Message/{lang}/FMes.bin")
            d = _zip_read(z, f"Message/{lang}/FMes.dat")
            idx = validate_index(b, d)
            raw_mismatches = 0
            internal_nul_entries = 0
            msbt_files = 0
            entries = 0
            exact_rebuild_ok = True
            _h, slots = read_index(b)
            for s in slots:
                if not s.size:
                    continue
                payload = d[s.offset:s.offset+s.size]
                msbt_files += 1
                msbt = parse_msbt(payload, strict=True)
                raws_for_rebuild = txt2_raw_entries(msbt)
                # Fast exact no-op: rebuild TXT2 from the exact raw entries and preserve all other sections.
                if replace_txt2(payload, raws_for_rebuild) != payload:
                    exact_rebuild_ok = False
                for raw in raws_for_rebuild:
                    entries += 1
                    text = decode_raw_text(raw, msbt.endian)
                    if "<U:0000>" in text:
                        internal_nul_entries += 1
                    if encode_tokenized_text(text, msbt.endian) != raw:
                        raw_mismatches += 1
            report["official_languages"][lang] = {
                "index_issue_count": len(idx["issues"]),
                "msbt_files": msbt_files,
                "entries": entries,
                "internal_u0000_entries": internal_nul_entries,
                "decode_reencode_raw_mismatch_count": raw_mismatches,
                "exact_extract_json_build_roundtrip": exact_rebuild_ok,
                "bin_sha256": sha256_bytes(b),
                "dat_sha256": sha256_bytes(d),
            }
    # Package under work test.
    if args.package_zip:
        with zipfile.ZipFile(args.package_zip) as z:
            names = set(z.namelist())
            b = z.read("FMes.bin")
            d = z.read("FMes.dat")
            all_json = json.loads(z.read("json/all.json").decode("utf-8"))
        rb, rd, brep = build_container_from_json(b, d, all_json)
        verify = compare_json_to_container(b, d, rb, rd, all_json)
        report["package_tests"]["source_package"] = Path(args.package_zip).name
        report["package_tests"]["source_index_issue_count"] = len(validate_index(b, d)["issues"])
        report["package_tests"]["rebuilt_index_issue_count"] = len(validate_index(rb, rd)["issues"])
        report["package_tests"]["json_vs_rebuilt_mismatch_count"] = verify["json_vs_output_mismatch_count"]
        report["package_tests"]["non_txt2_diff_count"] = verify["non_txt2_diff_count"]
        report["package_tests"]["rebuilt_bin_sha256"] = sha256_bytes(rb)
        report["package_tests"]["rebuilt_dat_sha256"] = sha256_bytes(rd)
        # Bug trap: modify a JSON entry while preserving raw_full_hex/original fields.
        probe = json.loads(json.dumps(all_json, ensure_ascii=False))
        first_msbt = sorted(probe.keys())[0]
        first_entry = sorted(probe[first_msbt].keys(), key=lambda x: int(x))[0]
        old_tok = entry_token(probe[first_msbt][first_entry])
        marker = "<<<SAFE_PACKAGER_PROBE>>>"
        if isinstance(probe[first_msbt][first_entry], dict):
            probe[first_msbt][first_entry]["tokenized_text"] = old_tok + marker
            # Deliberately also make original equal to new text. Old buggy scripts would still use raw_full_hex.
            probe[first_msbt][first_entry]["original_tokenized_text"] = old_tok + marker
            probe[first_msbt][first_entry]["text"] = old_tok + marker
            probe[first_msbt][first_entry]["original_text"] = old_tok + marker
        prb, prd, _ = build_container_from_json(b, d, probe)
        extracted = extract_json_from_container(prb, prd)
        probe_ok = marker in entry_token(extracted[first_msbt][first_entry])
        report["bugs_caught"]["raw_full_hex_is_ignored_when_building"] = probe_ok
        # Old-decoder bug demonstration: first-U+0000 truncation in official menu entries.
        report["bugs_caught"]["internal_u0000_supported"] = any(
            v["internal_u0000_entries"] > 0 and v["decode_reencode_raw_mismatch_count"] == 0
            for v in report["official_languages"].values()
        )
    write_json(out_dir / "selftest_report.json", report)
    # Human summary.
    lines = []
    lines.append("# FMes safe packager test özeti\n")
    lines.append("## Bulunan eski betik hataları\n")
    lines.append("- `raw_full_hex` kullanımı: JSON değişmiş olsa bile eski ham byte geri yazılabiliyordu. Yeni betik build sırasında `raw_full_hex` alanını **daima yok sayıyor**.\n")
    lines.append("- Boş slot offsetleri: eski betik boş slotları `0` yapabiliyordu. Resmi 8 dilde tüm slotlar kümülatif; yeni betik boş slotlara da current DAT cursor yazar.\n")
    lines.append("- İç `U+0000` menü ayırıcıları: eski decoder ilk `00 00` gördüğü yerde metni kesiyordu. Yeni decoder sadece en sondaki terminator’ı keser, içerideki `U+0000` değerlerini `<U:0000>` olarak korur.\n")
    lines.append("- `TXT2` dışı MSBT bölümleri: yeni betik `LBL1/ATR1/TSY1` ve diğer tüm non-`TXT2` section’ları byte-for-byte korur.\n")
    lines.append("\n## Resmi dil testleri\n")
    for lang, r in report["official_languages"].items():
        lines.append(f"- {lang}: index issue={r['index_issue_count']}, entries={r['entries']}, internal `<U:0000>` entries={r['internal_u0000_entries']}, decode/re-encode mismatch={r['decode_reencode_raw_mismatch_count']}, exact rebuild={r['exact_extract_json_build_roundtrip']}\n")
    if "package_tests" in report and report["package_tests"]:
        p = report["package_tests"]
        lines.append("\n## Kaynak paket testi\n")
        lines.append(f"- Paket: `{p['source_package']}`\n")
        lines.append(f"- Rebuilt index issue: {p['rebuilt_index_issue_count']}\n")
        lines.append(f"- JSON ↔ rebuilt FMes mismatch: {p['json_vs_rebuilt_mismatch_count']}\n")
        lines.append(f"- Non-TXT2 section farkı: {p['non_txt2_diff_count']}\n")
    (out_dir / "selftest_summary_TR.md").write_text("".join(lines), encoding="utf-8")

def make_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Safe FMes/MSBT JSON packager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract-json", help="Extract FMes.bin/dat to canonical all.json")
    s.add_argument("--bin", required=True)
    s.add_argument("--dat", required=True)
    s.add_argument("--out-json", required=True)
    s.add_argument("--per-msbt-dir")

    s = sub.add_parser("build", help="Build FMes.bin/dat from JSON tokenized_text")
    s.add_argument("--base-bin", required=True)
    s.add_argument("--base-dat", required=True)
    s.add_argument("--json", required=True)
    s.add_argument("--out-bin", required=True)
    s.add_argument("--out-dat", required=True)
    s.add_argument("--report")
    s.add_argument("--allow-failed-verify", action="store_true")

    s = sub.add_parser("verify", help="Verify FMes.bin/dat structure and optional JSON equivalence")
    s.add_argument("--bin", required=True)
    s.add_argument("--dat", required=True)
    s.add_argument("--json")
    s.add_argument("--report")

    s = sub.add_parser("selftest", help="Run official-language and package regression tests")
    s.add_argument("--message-zip", required=True)
    s.add_argument("--package-zip")
    s.add_argument("--out-dir", required=True)

    return ap

def main(argv: Optional[List[str]] = None) -> int:
    ap = make_argparser()
    args = ap.parse_args(argv)
    try:
        if args.cmd == "extract-json":
            export_json_cmd(args)
        elif args.cmd == "build":
            build_cmd(args)
        elif args.cmd == "verify":
            verify_cmd(args)
        elif args.cmd == "selftest":
            selftest_cmd(args)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
