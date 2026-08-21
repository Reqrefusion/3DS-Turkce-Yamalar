#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, shutil, subprocess, sys, tempfile
from pathlib import Path

NAMES=['Caption_US.bffnt','UI_Caption_US.bffnt','Common_Sura_B_16.bffnt']

def run(cmd, cwd=None):
    print('\n$ ' + ' '.join(str(x) for x in cmd))
    p=subprocess.run(cmd,cwd=cwd)
    if p.returncode!=0:
        raise SystemExit(p.returncode)

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def verify_manifest(root:Path):
    mf=root/'SHA256SUMS.txt'; bad=[]; count=0
    for line in mf.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        hx, rel=line.split('  ',1); p=root/rel; count+=1
        if not p.exists() or sha256(p)!=hx: bad.append(rel)
    print(f'Checksum files: {count}; mismatches: {len(bad)}')
    if bad:
        for x in bad[:50]: print('BAD:',x)
        raise SystemExit(1)

def main():
    ap=argparse.ArgumentParser(description='Run all technical validations for WarioWare TR Toolkit v2.')
    ap.add_argument('root',nargs='?',type=Path)
    a=ap.parse_args(); root=(a.root or Path(__file__).resolve().parents[1]).resolve()
    tools=root/'tools'; patch_msg=root/'PATCH_READY_TECHNICAL/romfs/Message/EU/EUen'; patch_font=root/'PATCH_READY_TECHNICAL/romfs/Font'
    ref_msg=root/'references/EUen_original'; base_font=root/'references/font_base'; user_font=root/'references/font_user_patch'; csv_root=root/'comparison_csv'

    print('WarioWare TR Toolkit v2 technical verification'); print('Root:',root)
    verify_manifest(root)

    # MSBT: independent structural verifier + direct byte-identical round-trip.
    run([sys.executable,str(tools/'msbt_technical_verify.py'),str(patch_msg),'--reference-root',str(ref_msg)])
    run([sys.executable,str(tools/'msbt_direct_tool.py'),'verify',str(patch_msg)])

    # BFFNT v5: independent parser verifies single CWDH/CMAP, user Turkish preservation, base glyph restoration.
    run([sys.executable,str(tools/'font_v5_independent_verify.py'),str(base_font),str(user_font),str(patch_font),'--report-dir',str(root/'reports/font_v5')])

    # Deterministic font rebuild must be byte-identical to packaged final fonts.
    ftmp=Path(tempfile.mkdtemp(prefix='wario_font_v5_'))
    try:
        run([sys.executable,str(tools/'bffnt_preserve_user_v5.py'),str(base_font),str(user_font),str(ftmp)])
        bad=[]
        for n in NAMES:
            if (ftmp/n).read_bytes()!=(patch_font/n).read_bytes(): bad.append(n)
        print(f'Font deterministic rebuild byte-identical: {len(NAMES)-len(bad)}/{len(NAMES)}')
        if bad:
            print('BAD FONT REBUILDS:',bad); raise SystemExit(1)
    finally:
        shutil.rmtree(ftmp,ignore_errors=True)

    # Untouched multilingual CSVs must inject back to exactly the packaged MSBT baseline.
    tmp=Path(tempfile.mkdtemp(prefix='warioware_batch_verify_'))
    try:
        out=tmp/'msbt'
        run([sys.executable,str(tools/'msbt_batch_inject.py'),str(patch_msg),str(csv_root),str(out),'--column','TR'])
        mism=[]; files=0
        for p in sorted(patch_msg.rglob('*.msbt')):
            rel=p.relative_to(patch_msg); q=out/rel; files+=1
            if not q.exists() or p.read_bytes()!=q.read_bytes(): mism.append(rel.as_posix())
        print(f'CSV reinjection byte-identical: {files-len(mism)}/{files}')
        if mism:
            print('Mismatches:',mism[:50]); raise SystemExit(1)
    finally:
        shutil.rmtree(tmp,ignore_errors=True)

    # No XMSBT/XML in final toolkit path.
    forbidden=[p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.xmsbt','.xml')]
    print(f'Forbidden XMSBT/XML files: {len(forbidden)}')
    if forbidden:
        for p in forbidden[:20]: print('BAD:',p.relative_to(root)); raise SystemExit(1)

    print('\nALL TECHNICAL CHECKS PASSED.')

if __name__=='__main__': main()
