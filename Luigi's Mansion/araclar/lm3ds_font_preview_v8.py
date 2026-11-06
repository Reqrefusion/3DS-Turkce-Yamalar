#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
from lm3ds_font_fix_v8 import decode_gzf,cmap,glyph_tile

def render_text(data:bytes,text:str,scale:int=4,pad:int=6):
    meta,entries,atlas=decode_gzf(data); m=cmap(entries)
    # first field after codepoint behaves as advance; third is horizontal origin/bearing.
    advances=[]
    for ch in text:
        if ch==' ': advances.append(7)
        elif ch in m: advances.append(m[ch][1])
        else: advances.append(10)
    width=sum(advances)+pad*2+20
    height=meta['th']+pad*2
    canvas=Image.new('L',(width,height),0)
    cursor=pad+10
    for ch,adv in zip(text,advances):
        if ch==' ': cursor+=adv; continue
        e=m.get(ch)
        if not e: cursor+=adv; continue
        g=glyph_tile(atlas,meta,e)
        x=cursor-e[3]
        canvas=ImageChops.lighter(canvas, _place(canvas.size,g,(x,pad)))
        cursor+=adv
    if scale!=1: canvas=canvas.resize((canvas.width*scale,canvas.height*scale),Image.Resampling.NEAREST)
    return canvas

def _place(size,g,xy):
    out=Image.new('L',size,0); out.paste(g,xy); return out

def sheet(font_path:str,out_path:str,texts:list[str]):
    data=Path(font_path).read_bytes(); ims=[render_text(data,t) for t in texts]
    W=max(i.width for i in ims)+20; H=sum(i.height+32 for i in ims)+10
    out=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(out); y=8
    for t,im in zip(texts,ims):
        d.text((8,y),t,fill='black'); y+=18
        rgb=Image.new('RGB',im.size,'black'); rgb.paste((255,255,255),mask=im)
        out.paste(rgb,(8,y)); y+=im.height+14
    out.save(out_path)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('font');ap.add_argument('out');ap.add_argument('texts',nargs='+')
    a=ap.parse_args();sheet(a.font,a.out,a.texts)
