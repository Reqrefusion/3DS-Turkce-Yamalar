#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, struct, hashlib, json, csv, sys
from typing import Dict, List, Tuple

# Standalone low-level BFFNT reader/texture codec. No v4 dependency.
from dataclasses import dataclass

FMT_A8=0x08
FMT_A4=0x0B

@dataclass
class Font:
    path:Path; data:bytes; e:str; header_size:int; version:int; block_count:int
    tglp_pos:int; cwdh_pos:int; cmap_first_pos:int; cmap_last_pos:int
    cell_w:int; cell_h:int; sheet_count:int; max_char_w:int; sheet_size:int; baseline:int; fmt:int
    cols:int; rows:int; sheet_w:int; sheet_h:int; sheet_off:int
    mapping:Dict[int,int]; widths:Dict[int,bytes]; cwdh_ranges:List[Tuple[int,int,int]]

def parse_cmap_chain(b:bytes,e:str,ptr:int):
    out={}; poss=[]
    while ptr:
        pos=ptr-8; poss.append(pos)
        magic,size,start,end,typ,res,nextp=struct.unpack_from(e+'4sI4HI',b,pos)
        if magic!=b'CMAP': raise ValueError('Bad CMAP')
        d=b[pos+20:pos+size]
        if typ==0:
            idx0=struct.unpack_from(e+'H',d,0)[0]
            for cp in range(start,end+1): out[cp]=idx0+cp-start
        elif typ==1:
            vals=struct.unpack_from(e+f'{end-start+1}H',d,0)
            for cp,idx in zip(range(start,end+1),vals):
                if idx!=0xFFFF: out[cp]=idx
        elif typ==2:
            n=struct.unpack_from(e+'H',d,0)[0]; q=2
            for _ in range(n):
                cp,idx=struct.unpack_from(e+'2H',d,q); q+=4; out[cp]=idx
        else: raise ValueError(f'Unknown CMAP method {typ}')
        ptr=nextp
    return out,poss

def parse_cwdh_chain(b:bytes,e:str,ptr:int):
    widths={}; ranges=[]
    while ptr:
        pos=ptr-8
        magic,size,start,end,nextp=struct.unpack_from(e+'4sI2HI',b,pos)
        if magic!=b'CWDH': raise ValueError('Bad CWDH')
        n=end-start+1; raw=b[pos+16:pos+16+n*3]
        if len(raw)<n*3: raise ValueError('Short CWDH')
        for i in range(n): widths[start+i]=raw[i*3:i*3+3]
        ranges.append((pos,start,end)); ptr=nextp
    return widths,ranges

def parse_font(path:Path)->Font:
    b=path.read_bytes()
    if b[:4] not in (b'FFNT',b'FFNU'): raise ValueError('Not BFFNT')
    e='<' if b[4:6]==b'\xff\xfe' else '>' if b[4:6]==b'\xfe\xff' else None
    if not e: raise ValueError('Bad BOM')
    hs=struct.unpack_from(e+'H',b,6)[0]; ver=struct.unpack_from(e+'I',b,8)[0]; fs=struct.unpack_from(e+'I',b,12)[0]
    blocks=struct.unpack_from(e+'H',b,16)[0]
    if fs!=len(b): raise ValueError(f'file size mismatch {fs}/{len(b)}')
    finf=struct.unpack_from(e+'4sI4B2H4B3I',b,0x14)
    if finf[0]!=b'FINF': raise ValueError('Bad FINF')
    tptr,cptr,mptr=finf[-3:]
    tp=tptr-8
    t=struct.unpack_from(e+'4sI4BI6HI',b,tp)
    _,_,cw,ch,sc,mcw,ssize,base,fmt,cols,rows,sw,sh,soff=t
    mapping,cmap_pos=parse_cmap_chain(b,e,mptr)
    widths,cwdh_ranges=parse_cwdh_chain(b,e,cptr)
    return Font(path,b,e,hs,ver,blocks,tp,cptr-8,cmap_pos[0],cmap_pos[-1],cw,ch,sc,mcw,ssize,base,fmt,cols,rows,sw,sh,soff,mapping,widths,cwdh_ranges)

def iter_swizzle_positions(w,h):
    if w%8 or h%8: raise ValueError('sheet not 8px tiled')
    for ty in range(h//8):
      for tx in range(w//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             dp=x3+x2*4+x*16+tx*64 + y3*2+y2*8+y*32+ty*w*8
             yield px,py,dp

def decode_alpha(f:Font):
    raw=f.data[f.sheet_off:f.sheet_off+f.sheet_size]; a=[0]*(f.sheet_w*f.sheet_h)
    for x,y,dp in iter_swizzle_positions(f.sheet_w,f.sheet_h):
        if f.fmt==FMT_A8: v=raw[dp]
        elif f.fmt==FMT_A4: v=((raw[dp//2]>>((dp&1)*4))&15)*17
        else: raise ValueError(f'unsupported format {f.fmt}')
        a[x+y*f.sheet_w]=v
    return a

def encode_alpha(f:Font,a:List[int]):
    raw=bytearray(f.sheet_size)
    for x,y,dp in iter_swizzle_positions(f.sheet_w,f.sheet_h):
        v=a[x+y*f.sheet_w]
        if f.fmt==FMT_A8: raw[dp]=max(0,min(255,v))
        elif f.fmt==FMT_A4:
            q=max(0,min(15,int(round(v/17)))); raw[dp//2]|=q<<((dp&1)*4)
        else: raise ValueError('unsupported')
    return bytes(raw)

def runtime_origin(f:Font,idx:int):
    per=f.cols*f.rows; local=idx%per; sheet=idx//per
    if sheet>=f.sheet_count: raise ValueError('index exceeds sheets')
    return sheet,(local%f.cols)*(f.cell_w+1)+1,(local//f.cols)*(f.cell_h+1)+1

def unpack_sbyte(b:int)->int: return b-256 if b>=128 else b

def metric(f:Font,idx:int):
    x=f.widths[idx]; return tuple(unpack_sbyte(v) for v in x)

NAMES=['Caption_US.bffnt','UI_Caption_US.bffnt','Common_Sura_B_16.bffnt']
TRCORE='ÇĞİÖŞÜçğıöşü'


def copy_full_runtime_cell(src_f, src_a, src_idx, dst_f, dst_a, dst_idx):
    # Copy exactly the drawable cell, not the 1px separator. Geometry is identical between base/user patch.
    _,sx,sy=runtime_origin(src_f,src_idx)
    _,dx,dy=runtime_origin(dst_f,dst_idx)
    for y in range(src_f.cell_h):
        for x in range(src_f.cell_w):
            dst_a[(dx+x)+(dy+y)*dst_f.sheet_w]=src_a[(sx+x)+(sy+y)*src_f.sheet_w]


def glyph_cell_tuple(f,a,idx):
    _,x,y=runtime_origin(f,idx)
    return tuple(a[(x+xx)+(y+yy)*f.sheet_w] for yy in range(f.cell_h) for xx in range(f.cell_w))


def build_cwdh(records: List[bytes], e: str) -> bytes:
    start=0; end=len(records)-1
    body=b''.join(records)
    size=16+len(body)
    pad=(-size)%4
    size+=pad
    return struct.pack(e+'4sI2HI',b'CWDH',size,start,end,0)+body+b'\0'*pad


def build_cmap_scan(mapping: Dict[int,int], e: str) -> bytes:
    items=sorted(mapping.items())
    start=min(cp for cp,_ in items); end=max(cp for cp,_ in items)
    body=struct.pack(e+'H',len(items))+b''.join(struct.pack(e+'2H',cp,idx) for cp,idx in items)
    size=20+len(body)
    pad=(-size)%4
    size+=pad
    return struct.pack(e+'4sI4HI',b'CMAP',size,start,end,2,0,0)+body+b'\0'*pad


def finf_ptr_offsets(f):
    # FINF is fixed at 0x14 in these fonts. Its last three uint32 fields are TGLP,CWDH,CMAP pointers.
    # Struct: 4s I 4B 2H 4B 3I => last three start at FINF+20.
    return 0x14+20, 0x14+24, 0x14+28


def build_one(base_path:Path, user_path:Path, out_path:Path):
    b=parse_font(base_path); p=parse_font(user_path)
    geom=lambda f:(f.cell_w,f.cell_h,f.sheet_count,f.max_char_w,f.sheet_size,f.baseline,f.fmt,f.cols,f.rows,f.sheet_w,f.sheet_h,f.sheet_off)
    if geom(b)!=geom(p):
        raise ValueError(f'{base_path.name}: base/user geometry mismatch')
    ba=decode_alpha(b); pa=decode_alpha(p)
    final_a=pa[:]  # preserve user's texture as primary truth

    # 1) Existing same-codepoint/same-index non-Turkish glyphs that user tool accidentally changed: restore from base.
    restored_accidental=[]
    for cp,bidx in sorted(b.mapping.items()):
        pidx=p.mapping.get(cp)
        if pidx is None or pidx!=bidx or pidx not in p.widths:
            continue
        if chr(cp) in TRCORE:
            continue
        if p.widths[pidx]!=b.widths[bidx] or glyph_cell_tuple(p,pa,pidx)!=glyph_cell_tuple(b,ba,bidx):
            copy_full_runtime_cell(b,ba,bidx,p,final_a,pidx)
            restored_accidental.append((cp,pidx))

    # 2) Preserve ALL user mappings at same indices. Restore codepoints sacrificed by the user tool at NEW indices.
    final_map=dict(p.mapping)
    missing_original=[cp for cp in sorted(b.mapping) if cp not in p.mapping]
    next_idx=max(p.mapping.values())+1
    cap=p.cols*p.rows*p.sheet_count
    target_for={}
    for cp in missing_original:
        while next_idx < cap:
            _,x,y=runtime_origin(p,next_idx)
            # Require target cell + separators to be blank in USER texture.
            nonzero=False
            for yy in range(max(0,y-1),min(p.sheet_h,y+p.cell_h+1)):
                for xx in range(max(0,x-1),min(p.sheet_w,x+p.cell_w+1)):
                    if pa[xx+yy*p.sheet_w]:
                        nonzero=True; break
                if nonzero: break
            if not nonzero: break
            next_idx+=1
        if next_idx>=cap:
            raise ValueError(f'{base_path.name}: no isolated blank glyph cell for U+{cp:04X}')
        target_for[cp]=next_idx
        copy_full_runtime_cell(b,ba,b.mapping[cp],p,final_a,next_idx)
        final_map[cp]=next_idx
        next_idx+=1

    # 3) Build one contiguous CWDH, matching user's game-proven single-section layout.
    final_max=max(final_map.values())
    widths=[]
    restored_missing_width=[]
    reverse_base={idx:cp for cp,idx in b.mapping.items()}
    target_reverse={idx:cp for cp,idx in target_for.items()}
    for idx in range(final_max+1):
        if idx in p.widths:
            widths.append(p.widths[idx])
        elif idx in b.widths:
            widths.append(b.widths[idx])
            restored_missing_width.append(idx)
        elif idx in target_reverse:
            cp=target_reverse[idx]
            widths.append(b.widths[b.mapping[cp]])
        else:
            # Defensive: use FINF default width bytes. In this dataset this path should never be hit.
            # FINF default width lives at offsets 12..14 inside FINF payload => file offsets 0x14+12..15.
            widths.append(p.data[0x14+12:0x14+15])

    # Added restored original glyphs need their original metrics, overriding any generic placeholder above.
    for cp,tidx in target_for.items():
        widths[tidx]=b.widths[b.mapping[cp]]

    tex=encode_alpha(p,final_a)
    if len(tex)!=p.sheet_size:
        raise AssertionError('texture size changed')

    # 4) Keep header+FINF+TGLP (including USER texture) physical layout, rebuild ONLY trailing CWDH+CMAP as 1+1 sections.
    tglp_end=p.cwdh_pos  # physical CWDH begins immediately after TGLP in these files
    out=bytearray(p.data[:tglp_end])
    out[p.sheet_off:p.sheet_off+p.sheet_size]=tex
    while len(out)%4: out.append(0)
    cwdh_pos=len(out); cwdh=build_cwdh(widths,p.e); out+=cwdh
    while len(out)%4: out.append(0)
    cmap_pos=len(out); cmap=build_cmap_scan(final_map,p.e); out+=cmap

    # Header file size/block count. Exactly FINF,TGLP,CWDH,CMAP = 4 blocks (same as user's working font).
    struct.pack_into(p.e+'I',out,12,len(out))
    struct.pack_into(p.e+'H',out,16,4)
    t_off,c_off,m_off=finf_ptr_offsets(p)
    # TGLP pointer remains unchanged. CWDH/CMAP pointers use Nintendo convention section_start+8.
    struct.pack_into(p.e+'I',out,c_off,cwdh_pos+8)
    struct.pack_into(p.e+'I',out,m_off,cmap_pos+8)

    out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_bytes(out)

    # 5) Strong post-build verification.
    f=parse_font(out_path); fa=decode_alpha(f)
    if f.block_count!=4 or len(f.cwdh_ranges)!=1 or f.cmap_first_pos!=f.cmap_last_pos:
        raise AssertionError('not single CWDH/CMAP layout')
    if set(final_map.items()) != set(f.mapping.items()):
        raise AssertionError('final mapping parse mismatch')
    if max(f.mapping.values()) not in f.widths:
        raise AssertionError('last mapped glyph has no CWDH')

    # Every user mapping remains same index, same metric, same full cell unless explicitly accidental/original repair.
    accidental_indices={idx for _,idx in restored_accidental}
    user_mismatch=[]
    tur_mismatch=[]
    for cp,pidx in p.mapping.items():
        if f.mapping.get(cp)!=pidx:
            user_mismatch.append((cp,'mapping'))
            continue
        if pidx in p.widths and f.widths.get(pidx)!=p.widths[pidx]:
            user_mismatch.append((cp,'metric'))
        if pidx not in accidental_indices and glyph_cell_tuple(f,fa,pidx)!=glyph_cell_tuple(p,pa,pidx):
            user_mismatch.append((cp,'bitmap'))
        if chr(cp) in TRCORE and (f.mapping.get(cp)!=pidx or glyph_cell_tuple(f,fa,pidx)!=glyph_cell_tuple(p,pa,pidx)):
            tur_mismatch.append(cp)
    if user_mismatch or tur_mismatch:
        raise AssertionError(f'user preservation failed: {user_mismatch[:10]}, tur={tur_mismatch}')

    # All base codepoints restored, and non-sacrificed originals render exactly as base after accidental repairs.
    base_missing=[]; base_bad=[]
    for cp,bidx in b.mapping.items():
        if cp not in f.mapping:
            base_missing.append(cp); continue
        findex=f.mapping[cp]
        # original metric/bitmap must equal base for every original codepoint
        if f.widths.get(findex)!=b.widths.get(bidx):
            base_bad.append((cp,'metric'))
        if glyph_cell_tuple(f,fa,findex)!=glyph_cell_tuple(b,ba,bidx):
            base_bad.append((cp,'bitmap'))
    if base_missing or base_bad:
        raise AssertionError(f'base restore failed missing={base_missing[:10]} bad={base_bad[:10]}')

    # Turkish codepoints must be exact user mapping/index/bitmap/metric.
    tr_rows=[]
    for ch in TRCORE:
        cp=ord(ch); pidx=p.mapping.get(cp); fidx=f.mapping.get(cp)
        row={'char':ch,'codepoint':f'U+{cp:04X}','user_index':pidx,'final_index':fidx,
             'same_index':pidx==fidx,
             'same_metric':(pidx in p.widths and fidx in f.widths and p.widths[pidx]==f.widths[fidx]) if pidx is not None else (cp in b.mapping),
             'same_bitmap':(glyph_cell_tuple(p,pa,pidx)==glyph_cell_tuple(f,fa,fidx)) if pidx is not None else False}
        tr_rows.append(row)

    return {
      'font':base_path.name,
      'base_sha256':hashlib.sha256(b.data).hexdigest(),
      'user_sha256':hashlib.sha256(p.data).hexdigest(),
      'final_sha256':hashlib.sha256(out).hexdigest(),
      'final_size':len(out),
      'block_count':f.block_count,
      'cwdh_sections':len(f.cwdh_ranges),
      'cmap_sections':1,
      'user_mapping_count':len(p.mapping),
      'final_mapping_count':len(f.mapping),
      'all_user_mappings_same_index':True,
      'all_user_turkish_bitmaps_preserved':all(r['same_index'] and r['same_bitmap'] for r in tr_rows if r['user_index'] is not None),
      'restored_original_codepoints':[{'char':chr(cp),'codepoint':f'U+{cp:04X}','old_base_index':b.mapping[cp],'new_index':target_for[cp]} for cp in missing_original],
      'restored_accidental_user_glyphs':[{'char':chr(cp),'codepoint':f'U+{cp:04X}','index':idx} for cp,idx in restored_accidental],
      'restored_missing_cwdh_indices':restored_missing_width,
      'capacity':cap,
      'max_final_index':max(f.mapping.values()),
      'turkish_rows':tr_rows,
    }


def main():
    ap=argparse.ArgumentParser(description='Build WarioWare 3DS Turkish BFFNTs while preserving the user patch Turkish glyph indices/bitmaps exactly.')
    ap.add_argument('base_dir',type=Path)
    ap.add_argument('user_patch_dir',type=Path)
    ap.add_argument('out_dir',type=Path)
    a=ap.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    reports=[]
    for n in NAMES:
        reports.append(build_one(a.base_dir/n,a.user_patch_dir/n,a.out_dir/n))
    (a.out_dir/'font_v5_build_report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
    with (a.out_dir/'turkish_preservation_v5.csv').open('w',encoding='utf-8-sig',newline='') as h:
        fields=['Font','Character','Codepoint','User_Index','Final_Index','Same_Index','Same_Metric','Same_Bitmap']
        w=csv.DictWriter(h,fieldnames=fields);w.writeheader()
        for rep in reports:
            for r in rep['turkish_rows']:
                w.writerow({'Font':rep['font'],'Character':r['char'],'Codepoint':r['codepoint'],'User_Index':r['user_index'],'Final_Index':r['final_index'],'Same_Index':'EVET' if r['same_index'] else 'HAYIR','Same_Metric':'EVET' if r['same_metric'] else 'HAYIR','Same_Bitmap':'EVET' if r['same_bitmap'] else 'HAYIR'})
    print(json.dumps(reports,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
