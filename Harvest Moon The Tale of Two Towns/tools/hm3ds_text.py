#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harvest Moon 3DS Turkish Translation Helper
Target observed: CTR-P-AT2P / Title ID 000400000007A300

Safe design goal:
- Do not rebuild the game's proprietary container structure.
- Patch each message in place and keep the exact original byte allocation.
- Preserve non-text control words and offsets.

The game uses 16-bit little-endian glyph/control words.
Printable ASCII is encoded as 0x0800 + (ASCII - 0x20).
Message delimiter observed in mes_data.bin/event_mes_data.bin: 0x270E.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import zipfile
import zlib
from collections import Counter

TITLE_ID = "000400000007A300"
DELIM = 0x270E
BR = 0x2328
DEFAULT_MIN_GLYPHS = 4
DEFAULT_MIN_RATIO = 0.30

# Confirmed from the European localized message files by context.
# One slot may serve both cases visually in the original font.
KNOWN_EXTENDED = {
    0x0865: "ü",  # German für / über
    0x0868: "ä",  # German älter / gefährlich
    0x0878: "ö",  # German schön / können
    0x088E: "ß",  # German draußen / weiß
    0x086B: "ç",  # French garçon / façon
    0x0866: "é",  # French génial / dirigé
    0x086E: "è",  # French mère / inquiète
    0x0869: "à",  # French à
    0x089C: "œ",  # French cœur
}

SAFE_TURKISH = {
    # Existing European glyphs in the original font.
    "ç": 0x086B,
    "Ç": 0x0864,
    "ö": 0x0878,
    "Ö": 0x087D,
    "ü": 0x0865,
    "Ü": 0x087E,
}

# Full Turkish mapping for the included patched font_data.bin.
FONT_SLOT_TURKISH = {
    **SAFE_TURKISH,
    "ğ": 0x0868,  # patched: was ä
    "Ğ": 0x0872,  # patched: was Ä
    "ş": 0x088E,  # patched: was ß
    "Ş": 0x086C,  # patched: was ê
    "ı": 0x086E,  # patched: was è
    "İ": 0x0866,  # patched: was é
}

SAFE_FALLBACK = {
    "ğ": "g", "Ğ": "G",
    "ş": "s", "Ş": "S",
    "ı": "i", "İ": "I",
}

TOKEN_RE = re.compile(r"\{BR\}|\{#[0-9A-Fa-f]{4}\}")


def u16(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8)


def p16(v: int) -> bytes:
    return struct.pack("<H", v & 0xFFFF)


def is_ascii_glyph(w: int) -> bool:
    # Printable ASCII 0x20..0x7E maps to 0x0800..0x085E.
    return 0x0800 <= w <= 0x085E


def is_text_glyph(w: int) -> bool:
    return is_ascii_glyph(w) or w in KNOWN_EXTENDED


def decode_word(w: int) -> str:
    if is_ascii_glyph(w):
        return chr(0x20 + (w - 0x0800))
    if w in KNOWN_EXTENDED:
        return KNOWN_EXTENDED[w]
    if w == BR:
        return "{BR}"
    return f"{{#{w:04X}}}"


def decode_words(words: list[int]) -> str:
    return "".join(decode_word(w) for w in words)


def protected_controls(text: str) -> list[str]:
    # Layout controls may be moved/added/removed by the QA reflow tool.
    # Other raw controls (colors, prompts, variables, etc.) stay in exact order.
    layout = {"{BR}", "{#232B}"}
    return [m.group(0).upper() for m in TOKEN_RE.finditer(text) if m.group(0).upper() not in layout]


def normalize_punctuation(s: str) -> str:
    return (s.replace("’", "'").replace("‘", "'")
             .replace("“", '"').replace("”", '"')
             .replace("–", "-").replace("—", "-")
             .replace("…", "..."))


def load_custom_charmap(path: str | None) -> dict[str, int]:
    if not path:
        return {}
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for ch, val in obj.items():
        if isinstance(ch, str) and ch.startswith("_"):
            continue
        if not isinstance(ch, str) or len(ch) != 1:
            raise ValueError(f"Charmap key tek karakter olmalı: {ch!r}")
        if isinstance(val, int):
            code = val
        elif isinstance(val, str):
            val = val.strip().lower().replace("0x", "")
            code = int(val, 16)
        else:
            raise ValueError(f"Geçersiz charmap değeri: {ch!r}: {val!r}")
        if not 0 <= code <= 0xFFFF:
            raise ValueError(f"Charmap kodu 16-bit olmalı: {ch!r}: {code}")
        out[ch] = code
    return out


def encode_char(ch: str, mode: str, custom: dict[str, int]) -> int:
    if ch in custom:
        return custom[ch]
    o = ord(ch)
    if 0x20 <= o <= 0x7E:
        return 0x0800 + (o - 0x20)
    if mode == "safe":
        if ch in SAFE_TURKISH:
            return SAFE_TURKISH[ch]
        if ch in SAFE_FALLBACK:
            repl = SAFE_FALLBACK[ch]
            return 0x0800 + (ord(repl) - 0x20)
    elif mode == "slots":
        if ch in FONT_SLOT_TURKISH:
            return FONT_SLOT_TURKISH[ch]
    raise ValueError(f"Desteklenmeyen karakter: {ch!r} (U+{ord(ch):04X})")


def encode_text(text: str, mode: str, custom: dict[str, int]) -> list[int]:
    text = normalize_punctuation(text)
    words: list[int] = []
    pos = 0
    for m in TOKEN_RE.finditer(text):
        plain = text[pos:m.start()]
        for ch in plain:
            if ch in "\r\n":
                # Newline is treated as a line-break token.
                if ch == "\n":
                    words.append(BR)
            else:
                words.append(encode_char(ch, mode, custom))
        tok = m.group(0).upper()
        if tok == "{BR}":
            words.append(BR)
        else:
            words.append(int(tok[2:6], 16))
        pos = m.end()
    for ch in text[pos:]:
        if ch in "\r\n":
            if ch == "\n":
                words.append(BR)
        else:
            words.append(encode_char(ch, mode, custom))
    return words


def message_chunks(data: bytes):
    """Yield (body_start, body_end_exclusive) for even-aligned DELIM-separated chunks."""
    last = 0
    for i in range(0, len(data) - 1, 2):
        if u16(data, i) == DELIM:
            yield last, i
            last = i + 2


def chunk_stats(data: bytes, start: int, end: int):
    words = [u16(data, i) for i in range(start, end, 2)]
    glyphs = sum(is_text_glyph(w) for w in words)
    ratio = glyphs / len(words) if words else 0.0
    return words, glyphs, ratio


def find_editable_start(words: list[int]) -> int | None:
    for i, w in enumerate(words):
        if is_text_glyph(w):
            return i
    return None


def export_bin(input_path: Path, output_csv: Path, min_glyphs=DEFAULT_MIN_GLYPHS, min_ratio=DEFAULT_MIN_RATIO):
    data = input_path.read_bytes()
    rows = []
    idx = 0
    for start, end in message_chunks(data):
        if end <= start or (end - start) % 2:
            continue
        words, glyphs, ratio = chunk_stats(data, start, end)
        if glyphs < min_glyphs or ratio < min_ratio:
            continue
        edit_at = find_editable_start(words)
        if edit_at is None:
            continue
        prefix = words[:edit_at]
        editable = words[edit_at:]
        source = decode_words(editable)
        # Avoid rows that are almost entirely raw controls despite passing ratio.
        visible_chars = sum(1 for w in editable if is_text_glyph(w))
        if visible_chars < min_glyphs:
            continue
        body = data[start:end]
        rows.append({
            "id": idx,
            "offset_hex": f"0x{start:X}",
            "body_words": len(words),
            "prefix_words": len(prefix),
            "editable_words": len(editable),
            "text_ratio": f"{ratio:.3f}",
            "crc32": f"{zlib.crc32(body) & 0xFFFFFFFF:08X}",
            "source": source,
            "translation": "",
            "notes": "",
        })
        idx += 1

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["id", "offset_hex", "body_words", "prefix_words", "editable_words", "text_ratio", "crc32", "source", "translation", "notes"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def import_bin(input_path: Path, csv_path: Path, output_path: Path, mode: str, custom_charmap: dict[str, int], strict_controls=True):
    original = input_path.read_bytes()
    out = bytearray(original)
    patched = skipped = too_long = errors = 0
    issues = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            tr = (row.get("translation") or "")
            if tr == "":
                skipped += 1
                continue
            try:
                start = int(row["offset_hex"], 16)
                body_words = int(row["body_words"])
                prefix_words = int(row["prefix_words"])
                end = start + body_words * 2
                if start < 0 or end > len(original):
                    raise ValueError("Offset dosya dışında")
                body = original[start:end]
                crc = f"{zlib.crc32(body) & 0xFFFFFFFF:08X}"
                if crc.upper() != row["crc32"].strip().upper():
                    raise ValueError(f"CRC uyuşmuyor (CSV {row['crc32']}, dosya {crc})")

                source = row.get("source") or ""
                if strict_controls:
                    a = protected_controls(source)
                    b = protected_controls(tr)
                    if a != b:
                        raise ValueError("Korunan kontrol kodlarının sırası/değeri değişmiş. {#XXXX} tokenlarını aynen koruyun.")

                encoded = encode_text(tr, mode, custom_charmap)
                capacity = body_words - prefix_words
                if len(encoded) > capacity:
                    too_long += 1
                    issues.append(f"ID {row.get('id')}: {len(encoded)} word > {capacity} word (fazla: {len(encoded)-capacity})")
                    continue

                prefix_bytes = body[:prefix_words * 2]
                payload = b"".join(p16(w) for w in encoded)
                # Fill unused allocation with spaces, keeping chunk size unchanged.
                payload += p16(0x0800) * (capacity - len(encoded))
                replacement = prefix_bytes + payload
                if len(replacement) != len(body):
                    raise AssertionError("Internal size mismatch")
                out[start:end] = replacement
                patched += 1
            except Exception as e:
                errors += 1
                issues.append(f"ID {row.get('id','?')}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out)
    return patched, skipped, too_long, errors, issues


def candidate_score(data: bytes):
    total = runs = best = 0
    for align in (0, 1):
        cur = 0
        for i in range(align, len(data) - 1, 2):
            w = u16(data, i)
            good = is_text_glyph(w)
            if good:
                cur += 1
            else:
                if cur >= 8:
                    total += cur; runs += 1; best = max(best, cur)
                cur = 0
        if cur >= 8:
            total += cur; runs += 1; best = max(best, cur)
    return total, runs, best


def scan_zip(zip_path: Path):
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        for inf in z.infolist():
            if inf.is_dir() or inf.file_size > 5_000_000:
                continue
            if not inf.filename.lower().endswith((".bin", ".all", ".dat")):
                continue
            data = z.read(inf)
            total, runs, best = candidate_score(data)
            if total >= 40:
                rows.append((total, runs, best, inf.file_size, inf.filename))
    rows.sort(reverse=True)
    return rows


def prepare_zip(zip_path: Path, workdir: Path):
    wanted = [
        "romfs/mes_data.bin",
        "romfs/mes_data_fr_b.bin",
        "romfs/mes_data_fr_g.bin",
        "romfs/mes_data_ge.bin",
        "romfs/event_mes_data.bin",
        "romfs/event_mes_data_fr_b.bin",
        "romfs/event_mes_data_fr_g.bin",
        "romfs/event_mes_data_ge.bin",
        "romfs/font_data.bin",
        "romfs/demo_font.bcfnt",
    ]
    original_dir = workdir / "original"
    original_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        for n in wanted:
            if n in names:
                dest = original_dir / Path(n).name
                dest.write_bytes(z.read(n))
                extracted.append(dest)
    return extracted


def export_all_from_zip(zip_path: Path, workdir: Path):
    extracted = prepare_zip(zip_path, workdir)
    orig = workdir / "original"
    trans = workdir / "translations"
    trans.mkdir(parents=True, exist_ok=True)
    counts = {}
    for fn in ("mes_data.bin", "event_mes_data.bin"):
        src = orig / fn
        if src.exists():
            dst = trans / (fn.replace(".bin", ".csv"))
            counts[fn] = export_bin(src, dst)
    return extracted, counts


def make_layeredfs(mes: Path | None, event: Path | None, font: Path | None, outdir: Path):
    root = outdir / "luma" / "titles" / TITLE_ID / "romfs"
    root.mkdir(parents=True, exist_ok=True)
    copied = []
    for src, name in [(mes, "mes_data.bin"), (event, "event_mes_data.bin"), (font, "font_data.bin")]:
        if src:
            shutil.copy2(src, root / name)
            copied.append(root / name)
    return root, copied


def write_builtin_charmaps(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    safe = {
        "_comment": "Ç/Ö/Ü use confirmed European glyphs. ğ/ş/ı/İ are transliterated automatically in --mode safe and therefore are not listed here.",
        "ç": "086B", "Ç": "0864",
        "ö": "0878", "Ö": "087D",
        "ü": "0865", "Ü": "087E",
    }
    slots = {
        "_comment": "FULL TURKISH SLOT RESERVATION. These codes need font glyphs redrawn first; otherwise they display the original European accented glyphs.",
        "ç": "086B", "Ç": "0864",
        "ö": "0878", "Ö": "087D",
        "ü": "0865", "Ü": "087E",
        "ğ": "0868", "Ğ": "0872",
        "ş": "088E", "Ş": "086C",
        "ı": "086E", "İ": "0866",
    }
    (outdir / "charmap_safe.json").write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "charmap_fontslots.json").write_text(json.dumps(slots, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_scan(args):
    rows = scan_zip(Path(args.zip))
    print("score\truns\tbest\tsize\tfile")
    for r in rows:
        print("\t".join(map(str, r)))


def cmd_prepare(args):
    extracted, counts = export_all_from_zip(Path(args.zip), Path(args.workdir))
    write_builtin_charmaps(Path(args.workdir))
    print("Çıkarılan dosyalar:")
    for p in extracted:
        print("  ", p)
    print("\nCSV:")
    for fn, n in counts.items():
        print(f"  {fn}: {n} mesaj -> {Path(args.workdir)/'translations'/(fn.replace('.bin','.csv'))}")


def cmd_export(args):
    n = export_bin(Path(args.input), Path(args.output), args.min_glyphs, args.min_ratio)
    print(f"{n} mesaj dışa aktarıldı: {args.output}")


def cmd_import(args):
    custom = load_custom_charmap(args.charmap)
    patched, skipped, too_long, errors, issues = import_bin(
        Path(args.input), Path(args.csv), Path(args.output), args.mode, custom, not args.allow_control_changes
    )
    print(f"Yamalanan: {patched}")
    print(f"Boş bırakılan: {skipped}")
    print(f"Fazla uzun: {too_long}")
    print(f"Hata: {errors}")
    if issues:
        report = Path(str(args.output) + ".issues.txt")
        report.write_text("\n".join(issues), encoding="utf-8")
        print(f"Sorun raporu: {report}")
    if too_long or errors:
        print("UYARI: Sorunlu satırlar uygulanmadı; diğer geçerli satırlar çıktı dosyasına yazıldı.")


def cmd_layeredfs(args):
    root, copied = make_layeredfs(
        Path(args.mes) if args.mes else None,
        Path(args.event) if args.event else None,
        Path(args.font) if args.font else None,
        Path(args.outdir),
    )
    print("LayeredFS kökü:", root)
    for p in copied:
        print("  ", p)


def cmd_glyph_audit(args):
    for fn in args.files:
        p = Path(fn)
        b = p.read_bytes()
        c = Counter()
        for i in range(0, len(b)-1, 2):
            w = u16(b, i)
            if 0x085F <= w <= 0x08FF:
                c[w] += 1
        print(f"\n{p.name}")
        for code, n in c.most_common(args.top):
            label = KNOWN_EXTENDED.get(code, "?")
            print(f"  {code:04X}  {n:7d}  {label}")


def build_parser():
    ap = argparse.ArgumentParser(description="Harvest Moon 3DS Türkçe çeviri yardımcısı")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="ZIP içindeki metin adaylarını tara")
    p.add_argument("zip")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("prepare", help="Ana metin/font dosyalarını çıkar ve CSV üret")
    p.add_argument("zip")
    p.add_argument("workdir")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("export", help="Tek bir mes_data/event_mes_data BIN dosyasını CSV'ye çıkar")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--min-glyphs", type=int, default=DEFAULT_MIN_GLYPHS)
    p.add_argument("--min-ratio", type=float, default=DEFAULT_MIN_RATIO)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("import", help="CSV çevirilerini BIN dosyasına güvenli in-place yama")
    p.add_argument("input")
    p.add_argument("csv")
    p.add_argument("output")
    p.add_argument("--mode", choices=["safe", "slots"], default="safe")
    p.add_argument("--charmap", help="Ek/özel JSON karakter eşleme dosyası")
    p.add_argument("--allow-control-changes", action="store_true", help="{#XXXX} kontrol token değişikliklerine izin ver (riskli)")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("layeredfs", help="Luma3DS LayeredFS klasör yapısını oluştur")
    p.add_argument("--mes", help="Yamalanmış mes_data.bin")
    p.add_argument("--event", help="Yamalanmış event_mes_data.bin")
    p.add_argument("--font", help="Yamalanmış font_data.bin (opsiyonel)")
    p.add_argument("--outdir", default="build")
    p.set_defaults(func=cmd_layeredfs)

    p = sub.add_parser("glyph-audit", help="Avrupa dil dosyalarındaki özel glif kodlarını say")
    p.add_argument("files", nargs="+")
    p.add_argument("--top", type=int, default=30)
    p.set_defaults(func=cmd_glyph_audit)
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print("HATA:", e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
