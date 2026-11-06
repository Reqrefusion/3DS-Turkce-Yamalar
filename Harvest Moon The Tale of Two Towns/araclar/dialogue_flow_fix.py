#!/usr/bin/env python3
import csv,re,json,math,sys
from pathlib import Path
BR='{BR}'; PAGE='{#232B}'
TOK_RE=re.compile(r'\{#[0-9A-Fa-f]{4}\}',re.I)
BR_RE=re.compile(r'\{BR\}',re.I); PAGE_RE=re.compile(r'\{#232B\}',re.I)
CHOICE_RE=re.compile(r'(?i)(?:\{#2332\}|\{BR\}|^)\s*(Yes|No)[.!]?(?=\{BR\}|$)')

def visible(s): return len(TOK_RE.sub('',s).strip())
def split_pages(s): return PAGE_RE.split(s)
def lines(p):
    xs=BR_RE.split(p)
    while len(xs)>1 and not xs[-1].strip(): xs.pop()
    return xs

def page_stat(p): return [visible(x) for x in lines(p) if visible(x)>0]

def normalize_words(p):
    # layout BRs become spaces; raw controls stay attached to nearby text
    s=BR_RE.sub(' ',p)
    s=re.sub(r'[ \t]+',' ',s).strip()
    return s.split(' ') if s else []

def word_vis(w): return len(TOK_RE.sub('',w))
def line_vis(ws): return sum(word_vis(w) for w in ws)+max(0,len(ws)-1)

def best_wrap_page(p,maxw=28,maxlines=3):
    ws=normalize_words(p)
    if not ws: return p
    n=len(ws)
    # if impossible due to a huge word, keep original
    if any(word_vis(w)>maxw for w in ws): return p
    # DP enumerate partitions for k 1..maxlines. Prefer few lines, then balance.
    best=None
    for k in range(1,maxlines+1):
        # recursive partitions
        def rec(start, left, cur):
            nonlocal best
            if left==1:
                seg=ws[start:]
                if not seg: return
                L=line_vis(seg)
                if L>maxw: return
                lens=[line_vis(x) for x in cur+[seg]]
                # avoid ugly tiny tails; strong penalty for lines < 8 if total has enough text
                avg=sum(lens)/len(lens)
                tiny=sum((8-L)**2 for L in lens if L<8 and sum(lens)>=22)
                rag=sum((L-avg)**2 for L in lens)
                # prefer final line not dramatically shorter than prior
                tail=max(0,(max(lens)-lens[-1])-10)**2
                score=(k, tiny*50+tail*5+rag)
                if best is None or score<best[0]: best=(score,cur+[seg])
                return
            # leave enough words
            for end in range(start+1, n-(left-1)+1):
                seg=ws[start:end]
                if line_vis(seg)>maxw: break
                rec(end,left-1,cur+[seg])
        rec(0,k,[])
        if best and best[0][0]==k: break
    if not best: return p
    return BR.join(' '.join(seg) for seg in best[1])

def boundary_has_sensitive_control(left,right):
    # Don't remove a page transition directly tied to expression/flow controls.
    # Formatting color codes 206C/206D/206E are allowed; variables are not.
    allow={'#206C','#206D','#206E'}
    lt=list(TOK_RE.finditer(left)); rt=list(TOK_RE.finditer(right))
    # look at immediate non-space edge content
    ltail=left.rstrip(); rhead=right.lstrip()
    m=re.search(r'(\{#[0-9A-Fa-f]{4}\})$',ltail,re.I)
    if m and m.group(1).upper()[1:-1] not in allow: return True
    m=re.match(r'^(\{#[0-9A-Fa-f]{4}\})',rhead,re.I)
    if m and m.group(1).upper()[1:-1] not in allow: return True
    return False

def remove_extra_orphan_pages(source,tr,maxw=28,maxlines=3):
    src_count=len(split_pages(source))
    pages=split_pages(tr)
    changed=False
    # Never touch choice/menu layout here.
    if '{#2332}' in tr.upper(): return tr,False,0
    # Only remove page breaks added by translation, and only if adjacent pages can fit in one page.
    removed=0
    while len(pages)>src_count:
        candidates=[]
        for i in range(len(pages)-1):
            a,b=pages[i],pages[i+1]
            if boundary_has_sensitive_control(a,b): continue
            sa,sb=page_stat(a),page_stat(b)
            # prioritize actual orphan/tiny pages
            orphan=(len(sa)==1 or len(sb)==1 or (sa and min(sa)<8) or (sb and min(sb)<8))
            if not orphan: continue
            merged=(BR_RE.sub(' ',a).rstrip()+' '+BR_RE.sub(' ',b).lstrip()).strip()
            wrapped=best_wrap_page(merged,maxw,maxlines)
            st=page_stat(wrapped)
            if st and len(st)<=maxlines and max(st)<=maxw:
                # score: shorter orphan gets priority
                small=min(sum(sa) if sa else 999,sum(sb) if sb else 999)
                candidates.append((small,i,wrapped))
        if not candidates: break
        _,i,wrapped=min(candidates,key=lambda x:x[0])
        pages=pages[:i]+[wrapped]+pages[i+2:]
        changed=True; removed+=1
    return PAGE.join(pages),changed,removed

def rebalance_existing_pages(source,tr,maxw=28,maxlines=3):
    if '{#2332}' in tr.upper(): return tr,False
    # only prose-like rows: source pages themselves max 3 rows
    if any(len(page_stat(p))>maxlines for p in split_pages(source)): return tr,False
    out=[]; ch=False
    for p in split_pages(tr):
        st=page_stat(p)
        if not st or len(st)>maxlines: out.append(p); continue
        w=best_wrap_page(p,maxw,maxlines)
        # Only accept if <= current lines or it removes a very short line; never create extra lines.
        old=page_stat(p); new=page_stat(w)
        if new and len(new)<=maxlines and max(new)<=maxw:
            oldtiny=sum(1 for x in old if x<8); newtiny=sum(1 for x in new if x<8)
            # Only touch genuinely ugly/overflowing pages; preserve normal author's pacing.
            if not (oldtiny>0 or max(old,default=0)>maxw):
                out.append(p); continue
            # Never collapse a multi-line page into a single line.
            if len(old)>=2 and len(new)<2:
                ws=normalize_words(p)
                best2=None
                n=len(ws)
                for cut in range(1,n):
                    a,b=ws[:cut],ws[cut:]; la,lb=line_vis(a),line_vis(b)
                    if la<=maxw and lb<=maxw:
                        sc=abs(la-lb)+20*sum(1 for z in (la,lb) if z<8)
                        if best2 is None or sc<best2[0]: best2=(sc,BR.join((' '.join(a),' '.join(b))))
                if best2: w=best2[1]; new=page_stat(w)
                else: out.append(p); continue
            if newtiny<oldtiny or (max(new,default=0)<max(old,default=0) and len(new)<=len(old)):
                out.append(w); ch|=(w!=p); continue
        out.append(p)
    return PAGE.join(out),ch

def match_source_pacing(source,tr,maxw=28):
    sp=split_pages(source); tp=split_pages(tr)
    if len(sp)!=len(tp) or '{#2332}' in tr.upper(): return tr,False
    out=[]; changed=False
    for s_page,t_page in zip(sp,tp):
        ss=page_stat(s_page); ts=page_stat(t_page)
        if len(ss)>=2 and len(ts)==1 and ts and ts[0]>=15:
            ws=normalize_words(t_page); best2=None
            for cut in range(1,len(ws)):
                a,b=ws[:cut],ws[cut:]; la,lb=line_vis(a),line_vis(b)
                if la<=maxw and lb<=maxw and min(la,lb)>=5:
                    sc=abs(la-lb) + 10*max(0,8-min(la,lb))
                    if best2 is None or sc<best2[0]: best2=(sc,BR.join((' '.join(a),' '.join(b))))
            if best2:
                out.append(best2[1]); changed=True; continue
        out.append(t_page)
    return PAGE.join(out),changed

def patch_blank_choice_translation(src):
    # Keep untranslated surrounding prose intact but localize global decision labels.
    t=src
    # Option phrases, only where they occur as BR/menu lines.
    reps=[
      (r'(?i)^\s*Yes!(?=\{BR\}|$)', 'Evet!'),
      (r'(?i)^\s*Yes\.(?=\{BR\}|$)', 'Evet.'),
      (r'(?i)^\s*Yes(?=\{BR\}|$)', 'Evet'),
      (r'(?i)^\s*No!(?=\{BR\}|$)', 'Hayır!'),
      (r'(?i)^\s*No\.(?=\{BR\}|$)', 'Hayır.'),
      (r'(?i)^\s*No(?=\{BR\}|$)', 'Hayır'),
      (r'(?i)(?<=\{#2332\}) Yes!', ' Evet!'),
      (r'(?i)(?<=\{#2332\}) Yes\.', ' Evet.'),
      (r'(?i)(?<=\{#2332\}) Yes(?=\{BR\}|$)', ' Evet'),
      (r'(?i)(?<=\{BR\}) Yes!(?=\{BR\}|$)', ' Evet!'),
      (r'(?i)(?<=\{BR\}) Yes\.(?=\{BR\}|$)', ' Evet.'),
      (r'(?i)(?<=\{BR\}) Yes(?=\{BR\}|$)', ' Evet'),
      (r'(?i)(?<=\{BR\}) No!(?=\{BR\}|$)', ' Hayır!'),
      (r'(?i)(?<=\{BR\}) No\.(?=\{BR\}|$)', ' Hayır.'),
      (r'(?i)(?<=\{BR\}) No(?=\{BR\}|$)', ' Hayır'),
      (r'(?i)(?<=\{BR\}) I changed my mind\.(?=\{BR\}|$)', ' Vazgeçtim.'),
      (r'(?i)(?<=\{BR\}) Never mind\.(?=\{BR\}|$)', ' Vazgeçtim.'),
      (r'(?i)(?<=\{BR\}) No thanks\.(?=\{BR\}|$)', ' Hayır, sağ ol.'),
      (r'(?i)(?<=\{BR\}) I\'m ready!(?=\{BR\}|$)', ' Hazırım!'),
      (r'(?i)(?<=\{BR\}) Okay!(?=\{BR\}|$)', ' Tamam!'),
    ]
    for pat,rep in reps: t=re.sub(pat,rep,t)
    return t

def process(inp,out,report):
    with open(inp,encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f); fields=r.fieldnames; rows=list(r)
    rep={'file':str(inp),'choice_blank_patched':0,'flow_changed':0,'pagebreaks_removed':0,'choice_rows_total':0,'choice_rows_english_after':0,'new_orphan_before':0,'new_orphan_after':0,'changes':[]}
    def orphan_count(s): return sum(1 for p in split_pages(s) if len(page_stat(p))==1 and page_stat(p))
    for row in rows:
        src=row['source']; tr=row.get('translation') or ''
        if CHOICE_RE.search(src): rep['choice_rows_total']+=1
        before=tr
        if not tr and CHOICE_RE.search(src):
            cand=patch_blank_choice_translation(src)
            if cand!=src:
                row['translation']=tr=cand; rep['choice_blank_patched']+=1
        if tr:
            src_or=orphan_count(src); tr_or=orphan_count(tr)
            if tr_or>src_or: rep['new_orphan_before'] += tr_or-src_or
            t2,did,removed=remove_extra_orphan_pages(src,tr)
            t3,did2=rebalance_existing_pages(src,t2)
            t4,did3=match_source_pacing(src,t3)
            if t4!=tr:
                row['translation']=t4; rep['flow_changed']+=1; rep['pagebreaks_removed']+=removed
                if len(rep['changes'])<300: rep['changes'].append({'id':row['id'],'before':tr,'after':t4,'removed_pages':removed})
                tr=t4
            tr_or2=orphan_count(tr)
            if tr_or2>src_or: rep['new_orphan_after'] += tr_or2-src_or
        # check choice English after
        trf=row.get('translation') or ''
        if CHOICE_RE.search(src) and trf and CHOICE_RE.search(trf): rep['choice_rows_english_after']+=1
    with open(out,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    Path(report).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in rep.items() if k!='changes'},ensure_ascii=False,indent=2))

if __name__=='__main__': process(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
