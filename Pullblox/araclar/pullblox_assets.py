#!/usr/bin/env python3
"""Pullblox Turkish image-asset builder.

Rebuilds only the English-slot UI archives that contain baked English words:
  Game_U.lz: START! / CLEAR!
  Res_U.lz:  Congratulations!
All generated BCLIMs keep the original English texture dimensions, pixel format,
and byte size. DARC replacement is in-place; only target payload bytes change.
"""
from __future__ import annotations
from pathlib import Path
import argparse, struct, zipfile, hashlib
from collections import defaultdict, deque
from PIL import Image, ImageDraw, ImageFont

from bclim_codec import decode_bclim, encode_bclim, parse_header
from asset_probe import lz11_decompress, darc_entries

FONT_CANDIDATES = [
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]

def _font_path() -> Path:
    for p in FONT_CANDIDATES:
        if p.exists(): return p
    raise FileNotFoundError('A bold TrueType font is required for rebuilding preview textures.')

def lz11_compress(data: bytes) -> bytes:
    """Greedy Nintendo LZ11 compressor, verified by our independent decompressor."""
    n=len(data)
    out=bytearray(b'\x11')
    if n < 0x1000000:
        out += bytes((n & 0xff, (n>>8)&0xff, (n>>16)&0xff))
    else:
        out += b'\x00\x00\x00' + struct.pack('<I',n)
    # recent positions keyed by 3-byte prefix. Limit candidate count for speed.
    hist=defaultdict(deque)
    pos=0
    def add_position(p):
        if p+2>=n: return
        k=data[p:p+3]; q=hist[k]; q.append(p)
        while q and p-q[0] > 0x1000: q.popleft()
        while len(q)>96: q.popleft()
    while pos<n:
        flag_at=len(out); out.append(0); flags=0
        for bit in range(8):
            if pos>=n: break
            best_len=0; best_disp=0
            if pos+2<n:
                q=hist.get(data[pos:pos+3])
                if q:
                    maxlen=min(n-pos,0x10110)
                    # newest candidates tend to be best and are faster
                    for p in reversed(q):
                        disp=pos-p
                        if disp<1 or disp>0x1000: continue
                        l=3
                        while l<maxlen and data[p+l]==data[pos+l]: l+=1
                        if l>best_len:
                            best_len=l; best_disp=disp
                            if l==maxlen: break
            if best_len>=3:
                flags |= 0x80>>bit
                l=best_len; d=best_disp-1
                if l<=0x10:
                    out += bytes((((l-1)<<4)|((d>>8)&0xF), d&0xFF))
                elif l<=0x110:
                    v=l-0x11
                    out += bytes(((v>>4)&0xF, ((v&0xF)<<4)|((d>>8)&0xF), d&0xFF))
                else:
                    v=l-0x111
                    out += bytes((0x10|((v>>12)&0xF), (v>>4)&0xFF, ((v&0xF)<<4)|((d>>8)&0xF), d&0xFF))
                old=pos; pos += l
                for p in range(old,pos): add_position(p)
            else:
                out.append(data[pos]); add_position(pos); pos+=1
        out[flag_at]=flags
    return bytes(out)

def replace_darc_files(darc: bytes, replacements: dict[str, bytes]) -> bytes:
    entries={e['path']:e for e in darc_entries(darc) if not e['isdir']}
    out=bytearray(darc)
    for path,new in replacements.items():
        if path not in entries: raise KeyError(path)
        e=entries[path]
        if len(new)!=e['b']:
            raise ValueError(f'{path}: replacement must stay {e["b"]} bytes, got {len(new)}')
        out[e['a']:e['a']+e['b']]=new
    # structure must remain fully parseable and file metadata unchanged
    again={e['path']:(e['a'],e['b']) for e in darc_entries(bytes(out)) if not e['isdir']}
    before={e['path']:(e['a'],e['b']) for e in entries.values()}
    if again!=before: raise AssertionError('DARC structure changed')
    return bytes(out)

def get_darc_file(darc: bytes, path: str) -> bytes:
    for e in darc_entries(darc):
        if not e['isdir'] and e['path']==path:
            return darc[e['a']:e['a']+e['b']]
    raise KeyError(path)

def _fit_font(text:str, size:tuple[int,int], max_size=42, stroke=3, margin=(4,3), font_path=None):
    fp=str(font_path or _font_path()); W,H=size
    probe=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(probe)
    for fs in range(max_size,9,-1):
        font=ImageFont.truetype(fp,fs)
        bb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        if bb[2]-bb[0] <= W-2*margin[0] and bb[3]-bb[1] <= H-2*margin[1]-3:
            return font
    return ImageFont.truetype(fp,10)

def _text_width(draw,font,s,stroke=0):
    b=draw.textbbox((0,0),s,font=font,stroke_width=stroke); return b[2]-b[0]

def render_banner(size:tuple[int,int], text:str) -> Image.Image:
    """Approximate the official multicolour chunky UI lettering within original bounds."""
    W,H=size; img=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(img)
    font=_fit_font(text,size,max_size=36 if H<=42 else 39,stroke=2,margin=(6,4))
    # Original-style vivid letter cycle.
    palette=[(238,72,50,255),(246,194,38,255),(64,196,63,255),(45,105,220,255),(153,73,201,255)]
    widths=[_text_width(d,font,ch,stroke=2) for ch in text]
    # modest tracking, tighten if necessary
    tracking=0
    total=sum(widths)+tracking*(len(text)-1)
    x=max(1,(W-total)//2); y0=0
    # vertical placement based on bbox
    bb=d.textbbox((0,0),text,font=font,stroke_width=2)
    th=bb[3]-bb[1]; y=max(0,(H-th-3)//2 - bb[1] - 1)
    # Per-letter dark blue drop shadow then white border/colour fill.
    for i,(ch,cw) in enumerate(zip(text,widths)):
        d.text((x,y+3),ch,font=font,fill=(28,42,127,255),stroke_width=2,stroke_fill=(28,42,127,255))
        d.text((x,y),ch,font=font,fill=palette[i%len(palette)],stroke_width=2,stroke_fill=(255,255,238,255))
        x += cw+tracking
    return img

def render_congrats(size:tuple[int,int], text='TEBRİKLER!') -> tuple[Image.Image,Image.Image]:
    """Return (outline/alpha layer for Font_Cong0, luminance layer for Font_Cong1)."""
    W,H=size; fp=_font_path()
    probe=Image.new('RGBA',(W,H)); dr=ImageDraw.Draw(probe)
    font=_fit_font(text,size,max_size=38,stroke=2,margin=(5,2),font_path=fp)
    bb=dr.textbbox((0,0),text,font=font,stroke_width=2)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x=(W-tw)//2-bb[0]; y=(H-th)//2-bb[1]
    # Cong1 is a luminance mask: black background, white glyphs.
    main=Image.new('RGBA',(W,H),(0,0,0,255)); dm=ImageDraw.Draw(main)
    dm.text((x,y),text,font=font,fill=(255,255,255,255))
    # Cong0 carries white face + black outline/shadow with alpha.
    outline=Image.new('RGBA',(W,H),(0,0,0,0)); do=ImageDraw.Draw(outline)
    do.text((x+2,y+2),text,font=font,fill=(0,0,0,255),stroke_width=2,stroke_fill=(0,0,0,255))
    do.text((x,y),text,font=font,fill=(255,255,255,255),stroke_width=1,stroke_fill=(32,32,32,255))
    return outline,main

def build_from_zip(game_zip: Path, out_romfs: Path, preview_dir: Path|None=None):
    with zipfile.ZipFile(game_zip) as z:
        game_lz=z.read('romfs/EURen/lyt/Game_U.lz')
        res_lz=z.read('romfs/EURen/lyt/Res_U.lz')
    game=lz11_decompress(game_lz); res=lz11_decompress(res_lz)
    start_path='timg/G_PzlOp_USAen.bclim'; clear_path='timg/G_PzlEd_USAen.bclim'
    cong0_path='timg/Font_Cong0.bclim'; cong1_path='timg/Font_Cong1.bclim'
    start_tpl=get_darc_file(game,start_path); clear_tpl=get_darc_file(game,clear_path)
    c0_tpl=get_darc_file(res,cong0_path); c1_tpl=get_darc_file(res,cong1_path)
    start=render_banner(decode_bclim(start_tpl).size,'BAŞLA!')
    clear=render_banner(decode_bclim(clear_tpl).size,'TAMAM!')
    c0,c1=render_congrats(decode_bclim(c0_tpl).size,'TEBRİKLER!')
    start_b=encode_bclim(start,start_tpl); clear_b=encode_bclim(clear,clear_tpl)
    c0_b=encode_bclim(c0,c0_tpl); c1_b=encode_bclim(c1,c1_tpl)
    game2=replace_darc_files(game,{start_path:start_b,clear_path:clear_b})
    res2=replace_darc_files(res,{cong0_path:c0_b,cong1_path:c1_b})
    game2_lz=lz11_compress(game2); res2_lz=lz11_compress(res2)
    if lz11_decompress(game2_lz)!=game2: raise AssertionError('Game_U LZ11 roundtrip failed')
    if lz11_decompress(res2_lz)!=res2: raise AssertionError('Res_U LZ11 roundtrip failed')
    out=(out_romfs/'EURen'/'lyt'); out.mkdir(parents=True,exist_ok=True)
    (out/'Game_U.lz').write_bytes(game2_lz); (out/'Res_U.lz').write_bytes(res2_lz)
    if preview_dir:
        preview_dir.mkdir(parents=True,exist_ok=True)
        # Decode final BCLIM bytes, not pre-quantized PIL sources, so preview matches patch exactly.
        decode_bclim(start_b).save(preview_dir/'BAŞLA.png')
        decode_bclim(clear_b).save(preview_dir/'TAMAM.png')
        decode_bclim(c0_b).save(preview_dir/'TEBRİKLER_outline.png')
        decode_bclim(c1_b).save(preview_dir/'TEBRİKLER_mask.png')
    return {
        'Game_U_original_sha256':hashlib.sha256(game_lz).hexdigest(),
        'Game_U_patched_sha256':hashlib.sha256(game2_lz).hexdigest(),
        'Res_U_original_sha256':hashlib.sha256(res_lz).hexdigest(),
        'Res_U_patched_sha256':hashlib.sha256(res2_lz).hexdigest(),
        'Game_U_uncompressed_size':len(game2),'Game_U_lz_size':len(game2_lz),
        'Res_U_uncompressed_size':len(res2),'Res_U_lz_size':len(res2_lz),
        'textures':{
            start_path:{'text':'BAŞLA!','size':decode_bclim(start_b).size,'format':parse_header(start_b)[2]},
            clear_path:{'text':'TAMAM!','size':decode_bclim(clear_b).size,'format':parse_header(clear_b)[2]},
            cong0_path:{'text':'TEBRİKLER! outline','size':decode_bclim(c0_b).size,'format':parse_header(c0_b)[2]},
            cong1_path:{'text':'TEBRİKLER! mask','size':decode_bclim(c1_b).size,'format':parse_header(c1_b)[2]},
        }
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--zip',required=True,type=Path); ap.add_argument('--out-romfs',required=True,type=Path); ap.add_argument('--previews',type=Path)
    a=ap.parse_args(); print(build_from_zip(a.zip,a.out_romfs,a.previews))
if __name__=='__main__': main()
