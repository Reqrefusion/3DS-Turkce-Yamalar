#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, shutil, sys, tempfile
from pathlib import Path

def load_tool(here: Path):
    p=here/'acnl_script_tool.py'
    spec=importlib.util.spec_from_file_location('acnl_script_tool_local',p)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod

def main():
    ap=argparse.ArgumentParser(description='ACNL Türkçe romfs yamasını yeniden oluştur')
    ap.add_argument('--script',type=Path,required=True,help='Orijinal ROMFS/Script klasörü')
    ap.add_argument('--translations',type=Path,required=True,help='TRANSLATIONS_TR_FINAL klasörü')
    ap.add_argument('--font',type=Path,required=True,help='Orijinal ROMFS/Font klasörü')
    ap.add_argument('--out',type=Path,required=True,help='Çıktı patch klasörü')
    ap.add_argument('--target',default='EN')
    args=ap.parse_args()
    here=Path(__file__).resolve().parent; tool=load_tool(here)
    tool.validate_csv(args.script,args.translations,args.target,'TRANSLATION','cp1252')
    with tempfile.TemporaryDirectory(prefix='acnl_tr_') as td:
        injected=Path(td)/'Script_TR'
        tool.inject(args.script,args.translations,injected,args.target,'TRANSLATION','cp1252')
        if args.out.exists(): shutil.rmtree(args.out)
        sdst=args.out/'romfs'/'Script'; fdst=args.out/'romfs'/'Font'
        changed=0
        for f in injected.rglob('*.umsbt'):
            rel=f.relative_to(injected); original=args.script/rel
            if not original.is_file() or f.read_bytes()!=original.read_bytes():
                d=sdst/rel; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,d); changed+=1
        shutil.copytree(args.font,fdst)
        print(f'OK: {changed} değiştirilmiş UMSBT + Font klasörü -> {args.out}/romfs')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
