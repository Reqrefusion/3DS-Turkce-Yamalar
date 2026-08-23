import struct, os, sys

def dec_lz10(data, outlen):
    p=0; out=bytearray()
    while len(out)<outlen:
        flags=data[p]; p+=1
        for bit in range(7,-1,-1):
            if len(out)>=outlen: break
            if flags & (1<<bit):
                b1=data[p]; b2=data[p+1]; p+=2
                length=(b1>>4)+3
                disp=((b1&0xF)<<8)|b2
                src=len(out)-disp-1
                if src<0: raise ValueError(('bad lz disp',len(out),disp,p))
                for _ in range(length):
                    out.append(out[src]); src+=1
                    if len(out)>=outlen: break
            else:
                out.append(data[p]); p+=1
    return bytes(out)

def dec_huf(data, outlen, bitdepth):
    # Nintendo HUF20 headerless as used by Level5
    p=0
    tree_size=data[p]; tree_root=data[p+1]; p+=2
    tree=data[p:p+tree_size*2]; p += tree_size*2
    out=bytearray(outlen)
    tree_pos=tree_root; nxt=0; i=0; bits=0; flag=0
    symbols=outlen*8//bitdepth
    while i<symbols:
        if bits==0:
            if p+4>len(data): raise EOFError('huf flags')
            flag=struct.unpack_from('<i',data,p)[0] & 0xffffffff; p+=4; bits=32
        nxt += ((tree_pos & 0x3F)<<1)+2
        bits-=1
        direction=2 - ((flag>>bits)&1)  # 1 or 2
        leaf=((tree_pos>>(5+direction))&1)!=0
        idx=nxt-direction
        if not (0<=idx<len(tree)):
            raise ValueError(('bad tree idx',idx,len(tree),tree_pos,nxt,direction,i))
        tree_pos=tree[idx]
        if leaf:
            if bitdepth==8:
                out[i]=tree_pos; i+=1
            else:
                # Level5 uses Endian.Big for 4-bit HUF
                if i&1==0: out[i//2] |= tree_pos&0xF
                else: out[i//2] |= (tree_pos&0xF)<<4
                i+=1
            tree_pos=tree_root; nxt=0
    return bytes(out)

def dec_rle(data,outlen):
    p=0; out=bytearray()
    while len(out)<outlen:
        flag=data[p];p+=1
        if flag&0x80:
            n=(flag&0x7f)+3
            b=data[p];p+=1
            out.extend([b]*min(n,outlen-len(out)))
        else:
            n=(flag&0x7f)+1
            out.extend(data[p:p+min(n,outlen-len(out))]);p+=n
    return bytes(out)

def level5_dec(blob, off):
    v=struct.unpack_from('<I',blob,off)[0]; typ=v&7; outlen=v>>3; data=blob[off+4:]
    if typ==0: return bytes(data[:outlen])
    if typ==1: return dec_lz10(data,outlen)
    if typ==2: return dec_huf(data,outlen,4)
    if typ==3: return dec_huf(data,outlen,8)
    if typ==4: return dec_rle(data,outlen)
    raise ValueError(('unsupported',typ,hex(v)))

def cstr_sjis(buf,off):
    end=buf.find(b'\0',off)
    if end<0: end=len(buf)
    return buf[off:end].decode('cp932','replace')

def parse(path, outroot=None):
    blob=open(path,'rb').read()
    hdr=struct.unpack_from('<4sIIIIIHHII',blob,0)
    magic,t0o,t1o,feo,nto,datao,c0,c1,fc,infosz=hdr
    assert magic==b'XFSA'
    t0=level5_dec(blob,t0o); t1=level5_dec(blob,t1o); fe=level5_dec(blob,feo); names=level5_dec(blob,nto)
    assert len(t0)==c0*16,(len(t0),c0)
    assert len(t1)==c1*4,(len(t1),c1)
    assert len(fe)==fc*12,(len(fe),fc)
    entries=[]
    for i in range(fc):
        crc,comb1,comb2=struct.unpack_from('<III',fe,i*12)
        off=comb1&0x03ffffff
        size=comb2&0x007fffff
        nameoff=((comb1>>26)*512)+(comb2>>23)
        entries.append((crc,off,size,nameoff))
    files=[]
    for di in range(c0):
        h,comb1,feoff,unk,comb3=struct.unpack_from('<IIhhI',t0,di*16)
        first_name=comb1>>14; count=comb1&0x3fff; dirnameoff=comb3>>14
        dname=cstr_sjis(names,dirnameoff)
        for idx in range(feoff,feoff+count):
            crc,off,size,nameoff=entries[idx]
            fname=cstr_sjis(names,first_name+nameoff)
            full=(dname.rstrip('/\\')+'/'+fname).lstrip('/\\') if dname else fname
            datapos=datao+(off<<4)
            files.append((full,datapos,size,idx))
            if outroot:
                dest=os.path.join(outroot,full.replace('\\','/'))
                os.makedirs(os.path.dirname(dest),exist_ok=True)
                open(dest,'wb').write(blob[datapos:datapos+size])
    return hdr,files

if __name__=='__main__':
    for path in sys.argv[1:]:
        out='/mnt/data/xfsa_out/'+os.path.basename(path)
        hdr,files=parse(path,out)
        print(path, 'files',len(files),'out',out)
        for x in files:
            n=x[0].lower()
            if 'fnt' in n or n.endswith('.xf') or 'font' in n:
                print('FONT?',x)
