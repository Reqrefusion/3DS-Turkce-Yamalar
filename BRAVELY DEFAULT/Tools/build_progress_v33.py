#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys, json, shutil, struct, hashlib, os
from collections import defaultdict
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bravely_ui_tools import DarcArchive, patch_bclyt, patch_cfnt_turkish, cfnt_char_map, bclyt_entries, make_text_width_fn
from bclim_tools import decode_bclim, encode_rgba8_bclim
from raster_patch_tools import render_translation, render_custom_id
from raster_translations import RASTER_TEXT, MAP_TITLES
from translations_tr import translate_ui
from repack_bravely import parse_index

UI_ROOT=Path(os.environ.get('BD_UI_ROOT',str(HERE/'input/Graphics/UI_en')))
LANG_ROOT=Path(os.environ.get('BD_LANG_ROOT',str(UI_ROOT.parent)))
COMMON_GAME=Path(os.environ.get('BD_COMMON_GAME',str(HERE/'output/Common_en_gamefiles_v33/Common_en')))
UNIQUE_INDEX=Path(os.environ.get('BD_UNIQUE_INDEX',str(HERE/'unique_bclim_index.json')))
OUT=Path(os.environ.get('BD_OUT',str(HERE/'output/BravelyDefault_TR_progress_v33')))
STAGE=OUT/'_components'
ROMFS=OUT/'romfs'

FORCE_INPAINT_IDS={7,8,9,10,124,125,126,127,128,129,130,133,134,135,136,137,138,139,140,141,143,144,145,146,147,148,150,151,172,173,174,175,177,178,179,184,185,186,189,192,244,250,251,252,253,254,256,264,265,266,267,288,290,292,293,295,297,299,301,304,306,307}
SERIF_IDS=set(range(287,307))
FRAME_IDS={288,290,292,293,295,297,299,301,304,306}

report={
 'version':'progress_v3.3',
 'common_game_files':0,
 'bclyt_files_modified':0,
 'ui_text_changes':0,
 'font':{},
 'raster_unique_targets':0,
 'raster_occurrences_patched':0,
 'map_titles_patched':0,
 'components_modified':0,
 'crowd_archives_rebuilt':0,
 'direct_ui_files':0,
 'localized_geometry_uses':0,
 'fit_scaled_texts':0,
 'bclyt_validation_errors':[],
 'ui_changes':[],
 'modified_components':[],
 'crowd_outputs':[],
 'raster_changes':[],
 'notes':[
   'Graphics/UI_en crowd/index pairs are rebuilt when a packed component changes.',
   'BCLIM raster translations are re-encoded as RGBA8 for reliable editing.',
   'Localized DE/ES/FR/IT pane geometry is reused when available; Turkish text width is checked against CFNT advances.',
   'v3.3 retains the corrected txt1 0x4C/0x4E length fields and adds CMAP-based Turkish glyph source lookup.',
   'Raster occurrence index is bundled in Tools so the build is reproducible from the supplied source dump.'
 ]
}

if OUT.exists(): shutil.rmtree(OUT)
(STAGE).mkdir(parents=True)
(ROMFS/'Common_en').mkdir(parents=True)
shutil.copytree(COMMON_GAME,ROMFS/'Common_en',dirs_exist_ok=True)
report['common_game_files']=sum(1 for p in (ROMFS/'Common_en').rglob('*') if p.is_file())

# Build raster occurrence lookup from verified unique-visible set.
unique=json.loads(UNIQUE_INDEX.read_text(encoding='utf-8'))
raster_by_component=defaultdict(dict)
for it in unique:
    iid=it['id']
    if iid not in RASTER_TEXT: continue
    for occ in it['occurrences']:
        arel=occ['archive']
        # The visual scanner could misinterpret a crowd.fs whose first entry starts at offset 0 as a standalone DARC.
        # Remap the only translated occurrence of that kind to the actual first packed component.
        if iid==302 and arel=='Layout/ChapterTitle/crowd.fs':
            arel='Layout/ChapterTitle/00_Prologue'
        raster_by_component[arel][occ['inner']]={'id':iid,'text':RASTER_TEXT[iid]}
report['raster_unique_targets']=len(RASTER_TEXT)

# Map title components (each contains one title.bclim).
for name,text in MAP_TITLES.items():
    rel=f'Layout/31_MAP_TITLE/{name}'
    # inner is resolved dynamically below because DARC roots sometimes include './'.
    raster_by_component[rel]['__MAP_TITLE__']={'id':None,'text':text,'map_title':True}

# Cache localized comparison images for inpainting.
lang_arc_cache={}
def other_language_images(component_rel,inner):
    out=[]
    for lang in ('UI_de','UI_es','UI_fr','UI_it'):
        key=(lang,component_rel)
        if key not in lang_arc_cache:
            p=LANG_ROOT/lang/component_rel
            try:
                a=DarcArchive(p.read_bytes()); lang_arc_cache[key]=dict(a.files())
            except Exception:
                lang_arc_cache[key]={}
        b=lang_arc_cache[key].get(inner)
        if b:
            try: out.append(decode_bclim(b))
            except Exception: pass
    return out

# Build a width estimator from the patched Turkish CFNT so new glyphs are measured too.
text_width_fn=None
try:
    farc=DarcArchive((UI_ROOT/'Font'/'Font').read_bytes())
    for _ip,_b in farc.files():
        if _b[:4]==b'CFNT':
            _patched,_=patch_cfnt_turkish(_b)
            text_width_fn=make_text_width_fn(_patched)
            break
except Exception:
    text_width_fn=None

# Localized western panes are useful geometry donors: Nintendo/localization layouts often
# widen or reposition short labels for translated strings. Cache per language/component.
donor_arc_cache={}
def donor_sections(component_rel,inner_path):
    donors=defaultdict(list)
    for lang in ('UI_de','UI_es','UI_fr','UI_it'):
        key=(lang,component_rel)
        if key not in donor_arc_cache:
            p=LANG_ROOT/lang/component_rel
            try:
                a=DarcArchive(p.read_bytes()); donor_arc_cache[key]=dict(a.files())
            except Exception:
                donor_arc_cache[key]={}
        b=donor_arc_cache[key].get(inner_path)
        if not b or b[:4]!=b'CLYT': continue
        for ent in bclyt_entries(b):
            off=ent['section_offset']; sz=ent['section_size']
            donors[(ent['pane'],ent['ordinal'])].append(b[off:off+sz])
    return donors

# Scan every DARC component from the extracted UI tree.
for src in sorted(UI_ROOT.rglob('*')):
    if not src.is_file(): continue
    rel=str(src.relative_to(UI_ROOT))
    if src.name in ('crowd.fs','index.fs'): continue
    try: data=src.read_bytes()
    except: continue
    if data[:4]!=b'darc': continue
    try: arc=DarcArchive(data)
    except Exception: continue
    replacements={}; local_text=0; local_raster=[]; font_change=False

    # CFNT font patch.
    if rel=='Font/Font':
        for ip,b in arc.files():
            if b[:4]==b'CFNT':
                nb,frep=patch_cfnt_turkish(b)
                replacements[ip]=nb
                report['font']=frep|{'archive':rel,'inner':ip}
                font_change=True

    # BCLYT text patch.
    for ip,b in arc.files():
        if b[:4]!=b'CLYT': continue
        donors=donor_sections(rel,ip)
        nb,changes=patch_bclyt(b,translate_ui,context=rel+'::'+ip,donors=donors,width_fn=text_width_fn)
        if changes:
            # Structural validation of every changed txt1. This specifically catches the v3.1
            # pane-height corruption and malformed length/offset fields.
            ents={(e['pane'],e['ordinal']):e for e in bclyt_entries(nb)}
            for ch in changes:
                ent=ents.get((ch['pane'],ch['ordinal']))
                if not ent or ent['height']<=0.1 or ent['width']<=0.1:
                    report['bclyt_validation_errors'].append({'archive':rel,'inner':ip,'change':ch,'reason':'invalid pane geometry'})
                else:
                    sec=nb[ent['section_offset']:ent['section_offset']+ent['section_size']]
                    textoff=struct.unpack_from('<I',sec,0x58)[0]
                    declared=struct.unpack_from('<H',sec,0x4c)[0]
                    expected=len(ch['new'].encode('utf-16le'))+2
                    if declared!=expected or textoff>=len(sec):
                        report['bclyt_validation_errors'].append({'archive':rel,'inner':ip,'change':ch,'reason':'bad text length/offset','declared':declared,'expected':expected})
                report['localized_geometry_uses']+=int(ch.get('used_localized_geometry',False))
                report['fit_scaled_texts']+=int(ch.get('fit_scale',1.0)<0.999)
                report['ui_changes'].append({'archive':rel,'inner':ip,**ch})
            replacements[ip]=nb
            local_text+=len(changes)
            report['bclyt_files_modified']+=1
            report['ui_text_changes']+=len(changes)

    # BCLIM raster patch, including map titles.
    specmap=raster_by_component.get(rel,{})
    if specmap:
        files=dict(arc.files())
        # Resolve map title's actual inner path.
        if '__MAP_TITLE__' in specmap:
            s=specmap['__MAP_TITLE__']
            for ip,b in files.items():
                if ip.endswith('/title.bclim') or ip.endswith('title.bclim'):
                    specmap={k:v for k,v in specmap.items() if k!='__MAP_TITLE__'}
                    specmap[ip]=s
                    break
        for ip,spec in specmap.items():
            b=files.get(ip)
            if not b: continue
            try: enimg=decode_bclim(b)
            except Exception as e:
                local_raster.append({'inner':ip,'id':spec.get('id'),'text':spec['text'],'status':'decode_failed','error':str(e)})
                continue
            iid=spec.get('id')
            other=other_language_images(rel,ip)
            mode='bright_text' if iid in FRAME_IDS else ('inpaint' if (spec.get('map_title') or iid in FORCE_INPAINT_IDS) else 'auto')
            serif=bool(spec.get('map_title') or (iid in SERIF_IDS if iid is not None else False))
            try:
                custom=render_custom_id(iid,enimg,other) if iid is not None else None
                trimg=custom if custom is not None else render_translation(enimg,spec['text'],other,serif=serif,mode=mode)
                nb=encode_rgba8_bclim(trimg,b)
                # Structural visual round-trip check.
                chk=decode_bclim(nb)
                if chk.size!=enimg.size: raise AssertionError((chk.size,enimg.size))
                replacements[ip]=nb
                local_raster.append({'inner':ip,'id':iid,'text':spec['text'],'status':'patched','old_format':'native','new_format':'RGBA8','size_before':len(b),'size_after':len(nb)})
                report['raster_occurrences_patched']+=1
                if spec.get('map_title'): report['map_titles_patched']+=1
            except Exception as e:
                local_raster.append({'inner':ip,'id':iid,'text':spec['text'],'status':'patch_failed','error':str(e)})

    if replacements:
        newarc=arc.rebuild(replacements)
        dst=STAGE/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(newarc)
        report['components_modified']+=1
        report['modified_components'].append({'path':rel,'text_changes':local_text,'raster_changes':sum(x['status']=='patched' for x in local_raster),'font':font_change,'size_before':len(data),'size_after':len(newarc)})
        for x in local_raster: report['raster_changes'].append({'archive':rel,**x})

# Membership map: extracted components that are actually packed inside crowd.fs/index.fs.
member_of={}
crowd_folders=[]
for idx in sorted(UI_ROOT.rglob('index.fs')):
    folder=idx.parent
    if not (folder/'crowd.fs').is_file(): continue
    frel=str(folder.relative_to(UI_ROOT))
    try: ents=parse_index(idx.read_bytes())
    except Exception: continue
    crowd_folders.append((frel,folder,ents))
    for e in ents:
        comp=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
        member_of[comp]=frel

# Determine crowds affected by staged component changes.
affected=defaultdict(list)
for p in STAGE.rglob('*'):
    if not p.is_file(): continue
    rel=str(p.relative_to(STAGE))
    if rel in member_of: affected[member_of[rel]].append(rel)
    else:
        # Direct on-ROMFS DARC (e.g. Font/Font).
        dst=ROMFS/'Graphics'/'UI_en'/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dst)
        report['direct_ui_files']+=1

# Rebuild each affected crowd using staged components where present.
folder_lookup={frel:(folder,ents) for frel,folder,ents in crowd_folders}
for frel,changed in sorted(affected.items()):
    folder,ents=folder_lookup[frel]
    ib=folder.joinpath('index.fs').read_bytes(); idx=bytearray(ib); crowd=bytearray(); details=[]
    for e in ents:
        while len(crowd)%4: crowd.append(0)
        off=len(crowd)
        comp_rel=(f'{frel}/{e["name"]}' if frel!='.' else e['name']).strip('/')
        staged=STAGE/comp_rel; src=folder/e['name']
        fb=(staged if staged.is_file() else src).read_bytes()
        crowd+=fb
        struct.pack_into('<I',idx,e['pos']+4,off)
        struct.pack_into('<I',idx,e['pos']+8,len(fb))
        details.append((e['name'],off,len(fb)))
    while len(crowd)%4: crowd.append(0)
    outdir=ROMFS/'Graphics'/'UI_en'/frel; outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'crowd.fs').write_bytes(crowd); (outdir/'index.fs').write_bytes(idx)
    # validate index->crowd slices
    ents2=parse_index(bytes(idx))
    for e,(name,off,sz) in zip(ents2,details):
        assert (e['name'],e['offset'],e['size'])==(name,off,sz)
        assert len(crowd[off:off+sz])==sz
    report['crowd_archives_rebuilt']+=1
    report['crowd_outputs'].append({'folder':frel,'changed_components':len(changed),'entries':len(ents),'old_crowd_size':(folder/'crowd.fs').stat().st_size,'new_crowd_size':len(crowd)})

# Validate all patch DARC direct files / crowd entries that were changed.
# Font char map validation is especially important.
font_path=ROMFS/'Graphics'/'UI_en'/'Font'/'Font'
if font_path.is_file():
    a=DarcArchive(font_path.read_bytes())
    for ip,b in a.files():
        if b[:4]==b'CFNT':
            m=cfnt_char_map(b); assert all(c in m for c in 'ĞğİıŞş')

if report['bclyt_validation_errors']:
    raise AssertionError(f"BCLYT validation errors: {len(report['bclyt_validation_errors'])}")

# Build compact unresolved list from verified unique set.
resolved=set(RASTER_TEXT)
allids={it['id'] for it in unique}
report['verified_visible_raster_remaining_ids']=sorted(allids-resolved)
report['verified_visible_raster_remaining_count']=len(allids-resolved)

# Hash output patch files.
hashes=[]
for p in sorted(ROMFS.rglob('*')):
    if p.is_file():
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        hashes.append({'path':str(p.relative_to(ROMFS)),'size':p.stat().st_size,'sha256':h})
report['patch_file_count']=len(hashes)
report['patch_files']=hashes

(OUT/'BUILD_REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
# Remove staging from distributable build; tools/sources are packaged separately later.
shutil.rmtree(STAGE)
print(json.dumps({k:v for k,v in report.items() if k not in ('modified_components','raster_changes','patch_files','crowd_outputs')},ensure_ascii=False,indent=2))
