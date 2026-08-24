#!/usr/bin/env python3
from pathlib import Path
import argparse, json, base64, hashlib, struct, shutil, sys

def sha256(b): return hashlib.sha256(b).hexdigest()

def parse_charlist(b):
    o=0
    magic,total,nlen=struct.unpack_from('<III',b,o); o=12+nlen
    slen=struct.unpack_from('<I',b,o)[0]; o += 4+slen
    mapcount=struct.unpack_from('<I',b,o)[0]; o+=4
    entries=[]
    for _ in range(mapcount):
        cp,idx=struct.unpack_from('<II',b,o); entries.append((cp,idx)); o+=8
    return entries

def apply_one(src, spec):
    b=src.read_bytes()
    got=sha256(b)
    if got != spec['input_sha256']:
        raise RuntimeError(f"{src.name}: SHA-256 eşleşmedi. Orijinal dosya farklı olabilir.\nBeklenen: {spec['input_sha256']}\nBulunan:  {got}")
    edited=bytearray(b)
    for e in spec['map_edits']:
        old=struct.unpack_from('<I',edited,e['offset'])[0]
        if old != e['old_cp']:
            raise RuntimeError(f"{src.name}: U+{old:04X} beklenmeyen harita girdisi")
        struct.pack_into('<I',edited,e['offset'],e['new_cp'])
    reps=sorted(spec['record_replacements'], key=lambda r:r['start'])
    out=bytearray(); cur=0
    for r in reps:
        out.extend(edited[cur:r['start']])
        out.extend(base64.b64decode(r['data_b64']))
        cur=r['end']
    out.extend(edited[cur:])
    out=bytes(out)
    if sha256(out) != spec['output_sha256']:
        raise RuntimeError(f"{src.name}: çıktı doğrulama karması eşleşmedi")
    return out

def main():
    ap=argparse.ArgumentParser(description='VLR 3DS Türkçe font yaması')
    ap.add_argument('fonts_dir', nargs='?', default='fonts', help='Orijinal .dat fontlarının bulunduğu klasör (varsayılan: fonts)')
    ap.add_argument('-o','--output', default='fonts_tr', help='Çıktı klasörü (varsayılan: fonts_tr)')
    a=ap.parse_args()
    here=Path(__file__).resolve().parent
    manifest=json.loads((here/'patches.json').read_text(encoding='utf-8'))
    srcdir=Path(a.fonts_dir).resolve(); outdir=Path(a.output).resolve(); outdir.mkdir(parents=True,exist_ok=True)
    done=[]
    for name,spec in manifest['fonts'].items():
        src=srcdir/name
        if not src.exists():
            raise FileNotFoundError(f'Eksik dosya: {src}')
        data=apply_one(src,spec)
        (outdir/name).write_bytes(data); done.append(name)
    # Generate a charlist for the patched Bold 12 font as a convenience.
    bold=outdir/'SKP2-Bold.12.dat'
    if bold.exists():
        entries=parse_charlist(bold.read_bytes())
        chars=[]
        for cp,idx in sorted(entries,key=lambda x:x[1]):
            try: chars.append(chr(cp))
            except ValueError: chars.append('�')
        (outdir/'SKP2-Bold_12_charlist.txt').write_text('\n'.join(chars)+'\n',encoding='utf-8')
    print(f'Tamamlandı: {len(done)} font -> {outdir}')
    print('Türkçe karakterler: ç ğ ı ö ş ü Ç Ğ İ Ö Ş Ü')

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'HATA: {e}', file=sys.stderr)
        sys.exit(1)
