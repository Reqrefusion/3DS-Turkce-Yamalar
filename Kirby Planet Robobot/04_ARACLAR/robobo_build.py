#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, shutil, sys, importlib.util

TITLE_ID='0004000000183600'

def load_module(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def main():
    ap=argparse.ArgumentParser(description='Kirby Planet Robobot TR CSV -> MSBT + fontlu ROMFS/Luma build')
    ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    a=ap.parse_args(); root=Path(a.root).resolve()
    csv_dir=root/'01_CEVIRI/MSBT_CSV'; msg_root=root/'02_KAYNAK/ORIJINAL_MSG'; fonts=root/'03_FONTLAR/TR_PATCHED_CMP'
    out=root/'BUILD_OUTPUT'
    if out.exists(): shutil.rmtree(out)
    romfs=out/'ROMFS_ONLY/romfs'; msgout=romfs/'msg'; fontout=romfs/'font'
    msgout.mkdir(parents=True,exist_ok=True); fontout.mkdir(parents=True,exist_ok=True)
    msbt=load_module(root/'04_ARACLAR/kirby_msbt_tool.py','robobo_msbt_build')
    scale_guard=load_module(root/'04_ARACLAR/robobo_scale_guard.py','robobo_scale_guard_build')
    # Güvenlik kuralı: bir satırda ölçek/küçültme komutu yalnız aynı kaydın resmî dillerinden
    # en az birinde kullanılıyorsa Türkçede kalabilir. Böylece belirli UI renderer'larında
    # hiç desteklenmeyen bir kontrol komutu sonradan eklenmez.
    scale_guard.guard_csv_dir(csv_dir, root/'05_RAPORLAR/BUILD_OLCEK_KODU_KONTROLU.csv', apply=True)
    # Structural malformed-token repair is idempotent; keeps edited CSV safe if a damaged source token remains.
    msbt.repair_malformed_tokens(csv_dir,'TR_Turkish',root/'05_RAPORLAR/BUILD_SON_TOKEN_ONARIMI.csv')
    msbt.inject_csvs(msg_root,csv_dir,msgout,'EU_English','TR_Turkish','keep','EU_English')
    shutil.copytree(fonts,fontout,dirs_exist_ok=True)
    # Luma SD tree, using title id present in the user's original patch.
    sdromfs=out/'SD_ROOT/luma/titles'/TITLE_ID/'romfs'
    shutil.copytree(romfs,sdromfs,dirs_exist_ok=True)
    print(f'Build hazır: {out}')
    print(f'ROMFS: {romfs}')
    print(f'Luma:  {sdromfs}')
if __name__=='__main__': main()
