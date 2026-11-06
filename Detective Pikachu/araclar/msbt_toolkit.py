#!/usr/bin/env python3
"""Detective Pikachu / Nintendo MSBT comparison and rebuild toolkit.

Supports this game's little-endian, UTF-8 MSBT files and preserves embedded
control codes by exposing them as {{CTRL:GGGG:TTTT:HEXARGS}} tokens.
"""
from __future__ import annotations
import argparse, csv, re, struct, sys
from pathlib import Path
from collections import defaultdict

CANONICAL_LANG_ORDER = [
    "English", "French", "German", "Italian", "Spanish",
    "JPN", "jp_hira", "Simp_Chinese", "Trad_Chinese", "Turkish"
]
CTRL_TOKEN_RE = re.compile(r"\{\{CTRL:([0-9A-Fa-f]{4}):([0-9A-Fa-f]{4}):([0-9A-Fa-f]*)\}\}")
BYTE_TOKEN_RE = re.compile(r"\{\{BYTE:([0-9A-Fa-f]{2})\}\}")
ANY_TOKEN_RE = re.compile(r"\{\{(?:CTRL:[0-9A-Fa-f]{4}:[0-9A-Fa-f]{4}:[0-9A-Fa-f]*|BYTE:[0-9A-Fa-f]{2})\}\}")


def align16(n: int) -> int:
    return (n + 15) & ~15


def _sections(data: bytes):
    pos = 32
    out = {}
    while pos + 16 <= len(data):
        magic_b = data[pos:pos+4]
        try:
            magic = magic_b.decode("ascii")
        except UnicodeDecodeError:
            break
        if not re.fullmatch(r"[A-Z0-9]{4}", magic):
            break
        size = struct.unpack_from("<I", data, pos + 4)[0]
        body = pos + 16
        if body + size > len(data):
            raise ValueError(f"Corrupt section {magic}: size beyond EOF")
        out[magic] = (pos, size, body)
        pos = align16(body + size)
    return out


def parse_msbt(path: str | Path):
    path = Path(path)
    data = path.read_bytes()
    if data[:8] != b"MsgStdBn":
        raise ValueError(f"Not an MSBT: {path}")
    if data[8:10] != b"\xff\xfe":
        raise ValueError(f"Only little-endian MSBT is supported: {path}")
    secs = _sections(data)
    if "LBL1" not in secs or "TXT2" not in secs:
        raise ValueError(f"Missing LBL1/TXT2 section: {path}")

    _, _, lbl_body = secs["LBL1"]
    group_count = struct.unpack_from("<I", data, lbl_body)[0]
    labels = {}
    for gi in range(group_count):
        count, rel = struct.unpack_from("<II", data, lbl_body + 4 + gi * 8)
        pos = lbl_body + rel
        for _ in range(count):
            ln = data[pos]
            pos += 1
            label = data[pos:pos+ln].decode("utf-8")
            pos += ln
            index = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            labels[index] = label

    txt_pos, txt_size, txt_body = secs["TXT2"]
    count = struct.unpack_from("<I", data, txt_body)[0]
    offsets = [struct.unpack_from("<I", data, txt_body + 4 + i * 4)[0] for i in range(count)]
    raws = []
    for i, rel in enumerate(offsets):
        start = txt_body + rel
        end = txt_body + (offsets[i+1] if i + 1 < count else txt_size)
        chunk = data[start:end]
        if chunk.endswith(b"\x00"):
            chunk = chunk[:-1]
        raws.append(chunk)

    return {
        "path": path, "data": data, "sections": secs,
        "labels": labels, "raws": raws, "txt_pos": txt_pos, "txt_size": txt_size,
    }


def decode_text(raw: bytes) -> str:
    """Decode UTF-8 text while losslessly tokenizing MSBT control codes."""
    parts = []
    buf = bytearray()

    def flush():
        nonlocal buf
        if not buf:
            return
        bb = bytes(buf)
        pos = 0
        while pos < len(bb):
            try:
                parts.append(bb[pos:].decode("utf-8"))
                pos = len(bb)
            except UnicodeDecodeError as e:
                if e.start:
                    parts.append(bb[pos:pos+e.start].decode("utf-8"))
                bad = bb[pos+e.start]
                parts.append(f"{{{{BYTE:{bad:02X}}}}}")
                pos += e.start + 1
        buf = bytearray()

    i = 0
    while i < len(raw):
        if raw[i] == 0x0E and i + 7 <= len(raw):
            arg_len = struct.unpack_from("<H", raw, i + 5)[0]
            end = i + 7 + arg_len
            if end <= len(raw):
                flush()
                group = struct.unpack_from("<H", raw, i + 1)[0]
                typ = struct.unpack_from("<H", raw, i + 3)[0]
                args = raw[i+7:end]
                parts.append(f"{{{{CTRL:{group:04X}:{typ:04X}:{args.hex().upper()}}}}}")
                i = end
                continue
        buf.append(raw[i])
        i += 1
    flush()
    return "".join(parts)


def encode_text(text: str) -> bytes:
    out = bytearray()
    pos = 0
    for m in ANY_TOKEN_RE.finditer(text):
        out += text[pos:m.start()].encode("utf-8")
        token = m.group(0)
        cm = CTRL_TOKEN_RE.fullmatch(token)
        if cm:
            group = int(cm.group(1), 16)
            typ = int(cm.group(2), 16)
            args = bytes.fromhex(cm.group(3))
            out.append(0x0E)
            out += struct.pack("<HHH", group, typ, len(args))
            out += args
        else:
            bm = BYTE_TOKEN_RE.fullmatch(token)
            out.append(int(bm.group(1), 16))
        pos = m.end()
    out += text[pos:].encode("utf-8")
    return bytes(out)


def control_signature(text: str):
    return tuple(m.group(0) for m in ANY_TOKEN_RE.finditer(text))


def build_msbt(base, texts):
    if len(texts) != len(base["raws"]):
        raise ValueError(f"Text count mismatch: expected {len(base['raws'])}, got {len(texts)}")
    raws = [encode_text(t) if isinstance(t, str) else bytes(t) for t in texts]
    count = len(raws)
    offset0 = 4 + 4 * count
    offsets = []
    payload = bytearray()
    cursor = offset0
    for raw in raws:
        offsets.append(cursor)
        blob = raw + b"\x00"
        payload += blob
        cursor += len(blob)
    body = bytearray(struct.pack("<I", count))
    body += b"".join(struct.pack("<I", x) for x in offsets)
    body += payload

    data = bytearray(base["data"][:base["txt_pos"]])
    old_hdr = bytearray(base["data"][base["txt_pos"]:base["txt_pos"]+16])
    struct.pack_into("<I", old_hdr, 4, len(body))
    data += old_hdr
    data += body
    data += b"\xAB" * (align16(len(data)) - len(data))
    struct.pack_into("<I", data, 18, len(data))
    return bytes(data)


def discover_languages(message_dir: Path):
    found = [p.name for p in message_dir.iterdir() if p.is_dir()]
    rank = {x:i for i,x in enumerate(CANONICAL_LANG_ORDER)}
    return sorted(found, key=lambda x: (rank.get(x, 999), x.lower()))


def parse_extra(values):
    extras = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError("--extra must be NAME=/path/to/msbt_dir")
        name, path = item.split("=", 1)
        extras[name] = Path(path)
    return extras


def export_comparison(message_dir: Path, out_dir: Path, extras=None):
    extras = extras or {}
    langs = discover_languages(message_dir)
    lang_dirs = {x: message_dir / x for x in langs}
    lang_dirs.update(extras)
    all_langs = list(lang_dirs)
    rank = {x:i for i,x in enumerate(CANONICAL_LANG_ORDER)}
    all_langs = sorted(all_langs, key=lambda x:(rank.get(x,999), x.lower()))

    if "English" not in lang_dirs:
        raise ValueError("English directory is required as alignment base")
    files = sorted(p.name for p in lang_dirs["English"].glob("*.msbt"))
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    for fname in files:
        parsed = {}
        for lang in all_langs:
            p = lang_dirs[lang] / fname
            if not p.exists():
                raise FileNotFoundError(f"Missing {lang}/{fname}")
            parsed[lang] = parse_msbt(p)
        base = parsed["English"]
        base_labels = [base["labels"].get(i, f"__INDEX_{i}") for i in range(len(base["raws"]))]
        for lang, obj in parsed.items():
            labels = [obj["labels"].get(i, f"__INDEX_{i}") for i in range(len(obj["raws"]))]
            if labels != base_labels:
                raise ValueError(f"Label/index mismatch in {lang}/{fname}")

        csv_path = out_dir / (Path(fname).stem + ".csv")
        headers = ["Index", "Label"] + all_langs
        if "Turkish" not in all_langs:
            headers += ["Turkish_Current", "Turkish_Revised", "Review_Notes"]
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for i, label in enumerate(base_labels):
                row = {"Index": i, "Label": label}
                for lang in all_langs:
                    row[lang] = decode_text(parsed[lang]["raws"][i])
                if "Turkish" not in all_langs:
                    row["Turkish_Current"] = ""
                    row["Turkish_Revised"] = ""
                    row["Review_Notes"] = ""
                w.writerow(row)
        manifest.append((fname, len(base["raws"])))

    with (out_dir / "_manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["File", "Rows"])
        w.writerows(manifest)
    return all_langs, manifest


def read_csv_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def apply_csv(base_path: Path, csv_path: Path, column: str, output: Path, strict_controls=True, fallback_column=None):
    base = parse_msbt(base_path)
    rows = read_csv_rows(csv_path)
    if len(rows) != len(base["raws"]):
        raise ValueError(f"CSV row count {len(rows)} != MSBT text count {len(base['raws'])}")
    texts = []
    for i, row in enumerate(rows):
        expected_label = base["labels"].get(i, f"__INDEX_{i}")
        if row.get("Label") != expected_label:
            raise ValueError(f"Row {i}: label mismatch: CSV={row.get('Label')!r}, MSBT={expected_label!r}")
        text = row.get(column, "")
        if not text and fallback_column:
            text = row.get(fallback_column, "")
        if text == "" and base["raws"][i] != b"":
            raise ValueError(f"Row {i} ({expected_label}) has blank {column!r}")
        if strict_controls:
            base_text = decode_text(base["raws"][i])
            if control_signature(text) != control_signature(base_text):
                raise ValueError(
                    f"Row {i} ({expected_label}) control tokens differ from base. "
                    "Keep {{CTRL:...}} tokens unchanged or use --no-strict-controls."
                )
        texts.append(text)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_msbt(base, texts))


def validate_dir(message_dir: Path, extra=None):
    extra = extra or {}
    langs = discover_languages(message_dir)
    dirs = {x:message_dir/x for x in langs}
    dirs.update(extra)
    if "English" not in dirs:
        raise ValueError("English directory missing")
    files = sorted(p.name for p in dirs["English"].glob("*.msbt"))
    total = 0
    for fname in files:
        base = parse_msbt(dirs["English"]/fname)
        labs0 = [base["labels"].get(i) for i in range(len(base["raws"]))]
        for lang, d in dirs.items():
            p = d/fname
            if not p.exists():
                raise FileNotFoundError(p)
            m = parse_msbt(p)
            labs = [m["labels"].get(i) for i in range(len(m["raws"]))]
            if labs != labs0:
                raise ValueError(f"Mismatch: {lang}/{fname}")
        total += len(labs0)
    print(f"OK: {len(files)} files, {len(dirs)} languages, {total} aligned message rows per language.")


def qa_csv(csv_path: Path, turkish_column: str, out_path: Path, source_column="English"):
    rows = read_csv_rows(csv_path)
    findings = []
    source_to_tr = defaultdict(set)
    for row in rows:
        src = row.get(source_column, "")
        tr = row.get(turkish_column, "")
        if tr:
            source_to_tr[src].add(tr)
    for row in rows:
        idx, label = row.get("Index", ""), row.get("Label", "")
        src, tr = row.get(source_column, ""), row.get(turkish_column, "")
        flags = []
        if not tr:
            flags.append("EMPTY_TR")
        else:
            if tr == src and any(ch.isalpha() for ch in src): flags.append("SAME_AS_ENGLISH")
            if control_signature(tr) != control_signature(src): flags.append("CONTROL_MISMATCH")
            src_plain = ANY_TOKEN_RE.sub("", src)
            tr_plain = ANY_TOKEN_RE.sub("", tr)
            if src_plain and tr_plain:
                ratio = len(tr_plain) / max(1, len(src_plain))
                if ratio > 1.85: flags.append("VERY_LONG")
                if ratio < 0.42: flags.append("VERY_SHORT")
            if src.count("\n") != tr.count("\n"): flags.append("NEWLINE_DIFF")
            if len(source_to_tr.get(src, ())) > 1: flags.append("INCONSISTENT_REPEATED_SOURCE")
        if flags:
            findings.append([idx, label, ";".join(flags), src, tr])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w=csv.writer(f); w.writerow(["Index","Label","Flags",source_column,turkish_column]); w.writerows(findings)
    print(f"QA: {len(findings)} flagged rows -> {out_path}")



def apply_dir(base_dir: Path, csv_dir: Path, column: str, output_dir: Path, strict_controls=True, fallback_column=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(p for p in csv_dir.glob("*.csv") if not p.name.startswith("_"))
    if not csv_files:
        raise ValueError(f"No per-file CSVs found in {csv_dir}")
    written = 0
    for csv_path in csv_files:
        base_path = base_dir / (csv_path.stem + ".msbt")
        if not base_path.exists():
            raise FileNotFoundError(base_path)
        out_path = output_dir / base_path.name
        apply_csv(base_path, csv_path, column, out_path, strict_controls, fallback_column)
        written += 1
    print(f"Built {written} MSBT files -> {output_dir}")


def qa_dir(csv_dir: Path, turkish_column: str, out_dir: Path, source_column="English"):
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for csv_path in sorted(p for p in csv_dir.glob("*.csv") if not p.name.startswith("_")):
        out_path = out_dir / (csv_path.stem + "_qa.csv")
        qa_csv(csv_path, turkish_column, out_path, source_column)
        total += 1
    print(f"QA reports created for {total} files -> {out_dir}")


def make_review_assets(csv_dir: Path):
    """Create heuristic review priority and translation-memory CSVs from comparison CSVs."""
    per_files = sorted(p for p in csv_dir.glob("*.csv") if not p.name.startswith("_"))
    langs = ["English","French","German","Italian","Spanish","JPN","jp_hira","Simp_Chinese","Trad_Chinese"]
    priority_rows=[]
    memory=defaultdict(lambda: {"count":0, "files":set(), **{x:set() for x in langs[1:]}})

    def plain(s):
        s=ANY_TOKEN_RE.sub("", s or "")
        return s.replace("\n"," ").strip()
    def mood(s):
        s=plain(s)
        return ("?" in s or "？" in s, "!" in s or "！" in s, "..." in s or "…" in s)

    for path in per_files:
        rows=read_csv_rows(path)
        for row in rows:
            en=row.get("English","")
            key=plain(en)
            if key:
                ent=memory[key]; ent["count"]+=1; ent["files"].add(path.stem)
                for lang in langs[1:]:
                    if row.get(lang): ent[lang].add(plain(row[lang]))

            reasons=[]; score=0
            controls={lang:control_signature(row.get(lang,"")) for lang in langs}
            if len(set(controls.values()))>1:
                score+=4; reasons.append("control-code variation")
            newlines={lang:(row.get(lang,"").count("\n")) for lang in langs}
            if len(set(newlines.values()))>1:
                score+=2; reasons.append("line-break variation")
            moods={lang:mood(row.get(lang,"")) for lang in langs if lang!="jp_hira"}
            if len(set(moods.values()))>1:
                score+=2; reasons.append("question/exclamation/ellipsis variation")
            latin_lens=[]
            for lang in ["English","French","German","Italian","Spanish"]:
                x=plain(row.get(lang,""))
                if x: latin_lens.append(len(x))
            if len(latin_lens)>=3:
                ratio=max(latin_lens)/max(1,min(latin_lens))
                if ratio>=2.5:
                    score+=3; reasons.append("large localization expansion/compression")
                elif ratio>=1.8:
                    score+=2; reasons.append("localization expansion/compression")
            label=row.get("Label","")
            if any(x in label for x in ("_SEL_","SELECT","QUESTION","QTM","CHOICE")):
                score+=1; reasons.append("choice/prompt context")
            if score>=3:
                priority_rows.append([path.name,row.get("Index",""),label,score,"; ".join(reasons)] + [row.get(x,"") for x in langs])

    priority_rows.sort(key=lambda r:(-int(r[3]), r[0], int(r[1]) if str(r[1]).isdigit() else 999999))
    with (csv_dir/"_review_priority.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["File","Index","Label","PriorityScore","Reasons"]+langs); w.writerows(priority_rows)

    mem_rows=[]
    for en,ent in memory.items():
        if ent["count"]<2 or len(en)>90: continue
        row=[ent["count"]," | ".join(sorted(ent["files"])),en]
        for lang in langs[1:]: row.append(" || ".join(sorted(ent[lang])))
        mem_rows.append(row)
    mem_rows.sort(key=lambda r:(-r[0], r[2].lower()))
    with (csv_dir/"_translation_memory.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["Occurrences","Files"]+langs); w.writerows(mem_rows)
    print(f"Review priority rows: {len(priority_rows)}; repeated-source memory rows: {len(mem_rows)}")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest="cmd", required=True)

    p=sub.add_parser("export", help="Export one side-by-side CSV per MSBT file")
    p.add_argument("message_dir", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--extra", action="append", default=[], help="Additional language dir, e.g. Turkish=/path/to/Turkish")

    p=sub.add_parser("validate", help="Validate file/label alignment across languages")
    p.add_argument("message_dir", type=Path)
    p.add_argument("--extra", action="append", default=[])

    p=sub.add_parser("apply", help="Build an MSBT from an edited CSV column")
    p.add_argument("base_msbt", type=Path)
    p.add_argument("csv_file", type=Path)
    p.add_argument("column")
    p.add_argument("output_msbt", type=Path)
    p.add_argument("--fallback-column", default=None)
    p.add_argument("--no-strict-controls", action="store_true")

    p=sub.add_parser("qa", help="Create QA flags for a Turkish column in one CSV")
    p.add_argument("csv_file", type=Path)
    p.add_argument("turkish_column")
    p.add_argument("output_csv", type=Path)
    p.add_argument("--source-column", default="English")

    p=sub.add_parser("apply-dir", help="Batch-build all MSBT files from per-file CSVs")
    p.add_argument("base_dir", type=Path)
    p.add_argument("csv_dir", type=Path)
    p.add_argument("column")
    p.add_argument("output_dir", type=Path)
    p.add_argument("--fallback-column", default=None)
    p.add_argument("--no-strict-controls", action="store_true")

    p=sub.add_parser("qa-dir", help="Create Turkish QA reports for every per-file CSV")
    p.add_argument("csv_dir", type=Path)
    p.add_argument("turkish_column")
    p.add_argument("output_dir", type=Path)
    p.add_argument("--source-column", default="English")

    p=sub.add_parser("review-assets", help="Build heuristic creative-review priority and translation-memory CSVs")
    p.add_argument("csv_dir", type=Path)

    args=ap.parse_args()
    if args.cmd=="export":
        langs, manifest=export_comparison(args.message_dir, args.out_dir, parse_extra(args.extra))
        print("Languages:", ", ".join(langs)); print(f"Exported {len(manifest)} CSV files.")
    elif args.cmd=="validate":
        validate_dir(args.message_dir, parse_extra(args.extra))
    elif args.cmd=="apply":
        apply_csv(args.base_msbt, args.csv_file, args.column, args.output_msbt,
                  strict_controls=not args.no_strict_controls, fallback_column=args.fallback_column)
        print(f"Wrote: {args.output_msbt}")
    elif args.cmd=="qa":
        qa_csv(args.csv_file, args.turkish_column, args.output_csv, args.source_column)
    elif args.cmd=="apply-dir":
        apply_dir(args.base_dir, args.csv_dir, args.column, args.output_dir,
                  strict_controls=not args.no_strict_controls, fallback_column=args.fallback_column)
    elif args.cmd=="qa-dir":
        qa_dir(args.csv_dir, args.turkish_column, args.output_dir, args.source_column)
    elif args.cmd=="review-assets":
        make_review_assets(args.csv_dir)

if __name__ == "__main__":
    main()
