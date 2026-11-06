from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSans-CondensedBold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
]
SERIF_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf',
]

def pick_font(serif=False):
    for p in (SERIF_CANDIDATES if serif else FONT_CANDIDATES):
        if Path(p).exists(): return p
    raise FileNotFoundError('No suitable font found; install DejaVu/Noto or edit FONT_CANDIDATES')

def alpha_bbox(img:Image.Image, threshold=8):
    a=np.asarray(img.convert('RGBA'))[:,:,3]
    ys,xs=np.where(a>threshold)
    if len(xs)==0: return (0,0,img.width,img.height)
    return (int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))

def _border_alpha_fraction(img:Image.Image):
    a=np.asarray(img.convert('RGBA'))[:,:,3]
    if min(a.shape)<2: return float((a>8).mean())
    b=np.concatenate([a[0],a[-1],a[:,0],a[:,-1]])
    return float((b>8).mean())

def is_text_only(img:Image.Image):
    a=np.asarray(img.convert('RGBA'))[:,:,3]
    occ=float((a>8).mean())
    # Most pure-label BCLIMs are transparent around glyphs.
    return _border_alpha_fraction(img)<0.08 and occ<0.42

def sample_text_colors(img:Image.Image):
    arr=np.asarray(img.convert('RGBA'))
    px=arr[arr[:,:,3]>48]
    if len(px)==0: return (235,235,235,255),(20,20,20,255)
    rgb=px[:,:3].astype(np.float32)
    lum=0.2126*rgb[:,0]+0.7152*rgb[:,1]+0.0722*rgb[:,2]
    # Main fill: median of brighter half, unless texture is overall very dark.
    q50=np.quantile(lum,0.50); q85=np.quantile(lum,0.85)
    if q85<105:
        sel=rgb[lum>=q50]
    else:
        sel=rgb[lum>=np.quantile(lum,0.68)]
    fill=tuple(int(x) for x in np.median(sel,axis=0))+(255,)
    # Stroke should contrast with the fill.
    fl=0.2126*fill[0]+0.7152*fill[1]+0.0722*fill[2]
    if fl>145: stroke=(10,10,18,245)
    else: stroke=(235,235,235,230) if fl<65 else (15,15,15,245)
    return fill,stroke

def _fit_font(text,bbox,font_path,stroke=1,min_size=5,max_size=64):
    x0,y0,x1,y1=bbox; w=max(1,x1-x0);h=max(1,y1-y0)
    dummy=Image.new('RGBA',(4,4)); d=ImageDraw.Draw(dummy)
    best=ImageFont.truetype(font_path,min_size)
    for size in range(min(max_size,h*2),min_size-1,-1):
        f=ImageFont.truetype(font_path,size)
        bb=d.textbbox((0,0),text,font=f,stroke_width=stroke)
        tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        if tw<=w and th<=h:
            best=f; break
    return best

def _draw_centered(canvas:Image.Image,text:str,bbox,fill,stroke,serif=False,stroke_width=None):
    x0,y0,x1,y1=bbox
    # Small texture labels benefit from condensed sans; chapter subtitles use serif.
    fp=pick_font(serif)
    if stroke_width is None:
        stroke_width=1 if (y1-y0)>=10 else 0
    font=_fit_font(text,bbox,fp,stroke=stroke_width,min_size=4,max_size=64)
    d=ImageDraw.Draw(canvas)
    bb=d.textbbox((0,0),text,font=font,stroke_width=stroke_width)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x=x0+(x1-x0-tw)//2-bb[0]
    y=y0+(y1-y0-th)//2-bb[1]
    # A one-pixel soft shadow improves readability at 3DS scale.
    if (y1-y0)>=14:
        sh=(0,0,0,100)
        d.text((x+1,y+1),text,font=font,fill=sh,stroke_width=stroke_width,stroke_fill=(0,0,0,80))
    d.text((x,y),text,font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke)
    return canvas

def language_diff_mask(en:Image.Image, others:list[Image.Image]):
    ea=np.asarray(en.convert('RGBA')).astype(np.int16)
    masks=[]
    for im in others:
        if im.size!=en.size: continue
        oa=np.asarray(im.convert('RGBA')).astype(np.int16)
        # Alpha and RGB difference; threshold filters ETC1 noise/padding differences.
        delta=np.max(np.abs(ea-oa),axis=2)
        masks.append((delta>22).astype(np.uint8)*255)
    if not masks: return np.zeros((en.height,en.width),np.uint8)
    m=np.maximum.reduce(masks)
    k=np.ones((3,3),np.uint8)
    m=cv2.dilate(m,k,iterations=1)
    return m

def inpaint_language_area(en:Image.Image, others:list[Image.Image]):
    arr=np.asarray(en.convert('RGBA')).copy()
    mask=language_diff_mask(en,others)
    if mask.max()==0:
        return en.copy(), alpha_bbox(en), mask
    ys,xs=np.where(mask>0)
    bbox=(max(0,int(xs.min())-1),max(0,int(ys.min())-1),min(en.width,int(xs.max())+2),min(en.height,int(ys.max())+2))
    # Inpaint RGB. Preserve alpha for opaque UI panels; alpha holes are handled separately.
    rgb=cv2.inpaint(arr[:,:,:3],mask,3,cv2.INPAINT_TELEA)
    # For alpha, nearest/telea works well on button/plate textures.
    a=cv2.inpaint(arr[:,:,3],mask,3,cv2.INPAINT_TELEA)
    out=np.dstack([rgb,a]).astype(np.uint8)
    return Image.fromarray(out,'RGBA'),bbox,mask

def render_translation(en:Image.Image,text:str,other_langs:list[Image.Image]|None=None,serif=False,mode='auto'):
    en=en.convert('RGBA'); fill,stroke=sample_text_colors(en)
    if mode=='bright_text':
        arr=np.asarray(en).copy()
        rgb=arr[:,:,:3].astype(np.float32); a=arr[:,:,3]
        lum=0.2126*rgb[:,:,0]+0.7152*rgb[:,:,1]+0.0722*rgb[:,:,2]
        # Chapter/frame labels are the bright pixels near the top center; ornaments are dark.
        yy=np.indices(lum.shape)[0]
        mask=(a>24)&(lum>105)&(yy < en.height*0.45)
        ys,xs=np.where(mask)
        if len(xs):
            x0=max(0,int(xs.min())-5); x1=min(en.width,int(xs.max())+6)
            y0=max(0,int(ys.min())-3); y1=min(en.height,int(ys.max())+4)
            arr[y0:y1,x0:x1]=0
            base=Image.fromarray(arr.astype(np.uint8),'RGBA')
            bb=(max(1,x0-8),max(0,y0-2),min(en.width-1,x1+8),min(en.height,y1+2))
            # sample original bright text for its intended tone
            vals=rgb[mask]
            if len(vals): fill=tuple(int(v) for v in np.median(vals,axis=0))+(255,)
            stroke=(8,8,8,235)
            return _draw_centered(base,text,bb,fill,stroke,serif=True,stroke_width=1)
        # Fall through to automatic handling if no bright title pixels were found.
    text_only = is_text_only(en) if mode=='auto' else (mode=='text_only')
    if text_only:
        bb=alpha_bbox(en)
        # Add tiny margin so long Turkish words can use original empty width.
        x0,y0,x1,y1=bb
        bb=(max(0,x0-2),max(0,y0-1),min(en.width,x1+2),min(en.height,y1+1))
        base=Image.new('RGBA',en.size,(0,0,0,0))
        # If text would be cramped, allow full canvas width while keeping original vertical band.
        if (x1-x0)<en.width*0.78:
            bb=(1,bb[1],en.width-1,bb[3])
        return _draw_centered(base,text,bb,fill,stroke,serif=serif)
    others=other_langs or []
    base,bb,mask=inpaint_language_area(en,others)
    # If diff mask is too tiny or suspicious, use alpha bbox rather than overwrite whole art.
    if (bb[2]-bb[0])<6 or (bb[3]-bb[1])<5:
        bb=alpha_bbox(en)
    # Give translated text a little more horizontal room inside its local band.
    pad=max(2,int(en.width*0.02)); bb=(max(0,bb[0]-pad),bb[1],min(en.width,bb[2]+pad),bb[3])
    return _draw_centered(base,text,bb,fill,stroke,serif=serif)

def _draw_fit_at(canvas, text, box, fill=(35,20,15,255), serif=True, align='center', stroke_width=0, stroke=(0,0,0,0), min_size=4):
    """Draw text inside a fixed box; used for multi-label textures."""
    fp=pick_font(serif)
    font=_fit_font(text,box,fp,stroke=stroke_width,min_size=min_size,max_size=48)
    d=ImageDraw.Draw(canvas)
    bb=d.textbbox((0,0),text,font=font,stroke_width=stroke_width)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    x0,y0,x1,y1=box
    if align=='left': x=x0-bb[0]
    elif align=='right': x=x1-tw-bb[0]
    else: x=x0+((x1-x0)-tw)//2-bb[0]
    y=y0+((y1-y0)-th)//2-bb[1]
    d.text((x,y),text,font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke)
    return canvas

def render_custom_id(iid:int,en:Image.Image,other_langs:list[Image.Image]|None=None):
    """Exact multi-region patches for compound English textures."""
    en=en.convert('RGBA')
    if iid in (259,260):
        # These textures contain labels only; rebuilding on transparent background is safest.
        fill,_=sample_text_colors(en)
        out=Image.new('RGBA',en.size,(0,0,0,0))
        # compact Turkish stat abbreviations; keep HP/MP conventions recognizable.
        if iid==259:
            items=[('Azm HP',(0,0,52,18)),('F.ATK',(0,18,46,32)),('F.DEF',(47,18,96,32)),('İsabet',(97,18,140,32)),
                   ('B.ATK',(0,31,46,45)),('B.DEF',(47,31,96,45)),('Kaçın',(97,31,140,45)),
                   ('ZEK',(0,44,46,60)),('ZHN',(47,44,96,60)),('HIZ',(97,44,140,60))]
        else:
            items=[('Azm HP',(0,0,64,18)),('Azm BP',(74,0,140,18)),('F.ATK',(0,18,46,32)),('F.DEF',(47,18,96,32)),('İsabet',(97,18,140,32)),
                   ('B.ATK',(0,31,46,45)),('B.DEF',(47,31,96,45)),('Kaçın',(97,31,140,45)),
                   ('ZEK',(0,44,46,60)),('ZHN',(47,44,96,60)),('HIZ',(97,44,140,60))]
        for txt,box in items: _draw_fit_at(out,txt,box,fill=fill,serif=True,align='left',min_size=4)
        return out
    if iid==263:
        out=en.copy(); d=ImageDraw.Draw(out)
        # Top/middle title strips are flat dark panels; bottom title is on a light panel.
        d.rectangle((5,2,133,17),fill=(55,55,60,255))
        d.rectangle((5,116,133,132),fill=(55,55,60,255))
        d.rectangle((8,202,91,224),fill=(225,247,250,255))
        _draw_fit_at(out,'Profil',(10,2,130,17),fill=(245,245,245,255),serif=True,align='left',stroke_width=1,stroke=(15,15,18,220),min_size=5)
        _draw_fit_at(out,'Çağrı Bilgisi',(10,116,130,132),fill=(245,245,245,255),serif=True,align='left',stroke_width=1,stroke=(15,15,18,220),min_size=5)
        _draw_fit_at(out,'Güç',(12,202,90,224),fill=(25,20,28,255),serif=True,align='left',min_size=5)
        return out
    if iid==281:
        # Tutorial screenshot: inpaint all localized glyph differences first, then rebuild the three labels.
        base,_,_=inpaint_language_area(en,other_langs or [])
        # Give panels clean local bands to avoid residual glyphs while preserving borders/arrow.
        a=np.asarray(base).copy()
        # sample local light panel pixels for left/right labels
        for x0,y0,x1,y1 in [(35,7,126,43),(158,7,238,43)]:
            roi=a[y0:y1,x0:x1]
            px=roi.reshape(-1,4); valid=px[px[:,3]>100]
            col=np.median(valid,axis=0).astype(np.uint8) if len(valid) else np.array([210,235,240,255],np.uint8)
            # only clear central text area, not rounded border
            a[y0+5:y1-3,x0+4:x1-3]=col
        base=Image.fromarray(a,'RGBA')
        _draw_fit_at(base,'Sv 1\nSerbest',(40,9,126,42),fill=(20,20,35,255),serif=True,stroke_width=0,min_size=4)
        _draw_fit_at(base,'Sv 2\nSerbest',(162,9,236,42),fill=(20,20,35,255),serif=True,stroke_width=0,min_size=4)
        # Center badge, compact two-line Turkish.
        _draw_fit_at(base,'SEVİYE\nARTTI!',(94,5,153,34),fill=(225,245,255,255),serif=False,stroke_width=1,stroke=(20,70,130,255),min_size=4)
        return base
    if iid==282:
        # Only the top action label is English.
        out=en.copy(); arr=np.asarray(out).copy()
        # Clear top banner text while preserving the dark banner.
        band=arr[0:25,0:102]
        valid=band.reshape(-1,4); valid=valid[(valid[:,3]>150) & (valid[:,:3].mean(axis=1)<110)]
        col=np.median(valid,axis=0).astype(np.uint8) if len(valid) else np.array([38,62,63,255],np.uint8)
        arr[2:24,20:83]=col
        out=Image.fromarray(arr,'RGBA')
        _draw_fit_at(out,'İncele',(17,2,86,24),fill=(245,245,240,255),serif=True,stroke_width=1,stroke=(20,20,20,230),min_size=5)
        return out
    if iid==7:
        # Camera help button: preserve icon region, replace only right text band.
        arr=np.asarray(en).copy(); x0,y0,x1,y1=96,0,en.width,en.height
        roi=arr[y0:y1,x0:x1]; px=roi.reshape(-1,4); valid=px[(px[:,3]>100) & (px[:,:3].mean(axis=1)<180)]
        col=np.median(valid,axis=0).astype(np.uint8) if len(valid) else np.array([80,80,80,255],np.uint8)
        arr[1:y1-1,103:x1-2]=col
        out=Image.fromarray(arr,'RGBA')
        _draw_fit_at(out,'Başlığa Dön',(102,1,x1-2,y1-1),fill=(245,245,245,255),serif=False,stroke_width=1,stroke=(25,25,25,240),min_size=4)
        return out
    if iid==307:
        # Minimap dowsing label; preserve chest graphic beneath.
        arr=np.asarray(en).copy(); roi=arr[0:14,5:70]; px=roi.reshape(-1,4); valid=px[px[:,3]>40]
        col=np.median(valid,axis=0).astype(np.uint8) if len(valid) else np.array([75,100,110,220],np.uint8)
        arr[0:14,5:70]=col
        out=Image.fromarray(arr,'RGBA')
        _draw_fit_at(out,'Sandıklar',(5,0,70,14),fill=(245,245,245,255),serif=False,stroke_width=1,stroke=(30,40,50,230),min_size=4)
        return out
    return None
