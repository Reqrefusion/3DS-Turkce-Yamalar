#!/usr/bin/env python3
from __future__ import annotations
import argparse, re, sys
from pathlib import Path
from translation_common import FILE_RE, control_tokens, load_jsonl, max_visible_chars

REQUIRED={"file","index","label","source_sha256","source_line_count","source_max_visible_chars","control_tokens","translation"}
HEX64=re.compile(r"^[0-9a-f]{64}$")

def main() -> int:
    ap=argparse.ArgumentParser(description="Star Fox 64 3D TR çeviri kaynağını doğrula")
    ap.add_argument("path", nargs="?", default="translations/tr_TR.jsonl")
    ap.add_argument("--max-extra-chars", type=int, default=8, help="Kaynak en uzun görünür satırına izin verilen ek karakter")
    args=ap.parse_args()
    path=Path(args.path)
    try: rows=load_jsonl(path)
    except Exception as exc:
        print(f"HATA: {exc}", file=sys.stderr); return 2
    errors=[]; warnings=[]; seen=set()
    for row in rows:
        ln=row.get("_line_no","?")
        missing=REQUIRED-set(row)
        if missing: errors.append(f"satır {ln}: eksik alanlar: {', '.join(sorted(missing))}"); continue
        key=(row["file"], row["index"])
        if key in seen: errors.append(f"satır {ln}: yinelenen anahtar {key}")
        seen.add(key)
        if not isinstance(row["file"],str) or not FILE_RE.match(row["file"]): errors.append(f"satır {ln}: dosya adı beklenen biçimde değil")
        if not isinstance(row["index"],int) or row["index"] < 0: errors.append(f"satır {ln}: index geçersiz")
        if not isinstance(row["source_sha256"],str) or not HEX64.match(row["source_sha256"]): errors.append(f"satır {ln}: source_sha256 geçersiz")
        tr=row["translation"]
        if not isinstance(tr,str): errors.append(f"satır {ln}: translation metin değil"); continue
        if tr == "" and row["source_sha256"] != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": errors.append(f"satır {ln}: kaynak boş değilken çeviri boş")
        actual=control_tokens(tr)
        expected=row["control_tokens"]
        if actual != expected: errors.append(f"satır {ln}: MSBT kontrol tokenları değişmiş; beklenen {expected}, bulunan {actual}")
        line_count=tr.count("\n")+1
        if line_count > row["source_line_count"]: errors.append(f"satır {ln}: çeviri {line_count} satır, kaynak sınırı {row['source_line_count']}")
        mx=max_visible_chars(tr); limit=row["source_max_visible_chars"]
        if limit >= 0 and mx > limit + args.max_extra_chars:
            errors.append(f"satır {ln}: en uzun görünür satır {mx} karakter, izin verilen sınır {limit + args.max_extra_chars} (kaynak {limit} + {args.max_extra_chars})")
    if errors:
        print(f"DOĞRULAMA BAŞARISIZ: {len(errors)} hata", file=sys.stderr)
        for e in errors[:100]: print(" - "+e, file=sys.stderr)
        if len(errors)>100: print(f" ... ve {len(errors)-100} hata daha", file=sys.stderr)
        return 1
    print(f"OK: {len(rows)} kayıt, {len(seen)} benzersiz anahtar. Kontrol tokenları, satır sayısı ve uzun satır toleransı temiz.")
    return 0

if __name__ == '__main__': raise SystemExit(main())
