#!/usr/bin/env python3
"""Gravity Falls / UbiArt LOC8 extractor and injector.

This parser targets the LOC8 layout used by Gravity Falls: Legend of the Gnome
Gemulets (3DS): a game-specific prefix, then N language blocks. Each language
contains a main string table and a second string table whose entries have 16
bytes of per-string metadata. Prefix, language IDs, metadata and tail are
preserved exactly.
"""
from __future__ import annotations
import argparse, csv, struct
from dataclasses import dataclass
from pathlib import Path

BE = ">"

LANG_NAMES = {0: "English", 1: "French", 2: "Japanese", 3: "German", 4: "Spanish", 5: "Italian"}

@dataclass
class Entry:
    id: int
    text: str
    meta: bytes = b""

@dataclass
class Language:
    id: int
    main: list[Entry]
    dialogue: list[Entry]

@dataclass
class Loc8:
    prefix: bytes
    languages: list[Language]
    tail: bytes
    start: int


def u32(data: bytes, pos: int) -> tuple[int, int]:
    if pos + 4 > len(data):
        raise ValueError("Unexpected EOF")
    return struct.unpack_from(">I", data, pos)[0], pos + 4


def read_text_entry(data: bytes, pos: int, with_meta: bool) -> tuple[Entry, int]:
    sid, pos = u32(data, pos)
    n, pos = u32(data, pos)
    if n > len(data) - pos:
        raise ValueError("Invalid string length")
    raw = data[pos:pos+n]
    pos += n
    text = raw.decode("utf-8")
    meta = b""
    if with_meta:
        if pos + 16 > len(data):
            raise ValueError("Missing secondary-entry metadata")
        meta = data[pos:pos+16]
        pos += 16
    return Entry(sid, text, meta), pos


def try_parse_at(data: bytes, start: int) -> Loc8 | None:
    try:
        lang_count, pos = u32(data, start)
        if not (1 <= lang_count <= 32):
            return None
        langs: list[Language] = []
        seen_ids: set[int] = set()
        for _ in range(lang_count):
            lid, pos = u32(data, pos)
            if lid > 1000 or lid in seen_ids:
                return None
            seen_ids.add(lid)
            main_count, pos = u32(data, pos)
            if not (1 <= main_count <= 100000):
                return None
            main = []
            for _ in range(main_count):
                e, pos = read_text_entry(data, pos, False)
                main.append(e)
            secondary_count, pos = u32(data, pos)
            if not (1 <= secondary_count <= 100000):
                return None
            dialogue = []
            for _ in range(secondary_count):
                e, pos = read_text_entry(data, pos, True)
                dialogue.append(e)
            langs.append(Language(lid, main, dialogue))
        # Gravity Falls has substantial text in both tables; this rejects random matches.
        if sum(len(x.main) + len(x.dialogue) for x in langs) < 100:
            return None
        return Loc8(data[:start], langs, data[pos:], start)
    except (ValueError, UnicodeDecodeError, struct.error):
        return None


def parse_loc8(path: Path) -> Loc8:
    data = path.read_bytes()
    # The real table is 4-byte aligned in this game. Scan aligned positions first.
    for start in range(0, len(data) - 12, 4):
        obj = try_parse_at(data, start)
        if obj is not None:
            return obj
    # Fallback for variants with an unaligned prefix.
    for start in range(0, len(data) - 12):
        obj = try_parse_at(data, start)
        if obj is not None:
            return obj
    raise ValueError("LOC8 language table could not be found")


def serialize(obj: Loc8) -> bytes:
    out = bytearray(obj.prefix)
    out += struct.pack(">I", len(obj.languages))
    for lang in obj.languages:
        out += struct.pack(">II", lang.id, len(lang.main))
        for e in lang.main:
            raw = e.text.encode("utf-8")
            out += struct.pack(">II", e.id, len(raw)) + raw
        out += struct.pack(">I", len(lang.dialogue))
        for e in lang.dialogue:
            raw = e.text.encode("utf-8")
            if len(e.meta) != 16:
                raise ValueError("Secondary entry metadata must be exactly 16 bytes")
            out += struct.pack(">II", e.id, len(raw)) + raw + e.meta
    out += obj.tail
    return bytes(out)


def get_lang(obj: Loc8, lang_id: int) -> Language:
    for lang in obj.languages:
        if lang.id == lang_id:
            return lang
    raise KeyError(f"Language id {lang_id} not found; available: {[x.id for x in obj.languages]}")


def cmd_info(args):
    obj = parse_loc8(Path(args.input))
    print(f"table_offset=0x{obj.start:X}")
    print(f"prefix={len(obj.prefix)} bytes, tail={len(obj.tail)} bytes")
    print(f"languages={len(obj.languages)}")
    for l in obj.languages:
        print(f"  id={l.id}: main={len(l.main)} dialogue={len(l.dialogue)} total={len(l.main)+len(l.dialogue)}")


def _write_multilang_group_csv(obj: Loc8, group: str, out: Path) -> int:
    langs = {l.id: l for l in obj.languages}
    if 0 not in langs:
        raise ValueError("English language slot (id 0) not found")
    base = getattr(langs[0], group)
    available = [(lid, LANG_NAMES.get(lid, f"Language_{lid}")) for lid in sorted(langs)]
    fields = ["index", "id"] + [name for _, name in available] + ["Turkish"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, e in enumerate(base):
            row = {"index": i, "id": e.id, "Turkish": ""}
            for lid, name in available:
                arr = getattr(langs[lid], group)
                if len(arr) != len(base) or arr[i].id != e.id:
                    raise ValueError(f"Language table mismatch in {group} at row {i}, language {lid}")
                row[name] = arr[i].text
            w.writerow(row)
    return len(base)


def cmd_extract(args):
    obj = parse_loc8(Path(args.input))
    lang = get_lang(obj, args.lang)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["group", "index", "id", "source", "translation"])
        w.writeheader()
        for group, entries in (("main", lang.main), ("dialogue", lang.dialogue)):
            for i, e in enumerate(entries):
                w.writerow({"group": group, "index": i, "id": e.id, "source": e.text, "translation": ""})
    print(f"Wrote {len(lang.main)+len(lang.dialogue)} rows to {out}")


def cmd_extract_split(args):
    obj = parse_loc8(Path(args.input))
    outdir = Path(args.output_dir)
    main_n = _write_multilang_group_csv(obj, "main", outdir / "main.csv")
    dialogue_n = _write_multilang_group_csv(obj, "dialogue", outdir / "dialogue.csv")
    print(f"Wrote main.csv ({main_n} rows) and dialogue.csv ({dialogue_n} rows) to {outdir}")

def load_csv(path: Path, group_override: str | None = None) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows and path.stat().st_size:
        raise ValueError("CSV has no data rows")
    required = {"index", "id"}
    if group_override is None:
        required.add("group")
    if rows and not required.issubset(rows[0].keys()):
        raise ValueError(f"CSV must contain columns: {sorted(required)} and either Turkish or translation")
    if rows and not ({"Turkish", "translation"} & set(rows[0].keys())):
        raise ValueError("CSV must contain either a Turkish or translation column")
    if group_override is not None:
        for r in rows:
            r["group"] = group_override
    return rows


def apply_rows(lang: Language, rows: list[dict[str, str]]) -> int:
    changed = 0
    groups = {"main": lang.main, "dialogue": lang.dialogue}
    for r in rows:
        tr = r.get("Turkish", r.get("translation", ""))
        if tr == "":
            continue
        group = r["group"].strip().lower()
        if group not in groups:
            raise ValueError(f"Unknown group {group!r}")
        idx = int(r["index"])
        sid = int(r["id"])
        arr = groups[group]
        if not (0 <= idx < len(arr)):
            raise IndexError(f"{group} index {idx} out of range")
        if arr[idx].id != sid:
            raise ValueError(f"CSV mismatch at {group}[{idx}]: file id={arr[idx].id}, csv id={sid}")
        if arr[idx].text != tr:
            arr[idx].text = tr
            changed += 1
    return changed

def cmd_inject(args):
    obj = parse_loc8(Path(args.input))
    rows = load_csv(Path(args.csv))
    target = get_lang(obj, args.lang)
    changed = apply_rows(target, rows)
    if args.all_languages:
        # Apply the same translated strings by group/index to every slot. IDs and metadata stay slot-native.
        for lang in obj.languages:
            if lang.id == target.id:
                continue
            for group_name in ("main", "dialogue"):
                src_arr = getattr(target, group_name)
                dst_arr = getattr(lang, group_name)
                if len(src_arr) != len(dst_arr):
                    raise ValueError("Language table lengths differ; cannot clone safely")
                for i in range(len(src_arr)):
                    dst_arr[i].text = src_arr[i].text
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(serialize(obj))
    print(f"Injected {changed} translated rows into language {args.lang}; wrote {out}")
    if args.all_languages:
        print("The translated text was cloned to all language slots.")



def cmd_inject_split(args):
    obj = parse_loc8(Path(args.input))
    csv_dir = Path(args.csv_dir)
    rows = []
    rows += load_csv(csv_dir / "main.csv", "main")
    rows += load_csv(csv_dir / "dialogue.csv", "dialogue")
    target = get_lang(obj, args.lang)
    changed = apply_rows(target, rows)
    if args.all_languages:
        for lang in obj.languages:
            if lang.id == target.id:
                continue
            for group_name in ("main", "dialogue"):
                src_arr = getattr(target, group_name)
                dst_arr = getattr(lang, group_name)
                if len(src_arr) != len(dst_arr):
                    raise ValueError("Language table lengths differ; cannot clone safely")
                for i in range(len(src_arr)):
                    dst_arr[i].text = src_arr[i].text
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(serialize(obj))
    print(f"Injected {changed} translated rows from split CSVs into language {args.lang}; wrote {out}")
    if args.all_languages:
        print("The translated text was cloned to all language slots.")

def cmd_roundtrip(args):
    p = Path(args.input)
    obj = parse_loc8(p)
    rebuilt = serialize(obj)
    original = p.read_bytes()
    if rebuilt == original:
        print("OK: byte-identical round-trip")
    else:
        print(f"FAIL: rebuilt file differs (original={len(original)}, rebuilt={len(rebuilt)})")
        raise SystemExit(2)


def main():
    ap = argparse.ArgumentParser(description="Extract/inject Gravity Falls UbiArt LOC8 text")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("info"); p.add_argument("input"); p.set_defaults(func=cmd_info)
    p = sp.add_parser("extract"); p.add_argument("input"); p.add_argument("output"); p.add_argument("--lang", type=int, default=0); p.set_defaults(func=cmd_extract)
    p = sp.add_parser("extract-split"); p.add_argument("input"); p.add_argument("output_dir"); p.set_defaults(func=cmd_extract_split)
    p = sp.add_parser("inject"); p.add_argument("input"); p.add_argument("csv"); p.add_argument("output"); p.add_argument("--lang", type=int, default=0); p.add_argument("--all-languages", action="store_true"); p.set_defaults(func=cmd_inject)
    p = sp.add_parser("inject-split"); p.add_argument("input"); p.add_argument("csv_dir"); p.add_argument("output"); p.add_argument("--lang", type=int, default=0); p.add_argument("--all-languages", action="store_true"); p.set_defaults(func=cmd_inject_split)
    p = sp.add_parser("roundtrip"); p.add_argument("input"); p.set_defaults(func=cmd_roundtrip)
    args = ap.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
