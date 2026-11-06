from pathlib import Path
import struct, hashlib, zipfile, os, json

def lz11_decompress(data: bytes)->bytes:
    if not data or data[0]!=0x11: raise ValueError('not LZ11')
    size=data[1]|(data[2]<<8)|(data[3]<<16); pos=4
    if size==0:
        if len(data)<8: raise ValueError('truncated ext size')
        size=struct.unpack_from('<I',data,4)[0]; pos=8
    out=bytearray()
    while len(out)<size:
        if pos>=len(data): raise ValueError('truncated flags')
        flags=data[pos]; pos+=1
        for bit in range(8):
            if len(out)>=size: break
            if flags & (0x80>>bit):
                if pos>=len(data): raise ValueError('truncated comp')
                b1=data[pos]; pos+=1
                hi=b1>>4
                if hi==0:
                    if pos+1>=len(data): raise ValueError('trunc case0')
                    b2=data[pos]; b3=data[pos+1]; pos+=2
                    length=((b1&0xF)<<4 | (b2>>4)) + 0x11
                    disp=((b2&0xF)<<8 | b3) + 1
                elif hi==1:
                    if pos+2>=len(data): raise ValueError('trunc case1')
                    b2,b3,b4=data[pos],data[pos+1],data[pos+2]; pos+=3
                    length=((b1&0xF)<<12 | b2<<4 | (b3>>4)) + 0x111
                    disp=((b3&0xF)<<8 | b4) + 1
                else:
                    if pos>=len(data): raise ValueError('trunc normal')
                    b2=data[pos];pos+=1
                    length=hi+1
                    disp=((b1&0xF)<<8 | b2)+1
                if disp>len(out): raise ValueError(f'bad disp {disp}>{len(out)}')
                for _ in range(length):
                    out.append(out[-disp])
                    if len(out)>=size: break
            else:
                if pos>=len(data): raise ValueError('truncated literal')
                out.append(data[pos]);pos+=1
                if len(out)>=size: break
    return bytes(out)

def darc_entries(data:bytes):
    if data[:4]!=b'darc': raise ValueError('not darc')
    e='<' if data[4:6]==b'\xff\xfe' else '>'
    magic,bom,hlen,ver,flen,ft_off,ft_len,data_off=struct.unpack_from(e+'4sHHIIIII',data,0)
    root=struct.unpack_from(e+'III',data,ft_off); n=root[2]
    names_start=ft_off+n*12
    nodes=[]
    def name_at(off):
        q=names_start+off; chars=[]
        while q+2<=ft_off+ft_len:
            c=struct.unpack_from(e+'H',data,q)[0];q+=2
            if c==0: break
            chars.append(c)
        return ''.join(chr(c) for c in chars)
    # build paths with directory stack via end indices
    stack=[] # (end_index, name)
    for i in range(n):
        x,y,z=struct.unpack_from(e+'III',data,ft_off+i*12)
        isdir=bool(x&0x01000000); noff=x&0x00ffffff; name=name_at(noff)
        while stack and i>=stack[-1][0]: stack.pop()
        if i==0: path=''
        elif name=='.': path=''
        else:
            prefix='/'.join(s[1] for s in stack if s[1] not in ('','.'))
            path=(prefix+'/' if prefix else '')+name
        nodes.append({'index':i,'name':name,'path':path,'isdir':isdir,'a':y,'b':z})
        if isdir and i not in (0,1): stack.append((z,name))
    return nodes

if __name__=='__main__':
    zpath=Path('/mnt/data/0004000000068F00.00000003 Pullblox (CTR-N-JCAP) (E).zip')
    outroot=Path('/mnt/data/pullblox_assets_dec'); outroot.mkdir(exist_ok=True)
    records=[]
    with zipfile.ZipFile(zpath) as z:
        for lang in ['EURen','EURde','EURes','EURfr','EURit']:
            for pack in ['Game_U','MenuTtl_U','Msg','Res_U']:
                name=f'romfs/{lang}/lyt/{pack}.lz'
                raw=z.read(name); dec=lz11_decompress(raw)
                p=outroot/lang; p.mkdir(exist_ok=True)
                (p/(pack+'.darc')).write_bytes(dec)
                nodes=darc_entries(dec)
                for nd in nodes:
                    if nd['isdir'] or not nd['path']: continue
                    off,size=nd['a'],nd['b']; blob=dec[off:off+size]
                    records.append({'lang':lang,'pack':pack,'path':nd['path'],'off':off,'size':size,'sha1':hashlib.sha1(blob).hexdigest(),'magic':blob[:4].decode('latin1')})
    Path('/mnt/data/pullblox_work/asset_inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    from collections import defaultdict
    by=defaultdict(list)
    for r in records: by[(r['pack'],r['path'])].append(r)
    for k,arr in sorted(by.items()):
        if len(arr)>=2 and len({x['sha1'] for x in arr})>1:
            print(k, [(x['lang'],x['size'],x['magic'],x['sha1'][:8]) for x in arr])
