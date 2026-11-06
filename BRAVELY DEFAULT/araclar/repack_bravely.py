from __future__ import annotations
from pathlib import Path
import struct, sys, json, shutil, zlib

FREESECT=0xFFFFFFFF
ENDOFCHAIN=0xFFFFFFFE
FATSECT=0xFFFFFFFD
DIFSECT=0xFFFFFFFC
NOSTREAM=0xFFFFFFFF

class CFBError(Exception): pass

class CFB:
    def __init__(self, data: bytes):
        self.data=data
        if data[:8] != bytes.fromhex('D0CF11E0A1B11AE1'):
            raise CFBError('not CFB')
        self.major=struct.unpack_from('<H',data,0x1A)[0]
        byteorder=struct.unpack_from('<H',data,0x1C)[0]
        if byteorder != 0xFFFE: raise CFBError('bad byte order')
        self.sector_size=1 << struct.unpack_from('<H',data,0x1E)[0]
        self.mini_sector_size=1 << struct.unpack_from('<H',data,0x20)[0]
        self.num_fat=struct.unpack_from('<I',data,0x2C)[0]
        self.first_dir=struct.unpack_from('<I',data,0x30)[0]
        self.mini_cutoff=struct.unpack_from('<I',data,0x38)[0]
        self.first_minifat=struct.unpack_from('<I',data,0x3C)[0]
        self.num_minifat=struct.unpack_from('<I',data,0x40)[0]
        self.first_difat=struct.unpack_from('<I',data,0x44)[0]
        self.num_difat=struct.unpack_from('<I',data,0x48)[0]
        self.difat=[x for x in struct.unpack_from('<109I',data,0x4C) if x != FREESECT]
        sid=self.first_difat
        for _ in range(self.num_difat):
            if sid in (ENDOFCHAIN, FREESECT): break
            sec=self.sector(sid)
            n=self.sector_size//4
            vals=struct.unpack_from('<%dI'%n,sec,0)
            self.difat.extend(x for x in vals[:-1] if x != FREESECT)
            sid=vals[-1]
        self.difat=self.difat[:self.num_fat]
        fat=[]
        for fsid in self.difat:
            fat.extend(struct.unpack_from('<%dI'%(self.sector_size//4), self.sector(fsid),0))
        self.fat=fat
        self.dir_bytes=self.read_chain(self.first_dir)
        self.entries=[]
        for off in range(0,len(self.dir_bytes),128):
            d=self.dir_bytes[off:off+128]
            if len(d)<128: break
            nlen=struct.unpack_from('<H',d,64)[0]
            if nlen>=2 and nlen<=64:
                name=d[:nlen-2].decode('utf-16le','replace')
            else: name=''
            etype=d[66]
            start=struct.unpack_from('<I',d,116)[0]
            size=struct.unpack_from('<Q',d,120)[0]
            if self.major==3: size &= 0xFFFFFFFF
            self.entries.append({'name':name,'type':etype,'start':start,'size':size,'raw':d})
        roots=[e for e in self.entries if e['type']==5]
        self.root=roots[0] if roots else None
        self.minifat=[]
        self.mini_stream=b''
        if self.num_minifat and self.first_minifat not in (ENDOFCHAIN,FREESECT):
            mfb=self.read_chain(self.first_minifat)
            self.minifat=list(struct.unpack_from('<%dI'%(len(mfb)//4),mfb,0))
        if self.root and self.root['size'] and self.root['start'] not in (ENDOFCHAIN,FREESECT):
            self.mini_stream=self.read_chain(self.root['start'])[:self.root['size']]
    def sector(self,sid:int)->bytes:
        off=(sid+1)*self.sector_size
        return self.data[off:off+self.sector_size]
    def read_chain(self,start:int)->bytes:
        if start in (ENDOFCHAIN,FREESECT): return b''
        out=[]; sid=start; seen=set()
        while sid not in (ENDOFCHAIN,FREESECT):
            if sid in seen: raise CFBError('FAT loop')
            seen.add(sid)
            if sid>=len(self.fat): raise CFBError(f'bad FAT sid {sid}')
            out.append(self.sector(sid))
            sid=self.fat[sid]
        return b''.join(out)
    def read_mini_chain(self,start:int)->bytes:
        if start in (ENDOFCHAIN,FREESECT): return b''
        out=[]; sid=start; seen=set()
        while sid not in (ENDOFCHAIN,FREESECT):
            if sid in seen: raise CFBError('miniFAT loop')
            seen.add(sid)
            off=sid*self.mini_sector_size
            out.append(self.mini_stream[off:off+self.mini_sector_size])
            if sid>=len(self.minifat): raise CFBError('bad mini sid')
            sid=self.minifat[sid]
        return b''.join(out)
    def stream(self,name:str)->bytes:
        for e in self.entries:
            if e['type']==2 and e['name'].lower()==name.lower():
                if e['size'] < self.mini_cutoff:
                    b=self.read_mini_chain(e['start'])
                else:
                    b=self.read_chain(e['start'])
                return b[:e['size']]
        raise KeyError(name)


def get_biff_stream(path: Path)->bytes:
    b=path.read_bytes()
    if b[:8]==bytes.fromhex('D0CF11E0A1B11AE1'):
        c=CFB(b)
        for n in ('Workbook','Book'):
            try:return c.stream(n)
            except KeyError: pass
        raise CFBError(f'No Workbook stream in {path}')
    return b


def decode_rk(rk:int)->float:
    mult100=rk&1; isint=(rk>>1)&1; valraw=rk&0xFFFFFFFC
    if isint:
        val=struct.unpack('<i',struct.pack('<I',valraw))[0]>>2
    else:
        val=struct.unpack('<d',struct.pack('<II',0,valraw))[0]
    if mult100: val/=100
    return float(val)

class SegReader:
    def __init__(self, segments, seg=0, pos=0):
        self.segments=segments; self.si=seg; self.pos=pos
    def _next(self):
        self.si+=1; self.pos=0
        if self.si>=len(self.segments): raise EOFError
    def read_raw(self,n):
        out=bytearray()
        while n:
            if self.si>=len(self.segments): raise EOFError
            seg=self.segments[self.si]
            avail=len(seg)-self.pos
            if avail<=0:
                self._next(); continue
            k=min(n,avail); out+=seg[self.pos:self.pos+k]; self.pos+=k; n-=k
        return bytes(out)
    def read_u8(self): return self.read_raw(1)[0]
    def read_u16(self): return struct.unpack('<H',self.read_raw(2))[0]
    def read_u32(self): return struct.unpack('<I',self.read_raw(4))[0]
    def at_segment_end(self): return self.si<len(self.segments) and self.pos>=len(self.segments[self.si])
    def next_segment(self): self._next()


def parse_sst(segments):
    if not segments: return []
    r=SegReader(segments,0,0)
    total=r.read_u32(); unique=r.read_u32()
    strings=[]
    for _ in range(unique):
        cch=r.read_u16(); flags=r.read_u8()
        high=bool(flags&1); rich=bool(flags&0x08); ext=bool(flags&0x04)
        cRun=r.read_u16() if rich else 0
        cbExt=r.read_u32() if ext else 0
        chars=[]; remain=cch
        while remain:
            if r.at_segment_end():
                r.next_segment()
                # During the character array, each CONTINUE starts with a fresh fHighByte flag.
                high=bool(r.read_u8()&1)
            seg=r.segments[r.si]
            avail=len(seg)-r.pos
            bpc=2 if high else 1
            maxchars=avail//bpc
            if maxchars<=0:
                r.next_segment(); high=bool(r.read_u8()&1); continue
            n=min(remain,maxchars)
            raw=r.read_raw(n*bpc)
            chars.append(raw.decode('utf-16le' if high else 'latin1','replace'))
            remain-=n
        if cRun:
            r.read_raw(cRun*4)
        if cbExt:
            r.read_raw(cbExt)
        strings.append(''.join(chars))
    return strings


def parse_biff(path: Path):
    b=get_biff_stream(path)
    recs=[]; o=0
    while o+4<=len(b):
        rt,ln=struct.unpack_from('<HH',b,o)
        if o+4+ln>len(b): break
        d=b[o+4:o+4+ln]
        recs.append((o,rt,d)); o+=4+ln
    sheets=[]
    for o,rt,d in recs:
        if rt==0x0085 and len(d)>=8:
            off=struct.unpack_from('<I',d,0)[0]
            n=d[6]; flags=d[7]; raw=d[8:]
            name=raw[:n*2].decode('utf-16le','replace') if flags&1 else raw[:n].decode('latin1','replace')
            sheets.append((off,name))
    byoff={o:i for i,(o,_,_) in enumerate(recs)}
    if not sheets:
        ws=[]
        for i,(o,rt,d) in enumerate(recs):
            if rt==0x0809 and len(d)>=4 and struct.unpack_from('<H',d,2)[0]==0x0010:
                ws.append(o)
        if len(ws)==1: sheets=[(ws[0],path.stem)]
        elif ws: sheets=[(off,f'Sheet{j+1}') for j,off in enumerate(ws)]
    # workbook-level SST
    sst=[]
    for i,(o,rt,d) in enumerate(recs):
        if rt==0x00FC:
            segs=[d]; j=i+1
            while j<len(recs) and recs[j][1]==0x003C:
                segs.append(recs[j][2]); j+=1
            try: sst=parse_sst(segs)
            except Exception as e:
                raise RuntimeError(f'SST parse failed for {path}: {e}')
            break
    out={}
    for off,name in sheets:
        i=byoff.get(off)
        if i is None:
            candidates=[(abs(o-off),idx) for idx,(o,rt,d) in enumerate(recs) if rt==0x0809]
            if not candidates: continue
            i=min(candidates)[1]
        cells={}
        for o,rt,d in recs[i+1:]:
            if rt==0x000A: break
            if rt==0x0203 and len(d)>=14:
                r0,c,xf=struct.unpack_from('<HHH',d,0); cells[(r0,c)]=struct.unpack_from('<d',d,6)[0]
            elif rt==0x0204 and len(d)>=9:
                r0,c,xf,cch=struct.unpack_from('<HHHH',d,0); flags=d[8]; raw=d[9:]
                cells[(r0,c)]=raw[:cch*2].decode('utf-16le','replace') if flags&1 else raw[:cch].decode('latin1','replace')
            elif rt==0x027E and len(d)>=10:
                r0,c,xf=struct.unpack_from('<HHH',d,0); cells[(r0,c)]=decode_rk(struct.unpack_from('<I',d,6)[0])
            elif rt==0x00FD and len(d)>=10:
                r0,c,xf=struct.unpack_from('<HHH',d,0); idx=struct.unpack_from('<I',d,6)[0]
                cells[(r0,c)]=sst[idx] if idx<len(sst) else ''
            elif rt==0x00BD and len(d)>=6: # MULRK
                r0,c0=struct.unpack_from('<HH',d,0); c_last=struct.unpack_from('<H',d,len(d)-2)[0]
                n=c_last-c0+1
                pos=4
                for j in range(n):
                    if pos+6>len(d)-2: break
                    xf=struct.unpack_from('<H',d,pos)[0]; rk=struct.unpack_from('<I',d,pos+2)[0]
                    cells[(r0,c0+j)]=decode_rk(rk); pos+=6
        out[name]=cells
    return out

def sheet_matrix(cells):
    if not cells: return []
    mr=max(r for r,c in cells)+1; mc=max(c for r,c in cells)+1
    return [[cells.get((r,c),'') for c in range(mc)] for r in range(mr)]

if __name__=='__main__':
    for arg in sys.argv[1:]:
        p=Path(arg); wb=parse_biff(p)
        print(p, 'sheets',len(wb))
        for n,c in wb.items():
            mat=sheet_matrix(c)
            print(' ',n, len(mat), len(mat[0]) if mat else 0, mat[:2])

# --- Bravely BTBF repacking helpers ---
def normalize_sheet_filename(name:str)->str:
    # BravelyCrowd replaces underscores with spaces in worksheet names.
    return name.replace(' ', '_')

def resolve_sheet_target(xls_path:Path, sheet_name:str)->Path|None:
    parent=xls_path.parent
    cands=[parent/sheet_name, parent/normalize_sheet_filename(sheet_name)]
    for c in cands:
        if c.exists() and c.is_file(): return c
    # single-table .xls often uses base name; search known BTBF-ish extensions
    stem=xls_path.stem
    for ext in ['.btb','.tbl','.txb','.subtitles','.spb','.trb','.mtb']:
        c=parent/(stem+ext)
        if c.exists(): return c
    return None

def btbf_meta(b:bytes):
    if b[:4]!=b'BTBF' or len(b)<0x30: raise ValueError('not BTBF')
    vals=struct.unpack_from('<11I',b,4)
    # file_size, header_size, data_size, label_start, label_size, text_start, text_size, record_size, count, unk1, unk2
    keys=['file_size','header_size','data_size','label_start','label_size','text_start','text_size','record_size','count','unk1','unk2']
    return dict(zip(keys,vals))

def signed_or_unsigned_equal(x, u):
    try: xi=int(round(float(x)))
    except: return False
    return xi==u or (xi<0 and (xi & 0xffffffff)==u)

def validate_sheet_layout(xls_path:Path,sheet_name:str,cells:dict,target:Path):
    mat=sheet_matrix(cells)
    b=target.read_bytes(); m=btbf_meta(b)
    if not mat: return {'ok':True,'empty':True,'target':str(target)}
    nrows=len(mat)-1; ncols=len(mat[0]); fcount=m['record_size']//4
    vcount=ncols-fcount
    headers=mat[0]
    problems=[]
    if m['record_size']%4: problems.append('record_size not divisible by4')
    if vcount<0: problems.append(f'negative virtual count {vcount}')
    if nrows!=m['count']: problems.append(f'rows {nrows} != count {m["count"]}')
    if m['data_size']!=m['record_size']*m['count']: problems.append('data_size mismatch')
    if m['label_start']!=0x30+m['data_size']: problems.append('label_start mismatch')
    if m['text_start']!=((m['label_start']+m['label_size']+1)&~1): problems.append('text_start mismatch')
    if len(b)!=m['text_start']+m['text_size']: problems.append('file length mismatch')
    # pointer header counts and xls->binary pointer equality
    if vcount>=0:
        v_text=sum(1 for h in headers[:vcount] if h=='Text')
        v_label=sum(1 for h in headers[:vcount] if h=='Label')
        p_text=[];p_label=[]
        for c,h in enumerate(headers[vcount:],start=vcount):
            if h=='Text Pntr': p_text.append(c)
            elif h=='Label Pntr': p_label.append(c)
        if v_text!=len(p_text): problems.append(f'Text virtual {v_text} != ptr {len(p_text)}')
        if v_label!=len(p_label): problems.append(f'Label virtual {v_label} != ptr {len(p_label)}')
        mism=0; checked=0
        for r in range(1,min(len(mat), 50)):
            for c in p_text+p_label:
                fidx=c-vcount
                u=struct.unpack_from('<I',b,0x30+(r-1)*m['record_size']+4*fidx)[0]
                x=mat[r][c] if c<len(mat[r]) else ''
                if x!='':
                    checked+=1
                    if not signed_or_unsigned_equal(x,u): mism+=1
        if mism: problems.append(f'pointer numeric mismatch {mism}/{checked}')
    return {'ok':not problems,'problems':problems,'target':str(target),'rows':nrows,'cols':ncols,'vcount':vcount,'fcount':fcount}

def read_utf16z(block:bytes, ptr:int)->str|None:
    if ptr<0 or ptr>=len(block): return None
    # pointers should be even, but tolerate odd by scanning pairs from ptr
    end=ptr
    while end+1<len(block):
        if block[end]==0 and block[end+1]==0: break
        end+=2
    raw=block[ptr:end]
    return raw.decode('utf-16le','replace')

def text_layout(mat, meta):
    if not mat: return [],[],-1
    ncols=len(mat[0]); fcount=meta['record_size']//4; vcount=ncols-fcount
    headers=mat[0]
    v_text=[c for c,h in enumerate(headers[:vcount]) if h=='Text']
    p_text=[c for c,h in enumerate(headers[vcount:],start=vcount) if h=='Text Pntr']
    return v_text,p_text,vcount

def sheet_text_changes(cells:dict, target:Path):
    mat=sheet_matrix(cells); b=target.read_bytes(); m=btbf_meta(b)
    if not mat: return []
    v_text,p_text,vcount=text_layout(mat,m)
    if len(v_text)!=len(p_text): raise ValueError('text column/pointer mismatch')
    oldblock=b[m['text_start']:m['text_start']+m['text_size']]
    changes=[]
    for r in range(1,len(mat)):
        for k,(vc,pc) in enumerate(zip(v_text,p_text)):
            fidx=pc-vcount; ptr=struct.unpack_from('<I',b,0x30+(r-1)*m['record_size']+4*fidx)[0]
            old=read_utf16z(oldblock,ptr)
            new=mat[r][vc] if vc<len(mat[r]) else ''
            if not isinstance(new,str): new=str(new)
            # invalid/sentinel pointer is represented as an empty virtual string
            oldcmp='' if old is None else old
            if oldcmp!=new:
                changes.append((r,k,oldcmp,new,ptr))
    return changes

def repack_btbf_from_sheet(cells:dict,target:Path,out:Path):
    mat=sheet_matrix(cells); b=target.read_bytes(); m=btbf_meta(b)
    if not mat:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(b); return {'changed':False,'text_changes':0,'old_size':len(b),'new_size':len(b)}
    v_text,p_text,vcount=text_layout(mat,m)
    changes=sheet_text_changes(cells,target)
    if not changes:
        out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(b); return {'changed':False,'text_changes':0,'old_size':len(b),'new_size':len(b)}
    data=bytearray(b[0x30:m['label_start']])
    # Keep label block and its alignment padding byte(s) exactly as-is.
    labels_and_pad=b[m['label_start']:m['text_start']]
    oldblock=b[m['text_start']:m['text_start']+m['text_size']]
    newblock=bytearray()
    for r in range(1,len(mat)):
        for vc,pc in zip(v_text,p_text):
            fidx=pc-vcount
            roff=(r-1)*m['record_size']+4*fidx
            origptr=struct.unpack_from('<I',data,roff)[0]
            text=mat[r][vc] if vc<len(mat[r]) else ''
            if not isinstance(text,str): text=str(text)
            if (origptr==0xFFFFFFFF or origptr>=m['text_size']) and text=='':
                # Preserve null/sentinel pointer semantics.
                continue
            ptr=len(newblock)
            struct.pack_into('<I',data,roff,ptr)
            newblock += text.encode('utf-16le') + b'\x00\x00'
    header=bytearray(b[:0x30])
    new_size=m['text_start']+len(newblock)
    struct.pack_into('<I',header,0x04,new_size)
    struct.pack_into('<I',header,0x1C,len(newblock))
    nb=bytes(header)+bytes(data)+labels_and_pad+bytes(newblock)
    if len(nb)!=new_size: raise AssertionError((len(nb),new_size,target))
    out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(nb)
    # Verify every valid text pointer decodes exactly to the workbook cell.
    nm=btbf_meta(nb); block=nb[nm['text_start']:]
    for r in range(1,len(mat)):
        for vc,pc in zip(v_text,p_text):
            fidx=pc-vcount; ptr=struct.unpack_from('<I',nb,0x30+(r-1)*nm['record_size']+4*fidx)[0]
            text=mat[r][vc] if vc<len(mat[r]) else ''
            if not isinstance(text,str): text=str(text)
            if ptr==0xFFFFFFFF or ptr>=nm['text_size']:
                if text!='': raise AssertionError(f'null ptr but text at {target} row{r}')
            else:
                got=read_utf16z(block,ptr)
                if got!=text: raise AssertionError(f'text verify failed {target} row{r}: {got!r}!={text!r}')
    return {'changed':True,'text_changes':len(changes),'old_size':len(b),'new_size':len(nb)}

def parse_index(index_bytes:bytes):
    ents=[]; pos=0; seen=set()
    while True:
        if pos in seen or pos+16>len(index_bytes): raise ValueError('bad index chain')
        seen.add(pos)
        nxt,off,sz,h=struct.unpack_from('<IIII',index_bytes,pos)
        try:end=index_bytes.index(0,pos+16)
        except ValueError: raise ValueError('unterminated index name')
        name=index_bytes[pos+16:end].decode('ascii')
        ents.append({'pos':pos,'next':nxt,'offset':off,'size':sz,'hash':h,'name':name})
        if nxt==0: break
        pos=nxt
    return ents

def rebuild_crowd_index(folder:Path,outfolder:Path):
    ib=(folder/'index.fs').read_bytes(); ents=parse_index(ib)
    idx=bytearray(ib); crowd=bytearray(); details=[]
    for e in ents:
        while len(crowd)%4: crowd.append(0)
        off=len(crowd)
        src=outfolder/e['name']
        if not src.exists(): src=folder/e['name']
        fb=src.read_bytes(); crowd+=fb
        struct.pack_into('<I',idx,e['pos']+4,off)
        struct.pack_into('<I',idx,e['pos']+8,len(fb))
        details.append((e['name'],off,len(fb)))
    while len(crowd)%4: crowd.append(0)
    (outfolder/'crowd.fs').write_bytes(crowd)
    (outfolder/'index.fs').write_bytes(idx)
    # Round-trip index validation
    ents2=parse_index(bytes(idx))
    for e,d in zip(ents2,details):
        name,off,sz=d
        if (e['name'],e['offset'],e['size'])!=(name,off,sz): raise AssertionError('index verify')
        built=(outfolder/name).read_bytes() if (outfolder/name).exists() else (folder/name).read_bytes()
        if crowd[off:off+sz]!=built: raise AssertionError(f'crowd verify {name}')
    return {'entries':len(ents),'old_crowd_size':(folder/'crowd.fs').stat().st_size,'new_crowd_size':len(crowd)}

def repack_tree(root:Path,outroot:Path):
    if outroot.exists(): shutil.rmtree(outroot)
    shutil.copytree(root,outroot)
    stats={'sheets':0,'files_changed':0,'text_changes':0,'binary_results':[],'archives':[]}
    # Apply every edited xls except the explicit English backup.
    for xp in sorted(root.rglob('*.xls')):
        if xp.name.lower()=='crowd_en.xls': continue
        wb=parse_biff(xp)
        for sh,cells in wb.items():
            stats['sheets']+=1
            target=resolve_sheet_target(xp,sh)
            if target is None: raise FileNotFoundError(f'no target for {xp}::{sh}')
            rel=target.relative_to(root); out=outroot/rel
            res=repack_btbf_from_sheet(cells,target,out)
            if res['changed']:
                stats['files_changed']+=1; stats['text_changes']+=res['text_changes']
                stats['binary_results'].append({'file':str(rel),**res})
    # Rebuild every crowd/index archive pair using rebuilt components.
    for idx in sorted(root.rglob('index.fs')):
        folder=idx.parent; rel=folder.relative_to(root); of=outroot/rel
        ar=rebuild_crowd_index(folder,of); stats['archives'].append({'folder':str(rel),**ar})
    return stats
