from __future__ import annotations
import math, struct, sys, zipfile, zlib, shutil, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, '/mnt/data')
import mp100_tool
from bflim_codec import info as bflim_info, decode as bflim_decode, _pow2ceil, _swizzle_for_pack

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'

def encode_la4(img: Image.Image, *, swizzle=4, align=0x80, version=0x07020100, endian='<') -> bytes:
    img=img.convert('RGBA')
    width,height=img.size
    swimg=_swizzle_for_pack(img,swizzle)
    w,h=swimg.size
    dataw=_pow2ceil(w); datah=_pow2ceil(h)
    tilesx=math.ceil(dataw/8); tilesy=math.ceil(datah/8)
    raw=bytearray(dataw*datah)
    pix=swimg.load()
    for yt in range(tilesy):
      for xt in range(tilesx):
       for ys in range(2):
        for xs in range(2):
         for yb in range(2):
          for xb in range(2):
           for yp in range(2):
            for xp in range(2):
             y=yt*8+ys*4+yb*2+yp; x=xt*8+xs*4+xb*2+xp
             if x>=w or y>=h: rgba=(0,0,0,0)
             else: rgba=pix[x,y]
             r,g,b,a=rgba
             # perceptual-ish luminance, then 4-bit quantize
             L=round((0.299*r+0.587*g+0.114*b)/17)
             A=round(a/17)
             L=max(0,min(15,L)); A=max(0,min(15,A))
             pindex=yt*tilesx*64+xt*64+ys*32+xs*16+yb*8+xb*4+yp*2+xp
             raw[pindex]=(L<<4)|A
    pad=(-len(raw))%align
    body=bytes(raw)+b'\0'*pad
    filelen=len(body)+40
    hdr=struct.pack(endian+'4sHHIIHH',b'FLIM',0xfeff,0x14,version,filelen,1,0)
    imag=struct.pack(endian+'4sIHHHBBI',b'imag',0x10,width,height,align,2,swizzle,len(raw))
    return body+hdr+imag

def fit_font(text,maxw,size_hi,size_lo=4):
    d=ImageDraw.Draw(Image.new('L',(1,1)))
    for s in range(size_hi,size_lo-1,-1):
        f=ImageFont.truetype(FONT,s)
        bb=d.textbbox((0,0),text,font=f)
        if bb[2]-bb[0] <= maxw: return f
    return ImageFont.truetype(FONT,size_lo)

def make_basla(src: Image.Image) -> Image.Image:
    # Keep the entire original pause icon/artwork, modify only the word plaque.
    im=src.convert('RGBA').copy()
    S=8
    big=im.resize((im.width*S,im.height*S), Image.Resampling.NEAREST)
    d=ImageDraw.Draw(big)
    # Original plaque is around x=17..48, y=26..37 at 64x64.
    # Repaint only the interior and edge so English letters are fully removed.
    x0,y0,x1,y1=(17*S,26*S,49*S,38*S)
    d.rectangle((x0,y0,x1,y1), fill=(238,238,238,255), outline=(88,88,88,255), width=S)
    # inner highlight, matching the original beveled label
    d.line([(18*S,27*S),(48*S,27*S)], fill=(255,255,255,255), width=S)
    d.line([(18*S,27*S),(18*S,37*S)], fill=(255,255,255,255), width=S)
    text='BAŞLA'
    # render at high-res for clean A4 quantization
    # fit against 28 pixels of native width
    f=fit_font(text,28,8,6)
    f=ImageFont.truetype(FONT,f.size*S)
    bb=d.textbbox((0,0),text,font=f)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    tx=(33*S-tw/2)-bb[0]
    ty=(32*S-th/2)-bb[1]
    d.text((tx,ty),text,font=f,fill=(55,55,55,255))
    return big.resize(im.size,Image.Resampling.LANCZOS)

def replace_sarc_same_size(sarc: bytes, name: str, replacement: bytes) -> bytes:
    for n,st,en in mp100_tool.sarc_entries(sarc):
        if n==name:
            if len(replacement)!=(en-st):
                raise ValueError(f'replacement size differs for {name}: {len(replacement)} != {en-st}')
            out=bytearray(sarc); out[st:en]=replacement; return bytes(out)
    raise KeyError(name)

def patch_system_zdat(system_zdat: bytes):
    arc=mp100_tool.rzpk_unpack(system_zdat)
    replacements={}
    report={}
    for name,raw,_ in arc['files']:
        if name!='sys_pause.arc': continue
        sarc=raw
        target='timg/sys_icon_pauseng.bflim'
        for n,st,en in mp100_tool.sarc_entries(sarc):
            if n==target:
                orig=sarc[st:en]
                inf=bflim_info(orig)
                if inf['format']!=2: raise ValueError(inf)
                src=bflim_decode(orig)
                edited=make_basla(src)
                enc=encode_la4(edited,swizzle=inf['swizzle'],align=inf['align'],version=inf['version'],endian=inf['endian'])
                if len(enc)!=len(orig): raise AssertionError((len(enc),len(orig)))
                # Verify file and visual decode after re-encode.
                chk=bflim_decode(enc)
                if chk.size!=src.size: raise AssertionError('decoded size changed')
                patched_sarc=replace_sarc_same_size(sarc,target,enc)
                replacements[name]=patched_sarc
                report={'archive':name,'texture':target,'translation':'START → BAŞLA','bflim':bflim_info(enc)}
                break
    if not replacements: raise RuntimeError('target texture not found')
    packed=mp100_tool.rzpk_pack(arc,replacements)
    # roundtrip verify replacement remains present and BFLIM decodes
    check=mp100_tool.rzpk_unpack(packed)
    sp=next(raw for name,raw,_ in check['files'] if name=='sys_pause.arc')
    for n,st,en in mp100_tool.sarc_entries(sp):
        if n=='timg/sys_icon_pauseng.bflim':
            im=bflim_decode(sp[st:en])
            if im.size!=(64,64): raise AssertionError('bad patched icon')
            break
    else: raise AssertionError('patched icon disappeared')
    return packed,report

def main():
    if len(sys.argv)<4:
        print('usage: patch_ui_graphics.py ROM.zip IN_LAYEREDFS_DIR OUT_LAYEREDFS_DIR'); return 2
    rom=Path(sys.argv[1]); srcdir=Path(sys.argv[2]); outdir=Path(sys.argv[3])
    if outdir.exists(): shutil.rmtree(outdir)
    shutil.copytree(srcdir,outdir)
    with zipfile.ZipFile(rom) as z:
        system=z.read('romfs/common/system/system.zdat')
    patched,rep=patch_system_zdat(system)
    root=outdir/'luma/titles/00040000001C4D00/romfs/common/system'
    root.mkdir(parents=True,exist_ok=True)
    (root/'system.zdat').write_bytes(patched)
    # update report if present
    rp=outdir/'build_report.json'
    data=json.loads(rp.read_text('utf-8')) if rp.exists() else {}
    data['ui_graphics_patch']=[rep]
    data['logos_modified']=False
    rp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rep,ensure_ascii=False,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
