#!/usr/bin/env python3
"""Verify a built Pullblox Turkish LayeredFS patch against an original game dump.

Checks:
- patched MSBT reparses, labels match original, and every Turkish CSV string matches exactly
- special MSBT control-token sequences match the English source
- LZ11 archives decompress successfully and remain valid DARC archives
- DARC file paths, offsets and sizes are unchanged
- every non-target asset is byte-identical to the original
- target BCLIM geometry, format, payload size and 0x28-byte CLIM footer are unchanged
- target BCLIMs decode at their declared dimensions
"""
from __future__ import annotations
from pathlib import Path
import argparse, csv, hashlib, json, tempfile, zipfile, sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from pullblox_tool import parse_msbt, raw_to_csv_text, control_signature, visible_text
from asset_probe import lz11_decompress, darc_entries
from bclim_codec import parse_header, decode_bclim

TARGETS={
    'Game_U.lz': {'timg/G_PzlOp_USAen.bclim','timg/G_PzlEd_USAen.bclim'},
    'Res_U.lz': {'timg/Font_Cong0.bclim','timg/Font_Cong1.bclim'},
}

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def file_map(darc:bytes):
    return {e['path']:e for e in darc_entries(darc) if not e['isdir'] and e['path']}

def blob(darc:bytes,e): return darc[e['a']:e['a']+e['b']]

def verify_msbt(z:zipfile.ZipFile, patch_root:Path, csv_path:Path):
    original=z.read('romfs/EURen/msg/orca.msbt')
    with tempfile.TemporaryDirectory() as td:
        op=Path(td)/'original.msbt'; op.write_bytes(original)
        om=parse_msbt(op)
    pp=patch_root/'luma/titles/0004000000068F00/romfs/EURen/msg/orca.msbt'
    pm=parse_msbt(pp)
    if pm.labels_by_index != om.labels_by_index:
        raise AssertionError('MSBT label list/order changed')
    src=[raw_to_csv_text(x,om.endian,om.encoding) for x in om.texts_raw]
    got=[raw_to_csv_text(x,pm.endian,pm.encoding) for x in pm.texts_raw]
    rows={}
    with csv_path.open('r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): rows[r['label']]=r
    mismatch=[]; ctl=[]; nonempty=0
    for i,label in enumerate(om.labels_by_index):
        expected=rows[label].get('Turkish','') if label in rows else ''
        if not visible_text(src[i]): expected=src[i]
        if visible_text(src[i]): nonempty+=1
        if got[i] != expected: mismatch.append(label)
        if control_signature(got[i]) != control_signature(src[i]): ctl.append(label)
    if mismatch: raise AssertionError(f'MSBT/CSV text mismatch: {mismatch[:20]}')
    if ctl: raise AssertionError(f'MSBT control-token mismatch: {ctl[:20]}')
    return {
        'entries':len(got), 'source_nonempty':nonempty, 'csv_exact_match':True,
        'control_sequences_match':True, 'sha256':sha(pp.read_bytes()),
        'size':pp.stat().st_size,
    }

def verify_archive(z:zipfile.ZipFile, patch_root:Path, pack:str):
    zname='romfs/EURen/lyt/'+pack
    original_lz=z.read(zname)
    patched_path=patch_root/'luma/titles/0004000000068F00/romfs/EURen/lyt'/pack
    patched_lz=patched_path.read_bytes()
    original=lz11_decompress(original_lz); patched=lz11_decompress(patched_lz)
    om=file_map(original); pm=file_map(patched)
    if set(om)!=set(pm): raise AssertionError(f'{pack}: DARC paths changed')
    target_reports={}; changed=[]
    for path in sorted(om):
        oe,pe=om[path],pm[path]
        if (oe['a'],oe['b']) != (pe['a'],pe['b']):
            raise AssertionError(f'{pack}:{path}: DARC offset/size changed')
        ob,pb=blob(original,oe),blob(patched,pe)
        if path in TARGETS[pack]:
            if ob==pb: raise AssertionError(f'{pack}:{path}: target was not changed')
            oh=parse_header(ob); ph=parse_header(pb)
            if oh[:4] != ph[:4]:
                raise AssertionError(f'{pack}:{path}: width/height/format/data-length changed: {oh[:4]} -> {ph[:4]}')
            if ob[-0x28:] != pb[-0x28:]:
                raise AssertionError(f'{pack}:{path}: CLIM footer/header bytes changed')
            if len(ob)!=len(pb): raise AssertionError(f'{pack}:{path}: BCLIM file length changed')
            img=decode_bclim(pb)
            if img.size != (ph[0],ph[1]): raise AssertionError(f'{pack}:{path}: decode geometry mismatch')
            target_reports[path]={
                'changed':True,'file_size':len(pb),'width':ph[0],'height':ph[1],
                'format':ph[2],'texture_data_length':ph[3],
                'clim_footer_identical':True,'decoded_size':list(img.size),
                'original_sha256':sha(ob),'patched_sha256':sha(pb),
            }
            changed.append(path)
        elif ob != pb:
            raise AssertionError(f'{pack}:{path}: non-target asset changed')
    if set(changed)!=TARGETS[pack]: raise AssertionError(f'{pack}: not all targets changed')
    return {
        'lz11_decompress_ok':True,'darc_parse_ok':True,'same_paths_offsets_sizes':True,
        'non_target_files_byte_identical':True,
        'original_lz_sha256':sha(original_lz),'patched_lz_sha256':sha(patched_lz),
        'original_uncompressed_size':len(original),'patched_uncompressed_size':len(patched),
        'targets':target_reports,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--original-zip',required=True,type=Path)
    ap.add_argument('--patch-root',required=True,type=Path)
    ap.add_argument('--csv',required=True,type=Path)
    ap.add_argument('--json',type=Path)
    a=ap.parse_args()
    with zipfile.ZipFile(a.original_zip) as z:
        rep={'msbt':verify_msbt(z,a.patch_root,a.csv),'assets':{}}
        for p in TARGETS: rep['assets'][p]=verify_archive(z,a.patch_root,p)
    rep['all_static_checks_passed']=True
    text=json.dumps(rep,ensure_ascii=False,indent=2)
    print(text)
    if a.json:
        a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(text,encoding='utf-8')
if __name__=='__main__': main()
