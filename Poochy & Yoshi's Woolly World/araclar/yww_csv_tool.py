#!/usr/bin/env python3
"""CSV-only Poochy & Yoshi's Woolly World (3DS) Turkish localization tool.

Standard-library only. Supports:
  export  - extract all 11 merino.msbt languages side-by-side to CSV
  qa      - structural checks for Turkish column against source MSBT
  build   - inject Turkish into EU_English merino.msbt and apply prepared
            static_char/font support files
  verify  - reopen output and verify structure/text/support files

This tool intentionally does not include a GUI.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import struct
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

LOCALES = [
    "EU_Dutch", "EU_English", "EU_French", "EU_German", "EU_Italian", "EU_Spanish",
    "JP_Japanese", "KR_Korean", "US_English", "US_French", "US_Spanish",
]
CSV_FIELDS = ["label", *LOCALES, "Turkish", "note", "status"]
TARGET_LOCALE = "EU_English"
TARGET_MSBT = f"message/{TARGET_LOCALE}/merino.msbt"
SUPPORT_ENTRIES = [
    "message/EU_English/static_char.msbt",
    "region_common/frame/font/keito25pt.bffnt",
    "region_common/module/game/font/keito25pt.bffnt",
]
TAG_RE = re.compile(r"⟦TAG:(\d+):(\d+):([0-9A-Fa-f]*)⟧")
END_RE = re.compile(r"⟦END:(\d+):(\d+)⟧")
PLACEHOLDER_RE = re.compile(r"\[\d+\]")
NUMBER_RE = re.compile(r"(?<![\w])\d+(?:[.,]\d+)?(?![\w])")
TURKISH_CORE = set("ÇĞİÖŞÜçğıöşü")

class MSBTError(RuntimeError):
    pass

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: os.PathLike | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _align16(n: int) -> int:
    return (n + 15) & ~15

def _endian(data: bytes) -> str:
    if data[:8] != b"MsgStdBn":
        raise MSBTError("MsgStdBn başlığı yok; MSBT bekleniyordu")
    bom = data[8:10]
    if bom == b"\xff\xfe":
        return "<"
    if bom == b"\xfe\xff":
        return ">"
    raise MSBTError(f"Bilinmeyen BOM: {bom.hex()}")

def _sections(data: bytes) -> List[Tuple[str, int, int, int]]:
    e = _endian(data)
    count = struct.unpack_from(e + "H", data, 14)[0]
    pos = 32
    out = []
    for _ in range(count):
        if pos + 16 > len(data):
            raise MSBTError("Kesilmiş bölüm başlığı")
        magic = data[pos:pos+4].decode("ascii", "replace")
        size = struct.unpack_from(e + "I", data, pos + 4)[0]
        out.append((magic, pos, pos + 16, size))
        pos = _align16(pos + 16 + size)
    return out

def _decode_text(raw: bytes, e: str) -> str:
    p = 0
    chunks: List[str] = []
    normal = bytearray()
    enc = "utf-16le" if e == "<" else "utf-16be"

    def flush() -> None:
        nonlocal normal
        if normal:
            chunks.append(bytes(normal).decode(enc, "surrogatepass"))
            normal = bytearray()

    while p + 2 <= len(raw):
        u = struct.unpack_from(e + "H", raw, p)[0]
        if u == 0:
            flush(); break
        if u == 0x000E:
            flush()
            if p + 8 > len(raw):
                raise MSBTError("Kesilmiş TAG kontrol kodu")
            group, typ, n = struct.unpack_from(e + "HHH", raw, p + 2)
            if p + 8 + n > len(raw):
                raise MSBTError("Kesilmiş TAG payload")
            payload = raw[p + 8:p + 8 + n]
            chunks.append(f"⟦TAG:{group}:{typ}:{payload.hex()}⟧")
            p += 8 + n
            continue
        if u == 0x000F:
            flush()
            if p + 6 > len(raw):
                raise MSBTError("Kesilmiş END kontrol kodu")
            group, typ = struct.unpack_from(e + "HH", raw, p + 2)
            chunks.append(f"⟦END:{group}:{typ}⟧")
            p += 6
            continue
        normal.extend(raw[p:p+2])
        p += 2
    else:
        flush()
    return "".join(chunks)

def _encode_text(text: str, e: str) -> bytes:
    enc = "utf-16le" if e == "<" else "utf-16be"
    out = bytearray()
    p = 0
    while p < len(text):
        mt = TAG_RE.search(text, p)
        me = END_RE.search(text, p)
        candidates = [m for m in (mt, me) if m]
        m = min(candidates, key=lambda x: x.start()) if candidates else None
        if not m:
            out += text[p:].encode(enc, "surrogatepass")
            break
        out += text[p:m.start()].encode(enc, "surrogatepass")
        if m.re is TAG_RE:
            group = int(m.group(1)); typ = int(m.group(2)); payload = bytes.fromhex(m.group(3))
            out += struct.pack(e + "HHHH", 0x000E, group, typ, len(payload)) + payload
        else:
            group = int(m.group(1)); typ = int(m.group(2))
            out += struct.pack(e + "HHH", 0x000F, group, typ)
        p = m.end()
    out += struct.pack(e + "H", 0)
    return bytes(out)

def parse_msbt(data: bytes) -> Tuple[List[str], List[str]]:
    e = _endian(data)
    secs = {m: (off, ds, size) for m, off, ds, size in _sections(data)}
    if "LBL1" not in secs or "TXT2" not in secs:
        raise MSBTError("LBL1/TXT2 bölümü bulunamadı")

    _, lds, lsize = secs["LBL1"]
    groups = struct.unpack_from(e + "I", data, lds)[0]
    labels_by_index: Dict[int, str] = {}
    table = lds + 4
    for gi in range(groups):
        cnt, rel = struct.unpack_from(e + "II", data, table + 8 * gi)
        p = lds + rel
        for _ in range(cnt):
            n = data[p]; p += 1
            label = data[p:p+n].decode("utf-8", "replace"); p += n
            idx = struct.unpack_from(e + "I", data, p)[0]; p += 4
            labels_by_index[idx] = label

    _, tds, tsize = secs["TXT2"]
    count = struct.unpack_from(e + "I", data, tds)[0]
    offsets = list(struct.unpack_from(e + f"{count}I", data, tds + 4))
    texts: List[str] = []
    section_end = tds + tsize
    for i, rel in enumerate(offsets):
        start = tds + rel
        end = tds + offsets[i+1] if i + 1 < count else section_end
        texts.append(_decode_text(data[start:end], e))

    labels = [labels_by_index.get(i, f"__INDEX_{i}") for i in range(count)]
    return labels, texts

def replace_texts(template: bytes, texts: List[str]) -> bytes:
    e = _endian(template)
    secs = _sections(template)
    txt = next((s for s in secs if s[0] == "TXT2"), None)
    if not txt:
        raise MSBTError("TXT2 bulunamadı")
    _, txt_off, tds, old_size = txt
    old_count = struct.unpack_from(e + "I", template, tds)[0]
    if old_count != len(texts):
        raise MSBTError(f"Metin sayısı farklı: kaynak {old_count}, CSV {len(texts)}")

    encoded = [_encode_text(t, e) for t in texts]
    first_off = 4 + 4 * len(encoded)
    offsets = []
    cursor = first_off
    for b in encoded:
        offsets.append(cursor); cursor += len(b)
    body = bytearray(struct.pack(e + "I", len(encoded)))
    body += struct.pack(e + f"{len(offsets)}I", *offsets)
    for b in encoded: body += b

    hdr = bytearray(template[txt_off:txt_off+16])
    struct.pack_into(e + "I", hdr, 4, len(body))
    new = bytearray(template[:txt_off]) + hdr + body
    while len(new) % 16:
        new.append(0xAB)
    if e == "<":
        struct.pack_into("<I", new, 18, len(new))
    else:
        struct.pack_into(">I", new, 18, len(new))
    return bytes(new)

def load_csv(path: os.PathLike | str) -> List[dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def save_csv(path: os.PathLike | str, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)

def export_csv(game_zip: str, out_csv: str) -> dict:
    per: Dict[str, Dict[str, str]] = {}
    order: List[str] = []
    with zipfile.ZipFile(game_zip, "r") as z:
        for loc in LOCALES:
            p = f"message/{loc}/merino.msbt"
            labels, texts = parse_msbt(z.read(p))
            per[loc] = dict(zip(labels, texts))
            if loc == TARGET_LOCALE: order = labels
    rows = []
    for lab in order:
        row = {"label": lab}
        for loc in LOCALES: row[loc] = per[loc].get(lab, "")
        row.update({"Turkish": "", "note": "", "status": ""})
        rows.append(row)
    save_csv(out_csv, rows)
    return {"rows": len(rows), "out": str(out_csv), "locales": LOCALES}

def _tag_signature(s: str):
    return [(m.group(1), m.group(2), m.group(3).lower()) for m in TAG_RE.finditer(s)] + [
        ("END", m.group(1), m.group(2)) for m in END_RE.finditer(s)
    ]

def _ordered_tokens(regex: re.Pattern, s: str):
    return regex.findall(s)

def qa(game_zip: str, csv_path: str) -> dict:
    rows = load_csv(csv_path)
    with zipfile.ZipFile(game_zip, "r") as z:
        src_labels, src_texts = parse_msbt(z.read(TARGET_MSBT))
    src = dict(zip(src_labels, src_texts))
    errors = []
    warnings = []
    seen = set()
    for i, r in enumerate(rows, start=2):
        lab = r.get("label", "")
        tr = r.get("Turkish", "")
        if not lab:
            errors.append({"row": i, "type": "missing_label"}); continue
        if lab in seen: errors.append({"row": i, "label": lab, "type": "duplicate_label"})
        seen.add(lab)
        if lab not in src:
            errors.append({"row": i, "label": lab, "type": "unknown_label"}); continue
        st = src[lab]
        if st.strip() and not tr.strip(): errors.append({"row": i, "label": lab, "type": "missing_turkish"})
        if _tag_signature(st) != _tag_signature(tr): errors.append({"row": i, "label": lab, "type": "control_tag_mismatch"})
        if _ordered_tokens(PLACEHOLDER_RE, st) != _ordered_tokens(PLACEHOLDER_RE, tr): errors.append({"row": i, "label": lab, "type": "placeholder_mismatch"})
        # Numbers can legitimately be localized in prose. Flag as warning, not fatal.
        if _ordered_tokens(NUMBER_RE, st) != _ordered_tokens(NUMBER_RE, tr): warnings.append({"row": i, "label": lab, "type": "number_token_difference"})
    missing_labels = [x for x in src_labels if x not in seen]
    for lab in missing_labels: errors.append({"label": lab, "type": "csv_missing_source_label"})
    return {
        "ok": not errors,
        "source_rows": len(src_labels), "csv_rows": len(rows),
        "translated_nonblank": sum(bool(r.get("Turkish", "").strip()) for r in rows),
        "errors": errors, "warnings": warnings,
    }

def _load_support(support_dir: Path) -> Dict[str, bytes]:
    support = {}
    for entry in SUPPORT_ENTRIES:
        p = support_dir / entry
        if not p.is_file():
            raise FileNotFoundError(f"Destek dosyası eksik: {p}")
        support[entry] = p.read_bytes()
    return support

def build(game_zip: str, csv_path: str, out_zip: str, support_dir: str) -> dict:
    report = qa(game_zip, csv_path)
    if not report["ok"]:
        raise SystemExit("QA başarısız; build durduruldu. Önce 'qa' komutunu çalıştırın.")
    rows = load_csv(csv_path)
    bylab = {r["label"]: r.get("Turkish", "") for r in rows}
    support = _load_support(Path(support_dir))
    with zipfile.ZipFile(game_zip, "r") as zin:
        labels, _ = parse_msbt(zin.read(TARGET_MSBT))
        new_msbt = replace_texts(zin.read(TARGET_MSBT), [bylab[x] for x in labels])
        replacements = {TARGET_MSBT: new_msbt, **support}
        with zipfile.ZipFile(out_zip, "w") as zout:
            for info in zin.infolist():
                data = replacements.get(info.filename, zin.read(info.filename))
                # Copy original ZIP metadata and compression method.
                zout.writestr(info, data)
    return {
        "ok": True, "out": out_zip, "entries_changed": sorted(replacements),
        "sha256": sha256_file(out_zip),
    }

def verify(original_zip: str, built_zip: str, csv_path: str, support_dir: str) -> dict:
    rows = load_csv(csv_path); bylab = {r["label"]: r.get("Turkish", "") for r in rows}
    support = _load_support(Path(support_dir))
    errors = []
    with zipfile.ZipFile(original_zip, "r") as zo, zipfile.ZipFile(built_zip, "r") as zb:
        on = zo.namelist(); bn = zb.namelist()
        if on != bn: errors.append({"type": "zip_structure_or_order_mismatch", "original": len(on), "built": len(bn)})
        labels, texts = parse_msbt(zb.read(TARGET_MSBT))
        for lab, txt in zip(labels, texts):
            if bylab.get(lab) != txt:
                errors.append({"type": "text_roundtrip_mismatch", "label": lab})
                if len(errors) >= 25: break
        for entry, expected in support.items():
            if zb.read(entry) != expected: errors.append({"type": "support_file_mismatch", "entry": entry})
    return {"ok": not errors, "errors": errors, "sha256": sha256_file(built_zip), "entries": len(bn)}

def _default_support() -> str:
    return str(Path(__file__).resolve().parent / "support")

def main() -> None:
    ap = argparse.ArgumentParser(description="YWW 3DS Türkçe CSV-only localization tool")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("export", help="11 dili yan yana CSV'ye çıkar")
    p.add_argument("game_zip"); p.add_argument("out_csv")
    p = sp.add_parser("qa", help="CSV yapısal QA")
    p.add_argument("game_zip"); p.add_argument("csv"); p.add_argument("--out")
    p = sp.add_parser("build", help="Türkçe CSV'yi EU English slotuna enjekte et")
    p.add_argument("game_zip"); p.add_argument("csv"); p.add_argument("out_zip"); p.add_argument("--support-dir", default=_default_support())
    p = sp.add_parser("verify", help="Build çıktısını geri okuyarak doğrula")
    p.add_argument("original_zip"); p.add_argument("built_zip"); p.add_argument("csv"); p.add_argument("--support-dir", default=_default_support()); p.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "export": rep = export_csv(a.game_zip, a.out_csv)
    elif a.cmd == "qa": rep = qa(a.game_zip, a.csv)
    elif a.cmd == "build": rep = build(a.game_zip, a.csv, a.out_zip, a.support_dir)
    else: rep = verify(a.original_zip, a.built_zip, a.csv, a.support_dir)
    text = json.dumps(rep, ensure_ascii=False, indent=2)
    print(text)
    if getattr(a, "out", None): Path(a.out).write_text(text + "\n", encoding="utf-8")
    if not rep.get("ok", True): raise SystemExit(2)

if __name__ == "__main__":
    main()
