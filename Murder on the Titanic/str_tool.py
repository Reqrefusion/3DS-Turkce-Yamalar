
#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
import struct
from pathlib import Path

def read_str(path: str):
    data = Path(path).read_bytes()
    if len(data) < 4:
        raise ValueError("Dosya çok kısa.")
    count = struct.unpack_from("<I", data, 0)[0]
    table_size = 4 + count * 4
    if len(data) < table_size:
        raise ValueError("Geçersiz ofset tablosu.")
    offsets = list(struct.unpack_from("<" + "I" * count, data, 4))
    text_start = table_size

    strings = []
    for i in range(count):
        start_units = offsets[i]
        end_units = offsets[i + 1] if i + 1 < count else (len(data) - text_start) // 2
        start = text_start + start_units * 2
        end = text_start + end_units * 2
        if start > len(data) or end > len(data) or end < start:
            raise ValueError(f"Bozuk ofset: index={i}, start={start}, end={end}")
        raw = data[start:end]
        text = raw.decode("utf-16le", errors="strict")
        if text.endswith("\x00"):
            text = text[:-1]
        strings.append(text)
    return strings

def write_str(strings, out_path: str):
    encoded = []
    offsets = []
    cursor_units = 0
    for s in strings:
        if "\x00" in s:
            raise ValueError("Metnin içinde NUL (\\x00) karakteri var; bu formatta kullanılamaz.")
        offsets.append(cursor_units)
        blob = (s + "\x00").encode("utf-16le")
        encoded.append(blob)
        cursor_units += len(blob) // 2

    header = struct.pack("<I", len(strings))
    table = struct.pack("<" + "I" * len(offsets), *offsets)
    Path(out_path).write_bytes(header + table + b"".join(encoded))

def export_csv(strings, out_csv: str):
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "text"])
        for i, s in enumerate(strings):
            w.writerow([i, s])

def build_compare_csv(out_csv: str, columns: dict[str, list[str]]):
    names = list(columns.keys())
    count = len(next(iter(columns.values())))
    for name, arr in columns.items():
        if len(arr) != count:
            raise ValueError(f"Kolon uzunluğu eşleşmiyor: {name}")
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", *names, "tr"])
        for i in range(count):
            row = [i] + [columns[name][i] for name in names] + [""]
            w.writerow(row)

def read_csv_column(csv_path: str, column: str, fallback: str | None = None):
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if "index" not in (r.fieldnames or []):
            raise ValueError("CSV içinde 'index' kolonu yok.")
        if column not in (r.fieldnames or []):
            raise ValueError(f"CSV içinde '{column}' kolonu yok.")
        if fallback and fallback not in (r.fieldnames or []):
            raise ValueError(f"CSV içinde fallback kolonu '{fallback}' yok.")

        for row in r:
            idx = int(row["index"])
            value = row.get(column, "")
            if (value is None or value == "") and fallback:
                value = row.get(fallback, "")
            rows.append((idx, value if value is not None else ""))

    rows.sort(key=lambda x: x[0])
    if not rows:
        return []
    expected = list(range(rows[-1][0] + 1))
    seen = [i for i, _ in rows]
    if seen != expected:
        raise ValueError("Index sıralaması eksik veya bozuk. 0..N-1 olmalı.")
    return [text for _, text in rows]

def main():
    ap = argparse.ArgumentParser(
        description="Murder on the Titanic tarzı .str dosyalarını çıkarma/paketleme aracı"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("extract", help=".str -> CSV")
    p1.add_argument("input")
    p1.add_argument("output_csv")

    p2 = sub.add_parser("pack", help="CSV -> .str")
    p2.add_argument("input_csv")
    p2.add_argument("output_str")
    p2.add_argument("--column", default="text", help="Kullanılacak CSV kolonu (varsayılan: text)")
    p2.add_argument("--fallback", default=None, help="Boşsa buradan doldur")

    p3 = sub.add_parser("compare", help="Birden fazla .str dosyasından karşılaştırma CSV'si üret")
    p3.add_argument("output_csv")
    p3.add_argument("inputs", nargs="+", help="ad=dosya.str biçiminde, örn en=gamestrings_en.str")

    args = ap.parse_args()

    if args.cmd == "extract":
        export_csv(read_str(args.input), args.output_csv)
        print(f"Yazıldı: {args.output_csv}")

    elif args.cmd == "pack":
        strings = read_csv_column(args.input_csv, args.column, args.fallback)
        write_str(strings, args.output_str)
        print(f"Yazıldı: {args.output_str}")

    elif args.cmd == "compare":
        cols = {}
        for item in args.inputs:
            if "=" not in item:
                raise ValueError("compare girdileri ad=dosya.str biçiminde olmalı")
            name, path = item.split("=", 1)
            cols[name] = read_str(path)
        build_compare_csv(args.output_csv, cols)
        print(f"Yazıldı: {args.output_csv}")

if __name__ == "__main__":
    main()
