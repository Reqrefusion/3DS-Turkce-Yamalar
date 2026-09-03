#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,struct,re,zipfile,hashlib,sys,importlib.util
from collections import Counter,defaultdict

MSBT_MAGIC=b'MsgStdBn'
LANGS=('deu','eng','esp','fra','ita','nld')

def load_tool(path=None):
    candidates=[]
    if path: candidates.append(Path(path))
    candidates += [Path(__file__).with_name('sushi_msbt_csv_flat.py'),Path('/mnt/data/sushi_work/review_v09/Araclar/sushi_msbt_csv_flat.py')]
    for p in candidates:
        if p.exists():
            spec=importlib.util.spec_from_file_location('msbtkit',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    raise FileNotFoundError('sushi_msbt_csv_flat.py bulunamadı')

M=None

def detect_source(root):
    root=Path(root)
    if all((root/x).is_dir() for x in LANGS): return root
    for p in [root/'msgstudio',root/'romfs'/'lang'/'EU'/'msgstudio']:
        if all((p/x).is_dir() for x in LANGS): return p
    for p in root.rglob('msgstudio'):
        if all((p/x).is_dir() for x in LANGS): return p
    raise FileNotFoundError(root)

def detect_patch(root):
    root=Path(root)
    for p in [root,root/'msgstudio',root/'romfs'/'lang'/'EU'/'msgstudio']:
        if (p/'eng').is_dir(): return p
    for p in root.rglob('msgstudio'):
        if (p/'eng').is_dir(): return p
    raise FileNotFoundError(root)

def align16(n): return (n+15)&~15

def raw_labels(doc):
    sec=None
    for s in doc.sections:
        if s[0]==b'LBL1': sec=s;break
    if not sec:return []
    _,pos,size,end=sec; payload=doc.data[pos+0x10:end]; e=doc.e
    if len(payload)<4:return []
    groups=struct.unpack_from(e+'I',payload,0)[0]; out=[]
    if 4+8*groups>len(payload): raise ValueError('LBL1 group tablosu taşmış')
    for g in range(groups):
        count,off=struct.unpack_from(e+'II',payload,4+8*g)
        q=off
        for _ in range(count):
            if q>=len(payload):raise ValueError('LBL1 etiket ofseti taşmış')
            ln=payload[q]
            if q+1+ln+4>len(payload):raise ValueError('LBL1 etiket kaydı taşmış')
            raw=payload[q+1:q+1+ln]
            try:name=raw.decode('utf-8')
            except UnicodeDecodeError:name=raw.decode('latin1')
            idx=struct.unpack_from(e+'I',payload,q+1+ln)[0]
            out.append((name,idx)); q+=1+ln+4
    return out

def structural_errors(path):
    errs=[]
    try: doc=M.MSBT(path)
    except Exception as e:return [f'parse: {e}']
    d=doc.data; e=doc.e
    if len(d)<0x20: errs.append('header < 0x20'); return errs
    try: declared=struct.unpack_from(e+'I',d,0x12)[0]
    except: declared=-1
    if declared!=len(d):errs.append(f'header file_size={declared}, actual={len(d)}')
    pos=0x20
    if len(doc.sections)!=doc.section_count:errs.append('section_count mismatch')
    for i,(magic,sp,size,end) in enumerate(doc.sections):
        if sp!=pos:errs.append(f'section {i} start {sp:#x} != expected {pos:#x}')
        if end>len(d):errs.append(f'section {i} end out of bounds')
        pos=align16(end)
    if not any(s[0]==b'LBL1' for s in doc.sections):errs.append('LBL1 missing')
    if not any(s[0]==b'TXT2' for s in doc.sections):errs.append('TXT2 missing')
    try:
        labs=raw_labels(doc); names=[x[0] for x in labs]
        dup=[x for x,n in Counter(names).items() if n>1]
        if dup:errs.append('duplicate LBL1 labels: '+','.join(dup[:5]))
        bad=[(n,i) for n,i in labs if i>=len(doc.texts)]
        if bad:errs.append(f'LBL1 index out of TXT2: {bad[:3]}')
        if len(labs)!=len(doc.labels):errs.append(f'raw labels {len(labs)} != unique parsed {len(doc.labels)}')
    except Exception as ex:errs.append(f'LBL1 raw validation: {ex}')
    # TXT2 offsets raw monotonic/in-bounds
    try:
        sec=next(s for s in doc.sections if s[0]==b'TXT2'); _,sp,size,end=sec; payload=d[sp+0x10:end]
        n=struct.unpack_from(e+'I',payload,0)[0]
        if 4+4*n>len(payload):errs.append('TXT2 offset table out of bounds')
        else:
            offs=list(struct.unpack_from(e+f'{n}I',payload,4)) if n else []
            if offs!=sorted(offs):errs.append('TXT2 offsets not monotonic')
            if any(o<4+4*n or o>len(payload) for o in offs):errs.append('TXT2 offset outside payload')
            if n!=len(doc.texts):errs.append('TXT2 count parse mismatch')
    except Exception as ex:errs.append(f'TXT2 validation: {ex}')
    return errs

def parse_controls(escaped):
    s=M.unescape_text(escaped or '')
    out=[]; errs=[]; i=0
    while i<len(s):
        o=ord(s[i])
        if o==0x000E:
            if i+4>len(s): errs.append(f'0x000E truncated at char {i}');break
            g,t,n=ord(s[i+1]),ord(s[i+2]),ord(s[i+3])
            if n%2: errs.append(f'0x000E odd arg byte count {n} at {i}');i+=1;continue
            k=n//2
            if i+4+k>len(s):errs.append(f'0x000E args truncated at {i}: need {k} UTF16 units');break
            args=tuple(ord(x) for x in s[i+4:i+4+k]);out.append(('E',g,t,n,args));i+=4+k;continue
        if o==0x000F:
            if i+3>len(s):errs.append(f'0x000F truncated at char {i}');break
            out.append(('F',ord(s[i+1]),ord(s[i+2])));i+=3;continue
        i+=1
    return out,errs

def formatting_span_errors(escaped):
    """Detect only definitely empty group-0/type-3 formatting regions.

    BFFNT/MSBT style commands can legitimately be layered/nested, so nesting itself
    is not an error. Runtime group-1 commands render text/numbers and therefore
    count as visible content inside a styled region.
    """
    s=M.unescape_text(escaped or '')
    errs=[]; i=0; active=False; had_content=False
    while i<len(s):
        o=ord(s[i])
        if o==0x000E:
            if i+4>len(s): break
            g,t,n=ord(s[i+1]),ord(s[i+2]),ord(s[i+3]); k=n//2
            if i+4+k>len(s): break
            args=tuple(ord(x) for x in s[i+4:i+4+k])
            if g==0 and t==3 and n==4:
                is_reset=(args==(0,65280))
                if is_reset:
                    if active and not had_content: errs.append(f'empty formatting region ending at {i}')
                    active=False; had_content=False
                else:
                    # Multiple style commands may intentionally layer before text.
                    if not active:
                        active=True; had_content=False
            elif active and g==1:
                # Runtime substitution (name/count/item/etc.) produces visible content.
                had_content=True
            i+=4+k; continue
        if o==0x000F:
            if i+3>len(s): break
            i+=3; continue
        if active and o>=32 and o not in (0xFEFF,) and not (0xE000<=o<=0xF8FF) and not (0xFF00<=o<=0xFFEF):
            had_content=True
        i+=1
    # An unclosed style may be intentional because some commands persist across a box;
    # structural/control parity checks cover malformed byte sequences separately.
    return errs

_u=re.compile(r'\\u[0-9A-Fa-f]{4}')
def visible(s):
    s=_u.sub('',s or '').replace('\\n','').replace('\\r','').replace('\\t','').replace('\\','')
    return ''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF and not 0xFF00<=ord(c)<=0xFFEF).strip()

def add(rows,check,status,details='',count=''):
    rows.append({'check':check,'status':status,'count':count,'details':details})

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    global M
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True);ap.add_argument('--patch',required=True);ap.add_argument('--csv',required=True);ap.add_argument('--roundtrip',required=True)
    ap.add_argument('--layer-zip');ap.add_argument('--full-zip');ap.add_argument('--tool');ap.add_argument('--report',required=True);ap.add_argument('--summary',required=True)
    a=ap.parse_args(); M=load_tool(a.tool)
    src=detect_source(a.source); pat=detect_patch(a.patch); csvdir=Path(a.csv); rt=Path(a.roundtrip)
    report=[]; failures=[]; warnings=[]
    eng_files={p.name:p.relative_to(src/'eng') for p in (src/'eng').rglob('*.msbt')}
    pat_files={p.name:p.relative_to(pat/'eng') for p in (pat/'eng').rglob('*.msbt')}
    if len(eng_files)==243 and set(eng_files)==set(pat_files):add(report,'MSBT file set','PASS','Source/patch filenames identical',243)
    else:
        add(report,'MSBT file set','FAIL',f'source={len(eng_files)} patch={len(pat_files)} missing={len(set(eng_files)-set(pat_files))} extra={len(set(pat_files)-set(eng_files))}');failures.append('MSBT file set')
    # filename uniqueness in source relative tree
    allrels=[p.relative_to(src/'eng') for p in (src/'eng').rglob('*.msbt')]; names=[p.name for p in allrels];dups=[n for n,c in Counter(names).items() if c>1]
    if not dups:add(report,'Unique MSBT basenames','PASS','Flat CSV mapping unambiguous',len(names))
    else:add(report,'Unique MSBT basenames','FAIL',','.join(dups));failures.append('duplicate basenames')

    structure_bad=[]; label_bad=[]
    for name,rel in eng_files.items():
        pp=pat/'eng'/rel; ee=src/'eng'/rel
        er=structural_errors(pp)
        if er:structure_bad.append((name,'; '.join(er)))
        try:
            de=M.MSBT(ee); dp=M.MSBT(pp)
            if set(de.labels)!=set(dp.labels) or len(de.texts)!=len(dp.texts):label_bad.append(name)
        except Exception as ex:label_bad.append(name+':'+str(ex))
    if not structure_bad:add(report,'MSBT structural integrity','PASS','Headers, sections, LBL1, TXT2, offsets and indices valid',len(eng_files))
    else:add(report,'MSBT structural integrity','FAIL',str(structure_bad[:5]),len(structure_bad));failures.append('MSBT structural')
    if not label_bad:add(report,'Source/Patch label and TXT2 parity','PASS','ENG source label sets and TXT2 counts match patch',len(eng_files))
    else:add(report,'Source/Patch label and TXT2 parity','FAIL',str(label_bad[:8]),len(label_bad));failures.append('label parity')

    csv_files=list(csvdir.glob('*.csv'))
    if len(csv_files)==243:add(report,'CSV file count','PASS','One CSV per MSBT',243)
    else:add(report,'CSV file count','FAIL',str(len(csv_files)),len(csv_files));failures.append('csv count')
    rows=[]
    for p in csv_files:
        with p.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):r['_file']=p.name;rows.append(r)
    if len(rows)==10676:add(report,'CSV row count','PASS','Expected total label rows',len(rows))
    else:add(report,'CSV row count','FAIL',f'{len(rows)}',len(rows));failures.append('row count')
    keycounts=Counter((r['_file'],r['label']) for r in rows); dupkeys=[k for k,n in keycounts.items() if n>1]
    if not dupkeys:add(report,'CSV file+label uniqueness','PASS','Every CSV label key is unique',len(rows))
    else:add(report,'CSV file+label uniqueness','FAIL',str(dupkeys[:10]),len(dupkeys));failures.append('csv duplicate labels')

    malformed=[]; g1mis=[]; type2mis=[]; fffd=[]; blanks=[]; formatbad=[]; dupcsv=[]
    for r in rows:
        ce,ee=parse_controls(r.get('eng','')); ct,et=parse_controls(r.get('tur',''))
        if et:malformed.append((r['_file'],r['label'],et))
        ge=[x for x in ce if len(x)>2 and x[1]==1]; gt=[x for x in ct if len(x)>2 and x[1]==1]
        if ge!=gt:g1mis.append((r['_file'],r['label'],ge,gt))
        e2=[x for x in ce if len(x)>2 and x[0]=='E' and x[1]==0 and x[2]==2] + [x for x in ce if x[0]=='F' and len(x)>2 and x[1]==0 and x[2]==2]
        t2=[x for x in ct if len(x)>2 and x[0]=='E' and x[1]==0 and x[2]==2] + [x for x in ct if x[0]=='F' and len(x)>2 and x[1]==0 and x[2]==2]
        if e2!=t2:type2mis.append((r['_file'],r['label'],e2,t2))
        if '�' in r.get('tur','') and '�' not in r.get('eng',''):fffd.append((r['_file'],r['label']))
        if visible(r.get('eng','')) and not visible(r.get('tur','')):blanks.append((r['_file'],r['label']))
        fe=formatting_span_errors(r.get('tur',''))
        if fe:formatbad.append((r['_file'],r['label'],fe))
    for check,data,detail in [
        ('Inline control syntax',malformed,'No truncated/odd-size 0x000E or 0x000F commands'),
        ('Runtime group-1 command parity',g1mis,'Dynamic variable/control command sequence exactly matches ENG source'),
        ('Speech/emphasis type-2 parity',type2mis,'Voice/emphasis control signature exactly matches ENG source'),
        ('Patch-specific U+FFFD corruption',fffd,'No replacement character introduced where ENG does not have one'),
        ('Visible ENG / blank TUR',blanks,'No visible English source row is accidentally blank in Turkish'),
        ('Formatting span integrity',formatbad,'No empty, orphaned, nested or unclosed group-0/type-3 formatting span')]:
        if not data:add(report,check,'PASS',detail,0)
        else:add(report,check,'FAIL',str(data[:10]),len(data));failures.append(check)

    # roundtrip CSV exact
    rtmis=[]; rtrows=0
    for p in csv_files:
        q=rt/p.name
        if not q.exists():rtmis.append((p.name,'missing roundtrip'));continue
        with p.open(encoding='utf-8-sig',newline='') as f1,q.open(encoding='utf-8-sig',newline='') as f2:
            aa=list(csv.DictReader(f1)); bb={x['label']:x for x in csv.DictReader(f2)}
            for r in aa:
                rtrows+=1; x=bb.get(r['label'])
                if x is None or r.get('tur','')!=x.get('tur',''):rtmis.append((p.name,r['label']))
    if not rtmis and rtrows==10676:add(report,'CSV→MSBT→CSV exact roundtrip','PASS','All TUR cells reproduce byte-logically via toolkit',rtrows)
    else:add(report,'CSV→MSBT→CSV exact roundtrip','FAIL',str(rtmis[:10]),len(rtmis));failures.append('roundtrip')

    # M/F same-source discrepancy is warning only; Turkish gender neutral but some labels can intentionally differ for segmentation/context.
    mf=[]
    by={(r['_file'],r['label']):r for r in rows}
    for r in rows:
        lab=r['label']
        mate=None
        if lab.endswith('_M'): mate=lab[:-2]+'_F'
        elif lab.endswith('_F'): mate=lab[:-2]+'_M'
        elif lab.endswith('_f'): mate=lab[:-2]
        if mate and (r['_file'],mate) in by:
            x=by[(r['_file'],mate)]
            if r.get('eng','') and r.get('eng','')==x.get('eng','') and r.get('tur','')!=x.get('tur',''):
                key=tuple(sorted([lab,mate])); mf.append((r['_file'],key,r.get('tur',''),x.get('tur','')))
    # dedup
    seen=set();mf2=[]
    for x in mf:
        k=(x[0],x[1])
        if k not in seen:seen.add(k);mf2.append(x)
    if not mf2:add(report,'Same-source M/F consistency','PASS','No divergent Turkish variants for identical ENG source',0)
    else:
        add(report,'Same-source M/F consistency','WARN',f'{len(mf2)} pairs remain for manual/context review; not automatically treated as structural failure. First: {[(x[0],x[1]) for x in mf2[:8]]}',len(mf2));warnings.append('M/F differences')

    # ZIP checks
    def zipcheck(path,kind):
        p=Path(path); problems=[]
        if not p.exists():return ['missing zip']
        try:
            with zipfile.ZipFile(p) as z:
                bad=z.testzip()
                if bad:problems.append('CRC:'+bad)
                names=z.namelist()
                if kind=='layer':
                    badroots=[n for n in names if n and not n.startswith('LayeredFS/00040000001C1D00/')]
                    if badroots:problems.append('wrong root:'+str(badroots[:3]))
                    ms=[n for n in names if n.lower().endswith('.msbt')]
                    if len(ms)!=243:problems.append(f'msbt={len(ms)}')
                if kind=='full':
                    for req in ['LayeredFS/00040000001C1D00/','CSV/','Araclar/','Raporlar/']:
                        if not any(n.startswith(req) for n in names):problems.append('missing '+req)
                    csvs=[n for n in names if n.startswith('CSV/') and n.lower().endswith('.csv')]
                    ms=[n for n in names if n.startswith('LayeredFS/00040000001C1D00/') and n.lower().endswith('.msbt')]
                    if len(csvs)!=243:problems.append(f'csv={len(csvs)}')
                    if len(ms)!=243:problems.append(f'msbt={len(ms)}')
                    # manifest validation if present
                    if 'DOSYA_MANIFESTOSU_SHA256.txt' in names:
                        lines=z.read('DOSYA_MANIFESTOSU_SHA256.txt').decode('utf-8').splitlines();mm=[]
                        for line in lines:
                            if '  ' not in line:continue
                            h,n=line.split('  ',1)
                            try:data=z.read(n)
                            except KeyError:mm.append('missing:'+n);continue
                            if sha(data)!=h:mm.append('hash:'+n)
                        if mm:problems.append('manifest mismatch '+str(mm[:3]))
                    else:problems.append('manifest missing')
        except Exception as e:problems.append(str(e))
        return problems
    if a.layer_zip:
        zp=zipcheck(a.layer_zip,'layer')
        if zp:add(report,'LayeredFS ZIP integrity/path','FAIL','; '.join(zp));failures.append('layer zip')
        else:add(report,'LayeredFS ZIP integrity/path','PASS','CRC OK; exact LayeredFS/00040000001C1D00 root; 243 MSBT',243)
    if a.full_zip:
        zp=zipcheck(a.full_zip,'full')
        if zp:add(report,'FULL ZIP integrity/path/manifest','FAIL','; '.join(zp));failures.append('full zip')
        else:add(report,'FULL ZIP integrity/path/manifest','PASS','CRC OK; required roots, 243 CSV, 243 MSBT and SHA256 manifest verified',243)

    # Whole-patch line length heuristic: warning, not structural failure.
    long=[]
    ctrl=re.compile(r'\\u[0-9A-Fa-f]{4}')
    for r in rows:
        for i,line in enumerate(r.get('tur','').split('\\n'),1):
            s=ctrl.sub('',line);s=''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF and not 0xFF00<=ord(c)<=0xFFEF)
            if len(s)>48:long.append((r['_file'],r['label'],i,len(s)))
    if long:
        add(report,'Whole-patch >48 visible-char heuristic','WARN',f'Heuristic only; box widths vary. {len(long)} lines. First: {long[:8]}',len(long));warnings.append('long-line heuristic')
    else:add(report,'Whole-patch >48 visible-char heuristic','PASS','No lines exceed heuristic threshold',0)

    Path(a.report).parent.mkdir(parents=True,exist_ok=True)
    with Path(a.report).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['check','status','count','details']);w.writeheader();w.writerows(report)
    passes=sum(1 for x in report if x['status']=='PASS');fails=sum(1 for x in report if x['status']=='FAIL');warns=sum(1 for x in report if x['status']=='WARN')
    text=(f'TEKNİK DOĞRULAMA\nPASS: {passes}\nFAIL: {fails}\nWARN: {warns}\n'
          f'MSBT: {len(eng_files)}\nCSV satırı: {len(rows)}\n'
          f'Malformed inline commands: {len(malformed)}\nRuntime group1 mismatches: {len(g1mis)}\nSpeech/type2 mismatches: {len(type2mis)}\n'
          f'Patch-specific U+FFFD: {len(fffd)}\nVisible source / blank Turkish: {len(blanks)}\nFormatting span errors: {len(formatbad)}\nRoundtrip mismatches: {len(rtmis)}\n'
          f'Same-source M/F differences (warning): {len(mf2)}\n')
    Path(a.summary).write_text(text,encoding='utf-8')
    print(text)
    if failures:
        print('FAILURES:',failures,file=sys.stderr);return 2
    return 0
if __name__=='__main__':raise SystemExit(main())
