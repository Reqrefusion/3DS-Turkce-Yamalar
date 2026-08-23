import struct, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from xfsa_extract import level5_dec
from fnt01_parse import parse as parse_fnt
from xpck_repack import repack as repack_xpck

SHIFTS={0:11,1:6,2:1}

def align4(n): return (n+3)&~3

def l5raw(data): return struct.pack('<I',len(data)<<3)+bytes(data)

# Morton layout used by CTR2 Level-5 RGBA5551 tiles.
Q_TO_XY=[]
XY_TO_Q={}
for q in range(64):
    x=((q>>1)&1)|(((q>>3)&1)<<1)|(((q>>5)&1)<<2)
    y=(q&1)|(((q>>2)&1)<<1)|(((q>>4)&1)<<2)
    Q_TO_XY.append((x,y)); XY_TO_Q[(x,y)]=q

class Xi:
    def __init__(self,path):
        self.path=path; self.b=Path(path).read_bytes(); b=self.b
        assert b[:8].startswith(b'IMGC00')
        self.width,self.height=struct.unpack_from('<hh',b,16)
        self.W=(self.width+7)&~7; self.H=(self.height+7)&~7
        self.datao=struct.unpack_from('<i',b,28)[0]
        self.io=struct.unpack_from('<H',b,24)[0]
        self.to,self.ts,self.do,self.ds=struct.unpack_from('<iiii',b,self.io)
        traw=level5_dec(b,self.datao+self.to); self.tiles=list(struct.unpack('<'+'h'*(len(traw)//2),traw))
        self.data=level5_dec(b,self.datao+self.do)
        assert len(self.tiles)==(self.W//8)*(self.H//8),(len(self.tiles),self.W,self.H)
    def word(self,x,y):
        ti=(y//8)*(self.W//8)+(x//8); tid=self.tiles[ti]
        q=XY_TO_Q[(x&7,y&7)]
        return struct.unpack_from('<H',self.data,tid*128+q*2)[0]
    def channel(self,x,y,ch): return (self.word(x,y)>>SHIFTS[ch])&31
    def linear(self,new_h=None):
        H2=((new_h if new_h is not None else self.height)+7)&~7
        # 1 is black RGB + alpha bit set, matching the source's blank font background.
        out=[1]*(self.W*H2)
        for y in range(self.H):
            for x in range(self.W): out[y*self.W+x]=self.word(x,y)
        return out,H2
    def build(self,linear,new_height,outpath):
        W=self.W; H=(new_height+7)&~7; assert len(linear)==W*H
        # Build the tile map with deduplication. The original Level-5 fonts reuse
        # identical 8x8 tiles heavily; preserving that behavior keeps patched
        # fonts compact instead of storing every blank/repeated tile again.
        tile_ids=[]; unique_tiles=[]; tile_index={}
        tile_count=(W//8)*(H//8)
        for ty in range(0,H,8):
            for tx in range(0,W,8):
                tile=bytearray()
                for q in range(64):
                    lx,ly=Q_TO_XY[q]; tile += struct.pack('<H',linear[(ty+ly)*W+(tx+lx)])
                key=bytes(tile)
                tid=tile_index.get(key)
                if tid is None:
                    tid=len(unique_tiles)
                    if tid >= 0x8000: raise ValueError('XI tile index overflow')
                    tile_index[key]=tid; unique_tiles.append(key)
                tile_ids.append(tid)
        assert len(tile_ids)==tile_count
        storage=b''.join(unique_tiles)
        tile_raw=b''.join(struct.pack('<h',i) for i in tile_ids)
        tb=l5raw(tile_raw); db=l5raw(storage)
        out=bytearray(self.b[:self.datao])
        struct.pack_into('<h',out,18,new_height)
        struct.pack_into('<iiii',out,self.io,0,len(tb),len(tb),len(db))
        out.extend(tb); out.extend(db)
        Path(outpath).write_bytes(out)
        return len(out)

def get_mask(fnt,xi,cp):
    info=next(i for i in fnt['infos'] if i['cp']==cp)
    ox,oy,w,h=info['size']; ch=info['idx']
    m=[[xi.channel(info['x']+x,info['y']+y,ch) for x in range(w)] for y in range(h)]
    return info,m

def blank(w,h): return [[0]*w for _ in range(h)]

def blit_max(dst,src,dx,dy):
    H=len(dst); W=len(dst[0]) if H else 0
    for y,row in enumerate(src):
        yy=dy+y
        if yy<0 or yy>=H: continue
        for x,v in enumerate(row):
            xx=dx+x
            if 0<=xx<W and v>dst[yy][xx]: dst[yy][xx]=v

def resize_nearest(src,neww,newh=None):
    oh=len(src); ow=len(src[0]) if oh else 0
    if newh is None: newh=oh
    if not ow or not oh:return blank(neww,newh)
    out=blank(neww,newh)
    for y in range(newh):
        sy=min(oh-1,int((y+0.5)*oh/newh))
        for x in range(neww):
            sx=min(ow-1,int((x+0.5)*ow/neww))
            out[y][x]=src[sy][sx]
    return out

def make_breve(width,rows):
    # Anti-aliased U-shaped breve, scaled from a compact 7x3 template.
    tpl=[
      [0,10,0,0,0,10,0],
      [0,20,8,0,8,20,0],
      [0,0,16,28,16,0,0],
    ]
    return resize_nearest(tpl,width,rows)

def compose_missing(variant,fnt,xi):
    # Returns cp -> {mask,size=(ox,oy,w,h),adv}
    specs={}
    if variant=='nrm':
        targets={
          0x011E:(0,0,11,16,0x47), # Ğ <- G + breve
          0x011F:(0,3,8,15,0x67),  # ğ <- g + breve
          0x0130:(1,1,2,14,0x49),  # İ <- I + dot
          0x0131:(1,6,2,9,0x69),   # ı <- i - dot
          0x015E:(0,3,9,15,0x53),  # Ş <- S + cedilla
          0x015F:(0,6,7,12,0x73),  # ş <- s + cedilla
        }
    else:
        targets={
          0x011E:(0,0,9,13,0x47),
          0x011F:(0,2,7,13,0x67),
          0x0130:(1,0,2,13,0x49),
          0x0131:(0,5,2,8,0x69),
          0x015E:(0,2,8,13,0x53),
          0x015F:(0,5,6,10,0x73),
        }
    cache={}
    for cp in set(v[4] for v in targets.values())|{0x43,0xC7,0x63,0xE7,0x69}:
        try: cache[cp]=get_mask(fnt,xi,cp)
        except StopIteration: pass
    for cp,(ox,oy,w,h,basecp) in targets.items():
        baseinfo,basem=cache[basecp]; m=blank(w,h)
        if cp in (0x011E,0x011F):
            # preserve absolute baseline placement; accent occupies the freed rows above.
            dy=baseinfo['size'][1]-oy
            blit_max(m,resize_nearest(basem,w,len(basem)),0,dy)
            accent_rows=max(2,dy)
            blit_max(m,make_breve(w,accent_rows),0,0)
        elif cp==0x0130:
            dy=baseinfo['size'][1]-oy
            blit_max(m,resize_nearest(basem,w,len(basem)),0,dy)
            # centered single dot above uppercase I
            m[0][max(0,w//2-1)]=31
            if w>1: m[0][w//2]=20
        elif cp==0x0131:
            # Crop the dot rows from lowercase i while preserving its absolute vertical position.
            srcinfo,srcm=cache[0x69]; start=max(0,oy-srcinfo['size'][1])
            cropped=srcm[start:start+h]
            blit_max(m,resize_nearest(cropped,w,len(cropped)),0,0)
        elif cp in (0x015E,0x015F):
            blit_max(m,resize_nearest(basem,w,len(basem)),0,0)
            if cp==0x015E: accinfo,accm=cache[0xC7]; base_ref=cache[0x43][1]
            else: accinfo,accm=cache[0xE7]; base_ref=cache[0x63][1]
            # Last three rows include the start and tail of the cedilla in this Level-5 font.
            tail=accm[max(0,len(accm)-3):]
            tail=resize_nearest(tail,w,min(3,h))
            blit_max(m,tail,0,h-len(tail))
        specs[cp]={'mask':m,'size':(ox,oy,w,h),'adv':baseinfo['adv']}
    return specs

def write_mask(linear,W,x0,y0,ch,mask):
    shift=SHIFTS[ch]; cmask=31<<shift
    for y,row in enumerate(mask):
        for x,v in enumerate(row):
            pos=(y0+y)*W+(x0+x); word=linear[pos]
            word=(word & ~cmask) | ((int(v)&31)<<shift)
            word |= 1  # preserve/set alpha bit
            linear[pos]=word

def rebuild_fnt(orig_path,synth,locations,outpath):
    f=parse_fnt(orig_path); b=f['blob']
    # Re-read raw char-size stream and old char infos.
    cso,csc,lco,lcc,sco,scc=struct.unpack_from('<6h',b,0x1c)
    csraw=bytearray(level5_dec(b,cso<<2)); lcraw=level5_dec(b,lco<<2)
    sizes=[struct.unpack_from('<bbBB',csraw,i*4) for i in range(csc)]
    records=[bytearray(lcraw[i:i+8]) for i in range(0,len(lcraw),8)]
    by={struct.unpack_from('<H',r,0)[0]:bytes(r) for r in records}
    old_escape_cp=struct.unpack_from('<H',records[f['le']],0)[0]
    rec_by={struct.unpack_from('<H',r,0)[0]:r for r in records}
    # Existing Western Turkish letters: PUA aliases can point to the exact same atlas data.
    pua_existing={0xE000:0x00C7,0xE001:0x00E7,0xE006:0x00D6,0xE007:0x00F6,0xE00A:0x00DC,0xE00B:0x00FC}
    for dst,src in pua_existing.items():
        r=bytearray(by[src]); struct.pack_into('<H',r,0,dst); rec_by[dst]=r
    pua_missing={0xE002:0x011E,0xE003:0x011F,0xE004:0x0130,0xE005:0x0131,0xE008:0x015E,0xE009:0x015F}
    # Add actual Unicode records plus PUA aliases for the six synthesized glyphs.
    for actual,spec in synth.items():
        size=spec['size']
        try: si=sizes.index(size)
        except ValueError:
            if len(sizes)>=1024: raise ValueError('size table full')
            si=len(sizes); sizes.append(size); csraw.extend(struct.pack('<bbBB',*size))
        x,y,ch=locations[actual]
        sizeinfo=(spec['adv']<<10)|si
        imageinfo=(y<<18)|(x<<4)|ch
        r=bytearray(struct.pack('<HHI',actual,sizeinfo,imageinfo)); rec_by[actual]=r
        for pua,srcactual in pua_missing.items():
            if srcactual==actual:
                rr=bytearray(r); struct.pack_into('<H',rr,0,pua); rec_by[pua]=rr
    records=sorted(rec_by.values(),key=lambda r:struct.unpack_from('<H',r,0)[0])
    new_escape=next(i for i,r in enumerate(records) if struct.unpack_from('<H',r,0)[0]==old_escape_cp)
    csblock=l5raw(b''.join(struct.pack('<bbBB',*s) for s in sizes))
    cso_new=0x28; lco_new=align4(cso_new+len(csblock))
    lcblock=l5raw(b''.join(records)); sco_new=align4(lco_new+len(lcblock))
    scraw=f['scraw']; scblock=l5raw(scraw) if scc else b''
    out=bytearray(sco_new+len(scblock)); out[:0x28]=b[:0x28]
    struct.pack_into('<H',out,16,new_escape)
    struct.pack_into('<6h',out,0x1c,cso_new>>2,len(sizes),lco_new>>2,len(records),sco_new>>2,scc)
    out[cso_new:cso_new+len(csblock)]=csblock
    out[lco_new:lco_new+len(lcblock)]=lcblock
    if scblock: out[sco_new:sco_new+len(scblock)]=scblock
    Path(outpath).write_bytes(out)
    # validate all 12 PUA and actual six are present
    q=parse_fnt(outpath); codes={z['cp'] for z in q['infos']}
    assert all(c in codes for c in range(0xE000,0xE00C))
    assert all(c in codes for c in synth)
    return len(out),len(sizes),len(records),new_escape

def build_variant(variant,src_xf,out_xf,work):
    fnt_path=f'/mnt/data/font_scan/eu_{variant}/FNT.bin'; xi_path=f'/mnt/data/font_scan/eu_{variant}/000.xi'
    f=parse_fnt(fnt_path); xi=Xi(xi_path); synth=compose_missing(variant,f,xi)
    start_y=xi.H
    new_height=56 if variant=='nrm' else 40
    linear,H2=xi.linear(new_height)
    locations={}; x=8
    for cp in [0x011E,0x011F,0x0130,0x0131,0x015E,0x015F]:
        spec=synth[cp]; w=spec['size'][2]; h=spec['size'][3]
        locations[cp]=(x,start_y,0); write_mask(linear,xi.W,x,start_y,0,spec['mask']); x+=w+4
    out_xi=str(Path(work)/f'{variant}_000.xi'); out_fnt=str(Path(work)/f'{variant}_FNT.bin')
    xi_size=xi.build(linear,new_height,out_xi)
    fnt_stat=rebuild_fnt(fnt_path,synth,locations,out_fnt)
    repack_xpck(src_xf,{'000.xi':out_xi,'FNT.bin':out_fnt},out_xf)
    return {'xi':xi_size,'fnt':fnt_stat,'xf':Path(out_xf).stat().st_size,'locations':locations,'synth':synth}

if __name__=='__main__':
    outdir=Path('/mnt/data/turkish_font_exact'); outdir.mkdir(exist_ok=True)
    a=build_variant('nrm','/mnt/data/xfsa_out/lt5_a.fa/fnt/[eu]/nrm.xf',str(outdir/'nrm.xf'),outdir)
    b=build_variant('sml','/mnt/data/xfsa_out/lt5_a.fa/fnt/[eu]/sml.xf',str(outdir/'sml.xf'),outdir)
    print('NRM',a); print('SML',b)
