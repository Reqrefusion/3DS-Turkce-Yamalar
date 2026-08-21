#!/usr/bin/env python3
"""Independent technical verifier for a translated MSBT tree.

Checks each MSBT's header/file size, 16-byte section traversal, LBL1/TXT2
integrity, label indices, TXT2 offsets/terminators and inline-control bounds.
With --reference-root, also requires identical label/index mapping, identical
non-TXT2 sections and identical inline MSBT control sequences to the reference.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, struct
from pathlib import Path


def u16(b,o,e): return struct.unpack_from(e+'H',b,o)[0]
def u32(b,o,e): return struct.unpack_from(e+'I',b,o)[0]

def parse(path:Path):
    b=path.read_bytes()
    if len(b)<0x20 or b[:8]!=b'MsgStdBn': raise ValueError('Bad MSBT magic/size')
    if b[8:10]==b'\xff\xfe': e='<'
    elif b[8:10]==b'\xfe\xff': e='>'
    else: raise ValueError('Bad BOM')
    enc=b[0x0c]; count=u16(b,0x0e,e); declared=u32(b,0x12,e)
    if declared!=len(b): raise ValueError(f'Declared size {declared} != actual {len(b)}')
    pos=0x20; sections=[]
    for si in range(count):
        if pos%16: raise ValueError(f'Section {si} not 16-byte aligned')
        if pos+16>len(b): raise ValueError('Section header outside file')
        try: magic=b[pos:pos+4].decode('ascii','strict')
        except Exception: raise ValueError('Non-ASCII section magic')
        size=u32(b,pos+4,e); start=pos+16; end=start+size
        if end>len(b): raise ValueError(f'{magic} section outside file')
        nxt=(end+15)&~15
        if nxt>len(b): raise ValueError(f'{magic} padding outside file')
        sections.append((magic,b[start:end],b[pos:pos+16],b[end:nxt],pos))
        pos=nxt
    if pos!=len(b): raise ValueError(f'Section traversal ended at {pos}, file size {len(b)}')
    smap={}
    for magic,data,header,pad,p in sections:
        if magic in smap: raise ValueError(f'Duplicate section {magic}')
        smap[magic]=data
    if 'TXT2' not in smap: raise ValueError('TXT2 missing')
    labels={}
    if 'LBL1' in smap:
        s=smap['LBL1']
        if len(s)<4: raise ValueError('Short LBL1')
        gc=u32(s,0,e); table_end=4+gc*8
        if table_end>len(s): raise ValueError('LBL1 group table outside section')
        for i in range(gc):
            n=u32(s,4+i*8,e); p=u32(s,8+i*8,e)
            if p>len(s): raise ValueError('LBL1 group offset outside section')
            for _ in range(n):
                if p>=len(s): raise ValueError('LBL1 label outside section')
                nl=s[p]; p+=1
                if p+nl+4>len(s): raise ValueError('Truncated LBL1 label')
                name=s[p:p+nl].decode('ascii','strict'); p+=nl
                idx=u32(s,p,e);p+=4
                if name in labels: raise ValueError(f'Duplicate label {name}')
                labels[name]=idx
    t=smap['TXT2']
    if len(t)<4: raise ValueError('Short TXT2')
    tc=u32(t,0,e); table_end=4+tc*4
    if table_end>len(t): raise ValueError('TXT2 table outside section')
    offs=[u32(t,4+i*4,e) for i in range(tc)]
    if offs!=sorted(offs): raise ValueError('TXT2 offsets not sorted')
    if any(o<table_end or o>len(t) for o in offs): raise ValueError('TXT2 offset out of bounds')
    texts=[]
    for i,st in enumerate(offs):
        en=offs[i+1] if i+1<tc else len(t)
        if st>en: raise ValueError('TXT2 reversed range')
        raw=t[st:en]; texts.append(raw)
        if enc==1:
            if len(raw)%2: raise ValueError(f'TXT2 string {i} has odd byte length')
            if not raw.endswith(b'\x00\x00'): raise ValueError(f'TXT2 string {i} missing UTF-16 terminator')
            # Validate control bounds while scanning 16-bit units.
            q=0
            while q+2<=len(raw):
                code=u16(raw,q,e)
                if code==0x000e:
                    if q+8>len(raw): raise ValueError(f'Truncated control header in string {i}')
                    plen=u16(raw,q+6,e); end=q+8+plen
                    if end>len(raw): raise ValueError(f'Control payload outside string {i}')
                    q=end
                else: q+=2
        elif enc==0:
            if not raw.endswith(b'\x00'): raise ValueError(f'TXT2 string {i} missing UTF-8 terminator')
        else: raise ValueError(f'Unsupported encoding byte {enc}')
    if any(idx>=tc for idx in labels.values()): raise ValueError('LBL1 index outside TXT2')
    return dict(path=path,b=b,e=e,enc=enc,count=count,sections=sections,smap=smap,labels=labels,texts=texts)

def controls(m, raw):
    if m['enc']!=1: return []
    e=m['e']; out=[]; q=0
    while q+2<=len(raw):
        code=u16(raw,q,e)
        if code==0x000e:
            group=u16(raw,q+2,e); typ=u16(raw,q+4,e); plen=u16(raw,q+6,e); end=q+8+plen
            out.append((group,typ,raw[q+8:end]))
            q=end
        else:q+=2
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('translated_root',type=Path);ap.add_argument('--reference-root',type=Path);ap.add_argument('--csv',type=Path)
    a=ap.parse_args()
    files=sorted(a.translated_root.rglob('*.msbt'))
    rows=[]; errors=[]; texts_total=0
    for p in files:
        rel=p.relative_to(a.translated_root)
        row={'MSBT':rel.as_posix(),'OK':'EVET','Texts':'','Labels':'','Reference_Label_Map':'','Non_TXT2_Sections':'','Control_Sequences':''}
        try:
            m=parse(p); texts_total+=len(m['texts']);row['Texts']=len(m['texts']);row['Labels']=len(m['labels'])
            if a.reference_root:
                q=a.reference_root/rel
                if not q.exists(): raise ValueError('Reference file missing')
                r=parse(q)
                row['Reference_Label_Map']='EVET' if m['labels']==r['labels'] else 'HAYIR'
                asec=[(x[0],x[1]) for x in m['sections'] if x[0]!='TXT2']; bsec=[(x[0],x[1]) for x in r['sections'] if x[0]!='TXT2']
                row['Non_TXT2_Sections']='EVET' if asec==bsec else 'HAYIR'
                ctrl_ok=len(m['texts'])==len(r['texts']) and all(controls(m,x)==controls(r,y) for x,y in zip(m['texts'],r['texts']))
                row['Control_Sequences']='EVET' if ctrl_ok else 'HAYIR'
                if row['Reference_Label_Map']!='EVET' or row['Non_TXT2_Sections']!='EVET' or row['Control_Sequences']!='EVET': raise ValueError('Reference structural comparison failed')
        except Exception as ex:
            row['OK']='HAYIR'; errors.append(f'{rel}: {ex}')
        rows.append(row)
    if a.csv:
        a.csv.parent.mkdir(parents=True,exist_ok=True)
        with a.csv.open('w',encoding='utf-8-sig',newline='') as h:
            w=csv.DictWriter(h,fieldnames=list(rows[0].keys()) if rows else ['MSBT','OK']);w.writeheader();w.writerows(rows)
    summary={'files':len(files),'texts':texts_total,'errors':len(errors),'all_ok':not errors}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for e in errors[:50]: print(e)
    raise SystemExit(0 if not errors else 1)

if __name__=='__main__': main()
