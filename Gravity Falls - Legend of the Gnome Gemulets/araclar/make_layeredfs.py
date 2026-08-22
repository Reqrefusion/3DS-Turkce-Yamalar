#!/usr/bin/env python3
"""Create a Luma3DS LayeredFS patch tree for Gravity Falls CTR-P-AGFP."""
from __future__ import annotations
import argparse, shutil
from pathlib import Path
TITLE_ID = "000400000014D900"

def copy(src: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(dst)

def main():
    ap=argparse.ArgumentParser(description=f"Build luma/titles/{TITLE_ID}/romfs patch tree")
    ap.add_argument("output_root", help="Folder where luma/titles/... will be created")
    ap.add_argument("--loc8", help="Patched localisation.loc8")
    ap.add_argument("--bundle", help="Patched bundle_ctr.ipk")
    ap.add_argument("--fulllogic", help="Patched fulllogic_ctr.ipk")
    a=ap.parse_args()
    root=Path(a.output_root)/"luma"/"titles"/TITLE_ID/"romfs"
    if a.loc8:
        copy(a.loc8, root/"enginedata"/"localisation"/"localisation.loc8")
    if a.bundle:
        copy(a.bundle, root/"bundle_ctr.ipk")
    if a.fulllogic:
        copy(a.fulllogic, root/"fulllogic_ctr.ipk")
    if not a.loc8 and not a.bundle and not a.fulllogic:
        root.mkdir(parents=True,exist_ok=True); print(root)
if __name__=="__main__": main()
