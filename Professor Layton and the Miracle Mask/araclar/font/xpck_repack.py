from pathlib import Path
import struct, os, sys
sys.path.insert(0, str(Path(__file__).parent))
from xfsa_extract import level5_dec

def align4(n): return (n+3)&~3

def repack(orig_path, replacements, out_path):
    b=bytearray(open(orig_path,'rb').read())
    assert b[:4]==b'XPCK'
    fc1,fc2=b[4],b[5]; fc=((fc2&0xF)<<8)|fc1
    tmp1,tmp2,tmp3,tmp4,tmp5=struct.unpack_from('<5H',b,6)
    fio=tmp1<<2; nto=tmp2<<2; datao=tmp3<<2
    names=level5_dec(b,nto)
    files=[]
    for i in range(fc):
        eoff=fio+i*12
        crc,nameoff,offlo,sizelo,offhi,sizehi=struct.unpack_from('<IHHHBB',b,eoff)
        fileoff=((offhi<<16)|offlo)<<2
        size=(sizehi<<16)|sizelo
        end=names.find(b'\0',nameoff)
        name=names[nameoff:end].decode('ascii','replace')
        payload=bytes(b[datao+fileoff:datao+fileoff+size])
        if name in replacements:
            rv=replacements[name]
            payload=open(rv,'rb').read() if isinstance(rv,(str,os.PathLike)) else bytes(rv)
        files.append([name,payload,eoff,crc,nameoff])
    # Preserve all metadata prefix through data offset; rebuild data compactly on 4-byte boundaries.
    out=bytearray(b[:datao])
    pos=0
    for name,payload,eoff,crc,nameoff in files:
        pos=align4(pos)
        if len(out)<datao+pos: out.extend(b'\0'*(datao+pos-len(out)))
        fileoff_units=pos>>2
        size=len(payload)
        if fileoff_units >= (1<<24) or size >= (1<<24): raise ValueError('XPCK field overflow')
        struct.pack_into('<IHHHBB',out,eoff,crc,nameoff,fileoff_units&0xffff,size&0xffff,(fileoff_units>>16)&0xff,(size>>16)&0xff)
        out.extend(payload)
        pos += size
    # Match original writer behavior: 8 zero bytes after last member, then 4-byte align.
    out.extend(b'\0'*8); pos += 8
    while (len(out)-datao)&3: out.append(0); pos += 1
    struct.pack_into('<I',out,16,(len(out)-datao)>>2)
    open(out_path,'wb').write(out)
    return [(x[0],len(x[1])) for x in files],len(out)

if __name__=='__main__':
    orig,out,fnt=sys.argv[1:4]
    print(repack(orig,{'FNT.bin':fnt},out))
