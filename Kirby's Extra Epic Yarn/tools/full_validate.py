from __future__ import annotations
import argparse,csv,hashlib,json,os,re,tempfile,zipfile,sys,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ktl.msbt import MsbtFile,control_tokens
from ktl.bffnt import missing_chars,char_advance_widths,text_line_widths
from ktl.project import LANG_ORDER
from ktl.fullpatch import TITLE_SMDH,TITLE_CODE,TEST_SAMPLE_TR

PH_RE=re.compile(r'<[^>\n]+>')

def smdh_titles(b:bytes):
    out=[]
    for i in range(16):
        o=8+i*0x200;vals=[]
        for rel,size in ((0,0x80),(0x80,0x100),(0x180,0x80)):
            vals.append(b[o+rel:o+rel+size].decode('utf-16le','ignore').split('\0')[0])
        out.append(vals)
    return out

def group_label(label): return re.sub(r'\d+','#',label)

def main():
    ap=argparse.ArgumentParser(description='Türkçe paket: yapısal, font ve piksel-genişliği doğrulaması')
    ap.add_argument('source',nargs='?',default=str(ROOT/'input'/'source.zip'))
    ap.add_argument('csv',nargs='?',default=str(ROOT/'data'/'Kirby_TR_translated.csv'))
    ap.add_argument('patched',nargs='?',default=str(ROOT/'output'/'Kirby_Extra_Epic_Yarn_TR_FINAL_SAFE.zip'))
    ap.add_argument('--json-out',default=str(ROOT/'reports'/'full_validation_v2.json'))
    a=ap.parse_args()
    with open(a.csv,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    by={r['Label']:r['Turkish'] for r in rows}
    checks={}
    checks['row_count_2238']=(len(rows)==2238)
    checks['eu_blank_structure_preserved']=all(bool(r['EU_English'].strip())==bool(r['Turkish'].strip()) for r in rows)
    checks['intentional_empty_labels']=[r['Label'] for r in rows if not r['EU_English'].strip()]
    checks['control_codes_match_eu']=all(control_tokens(r['EU_English'])==control_tokens(r['Turkish']) for r in rows)
    checks['placeholders_match_eu']=all(sorted(PH_RE.findall(r['EU_English']))==sorted(PH_RE.findall(r['Turkish'])) for r in rows)

    # Cross-locale structural audit.
    presence=[]; ctrl_variants=[]; placeholder_variants=[]
    for r in rows:
        present=[x for x in LANG_ORDER if r.get(x,'').strip()]; absent=[x for x in LANG_ORDER if not r.get(x,'').strip()]
        if present and absent: presence.append({'label':r['Label'],'present':present,'absent':absent,'canonical_eu_present':bool(r['EU_English'].strip())})
        c={x:tuple(control_tokens(r.get(x,''))) for x in LANG_ORDER}
        if len(set(c.values()))>1: ctrl_variants.append({'label':r['Label'],'variants':{k:list(v) for k,v in c.items()}})
        p={x:tuple(PH_RE.findall(r.get(x,''))) for x in LANG_ORDER}
        if len(set(p.values()))>1: placeholder_variants.append({'label':r['Label'],'variants':{k:list(v) for k,v in p.items()}})
    checks['cross_language_presence_variants']=presence
    checks['cross_language_control_variants']=ctrl_variants
    checks['cross_language_placeholder_variants']=placeholder_variants

    # Real BFFNT advance-width audit. Capacity is inferred from the widest source-localization line in the same label family.
    with zipfile.ZipFile(a.source) as src:
        fonts=[]
        for n in ('frame/font/GameFont1.bffnt','frame/font/GameFont2.bffnt'):
            fonts.append(char_advance_widths(src.read(n)))
        cps=set().union(*(set(f) for f in fonts)); adv={cp:max(f.get(cp,0) for f in fonts) for cp in cps}
        def mw(s): return max(text_line_widths(s,adv) or [0])
        group_caps={}; group_line_caps={}
        for r in rows:
            g=group_label(r['Label'])
            for loc in LANG_ORDER[:8]:
                if r.get(loc,'').strip():
                    group_caps[g]=max(group_caps.get(g,0),mw(r[loc]))
                    group_line_caps[g]=max(group_line_caps.get(g,0),len(r[loc].splitlines()) or 1)
        width_rows=[]
        for r in rows:
            if not r['Turkish'].strip(): continue
            g=group_label(r['Label']); cap=group_caps.get(g,0);tw=mw(r['Turkish'])
            ratio=(tw/cap) if cap else 0
            width_rows.append({'label':r['Label'],'group':g,'turkish_max_px':tw,'observed_group_source_max_px':cap,'ratio':round(ratio,4),'turkish_lines':len(r['Turkish'].splitlines()) or 1,'observed_group_max_lines':group_line_caps.get(g,0)})
        warnings=[x for x in width_rows if x['ratio']>1.05 or (x['observed_group_max_lines'] and x['turkish_lines']>x['observed_group_max_lines'])]
        checks['pixel_layout']={'method':'max advance width across GameFont1/GameFont2; compare against widest Latin-source line in same label family','rows_checked':len(width_rows),'warnings_over_5pct_or_lines':warnings,'warning_count':len(warnings),'max_ratio':max((x['ratio'] for x in width_rows),default=0)}

        # Font coverage against all actually rendered Turkish strings + translated test sample.
        fontrep={}
        for n in ('frame/font/GameFont1.bffnt','frame/font/GameFont2.bffnt'):
            with tempfile.NamedTemporaryFile(suffix='.bffnt',delete=False) as f: f.write(src.read(n));tmp=f.name
            try: fontrep[n]=sorted(missing_chars(tmp,list(by.values())+[TEST_SAMPLE_TR]))
            finally: os.unlink(tmp)
        checks['font_missing']=fontrep;checks['font_all_used_glyphs_present']=all(not x for x in fontrep.values())

    expected_changed={'exefs/code.bin','exefs/icon.bin'}
    for loc in LANG_ORDER:
        expected_changed.add(f'message/{loc}/fluff.msbt');expected_changed.add(f'message/{loc}/test_sample.msbt')
    with zipfile.ZipFile(a.source) as src, zipfile.ZipFile(a.patched) as pat:
        sn=[n for n in src.namelist() if not n.endswith('/')];pn=[n for n in pat.namelist() if not n.endswith('/')]
        checks['file_list_preserved']=(sn==pn)
        changed=[]
        for n in sn:
            if hashlib.sha256(src.read(n)).digest()!=hashlib.sha256(pat.read(n)).digest(): changed.append(n)
        checks['changed_files']=changed
        checks['changed_files_exactly_expected']=(set(changed)==expected_changed)
        checks['banner_byte_identical']=hashlib.sha256(src.read('exefs/banner.bin')).digest()==hashlib.sha256(pat.read('exefs/banner.bin')).digest()
        locres={}
        for loc in LANG_ORDER:
            m=MsbtFile.from_bytes(pat.read(f'message/{loc}/fluff.msbt'))
            t=MsbtFile.from_bytes(pat.read(f'message/{loc}/test_sample.msbt'))
            locres[loc]={'rows':len(m.labels),'canonical_turkish_exact':len(m.labels)==len(rows) and all(m.texts[i]==by[m.labels[i]] for i in range(len(m.labels))),'test_sample_turkish':all(x==TEST_SAMPLE_TR for x in t.texts)}
        checks['locales']=locres;checks['all_10_locales_exact']=all(v['canonical_turkish_exact'] and v['test_sample_turkish'] for v in locres.values())
        titles=smdh_titles(pat.read('exefs/icon.bin'))
        checks['smdh_all_16_turkish']=all(s==TITLE_SMDH and l==TITLE_SMDH and p=='Nintendo' for s,l,p in titles)
        cb=pat.read('exefs/code.bin');checks['code_title_turkish']=TITLE_CODE.encode('utf-16le') in cb;checks['old_code_title_absent']="Kirby's Extra Epic Yarn".encode('utf-16le') not in cb
    critical=['row_count_2238','eu_blank_structure_preserved','control_codes_match_eu','placeholders_match_eu','font_all_used_glyphs_present','file_list_preserved','changed_files_exactly_expected','banner_byte_identical','all_10_locales_exact','smdh_all_16_turkish','code_title_turkish','old_code_title_absent']
    checks['all_critical_checks_pass']=all(checks[k] for k in critical) and checks['pixel_layout']['warning_count']==0
    out={'rows':len(rows),'source':a.source,'patched':a.patched,'checks':checks}
    Path(a.json_out).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'all_critical_checks_pass':checks['all_critical_checks_pass'],'pixel_warning_count':checks['pixel_layout']['warning_count'],'font_missing':fontrep,'intentional_empty_labels':checks['intentional_empty_labels'],'changed_files':changed,'banner_byte_identical':checks['banner_byte_identical']},ensure_ascii=False,indent=2))
    raise SystemExit(0 if checks['all_critical_checks_pass'] else 1)
if __name__=='__main__':main()
