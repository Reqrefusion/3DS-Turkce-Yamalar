#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, struct, hashlib, json
from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageChops

def _find_default_font():
    candidates=[
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'),
        Path('/usr/share/fonts/dejavu/DejaVuSansCondensed-Bold.ttf'),
        Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('C:/Windows/Fonts/ARIALBD.TTF'),
        Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
        Path('/Library/Fonts/Arial Bold.ttf'),
    ]
    for p in candidates:
        if p.exists(): return str(p)
    # Pillow/fontconfig may still resolve this by family filename.
    return 'DejaVuSansCondensed-Bold.ttf'

DEFAULT_FONT = _find_default_font()

def _find_keyboard_fonts():
    back_candidates=[
        Path('/usr/share/fonts/truetype/lato/Lato-Medium.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
    ]
    action_candidates=[
        Path('/usr/share/fonts/truetype/paratype/PTM75F.ttf'),
        Path('C:/Windows/Fonts/consolab.ttf'),
        Path('C:/Windows/Fonts/arialbd.ttf'),
        Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
    ]
    def pick(xs):
        for p in xs:
            if p.exists(): return str(p)
        return DEFAULT_FONT
    return pick(back_candidates), pick(action_candidates)
KEYBOARD_BACK_FONT, KEYBOARD_ACTION_FONT = _find_keyboard_fonts()

DIMS = {
    (0,0):(8,8),(0,1):(16,8),(0,2):(8,16),
    (1,0):(16,16),(1,1):(32,8),(1,2):(8,32),
    (2,0):(32,32),(2,1):(32,16),(2,2):(16,32),
    (3,0):(64,64),(3,1):(64,32),(3,2):(32,64),
}

def obj_dims(code:int):
    shape=code & 0xFF; size=(code>>8)&0xFF
    if (size,shape) not in DIMS:
        raise ValueError(f'Bilinmeyen OBJ boyut kodu 0x{code:04X}')
    return DIMS[(size,shape)]

def parse_container(data:bytes):
    n=struct.unpack_from('<I',data,0)[0]
    header=4+8*n
    entries=[struct.unpack_from('<II',data,4+i*8) for i in range(n)]
    resources=[bytearray(data[header+o:header+o+s]) for o,s in entries]
    if header + entries[-1][0] + entries[-1][1] != len(data):
        raise ValueError('Kaynak tablosu/dosya boyu uyuşmuyor')
    return n,resources

def rebuild_container(resources:list[bytearray]):
    n=len(resources); header=4+8*n; out=bytearray(header); struct.pack_into('<I',out,0,n)
    body=bytearray(); off=0
    for i,r in enumerate(resources):
        struct.pack_into('<II',out,4+i*8,off,len(r)); body += r; off += len(r)
    return bytes(out+body)

def parse_cells(meta:bytes):
    if len(meta)<4: return []
    data_end,count=struct.unpack_from('<HH',meta,0)
    if count>1000 or 4+2*count>len(meta): return []
    offs=list(struct.unpack_from('<'+'H'*count,meta,4))
    starts=[4+o for o in offs]
    limit=min(len(meta),4+data_end)
    cells=[]
    for j,st in enumerate(starts):
        ed=starts[j+1] if j+1<count else limit
        if st<0 or st>len(meta) or ed<st: cells.append([]); continue
        rec=meta[st:ed]
        if len(rec)<2: cells.append([]); continue
        num=struct.unpack_from('<H',rec,0)[0]; objs=[]
        if 2+12*num>len(rec): cells.append([]); continue
        for k in range(num):
            x,y,tile,unk,dim,pal=struct.unpack_from('<hhHHHH',rec,2+12*k)
            try: wh=obj_dims(dim)
            except ValueError: continue
            objs.append({'x':x,'y':y,'tile':tile,'unk':unk,'dim':dim,'pal':pal,'w':wh[0],'h':wh[1]})
        cells.append(objs)
    return cells

def palette_rgb(pal:bytes, absolute_index:int):
    if absolute_index*2+2>len(pal): return (255,255,255)
    v=struct.unpack_from('<H',pal,absolute_index*2)[0]
    return ((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31)

def tile_get(gfx:bytes,tile:int):
    off=tile*32; b=gfx[off:off+32]
    if len(b)!=32: raise ValueError(f'Tile {tile} grafik verisi dışında')
    p=[[0]*8 for _ in range(8)]
    for y in range(8):
        for q in range(4):
            v=b[y*4+q]; p[y][q*2]=v&15; p[y][q*2+1]=(v>>4)&15
    return p

def tile_put(gfx:bytearray,tile:int,pix):
    off=tile*32
    if off+32>len(gfx): raise ValueError(f'Tile {tile} grafik verisi dışında')
    for y in range(8):
        for q in range(4):
            a=pix[y][q*2]&15; b=pix[y][q*2+1]&15
            gfx[off+y*4+q]=a|(b<<4)

def object_index_image(gfx:bytes,obj):
    w,h=obj['w'],obj['h']; tw=w//8; th=h//8
    im=Image.new('L',(w,h),0); px=im.load()
    for ty in range(th):
        for tx in range(tw):
            p=tile_get(gfx,obj['tile']+ty*tw+tx)
            for y in range(8):
                for x in range(8): px[tx*8+x,ty*8+y]=p[y][x]
    return im

def write_object_index_image(gfx:bytearray,obj,im:Image.Image):
    im=im.convert('L'); w,h=obj['w'],obj['h']
    if im.size!=(w,h): raise ValueError('OBJ görüntü boyutu uyuşmuyor')
    tw=w//8; th=h//8; px=im.load()
    for ty in range(th):
        for tx in range(tw):
            p=[[px[tx*8+x,ty*8+y]&15 for x in range(8)] for y in range(8)]
            tile_put(gfx,obj['tile']+ty*tw+tx,p)

def render_object_rgba(gfx:bytes,pal:bytes,obj):
    idx=object_index_image(gfx,obj); out=Image.new('RGBA',idx.size,(0,0,0,0)); p=out.load(); s=idx.load(); base=(obj['pal']&15)*16
    for y in range(out.height):
        for x in range(out.width):
            i=s[x,y]
            p[x,y]=(0,0,0,0) if i==0 else (*palette_rgb(pal,base+i),255)
    return out

def render_cell(resources,group:int,cell:int,scale=1):
    gfx,pal,meta=resources[3*group:3*group+3]; cells=parse_cells(meta); objs=cells[cell]
    if not objs: return Image.new('RGBA',(1,1),(0,0,0,0))
    minx=min(o['x'] for o in objs); miny=min(o['y'] for o in objs); maxx=max(o['x']+o['w'] for o in objs); maxy=max(o['y']+o['h'] for o in objs)
    im=Image.new('RGBA',(maxx-minx,maxy-miny),(0,0,0,0))
    for o in objs: im.alpha_composite(render_object_rgba(gfx,pal,o),(o['x']-minx,o['y']-miny))
    if scale!=1: im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
    return im

def cell_mask(resources,group:int,cell:int):
    im=render_cell(resources,group,cell,1)
    return im.getchannel('A').point(lambda x:255 if x else 0).convert('1')

def find_exact_cells(resources,tgroup,tcell):
    target=cell_mask(resources,tgroup,tcell); hits=[]
    for g in range(len(resources)//3):
        try: cs=parse_cells(resources[3*g+2])
        except Exception: continue
        for c in range(len(cs)):
            try: im=cell_mask(resources,g,c)
            except Exception: continue
            if im.size!=target.size: continue
            if ImageChops.difference(im.convert('L'),target.convert('L')).getbbox() is None: hits.append((g,c))
    return hits

def used_indices(gfx:bytes,objs):
    cnt=Counter()
    for o in objs:
        im=object_index_image(gfx,o)
        cnt.update(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata())
    return cnt

def choose_palette_indices(gfx:bytes,pal:bytes,objs,style='normal'):
    cnt=used_indices(gfx,objs); pids=Counter(o['pal']&15 for o in objs); pid=pids.most_common(1)[0][0]
    present=[i for i,n in cnt.items() if i!=0 and n]
    if not present: return pid,15,1
    vals=[]
    for i in present:
        rgb=palette_rgb(pal,pid*16+i); lum=0.2126*rgb[0]+0.7152*rgb[1]+0.0722*rgb[2]
        vals.append((lum,i,rgb,cnt[i]))
    vals.sort()
    if style=='touch':
        outline=max(vals)[1]; fill=min(vals, key=lambda t: abs(t[0]-120))[1]
    else:
        outline=vals[0][1]; fill=vals[-1][1]
        if outline==fill and len(vals)>1: outline=vals[0][1]
    return pid,fill,outline

def fit_font(text:str,w:int,h:int,font_path=DEFAULT_FONT,padding=1,max_size=40):
    lines=text.split('\n')
    for size in range(min(max_size,h*2),4,-1):
        font=ImageFont.truetype(font_path,size)
        bxs=[font.getbbox(line or ' ') for line in lines]
        widths=[b[2]-b[0] for b in bxs]; heights=[b[3]-b[1] for b in bxs]
        lineh=max(heights+[size]); totalh=lineh*len(lines)
        if max(widths+[0])<=w-2*padding and totalh<=h-2*padding: return font,lineh
    return ImageFont.truetype(font_path,5),6

def draw_index_text(text:str,w:int,h:int,fill_idx:int,outline_idx:int,font_path=DEFAULT_FONT,padding=1,outline_width=1,align='center'):
    S=4; font,_=fit_font(text,w*S,h*S,font_path,padding*S,max_size=h*S)
    mask_fill=Image.new('L',(w*S,h*S),0); mask_outline=Image.new('L',(w*S,h*S),0)
    df=ImageDraw.Draw(mask_fill); do=ImageDraw.Draw(mask_outline); lines=text.split('\n')
    lineh=max(1,h*S//len(lines))
    for li,line in enumerate(lines):
        bb=df.textbbox((0,0),line,font=font,stroke_width=0); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        x=(w*S-tw)//2 if align=='center' else padding*S
        y=li*lineh+(lineh-th)//2-bb[1]
        do.text((x,y),line,font=font,fill=255,stroke_width=outline_width*S,stroke_fill=255)
        df.text((x,y),line,font=font,fill=255)
    mo=mask_outline.resize((w,h),Image.Resampling.LANCZOS); mf=mask_fill.resize((w,h),Image.Resampling.LANCZOS)
    out=Image.new('L',(w,h),0); po=out.load(); a=mo.load(); b=mf.load()
    for y in range(h):
        for x in range(w):
            if a[x,y]>=72: po[x,y]=outline_idx
            if b[x,y]>=96: po[x,y]=fill_idx
    return out

def patch_cell(resources,group:int,cell:int,text:str,selector='all',style='normal',font_path=DEFAULT_FONT,outline_width=1):
    gfx,pal,meta=resources[3*group:3*group+3]; cells=parse_cells(meta); objs=cells[cell]
    if selector=='all': sel=list(range(len(objs)))
    elif selector=='back_text': sel=[i for i,o in enumerate(objs) if o['w']==32 and o['h']==16]
    elif isinstance(selector,(list,tuple)): sel=list(selector)
    else: raise ValueError(f'Bilinmeyen selector {selector}')
    if not sel: raise ValueError(f'R{group} C{cell}: seçilecek OBJ yok')
    sobjs=[objs[i] for i in sel]
    minx=min(o['x'] for o in sobjs); miny=min(o['y'] for o in sobjs); maxx=max(o['x']+o['w'] for o in sobjs); maxy=max(o['y']+o['h'] for o in sobjs)
    w=maxx-minx; h=maxy-miny
    pid,fill,outline=choose_palette_indices(gfx,pal,sobjs,style)
    canvas=draw_index_text(text,w,h,fill,outline,font_path,1,outline_width)
    for i in sel:
        o=objs[i]
        crop=canvas.crop((o['x']-minx,o['y']-miny,o['x']-minx+o['w'],o['y']-miny+o['h']))
        write_object_index_image(gfx,o,crop)
    return {'group':group,'cell':cell,'text':text,'objects':sel,'bbox':[w,h],'fill':fill,'outline':outline,'palette':pid}

def draw_native_label(text,w,h,fill,outline,size=9,stroke=1,font_path=DEFAULT_FONT):
    """Draw a small native-resolution indexed label; avoids downscaled antialias artifacts."""
    mask=Image.new('L',(w,h),0); d=ImageDraw.Draw(mask); f=ImageFont.truetype(font_path,size)
    bb=d.textbbox((0,0),text,font=f,stroke_width=stroke); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x=(w-tw)//2-bb[0]; y=(h-th)//2-bb[1]
    d.text((x,y),text,font=f,fill=255,stroke_width=stroke,stroke_fill=128)
    out=Image.new('L',(w,h),0); src=mask.load(); dst=out.load()
    for yy in range(h):
        for xx in range(w):
            v=src[xx,yy]
            if v>=220: dst[xx,yy]=fill
            elif v>=50: dst[xx,yy]=outline
    return out

def patch_keyboard_label(resources,cell:int,text:str,size=9,group=8,icon_width=16,font_path=DEFAULT_FONT):
    """Patch keyboard image-button text while preserving the B/Y/X icon portion."""
    gfx,pal,meta=resources[3*group:3*group+3]; objs=parse_cells(meta)[cell]
    if not objs: raise ValueError(f'R{group} C{cell}: klavye hücresi boş')
    minx=min(o['x'] for o in objs); miny=min(o['y'] for o in objs)
    maxx=max(o['x']+o['w'] for o in objs); maxy=max(o['y']+o['h'] for o in objs)
    w,h=maxx-minx,maxy-miny
    cv=Image.new('L',(w,h),0)
    for o in objs: cv.paste(object_index_image(gfx,o),(o['x']-minx,o['y']-miny))
    icon=cv.crop((0,0,icon_width,h)).copy()
    _,fill,outline=choose_palette_indices(gfx,pal,objs,'normal')
    cv.paste(0,(icon_width,0,w,h))
    cv.paste(draw_native_label(text,w-icon_width,h,fill,outline,size,1,font_path),(icon_width,0))
    cv.paste(icon,(0,0))
    for o in objs:
        crop=cv.crop((o['x']-minx,o['y']-miny,o['x']-minx+o['w'],o['y']-miny+o['h']))
        write_object_index_image(gfx,o,crop)
    return {'group':group,'cell':cell,'text':text,'size':[w,h],'font_size':size}



def _selector_indices(objs, selector):
    if selector=='all': return list(range(len(objs)))
    if selector=='back_text': return [i for i,o in enumerate(objs) if o['w']==32 and o['h']==16]
    if isinstance(selector,(list,tuple)): return list(selector)
    raise ValueError(f'Bilinmeyen selector {selector}')

def _selected_index_canvas(resources,group:int,cell:int,selector='all'):
    gfx,pal,meta=resources[3*group:3*group+3]; objs=parse_cells(meta)[cell]; inds=_selector_indices(objs,selector)
    sobjs=[objs[i] for i in inds]
    minx=min(o['x'] for o in sobjs); miny=min(o['y'] for o in sobjs); maxx=max(o['x']+o['w'] for o in sobjs); maxy=max(o['y']+o['h'] for o in sobjs)
    cv=Image.new('L',(maxx-minx,maxy-miny),0)
    for i in inds:
        o=objs[i]; cv.paste(object_index_image(gfx,o),(o['x']-minx,o['y']-miny))
    return cv,(minx,miny,maxx,maxy),inds,objs

def draw_native_fit_label(text,w,h,fill,outline,reference_bbox,font_path=DEFAULT_FONT,stroke=1):
    """Fit text to the original label's vertical metrics while keeping the sprite canvas unchanged."""
    d0=ImageDraw.Draw(Image.new('L',(1,1),0))
    if reference_bbox:
        target_h=max(1,reference_bbox[3]-reference_bbox[1]); cy=(reference_bbox[1]+reference_bbox[3])/2
    else:
        target_h=max(1,h-2); cy=h/2
    best=None
    for size in range(5,33):
        f=ImageFont.truetype(font_path,size); bb=d0.textbbox((0,0),text,font=f,stroke_width=stroke); tw,th=bb[2]-bb[0],bb[3]-bb[1]
        if tw<=w-2 and th<=h-1 and th<=target_h+1:
            score=(abs(th-target_h),-th,tw)
            if best is None or score<best[0]: best=(score,size,f,bb,tw,th)
    if best is None:
        for size in range(32,4,-1):
            f=ImageFont.truetype(font_path,size); bb=d0.textbbox((0,0),text,font=f,stroke_width=stroke); tw,th=bb[2]-bb[0],bb[3]-bb[1]
            if tw<=w-2 and th<=h-1:
                best=((99,0,0),size,f,bb,tw,th); break
    if best is None: raise ValueError(f'Metin alana sığmıyor: {text!r} {w}x{h}')
    _,size,font,bb,tw,th=best
    x=(w-tw)//2-bb[0]; y=round(cy-th/2)-bb[1]
    top=y+bb[1]; bot=y+bb[3]
    if top<0: y-=top
    if bot>h: y-=bot-h
    mo=Image.new('L',(w,h),0); mf=Image.new('L',(w,h),0); do=ImageDraw.Draw(mo); df=ImageDraw.Draw(mf)
    do.text((x,y),text,font=font,fill=255,stroke_width=stroke,stroke_fill=255); df.text((x,y),text,font=font,fill=255)
    out=Image.new('L',(w,h),0); a=mo.load(); b=mf.load(); o=out.load()
    for yy in range(h):
        for xx in range(w):
            if a[xx,yy]: o[xx,yy]=outline
            if b[xx,yy]: o[xx,yy]=fill
    return out, {'font_size':size,'reference_bbox':reference_bbox,'output_bbox':out.getbbox(),'canvas':[w,h]}

def patch_cell_fit(resources,reference_resources,group:int,cell:int,text:str,selector='all',style='normal',font_path=DEFAULT_FONT):
    gfx,pal,meta=resources[3*group:3*group+3]; objs=parse_cells(meta)[cell]
    refcv,_,inds,_=_selected_index_canvas(reference_resources,group,cell,selector); refbbox=refcv.getbbox()
    sobjs=[objs[i] for i in inds]; minx=min(o['x'] for o in sobjs); miny=min(o['y'] for o in sobjs); maxx=max(o['x']+o['w'] for o in sobjs); maxy=max(o['y']+o['h'] for o in sobjs)
    w,h=maxx-minx,maxy-miny; pid,fill,outline=choose_palette_indices(gfx,pal,sobjs,style)
    canvas,info=draw_native_fit_label(text,w,h,fill,outline,refbbox,font_path,1)
    for i in inds:
        o=objs[i]; crop=canvas.crop((o['x']-minx,o['y']-miny,o['x']-minx+o['w'],o['y']-miny+o['h'])); write_object_index_image(gfx,o,crop)
    return {'group':group,'cell':cell,'text':text,'objects':inds,'palette':pid,**info}

KEYBOARD_BITMAP = {
    'G':['01110','10000','10000','10000','10111','10001','10001','10001','01110'],
    'E':['11111','10000','10000','11110','10000','10000','10000','10000','11111'],
    'R':['11110','10001','10001','11110','10100','10010','10001','10001','10001'],
    'İ':['00100','00000','00100','00100','00100','00100','00100','00100','00100'],
    'I':['00100','00000','00100','00100','00100','00100','00100','00100','00100'],
    'O':['01110','10001','10001','10001','10001','10001','10001','10001','01110'],
    'N':['10001','11001','11001','10101','10101','10011','10011','10001','10001'],
    'A':['01110','10001','10001','10001','11111','10001','10001','10001','10001'],
    'Y':['10001','10001','01010','01010','00100','00100','00100','00100','00100'],
    'S':['01111','10000','10000','01110','00001','00001','00001','00001','11110'],
    'L':['10000','10000','10000','10000','10000','10000','10000','10000','11111'],
}

def draw_keyboard_bitmap(text,w,h,fill,outline,reference_bbox):
    """Deterministic keyboard glyphs; keep validated height, fit width to ~90% of original label."""
    glyphs=[]
    for ch in text:
        if ch not in KEYBOARD_BITMAP: raise ValueError(f'Klavye bitmap glifi yok: {ch!r}')
        glyphs.append(KEYBOARD_BITMAP[ch])
    widths=[len(g[0]) for g in glyphs]; bw=sum(widths)+max(0,len(glyphs)-1); bh=9
    base=Image.new('L',(bw,bh),0); bp=base.load(); xx0=0
    for g in glyphs:
        for yy,row in enumerate(g):
            for xx,v in enumerate(row):
                if v=='1': bp[xx0+xx,yy]=255
        xx0+=len(g[0])+1
    if reference_bbox:
        ref_w=max(1,reference_bbox[2]-reference_bbox[0])
        cy=(reference_bbox[1]+reference_bbox[3])/2
    else:
        ref_w=min(w,bw+2); cy=h/2
    # Width-only correction: preserve the previously validated 9px glyph height, but use the
    # original English label width as a guide. Always leave at least 1px on both sides.
    desired_output_w=max(bw+2, round(ref_w*0.90))
    desired_output_w=min(w-2, desired_output_w)
    inner_w=max(1,desired_output_w-2)
    scaled=base.resize((inner_w,bh), Image.Resampling.NEAREST)
    out=Image.new('L',(w,h),0); op=out.load(); sp=scaled.load()
    x0=(w-inner_w)//2
    y0=round(cy-bh/2)
    if y0<1: y0=1
    if y0+bh>h-1: y0=max(0,h-1-bh)
    for yy in range(bh):
        for xx in range(inner_w):
            if not sp[xx,yy]: continue
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    X=x0+xx+dx; Y=y0+yy+dy
                    if 0<=X<w and 0<=Y<h: op[X,Y]=outline
    for yy in range(bh):
        for xx in range(inner_w):
            if sp[xx,yy]:
                X=x0+xx; Y=y0+yy
                if 0<=X<w and 0<=Y<h: op[X,Y]=fill
    return out, {'bitmap':True,'reference_bbox':reference_bbox,'output_bbox':out.getbbox(),'canvas':[w,h], 'width_fit_ratio':0.90}

def patch_keyboard_label_fit(resources,reference_resources,cell:int,text:str,group=8,icon_width=16,font_path=DEFAULT_FONT):
    gfx,pal,meta=resources[3*group:3*group+3]; objs=parse_cells(meta)[cell]
    minx=min(o['x'] for o in objs); miny=min(o['y'] for o in objs); maxx=max(o['x']+o['w'] for o in objs); maxy=max(o['y']+o['h'] for o in objs); w,h=maxx-minx,maxy-miny
    cv=Image.new('L',(w,h),0)
    for o in objs: cv.paste(object_index_image(gfx,o),(o['x']-minx,o['y']-miny))
    icon=cv.crop((0,0,icon_width,h)).copy()
    rgfx,rpal,rmeta=reference_resources[3*group:3*group+3]; robjs=parse_cells(rmeta)[cell]; rcv=Image.new('L',(w,h),0)
    for o in robjs: rcv.paste(object_index_image(rgfx,o),(o['x']-minx,o['y']-miny))
    rb=rcv.crop((icon_width,0,w,h)).getbbox()
    _,fill,outline=choose_palette_indices(gfx,pal,objs,'normal')
    label,info=draw_keyboard_bitmap(text,w-icon_width,h,fill,outline,rb)
    cv.paste(0,(icon_width,0,w,h)); cv.paste(label,(icon_width,0)); cv.paste(icon,(0,0))
    for o in objs: write_object_index_image(gfx,o,cv.crop((o['x']-minx,o['y']-miny,o['x']-minx+o['w'],o['y']-miny+o['h'])))
    return {'group':group,'cell':cell,'text':text,**info}

def sha256(b): return hashlib.sha256(b).hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Harvest Moon 3DS console_obj_data.bin güvenli Türkçe UI grafik yamalayıcı')
    ap.add_argument('input'); ap.add_argument('output'); ap.add_argument('--preview-dir'); ap.add_argument('--report'); ap.add_argument('--font',default=DEFAULT_FONT,help='Türkçe glif destekli TTF/OTF yolu')
    args=ap.parse_args()
    data=Path(args.input).read_bytes(); n,res=parse_container(data); reference=[bytearray(r) for r in res]
    if n!=282: raise SystemExit(f'Beklenmeyen resource sayısı: {n} (beklenen 282)')
    report=[]; seen=set()

    # Exact duplicate templates. This catches repeated Back/Close/menu copies safely.
    templates=[
        (4,8,'Geri','back_text','normal'),
        (1,27,'Kapat','back_text','normal'),
        (1,58,'Çanta','all','normal'),
        (1,59,'Depo','all','normal'),
        (1,52,'Balık','all','normal'),
        (1,53,'Böcekler','all','normal'),
    ]
    for tg,tc,text,selector,style in templates:
        for g,c in find_exact_cells(reference,tg,tc):
            key=(g,c,text)
            if key in seen: continue
            try: report.append(patch_cell_fit(res,reference,g,c,text,selector,style,args.font)); seen.add(key)
            except Exception as e: report.append({'group':g,'cell':c,'text':text,'error':str(e)})

    # Only cells visually verified as text-only (or text object explicitly selected).
    targets=[
        (82,2,'Dokunmatik ekrana dokun!','all','touch'),
        (12,31,'Salata','all','normal'),(12,32,'Çorba','all','normal'),
        (12,33,'Başlangıç','all','normal'),(12,34,'Ana Yemek','all','normal'),
        (12,35,'Tatlı','all','normal'),(12,36,'Diğer','all','normal'),
        (83,54,'Ödül','all','normal'),(83,66,'Gönder','all','normal'),(83,67,'Al','all','normal'),
        (85,54,'İstek','all','normal'),
        (87,31,'İstekler','all','normal'),(87,32,'Geçmiş','all','normal'),
        (87,59,'gün daha','all','normal'),(87,71,'Son gün!','all','normal'),
        (88,38,'İstek','all','normal'),(88,39,'Ödül','all','normal'),
        (84,31,'Ürünler','all','normal'),(84,32,'Hayvansal','all','normal'),
        (84,33,'Balık','all','normal'),(84,34,'Böcekler','all','normal'),(84,35,'Bilgi','all','normal'),
        (86,14,'YENİ','all','normal'),(86,15,'YENİ','all','normal'),
        (92,36,'Yemek','all','normal'),(92,37,'Yemek','all','normal'),
        (92,38,'Ürün','all','normal'),(92,39,'Hayvan','all','normal'),
        (92,40,'Olta','all','normal'),(92,41,'Elle Av','all','normal'),(92,42,'Böcek','all','normal'),
        # Seasons: object 0 is the text sprite; decorative leaf/background objects are untouched.
        (3,7,'Bahar',[0],'normal'),(3,8,'Yaz',[0],'normal'),(3,9,'Güz',[0],'normal'),(3,10,'Kış',[0],'normal'),
    ]
    for g,c,text,selector,style in targets:
        key=(g,c,text)
        if key in seen: continue
        try: report.append(patch_cell_fit(res,reference,g,c,text,selector,style,args.font)); seen.add(key)
        except Exception as e: report.append({'group':g,'cell':c,'text':text,'error':str(e)})

    # Final keyboard image-buttons. Use smaller metrics so labels stay within the original
    # sprite region on real hardware. Selected-state cells share the same underlying graphics,
    # so patching the normal cells updates both normal and selected variants consistently.
    for cell,text,size in [(15,'GERİ',0),(48,'ONAY',0),(50,'SİL',0)]:
        try: report.append(patch_keyboard_label_fit(res,reference,cell,text))
        except Exception as e: report.append({'group':8,'cell':cell,'text':text,'error':str(e)})

    out=rebuild_container(res)
    if len(out)!=len(data): raise SystemExit('Dosya boyu değişti; güvenlik nedeniyle çıktı yazılmadı')
    Path(args.output).parent.mkdir(parents=True,exist_ok=True); Path(args.output).write_bytes(out)
    if args.preview_dir:
        pd=Path(args.preview_dir); pd.mkdir(parents=True,exist_ok=True)
        for g,c,name in [(4,8,'back'),(1,27,'close'),(82,2,'touch'),(1,59,'storage'),(1,53,'critters'),(12,33,'appetizer'),(87,31,'request_list'),(84,32,'animal_products'),(3,7,'spring')]:
            try: render_cell(res,g,c,4).save(pd/f'{name}_R{g}_C{c}.png')
            except Exception: pass
    rep={'input_sha256':sha256(data),'output_sha256':sha256(out),'size':len(out),'patched_entries':report,'errors':[r for r in report if 'error' in r]}
    if args.report: Path(args.report).write_text(json.dumps(rep,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Yazıldı: {args.output} | {len(report)} patch kaydı | hata={len(rep["errors"])} | boyut={len(out)}')

if __name__=='__main__': main()
