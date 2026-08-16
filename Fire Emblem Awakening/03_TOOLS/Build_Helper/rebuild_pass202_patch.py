#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild Fire Emblem Awakening Turkish Pass202 patch from the included project.
Run from this file's directory or anywhere; defaults resolve relative to the bundle.
"""
from pathlib import Path
import argparse, subprocess, sys, zipfile, shutil

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m", default=str(ROOT / "06_REFERENCE_INPUTS" / "m.zip"))
    ap.add_argument("--project", default=str(ROOT / "02_SOURCE_REVIEW" / "project_with_regenerated_manifest"))
    ap.add_argument("--fonts", default=str(ROOT / "04_FONT_WORK" / "fonts_TR.zip"))
    ap.add_argument("--out", default=str(ROOT / "_rebuilt_output"))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tool = ROOT / "03_TOOLS" / "Language_Tool_V2" / "fea_lang_tool.py"
    full = out / "m_TR_Pass202_full.zip"

    subprocess.check_call([
        sys.executable, str(tool), "inject", args.m, args.project,
        "--target", "U", "--column", "TR", "--fallback", "U",
        "--output", str(full)
    ])
    subprocess.check_call([sys.executable, str(tool), "verify", str(full)])

    romfs = out / "romfs"
    if romfs.exists():
        shutil.rmtree(romfs)
    (romfs / "m" / "U").mkdir(parents=True)
    (romfs / "fonts").mkdir(parents=True)

    with zipfile.ZipFile(full) as z:
        for n in z.namelist():
            if n.startswith("m/U/") and n.endswith(".bin.lz"):
                rel = Path(n).relative_to("m/U")
                dst = romfs / "m" / "U" / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(z.read(n))

    with zipfile.ZipFile(args.fonts) as z:
        for n in z.namelist():
            if n.lower().endswith(".bfnt.lz"):
                (romfs / "fonts" / Path(n).name).write_bytes(z.read(n))

    print("Hazır:", romfs)

if __name__ == "__main__":
    main()
