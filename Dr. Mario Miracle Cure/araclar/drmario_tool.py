#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dr. Mario 3DS kaynak araçları.

SSZL/ARCV/SARC/MSBT/BFLIM çıkarma ve yeniden enjeksiyon işlemleri.
BFLIM <-> PNG işlemleri için Pillow gerekir.
"""
from __future__ import annotations
import argparse, json, math, struct
from pathlib import Path
from typing import Dict, List

# ---------------- SSZL / LZSS ----------------

def lzss_decompress(payload: bytes, expected_size: int | None = None) -> bytes:
    N, F = 4096, 18
    ring = bytearray(N)
    r = N - F
    src = 0
    out = bytearray()
    flags = 0
    while src < len(payload) and (expected_size is None or len(out) < expected_size):
        flags >>= 1
        if flags & 0x100 == 0:
            if src >= len(payload): break
            flags = payload[src] | 0xFF00
            src += 1
        if flags & 1:
            if src >= len(payload): break
            c = payload[src]; src += 1
            out.append(c); ring[r] = c; r = (r + 1) & (N - 1)
        else:
            if src + 1 >= len(payload): break
            i = payload[src]; j = payload[src + 1]; src += 2
            i |= (j & 0xF0) << 4
            length = (j & 0x0F) + 3
            for k in range(length):
                c = ring[(i + k) & (N - 1)]
                out.append(c); ring[r] = c; r = (r + 1) & (N - 1)
                if expected_size is not None and len(out) >= expected_size: break
    if expected_size is not None and len(out) != expected_size:
        raise ValueError(f'LZSS boyutu uyuşmuyor: {len(out)} != {expected_size}')
    return bytes(out)

def lzss_compress_literals(data: bytes) -> bytes:
    """Geçerli LZSS üretir; sadelik için yalnız literal bloklar kullanır."""
    out = bytearray(); p = 0
    while p < len(data):
        n = min(8, len(data) - p)
        out.append((1 << n) - 1)
        out.extend(data[p:p+n]); p += n
    return bytes(out)

def lzss_compress(data: bytes) -> bytes:
    """4 KiB halka, 3–18 bayt eşleşme; özgün çözücüyle uyumlu LZSS."""
    from collections import defaultdict, deque
    chains=defaultdict(deque);out=bytearray();pos=0;n=len(data)
    while pos<n:
        fp=len(out);out.append(0);flags=0
        for bit in range(8):
            if pos>=n:break
            key=data[pos:pos+3];q=chains[key]
            while q and pos-q[0]>4096:q.popleft()
            best=0;bestpos=0;limit=min(18,n-pos)
            if limit>=3:
                for old in reversed(q):
                    length=3
                    while length<limit and data[old+length]==data[pos+length]:length+=1
                    if length>best:best,bestpos=length,old
                    if best==limit:break
            if best>=3:
                index=(4096-18+bestpos)&4095
                out.extend((index&255,((index>>4)&240)|(best-3)));count=best
            else:
                flags|=1<<bit;out.append(data[pos]);count=1
            for i in range(pos,pos+count):
                if i+3<=n:
                    k=data[i:i+3];c=chains[k]
                    while c and i-c[0]>=4096:c.popleft()
                    c.append(i)
                    # Uzun tek renkli dokularda aramayı sınırla.
                    if len(c)>128:c.popleft()
            pos+=count
        out[fp]=flags
    return bytes(out)

def sszl_unpack(data: bytes) -> bytes:
    if data[:4] != b'SSZL' or len(data) < 16: raise ValueError('SSZL değil')
    comp_size, raw_size = struct.unpack_from('<II', data, 8)
    if len(data)<16+comp_size:raise ValueError('Kesik SSZL verisi')
    return lzss_decompress(data[16:16+comp_size], raw_size)

def sszl_pack(raw: bytes) -> bytes:
    payload = lzss_compress(raw)
    return b'SSZL' + struct.pack('<III', 0, len(payload), len(raw)) + payload

# ---------------- ARCV ----------------

def align_up(v: int, a: int) -> int:
    return (v + a - 1) & ~(a - 1)

def arcv_parse(data: bytes):
    if data[:4] != b'ARCV': raise ValueError('ARCV değil')
    count, total = struct.unpack_from('<II', data, 4)
    entries=[]; p=0x0C
    for _ in range(count):
        off,size,h=struct.unpack_from('<III',data,p)
        rawname=data[p+12:p+44]
        name=rawname.split(b'\0',1)[0].decode('utf-8','replace')
        entries.append({'offset':off,'size':size,'hash':h,'name':name,'data':data[off:off+size]})
        p += 44
    return {'count':count,'declared_size':total,'entries':entries}

def arcv_build(parsed, replacements: Dict[str, bytes] | None = None) -> bytes:
    replacements = replacements or {}; entries=parsed['entries']
    # Bu oyunun ARCV okuyucusu veri bloklarını 0x80 sınırında bekliyor.
    # 0x20 hizalama masaüstü ayrıştırıcısında çalışsa da gerçek 3DS'te
    # sonraki sahne yüklenirken siyah ekran/donmaya yol açıyor.
    header_end=0x0C+len(entries)*44; data_start=align_up(header_end,0x80)
    out=bytearray(data_start); out[:4]=b'ARCV'; struct.pack_into('<I',out,4,len(entries))
    p=0x0C; cursor=data_start; blobs=[]
    for e in entries:
        blob=replacements.get(e['name'],e['data']); cursor=align_up(cursor,0x80)
        name_b=e['name'].encode('utf-8')[:31]
        struct.pack_into('<III',out,p,cursor,len(blob),e['hash'])
        out[p+12:p+44]=name_b+b'\0'*(32-len(name_b))
        blobs.append((cursor,blob)); cursor += len(blob); p += 44
    total=align_up(cursor,0x80); out.extend(b'\0'*(total-len(out)))
    for off,blob in blobs: out[off:off+len(blob)] = blob
    struct.pack_into('<I',out,8,total)
    return bytes(out)

def arcv_extract(data: bytes, outdir: Path):
    p=arcv_parse(data); outdir.mkdir(parents=True,exist_ok=True); meta=[]
    for e in p['entries']:
        q=outdir/e['name']; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(e['data'])
        meta.append({k:e[k] for k in ('name','hash')})
    (outdir/'_arcv.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')

def arcv_inject_from_dir(template: bytes, indir: Path) -> bytes:
    parsed=arcv_parse(template); repl={}
    for e in parsed['entries']:
        q=indir/e['name']
        if q.is_file(): repl[e['name']]=q.read_bytes()
    return arcv_build(parsed,repl)

# ---------------- MSBT ----------------

def msbt_sections(data: bytes):
    if data[:8] != b'MsgStdBn': raise ValueError('MSBT değil')
    n=struct.unpack_from('<H',data,14)[0]; p=0x20; out=[]
    for _ in range(n):
        magic=data[p:p+4]; size=struct.unpack_from('<I',data,p+4)[0]; end=p+16+size
        out.append((magic,p,size,data[p:end])); p=align_up(end,16)
    return out

def msbt_labels(data: bytes) -> Dict[int,str]:
    sec=next((x for x in msbt_sections(data) if x[0]==b'LBL1'),None)
    if not sec: return {}
    d=sec[3][16:]; ng=struct.unpack_from('<I',d,0)[0]; labels={}
    for g in range(ng):
        cnt,off=struct.unpack_from('<II',d,4+g*8); p=off
        for _ in range(cnt):
            ln=d[p]; p+=1; lab=d[p:p+ln].decode('ascii','replace'); p+=ln
            idx=struct.unpack_from('<I',d,p)[0]; p+=4; labels[idx]=lab
    return labels

def msbt_texts(data: bytes) -> List[str]:
    sec=next((x for x in msbt_sections(data) if x[0]==b'TXT2'),None)
    if not sec: return []
    d=sec[3][16:]; n=struct.unpack_from('<I',d,0)[0]
    offs=list(struct.unpack_from('<'+'I'*n,d,4)) if n else []; out=[]
    for i,off in enumerate(offs):
        end=offs[i+1] if i+1<n else len(d); raw=d[off:end]
        q=0
        while q+1<len(raw):
            code=struct.unpack_from('<H',raw,q)[0]
            if code==0:
                raw=raw[:q];break
            if code==0x0E:
                if q+8>len(raw):raise ValueError('Kesik MSBT kontrol kodu')
                length=struct.unpack_from('<H',raw,q+6)[0]
                if q+8+length>len(raw):raise ValueError('Kesik MSBT kontrol verisi')
                q+=8+length
            elif code==0x0F:
                if q+6>len(raw):raise ValueError('Kesik MSBT kapanış kodu')
                q+=6
            else:q+=2
        out.append(raw.decode('utf-16le','surrogatepass'))
    return out

def msbt_replace_texts(data: bytes, texts: List[str]) -> bytes:
    old=msbt_texts(data)
    if len(old)!=len(texts): raise ValueError(f'MSBT metin sayısı uyuşmuyor: {len(old)} != {len(texts)}')
    sections=msbt_sections(data)
    enc=[t.encode('utf-16le','surrogatepass')+b'\0\0' for t in texts]
    base=4+4*len(enc); offs=[]; cur=base
    for b in enc: offs.append(cur); cur+=len(b)
    body=bytearray(struct.pack('<I',len(enc)))
    if enc: body += struct.pack('<'+'I'*len(enc),*offs)
    for b in enc: body += b
    new_txt=b'TXT2'+struct.pack('<I',len(body))+b'\0'*8+body
    out=bytearray(data[:0x20])
    for magic,p,size,blob in sections:
        while len(out)%16: out.append(0xAB)
        out.extend(new_txt if magic==b'TXT2' else blob)
    while len(out)%16: out.append(0xAB)
    struct.pack_into('<I',out,0x12,len(out))
    return bytes(out)

def msbt_export_json(data: bytes, outpath: Path):
    labs=msbt_labels(data); txt=msbt_texts(data)
    arr=[{'index':i,'label':labs.get(i,''),'text':t} for i,t in enumerate(txt)]
    outpath.parent.mkdir(parents=True,exist_ok=True)
    outpath.write_text(json.dumps(arr,ensure_ascii=False,indent=2),encoding='utf-8')

# ---------------- SARC ----------------

def sarc_parse(data: bytes):
    if data[:4] != b'SARC': raise ValueError('SARC değil')
    bom=data[6:8]; order='<' if bom==b'\xff\xfe' else '>' if bom==b'\xfe\xff' else None
    if not order: raise ValueError('SARC byte order bilinmiyor')
    hsize=struct.unpack_from(order+'H',data,4)[0]; file_size=struct.unpack_from(order+'I',data,8)[0]
    data_off=struct.unpack_from(order+'I',data,12)[0]; sfat=hsize
    if data[sfat:sfat+4]!=b'SFAT': raise ValueError('SFAT bulunamadı')
    sfat_h=struct.unpack_from(order+'H',data,sfat+4)[0]; count=struct.unpack_from(order+'H',data,sfat+6)[0]
    hash_key=struct.unpack_from(order+'I',data,sfat+8)[0]; np=sfat+sfat_h; sfnt=np+count*16
    if data[sfnt:sfnt+4]!=b'SFNT': raise ValueError('SFNT bulunamadı')
    sfnt_h=struct.unpack_from(order+'H',data,sfnt+4)[0]; names_base=sfnt+sfnt_h; nodes=[]
    for i in range(count):
        h,attr,start,end=struct.unpack_from(order+'4I',data,np+i*16); name=None
        if attr>>24:
            noff=(attr&0x00FFFFFF)*4; z=data.find(b'\0',names_base+noff)
            name=data[names_base+noff:z].decode('utf-8','replace')
        nodes.append({'hash':h,'attr':attr,'start':start,'end':end,'name':name,'data':data[data_off+start:data_off+end]})
    return {'order':order,'header_size':hsize,'file_size':file_size,'data_offset':data_off,'hash_key':hash_key,'nodes':nodes}

def sarc_extract(data: bytes,outdir: Path):
    p=sarc_parse(data); outdir.mkdir(parents=True,exist_ok=True); manifest=[]
    for i,n in enumerate(p['nodes']):
        name=n['name'] or f'__unnamed_{i:04d}.bin'; q=outdir/name; q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(n['data'])
        manifest.append({'index':i,'name':name,'hash':n['hash'],'attr':n['attr']})
    (outdir/'_sarc.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

def sarc_patch_same_size(data: bytes,replacements: Dict[str,bytes]) -> bytes:
    p=sarc_parse(data); out=bytearray(data)
    unknown=set(replacements)-{n['name'] for n in p['nodes']}
    if unknown:raise ValueError(f'SARC girdisi bulunamadı: {sorted(unknown)}')
    for n in p['nodes']:
        name=n['name']
        if name in replacements:
            blob=replacements[name]; oldlen=n['end']-n['start']
            if len(blob)!=oldlen: raise ValueError(f'{name}: SARC içinde yerinde enjeksiyon için boyut değişmemeli ({len(blob)} != {oldlen})')
            off=p['data_offset']+n['start']; out[off:off+oldlen]=blob
    return bytes(out)

def sarc_inject_from_dir(template: bytes, indir: Path) -> bytes:
    parsed=sarc_parse(template); repl={}
    for n in parsed['nodes']:
        if not n['name']: continue
        q=indir/n['name']
        if q.is_file(): repl[n['name']]=q.read_bytes()
    return sarc_patch_same_size(template,repl)

# ---------------- BFLIM ----------------
FORMAT_BITS={0x00:8,0x01:8,0x02:8,0x03:16,0x04:16,0x05:16,0x06:24,0x07:16,0x08:16,0x09:32,0x0C:4,0x0D:4}

def _pow2(v:int)->int: return 1 if v<=1 else 1<<(v-1).bit_length()

def bflim_info(data: bytes):
    if len(data)<40 or data[-40:-36]!=b'FLIM' or data[-20:-16]!=b'imag': raise ValueError('BFLIM değil')
    flim=data[-40:-20]; magic,bom,hsize,unk1,fsize,unk2,mult,unk3=struct.unpack('=4s2H2IH2B',flim)
    order='<' if bom==0xFEFF else '>' if bom==0xFFFE else None
    if not order: raise ValueError('BFLIM byte order bilinmiyor')
    imag=data[-20:]; im,ps,height,width,alignment,fmt,swizzle,dsize=struct.unpack(order+'4sI3H2BI',imag)
    return {'order':order,'height':height,'width':width,'alignment':alignment,'format':fmt,'swizzle':swizzle,'data_size':dsize,'file_size':fsize,'flim_header':flim,'imag_header':imag}

def _rgba_from_raw(raw:bytes,fmt:int,index:int,order:str):
    if fmt==0x09:
        color=struct.unpack_from(order+'I',raw,index*4)[0]; return ((color>>24)&255,(color>>16)&255,(color>>8)&255,color&255)
    if fmt==0x06:
        r,g,b=raw[index*3:index*3+3]; return (r,g,b,255)
    if fmt==0x08:
        b1,b2=raw[index*2:index*2+2]
        if order=='<': b1,b2=b2,b1
        return ((b1>>4)*17,(b1&15)*17,(b2>>4)*17,(b2&15)*17)
    if fmt==0x07:
        b1,b2=raw[index*2:index*2+2]
        if order=='<': b1,b2=b2,b1
        r=(b1>>3)&31; g=((b1&7)<<2)|((b2>>6)&3); b=(b2>>1)&31; a=(b2&1)*255
        return (round(r*255/31),round(g*255/31),round(b*255/31),a)
    if fmt==0x05:
        b1,b2=raw[index*2:index*2+2]
        if order=='<': b1,b2=b2,b1
        r=(b1>>3)&31; g=((b1&7)<<3)|((b2>>5)&7); b=b2&31
        return (round(r*255/31),round(g*255/63),round(b*255/31),255)
    if fmt==0x03:
        l,a=raw[index*2:index*2+2]
        if order=='<': l,a=a,l
        return (l,l,l,a)
    if fmt==0x00:
        l=raw[index]; return (l,l,l,255)
    if fmt==0x01:
        a=raw[index]; return (255,255,255,a)
    if fmt==0x02:
        v=raw[index]; return ((v>>4)*17,)*3+((v&15)*17,)
    raise NotImplementedError(f'BFLIM format 0x{fmt:02X} desteklenmiyor')

def _raw_from_rgba(px,fmt:int,index:int,order:str)->bytes:
    r,g,b,a=px
    if fmt==0x09:
        return struct.pack(order+'I',(r<<24)|(g<<16)|(b<<8)|a)
    if fmt==0x06: return bytes((r,g,b))
    if fmt==0x08:
        z=bytes((((r//17)&15)<<4|((g//17)&15),((b//17)&15)<<4|((a//17)&15))); return z[::-1] if order=='<' else z
    if fmt==0x07:
        r5=round(r*31/255)&31; g5=round(g*31/255)&31; b5=round(b*31/255)&31; aa=1 if a>=128 else 0
        z=bytes(((r5<<3)|(g5>>2),((g5&3)<<6)|(b5<<1)|aa)); return z[::-1] if order=='<' else z
    if fmt==0x05:
        r5=round(r*31/255)&31; g6=round(g*63/255)&63; b5=round(b*31/255)&31
        z=bytes(((r5<<3)|(g6>>3),((g6&7)<<5)|b5)); return z[::-1] if order=='<' else z
    if fmt==0x03:
        l=round(r*.2126+g*.7152+b*.0722); z=bytes((l,a)); return z[::-1] if order=='<' else z
    if fmt==0x00:
        l=round(r*.2126+g*.7152+b*.0722); return bytes((l,))
    if fmt==0x01: return bytes((a,))
    if fmt==0x02:
        l=round(r*.2126+g*.7152+b*.0722)//17; return bytes((((l&15)<<4)|((a//17)&15),))
    raise NotImplementedError(f'BFLIM format 0x{fmt:02X} desteklenmiyor')

def _texture_geometry(inf):
    w,h=inf['width'],inf['height']
    dw,dh=_pow2(max(8,w)),_pow2(max(8,h))
    expected=dw*dh*FORMAT_BITS[inf['format']]//8
    if expected != inf['data_size']:
        raise ValueError(f"Desteklenmeyen doku boyutu: {expected} != {inf['data_size']}")
    return w,h,dw,dh

def _morton(x,y,dw):
    return (y//8)*(dw*8)+(x//8)*64+sum(((x>>k)&1)<<(2*k) | ((y>>k)&1)<<(2*k+1) for k in range(3))

def bflim_decode_image(data:bytes):
    from PIL import Image
    inf=bflim_info(data); fmt=inf['format']
    if fmt not in FORMAT_BITS or FORMAT_BITS[fmt]==4:
        raise NotImplementedError(f'BFLIM biçimi desteklenmiyor: {fmt}')
    w,h,dw,dh=_texture_geometry(inf)
    raw=data[:inf['data_size']]
    img=Image.new('RGBA',(dw,dh))
    img.putdata([_rgba_from_raw(raw,fmt,_morton(x,y,dw),inf['order']) for y in range(dh) for x in range(dw)])
    # Önce fiziksel yüzeyi döndür, sonra mantıksal alanı kırp.
    if inf['swizzle']==4:
        img=img.transpose(Image.Transpose.ROTATE_90)
        w,h=h,w
    elif inf['swizzle']==8:
        img=img.transpose(Image.Transpose.ROTATE_90).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        w,h=h,w
    elif inf['swizzle']!=0:
        raise NotImplementedError('Bilinmeyen swizzle')
    return img.crop((0,0,w,h)),inf

def bflim_encode_image(img, template:bytes)->bytes:
    from PIL import Image
    inf=bflim_info(template);fmt=inf['format']
    if fmt not in FORMAT_BITS or FORMAT_BITS[fmt]==4: raise NotImplementedError('BFLIM biçimi desteklenmiyor')
    w,h,dw,dh=_texture_geometry(inf);sw=inf['swizzle']
    logical=(h,w) if sw in (4,8) else (w,h)
    if img.size!=logical:raise ValueError(f'PNG boyutu {img.size}; beklenen {logical}')
    # Dolgu baytlarını koru; yalnızca mantıksal pikselleri değiştir.
    src=img.convert('RGBA').load();raw=bytearray(template[:inf['data_size']]);bpp=FORMAT_BITS[fmt]//8
    for y in range(logical[1]):
        for x in range(logical[0]):
            if sw==4: xx,yy=dw-1-y,x
            elif sw==8:xx,yy=y,x
            elif sw==0:xx,yy=x,y
            else:raise NotImplementedError('Bilinmeyen swizzle')
            di=_morton(xx,yy,dw)
            raw[di*bpp:(di+1)*bpp]=_raw_from_rgba(src[x,y],fmt,di,inf['order'])
    return bytes(raw)+template[inf['data_size']:]

# ---------------- CLI ----------------
def main():
    ap=argparse.ArgumentParser(description='Dr. Mario 3DS çıkarma/enjeksiyon araçları')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('sszl-ac'); p.add_argument('girdi'); p.add_argument('cikti')
    p=sp.add_parser('sszl-kapat'); p.add_argument('girdi'); p.add_argument('cikti')
    p=sp.add_parser('arcv-ac'); p.add_argument('girdi'); p.add_argument('klasor')
    p=sp.add_parser('arcv-enjekte'); p.add_argument('girdi'); p.add_argument('klasor'); p.add_argument('cikti')
    p=sp.add_parser('sarc-ac'); p.add_argument('girdi'); p.add_argument('klasor')
    p=sp.add_parser('sarc-enjekte'); p.add_argument('girdi'); p.add_argument('klasor'); p.add_argument('cikti')
    p=sp.add_parser('msbt-json'); p.add_argument('girdi'); p.add_argument('cikti')
    p=sp.add_parser('msbt-enjekte'); p.add_argument('girdi'); p.add_argument('json'); p.add_argument('cikti')
    p=sp.add_parser('bflim-png'); p.add_argument('girdi'); p.add_argument('cikti')
    p=sp.add_parser('png-bflim'); p.add_argument('png'); p.add_argument('sablon'); p.add_argument('cikti')
    a=ap.parse_args()
    if a.cmd=='sszl-ac': Path(a.cikti).write_bytes(sszl_unpack(Path(a.girdi).read_bytes()))
    elif a.cmd=='sszl-kapat': Path(a.cikti).write_bytes(sszl_pack(Path(a.girdi).read_bytes()))
    elif a.cmd=='arcv-ac': arcv_extract(Path(a.girdi).read_bytes(),Path(a.klasor))
    elif a.cmd=='arcv-enjekte': Path(a.cikti).write_bytes(arcv_inject_from_dir(Path(a.girdi).read_bytes(),Path(a.klasor)))
    elif a.cmd=='sarc-ac': sarc_extract(Path(a.girdi).read_bytes(),Path(a.klasor))
    elif a.cmd=='sarc-enjekte': Path(a.cikti).write_bytes(sarc_inject_from_dir(Path(a.girdi).read_bytes(),Path(a.klasor)))
    elif a.cmd=='msbt-json': msbt_export_json(Path(a.girdi).read_bytes(),Path(a.cikti))
    elif a.cmd=='msbt-enjekte':
        obj=json.loads(Path(a.json).read_text(encoding='utf-8')); texts=[x['text'] if isinstance(x,dict) else x for x in obj]
        Path(a.cikti).write_bytes(msbt_replace_texts(Path(a.girdi).read_bytes(),texts))
    elif a.cmd=='bflim-png':
        img,_=bflim_decode_image(Path(a.girdi).read_bytes()); img.save(a.cikti)
    elif a.cmd=='png-bflim':
        from PIL import Image
        img=Image.open(a.png).convert('RGBA'); Path(a.cikti).write_bytes(bflim_encode_image(img,Path(a.sablon).read_bytes()))

if __name__=='__main__': main()
