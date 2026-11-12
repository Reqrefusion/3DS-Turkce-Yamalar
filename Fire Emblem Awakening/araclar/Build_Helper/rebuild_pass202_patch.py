#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Fire Emblem Awakening Turkish Pass202 patch from the included project.

The --m input may be:
  * the original m.zip (contains m/F..m/U), or
  * a romfs folder containing m/U (single-language U source is enough), or
  * an m folder containing U.

Outputs:
  000400000009F100/romfs/  (installable Luma title patch, synced by default)

Optional build artifacts are written to a temporary folder by default; use
--out <folder> to keep them. No build artifacts are stored in the repository.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
TOOL = ROOT / "araclar" / "Language_Tool_V2" / "fea_lang_tool.py"
ZIP_DATE_TIME = (2020, 1, 1, 0, 0, 0)


def write_zip_file(z: zipfile.ZipFile, src: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    z.writestr(info, src.read_bytes())


def run(cmd):
    print("+ " + " ".join(str(x) for x in cmd))
    subprocess.check_call([str(x) for x in cmd])


def find_u_root(base: Path) -> Path:
    """Return the folder that directly contains the U language directory."""
    if (base / "U").is_dir():
        return base
    children = [p for p in base.iterdir() if p.is_dir() and (p / "U").is_dir()]
    if len(children) == 1:
        return children[0]
    candidates = sorted({p.parent for p in base.rglob("U") if p.is_dir()})
    if len(candidates) == 1:
        return candidates[0]
    raise SystemExit(f"U dil klasörü tek olarak bulunamadı: {base}")


def copy_u_files(u_root: Path, dest: Path) -> int:
    count = 0
    for src in sorted((u_root / "U").rglob("*.bin.lz")):
        rel = src.relative_to(u_root / "U")
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    return count


def iter_fonts(path: Path):
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if not name.endswith("/") and name.lower().endswith(".bfnt.lz"):
                    yield Path(name).name, z.read(name)
        return
    if path.is_dir():
        for p in sorted(path.rglob("*.bfnt.lz")):
            yield p.name, p.read_bytes()
        return
    raise SystemExit(f"Font kaynağı ZIP veya klasör değil: {path}")


def sync_tree(src: Path, dst: Path) -> int:
    """Copy src files over dst in place, preserving existing tracked files."""
    src = src.resolve()
    dst = dst.resolve()
    if src == dst:
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        target = dst / p.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        count += 1
    src_files = {p.relative_to(src).as_posix(): p for p in src.rglob("*") if p.is_file()}
    dst_files = {p.relative_to(dst).as_posix(): p for p in dst.rglob("*") if p.is_file()}
    if set(src_files) != set(dst_files):
        raise SystemExit(f"Yama klasörü dosya listesi eşleşmiyor: {dst}")
    for rel, p in src_files.items():
        if p.read_bytes() != dst_files[rel].read_bytes():
            raise SystemExit(f"Yama klasörü kopya doğrulaması başarısız: {rel}")
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", default=str(ROOT / "06_REFERENCE_INPUTS" / "m.zip"),
                    help="Orijinal m.zip veya U dil klasörünü içeren romfs/m klasörü")
    ap.add_argument("--project", default=str(ROOT / "ceviri" / "project_normalized_with_manifest"))
    ap.add_argument("--fonts", default=str(ROOT / "varliklar" / "fontlar"),
                    help="Font klasörü veya ZIP (varsayılan: varliklar/fontlar)")
    ap.add_argument("--out", default=None,
                    help="Ara çıktı klasörü (varsayılan: sistem geçici klasörü)")
    ap.add_argument("--title-id", default="000400000009F100")
    ap.add_argument("--patch-dir", default=None,
                    help="Kurulabilir Title ID romfs klasörü (varsayılan: <oyun>/<title-id>/romfs)")
    ap.add_argument("--no-install", action="store_true",
                    help="Kurulabilir yama klasörüne senkronizasyon yapma")
    args = ap.parse_args()

    m_path = Path(args.m)
    fonts_path = Path(args.fonts)
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="fea_pass202_"))
    out.mkdir(parents=True, exist_ok=True)

    if not m_path.exists():
        raise SystemExit(f"Kaynak bulunamadı: {m_path}")

    full_zip = out / "m_TR_Pass202_full.zip"
    full_dir = out / "m_TR_Pass202_full"

    if m_path.is_file() and zipfile.is_zipfile(m_path):
        run([sys.executable, TOOL, "inject", m_path, args.project,
             "--target", "U", "--column", "TR", "--fallback", "U",
             "--output", full_zip])
        run([sys.executable, TOOL, "verify", full_zip, "--langs", "U"])
        with zipfile.ZipFile(full_zip) as z:
            names = [n for n in z.namelist() if n.endswith(".bin.lz") and "/U/" in n]
            prefix = None
            for n in names:
                if n.endswith("/U") or "/U/" in n:
                    prefix = n.split("/U/")[0]
                    break
            if prefix is None:
                raise SystemExit("m_TR_Pass202_full.zip içinde U klasörü bulunamadı.")
    else:
        run([sys.executable, TOOL, "inject", m_path, args.project,
             "--target", "U", "--column", "TR", "--fallback", "U",
             "--output", full_dir])
        run([sys.executable, TOOL, "verify", full_dir, "--langs", "U"])
        u_root = find_u_root(full_dir)

    romfs = out / "romfs"
    if romfs.exists():
        shutil.rmtree(romfs)
    (romfs / "m" / "U").mkdir(parents=True)
    (romfs / "fonts").mkdir(parents=True)

    if m_path.is_file() and zipfile.is_zipfile(m_path):
        with zipfile.ZipFile(full_zip) as z:
            count = 0
            for n in z.namelist():
                if not n.startswith(prefix + "/U/") or not n.endswith(".bin.lz"):
                    continue
                rel = Path(n).relative_to(prefix + "/U")
                dst = romfs / "m" / "U" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(z.read(n))
                count += 1
    else:
        count = copy_u_files(u_root, romfs / "m" / "U")

    font_count = 0
    for name, data in iter_fonts(fonts_path):
        (romfs / "fonts" / name).write_bytes(data)
        font_count += 1

    if not (m_path.is_file() and zipfile.is_zipfile(m_path)):
        if full_zip.exists():
            full_zip.unlink()
        with zipfile.ZipFile(full_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in sorted((romfs / "m").rglob("*.bin.lz")):
                write_zip_file(z, p, p.relative_to(romfs).as_posix())
        run([sys.executable, TOOL, "verify", full_zip, "--langs", "U"])

    patch_dir = Path(args.patch_dir) if args.patch_dir else ROOT / args.title_id / "romfs"
    installed = 0
    if not args.no_install:
        installed = sync_tree(romfs, patch_dir)
        run([sys.executable, TOOL, "verify", patch_dir, "--langs", "U"])

    luma_zip = out / "FEA_TR_Pass202_Luma.zip"
    if luma_zip.exists():
        luma_zip.unlink()
    with zipfile.ZipFile(luma_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(romfs.rglob("*")):
            if p.is_file():
                arc = f"{args.title_id}/romfs/{p.relative_to(romfs).as_posix()}"
                write_zip_file(z, p, arc)

    print(f"Hazır: {romfs}  ({count} metin dosyası, {font_count} font)")
    if not args.no_install:
        print(f"Yama konumu: {patch_dir}  ({installed} dosya senkronize edildi)")
    print(f"Ara çıktılar: {out}")
    print(f"m arşivi: {full_zip}  ({full_zip.stat().st_size} bayt)")
    print(f"Luma ZIP: {luma_zip}  ({luma_zip.stat().st_size} bayt)")


if __name__ == "__main__":
    main()
