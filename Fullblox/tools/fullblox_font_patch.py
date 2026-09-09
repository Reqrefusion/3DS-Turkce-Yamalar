#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import fullblox_core as core
import bflim_codec as bc
from fullblox_assets import lz11_compress

# Reuse six glyph slots that exist in the European Outline font but are only mapped
# to Japanese kanji unused by this title's European localisations. Keeping all glyph
# indices <= 334 avoids a runtime limit observed when adding new glyph indices.
SLOTS = {
    'Ğ': 303,  # originally U+4E0A
    'ğ': 304,  # originally U+4FDD
    'İ': 305,  # originally U+5143
    'ı': 306,  # originally U+5168
    'Ş': 307,  # originally U+5206
    'ş': 308,  # originally U+524D
}
OLD_CODES = [0x4E0A,0x4FDD,0x5143,0x5168,0x5206,0x524D]
NEW_CODES = [ord('Ğ'),ord('ğ'),ord('İ'),ord('ı'),ord('Ş'),ord('ş')]


def endian(data: bytes) -> str:
    if data[4:6] == b'\xff\xfe': return '<'
    if data[4:6] == b'\xfe\xff': return '>'
    raise ValueError('bad FFNT BOM')


def parse_font(data: bytes):
    e=endian(data)
    if data[:4] != b'FFNT': raise ValueError('not FFNT')
    hsz=struct.unpack_from(e+'H',data,6)[0]
    finf=hsz
    if data[finf:finf+4] != b'FINF': raise ValueError('FINF missing')
    tptr,cwdhptr,cmapptr=struct.unpack_from(e+'III',data,finf+0x14)
    t=tptr-8
    cw,ch,sheets,maxw=struct.unpack_from(e+'4B',data,t+8)
    sheetsize=struct.unpack_from(e+'I',data,t+12)[0]
    baseline,fmt=struct.unpack_from(e+'2H',data,t+16)
    cols,rows,w,h,doff=struct.unpack_from(e+'4HI',data,t+20)
    return dict(e=e,hsz=hsz,finf=finf,t=t,cwdh=cwdhptr-8,cmap=cmapptr-8,
                cw=cw,ch=ch,sheets=sheets,maxw=maxw,sheetsize=sheetsize,
                baseline=baseline,fmt=fmt,cols=cols,rows=rows,w=w,h=h,doff=doff)


def decode_la8(data: bytes,m):
    if m['fmt'] != 5: raise ValueError(f"Outline expected LA8, got {m['fmt']}")
    raw=data[m['doff']:m['doff']+m['sheetsize']]
    L=np.zeros((m['h'],m['w']),np.uint8); A=np.zeros_like(L); p=0
    for x,y in bc._pix_order_positions(m['w'],m['h']):
        L[y,x]=raw[p]; A[y,x]=raw[p+1]; p+=2
    if p != len(raw): raise AssertionError((p,len(raw)))
    return L,A


def encode_la8(L,A,m):
    out=bytearray()
    for x,y in bc._pix_order_positions(m['w'],m['h']):
        out += bytes((int(L[y,x]),int(A[y,x])))
    if len(out) != m['sheetsize']: raise AssertionError('sheet size')
    return bytes(out)


def cell_xy(idx,m):
    return (idx % m['cols'])*(m['cw']+1)+1, (idx // m['cols'])*(m['ch']+1)+1

def get_cell(arr,idx,m):
    x,y=cell_xy(idx,m); return arr[y:y+m['ch'],x:x+m['cw']].copy()

def put_cell(arr,idx,cell,m):
    x,y=cell_xy(idx,m); arr[y:y+m['ch'],x:x+m['cw']]=cell


def expand_alpha(a):
    return np.array(Image.fromarray(a,'L').filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.5)),dtype=np.uint8)


def draw_breve(shape,cx,y0,width):
    h,w=shape; scale=8
    im=Image.new('L',(w*scale,h*scale),0); d=ImageDraw.Draw(im)
    x0=(cx-width/2)*scale; x1=(cx+width/2)*scale
    pts=[(x0,y0*scale),((cx-width*.28)*scale,(y0+1.6)*scale),(cx*scale,(y0+2.1)*scale),((cx+width*.28)*scale,(y0+1.6)*scale),(x1,y0*scale)]
    d.line(pts,fill=255,width=scale,joint='curve')
    return np.array(im.resize((w,h),Image.Resampling.LANCZOS),dtype=np.uint8)


def width_triplet(data: bytes,m,gi:int):
    e=m['e']; off=m['cwdh']; seen=set()
    while off not in seen:
        seen.add(off); start,end,nxt=struct.unpack_from(e+'HHI',data,off+8)
        if start <= gi <= end:
            q=off+16+(gi-start)*3
            return struct.unpack_from('bBB',data,q), q
        if not nxt: break
        off=nxt-8
    raise KeyError(gi)


def find_scan_pairs(data:bytes,m):
    e=m['e']; off=m['cmap']; seen=set()
    while off not in seen:
        seen.add(off)
        start,end,method,res,nxt=struct.unpack_from(e+'HHHHI',data,off+8)
        if method==2:
            cnt=struct.unpack_from(e+'H',data,off+20)[0]
            pairs=[struct.unpack_from(e+'HH',data,off+22+i*4) for i in range(cnt)]
            yield off,pairs
        if not nxt: break
        off=nxt-8


def build(src_lz:Path,dst_lz:Path,preview:Path|None=None,report:Path|None=None):
    packed=src_lz.read_bytes(); original=core.lz11_decompress(packed); data=bytearray(original); m=parse_font(data)
    fm=core.CFNTMetrics(bytes(data))
    # These Turkish letters must be absent before patching.
    missing=[ch for ch in SLOTS if ord(ch) not in fm.glyph_by_code]
    if set(missing)!=set(SLOTS): raise ValueError(f'unexpected Turkish coverage before patch: {missing}')

    # Verify source CMAP slots are the expected unused Japanese mappings.
    scan_target=None
    for off,pairs in find_scan_pairs(bytes(data),m):
        loc={cp:(i,gi) for i,(cp,gi) in enumerate(pairs)}
        if all(cp in loc for cp in OLD_CODES):
            scan_target=(off,pairs,loc); break
    if scan_target is None: raise ValueError('expected Japanese scan mappings not found')
    off,pairs,loc=scan_target
    old_slots=[]
    for cp,expected_gi in zip(OLD_CODES,[303,304,305,306,307,308]):
        i,gi=loc[cp]
        if gi!=expected_gi: raise ValueError((hex(cp),gi,expected_gi))
        old_slots.append((i,cp,gi))

    L,A=decode_la8(bytes(data),m)
    def cells(ch):
        gi=fm.glyph_by_code[ord(ch)]; return get_cell(L,gi,m),get_cell(A,gi,m),gi
    LI,AI,_=cells('I'); Li,Ai,_=cells('i'); Lc,Ac,_=cells('ç')
    glyphs={}
    # Dotless lowercase i: use the game's own lowercase-i stem, removing only
    # the detached dot. This preserves the lowercase x-height/baseline instead
    # of incorrectly using the full-height capital-I stem.
    dotlessL=Li.copy(); dotlessA=Ai.copy()
    dotlessL[:12,:]=0; dotlessA[:12,:]=0
    glyphs['ı']=(dotlessL,dotlessA)
    # Dotted capital I: keep the exact capital-I body and add the game's own
    # lowercase-i dot above it, leaving a clear gap so the glyph does not become
    # a single over-tall vertical stroke.
    dottedL=LI.copy(); dottedA=AI.copy()
    dot_src_L=np.zeros_like(Li); dot_src_A=np.zeros_like(Ai)
    dot_src_L[7:11,:]=Li[7:11,:]; dot_src_A[7:11,:]=Ai[7:11,:]
    # Move the detached dot 5 pixels upward (rows 7..10 -> 2..5).
    dottedL[2:6,:]=np.maximum(dottedL[2:6,:],dot_src_L[7:11,:])
    dottedA[2:6,:]=np.maximum(dottedA[2:6,:],dot_src_A[7:11,:])
    glyphs['İ']=(dottedL,dottedA)
    # s-cedilla from existing ç accent
    cedA=np.zeros_like(Ac); cedA[25:,:]=Ac[25:,:]
    for ch,base,shift in [('ş','s',0),('Ş','S',1)]:
        Lb,Ab,_=cells(base)
        accentA=np.zeros_like(Ab)
        if shift: accentA[:,shift:]=cedA[:,:-shift]
        else: accentA=cedA.copy()
        glyphs[ch]=(np.maximum(Lb,expand_alpha(accentA)),np.maximum(Ab,accentA))
    # breve g/G
    for ch,base,cx,y0,wid in [('ğ','g',8.5,6.0,10),('Ğ','G',10.0,0.2,11)]:
        Lb,Ab,_=cells(base); aa=draw_breve(Ab.shape,cx,y0,wid)
        glyphs[ch]=(np.maximum(Lb,expand_alpha(aa)),np.maximum(Ab,aa))

    # Put new glyph imagery into existing <=334 slots and copy width metrics in place.
    base_for={'Ğ':'G','ğ':'g','İ':'I','ı':'i','Ş':'S','ş':'s'}
    width_changes={}
    for ch,gi in SLOTS.items():
        put_cell(L,gi,glyphs[ch][0],m); put_cell(A,gi,glyphs[ch][1],m)
        basegi=fm.glyph_by_code[ord(base_for[ch])]
        (trip,_)=width_triplet(bytes(data),m,basegi)
        oldtrip,q=width_triplet(bytes(data),m,gi)
        struct.pack_into('bBB',data,q,*trip)
        width_changes[ch]={'glyph':gi,'old':list(oldtrip),'new':list(trip),'base':base_for[ch]}
    data[m['doff']:m['doff']+m['sheetsize']]=encode_la8(L,A,m)

    # Replace six existing scan-codepoints IN PLACE. Keep pair ordering ascending.
    # Assign sorted Turkish codepoints to the six consecutive glyph slots.
    code_to_glyph=[(ord('Ğ'),303),(ord('ğ'),304),(ord('İ'),305),(ord('ı'),306),(ord('Ş'),307),(ord('ş'),308)]
    for (i,oldcp,oldgi),(newcp,newgi) in zip(old_slots,code_to_glyph):
        if oldgi!=newgi: raise AssertionError('slot mismatch')
        struct.pack_into(m['e']+'HH',data,off+22+i*4,newcp,newgi)

    # No structural bytes may change: same decompressed length, same header filesize/block count, same section boundaries.
    if len(data)!=len(original): raise AssertionError('font size changed')
    if data[:0x14]!=original[:0x14]: raise AssertionError('FFNT header changed')
    # Verify parser now maps all Turkish glyphs to <=334.
    newfm=core.CFNTMetrics(bytes(data)); verify={}
    for ch,gi in SLOTS.items():
        got=newfm.glyph_by_code.get(ord(ch)); verify[ch]={'glyph':got,'expected':gi,'width':newfm.char_width(ch)}
        if got!=gi: raise AssertionError((ch,got,gi))
    # Verify replaced Japanese codes are no longer mapped.
    for cp in OLD_CODES:
        if cp in newfm.glyph_by_code: raise AssertionError(f'old codepoint still mapped {cp:04X}')

    newpacked=lz11_compress(bytes(data))
    if core.lz11_decompress(newpacked)!=bytes(data): raise AssertionError('LZ11 roundtrip')
    dst_lz.parent.mkdir(parents=True,exist_ok=True); dst_lz.write_bytes(newpacked)

    if preview:
        scale=8; margin=8; cw=m['cw']*scale; chh=m['ch']*scale
        sheet=Image.new('RGB',(3*(cw+margin)+margin,2*(chh+40+margin)+margin),(30,30,30)); d=ImageDraw.Draw(sheet)
        order=['Ğ','ğ','İ','ı','Ş','ş']
        for n,ch in enumerate(order):
            r=n//3;c=n%3;x=margin+c*(cw+margin);y=margin+r*(chh+40+margin)
            l,a=glyphs[ch]
            rgba=np.zeros((m['ch'],m['cw'],4),np.uint8);rgba[:,:,0]=40;rgba[:,:,1]=160;rgba[:,:,2]=210;rgba[:,:,3]=l
            im=Image.fromarray(rgba,'RGBA').resize((cw,chh),Image.Resampling.NEAREST);sheet.paste(im,(x,y),im)
            fill=np.zeros((m['ch'],m['cw'],4),np.uint8);fill[:,:,:3]=255;fill[:,:,3]=a
            fim=Image.fromarray(fill,'RGBA').resize((cw,chh),Image.Resampling.NEAREST);sheet.paste(fim,(x,y),fim)
            d.text((x+2,y+chh+3),f'{ch} -> {SLOTS[ch]}',fill='white')
        preview.parent.mkdir(parents=True,exist_ok=True);sheet.save(preview)

    # Compute changed byte ranges for transparency.
    changed=[i for i,(a,b) in enumerate(zip(original,data)) if a!=b]
    rep={
        'method':'in_place_repurpose_unused_original_glyph_slots',
        'source_sha256':hashlib.sha256(packed).hexdigest(),
        'output_sha256':hashlib.sha256(newpacked).hexdigest(),
        'decompressed_size_preserved':len(data),
        'ffnt_header_preserved':data[:0x14]==original[:0x14],
        'block_count_preserved':struct.unpack_from(m['e']+'I',original,0x10)[0],
        'replaced_original_codepoints':[f'U+{x:04X}' for x in OLD_CODES],
        'new_mappings':verify,
        'width_changes':width_changes,
        'changed_byte_count':len(changed),
        'min_changed_offset':min(changed) if changed else None,
        'max_changed_offset':max(changed) if changed else None,
    }
    if report:
        report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rep,ensure_ascii=False,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preview',type=Path);ap.add_argument('--report',type=Path);a=ap.parse_args()
    build(a.src,a.out,a.preview,a.report)
