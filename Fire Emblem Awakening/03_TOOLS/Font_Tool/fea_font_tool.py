#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fire Emblem Awakening BFNT Font Tool
------------------------------------
CLI extractor/injector for the game's custom .bfnt.lz font files.

Requires:
    Python 3.9+
    Pillow   (pip install pillow)

This tool intentionally keeps the original BFNT structure and only patches:
- glyph table entries (same row count)
- texture atlas data

It supports the outer Fire Emblem 0x13 wrapper + embedded Nintendo LZ11.
"""

from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
import zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("HATA: Pillow gerekli. Kurulum: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

try:
    import fea_lang_tool as langtool
except ImportError:
    print(
        "HATA: fea_lang_tool.py bu dosyayla aynı klasörde olmalı "
        "(LZ11 sıkıştırma/açma için).",
        file=sys.stderr,
    )
    raise SystemExit(2)


TILE_TABLE = (
    (0, 1, 4, 5, 16, 17, 20, 21),
    (2, 3, 6, 7, 18, 19, 22, 23),
    (8, 9, 12, 13, 24, 25, 28, 29),
    (10, 11, 14, 15, 26, 27, 30, 31),
    (32, 33, 36, 37, 48, 49, 52, 53),
    (34, 35, 38, 39, 50, 51, 54, 55),
    (40, 41, 44, 45, 56, 57, 60, 61),
    (42, 43, 46, 47, 58, 59, 62, 63),
)

TR_CHARS = "ÇĞİÖŞÜçğıöşü"


class FontToolError(RuntimeError):
    pass


def unpack_bfnt_lz(data: bytes) -> bytes:
    # Fire Emblem wrapper: [13 size24] [11 size24 ...]
    if len(data) >= 8 and data[0] == 0x13 and data[4] == 0x11:
        raw = langtool.lz11_decompress(data[4:])
        declared = int.from_bytes(data[1:4], "little")
        if declared and declared != len(raw):
            raise FontToolError(
                f"0x13 boyutu uyuşmuyor: header={declared}, gerçek={len(raw)}"
            )
        return raw

    if data and data[0] == 0x11:
        return langtool.lz11_decompress(data)

    # Allow already-decompressed .bfnt data.
    return data


def pack_bfnt_lz(raw: bytes) -> bytes:
    cmp_data = langtool.lz11_compress(raw)
    if not cmp_data or cmp_data[0] != 0x11:
        raise FontToolError("LZ11 sıkıştırıcı beklenmeyen çıktı verdi.")
    out = bytearray(4 + len(cmp_data))
    out[0] = 0x13
    out[1:4] = cmp_data[1:4]
    out[4:] = cmp_data
    return bytes(out)


def parse_meta(raw: bytes) -> dict:
    if len(raw) < 0x30:
        raise FontToolError("BFNT çok kısa.")

    width = struct.unpack_from("<H", raw, 0x10)[0]
    height = struct.unpack_from("<H", raw, 0x12)[0]
    texture_size = struct.unpack_from("<I", raw, 0x14)[0]
    texture_count = struct.unpack_from("<H", raw, 0x1A)[0]
    glyph_count = struct.unpack_from("<H", raw, 0x22)[0]
    texture_offset = struct.unpack_from("<I", raw, 0x24)[0]

    if not width or not height or not texture_count or not glyph_count:
        raise FontToolError("BFNT header alanları geçersiz.")

    table_start = texture_offset - glyph_count * 16
    if table_start < 0x30 or table_start + glyph_count * 16 != texture_offset:
        raise FontToolError("Glyph tablosu konumu doğrulanamadı.")

    expected_l4 = width * height // 2
    expected_l8 = width * height
    if texture_size == expected_l4:
        texture_format = "L4"
    elif texture_size == expected_l8:
        texture_format = "L8"
    else:
        raise FontToolError(
            f"Desteklenmeyen atlas biçimi/boyutu: {width}x{height}, "
            f"texture_size={texture_size}"
        )

    end = texture_offset + texture_size * texture_count
    if end > len(raw):
        raise FontToolError("Texture verisi dosya sınırını aşıyor.")

    return {
        "width": width,
        "height": height,
        "texture_size": texture_size,
        "texture_count": texture_count,
        "glyph_count": glyph_count,
        "texture_offset": texture_offset,
        "table_start": table_start,
        "texture_format": texture_format,
        "raw_size": len(raw),
    }


def pixel_byte_offset(width: int, x: int, y: int, bpp: float) -> int:
    tiles_per_row = (width + 7) // 8
    base = ((x // 8) + (y // 8) * tiles_per_row) * int(64 * bpp)
    tile_index = TILE_TABLE[y & 7][x & 7]
    return base + int(tile_index * bpp)


def decode_texture(data: bytes, width: int, height: int, fmt: str) -> Image.Image:
    img = Image.new("L", (width, height), 0)
    px = img.load()

    if fmt == "L4":
        for y in range(height):
            for x in range(width):
                off = pixel_byte_offset(width, x, y, 0.5)
                value = (data[off] >> (4 * (x & 1))) & 0xF
                px[x, y] = value * 17
    elif fmt == "L8":
        for y in range(height):
            for x in range(width):
                off = pixel_byte_offset(width, x, y, 1.0)
                px[x, y] = data[off]
    else:
        raise FontToolError(f"Bilinmeyen format: {fmt}")

    return img


def encode_texture(img: Image.Image, width: int, height: int, fmt: str) -> bytes:
    if img.size != (width, height):
        raise FontToolError(
            f"PNG boyutu yanlış: {img.size[0]}x{img.size[1]}, "
            f"beklenen {width}x{height}"
        )

    img = img.convert("L")
    px = img.load()

    if fmt == "L4":
        out = bytearray(width * height // 2)
        for y in range(height):
            for x in range(width):
                off = pixel_byte_offset(width, x, y, 0.5)
                nibble = max(0, min(15, int(round(px[x, y] / 17.0))))
                shift = 4 * (x & 1)
                out[off] = (out[off] & ~(0xF << shift)) | (nibble << shift)
        return bytes(out)

    if fmt == "L8":
        out = bytearray(width * height)
        for y in range(height):
            for x in range(width):
                off = pixel_byte_offset(width, x, y, 1.0)
                out[off] = px[x, y]
        return bytes(out)

    raise FontToolError(f"Bilinmeyen format: {fmt}")


def read_glyphs(raw: bytes, meta: dict) -> list[dict]:
    rows = []
    base = meta["table_start"]

    for i in range(meta["glyph_count"]):
        off = base + i * 16
        entry = raw[off : off + 16]
        codepoint, page, x, y = struct.unpack_from("<HHHH", entry, 0)
        rows.append(
            {
                "index": i,
                "codepoint": codepoint,
                "char": chr(codepoint) if codepoint else "",
                "page": page,
                "x": x,
                "y": y,
                "width": entry[8],
                "height": entry[9],
                "byte10": entry[10],
                "byte11": entry[11],
                "byte12": entry[12],
                "tail_hex": entry[13:16].hex(),
            }
        )
    return rows


CSV_FIELDS = [
    "index",
    "codepoint",
    "char",
    "page",
    "x",
    "y",
    "width",
    "height",
    "byte10",
    "byte11",
    "byte12",
    "tail_hex",
]


def write_glyph_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def parse_int(value: str) -> int:
    value = str(value).strip()
    if value.lower().startswith("0x"):
        return int(value, 16)
    return int(value)


def read_glyph_csv(path: Path, expected_count: int) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != expected_count:
        raise FontToolError(
            f"{path.name}: satır sayısı değişmiş ({len(rows)}), "
            f"beklenen {expected_count}. Bu sürüm glyph sayısını değiştirmez."
        )

    result = []
    for pos, row in enumerate(rows):
        index = parse_int(row["index"])
        if index != pos:
            raise FontToolError(
                f"{path.name}: index sırası değişmiş. Satır {pos+2}: index={index}"
            )

        cp_field = row.get("codepoint", "").strip()
        ch_field = row.get("char", "")
        if cp_field:
            cp = parse_int(cp_field)
        elif ch_field:
            cp = ord(ch_field[0])
        else:
            cp = 0

        tail = bytes.fromhex(row.get("tail_hex", "") or "000000")
        if len(tail) != 3:
            raise FontToolError(f"{path.name}: tail_hex 3 byte olmalı.")

        item = {
            "index": index,
            "codepoint": cp,
            "page": parse_int(row["page"]),
            "x": parse_int(row["x"]),
            "y": parse_int(row["y"]),
            "width": parse_int(row["width"]),
            "height": parse_int(row["height"]),
            "byte10": parse_int(row["byte10"]),
            "byte11": parse_int(row["byte11"]),
            "byte12": parse_int(row["byte12"]),
            "tail": tail,
        }

        if not (0 <= item["codepoint"] <= 0xFFFF):
            raise FontToolError(f"{path.name}: codepoint UTF-16 aralığı dışında.")
        for key in ("page", "x", "y"):
            if not (0 <= item[key] <= 0xFFFF):
                raise FontToolError(f"{path.name}: {key} aralık dışında.")
        for key in ("width", "height", "byte10", "byte11", "byte12"):
            if not (0 <= item[key] <= 0xFF):
                raise FontToolError(f"{path.name}: {key} byte aralığı dışında.")

        result.append(item)
    return result


def write_glyphs(raw: bytearray, meta: dict, rows: list[dict]) -> None:
    base = meta["table_start"]
    for i, row in enumerate(rows):
        entry = bytearray(16)
        struct.pack_into(
            "<HHHH",
            entry,
            0,
            row["codepoint"],
            row["page"],
            row["x"],
            row["y"],
        )
        entry[8] = row["width"]
        entry[9] = row["height"]
        entry[10] = row["byte10"]
        entry[11] = row["byte11"]
        entry[12] = row["byte12"]
        entry[13:16] = row["tail"]
        raw[base + i * 16 : base + (i + 1) * 16] = entry


def visible_glyph(img: Image.Image, row: dict) -> bool:
    if row["width"] <= 0 or row["height"] <= 0:
        return False
    x, y = row["x"], row["y"]
    w, h = row["width"], row["height"]
    if x + w > img.width or y + h > img.height:
        return False
    crop = img.crop((x, y, x + w, y + h))
    extrema = crop.getextrema()
    return bool(extrema and extrema[1] > 0)


def iter_font_files_from_zip(z: zipfile.ZipFile):
    for name in sorted(z.namelist()):
        if not name.endswith("/") and name.lower().endswith(".bfnt.lz"):
            yield name, z.read(name)


def extract_one(name: str, packed: bytes, out_root: Path) -> dict:
    raw = unpack_bfnt_lz(packed)
    meta = parse_meta(raw)
    rows = read_glyphs(raw, meta)

    folder = out_root / Path(name).name.removesuffix(".bfnt.lz")
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "original.bfnt").write_bytes(raw)
    write_glyph_csv(folder / "glyphs.csv", rows)

    for page in range(meta["texture_count"]):
        start = meta["texture_offset"] + page * meta["texture_size"]
        tex = raw[start : start + meta["texture_size"]]
        img = decode_texture(tex, meta["width"], meta["height"], meta["texture_format"])
        img.save(folder / f"page_{page}.png")

    metadata = dict(meta)
    metadata["source_name"] = name
    (folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata


def cmd_extract(args):
    src = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src, "r") as z:
            items = list(iter_font_files_from_zip(z))
            if not items:
                raise FontToolError("ZIP içinde .bfnt.lz bulunamadı.")
            for name, data in items:
                meta = extract_one(name, data, out)
                print(
                    f"[OK] {name}: {meta['glyph_count']} glyph, "
                    f"{meta['texture_count']} atlas, {meta['texture_format']}"
                )
    else:
        meta = extract_one(src.name, src.read_bytes(), out)
        print(
            f"[OK] {src.name}: {meta['glyph_count']} glyph, "
            f"{meta['texture_count']} atlas, {meta['texture_format']}"
        )


def rebuild_one(original_packed: bytes, project_folder: Path) -> bytes:
    raw = bytearray(unpack_bfnt_lz(original_packed))
    meta = parse_meta(raw)

    rows = read_glyph_csv(project_folder / "glyphs.csv", meta["glyph_count"])
    write_glyphs(raw, meta, rows)

    for page in range(meta["texture_count"]):
        png = project_folder / f"page_{page}.png"
        if not png.exists():
            raise FontToolError(f"Eksik PNG: {png}")
        img = Image.open(png)
        tex = encode_texture(img, meta["width"], meta["height"], meta["texture_format"])
        start = meta["texture_offset"] + page * meta["texture_size"]
        raw[start : start + meta["texture_size"]] = tex

    packed = pack_bfnt_lz(bytes(raw))

    # Full round-trip validation.
    check = unpack_bfnt_lz(packed)
    if check != bytes(raw):
        raise FontToolError(f"LZ doğrulaması başarısız: {project_folder.name}")

    return packed


def cmd_inject(args):
    src = Path(args.input)
    project = Path(args.project)
    out = Path(args.output)

    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(
            out, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            font_names = {
                Path(n).name.removesuffix(".bfnt.lz"): n
                for n in zin.namelist()
                if n.lower().endswith(".bfnt.lz")
            }
            rebuilt = set()

            for name in zin.namelist():
                data = zin.read(name)
                if name.lower().endswith(".bfnt.lz"):
                    key = Path(name).name.removesuffix(".bfnt.lz")
                    folder = project / key
                    if folder.is_dir():
                        data = rebuild_one(data, folder)
                        rebuilt.add(key)
                        print(f"[OK] rebuilt {name}")
                zout.writestr(name, data)

            missing = [p.name for p in project.iterdir() if p.is_dir() and p.name not in rebuilt]
            if missing:
                print(
                    "UYARI: Orijinal ZIP'te karşılığı bulunmayan proje klasörleri: "
                    + ", ".join(sorted(missing)),
                    file=sys.stderr,
                )
    else:
        folder = project
        if (project / src.name.removesuffix(".bfnt.lz")).is_dir():
            folder = project / src.name.removesuffix(".bfnt.lz")
        out.write_bytes(rebuild_one(src.read_bytes(), folder))
        print(f"[OK] {out}")


def report_one(name: str, packed: bytes):
    raw = unpack_bfnt_lz(packed)
    meta = parse_meta(raw)
    rows = read_glyphs(raw, meta)

    pages = []
    for page in range(meta["texture_count"]):
        start = meta["texture_offset"] + page * meta["texture_size"]
        pages.append(
            decode_texture(
                raw[start : start + meta["texture_size"]],
                meta["width"],
                meta["height"],
                meta["texture_format"],
            )
        )

    by_cp = {}
    for row in rows:
        by_cp.setdefault(row["codepoint"], row)

    result = []
    for ch in TR_CHARS:
        row = by_cp.get(ord(ch))
        if row is None:
            state = "YOK"
        elif row["page"] >= len(pages):
            state = "HATALI SAYFA"
        elif visible_glyph(pages[row["page"]], row):
            state = "OK"
        else:
            state = "BOŞ/PLACEHOLDER"

        # Catch a common Turkish-font mistake: U+0131 (dotless ı) must not
        # reuse the exact same bitmap as U+0069 (dotted i).
        if ch == "ı" and state == "OK":
            src = by_cp.get(ord("i"))
            if src is not None and src["page"] < len(pages):
                def _glyph_bytes(r):
                    im = pages[r["page"]]
                    return im.crop((r["x"], r["y"], r["x"] + r["width"], r["y"] + r["height"]))
                a = _glyph_bytes(src)
                b = _glyph_bytes(row)
                if a.size == b.size and a.tobytes() == b.tobytes():
                    state = "HATALI: i İLE AYNI BITMAP"

        result.append((ch, f"U+{ord(ch):04X}", state))
    return meta, result


def cmd_report(args):
    src = Path(args.input)
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src, "r") as z:
            for name, data in iter_font_files_from_zip(z):
                meta, result = report_one(name, data)
                print(
                    f"\n{name}  "
                    f"({meta['width']}x{meta['height']}, "
                    f"{meta['texture_format']}, {meta['glyph_count']} glyph)"
                )
                for ch, cp, state in result:
                    print(f"  {ch} {cp}: {state}")
    else:
        meta, result = report_one(src.name, src.read_bytes())
        print(
            f"{src.name} ({meta['width']}x{meta['height']}, "
            f"{meta['texture_format']}, {meta['glyph_count']} glyph)"
        )
        for ch, cp, state in result:
            print(f"  {ch} {cp}: {state}")


def build_parser():
    p = argparse.ArgumentParser(
        description="Fire Emblem Awakening .bfnt.lz font extractor/injector"
    )
    sub = p.add_subparsers(dest="command", required=True)

    ex = sub.add_parser("extract", help="BFNT atlaslarını PNG + glyphs.csv olarak çıkar")
    ex.add_argument("input", help="fonts.zip veya tek .bfnt.lz")
    ex.add_argument("output", help="çıktı proje klasörü")
    ex.set_defaults(func=cmd_extract)

    inj = sub.add_parser("inject", help="PNG + glyphs.csv değişikliklerini BFNT'ye enjekte et")
    inj.add_argument("input", help="orijinal fonts.zip veya tek .bfnt.lz")
    inj.add_argument("project", help="extract ile oluşan proje klasörü")
    inj.add_argument("output", help="çıktı ZIP/.bfnt.lz")
    inj.set_defaults(func=cmd_inject)

    rep = sub.add_parser(
        "turkish-report",
        help="ÇĞİÖŞÜçğıöşü karakterlerinin gerçekten çizilip çizilmediğini kontrol et",
    )
    rep.add_argument("input", help="fonts.zip veya tek .bfnt.lz")
    rep.set_defaults(func=cmd_report)

    return p


def main():
    p = build_parser()
    args = p.parse_args()
    try:
        args.func(args)
    except (FontToolError, OSError, ValueError, csv.Error) as e:
        print(f"HATA: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
