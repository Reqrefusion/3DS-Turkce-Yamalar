#!/usr/bin/env python3
from __future__ import annotations
import argparse, subprocess, sys, tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
IPK=HERE/'ipk_tool.py'
EXACT=HERE/'font_turkish_exact.py'
BCFNT_ENTRY='enginedata/shaders/compiled/ctr/tahoma.bcfnt'
TFNS=[
 'cache/itf_cooked/ctr/enginedata/misc/fonts/mylifecoach65.tfn.ckd',
 'cache/itf_cooked/ctr/enginedata/misc/fonts/mylifecoach66.tfn.ckd',
]
TGAS=[
 'cache/itf_cooked/ctr/enginedata/misc/fonts/mylifecoach65.tga.ckd',
 'cache/itf_cooked/ctr/enginedata/misc/fonts/mylifecoach66.tga.ckd',
]

def run(*a): subprocess.run([sys.executable,*map(str,a)],check=True)
def replace_chain(src,repls,out,tmp,prefix):
    cur=src
    for i,(entry,payload) in enumerate(repls):
        nxt=out if i==len(repls)-1 else tmp/f'{prefix}_{i}.ipk'
        run(IPK,'replace',cur,entry,payload,nxt,'--compression','preserve');cur=nxt
    run(IPK,'check',out)

def main():
    ap=argparse.ArgumentParser(description='Gravity Falls 3DS gerçek Türkçe fontlarını üretip IPK arşivlerine uygular')
    ap.add_argument('bundle',help='Orijinal bundle_ctr.ipk')
    ap.add_argument('fulllogic',help='Orijinal fulllogic_ctr.ipk')
    ap.add_argument('output_dir')
    a=ap.parse_args();outdir=Path(a.output_dir);outdir.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gf_tr_fonts_') as td:
        tmp=Path(td); bundle=Path(a.bundle); full=Path(a.fulllogic)
        stock_b=tmp/'tahoma.bcfnt'; tr_b=tmp/'tahoma_tr.bcfnt'
        run(IPK,'extract',bundle,BCFNT_ENTRY,stock_b); run(EXACT,'bcfnt',stock_b,tr_b)
        bundle_repls=[(BCFNT_ENTRY,tr_b)]; full_repls=[]
        for i,(tfne,tgae) in enumerate(zip(TFNS,TGAS)):
            st=tmp/f'font{i}.tfn.ckd'; sg=tmp/f'font{i}.tga.ckd'; pt=tmp/f'font{i}_tr.tfn.ckd'; pg=tmp/f'font{i}_tr.tga.ckd'
            run(IPK,'extract',bundle,tfne,st);run(IPK,'extract',bundle,tgae,sg)
            run(EXACT,'tfn',st,sg,pt,pg)
            bundle_repls += [(tfne,pt),(tgae,pg)];full_repls.append((tfne,pt))
        replace_chain(bundle,bundle_repls,outdir/'bundle_ctr.ipk',tmp,'bundle')
        replace_chain(full,full_repls,outdir/'fulllogic_ctr.ipk',tmp,'full')
        print('Hazır:',outdir/'bundle_ctr.ipk')
        print('Hazır:',outdir/'fulllogic_ctr.ipk')
if __name__=='__main__':main()
