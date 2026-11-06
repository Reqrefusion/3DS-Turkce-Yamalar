#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""New Art Academy (3DS) Turkish CFNA font analyzer/patcher.

The two main game fonts already contain native Turkish glyphs.  The legacy
STB 1.0 table is single-byte, so six Turkish-only letters cannot be encoded
there.  This tool repoints six unused Western-European code points to the
existing Turkish glyph indices without touching the glyph textures.

Legacy byte/codepoint aliases used by naa_localizer.py:
    Ð -> Ğ   ð -> ğ   Ý -> İ   ÿ -> ı   Þ -> Ş   þ -> ş

This keeps the CFNA size/layout unchanged and only edits CMAP table entries.
"""
from __future__ import annotations

import argparse
import struct
import sys
import zipfile
from pathlib import Path, PurePosixPath

TURKISH = "ÇçĞğİıÖöŞşÜü"
ALIASES = {
    "Ð": "Ğ",
    "ð": "ğ",
    "Ý": "İ",
    "ÿ": "ı",
    "Þ": "Ş",
    "þ": "ş",
}
MAIN_FONTS = ["fonts/chelseyFont.bcfna", "fonts/dfhsGothic.bcfna"]
OPTIONAL_FONTS = ["fonts/eshop.bcfna"]


def u16(b: bytes | bytearray, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def u32(b: bytes | bytearray, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


class CFNAError(Exception):
    pass


class SourceFS:
    def __init__(self, source: str | Path):
        self.path = Path(source)
        self.z: zipfile.ZipFile | None = None
        if self.path.is_file() and self.path.suffix.lower() == ".zip":
            self.z = zipfile.ZipFile(self.path, "r")
        elif not self.path.is_dir():
            raise FileNotFoundError(f"Kaynak bulunamadı: {self.path}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.z:
            self.z.close()

    def names(self) -> set[str]:
        if self.z:
            return {n for n in self.z.namelist() if not n.endswith("/")}
        return {p.relative_to(self.path).as_posix() for p in self.path.rglob("*") if p.is_file()}

    def read(self, rel: str) -> bytes:
        rel = PurePosixPath(rel).as_posix()
        if self.z:
            return self.z.read(rel)
        return (self.path / Path(rel)).read_bytes()


class CFNAFont:
    def __init__(self, raw: bytes, path: str = ""):
        self.raw = bytearray(raw)
        self.path = path
        if len(raw) < 40 or raw[:4] != b"CFNA":
            raise CFNAError(f"{path}: CFNA başlığı yok")
        self.finf = raw.find(b"FINF")
        if self.finf < 0:
            raise CFNAError(f"{path}: FINF bölümü yok")
        if self.finf + 28 > len(raw):
            raise CFNAError(f"{path}: FINF bölümü bozuk")
        cmap_ptr = u32(raw, self.finf + 24)
        if cmap_ptr < 8:
            raise CFNAError(f"{path}: CMAP işaretçisi geçersiz")
        self.first_cmap = cmap_ptr - 8
        self.mapping: dict[int, int] = {}
        self.locations: dict[int, tuple[str, int, int]] = {}
        self._parse_cmaps()

    def _parse_cmaps(self):
        off = self.first_cmap
        seen = set()
        while off and off not in seen:
            seen.add(off)
            if off + 20 > len(self.raw) or self.raw[off:off+4] != b"CMAP":
                raise CFNAError(f"{self.path}: CMAP zinciri bozuk (0x{off:X})")
            begin, end, method, _reserved = struct.unpack_from("<HHHH", self.raw, off + 8)
            next_ptr = u32(self.raw, off + 16)
            pos = off + 20
            if method == 0:  # direct
                base = u16(self.raw, pos)
                for cp in range(begin, end + 1):
                    self.mapping[cp] = base + (cp - begin)
                    self.locations[cp] = ("direct", pos, off)
            elif method == 1:  # table
                need = pos + (end - begin + 1) * 2
                if need > len(self.raw):
                    raise CFNAError(f"{self.path}: CMAP tablo sınırı bozuk")
                for i, cp in enumerate(range(begin, end + 1)):
                    loc = pos + i * 2
                    idx = u16(self.raw, loc)
                    if idx != 0xFFFF:
                        self.mapping[cp] = idx
                    self.locations[cp] = ("table", loc, off)
            elif method == 2:  # scan
                count = u16(self.raw, pos)
                pos += 2
                if pos + count * 4 > len(self.raw):
                    raise CFNAError(f"{self.path}: CMAP scan sınırı bozuk")
                for i in range(count):
                    cp, idx = struct.unpack_from("<HH", self.raw, pos + i * 4)
                    self.mapping[cp] = idx
                    self.locations[cp] = ("scan", pos + i * 4 + 2, off)
            else:
                raise CFNAError(f"{self.path}: desteklenmeyen CMAP yöntemi {method}")
            off = next_ptr - 8 if next_ptr else 0

    def glyph(self, ch: str) -> int | None:
        return self.mapping.get(ord(ch))

    def coverage(self) -> dict[str, int | None]:
        return {ch: self.glyph(ch) for ch in TURKISH}

    def patch_legacy_aliases(self) -> list[str]:
        notes = []
        for alias, target in ALIASES.items():
            target_idx = self.glyph(target)
            if target_idx is None:
                raise CFNAError(f"{self.path}: hedef Türkçe glifi yok: {target} U+{ord(target):04X}")
            loc_info = self.locations.get(ord(alias))
            if not loc_info:
                raise CFNAError(f"{self.path}: eşleme kod noktası yok: {alias} U+{ord(alias):04X}")
            method, loc, _section = loc_info
            if method not in {"table", "scan"}:
                raise CFNAError(
                    f"{self.path}: {alias} doğrudan CMAP içinde; dosya boyutunu değiştirmeden tekil yama yapılamıyor"
                )
            old_idx = u16(self.raw, loc)
            struct.pack_into("<H", self.raw, loc, target_idx)
            self.mapping[ord(alias)] = target_idx
            notes.append(
                f"{alias} U+{ord(alias):04X}: glyph {old_idx} -> {target_idx} ({target} U+{ord(target):04X})"
            )
        return notes

    def bytes(self) -> bytes:
        return bytes(self.raw)


def analyze_bytes(raw: bytes, path: str) -> list[str]:
    f = CFNAFont(raw, path)
    lines = [f"[{path}]", f"Boyut: {len(raw)} bayt", f"CMAP karakter sayısı: {len(f.mapping)}"]
    cov = f.coverage()
    missing = [ch for ch, idx in cov.items() if idx is None]
    lines.append("Türkçe glifler: " + ("TAM (12/12)" if not missing else f"EKSİK ({12-len(missing)}/12)"))
    for ch in TURKISH:
        idx = cov[ch]
        lines.append(f"  {ch} U+{ord(ch):04X}: " + (f"glyph {idx}" if idx is not None else "YOK"))
    if path in MAIN_FONTS:
        lines.append("Legacy STB1.0 alias hedefleri:")
        for a, t in ALIASES.items():
            lines.append(f"  {a} -> {t}: alias glyph={f.glyph(a)}, hedef glyph={f.glyph(t)}")
    return lines


def patch_font_bytes(raw: bytes, path: str) -> tuple[bytes, list[str]]:
    f = CFNAFont(raw, path)
    notes = f.patch_legacy_aliases()
    patched = f.bytes()
    if len(patched) != len(raw):
        raise CFNAError(f"{path}: yama dosya boyutunu değiştirdi")
    # Reparse and verify every alias points to the target Turkish glyph.
    v = CFNAFont(patched, path)
    for alias, target in ALIASES.items():
        if v.glyph(alias) != v.glyph(target):
            raise CFNAError(f"{path}: doğrulama başarısız: {alias}->{target}")
    return patched, notes


def build_font_patch_from_reader(read_func, names: set[str], out_root: Path) -> tuple[int, list[str]]:
    notes: list[str] = []
    count = 0
    for rel in MAIN_FONTS:
        if rel not in names:
            raise CFNAError(f"Kaynakta gerekli font yok: {rel}")
        patched, n = patch_font_bytes(read_func(rel), rel)
        dest = out_root / Path(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(patched)
        count += 1
        notes.append(f"{rel}: Türkçe legacy alias yaması uygulandı")
        notes.extend("  " + x for x in n)
    return count, notes


def cmd_analyze(args):
    with SourceFS(args.source) as src:
        names = src.names()
        all_lines = []
        for rel in MAIN_FONTS + OPTIONAL_FONTS:
            if rel in names:
                all_lines.extend(analyze_bytes(src.read(rel), rel))
                all_lines.append("")
    text = "\n".join(all_lines).rstrip() + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"OK: font raporu -> {args.out}")
    else:
        print(text, end="")


def cmd_patch(args):
    out = Path(args.out)
    with SourceFS(args.source) as src:
        count, notes = build_font_patch_from_reader(src.read, src.names(), out)
    report = out / "_turkish_font_patch.txt"
    report.write_text(
        "New Art Academy Türkçe font yaması\n"
        "==================================\n"
        "Bu yama mevcut Türkçe glifleri kullanır; bitmap/glyph texture yeniden çizilmez.\n"
        "STB1.0 için: Ð→Ğ, ð→ğ, Ý→İ, ÿ→ı, Þ→Ş, þ→ş\n\n" + "\n".join(notes) + "\n",
        encoding="utf-8",
    )
    print(f"OK: {count} ana font Türkçe legacy eşleme ile yamalandı -> {out}")


def make_parser():
    p = argparse.ArgumentParser(description="New Art Academy 3DS CFNA Türkçe font aracı")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze", help="CFNA fontların Türkçe karakter kapsamını raporla")
    a.add_argument("source", help="RomFS klasörü veya romfs.zip")
    a.add_argument("--out", help="raporu UTF-8 metin dosyasına yaz")
    a.set_defaults(func=cmd_analyze)
    q = sub.add_parser("patch", help="ana fontlarda STB1.0 Türkçe alias CMAP yaması üret")
    q.add_argument("source", help="RomFS klasörü veya romfs.zip")
    q.add_argument("--out", default="font_patch_romfs", help="çıktı RomFS yama klasörü")
    q.set_defaults(func=cmd_patch)
    return p


def main():
    args = make_parser().parse_args()
    try:
        args.func(args)
    except (OSError, zipfile.BadZipFile, CFNAError, KeyError) as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
