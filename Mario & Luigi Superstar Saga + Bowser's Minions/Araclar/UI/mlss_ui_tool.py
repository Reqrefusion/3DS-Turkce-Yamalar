#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mario & Luigi: Superstar Saga + Bowser's Minions (3DS / ML1R)
UI BG4 translation helper.

Works on the user-supplied EU Obj archives. It identifies language-specific
sprite buffers by comparing the six EU language variants, replaces selected
English animation labels with Turkish raster text, Backwards-LZ77 compresses
the changed graphics, and rebuilds the BG4 archive without renaming entries.

This is a purpose-built implementation. Binary structure/rendering notes are
credited in THIRD_PARTY_NOTICES.txt in the distributed package.
"""
import argparse, csv, pathlib, struct
from collections import defaultdict
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# BG4 + Backwards LZ77
# ---------------------------------------------------------------------------
def entries_from_bytes(b):
    magic,ver,count,meta,derived,mult=struct.unpack_from('<4sHHIHH',b,0)
    if magic!=b'BG4\0': raise ValueError('BG4 magic bulunamadı')
    entries=[]; off=16
    for i in range(count):
        rawoff,rawsize,name_hash,name_off=struct.unpack_from('<IIIH',b,off)
        e={'i':i,'entry_off':off,'raw_file_offset':rawoff,'file_offset':rawoff&0x7fffffff,
           'compressed_flag':bool(rawoff&0x80000000),'file_size':rawsize&0x7fffffff,
           'raw_size':rawsize,'name_hash':name_hash,'name_offset':name_off}
        entries.append(e); off+=14
    origin=off
    for e in entries:
        pos=origin+e['name_offset']
        if pos>=len(b): e['name']='(invalid)'; continue
        end=b.find(b'\0',pos)
        if end<0: end=min(len(b),pos+128)
        e['name']=b[pos:end].decode('ascii','replace')
    return {'ver':ver,'count':count,'meta':meta,'derived':derived,'mult':mult,'origin':origin},entries

def valid_map(b,es):
    return {e['name']:e for e in es if e['file_offset'] and e['file_size'] and e['file_offset']+e['file_size']<=len(b)}

def blz_info(data):
    if len(data)<8:return None
    topbottom,origbottom=struct.unpack_from('<II',data,len(data)-8)
    top=topbottom&0xffffff; bottom=(topbottom>>24)&0xff
    return {'ok':8<=bottom<=11 and bottom<=top<=len(data),'top':top,'bottom':bottom,
            'origbottom':origbottom,'usize':len(data)+origbottom}

def blz_decompress(data):
    info=blz_info(data)
    if not info or not info['ok']: raise ValueError('Backwards LZ77 başlığı geçersiz')
    out=bytearray(len(data)+info['origbottom']); out[:len(data)]=data
    dest=len(out); src=len(data)-info['bottom']; end=len(data)-info['top']
    while src>end:
        src-=1; flag=out[src]
        for i in range(8):
            if ((flag<<i)&0x80)==0:
                dest-=1; src-=1; out[dest]=out[src]
            else:
                src-=1; n=out[src]; src-=1
                noff=(((n&0x0f)<<8)|out[src])+3; nsize=((n>>4)&0x0f)+3
                p=dest+noff
                for _ in range(nsize): dest-=1; p-=1; out[dest]=out[p]
            if src<=end: break
    return bytes(out)

def blz_compress(data, prefix_len=0):
    data=bytes(data)
    suffix=data[prefix_len:]; y=suffix[::-1]
    out=bytearray(); pos=0; n=len(y)
    while pos<n:
        fpos=len(out); out.append(0); flag=0
        for bit in range(8):
            if pos>=n: break
            best_len=0; best_dist=0; maxdist=min(4098,pos)
            if maxdist>=3:
                lo=max(0,pos-maxdist); target=bytes([y[pos]])
                cand=y.rfind(target,lo,pos-2); tries=0
                while cand>=lo and tries<256:
                    dist=pos-cand
                    if dist>=3:
                        L=1; maxL=min(18,n-pos)
                        while L<maxL and y[pos+L]==y[pos+L-dist]: L+=1
                        if L>=3 and L>best_len:
                            best_len,best_dist=L,dist
                            if L==18: break
                    tries+=1; cand=y.rfind(target,lo,cand)
            if best_len>=3:
                flag|=0x80>>bit; v=best_dist-3
                out.append(((best_len-3)<<4)|((v>>8)&0xf)); out.append(v&0xff); pos+=best_len
            else:
                out.append(y[pos]); pos+=1
        out[fpos]=flag
    stream=bytes(out)[::-1]
    comp=bytearray(data[:prefix_len]); comp+=stream
    final_len=len(comp)+8; origbottom=len(data)-final_len
    if origbottom<=0: raise ValueError('Veri BLZ için yeterince sıkışmadı')
    top=final_len-prefix_len
    if top>0xffffff: raise ValueError('BLZ bölümü çok büyük')
    comp+=struct.pack('<II',top|(8<<24),origbottom)
    res=bytes(comp)
    if blz_decompress(res)!=data: raise ValueError('BLZ roundtrip başarısız')
    return res

def blz_compress_best(data):
    for p in (0,16,32,64,128,256,512,1024,2048,4096):
        if p>=len(data): break
        try:return blz_compress(data,p)
        except ValueError: pass
    raise ValueError('BLZ sıkıştırması üretilemedi')

def dec_entry(b,e):
    raw=b[e['file_offset']:e['file_offset']+e['file_size']]
    return blz_decompress(raw) if e['compressed_flag'] else raw

def load_assets(archive_path):
    b=pathlib.Path(archive_path).read_bytes(); h,es=entries_from_bytes(b); vm=valid_map(b,es)
    cai=dec_entry(b,vm['_CA_INFO_']); ch,ces=entries_from_bytes(cai); cv=valid_map(cai,ces)
    out={}
    for name,e in cv.items():
        rec=cai[e['file_offset']:e['file_offset']+e['file_size']]
        names=[x.decode('ascii','replace') for x in rec.split(b'\0') if x and all(32<=c<127 for c in x)]
        if len(names)>=2 and names[0] in vm and names[1] in vm:
            out[name]={'meta_entry':names[0],'graph_entry':names[1],
                       'meta':dec_entry(b,vm[names[0]]),'graph':dec_entry(b,vm[names[1]])}
    return b,h,es,vm,out

def repack_bg4(original, header, entries, replacements):
    """replacements maps top-level entry name -> raw stored blob (already compressed if flag set)."""
    b=bytearray(original[:header['meta']]); valid=[e for e in entries if e['file_offset'] and e['file_size']]
    valid.sort(key=lambda e:e['file_offset'])
    pos=header['meta']
    for e in valid:
        old=original[e['file_offset']:e['file_offset']+e['file_size']]
        blob=replacements.get(e['name'],old)
        flag=0x80000000 if e['compressed_flag'] else 0
        struct.pack_into('<I',b,e['entry_off'],pos|flag)
        struct.pack_into('<I',b,e['entry_off']+4,len(blob)|(e['raw_size']&0x80000000))
        b.extend(blob); pos+=len(blob)
    return bytes(b)

# ---------------------------------------------------------------------------
# ML1R sprite structures / pixels
# ---------------------------------------------------------------------------
SW=np.array([
0x00,0x01,0x04,0x05,0x10,0x11,0x14,0x15,0x02,0x03,0x06,0x07,0x12,0x13,0x16,0x17,
0x08,0x09,0x0C,0x0D,0x18,0x19,0x1C,0x1D,0x0A,0x0B,0x0E,0x0F,0x1A,0x1B,0x1E,0x1F,
0x20,0x21,0x24,0x25,0x30,0x31,0x34,0x35,0x22,0x23,0x26,0x27,0x32,0x33,0x36,0x37,
0x28,0x29,0x2C,0x2D,0x38,0x39,0x3C,0x3D,0x2A,0x2B,0x2E,0x2F,0x3A,0x3B,0x3E,0x3F],dtype=np.int64)
SIZES=[[(8,8),(16,16),(32,32),(64,64)],[(16,8),(32,8),(32,16),(64,32)],[(8,16),(8,32),(16,32),(32,64)]]
MODES=[('RGBA8888',32),('RGB888',24),('RGBA5551',16),('RGB565',16),('RGBA4444',16),('LA88',16),('HILO88',16),('L8',8),('A8',8),('LA44',8),('L4',4),('A4',4),('ETC1',4),('ETC1A4',8)]
class AnimData:
    def __init__(self,b):
        self.b=b
        self.anim_num,self.color_idx,self.renderer_num,self.unused,self.anim_file_length,self.graph_file_length=struct.unpack_from('<4B2I',b,0)
        self.frame_offset,self.part_offset_raw,self.part_trans_offset,self.full_trans_offset,self.renderer_offset,self.normal_offset=struct.unpack_from('<6I',b,12)
        self.anim_offset=100; self.sprite_sheet_mode=self.part_offset_raw==0
        self.part_offset=self.anim_offset+self.anim_num*8 if self.sprite_sheet_mode else self.part_offset_raw
        self.mode=MODES[self.color_idx]
        if self.sprite_sheet_mode: raise NotImplementedError('Sprite-sheet modu bu araçta düzenlenmiyor')
    def anim(self,i):return struct.unpack_from('<4H',self.b,self.anim_offset+i*8)
    def frame(self,i):return struct.unpack_from('<HBBHH',self.b,self.frame_offset+i*8)
    def part(self,i):return struct.unpack_from('<HHhHhhI',self.b,self.part_offset+i*16)

def dims_for_part(p):
    sh=(p[0]>>2)&3; sz=p[0]&3
    if sh>2: raise ValueError('Geçersiz OAM shape')
    return SIZES[sh][sz]

def _swizzle(w,h):return (np.arange((w*h)//64)[:,None]*64+SW).flatten()

def decode_pixels(raw,mode,sw):
    raw=np.frombuffer(raw,dtype=np.uint8)
    if mode=='RGBA8888':
        p=raw.view('<u4')[sw].astype(np.uint32); r=(p>>24)&255;g=(p>>16)&255;b=(p>>8)&255;a=p&255
    elif mode=='RGBA4444':
        p=raw.view('<u2')[sw].astype(np.uint16);r=((p>>12)&15)*17;g=((p>>8)&15)*17;b=((p>>4)&15)*17;a=(p&15)*17
    elif mode=='RGBA5551':
        p=raw.view('<u2')[sw].astype(np.uint16);r=((p>>11)&31)*255//31;g=((p>>6)&31)*255//31;b=((p>>1)&31)*255//31;a=(p&1)*255
    elif mode=='RGB565':
        p=raw.view('<u2')[sw].astype(np.uint16);r=((p>>11)&31)*255//31;g=((p>>5)&63)*255//63;b=(p&31)*255//31;a=np.full_like(r,255)
    else: raise NotImplementedError('Yazma için desteklenmeyen texture modu: '+mode)
    return np.stack([r,g,b,a],-1).astype(np.uint8)

def encode_pixels(pix,mode,sw):
    r=pix[:,0].astype(np.uint32);g=pix[:,1].astype(np.uint32);b=pix[:,2].astype(np.uint32);a=pix[:,3].astype(np.uint32)
    n=len(pix)
    if mode=='RGBA8888': vals=(r<<24)|(g<<16)|(b<<8)|a; raw=np.zeros(n,dtype='<u4');raw[sw]=vals.astype('<u4');return raw.tobytes()
    if mode=='RGBA4444':
        vals=((r+8)//17<<12)|((g+8)//17<<8)|((b+8)//17<<4)|((a+8)//17);raw=np.zeros(n,dtype='<u2');raw[sw]=vals.astype('<u2');return raw.tobytes()
    if mode=='RGBA5551':
        vals=((r*31+127)//255<<11)|((g*31+127)//255<<6)|((b*31+127)//255<<1)|(a>=128);raw=np.zeros(n,dtype='<u2');raw[sw]=vals.astype('<u2');return raw.tobytes()
    if mode=='RGB565':
        vals=((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b*31+127)//255);raw=np.zeros(n,dtype='<u2');raw[sw]=vals.astype('<u2');return raw.tobytes()
    raise NotImplementedError(mode)

def decode_part(ad,graph,pi,display=True):
    p=ad.part(pi);w,h=dims_for_part(p);st=128*p[3];sz=w*h*ad.mode[1]//8
    px=decode_pixels(graph[st:st+sz],ad.mode[0],_swizzle(w,h))
    out=px.reshape(h//8,w//8,8,8,4).transpose(0,2,1,3,4).reshape(h,w,4)
    if display:
        if p[0]&0x100: out=np.flip(out,1)
        if p[0]&0x200: out=np.flip(out,0)
    return out.copy()

def encode_part(ad,pi,img_display):
    p=ad.part(pi);w,h=dims_for_part(p);out=np.array(img_display,dtype=np.uint8).copy()
    if out.shape!=(h,w,4): raise ValueError('Parça boyutu uyuşmuyor')
    if p[0]&0x200: out=np.flip(out,0)
    if p[0]&0x100: out=np.flip(out,1)
    pix=out.reshape(h//8,8,w//8,8,4).transpose(0,2,1,3,4).reshape(-1,4)
    return encode_pixels(pix,ad.mode[0],_swizzle(w,h))

def rect_for_part(ad,pi):
    p=ad.part(pi);w,h=dims_for_part(p);x,y=p[4],p[5]
    return (x-w//2,-y-h//2,x-w//2+w,-y-h//2+h)

# ---------------------------------------------------------------------------
# Translation drawing
# ---------------------------------------------------------------------------
LANGS=('en','fr','sp','it','ge','du')
NORMAL_FONT_CANDIDATES=[
    # Windows
    'C:/Windows/Fonts/arialbd.ttf','C:/Windows/Fonts/seguisb.ttf','C:/Windows/Fonts/arial.ttf',
    # macOS
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf','/Library/Fonts/Arial Bold.ttf',
    # Linux
    '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf']
STYLIZED_FONT_CANDIDATES=[
    'C:/Windows/Fonts/arialbd.ttf','C:/Windows/Fonts/seguisb.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf','/Library/Fonts/Arial Bold.ttf',
    '/usr/share/fonts/truetype/noto/NotoSans-Black.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf']
def find_font(stylized=False):
    for p in (STYLIZED_FONT_CANDIDATES if stylized else NORMAL_FONT_CANDIDATES):
        if pathlib.Path(p).exists():return p
    raise FileNotFoundError('Türkçe karakterleri içeren uygun bir sistem fontu bulunamadı')

def pixel_mode_background(images):
    """Approximate language-neutral base from 2..6 same-sized RGBA images."""
    a=np.stack(images,0).astype(np.uint8); L,H,W,_=a.shape
    vals=a.reshape(L,-1,4).copy().view('<u4').reshape(L,-1)
    counts=np.stack([(vals==vals[i]).sum(0) for i in range(L)],0)
    best=counts.argmax(0); maxc=counts.max(0)
    col=np.arange(vals.shape[1]); chosen=vals[best,col].copy()
    tie=np.where(maxc==1)[0]
    if len(tie):
        rgba=a.reshape(L,-1,4)[:,tie,:]
        alpha=rgba[:,:,3].astype(np.int32); lum=rgba[:,:,:3].mean(2)
        score=alpha*1000+lum
        bi=score.argmin(0); chosen[tie]=vals[bi,tie]
    return chosen.view(np.uint8).reshape(H,W,4).copy()

def text_bbox(draw,text,font,stroke=0,spacing=0):
    if '\n' in text:return draw.multiline_textbbox((0,0),text,font=font,stroke_width=stroke,spacing=spacing,align='center')
    return draw.textbbox((0,0),text,font=font,stroke_width=stroke)

def fit_font(text,w,h,max_size=None,stroke_ratio=.08):
    fontfile=find_font(False); max_size=max_size or max(6,int(h*.68)); dummy=ImageDraw.Draw(Image.new('L',(1,1)))
    for size in range(max_size,4,-1):
        f=ImageFont.truetype(fontfile,size); sw=max(1,round(size*stroke_ratio)); box=text_bbox(dummy,text,f,sw,max(0,size//10));tw=box[2]-box[0];th=box[3]-box[1]
        if tw<=w and th<=h:return f,sw,box
    f=ImageFont.truetype(fontfile,5);return f,1,text_bbox(dummy,text,f,1,0)

def render_normal(text,size,fill=(245,245,245,255),stroke=(55,40,32,255),target_bbox=None,tiny=False):
    W,H=size; layer=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(layer)
    if target_bbox is None:target_bbox=(1,1,W-1,H-1)
    x0,y0,x1,y1=target_bbox; aw=max(2,x1-x0);ah=max(2,y1-y0)
    f,sw,box=fit_font(text,aw,ah,max_size=(ah if tiny else None),stroke_ratio=.055 if tiny else .07)
    spacing=max(0,getattr(f,'size',10)//10)
    box=text_bbox(d,text,f,sw,spacing);tw=box[2]-box[0];th=box[3]-box[1]
    x=x0+(aw-tw)//2-box[0];y=y0+(ah-th)//2-box[1]
    if '\n' in text:d.multiline_text((x,y),text,font=f,fill=fill,stroke_width=sw,stroke_fill=stroke,spacing=spacing,align='center')
    else:d.text((x,y),text,font=f,fill=fill,stroke_width=sw,stroke_fill=stroke)
    return np.array(layer)

def render_stylized(text,size,theme='orange',target_bbox=None):
    W,H=size
    if target_bbox is None:target_bbox=(1,1,W-1,H-1)
    x0,y0,x1,y1=target_bbox; aw=max(2,x1-x0);ah=max(2,y1-y0)
    dummy=ImageDraw.Draw(Image.new('L',(1,1)))
    fontfile=find_font(True)
    f=None; outer=1
    for sz in range(max(7,int(ah*.9)),6,-1):
        ff=ImageFont.truetype(fontfile,sz); oo=max(2,sz//9); bb=text_bbox(dummy,text,ff,oo,max(0,sz//12));
        if bb[2]-bb[0]<=aw and bb[3]-bb[1]<=ah:f,outer,box=ff,oo,bb;break
    if f is None:f=ImageFont.truetype(fontfile,7);outer=1;box=text_bbox(dummy,text,f,outer,0)
    spacing=max(0,f.size//12); box=text_bbox(dummy,text,f,outer,spacing);tw=box[2]-box[0];th=box[3]-box[1]
    x=x0+(aw-tw)//2-box[0];y=y0+(ah-th)//2-box[1]
    fillmask=Image.new('L',(W,H),0);fd=ImageDraw.Draw(fillmask)
    bordermask=Image.new('L',(W,H),0);bd=ImageDraw.Draw(bordermask)
    innermask=Image.new('L',(W,H),0);idraw=ImageDraw.Draw(innermask)
    kwargs=dict(font=f,spacing=spacing,align='center')
    fn='multiline_text' if '\n' in text else 'text'
    getattr(bd,fn)((x,y),text,fill=255,stroke_width=outer,stroke_fill=255,**kwargs)
    inner=max(1,outer//2)
    getattr(idraw,fn)((x,y),text,fill=255,stroke_width=inner,stroke_fill=255,**kwargs)
    getattr(fd,fn)((x,y),text,fill=255,**kwargs)
    palettes={
      'blue':((40,145,255,255),(65,235,255,255)),
      'orange':((255,235,75,255),(255,115,20,255)),
      'green':((95,255,100,255),(255,235,55,255)),
      'red':((255,40,35,255),(255,100,145,255)),
      'white':((255,255,255,255),(150,220,255,255)),
      'yellow':((255,255,105,255),(255,160,20,255)),
      'rainbow':((255,235,45,255),(255,100,45,255)),
    }
    top,bot=palettes.get(theme,palettes['orange'])
    grad=np.zeros((H,W,4),dtype=np.uint8)
    for yy in range(H):
        t=yy/max(1,H-1); grad[yy,:,0:4]=[round(top[c]*(1-t)+bot[c]*t) for c in range(4)]
    if theme=='rainbow':
        cols=[(255,230,30),(40,230,70),(40,215,255),(255,120,20)]
        for xx in range(W):
            k=(xx/max(1,W-1))*(len(cols)-1);i=min(len(cols)-2,int(k));t=k-i
            grad[:,xx,:3]=[round(cols[i][c]*(1-t)+cols[i+1][c]*t) for c in range(3)]
    out=Image.new('RGBA',(W,H),(0,0,0,0))
    navy=Image.new('RGBA',(W,H),(7,30,82,255)); white=Image.new('RGBA',(W,H),(245,248,255,255)); g=Image.fromarray(grad)
    out.paste(navy,(0,0),bordermask);out.paste(white,(0,0),innermask);out.paste(g,(0,0),fillmask)
    return np.array(out)

def clean_normal_background(base, english):
    """Remove pre-rendered localized label pixels while keeping dark UI backing."""
    out=base.copy(); rgb=english[:,:,:3].astype(np.int16); alpha=english[:,:,3]
    lum=rgb.max(2)
    mask=(alpha>24)&(lum>105)
    sat=rgb.max(2)-rgb.min(2); mask |= (alpha>40)&(sat>70)&(lum>75)
    if not mask.any():
        if (alpha>8).mean()<0.30: return np.zeros_like(out)
        return out
    m=Image.fromarray((mask*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(3))
    mask=np.array(m)>0
    if (out[:,:,3]>8).mean()<0.45:
        repl=np.array([0,0,0,0],dtype=np.uint8)
    else:
        keep=~mask; vals=out[keep]
        if len(vals):
            packed=vals.copy().view('<u4').reshape(-1)
            uniq,cnt=np.unique(packed,return_counts=True); v=int(uniq[cnt.argmax()])
            repl=np.array([v&255,(v>>8)&255,(v>>16)&255,(v>>24)&255],dtype=np.uint8)
        else: repl=np.array([0,0,0,0],dtype=np.uint8)
    out[mask]=repl
    return out

def estimate_fill(en_parts,neutral_parts):
    samples=[]
    for a,b in zip(en_parts,neutral_parts):
        diff=np.any(a!=b,2)&(a[:,:,3]>30)
        px=a[diff]
        if len(px):samples.append(px)
    if not samples:return (245,245,245,255),(50,35,30,255)
    px=np.concatenate(samples,0); lum=px[:,:3].mean(1)
    bright=px[lum>=np.percentile(lum,75)]
    fill=tuple(np.median(bright,0).astype(int).tolist()) if len(bright) else (245,245,245,255)
    dark=px[lum<=np.percentile(lum,25)]
    stroke=tuple(np.median(dark,0).astype(int).tolist()) if len(dark) else (50,35,30,255)
    if max(fill[:3])<105: fill=(245,245,245,255)
    if stroke[3]<80: stroke=(45,35,30,255)
    return fill,stroke

def load_translation_csv(path):
    rows=[]
    with open(path,'r',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r.get('enabled','1').strip().lower() in ('0','false','no','hayır'):continue
            r['animation']=int(r['animation'])
            r['turkish']=r.get('turkish','').replace('\\n','\n')
            r['english']=r.get('english','').replace('\\n','\n')
            rows.append(r)
    return rows

def translate_archive(src_path,out_path,rows,preview_dir=None):
    original,h,es,vm,assets=load_assets(src_path)
    graph_work={}; graph_entry_for={}; modified_entries=set(); report=[]
    for row in rows:
        name=row['asset']; ai=row['animation']; tr=row['turkish']; style=row.get('style','normal').strip() or 'normal'
        if name not in assets: report.append((name,ai,'SKIP: asset yok'));continue
        base=name[:-2] if name.endswith('en') else None
        variants={l:assets.get(base+l) for l in LANGS} if base else {}
        variants={l:v for l,v in variants.items() if v is not None}
        if 'en' not in variants or len(variants)<2: report.append((name,ai,'SKIP: dil varyantı yetersiz'));continue
        en=variants['en']; ad=AnimData(en['meta'])
        if ai<0 or ai>=ad.anim_num: report.append((name,ai,'SKIP: anim index'));continue
        graphs={l:v['graph'] for l,v in variants.items()}
        if name not in graph_work:graph_work[name]=bytearray(en['graph']);graph_entry_for[name]=en['graph_entry']
        work=graph_work[name]
        ff,nframes,_,_=ad.anim(ai); fp,np_,*_=ad.frame(ff)
        diff_parts=[]
        for pi in range(fp,fp+np_):
            p=ad.part(pi);w,hh=dims_for_part(p);st=128*p[3];sz=w*hh*ad.mode[1]//8
            chunks=[graphs[l][st:st+sz] for l in variants]
            if len(set(chunks))>1:diff_parts.append(pi)
        if not diff_parts: report.append((name,ai,'SKIP: yerelleştirilmiş parça yok'));continue
        rects=[rect_for_part(ad,pi) for pi in diff_parts]
        minx=min(r[0] for r in rects);miny=min(r[1] for r in rects);maxx=max(r[2] for r in rects);maxy=max(r[3] for r in rects)
        W=maxx-minx;H=maxy-miny
        en_imgs=[];neutral=[]
        for pi in diff_parts:
            imgs=[decode_part(ad,graphs[l],pi,display=True) for l in variants]
            en_imgs.append(imgs[list(variants).index('en')])
            neutral.append(pixel_mode_background(imgs))
        mask=np.zeros((H,W),dtype=bool)
        for pi,eim,bim,r in zip(diff_parts,en_imgs,neutral,rects):
            x0,y0,x1,y1=r; local=np.any(eim!=bim,2)&(eim[:,:,3]>8)
            yy=y0-miny;xx=x0-minx;mask[yy:yy+local.shape[0],xx:xx+local.shape[1]] |= local
        ys,xs=np.where(mask)
        if len(xs):
            bx0=max(0,int(xs.min())-2);by0=max(0,int(ys.min())-2);bx1=min(W,int(xs.max())+3);by1=min(H,int(ys.max())+3)
        else: bx0,by0,bx1,by1=1,1,W-1,H-1
        eng=row.get('english','')
        if len(tr.replace('\n',''))>max(1,len(eng))*1.12: bx0=1;bx1=W-1
        target=(bx0,by0,bx1,by1)
        if style.startswith('stylized'):
            theme=style.split('_',1)[1] if '_' in style else 'orange'
            textlayer=render_stylized(tr,(W,H),theme,target)
            bases=[np.zeros_like(x) for x in neutral]
        else:
            fill,stroke=estimate_fill(en_imgs,neutral)
            if style in ('normal_white','clear_white'):fill=(245,245,245,255)
            if style in ('normal_yellow','clear_yellow'):fill=(255,235,55,255)
            if style.startswith('clear_'):
                target=(1,1,W-1,H-1)
            textlayer=render_normal(tr,(W,H),fill,stroke,target,tiny=(style=='tiny'))
            bases=([np.zeros_like(x) for x in neutral] if style.startswith('clear_')
                   else [clean_normal_background(b,e) for b,e in zip(neutral,en_imgs)])
        for pi,baseim,r in zip(diff_parts,bases,rects):
            x0,y0,x1,y1=r; sx=x0-minx;sy=y0-miny; overlay=textlayer[sy:sy+(y1-y0),sx:sx+(x1-x0)]
            out=baseim.copy(); oa=overlay[:,:,3:4].astype(np.float32)/255.0
            out[:,:,:3]=(overlay[:,:,:3]*oa+out[:,:,:3]*(1-oa)).round().astype(np.uint8)
            out[:,:,3]=(overlay[:,:,3]+out[:,:,3]*(1-overlay[:,:,3].astype(np.float32)/255)).round().clip(0,255).astype(np.uint8)
            enc=encode_part(ad,pi,out);p=ad.part(pi);st=128*p[3]
            work[st:st+len(enc)]=enc
        report.append((name,ai,'OK'))
        if preview_dir:
            prev=np.zeros((H,W,4),dtype=np.uint8)
            for pi,r in zip(diff_parts,rects):
                x0,y0,x1,y1=r;pimg=decode_part(ad,bytes(work),pi,display=True);xx=x0-minx;yy=y0-miny
                dst=prev[yy:yy+pimg.shape[0],xx:xx+pimg.shape[1]];a=pimg[:,:,3:4].astype(float)/255
                dst[:,:,:3]=(pimg[:,:,:3]*a+dst[:,:,:3]*(1-a)).round().astype(np.uint8)
                dst[:,:,3]=(pimg[:,:,3]+dst[:,:,3]*(1-a[:,:,0])).round().clip(0,255).astype(np.uint8)
            pathlib.Path(preview_dir).mkdir(parents=True,exist_ok=True)
            Image.fromarray(prev).save(pathlib.Path(preview_dir)/f'{name}_a{ai:02d}.png')
    replacements={}
    for name,work in graph_work.items():
        entry=graph_entry_for[name]; comp=blz_compress_best(bytes(work)); replacements[entry]=comp;modified_entries.add(entry)
    rebuilt=repack_bg4(original,h,es,replacements)
    pathlib.Path(out_path).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(out_path).write_bytes(rebuilt)
    rb=rebuilt; rh,res=entries_from_bytes(rebuilt); rvm=valid_map(rb,res)
    for name,work in graph_work.items():
        entry=graph_entry_for[name]
        if dec_entry(rb,rvm[entry])!=bytes(work):raise ValueError(f'Yeniden paketleme doğrulaması başarısız: {entry}')
    return report,modified_entries

def main():
    ap=argparse.ArgumentParser(description='MLSS 3DS EU UI Türkçe sprite yama aracı')
    ap.add_argument('obj_eu',help='Obj/EU klasörü')
    ap.add_argument('translations',help='ui_translations.csv')
    ap.add_argument('output',help='çıktı Obj/EU klasörü')
    ap.add_argument('--preview',help='QA PNG klasörü')
    args=ap.parse_args(); rows=load_translation_csv(args.translations);by=defaultdict(list)
    for r in rows:by[r['archive']].append(r)
    out=pathlib.Path(args.output);out.mkdir(parents=True,exist_ok=True)
    for arc,rr in sorted(by.items()):
        src=pathlib.Path(args.obj_eu)/(arc+'.dat');dst=out/(arc+'.dat')
        rep,changed=translate_archive(src,dst,rr,(pathlib.Path(args.preview)/arc if args.preview else None))
        ok=sum(1 for x in rep if x[2]=='OK');print(f'{arc}: {ok}/{len(rep)} çeviri, {len(changed)} grafik kaydı güncellendi')
    return 0
if __name__=='__main__':raise SystemExit(main())
