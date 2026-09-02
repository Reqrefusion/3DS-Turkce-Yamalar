#!/usr/bin/env python3
"""Rebuild Turkish CP1254 glyphs in Cave Story 3D's BMFont from original glyph shapes.
Targets: 0xD0 Ğ, 0xDD İ, 0xDE Ş, 0xF0 ğ, 0xFD ı, 0xFE ş.
Uses the original game's Calibri bitmap atlas as the source, retaining anti-aliasing and metrics.
"""
from pathlib import Path
from PIL import Image
import argparse, re, numpy as np

TARGETS={208:71, 221:73, 222:83, 240:103, 253:105, 254:115}
PLACEMENT={208:(2,82), 221:(14,82), 222:(24,82), 240:(34,82), 253:(46,82), 254:(54,82)}
METRICS={
    208: dict(width=8,height=12,xoffset=0,yoffset=1,xadvance=8),   # Ğ
    221: dict(width=4,height=12,xoffset=0,yoffset=1,xadvance=4),   # İ
    222: dict(width=7,height=12,xoffset=-1,yoffset=3,xadvance=6),  # Ş
    240: dict(width=7,height=12,xoffset=0,yoffset=3,xadvance=6),   # ğ
    253: dict(width=4,height=8,xoffset=0,yoffset=5,xadvance=4),    # ı
    254: dict(width=6,height=10,xoffset=0,yoffset=5,xadvance=6),   # ş
}

def parse_chars(text):
    out={}
    for ln in text.splitlines():
        if ln.startswith('char id='):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',ln)}
            out[d['id']]=d
    return out

def crop_alpha(img,d):
    return np.array(img.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height'])))[:,:,3]

def make_glyphs(img, chars):
    G=crop_alpha(img,chars[71]); g=crop_alpha(img,chars[103])
    I=crop_alpha(img,chars[73]); i=crop_alpha(img,chars[105])
    S=crop_alpha(img,chars[83]); s=crop_alpha(img,chars[115])
    Cced=crop_alpha(img,chars[199]); cced=crop_alpha(img,chars[231])
    glyphs={}
    # Breve: deliberately light/anti-aliased and only two pixels high.
    breve8=np.zeros((2,8),dtype=np.uint8)
    breve8[0,[1,6]]=[120,120]
    breve8[1,[2,3,4,5]]=[95,200,200,95]
    breve7=np.zeros((2,7),dtype=np.uint8)
    breve7[0,[1,5]]=[120,120]
    breve7[1,[2,3,4]]=[110,220,110]
    # Ğ: accent + G body, following Ö/Ü vertical convention.
    a=np.zeros((12,8),dtype=np.uint8); a[0:2]=breve8; a[3:12]=G[1:10]; glyphs[208]=a
    # İ: copy actual i-dot alpha, then uppercase I body.
    a=np.zeros((12,4),dtype=np.uint8); a[1]=i[1]; a[3:12]=I[1:10]; glyphs[221]=a
    # Ş: S body + cedilla rows copied from original Ç.
    a=np.zeros((12,7),dtype=np.uint8); a[1:9]=S[1:9]
    # Center original Ç cedilla into width 7.
    a[9,2:4]=Cced[9,3:5]; a[10,2:4]=Cced[10,3:5]; glyphs[222]=a
    # ğ: same accent convention, original g including descender.
    a=np.zeros((12,7),dtype=np.uint8); a[0:2]=breve7; a[3:12]=g[1:10]; glyphs[240]=a
    # ı: lowercase i with dot area removed; crop to normal lowercase height.
    a=i[2:10].copy(); glyphs[253]=a
    # ş: s body + cedilla copied from original ç.
    a=np.zeros((10,6),dtype=np.uint8); a[1:7]=s[1:7]
    a[7,2:4]=cced[7,3:5]; a[8,2:4]=cced[8,3:5]; glyphs[254]=a
    return glyphs

def char_line(cid,x,y,m):
    return (f"char id={cid:<4} x={x:<5} y={y:<5} width={m['width']:<5} height={m['height']:<5} "
            f"xoffset={m['xoffset']:<5} yoffset={m['yoffset']:<5} xadvance={m['xadvance']:<5} page=0  chnl=15")

def rebuild_fnt(original_text):
    # Replace target char records.
    lines=original_text.replace('\r\n','\n').split('\n')
    out=[]
    for ln in lines:
        m=re.match(r'char id=(\d+)',ln)
        if m and int(m.group(1)) in TARGETS:
            cid=int(m.group(1)); x,y=PLACEMENT[cid]
            out.append(char_line(cid,x,y,METRICS[cid])); continue
        out.append(ln)
    # Rebuild kerning entries: remove old target-specific ones, clone from base letters.
    header_idx=next((i for i,l in enumerate(out) if l.startswith('kernings count=')),None)
    if header_idx is None:
        return '\r\n'.join(out)
    prefix=out[:header_idx]
    old_entries=[]
    for ln in out[header_idx+1:]:
        if ln.startswith('kerning first='):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',ln)}; old_entries.append(d)
    targets=set(TARGETS); base_to_target={v:k for k,v in TARGETS.items()}
    kept=[d for d in old_entries if d['first'] not in targets and d['second'] not in targets]
    generated={}
    # For every original non-target kerning, mirror G/g/I/i/S/s to its Turkish counterpart.
    for d in kept:
        f,s,a=d['first'],d['second'],d['amount']
        opts_f=[f] + ([base_to_target[f]] if f in base_to_target else [])
        opts_s=[s] + ([base_to_target[s]] if s in base_to_target else [])
        for ff in opts_f:
            for ss in opts_s:
                if ff==f and ss==s: continue
                generated[(ff,ss)]=a
    # Also preserve no duplicate and sort consistently.
    merged={(d['first'],d['second']):d['amount'] for d in kept}
    merged.update(generated)
    k_lines=[]
    for (f,s),a in sorted(merged.items()):
        k_lines.append(f"kerning first={f:<4} second={s:<4} amount={a}")
    prefix.append(f'kernings count={len(k_lines)}')
    prefix.extend(k_lines)
    return '\r\n'.join(prefix)+'\r\n'

def render_preview(img, fnt_text, out_path):
    chars=parse_chars(fnt_text)
    kern={}
    for ln in fnt_text.splitlines():
        if ln.startswith('kerning first='):
            d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',ln)}; kern[(d['first'],d['second'])]=d['amount']
    sample='ÇĞİÖŞÜ çğıöşü  Mağara Hikâyesi  Işınlanma  görüşürüz'
    bs=sample.encode('cp1254')
    W=420; H=40
    canvas=Image.new('RGBA',(W,H),(25,25,30,255)); x=8; baseline_y=5; prev=None
    for b in bs:
        if prev is not None: x+=kern.get((prev,b),0)
        d=chars.get(b)
        if not d: x+=6; prev=b; continue
        crop=img.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height']))
        canvas.alpha_composite(crop,(x+d['xoffset'],baseline_y+d['yoffset']))
        x+=d['xadvance']; prev=b
    canvas.resize((W*3,H*3),Image.Resampling.NEAREST).save(out_path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--original',default='/mnt/data/v9_work/orig/data')
    ap.add_argument('--target',default=str(Path(__file__).resolve().parents[1]/'000400000004D200/romfs/data'))
    ap.add_argument('--preview',default=str(Path(__file__).resolve().parents[1]/'ONIZLEMELER/font_tr_v9_preview.png'))
    a=ap.parse_args(); original=Path(a.original); target=Path(a.target); preview=Path(a.preview)
    img=Image.open(original/'font_batang_0.tga').convert('RGBA')
    fnt_bytes=(original/'font_batang.fnt').read_bytes(); original_text=fnt_bytes.decode('latin1')
    chars=parse_chars(original_text); glyphs=make_glyphs(img,chars)
    out_img=img.copy()
    # clear placement band from original (it is empty, but explicit makes reruns deterministic)
    for yy in range(80,100):
        for xx in range(0,80): out_img.putpixel((xx,yy),(255,255,255,0))
    arr=np.array(out_img)
    for cid,alpha in glyphs.items():
        x,y=PLACEMENT[cid]; h,w=alpha.shape
        arr[y:y+h,x:x+w,:3]=255; arr[y:y+h,x:x+w,3]=alpha
    out_img=Image.fromarray(arr,'RGBA')
    target.mkdir(parents=True,exist_ok=True)
    out_img.save(target/'font_batang_0.tga',format='TGA')
    out_fnt=rebuild_fnt(original_text)
    (target/'font_batang.fnt').write_bytes(out_fnt.encode('latin1'))
    preview.parent.mkdir(parents=True,exist_ok=True)
    render_preview(out_img,out_fnt,preview)
    print('Rebuilt Turkish glyphs:', ', '.join(chr(bytes([x]).decode('cp1254').encode('utf-8')[0]) if False else hex(x) for x in TARGETS))
    print('Preview:',preview)
if __name__=='__main__': main()
