#!/usr/bin/env python3
import argparse,struct,csv,hashlib,statistics,sys
from pathlib import Path
from lz11_codec import decompress
from bffnt_patch_tr_v2 import parse,extract_glyph,TR_TARGETS,BASE_FOR,SACRIFICE
TR12='ÇçĞğİıÖöŞşÜü'

def nodes(dec):
    e='<' if dec[6:8]==b'\xff\xfe' else '>';hdr=struct.unpack_from(e+'H',dec,4)[0];hsz,n,m=struct.unpack_from(e+'HHI',dec,hdr+4);no=hdr+hsz;do=struct.unpack_from(e+'I',dec,12)[0]
    return e,[(struct.unpack_from(e+'IIII',dec,no+i*16),do) for i in range(n)]

def image_equal(a,b): return a.tobytes()==b.tobytes()

def glyph_byte_offsets(info,idx):
    si,ox,oy = __import__("bffnt_patch_tr_v2").glyph_origin(info,idx)
    base=info["dataoff"]+si*info["ss"]; out=set()
    from bffnt_patch_tr_v2 import nib_index
    for y in range(info["ch"]):
        for x in range(info["cw"]):
            ni=nib_index(ox+x,oy+y,info["sw"]); out.add(base+ni//2)
    return out

def bb(im): return im.getbbox() or (0,0,0,0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',required=True);ap.add_argument('--patched',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    o_root=Path(a.original);p_root=Path(a.patched); rows=[];fails=0;warns=0; patched_fonts=0
    for pp in sorted(p_root.rglob('*.Carc')):
        rel=pp.relative_to(p_root);op=o_root/rel
        if not op.exists(): rows.append([str(rel),'ARCHIVE_EXISTS','FAIL','orijinal bulunamadı']);fails+=1;continue
        try:o=decompress(op.read_bytes());m=decompress(pp.read_bytes())
        except Exception as ex:rows.append([str(rel),'LZ11','FAIL',str(ex)]);fails+=1;continue
        if len(o)!=len(m):rows.append([str(rel),'SARC_SIZE','FAIL',f'{len(o)} != {len(m)}']);fails+=1;continue
        on=nodes(o)[1];mn=nodes(m)[1]
        if len(on)!=len(mn):rows.append([str(rel),'NODE_COUNT','FAIL',f'{len(on)} != {len(mn)}']);fails+=1;continue
        for i,((oh,odo),(mh,mdo)) in enumerate(zip(on,mn)):
            if oh!=mh or odo!=mdo:
                rows.append([str(rel),f'NODE_META_{i}','FAIL','SARC node metadata değişti']);fails+=1;continue
            h,attr,st,en=oh;oa,ob=odo+st,odo+en;ma,mb=mdo+st,mdo+en;od=o[oa:ob];md=m[ma:mb]
            if od==md: continue
            if od[:4]!=b'FFNT' or md[:4]!=b'FFNT':
                rows.append([str(rel),f'NODE_{i}','FAIL','font dışı node değişti']);fails+=1;continue
            patched_fonts+=1
            oi,mi=parse(od),parse(md); om,mm=oi['mapping'],mi['mapping']
            miss=''.join(c for c in TR12 if ord(c) not in mm)
            if miss:
                rows.append([str(rel),f'FONT_{i}_TR12','FAIL','eksik='+miss]);fails+=1;continue
            # Determine newly assigned target glyphs.
            assigned={c:mm[ord(c)] for c in TR_TARGETS if ord(c) not in om}
            assigned_idxs=set(assigned.values())
            # Mapping must remain identical except added targets and consumed sacrifice codepoints.
            badmap=[]
            for cp,idx in om.items():
                if cp in SACRIFICE and idx in assigned_idxs: continue
                if mm.get(cp)!=idx: badmap.append((cp,idx,mm.get(cp)))
            for c,idx in assigned.items():
                if mm.get(ord(c))!=idx: badmap.append((ord(c),None,mm.get(ord(c))))
            if badmap:
                rows.append([str(rel),f'FONT_{i}_CMAP_PRESERVE','FAIL',str(badmap[:5])]);fails+=1
            else: rows.append([str(rel),f'FONT_{i}_CMAP_PRESERVE','PASS',f'{len(assigned)} yeni Türkçe eşleme'])
            # Width metrics: generated glyph must copy its base exactly; all untouched glyph widths must stay identical.
            badw=[]
            for idx,w in oi['widths'].items():
                if idx in assigned_idxs: continue
                if mi['widths'].get(idx)!=w: badw.append(idx)
            for c,idx in assigned.items():
                base=om[ord(BASE_FOR[c])]
                if mi['widths'].get(idx)!=oi['widths'].get(base): badw.append(idx)
            if badw:
                rows.append([str(rel),f'FONT_{i}_CWDH','FAIL','width farkı '+str(badw[:10])]);fails+=1
            else: rows.append([str(rel),f'FONT_{i}_CWDH','PASS','bearing/advance base karakterle uyumlu'])
            # Byte-level preservation: only consumed CMAP entries, target CWDH triples and target glyph texture bytes may change.
            allowed=set()
            byidx={idx:(cp,pos) for cp,idx,pos in oi['sparse'] if cp in SACRIFICE}
            for c,idx in assigned.items():
                if idx in byidx:
                    cp,pos=byidx[idx]; allowed.update(range(pos,pos+2))
                wp=oi['widthpos'].get(idx)
                if wp is not None: allowed.update(range(wp,wp+3))
                allowed.update(glyph_byte_offsets(oi,idx))
            diffs={k for k,(x,y) in enumerate(zip(od,md)) if x!=y}
            extra=diffs-allowed
            if extra:
                rows.append([str(rel),f'FONT_{i}_BYTE_PRESERVE','FAIL','izin dışı byte farkı '+str(sorted(extra)[:10])]);fails+=1
            else: rows.append([str(rel),f'FONT_{i}_BYTE_PRESERVE','PASS',f'{len(diffs)} değişen byte yalnız Türkçe slotlarında'])
            # Quality geometry.
            q=[]
            for c,idx in assigned.items():
                gim=extract_glyph(md,mi,idx); bim=extract_glyph(md,mi,mm[ord(BASE_FOR[c])]);
                if not gim.getbbox(): q.append(c+':boş');continue
                if image_equal(gim,bim): q.append(c+':base ile aynı')
            # dotless i must really be dotless and x-height-sized
            if 'ı' in assigned:
                di=extract_glyph(md,mi,assigned['ı']); ii=extract_glyph(md,mi,mm[ord('i')]);
                if image_equal(di,ii): q.append('ı:i ile aynı')
                tops=[bb(extract_glyph(md,mi,mm[ord(c)]))[1] for c in 'aceosuvx' if ord(c) in mm]
                if tops:
                    xt=statistics.median(tops); dt=bb(di)[1]
                    if abs(dt-xt)>3:q.append(f'ı:x-height top {dt}/{xt}')
            # Accent alignment to native European accents.
            if 'Ğ' in assigned and ord('Ä') in mm:
                if abs(bb(extract_glyph(md,mi,assigned['Ğ']))[1]-bb(extract_glyph(md,mi,mm[ord('Ä')]))[1])>2:q.append('Ğ:üst vurgu hizası')
            if 'ğ' in assigned and ord('ä') in mm:
                if abs(bb(extract_glyph(md,mi,assigned['ğ']))[1]-bb(extract_glyph(md,mi,mm[ord('ä')]))[1])>2:q.append('ğ:üst vurgu hizası')
            if 'İ' in assigned and ord('Ä') in mm:
                if abs(bb(extract_glyph(md,mi,assigned['İ']))[1]-bb(extract_glyph(md,mi,mm[ord('Ä')]))[1])>2:q.append('İ:nokta hizası')
            if 'Ş' in assigned and ord('Ç') in mm:
                if abs(bb(extract_glyph(md,mi,assigned['Ş']))[3]-bb(extract_glyph(md,mi,mm[ord('Ç')]))[3])>1:q.append('Ş:sedilla alt hizası')
            if 'ş' in assigned and ord('ç') in mm:
                if abs(bb(extract_glyph(md,mi,assigned['ş']))[3]-bb(extract_glyph(md,mi,mm[ord('ç')]))[3])>1:q.append('ş:sedilla alt hizası')
            if q:
                rows.append([str(rel),f'FONT_{i}_QUALITY','FAIL','; '.join(q)]);fails+=1
            else:rows.append([str(rel),f'FONT_{i}_QUALITY','PASS','glif geometrisi native Latin aksanlarıyla uyumlu'])
    # Global coverage: every suitable font in original tree must be present in patched tree and TR-complete there.
    # This validator assumes patched tree contains only changed CARCs; count is reported separately by generator.
    with Path(a.report).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['archive','test','result','detail']);w.writerows(rows)
    print(f'VALIDATION: patched_fonts={patched_fonts} PASS={sum(r[2]=="PASS" for r in rows)} FAIL={fails} WARN={warns}')
    raise SystemExit(1 if fails else 0)
if __name__=='__main__':main()
