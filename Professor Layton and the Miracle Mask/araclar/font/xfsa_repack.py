import os, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from xfsa_extract import level5_dec, parse

HDR = '<4sIIIIIHHII'
HDR_SIZE = struct.calcsize(HDR)

def align(n, a):
    return (n + a - 1) & ~(a - 1)

def l5raw(data: bytes) -> bytes:
    return struct.pack('<I', len(data) << 3) + data

def repack(orig_path, replacements, out_path):
    orig_path = str(orig_path); out_path = str(out_path)
    blob = Path(orig_path).read_bytes()
    magic,t0o,t1o,feo,nto,datao,c0,c1,fc,infosz = struct.unpack_from(HDR, blob, 0)
    if magic != b'XFSA': raise ValueError('Not XFSA')
    t0 = level5_dec(blob, t0o)
    t1 = level5_dec(blob, t1o)
    fe = bytearray(level5_dec(blob, feo))
    names = level5_dec(blob, nto)
    if len(fe) != fc * 12: raise ValueError('bad file-entry table')

    # Build source payload list by file-entry index. parse() resolves directory/name tables.
    _, files = parse(orig_path)
    by_idx = {idx:(name,pos,size) for name,pos,size,idx in files}
    if len(by_idx) != fc: raise ValueError(f'entry mismatch {len(by_idx)} != {fc}')

    replacement_bytes = {}
    for name, value in replacements.items():
        replacement_bytes[name] = Path(value).read_bytes() if isinstance(value, (str, os.PathLike)) else bytes(value)

    payloads=[]
    replaced=[]
    for idx in range(fc):
        name,pos,size = by_idx[idx]
        payload = replacement_bytes.get(name, blob[pos:pos+size])
        if name in replacement_bytes: replaced.append(name)
        payloads.append((name, bytes(payload)))
    missing=set(replacement_bytes)-set(replaced)
    if missing: raise KeyError(f'replacement path(s) not found: {sorted(missing)}')

    # Rebuild payload area compactly, keeping 16-byte XFSA offset units.
    data = bytearray()
    for idx,(name,payload) in enumerate(payloads):
        apos=align(len(data),16)
        if apos>len(data): data.extend(b'\0'*(apos-len(data)))
        off_units=apos>>4; size=len(payload)
        if off_units >= (1<<26): raise ValueError('XFSA data offset overflow')
        if size >= (1<<23): raise ValueError(f'XFSA member too large: {name}')
        crc,comb1,comb2=struct.unpack_from('<III',fe,idx*12)
        comb1=(comb1 & 0xFC000000) | off_units
        comb2=(comb2 & 0xFF800000) | size
        struct.pack_into('<III',fe,idx*12,crc,comb1,comb2)
        data.extend(payload)

    # Metadata blocks may use any Level-5 compression. Raw blocks are supported and
    # avoid altering their decoded contents. 128-byte data alignment mirrors source archives.
    blocks=[l5raw(t0),l5raw(t1),l5raw(bytes(fe)),l5raw(names)]
    offsets=[]; out=bytearray(b'\0'*HDR_SIZE)
    for block in blocks:
        p=align(len(out),4)
        if p>len(out): out.extend(b'\0'*(p-len(out)))
        offsets.append(p); out.extend(block)
    new_datao=align(len(out),0x80)
    if new_datao>len(out): out.extend(b'\0'*(new_datao-len(out)))
    out.extend(data)
    # info size is decoded metadata size; keep exact semantics from original.
    new_infosz=len(t0)+len(t1)+len(fe)+len(names)
    struct.pack_into(HDR,out,0,b'XFSA',offsets[0],offsets[1],offsets[2],offsets[3],new_datao,c0,c1,fc,new_infosz)
    Path(out_path).write_bytes(out)
    return {'files':fc,'replaced':replaced,'size':len(out),'data_offset':new_datao,'info_size':new_infosz}

if __name__=='__main__':
    if len(sys.argv)<5 or (len(sys.argv)-3)%2:
        raise SystemExit('usage: xfsa_repack.py ORIGINAL OUT member/path replacement [member replacement ...]')
    orig,out=sys.argv[1],sys.argv[2]
    args=sys.argv[3:]
    reps={args[i]:args[i+1] for i in range(0,len(args),2)}
    print(repack(orig,reps,out))
