import struct, os, sys
sys.path.insert(0,'/mnt/data')
from xfsa_extract import level5_dec

def align4(n): return (n+3)&~3

def l5raw(data):
    return struct.pack('<I', len(data)<<3) + data

def parse_fnt(path):
    b=open(path,'rb').read()
    assert b[:6]==b'FNTC01'
    version=struct.unpack_from('<H',b,8)[0]
    large_h,small_h=struct.unpack_from('<HH',b,12)
    esc_l,esc_s=struct.unpack_from('<HH',b,16)
    cso,csc,lco,lcc,sco,scc=struct.unpack_from('<6H',b,0x1c)
    cs=level5_dec(b,cso*4)
    lc=level5_dec(b,lco*4)
    sc=level5_dec(b,sco*4) if scc else b''
    assert len(cs)==csc*4,(len(cs),csc)
    assert len(lc)==lcc*8,(len(lc),lcc)
    assert not scc or len(sc)==scc*8,(len(sc),scc)
    lr=[bytearray(lc[i:i+8]) for i in range(0,len(lc),8)]
    sr=[bytearray(sc[i:i+8]) for i in range(0,len(sc),8)]
    return dict(blob=b, version=version, large_h=large_h,small_h=small_h,esc_l=esc_l,esc_s=esc_s,cs=cs,lr=lr,sr=sr)

def code(rec): return struct.unpack_from('<H',rec,0)[0]

def rebuild(f, mappings, outpath):
    # mappings: dst code -> source code, copy source visual/metrics exactly.
    orig_lr=f['lr']
    by={code(r):bytes(r) for r in orig_lr}
    old_escape_code=code(orig_lr[f['esc_l']]) if 0<=f['esc_l']<len(orig_lr) else None
    # Replace any existing destination, otherwise insert, then sort.
    rec_by={code(r):bytearray(r) for r in orig_lr}
    for dst,src in mappings.items():
        if src not in by: raise KeyError(hex(src))
        r=bytearray(by[src]); struct.pack_into('<H',r,0,dst); rec_by[dst]=r
    lr=sorted(rec_by.values(),key=code)
    new_escape=f['esc_l']
    if old_escape_code is not None:
        for i,r in enumerate(lr):
            if code(r)==old_escape_code:
                new_escape=i;break
    csblock=l5raw(f['cs'])
    cso=0x28
    lco=align4(cso+len(csblock))
    lcraw=b''.join(lr); lcblock=l5raw(lcraw)
    if f['sr']:
        sco=align4(lco+len(lcblock)); scblock=l5raw(b''.join(f['sr']))
    else:
        sco=align4(lco+len(lcblock)); scblock=b''
    out=bytearray(sco+len(scblock))
    # preserve first 0x28 and then patch offsets/counts/escape
    out[:0x28]=f['blob'][:0x28]
    struct.pack_into('<H',out,16,new_escape)
    struct.pack_into('<6H',out,0x1c,cso//4,len(f['cs'])//4,lco//4,len(lr),sco//4,len(f['sr']))
    out[cso:cso+len(csblock)]=csblock
    out[lco:lco+len(lcblock)]=lcblock
    if scblock: out[sco:sco+len(scblock)]=scblock
    open(outpath,'wb').write(out)
    # verify
    q=parse_fnt(outpath)
    qcodes={code(r) for r in q['lr']}
    assert all(x in qcodes for x in mappings)
    return len(out),new_escape,old_escape_code

if __name__=='__main__':
    PUA={
      0xE000:0x00C7, 0xE001:0x00E7,
      0xE002:0x0047, 0xE003:0x0067,
      0xE004:0x0049, 0xE005:0x0069,
      0xE006:0x00D6, 0xE007:0x00F6,
      0xE008:0x0053, 0xE009:0x0073,
      0xE00A:0x00DC, 0xE00B:0x00FC,
    }
    for variant in ['eu_nrm','eu_sml']:
      p=f'/mnt/data/font_scan/{variant}/FNT.bin'; f=parse_fnt(p)
      print(variant,'escape',f['esc_l'],hex(code(f['lr'][f['esc_l']])), 'counts',len(f['cs'])//4,len(f['lr']))
      out=f'/mnt/data/font_scan/{variant}/FNT.test.bin'; print(' ->',rebuild(f,PUA,out))
