#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, re, struct, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

TOKEN_RE = re.compile(r"⟦(MSBT|U16):([0-9A-Fa-f]+)⟧")
TR_CHARS = "ÇĞİÖŞÜçğıöşü"

class MSBTError(Exception): pass

@dataclass
class Section:
    magic: bytes
    payload: bytes
    reserved: bytes

class MSBT:
    def __init__(self, data: bytes, source: str = "<memory>"):
        self.source = source
        self.data = data
        if len(data) < 0x20 or data[:8] != b"MsgStdBn":
            raise MSBTError(f"{source}: MsgStdBn başlığı yok")
        bom = data[8:10]
        if bom == b"\xff\xfe": self.endian = "<"
        elif bom == b"\xfe\xff": self.endian = ">"
        else: raise MSBTError(f"{source}: bilinmeyen BOM {bom.hex()}")
        self.header = bytearray(data[:0x20])
        self.encoding = data[0x0C]
        self.section_count = struct.unpack_from(self.endian + "H", data, 0x0E)[0]
        self.file_size = struct.unpack_from(self.endian + "I", data, 0x12)[0]
        if self.file_size > len(data):
            raise MSBTError(f"{source}: başlıktaki dosya boyutu gerçek boyuttan büyük")
        self.sections: List[Section] = []
        pos = 0x20
        for i in range(self.section_count):
            if pos + 0x10 > len(data): raise MSBTError(f"{source}: bölüm {i} başlığı taşmış")
            magic = data[pos:pos+4]
            size = struct.unpack_from(self.endian + "I", data, pos+4)[0]
            reserved = data[pos+8:pos+0x10]
            start, end = pos + 0x10, pos + 0x10 + size
            if end > len(data): raise MSBTError(f"{source}: {magic!r} bölümü taşmış")
            self.sections.append(Section(magic, data[start:end], reserved))
            pos = (end + 0x0F) & ~0x0F
        self._parse_labels()
        self._parse_texts()

    @classmethod
    def from_file(cls, p: Path): return cls(p.read_bytes(), str(p))

    def _get_section(self, magic: bytes) -> Section:
        for s in self.sections:
            if s.magic == magic: return s
        raise MSBTError(f"{self.source}: {magic.decode(errors='replace')} bölümü yok")

    def _parse_labels(self):
        self.labels_by_index: Dict[int, List[str]] = {}
        try: sec = self._get_section(b"LBL1")
        except MSBTError: return
        p = sec.payload
        if len(p) < 4: raise MSBTError(f"{self.source}: LBL1 kısa")
        groups = struct.unpack_from(self.endian + "I", p, 0)[0]
        if 4 + groups*8 > len(p): raise MSBTError(f"{self.source}: LBL1 grup tablosu bozuk")
        for g in range(groups):
            count, off = struct.unpack_from(self.endian + "II", p, 4 + g*8)
            pos = off
            for _ in range(count):
                if pos >= len(p): raise MSBTError(f"{self.source}: LBL1 etiket taşması")
                ln = p[pos]; pos += 1
                if pos + ln + 4 > len(p): raise MSBTError(f"{self.source}: LBL1 etiket verisi taşması")
                label_b = p[pos:pos+ln]; pos += ln
                idx = struct.unpack_from(self.endian + "I", p, pos)[0]; pos += 4
                label = label_b.decode("utf-8", errors="replace")
                self.labels_by_index.setdefault(idx, []).append(label)

    def _parse_texts(self):
        sec = self._get_section(b"TXT2")
        p = sec.payload
        if len(p) < 4: raise MSBTError(f"{self.source}: TXT2 kısa")
        count = struct.unpack_from(self.endian + "I", p, 0)[0]
        if 4 + count*4 > len(p): raise MSBTError(f"{self.source}: TXT2 offset tablosu bozuk")
        offs = list(struct.unpack_from(self.endian + f"{count}I", p, 4)) if count else []
        self.raw_texts: List[bytes] = []
        self.texts: List[str] = []
        for i, off in enumerate(offs):
            end = offs[i+1] if i+1 < count else len(p)
            if off > end or end > len(p): raise MSBTError(f"{self.source}: TXT2 offset bozuk @{i}")
            raw = p[off:end]
            # Her string UTF-16 NUL ile biter; son TXT2 padding'i varsa yalnızca terminatöre kadar al.
            term = self._find_terminator(raw)
            if term is not None: raw = raw[:term]
            self.raw_texts.append(raw)
            self.texts.append(self.decode_msbt_text(raw))

    def _find_terminator(self, raw: bytes) -> Optional[int]:
        pos = 0
        while pos + 2 <= len(raw):
            unit = struct.unpack_from(self.endian + "H", raw, pos)[0]
            if unit == 0: return pos
            if unit == 0x000E and pos + 8 <= len(raw):
                arglen = struct.unpack_from(self.endian + "H", raw, pos+6)[0]
                pos += 8 + arglen
            elif unit == 0x000F and pos + 6 <= len(raw):
                pos += 6
            else: pos += 2
        return None

    def decode_msbt_text(self, raw: bytes) -> str:
        out: List[str] = []; plain = bytearray(); pos = 0
        enc = "utf-16le" if self.endian == "<" else "utf-16be"
        def flush():
            if plain:
                out.append(bytes(plain).decode(enc, errors="surrogatepass")); plain.clear()
        while pos < len(raw):
            if pos + 2 > len(raw):
                flush(); out.append(f"⟦MSBT:{raw[pos:].hex().upper()}⟧"); break
            unit = struct.unpack_from(self.endian + "H", raw, pos)[0]
            if unit == 0x000E:
                flush()
                if pos + 8 > len(raw):
                    out.append(f"⟦MSBT:{raw[pos:].hex().upper()}⟧"); break
                arglen = struct.unpack_from(self.endian + "H", raw, pos+6)[0]
                end = min(len(raw), pos + 8 + arglen)
                out.append(f"⟦MSBT:{raw[pos:end].hex().upper()}⟧"); pos = end
            elif unit == 0x000F:
                flush(); end = min(len(raw), pos+6)
                out.append(f"⟦MSBT:{raw[pos:end].hex().upper()}⟧"); pos = end
            elif unit < 0x20 and unit not in (0x09,0x0A,0x0D):
                flush(); out.append(f"⟦U16:{unit:04X}⟧"); pos += 2
            else:
                plain += raw[pos:pos+2]; pos += 2
        flush(); return ''.join(out)

    def encode_msbt_text(self, text: str) -> bytes:
        enc = "utf-16le" if self.endian == "<" else "utf-16be"
        out = bytearray(); last = 0
        for m in TOKEN_RE.finditer(text):
            if m.start() > last: out += text[last:m.start()].encode(enc, errors="surrogatepass")
            kind, hx = m.group(1), m.group(2)
            if kind == "MSBT":
                if len(hx) % 2: raise MSBTError(f"{self.source}: MSBT hex token uzunluğu tek")
                out += bytes.fromhex(hx)
            else:
                if len(hx) != 4: raise MSBTError(f"{self.source}: U16 tokeni 4 hex hane olmalı")
                out += struct.pack(self.endian + "H", int(hx,16))
            last = m.end()
        if last < len(text): out += text[last:].encode(enc, errors="surrogatepass")
        return bytes(out)

    def primary_label(self, idx: int) -> str:
        ls = self.labels_by_index.get(idx, [])
        return ls[0] if ls else f"#INDEX_{idx}"

    def label_to_index(self) -> Dict[str,int]:
        out = {}
        for idx, labels in self.labels_by_index.items():
            for l in labels: out[l] = idx
        return out

    def with_texts(self, new_texts: List[str]) -> bytes:
        if len(new_texts) != len(self.texts):
            raise MSBTError(f"{self.source}: metin sayısı değişemez ({len(self.texts)} -> {len(new_texts)})")
        encoded = [self.encode_msbt_text(t) + (b"\x00\x00") for t in new_texts]
        count = len(encoded); table_size = 4 + count*4
        offs=[]; cursor=table_size
        for raw in encoded: offs.append(cursor); cursor += len(raw)
        txt = bytearray(struct.pack(self.endian+"I", count))
        if count: txt += struct.pack(self.endian+f"{count}I", *offs)
        for raw in encoded: txt += raw

        out = bytearray(self.header)
        for sec in self.sections:
            payload = bytes(txt) if sec.magic == b"TXT2" else sec.payload
            out += sec.magic + struct.pack(self.endian+"I", len(payload)) + sec.reserved + payload
            while len(out) % 0x10: out.append(0xAB)
        struct.pack_into(self.endian+"I", out, 0x12, len(out))
        return bytes(out)


def discover_languages(msg_root: Path) -> List[str]:
    return sorted([p.name for p in msg_root.iterdir() if p.is_dir() and any(p.glob('*.msbt'))])

def discover_files(msg_root: Path, languages: List[str]) -> List[str]:
    names=set()
    for lang in languages: names.update(p.name for p in (msg_root/lang).glob('*.msbt'))
    return sorted(names, key=str.lower)

def read_csv(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))

def export_csvs(msg_root: Path, csv_dir: Path, base: str, target: Optional[str], prefill: bool):
    langs = discover_languages(msg_root)
    if not langs: raise MSBTError(f"Dil klasörü bulunamadı: {msg_root}")
    if base not in langs: raise MSBTError(f"Base dil yok: {base}; bulunanlar={langs}")
    columns = list(langs)
    if target and target not in columns: columns.append(target)
    csv_dir.mkdir(parents=True, exist_ok=True)
    files=discover_files(msg_root, langs)
    for fname in files:
        parsed: Dict[str,MSBT] = {}
        for lang in langs:
            p=msg_root/lang/fname
            if p.exists(): parsed[lang]=MSBT.from_file(p)
        b=parsed.get(base)
        if not b: continue
        ordered=[]; seen=set()
        for i in range(len(b.texts)):
            k=b.primary_label(i)
            if k not in seen: ordered.append(k); seen.add(k)
        for lang,m in parsed.items():
            for i in range(len(m.texts)):
                k=m.primary_label(i)
                if k not in seen: ordered.append(k); seen.add(k)
        maps={lang:{m.primary_label(i):m.texts[i] for i in range(len(m.texts))} for lang,m in parsed.items()}
        base_index={b.primary_label(i):i for i in range(len(b.texts))}
        outp=csv_dir/(Path(fname).stem+'.csv')
        with outp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f, fieldnames=['index','label']+columns, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for label in ordered:
                row={'index':base_index.get(label,''),'label':label}
                for lang in langs: row[lang]=maps.get(lang,{}).get(label,'')
                if target and target not in langs:
                    row[target]=maps.get(base,{}).get(label,'') if prefill else ''
                w.writerow(row)
    print(f"{len(files)} CSV oluşturuldu: {csv_dir}")

def import_msbt_column(csv_dir: Path, source_msg_dir: Path, column: str):
    """Mevcut bir MSBT yamasındaki metinleri CSV sütununa etiket adına göre taşır."""
    done=0; missing=0
    for cp in sorted(csv_dir.glob('*.csv')):
        src=source_msg_dir/(cp.stem+'.msbt')
        if not src.exists():
            print(f"UYARI: kaynak yok: {src}",file=sys.stderr); missing+=1; continue
        m=MSBT.from_file(src)
        smap={m.primary_label(i):m.texts[i] for i in range(len(m.texts))}
        with cp.open('r',encoding='utf-8-sig',newline='') as f:
            r=csv.DictReader(f); fields=list(r.fieldnames or []); rows=list(r)
        if column not in fields: fields.append(column)
        hit=0
        for row in rows:
            label=row.get('label','')
            if label in smap:
                row[column]=smap[label]; hit+=1
        with cp.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_MINIMAL); w.writeheader(); w.writerows(rows)
        print(f"{cp.name}: {hit} satır {column} sütununa aktarıldı")
        done+=1
    print(f"{done} CSV güncellendi; eksik kaynak: {missing}")

def repair_malformed_tokens(csv_dir: Path, column: str, report: Optional[Path]=None) -> int:
    """Eksik/truncated tag payload'larını düzeltir. Payload UTF-16 düz metinse tag dışına taşır."""
    token_re=re.compile(r"⟦MSBT:([0-9A-Fa-f]+)⟧")
    fixes=[]; unresolved=[]
    for cp in sorted(csv_dir.glob('*.csv')):
        with cp.open('r',encoding='utf-8-sig',newline='') as f:
            rd=csv.DictReader(f); fields=list(rd.fieldnames or []); rows=list(rd)
        changed=False
        for line,row in enumerate(rows,start=2):
            text=row.get(column,'')
            def repl(m):
                nonlocal changed
                hx=m.group(1)
                try: b=bytes.fromhex(hx)
                except Exception: return m.group(0)
                if len(b)<8: return m.group(0)
                if b[:2]==b'\x0e\x00': endian='little'; enc='utf-16le'
                elif b[:2]==b'\x00\x0e': endian='big'; enc='utf-16be'
                else: return m.group(0)
                declared=int.from_bytes(b[6:8],endian); actual=len(b)-8
                if declared==actual: return m.group(0)
                if actual<declared:
                    payload=b[8:]
                    # Yalnızca gerçekten UTF-16 düz metin görünüyorsa otomatik onar.
                    if len(payload)%2==0:
                        try: txt=payload.decode(enc).rstrip('\x00')
                        except UnicodeDecodeError: txt=''
                        printable=txt and all((ch.isprintable() or ch in '\t\n\r') for ch in txt)
                        if printable:
                            fixed=b[:6]+(0).to_bytes(2,endian)
                            new=f"⟦MSBT:{fixed.hex().upper()}⟧"+txt
                            fixes.append({'file':cp.name,'csv_line':line,'label':row.get('label',''),'declared_arg_bytes':declared,'actual_arg_bytes':actual,'old_token':m.group(0),'replacement':new})
                            changed=True; return new
                unresolved.append({'file':cp.name,'csv_line':line,'label':row.get('label',''),'declared_arg_bytes':declared,'actual_arg_bytes':actual,'old_token':m.group(0),'replacement':'ONARILAMADI'})
                return m.group(0)
            row[column]=token_re.sub(repl,text)
        if changed:
            with cp.open('w',encoding='utf-8-sig',newline='') as f:
                wr=csv.DictWriter(f,fieldnames=fields,quoting=csv.QUOTE_MINIMAL); wr.writeheader(); wr.writerows(rows)
    allrows=fixes+unresolved
    if report:
        report.parent.mkdir(parents=True,exist_ok=True)
        fields=['file','csv_line','label','declared_arg_bytes','actual_arg_bytes','old_token','replacement']
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader(); wr.writerows(allrows)
    print(f"Bozuk tag: {len(allrows)}; otomatik onarılan: {len(fixes)}; çözülemeyen: {len(unresolved)}")
    if report: print(f"Onarım raporu: {report}")
    return 1 if unresolved else 0


def inject_csvs(msg_root: Path, csv_dir: Path, out_msg_root: Path, base: str, target: str, empty_mode: str, out_lang_name: Optional[str]=None):
    out_lang_name = out_lang_name or target
    out_lang = out_msg_root/out_lang_name; out_lang.mkdir(parents=True, exist_ok=True)
    csvs=sorted(csv_dir.glob('*.csv'))
    done=0
    for cp in csvs:
        fname=cp.stem+'.msbt'
        template=msg_root/target/fname
        if not template.exists(): template=msg_root/base/fname
        if not template.exists():
            print(f"UYARI: template yok, atlandı: {fname}",file=sys.stderr); continue
        m=MSBT.from_file(template); rows=read_csv(cp)
        by_label={r.get('label',''):r for r in rows}; texts=list(m.texts)
        for i in range(len(texts)):
            label=m.primary_label(i); row=by_label.get(label)
            if not row: continue
            val=row.get(target,'')
            if val=='' and empty_mode=='keep': continue
            texts[i]=val
        (out_lang/fname).write_bytes(m.with_texts(texts)); done+=1
    print(f"{done} MSBT yazıldı: {out_lang}")

def token_sequence(s: str) -> List[str]:
    return [m.group(0) for m in TOKEN_RE.finditer(s) if m.group(1)=='MSBT']

def validate(msg_root: Path, csv_dir: Path, base: str, target: str, report: Optional[Path]=None) -> int:
    problems=0; report_rows=[]
    for cp in sorted(csv_dir.glob('*.csv')):
        rows=read_csv(cp)
        for n,r in enumerate(rows, start=2):
            src=r.get(base,''); dst=r.get(target,'')
            if target not in r:
                print(f"{cp.name}: hedef sütun yok: {target}"); problems+=1; break
            st=token_sequence(src); dt=token_sequence(dst)
            if st != dt:
                print(f"{cp.name}:{n} {r.get('label')}: kontrol kodu dizisi farklı")
                problems+=1
                report_rows.append({'file':cp.name,'csv_line':n,'label':r.get('label',''),'source_tokens':' | '.join(st),'target_tokens':' | '.join(dt),'source_text':src,'target_text':dst})
    if report:
        report.parent.mkdir(parents=True,exist_ok=True)
        fields=['file','csv_line','label','source_tokens','target_tokens','source_text','target_text']
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(report_rows)
        print(f"Kontrol kodu raporu: {report}")
    print(f"Doğrulama: {problems} uyarı")
    return 1 if problems else 0

def inspect_file(path: Path):
    m=MSBT.from_file(path)
    print(f"{path}: endian={m.endian} encoding={m.encoding} sections={[s.magic.decode(errors='replace') for s in m.sections]} texts={len(m.texts)} labels={sum(len(v) for v in m.labels_by_index.values())}")
    for i,t in enumerate(m.texts[:10]): print(f"[{i}] {m.primary_label(i)} = {t!r}")

def main():
    ap=argparse.ArgumentParser(description='Kirby Planet Robobot MSBT ↔ çok dilli CSV aracı')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('export'); p.add_argument('msg_root',type=Path); p.add_argument('csv_dir',type=Path); p.add_argument('--base',default='EU_English'); p.add_argument('--target',default='TR_Turkish'); p.add_argument('--blank-target',action='store_true')
    p=sp.add_parser('inject'); p.add_argument('msg_root',type=Path); p.add_argument('csv_dir',type=Path); p.add_argument('out_msg_root',type=Path); p.add_argument('--base',default='EU_English'); p.add_argument('--target',default='TR_Turkish'); p.add_argument('--out-lang',default=None,help='çıktı klasör adı; gerçek yama için örn. EU_English'); p.add_argument('--empty',choices=['keep','blank'],default='keep')
    p=sp.add_parser('import-column'); p.add_argument('csv_dir',type=Path); p.add_argument('source_msg_dir',type=Path); p.add_argument('--column',default='TR_Turkish')
    p=sp.add_parser('repair-malformed'); p.add_argument('csv_dir',type=Path); p.add_argument('--column',default='TR_Turkish'); p.add_argument('--report',type=Path)
    p=sp.add_parser('validate'); p.add_argument('msg_root',type=Path); p.add_argument('csv_dir',type=Path); p.add_argument('--base',default='EU_English'); p.add_argument('--target',default='TR_Turkish'); p.add_argument('--report',type=Path)
    p=sp.add_parser('inspect'); p.add_argument('file',type=Path)
    a=ap.parse_args()
    try:
        if a.cmd=='export': export_csvs(a.msg_root,a.csv_dir,a.base,a.target,not a.blank_target)
        elif a.cmd=='inject': inject_csvs(a.msg_root,a.csv_dir,a.out_msg_root,a.base,a.target,a.empty,a.out_lang)
        elif a.cmd=='import-column': import_msbt_column(a.csv_dir,a.source_msg_dir,a.column)
        elif a.cmd=='repair-malformed': raise SystemExit(repair_malformed_tokens(a.csv_dir,a.column,a.report))
        elif a.cmd=='validate': raise SystemExit(validate(a.msg_root,a.csv_dir,a.base,a.target,a.report))
        else: inspect_file(a.file)
    except MSBTError as e:
        print('HATA:',e,file=sys.stderr); raise SystemExit(2)
if __name__=='__main__': main()
