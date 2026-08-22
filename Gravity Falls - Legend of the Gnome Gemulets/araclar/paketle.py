#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
TITLE='000400000014D900'

def run(*a): subprocess.run([sys.executable,*map(str,a)],check=True)
def main():
    ap=argparse.ArgumentParser(description='Gravity Falls 3DS Türkçe LayeredFS paketi oluşturur')
    ap.add_argument('romfs',help='Oyundan çıkarılmış romfs klasörü')
    ap.add_argument('ceviri',help='main.csv ve dialogue.csv bulunan klasör')
    ap.add_argument('cikti',help='Çıktı klasörü')
    a=ap.parse_args();romfs=Path(a.romfs);csvdir=Path(a.ceviri);out=Path(a.cikti)
    req=[romfs/'enginedata/localisation/localisation.loc8',romfs/'bundle_ctr.ipk',romfs/'fulllogic_ctr.ipk',csvdir/'main.csv',csvdir/'dialogue.csv']
    miss=[p for p in req if not p.exists()]
    if miss: raise SystemExit('Eksik dosya(lar):\n'+'\n'.join(map(str,miss)))
    run(HERE/'validate_translation.py',csvdir/'main.csv',csvdir/'dialogue.csv')
    with tempfile.TemporaryDirectory(prefix='gf_tr_build_') as td:
        td=Path(td);loc=td/'localisation.loc8';fonts=td/'fonts'
        run(HERE/'loc8_tool.py','inject-split',romfs/'enginedata/localisation/localisation.loc8',csvdir,loc,'--lang','0','--all-languages')
        run(HERE/'font_workflow.py',romfs/'bundle_ctr.ipk',romfs/'fulllogic_ctr.ipk',fonts)
        root=out/'luma/titles'/TITLE/'romfs';(root/'enginedata/localisation').mkdir(parents=True,exist_ok=True)
        shutil.copy2(loc,root/'enginedata/localisation/localisation.loc8')
        shutil.copy2(fonts/'bundle_ctr.ipk',root/'bundle_ctr.ipk')
        shutil.copy2(fonts/'fulllogic_ctr.ipk',root/'fulllogic_ctr.ipk')
    print('Hazır LayeredFS:',out/'luma')
if __name__=='__main__':main()
