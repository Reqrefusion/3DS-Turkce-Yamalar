#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct, json, math


def align(v,a): return (v+a-1)//a*a

def read_utf16z(data: bytes, pos: int) -> str:
    chars=[]
    while pos+2<=len(data):
        c=struct.unpack_from('<H',data,pos)[0]; pos+=2
        if c==0: break
        chars.append(chr(c))
    return ''.join(chars)

@dataclass
class DarcNode:
    index:int; is_dir:bool; name:str; a:int; b:int; path:str

class DarcArchive:
    def __init__(self,data:bytes):
        if data[:4]!=b'darc': raise ValueError('Not DARC')
        self.data=data
        self.bom,self.header_size,self.version,self.file_size,self.ftoff,self.ftlen,self.dataoff=struct.unpack_from('<HHIIIII',data,4)
        root_w,root_a,root_b=struct.unpack_from('<III',data,self.ftoff)
        self.count=root_b
        self.namesoff=self.ftoff+self.count*12
        raw=[]
        for i in range(self.count):
            w,a,b=struct.unpack_from('<III',data,self.ftoff+i*12)
            raw.append((bool(w&0x01000000),read_utf16z(data,self.namesoff+(w&0xffffff)),a,b))
        nodes=[]; stack=[(raw[0][3],'')]
        nodes.append(DarcNode(0,True,raw[0][1],raw[0][2],raw[0][3],''))
        for i,(isdir,name,a,b) in enumerate(raw[1:],1):
            while stack and i>=stack[-1][0]: stack.pop()
            parent=stack[-1][1] if stack else ''
            path=(parent+'/'+name).strip('/')
            nodes.append(DarcNode(i,isdir,name,a,b,path))
            if isdir: stack.append((b,path))
        self.nodes=nodes

    def files(self):
        for n in self.nodes:
            if not n.is_dir:
                yield n.path,self.data[n.a:n.a+n.b]

    def rebuild(self,replacements:dict[str,bytes]) -> bytes:
        prefix=bytearray(self.data[:self.dataoff])
        out=bytearray(prefix)
        cursor=self.dataoff
        prev_old_end=self.dataoff
        # preserve/recreate original spacing behavior; 0x80-aligned starts stay aligned
        for n in self.nodes:
            if n.is_dir: continue
            old_gap=max(0,n.a-prev_old_end)
            if old_gap and n.a%0x80==0 and n.a==align(prev_old_end,0x80):
                target=align(cursor,0x80)
                if target>cursor: out.extend(b'\0'*(target-cursor)); cursor=target
            elif old_gap:
                # preserve non-alignment gap bytes (normally zero)
                gapbytes=self.data[prev_old_end:n.a]
                out.extend(gapbytes); cursor+=len(gapbytes)
            payload=replacements.get(n.path,self.data[n.a:n.a+n.b])
            newoff=cursor
            out.extend(payload); cursor+=len(payload)
            struct.pack_into('<II',out,self.ftoff+n.index*12+4,newoff,len(payload))
            prev_old_end=n.a+n.b
        struct.pack_into('<I',out,0x0c,len(out))
        return bytes(out)


def bclyt_entries(data:bytes):
    if data[:4]!=b'CLYT': return []
    off=struct.unpack_from('<H',data,6)[0]
    entries=[]; txtn=0
    while off+8<=len(data):
        magic=data[off:off+4]
        sz=struct.unpack_from('<I',data,off+4)[0]
        if sz<8 or off+sz>len(data): break
        if magic==b'txt1' and sz>=0x74:
            pane=data[off+0x0c:off+0x1c].split(b'\0',1)[0].decode('ascii','replace')
            to=struct.unpack_from('<I',data,off+0x58)[0]
            text=read_utf16z(data,off+to) if 0<to<sz else ''
            x,y,z=struct.unpack_from('<fff',data,off+0x24)
            width,height=struct.unpack_from('<ff',data,off+0x44)
            font_x,font_y=struct.unpack_from('<ff',data,off+0x64)
            entries.append({
                'section_offset':off,'section_size':sz,'pane':pane,'ordinal':txtn,
                'text_offset':to,'text':text,'x':x,'y':y,'z':z,'width':width,'height':height,
                'font_x':font_x,'font_y':font_y,'align_flags':bytes(data[off+0x54:off+0x58]),
                'section_prefix':bytes(data[off:off+min(sz,0x74)])
            })
            txtn+=1
        off+=sz
    return entries


def _copy_txt1_geometry(sec:bytearray, donor:bytes):
    """Copy only layout geometry/alignment fields from a same-pane localized donor txt1.
    Material/font IDs and text buffers remain from the English source.
    """
    if donor[:4]!=b'txt1' or len(donor)<0x74 or len(sec)<0x74: return
    # Keep visibility/name/user data. Copy position/rotation/scale/box dimensions.
    sec[0x24:0x4c]=donor[0x24:0x4c]
    # Copy line/origin alignment flags, but preserve material/font IDs at 0x50-0x53.
    sec[0x54:0x58]=donor[0x54:0x58]
    # Copy font size and spacing.
    sec[0x64:0x74]=donor[0x64:0x74]


def patch_bclyt(data:bytes, translate, context='', donors=None, width_fn=None, fit_margin=0.96):
    """Patch Bravely Default CLYT txt1 strings.

    translate(text,pane,ordinal,context)->new_text or None
    donors: optional dict[(pane, ordinal)] -> list of txt1 section bytes from other western locales.
    width_fn: optional callable(text)->advance width at the font's native size. If provided,
              font X size is reduced only when translated text would exceed the chosen pane width.

    Important Bravely txt1 offsets (this title's CLYT revision):
      0x44/0x48 = pane width/height (float)
      0x4C/0x4E = text byte length / buffer byte length
      0x58      = text offset
      0x64/0x68 = font X/Y size
    """
    if data[:4]!=b'CLYT': return data,[]
    hdrsz=struct.unpack_from('<H',data,6)[0]
    out=bytearray(data[:hdrsz]); off=hdrsz; changes=[]; txtn=0
    donors=donors or {}
    while off+8<=len(data):
        magic=data[off:off+4]; sz=struct.unpack_from('<I',data,off+4)[0]
        if sz<8 or off+sz>len(data):
            out.extend(data[off:]); break
        sec=bytearray(data[off:off+sz])
        if magic==b'txt1' and sz>=0x74:
            pane=sec[0x0c:0x1c].split(b'\0',1)[0].decode('ascii','replace')
            to=struct.unpack_from('<I',sec,0x58)[0]
            old=read_utf16z(sec,to) if 0<to<len(sec) else ''
            new=translate(old,pane,txtn,context)
            if new is not None and new!=old:
                # Prefer a professionally localized western geometry when one exists.
                dlist=donors.get((pane,txtn),[])
                if dlist:
                    # The widest donor pane is generally the safest for Turkish while retaining
                    # the game's own localized alignment/position decisions.
                    donor=max(dlist,key=lambda d: struct.unpack_from('<f',d,0x44)[0] if len(d)>=0x48 else 0.0)
                    _copy_txt1_geometry(sec,donor)
                enc=new.encode('utf-16le')+b'\0\0'
                # Correct text length fields. v3.1 mistakenly wrote these at 0x48, corrupting
                # the pane height; Bravely stores them at 0x4C/0x4E.
                struct.pack_into('<HH',sec,0x4c,len(enc),len(enc))
                # Optional horizontal fit guard. Preserve vertical size and alignment.
                fit_scale=1.0
                if width_fn is not None:
                    try:
                        pane_w=struct.unpack_from('<f',sec,0x44)[0]
                        font_x=struct.unpack_from('<f',sec,0x64)[0]
                        native=width_fn(new)
                        # CFNT advances are in approximately native 14px units for this font.
                        rendered=native*(font_x/14.0)
                        limit=max(1.0,pane_w*fit_margin)
                        if rendered>limit and rendered>0:
                            fit_scale=max(0.72,limit/rendered)
                            struct.pack_into('<f',sec,0x64,font_x*fit_scale)
                    except Exception:
                        fit_scale=1.0
                # text begins at declared offset; preserve prefix, replace tail, 4-byte align section
                sec=sec[:to]+enc
                while len(sec)%4: sec.append(0)
                struct.pack_into('<I',sec,4,len(sec))
                changes.append({
                    'context':context,'pane':pane,'ordinal':txtn,'old':old,'new':new,
                    'pane_width':struct.unpack_from('<f',sec,0x44)[0],
                    'pane_height':struct.unpack_from('<f',sec,0x48)[0],
                    'font_x':struct.unpack_from('<f',sec,0x64)[0],
                    'font_y':struct.unpack_from('<f',sec,0x68)[0],
                    'fit_scale':fit_scale,'used_localized_geometry':bool(dlist)
                })
            txtn+=1
        out.extend(sec); off+=sz
    struct.pack_into('<I',out,0x0c,len(out))
    return bytes(out),changes

# ---- CFNT helpers ----

def _sheet_to_bitmap_la4(raw:bytes,width=256,height=256):
    bmp=bytearray(width*height)
    for tile_y in range(height//8):
      for tile_x in range(width//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tile_x*8
             py=y3+y2*2+y*4+tile_y*8
             dx=x3+x2*4+x*16+tile_x*64
             dy=y3*2+y2*8+y*32+tile_y*width*8
             bmp[px+py*width]=raw[dx+dy]
    return bmp

def _bitmap_to_sheet_la4(bmp:bytes,width=256,height=256):
    raw=bytearray(width*height)
    for tile_y in range(height//8):
      for tile_x in range(width//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tile_x*8
             py=y3+y2*2+y*4+tile_y*8
             dx=x3+x2*4+x*16+tile_x*64
             dy=y3*2+y2*8+y*32+tile_y*width*8
             raw[dx+dy]=bmp[px+py*width]
    return bytes(raw)

def _alpha(v): return v & 0x0f

def _put_max(cell,y,x,val):
    if 0<=y<len(cell) and 0<=x<len(cell[0]) and _alpha(val)>_alpha(cell[y][x]):
        cell[y][x]=val

def patch_cfnt_turkish(cfnt:bytes):
    if cfnt[:4]!=b'CFNT': raise ValueError('Not CFNT')
    d=bytearray(cfnt)
    # sections
    hdrsz=struct.unpack_from('<H',d,6)[0]; off=hdrsz; secs=[]
    while off+8<=len(d):
        m=d[off:off+4]; sz=struct.unpack_from('<I',d,off+4)[0]
        secs.append((m,off,sz)); off+=sz
    tglp=next(x for x in secs if x[0]==b'TGLP')[1]
    cwdh=next(x for x in secs if x[0]==b'CWDH')[1]
    cmaps=[x for x in secs if x[0]==b'CMAP']
    cellw,cellh,baseline,maxw,sheetsize,sheetcount,fmt,cols,rows,sw,sh,sheetoff=struct.unpack_from('<BBBBIHHHHHHI',d,tglp+8)
    if fmt!=9 or (sw,sh)!=(256,256): raise ValueError('Expected LA4 256x256 CFNT')
    cap=sheetcount*cols*rows
    endidx=struct.unpack_from('<H',d,cwdh+0x0a)[0]
    needed=6
    if endidx+needed>=cap: raise ValueError('Not enough spare glyph slots')
    new_indices=list(range(endidx+1,endidx+1+needed))
    # decode only sheets touched/source; cache
    cache={}
    def bitmap(si):
        if si not in cache:
            s=sheetoff+si*sheetsize
            cache[si]=_sheet_to_bitmap_la4(bytes(d[s:s+sheetsize]),sw,sh)
        return cache[si]
    def getcell(idx):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        return [[b[(y0+y)*sw+x0+x] for x in range(cellw)] for y in range(cellh)]
    def setcell(idx,c):
        si=idx//(cols*rows); rem=idx%(cols*rows); x0=(rem%cols)*(cellw+1); y0=(rem//cols)*(cellh+1); b=bitmap(si)
        for y in range(cellh):
            for x in range(cellw): b[(y0+y)*sw+x0+x]=c[y][x]
    # Resolve source glyphs through the font's own CMAP instead of hard-coded
    # glyph indices. The western font revisions do not guarantee identical glyph
    # numbering, so source glyphs are resolved dynamically from CMAP.
    cmap0=cfnt_char_map(bytes(d))
    required=('G','g','I','i','S','s','Ç','ç')
    missing=[ch for ch in required if ch not in cmap0]
    if missing: raise ValueError(f'Missing source glyphs in CFNT: {missing}')
    src={ch:cmap0[ch] for ch in required}
    # Ş: base S + cedilla bottom two rows from Ç
    S=getcell(src['S']); Cc=getcell(src['Ç'])
    for y in (12,13):
        for x in range(cellw): _put_max(S,y,x,Cc[y][x])
    ss=getcell(src['s']); cc=getcell(src['ç'])
    for y in (12,13):
        for x in range(cellw): _put_max(ss,y,x,cc[y][x])
    # İ: I + dot above; dot style copied from lowercase i
    Id=getcell(src['I']); ii=getcell(src['i'])
    dotvals=[v for v in ii[4] if _alpha(v)>0]
    v=max(dotvals,key=_alpha) if dotvals else 0xff
    _put_max(Id,2,2,v); _put_max(Id,2,3,v)
    # ı: lowercase i without its dot
    dotless=getcell(src['i'])
    for y in range(0,6):
        for x in range(cellw): dotless[y][x]=0xf0
    # Ğ/ğ: base + compact breve above (anti-alias friendly LA4 values)
    GG=getcell(src['G']); gg=getcell(src['g'])
    for c in (GG,gg):
        _put_max(c,2,3,0xfa); _put_max(c,2,6,0xfa)
        _put_max(c,3,4,0xff); _put_max(c,3,5,0xff)
    # Unicode order and glyph order: Ğ,ğ,İ,ı,Ş,ş
    cells=[GG,gg,Id,dotless,S,ss]
    for idx,c in zip(new_indices,cells): setcell(idx,c)
    # write modified sheets
    for si,b in cache.items():
        s=sheetoff+si*sheetsize; d[s:s+sheetsize]=_bitmap_to_sheet_la4(b,sw,sh)
    # copy width triples from base glyphs
    start0=struct.unpack_from('<H',d,cwdh+8)[0]
    triples=d[cwdh+0x10:cwdh+0x10+(endidx-start0+1)*3]
    def width_trip(idx):
        p=(idx-start0)*3; return bytes(triples[p:p+3])
    base_widths=[src['G'],src['g'],src['I'],src['i'],src['S'],src['s']]
    # append CWDH and CMAP at EOF, preserve old sections exactly
    new_cwdh_off=len(d)
    cw=bytearray(b'CWDH'+b'\0\0\0\0')
    cw.extend(struct.pack('<HHI',new_indices[0],new_indices[-1],0))
    for bi in base_widths: cw.extend(width_trip(bi))
    while len(cw)%4: cw.append(0)
    struct.pack_into('<I',cw,4,len(cw))
    d.extend(cw)
    new_cmap_off=len(d)
    pairs=[(0x011e,new_indices[0]),(0x011f,new_indices[1]),(0x0130,new_indices[2]),(0x0131,new_indices[3]),(0x015e,new_indices[4]),(0x015f,new_indices[5])]
    cm=bytearray(b'CMAP'+b'\0\0\0\0')
    cm.extend(struct.pack('<HHII',min(x for x,_ in pairs),max(x for x,_ in pairs),2,0))
    cm.extend(struct.pack('<H',len(pairs)))
    for cp,gi in pairs: cm.extend(struct.pack('<HH',cp,gi))
    while len(cm)%4: cm.append(0)
    struct.pack_into('<I',cm,4,len(cm)); d.extend(cm)
    # link old final sections. Pointers point 8 bytes into target section.
    struct.pack_into('<I',d,cwdh+0x0c,new_cwdh_off+8)
    last_cmap=cmaps[-1][1]
    struct.pack_into('<I',d,last_cmap+0x10,new_cmap_off+8)
    # header size/count
    struct.pack_into('<I',d,0x0c,len(d))
    oldcnt=struct.unpack_from('<I',d,0x10)[0]
    struct.pack_into('<I',d,0x10,oldcnt+2)
    return bytes(d), {'added':dict(zip(['Ğ','ğ','İ','ı','Ş','ş'],new_indices)),'new_size':len(d),'sections':oldcnt+2}


def cfnt_char_map(data:bytes):
    """Return char->glyph index for validation."""
    out={}; hdr=struct.unpack_from('<H',data,6)[0]; off=hdr
    while off+8<=len(data):
        m=data[off:off+4]; sz=struct.unpack_from('<I',data,off+4)[0]
        if m==b'CMAP':
            st,en,method,nxt=struct.unpack_from('<HHII',data,off+8)
            p=off+0x14
            if method==0:
                base=struct.unpack_from('<H',data,p)[0]
                for cp in range(st,en+1): out[chr(cp)]=base+(cp-st)
            elif method==1:
                for cp in range(st,en+1):
                    gi=struct.unpack_from('<H',data,p+2*(cp-st))[0]
                    if gi!=0xffff: out[chr(cp)]=gi
            elif method==2:
                n=struct.unpack_from('<H',data,p)[0]; p+=2
                for _ in range(n):
                    cp,gi=struct.unpack_from('<HH',data,p);p+=4;out[chr(cp)]=gi
        if sz<8: break
        off+=sz
    return out

def cfnt_advance_map(data:bytes):
    """Return char->advance width from CFNT CWDH/CMAP tables."""
    cmap=cfnt_char_map(data)
    widths={}
    hdr=struct.unpack_from('<H',data,6)[0]; off=hdr
    while off+8<=len(data):
        m=data[off:off+4]; sz=struct.unpack_from('<I',data,off+4)[0]
        if sz<8 or off+sz>len(data): break
        if m==b'CWDH' and sz>=0x10:
            st,en,nxt=struct.unpack_from('<HHI',data,off+8)
            for gi in range(st,en+1):
                p=off+0x10+(gi-st)*3
                if p+3<=off+sz:
                    left,glyph,advance=struct.unpack_from('<bBB',data,p)
                    widths[gi]=advance
        off+=sz
    return {ch:widths.get(gi,8) for ch,gi in cmap.items()}


def make_text_width_fn(cfnt:bytes):
    adv=cfnt_advance_map(cfnt)
    default=adv.get('W',10)
    def width(text:str):
        lines=text.split('\n') or ['']
        return max(sum(adv.get(ch,default) for ch in line) for line in lines)
    return width
