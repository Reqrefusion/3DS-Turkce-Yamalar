#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,hashlib
from collections import Counter
from pathlib import Path
import msbt_core as core

FILES=['autumn.msbt','event.msbt','staff.msbt','stage.msbt']
LANGS={'English':'EURen','German':'EURde','Spanish':'EURes','French':'EURfr','Italian':'EURit'}
FIELDS=['file','index','label','English','German','Spanish','French','Italian','Turkish',
        'official_max_lines','official_max_px','turkish_lines','turkish_max_px','fit_ratio','fit_status',
        'control_status','translation_status','translator_note']

def side_paths(root:Path,fname:str): return {k:root/v/'msg'/fname for k,v in LANGS.items()}

def load_rows(csvp:Path):
    d={}
    if csvp and csvp.exists():
        with csvp.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f): d[(r['file'],r['label'])]=r
    return d


def control_structure_valid(text:str)->bool:
    """Validate paired MSBT span controls while allowing language-driven reordering.

    Color/control TAGs without END are state changes. TAG pairs that have a matching
    END in the same message are treated as spans and must be properly nested.
    """
    sig=core.control_signature(text)
    end_types={(g,t) for kind,g,t,args in sig if kind=='END'}
    stack=[]
    for kind,g,t,args in sig:
        key=(g,t)
        if kind=='TAG' and key in end_types:
            stack.append(key)
        elif kind=='END':
            if not stack or stack[-1]!=key:
                return False
            stack.pop()
    return not stack

def controls_compatible(src:str,tr:str)->bool:
    """Require the same control-code inventory and valid pairing, not identical order.

    Official localizations reorder emphasized spans to fit grammar, so exact sequence
    equality is unnecessarily strict. Missing/extra controls are still rejected.
    """
    return (Counter(core.control_signature(src))==Counter(core.control_signature(tr))
            and control_structure_valid(tr))

def export(root:Path,out:Path,font:Path|None=None,merge:Path|None=None,seed_pullblox:Path|None=None):
    old=load_rows(merge) if merge else {}
    seed={}
    if seed_pullblox and seed_pullblox.exists():
        with seed_pullblox.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                if core.visible_text(r.get('English','')) and r.get('Turkish'):
                    seed.setdefault(r['English'],r['Turkish'])
    metrics=core.load_metrics(font)
    out.parent.mkdir(parents=True,exist_ok=True)
    total=0
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for fname in FILES:
            ms={k:core.parse_msbt(p) for k,p in side_paths(root,fname).items()}
            for m in ms.values(): core.roundtrip_self_test(m)
            eng=ms['English']
            for lang,m in ms.items():
                if m.labels_by_index!=eng.labels_by_index: raise ValueError(f'{fname}/{lang}: labels differ')
            dec={k:[core.raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw] for k,m in ms.items()}
            for i,label in enumerate(eng.labels_by_index):
                official=[dec[k][i] for k in LANGS]
                prior=old.get((fname,label),{})
                tr=prior.get('Turkish','') or seed.get(dec['English'][i],'')
                note=prior.get('translator_note','')
                status=prior.get('translation_status','')
                if not status: status='REUSED_PULLBLOX' if tr and dec['English'][i] in seed else ('DRAFT' if tr else 'EMPTY')
                if metrics:
                    st=[metrics.text_stats(x) for x in official]
                    ml=max(x[0] for x in st); mp=max(x[1] for x in st)
                    if tr:
                        tl,tp,_=metrics.text_stats(tr); ratio=tp/mp if mp else 1
                        fit='OK' if tl<=ml and tp<=mp else ('REVIEW' if tl<=ml and ratio<=1.10 else 'RISK')
                    else: tl=tp=0;ratio=0;fit='EMPTY'
                else:
                    ml=max(core.visible_text(x).count('\n')+1 for x in official);mp=0
                    tl=core.visible_text(tr).count('\n')+1 if tr else 0;tp=0;ratio=0;fit='N/A'
                cs='OK' if (not tr or controls_compatible(dec['English'][i],tr)) else 'MISMATCH'
                w.writerow({'file':fname,'index':i,'label':label,**{k:dec[k][i] for k in LANGS},'Turkish':tr,
                    'official_max_lines':ml,'official_max_px':mp,'turkish_lines':tl,'turkish_max_px':tp,'fit_ratio':f'{ratio:.3f}',
                    'fit_status':fit,'control_status':cs,'translation_status':status,'translator_note':note})
                total+=1
    print(f'Exported {total} rows -> {out}')

def inject(root:Path,csvp:Path,out_romfs:Path,strict=True):
    rows=load_rows(csvp); result={}
    for fname in FILES:
        m=core.parse_msbt(root/'EURen'/'msg'/fname);core.roundtrip_self_test(m)
        src=[core.raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw]
        new=[];problems=[]
        for i,label in enumerate(m.labels_by_index):
            r=rows.get((fname,label))
            if r is None: problems.append(f'{fname}/{label}: missing row');new.append(src[i]);continue
            tr=r.get('Turkish','')
            if not core.visible_text(src[i]): tr=src[i]
            elif not tr:
                problems.append(f'{fname}/{label}: missing Turkish'); tr=src[i]
            if not controls_compatible(src[i],tr): problems.append(f'{fname}/{label}: control mismatch')
            try: core.csv_text_to_raw(tr,m.endian,m.encoding)
            except Exception as e: problems.append(f'{fname}/{label}: encode {e}')
            new.append(tr)
        if strict and problems: raise ValueError('\n'.join(problems[:100]))
        data=core.build_msbt(m,new)
        dest=out_romfs/'EURen'/'msg'/fname;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        chk=core.parse_msbt(dest); got=[core.raw_to_csv_text(r,chk.endian,chk.encoding) for r in chk.texts_raw]
        if got!=new: raise AssertionError(fname+' post-build mismatch')
        result[fname]={'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'issues':len(problems)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result

def validate(root:Path,csvp:Path,font:Path|None=None):
    rows=load_rows(csvp);metrics=core.load_metrics(font)
    counts={'total':0,'source_nonempty':0,'translated_nonempty':0,'empty_missing':0,'control_mismatch':0,'encoding_error':0,
            'fit_review':0,'fit_risk':0,'line_count_overflow':0,'two_line_overflow':0,'source_2line_to_3plus':0,'unknown_glyph':0}
    issues=[]; required=set(); sourcechars=set()
    for fname in FILES:
        ms={k:core.parse_msbt(p) for k,p in side_paths(root,fname).items()}
        eng=ms['English']; dec={k:[core.raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw] for k,m in ms.items()}
        for i,label in enumerate(eng.labels_by_index):
            counts['total']+=1; src=dec['English'][i];r=rows.get((fname,label),{});tr=r.get('Turkish','')
            sourcechars.update(ch for ch in core.visible_text(src) if ch not in '\n\r\t')
            if core.visible_text(src): counts['source_nonempty']+=1
            if tr: counts['translated_nonempty']+=1
            elif core.visible_text(src): counts['empty_missing']+=1;issues.append((fname,label,'EMPTY','missing'))
            if tr and not controls_compatible(src,tr): counts['control_mismatch']+=1;issues.append((fname,label,'CONTROL','inventory/structure'))
            if tr:
                try: core.csv_text_to_raw(tr,eng.endian,eng.encoding)
                except Exception as e: counts['encoding_error']+=1;issues.append((fname,label,'ENCODING',str(e)))
                required.update(ch for ch in core.visible_text(tr) if ch not in '\n\r\t')
            if metrics and tr:
                ost=[metrics.text_stats(dec[k][i]) for k in LANGS]
                ml=max(x[0] for x in ost); mp=max(x[1] for x in ost); tl,tp,_=metrics.text_stats(tr)
                if tl>ml:
                    counts['line_count_overflow']+=1;issues.append((fname,label,'LINE_COUNT',f'{tl}>{ml}'))
                src_lines=metrics.text_stats(src)[0]
                if ml==2 and (tl>2 or tp>mp):
                    counts['two_line_overflow']+=1;issues.append((fname,label,'TWO_LINE',f'{tl} lines/{tp}px > 2/{mp}px'))
                if src_lines<=2 and tl>2:
                    counts['source_2line_to_3plus']+=1;issues.append((fname,label,'SOURCE_2LINE_TO_3PLUS',f'English {src_lines} line(s), Turkish {tl} lines'))
                ratio=tp/mp if mp else 1
                if tl>ml+1 or ratio>1.20: counts['fit_risk']+=1;issues.append((fname,label,'FIT_RISK',f'{tl}/{tp} vs {ml}/{mp} ratio {ratio:.2f}'))
                elif tl>ml or ratio>1.05: counts['fit_review']+=1;issues.append((fname,label,'FIT_REVIEW',f'{tl}/{tp} vs {ml}/{mp} ratio {ratio:.2f}'))
    if metrics:
        missing=sorted(ch for ch in required if ord(ch) not in metrics.glyph_by_code and ch not in sourcechars)
        counts['unknown_glyph']=len(missing)
        if missing: issues.append(('*','*','GLYPH',''.join(missing)))
    rep={'counts':counts,'issues':[{'file':a,'label':b,'kind':c,'detail':d} for a,b,c,d in issues]}
    print(json.dumps(rep,ensure_ascii=False,indent=2));return rep

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('export');p.add_argument('--romfs',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);p.add_argument('--font',type=Path);p.add_argument('--merge',type=Path);p.add_argument('--seed-pullblox',type=Path)
    p=sp.add_parser('inject');p.add_argument('--romfs',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);p.add_argument('--out-romfs',type=Path,required=True);p.add_argument('--non-strict',action='store_true')
    p=sp.add_parser('validate');p.add_argument('--romfs',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);p.add_argument('--font',type=Path);p.add_argument('--json',type=Path)
    a=ap.parse_args()
    if a.cmd=='export': export(a.romfs,a.csv,a.font,a.merge,a.seed_pullblox)
    elif a.cmd=='inject': inject(a.romfs,a.csv,a.out_romfs,not a.non_strict)
    else:
        rep=validate(a.romfs,a.csv,a.font)
        if a.json: a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
