#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, json, zipfile
from collections import Counter
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import msbt_core as core
import fallblox_tool as ft
from asset_probe import lz11_decompress, darc_entries
from bclim_codec import parse_header

TITLE='00040000000B4F00'
MSBTS=['autumn.msbt','event.msbt','staff.msbt','stage.msbt']
TARGETS={
 'Game_U.lz':['timg/G_PzlOp_USAen.bclim','timg/G_PzlEd_USAen.bclim'],
 'Res_U.lz':['timg/Font_Cong0.bclim','timg/Font_Cong1.bclim'],
}

def sha(b): return hashlib.sha256(b).hexdigest()
def files_by_path(darc:bytes):
    out={}
    for e in darc_entries(darc):
        if not e['isdir']:
            out[e['path']]=darc[e['a']:e['a']+e['b']]
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-zip',type=Path,required=True)
    ap.add_argument('--patch-root',type=Path,required=True,help='Fallblox_TR_Patch directory')
    ap.add_argument('--json',type=Path)
    a=ap.parse_args()
    romfs=a.patch_root/'luma'/'titles'/TITLE/'romfs'
    csvp=a.patch_root/'translation'/'fallblox_tr.csv'
    rows={}
    with csvp.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): rows[(r['file'],r['label'])]=r
    result={'ok':True,'msbt':{},'assets':{}}
    # MSBT text and control verification against package CSV.
    for fname in MSBTS:
        p=romfs/'EURen'/'msg'/fname
        m=core.parse_msbt(p)
        got=[core.raw_to_csv_text(x,m.endian,m.encoding) for x in m.texts_raw]
        problems=[]
        for i,label in enumerate(m.labels_by_index):
            r=rows.get((fname,label))
            if r is None:
                problems.append(label+': missing CSV row'); continue
            expected=r.get('Turkish','') if core.visible_text(r.get('English','')) else r.get('English','')
            if got[i]!=expected: problems.append(label+': patch text differs from CSV')
            if expected and not ft.controls_compatible(r.get('English',''),expected): problems.append(label+': control inventory/structure mismatch')
        result['msbt'][fname]={'sha256':sha(p.read_bytes()),'size':p.stat().st_size,'message_count':len(got),'issues':problems}
        if problems: result['ok']=False
    # Asset structure verification against original Fallblox English archives.
    with zipfile.ZipFile(a.source_zip) as z:
        for lname,targets in TARGETS.items():
            orig_lz=z.read('romfs/EURen/lyt/'+lname)
            patched_lz=(romfs/'EURen'/'lyt'/lname).read_bytes()
            orig=lz11_decompress(orig_lz); patched=lz11_decompress(patched_lz)
            of=files_by_path(orig); pf=files_by_path(patched)
            issues=[]
            if set(of)!=set(pf): issues.append('DARC file list differs')
            changed=[]
            for path in sorted(set(of)&set(pf)):
                if of[path]!=pf[path]: changed.append(path)
                if path not in targets and of[path]!=pf[path]: issues.append('unexpected changed DARC file: '+path)
            tex={}
            for path in targets:
                if path not in of or path not in pf:
                    issues.append('missing target '+path); continue
                oh=parse_header(of[path]); ph=parse_header(pf[path])
                # parse_header tuple contains dimensions/format/data layout; entire nontexture metadata must remain same length/footer.
                same_header=(oh==ph and len(of[path])==len(pf[path]) and of[path][-0x28:]==pf[path][-0x28:])
                
                def _j(v):
                    return v.hex() if isinstance(v,(bytes,bytearray)) else v
                tex[path]={'original_header':[_j(v) for v in oh],'patched_header':[_j(v) for v in ph],'same_metadata':same_header,'size':len(pf[path])}
                if not same_header: issues.append('BCLIM metadata changed: '+path)
            result['assets'][lname]={
                'original_sha256':sha(orig_lz),'patched_sha256':sha(patched_lz),
                'uncompressed_size':len(patched),'changed_files':changed,'expected_changed_files':targets,
                'textures':tex,'issues':issues,
            }
            if issues or sorted(changed)!=sorted(targets): result['ok']=False
    text=json.dumps(result,ensure_ascii=False,indent=2)
    print(text)
    if a.json: a.json.write_text(text,encoding='utf-8')
    raise SystemExit(0 if result['ok'] else 1)
if __name__=='__main__': main()
