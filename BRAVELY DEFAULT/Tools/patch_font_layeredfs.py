#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, sys, json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bravely_font_tools_v35 import patch_font_archive, verify_font_archive
TIDS={'EUR':'00040000000FC600','USA':'00040000000FC500'}
FONT_PATHS=[Path('Graphics/UI/Font/Font'),Path('Graphics/UI_en/Font/Font')]

def main():
    ap=argparse.ArgumentParser(description='Bravely Default ortak + İngilizce font arşivlerini Türkçe karakterlerle LayeredFS hedefine üretir.')
    ap.add_argument('--source-romfs',required=True,type=Path)
    ap.add_argument('--region',choices=('EUR','USA'),required=True)
    ap.add_argument('--sd-root',required=True,type=Path)
    a=ap.parse_args()
    results={}
    for rel in FONT_PATHS:
        src=a.source_romfs/rel
        if not src.is_file(): raise FileNotFoundError(src)
        patched,info=patch_font_archive(src.read_bytes())
        dst=a.sd_root/'luma'/'titles'/TIDS[a.region]/'romfs'/rel
        dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(patched)
        results[str(rel)]={'destination':str(dst),'verification':verify_font_archive(patched),'patch':info['patched']}
        print('Font yaması hazır:',dst)
    report=a.sd_root/'FONT_PATCH_REPORT_v35.json'
    report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Doğrulama raporu:',report)

if __name__=='__main__': main()
