#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse,csv,io,re,shutil,struct,sys,zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

BASE_TITLE_ID='0004001000022800'
UPDATE_TITLE_ID='0004000E00022800'
LANGS=['EU_English','EU_French','EU_German','EU_Spanish','EU_Italian','EU_Dutch','EU_Portuguese','EU_Russian']
U32_NONE=0xFFFFFFFF

def align(v,b): return (v+b-1)&~(b-1)

# ---- CXI/RomFS extractor ----
def read_cxi_bytes(path:Path):
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path,'r') as z:
            xs=[n for n in z.namelist() if n.lower().endswith('.cxi') and '00022800' in n]
            if not xs: xs=[n for n in z.namelist() if n.lower().endswith('.cxi')]
            if len(xs)!=1: raise ValueError(f'ZIP içinde uygun tek CXI bulunamadı ({len(xs)} aday).')
            return z.read(xs[0]),xs[0]
    return path.read_bytes(),path.name

def ncch_program_id(cxi):
    if len(cxi)<0x200 or cxi[0x100:0x104]!=b'NCCH': raise ValueError('NCCH/CXI başlığı bulunamadı.')
    return struct.unpack_from('<Q',cxi,0x118)[0]

def ncch_product_code(cxi): return cxi[0x150:0x160].split(b'\0',1)[0].decode('ascii','replace')

def extract_romfs_from_cxi(cxi:bytes,out:Path):
    ru,rsu=struct.unpack_from('<II',cxi,0x1B0); ro=ru*0x200; rs=rsu*0x200; rom=cxi[ro:ro+rs]
    if rom[:4]!=b'IVFC': raise ValueError('RomFS/IVFC bulunamadı.')
    l3=rom[0x1000:]
    if len(l3)<0x28 or struct.unpack_from('<I',l3,0)[0]!=0x28: raise ValueError('Decrypted/plaintext RomFS gerekli.')
    _,dho,dhl,dmo,dml,fho,fhl,fmo,fml,fdo=struct.unpack_from('<10I',l3,0)
    dmeta=l3[dmo:dmo+dml]; fmeta=l3[fmo:fmo+fml]
    def de(o):
        parent,sib,child,first,h,n=struct.unpack_from('<6I',dmeta,o); name=dmeta[o+0x18:o+0x18+n].decode('utf-16le') if n else ''
        return parent,sib,child,first,h,n,name
    def fe(o):
        parent,sib=struct.unpack_from('<II',fmeta,o); do,dl=struct.unpack_from('<QQ',fmeta,o+8); h,n=struct.unpack_from('<II',fmeta,o+0x18); name=fmeta[o+0x20:o+0x20+n].decode('utf-16le') if n else ''
        return parent,sib,do,dl,h,n,name
    out.mkdir(parents=True,exist_ok=True); sd=set(); sf=set(); count=0
    def walk(o,p):
        nonlocal count
        if o in sd:return
        sd.add(o);_,_,child,first,_,_,name=de(o); here=p/name if name else p; here.mkdir(parents=True,exist_ok=True)
        x=first
        while x!=U32_NONE:
            if x in sf:break
            sf.add(x);_,sib,do,dl,_,_,name=fe(x); (here/name).write_bytes(l3[fdo+do:fdo+do+dl]); count+=1; x=sib
        x=child
        while x!=U32_NONE:
            sib=de(x)[1];walk(x,here);x=sib
    walk(0,out)
    return {'title_id':f'{ncch_program_id(cxi):016X}','product_code':ncch_product_code(cxi),'files':count}

# ---- BMS reader/writer ----
def read_nstr(b:bytes,p:int):
    e=b.index(0,p); s=b[p:e].decode('utf-8'); q=e+1
    while q<len(b) and b[q]==0:q+=1
    return s,q

def read_utf16(b:bytes,p:int):
    if b[p:p+2]==b'\xff\xfe': endian='little';enc='utf-16le';q=p+2
    elif b[p:p+2]==b'\xfe\xff': endian='big';enc='utf-16be';q=p+2
    else: raise ValueError(f'UTF16 BOM yok @ {p:#x}')
    e=q
    while e+1<len(b) and b[e:e+2]!=b'\0\0':e+=2
    s=b[q:e].decode(enc); q=e+2
    while q<len(b) and b[q]==0:q+=1
    return s,q,endian

def write_nstr(s:str):
    x=s.encode('utf-8'); return x+b'\0'*(4-(len(x)%4))

def write_utf16(s:str,endian='little'):
    x=s.encode('utf-16le' if endian=='little' else 'utf-16be'); bom=b'\xff\xfe' if endian=='little' else b'\xfe\xff'
    # writer used by bms2json: BOM + payload + zero padding to 8 based on payload length
    return bom+x+b'\0'*(8-(len(x)%8))

@dataclass
class BMSMEntry:
    label:str; source_label:str; message:str; x_scale:str; y_scale:str; secondary_source_label:str; endian:str='little'

def parse_bmsm(path:Path|bytes):
    b=path if isinstance(path,bytes) else path.read_bytes(); n,string_count=struct.unpack_from('<II',b,0); p=8; out=[]
    for _ in range(n):
        label,p=read_nstr(b,p); src,p=read_nstr(b,p); msg,p,endian=read_utf16(b,p); xs,p=read_nstr(b,p); ys,p=read_nstr(b,p); sec,p=read_nstr(b,p)
        out.append(BMSMEntry(label,src,msg,xs,ys,sec,endian))
    return out,string_count

def build_bmsm(entries,string_count=6):
    out=bytearray(struct.pack('<II',len(entries),string_count))
    for e in entries:
        out+=write_nstr(e.label);out+=write_nstr(e.source_label);out+=write_utf16(e.message,e.endian);out+=write_nstr(e.x_scale);out+=write_nstr(e.y_scale);out+=write_nstr(e.secondary_source_label)
    return bytes(out)

@dataclass
class BMSSEntry:
    label:str; max_width:str; unk1:str; font_path:str; fore_color:str; back_color:str; x_scale:str; y_scale:str; x_pos:str; y_pos:str; unk2:str; unk3:str; unk4:str

def parse_bmss(path:Path):
    b=path.read_bytes();n,sc=struct.unpack_from('<II',b,0);p=8;out=[]
    for _ in range(n):
        vals=[]
        for __ in range(sc): s,p=read_nstr(b,p);vals.append(s)
        if sc>=13: out.append(BMSSEntry(*vals[:13]))
    return out

# ---- BCFNT ----
@dataclass
class FontInfo:
    char_to_index:dict[int,int]; widths:dict[int,tuple[int,int,int]]; default_char_width:int

def parse_bcfnt(b:bytes):
    if b[:4] not in (b'CFNT',b'CFNU'): raise ValueError('BCFNT/CFNT sihri yok')
    finf=b.find(b'FINF');cwdh=b.find(b'CWDH');cmaps=[i for i in range(len(b)) if b.startswith(b'CMAP',i)]
    if min(finf,cwdh)<0 or not cmaps: raise ValueError('Font bölümleri eksik')
    # default glyph width from FINF char width triplet (offset convention varies); safer use first CWDH advance fallback
    start,end=struct.unpack_from('<HH',b,cwdh+8); widths={}
    p=cwdh+0x10
    for idx in range(start,end+1):
        if p+3>len(b):break
        left=struct.unpack_from('<b',b,p)[0];gw=b[p+1];adv=b[p+2];widths[idx]=(left,gw,adv);p+=3
    c2i={}
    for c in cmaps:
        first,last=struct.unpack_from('<HH',b,c+8);typ=struct.unpack_from('<H',b,c+0x0C)[0]
        if typ==0:
            base=struct.unpack_from('<H',b,c+0x14)[0]
            for cp in range(first,last+1):c2i[cp]=base+(cp-first)
        elif typ==1:
            p=c+0x14
            for cp in range(first,last+1):
                idx=struct.unpack_from('<H',b,p)[0];p+=2
                if idx!=0xFFFF:c2i[cp]=idx
        elif typ==2:
            cnt=struct.unpack_from('<H',b,c+0x14)[0];p=c+0x16
            for _ in range(cnt):cp,idx=struct.unpack_from('<HH',b,p);p+=4;c2i[cp]=idx
    default=next(iter(widths.values()))[2] if widths else 16
    return FontInfo(c2i,widths,default)

def morton8(x,y): return ((x&1)|((y&1)<<1)|((x&2)<<1)|((y&2)<<2)|((x&4)<<2)|((y&4)<<3))

def _tglp_meta(b,t):
    cw,ch,base,maxw=struct.unpack_from('<4B',b,t+8);ss=struct.unpack_from('<I',b,t+0x0C)[0];sc,fmt,cols,rows,sw,sh=struct.unpack_from('<6H',b,t+0x10);ptr=struct.unpack_from('<I',b,t+0x1C)[0]
    return cw,ch,base,maxw,ss,sc,fmt,cols,rows,sw,sh,ptr

def decode_glyph(b,t,idx):
    cw,ch,base,maxw,ss,sc,fmt,cols,rows,sw,sh,ptr=_tglp_meta(b,t)
    if fmt!=9: raise ValueError('Yalnızca LA4 (format 9) destekleniyor.')
    per=cols*rows;sheet=idx//per;slot=idx%per;slotw=sw//cols;sloth=sh//rows;x0=(slot%cols)*slotw;y0=(slot//cols)*sloth
    raw=b[ptr+sheet*ss:ptr+(sheet+1)*ss]; tiles=sw//8
    lum=[[0]*slotw for _ in range(sloth)];alp=[[0]*slotw for _ in range(sloth)]
    for yy in range(sloth):
      y=y0+yy
      for xx in range(slotw):
        x=x0+xx;tile=(y//8)*tiles+(x//8);pos=tile*64+morton8(x&7,y&7);v=raw[pos];lum[yy][xx]=v>>4;alp[yy][xx]=v&15
    return lum,alp

def write_glyph(buf,t,idx,lum,alp):
    cw,ch,base,maxw,ss,sc,fmt,cols,rows,sw,sh,ptr=_tglp_meta(buf,t);per=cols*rows;sheet=idx//per;slot=idx%per;slotw=sw//cols;sloth=sh//rows;x0=(slot%cols)*slotw;y0=(slot//cols)*sloth;tiles=sw//8
    for yy in range(min(sloth,len(alp))):
      y=y0+yy
      for xx in range(min(slotw,len(alp[yy]))):
        x=x0+xx;tile=(y//8)*tiles+(x//8);pos=ptr+sheet*ss+tile*64+morton8(x&7,y&7);buf[pos]=((lum[yy][xx]&15)<<4)|(alp[yy][xx]&15)

def bbox(mask):
    pts=[(x,y) for y,row in enumerate(mask) for x,v in enumerate(row) if v]
    if not pts:return None
    xs=[x for x,y in pts];ys=[y for x,y in pts];return min(xs),min(ys),max(xs)+1,max(ys)+1

def copy_g(g): return ([r[:] for r in g[0]],[r[:] for r in g[1]])
def erase(l,a,box):
    x0,y0,x1,y1=box
    for y in range(max(0,y0),min(len(a),y1)):
      for x in range(max(0,x0),min(len(a[0]),x1)):l[y][x]=a[y][x]=0

def overlay(dl,da,sl,sa,dx,dy,box):
    x0,y0,x1,y1=box;h=len(da);w=len(da[0])
    for sy in range(y0,y1):
      ty=sy+dy
      if not 0<=ty<h:continue
      for sx in range(x0,x1):
        tx=sx+dx
        if not 0<=tx<w:continue
        da[ty][tx]=max(da[ty][tx],sa[sy][sx]);dl[ty][tx]=max(dl[ty][tx],sl[sy][sx])

def breve(l,a,cx,top,width):
    h=len(a);w=len(a[0]);half=max(3,width//2)
    for x in range(cx-half,cx+half+1):
      if not 0<=x<w:continue
      norm=abs(x-cx)/max(1,half);y=int(round(top+max(2,h//18)*(1-norm*norm)))
      for yy in range(y-1,y+2):
        if 0<=yy<h:a[yy][x]=15;l[yy][x]=max(l[yy][x],12)

def patch_turkish_font(b:bytes):
    info=parse_bcfnt(b); needed='ĞğİıŞş'
    if all(ord(c) in info.char_to_index for c in needed):return b
    t=b.find(b'TGLP');cwdh=b.find(b'CWDH');finf=b.find(b'FINF');cmaps=[i for i in range(len(b)) if b.startswith(b'CMAP',i)]
    if min(t,cwdh,finf)<0 or not cmaps:raise ValueError('Font blokları bulunamadı')
    cw,ch,base,maxw,ss,sc,fmt,cols,rows,sw,sh,ptr=_tglp_meta(b,t)
    if fmt!=9:raise ValueError('LA4 olmayan font')
    cap=sc*cols*rows;first=max(info.char_to_index.values())+1;need=len(needed);extra=max(0,first+need-cap);add=(extra+cols*rows-1)//(cols*rows)
    ins=b'\0'*(ss*add);buf=bytearray(b[:cwdh]+ins+b[cwdh:]);newcwdh=cwdh+len(ins)
    struct.pack_into('<I',buf,t+4,struct.unpack_from('<I',b,t+4)[0]+len(ins));struct.pack_into('<H',buf,t+0x10,sc+add)
    cur=parse_bcfnt(bytes(buf)); src={c:cur.char_to_index[ord(c)] for c in 'GgIiSsCcÇç'}; glyph={c:decode_glyph(bytes(buf),t,i) for c,i in src.items()}
    made={}
    for out,basech in [('Ğ','G'),('ğ','g')]:
      l,a=copy_g(glyph[basech]);bb=bbox(a) or (0,0,len(a[0])//2,len(a)*3//4);cx=(bb[0]+bb[2])//2;top=max(1,bb[1]-max(4,len(a)//10));breve(l,a,cx,top,max(8,(bb[2]-bb[0])//2));made[out]=(l,a)
    l,a=copy_g(glyph['i']);bb=bbox(a)
    if bb: erase(l,a,(0,0,len(a[0]),max(1,bb[1]+len(a)//3)))
    made['ı']=(l,a)
    l,a=copy_g(glyph['I']);bb=bbox(a) or (0,0,len(a[0])//2,len(a)*3//4);cx=(bb[0]+bb[2])//2;cy=max(2,bb[1]-max(3,len(a)//12))
    for yy in range(max(0,cy-2),min(len(a),cy+3)):
      for xx in range(max(0,cx-2),min(len(a[0]),cx+3)):
        if (xx-cx)**2+(yy-cy)**2<=4:a[yy][xx]=15;l[yy][xx]=15
    made['İ']=(l,a)
    for out,basech,cedch,ref in [('Ş','S','Ç','C'),('ş','s','ç','c')]:
      l,a=copy_g(glyph[basech]);cl,ca=glyph[cedch];rb=bbox(glyph[ref][1]) or (0,0,len(a[0])//2,len(a)*3//4);cb=bbox([[v if y>=rb[3]-1 else 0 for v in row] for y,row in enumerate(ca)]);sb=bbox(a) or rb
      if cb: overlay(l,a,cl,ca,(sb[0]+sb[2]-cb[0]-cb[2])//2,min(len(a)-1,sb[3]-1)-cb[1],cb)
      made[out]=(l,a)
    newmap={}
    for j,c in enumerate(needed): idx=first+j;write_glyph(buf,t,idx,*made[c]);newmap[ord(c)]=idx
    # rebuild CWDH
    start,end=struct.unpack_from('<HH',buf,newcwdh+8); rec=bytearray(buf[newcwdh+0x10:newcwdh+0x10+(end-start+1)*3]); swc={'Ğ':'G','ğ':'g','İ':'I','ı':'i','Ş':'S','ş':'s'}
    for c in needed:
      left,gw,adv=cur.widths[cur.char_to_index[ord(swc[c])]];rec+=struct.pack('<bBB',left,gw,adv)
    csize=align(0x10+len(rec),4);cblk=bytearray(csize);cblk[:0x10]=buf[newcwdh:newcwdh+0x10];struct.pack_into('<I',cblk,4,csize);struct.pack_into('<H',cblk,0x0A,first+need-1);struct.pack_into('<I',cblk,0x0C,0);cblk[0x10:0x10+len(rec)]=rec
    shifted=[x+len(ins) for x in cmaps]; blocks=[]
    for p in shifted:
      sz=struct.unpack_from('<I',buf,p+4)[0];blocks.append(bytearray(buf[p:p+sz]))
    # append a new scan CMAP instead of requiring last existing one to be scan
    scan=bytearray(align(0x16+4*len(newmap),4));scan[:4]=b'CMAP';struct.pack_into('<I',scan,4,len(scan));struct.pack_into('<HHH',scan,8,min(newmap),max(newmap),2);struct.pack_into('<H',scan,0x0E,0);struct.pack_into('<I',scan,0x10,0);struct.pack_into('<H',scan,0x14,len(newmap));q=0x16
    for cp,idx in sorted(newmap.items()):struct.pack_into('<HH',scan,q,cp,idx);q+=4
    blocks.append(scan)
    rebuilt=bytearray(buf[:newcwdh])+cblk; positions=[]
    for bl in blocks:positions.append(len(rebuilt));rebuilt+=bl
    for i,p in enumerate(positions):struct.pack_into('<I',rebuilt,p+0x10,positions[i+1]+8 if i+1<len(positions) else 0)
    struct.pack_into('<I',rebuilt,finf+0x14,newcwdh+8);struct.pack_into('<I',rebuilt,finf+0x18,positions[0]+8);struct.pack_into('<I',rebuilt,0x0C,len(rebuilt))
    chk=parse_bcfnt(bytes(rebuilt));miss=[c for c in needed if ord(c) not in chk.char_to_index]
    if miss:raise ValueError('Font yaması doğrulanamadı: '+''.join(miss))
    return bytes(rebuilt)

def token_multiset(s):
    # Preserve all bracket placeholders/tags and PUA button glyphs.
    tags=re.findall(r'\[[^\]]+\]',s); pua=[c for c in s if 0xE000<=ord(c)<=0xF8FF]; return sorted(tags+pua)

def export_csv(romfs:Path,out:Path):
    base=romfs/'message'/'EU_English'/'message'; files=sorted(base.rglob('*.bmsm')); rows=[]
    parsed={}
    for lang in LANGS:
      lb=romfs/'message'/lang/'message';parsed[lang]={}
      for f in files:
        rel=f.relative_to(base); parsed[lang][str(rel)]=parse_bmsm(lb/rel)[0]
    for rel in [str(f.relative_to(base)) for f in files]:
      ens=parsed['EU_English'][rel]
      for idx,e in enumerate(ens):
        row={'File':rel,'EntryIndex':idx,'Label':e.label,'SourceLabel':e.source_label,'XScale':e.x_scale,'YScale':e.y_scale,'SecondarySourceLabel':e.secondary_source_label}
        for lang in LANGS:
          le=parsed[lang][rel][idx];row[lang]=le.message
        row['Turkish']='';rows.append(row)
    with open(out,'w',encoding='utf-8-sig',newline='') as f:
      w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(f'{len(rows)} kayıt -> {out}')

def load_csv(p):return list(csv.DictReader(open(p,encoding='utf-8-sig')))

def validate_csv(p):
    rows=load_csv(p);errs=[];miss=0
    for n,r in enumerate(rows,2):
      en=r['EU_English'];tr=r['Turkish']
      if en.strip() and not tr.strip():miss+=1;continue
      if tr and token_multiset(en)!=token_multiset(tr):errs.append(f'satır {n}: kontrol/placeholder uyuşmazlığı {r["File"]}:{r["Label"]}')
    print('Eksik Türkçe:',miss);print('Kontrol/placeholder hatası:',len(errs))
    for x in errs[:30]:print(' -',x)
    return miss,errs

def build_patch(romfs:Path,csvp:Path,out:Path,all_languages=True,title_id=BASE_TITLE_ID,allow_incomplete=False):
    rows=load_csv(csvp);miss,errs=validate_csv(csvp)
    if errs:raise SystemExit('CSV kontrol/placeholder doğrulaması başarısız; yama oluşturulmadı.')
    if miss and not allow_incomplete:raise SystemExit('CSV içinde eksik Türkçe var; --allow-incomplete ile eksik satırları İngilizce bırakabilirsin.')
    root=out/'luma'/'titles'/title_id/'romfs'; msgroot=root/'message';
    by={}
    for r in rows:by.setdefault(r['File'],[]).append(r)
    source_base=romfs/'message'/'EU_English'/'message'; targets=LANGS if all_languages else ['EU_English']
    fallback_count=0
    for rel,rr in by.items():
      orig,sc=parse_bmsm(source_base/rel)
      if len(orig)!=len(rr):raise ValueError(f'Kayıt sayısı uyuşmuyor: {rel}')
      expected=[]
      for i,(e,r) in enumerate(zip(orig,rr)):
        if e.label!=r['Label']:raise ValueError(f'Etiket/sıra uyuşmuyor: {rel} #{i}')
        text=r['Turkish'] if r['Turkish'].strip() else r['EU_English']
        if not r['Turkish'].strip() and r['EU_English'].strip(): fallback_count+=1
        e.message=text; expected.append(text)
      payload=build_bmsm(orig,sc)
      chk,_=parse_bmsm(payload)
      if [e.message for e in chk]!=expected:raise ValueError('BMSM roundtrip başarısız: '+rel)
      for lang in targets:
        dest=msgroot/lang/'message'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(payload)
    fsrc=romfs/'font'/'LA4';fdst=root/'font'/'LA4';fdst.mkdir(parents=True,exist_ok=True)
    for p in fsrc.glob('*.bcfnt'):
      q=fdst/p.name;q.write_bytes(patch_turkish_font(p.read_bytes()))
    print('LayeredFS:',root)
    print('İngilizce bırakılan eksik kayıt:',fallback_count)

def main():
    ap=argparse.ArgumentParser(description='StreetPass Mii Plaza EUR update BMSM Türkçe aracı')
    sp=ap.add_subparsers(dest='cmd',required=True)
    a=sp.add_parser('extract');a.add_argument('input');a.add_argument('--out',default='mii_update_romfs')
    a=sp.add_parser('export');a.add_argument('romfs');a.add_argument('--csv',default='mii_update_all_languages.csv')
    a=sp.add_parser('validate');a.add_argument('csv')
    a=sp.add_parser('build');a.add_argument('romfs');a.add_argument('csv');a.add_argument('--out',default='patch');a.add_argument('--english-only',action='store_true');a.add_argument('--allow-incomplete',action='store_true')
    args=ap.parse_args()
    if args.cmd=='extract':
      cxi,name=read_cxi_bytes(Path(args.input));info=extract_romfs_from_cxi(cxi,Path(args.out));print(name,info)
    elif args.cmd=='export':export_csv(Path(args.romfs),Path(args.csv))
    elif args.cmd=='validate':validate_csv(Path(args.csv))
    elif args.cmd=='build':build_patch(Path(args.romfs),Path(args.csv),Path(args.out),not args.english_only,allow_incomplete=args.allow_incomplete)
if __name__=='__main__':main()
