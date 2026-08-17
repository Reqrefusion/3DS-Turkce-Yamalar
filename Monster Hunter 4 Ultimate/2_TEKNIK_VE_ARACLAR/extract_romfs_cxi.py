from pathlib import Path
import struct, sys, os

cxi=Path(sys.argv[1]); out=Path(sys.argv[2])
with cxi.open('rb') as f:
    f.seek(0x1B0)
    ro_units, rs_units, _ = struct.unpack('<III', f.read(12))
    romfs_off=ro_units*0x200
    f.seek(romfs_off)
    if f.read(4)!=b'IVFC': raise SystemExit('No IVFC')
    # This update CXI places usable RomFS Level3 at +0x1000. Verify header shape.
    candidates=[0x1000]
    level3=None
    for rel in candidates:
        f.seek(romfs_off+rel); h=f.read(0x28)
        if len(h)==0x28:
            vals=struct.unpack('<10I',h)
            if vals[0] in (0x28,0x2c) and vals[8] < rs_units*0x200:
                level3=romfs_off+rel; header=vals; break
    if level3 is None: raise SystemExit('Could not locate Level3')
    (hdrlen, dh_off,dh_len, dm_off,dm_len, fh_off,fh_len, fm_off,fm_len, data_off)=header
    print('romfs_off',hex(romfs_off),'level3',hex(level3-romfs_off),'header',header)
    dm_base=level3+dm_off; fm_base=level3+fm_off; data_base=level3+data_off
    SENT=0xFFFFFFFF
    def read_dir(off):
        f.seek(dm_base+off); b=f.read(24)
        parent,sib,childd,childf,nexth,nlen=struct.unpack('<6I',b)
        name=f.read(nlen).decode('utf-16le') if nlen else ''
        return dict(off=off,parent=parent,sib=sib,childd=childd,childf=childf,nexth=nexth,nlen=nlen,name=name)
    def read_file(off):
        f.seek(fm_base+off); b=f.read(32)
        parent,sib,doff,dlen,nexth,nlen=struct.unpack('<IIQQII',b)
        name=f.read(nlen).decode('utf-16le') if nlen else ''
        return dict(off=off,parent=parent,sib=sib,doff=doff,dlen=dlen,nexth=nexth,nlen=nlen,name=name)
    seen_dirs=set(); seen_files=set(); count=[0,0]
    def walk_dir(off, rel):
        if off in seen_dirs: return
        seen_dirs.add(off); count[0]+=1
        d=read_dir(off)
        cur=d['childf']
        while cur!=SENT:
            if cur in seen_files: break
            seen_files.add(cur); count[1]+=1
            fe=read_file(cur)
            dest=out/rel/fe['name']; dest.parent.mkdir(parents=True,exist_ok=True)
            f.seek(data_base+fe['doff'])
            remaining=fe['dlen']
            with dest.open('wb') as g:
                while remaining:
                    chunk=f.read(min(1024*1024,remaining))
                    if not chunk: raise EOFError(dest)
                    g.write(chunk); remaining-=len(chunk)
            cur=fe['sib']
        cur=d['childd']
        while cur!=SENT:
            cd=read_dir(cur)
            walk_dir(cur, rel/cd['name'])
            cur=cd['sib']
    out.mkdir(parents=True,exist_ok=True)
    walk_dir(0,Path('.'))
    print('dirs',count[0],'files',count[1])
