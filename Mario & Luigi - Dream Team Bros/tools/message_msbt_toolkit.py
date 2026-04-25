#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, struct, shutil, tempfile, zipfile, hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

CTRL_TAG_RE = re.compile(r"<C:([0-9A-Fa-f]{4}),([0-9A-Fa-f]{4}),([0-9A-Fa-f]*)>")
TOKEN_RE = re.compile(r"(<C:[^>]*>|<U:[0-9A-Fa-f]{4}>|<B:[0-9A-Fa-f]{2}>)")
U_TOKEN_RE = re.compile(r"<U:([0-9A-Fa-f]{4})>")
B_TOKEN_RE = re.compile(r"<B:([0-9A-Fa-f]{2})>")

class ToolkitError(Exception):
    pass

@dataclass
class SlotEntry:
    index: int
    offset: int
    size: int

@dataclass
class Section:
    sig: str
    off: int
    size: int
    raw_blob: bytes
    body: bytes

@dataclass
class MsbtFile:
    data: bytes
    endian: str
    encoding: int
    version: int
    section_count: int
    file_size: int
    sections: List[Section]

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_index(bin_path: Path) -> Tuple[int, List[SlotEntry], bytes]:
    data = bin_path.read_bytes()
    if len(data) < 16:
        raise ToolkitError(f'BIN too small: {bin_path}')
    count = struct.unpack_from('<H', data, 2)[0]
    expected_len = 16 + count * 8
    if len(data) != expected_len:
        raise ToolkitError(f'BIN size mismatch: header expects {expected_len}, got {len(data)}')
    slots: List[SlotEntry] = []
    off = 16
    for i in range(count):
        slot_off, slot_size = struct.unpack_from('<II', data, off)
        slots.append(SlotEntry(i, slot_off, slot_size))
        off += 8
    return count, slots, data[:16]

def parse_msbt(data: bytes, strict_size: bool=False) -> MsbtFile:
    if data[:8] != b'MsgStdBn':
        raise ToolkitError('Not MSBT')
    bom = data[8:10]
    if bom == b'\xff\xfe':
        endian = '<'
    elif bom == b'\xfe\xff':
        endian = '>'
    else:
        raise ToolkitError(f'Unsupported BOM: {bom.hex()}')
    encoding = data[0x0C]
    version = data[0x0D]
    section_count = struct.unpack_from(endian + 'H', data, 0x0E)[0]
    file_size = struct.unpack_from(endian + 'I', data, 0x12)[0]
    if strict_size and file_size != len(data):
        raise ToolkitError(f'Header file size {file_size} != actual {len(data)}')
    headers: List[Tuple[str, int, int]] = []
    off = 0x20
    for _ in range(section_count):
        if off + 16 > len(data):
            raise ToolkitError('Section header out of range')
        sig = data[off:off+4].decode('ascii')
        size = struct.unpack_from(endian + 'I', data, off+4)[0]
        headers.append((sig, off, size))
        off = ((off + 0x10 + size + 0xF) // 0x10) * 0x10
    sections: List[Section] = []
    for i, (sig, off, size) in enumerate(headers):
        next_off = headers[i+1][1] if i + 1 < len(headers) else len(data)
        raw_blob = data[off:next_off]
        body = data[off+0x10:off+0x10+size]
        sections.append(Section(sig, off, size, raw_blob, body))
    return MsbtFile(data, endian, encoding, version, section_count, file_size, sections)

def decode_msbt_text(raw: bytes, endian: str) -> str:
    codec = 'utf-16le' if endian == '<' else 'utf-16be'
    ctrl_marker = struct.pack(endian + 'H', 0x000E)
    out: List[str] = []
    i = 0
    while i < len(raw):
        if i + 1 < len(raw) and raw[i:i+2] == b'\x00\x00':
            break
        if i + 8 <= len(raw) and raw[i:i+2] == ctrl_marker:
            group, typ, size = struct.unpack_from(endian + 'HHH', raw, i+2)
            params = raw[i+8:i+8+size]
            out.append(f"<C:{group:04X},{typ:04X},{params.hex().upper()}>")
            i += 8 + size
            continue
        if i + 1 < len(raw):
            out.append(raw[i:i+2].decode(codec, errors='replace'))
            i += 2
        else:
            out.append(f"<B:{raw[i]:02X}>")
            i += 1
    return ''.join(out)

def encode_tokenized_text(text: str, endian: str) -> bytes:
    codec = 'utf-16le' if endian == '<' else 'utf-16be'
    out = bytearray()
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            out.extend(text[pos:m.start()].encode(codec))
        tok = m.group(1)
        if tok.startswith('<C:'):
            cm = CTRL_TAG_RE.fullmatch(tok)
            if not cm:
                raise ToolkitError(f'Invalid control tag: {tok}')
            group = int(cm.group(1), 16)
            typ = int(cm.group(2), 16)
            param_hex = cm.group(3)
            params = bytes.fromhex(param_hex) if param_hex else b''
            out.extend(struct.pack(endian + 'H', 0x000E))
            out.extend(struct.pack(endian + 'HHH', group, typ, len(params)))
            out.extend(params)
        elif tok.startswith('<U:'):
            um = U_TOKEN_RE.fullmatch(tok)
            if not um:
                raise ToolkitError(f'Invalid U token: {tok}')
            cp = int(um.group(1), 16)
            out.extend(struct.pack(endian + 'H', cp))
        elif tok.startswith('<B:'):
            bm = B_TOKEN_RE.fullmatch(tok)
            if not bm:
                raise ToolkitError(f'Invalid B token: {tok}')
            out.append(int(bm.group(1), 16))
        else:
            raise ToolkitError(f'Unknown token: {tok}')
        pos = m.end()
    if pos < len(text):
        out.extend(text[pos:].encode(codec))
    if not out.endswith(b'\x00\x00'):
        out.extend(b'\x00\x00')
    return bytes(out)

def get_text_entries_with_raw(msbt_bytes: bytes) -> List[Tuple[str, bytes]]:
    msbt = parse_msbt(msbt_bytes, strict_size=False)
    txt = next(s for s in msbt.sections if s.sig == 'TXT2')
    count = struct.unpack_from(msbt.endian + 'I', txt.body, 0)[0]
    offsets = [struct.unpack_from(msbt.endian + 'I', txt.body, 4 + i*4)[0] for i in range(count)]
    entries: List[Tuple[str, bytes]] = []
    for i, start in enumerate(offsets):
        end = offsets[i+1] if i + 1 < count else len(txt.body)
        raw = txt.body[start:end]
        entries.append((decode_msbt_text(raw, msbt.endian), raw))
    return entries

def rebuild_txt2_body_from_raws(raws: List[bytes], endian: str) -> bytes:
    body = bytearray()
    body.extend(struct.pack(endian + 'I', len(raws)))
    cursor = 4 + 4 * len(raws)
    for raw in raws:
        body.extend(struct.pack(endian + 'I', cursor))
        cursor += len(raw)
    for raw in raws:
        body.extend(raw)
    return bytes(body)

def replace_txt_section_with_raws(msbt_bytes: bytes, raws: List[bytes]) -> bytes:
    msbt = parse_msbt(msbt_bytes, strict_size=False)
    original_entries = get_text_entries_with_raw(msbt_bytes)
    if len(raws) != len(original_entries):
        raise ToolkitError(f'TXT entry count mismatch: expected {len(original_entries)}, got {len(raws)}')
    original_raws = [raw for _text, raw in original_entries]
    if all(a == b for a, b in zip(raws, original_raws)):
        return msbt_bytes
    new_txt_body = rebuild_txt2_body_from_raws(raws, msbt.endian)
    rebuilt = bytearray(msbt_bytes[:0x20])
    for sec in msbt.sections:
        if sec.sig == 'TXT2':
            hdr = bytearray(sec.raw_blob[:0x10])
            struct.pack_into(msbt.endian + 'I', hdr, 4, len(new_txt_body))
            blob = bytes(hdr) + new_txt_body
            pad = (-len(blob)) % 0x10
            if pad:
                blob += b'\x00' * pad
            rebuilt.extend(blob)
        else:
            rebuilt.extend(sec.raw_blob)
    struct.pack_into(msbt.endian + 'I', rebuilt, 0x12, len(rebuilt))
    return bytes(rebuilt)

def build_json_entry(decoded_text: str, raw: bytes) -> Dict[str, Any]:
    return {
        "text": decoded_text,
        "tokenized_text": decoded_text,
        "original_text": decoded_text,
        "original_tokenized_text": decoded_text,
        "raw_full_hex": raw.hex().upper(),
    }

def export_msbt_json(msbt_bytes: bytes) -> Dict[str, Dict[str, Any]]:
    entries: Dict[str, Dict[str, Any]] = {}
    for idx, (text, raw) in enumerate(get_text_entries_with_raw(msbt_bytes)):
        entries[str(idx)] = build_json_entry(text, raw)
    return entries

def token_sequence(text: str) -> List[str]:
    """Return all token/control placeholders in order."""
    return [m.group(1) for m in TOKEN_RE.finditer(text or "")]

def strip_tokens(text: str) -> str:
    """Return visible text only, without <C:...>, <U:...> and <B:...> placeholders."""
    return TOKEN_RE.sub("", text or "")

def split_by_tokens(text: str) -> List[str]:
    """Split text while keeping tokens as separate list items."""
    if not text:
        return [""]
    parts: List[str] = []
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            parts.append(text[pos:m.start()])
        parts.append(m.group(1))
        pos = m.end()
    if pos < len(text):
        parts.append(text[pos:])
    if not parts:
        parts.append("")
    return parts

def _nearest_split(text: str, desired: int, lo: int, hi: int) -> int:
    """Find a safe split position near desired, preferably at whitespace."""
    desired = max(lo, min(hi, desired))
    if lo >= hi:
        return lo
    if desired <= lo or desired >= hi:
        return desired
    break_chars = set(" \t\n\r.,;:!?…)]}»›")
    best = desired
    for radius in range(0, max(desired - lo, hi - desired) + 1):
        for cand in (desired - radius, desired + radius):
            if lo <= cand <= hi:
                if cand == 0 or cand == len(text) or text[cand-1:cand] in break_chars or text[cand:cand+1] in break_chars:
                    return cand
    return best

def split_visible_for_skeleton(new_visible: str, original_segments: List[str]) -> List[str]:
    """Split new visible text into the same number of non-token visible slots as the original."""
    slots = [seg for seg in original_segments if seg]
    n = len(slots)
    if n <= 0:
        return []
    if n == 1:
        return [new_visible]
    old_total = sum(len(x) for x in slots)
    if old_total <= 0:
        return [new_visible] + [""] * (n - 1)
    chunks: List[str] = []
    last = 0
    for i, _seg in enumerate(slots[:-1]):
        remaining_slots = n - i - 1
        desired = round(len(new_visible) * (sum(len(x) for x in slots[:i+1]) / old_total))
        hi = max(last, len(new_visible) - remaining_slots)
        split_at = _nearest_split(new_visible, desired, last, hi)
        chunks.append(new_visible[last:split_at])
        last = split_at
    chunks.append(new_visible[last:])
    return chunks

def merge_visible_into_original_control_skeleton(original_tokenized: str, new_visible_text: str) -> str:
    """
    Preserve the original control-token skeleton and replace only visible text.

    This prevents dialogue control codes such as waits, page breaks, face/sound tags,
    and message-end tags from disappearing when a translator edits only `text` and
    accidentally removes <C:...> placeholders.
    """
    parts = split_by_tokens(original_tokenized)
    if not token_sequence(original_tokenized):
        return new_visible_text
    original_visible_parts = [p for p in parts if not TOKEN_RE.fullmatch(p or "")]
    nonempty_visible_count = sum(1 for p in original_visible_parts if p)
    new_visible = strip_tokens(new_visible_text)
    if nonempty_visible_count == 0:
        # Original entry is controls only. Keep it exactly; there is nowhere safe to insert prose.
        return original_tokenized
    replacement_chunks = split_visible_for_skeleton(new_visible, original_visible_parts)
    chunk_iter = iter(replacement_chunks)
    rebuilt: List[str] = []
    for part in parts:
        if TOKEN_RE.fullmatch(part or ""):
            rebuilt.append(part)
        else:
            if part:
                rebuilt.append(next(chunk_iter, ""))
            else:
                rebuilt.append("")
    return "".join(rebuilt)

def prepare_tokenized_for_import(
    candidate: str,
    original_tokenized: str,
    *,
    control_policy: str = "preserve",
    location: str = "",
    report: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Return a tokenized string safe to encode.

    control_policy:
      preserve: default. The original token sequence always wins. If candidate is
                missing or changed control tags, visible prose is merged into the
                original control skeleton.
      strict:   fail when the candidate token sequence differs from the original.
      allow:    old unsafe behavior; encode the candidate exactly as written.
    """
    if control_policy not in {"preserve", "strict", "allow"}:
        raise ToolkitError(f"Unknown control policy: {control_policy}")
    orig_seq = token_sequence(original_tokenized or "")
    cand_seq = token_sequence(candidate or "")
    if control_policy == "allow":
        return candidate
    if cand_seq == orig_seq:
        return candidate
    if control_policy == "strict":
        raise ToolkitError(
            f"Control token sequence changed at {location or '<unknown>'}: "
            f"expected {len(orig_seq)} tokens, got {len(cand_seq)}. "
            "Use --control-policy preserve to auto-restore original control codes, "
            "or edit tokenized_text manually."
        )
    # preserve: restore the exact original sequence and keep the candidate's visible text.
    repaired = merge_visible_into_original_control_skeleton(original_tokenized or "", candidate or "")
    if report is not None:
        report.append({
            "location": location,
            "action": "restored_original_control_sequence",
            "original_token_count": len(orig_seq),
            "candidate_token_count": len(cand_seq),
            "original_tokens": orig_seq,
            "candidate_tokens": cand_seq,
            "candidate_visible": strip_tokens(candidate or ""),
            "repaired_tokenized_text": repaired,
        })
    return repaired

def raw_from_json_entry(
    obj: Any,
    endian: str,
    *,
    fallback_original_text: str = "",
    control_policy: str = "preserve",
    location: str = "",
    report: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    if isinstance(obj, str):
        # String entries have no embedded original_tokenized_text metadata. They are
        # therefore encoded exactly as supplied, matching legacy behavior.
        return encode_tokenized_text(obj, endian)
    if not isinstance(obj, dict):
        raise ToolkitError(f'Unsupported JSON entry type: {type(obj)}')
    text = obj.get("text", "")
    tok = obj.get("tokenized_text", text)
    orig_text = obj.get("original_text", fallback_original_text)
    orig_tok = obj.get("original_tokenized_text", orig_text)
    raw_hex = obj.get("raw_full_hex")
    tok_changed = tok != orig_tok
    text_changed = text != orig_text
    if raw_hex is not None and not tok_changed and not text_changed:
        return bytes.fromhex(raw_hex)
    candidate = tok if tok_changed else text
    safe_tokenized = prepare_tokenized_for_import(
        candidate,
        orig_tok,
        control_policy=control_policy,
        location=location,
        report=report,
    )
    return encode_tokenized_text(safe_tokenized, endian)

def import_msbt_json(
    msbt_bytes: bytes,
    json_entries: Dict[str, Any],
    *,
    control_policy: str = "preserve",
    location_prefix: str = "",
    report: Optional[List[Dict[str, Any]]] = None,
) -> bytes:
    msbt = parse_msbt(msbt_bytes, strict_size=False)
    original = get_text_entries_with_raw(msbt_bytes)
    raws: List[bytes] = []
    for idx, (old_text, old_raw) in enumerate(original):
        key = str(idx)
        obj = json_entries.get(key)
        if obj is None:
            raws.append(old_raw)
        else:
            loc = f"{location_prefix}/{key}" if location_prefix else key
            raws.append(raw_from_json_entry(
                obj,
                msbt.endian,
                fallback_original_text=old_text,
                control_policy=control_policy,
                location=loc,
                report=report,
            ))
    return replace_txt_section_with_raws(msbt_bytes, raws)

def extract_container(bin_path: Path, dat_path: Path, out_dir: Path) -> None:
    count, slots, header = read_index(bin_path)
    dat = dat_path.read_bytes()
    out_dir.mkdir(parents=True, exist_ok=True)
    msbt_dir = out_dir / 'msbt'
    msbt_dir.mkdir(exist_ok=True)
    physical_nonempty_order = [slot.index for slot in sorted((s for s in slots if s.size), key=lambda s: s.offset)]
    manifest = {
        'slot_count': count,
        'bin_header_hex': header.hex().upper(),
        'physical_nonempty_order': physical_nonempty_order,
        'slots': []
    }
    for slot in slots:
        rec = {'index': slot.index, 'offset': slot.offset, 'size': slot.size, 'file': None}
        if slot.size:
            fname = f'{slot.index:04d}.msbt'
            (msbt_dir / fname).write_bytes(dat[slot.offset:slot.offset+slot.size])
            rec['file'] = f'msbt/{fname}'
        manifest['slots'].append(rec)
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

def repack_from_extract(extracted_dir: Path, out_bin: Path, out_dat: Path) -> None:
    manifest = json.loads((extracted_dir / 'manifest.json').read_text(encoding='utf-8'))
    slot_count = int(manifest['slot_count'])
    slots_meta = manifest['slots']
    physical = list(manifest.get('physical_nonempty_order', []))
    if len(slots_meta) != slot_count:
        raise ToolkitError('Manifest slot count mismatch')
    records = [(int(rec.get('offset', 0)), int(rec.get('size', 0))) for rec in slots_meta]
    dat = bytearray()
    for slot_idx in physical:
        rec = slots_meta[slot_idx]
        if not rec.get('file'):
            continue
        payload = (extracted_dir / rec['file']).read_bytes()
        records[slot_idx] = (len(dat), len(payload))
        dat.extend(payload)
    header = bytes.fromhex(manifest['bin_header_hex'])
    bin_out = bytearray(header)
    for off, size in records:
        bin_out.extend(struct.pack('<II', off, size))
    out_bin.write_bytes(bytes(bin_out))
    out_dat.write_bytes(bytes(dat))

def export_container_jsons(bin_path: Path, dat_path: Path, out_dir: Path) -> Dict[str, Any]:
    _, slots, _ = read_index(bin_path)
    dat = dat_path.read_bytes()
    all_entries: Dict[str, Any] = {}
    for slot in slots:
        if slot.size == 0:
            continue
        payload = dat[slot.offset:slot.offset+slot.size]
        all_entries[f'{slot.index:04d}.msbt'] = export_msbt_json(payload)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'all.json').write_text(json.dumps(all_entries, ensure_ascii=False, indent=2), encoding='utf-8')
    per = out_dir / 'per_msbt'
    per.mkdir(exist_ok=True)
    for fname, entries in all_entries.items():
        (per / f'{fname}.json').write_text(json.dumps({fname: entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    return {"msbt_files": len(all_entries)}

def export_standalone_json(msbt_path: Path, out_json: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    obj = {msbt_path.name: export_msbt_json(msbt_path.read_bytes())}
    out_json.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def import_container_from_json(bin_path: Path, dat_path: Path, json_root: Path, out_bin: Path, out_dat: Path, *, control_policy: str = "preserve", control_report: Optional[Path] = None) -> None:
    count, slots, header = read_index(bin_path)
    dat = dat_path.read_bytes()
    json_all_path = json_root / 'all.json'
    all_entries = json.loads(json_all_path.read_text(encoding='utf-8')) if json_all_path.exists() else {}
    records: List[Tuple[int, int]] = [(s.offset, s.size) for s in slots]
    new_dat = bytearray()
    all_report_items: Optional[List[Dict[str, Any]]] = [] if control_report else None
    physical_nonempty_order = [slot.index for slot in sorted((s for s in slots if s.size), key=lambda s: s.offset)]
    slots_by_index = {s.index: s for s in slots}
    for slot_idx in physical_nonempty_order:
        slot = slots_by_index[slot_idx]
        payload = dat[slot.offset:slot.offset+slot.size]
        key = f'{slot.index:04d}.msbt'
        entry_json = all_entries.get(key)
        if entry_json is None:
            per_json = json_root / 'per_msbt' / f'{key}.json'
            if per_json.exists():
                entry_json = json.loads(per_json.read_text(encoding='utf-8')).get(key)
        if entry_json is not None:
            payload = import_msbt_json(payload, entry_json, control_policy=control_policy, location_prefix=key, report=all_report_items)
        off = len(new_dat)
        new_dat.extend(payload)
        records[slot.index] = (off, len(payload))
    bin_out = bytearray(header)
    for off, size in records:
        bin_out.extend(struct.pack('<II', off, size))
    out_bin.write_bytes(bytes(bin_out))
    out_dat.write_bytes(bytes(new_dat))
    if control_report and all_report_items is not None:
        control_report.parent.mkdir(parents=True, exist_ok=True)
        control_report.write_text(json.dumps(all_report_items, ensure_ascii=False, indent=2), encoding="utf-8")


def import_standalone_from_json(msbt_path: Path, json_path: Path, out_msbt: Path, *, control_policy: str = "preserve", control_report: Optional[Path] = None) -> None:
    src = msbt_path.read_bytes()
    obj = json.loads(json_path.read_text(encoding='utf-8'))
    entries = obj.get(msbt_path.name, obj)
    report_items: Optional[List[Dict[str, Any]]] = [] if control_report else None
    rebuilt = import_msbt_json(src, entries, control_policy=control_policy, location_prefix=msbt_path.name, report=report_items)
    out_msbt.write_bytes(rebuilt)
    if control_report and report_items is not None:
        control_report.parent.mkdir(parents=True, exist_ok=True)
        control_report.write_text(json.dumps(report_items, ensure_ascii=False, indent=2), encoding="utf-8")

def verify_container_noop(bin_path: Path, dat_path: Path) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        ext = td / 'ext'
        extract_container(bin_path, dat_path, ext)
        rep_bin = td / 'r.bin'
        rep_dat = td / 'r.dat'
        repack_from_extract(ext, rep_bin, rep_dat)
        extract_ok = (bin_path.read_bytes() == rep_bin.read_bytes()) and (dat_path.read_bytes() == rep_dat.read_bytes())
        jdir = td / 'json'
        export_container_jsons(bin_path, dat_path, jdir)
        jbin = td / 'j.bin'
        jdat = td / 'j.dat'
        import_container_from_json(bin_path, dat_path, jdir, jbin, jdat)
        json_ok = (bin_path.read_bytes() == jbin.read_bytes()) and (dat_path.read_bytes() == jdat.read_bytes())
        count, slots, _ = read_index(bin_path)
        nonempty = sum(1 for s in slots if s.size)
        return {
            "slot_count": count,
            "nonempty_slots": nonempty,
            "extract_repack_exact": extract_ok,
            "json_roundtrip_exact": json_ok,
            "bin_sha256": sha256_bytes(bin_path.read_bytes()),
            "dat_sha256": sha256_bytes(dat_path.read_bytes()),
        }

def verify_standalone_noop(msbt_path: Path) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        jpath = td / 'one.json'
        export_standalone_json(msbt_path, jpath)
        out = td / 'out.msbt'
        import_standalone_from_json(msbt_path, jpath, out)
        src = msbt_path.read_bytes()
        reb = out.read_bytes()
        return {
            "exact": src == reb,
            "sha256": sha256_bytes(src),
            "entries": len(get_text_entries_with_raw(src)),
        }

def build_language_workspace(lang_dir: Path, out_dir: Path) -> Dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    original = out_dir / 'original'
    original.mkdir()
    report: Dict[str, Any] = {"language": lang_dir.name, "containers": {}, "standalone": {}, "all_checks_passed": True}
    for name in ['FMes.bin', 'FMes.dat', 'BMes.bin', 'BMes.dat']:
        src = lang_dir / name
        if src.exists():
            shutil.copy2(src, original / name)
    standalone_dir = original / 'standalone'
    standalone_dir.mkdir()
    for msbt_path in sorted(lang_dir.glob('*.msbt')):
        shutil.copy2(msbt_path, standalone_dir / msbt_path.name)
    raw_root = out_dir / 'raw_extracted'
    for prefix in ['FMes', 'BMes']:
        bin_path = lang_dir / f'{prefix}.bin'
        dat_path = lang_dir / f'{prefix}.dat'
        if not bin_path.exists():
            continue
        cdir = raw_root / prefix
        extract_container(bin_path, dat_path, cdir)
        report["containers"][prefix] = verify_container_noop(bin_path, dat_path)
        if not report["containers"][prefix]["extract_repack_exact"] or not report["containers"][prefix]["json_roundtrip_exact"]:
            report["all_checks_passed"] = False
    raw_std = raw_root / 'Standalone'
    raw_std.mkdir()
    json_std = out_dir / 'json_backups' / 'Standalone'
    json_std.mkdir(parents=True, exist_ok=True)
    all_standalone: Dict[str, Any] = {}
    for msbt_path in sorted(lang_dir.glob('*.msbt')):
        shutil.copy2(msbt_path, raw_std / msbt_path.name)
        export_standalone_json(msbt_path, json_std / f'{msbt_path.name}.json')
        all_standalone[msbt_path.name] = export_msbt_json(msbt_path.read_bytes())
        v = verify_standalone_noop(msbt_path)
        report["standalone"][msbt_path.name] = v
        if not v["exact"]:
            report["all_checks_passed"] = False
    (json_std / 'all.json').write_text(json.dumps(all_standalone, ensure_ascii=False, indent=2), encoding='utf-8')
    json_root = out_dir / 'json_backups'
    for prefix in ['FMes', 'BMes']:
        bin_path = lang_dir / f'{prefix}.bin'
        dat_path = lang_dir / f'{prefix}.dat'
        if bin_path.exists():
            export_container_jsons(bin_path, dat_path, json_root / prefix)
    (out_dir / 'verify_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (out_dir / 'README_TR.txt').write_text(
        "Bu çalışma klasörü üç şeyi birlikte içerir:\n"
        "1) original/: orijinal çalışan dosyalar\n"
        "2) raw_extracted/: ham çıkarılmış .msbt setleri ve manifestler\n"
        "3) json_backups/: her .msbt için ayrı JSON ve toplu all.json\n\n"
        "JSON formatı exact no-op restore içindir. Her girişte raw_full_hex saklanır;\n"
        "text/tokenized_text değiştirilmezse import sırasında ham veri aynen geri kullanılır.\n"
        "Böylece json -> msbt -> bin/dat no-op roundtrip exact doğrulanabilir.\n",
        encoding='utf-8'
    )
    return report

def build_tr_fmes_workspace(package_zip: Path, out_dir: Path) -> Dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    with tempfile.TemporaryDirectory() as td_:
        td = Path(td_)
        with zipfile.ZipFile(package_zip) as zf:
            zf.extractall(td)
        bin_candidates = list(td.glob('*.bin'))
        dat_candidates = list(td.glob('*.dat'))
        if not bin_candidates or not dat_candidates:
            raise ToolkitError('TR package missing bin/dat')
        bin_path = bin_candidates[0]
        dat_path = dat_candidates[0]
        original = out_dir / 'original'
        original.mkdir()
        shutil.copy2(bin_path, original / bin_path.name)
        shutil.copy2(dat_path, original / dat_path.name)
        raw_root = out_dir / 'raw_extracted' / 'FMes'
        extract_container(bin_path, dat_path, raw_root)
        json_root = out_dir / 'json_backups' / 'FMes'
        export_container_jsons(bin_path, dat_path, json_root)
        report = {
            "language": "TR_ManualV66",
            "package": package_zip.name,
            "container": verify_container_noop(bin_path, dat_path),
            "all_checks_passed": True,
        }
        if not report["container"]["extract_repack_exact"] or not report["container"]["json_roundtrip_exact"]:
            report["all_checks_passed"] = False
        (out_dir / 'verify_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        (out_dir / 'README_TR.txt').write_text(
            "Bu çalışma klasörü TR manual V66 FMes paketi içindir.\n"
            "original/: çalışan kaynak .bin/.dat\n"
            "raw_extracted/: ham .msbt seti ve manifest\n"
            "json_backups/: her .msbt için ayrı JSON ve all.json\n",
            encoding='utf-8'
        )
        return report


def scan_container_json_control_safety(bin_path: Path, dat_path: Path, json_root: Path) -> Dict[str, Any]:
    """Scan JSON edits against source files and report control-token mismatches without writing output."""
    _, slots, _ = read_index(bin_path)
    dat = dat_path.read_bytes()
    json_all_path = json_root / 'all.json'
    all_entries = json.loads(json_all_path.read_text(encoding='utf-8')) if json_all_path.exists() else {}
    physical_nonempty_order = [slot.index for slot in sorted((s for s in slots if s.size), key=lambda s: s.offset)]
    slots_by_index = {s.index: s for s in slots}
    issues: List[Dict[str, Any]] = []
    checked = mismatches = 0
    for slot_idx in physical_nonempty_order:
        slot = slots_by_index[slot_idx]
        payload = dat[slot.offset:slot.offset+slot.size]
        key = f'{slot.index:04d}.msbt'
        entry_json = all_entries.get(key)
        if entry_json is None:
            per_json = json_root / 'per_msbt' / f'{key}.json'
            if per_json.exists():
                entry_json = json.loads(per_json.read_text(encoding='utf-8')).get(key)
        if entry_json is None:
            continue
        original = get_text_entries_with_raw(payload)
        for idx, (old_text, _old_raw) in enumerate(original):
            obj = entry_json.get(str(idx)) if isinstance(entry_json, dict) else None
            if obj is None or not isinstance(obj, dict):
                continue
            text = obj.get('text', '')
            tok = obj.get('tokenized_text', text)
            orig_text = obj.get('original_text', old_text)
            orig_tok = obj.get('original_tokenized_text', orig_text)
            tok_changed = tok != orig_tok
            text_changed = text != orig_text
            if not tok_changed and not text_changed:
                continue
            checked += 1
            candidate = tok if tok_changed else text
            orig_seq = token_sequence(orig_tok)
            cand_seq = token_sequence(candidate)
            if orig_seq != cand_seq:
                mismatches += 1
                issues.append({
                    'location': f'{key}/{idx}',
                    'original_token_count': len(orig_seq),
                    'candidate_token_count': len(cand_seq),
                    'original_tokens': orig_seq,
                    'candidate_tokens': cand_seq,
                    'candidate_visible': strip_tokens(candidate),
                    'would_be_repaired_as': merge_visible_into_original_control_skeleton(orig_tok, candidate) if orig_seq else candidate,
                })
    return {
        'checked_changed_entries': checked,
        'control_sequence_mismatches': mismatches,
        'issues': issues,
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('extract-container'); s.add_argument('bin'); s.add_argument('dat'); s.add_argument('out_dir')
    s = sub.add_parser('repack-container'); s.add_argument('extracted_dir'); s.add_argument('out_bin'); s.add_argument('out_dat')
    s = sub.add_parser('export-container-json'); s.add_argument('bin'); s.add_argument('dat'); s.add_argument('out_dir')
    s = sub.add_parser('import-container-json'); s.add_argument('bin'); s.add_argument('dat'); s.add_argument('json_root'); s.add_argument('out_bin'); s.add_argument('out_dat'); s.add_argument('--control-policy', choices=['preserve','strict','allow'], default='preserve'); s.add_argument('--control-report')
    s = sub.add_parser('export-standalone-json'); s.add_argument('msbt'); s.add_argument('out_json')
    s = sub.add_parser('import-standalone-json'); s.add_argument('msbt'); s.add_argument('json_path'); s.add_argument('out_msbt'); s.add_argument('--control-policy', choices=['preserve','strict','allow'], default='preserve'); s.add_argument('--control-report')
    s = sub.add_parser('verify-container-noop'); s.add_argument('bin'); s.add_argument('dat'); s.add_argument('--out-json')
    s = sub.add_parser('validate-container-json'); s.add_argument('bin'); s.add_argument('dat'); s.add_argument('json_root'); s.add_argument('--out-json')
    s = sub.add_parser('verify-standalone-noop'); s.add_argument('msbt'); s.add_argument('--out-json')
    s = sub.add_parser('build-language-workspace'); s.add_argument('lang_dir'); s.add_argument('out_dir')
    s = sub.add_parser('build-tr-workspace'); s.add_argument('package_zip'); s.add_argument('out_dir')
    args = ap.parse_args()
    if args.cmd == 'extract-container':
        extract_container(Path(args.bin), Path(args.dat), Path(args.out_dir))
    elif args.cmd == 'repack-container':
        repack_from_extract(Path(args.extracted_dir), Path(args.out_bin), Path(args.out_dat))
    elif args.cmd == 'export-container-json':
        export_container_jsons(Path(args.bin), Path(args.dat), Path(args.out_dir))
    elif args.cmd == 'import-container-json':
        import_container_from_json(Path(args.bin), Path(args.dat), Path(args.json_root), Path(args.out_bin), Path(args.out_dat), control_policy=args.control_policy, control_report=Path(args.control_report) if args.control_report else None)
    elif args.cmd == 'export-standalone-json':
        export_standalone_json(Path(args.msbt), Path(args.out_json))
    elif args.cmd == 'import-standalone-json':
        import_standalone_from_json(Path(args.msbt), Path(args.json_path), Path(args.out_msbt), control_policy=args.control_policy, control_report=Path(args.control_report) if args.control_report else None)
    elif args.cmd == 'verify-container-noop':
        result = verify_container_noop(Path(args.bin), Path(args.dat))
        txt = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out_json: Path(args.out_json).write_text(txt, encoding='utf-8')
        else: print(txt)
    elif args.cmd == 'validate-container-json':
        result = scan_container_json_control_safety(Path(args.bin), Path(args.dat), Path(args.json_root))
        txt = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out_json: Path(args.out_json).write_text(txt, encoding='utf-8')
        else: print(txt)
    elif args.cmd == 'verify-standalone-noop':
        result = verify_standalone_noop(Path(args.msbt))
        txt = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out_json: Path(args.out_json).write_text(txt, encoding='utf-8')
        else: print(txt)
    elif args.cmd == 'build-language-workspace':
        print(json.dumps(build_language_workspace(Path(args.lang_dir), Path(args.out_dir)), ensure_ascii=False, indent=2))
    elif args.cmd == 'build-tr-workspace':
        print(json.dumps(build_tr_fmes_workspace(Path(args.package_zip), Path(args.out_dir)), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
