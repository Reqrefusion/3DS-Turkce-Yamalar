#!/usr/bin/env python3
import argparse,struct,hashlib,json,csv,sys
from pathlib import Path
from lz11_codec import decompress
from lz11_fast16 import compress
from bffnt_patch_tr_v3 import patch_font

def parse_sarc(dec):
    if dec[:4]!=b'SARC':raise ValueError('SARC bulunamadı')
    e='<' if dec[6:8]==b'\xff\xfe' else '>';hdr=struct.unpack_from(e+'H',dec,4)[0];hsz,nodes,mult=struct.unpack_from(e+'HHI',dec,hdr+4)
    return e,nodes,hdr+hsz,struct.unpack_from(e+'I',dec,12)[0]

def one(src,dst,cache):
    raw=src.read_bytes();dec=bytearray(decompress(raw));e,nodes,no,do=parse_sarc(dec); rows=[];pc=0
    for i in range(nodes):
        h,a,st,en=struct.unpack_from(e+'IIII',dec,no+i*16);A,B=do+st,do+en;dat=bytes(dec[A:B])
        if dat[:4]!=b'FFNT':continue
        sha=hashlib.sha1(dat).hexdigest()
        if sha not in cache:cache[sha]=patch_font(dat)
        pat,rep=cache[sha]
        rows.append({'archive':str(src),'node':i,'hash':f'{h:08X}','patched':rep.get('patched',False),'reason':rep.get('reason',''),'missing_before':''.join(rep.get('missing_before',[])),'scan_reordered':rep.get('scan_sections_reordered',0)})
        if rep.get('patched'):
            if len(pat)!=len(dat):raise RuntimeError('Font boyutu değişti')
            dec[A:B]=pat;pc+=1
    if pc:
        dst.parent.mkdir(parents=True,exist_ok=True);c=compress(bytes(dec))
        if decompress(c)!=bytes(dec):raise RuntimeError('LZ11 roundtrip')
        dst.write_bytes(c)
    return pc,rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--layout-dir',required=True);ap.add_argument('--out-dir',required=True);ap.add_argument('--report');a=ap.parse_args()
    root=Path(a.layout_dir);out=Path(a.out_dir);cache={};rows=[];changed=[]
    for src in sorted(root.rglob('*.Carc')):
        pc,rr=one(src,out/src.relative_to(root),cache);rows+=rr
        if pc:changed.append((src.relative_to(root),pc));print(src.relative_to(root),pc)
    rp=Path(a.report) if a.report else out/'FONT_PATCH_V3_REPORT.csv';rp.parent.mkdir(parents=True,exist_ok=True)
    if rows:
        with rp.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    print('CARC',len(changed),'FONT',sum(x[1] for x in changed))
if __name__=='__main__':main()
