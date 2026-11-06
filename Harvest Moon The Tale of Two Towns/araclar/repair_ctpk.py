#!/usr/bin/env python3
from pathlib import Path
import struct, argparse, sys
sys.path.insert(0,str(Path(__file__).parent))
from etc1_codec import decode_rgba4, encode_etc1a4, decode_etc1a4

def repair(orig_p, mod_p, out_p, preview_dir=None):
    o=bytearray(Path(orig_p).read_bytes()); m=Path(mod_p).read_bytes()
    if o[:4]!=b'CTPK' or m[:4]!=b'CTPK': raise ValueError('CTPK değil')
    no=struct.unpack_from('<H',o,6)[0]; nm=struct.unpack_from('<H',m,6)[0]
    if no!=nm: raise ValueError('texture count farklı')
    do=struct.unpack_from('<I',o,8)[0]; dm=struct.unpack_from('<I',m,8)[0]
    changed=[]
    pd=Path(preview_dir) if preview_dir else None
    if pd: pd.mkdir(parents=True,exist_ok=True)
    for i in range(no):
        oo=0x20+i*0x20; mo=0x20+i*0x20
        osz,orel=struct.unpack_from('<II',o,oo+4); msz,mrel=struct.unpack_from('<II',m,mo+4)
        of=o[oo+12]; mf=m[mo+12]; ow,oh=struct.unpack_from('<HH',o,oo+16); mw,mh=struct.unpack_from('<HH',m,mo+16)
        if (ow,oh)!=(mw,mh): continue
        oraw=bytes(o[do+orel:do+orel+osz]); mraw=m[dm+mrel:dm+mrel+msz]
        # Previous tool converted translated ETC1A4 textures to RGBA4. Re-encode to original ETC1A4 in-place.
        if of==0x0D and mf==0x04 and msz==osz*2:
            im=decode_rgba4(mraw,ow,oh); enc=encode_etc1a4(im)
            if len(enc)!=osz: raise ValueError(f'{i}: encoded size mismatch')
            o[do+orel:do+orel+osz]=enc; changed.append(i)
            if pd: decode_etc1a4(enc,ow,oh).save(pd/f'tex_{i:02d}.png')
        # Same-format/same-size texture changed: copy only raw texture data, never container metadata.
        elif of==mf and osz==msz and oraw!=mraw:
            # Only use when the mod's metadata for this texture matches dimensions/format exactly.
            o[do+orel:do+orel+osz]=mraw; changed.append(i)
    Path(out_p).parent.mkdir(parents=True,exist_ok=True); Path(out_p).write_bytes(o)
    return changed

if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('orig');ap.add_argument('mod');ap.add_argument('out');ap.add_argument('--preview-dir');a=ap.parse_args()
 ch=repair(a.orig,a.mod,a.out,a.preview_dir); print('changed',ch,'size',Path(a.out).stat().st_size)
