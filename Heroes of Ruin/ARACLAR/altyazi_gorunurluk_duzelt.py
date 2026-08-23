#!/usr/bin/env python3
from pathlib import Path
import struct, sys, json

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hor_formats import blz_decompress, parse_darc
from cutscene_archive_repair import blz_compress_canonical

SUB_TEXTURES = ('timg/tr_sub_bg.bclim', 'timg/tr_sub_text.bclim')
SUB_PANES = {'TR_SubBG': 20.0, 'TR_SubText': 21.0}


def sections(b: bytes):
    if b[:4] != b'CLYT': raise ValueError('BCLYT magic')
    pos = struct.unpack_from('<H', b, 6)[0]
    cnt = struct.unpack_from('<H', b, 0x10)[0]
    out=[]
    for i in range(cnt):
        if pos+8 > len(b): raise ValueError('BCLYT section range')
        sz=struct.unpack_from('<I',b,pos+4)[0]
        if sz<8 or pos+sz>len(b): raise ValueError('BCLYT section size')
        out.append((i,pos,b[pos:pos+4],sz))
        pos+=sz
    if pos != len(b): raise ValueError('BCLYT trailing data')
    return out


def patch_bclyt(b: bytes):
    out=bytearray(b); found=set()
    for _i,pos,sig,sz in sections(b):
        if sig != b'pic1' or sz < 0x60: continue
        name=b[pos+0x0c:pos+0x1c].split(b'\0',1)[0].decode('ascii','replace')
        if name in SUB_PANES:
            struct.pack_into('<f',out,pos+0x2c,SUB_PANES[name])
            # görünür + tam alpha
            out[pos+8] |= 1
            out[pos+10] = 0xFF
            found.add(name)
    if found != set(SUB_PANES):
        raise ValueError(f'altyazi pane eksik: {set(SUB_PANES)-found}')
    return bytes(out)


def patch_bclim(b: bytes):
    if len(b)<0x28 or b[-0x28:-0x24] != b'CLIM':
        raise ValueError('BCLIM footer bulunamadi')
    out=bytearray(b); base=len(out)-0x28
    fmt=struct.unpack_from('<I',out,base+0x20)[0]
    data_len=struct.unpack_from('<I',out,base+0x24)[0]
    if data_len != base:
        raise ValueError(f'BCLIM veri boyu tutmuyor: {data_len} != {base}')
    if fmt == 8:
        return bytes(out)
    if fmt not in (1, 0x0001000C):
        raise ValueError(f'beklenmeyen TR BCLIM formatı: {fmt:#x}')
    # A8 piksel akışını, oyunun kendi animaticlerinde kullanılan RGBA4444 (format 8)
    # biçimine çevir. Böylece yalnız teorik desteklenen A8'e bağımlı kalmıyoruz.
    src=bytes(out[:base]); pix=bytearray(len(src)*2)
    for i,a in enumerate(src):
        v=0xFFF0 | (a >> 4)  # beyaz RGB + 4-bit alpha
        struct.pack_into('<H',pix,i*2,v)
    footer=bytearray(out[base:])
    struct.pack_into('<I',footer,0x0C,len(pix)+0x28)  # CLIM file size
    struct.pack_into('<I',footer,0x20,8)             # RGBA4444
    struct.pack_into('<I',footer,0x24,len(pix))
    return bytes(pix+footer)


def rebuild_darc(raw: bytes, replacements: dict[str,bytes]):
    arc=parse_darc(raw)
    files=sorted([n for n in arc.nodes if not n.is_dir], key=lambda n:n.field1)
    blobs={n.path:raw[n.field1:n.field1+n.field2] for n in files}
    for p,b in replacements.items():
        if p not in blobs: raise KeyError(p)
        blobs[p]=b
    out=bytearray(raw[:arc.data_offset])
    for idx,n in enumerate(files):
        if idx:
            while len(out)%0x80: out.append(0)
        start=len(out); blob=blobs[n.path]
        struct.pack_into('<II',out,n.node_offset+4,start,len(blob))
        out += blob
    struct.pack_into('<I',out,0x0C,len(out))
    # reparse verification
    a2=parse_darc(bytes(out))
    if [n.path for n in a2.nodes] != [n.path for n in arc.nodes]:
        raise RuntimeError('DARC node list changed')
    return bytes(out)


def patch_one(path: Path):
    packed=path.read_bytes(); raw=blz_decompress(packed); arc=parse_darc(raw)
    bclyts=[n for n in arc.nodes if not n.is_dir and n.path.lower().endswith('.bclyt')]
    if len(bclyts)!=1: raise ValueError(f'{path.name}: BCLYT sayisi {len(bclyts)}')
    repl={}
    n=bclyts[0]; repl[n.path]=patch_bclyt(raw[n.field1:n.field1+n.field2])
    for sp in SUB_TEXTURES:
        sn=next((x for x in arc.nodes if not x.is_dir and x.path==sp),None)
        if sn is None: raise ValueError(f'{path.name}: {sp} yok')
        repl[sp]=patch_bclim(raw[sn.field1:sn.field1+sn.field2])
    newraw=rebuild_darc(raw,repl)
    newpacked=blz_compress_canonical(newraw)
    if blz_decompress(newpacked)!=newraw: raise RuntimeError('BLZ roundtrip')
    path.write_bytes(newpacked)
    return {'file':path.name,'old':len(packed),'new':len(newpacked)}


def verify_one(path: Path):
    raw=blz_decompress(path.read_bytes()); arc=parse_darc(raw)
    bc=next(n for n in arc.nodes if not n.is_dir and n.path.lower().endswith('.bclyt'))
    b=raw[bc.field1:bc.field1+bc.field2]
    panes={}
    for _i,pos,sig,sz in sections(b):
        if sig==b'pic1':
            name=b[pos+0x0c:pos+0x1c].split(b'\0',1)[0].decode('ascii','replace')
            if name in SUB_PANES: panes[name]=struct.unpack_from('<f',b,pos+0x2c)[0]
    fmts={}
    for sp in SUB_TEXTURES:
        n=next(x for x in arc.nodes if not x.is_dir and x.path==sp)
        x=raw[n.field1:n.field1+n.field2]; base=len(x)-0x28
        fmts[sp]=struct.unpack_from('<I',x,base+0x20)[0]
    return panes,fmts


def main():
    if len(sys.argv)!=2:
        print('Kullanim: python altyazi_gorunurluk_duzelt.py <UI klasoru>'); return 2
    ui=Path(sys.argv[1]); rows=[]
    for p in sorted(ui.glob('aniscene_*.arc_')):
        try:
            raw=blz_decompress(p.read_bytes()); a=parse_darc(raw)
            paths={n.path for n in a.nodes if not n.is_dir}
            if not set(SUB_TEXTURES)<=paths: continue
            rows.append(patch_one(p))
            panes,fmts=verify_one(p)
            if panes != SUB_PANES or any(v!=8 for v in fmts.values()):
                raise RuntimeError(f'dogrulama: panes={panes}, fmts={fmts}')
        except Exception as e:
            print(f'HATA {p}: {e}',file=sys.stderr); return 1
    print(json.dumps({'patched':len(rows),'files':rows},ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
