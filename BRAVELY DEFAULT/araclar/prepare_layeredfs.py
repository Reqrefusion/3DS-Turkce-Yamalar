#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, shutil, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bravely_ui_tools import DarcArchive, patch_cfnt_turkish

TIDS={'EUR':'00040000000FC600','USA':'00040000000FC500'}

def patch_font(src:Path,dst:Path):
    raw=src.read_bytes(); arc=DarcArchive(raw); repl={}; info=None
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,info=patch_cfnt_turkish(b); repl[ip]=nb; break
    if not repl: raise RuntimeError('Font DARC içinde CFNT bulunamadı: '+str(src))
    dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(arc.rebuild(repl))
    return info

def main():
    ap=argparse.ArgumentParser(description='Bravely Default TR v3.3 LayeredFS ağacını hazırlar ve fontu kendi dumpınızdan yamalar.')
    ap.add_argument('--source-romfs',required=True,type=Path,help='Orijinal oyundan çıkarılmış romfs kökü')
    ap.add_argument('--region',choices=sorted(TIDS),required=True)
    ap.add_argument('--output',required=True,type=Path,help='SD kart kökü veya hazırlanacak boş klasör')
    ap.add_argument('--patch-romfs',type=Path,default=HERE.parent/'romfs',help='Bu progress paketindeki patch romfs')
    args=ap.parse_args()
    target=args.output/'luma'/'titles'/TIDS[args.region]/'romfs'
    target.mkdir(parents=True,exist_ok=True)
    shutil.copytree(args.patch_romfs,target,dirs_exist_ok=True)
    srcfont=args.source_romfs/'Graphics'/'UI_en'/'Font'/'Font'
    if not srcfont.is_file(): raise FileNotFoundError('Orijinal font bulunamadı: '+str(srcfont))
    outfont=target/'Graphics'/'UI_en'/'Font'/'Font'
    info=patch_font(srcfont,outfont)
    print('Hazır:',target)
    print('Türkçe font:',outfont)
    print('Glyph bilgisi:',info)
if __name__=='__main__': main()
