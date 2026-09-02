#!/usr/bin/env python3
"""Inventory Cave Story 3D bitmap assets and optionally build contact sheets."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
import argparse, math, csv
EXT={'.pbm','.tga','.bmp','.png','.jpg','.jpeg'}

def bmp_bpp(path):
    try:
        b=path.read_bytes()[:32]
        if b[:2]==b'BM': return int.from_bytes(b[28:30],'little')
    except: pass
    return None

def make_sheet(files,out,thumb=(192,144),cols=5):
    rows=math.ceil(len(files)/cols)
    cellw,cellh=thumb[0],thumb[1]+24
    sheet=Image.new('RGB',(cols*cellw,rows*cellh),'white')
    dr=ImageDraw.Draw(sheet)
    for i,p in enumerate(files):
        x=(i%cols)*cellw; y=(i//cols)*cellh
        try:
            im=Image.open(p).convert('RGBA')
            bg=Image.new('RGBA',im.size,(35,35,35,255)); bg.alpha_composite(im)
            im=bg.convert('RGB'); im.thumbnail((thumb[0]-8,thumb[1]-8),Image.Resampling.NEAREST)
            sheet.paste(im,(x+(thumb[0]-im.width)//2,y+(thumb[1]-im.height)//2))
        except Exception as e:
            dr.text((x+4,y+4),f'ERR {e}',fill='red')
        dr.text((x+3,y+thumb[1]+3),p.name[:28],fill='black')
    sheet.save(out)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--outdir',default='image_inventory'); a=ap.parse_args()
    root=Path(a.root); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True)
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in EXT)
    with open(out/'image_inventory.tsv','w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(['path','width','height','mode','bmp_bpp'])
        for p in files:
            try:
                im=Image.open(p); row=[p.relative_to(root).as_posix(),im.width,im.height,im.mode,bmp_bpp(p) or '']
            except Exception as e: row=[p.relative_to(root).as_posix(),'','','ERR:'+str(e),'']
            w.writerow(row)
    groups={'.': [p for p in files if p.parent==root],
            'npc':[p for p in files if p.parent==root/'npc'],
            'stage':[p for p in files if p.parent==root/'stage']}
    for name,arr in groups.items():
        if arr: make_sheet(arr,out/f'{name.replace(".","top")}_contact.png')
    print('images:',len(files),'inventory:',out/'image_inventory.tsv')
if __name__=='__main__': main()
