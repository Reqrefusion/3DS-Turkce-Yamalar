#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, os, shutil, struct, sys, unicodedata, zipfile
from pathlib import Path
from collections import OrderedDict, defaultdict

LANGS = ('deu','eng','esp','fra','ita','nld')
MSBT_MAGIC=b'MsgStdBn'

def endian_from_bom(d: bytes)->str:
    bom=d[8:10]
    if bom==b'\xff\xfe': return '<'
    if bom==b'\xfe\xff': return '>'
    raise ValueError('Geçersiz MSBT BOM')

def align16(n:int)->int: return (n+15)&~15

def escape_text(s:str)->str:
    out=[]
    for ch in s:
        cp=ord(ch)
        if ch=='\\': out.append('\\\\')
        elif ch=='\n': out.append('\\n')
        elif ch=='\r': out.append('\\r')
        elif ch=='\t': out.append('\\t')
        elif cp<0x20 or 0x7f<=cp<=0x9f or 0xD800<=cp<=0xDFFF:
            out.append(f'\\u{cp:04X}')
        else: out.append(ch)
    return ''.join(out)

def unescape_text(s:str)->str:
    out=[]; i=0
    while i<len(s):
        if s[i]!='\\': out.append(s[i]); i+=1; continue
        if i+1>=len(s): out.append('\\'); break
        c=s[i+1]
        if c=='\\': out.append('\\'); i+=2
        elif c=='n': out.append('\n'); i+=2
        elif c=='r': out.append('\r'); i+=2
        elif c=='t': out.append('\t'); i+=2
        elif c=='u' and i+6<=len(s):
            try: out.append(chr(int(s[i+2:i+6],16))); i+=6
            except ValueError: out.append('\\'); i+=1
        elif c=='U' and i+10<=len(s):
            try: out.append(chr(int(s[i+2:i+10],16))); i+=10
            except ValueError: out.append('\\'); i+=1
        else: out.append('\\'); i+=1
    return ''.join(out)

class MSBT:
    def __init__(self,path:Path):
        self.path=Path(path); self.data=self.path.read_bytes()
        if self.data[:8]!=MSBT_MAGIC: raise ValueError(f'{path}: MSBT değil')
        self.e=endian_from_bom(self.data)
        self.encoding=self.data[12]
        self.section_count=struct.unpack_from(self.e+'H',self.data,14)[0]
        self.sections=[]; pos=0x20
        for _ in range(self.section_count):
            magic=self.data[pos:pos+4]
            if len(magic)<4: raise ValueError(f'{path}: bölüm başlığı eksik')
            size=struct.unpack_from(self.e+'I',self.data,pos+4)[0]
            end=pos+0x10+size
            self.sections.append((magic,pos,size,end))
            pos=align16(end)
        self.labels=self._labels(); self.texts=self._texts()
        self.by_label=OrderedDict()
        for name,idx in sorted(self.labels.items(), key=lambda kv:(kv[1],kv[0])):
            if idx < len(self.texts): self.by_label[name]=self.texts[idx]
    def _sec(self,magic):
        for s in self.sections:
            if s[0]==magic:return s
        return None
    def _labels(self):
        sec=self._sec(b'LBL1'); out={}
        if not sec:return out
        _,pos,size,end=sec; p=pos+0x10; payload=self.data[p:end]
        groups=struct.unpack_from(self.e+'I',payload,0)[0]
        for g in range(groups):
            count,off=struct.unpack_from(self.e+'II',payload,4+8*g); q=off
            for _ in range(count):
                ln=payload[q]; raw=payload[q+1:q+1+ln]
                try:name=raw.decode('utf-8')
                except UnicodeDecodeError:name=raw.decode('latin1')
                idx=struct.unpack_from(self.e+'I',payload,q+1+ln)[0]
                out[name]=idx; q+=1+ln+4
        return out
    def _texts(self):
        sec=self._sec(b'TXT2')
        if not sec:return []
        _,pos,size,end=sec; payload=self.data[pos+0x10:end]
        n=struct.unpack_from(self.e+'I',payload,0)[0]
        offs=list(struct.unpack_from(self.e+f'{n}I',payload,4)) if n else []
        res=[]
        for i,o in enumerate(offs):
            z=offs[i+1] if i+1<n else len(payload); raw=payload[o:z]
            if self.encoding==1:
                term=b'\x00\x00'; enc='utf-16-le' if self.e=='<' else 'utf-16-be'
                if raw.endswith(term): raw=raw[:-2]
                res.append(raw.decode(enc,'surrogatepass'))
            elif self.encoding==0:
                if raw.endswith(b'\0'): raw=raw[:-1]
                res.append(raw.decode('utf-8','surrogateescape'))
            else: raise ValueError(f'{self.path}: desteklenmeyen encoding {self.encoding}')
        return res
    def rebuild(self, replacements:dict[str,str], out:Path):
        texts=list(self.texts)
        for label,text in replacements.items():
            if label not in self.labels: continue
            texts[self.labels[label]]=text
        if self.encoding==1:
            enc='utf-16-le' if self.e=='<' else 'utf-16-be'; term=b'\0\0'
            blobs=[t.encode(enc,'surrogatepass')+term for t in texts]
        else:
            blobs=[t.encode('utf-8','surrogateescape')+b'\0' for t in texts]
        head=4+4*len(blobs); offs=[]; cur=head
        for b in blobs: offs.append(cur); cur+=len(b)
        payload=struct.pack(self.e+'I',len(blobs))
        if offs: payload+=struct.pack(self.e+f'{len(offs)}I',*offs)
        payload+=b''.join(blobs)
        chunks=[bytearray(self.data[:0x20])]
        for magic,pos,size,end in self.sections:
            hdr=bytearray(self.data[pos:pos+0x10])
            body=self.data[pos+0x10:end]
            if magic==b'TXT2':
                struct.pack_into(self.e+'I',hdr,4,len(payload)); body=payload
            chunk=bytes(hdr)+body
            chunk += b'\xAB' * ((16-(len(chunk)%16))%16)
            chunks.append(bytearray(chunk))
        new=bytearray().join(chunks)
        struct.pack_into(self.e+'I',new,0x12,len(new))
        out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(new)
        # Parse it again as a sanity check.
        check=MSBT(out)
        for k,v in replacements.items():
            if k in check.by_label and check.by_label[k]!=v:
                raise ValueError(f'{out}: doğrulama başarısız: {k}')

def detect_root(root:Path, patch=False)->Path:
    root=Path(root)
    candidates=[root/root.name if (root/root.name).exists() else root,
                root/'msgstudio',
                root/'romfs'/'lang'/'EU'/'msgstudio']
    for c in candidates:
        if all((c/x).is_dir() for x in (('eng',) if patch else LANGS)):
            return c
    # recursive fallback
    for c in root.rglob('msgstudio'):
        if all((c/x).is_dir() for x in (('eng',) if patch else LANGS)):
            return c
    raise FileNotFoundError(f'msgstudio kökü bulunamadı: {root}')

def iter_rel_msbt(langroot:Path):
    return sorted(p.relative_to(langroot) for p in langroot.rglob('*.msbt'))

def _unique_msbt_name_map(langroot:Path):
    """Return {MSBT filename: relative path}; fail loudly on duplicate filenames."""
    mapping={}
    duplicates=defaultdict(list)
    for rel in iter_rel_msbt(langroot):
        name=rel.name
        if name in mapping:
            duplicates[name].extend([mapping[name],rel])
        else:
            mapping[name]=rel
    if duplicates:
        detail='; '.join(f"{k}: {', '.join(map(str, dict.fromkeys(v)))}" for k,v in sorted(duplicates.items()))
        raise ValueError('Aynı MSBT dosya adı birden fazla klasörde bulundu; düz CSV adı belirsiz olur: '+detail)
    return mapping

def export_csv(source:Path, patch:Path, outdir:Path):
    sroot=detect_root(source); proot=detect_root(patch,True)
    name_map=_unique_msbt_name_map(sroot/'eng')
    outdir.mkdir(parents=True,exist_ok=True)
    written=0
    for msbt_name,rel in sorted(name_map.items(), key=lambda kv:str(kv[1]).lower()):
        docs={l:MSBT(sroot/l/rel) for l in LANGS}
        pp=proot/'eng'/rel; pd=MSBT(pp) if pp.exists() else None
        labels=set().union(*(d.labels for d in docs.values()))
        if pd: labels |= set(pd.labels)
        def key(lbl):
            if lbl in docs['eng'].labels:return (0,docs['eng'].labels[lbl],lbl)
            if pd and lbl in pd.labels:return (1,pd.labels[lbl],lbl)
            return (2,0,lbl)
        # One flat CSV per MSBT filename: Foo.msbt -> Foo.csv
        dest=outdir/(Path(msbt_name).stem+'.csv')
        with dest.open('w',newline='',encoding='utf-8-sig') as f:
            fields=['label','index']+list(LANGS)+['tur']
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
            for lbl in sorted(labels,key=key):
                row={'label':lbl,'index':docs['eng'].labels.get(lbl, pd.labels.get(lbl,'') if pd else '')}
                for l,d in docs.items(): row[l]=escape_text(d.by_label.get(lbl,''))
                row['tur']=escape_text(pd.by_label.get(lbl,'')) if pd else ''
                w.writerow(row)
        written+=1
    print(f'{written} CSV yazıldı (her MSBT için bir CSV, tek klasör): {outdir}')

def import_csv(csvdir:Path, basepatch:Path, outroot:Path, column='tur'):
    proot=detect_root(basepatch,True)
    name_map=_unique_msbt_name_map(proot/'eng')
    stem_map={}
    for name,rel in name_map.items():
        stem=Path(name).stem
        if stem in stem_map:
            raise ValueError(f'Aynı CSV kök adına dönüşen MSBT bulundu: {stem}')
        stem_map[stem]=rel
    # preserve outer package structure
    outer=Path(basepatch)
    if outroot.exists(): shutil.rmtree(outroot)
    shutil.copytree(outer,outroot)
    outproot=detect_root(outroot,True)
    done=0
    for c in sorted(Path(csvdir).glob('*.csv')):
        rel=stem_map.get(c.stem)
        if rel is None:
            print(f'UYARI: {c.name} adına karşılık gelen MSBT yok, atlandı',file=sys.stderr); continue
        src=proot/'eng'/rel
        repl={}
        with c.open('r',encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                if row.get('label') and column in row:
                    repl[row['label']]=unescape_text(row[column])
        MSBT(src).rebuild(repl,outproot/'eng'/rel); done+=1
    print(f'{done} MSBT enjekte edildi: {outroot}')

def validate(source:Path, patch:Path):
    sroot=detect_root(source); proot=detect_root(patch,True)
    rels=iter_rel_msbt(sroot/'eng'); issues=[]; total_strings=changed=0
    srcset=set(rels); pset=set(iter_rel_msbt(proot/'eng'))
    if srcset!=pset:
        issues.append(f'Dosya kümesi farkı: kaynakta-ekstra={len(srcset-pset)}, yamada-ekstra={len(pset-srcset)}')
    for rel in sorted(srcset & pset):
        eng=MSBT(sroot/'eng'/rel); pat=MSBT(proot/'eng'/rel)
        total_strings+=len(eng.by_label)
        changed+=sum(eng.by_label.get(k)!=v for k,v in pat.by_label.items() if k in eng.by_label)
        if set(eng.labels)!=set(pat.labels): issues.append(f'{rel}: label kümesi farklı')
        if len(eng.texts)!=len(pat.texts): issues.append(f'{rel}: TXT2 sayısı {len(eng.texts)} != {len(pat.texts)}')
    print(f'Kaynak MSBT: {len(srcset)} | Yama MSBT: {len(pset)} | Etiketli İngilizce metin: {total_strings} | Değişen: {changed}')
    if issues:
        print('Sorunlar:'); [print(' -',x) for x in issues[:100]]; return 1
    print('Yapısal doğrulama: OK'); return 0

def package(inp:Path, outzip:Path):
    inp=Path(inp); outzip=Path(outzip); outzip.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(outzip,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(inp.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(inp.parent))
    print(outzip)

def bffnt_chars(path:Path):
    d=Path(path).read_bytes()
    if d[:4]!=b'FFNT': raise ValueError(f'{path}: FFNT değil')
    e='<' if d[4:6]==b'\xff\xfe' else '>'
    out=set(); pos=0
    while True:
        i=d.find(b'CMAP',pos)
        if i<0: break
        size,start,end,method,res,nextoff=struct.unpack_from(e+'IHHHHI',d,i+4); q=i+20
        if method==0:
            out.update(range(start,end+1))
        elif method==1:
            n=end-start+1
            vals=struct.unpack_from(e+f'{n}H',d,q)
            out.update(cp for cp,v in zip(range(start,end+1),vals) if v!=0xFFFF)
        elif method==2:
            count=struct.unpack_from(e+'H',d,q)[0]; q+=2
            for _ in range(count):
                cp,idx=struct.unpack_from(e+'HH',d,q); q+=4; out.add(cp)
        pos=i+4
    return out

def fontscan(fontdir:Path, patch:Path):
    proot=detect_root(patch,True); used=set()
    for p in (proot/'eng').rglob('*.msbt'):
        for s in MSBT(p).texts:
            used.update(ord(c) for c in s if c.isprintable() and not c.isspace())
    tur=set(map(ord,'çÇğĞıİöÖşŞüÜ'))
    for f in sorted(Path(fontdir).rglob('*.bffnt')):
        cs=bffnt_chars(f); miss=sorted((used|tur)-cs)
        turmiss=''.join(chr(x) for x in sorted(tur-cs))
        print(f'{f.name}: CMAP={len(cs)} karakter | eksik Türkçe harfler: {turmiss or "yok"}')
        common=[x for x in miss if x<0x3000][:30]
        if common: print('  Yamada kullanılan ilk eksikler:', ' '.join(f'U+{x:04X}({chr(x)})' for x in common))

def main():
    ap=argparse.ArgumentParser(description='Sushi Striker 3DS MSBT çok-dilli CSV dışa/içe aktarma aracı')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('export'); p.add_argument('--source',required=True,type=Path); p.add_argument('--patch',required=True,type=Path); p.add_argument('--out',required=True,type=Path)
    p=sp.add_parser('import'); p.add_argument('--csv',required=True,type=Path); p.add_argument('--patch',required=True,type=Path); p.add_argument('--out',required=True,type=Path); p.add_argument('--column',default='tur')
    p=sp.add_parser('validate'); p.add_argument('--source',required=True,type=Path); p.add_argument('--patch',required=True,type=Path)
    p=sp.add_parser('package'); p.add_argument('--input',required=True,type=Path); p.add_argument('--out',required=True,type=Path)
    p=sp.add_parser('fontscan'); p.add_argument('--fonts',required=True,type=Path); p.add_argument('--patch',required=True,type=Path)
    a=ap.parse_args()
    if a.cmd=='export': export_csv(a.source,a.patch,a.out)
    elif a.cmd=='import': import_csv(a.csv,a.patch,a.out,a.column)
    elif a.cmd=='validate': raise SystemExit(validate(a.source,a.patch))
    elif a.cmd=='package': package(a.input,a.out)
    elif a.cmd=='fontscan': fontscan(a.fonts,a.patch)
if __name__=='__main__': main()
