#!/usr/bin/env python3
# Rhythm Heaven Megamix TR localization helper
# Standard-library only. Handles the game's 4-byte-size+zlib SARC wrapper,
# MSBT text export/import and CTR BFFNT A4 bitmap-font Turkish glyph patching.

from __future__ import annotations
import argparse, csv, io, os, re, struct, sys, zlib, html, zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

TR_CHARS = "ÇĞİÖŞÜçğıöşü"
BASE_FOR = {
    'Ç':'C','Ğ':'G','İ':'I','Ö':'O','Ş':'S','Ü':'U',
    'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u',
}


def align(n:int, a:int)->int:
    return (n + a - 1) // a * a


def read_wrapped_zlib(path: Path) -> bytes:
    b = path.read_bytes()
    if len(b) < 6:
        raise ValueError(f"Too short: {path}")
    declared = int.from_bytes(b[:4], 'big')
    raw = zlib.decompress(b[4:])
    if declared != len(raw):
        raise ValueError(f"Size header mismatch in {path}: {declared} != {len(raw)}")
    return raw


def write_wrapped_zlib(raw: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack('>I', len(raw)) + zlib.compress(raw, 9))


@dataclass
class SarcNode:
    name: str
    node_pos: int
    start: int
    end: int


class Sarc:
    def __init__(self, raw: bytes):
        if raw[:4] != b'SARC':
            raise ValueError('Not a SARC')
        self.raw = raw
        self.endian = '<' if raw[6:8] == b'\xff\xfe' else '>'
        e = self.endian
        self.header_size = struct.unpack_from(e+'H', raw, 4)[0]
        self.data_offset = struct.unpack_from(e+'I', raw, 12)[0]
        if raw[self.header_size:self.header_size+4] != b'SFAT':
            raise ValueError('Missing SFAT')
        sfat_hsz, count, _ = struct.unpack_from(e+'HHI', raw, self.header_size+4)
        self.node_base = self.header_size + sfat_hsz
        sfnt_pos = self.node_base + count * 16
        if raw[sfnt_pos:sfnt_pos+4] != b'SFNT':
            raise ValueError('Missing SFNT')
        sfnt_hsz = struct.unpack_from(e+'H', raw, sfnt_pos+4)[0]
        str_base = sfnt_pos + sfnt_hsz
        self.nodes: List[SarcNode] = []
        for i in range(count):
            p = self.node_base + i*16
            _, noff, st, en = struct.unpack_from(e+'IIII', raw, p)
            if (noff >> 24) & 1:
                off = (noff & 0x00FFFFFF) * 4
                z = raw.find(b'\0', str_base+off)
                if z < 0: raise ValueError('Bad SARC filename')
                name = raw[str_base+off:z].decode('utf-8')
            else:
                name = f'__unnamed_{i:04d}'
            self.nodes.append(SarcNode(name, p, st, en))

    def files(self) -> Dict[str, bytes]:
        return {n.name: self.raw[self.data_offset+n.start:self.data_offset+n.end] for n in self.nodes}

    def rebuild(self, replacements: Dict[str, bytes], alignment:int=16) -> bytes:
        e = self.endian
        out = bytearray(self.raw[:self.data_offset])
        data = bytearray()
        original = self.files()
        for i, n in enumerate(self.nodes):
            if i:
                pad = align(len(data), alignment) - len(data)
                if pad: data += b'\0' * pad
            st = len(data)
            content = replacements.get(n.name, original[n.name])
            data += content
            en = len(data)
            struct.pack_into(e+'II', out, n.node_pos+8, st, en)
        out += data
        struct.pack_into(e+'I', out, 8, len(out))
        return bytes(out)


def msbt_sections(b: bytes) -> Tuple[str, List[Tuple[int,int,bytes]]]:
    if b[:8] != b'MsgStdBn':
        raise ValueError('Not MSBT')
    e = '<' if b[8:10] == b'\xff\xfe' else '>'
    count = struct.unpack_from(e+'H', b, 14)[0]
    pos = 0x20
    sections=[]
    for _ in range(count):
        if pos+16 > len(b): raise ValueError('Truncated MSBT section')
        sig=b[pos:pos+4]
        size=struct.unpack_from(e+'I', b, pos+4)[0]
        end=pos+16+size
        padded=align(end,16)
        sections.append((pos,padded,sig))
        pos=padded
    return e, sections


def parse_lbl1(b:bytes, e:str)->Dict[int,str]:
    pos=b.find(b'LBL1')
    if pos<0: return {}
    d=pos+16
    groups=struct.unpack_from(e+'I',b,d)[0]
    labels={}
    for g in range(groups):
        cnt,off=struct.unpack_from(e+'II',b,d+4+8*g)
        q=d+off
        for _ in range(cnt):
            ln=b[q]; q+=1
            name=b[q:q+ln].decode('utf-8'); q+=ln
            idx=struct.unpack_from(e+'I',b,q)[0];q+=4
            labels[idx]=name
    return labels


def parse_txt2_raw(b:bytes,e:str)->List[bytes]:
    pos=b.find(b'TXT2')
    if pos<0: raise ValueError('No TXT2')
    size=struct.unpack_from(e+'I',b,pos+4)[0]
    d=pos+16
    n=struct.unpack_from(e+'I',b,d)[0]
    offs=[struct.unpack_from(e+'I',b,d+4+4*i)[0] for i in range(n)]
    out=[]
    for i,o in enumerate(offs):
        st=d+o
        en=d+(offs[i+1] if i+1<n else size)
        raw=b[st:en]
        # Offsets delimit each null-terminated string. TXT2 section padding is outside
        # the declared data size, so remove exactly one UTF-16 terminator pair.
        if len(raw)>=2 and raw[-2:]==b'\0\0':
            raw=raw[:-2]
        out.append(raw)
    return out


def protected_tokens(text:str)->List[str]:
    return re.findall(r'\[\[(?:TAG|END|PUA):[^\]]+\]\]', text)


def raw_to_editable(raw:bytes,e:str='<')->str:
    enc='utf-16le' if e=='<' else 'utf-16be'
    out=[]; i=0; normal=bytearray()
    def flush():
        if normal:
            s=bytes(normal).decode(enc,'surrogatepass')
            s=s.replace('\\','\\\\').replace('\n','\\n').replace('\r','\\r').replace('\t','\\t')
            out.append(s); normal.clear()
    while i+1<len(raw):
        u=struct.unpack_from(e+'H',raw,i)[0]
        if u==0x000E and i+8<=len(raw):
            flush()
            group,typ,alen=struct.unpack_from(e+'HHH',raw,i+2)
            end=i+8+alen
            if end>len(raw):
                normal += raw[i:i+2]; i+=2; continue
            args=raw[i+8:end].hex().upper()
            out.append(f'[[TAG:{group:04X}:{typ:04X}:{args}]]')
            i=end; continue
        if u==0x000F and i+6<=len(raw):
            flush(); group,typ=struct.unpack_from(e+'HH',raw,i+2)
            out.append(f'[[END:{group:04X}:{typ:04X}]]'); i+=6; continue
        if 0xE000<=u<=0xF8FF:
            flush(); out.append(f'[[PUA:{u:04X}]]'); i+=2; continue
        normal += raw[i:i+2]; i+=2
    if i<len(raw): normal += raw[i:]
    flush()
    return ''.join(out)


def editable_to_raw(text:str,e:str='<')->bytes:
    enc='utf-16le' if e=='<' else 'utf-16be'
    out=bytearray(); i=0; plain=[]
    def flush_plain():
        if not plain:return
        s=''.join(plain); plain.clear()
        # Interpret only our explicit escapes.
        r=[]; j=0
        while j<len(s):
            if s[j]=='\\' and j+1<len(s):
                c=s[j+1]
                if c=='n':r.append('\n');j+=2;continue
                if c=='r':r.append('\r');j+=2;continue
                if c=='t':r.append('\t');j+=2;continue
                if c=='\\':r.append('\\');j+=2;continue
            r.append(s[j]);j+=1
        out.extend(''.join(r).encode(enc,'surrogatepass'))
    token_re=re.compile(r'\[\[(TAG|END|PUA):([^\]]+)\]\]')
    while i<len(text):
        m=token_re.match(text,i)
        if not m:
            plain.append(text[i]); i+=1; continue
        flush_plain(); kind,payload=m.group(1),m.group(2)
        if kind=='TAG':
            parts=payload.split(':',2)
            if len(parts)!=3: raise ValueError(f'Bad TAG token: {m.group(0)}')
            group=int(parts[0],16); typ=int(parts[1],16); args=bytes.fromhex(parts[2]) if parts[2] else b''
            out += struct.pack(e+'HHHH',0x000E,group,typ,len(args)) + args
        elif kind=='END':
            parts=payload.split(':')
            if len(parts)!=2: raise ValueError(f'Bad END token: {m.group(0)}')
            out += struct.pack(e+'HHH',0x000F,int(parts[0],16),int(parts[1],16))
        else:
            out += struct.pack(e+'H',int(payload,16))
        i=m.end()
    flush_plain(); return bytes(out)


def rebuild_msbt_txt2(b:bytes, new_raw:List[bytes])->bytes:
    e,secs=msbt_sections(b)
    txt_idx=None
    for i,(_,_,sig) in enumerate(secs):
        if sig==b'TXT2':txt_idx=i;break
    if txt_idx is None: raise ValueError('No TXT2')
    pos,padded,_=secs[txt_idx]
    d=bytearray()
    n=len(new_raw)
    d += struct.pack(e+'I',n)
    base=4+4*n
    cur=base
    for r in new_raw:
        d += struct.pack(e+'I',cur)
        cur += len(r)+2
    for r in new_raw:
        d += r+b'\0\0'
    sec=bytearray(b'TXT2'+struct.pack(e+'I',len(d))+b'\0'*8+d)
    sec += b'\0'*(align(len(sec),16)-len(sec))
    out=bytearray(b[:pos])+sec+bytearray(b[padded:])
    struct.pack_into(e+'I',out,18,len(out))
    return bytes(out)


def msbt_entries(b:bytes)->List[Tuple[int,str,str]]:
    e,_=msbt_sections(b)
    labels=parse_lbl1(b,e); raws=parse_txt2_raw(b,e)
    return [(i,labels.get(i,f'#{i}'),raw_to_editable(r,e)) for i,r in enumerate(raws)]


LANGUAGE_ORDER = ['English','French','German','Italian','Spanish','Turkish']


def _clean_xmsbt_reference(text:str)->str:
    # Old XMSBT exports encode MSBT control data as XML numeric references plus packed UTF-16 words.
    # For reference columns we keep readable prose and PUA icons, not binary control arguments.
    # Packed formatting arguments in old XMSBT exports often appear as a non-ASCII word + U+FF00.
    # Remove that pair before stripping numeric XML control references, so adjacent prose is untouched.
    text=re.sub(r'[^\x00-\x7F]\uFF00','',text)
    text=re.sub(r'&#x[0-9A-Fa-f]+;|&#[0-9]+;','',text)
    text=html.unescape(text).replace('\\0','')
    out=[]
    for ch in text:
        cp=ord(ch)
        if ch in '\r\n\t': out.append(ch); continue
        if 0xE000<=cp<=0xF8FF:
            out.append(f'[[PUA:{cp:04X}]]'); continue
        if cp==0xFFFD: continue
        # XMSBT control arguments can appear as arbitrary Hangul/CJK/full-width words.
        if cp>=0x3000: continue
        if cp<0x20: continue
        out.append(ch)
    return ''.join(out).replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')


def load_xmsbt_reference_zip(path:Path)->Dict[str,Dict[str,str]]:
    refs={}
    with zipfile.ZipFile(path,'r') as z:
        for member in z.namelist():
            if not member.lower().endswith('.xmsbt'): continue
            raw=z.read(member)
            text=raw.decode('utf-16')
            entries={}
            for m in re.finditer(r'<entry\s+label="([^"]+)">\s*<text>(.*?)</text>\s*</entry>',text,re.S):
                entries[m.group(1)]=_clean_xmsbt_reference(m.group(2))
            internal='arc/'+Path(member).stem+'.msbt'
            refs[internal]=entries
    return refs


def _entry_lookup(msbt:bytes):
    entries=msbt_entries(msbt)
    return entries, {lab:(idx,text) for idx,lab,text in entries}, {idx:(lab,text) for idx,lab,text in entries}


def _plain_for_qa(text:str)->str:
    return re.sub(r'\[\[[^\]]+\]\]','',text).replace('\\n',' ').strip()


def export_multilang(archives:Dict[str,Path], outdir:Path, english_xmsbt_zip:Path|None=None)->None:
    """Export one TSV per MSBT, mirroring EUENmessage/pajama_sarc/arc/*.msbt."""
    missing=[x for x in LANGUAGE_ORDER if x not in archives]
    if missing:
        raise ValueError('Missing language archive(s): '+', '.join(missing))
    loaded={lang:Sarc(read_wrapped_zlib(Path(path))).files() for lang,path in archives.items()}
    english_ref=load_xmsbt_reference_zip(english_xmsbt_zip) if english_xmsbt_zip else {}
    names=sorted(set().union(*[{n for n in fs if n.lower().endswith('.msbt')} for fs in loaded.values()]))
    base=outdir/'EUENmessage'/'pajama_sarc'
    base.mkdir(parents=True,exist_ok=True)
    total=0; flagged=0; file_stats=[]
    fields=['index','label',*LANGUAGE_ORDER,'status']
    for name in names:
        per={}
        for lang in LANGUAGE_ORDER:
            b=loaded[lang].get(name)
            per[lang]=_entry_lookup(b) if b is not None else ([],{}, {})
        # Turkish order is authoritative for injection. Add any source-only labels afterwards.
        ordered=[]; seen=set()
        for lang in ['Turkish','English','French','German','Italian','Spanish']:
            for idx,lab,text in per[lang][0]:
                if lab not in seen:
                    ordered.append((idx,lab));seen.add(lab)
        rows=[]; file_flagged=0
        for default_idx,lab in ordered:
            row={'index':default_idx,'label':lab}
            status=[]
            texts={}
            for lang in LANGUAGE_ORDER:
                entries,bylab,byidx=per[lang]
                if lab in bylab:
                    idx,text=bylab[lab]
                elif default_idx in byidx:
                    _lab,text=byidx[default_idx]
                    status.append('INDEX_FALLBACK_'+lang.upper())
                else:
                    text='';status.append('MISSING_'+lang.upper())
                if lang=='English':
                    qa_english=text
                    if name in english_ref and lab in english_ref[name]:
                        text=english_ref[name][lab]
                texts[lang]=text;row[lang]=text
            en=texts['English'];tr=texts['Turkish']
            if tr and en:
                if _plain_for_qa(en)==_plain_for_qa(tr) and re.search(r'[A-Za-z]{3}',_plain_for_qa(en)):
                    status.append('UNTRANSLATED')
                if protected_tokens(qa_english)!=protected_tokens(tr): status.append('CONTROL_DIFF_EN_TR')
                en_lines=en.split('\\n');tr_lines=tr.split('\\n')
                if max((len(x) for x in tr_lines),default=0) > max(30,int(max((len(x) for x in en_lines),default=1)*1.55)):
                    status.append('LONG_TR_LINE')
            if '\ufffd' in tr: status.append('BAD_TR_CHAR')
            row['status']=','.join(dict.fromkeys(status))
            if row['status']: file_flagged+=1
            rows.append(row)
        target=base/(name+'.tsv')
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',quoting=csv.QUOTE_MINIMAL)
            w.writeheader();w.writerows(rows)
        total+=len(rows);flagged+=file_flagged
        file_stats.append((name,len(rows),file_flagged))
    # Small manifest only; translations themselves remain split by original file.
    manifest=outdir/'PROJECT_INFO.txt'
    lines=[
        'Rhythm Heaven Megamix - multilingual split localization project',
        'Structure: EUENmessage/pajama_sarc/arc/<original>.msbt.tsv',
        'Columns: index, label, English, French, German, Italian, Spanish, Turkish, status',
        f'Total files: {len(names)}',f'Total rows: {total}',f'Rows flagged: {flagged}','',
        'Language sources:'
    ]
    lines += [f'  {lang}: {archives[lang]}' for lang in LANGUAGE_ORDER]
    if english_xmsbt_zip: lines.append(f'  English reference override (XMSBT): {english_xmsbt_zip}')
    lines += ['', 'Per-file counts:']+[f'  {n}: {cnt} rows, {flg} flagged' for n,cnt,flg in file_stats]
    manifest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Exported {total} rows across {len(names)} split TSV files -> {base}')
    print(f'Rows flagged: {flagged}')


def import_project_folder(source_tr_zlib:Path, project_dir:Path, out_zlib:Path)->None:
    """Inject Turkish column from recursively split *.msbt.tsv files."""
    sarc=Sarc(read_wrapped_zlib(source_tr_zlib)); files=sarc.files(); repl={};errors=[];changed_files=0
    tables=sorted(project_dir.rglob('*.msbt.tsv'))
    if not tables: raise ValueError(f'No *.msbt.tsv files under {project_dir}')
    for table in tables:
        # Everything after pajama_sarc/ mirrors the internal SARC name.
        parts=table.parts
        try:
            k=parts.index('pajama_sarc')
            internal='/'.join(parts[k+1:])[:-4]  # remove only trailing .tsv
        except ValueError:
            internal=table.name[:-4]
        if internal not in files:
            # Reference-only rows/files may exist in another language; do not make build impossible.
            continue
        changes={}
        with table.open('r',encoding='utf-8-sig',newline='') as f:
            rd=csv.DictReader(f,delimiter='\t')
            required={'label','Turkish'}
            if not required.issubset(set(rd.fieldnames or [])):
                errors.append(f'{table}: missing columns {sorted(required-set(rd.fieldnames or []))}')
                continue
            for row in rd:
                changes[row['label']]=row['Turkish']
        b=files[internal];e,_=msbt_sections(b);old=msbt_entries(b);oldraw=parse_txt2_raw(b,e);newraw=[];did=False
        labels={lab for _,lab,_ in old}
        for (idx,label,oldtext),raw in zip(old,oldraw):
            if label not in changes:
                newraw.append(raw);continue
            text=changes[label]
            if protected_tokens(text)!=protected_tokens(oldtext):
                errors.append(f'{internal}:{label}: protected token sequence changed')
                newraw.append(raw);continue
            try:
                nr=editable_to_raw(text,e);newraw.append(nr);did |= (nr!=raw)
            except Exception as ex:
                errors.append(f'{internal}:{label}: {ex}');newraw.append(raw)
        unknown=[lab for lab in changes if lab not in labels]
        # Unknown labels can be present because other official languages contain extra entries.
        # They are intentionally ignored instead of blocking the build.
        if did:
            repl[internal]=rebuild_msbt_txt2(b,newraw);changed_files+=1
    if errors:
        raise ValueError('Import aborted:\n'+'\n'.join(errors[:80])+('\n...' if len(errors)>80 else ''))
    raw=sarc.rebuild(repl);write_wrapped_zlib(raw,out_zlib)
    print(f'Built message archive -> {out_zlib} ({changed_files} MSBT files changed)')


# ---------- BFFNT ----------

def parse_cmap(b:bytes)->Dict[int,int]:
    out={};p=0
    while True:
        p=b.find(b'CMAP',p)
        if p<0:break
        size=struct.unpack_from('<I',b,p+4)[0]
        begin,end,method,_res,_next=struct.unpack_from('<HHHHI',b,p+8); d=p+20
        if method==0:
            start=struct.unpack_from('<H',b,d)[0]
            for cp in range(begin,end+1):out[cp]=start+cp-begin
        elif method==1:
            for cp in range(begin,end+1):
                idx=struct.unpack_from('<H',b,d+2*(cp-begin))[0]
                if idx!=0xFFFF:out[cp]=idx
        elif method==2:
            n=struct.unpack_from('<H',b,d)[0]
            for i in range(n):
                cp,idx=struct.unpack_from('<HH',b,d+2+4*i);out[cp]=idx
        p += max(4,size)
    return out


def morton8(x:int,y:int)->int:
    o=0
    for bit in range(3):
        o|=((x>>bit)&1)<<(2*bit)
        o|=((y>>bit)&1)<<(2*bit+1)
    return o


def decode_a4(data:bytes,w:int,h:int)->List[List[int]]:
    img=[[0]*w for _ in range(h)]
    tiles_per_row=w//8
    for y in range(h):
        for x in range(w):
            k=((y//8)*tiles_per_row+(x//8))*64+morton8(x&7,y&7)
            v=data[k//2]; img[y][x]=((v>>4)&15) if (k&1) else (v&15)
    return img


def encode_a4(img:List[List[int]],w:int,h:int)->bytes:
    out=bytearray(w*h//2); tiles_per_row=w//8
    for y in range(h):
        for x in range(w):
            k=((y//8)*tiles_per_row+(x//8))*64+morton8(x&7,y&7)
            v=max(0,min(15,int(img[y][x])))
            if k&1: out[k//2]=(out[k//2]&0x0F)|(v<<4)
            else: out[k//2]=(out[k//2]&0xF0)|v
    return bytes(out)


def crop_cell(img,cw,ch,cols,idx):
    x=(idx%cols)*(cw+1); y=(idx//cols)*(ch+1)
    return [row[x:x+cw] for row in img[y:y+ch]]


def paste_cell(img,cell,cw,ch,cols,idx):
    x=(idx%cols)*(cw+1); y=(idx//cols)*(ch+1)
    for yy in range(min(ch,len(cell))):
        for xx in range(min(cw,len(cell[yy]))):
            if 0<=y+yy<len(img) and 0<=x+xx<len(img[0]):img[y+yy][x+xx]=cell[yy][xx]


def bbox(cell):
    ys=[];xs=[]
    for y,row in enumerate(cell):
        for x,v in enumerate(row):
            if v:
                xs.append(x);ys.append(y)
    if not xs:return (0,0,max(0,len(cell[0])-1),max(0,len(cell)-1))
    return min(xs),min(ys),max(xs),max(ys)


def clone(cell):return [r[:] for r in cell]


def draw_dot(cell, two=False):
    c=clone(cell); cw=len(c[0]); ch=len(c); x0,y0,x1,y1=bbox(c)
    sz=max(2,round(min(cw,ch)/11)); yy=max(0,y0-sz-1)
    center=(x0+x1)//2
    centers=[center] if not two else [center-max(2,cw//8),center+max(2,cw//8)]
    for cx in centers:
        for y in range(yy,min(ch,yy+sz)):
            for x in range(max(0,cx-sz//2),min(cw,cx+(sz+1)//2)):
                c[y][x]=15
    return c


def draw_breve(cell):
    c=clone(cell); cw=len(c[0]); ch=len(c); x0,y0,x1,y1=bbox(c)
    width=max(5,(x1-x0+1)//2); height=max(2,ch//16); cx=(x0+x1)//2
    top=max(0,y0-height-2)
    # U-shaped breve: ends slightly higher, center lower.
    for dx in range(-width//2,width//2+1):
        frac=abs(dx)/(max(1,width/2))
        yy=top + int((1-frac)*height)
        for t in range(max(1,ch//28)):
            y=yy+t; x=cx+dx
            if 0<=x<cw and 0<=y<ch:c[y][x]=15
    return c


def draw_cedilla(cell, baseline:int):
    c=clone(cell); cw=len(c[0]); ch=len(c); x0,y0,x1,y1=bbox(c); cx=(x0+x1)//2
    y=max(baseline+1,y1+1); y=min(ch-1,y)
    pts=[]
    length=max(3,ch//9)
    for k in range(length):
        # starts centered, curves left, then back a bit
        dx=0 if k<2 else -(1+(k-2)//2)
        pts.append((cx+dx,y+k))
    for x,yy in pts:
        if yy>=ch:break
        for t in range(max(1,cw//24)):
            xx=x+t
            if 0<=xx<cw:c[yy][xx]=15
    return c


def remove_i_dot(cell):
    c=clone(cell); ch=len(c); cw=len(c[0])
    # Find an empty horizontal separator near the top; remove everything above it.
    row_has=[any(v for v in row) for row in c]
    first=next((i for i,v in enumerate(row_has) if v),0)
    sep=None
    for y in range(first+1,min(ch//2+3,ch)):
        if not row_has[y] and any(row_has[y+1:]): sep=y; break
    if sep is None: sep=max(first+2,ch//4)
    for y in range(0,sep+1):
        for x in range(cw):c[y][x]=0
    return c


def synthesize(base_cell,target,baseline):
    if target=='ı': return remove_i_dot(base_cell)
    if target=='İ': return draw_dot(base_cell,False)
    if target in ('Ö','ö','Ü','ü'):return draw_dot(base_cell,True)
    if target in ('Ğ','ğ'):return draw_breve(base_cell)
    if target in ('Ç','ç','Ş','ş'):return draw_cedilla(base_cell,baseline)
    return clone(base_cell)


def scale_cell(src,tw,th):
    sh=len(src); sw=len(src[0]); out=[[0]*tw for _ in range(th)]
    for y in range(th):
        sy=min(sh-1,int(y*sh/th))
        for x in range(tw):
            sx=min(sw-1,int(x*sw/tw)); out[y][x]=src[sy][sx]
    return out


def parse_font_info(b:bytes):
    if b[:4]!=b'FFNT' or b[4:6]!=b'\xff\xfe': raise ValueError('Only little-endian BFFNT supported')
    t=b.find(b'TGLP'); c=b.find(b'CWDH')
    if t<0 or c<0: raise ValueError('Missing TGLP/CWDH')
    q=t+8
    info={
        't':t,'q':q,'cwdh':c,'cw':b[q],'ch':b[q+1],'sheets':b[q+2],'maxw':b[q+3],
        'sheetSize':struct.unpack_from('<I',b,q+4)[0], 'baseline':b[q+8], 'fmt':struct.unpack_from('<H',b,q+10)[0],
        'cols':struct.unpack_from('<H',b,q+12)[0], 'rows':struct.unpack_from('<H',b,q+14)[0],
        'w':struct.unpack_from('<H',b,q+16)[0], 'h':struct.unpack_from('<H',b,q+18)[0],
        'dataoff':struct.unpack_from('<I',b,q+20)[0],
    }
    start,end=struct.unpack_from('<HH',b,c+8); info['metric_start']=start;info['metric_end']=end
    metrics=[]
    for idx in range(start,end+1):
        o=c+16+(idx-start)*3;metrics.append(bytes(b[o:o+3]))
    info['metrics']=metrics
    return info


def rebuild_cmap(mapping:Dict[int,int])->bytes:
    pairs=sorted(mapping.items())
    body=struct.pack('<HHHHI',0,0xFFFF,2,0,0)+struct.pack('<H',len(pairs))
    for cp,idx in pairs: body+=struct.pack('<HH',cp,idx)
    total=align(8+len(body),4)
    sec=bytearray(b'CMAP'+struct.pack('<I',total)+body)
    sec+=b'\0'*(total-len(sec));return bytes(sec)


def rebuild_cwdh(metrics:List[bytes])->bytes:
    body=struct.pack('<HHI',0,len(metrics)-1,0)+b''.join(metrics)
    total=align(8+len(body),4)
    sec=bytearray(b'CWDH'+struct.pack('<I',total)+body)
    sec+=b'\0'*(total-len(sec));return bytes(sec)


def patch_bffnt(b:bytes, fallback:Tuple[bytes,Dict[int,int]]|None=None):
    info=parse_font_info(b)
    if info['fmt']!=11 or info['sheets']!=1:
        return b,{'changed':False,'reason':f'unsupported fmt={info["fmt"]} sheets={info["sheets"]}'}
    mapping=parse_cmap(b)
    missing=[c for c in TR_CHARS if ord(c) not in mapping]
    if not missing:return b,{'changed':False,'added':'','fallback':''}
    old_end=info['metric_end']; needed=old_end+1+len(missing)
    nw,nh,ncols,nrows=info['w'],info['h'],info['cols'],info['rows']
    while ncols*nrows<needed:
        if nh<1024:
            nh*=2; nrows=nh//(info['ch']+1)
        elif nw<1024:
            nw*=2; ncols=nw//(info['cw']+1)
        else: raise ValueError('Font texture cannot be expanded further')
    olddata=b[info['dataoff']:info['dataoff']+info['sheetSize']]
    oldimg=decode_a4(olddata,info['w'],info['h'])
    newimg=[[0]*nw for _ in range(nh)]
    # Re-layout existing indexed cells so a changed column count remains valid.
    for idx in range(old_end+1):
        cell=crop_cell(oldimg,info['cw'],info['ch'],info['cols'],idx)
        paste_cell(newimg,cell,info['cw'],info['ch'],ncols,idx)
    metrics=list(info['metrics'])
    fallback_used=[]
    # Parse fallback font once.
    fb_info=fb_map=fb_img=None
    if fallback:
        fb_bytes,fb_map=fallback
        fb_info=parse_font_info(fb_bytes)
        fb_img=decode_a4(fb_bytes[fb_info['dataoff']:fb_info['dataoff']+fb_info['sheetSize']],fb_info['w'],fb_info['h'])
    nextidx=old_end+1
    for ch in missing:
        base=BASE_FOR[ch]; baseidx=mapping.get(ord(base))
        metric=None
        if baseidx is not None and baseidx<=old_end:
            basecell=crop_cell(newimg,info['cw'],info['ch'],ncols,baseidx)
            cell=synthesize(basecell,ch,info['baseline'])
            metric=metrics[baseidx]
        elif fb_map and ord(ch) in fb_map:
            fi=fb_map[ord(ch)]
            srccell=crop_cell(fb_img,fb_info['cw'],fb_info['ch'],fb_info['cols'],fi)
            cell=scale_cell(srccell,info['cw'],info['ch'])
            x0,y0,x1,y1=bbox(cell); gw=max(1,x1-x0+1)
            metric=bytes((0,min(255,gw),min(255,max(gw+1,info['maxw']))))
            fallback_used.append(ch)
        else:
            # Last resort: blank readable placeholder rectangle.
            cell=[[0]*info['cw'] for _ in range(info['ch'])]
            for x in range(2,max(3,info['cw']-2)):
                cell[2][x]=15; cell[max(2,info['ch']-3)][x]=15
            for y in range(2,max(3,info['ch']-2)):
                cell[y][2]=15; cell[y][max(2,info['cw']-3)]=15
            metric=bytes((0,min(255,info['cw']-2),min(255,info['maxw'])))
            fallback_used.append(ch+'?')
        paste_cell(newimg,cell,info['cw'],info['ch'],ncols,nextidx)
        metrics.append(metric); mapping[ord(ch)]=nextidx; nextidx+=1
    tex=encode_a4(newimg,nw,nh)
    # Rebuild from sheet-data offset onward. Prefix contains FFNT/FINF/TGLP + padding.
    out=bytearray(b[:info['dataoff']]); out += tex
    cwdh_pos=len(out); cwdh=rebuild_cwdh(metrics); out+=cwdh
    cmap_pos=len(out); cmap=rebuild_cmap(mapping);out+=cmap
    # Patch header + FINF pointers + TGLP values.
    struct.pack_into('<I',out,12,len(out)); struct.pack_into('<H',out,16,4)
    struct.pack_into('<I',out,info['t']+4,cwdh_pos-info['t'])
    q=info['q']; out[q+2]=1
    struct.pack_into('<I',out,q+4,len(tex)); struct.pack_into('<H',out,q+12,ncols);struct.pack_into('<H',out,q+14,nrows)
    struct.pack_into('<H',out,q+16,nw);struct.pack_into('<H',out,q+18,nh)
    # FINF pointers: TGLP data pointer at +20 from FINF start, CWDH +24, CMAP +28.
    finf=b.find(b'FINF')
    struct.pack_into('<I',out,finf+24,cwdh_pos+8);struct.pack_into('<I',out,finf+28,cmap_pos+8)
    return bytes(out),{'changed':True,'added':''.join(missing),'fallback':''.join(fallback_used),'size_before':len(b),'size_after':len(out),'dims':f'{info["w"]}x{info["h"]}->{nw}x{nh}'}


def patch_layout_zlib(path:Path,outpath:Path,fallback_font:bytes|None,fallback_large:bytes|None=None):
    sarc=Sarc(read_wrapped_zlib(path)); files=sarc.files(); repl={}; report=[]
    for name,data in files.items():
        if name.lower().endswith('.bffnt'):
            try:
                inf=parse_font_info(data)
                chosen=fallback_large if (fallback_large and inf['ch']>=38 and 'Kurokane40' not in name) else fallback_font
                fb_tuple=(chosen,parse_cmap(chosen)) if chosen else None
                new,rep=patch_bffnt(data,fb_tuple)
            except Exception as ex: rep={'changed':False,'reason':str(ex)};new=data
            if new!=data:repl[name]=new
            rep={'archive':path.name,'font':name,**rep};report.append(rep)
    raw=sarc.rebuild(repl);write_wrapped_zlib(raw,outpath);return report


def patch_fonts(layout_dir:Path,outdir:Path,report_path:Path|None=None):
    outdir.mkdir(parents=True,exist_ok=True)
    zlibs=sorted(layout_dir.glob('*.zlib'))
    if not zlibs:raise ValueError(f'No .zlib files in {layout_dir}')
    # Prefer already-TR-patched Kurokane20 as a readable fallback for rare decorative fonts.
    fallback=None
    for p in zlibs:
        s=Sarc(read_wrapped_zlib(p));
        for n,d in s.files().items():
            if n.endswith('FotKurokane20px_3dsBitmap.bffnt'):
                fallback=d;break
        if fallback:break
    # Build a patched 40px fallback too; it scales more cleanly into large decorative fonts.
    fallback_large=None
    if fallback:
        for p in zlibs:
            ss=Sarc(read_wrapped_zlib(p))
            for n,d in ss.files().items():
                if n.endswith('FotKurokane40px_3dsBitmap.bffnt'):
                    fallback_large=patch_bffnt(d,(fallback,parse_cmap(fallback)))[0];break
            if fallback_large:break
    reports=[]
    for p in zlibs:
        reports+=patch_layout_zlib(p,outdir/p.name,fallback,fallback_large)
        print('Patched',p.name)
    if report_path is None:report_path=outdir/'font_report.tsv'
    fields=['archive','font','changed','added','fallback','size_before','size_after','dims','reason']
    with report_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(reports)
    print('Font report ->',report_path)


def coverage_font(b:bytes)->str:
    m=parse_cmap(b);return ''.join(c for c in TR_CHARS if ord(c) in m)


def verify_layout_dir(layout_dir:Path):
    bad=[];total=0
    for p in sorted(layout_dir.glob('*.zlib')):
        s=Sarc(read_wrapped_zlib(p))
        for n,d in s.files().items():
            if n.lower().endswith('.bffnt'):
                total+=1; cov=coverage_font(d); miss=''.join(c for c in TR_CHARS if c not in cov)
                print(f'{p.name}\t{n}\tcoverage={cov}\tmissing={miss}')
                if miss:bad.append((p.name,n,miss))
    print(f'Fonts checked: {total}; incomplete: {len(bad)}')
    return 1 if bad else 0


def main():
    ap=argparse.ArgumentParser(description='Rhythm Heaven Megamix Turkish text helper v9 (MSBT only; hardware-safe font builder is separate)')
    sub=ap.add_subparsers(dest='cmd',required=True)

    p=sub.add_parser('export-multilang',help='Export split multilingual TSVs matching the original MSBT tree')
    for arg in ['english','french','german','italian','spanish','turkish']:
        p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--english-xmsbt-zip',type=Path,required=False,help='Optional original English en.zip reference when EUEN MSBT is already patched')
    p.add_argument('--out',type=Path,required=True)

    p=sub.add_parser('build-message-folder',help='Inject Turkish column from split *.msbt.tsv files')
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)

    a=ap.parse_args()
    if a.cmd=='export-multilang':
        export_multilang({
            'English':a.english,'French':a.french,'German':a.german,
            'Italian':a.italian,'Spanish':a.spanish,'Turkish':a.turkish,
        },a.out,a.english_xmsbt_zip)
    elif a.cmd=='build-message-folder':
        import_project_folder(a.source,a.project,a.out)

if __name__=='__main__':main()
