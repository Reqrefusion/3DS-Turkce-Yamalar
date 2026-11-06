#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import struct, hashlib
from bravely_ui_tools import (
    DarcArchive, cfnt_char_map, _sheet_to_bitmap_la4, _bitmap_to_sheet_la4, _alpha, _put_max
)

TR_CHARS=('Ğ','ğ','İ','ı','Ş','ş')


def _sections(d: bytes):
    hdr=struct.unpack_from('<H',d,6)[0]
    off=hdr; out=[]
    while off+8<=len(d):
        m=d[off:off+4]; sz=struct.unpack_from('<I',d,off+4)[0]
        if sz<8 or off+sz>len(d):
            break
        out.append((m,off,sz)); off+=sz
    return out


def _row_groups(cell):
    rows=[any(_alpha(v)>0 for v in row) for row in cell]
    groups=[]; s=None
    for i,on in enumerate(rows+[False]):
        if on and s is None: s=i
        elif not on and s is not None:
            groups.append((s,i-1)); s=None
    return groups


def _bbox(cell):
    pts=[(x,y) for y,row in enumerate(cell) for x,v in enumerate(row) if _alpha(v)>0]
    if not pts: return (0,0,len(cell[0])-1,len(cell)-1)
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return min(xs),min(ys),max(xs),max(ys)


def patch_cfnt_turkish_generic(cfnt: bytes):
    """Add Ğ ğ İ ı Ş ş to Bravely Default CFNT.

    Supports both known western fonts in this title:
      * Graphics/UI_en/Font/Font  -> 14x14 cells, 256x256 LA4 sheets
      * Graphics/UI/Font/Font     -> 17x17 cells, 128x128 LA4 sheets

    The new glyph slots are appended inside existing spare TGLP cells, while new
    CWDH and CMAP blocks are appended to the linked chains. Source glyph indices
    are resolved from the font's own Unicode CMAP instead of hard-coded values.
    """
    if cfnt[:4]!=b'CFNT': raise ValueError('Not CFNT')
    d=bytearray(cfnt); secs=_sections(cfnt)
    tglp=next(x for x in secs if x[0]==b'TGLP')[1]
    cwdhs=[x for x in secs if x[0]==b'CWDH']
    cmaps=[x for x in secs if x[0]==b'CMAP']
    if not cwdhs or not cmaps: raise ValueError('Missing CWDH/CMAP')
    # This title uses one physical CWDH before our appended extension.
    cwdh=cwdhs[-1][1]
    cellw,cellh,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,tglp+8)
    if fmt!=9: raise ValueError(f'Expected LA4 font, got format {fmt}')
    if sw%8 or sh%8: raise ValueError(f'Unexpected sheet size {sw}x{sh}')
    cap=sheetcount*cols*rows
    start0=struct.unpack_from('<H',d,cwdh+8)[0]
    endidx=struct.unpack_from('<H',d,cwdh+0x0a)[0]
    if endidx+6>=cap: raise ValueError(f'Not enough spare glyph slots: end={endidx} cap={cap}')
    new_indices=list(range(endidx+1,endidx+7))

    cmap0=cfnt_char_map(bytes(d))
    required=('G','g','I','i','S','s','C','c','Ç','ç')
    missing=[ch for ch in required if ch not in cmap0]
    if missing: raise ValueError(f'Missing source glyphs: {missing}')
    src={ch:cmap0[ch] for ch in required}

    cache={}
    def bitmap(si):
        if si not in cache:
            s=sheetoff+si*sheetsize
            cache[si]=_sheet_to_bitmap_la4(bytes(d[s:s+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows)
        x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        return [[b[(y0+y)*sw+x0+x] for x in range(cellw)] for y in range(cellh)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows)
        x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        for y in range(cellh):
            for x in range(cellw): b[(y0+y)*sw+x0+x]=c[y][x]

    # Ğ / ğ: preserve base G/g and draw a compact breve in the free rows above.
    GG=getcell(src['G']); gg=getcell(src['g'])
    for c in (GG,gg):
        minx,miny,maxx,maxy=_bbox(c); cx=(minx+maxx)//2
        # Three-row U-shaped breve, fitted above the base glyph.
        y2=max(0,miny-1); y1=max(0,y2-1); y0=max(0,y1-1)
        dx=max(2,min(3,(maxx-minx)//4))
        _put_max(c,y0,cx-dx,0xfa); _put_max(c,y0,cx+dx,0xfa)
        _put_max(c,y1,cx-dx+1,0xff); _put_max(c,y1,cx+dx-1,0xff)
        _put_max(c,y2,cx-1,0xff); _put_max(c,y2,cx,0xff)

    # İ: uppercase I plus the dot component from lowercase i, centered over I.
    Id=getcell(src['I']); i_src=getcell(src['i'])
    groups=_row_groups(i_src)
    if len(groups)>=2:
        ds,de=groups[0]
        dot_pts=[(x,y,i_src[y][x]) for y in range(ds,de+1) for x in range(cellw) if _alpha(i_src[y][x])>0]
    else:
        dot_pts=[]
    ix0,iy0,ix1,iy1=_bbox(Id); icx=(ix0+ix1)//2
    if dot_pts:
        dx0=min(x for x,y,v in dot_pts); dx1=max(x for x,y,v in dot_pts); dcx=(dx0+dx1)//2
        target_bottom=max(0,iy0-2)
        source_bottom=max(y for x,y,v in dot_pts)
        yshift=target_bottom-source_bottom
        xshift=icx-dcx
        for x,y,v in dot_pts: _put_max(Id,y+yshift,x+xshift,v)
    else:
        _put_max(Id,max(0,iy0-2),icx,0xff)

    # ı: lowercase i without its detached dot component.
    dotless=getcell(src['i']); groups=_row_groups(dotless)
    if len(groups)>=2:
        ds,de=groups[0]
        for y in range(ds,de+1):
            for x in range(cellw): dotless[y][x]=0xf0
    else:
        # conservative fallback: clear only rows above the body top
        minx,miny,maxx,maxy=_bbox(dotless)
        for y in range(0,max(0,miny+2)):
            for x in range(cellw): dotless[y][x]=0xf0

    # Ş / ş: copy the cedilla pixels from the font's own Ç/ç below baseline.
    SS=getcell(src['S']); ss=getcell(src['s'])
    Cced=getcell(src['Ç']); cced=getcell(src['ç'])
    # Keep only the descender zone; this avoids copying any C-shape antialiasing.
    for out,accent in ((SS,Cced),(ss,cced)):
        for y in range(min(cellh,baseline+1),cellh):
            for x in range(cellw):
                if _alpha(accent[y][x])>0: _put_max(out,y,x,accent[y][x])

    cells=[GG,gg,Id,dotless,SS,ss]
    for idx,c in zip(new_indices,cells): setcell(idx,c)
    for si,bmp in cache.items():
        s=sheetoff+si*sheetsize; d[s:s+sheetsize]=_bitmap_to_sheet_la4(bmp,sw,sh)

    # Width triples from corresponding base glyphs. Search the linked CWDH ranges.
    width_by_glyph={}
    for _,coff,csz in cwdhs:
        st,en,nxt=struct.unpack_from('<HHI',d,coff+8)
        for gi in range(st,en+1):
            p=coff+0x10+(gi-st)*3
            if p+3<=coff+csz: width_by_glyph[gi]=bytes(d[p:p+3])
    base_widths=[src['G'],src['g'],src['I'],src['i'],src['S'],src['s']]
    if any(x not in width_by_glyph for x in base_widths): raise ValueError('Missing base widths')

    new_cwdh_off=len(d)
    cw=bytearray(b'CWDH'+b'\0\0\0\0')
    cw.extend(struct.pack('<HHI',new_indices[0],new_indices[-1],0))
    for bi in base_widths: cw.extend(width_by_glyph[bi])
    while len(cw)%4: cw.append(0)
    struct.pack_into('<I',cw,4,len(cw)); d.extend(cw)

    new_cmap_off=len(d)
    pairs=list(zip((0x011e,0x011f,0x0130,0x0131,0x015e,0x015f),new_indices))
    cm=bytearray(b'CMAP'+b'\0\0\0\0')
    cm.extend(struct.pack('<HHII',min(cp for cp,_ in pairs),max(cp for cp,_ in pairs),2,0))
    cm.extend(struct.pack('<H',len(pairs)))
    for cp,gi in pairs: cm.extend(struct.pack('<HH',cp,gi))
    while len(cm)%4: cm.append(0)
    struct.pack_into('<I',cm,4,len(cm)); d.extend(cm)

    # Link extension onto the active chains. CFNT pointers point 8 bytes into sections.
    last_cwdh=cwdhs[-1][1]; last_cmap=cmaps[-1][1]
    struct.pack_into('<I',d,last_cwdh+0x0c,new_cwdh_off+8)
    struct.pack_into('<I',d,last_cmap+0x10,new_cmap_off+8)
    struct.pack_into('<I',d,0x0c,len(d))
    oldcnt=struct.unpack_from('<I',d,0x10)[0]
    struct.pack_into('<I',d,0x10,oldcnt+2)

    out=bytes(d)
    return out, {
        'added':dict(zip(TR_CHARS,new_indices)), 'new_size':len(out),'sections':oldcnt+2,
        'cell':[cellw,cellh], 'sheet':[sw,sh], 'sheet_count':sheetcount,
        'capacity':cap, 'base_end_glyph':endidx,
    }


def active_cmap_map(cfnt: bytes):
    """Follow FINF->CMAP->next exactly as the 3DS renderer does."""
    if cfnt[:4]!=b'CFNT': raise ValueError('Not CFNT')
    hs=struct.unpack_from('<H',cfnt,6)[0]
    if cfnt[hs:hs+4]!=b'FINF': raise ValueError('Missing FINF')
    cmap_ptr=struct.unpack_from('<I',cfnt,hs+0x18)[0]
    out={}; chain=[]; seen=set()
    while cmap_ptr:
        off=cmap_ptr-8
        if off in seen: raise ValueError('CMAP loop')
        seen.add(off)
        if cfnt[off:off+4]!=b'CMAP': raise ValueError(f'Bad CMAP pointer {cmap_ptr:#x}')
        sz=struct.unpack_from('<I',cfnt,off+4)[0]
        st,en,method,res,nxt=struct.unpack_from('<4HI',cfnt,off+8)
        p=off+0x14
        if method==0:
            base=struct.unpack_from('<H',cfnt,p)[0]
            for cp in range(st,en+1): out[chr(cp)]=base+(cp-st)
        elif method==1:
            for cp in range(st,en+1):
                gi=struct.unpack_from('<H',cfnt,p+2*(cp-st))[0]
                if gi!=0xffff: out[chr(cp)]=gi
        elif method==2:
            n=struct.unpack_from('<H',cfnt,p)[0]; p+=2
            for _ in range(n):
                cp,gi=struct.unpack_from('<HH',cfnt,p); p+=4; out[chr(cp)]=gi
        else: raise ValueError(f'Unknown CMAP method {method}')
        chain.append({'offset':off,'size':sz,'start':st,'end':en,'method':method,'next':nxt})
        cmap_ptr=nxt
    return out,chain


def verify_font_archive(outer: bytes):
    arc=DarcArchive(outer)
    found=[]
    for ip,b in arc.files():
        if b[:4]!=b'CFNT': continue
        cmap,chain=active_cmap_map(b)
        tr={ch:cmap.get(ch) for ch in TR_CHARS}
        if any(v is None for v in tr.values()): raise ValueError(f'Missing Turkish CMAP in {ip}: {tr}')
        # Verify every mapped glyph falls inside TGLP capacity and has visible alpha.
        secs=_sections(b); tglp=next(x for x in secs if x[0]==b'TGLP')[1]
        cellw,cellh,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',b,tglp+8)
        cap=sheetcount*cols*rows; cache={}; vis={}
        for ch,gi in tr.items():
            if not (0<=gi<cap): raise ValueError(f'{ch} glyph {gi} outside capacity {cap}')
            si=gi//(cols*rows); rem=gi%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1)
            if si not in cache:
                s=sheetoff+si*sheetsize; cache[si]=_sheet_to_bitmap_la4(b[s:s+sheetsize],sw,sh)
            bmp=cache[si]
            count=sum(1 for y in range(cellh) for x in range(cellw) if _alpha(bmp[(y0+y)*sw+x0+x])>0)
            if count==0: raise ValueError(f'{ch} glyph {gi} is blank')
            vis[ch]=count
        found.append({'internal_path':ip,'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'turkish_map':tr,'visible_pixels':vis,'cmap_chain_length':len(chain),'cell':[cellw,cellh],'sheet':[sw,sh],'capacity':cap})
    if not found: raise ValueError('No CFNT in DARC')
    return {'outer_sha256':hashlib.sha256(outer).hexdigest(),'outer_size':len(outer),'fonts':found}


def patch_font_archive(outer: bytes):
    arc=DarcArchive(outer); repl={}; infos=[]
    for ip,b in arc.files():
        if b[:4]==b'CFNT':
            nb,info=patch_cfnt_turkish_generic(b); repl[ip]=nb; infos.append({'internal_path':ip,**info})
    if not repl: raise ValueError('No CFNT in DARC')
    out=arc.rebuild(repl)
    verify=verify_font_archive(out)
    return out, {'patched':infos,'verification':verify}
