#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse,struct,hashlib,json,sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
from bflim_codec import parse_header,decode_bflim,encode_bflim
from fullblox_core import lz11_decompress

def u16(d,o,e): return struct.unpack_from(e+'H',d,o)[0]
def u32(d,o,e): return struct.unpack_from(e+'I',d,o)[0]

def sarc_entries(d:bytes):
    if d[:4]!=b'SARC': raise ValueError('not SARC')
    e='<' if d[6:8]==b'\xff\xfe' else '>' if d[6:8]==b'\xfe\xff' else None
    if not e: raise ValueError('bad SARC BOM')
    hsz=u16(d,4,e); dataoff=u32(d,0x0c,e); sfat=hsz
    if d[sfat:sfat+4]!=b'SFAT': raise ValueError('no SFAT')
    sh=u16(d,sfat+4,e); n=u16(d,sfat+6,e); nodes=sfat+sh; sfnt=nodes+n*0x10
    if d[sfnt:sfnt+4]!=b'SFNT': raise ValueError('no SFNT')
    nbase=sfnt+u16(d,sfnt+4,e)
    out=[]
    for i in range(n):
        o=nodes+i*0x10; nf=u32(d,o+4,e); a=u32(d,o+8,e); b=u32(d,o+12,e)
        name=''
        if nf>>24:
            q=nbase+(nf&0xffffff)*4; z=d.find(b'\0',q); name=d[q:z].decode('utf-8','replace')
        out.append({'name':name,'off':dataoff+a,'size':b-a})
    return out

def lz11_compress(data:bytes)->bytes:
    from collections import defaultdict,deque
    n=len(data); out=bytearray(b"\x11")
    if n<0x1000000: out+=bytes((n&255,(n>>8)&255,(n>>16)&255))
    else: out+=b"\x00\x00\x00"+struct.pack("<I",n)
    hist=defaultdict(deque);pos=0
    def add(p):
        if p+2>=n:return
        k=data[p:p+3];q=hist[k];q.append(p)
        while q and p-q[0]>0x1000:q.popleft()
        while len(q)>64:q.popleft()
    while pos<n:
        flag_at=len(out);out.append(0);flags=0
        for bit in range(8):
            if pos>=n:break
            best_len=0;best_disp=0
            if pos+2<n:
                q=hist.get(data[pos:pos+3])
                if q:
                    maxlen=min(n-pos,0x10110)
                    for pp in reversed(q):
                        disp=pos-pp
                        if disp<1 or disp>0x1000:continue
                        l=3
                        while l<maxlen and data[pp+l]==data[pos+l]:l+=1
                        if l>best_len:
                            best_len=l;best_disp=disp
                            if l==maxlen:break
            if best_len>=3:
                flags|=0x80>>bit;l=best_len;d=best_disp-1
                if l<=0x10:out+=bytes((((l-1)<<4)|((d>>8)&15),d&255))
                elif l<=0x110:
                    v=l-0x11;out+=bytes(((v>>4)&15,((v&15)<<4)|((d>>8)&15),d&255))
                else:
                    v=l-0x111;out+=bytes((0x10|((v>>12)&15),(v>>4)&255,((v&15)<<4)|((d>>8)&15),d&255))
                old=pos;pos+=l
                for pp in range(old,pos):add(pp)
            else:
                out.append(data[pos]);add(pos);pos+=1
        out[flag_at]=flags
    return bytes(out)

def get_entry(d:bytes,name:str):
    for e in sarc_entries(d):
        if e['name']==name: return e
    raise KeyError(name)

def patch_pack(src_lz:Path, dest_lz:Path, replacements:dict[str,Path], report:dict):
    raw=src_lz.read_bytes(); sarc=lz11_decompress(raw); buf=bytearray(sarc)
    packrep={'source_sha256':hashlib.sha256(raw).hexdigest(),'sarc_sha256_before':hashlib.sha256(sarc).hexdigest(),'entries':{}}
    for name,pngp in replacements.items():
        ent=get_entry(sarc,name); old=sarc[ent['off']:ent['off']+ent['size']]
        inf=parse_header(old); img=Image.open(pngp).convert('RGBA')
        new=encode_bflim(img,old)
        if len(new)!=len(old): raise AssertionError(f'{name}: size changed')
        if new[-0x28:]!=old[-0x28:]: raise AssertionError(f'{name}: BFLIM metadata changed')
        buf[ent['off']:ent['off']+ent['size']]=new
        # verify decoded dimensions and metadata
        dec=decode_bflim(new)
        if dec.size!=img.size: raise AssertionError(f'{name}: display size mismatch')
        packrep['entries'][name]={
            'offset':ent['off'],'size':ent['size'],'format':inf['format'],'swizzle':inf['swizzle'],
            'stored_width':inf['stored_width'],'stored_height':inf['stored_height'],'display_size':list(img.size),
            'old_sha256':hashlib.sha256(old).hexdigest(),'new_sha256':hashlib.sha256(new).hexdigest(),
            'footer_preserved':new[-0x28:]==old[-0x28:]
        }
    newsarc=bytes(buf); packed=lz11_compress(newsarc)
    # round-trip exact decompression
    if lz11_decompress(packed)!=newsarc: raise AssertionError(src_lz.name+': LZ11 roundtrip failed')
    dest_lz.parent.mkdir(parents=True,exist_ok=True); dest_lz.write_bytes(packed)
    packrep['sarc_sha256_after']=hashlib.sha256(newsarc).hexdigest();packrep['output_sha256']=hashlib.sha256(packed).hexdigest();packrep['output_size']=len(packed)
    report[src_lz.name]=packrep

def build(romfs:Path, previews:Path, out_romfs:Path, report_path:Path|None=None):
    report={}
    targets=[
      ('EURen','Guide_D.lz', {'timg/G_Btn_Map_EURen.bflim': previews/'HARİTA.png'}),
      ('EURen','Play_U.lz', {'timg/P_U_Op_EURen.bflim': previews/'BAŞLA.png','timg/P_U_Ed_EURen.bflim': previews/'TAMAM.png'}),
      # Use the official EURes result-screen scheme for Turkish. Its BFLYT and
      # animations are equivalent to EURen apart from the localized texture names,
      # while the font texture is conventional ETC1A4 and works cleanly with a
      # separate A4 highlight mask.
      ('EURes','Rslt_Base_U.lz', {'timg/R_CongratsFont_EURes.bflim': previews/'TEBRİKLER_font.png','timg/R_CongratsMask_EURes.bflim': previews/'TEBRİKLER_mask.png'}),
    ]
    for lang,pack,repl in targets:
        patch_pack(romfs/'lyt'/lang/pack, out_romfs/'lyt'/'EURen'/pack, repl, report)
    if report_path:
        report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2)); return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--romfs',type=Path,required=True);ap.add_argument('--previews',type=Path,required=True);ap.add_argument('--out-romfs',type=Path,required=True);ap.add_argument('--report',type=Path)
    a=ap.parse_args();build(a.romfs,a.previews,a.out_romfs,a.report)
if __name__=='__main__':main()
