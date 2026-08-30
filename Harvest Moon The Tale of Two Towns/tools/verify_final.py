#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, csv, gzip, hashlib, json, py_compile, re, struct, subprocess, sys, tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))

import hm3ds_text as hm
import short_table_repack
from release_info import RELEASE_NAME, RELEASE_VERSION, TITLE_ID

ROMFS = ROOT / 'luma' / 'titles' / TITLE_ID / 'romfs'
CMAP = hm.load_custom_charmap(str(TOOLS / 'charmap_turkish_full.json'))

SYSTEM_BANKS = ['mes_data.bin','mes_data_fr_b.bin','mes_data_fr_g.bin','mes_data_ge.bin']
EVENT_BANKS = ['event_mes_data.bin','event_mes_data_fr_b.bin','event_mes_data_fr_g.bin','event_mes_data_ge.bin']
EXPECTED_FILES = {
    'CTR/CEC/CecLayout.arc',
    'CTR/Console/Title.arc.gz',
    'CTR/Console/menu_icon.ctpk',
    'CTR/Console/staffroll_logo.ctpk',
    'CTR/Console/update_button.arc.gz',
    'CTR/Console/wait_message.ctpk',
    'CTR/NadeNade/Lower.arc',
    'CTR/NadeNade/Upper.arc',
    'CTR/Select_Language.arc',
    'console_obj_data.bin','console_obj_data_fr.bin','console_obj_data_ge.bin',
    *SYSTEM_BANKS, *EVENT_BANKS, 'font_data.bin',
}
DIRECT_SYSTEM = [
    ('Request Beginner','Görev Acemisi'),
    ("{#2333} Save and go to bed.{BR} Go to bed without saving.{BR} Don't go to bed yet.",'{#2333} Kaydet ve uyu.{BR} Kaydetmeden uyu.{BR} Henüz uyuma.'),
    ('Saving.','Kayıt.'),('Local Play','Yerel Oyun'),("She's happy and healthy!",'Mutlu ve sağlıklı!'),
    ('Upgrades!','Gelişim!'),('Renovations?','Tadilat?'),('Item Needed','Gerekli'),('A Fine Axe!','İyi Balta!'),
    ('Midnight Snack?','Gece Yemeği?'),('Help Wanted!','Yardım Lazım'),('Touch screen','Ekrana dokun'),
]
DIRECT_EVENT = [
    ('{#232F}Please pick your character.{BR}{#2332} Male{BR} Female','{#232F}Karakterini seç.{BR}{#2332} Erkek{BR} Kadın'),
    ("We're here!{BR}This is your farm.",'Geldik!{BR}Burası çiftliğin.'),
    ('This is the place!{BR}Your new farm!','İşte burası!{BR}Yeni çiftliğin!'),
    ('Where shall we go?','Nereye gidelim?'),('Where do you wanna go?','Nereye gidelim?'),
    ('Stop! Sit! Heel!','Dur! Otur! Gel!'),
    ('{#2137}Talk about the request?{BR}{#2332} Yes{BR} No','{#2137}İsteği konuşalım mı{BR}{#2332} Evet{BR} Hayır'),
]

def enc(text: str) -> bytes:
    return b''.join(hm.p16(w) for w in hm.encode_text(text, 'slots', CMAP))

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rel_files(base: Path) -> dict[str, Path]:
    return {str(p.relative_to(base)).replace('\\','/'): p for p in base.rglob('*') if p.is_file()}

def check_equal_banks(report, names, label):
    hashes={n:sha256(ROMFS/n) for n in names}
    report['checks'][label+'_hashes']=hashes
    report['checks'][label+'_all_equal']=len(set(hashes.values()))==1

def check_direct(report, banks, pairs, label):
    result={}
    for bank in banks:
        data=(ROMFS/bank).read_bytes(); one={}
        for old,new in pairs:
            one[new]={'new_present':enc(new) in data,'old_absent':enc(old) not in data}
        result[bank]=one
    report['checks'][label]=result

def parse_table_contents(data: bytes, base: int):
    import struct
    o0=struct.unpack_from('<I',data,base)[0]; n=o0//4
    offs=[struct.unpack_from('<I',data,base+4*i)[0] for i in range(n)]
    starts=[base+v for v in offs]
    end=None
    for x in range(starts[-1],min(len(data)-1,starts[-1]+0x10000),2):
        if struct.unpack_from('<H',data,x)[0]==short_table_repack.END:
            end=x;break
    if end is None: raise RuntimeError(f'table end missing @ {base:#x}')
    contents=[]
    for i,s in enumerate(starts):
        delim=(starts[i+1]-2) if i+1<n else end-2
        contents.append(data[s:delim])
    return contents

def check_short_tables(report):
    mes=(ROMFS/'mes_data.bin').read_bytes(); ev=(ROMFS/'event_mes_data.bin').read_bytes()
    checks=[]
    for base,replacements,label in short_table_repack.MES_SPECS:
        contents=parse_table_contents(mes,base)
        for old,new in replacements.items():
            checks.append({'table':label,'old':old,'new':new,'new_present':any(enc(new) in c for c in contents),'old_absent':not any(enc(old) in c for c in contents)})
    base,replacements,label=short_table_repack.EVENT_SPEC
    contents=parse_table_contents(ev,base)
    for old,new in replacements.items():
        checks.append({'table':label,'old':old,'new':new,'new_present':any(enc(new) in c for c in contents),'old_absent':not any(enc(old) in c for c in contents)})
    report['checks']['short_tables']=checks

def check_graphics(report):
    checks={}
    console_names=['console_obj_data.bin','console_obj_data_fr.bin','console_obj_data_ge.bin']
    hashes={n:sha256(ROMFS/n) for n in console_names}
    checks['console_variants_equal']=len(set(hashes.values()))==1
    data=(ROMFS/'console_obj_data.bin').read_bytes()
    n=struct.unpack_from('<I',data,0)[0]
    header=4+8*n
    entries=[struct.unpack_from('<II',data,4+i*8) for i in range(n)]
    resources=[data[header+o:header+o+size] for o,size in entries]
    rebuilt=bytearray(header); struct.pack_into('<I',rebuilt,0,n); body=bytearray(); off=0
    for i,r in enumerate(resources):
        struct.pack_into('<II',rebuilt,4+i*8,off,len(r)); body+=r; off+=len(r)
    checks['console_resource_count']=n
    checks['console_roundtrip_identical']=bytes(rebuilt+body)==data
    magic_expect={
        'CTR/CEC/CecLayout.arc':b'darc','CTR/NadeNade/Upper.arc':b'darc','CTR/NadeNade/Lower.arc':b'darc','CTR/Select_Language.arc':b'darc',
        'CTR/Console/menu_icon.ctpk':b'CTPK','CTR/Console/wait_message.ctpk':b'CTPK','CTR/Console/staffroll_logo.ctpk':b'CTPK',
    }
    checks['container_magic']={rel:(ROMFS/rel).read_bytes().startswith(magic) for rel,magic in magic_expect.items()}
    checks['gzip_darc']={}
    for rel in ['CTR/Console/Title.arc.gz','CTR/Console/update_button.arc.gz']:
        try: checks['gzip_darc'][rel]=gzip.decompress((ROMFS/rel).read_bytes()).startswith(b'darc')
        except Exception: checks['gzip_darc'][rel]=False
    src=(TOOLS/'console_obj_lib.py').read_text(encoding='utf-8')
    required=['Bilgi','İstekler','Geçmiş','Son gün!','Elle Av','Hayvansal',"(15,'GERİ'","(48,'ONAY'","(50,'SİL'"]
    forbidden=['İstek Listesi','İstek Geçmişi','bugün bitiyor','Elle Balık','Hayvansal Ürünler',"(84,35,'Veri'"]
    checks['console_tool_required_labels']={x:(x in src) for x in required}
    checks['console_tool_forbidden_labels_absent']={x:(x not in src) for x in forbidden}
    previews=ROOT/'qa'/'previews'
    checks['final_previews']={n:(previews/n).is_file() for n in ['console_labels.png','cec_delivery.png','cec_receive.png','nadenade_title.png']}

    ga=ROOT/'qa'/'GRAPHICS_AUDIT.json'
    try:
        gd=json.loads(ga.read_text(encoding='utf-8')); checks['graphics_audit_passed']=bool(gd.get('passed'))
    except Exception:
        checks['graphics_audit_passed']=False
    wa=ROOT/'qa'/'WIDTH_AUDIT.json'
    try:
        wd=json.loads(wa.read_text(encoding='utf-8')); checks['width_audit_passed']=bool(wd.get('passed'))
    except Exception:
        checks['width_audit_passed']=False
    report['checks']['graphics']=checks

def check_csv(report):
    counts={}
    for base in ['mes_data','event_mes_data']:
        p=ROOT/'translations'/f'{base}.csv'
        with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        counts[base]={'rows':len(rows),'filled':sum(bool((r.get('translation') or '').strip()) for r in rows)}
    report['checks']['csv_counts']=counts

def check_residual_system_english(report):
    # mes_data is expected to be fully translated for normal user-facing text.
    # Remaining pure-ASCII English-like blocks are allowed only in known internal
    # flag/debug/test tables. This catches hidden UI strings outside the normal CSV path.
    stop=set('the and to of in is it you your for this that with on are be not can please yes no save load item data test settings start end buy get day animal farm screen play host client next use how when where what name select pick press button'.split())
    internal_ranges=[(0x2200,0x9000),(0x1FF00,0x28000)]
    candidates=[]
    with tempfile.TemporaryDirectory(prefix='hmtr_text_audit_') as td:
        csvp=Path(td)/'mes_all.csv'
        hm.export_bin(ROMFS/'mes_data.bin',csvp,min_glyphs=1,min_ratio=0.15)
        with csvp.open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                text=row.get('source','')
                plain=re.sub(r'\{[^}]+\}',' ',text)
                if any(ord(ch)>127 for ch in plain): continue
                words=re.findall(r'[A-Za-z]+',plain.lower())
                if len(words)<2: continue
                score=sum(w in stop for w in words)
                if score<2: continue
                off=int(row['offset_hex'],16)
                candidates.append({'id':int(row['id']),'offset':row['offset_hex'],'score':score,'words':len(words),'text':text[:240],'internal':any(a<=off<b for a,b in internal_ranges)})
    report['checks']['residual_system_english']={
        'candidate_count':len(candidates),
        'outside_internal_ranges':[x for x in candidates if not x['internal']],
        'internal_candidate_offsets':[x['offset'] for x in candidates if x['internal']],
    }

def check_stale_versions(report):
    hits=[]
    pattern=re.compile(r'(?i)\bv(?:4|5|6|7|8|9|10|11|12|13|14|15)\b|FINAL_V(?:4|5|6|7|8|9|10|11|12|13|14|15)|build_final_v(?:4|5|6|7|8|9|10|11|12|13|14|15)|hm3ds_tr_tool_v\d+')
    text_ext={'.py','.md','.txt','.bat','.json','.csv'}
    for p in ROOT.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in text_ext or '__pycache__' in p.parts: continue
        try: text=p.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError: continue
        for no,line in enumerate(text.splitlines(),1):
            if pattern.search(line): hits.append({'file':str(p.relative_to(ROOT)),'line':no,'text':line[:240]})
    report['checks']['stale_version_refs']=hits

def check_tools_compile(report):
    failures=[]
    for p in TOOLS.glob('*.py'):
        try: py_compile.compile(str(p),doraise=True)
        except Exception as e: failures.append({'file':p.name,'error':str(e)})
    report['checks']['tool_compile_failures']=failures

def compare_rebuild(report, rom_zip: Path):
    with tempfile.TemporaryDirectory(prefix='hmtr_verify_') as td:
        out=Path(td)/'rebuild'
        subprocess.run([sys.executable,str(TOOLS/'build_final.py'),str(rom_zip),'-o',str(out)],check=True,cwd=ROOT)
        rebuilt=out/'luma'/'titles'/TITLE_ID/'romfs'
        a=rel_files(ROMFS); b=rel_files(rebuilt)
        missing=sorted(set(a)-set(b)); extra=sorted(set(b)-set(a)); changed=[]
        for name in sorted(set(a)&set(b)):
            if sha256(a[name])!=sha256(b[name]): changed.append(name)
        report['checks']['clean_rebuild_compare']={'missing':missing,'extra':extra,'changed':changed,'identical':not(missing or extra or changed)}

def all_pass(report):
    c=report['checks']
    if set(c['package_files']) != EXPECTED_FILES: return False
    if not c['system_banks_all_equal'] or not c['event_banks_all_equal']: return False
    if c['stale_version_refs'] or c['tool_compile_failures']: return False
    if c['residual_system_english']['outside_internal_ranges']: return False
    for group in ['direct_system_patches','direct_event_patches']:
        for bank in c[group].values():
            for x in bank.values():
                if not all(x.values()): return False
    if not all(x['new_present'] and x['old_absent'] for x in c['short_tables']): return False
    g=c['graphics']
    if not g['console_variants_equal'] or g['console_resource_count']!=282 or not g['console_roundtrip_identical']: return False
    if not all(g['container_magic'].values()) or not all(g['gzip_darc'].values()): return False
    if not all(g['console_tool_required_labels'].values()) or not all(g['console_tool_forbidden_labels_absent'].values()): return False
    if not all(g['final_previews'].values()) or not g.get('graphics_audit_passed') or not g.get('width_audit_passed'): return False
    cr=c.get('clean_rebuild_compare')
    if cr is not None and not cr['identical']: return False
    return True

def main():
    ap=argparse.ArgumentParser(description=f'{RELEASE_NAME} final doğrulama aracı')
    ap.add_argument('--rom-zip',type=Path,help='Temiz Avrupa ROM ZIP; verilirse sıfırdan yeniden üretip byte-byte karşılaştırır.')
    args=ap.parse_args()
    report={'release':RELEASE_NAME,'version':RELEASE_VERSION,'checks':{},'files':{}}
    files=rel_files(ROMFS)
    report['checks']['package_files']=sorted(files)
    report['files']={n:{'size':p.stat().st_size,'sha256':sha256(p)} for n,p in sorted(files.items())}
    check_equal_banks(report,SYSTEM_BANKS,'system_banks')
    check_equal_banks(report,EVENT_BANKS,'event_banks')
    check_direct(report,SYSTEM_BANKS,DIRECT_SYSTEM,'direct_system_patches')
    check_direct(report,EVENT_BANKS,DIRECT_EVENT,'direct_event_patches')
    check_short_tables(report); check_graphics(report); check_csv(report); check_residual_system_english(report); check_stale_versions(report); check_tools_compile(report)
    if args.rom_zip: compare_rebuild(report,args.rom_zip)
    report['passed']=all_pass(report)
    out=ROOT/'qa'/'FINAL_QA.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'release':RELEASE_NAME,'passed':report['passed'],'stale_version_refs':len(report['checks']['stale_version_refs']),'compile_failures':len(report['checks']['tool_compile_failures']),'clean_rebuild':report['checks'].get('clean_rebuild_compare')},ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['passed'] else 1)

if __name__=='__main__': main()
