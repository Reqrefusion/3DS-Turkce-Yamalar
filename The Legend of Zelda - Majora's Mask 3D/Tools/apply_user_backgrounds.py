"""Overlay Turkish lettering on the supplied cleaned native texture atlases.
No inpainting, surface reconstruction, or background erasure is performed.
Run after Tools/rebuild.py to rebuild R5 then apply this R6 overlay.
"""
from pathlib import Path
import ctypes,json,hashlib,sys,subprocess,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'Tools'))
import mm3d_tr_tool_v3 as t
import etc1_codec
so=R/'Tools/fast_etc.so'
if not so.exists():subprocess.run(['g++','-O3','-shared','-fPIC',str(R/'Tools/fast_etc.cpp'),'-o',str(so)],check=True)
lib=ctypes.CDLL(str(so));lib.encode_block.argtypes=[ctypes.POINTER(ctypes.c_uint8)];lib.encode_block.restype=ctypes.c_uint64
def fast(p):
 a=np.array(p,dtype=np.uint8);return int(lib.encode_block(a.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)))).to_bytes(8,'little')
etc1_codec.encode_block=fast
specpath=R/'QA/R5_verification.json'
if not specpath.exists():shutil.copy2(R/'QA/verification.json',specpath)
specs=json.loads(specpath.read_text())['labels']
rom=R/'0004000000125600/romfs'
before={p.relative_to(rom).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in rom.rglob('*') if p.is_file()}
report={'version':'R6','background_source':'user-supplied 01_ARKAPLANLI_DUZENLE(1).zip','background_cleaning_operations':0,'game_tested':False,'assets':[]}
font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
patches={}
(R/'QA/R6_native').mkdir(parents=True,exist_ok=True)
for p in sorted((R/'BuildInputs/UserClean').glob('*.ctxb.png')):
 name=p.name.removesuffix('.png');garname,entry=name.split('__');key=entry.removesuffix('.ctxb')
 base=Image.open(p).convert('RGBA');im=base.copy();old=Image.open(R/'BuildInputs/R5_Graphics'/p.name).convert('RGBA')
 assert old.size==im.size
 allowed=np.zeros((im.height,im.width),bool);overlay=Image.new('RGBA',im.size)
 counts={'opaque_text_overlays':0,'transparent_text_replacements':0}
 for sp in [s for s in specs if s['asset']==key]:
  box=sp['clear_cell'];x0,y0,x1,y1=box
  if sp['mode']=='transparent':
   # Transfer the already-localized transparent text sprite from R5.
   # This does not sample or repaint any button surface.
   im.paste(old.crop(box),box);allowed[y0:y1,x0:x1]=True
   counts['transparent_text_replacements']+=1
   continue
  bx=sp['draw_cell'];bw=bx[2]-bx[0];bh=bx[3]-bx[1];scale=4
  fs=round(sp['font_size']*scale);f=ImageFont.truetype(font,fs)
  bb=f.getbbox(sp['text'],stroke_width=scale)
  tile=Image.new('RGBA',(bw*scale,bh*scale));d=ImageDraw.Draw(tile)
  xx=(bw*scale-(bb[2]-bb[0]))/2-bb[0];yy=(bh*scale-(bb[3]-bb[1]))/2-bb[1]
  d.text((round(xx),round(yy)),sp['text'],font=f,fill=(250,250,250,255),stroke_fill=(25,25,25,255),stroke_width=scale)
  tile=tile.resize((bw,bh),Image.Resampling.LANCZOS)
  im.alpha_composite(tile,(bx[0],bx[1]));overlay.alpha_composite(tile,(bx[0],bx[1]))
  allowed[bx[1]:bx[3],bx[0]:bx[2]]|=np.array(tile)[:,:,3]>0
  counts['opaque_text_overlays']+=1
 changed=np.any(np.array(im)!=np.array(base),axis=2)
 assert not (changed & ~allowed).any(),p.name
 png=R/'Graphics'/p.name;im.save(png);overlay.save(R/'QA/R6_native'/(key+'.lettering.png'))
 # Encode from the matching original CTXB, keeping all untouched compressed blocks.
 source=R/'BuildInputs/sources/layout/EU_English'/(garname+'.gar');g=t.Gar2.load(source)
 e=next(e for e in g.entries if e.path==entry)
 src=R/'QA/R6_native'/(name+'.source');src.write_bytes(e.data)
 built=R/'QA/R6_native'/name;enc=t.ctxb_inject_png(src,png,built)
 decoded=t.decode_ctxb_texture(built);decoded.save(R/'QA'/(name+'.decoded.png'))
 patches.setdefault(garname+'.gar',{})[entry]=built.read_bytes()
 fmt=t.ctxb_info(src)['textures'][0]['format']
 if fmt in ('RGBA8','RGBA4'):
  quant=np.array(im) if fmt=='RGBA8' else (np.array(im)//17)*17
  # RGBA4 writer quantizes high nibbles, not division by 17.
  if fmt=='RGBA4':quant=(np.array(im)>>4)*17
  assert np.array_equal(np.array(decoded),quant)
 report['assets'].append({'file':p.name,**counts,'background_changes_outside_text_before_encoding':0,'source_png_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'format':fmt,'encode':{k:v for k,v in enc.items() if k!='output'}})
 print(p.name,counts,flush=True)
for name,repls in patches.items():
 p=rom/'layout/EU_English'/name;g=t.Gar2.load(p);raw=bytearray(g.raw)
 for e in g.entries:
  if e.path in repls:
   assert len(repls[e.path])==e.size;raw[e.data_offset:e.data_offset+e.size]=repls[e.path]
 p.write_bytes(raw);check=t.Gar2.load(p)
 assert len(check.raw)==len(g.raw)
 for a,b in zip(g.entries,check.entries):
  assert (a.path,a.size,a.data_offset)==(b.path,b.size,b.data_offset)
  if a.path not in repls:assert a.data==b.data
report['unchanged_install_files']=[]
for p in rom.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(rom).as_posix()
 if rel not in {'layout/EU_English/'+n for n in patches}:
  assert hashlib.sha256(p.read_bytes()).hexdigest()==before[rel]
  report['unchanged_install_files'].append(rel)
report['modified_archives']=list(patches)
(R/'QA/R6_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('DONE',len(report['assets']),'atlases; background cleaning: 0')
