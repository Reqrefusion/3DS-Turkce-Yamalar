#!/usr/bin/env python3
import argparse,struct,hashlib,json,csv,sys
from pathlib import Path
from lz11_codec import decompress,compress
from bffnt_patch_tr_v2 import patch_font

def parse_sarc_nodes(dec):
    if dec[:4]!=b'SARC': raise ValueError('SARC bulunamadı')
    e='<' if dec[6:8]==b'\xff\xfe' else '>'
    hdr=struct.unpack_from(e+'H',dec,4)[0]
    hsz,nodes,mult=struct.unpack_from(e+'HHI',dec,hdr+4)
    nodeoff=hdr+hsz; doff=struct.unpack_from(e+'I',dec,12)[0]
    return e,nodes,nodeoff,doff

def patch_archive(src,dst,cache):
    raw=src.read_bytes(); dec=bytearray(decompress(raw)); e,nodes,nodeoff,doff=parse_sarc_nodes(dec)
    rows=[]; pc=0; suitable=0
    for i in range(nodes):
        h,attr,st,en=struct.unpack_from(e+'IIII',dec,nodeoff+i*16); a,b=doff+st,doff+en; dat=bytes(dec[a:b])
        if dat[:4]!=b'FFNT': continue
        sha=hashlib.sha1(dat).hexdigest()
        if sha not in cache: cache[sha]=patch_font(dat)
        pat,rep=cache[sha]
        if rep.get('reason')!='unsuitable': suitable += 1
        if rep.get('patched'):
            if len(pat)!=len(dat): raise RuntimeError(f'{src}: Font boyutu değişti')
            dec[a:b]=pat; pc+=1
        rows.append({
            'archive':str(src),'node':i,'sarc_hash':f'{h:08X}','font_size':len(dat),
            'patched':rep.get('patched',False),'reason':rep.get('reason',''),
            'missing_before':''.join(rep.get('missing_before',[])),
            'assigned':json.dumps(rep.get('assigned',{}),ensure_ascii=False),
            'cell':json.dumps(rep.get('cell','')),'baseline':rep.get('baseline','')
        })
    if pc:
        dst.parent.mkdir(parents=True,exist_ok=True)
        comp=compress(bytes(dec),max_candidates=1)
        if decompress(comp)!=bytes(dec): raise RuntimeError(f'{src}: LZ11 round-trip başarısız')
        dst.write_bytes(comp)
    return pc,suitable,rows

def main():
    ap=argparse.ArgumentParser(description='Sushi Striker layout CARC dosyalarındaki tüm uygun BFFNT fontlara Türkçe ĞğİıŞş gliflerini ekler.')
    ap.add_argument('--layout-dir',required=True,help='Orijinal RomFS sys/layout klasörü')
    ap.add_argument('--out-dir',required=True,help='Yamalanmış CARC çıktıları (aynı göreli klasör yapısıyla)')
    ap.add_argument('--report',default=None,help='CSV raporu; verilmezse out-dir/FONT_PATCH_ALL_REPORT.csv')
    a=ap.parse_args(); srcroot=Path(a.layout_dir); outroot=Path(a.out_dir); cache={}; allrows=[]; changed=[]; totalfonts=0
    for src in sorted(srcroot.rglob('*.Carc')):
        rel=src.relative_to(srcroot); dst=outroot/rel
        if dst.exists():
            print(f'{rel}: mevcut çıktı, atlandı (resume)'); continue
        try: pc,suitable,rows=patch_archive(src,dst,cache)
        except Exception as ex:
            print('HATA',rel,ex,file=sys.stderr); raise
        totalfonts += len(rows); allrows += rows
        if pc:
            changed.append((str(rel),pc)); print(f'{rel}: {pc} font yamalandı')
    report=Path(a.report) if a.report else outroot/'FONT_PATCH_ALL_REPORT.csv'
    report.parent.mkdir(parents=True,exist_ok=True)
    if allrows:
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    print(f'Bitti: {len(changed)} CARC değişti, {sum(x[1] for x in changed)} font yamalandı, {totalfonts} FFNT incelendi.')

if __name__=='__main__': main()
