#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,hashlib,re
from collections import Counter
from pathlib import Path
import fullblox_core as core

FILES=['cec.msbt','common.msbt','course.msbt','demo.msbt','dialog.msbt','edit.msbt','event.msbt','guide.msbt','menu.msbt','play.msbt','result.msbt','sale.msbt','staff.msbt']
LANGS={'English':'EURen','German':'EURde','Spanish':'EURes','French':'EURfr','Italian':'EURit'}
BUTTON_TAG_RE=re.compile(r'⟦TAG:0004:0002:[0-9A-Fa-f]+⟧')

def metric_text(s:str)->str:
    # Button controls draw a visible icon even though visible_text() removes controls.
    # Represent each as one conservative 32px system glyph for width checks.
    return BUTTON_TAG_RE.sub('\ue000', s)

def path(root:Path,lang:str,fname:str): return root/'msg'/lang/fname

def rows_by_key(csvp:Path):
    d={}
    with csvp.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): d[(r['file'],r['label'])]=r
    return d

def control_structure_valid(text:str)->bool:
    sig=core.control_signature(text)
    end_types={(g,t) for kind,g,t,args in sig if kind=='END'}
    st=[]
    for kind,g,t,args in sig:
        key=(g,t)
        if kind=='TAG' and key in end_types: st.append(key)
        elif kind=='END':
            if not st or st[-1]!=key: return False
            st.pop()
    return not st

def controls_compatible(src:str,tr:str)->bool:
    return Counter(core.control_signature(src))==Counter(core.control_signature(tr)) and control_structure_valid(tr)

def load_all(root:Path,fname:str):
    ms={k:core.parse_msbt(path(root,v,fname)) for k,v in LANGS.items()}
    eng=ms['English']
    for lang,m in ms.items():
        core.roundtrip_self_test(m)
        if m.labels_by_index!=eng.labels_by_index: raise ValueError(f'{fname}/{lang}: labels differ')
    dec={k:[core.raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw] for k,m in ms.items()}
    return ms,dec

def inject(root:Path,csvp:Path,out_romfs:Path,strict=True):
    rows=rows_by_key(csvp); result={}
    for fname in FILES:
        m=core.parse_msbt(path(root,'EURen',fname));core.roundtrip_self_test(m)
        src=[core.raw_to_csv_text(r,m.endian,m.encoding) for r in m.texts_raw]
        new=[];problems=[]
        for i,label in enumerate(m.labels_by_index):
            r=rows.get((fname,label)); tr=(r or {}).get('Turkish','')
            if not core.visible_text(src[i]):
                # Keep pure dynamic/control messages from the CSV if present, otherwise source.
                tr=tr or src[i]
            elif not tr:
                problems.append(f'{fname}/{label}: missing Turkish');tr=src[i]
            if not controls_compatible(src[i],tr): problems.append(f'{fname}/{label}: control mismatch')
            try: core.csv_text_to_raw(tr,m.endian,m.encoding)
            except Exception as e: problems.append(f'{fname}/{label}: encode {e}')
            new.append(tr)
        if strict and problems: raise ValueError('\n'.join(problems[:200]))
        data=core.build_msbt(m,new)
        dest=out_romfs/'msg'/'EURen'/fname;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        chk=core.parse_msbt(dest); got=[core.raw_to_csv_text(r,chk.endian,chk.encoding) for r in chk.texts_raw]
        if got!=new: raise AssertionError(fname+' post-build mismatch')
        result[fname]={'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'issues':len(problems)}
    print(json.dumps(result,ensure_ascii=False,indent=2)); return result

def validate(root:Path,csvp:Path,font:Path|None=None):
    rows=rows_by_key(csvp); metrics=core.load_metrics(font)
    counts={'total':0,'source_nonempty':0,'translated_nonempty':0,'empty_missing':0,'control_mismatch':0,'encoding_error':0,
            'unknown_glyph':0,'line_count_overflow':0,'source_2line_to_3plus':0,'two_line_overflow':0,'fit_review':0,'fit_risk':0,
            'button_suffix_overlap_risk':0,'multi_line_width_overflow':0}
    issues=[];required=set();sourcechars=set()
    for fname in FILES:
        ms,dec=load_all(root,fname); eng=ms['English']
        for i,label in enumerate(eng.labels_by_index):
            counts['total']+=1;src=dec['English'][i];r=rows.get((fname,label),{});tr=r.get('Turkish','')
            sv=core.visible_text(src);tv=core.visible_text(tr)
            sourcechars.update(ch for ch in sv if ch not in '\r\n\t')
            if sv: counts['source_nonempty']+=1
            if tr: counts['translated_nonempty']+=1
            elif sv: counts['empty_missing']+=1;issues.append((fname,label,'EMPTY','missing'))
            if tr and not controls_compatible(src,tr): counts['control_mismatch']+=1;issues.append((fname,label,'CONTROL','inventory/structure'))
            if tr:
                try: core.csv_text_to_raw(tr,eng.endian,eng.encoding)
                except Exception as e: counts['encoding_error']+=1;issues.append((fname,label,'ENCODING',str(e)))
                required.update(ch for ch in tv if ch not in '\r\n\t')
                # Fullblox renders button icons as controls. Avoid suffix/punctuation glued directly to the icon control.
                if re.search(r'⟦TAG:0004:0002:[0-9A-Fa-f]+⟧[\'’][A-Za-zÇĞİÖŞÜçğıöşü]',tr):
                    counts['button_suffix_overlap_risk']+=1;issues.append((fname,label,'BUTTON_SUFFIX','suffix glued to button icon'))
            if metrics and tr:
                ost=[metrics.text_stats(metric_text(dec[k][i])) for k in LANGS]
                eng_lines,eng_px,_=ost[0]; official_lines=max(x[0] for x in ost); official_px=max(x[1] for x in ost)
                # Prefer width budget from official languages using no more lines than Turkish target/source box.
                tl,tp,_=metrics.text_stats(metric_text(tr))
                if tl>official_lines:
                    counts['line_count_overflow']+=1;issues.append((fname,label,'LINE_COUNT',f'{tl}>{official_lines}'))
                if eng_lines<=2 and tl>2:
                    counts['source_2line_to_3plus']+=1;issues.append((fname,label,'SOURCE_2LINE_TO_3PLUS',f'English {eng_lines}, Turkish {tl}'))
                same_budget=[x[1] for x in ost if x[0]<=max(eng_lines,2)]
                strict_px=max(same_budget) if same_budget else official_px
                if eng_lines==2 and (tl>2 or tp>strict_px):
                    counts['two_line_overflow']+=1;issues.append((fname,label,'TWO_LINE',f'{tl} lines/{tp}px > 2/{strict_px}px'))
                # Any multi-line UI text must fit within the widest line that an
                # official localization actually uses for this same message.
                # No percentage tolerance: the game can auto-wrap on a difference
                # of only a few pixels and create an unintended extra line.
                if official_lines>1 and tp>official_px:
                    counts['multi_line_width_overflow']+=1;issues.append((fname,label,'MULTI_LINE_WIDTH',f'{tp}px > official {official_px}px'))
                ratio=tp/official_px if official_px else 1
                if tl>official_lines+1 or ratio>1.20:
                    counts['fit_risk']+=1;issues.append((fname,label,'FIT_RISK',f'{tl}/{tp} vs {official_lines}/{official_px} ratio {ratio:.2f}'))
                elif tl>official_lines or ratio>1.05:
                    counts['fit_review']+=1;issues.append((fname,label,'FIT_REVIEW',f'{tl}/{tp} vs {official_lines}/{official_px} ratio {ratio:.2f}'))
    if metrics:
        missing=sorted(ch for ch in required if ord(ch) not in metrics.glyph_by_code and ch not in sourcechars and not (0xE000<=ord(ch)<=0xE07E))
        counts['unknown_glyph']=len(missing)
        if missing: issues.append(('*','*','GLYPH',''.join(missing)))
    rep={'counts':counts,'issues':[{'file':a,'label':b,'kind':c,'detail':d} for a,b,c,d in issues]}
    print(json.dumps(rep,ensure_ascii=False,indent=2));return rep

def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('inject');p.add_argument('--romfs',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);p.add_argument('--out-romfs',type=Path,required=True);p.add_argument('--non-strict',action='store_true')
    p=sp.add_parser('validate');p.add_argument('--romfs',type=Path,required=True);p.add_argument('--csv',type=Path,required=True);p.add_argument('--font',type=Path);p.add_argument('--json',type=Path)
    a=ap.parse_args()
    if a.cmd=='inject': inject(a.romfs,a.csv,a.out_romfs,not a.non_strict)
    else:
        rep=validate(a.romfs,a.csv,a.font)
        if a.json: a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__': main()
