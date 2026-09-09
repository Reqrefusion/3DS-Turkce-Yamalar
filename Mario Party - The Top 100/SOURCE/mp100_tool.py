#!/usr/bin/env python3
# Mario Party: The Top 100 (EUR) localization helper
# Pure Python: export multilingual MSBT -> CSV, validate Turkish, rebuild RZPK/ZDAT,
# generate Luma3DS LayeredFS tree, and patch the game's A4 BFFNT fonts for Turkish.
from __future__ import annotations
import argparse,csv,io,json,math,re,struct,sys,unicodedata,zipfile,zlib
from collections import Counter,defaultdict
from pathlib import Path

TITLE_ID='00040000001C4D00'
LANGS=['English','French','German','Spanish','Italian','Dutch']
TURKISH_CHARS='çÇöÖüÜğĞşŞıİ'
NEEDED_FONT_CHARS='ğĞşŞıİ'
TOKEN_RE=re.compile(r'(\{C:\d+:\d+:[0-9a-fA-F]*\}|\{E:\d+:\d+\}|\[(?:b(?:a|b|x|y|l|r|sl|c|h|p)|n\d+|mg\d+|\d+|_[A-Za-z0-9]+)\])')

def a4(x): return (x+3)&~3
def a16(x): return (x+15)&~15
def u16(b,o,e='<'): return struct.unpack_from(e+'H',b,o)[0]
def u32(b,o,e='<'): return struct.unpack_from(e+'I',b,o)[0]

# ---------------- RZPK / ZDAT ----------------
def rzpk_unpack(data:bytes):
    if data[:4]!=b'RZPK': raise ValueError('Not an RZPK/ZDAT archive')
    version,n,data_start,field10,name_size=struct.unpack_from('<5I',data,4)
    table=data_start-n*16
    names_blob=data[0x20:table]
    files=[]
    for i in range(n):
        name_off,usize,csize,rel=struct.unpack_from('<4I',data,table+i*16)
        end=names_blob.find(b'\0',name_off)
        if end<0: raise ValueError('Bad RZPK filename table')
        name=names_blob[name_off:end].decode('utf-8')
        comp=data[data_start+rel:data_start+rel+csize]
        raw=zlib.decompress(comp)
        if len(raw)!=usize: raise ValueError(f'RZPK size mismatch: {name}')
        files.append([name,raw,name_off])
    return {'version':version,'field10':field10,'name_size':name_size,'names_blob':names_blob,
            'data_start':data_start,'files':files,'orig_header':data[:0x20]}

def rzpk_pack(arc, replacements:dict[str,bytes]|None=None):
    replacements=replacements or {}
    files=[]
    for name,raw,name_off in arc['files']:
        raw=replacements.get(name,raw)
        comp=zlib.compress(raw,6) # originals use normal zlib (78 9C)
        files.append((name,raw,comp,name_off))
    n=len(files)
    names=arc['names_blob']
    data_start=0x20+len(names)+n*16
    if data_start%4: # normally already aligned; preserve simple RZPK layout
        names += b'\0'*(4-data_start%4); data_start=a4(data_start)
    out=bytearray(0x20)
    # field10 is not needed for extraction and behaves like an opaque per-archive value;
    # preserve it exactly from the donor archive.
    struct.pack_into('<4sIIIIIQ',out,0,b'RZPK',arc['version'],n,data_start,arc['field10'],len(names),0)
    out.extend(names)
    rel=0
    table=bytearray()
    payload=bytearray()
    for name,raw,comp,name_off in files:
        table += struct.pack('<4I',name_off,len(raw),len(comp),rel)
        payload += comp; rel += len(comp)
    out += table+payload
    return bytes(out)

# ---------------- MSBT ----------------
def msbt_sections(data:bytes):
    if data[:8]!=b'MsgStdBn': raise ValueError('Not MSBT')
    e='<' if data[8:10]==b'\xff\xfe' else '>'
    count=u16(data,0x0e,e)
    out=[]; off=0x20
    for _ in range(count):
        off=a16(off)
        magic=data[off:off+4].decode('ascii','replace')
        size=u32(data,off+4,e)
        out.append((magic,off,size,data[off:off+16],data[off+16:off+16+size]))
        off += 16+size
    return e,out

def decode_msbt_string(raw:bytes,e:str):
    units=[u16(raw,j,e) for j in range(0,len(raw)-1,2)]
    out=[]; j=0
    while j<len(units):
        u=units[j]
        if u==0: break
        if u==0x000e and j+3<len(units):
            grp,typ,alen=units[j+1:j+4]
            n=(alen+1)//2
            argunits=units[j+4:j+4+n]
            argbytes=b''.join(struct.pack(e+'H',x) for x in argunits)[:alen]
            out.append(f'{{C:{grp}:{typ}:{argbytes.hex()}}}'); j+=4+n; continue
        if u==0x000f and j+2<len(units):
            grp,typ=units[j+1:j+3]; out.append(f'{{E:{grp}:{typ}}}'); j+=3; continue
        if 0xD800<=u<=0xDBFF and j+1<len(units) and 0xDC00<=units[j+1]<=0xDFFF:
            cp=0x10000+((u-0xD800)<<10)+(units[j+1]-0xDC00); out.append(chr(cp)); j+=2
        else: out.append(chr(u)); j+=1
    return ''.join(out)

def encode_msbt_string(text:str,e:str):
    out=bytearray(); pos=0
    cre=re.compile(r'\{C:(\d+):(\d+):([0-9a-fA-F]*)\}|\{E:(\d+):(\d+)\}')
    for m in cre.finditer(text):
        out += text[pos:m.start()].encode('utf-16le' if e=='<' else 'utf-16be')
        if m.group(1) is not None:
            grp,typ=int(m.group(1)),int(m.group(2)); arg=bytes.fromhex(m.group(3))
            out += struct.pack(e+'HHHH',0x000e,grp,typ,len(arg))
            if len(arg)%2: arg += b'\0'
            out += arg if e=='<' else b''.join(arg[i:i+2][::-1] for i in range(0,len(arg),2))
        else:
            out += struct.pack(e+'HHH',0x000f,int(m.group(4)),int(m.group(5)))
        pos=m.end()
    out += text[pos:].encode('utf-16le' if e=='<' else 'utf-16be')
    out += struct.pack(e+'H',0)
    return bytes(out)

def parse_msbt(data:bytes):
    e,secs=msbt_sections(data)
    lbl=next(x for x in secs if x[0]=='LBL1'); txt=next(x for x in secs if x[0]=='TXT2')
    s=lbl[1]+16; groups=u32(data,s,e); labels={}
    for g in range(groups):
        cnt,rel=struct.unpack_from(e+'II',data,s+4+g*8); p=s+rel
        for _ in range(cnt):
            ln=data[p]; p+=1; lab=data[p:p+ln].decode('utf-8'); p+=ln
            idx=u32(data,p,e); p+=4; labels[lab]=idx
    t=txt[1]+16; count=u32(data,t,e)
    offs=[u32(data,t+4+4*i,e) for i in range(count)]
    texts=[]
    for i,rel in enumerate(offs):
        start=t+rel; end=t+offs[i+1] if i+1<count else txt[1]+16+txt[2]
        texts.append(decode_msbt_string(data[start:end],e))
    return e,labels,texts,secs

def patch_msbt(data:bytes, by_label:dict[str,str]):
    e,labels,texts,secs=parse_msbt(data)
    for lab,new in by_label.items():
        if lab not in labels: raise KeyError(f'MSBT label not found: {lab}')
        texts[labels[lab]]=new
    payload=bytearray(struct.pack(e+'I',len(texts)))
    off_base=4+4*len(texts); encoded=[]; cur=off_base
    for text in texts:
        raw=encode_msbt_string(text,e); encoded.append(raw); payload += struct.pack(e+'I',cur); cur+=len(raw)
    payload += b''.join(encoded)
    hdr=bytearray(data[:0x20]); out=bytearray(hdr)
    for magic,oldoff,oldsize,sh,pay in secs:
        while len(out)%16: out.append(0xAB)
        if magic=='TXT2': pay=bytes(payload)
        sh=bytearray(sh); struct.pack_into(e+'I',sh,4,len(pay)); out += sh+pay
    # preserve convention: whole file padded to 16 with AB, but header length includes padding.
    while len(out)%16: out.append(0xAB)
    struct.pack_into(e+'I',out,0x12,len(out))
    return bytes(out)

# ---------------- CSV ----------------
def read_lang_from_zip(zf:zipfile.ZipFile,lang:str):
    data=zf.read(f'romfs/mess/EU_{lang}.zdat'); arc=rzpk_unpack(data); d={}
    for name,raw,_ in arc['files']:
        if name.endswith('.msbt'):
            _,labels,texts,_=parse_msbt(raw); d[name]={lab:texts[idx] for lab,idx in labels.items()}
    return d

def observed_constraints(vals):
    vals=[v for v in vals if v is not None]
    lines=[v.split('\n') for v in vals]
    max_lines=max(map(len,lines),default=1)
    max_line_chars=max((len(x) for ls in lines for x in ls),default=0)
    max_total=max(map(len,vals),default=0)
    min_total=min(map(len,vals),default=0)
    return max_lines,max_line_chars,min_total,max_total

def export_csv(zip_path:Path,out_csv:Path):
    with zipfile.ZipFile(zip_path) as z:
        all_lang={lang:read_lang_from_zip(z,lang) for lang in LANGS}
    rows=[]
    for fn in sorted(all_lang['English']):
        labels=list(all_lang['English'][fn])
        for lang in LANGS[1:]:
            if set(labels)!=set(all_lang[lang][fn]): raise ValueError(f'Label mismatch: {fn} {lang}')
        for idx,lab in enumerate(labels):
            vals=[all_lang[L][fn][lab] for L in LANGS]
            ml,mch,mn,mx=observed_constraints(vals)
            rows.append({'file':fn,'label':lab,'index':idx,**{L:all_lang[L][fn][lab] for L in LANGS},
                         'Turkish':'','Notes':'','ObservedMaxLines':ml,'ObservedMaxLineChars':mch,
                         'ObservedMinTotalChars':mn,'ObservedMaxTotalChars':mx})
    fields=['file','label','index']+LANGS+['Turkish','Notes','ObservedMaxLines','ObservedMaxLineChars','ObservedMinTotalChars','ObservedMaxTotalChars']
    with open(out_csv,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    return len(rows)

def csv_rows(path:Path):
    with open(path,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def token_multiset(s):
    # Most control codes must stay byte-identical. C:2:1 is a localized inflection
    # payload (e.g. victory/victories), so compare its control signature while
    # allowing the embedded language text to change.
    out=Counter()
    for tok in TOKEN_RE.findall(s or ''):
        if tok.startswith('{C:2:1:'):
            out['{C:2:1:*}'] += 1
        else:
            out[tok] += 1
    return out

def pua_multiset(s):
    return Counter(ch for ch in (s or '') if 0xE000 <= ord(ch) <= 0xF8FF)

def validate_rows(rows, require_all=True):
    issues=[]
    for r in rows:
        tr=r.get('Turkish','')
        key=f"{r.get('file')}:{r.get('label')}"
        if not tr:
            if require_all: issues.append((key,'EMPTY','Turkish is empty'))
            continue
        en=r.get('English','')
        if token_multiset(en)!=token_multiset(tr):
            issues.append((key,'TOKENS',f"EN={dict(token_multiset(en))} TR={dict(token_multiset(tr))}"))
        if pua_multiset(en)!=pua_multiset(tr):
            issues.append((key,'ICONS',f"EN={dict(pua_multiset(en))} TR={dict(pua_multiset(tr))}"))
        vals=[r.get(L,'') for L in LANGS]
        ml,mch,_,mx=observed_constraints(vals)
        tlines=tr.split('\n'); tmax=max(map(len,tlines),default=0)
        if len(tlines)>ml: issues.append((key,'LINES',f'TR {len(tlines)} > observed {ml}'))
        if mch and tmax>math.ceil(mch*1.15): issues.append((key,'LINE_LEN',f'TR max line {tmax} > observed {mch}'))
        if mx and len(tr)>math.ceil(mx*1.25): issues.append((key,'TOTAL_LEN',f'TR {len(tr)} > observed {mx}'))
    return issues

# ---------------- Font patch ----------------
def decode_a4(data:bytes,w:int,h:int):
    from PIL import Image
    W=1<<(w-1).bit_length(); H=1<<(h-1).bit_length(); out=[0]*(W*H)
    for ty in range(H//8):
      for tx in range(W//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             if px>=w or py>=h: continue
             pos=(x3+x2*4+x*16+tx*64)+(y3*2+y2*8+y*32+ty*W*8)
             out[px+py*W]=((data[pos//2]>>((pos&1)*4))&15)*17
    im=Image.new('L',(W,H)); im.putdata(out); return im.crop((0,0,w,h))

def encode_a4(im):
    # inverse of decode_a4; quantizes to 4-bit alpha.
    w,h=im.size; W=1<<(w-1).bit_length(); H=1<<(h-1).bit_length(); pix=list(im.getdata())
    data=bytearray((W*H)//2)
    for ty in range(H//8):
      for tx in range(W//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             if px>=w or py>=h: a=0
             else: a=max(0,min(15,round(pix[px+py*w]/17)))
             pos=(x3+x2*4+x*16+tx*64)+(y3*2+y2*8+y*32+ty*W*8)
             bi=pos//2; sh=(pos&1)*4; data[bi] |= (a&15)<<sh
    return bytes(data[:(w*h+1)//2]) if W==w and H==h else bytes(data)

def bffnt_map_info(b:bytes):
    if b[:4]!=b'FFNT': raise ValueError('Not BFFNT')
    fin=struct.unpack_from('<4sI4B2H4B3I',b,0x14); tglp_off,cwdh_off,cmap_off=fin[-3:]
    t=struct.unpack_from('<4sI4BI6HI',b,tglp_off-8)
    info={'cell_w':t[2],'cell_h':t[3],'sheets':t[4],'sheet_size':t[6],'baseline':t[7],
          'fmt':t[8],'cols':t[9],'rows':t[10],'sheet_w':t[11],'sheet_h':t[12],'sheet_off':t[13],
          'cwdh_off':cwdh_off,'cmap_off':cmap_off}
    mapping={}; scan_sections=[]; off=cmap_off
    while off:
        p=off-8; magic,size,start,end,typ,res,nxt=struct.unpack_from('<4sI4HI',b,p); q=p+20
        if typ==0:
            base=u16(b,q)
            for cp in range(start,end+1): mapping[cp]=base+cp-start
        elif typ==1:
            for i,cp in enumerate(range(start,end+1)):
                v=u16(b,q+2*i)
                if v!=0xffff: mapping[cp]=v
        elif typ==2:
            cnt=u16(b,q); ent=[]
            for i in range(cnt):
                cp,idx=struct.unpack_from('<HH',b,q+2+4*i); mapping[cp]=idx; ent.append((cp,idx))
            scan_sections.append((p,size,start,end,typ,res,nxt,ent))
        off=nxt
    return info,mapping,scan_sections

def get_width_pos(b,idx,cwdh_off):
    off=cwdh_off
    while off:
        p=off-8; magic,size,start,end,nxt=struct.unpack_from('<4sI2HI',b,p)
        if start<=idx<=end: return p+16+3*(idx-start)
        off=nxt
    raise KeyError(f'No CWDH width for glyph {idx}')

def _bbox(arr,threshold=20):
    import numpy as np
    ys,xs=np.where(arr>threshold)
    if len(xs)==0:return (0,0,0,0)
    return (xs.min(),ys.min(),xs.max()+1,ys.max()+1)

def make_turkish_glyph(base_img, target:str, refs:dict[str,object]):
    from PIL import Image,ImageDraw
    import numpy as np
    im=base_img.copy(); A=np.array(im,dtype=np.uint8); h,w=A.shape
    if target in 'şŞ':
        ref=np.array(refs['ç' if target=='ş' else 'Ç'],dtype=np.uint8)
        plain=np.array(refs['c' if target=='ş' else 'C'],dtype=np.uint8)
        _,_,_,bottom=_bbox(plain)
        accent=np.zeros_like(ref); accent[max(0,bottom-1):,:]=ref[max(0,bottom-1):,:]
        # center accent under target's visible base to handle width differences.
        ys,xs=np.where(accent>20)
        if len(xs):
            ab=(xs.min(),ys.min(),xs.max()+1,ys.max()+1); tb=_bbox(A)
            shift=round(((tb[0]+tb[2])-(ab[0]+ab[2]))/2)
            shifted=np.zeros_like(accent)
            if shift>=0: shifted[:,shift:]=accent[:,:w-shift]
            else: shifted[:,:w+shift]=accent[:,-shift:]
            A=np.maximum(A,shifted)
        return Image.fromarray(A,'L')
    def _row_bands(arr, threshold=150):
        # Use the bright core rather than the soft outline/shadow. In these A4
        # fonts the grey outline of lowercase i bridges its dot and stem.
        has=(arr>threshold).any(axis=1); bands=[]; st=None
        for yy,on in enumerate(has):
            if on and st is None: st=yy
            elif not on and st is not None: bands.append((st,yy)); st=None
        if st is not None: bands.append((st,len(has)))
        return bands
    if target=='ı':
        bands=_row_bands(A)
        if len(bands)>=2:
            # Everything above the stem's bright core belongs to the dot and
            # its antialiasing/shadow. Preserve the stem from its core onward.
            stem_start=bands[1][0]
            A[:stem_start,:]=0
        else:
            A[:max(1,int(h*0.35)),:]=0
        return Image.fromarray(A,'L')
    if target=='İ':
        ri=np.array(refs['i'],dtype=np.uint8); bands=_row_bands(ri)
        if len(bands)>=2:
            stem_start=bands[1][0]
            dot_src=ri[:stem_start,:]
            ys,xs=np.where(dot_src>20)
            if len(xs):
                x0,x1=xs.min(),xs.max()+1; y0,y1=ys.min(),ys.max()+1
                dot=dot_src[y0:y1,x0:x1]
                tb=_bbox(A)
                dot_h,dot_w=dot.shape
                tx=round((tb[0]+tb[2]-dot_w)/2)
                # Leave a small gap above the capital stem while staying in-cell.
                ty=max(0,tb[1]-dot_h-max(1,round(h*0.035)))
                xlo=max(0,tx); ylo=max(0,ty); xhi=min(w,tx+dot_w); yhi=min(h,ty+dot_h)
                if xlo<xhi and ylo<yhi:
                    sx=xlo-tx; sy=ylo-ty
                    A[ylo:yhi,xlo:xhi]=np.maximum(A[ylo:yhi,xlo:xhi],dot[sy:sy+(yhi-ylo),sx:sx+(xhi-xlo)])
        return Image.fromarray(A,'L')
    if target in 'ğĞ':
        # Draw a compact breve above G/g. Use 4x supersampling for smooth A4 edges.
        scale=4; big=im.resize((w*scale,h*scale))
        draw=ImageDraw.Draw(big)
        bb=_bbox(A); cx=(bb[0]+bb[2])/2
        acc_w=max(6,round(w*0.28)); acc_h=max(3,round(h*0.10))
        # place at accent zone used by other accented Latin letters.
        y=max(0,round(h*0.02)); x0=round(cx-acc_w/2); x1=x0+acc_w
        box=(x0*scale,(y-acc_h//2)*scale,x1*scale,(y+acc_h)*scale)
        stroke=max(1,round(w*0.035))*scale
        # lower half of ellipse gives a breve-like cup.
        draw.arc(box,start=10,end=170,fill=255,width=stroke)
        big=big.resize((w,h))
        return big
    return im

def patch_bffnt_turkish(data:bytes):
    from PIL import Image
    b=bytearray(data); info,mapping,scans=bffnt_map_info(bytes(b))
    if info['fmt']!=0x0B: raise ValueError('Expected A4 BFFNT')
    targets={'ğ':'g','Ğ':'G','ş':'s','Ş':'S','ı':'i','İ':'I'}
    missing=[c for c in targets if ord(c) not in mapping]
    if not missing: return bytes(b),{}
    # last scan has many game-specific CJK entries in system/telop; pick six unique CJK entries.
    if not scans: raise ValueError('No scan CMAP to repurpose')
    p,size,start,end,typ,res,nxt,entries=scans[-1]
    byidx=defaultdict(list)
    for cp,idx in mapping.items(): byidx[idx].append(cp)
    donors=[(cp,idx) for cp,idx in entries if 0x4E00<=cp<=0x9FFF and len(byidx[idx])==1]
    if len(donors)<len(missing): raise ValueError('Not enough safe donor glyphs')
    donors=donors[:len(missing)]
    # decode all sheets
    sheets=[]
    for s in range(info['sheets']):
        st=info['sheet_off']+s*info['sheet_size']; raw=bytes(b[st:st+info['sheet_size']])
        sheets.append(decode_a4(raw,info['sheet_w'],info['sheet_h']))
    pitchx,pitchy=info['cell_w']+1,info['cell_h']+1; per=info['cols']*info['rows']
    def crop_idx(idx):
        sh=idx//per; r=idx%per; x=(r%info['cols'])*pitchx; y=(r//info['cols'])*pitchy
        return sheets[sh].crop((x,y,x+pitchx,y+pitchy)),(sh,x,y)
    refs={}
    for c in 'gGsSiIcCçÇ': refs[c]=crop_idx(mapping[ord(c)])[0]
    report={}
    replaced={cp:idx for cp,idx in entries}
    for target,(oldcp,donor_idx) in zip(missing,donors):
        base=targets[target]; base_idx=mapping[ord(base)]
        base_im,_=crop_idx(base_idx); new_im=make_turkish_glyph(base_im,target,refs)
        sh,x,y=crop_idx(donor_idx)[1]; sheets[sh].paste(new_im,(x,y))
        # donor width -> base width
        dpos=get_width_pos(bytes(b),donor_idx,info['cwdh_off']); bpos=get_width_pos(bytes(b),base_idx,info['cwdh_off'])
        b[dpos:dpos+3]=b[bpos:bpos+3]
        del replaced[oldcp]; replaced[ord(target)]=donor_idx
        report[target]={'glyph_index':donor_idx,'replaced_codepoint':f'U+{oldcp:04X}','base':base}
    # Rewrite same-sized scan table sorted by codepoint, preserving count and section size.
    newent=sorted(replaced.items())
    q=p+20; oldcnt=u16(b,q)
    if len(newent)!=oldcnt: raise AssertionError('scan entry count changed')
    struct.pack_into('<H',b,q,oldcnt)
    for i,(cp,idx) in enumerate(newent): struct.pack_into('<HH',b,q+2+4*i,cp,idx)
    # write sheets back in place
    for s,im in enumerate(sheets):
        raw=encode_a4(im)
        if len(raw)!=info['sheet_size']: raise AssertionError((len(raw),info['sheet_size']))
        st=info['sheet_off']+s*info['sheet_size']; b[st:st+info['sheet_size']]=raw
    # verify new map
    _,m2,_=bffnt_map_info(bytes(b))
    for c in missing:
        if ord(c) not in m2: raise AssertionError(f'font map failed for {c}')
    return bytes(b),report

def sarc_entries(raw:bytes):
    if raw[:4]!=b'SARC': raise ValueError('Not SARC')
    e='<' if raw[6:8]==b'\xff\xfe' else '>'
    hs=u16(raw,4,e); data_off=u32(raw,0x0c,e); sfat=hs; n=u16(raw,sfat+6,e); node=sfat+0x0c
    sfnt=node+n*16; names=sfnt+u16(raw,sfnt+4,e); out=[]
    for i in range(n):
        h,attr,st,en=struct.unpack_from(e+'4I',raw,node+i*16); no=(attr&0xffffff)*4
        p=names+no; q=raw.index(0,p); name=raw[p:q].decode('utf-8')
        out.append((name,data_off+st,data_off+en))
    return out

def patch_fonts_arc_p(ndcf:bytes):
    if ndcf[:4]!=b'NDCF': raise ValueError('Not NDCF fonts.arc.p')
    raw=zlib.decompress(ndcf[16:]); out=bytearray(raw); report={}
    for name,st,en in sarc_entries(raw):
        if name.endswith(('nsfont_system.bffnt','nsfont_telop.bffnt')):
            patched,rep=patch_bffnt_turkish(raw[st:en])
            if len(patched)!=en-st: raise AssertionError('BFFNT size changed')
            out[st:en]=patched; report[name]=rep
    comp=zlib.compress(bytes(out),6)
    hdr=bytearray(ndcf[:16]); struct.pack_into('<I',hdr,8,len(out)); struct.pack_into('<I',hdr,12,len(comp))
    return bytes(hdr)+comp,report

# ---------------- Build ----------------
def load_translations(rows):
    d=defaultdict(dict)
    for r in rows:
        if r.get('Turkish'): d[r['file']][r['label']]=r['Turkish']
    return d

def build_zdat(original:bytes,translations):
    arc=rzpk_unpack(original); repl={}
    for name,raw,_ in arc['files']:
        if name.endswith('.msbt') and name in translations:
            repl[name]=patch_msbt(raw,translations[name])
    packed=rzpk_pack(arc,repl)
    # self-check all files decompress and Turkish text roundtrips
    check=rzpk_unpack(packed)
    for name,raw,_ in check['files']:
        if name in translations:
            _,labels,texts,_=parse_msbt(raw)
            for lab,val in translations[name].items():
                if texts[labels[lab]]!=val: raise AssertionError(f'roundtrip failed {name}:{lab}')
    return packed

def build_layeredfs(zip_path:Path,csv_path:Path,out_dir:Path,all_eu=False,allow_missing=False,patch_font=True):
    rows=csv_rows(csv_path); issues=validate_rows(rows,require_all=not allow_missing)
    hard=[x for x in issues if x[1] in ('EMPTY','TOKENS')]
    if hard and not allow_missing:
        print(f'Validation failed with {len(hard)} hard issue(s). First 20:',file=sys.stderr)
        for x in hard[:20]: print('  ',x,file=sys.stderr)
        raise SystemExit(2)
    tr=load_translations(rows)
    root=out_dir/'luma'/'titles'/TITLE_ID/'romfs'; (root/'mess').mkdir(parents=True,exist_ok=True)
    targets=LANGS if all_eu else ['English']
    with zipfile.ZipFile(zip_path) as z:
        for lang in targets:
            orig=z.read(f'romfs/mess/EU_{lang}.zdat')
            (root/'mess'/f'EU_{lang}.zdat').write_bytes(build_zdat(orig,tr))
        font_report={}
        if patch_font:
            orig=z.read('romfs/font/fonts.arc.p'); patched,font_report=patch_fonts_arc_p(orig)
            (root/'font').mkdir(parents=True,exist_ok=True); (root/'font'/'fonts.arc.p').write_bytes(patched)
    report={'title_id':TITLE_ID,'targets':targets,'rows':len(rows),'translated':sum(bool(r.get('Turkish')) for r in rows),
            'validation_issues':[{'key':a,'type':b,'detail':c} for a,b,c in issues], 'font_patch':font_report}
    (out_dir/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    ap=argparse.ArgumentParser(description='Mario Party: The Top 100 EUR Turkish localization tool')
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('export');p.add_argument('zip',type=Path);p.add_argument('csv',type=Path)
    p=sub.add_parser('validate');p.add_argument('csv',type=Path);p.add_argument('--allow-missing',action='store_true')
    p=sub.add_parser('build');p.add_argument('zip',type=Path);p.add_argument('csv',type=Path);p.add_argument('out',type=Path)
    p.add_argument('--all-eu',action='store_true');p.add_argument('--allow-missing',action='store_true');p.add_argument('--no-font',action='store_true')
    a=ap.parse_args()
    if a.cmd=='export': print(f'Exported {export_csv(a.zip,a.csv)} rows -> {a.csv}')
    elif a.cmd=='validate':
        issues=validate_rows(csv_rows(a.csv),not a.allow_missing); print(json.dumps(issues,ensure_ascii=False,indent=2)); print('issues',len(issues))
    elif a.cmd=='build':
        rep=build_layeredfs(a.zip,a.csv,a.out,a.all_eu,a.allow_missing,not a.no_font); print(json.dumps(rep,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
