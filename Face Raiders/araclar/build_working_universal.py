#!/usr/bin/env python3
"""Rebuild the exact working Face Raiders Turkish universal LayeredFS patch.

Method used by the confirmed-working v2 package:
  1. Read the EU English StgFace MSBT from the user's decrypted CXI/ZIP.
  2. Replace all non-empty source strings from the CSV Turkish column.
  3. Validate printf placeholders and Nintendo private-use button glyphs.
  4. Rebuild and re-parse the MSBT.
  5. Copy that same translated MSBT under every shipped StgFace language filename.
  6. Emit both EUR Old3DS and EUR New3DS LayeredFS title folders.

Uses only Python's standard library plus faceraiders_localizer.py in this folder.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

import faceraiders_localizer as fl

DEFAULT_TITLE_IDS = ("0004001000022D00", "0004001020022D00")


def build(input_path: Path, csv_path: Path, out_root: Path, title_ids: tuple[str, ...]) -> None:
    rom = fl.choose_romfs(input_path, "StgFace")
    _, tr_by_label = fl.read_csv_translation(csv_path)

    base_path = "hal/msg/StgFace/StgFaceEU_English.msbt"
    base = fl.MSBT(rom.get(base_path))
    old = base.texts()
    new = list(old)
    problems: list[str] = []

    for label, idx in base.labels.items():
        src = old[idx]
        tr = tr_by_label.get(label, "")
        if src and not tr:
            problems.append(f"{label}: source dolu ama Turkish boş")
            continue
        if not tr:
            continue
        if fl.fmt_tokens(src) != fl.fmt_tokens(tr):
            problems.append(f"{label}: printf placeholder uyuşmuyor")
        if fl.pua_chars(src) != fl.pua_chars(tr):
            problems.append(f"{label}: PUA/düğme glifi uyuşmuyor")
        new[idx] = tr

    if problems:
        raise SystemExit("Doğrulama hataları:\n  - " + "\n  - ".join(problems))

    patched = base.rebuild(new)
    check = fl.MSBT(patched)
    if check.texts() != new:
        raise SystemExit("MSBT yeniden açma doğrulaması başarısız.")

    shipped_names = [Path(p).name for p in rom.find(prefix="hal/msg/StgFace/StgFace", suffix=".msbt")]
    if not shipped_names:
        raise SystemExit("StgFace dil dosyaları bulunamadı.")

    for tid in title_ids:
        target = out_root / "luma" / "titles" / tid / "romfs" / "hal" / "msg" / "StgFace"
        target.mkdir(parents=True, exist_ok=True)
        for name in shipped_names:
            (target / name).write_bytes(patched)

    print(f"Kaynak CXI: {rom.source_name}")
    print(f"Kaynak Title ID: {rom.title_id:016X}")
    print(f"Dil dosyası sayısı: {len(shipped_names)}")
    print(f"Türkçeleştirilen dolu metin: {sum(1 for s, t in zip(old, new) if s and t != s)}")
    print("Hedef Title ID'ler: " + ", ".join(title_ids))
    print(f"Çıktı: {out_root}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Decrypted Face Raiders .cxi veya CXI içeren .zip")
    ap.add_argument("csv", help="StgFace_all_languages_TR.csv")
    ap.add_argument("out", help="Çıktı klasörü")
    ap.add_argument("--title-id", action="append", dest="title_ids",
                    help="Ek/özel Title ID. Verilmezse EUR Old3DS + New3DS kullanılır.")
    args = ap.parse_args()
    tids = tuple(args.title_ids) if args.title_ids else DEFAULT_TITLE_IDS
    build(Path(args.input), Path(args.csv), Path(args.out), tids)


if __name__ == "__main__":
    main()
