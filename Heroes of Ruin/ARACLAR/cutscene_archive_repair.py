from pathlib import Path
import struct, shutil, json, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hor_formats import blz_decompress, parse_darc


def _lz_common(data: bytes):
    def search(pos):
        start=max(0,pos-0x1002)
        lo,hi=0,min(18,len(data)-pos)
        bp=bl=0
        while lo<=hi:
            ln=(lo+hi)//2
            m=data[pos:pos+ln]
            mp=data.rfind(m,start,pos)
            if mp<0:
                hi=ln-1
            else:
                if ln>bl: bp,bl=mp,ln
                lo=ln+1
        return bp,bl
    result=bytearray(); cur=0
    ignD=ignC=0; ignore={0:(0,0)}; best=0
    while cur<len(data):
        fpos=len(result); result.append(0); flags=0; ignC+=1
        for i in range(8):
            if cur>=len(data): break
            sp,sl=search(cur); disp=cur-sp-3
            if sl>2:
                flags|=1<<(7-i)
                result.append((((sl-3)&0xF)<<4)|((disp>>8)&0xF));result.append(disp&0xff)
                cur+=sl;ignD+=sl;ignC+=2
            else:
                result.append(data[cur]);cur+=1;ignD+=1;ignC+=1
            saving=cur-len(result)
            if saving>best:
                ignD=ignC=0;best=saving
            if saving not in ignore: ignore[saving]=(cur,len(result))
        result[fpos]=flags
    final=cur-len(result)
    if final<best:
        final+=1
        while final not in ignore: final+=1
        return bytes(result),cur-ignore[final][0],len(result)-ignore[final][1]
    return bytes(result),0,0

def blz_compress_canonical(data: bytes) -> bytes:
    c,ignD,ignC=_lz_common(data[::-1]); c=bytearray(c[::-1])
    if not c or len(data)+4 < ((len(c)+3)&~3)+8:
        out=bytearray(data)
        while len(out)%4: out.append(0)
        out+=b'\0'*4
        return bytes(out)
    actual=len(c)-ignC
    c=bytearray(data[:ignD])+c[ignC:]
    extra=len(data)-len(c); hlen=8
    while len(c)%4: c.append(0xFF); hlen+=1
    ptr=len(c); c+=b'\0'*8
    struct.pack_into('<I',c,ptr,actual+hlen); c[ptr+3]=hlen
    struct.pack_into('<I',c,ptr+4,extra-hlen)
    return bytes(c)

def get_file(raw, arc, path):
    n=next(n for n in arc.nodes if not n.is_dir and n.path==path)
    return raw[n.field1:n.field1+n.field2]

def find_bclyt_path(arc):
    hits=[n.path for n in arc.nodes if not n.is_dir and n.path.lower().endswith('.bclyt')]
    if len(hits)!=1: raise ValueError(f'expected 1 BCLYT, got {hits}')
    return hits[0]

def sections(b):
    if b[:4]!=b'CLYT' or struct.unpack_from('<H',b,4)[0]!=0xFEFF: raise ValueError('bad BCLYT')
    cnt=struct.unpack_from('<H',b,0x10)[0];pos=struct.unpack_from('<H',b,6)[0]
    out=[]
    for _ in range(cnt):
        sz=struct.unpack_from('<I',b,pos+4)[0]
        if sz<8 or pos+sz>len(b): raise ValueError('bad section')
        out.append((b[pos:pos+4],b[pos:pos+sz]));pos+=sz
    if pos!=len(b): raise ValueError('BCLYT trailing bytes')
    return out

def txl_names(sec):
    cnt=struct.unpack_from('<H',sec,8)[0]; names=[]
    for i in range(cnt):
        rel=struct.unpack_from('<I',sec,12+4*i)[0]; p=12+rel
        e=sec.index(0,p)
        names.append(sec[p:e].decode('ascii'))
    return names

def build_txl(names):
    sec=bytearray(b'txl1'+b'\0'*4+struct.pack('<HH',len(names),0))
    sec += b'\0'*(4*len(names))
    for i,name in enumerate(names):
        pos=len(sec); struct.pack_into('<I',sec,12+4*i,pos-12)
        sec += name.encode('ascii')+b'\0'
    while len(sec)%4: sec.append(0)
    struct.pack_into('<I',sec,4,len(sec))
    return bytes(sec)

def repair_bclyt(orig_b, patched_b):
    os=sections(orig_b); ps=sections(patched_b)
    otxl=next(s for m,s in os if m==b'txl1')
    base=txl_names(otxl)
    wanted=base+['tr_sub_bg.bclim','tr_sub_text.bclim']
    out=bytearray(patched_b[:0x14]); rebuilt=[]
    for m,s in ps:
        rebuilt.append(build_txl(wanted) if m==b'txl1' else s)
    out=bytearray(patched_b[:0x14])+bytearray().join(rebuilt)
    struct.pack_into('<I',out,0x0C,len(out))
    # count stays that of patched layout
    # Verify exact base texture list prefix and new names
    ns=txl_names(next(s for m,s in sections(bytes(out)) if m==b'txl1'))
    if ns!=wanted: raise RuntimeError('txl verification failed')
    return bytes(out)

def rebuild_darc(patched_raw, replacement_path, replacement_blob):
    arc=parse_darc(patched_raw)
    files=sorted([n for n in arc.nodes if not n.is_dir],key=lambda n:n.field1)
    blobs={n.path: patched_raw[n.field1:n.field1+n.field2] for n in files}
    blobs[replacement_path]=replacement_blob
    out=bytearray(patched_raw[:arc.data_offset])
    for idx,n in enumerate(files):
        if idx>0:
            while len(out)%0x80: out.append(0)
        start=len(out); blob=blobs[n.path]
        struct.pack_into('<II',out,n.node_offset+4,start,len(blob))
        out+=blob
    struct.pack_into('<I',out,0x0C,len(out))
    # Verify archive and all paths
    a2=parse_darc(bytes(out))
    if [n.path for n in a2.nodes]!=[n.path for n in arc.nodes]: raise RuntimeError('DARC path mismatch')
    return bytes(out)

def repair_one(orig_path, patched_path, out_path):
    oraw=blz_decompress(orig_path.read_bytes()); praw=blz_decompress(patched_path.read_bytes())
    oa=parse_darc(oraw); pa=parse_darc(praw)
    op=find_bclyt_path(oa); pp=find_bclyt_path(pa)
    if op!=pp: raise RuntimeError((op,pp))
    ob=get_file(oraw,oa,op); pb=get_file(praw,pa,pp)
    fb=repair_bclyt(ob,pb)
    rraw=rebuild_darc(praw,pp,fb)
    packed=blz_compress_canonical(rraw)
    if blz_decompress(packed)!=rraw: raise RuntimeError('BLZ roundtrip')
    # strong validations
    ra=parse_darc(rraw); rb=get_file(rraw,ra,pp)
    names=txl_names(next(s for m,s in sections(rb) if m==b'txl1'))
    orig_names=txl_names(next(s for m,s in sections(ob) if m==b'txl1'))
    if names[:-2]!=orig_names or names[-2:]!=['tr_sub_bg.bclim','tr_sub_text.bclim']:
        raise RuntimeError('texture list mismatch')
    out_path.parent.mkdir(parents=True,exist_ok=True);out_path.write_bytes(packed)
    return {'name':out_path.name,'orig_packed':orig_path.stat().st_size,'old_patched':patched_path.stat().st_size,'fixed_packed':len(packed),'fixed_raw':len(rraw),'textures':len(names)}

if __name__=='__main__':
    if len(sys.argv)!=4:
        print('usage: repair <original UI dir> <buggy patched UI dir> <out UI dir>'); raise SystemExit(2)
    o,p,out=map(Path,sys.argv[1:]); rows=[]
    for pf in sorted(p.glob('aniscene_*.arc_')):
        of=o/pf.name
        if of.exists(): rows.append(repair_one(of,pf,out/pf.name))
    print(json.dumps(rows,indent=2))
