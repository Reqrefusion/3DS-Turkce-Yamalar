#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import struct, json, hashlib, sys
sys.path.insert(0, str(Path(__file__).parent))
from mh4_lmd_tool_v3 import ArcFile

ARC=Path('/mnt/data/v7work/patched/eng/data/core_common.arc')
OUT=Path('/mnt/data/v7work/font_report'); OUT.mkdir(parents=True,exist_ok=True)
# text codepoint donor -> intended Turkish glyph. LFD records remain untouched.
MAP={'Ō':'Ğ','ō':'ğ','ˇ':'İ','˘':'ı','Ū':'Ş','¿':'ş'}
BASE={'Ğ':'G','ğ':'g','İ':'I','ı':'i','Ş':'S','ş':'s'}

def sha(b): return hashlib.sha256(b).hexdigest()
def parse_tex_header(b):
    if b[:4]!=b'TEX\0': raise ValueError('not TEX')
    x=int.from_bytes(b[4:12],'little'); o=0
    def take(n):
        nonlocal o
        v=(x>>o)&((1<<n)-1);o+=n;return v
    ver=take(12); sw=take(12); take(4); take(4); mip=take(6); w=take(13); h=take(13)
    return ver,sw,mip,w,h,b[12],b[13]
def decode_a4(b):
    ver,sw,mip,w,h,imgs,fmt=parse_tex_header(b)
    if sw!=0 or fmt!=0x0E: raise ValueError((ver,sw,mip,w,h,imgs,fmt))
    off=16+(0 if ver==0xA4 else mip*imgs*4)
    raw=b[off:off+w*h//2]
    vals=[]
    for q in raw: vals.extend([(q&15)*17,((q>>4)&15)*17])
    pix=bytearray(w*h);i=0
    for ty in range(0,h,8):
      for tx in range(0,w,8):
       for p in range(64):
        xx=(p&1)|((p&4)>>1)|((p&16)>>2); yy=((p&2)>>1)|((p&8)>>2)|((p&32)>>3)
        pix[(ty+yy)*w+tx+xx]=vals[i];i+=1
    return off,w,h,Image.frombytes('L',(w,h),bytes(pix))
def encode_a4(template,off,im):
    w,h=im.size; d=im.tobytes(); n=[]
    for ty in range(0,h,8):
      for tx in range(0,w,8):
       for p in range(64):
        xx=(p&1)|((p&4)>>1)|((p&16)>>2); yy=((p&2)>>1)|((p&8)>>2)|((p&32)>>3)
        n.append(max(0,min(15,int(round(d[(ty+yy)*w+tx+xx]/17)))))
    raw=bytearray(n[i]|(n[i+1]<<4) for i in range(0,len(n),2)); out=bytearray(template); out[off:off+len(raw)]=raw; return bytes(out)

def parse_lfd(b):
    if b[:4]!=b'lfd\0': raise ValueError('bad lfd')
    count=struct.unpack_from('<I',b,8)[0]; table=struct.unpack_from('<I',b,0x1c)[0]; end=struct.unpack_from('<I',b,0x20)[0]
    if table+count*20!=end: raise ValueError('bad table')
    rec={}
    for i in range(count):
      o=table+i*20; cp=struct.unpack_from('<I',b,o)[0]; x=struct.unpack_from('<H',b,o+5)[0]; y=b[o+7]*16; w=b[o+8]; adv=struct.unpack_from('<H',b,o+12)[0]
      rec[chr(cp)]={'i':i,'x':x,'y':y,'w':w,'adv':adv}
    return count,rec

def pmax(dst,src,x,y):
    for sy in range(src.height):
      dy=y+sy
      if not 0<=dy<dst.height: continue
      for sx in range(src.width):
       dx=x+sx
       if 0<=dx<dst.width:
        v=src.getpixel((sx,sy))
        if v>dst.getpixel((dx,dy)): dst.putpixel((dx,dy),v)

a=ArcFile.parse(ARC.read_bytes())
tex=a.entries[2].decompress(); lfd=a.entries[3].decompress(); lfd_sha=sha(lfd)
off,W,H,atlas=decode_a4(tex); before=atlas.copy(); count,recs=parse_lfd(lfd)
required=set(MAP)|set(BASE.values())|{'Ç','ç','˙'}
missing=required-set(recs)
if missing: raise SystemExit(f'missing records {missing}')
# exact donor metrics: no LFD edits needed
for d,t in MAP.items():
    dm,bm=recs[d],recs[BASE[t]]
    if (dm['w'],dm['adv']) != (bm['w'],bm['adv']):
        raise SystemExit(f'metric mismatch {d}->{t}: donor {(dm["w"],dm["adv"])} base {(bm["w"],bm["adv"])}')

def crop(ch):
    m=recs[ch]; return before.crop((m['x'],m['y'],m['x']+m['w'],m['y']+16))
def accent(ch):
    c=crop(ch); bb=c.getbbox();
    if not bb: raise ValueError(ch)
    return c.crop(bb)
breve=accent('˘'); dot=accent('˙'); Cced=crop('Ç'); cced=crop('ç')

def synth(ch,w):
    base=crop(BASE[ch]); out=Image.new('L',(w,16),0); x=max(0,(w-base.width)//2)
    if ch=='Ğ':
      pmax(out,base,x,2); pmax(out,breve,(w-breve.width)//2,0)
    elif ch=='ğ':
      pmax(out,base,x,0); pmax(out,breve,(w-breve.width)//2,1)
    elif ch=='İ':
      pmax(out,base,x,2); pmax(out,dot,(w-dot.width)//2,0)
    elif ch=='ı':
      clean=base.copy()
      for yy in range(0,5):
       for xx in range(clean.width): clean.putpixel((xx,yy),0)
      pmax(out,clean,x,0)
    elif ch=='Ş':
      pmax(out,base,x,-1); ced=Cced.crop((0,12,Cced.width,16)); pmax(out,ced,(w-ced.width)//2,12)
    elif ch=='ş':
      pmax(out,base,x,0); ced=cced.crop((0,13,cced.width,16)); pmax(out,ced,(w-ced.width)//2,13)
    return out

allowed=set(); rep=[]
for donor,turk in MAP.items():
    m=recs[donor]; rect=(m['x'],m['y'],m['x']+m['w'],m['y']+16)
    atlas.paste(0,rect); atlas.paste(synth(turk,m['w']),(m['x'],m['y']))
    for y in range(rect[1],rect[3]):
      for x in range(rect[0],rect[2]): allowed.add((x,y))
    rep.append({'donor':donor,'turkish':turk,**m})
newtex=encode_a4(tex,off,atlas)
_,_,_,rt=decode_a4(newtex)
changed=[]; outside=[]
for y in range(H):
  for x in range(W):
    if before.getpixel((x,y))!=rt.getpixel((x,y)):
      changed.append((x,y))
      if (x,y) not in allowed: outside.append((x,y))
if outside: raise SystemExit(f'outside pixels {outside[:8]} count={len(outside)}')
# build ARC changing ONLY texture entry 2
pre=[e.decompress() for e in a.entries]
newarc=a.build({2:newtex}); b=ArcFile.parse(newarc)
for i,e in enumerate(b.entries):
    got=e.decompress()
    if i==2:
      if got!=newtex: raise SystemExit('tex roundtrip mismatch')
    elif got!=pre[i]: raise SystemExit(f'unexpected decompressed entry change {i} {e.name}')
ARC.write_bytes(newarc)
# LFD must be byte-identical
b2=ArcFile.parse(newarc)
if sha(b2.entries[3].decompress())!=lfd_sha: raise SystemExit('LFD changed')
report={'lfd_count':count,'lfd_sha256_unchanged':lfd_sha,'source_tex_sha256':sha(tex),'patched_tex_sha256':sha(newtex),'changed_pixels':len(changed),'outside_pixels':0,'map':rep}
(OUT/'safe_donor_font_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
# preview donors after patch
pv=Image.new('L',(6*16,18),0)
for j,(d,t) in enumerate(MAP.items()):
    m=recs[d]; g=rt.crop((m['x'],m['y'],m['x']+m['w'],m['y']+16)); pv.paste(g,(j*16+(16-m['w'])//2,0))
pv.resize((768,144),Image.Resampling.NEAREST).save(OUT/'safe_donor_TR_preview.png')
(OUT/'font_loc_00_AM_NOMIP_SAFE_TR.tex').write_bytes(newtex)
(OUT/'font_loc_ORIGINAL.lfd').write_bytes(lfd)
print(json.dumps(report,ensure_ascii=False,indent=2))
