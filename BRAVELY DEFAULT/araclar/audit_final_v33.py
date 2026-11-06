#!/usr/bin/env python3
from pathlib import Path
import sys, json, hashlib, struct, re
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from repack_bravely import parse_index, btbf_meta
from bravely_ui_tools import DarcArchive, cfnt_char_map

ROOT=Path(sys.argv[1])
ROMFS=ROOT/'romfs'
report={'version':'v3.3','errors':[],'warnings':[],'archive_pairs':0,'archive_entries':0,'darc_entries_validated':0,'btbf_entries_validated':0,'font':{},'romfs_file_count':0,'unexpected_source_files':[],'sha256':[]}

# Validate every crowd/index pair in the final patch.
for idx in sorted(ROMFS.rglob('index.fs')):
    crowd=idx.with_name('crowd.fs')
    if not crowd.is_file():
        report['errors'].append({'path':str(idx.relative_to(ROMFS)),'error':'missing crowd.fs'}); continue
    try: ents=parse_index(idx.read_bytes())
    except Exception as e:
        report['errors'].append({'path':str(idx.relative_to(ROMFS)),'error':'index parse','detail':str(e)}); continue
    cb=crowd.read_bytes(); report['archive_pairs']+=1; report['archive_entries']+=len(ents)
    prev_end=0
    for e in sorted(ents,key=lambda x:x['offset']):
        off,sz=e['offset'],e['size']
        if off%4: report['errors'].append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'offset not 4-aligned','offset':off})
        if off<prev_end: report['errors'].append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'overlap'})
        if off+sz>len(cb): report['errors'].append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'slice out of bounds'}) ; continue
        prev_end=max(prev_end,off+sz); blob=cb[off:off+sz]
        try:
            if blob[:4]==b'darc': DarcArchive(blob); report['darc_entries_validated']+=1
            elif blob[:4]==b'BTBF':
                m=btbf_meta(blob)
                if m['text_start']+m['text_size']>len(blob): raise ValueError('BTBF text block out of bounds')
                report['btbf_entries_validated']+=1
        except Exception as ex:
            report['errors'].append({'path':str(idx.relative_to(ROMFS)),'entry':e['name'],'error':'component parse','detail':str(ex)})

# Direct font/DARC validation.
font=ROMFS/'Graphics/UI_en/Font/Font'
if font.is_file():
    try:
        arc=DarcArchive(font.read_bytes()); found=False
        for ip,b in arc.files():
            if b[:4]==b'CFNT':
                found=True; cmap=cfnt_char_map(b)
                report['font']={'inner':ip,'turkish_chars':{c:cmap.get(c) for c in 'ÇçÖöÜüĞğİıŞş'},'all_required_present':all(c in cmap for c in 'ÇçÖöÜüĞğİıŞş')}
        if not found: report['errors'].append({'path':str(font.relative_to(ROMFS)),'error':'no CFNT in font DARC'})
        elif not report['font']['all_required_present']: report['errors'].append({'path':str(font.relative_to(ROMFS)),'error':'missing Turkish glyph'})
    except Exception as e: report['errors'].append({'path':str(font.relative_to(ROMFS)),'error':'font parse','detail':str(e)})
else: report['errors'].append({'path':'Graphics/UI_en/Font/Font','error':'font patch missing'})

# Runtime tree hygiene + hashes.
bad_ext={'.xls','.xlsx','.csv','.png','.py','.json','.md','.txt'}
for p in sorted(ROMFS.rglob('*')):
    if not p.is_file(): continue
    report['romfs_file_count']+=1
    if p.suffix.lower() in bad_ext: report['unexpected_source_files'].append(str(p.relative_to(ROMFS)))
    report['sha256'].append({'path':str(p.relative_to(ROMFS)),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
if report['unexpected_source_files']: report['errors'].append({'error':'source/intermediate files found in romfs','files':report['unexpected_source_files']})
report['ok']=not report['errors']
(ROOT/'Reports/TECHNICAL_AUDIT_v33.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'MANIFEST_SHA256.json').write_text(json.dumps(report['sha256'],ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='sha256'},ensure_ascii=False,indent=2))
if report['errors']: raise SystemExit(2)
