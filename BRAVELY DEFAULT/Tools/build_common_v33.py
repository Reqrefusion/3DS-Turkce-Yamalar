#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, shutil, sys, os, struct, re, collections

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from repack_bravely import parse_biff, resolve_sheet_target, btbf_meta, text_layout, sheet_matrix, read_utf16z, repack_btbf_from_sheet, rebuild_crowd_index
from translations_tr import UI_TRANSLATIONS, translate_location
from message_supplemental_tr import MESSAGE_SUPPLEMENTAL
from message_deep_tr import MESSAGE_DEEP
from eventviewer_v33_tr import EVENT_VIEWER_TR
from shop_v33_tr import SHOP_TR
from parameter_v33_tr import translate_parameter_text
from misc_v33_tr import STRUCTURED_TR, MESSAGE_V33_TR

SRC=Path(os.environ.get('BD_COMMON_SRC',str(HERE/'input/Common_en')))
WORK=Path(os.environ.get('BD_COMMON_WORK',str(HERE/'output/Common_en_rebuilt_v33')))
GAME=Path(os.environ.get('BD_COMMON_GAME_OUT',str(HERE/'output/Common_en_gamefiles_v33/Common_en')))
REPORT=Path(os.environ.get('BD_COMMON_AUDIT',str(HERE/'COMMON_EN_AUDIT_v33.json')))
COMMON=json.loads((HERE/'common_tr_dict.json').read_text(encoding='utf-8'))

COMBINED={}
COMBINED.update(UI_TRANSLATIONS)
COMBINED.update(COMMON)
COMBINED.update(MESSAGE_SUPPLEMENTAL)
COMBINED.update(MESSAGE_DEEP)
COMBINED.update(STRUCTURED_TR)
COMBINED.update(MESSAGE_V33_TR)

SAFE_TOP={'Paramater','MessageTable','Shop','Battle','MenuTable','ShipTable','PartyChat'}

if WORK.exists(): shutil.rmtree(WORK)
shutil.copytree(SRC,WORK)

stats={
 'version':'common_v3.3', 'sheets':0, 'files_rebuilt':0, 'text_changes_total':0,
 'archives_rebuilt':0, 'runtime_file_count':0,
 'v33_eventviewer_overrides':0, 'v33_shop_fills':0, 'v33_parameter_description_fills':0,
 'v33_structured_fills':0, 'v33_legacy_message_fills':0, 'v33_location_fills':0,
 'v32_consistency_fills':0, 'forced_overrides':[], 'new_by_sheet':{},
 'remaining_identical_by_sheet':{}, 'remaining_identical_samples':{},
 'notes':[
  'User Common_en remains terminology authority; existing translated cells are preserved except curated EventViewer quality fixes.',
  'EventViewer source-keyed overrides repair mixed Turkish/English titles created by earlier partial word substitutions.',
  'Parameter v3.3 rules only fill cells still identical to original source; user-authored translations are not overwritten.',
  'Legacy Japanese system/network strings are translated conservatively when exact source is known.',
 ]
}

for xp in sorted(SRC.rglob('*.xls')):
    if xp.name.lower()=='crowd_en.xls': continue
    top=xp.relative_to(SRC).parts[0]
    wb=parse_biff(xp)
    for sh,cells in wb.items():
        stats['sheets']+=1
        target=resolve_sheet_target(xp,sh)
        if target is None: raise FileNotFoundError(f'no target for {xp}::{sh}')
        mat=sheet_matrix(cells); b=target.read_bytes(); meta=btbf_meta(b)
        v_text,p_text,vcount=text_layout(mat,meta)
        oldblock=b[meta['text_start']:meta['text_start']+meta['text_size']]
        if top in SAFE_TOP:
            for r in range(1,len(mat)):
                for vc,pc in zip(v_text,p_text):
                    fidx=pc-vcount
                    ptr=struct.unpack_from('<I',b,0x30+(r-1)*meta['record_size']+4*fidx)[0]
                    old=read_utf16z(oldblock,ptr) or ''
                    if not old: continue
                    cur=cells.get((r,vc),'')
                    if not isinstance(cur,str): cur=str(cur)
                    tr=None; reason=None; force=False

                    # Event viewer: source-keyed curation intentionally replaces bad partial translations.
                    if top=='MenuTable' and sh=='EventViewer.mtb' and old in EVENT_VIEWER_TR:
                        tr=EVENT_VIEWER_TR[old]; reason='eventviewer'; force=True
                    elif cur==old:
                        if top=='Shop' and old in SHOP_TR:
                            tr=SHOP_TR[old]; reason='shop'
                        elif top=='Paramater':
                            tr=translate_parameter_text(old)
                            if tr: reason='parameter'
                            elif old in STRUCTURED_TR:
                                tr=STRUCTURED_TR[old]; reason='structured'
                        elif top=='MessageTable' and old in MESSAGE_V33_TR:
                            tr=MESSAGE_V33_TR[old]; reason='legacy_message'
                        elif top=='MenuTable' and old in STRUCTURED_TR:
                            tr=STRUCTURED_TR[old]; reason='structured'
                        elif top=='Battle' and old in STRUCTURED_TR:
                            tr=STRUCTURED_TR[old]; reason='structured'
                        elif top=='PartyChat' and old in STRUCTURED_TR:
                            tr=STRUCTURED_TR[old]; reason='structured'
                        elif top=='ShipTable':
                            tr=translate_location(old)
                            if tr: reason='location'
                        if not tr:
                            tr=COMBINED.get(old)
                            if tr and tr!=old: reason='v32_consistency'
                    if not isinstance(tr,str) or not tr or tr==cur: continue
                    if not force and cur!=old: continue
                    cells[(r,vc)]=tr
                    key=f'{top}/{sh}'
                    stats['new_by_sheet'][key]=stats['new_by_sheet'].get(key,0)+1
                    if reason=='eventviewer':
                        stats['v33_eventviewer_overrides']+=1
                        if cur!=old: stats['forced_overrides'].append({'sheet':key,'row':r,'source':old,'before':cur,'after':tr})
                    elif reason=='shop': stats['v33_shop_fills']+=1
                    elif reason=='parameter': stats['v33_parameter_description_fills']+=1
                    elif reason=='structured': stats['v33_structured_fills']+=1
                    elif reason=='legacy_message': stats['v33_legacy_message_fills']+=1
                    elif reason=='location': stats['v33_location_fills']+=1
                    elif reason=='v32_consistency': stats['v32_consistency_fills']+=1

        rel=target.relative_to(SRC); out=WORK/rel
        res=repack_btbf_from_sheet(cells,target,out)
        if res['changed']:
            stats['files_rebuilt']+=1; stats['text_changes_total']+=res['text_changes']

# Rebuild packed Common_en archives.
for idx in sorted(SRC.rglob('index.fs')):
    folder=idx.parent; rel=folder.relative_to(SRC); outfolder=WORK/rel
    rebuild_crowd_index(folder,outfolder); stats['archives_rebuilt']+=1

# Minimal runtime tree.
if GAME.parent.exists(): shutil.rmtree(GAME.parent)
GAME.mkdir(parents=True)
RUNTIME_EXT={'.btb','.tbl','.txb','.subtitles','.spb','.trb','.mtb'}
for folder in sorted([p for p in WORK.rglob('*') if p.is_dir()]):
    rel=folder.relative_to(WORK)
    if (folder/'crowd.fs').is_file() and (folder/'index.fs').is_file():
        dst=GAME/rel; dst.mkdir(parents=True,exist_ok=True)
        shutil.copy2(folder/'crowd.fs',dst/'crowd.fs'); shutil.copy2(folder/'index.fs',dst/'index.fs')
for p in sorted(WORK.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in RUNTIME_EXT: continue
    rel=p.relative_to(WORK)
    if (p.parent/'crowd.fs').is_file() and (p.parent/'index.fs').is_file(): continue
    dst=GAME/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst)
stats['runtime_file_count']=sum(1 for p in GAME.rglob('*') if p.is_file())

# Residual equality audit: original text == rebuilt text means no translation has changed that field.
# This is an audit signal, not automatically an error (proper names/codes/test strings are expected).
rem=collections.Counter(); samples=collections.defaultdict(list)
for xp in sorted(SRC.rglob('*.xls')):
    if xp.name.lower()=='crowd_en.xls': continue
    wb=parse_biff(xp)
    for sh,cells in wb.items():
        target=resolve_sheet_target(xp,sh)
        if target is None: continue
        rebuilt=WORK/target.relative_to(SRC)
        if not rebuilt.is_file(): continue
        mat=sheet_matrix(cells); bo=target.read_bytes(); bn=rebuilt.read_bytes(); mo=btbf_meta(bo); mn=btbf_meta(bn)
        vt,pt,vc=text_layout(mat,mo); blo=bo[mo['text_start']:mo['text_start']+mo['text_size']]; bln=bn[mn['text_start']:mn['text_start']+mn['text_size']]
        top=xp.relative_to(SRC).parts[0]; key=f'{top}/{sh}'
        for r in range(1,len(mat)):
            for v,p in zip(vt,pt):
                fi=p-vc
                po=struct.unpack_from('<I',bo,0x30+(r-1)*mo['record_size']+4*fi)[0]
                pn=struct.unpack_from('<I',bn,0x30+(r-1)*mn['record_size']+4*fi)[0]
                old=read_utf16z(blo,po) or ''; new=read_utf16z(bln,pn) or ''
                if old and old==new and any(ch.isalpha() for ch in old):
                    rem[key]+=1
                    if len(samples[key])<12: samples[key].append({'row':r,'text':old})
stats['remaining_identical_by_sheet']=dict(sorted(rem.items(),key=lambda kv:(-kv[1],kv[0])))
stats['remaining_identical_samples']=dict(samples)

REPORT.write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in stats.items() if k not in ('forced_overrides','remaining_identical_samples')},ensure_ascii=False,indent=2))
