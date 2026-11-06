# zrc_batch_lz11.py
# Batch LZ11 decompress/compress for .zrc files (Kid Icarus Uprising etc.)
# Usage:
#   py -3 zrc_batch_lz11.py unpack "INPUT_FOLDER"
#   py -3 zrc_batch_lz11.py pack   "DECOMPRESSED_FOLDER"

from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict

WINDOW_SIZE = 0x1000         # LZ11 sliding window
MAX_MATCH_LEN = 0x110        # 272 (so we only use 2-byte or 3-byte length encoding)

def lz11_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x11:
        raise ValueError("Bu dosya LZ11 (0x11) ile başlamıyor.")

    out_size = data[1] | (data[2] << 8) | (data[3] << 16)
    pos = 4

    # Some variants store 32-bit size when 3-byte size is zero
    if out_size == 0:
        out_size = int.from_bytes(data[pos:pos+4], "little")
        pos += 4

    out = bytearray()
    while len(out) < out_size and pos < len(data):
        flags = data[pos]
        pos += 1

        for bit in range(8):
            if len(out) >= out_size or pos >= len(data):
                break

            if (flags & (0x80 >> bit)) == 0:
                # literal
                out.append(data[pos])
                pos += 1
            else:
                if pos >= len(data):
                    break

                b1 = data[pos]
                pos += 1
                t = b1 >> 4

                if t == 0:
                    # 3-byte length
                    if pos + 1 >= len(data):
                        break
                    b2 = data[pos]
                    b3 = data[pos + 1]
                    pos += 2

                    length = (((b1 & 0x0F) << 4) | (b2 >> 4)) + 0x11
                    disp = (((b2 & 0x0F) << 8) | b3) + 1

                elif t == 1:
                    # 4-byte length (rare; still supported in decompressor)
                    if pos + 2 >= len(data):
                        break
                    b2 = data[pos]
                    b3 = data[pos + 1]
                    b4 = data[pos + 2]
                    pos += 3

                    length = (((b1 & 0x0F) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                    disp = (((b3 & 0x0F) << 8) | b4) + 1

                else:
                    # 2-byte length
                    if pos >= len(data):
                        break
                    b2 = data[pos]
                    pos += 1

                    length = t + 1
                    disp = (((b1 & 0x0F) << 8) | b2) + 1

                if disp > len(out):
                    raise ValueError("Geçersiz geri referans (disp). Dosya bozuk olabilir.")

                start = len(out) - disp
                for _ in range(length):
                    if len(out) >= out_size:
                        break
                    out.append(out[start])
                    start += 1

    return bytes(out)

def _find_best_match(data: bytes, pos: int, index: dict[bytes, list[int]]) -> tuple[int, int]:
    """Returns (best_len, best_disp). best_len>=3 means use a reference."""
    if pos + 3 > len(data):
        return (0, 0)

    key = data[pos:pos+3]
    candidates = index.get(key)
    if not candidates:
        return (0, 0)

    best_len = 0
    best_disp = 0

    # Search candidates from newest to oldest, but only inside window
    for p in reversed(candidates):
        disp = pos - p
        if disp <= 0:
            continue
        if disp > WINDOW_SIZE:
            break

        max_len = min(MAX_MATCH_LEN, len(data) - pos)
        length = 3
        while length < max_len and data[p + length] == data[pos + length]:
            length += 1

        if length > best_len:
            best_len = length
            best_disp = disp
            if best_len == max_len:
                break

    if best_len < 3:
        return (0, 0)
    return (best_len, best_disp)

def lz11_compress(raw: bytes) -> bytes:
    n = len(raw)
    out = bytearray()

    # Header
    out.append(0x11)
    if n <= 0xFFFFFF:
        out += n.to_bytes(3, "little")
    else:
        out += (0).to_bytes(3, "little")
        out += n.to_bytes(4, "little")

    index: dict[bytes, list[int]] = defaultdict(list)

    i = 0
    flags_pos = len(out)
    out.append(0)
    flags = 0
    bit = 0

    def flush_flags():
        nonlocal flags_pos, flags, bit
        out[flags_pos] = flags
        flags_pos = len(out)
        out.append(0)
        flags = 0
        bit = 0

    while i < n:
        # Update index with current position for future matches
        if i + 3 <= n:
            index[raw[i:i+3]].append(i)
            # Keep index lists from growing too much (optional small pruning)
            if len(index[raw[i:i+3]]) > 256:
                index[raw[i:i+3]] = index[raw[i:i+3]][-256:]

        best_len, best_disp = _find_best_match(raw, i, index)

        if best_len >= 3:
            # Mark this bit as "reference"
            flags |= (0x80 >> bit)

            # Clamp to max we encode (<=272)
            if best_len > MAX_MATCH_LEN:
                best_len = MAX_MATCH_LEN

            disp_minus_1 = best_disp - 1

            if best_len <= 0x10:
                # 2-byte form: length = t+1 where t in [2..15]
                t = best_len - 1  # 2..15
                b1 = ((t & 0x0F) << 4) | ((disp_minus_1 >> 8) & 0x0F)
                b2 = disp_minus_1 & 0xFF
                out += bytes([b1, b2])
            else:
                # 3-byte form: length = x + 0x11, x in [0..0xFF]
                x = best_len - 0x11  # 0..255
                b1 = ((0 & 0x0F) << 4) | ((x >> 4) & 0x0F)
                b2 = ((x & 0x0F) << 4) | ((disp_minus_1 >> 8) & 0x0F)
                b3 = disp_minus_1 & 0xFF
                out += bytes([b1, b2, b3])

            i += best_len
        else:
            # Literal
            out.append(raw[i])
            i += 1

        bit += 1
        if bit == 8:
            flush_flags()

    # Write last flags
    out[flags_pos] = flags

    # Remove trailing empty flags byte if no data followed it
    if len(out) >= 1 and out[-1] == 0 and out[flags_pos] == 0 and flags_pos == len(out)-1:
        out.pop()

    return bytes(out)

def guess_ext(dec: bytes) -> str:
    if dec.startswith(b"darc"):
        return ".darc"
    if dec.startswith(b"SARC"):
        return ".sarc"
    return ".bin"

def unpack_folder(input_dir: Path) -> Path:
    out_dir = input_dir.parent / (input_dir.name + "_DEC_OUT")
    out_dir.mkdir(parents=True, exist_ok=True)

    zrc_files = sorted(input_dir.rglob("*.zrc"))
    if not zrc_files:
        print("Bu klasorde .zrc bulunamadi:", input_dir)
        return out_dir

    ok = 0
    fail = 0
    for p in zrc_files:
        rel = p.relative_to(input_dir)
        try:
            data = p.read_bytes()
            if not data or data[0] != 0x11:
                print(f"[SKIP] LZ11 degil (0x11 yok): {rel}")
                continue

            dec = lz11_decompress(data)
            ext = guess_ext(dec)
            target = (out_dir / rel.parent / (p.stem + "_dec" + ext))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(dec)
            ok += 1
            print(f"[OK]  {rel} -> {target.relative_to(out_dir)}  ({len(dec)} bytes)")
        except Exception as e:
            fail += 1
            print(f"[FAIL] {rel}  -> {e}")

    print(f"\nUNPACK bitti. OK={ok}, FAIL={fail}")
    print("Cikti klasoru:", out_dir)
    return out_dir

def pack_folder(dec_dir: Path) -> Path:
    out_dir = dec_dir.parent / (dec_dir.name + "_PACKED_ZRC")
    out_dir.mkdir(parents=True, exist_ok=True)

    # compress everything that ends with _dec.(darc|bin|sarc) by default
    candidates = sorted([p for p in dec_dir.rglob("*") if p.is_file() and "_dec" in p.stem])
    if not candidates:
        print("Bu klasorde _dec dosya bulunamadi:", dec_dir)
        return out_dir

    ok = 0
    fail = 0
    for p in candidates:
        rel = p.relative_to(dec_dir)
        try:
            raw = p.read_bytes()
            comp = lz11_compress(raw)

            # Remove _dec suffix from name if present
            base = p.stem
            if base.endswith("_dec"):
                base = base[:-4]

            target = out_dir / rel.parent / (base + ".zrc")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(comp)
            ok += 1
            print(f"[OK]  {rel} -> {target.relative_to(out_dir)}  ({len(comp)} bytes)")
        except Exception as e:
            fail += 1
            print(f"[FAIL] {rel}  -> {e}")

    print(f"\nPACK bitti. OK={ok}, FAIL={fail}")
    print("Cikti klasoru:", out_dir)
    return out_dir

def main():
    if len(sys.argv) < 3:
        print(
            "Kullanim:\n"
            "  py -3 zrc_batch_lz11.py unpack \"KLASOR\"\n"
            "  py -3 zrc_batch_lz11.py pack   \"DEC_KLASOR\"\n"
        )
        sys.exit(1)

    mode = sys.argv[1].lower().strip()
    folder = Path(sys.argv[2]).expanduser()

    if not folder.exists() or not folder.is_dir():
        print("Klasor bulunamadi:", folder)
        sys.exit(1)

    if mode == "unpack":
        unpack_folder(folder)
    elif mode == "pack":
        pack_folder(folder)
    else:
        print("Gecersiz mod:", mode, "(unpack veya pack yaz)")
        sys.exit(1)

if __name__ == "__main__":
    main()
