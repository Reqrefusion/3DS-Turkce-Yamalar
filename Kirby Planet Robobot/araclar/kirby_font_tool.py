#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, struct, sys
from collections import defaultdict, deque
from pathlib import Path

TR_CHARS = "ÇĞİÖŞÜçğıöşü"

class FontError(Exception): pass

def lz11_decompress(data: bytes) -> bytes:
    if not data or data[0] != 0x11: raise FontError('LZ11 (0x11) başlığı yok')
    size=int.from_bytes(data[1:4],'little'); pos=4
    if size==0:
        if len(data)<8: raise FontError('LZ11 başlığı kısa')
        size=int.from_bytes(data[4:8],'little'); pos=8
    out=bytearray()
    while len(out)<size:
        if pos>=len(data): raise FontError('LZ11 veri erken bitti')
        flags=data[pos]; pos+=1
        for bit in range(8):
            if len(out)>=size: break
            if flags & (0x80>>bit):
                if pos>=len(data): raise FontError('LZ11 backref kısa')
                b1=data[pos]; pos+=1; hi=b1>>4
                if hi==0:
                    if pos+2>len(data): raise FontError('LZ11 backref kısa')
                    b2,b3=data[pos],data[pos+1]; pos+=2
                    length=(((b1&0xF)<<4)|(b2>>4))+0x11
                    disp=(((b2&0xF)<<8)|b3)+1
                elif hi==1:
                    if pos+3>len(data): raise FontError('LZ11 backref kısa')
                    b2,b3,b4=data[pos],data[pos+1],data[pos+2]; pos+=3
                    length=(((b1&0xF)<<12)|(b2<<4)|(b3>>4))+0x111
                    disp=(((b3&0xF)<<8)|b4)+1
                else:
                    if pos>=len(data): raise FontError('LZ11 backref kısa')
                    b2=data[pos]; pos+=1
                    length=hi+1; disp=(((b1&0xF)<<8)|b2)+1
                if disp>len(out): raise FontError(f'LZ11 geçersiz mesafe {disp}')
                for _ in range(length):
                    out.append(out[-disp])
                    if len(out)>=size: break
            else:
                if pos>=len(data): raise FontError('LZ11 literal kısa')
                out.append(data[pos]); pos+=1
    return bytes(out)

def _encode_ref(length:int, disp:int) -> bytes:
    d=disp-1
    if not (1<=disp<=0x1000): raise ValueError('disp')
    if 3<=length<=0x10:
        return bytes([((length-1)<<4)|((d>>8)&0xF), d&0xFF])
    if 0x11<=length<=0x110:
        v=length-0x11
        return bytes([((v>>4)&0xF), ((v&0xF)<<4)|((d>>8)&0xF), d&0xFF])
    if 0x111<=length<=0x10110:
        v=length-0x111
        return bytes([0x10|((v>>12)&0xF), (v>>4)&0xFF, ((v&0xF)<<4)|((d>>8)&0xF), d&0xFF])
    raise ValueError('length')

def lz11_compress(data: bytes) -> bytes:
    n=len(data)
    if n < 0x1000000: out=bytearray([0x11])+bytearray(n.to_bytes(3,'little'))
    else: out=bytearray([0x11,0,0,0])+bytearray(n.to_bytes(4,'little'))
    buckets=defaultdict(deque)
    pos=0
    while pos<n:
        flag_pos=len(out); out.append(0); flags=0
        for bit in range(8):
            if pos>=n: break
            best_len=0; best_disp=0
            if pos+2<n:
                key=data[pos:pos+3]
                dq=buckets[key]
                while dq and pos-dq[0]>0x1000: dq.popleft()
                # En yeni adaylar genelde en iyi/ucuz; 96 adayla sınırla.
                for cand in reversed(list(dq)[-96:]):
                    disp=pos-cand
                    maxlen=min(0x10110,n-pos)
                    l=3
                    while l<maxlen and data[cand+l]==data[pos+l]: l+=1
                    if l>best_len:
                        best_len=l; best_disp=disp
                        if l==maxlen: break
            if best_len>=3:
                flags |= 0x80>>bit
                out += _encode_ref(best_len,best_disp)
                advance=best_len
            else:
                out.append(data[pos]); advance=1
            # Atlanan her pozisyonu sözlüğe ekle ki ileride eşleşsin.
            end=min(n-2,pos+advance)
            for q in range(pos,end):
                k=data[q:q+3]; dq=buckets[k]; dq.append(q)
                while dq and q-dq[0]>0x1000: dq.popleft()
            pos += advance
        out[flag_pos]=flags
    while len(out)%4: out.append(0)
    return bytes(out)

def ensure_bcfnt(data: bytes) -> bytes:
    if data.startswith(b'CFNT') or data.startswith(b'CFNU'): return data
    if data.startswith(b'\x11'): return lz11_decompress(data)
    raise FontError('CFNT/CFNU veya LZ11 font değil')

def parse_bcfnt(data: bytes):
    data=ensure_bcfnt(data)
    if len(data)<0x34: raise FontError('BCFNT çok kısa')
    bom=data[4:6]
    if bom==b'\xff\xfe': order='<'
    elif bom==b'\xfe\xff': order='>'
    else: raise FontError('BCFNT BOM bozuk')
    magic,bomv,hsize,ver,fsize,sections=struct.unpack_from(order+'4s2H3I',data,0)
    if magic not in (b'CFNT',b'CFNU'): raise FontError('CFNT magic yok')
    finf=struct.unpack_from(order+'4sI2BH4B3I4B',data,0x14)
    if finf[0]!=b'FINF': raise FontError('FINF yok')
    tglp_off,cwdh_off,cmap_off=finf[9],finf[10],finf[11]
    tpos=tglp_off-8
    tg=struct.unpack_from(order+'4sI4BI6HI',data,tpos)
    if tg[0]!=b'TGLP': raise FontError('TGLP yok')
    _,tglp_size,cell_w,cell_h,baseline,max_char_w,sheet_size,sheet_count,pixel_fmt,cols,rows,sheet_w,sheet_h,sheet_data_off=tg
    mapping={}; p=cmap_off; seen=set(); cmaps=0
    while p and p not in seen:
        seen.add(p); pos=p-8
        if pos<0 or pos+0x14>len(data): raise FontError('CMAP offset bozuk')
        cmagic,sz,start,end,method,unknown,nextp=struct.unpack_from(order+'4sI4HI',data,pos)
        if cmagic!=b'CMAP': raise FontError('CMAP magic bozuk')
        q=pos+0x14; cmaps+=1
        if method==0:
            idxoff=struct.unpack_from(order+'H',data,q)[0]
            for c in range(start,end+1): mapping[chr(c)]=c-start+idxoff
        elif method==1:
            for i,c in enumerate(range(start,end+1)):
                idx=struct.unpack_from(order+'H',data,q+2*i)[0]
                if idx!=0xFFFF: mapping[chr(c)]=idx
        elif method==2:
            count=struct.unpack_from(order+'H',data,q)[0]
            for i in range(count):
                c,idx=struct.unpack_from(order+'2H',data,q+2+4*i); mapping[chr(c)]=idx
        else: raise FontError(f'CMAP method {method} bilinmiyor')
        p=nextp
    return {
        'file_size':fsize,'version':ver,'sections':sections,'encoding':finf[8],
        'cell_w':cell_w,'cell_h':cell_h,'baseline':baseline,'pixel_format':pixel_fmt,
        'sheet_count':sheet_count,'cols':cols,'rows':rows,'sheet_w':sheet_w,'sheet_h':sheet_h,
        'mapped_count':len(mapping),'mapping':mapping,'cmaps':cmaps,
    }

def cmd_decompress(inp:Path,out:Path):
    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(lz11_decompress(inp.read_bytes())); print(out)

def cmd_compress(inp:Path,out:Path):
    out.parent.mkdir(parents=True,exist_ok=True); packed=lz11_compress(inp.read_bytes());
    if lz11_decompress(packed)!=inp.read_bytes(): raise FontError('Sıkıştırma doğrulaması başarısız')
    out.write_bytes(packed); print(out)

def cmd_unpack_all(root:Path,outdir:Path):
    n=0
    for p in root.rglob('*.bcfnt.cmp'):
        rel=p.relative_to(root); dst=outdir/Path(str(rel)[:-4]); dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(lz11_decompress(p.read_bytes())); n+=1
    print(f'{n} font açıldı: {outdir}')

def cmd_pack_all(root:Path,outdir:Path):
    n=0
    for p in root.rglob('*.bcfnt'):
        rel=p.relative_to(root); dst=outdir/Path(str(rel)+'.cmp'); dst.parent.mkdir(parents=True,exist_ok=True)
        raw=p.read_bytes(); packed=lz11_compress(raw)
        if lz11_decompress(packed)!=raw: raise FontError(f'{p}: doğrulama başarısız')
        dst.write_bytes(packed); n+=1
    print(f'{n} font paketlendi: {outdir}')

def cmd_audit(root:Path, csv_out:Path, chars:str):
    rows=[]
    files=sorted([p for p in root.rglob('*') if p.is_file() and (p.name.endswith('.bcfnt.cmp') or p.name.endswith('.bcfnt'))])
    for p in files:
        try:
            info=parse_bcfnt(p.read_bytes()); m=info['mapping']; present=''.join(c for c in chars if c in m); missing=''.join(c for c in chars if c not in m)
            rows.append({'file':str(p.relative_to(root)),'present':present,'missing':missing,'mapped':info['mapped_count'],'cell':f"{info['cell_w']}x{info['cell_h']}",'sheets':info['sheet_count'],'grid':f"{info['cols']}x{info['rows']}",'pixel_format':info['pixel_format']})
        except Exception as e:
            rows.append({'file':str(p.relative_to(root)),'present':'','missing':chars,'mapped':'','cell':'','sheets':'','grid':'','pixel_format':'','error':str(e)})
    csv_out.parent.mkdir(parents=True,exist_ok=True)
    fields=['file','present','missing','mapped','cell','sheets','grid','pixel_format','error']
    with csv_out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader();
        for r in rows: w.writerow(r)
    print(f'{len(rows)} font denetlendi: {csv_out}')
    for r in rows:
        if r.get('missing'): print(f"{r['file']}: eksik {r['missing']}")

def main():
    ap=argparse.ArgumentParser(description='Kirby 3DS BCFNT/LZ11 font yardımcısı')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('decompress'); p.add_argument('input',type=Path); p.add_argument('output',type=Path)
    p=sp.add_parser('compress'); p.add_argument('input',type=Path); p.add_argument('output',type=Path)
    p=sp.add_parser('unpack-all'); p.add_argument('font_root',type=Path); p.add_argument('output_dir',type=Path)
    p=sp.add_parser('pack-all'); p.add_argument('bcfnt_root',type=Path); p.add_argument('output_dir',type=Path)
    p=sp.add_parser('audit'); p.add_argument('font_root',type=Path); p.add_argument('csv_out',type=Path); p.add_argument('--chars',default=TR_CHARS)
    a=ap.parse_args()
    try:
        if a.cmd=='decompress': cmd_decompress(a.input,a.output)
        elif a.cmd=='compress': cmd_compress(a.input,a.output)
        elif a.cmd=='unpack-all': cmd_unpack_all(a.font_root,a.output_dir)
        elif a.cmd=='pack-all': cmd_pack_all(a.bcfnt_root,a.output_dir)
        else: cmd_audit(a.font_root,a.csv_out,a.chars)
    except FontError as e:
        print('HATA:',e,file=sys.stderr); raise SystemExit(2)
if __name__=='__main__': main()
