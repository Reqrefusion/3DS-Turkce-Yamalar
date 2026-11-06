import os
import hashlib
from collections import defaultdict
from pathlib import Path

def sha256_hash(file_path: Path, chunk_size=1024 * 1024) -> str:
    """Dosyanın SHA-256 hash'ini hesaplar (parça parça okur)."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def find_duplicate_xmsbt(folder: str):
    folder_path = Path(folder)

    if not folder_path.exists():
        print("Klasör bulunamadı:", folder)
        return

    # 1) Önce dosyaları boyutlarına göre grupla (hız için)
    size_map = defaultdict(list)

    for root, _, files in os.walk(folder_path):
        for name in files:
            if name.lower().endswith(".xmsbt"):
                path = Path(root) / name
                try:
                    size_map[path.stat().st_size].append(path)
                except OSError:
                    print("Okunamayan dosya:", path)

    # 2) Boyutu aynı olanlar arasında hash karşılaştırması yap
    hash_map = defaultdict(list)

    for size, paths in size_map.items():
        if len(paths) < 2:
            continue  # bu boyutta tek dosya varsa duplicate olamaz

        for p in paths:
            try:
                file_hash = sha256_hash(p)
                hash_map[(size, file_hash)].append(p)
            except OSError:
                print("Okunamayan dosya:", p)

    # 3) Duplicate grupları yazdır
    duplicates = {k: v for k, v in hash_map.items() if len(v) > 1}

    if not duplicates:
        print("✅ Aynı olan .xmsbt dosyası bulunamadı.")
        return

    print("\n✅ Bulunan birebir aynı dosyalar:\n")

    group_no = 1
    for (size, file_hash), paths in duplicates.items():
        print(f"--- Grup {group_no} ---")
        print(f"Boyut: {size} byte")
        print(f"SHA256: {file_hash}")
        for p in paths:
            print("  ", p)
        print()
        group_no += 1

if __name__ == "__main__":
    # Buraya klasör yolunu yaz
    target_folder = r"D:\Users\furka\Documents\3ds test\kidicarus\msbt_out\romfs_dir\eu\stage_DEC_OUT\__msbt__\en"
    find_duplicate_xmsbt(target_folder)
