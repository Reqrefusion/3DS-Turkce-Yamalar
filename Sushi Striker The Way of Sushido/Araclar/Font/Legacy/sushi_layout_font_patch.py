#!/usr/bin/env python3
import argparse,struct,hashlib,json,csv,sys
from pathlib import Path
from lz11_codec import decompress,compress
from bffnt_patch_tr_fast import patch_font

DEFAULT_ARCHIVES=['Title.Carc','FileSelect.Carc','MenuConfig.Carc','MenuTop.Carc','Loading.Carc','Global.Carc']

def patch_archive(src,dst,cache):
    raw=src.read_bytes(); dec=bytearray(decompress(raw))
    if dec[:4]!=b'SARC': raise ValueError(f'{src.name}: SARC bulunamadı')
    e='<' if dec[6:8]==b'\xff\xfe' else '>';hdr=struct.unpack_from(e+'H',dec,4)[0];hsz,nodes,mult=struct.unpack_from(e+'HHI',dec,hdr+4);nodeoff=hdr+hsz;doff=struct.unpack_from(e+'I',dec,12)[0]
    rows=[];pc=0
    for i in range(nodes):
        h,attr,st,en=struct.unpack_from(e+'IIII',dec,nodeoff+i*16);a,b=doff+st,doff+en;dat=bytes(dec[a:b])
        if dat[:4]!=b'FFNT': continue
        sha=hashlib.sha1(dat).hexdigest()
        if sha not in cache: cache[sha]=patch_font(dat)
        pat,rep=cache[sha]
        if rep.get('patched'):
            if len(pat)!=len(dat): raise RuntimeError('Font boyutu değişti')
            dec[a:b]=pat;pc+=1
        rows.append({'archive':src.name,'node':i,'sarc_hash':f'{h:08X}','font_size':len(dat),'patched':rep.get('patched',False),'missing_before':''.join(rep.get('missing_before',[])),'assigned':json.dumps(rep.get('assigned',{}),ensure_ascii=False),'reason':rep.get('reason','')})
    dst.parent.mkdir(parents=True,exist_ok=True)
    comp=compress(bytes(dec),max_candidates=1)
    if decompress(comp)!=bytes(dec): raise RuntimeError('LZ11 round-trip başarısız')
    dst.write_bytes(comp)
    return pc,rows

def main():
    ap=argparse.ArgumentParser(description='Sushi Striker 3DS layout BFFNT Türkçe karakter yaması')
    ap.add_argument('--layout-dir',required=True,help='RomFS sys/layout klasörü')
    ap.add_argument('--out-dir',required=True,help='Yamalanmış .Carc çıktı klasörü')
    ap.add_argument('--archives',nargs='*',default=DEFAULT_ARCHIVES)
    a=ap.parse_args(); src=Path(a.layout_dir);out=Path(a.out_dir);cache={};rows=[]
    for n in a.archives:
        p=src/n
        if not p.exists(): print('ATLANDI:',n,'bulunamadı');continue
        c,r=patch_archive(p,out/n,cache);rows+=r;print(n,':',c,'font yamalandı')
    if rows:
        with (out/'FONT_PATCH_REPORT.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

if __name__=='__main__':main()
