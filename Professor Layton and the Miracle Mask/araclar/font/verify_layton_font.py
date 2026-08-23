import hashlib, os, struct, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import xfsa_extract
from xfsa_extract import level5_dec
from fnt01_parse import parse as parse_fnt
from make_turkish_font import Xi

TARGETS = {
    'fnt/[eu]/nrm.xf': 'nrm',
    'fnt/[eu]/sml.xf': 'sml',
}
PUA = {
    0xE000:0x00C7, 0xE001:0x00E7, 0xE002:0x011E, 0xE003:0x011F,
    0xE004:0x0130, 0xE005:0x0131, 0xE006:0x00D6, 0xE007:0x00F6,
    0xE008:0x015E, 0xE009:0x015F, 0xE00A:0x00DC, 0xE00B:0x00FC,
}

def xpck_members(path):
    b=Path(path).read_bytes(); assert b[:4]==b'XPCK'
    fc=((b[5]&0xf)<<8)|b[4]
    fio,nto,datao,_,_=struct.unpack_from('<5H',b,6)
    fio<<=2; nto<<=2; datao<<=2
    names=level5_dec(b,nto); out={}
    for i in range(fc):
        crc,nameoff,offlo,sizelo,offhi,sizehi=struct.unpack_from('<IHHHBB',b,fio+i*12)
        fileoff=((offhi<<16)|offlo)<<2; size=(sizehi<<16)|sizelo
        end=names.find(b'\0',nameoff); name=names[nameoff:end].decode('ascii')
        out[name]=b[datao+fileoff:datao+fileoff+size]
    return out

def verify_xf(path, label):
    members=xpck_members(path)
    assert {'FNT.bin','000.xi'} <= set(members)
    with tempfile.TemporaryDirectory() as td:
        fntp=Path(td)/'FNT.bin'; xip=Path(td)/'000.xi'
        fntp.write_bytes(members['FNT.bin']); xip.write_bytes(members['000.xi'])
        f=parse_fnt(fntp); xi=Xi(xip)
        by={i['cp']:i for i in f['infos']}
        required=set(PUA)|set(PUA.values())
        missing=sorted(required-set(by))
        assert not missing, f'{label}: missing {missing}'
        # Every PUA alias must resolve to exactly the same size/advance/image location
        # as its intended real Unicode glyph.
        for pua, real in PUA.items():
            a,b=by[pua],by[real]
            assert (a['si'],a['adv'],a['idx'],a['x'],a['y'],a['size']) == (b['si'],b['adv'],b['idx'],b['x'],b['y'],b['size']), (label,hex(pua),hex(real))
        # All referenced glyph rectangles must fit in the atlas and channels must be valid.
        for cp in required:
            z=by[cp]; ox,oy,w,h=z['size']
            assert z['idx'] in (0,1,2), (label,hex(cp),'channel',z['idx'])
            assert z['x']>=0 and z['y']>=0 and z['x']+w<=xi.width and z['y']+h<=xi.height, (label,hex(cp),'bounds')
        # XI tile table must be internally valid.
        assert min(xi.tiles)>=0 and max(xi.tiles)*128 < len(xi.data)
        return {
            'label':label,'xf_size':Path(path).stat().st_size,'font_records':len(f['infos']),
            'size_records':len(f['sizes']),'atlas':f'{xi.width}x{xi.height}',
            'tile_refs':len(xi.tiles),'unique_tiles':len(set(xi.tiles)),
            'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        }

def verify_fa(orig, patched):
    _,fo=xfsa_extract.parse(orig); _,fp=xfsa_extract.parse(patched)
    assert len(fo)==len(fp)
    mo={n:(p,s,i) for n,p,s,i in fo}; mp={n:(p,s,i) for n,p,s,i in fp}
    assert set(mo)==set(mp)
    bo=Path(orig).read_bytes(); bp=Path(patched).read_bytes()
    changed=[]
    for n in mo:
        po,so,_=mo[n]; pp,sp,_=mp[n]
        if hashlib.sha256(bo[po:po+so]).digest()!=hashlib.sha256(bp[pp:pp+sp]).digest(): changed.append(n)
    assert set(changed)==set(TARGETS), changed
    results=[]
    with tempfile.TemporaryDirectory() as td:
        for n,label in TARGETS.items():
            pp,sp,_=mp[n]; out=Path(td)/(label+'.xf'); out.write_bytes(bp[pp:pp+sp])
            results.append(verify_xf(out,label))
    return len(fp),changed,results

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: verify_layton_font.py ORIGINAL_lt5_a.fa PATCHED_lt5_a.fa')
    count,changed,results=verify_fa(sys.argv[1],sys.argv[2])
    print(f'XFSA OK: {count} members; only changed: {changed}')
    for r in results: print(r)
    print('PASS: Turkish PUA aliases and Unicode glyphs validated.')
