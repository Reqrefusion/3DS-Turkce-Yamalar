#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kid Icarus: Uprising gibi 3DS oyunlarında "bin" içinde gömülü MSBT (MsgStdBn) bloklarını
toplu şekilde extract + restore eder.

Kullanım:
  1) Extract:
     python msbt_bulk.py extract -i "INPUT_FOLDER" -o "OUT_FOLDER"

  2) Restore (çevirilmiş .msbt'leri geri göm):
     python msbt_bulk.py restore -i "INPUT_FOLDER" -o "OUT_FOLDER"

Notlar:
- Script, INPUT_FOLDER içindeki tüm dosyalarda MsgStdBn arar.
- MSBT boyutunu header içindeki "Total Filesize" alanından okur (MSBT spec).
- Restore, OUT_FOLDER altında çıkan .msbt dosyalarını baz alarak original dosyalara geri yazar.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


MAGIC = b"MsgStdBn"


def sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def find_all_magic_positions(data: bytes, magic: bytes = MAGIC) -> List[int]:
    """Return all offsets where magic occurs."""
    offsets = []
    start = 0
    while True:
        idx = data.find(magic, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    return offsets


def read_u32(data: bytes, off: int, endian: str) -> int:
    """Read unsigned 32-bit int."""
    return int.from_bytes(data[off:off+4], endian, signed=False)


def detect_endian_and_size(data: bytes, msbt_off: int) -> Optional[Tuple[str, int]]:
    """
    MSBT header: Total Filesize field at offset 0x12 from start (u32, endian depends).
    Endianness usually LE on 3DS, but we verify plausibility.
    """
    size_off = msbt_off + 0x12
    if size_off + 4 > len(data):
        return None

    size_le = read_u32(data, size_off, "little")
    size_be = read_u32(data, size_off, "big")

    # Choose plausible size: must be > 0x20 and inside file
    def plausible(sz: int) -> bool:
        return 0x20 <= sz <= (len(data) - msbt_off)

    le_ok = plausible(size_le)
    be_ok = plausible(size_be)

    if le_ok and not be_ok:
        return ("little", size_le)
    if be_ok and not le_ok:
        return ("big", size_be)

    # If both plausible, prefer little (3DS most common).
    if le_ok and be_ok:
        return ("little", size_le)

    return None


def safe_relpath(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def extract_msbt_from_file(src_path: Path, in_root: Path, out_root: Path) -> List[Dict]:
    """
    Extract all MSBT blocks embedded in a file.
    Returns list of index entries.
    """
    entries = []
    data = src_path.read_bytes()
    offsets = find_all_magic_positions(data, MAGIC)
    if not offsets:
        return entries

    rel = safe_relpath(src_path, in_root)
    base_out_dir = out_root / rel
    # We store extracted msbt files next to a virtual folder named "__msbt__"
    out_dir = base_out_dir.parent / "__msbt__"
    ensure_dir(out_dir)

    file_sha1 = sha1_file(src_path)

    for i, off in enumerate(offsets):
        det = detect_endian_and_size(data, off)
        if not det:
            continue
        endian, size = det
        end = off + size
        if end > len(data):
            continue

        msbt_blob = data[off:end]

        # Output name: originalfilename__<index>__0xOFFSET.msbt
        out_name = f"{src_path.name}__{i:02d}__0x{off:08X}.msbt"
        out_path = out_dir / out_name
        out_path.write_bytes(msbt_blob)

        entries.append({
            "source_relpath": rel,
            "source_sha1": file_sha1,
            "msbt_index": i,
            "msbt_offset": off,
            "msbt_size": size,
            "endian_guess": endian,
            "extracted_relpath": safe_relpath(out_path, out_root),
        })

    return entries


def cmd_extract(in_dir: Path, out_dir: Path) -> None:
    in_dir = in_dir.resolve()
    out_dir = out_dir.resolve()
    ensure_dir(out_dir)

    all_entries = []
    scanned = 0
    extracted_files = 0

    for p in in_dir.rglob("*"):
        if not p.is_file():
            continue
        scanned += 1
        try:
            entries = extract_msbt_from_file(p, in_dir, out_dir)
            if entries:
                all_entries.extend(entries)
                extracted_files += len(entries)
        except Exception as e:
            print(f"[!] Hata (extract) {p}: {e}")

    index_path = out_dir / "msbt_index.json"
    index_path.write_text(json.dumps({
        "input_root": str(in_dir),
        "output_root": str(out_dir),
        "total_scanned_files": scanned,
        "total_msbt_extracted": extracted_files,
        "entries": all_entries
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] Tarandı: {scanned} dosya")
    print(f"[OK] Çıkarılan MSBT: {extracted_files}")
    print(f"[OK] Index: {index_path}")


def restore_one_entry(entry: Dict, in_root: Path, out_root: Path) -> bool:
    """
    Restore a single MSBT entry back into its source file in-place.
    Uses extracted_relpath from OUT_FOLDER.
    """
    src_path = in_root / entry["source_relpath"]
    msbt_path = out_root / entry["extracted_relpath"]

    if not src_path.exists():
        print(f"[!] Source yok: {src_path}")
        return False
    if not msbt_path.exists():
        print(f"[!] MSBT yok: {msbt_path}")
        return False

    # Integrity check (optional): warn if source changed
    current_sha1 = sha1_file(src_path)
    if current_sha1 != entry["source_sha1"]:
        print(f"[!] UYARI: Source değişmiş görünüyor (sha1 farklı): {src_path}")

    data = bytearray(src_path.read_bytes())
    off = int(entry["msbt_offset"])
    orig_size = int(entry["msbt_size"])

    new_blob = msbt_path.read_bytes()

    if len(new_blob) > orig_size:
        print(f"[X] Boyut büyümüş! {msbt_path.name} ({len(new_blob)}) > original ({orig_size})")
        return False

    # If smaller, pad with zeros to keep container stable
    if len(new_blob) < orig_size:
        new_blob += b"\x00" * (orig_size - len(new_blob))

    # Safety: check original magic still there
    if data[off:off+8] != MAGIC:
        print(f"[!] UYARI: Orijinal offsette MsgStdBn yok (offset kaymış olabilir): {src_path}")
        # Still write if user wants; but safer to stop:
        return False

    data[off:off+orig_size] = new_blob
    src_path.write_bytes(data)
    return True


def cmd_restore(in_dir: Path, out_dir: Path) -> None:
    in_dir = in_dir.resolve()
    out_dir = out_dir.resolve()

    index_path = out_dir / "msbt_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Index bulunamadı: {index_path}")

    idx = json.loads(index_path.read_text(encoding="utf-8"))
    entries = idx.get("entries", [])

    ok = 0
    fail = 0
    for e in entries:
        try:
            if restore_one_entry(e, in_dir, out_dir):
                ok += 1
            else:
                fail += 1
        except Exception as ex:
            print(f"[!] Hata (restore) {e.get('source_relpath')}: {ex}")
            fail += 1

    print(f"[OK] Restore başarılı: {ok}")
    print(f"[OK] Restore başarısız: {fail}")
    print("Not: Eğer 'Boyut büyümüş' hatası alırsan, çeviride metni kısalt veya MSBT yapısını yeniden paketleyebilen bir editör kullan.")


def main():
    ap = argparse.ArgumentParser(description="Bulk MSBT extractor/restorer (MsgStdBn) for nested folders.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_e = sub.add_parser("extract", help="Scan folder recursively, extract embedded MSBT blocks.")
    ap_e.add_argument("-i", "--input", required=True, help="Input folder (original extracted game files).")
    ap_e.add_argument("-o", "--output", required=True, help="Output folder for extracted MSBTs + index.")

    ap_r = sub.add_parser("restore", help="Restore edited MSBTs back into original files using index.")
    ap_r.add_argument("-i", "--input", required=True, help="Input folder (same as original input).")
    ap_r.add_argument("-o", "--output", required=True, help="Output folder where msbt_index.json exists.")

    args = ap.parse_args()
    in_dir = Path(args.input)
    out_dir = Path(args.output)

    if args.cmd == "extract":
        cmd_extract(in_dir, out_dir)
    elif args.cmd == "restore":
        cmd_restore(in_dir, out_dir)


if __name__ == "__main__":
    main()
