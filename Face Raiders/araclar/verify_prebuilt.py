#!/usr/bin/env python3
"""Verify all prebuilt Turkish MSBT files against the CSV Turkish column."""
from __future__ import annotations
import argparse
from pathlib import Path
import faceraiders_localizer as fl


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("patch_root", help="Klasör: 00_SD_ROOT_READY veya başka LayeredFS kökü")
    args = ap.parse_args()

    _, tr = fl.read_csv_translation(Path(args.csv))
    files = sorted(Path(args.patch_root).glob("luma/titles/*/romfs/hal/msg/StgFace/*.msbt"))
    if not files:
        raise SystemExit("MSBT bulunamadı.")

    failures = []
    for f in files:
        m = fl.MSBT(f.read_bytes())
        texts = m.texts()
        for label, idx in m.labels.items():
            wanted = tr.get(label, "")
            # Empty source/index rows legitimately remain empty.
            if wanted and texts[idx] != wanted:
                failures.append(f"{f}: {label} uyuşmuyor")
                break

    if failures:
        print("FAIL")
        for x in failures:
            print(x)
        raise SystemExit(2)
    print(f"OK: {len(files)} MSBT dosyasının Türkçe metinleri CSV ile birebir eşleşiyor.")


if __name__ == "__main__":
    main()
