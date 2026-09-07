#!/usr/bin/env python3
"""Luigi's Mansion 3DS EU Turkish font fixer v8 — source-glyph composite edition.

Goals:
* Never resize the original GZF atlases.
* Never increase entry counts or move image payload offsets.
* Never use an external/system font for the added Turkish glyphs.
* Build every added shape from original game glyph pixels:
  - location.gzf bases/accents from location.gzf itself,
  - cedilla source from ending.gzf (same game's serif UI font family),
  - breve source from the game's main.gzf Turkish glyph,
  - Y / dotted I assembled from source strokes already present in location.gzf.

This is deliberately conservative: all original common glyph bitmaps and metrics remain
byte-identical. Only repurposed Turkish slots in location.gzf and five reserved Turkish
slots in ending.gzf are changed.
"""
from __future__ import annotations
import argparse, math, struct, zipfile
from pathlib import Path
from PIL import Image, ImageChops

# ---------- GZF codec ----------
def _zorder_x(tile_size:int,count:int)->int:
    div=tile_size//2; x=count//div & div
    while div>1:
        div//=2; x |= count//div & div
    return x

def _zorder_y(tile_size:int,count:int)->int:
    div=tile_size; div2=tile_size//2; y=count//div & div2
    while div2>1:
        div//=2; div2//=2; y |= count//div & div2
    return y

def _points(width:int,height:int,tile_size:int=8):
    sw=(width+7)&~7; sh=(height+7)&~7
    tile_size=2 << int(math.log(((tile_size+7)&~7)-1,2))
    p=tile_size**2; stride=sw
    for i in range(sw*sh):
        xo=(i//p%(stride//tile_size))*tile_size
        yo=(i//p//(stride//tile_size))*tile_size
        yield xo+_zorder_x(tile_size,i), yo+_zorder_y(tile_size,i)

def decode_gzf(data:bytes):
    if data[:4] != b'GZFX': raise ValueError('Not GZFX')
    version,iho,ilen,elen,unk1=struct.unpack_from('<IHHHH',data,4)
    image_count,entry_count,unk2,fmt=struct.unpack_from('<IIII',data,0x10)
    font_size,unk4,unk5,tw,th,unk8,unk9=struct.unpack_from('<HHHHHHI',data,0x20)
    if image_count != 1 or ilen != 8 or elen != 12:
        raise ValueError('Unexpected GZF layout')
    off,w,h=struct.unpack_from('<IHH',data,iho)
    n=w*h//(2 if fmt==8 else 1); raw=data[off:off+n]
    atlas=Image.new('L',(w,h),0)
    for i,(x,y) in enumerate(_points(w,h)):
        if x>=w or y>=h: continue
        if fmt==8:
            b=raw[i//2]; a=((b&15) if i%2==0 else (b>>4))*17
        else: a=raw[i]
        atlas.putpixel((x,y),a)
    eoff=iho+image_count*ilen
    entries=[list(struct.unpack_from('<IHHHBB',data,eoff+i*elen)) for i in range(entry_count)]
    meta=dict(version=version,iho=iho,ilen=ilen,elen=elen,unk1=unk1,image_count=image_count,
              unk2=unk2,fmt=fmt,font_size=font_size,unk4=unk4,unk5=unk5,tw=tw,th=th,
              unk8=unk8,unk9=unk9,original_image_off=off,original_w=w,original_h=h,
              original_entry_count=entry_count,original_size=len(data))
    return meta,entries,atlas

def encode_atlas(atlas:Image.Image,fmt:int)->bytes:
    vals=[]; w,h=atlas.size
    for x,y in _points(w,h): vals.append(atlas.getpixel((x,y)) if x<w and y<h else 0)
    if fmt==8:
        out=bytearray()
        for i in range(0,len(vals),2):
            lo=round(vals[i]/17)&0xF; hi=round(vals[i+1]/17)&0xF if i+1<len(vals) else 0
            out.append(lo|(hi<<4))
        return bytes(out[:w*h//2])
    return bytes(vals[:w*h])

def rebuild_gzf(meta,entries,atlas)->bytes:
    iho=meta['iho']; ilen=meta['ilen']; elen=meta['elen']
    table_end=iho + meta['image_count']*ilen + len(entries)*elen
    image_off=(table_end+0x7f)&~0x7f
    w,h=atlas.size
    header=bytearray(max(iho,0x30)); header[:4]=b'GZFX'
    struct.pack_into('<IHHHH',header,4,meta['version'],iho,ilen,elen,meta['unk1'])
    struct.pack_into('<IIII',header,0x10,meta['image_count'],len(entries),meta['unk2'],meta['fmt'])
    struct.pack_into('<HHHHHHI',header,0x20,meta['font_size'],meta['unk4'],meta['unk5'],meta['tw'],meta['th'],meta['unk8'],meta['unk9'])
    out=header
    if len(out)<iho: out.extend(b'\0'*(iho-len(out)))
    out.extend(struct.pack('<IHH',image_off,w,h))
    for e in entries: out.extend(struct.pack('<IHHHBB',*e))
    out.extend(b'\0'*(image_off-len(out)))
    out.extend(encode_atlas(atlas,meta['fmt']))
    return bytes(out)

def cmap(entries): return {chr(e[0]):e for e in entries}
def glyph_tile(atlas,meta,e):
    tw,th=meta['tw'],meta['th']; return atlas.crop((e[4]*tw,e[5]*th,(e[4]+1)*tw,(e[5]+1)*th))
def put_tile(atlas,meta,e,img):
    tw,th=meta['tw'],meta['th']; atlas.paste(img,(e[4]*tw,e[5]*th))
def plus(base,*layers):
    out=base.copy()
    for layer in layers: out=ImageChops.lighter(out,layer)
    return out

def layer_at(size,im,xy):
    out=Image.new('L',size,0); out.paste(im,xy); return out

def positive_mark(accented,base,box,threshold=12):
    """Extra accent pixels only, avoiding base-glyph rasterization differences."""
    d=ImageChops.subtract(accented,base).crop(box)
    d=d.point(lambda p:p if p>=threshold else 0)
    b=d.getbbox()
    return d.crop(b) if b else d

def raw_region(im,box,threshold=0):
    c=im.crop(box)
    if threshold: c=c.point(lambda p:p if p>=threshold else 0)
    b=c.getbbox()
    return c.crop(b) if b else c

# ---------- source-composed location glyphs ----------
def _build_location_y(V:Image.Image,T:Image.Image)->Image.Image:
    # Upper fork from V; central stem + bottom serif from T. No foreign raster source.
    out=Image.new('L',V.size,0)
    out.paste(V.crop((0,0,V.width,14)),(0,0))  # exact V rows through fork
    bridge=layer_at(V.size,V.crop((10,13,16,16)),(10,13))
    stem=layer_at(V.size,T.crop((10,13,16,21)),(10,13))
    out=plus(out,bridge,stem)
    # Below the fork, only central stem/serif remains.
    px=out.load()
    for y in range(14,V.height):
        for x in range(V.width):
            if x<10 or x>15: px[x,y]=0
    return out

def _build_location_i_cap(T:Image.Image)->Image.Image:
    # Classic serif I assembled from T's own central stem and bottom serif.
    out=Image.new('L',T.size,0)
    out.paste(T.crop((10,10,16,18)),(10,8))
    bottom=T.crop((9,18,17,20)); out.paste(bottom,(9,18))
    out.paste(bottom.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(9,5))
    return out

def fix_location(original:bytes, ending_original:bytes, main_original:bytes):
    meta,entries,atlas=decode_gzf(original); em=cmap(entries)
    e_meta,e_entries,e_atlas=decode_gzf(ending_original); eem=cmap(e_entries)
    m_meta,m_entries,m_atlas=decode_gzf(main_original); mem=cmap(m_entries)
    if atlas.size!=(1024,64) or len(entries)!=75 or meta['original_image_off']!=0x400:
        raise ValueError('Unexpected EU location.gzf geometry')

    # Ten slots not needed by the English-based Turkish LayeredFS patch.
    replacements={'É':'Y','à':'Ç','á':'Ö','ä':'â','è':'ö','é':'ğ','í':'İ','ñ':'ı','ó':'Ş','ú':'ş'}
    donor_entries={src:em[src] for src in replacements}
    size=(meta['tw'],meta['th'])
    L=lambda ch:glyph_tile(atlas,meta,em[ch])
    E=lambda ch:glyph_tile(e_atlas,e_meta,eem[ch])
    M=lambda ch:glyph_tile(m_atlas,m_meta,mem[ch])

    # Exact source marks.
    dia=positive_mark(L('ü'),L('u'),(0,0,meta['tw'],9),8)           # location diaeresis
    acute=positive_mark(L('á'),L('a'),(0,0,meta['tw'],9),12)        # / from location
    grave=positive_mark(L('à'),L('a'),(0,0,meta['tw'],9),12)        # \\ from location
    breve=raw_region(M('ğ'),(3,0,18,8),12).resize((11,4),Image.Resampling.LANCZOS)  # game's real breve
    ced_cap=positive_mark(E('Ç'),E('C'),(0,22,e_meta['tw'],27),12)  # game's real cedilla
    ced_low=positive_mark(E('ç'),E('c'),(0,22,e_meta['tw'],27),12)
    dot=raw_region(L('i'),(10,5,17,9),12)

    # Keep source sizes where possible; only the ending-font cedilla is reduced to the
    # 26px location tile. It remains a source bitmap, not a redrawn mark.
    if ced_cap.size!=(6,4): ced_cap=ced_cap.resize((6,4),Image.Resampling.LANCZOS)
    if ced_low.size!=(6,4): ced_low=ced_low.resize((6,4),Image.Resampling.LANCZOS)

    Y=_build_location_y(L('V'),L('T'))
    Icap=_build_location_i_cap(L('T'))
    Idot=dot.resize((5,3),Image.Resampling.LANCZOS)

    # Circumflex is assembled from the location font's own acute + grave strokes.
    # Left is acute (/), right is grave (\\), yielding ^.
    circ=Image.new('L',size,0)
    circ=plus(circ,layer_at(size,acute,(10,5)),layer_at(size,grave,(13,5)))

    glyphs={
        'Y':Y,
        'Ç':plus(L('C'),layer_at(size,ced_cap,(11,21))),
        'Ö':plus(L('O'),layer_at(size,dia,(9,1))),
        'â':plus(L('a'),circ),
        'ö':plus(L('o'),layer_at(size,dia,(9,5))),
        'ğ':plus(L('g'),layer_at(size,breve,(8,4))),
        'İ':plus(Icap,layer_at(size,Idot,(11,1))),
        'Ş':plus(L('S'),layer_at(size,ced_cap,(11,21))),
        'ş':plus(L('s'),layer_at(size,ced_low,(11,21))),
    }
    dotless=L('i').copy(); dotless.paste(0,(0,0,meta['tw'],9)); glyphs['ı']=dotless

    metric_base={'Y':'V','Ç':'C','Ö':'O','â':'a','ö':'o','ğ':'g','İ':'i','ı':'i','Ş':'S','ş':'s'}
    for src,dst in replacements.items():
        e=donor_entries[src]; base=em[metric_base[dst]]
        e[0]=ord(dst); e[1]=base[1]; e[2]=base[2]; e[3]=base[3]
        put_tile(atlas,meta,e,glyphs[dst])
    entries.sort(key=lambda e:e[0])
    out=rebuild_gzf(meta,entries,atlas)
    nm,ne,na=decode_gzf(out)
    assert len(out)==len(original) and len(ne)==75 and na.size==(1024,64)
    assert nm['original_image_off']==0x400
    return out

# ---------- source-composed ending glyphs ----------
def fix_ending(original:bytes, main_original:bytes):
    meta,entries,atlas=decode_gzf(original); em=cmap(entries)
    m_meta,m_entries,m_atlas=decode_gzf(main_original); mem=cmap(m_entries)
    E=lambda ch:glyph_tile(atlas,meta,em[ch])
    M=lambda ch:glyph_tile(m_atlas,m_meta,mem[ch])
    if atlas.size!=(1024,512): raise ValueError('Unexpected ending atlas')

    breve=raw_region(M('ğ'),(3,0,18,8),12).resize((11,4),Image.Resampling.LANCZOS)
    ced_cap=positive_mark(E('Ç'),E('C'),(0,22,meta['tw'],27),12)
    ced_low=positive_mark(E('ç'),E('c'),(0,22,meta['tw'],27),12)
    dot=raw_region(E('i'),(12,9,17,13),12)

    size=(meta['tw'],meta['th'])
    glyphs={
        'Ğ':plus(E('G'),layer_at(size,breve,(9,4))),
        'ğ':plus(E('g'),layer_at(size,breve,(9,4))),
        'İ':plus(E('I'),layer_at(size,dot,(13,4))),
        'Ş':plus(E('S'),layer_at(size,ced_cap,(12,22))),
        'ş':plus(E('s'),layer_at(size,ced_low,(12,22))),
    }
    bases={'Ğ':'G','ğ':'g','İ':'I','Ş':'S','ş':'s'}
    for ch,img in glyphs.items():
        e=em[ch]; b=em[bases[ch]]
        e[1]=b[1]; e[2]=b[2]; e[3]=b[3]
        put_tile(atlas,meta,e,img)
    entries.sort(key=lambda e:e[0])
    out=rebuild_gzf(meta,entries,atlas)
    nm,ne,na=decode_gzf(out)
    assert len(out)==len(original) and len(ne)==len(entries) and na.size==(1024,512)
    assert nm['original_image_off']==meta['original_image_off']
    return out

def find_member(zf:zipfile.ZipFile,suffix:str)->str:
    hits=[n for n in zf.namelist() if n.replace('\\','/').endswith(suffix)]
    if not hits: raise FileNotFoundError(suffix)
    return hits[0]

def main():
    ap=argparse.ArgumentParser(description='LM3DS EU Turkish source-glyph font fixer v8')
    ap.add_argument('--original',required=True,help='Original EU game romfs ZIP')
    ap.add_argument('--outdir',required=True)
    args=ap.parse_args(); out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.original) as z:
        loc=z.read(find_member(z,'romfs/Region_EU/location.gzf'))
        end=z.read(find_member(z,'romfs/Region_EU/ending.gzf'))
        mainf=z.read(find_member(z,'romfs/Region_EU/main.gzf'))
    loc2=fix_location(loc,end,mainf); end2=fix_ending(end,mainf)
    (out/'location.gzf').write_bytes(loc2); (out/'ending.gzf').write_bytes(end2)
    print('location.gzf',len(loc2),'bytes — source-composed, geometry preserved')
    print('ending.gzf',len(end2),'bytes — source-composed, geometry preserved')

if __name__=='__main__': main()
