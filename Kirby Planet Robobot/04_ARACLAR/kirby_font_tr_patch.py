from __future__ import annotations
import struct, math, csv, re
from pathlib import Path
from collections import defaultdict, deque

TR_CHARS='ÇĞİÖŞÜçğıöşü'
BASE_FOR={'Ç':'C','Ğ':'G','İ':'I','Ö':'O','Ş':'S','Ü':'U','ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u'}

class FontError(Exception): pass

# LZ11 copied from local toolkit implementation (own code)
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
                b1=data[pos]; pos+=1; hi=b1>>4
                if hi==0:
                    b2,b3=data[pos],data[pos+1]; pos+=2
                    length=(((b1&0xF)<<4)|(b2>>4))+0x11; disp=(((b2&0xF)<<8)|b3)+1
                elif hi==1:
                    b2,b3,b4=data[pos],data[pos+1],data[pos+2]; pos+=3
                    length=(((b1&0xF)<<12)|(b2<<4)|(b3>>4))+0x111; disp=(((b3&0xF)<<8)|b4)+1
                else:
                    b2=data[pos]; pos+=1; length=hi+1; disp=(((b1&0xF)<<8)|b2)+1
                if disp>len(out): raise FontError('LZ11 mesafe bozuk')
                for _ in range(length):
                    out.append(out[-disp])
                    if len(out)>=size: break
            else:
                out.append(data[pos]); pos+=1
    return bytes(out)

def _encode_ref(length:int, disp:int)->bytes:
    d=disp-1
    if 3<=length<=0x10: return bytes([((length-1)<<4)|((d>>8)&0xF),d&0xFF])
    if 0x11<=length<=0x110:
        v=length-0x11; return bytes([(v>>4)&0xF,((v&0xF)<<4)|((d>>8)&0xF),d&0xFF])
    v=length-0x111; return bytes([0x10|((v>>12)&0xF),(v>>4)&0xFF,((v&0xF)<<4)|((d>>8)&0xF),d&0xFF])

def lz11_compress(data: bytes)->bytes:
    n=len(data); out=bytearray([0x11])+bytearray(n.to_bytes(3,'little')) if n<0x1000000 else bytearray([0x11,0,0,0])+bytearray(n.to_bytes(4,'little'))
    buckets=defaultdict(deque); pos=0
    while pos<n:
        fp=len(out); out.append(0); flags=0
        for bit in range(8):
            if pos>=n: break
            best_len=best_disp=0
            if pos+2<n:
                key=data[pos:pos+3]; dq=buckets[key]
                while dq and pos-dq[0]>0x1000: dq.popleft()
                for cand in reversed(list(dq)[-96:]):
                    disp=pos-cand; maxlen=min(0x10110,n-pos); l=3
                    while l<maxlen and data[cand+l]==data[pos+l]: l+=1
                    if l>best_len: best_len,best_disp=l,disp
                    if l==maxlen: break
            if best_len>=3:
                flags|=0x80>>bit; out+=_encode_ref(best_len,best_disp); adv=best_len
            else: out.append(data[pos]); adv=1
            end=min(n-2,pos+adv)
            for q in range(pos,end):
                dq=buckets[data[q:q+3]]; dq.append(q)
                while dq and q-dq[0]>0x1000: dq.popleft()
            pos+=adv
        out[fp]=flags
    while len(out)%4: out.append(0)
    return bytes(out)

class BCFNT:
    def __init__(self, data: bytes):
        if data.startswith(b'\x11'): data=lz11_decompress(data)
        self.raw=bytearray(data)
        if self.raw[:4] not in (b'CFNT',b'CFNU'): raise FontError('CFNT/CFNU değil')
        bom=bytes(self.raw[4:6]); self.order='<' if bom==b'\xff\xfe' else '>' if bom==b'\xfe\xff' else None
        if not self.order: raise FontError('BOM bozuk')
        self._parse()
        self.sheet_cache={}
        self.modified_sheets=set()
    def _parse(self):
        r=self.raw; o=self.order
        self.file_size=struct.unpack_from(o+'I',r,0x0C)[0]; self.section_count=struct.unpack_from(o+'I',r,0x10)[0]
        finf=struct.unpack_from(o+'4sI2BH4B3I4B',r,0x14)
        if finf[0]!=b'FINF': raise FontError('FINF yok')
        self.tglp_off,self.cwdh_off,self.cmap_off=finf[9],finf[10],finf[11]
        self.tpos=self.tglp_off-8
        tg=struct.unpack_from(o+'4sI4BI6HI',r,self.tpos)
        if tg[0]!=b'TGLP': raise FontError('TGLP yok')
        (_,self.tglp_size,self.cell_w,self.cell_h,self.baseline,self.max_char_w,self.sheet_size,self.sheet_count,self.pixel_fmt,self.cols,self.rows,self.sheet_w,self.sheet_h,self.sheet_data_off)=tg
        if self.pixel_fmt not in (9,11): raise FontError(f'Desteklenmeyen texture formatı {self.pixel_fmt}; TR çizici LA4/A4 destekliyor')
        self._parse_cwdh(); self._parse_cmap()
    def _parse_cwdh(self):
        self.width_offsets={}; self.cwdh_sections=[]; p=self.cwdh_off; seen=set(); o=self.order
        while p and p not in seen:
            seen.add(p); pos=p-8
            magic,sz,start,end,nextp=struct.unpack_from(o+'4sI2HI',self.raw,pos)
            if magic!=b'CWDH': raise FontError('CWDH zinciri bozuk')
            self.cwdh_sections.append((pos,sz,start,end,nextp))
            base=pos+0x10
            for idx in range(start,end+1): self.width_offsets[idx]=base+(idx-start)*3
            p=nextp
    def _parse_cmap(self):
        self.mapping={}; self.cmap_sections=[]; p=self.cmap_off; seen=set(); o=self.order
        while p and p not in seen:
            seen.add(p); pos=p-8
            magic,sz,start,end,method,unk,nextp=struct.unpack_from(o+'4sI4HI',self.raw,pos)
            if magic!=b'CMAP': raise FontError('CMAP zinciri bozuk')
            self.cmap_sections.append((pos,sz,start,end,method,unk,nextp)); q=pos+0x14
            if method==0:
                idxoff=struct.unpack_from(o+'H',self.raw,q)[0]
                for c in range(start,end+1): self.mapping[chr(c)]=idxoff+(c-start)
            elif method==1:
                for i,c in enumerate(range(start,end+1)):
                    idx=struct.unpack_from(o+'H',self.raw,q+2*i)[0]
                    if idx!=0xFFFF: self.mapping[chr(c)]=idx
            elif method==2:
                count=struct.unpack_from(o+'H',self.raw,q)[0]
                for i in range(count):
                    c,idx=struct.unpack_from(o+'2H',self.raw,q+2+4*i); self.mapping[chr(c)]=idx
            else: raise FontError(f'CMAP method {method} bilinmiyor')
            p=nextp
    @property
    def capacity(self): return self.sheet_count*self.cols*self.rows
    def _sheet_pixels(self, si):
        if si in self.sheet_cache: return self.sheet_cache[si]
        w,h=self.sheet_w,self.sheet_h; W=1<<(w-1).bit_length(); H=1<<(h-1).bit_length(); fmt=self.pixel_fmt
        start=self.sheet_data_off+si*self.sheet_size; data=self.raw[start:start+self.sheet_size]
        out=[(0,0)]*(W*H)
        for ty in range(H//8):
            for tx in range(W//8):
                for y in range(2):
                    for x in range(2):
                        for y2 in range(2):
                            for x2 in range(2):
                                for y3 in range(2):
                                    for x3 in range(2):
                                        px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
                                        dp=x3+x2*4+x*16+tx*64 + y3*2+y2*8+y*32+ty*W*8
                                        if fmt==11:
                                            b=data[dp//2]; a=(b>>((dp&1)*4))&0xF; v=(15,a)
                                        else:
                                            b=data[dp]; v=((b>>4)&0xF,b&0xF)
                                        out[px+py*W]=v
        crop=[out[x+y*W] for y in range(h) for x in range(w)]
        self.sheet_cache[si]=crop; return crop
    def _encode_sheet(self, pix):
        w,h=self.sheet_w,self.sheet_h; W=1<<(w-1).bit_length(); H=1<<(h-1).bit_length(); fmt=self.pixel_fmt
        pad=[(0,0)]*(W*H)
        for y in range(h): pad[y*W:y*W+w]=pix[y*w:(y+1)*w]
        data=bytearray(self.sheet_size)
        for ty in range(H//8):
            for tx in range(W//8):
                for y in range(2):
                    for x in range(2):
                        for y2 in range(2):
                            for x2 in range(2):
                                for y3 in range(2):
                                    for x3 in range(2):
                                        px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
                                        dp=x3+x2*4+x*16+tx*64 + y3*2+y2*8+y*32+ty*W*8
                                        l,a=pad[px+py*W]
                                        if fmt==11: data[dp//2]|=(a&0xF)<<((dp&1)*4)
                                        else: data[dp]=((l&0xF)<<4)|(a&0xF)
        return bytes(data)
    def glyph_location(self, idx):
        if not (0<=idx<self.capacity): raise FontError(f'Glif index kapasite dışı {idx}/{self.capacity}')
        cps=self.cols*self.rows; si=idx//cps; local=idx%cps; col=local%self.cols; row=local//self.cols
        x=col*(self.cell_w+1)+1; y=row*(self.cell_h+1)+1
        return si,x,y
    def get_cell_idx(self,idx):
        si,x,y=self.glyph_location(idx); sh=self._sheet_pixels(si); w=self.sheet_w
        return [[sh[(y+yy)*w+x+xx] for xx in range(self.cell_w)] for yy in range(self.cell_h)]
    def get_cell(self,ch):
        if ch not in self.mapping: raise FontError(f'{ch!r} fontta yok')
        return self.get_cell_idx(self.mapping[ch])
    def set_cell_idx(self,idx,cell):
        si,x,y=self.glyph_location(idx); sh=self._sheet_pixels(si); w=self.sheet_w
        for yy,row in enumerate(cell):
            for xx,v in enumerate(row): sh[(y+yy)*w+x+xx]=v
        self.modified_sheets.add(si)
    def copy_width(self,src_idx,dst_idx):
        if src_idx not in self.width_offsets or dst_idx not in self.width_offsets: raise FontError('CWDH index yok')
        s=self.width_offsets[src_idx]; d=self.width_offsets[dst_idx]; self.raw[d:d+3]=self.raw[s:s+3]
    def merge_terminal_scan_cmap(self, additions):
        # Runtime-safe strategy for Kirby/CTR font lookup:
        # Keep Turkish entries inside the existing terminal method-2 scan CMAP.
        # Some Nintendo readers stop at a broad 0000-FFFF CMAP even when a codepoint
        # is absent, so appending a later CMAP can look valid in desktop parsers but
        # still fail in-game. The terminal scan CMAP is physically the final section
        # in these fonts, so it can be safely grown without shifting TGLP/CWDH offsets.
        adds={c:i for c,i in additions.items()}
        if not adds: return
        if not self.cmap_sections: raise FontError('CMAP yok')
        term=None
        for sec in self.cmap_sections:
            pos,sz,start,end,method,unk,nextp=sec
            if method==2 and nextp==0:
                term=sec
        if term is None: raise FontError('Terminal method-2 CMAP yok')
        pos,sz,start,end,method,unk,nextp=term
        if pos+sz != len(self.raw):
            raise FontError('Terminal CMAP dosyanın sonunda değil; güvenli büyütme yapılamaz')
        q=pos+0x14
        count=struct.unpack_from(self.order+'H',self.raw,q)[0]
        pairs={}
        for i in range(count):
            cp,idx=struct.unpack_from(self.order+'2H',self.raw,q+2+4*i)
            pairs[cp]=idx
        for ch,idx in adds.items():
            cp=ord(ch)
            if cp>0xFFFF: raise FontError('BMP dışı karakter desteklenmiyor')
            pairs[cp]=idx
        entries=sorted(pairs.items())
        payload=bytearray(struct.pack(self.order+'H',len(entries)))
        for cp,idx in entries:
            payload+=struct.pack(self.order+'2H',cp,idx)
        # Preserve broad bounds when present. Otherwise widen only as needed.
        nstart=min(start,min(cp for cp,_ in entries)); nend=max(end,max(cp for cp,_ in entries))
        nsize=0x14+len(payload)
        sec=struct.pack(self.order+'4sI4HI',b'CMAP',nsize,nstart,nend,2,unk,0)+payload
        self.raw[pos:]=sec
        self.file_size=len(self.raw)
        struct.pack_into(self.order+'I',self.raw,0x0C,self.file_size)
        self.mapping.update(adds)
        self._parse_cmap()

    def runtime_lookup(self, ch):
        # Conservative CTR-style lookup emulator: once a CMAP range claims the
        # codepoint, a miss in that section is treated as a final miss.
        cp=ord(ch); o=self.order
        for pos,sz,start,end,method,unk,nextp in self.cmap_sections:
            if not (start<=cp<=end):
                continue
            q=pos+0x14
            if method==0:
                idxoff=struct.unpack_from(o+'H',self.raw,q)[0]
                return idxoff+(cp-start)
            if method==1:
                idx=struct.unpack_from(o+'H',self.raw,q+2*(cp-start))[0]
                return None if idx==0xFFFF else idx
            if method==2:
                count=struct.unpack_from(o+'H',self.raw,q)[0]
                for i in range(count):
                    c,idx=struct.unpack_from(o+'2H',self.raw,q+2+4*i)
                    if c==cp: return idx
                return None
        return None
    def build(self):
        for si in sorted(self.modified_sheets):
            enc=self._encode_sheet(self.sheet_cache[si]); start=self.sheet_data_off+si*self.sheet_size; self.raw[start:start+self.sheet_size]=enc
        return bytes(self.raw)

def clone(cell): return [row[:] for row in cell]
def blank_like(cell): return [[(0,0) for _ in row] for row in cell]
def bbox(cell, threshold=0):
    pts=[(x,y) for y,row in enumerate(cell) for x,v in enumerate(row) if v[1]>threshold]
    if not pts: return None
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; return min(xs),min(ys),max(xs)+1,max(ys)+1

def components(cell, threshold=0):
    h=len(cell); w=len(cell[0]); on={(x,y) for y in range(h) for x in range(w) if cell[y][x][1]>threshold}; out=[]
    while on:
        start=next(iter(on)); stack=[start]; on.remove(start); comp=[]
        while stack:
            p=stack.pop(); comp.append(p); x,y=p
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==dy==0: continue
                    q=(x+dx,y+dy)
                    if q in on: on.remove(q); stack.append(q)
        out.append(comp)
    return out

def dot_component(cell):
    comps=components(cell,0)
    if len(comps)<2: return []
    # main body tends to be largest; choose component above the main body's top, else smallest upper component
    main=max(comps,key=len); main_top=min(y for x,y in main)
    cands=[c for c in comps if max(y for x,y in c)<main_top+1]
    if not cands: cands=sorted([c for c in comps if c is not main], key=lambda c:(min(y for x,y in c),len(c)))
    return max(cands,key=len) if cands else []

def clear_points(cell, pts):
    out=clone(cell)
    for x,y in pts: out[y][x]=(0,0)
    return out

def xheight_top(font, threshold=0):
    """Estimate lowercase x-height from ordinary undotted lowercase glyphs.

    threshold is alpha threshold (0..15). For v12 dotless-i construction,
    threshold=0 is intentional: the first visible lowercase outline/shadow row
    is part of the authored glyph and must be preserved.
    """
    samples='acem norsuvwxz'.replace(' ','')
    tops=[]
    for ch in samples:
        if ch not in font.mapping:
            continue
        bb=bbox(font.get_cell(ch), threshold)
        if bb:
            tops.append(bb[1])
    if not tops:
        return None
    tops.sort()
    n=len(tops)
    return tops[n//2] if n%2 else int(round((tops[n//2-1]+tops[n//2])/2))

def make_dotless_i(font, _unused_i_cell=None):
    """Build Turkish U+0131 by shortening capital I *from the middle*.

    v11 hard-cropped the top of I at the lowercase x-height. That removed the
    font's authored top antialias/outline cap and made dotless-i look flat.
    v12 keeps BOTH the original top and bottom caps of capital I and removes
    only rows from the straight middle stem. The shortened sequence is then
    bottom-aligned so its top lands at the font's lowercase x-height.

    This mirrors Kirby's native CommonStd_OL U+0131 very closely and also
    preserves the small shadow/outline region that belongs above the bright
    stem, between the dotted-i dot and its main body.
    """
    if 'I' not in font.mapping:
        raise FontError('ı üretimi için büyük I glifi yok')
    cap=font.get_cell('I')
    bb=bbox(cap, threshold=0)
    if not bb:
        return clone(cap)
    _x0, cap_top, _x1, cap_bottom = bb

    # Use the first *visible* lowercase outline row, not the strong-fill row.
    # This keeps the top shadow/antialias that v11 accidentally cut away.
    target_top=xheight_top(font, threshold=0)
    if target_top is None:
        target_top=cap_top
    target_top=max(cap_top, min(target_top, cap_bottom-1))

    remove_n=target_top-cap_top
    if remove_n<=0:
        return clone(cap)

    cap_h=cap_bottom-cap_top
    if remove_n>=cap_h-2:
        raise FontError('ı orta-kesim için I glifi çok kısa')

    # Remove rows around the geometric middle, while protecting at least the
    # upper/lower cap regions. For a straight I stem this is seam-free because
    # the middle rows are intentionally repetitive.
    keep_h=cap_h-remove_n
    cut_start=cap_top + (cap_h-remove_n)//2
    cut_start=max(cap_top+2, min(cut_start, cap_bottom-remove_n-2))
    cut_end=cut_start+remove_n

    kept=[row[:] for row in cap[cap_top:cut_start]] + [row[:] for row in cap[cut_end:cap_bottom]]
    out=blank_like(cap)
    place_top=cap_bottom-len(kept)
    for j,row in enumerate(kept):
        out[place_top+j]=row

    # Geometry invariants: preserve original top/bottom cap rows exactly while
    # landing on lowercase x-height. These checks catch accidental top-cropping.
    ob=bbox(out, threshold=0)
    if not ob or ob[1] != target_top or ob[3] != cap_bottom:
        raise FontError(f'ı orta-kesim geometrisi bozuk: hedef top={target_top}, çıktı={ob}')
    top_rows=min(2, len(kept))
    for k in range(top_rows):
        if out[target_top+k] != cap[cap_top+k]:
            raise FontError('ı üst gölge/cap satırları korunamadı')
    for k in range(top_rows):
        if out[cap_bottom-1-k] != cap[cap_bottom-1-k]:
            raise FontError('ı alt cap satırları korunamadı')
    return out

def overlay_pixels(dst, src, dx=0,dy=0):
    h=len(dst); w=len(dst[0])
    for y,row in enumerate(src):
        for x,v in enumerate(row):
            if v[1]<=0: continue
            xx=x+dx; yy=y+dy
            if 0<=xx<w and 0<=yy<h:
                old=dst[yy][xx]
                # take higher alpha; when equal favor brighter luma fill
                if v[1]>old[1] or (v[1]==old[1] and v[0]>old[0]): dst[yy][xx]=v

def crop_points(cell, pts):
    if not pts: return [[(0,0)]]
    x0=min(x for x,y in pts); y0=min(y for x,y in pts); x1=max(x for x,y in pts)+1; y1=max(y for x,y in pts)+1
    out=[[(0,0) for _ in range(x1-x0)] for __ in range(y1-y0)]
    for x,y in pts: out[y-y0][x-x0]=cell[y][x]
    return out

def shift_cell(cell, dx,dy):
    out=blank_like(cell); overlay_pixels(out,cell,dx,dy); return out

def render_stroke_mask(dst, points, outline=True):
    h=len(dst); w=len(dst[0]); pts={(x,y) for x,y in points if 0<=x<w and 0<=y<h}
    if not pts: return
    if outline:
        edge=set()
        for x,y in pts:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                q=(x+dx,y+dy)
                if 0<=q[0]<w and 0<=q[1]<h and q not in pts: edge.add(q)
        for x,y in edge:
            old=dst[y][x]
            if 12>old[1]: dst[y][x]=(0,12)
    for x,y in pts: dst[y][x]=(15,15)

def add_breve(cell, outline=False):
    out=clone(cell); bb=bbox(cell)
    if not bb: return out
    x0,y0,x1,y1=bb
    width=max(5, min(9, int(round((x1-x0)*0.48))))
    if width%2==0: width+=1
    height=2 if len(cell)<32 else 3
    cx=(x0+x1-1)//2
    # Breve ile harf arasında en az bir boş satır bırak.
    bottom=y0-2
    top=bottom-height+1
    if top<0:
        shift=-top
        out=shift_cell(cell,0,shift); bb=bbox(out); x0,y0,x1,y1=bb; cx=(x0+x1-1)//2
        bottom=y0-2; top=max(0,bottom-height+1)
    left=cx-width//2; right=cx+width//2
    pts=[]
    if height==2:
        # Üstte iki kısa uç, altta onları birleştiren kavisli gövde.
        pts += [(left,top),(left+1,top),(right-1,top),(right,top)]
        pts += [(x,bottom) for x in range(left+1,right)]
    else:
        pts += [(left,top),(left+1,top),(right-1,top),(right,top)]
        pts += [(left+1,top+1),(right-1,top+1)]
        pts += [(x,bottom) for x in range(left+2,right-1)]
    render_stroke_mask(out,pts,outline=outline)
    return out

def add_diaeresis(cell, dot_src=None):
    out=clone(cell); bb=bbox(cell)
    if not bb:return out
    x0,y0,x1,y1=bb
    if dot_src:
        dc=crop_points(dot_src[0],dot_src[1]); dw=len(dc[0]); dh=len(dc)
    else:
        dc=[[(15,15),(15,15)]]; dw=2; dh=1
    y=max(0,y0-dh-1)
    centers=[x0+(x1-x0)//3, x0+2*(x1-x0)//3]
    for c in centers: overlay_pixels(out,dc,c-dw//2,y)
    return out

def add_dot(cell, dot_src):
    out=clone(cell); bb=bbox(cell)
    if not bb:return out
    dc=crop_points(dot_src[0],dot_src[1]); dw=len(dc[0]); dh=len(dc); x0,y0,x1,y1=bb
    x=(x0+x1-dw)//2; y=max(0,y0-dh-1); overlay_pixels(out,dc,x,y); return out

def add_cedilla(cell, cedilla_src=None):
    out=clone(cell); bb=bbox(cell)
    if not bb:return out
    x0,y0,x1,y1=bb; h=len(cell); cx=(x0+x1-1)//2
    if cedilla_src:
        cc=crop_points(cedilla_src[0],cedilla_src[1]); cw=len(cc[0]); ch=len(cc); y=min(h-ch,max(y1-1,0)); overlay_pixels(out,cc,cx-cw//2,y); return out
    start=y1
    if start+3>=h:
        out=shift_cell(cell,0,-min(2,start+3-h+1)); bb=bbox(out); x0,y0,x1,y1=bb; cx=(x0+x1-1)//2; start=y1
    pts=[(cx,start),(cx+1,start+1),(cx,start+2),(cx-1,start+3)]
    render_stroke_mask(out,pts); return out

def extract_cedilla(font:BCFNT, upper=True):
    acc='Ç' if upper else 'ç'; base='C' if upper else 'c'
    if acc not in font.mapping or base not in font.mapping: return None
    ac=font.get_cell(acc); bc=font.get_cell(base); bb=bbox(bc)
    if not bb:return None
    cutoff=max(0,bb[3]-1)
    pts=[(x,y) for y,row in enumerate(ac) for x,v in enumerate(row) if y>=cutoff and v[1]>0 and (y>=len(bc) or bc[y][x][1]==0)]
    if len(pts)<2:
        pts=[(x,y) for y,row in enumerate(ac) for x,v in enumerate(row) if y>=bb[3] and v[1]>0]
    return ac,pts

def synthesize(font:BCFNT, ch:str):
    base=BASE_FOR[ch]
    if base not in font.mapping: raise FontError(f'{ch}: taban {base} yok')
    c=font.get_cell(base)
    i_cell=font.get_cell('i') if 'i' in font.mapping else None
    dcomp=dot_component(i_cell) if i_cell else []
    dot_src=(i_cell,dcomp) if i_cell and dcomp else None
    if ch in 'Ğğ': return add_breve(c, outline=(font.pixel_fmt==9))
    if ch=='İ': return add_dot(c,dot_src) if dot_src else add_diaeresis(c,None)
    if ch=='ı': return make_dotless_i(font)
    if ch in 'ÖÜöü': return add_diaeresis(c,dot_src)
    if ch in 'ÇŞ':
        src=extract_cedilla(font,True) if ch=='Ş' else None
        return add_cedilla(c,src)
    if ch in 'çş':
        src=extract_cedilla(font,False) if ch=='ş' else None
        return add_cedilla(c,src)
    return c

def choose_donors(font:BCFNT, n:int, used_chars:set[str]):
    inverse=defaultdict(list)
    for c,idx in font.mapping.items(): inverse[idx].append(c)
    cands=[]
    for idx,chars in inverse.items():
        if idx not in font.width_offsets: continue
        if any(c in used_chars or c in TR_CHARS or ord(c)<128 for c in chars): continue
        # Prefer CJK, then fullwidth, then >255, then extended Latin/symbols.
        cps=[ord(c) for c in chars]; cp=max(cps)
        if any(0x3000<=x<=0x9FFF for x in cps): pri=0
        elif any(0xFF00<=x<=0xFFEF for x in cps): pri=1
        elif any(x>0xFF for x in cps): pri=2
        else: pri=3
        cands.append((pri,-cp,idx,chars))
    cands.sort()
    if len(cands)<n: raise FontError(f'{n} donor glif lazım, güvenli aday {len(cands)}')
    return [(idx,chars[0]) for _,_,idx,chars in cands[:n]]

def patch_font(data:bytes, used_chars:set[str]):
    compressed=data.startswith(b'\x11'); font=BCFNT(data)
    missing=[c for c in TR_CHARS if c not in font.mapping]
    dotless_repaired=False
    # Fonts that natively contain the Turkish Latin block (not donor-injected)
    # keep the original hand-authored dotless-i. Kirby's CommonStd_OL has
    # adjacent uppercase/lowercase extended-Latin indices for these pairs.
    native_tr_pairs = all(a in font.mapping and b in font.mapping and font.mapping[b] == font.mapping[a] + 1
                          for a,b in [('Ğ','ğ'),('İ','ı'),('Ş','ş')])
    # v12: rebuild previously injected U+0131 by shortening capital I from its middle. Outlined i glyphs can have
    # dot outline pixels connected to the stem, so component-only removal is not
    # sufficient. Rebuild it from x-height geometry whenever i/ı are present.
    if (not native_tr_pairs) and 'I' in font.mapping and 'i' in font.mapping and 'ı' in font.mapping:
        desired=make_dotless_i(font)
        current=font.get_cell('ı')
        # A4 transparent texels may decode with arbitrary luma; alpha defines
        # visibility. Compare alpha geometry so the patcher is idempotent.
        desired_alpha=[[px[1] for px in row] for row in desired]
        current_alpha=[[px[1] for px in row] for row in current]
        if desired_alpha != current_alpha:
            font.set_cell_idx(font.mapping['ı'],desired)
            if font.mapping['i'] in font.width_offsets and font.mapping['ı'] in font.width_offsets:
                font.copy_width(font.mapping['i'],font.mapping['ı'])
            dotless_repaired=True
    if not missing:
        if not dotless_repaired:
            return data, {'status':'already_ok','missing_before':'','donors':'','dotless_i_fix':'no','raw_size':len(font.raw),'packed_size':len(data)}
        raw=font.build(); out=lz11_compress(raw) if compressed else raw
        verify=BCFNT(out)
        desired_top=xheight_top(verify, threshold=0)
        actual_bb=bbox(verify.get_cell('ı'), threshold=0)
        if desired_top is not None and (not actual_bb or actual_bb[1] != desired_top):
            raise FontError(f'ı görünür x-height doğrulaması başarısız: beklenen {desired_top}, gerçek {actual_bb}')
        return out, {'status':'repaired','missing_before':'','donors':'','dotless_i_fix':'yes','raw_size':len(raw),'packed_size':len(out)}
    # only patch text-capable fonts with ASCII bases
    needed_bases={BASE_FOR[c] for c in missing}
    if not needed_bases.issubset(font.mapping): return data, {'status':'skip','missing':' '.join(missing),'reason':'taban Latin glifleri yok'}
    donors=choose_donors(font,len(missing),used_chars)
    additions={}; donor_desc=[]
    for ch,(idx,donor_char) in zip(missing,donors):
        cell=synthesize(font,ch); font.set_cell_idx(idx,cell); font.copy_width(font.mapping[BASE_FOR[ch]],idx); additions[ch]=idx; donor_desc.append(f'{ch}<-{donor_char}(#{idx})')
    # flush modified sheet bytes before append; build once, then cmap append, then build again
    font.build(); font.merge_terminal_scan_cmap(additions); raw=font.build()
    out=lz11_compress(raw) if compressed else raw
    # verify compressed and mappings
    verify=BCFNT(out)
    still=[c for c in TR_CHARS if c not in verify.mapping]
    if still: raise FontError(f'Doğrulama sonrası eksik: {still}')
    runtime_still=[c for c in TR_CHARS if verify.runtime_lookup(c) is None]
    if runtime_still: raise FontError(f'Runtime CMAP doğrulaması sonrası eksik: {runtime_still}')
    return out, {'status':'patched','missing_before':''.join(missing),'donors':'; '.join(donor_desc),'dotless_i_fix':'yes' if ('ı' in missing or dotless_repaired) else 'no','raw_size':len(raw),'packed_size':len(out)}


def write_gray_png(path:Path, width:int, height:int, pixels:list[int]):
    import zlib, binascii
    if len(pixels)!=width*height: raise FontError('PNG piksel sayısı bozuk')
    def chunk(kind:bytes, data:bytes):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',binascii.crc32(kind+data)&0xFFFFFFFF)
    raw=bytearray()
    for y in range(height):
        raw.append(0)
        raw += bytes(pixels[y*width:(y+1)*width])
    png=b'\x89PNG\r\n\x1a\n'
    png+=chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,0,0,0,0))
    png+=chunk(b'IDAT',zlib.compress(bytes(raw),9))
    png+=chunk(b'IEND',b'')
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(png)

def make_preview(data:bytes, out_png:Path, chars:str=TR_CHARS, scale:int=5):
    f=BCFNT(data)
    present=[c for c in chars if c in f.mapping]
    if not present: raise FontError('Önizlenecek Türkçe glif yok')
    w=len(present)*f.cell_w; h=f.cell_h
    pix=[0]*(w*h)
    for n,c in enumerate(present):
        cell=f.get_cell(c)
        for y,row in enumerate(cell):
            for x,v in enumerate(row):
                lum,alpha=v[0]*17,v[1]*17
                bg=64
                pix[y*w+n*f.cell_w+x]=(lum*alpha + bg*(255-alpha))//255
    if scale>1:
        sw,sh=w*scale,h*scale; scaled=[0]*(sw*sh)
        for y in range(h):
            for x in range(w):
                val=pix[y*w+x]
                for yy in range(scale):
                    base=(y*scale+yy)*sw+x*scale
                    scaled[base:base+scale]=[val]*scale
        w,h,pix=sw,sh,scaled
    write_gray_png(out_png,w,h,pix)

def load_used_chars(path:Path|None):
    if not path: return set()
    return set(path.read_text(encoding='utf-8'))

def cmd_patch(inp:Path,out:Path,used_file:Path|None,preview:Path|None):
    used=load_used_chars(used_file); patched,rep=patch_font(inp.read_bytes(),used)
    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(patched)
    if preview and rep['status'] in ('patched','already_ok','repaired'): make_preview(patched,preview)
    print(f"{inp.name}: {rep['status']}")
    if rep.get('missing_before'): print('  önce eksik:',rep['missing_before'])
    if rep.get('donors'): print('  donorlar:',rep['donors'])
    if rep.get('reason'): print('  not:',rep['reason'])

def cmd_patch_all(root:Path,outroot:Path,used_file:Path|None,report_csv:Path|None,previews:Path|None):
    import shutil
    used=load_used_chars(used_file); rows=[]; count=0
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root); dst=outroot/rel
        if p.is_dir(): dst.mkdir(parents=True,exist_ok=True); continue
        dst.parent.mkdir(parents=True,exist_ok=True)
        if p.name.endswith('.bcfnt.cmp') or p.name.endswith('.bcfnt'):
            try:
                patched,rep=patch_font(p.read_bytes(),used); dst.write_bytes(patched)
                if previews and rep['status'] in ('patched','already_ok','repaired'):
                    try: make_preview(patched,previews/(str(rel).replace('/','__')+'.png'))
                    except Exception: pass
            except Exception as e:
                shutil.copy2(p,dst); rep={'status':'error','reason':str(e)}
            rows.append({'file':str(rel),'status':rep.get('status',''),'missing_before':rep.get('missing_before',rep.get('missing','')),'donors':rep.get('donors',''),'dotless_i_fix':rep.get('dotless_i_fix',''),'reason':rep.get('reason',''),'source_size':p.stat().st_size,'output_size':dst.stat().st_size})
            if rep.get('status') in ('patched','repaired'): count+=1
        else: shutil.copy2(p,dst)
    if report_csv:
        report_csv.parent.mkdir(parents=True,exist_ok=True)
        with report_csv.open('w',encoding='utf-8-sig',newline='') as f:
            fields=['file','status','missing_before','donors','dotless_i_fix','reason','source_size','output_size']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f'{count} font Türkçe için çizildi/enjekte edildi veya ı glifi onarıldı: {outroot}')
    for r in rows: print(f"{r['status']:10} {r['file']} {r['missing_before']}")

def cmd_verify(inp:Path):
    f=BCFNT(inp.read_bytes()); missing=''.join(c for c in TR_CHARS if c not in f.mapping)
    print(f'{inp}: cell={f.cell_w}x{f.cell_h} format={f.pixel_fmt} map={len(f.mapping)} sections={f.section_count}')
    print('Türkçe:', 'TAMAM' if not missing else 'EKSİK '+missing)
    raise SystemExit(0 if not missing else 1)

def main():
    import argparse
    ap=argparse.ArgumentParser(description='Kirby Planet Robobot BCFNT Türkçe glif çizici/enjektörü v12 (runtime-safe CMAP + büyük I orta-kesim tabanlı noktasız ı, yalnızca standart Python)')
    sp=ap.add_subparsers(dest='cmd',required=True)
    p=sp.add_parser('patch'); p.add_argument('input',type=Path); p.add_argument('output',type=Path); p.add_argument('--used-chars-file',type=Path); p.add_argument('--preview',type=Path)
    p=sp.add_parser('patch-all'); p.add_argument('font_root',type=Path); p.add_argument('output_root',type=Path); p.add_argument('--used-chars-file',type=Path); p.add_argument('--report',type=Path); p.add_argument('--previews',type=Path)
    p=sp.add_parser('preview'); p.add_argument('input',type=Path); p.add_argument('output_png',type=Path); p.add_argument('--scale',type=int,default=5)
    p=sp.add_parser('verify'); p.add_argument('input',type=Path)
    a=ap.parse_args()
    try:
        if a.cmd=='patch': cmd_patch(a.input,a.output,a.used_chars_file,a.preview)
        elif a.cmd=='patch-all': cmd_patch_all(a.font_root,a.output_root,a.used_chars_file,a.report,a.previews)
        elif a.cmd=='preview': make_preview(a.input.read_bytes(),a.output_png,scale=a.scale); print(a.output_png)
        else: cmd_verify(a.input)
    except FontError as e:
        print('HATA:',e); raise SystemExit(2)

if __name__=='__main__': main()
