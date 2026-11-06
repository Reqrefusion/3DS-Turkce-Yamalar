#!/usr/bin/env python3
from pathlib import Path
import sys,struct,subprocess,tempfile,shutil,hashlib,json,os
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/mnt/data/work_ui27')
TOOL=ROOT/'v9/ace_attorney_3ds_tr_v9_fontinfo_fix/tool'
sys.path.insert(0,str(TOOL))
from aat3ds_tr_v3 import parse_pack_inc,lz11_decompress
from bch_utils import parse_bch_textures,decode_texture,replace_texture

BASE=ROOT/'v26/ace_attorney_3ds_tr_v26_dotless_i_inline_origin_fix_fulltoolchain/romfs'
OUT=ROOT/'v27_assets'
OUT.mkdir(exist_ok=True)

# Source GS1 translated surface assets -> GS2/GS3 omitted equivalents.
COPY={
 8515:2683,11529:2683, # İngilizce
 8516:2684,11530:2684, # Japonca
 8531:2699,11545:2699, # Yeni Oyun
 8532:2700,11546:2700, # Devam
 8546:2714,11561:2714, # KAYDET
 8547:2715,11563:2715, # YÜKLE
}
SAI10=[2691,8523,11537]
MENU_CHECK=[6873,9709]
EVENT=[2707,8539,11554]
QUIT=[11562]

pack=(BASE/'pack.dat').read_bytes(); inc=(BASE/'pack.inc').read_bytes(); rec=parse_pack_inc(inc)

def raw_entry(idx):
 r=rec[idx]; raw,_=lz11_decompress(pack,r['offset']); return raw

def font_path():
 candidates=[Path('/usr/share/fonts/truetype/croscore/Arimo-Bold.ttf'),Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'),Path('C:/Windows/Fonts/arialbd.ttf')]
 for p in candidates:
  if p.exists(): return p
 raise FileNotFoundError('Bold TrueType font not found; pass/use Arial/Arimo/Liberation Sans Bold')
FONT=font_path()

def patch_sai10(raw):
 groups=parse_bch_textures(raw); g=next(x for x in groups if x['name']=='sai_10u'); t=g['textures'][0]
 im=decode_texture(raw,t).convert('RGBA'); d=ImageDraw.Draw(im)
 f=ImageFont.truetype(str(FONT),20)
 # original button bounds, two color states separated by 512 px vertically
 for off,bg,stroke in [(0,(121,47,0,255),(65,22,0,255)),(512,(250,176,11,255),(120,57,0,255))]:
  items=[(2,245+off,138,275+off,'Git'),(142,245+off,278,275+off,'İncele'),
         (2,285+off,138,315+off,'Sun'),(142,285+off,278,315+off,'Konuş')]
  for x0,y0,x1,y1,text in items:
   d.rectangle((x0+4,y0+4,x1-4,y1-4),fill=bg)
   bb=d.textbbox((0,0),text,font=f,stroke_width=2); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
   x=(x0+x1-tw)//2; y=(y0+y1-th)//2-bb[1]
   d.text((x,y),text,font=f,fill=(255,255,255,255),stroke_width=2,stroke_fill=stroke)
 return replace_texture(raw,t,im),im

def patch_check(raw):
 groups=parse_bch_textures(raw); g=next(x for x in groups if x['name'].lower()=='btn34'); t=g['textures'][0]
 old=decode_texture(raw,t).convert('RGBA')
 im=Image.new('RGBA',old.size,(255,255,255,0)); d=ImageDraw.Draw(im)
 # Match the original standalone CHECK label footprint but use Turkish INCELE.
 f=ImageFont.truetype(str(FONT),17)
 # two states: top orange accent, lower dark brown accent
 for y,stroke in [(1,(255,115,47,255)),(33,(117,49,0,255))]:
  text='İNCELE'; bb=d.textbbox((0,0),text,font=f,stroke_width=2)
  tw=bb[2]-bb[0]; x=2; # keep left aligned like original CHECK
  d.text((x,y-bb[1]),text,font=f,fill=(255,255,255,255),stroke_width=2,stroke_fill=stroke)
 return replace_texture(raw,t,im),im


def patch_event(raw):
 groups=parse_bch_textures(raw); g=next(x for x in groups if x['name']=='sai_1du'); t=g['textures'][0]
 im=decode_texture(raw,t).convert('RGBA'); d=ImageDraw.Draw(im)
 # Keep native box/border; erase only English label.
 d.rectangle((18,3,110,28),fill=(242,242,242,255))
 f=ImageFont.truetype(str(Path('/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf') if Path('/usr/share/fonts/truetype/croscore/Arimo-Regular.ttf').exists() else FONT),20)
 text='Olay';bb=d.textbbox((0,0),text,font=f);tw=bb[2]-bb[0];th=bb[3]-bb[1]
 x=(128-tw)//2;y=(32-th)//2-bb[1]
 d.text((x,y),text,font=f,fill=(98,47,30,255))
 return replace_texture(raw,t,im),im

def patch_quit(raw):
 groups=parse_bch_textures(raw); g=next(x for x in groups if x['name']=='sai_22_'); t=g['textures'][0]
 im=decode_texture(raw,t).convert('RGBA'); d=ImageDraw.Draw(im)
 # Button interior from original asset: x~38..282, y~8..112. Preserve frame.
 bg=(98,24,24,255)
 d.rectangle((55,14,266,64),fill=bg); d.rectangle((55,70,266,108),fill=bg)
 fi=ImageFont.truetype('/usr/share/fonts/truetype/croscore/Arimo-BoldItalic.ttf' if Path('/usr/share/fonts/truetype/croscore/Arimo-BoldItalic.ttf').exists() else str(FONT),40)
 fs=ImageFont.truetype(str(FONT),23)
 def centered(text,font,cy):
  bb=d.textbbox((0,0),text,font=font,stroke_width=2);tw=bb[2]-bb[0];th=bb[3]-bb[1]
  x=160-tw//2;y=cy-th//2-bb[1]
  # dark outer shadow then green rim, matching SAVE/LOAD family
  d.text((x,y),text,font=font,fill=(255,255,255,255),stroke_width=4,stroke_fill=(75,35,15,255))
  d.text((x,y),text,font=font,fill=(255,255,255,255),stroke_width=2,stroke_fill=(79,168,35,255))
 centered('ÇIKIŞ',fi,40); centered('Oyundan çık?',fs,91)
 return replace_texture(raw,t,im),im

raw_repl={}
# exact GS1 translated BCH copies are structurally identical; target metadata is preserved by same-size raw replacement.
for dst,src in COPY.items(): raw_repl[dst]=raw_entry(src)
# common English investigation action sheet is byte-identical across all games; patch once
patched10,prev10=patch_sai10(raw_entry(SAI10[0]))
for idx in SAI10: raw_repl[idx]=patched10
prev10.save(OUT/'sai_10u_TR_preview.png')
for idx in MENU_CHECK:
 rr,prev=patch_check(raw_entry(idx));raw_repl[idx]=rr;prev.save(OUT/f'{idx}_btn34_TR_preview.png')
# Remaining active English labels in save/quit surface
pev,prev=patch_event(raw_entry(EVENT[0]))
for idx in EVENT: raw_repl[idx]=pev
prev.save(OUT/'event_TR_preview.png')
for idx in QUIT:
 rr,prev=patch_quit(raw_entry(idx));raw_repl[idx]=rr;prev.save(OUT/f'{idx}_quit_TR_preview.png')

# Save raw replacements for audit/tooling.
rawdir=OUT/'raw';rawdir.mkdir(exist_ok=True)
for idx,raw in raw_repl.items(): (rawdir/f'{idx:05d}.bin').write_bytes(raw)

# Fast compressor compile once.
cpp=ROOT/'v26/ace_attorney_3ds_tr_v26_dotless_i_inline_origin_fix_fulltoolchain/tools/lz11_fast.cpp'
exe=OUT/'lz11_fast'
subprocess.run(['g++','-O3','-std=c++17',str(cpp),'-o',str(exe)],check=True)

# Preserve original compressed blobs for GS1-copy targets to avoid any recompression differences.
blob_repl={}
for dst,src in COPY.items():
 r=rec[src]; blob_repl[dst]=(pack[r['offset']:r['offset']+r['compressed']],r['decompressed'])
# Compress unique edited raws, dedupe sai10 blob.
def comp(raw,name):
 ip=OUT/(name+'.raw'); op=OUT/(name+'.lz11'); ip.write_bytes(raw)
 subprocess.run([str(exe),str(ip),str(op)],check=True,stdout=subprocess.DEVNULL)
 blob=op.read_bytes(); dec,_=lz11_decompress(blob,0)
 if dec!=raw: raise RuntimeError('LZ11 roundtrip mismatch '+name)
 ip.unlink();op.unlink();return blob
b10=comp(patched10,'sai10u_tr')
for idx in SAI10: blob_repl[idx]=(b10,len(patched10))
for idx in MENU_CHECK:
 blob_repl[idx]=(comp(raw_repl[idx],f'menu_{idx}'),len(raw_repl[idx]))
bev=comp(pev,'event_tr')
for idx in EVENT: blob_repl[idx]=(bev,len(pev))
for idx in QUIT: blob_repl[idx]=(comp(raw_repl[idx],f'quit_{idx}'),len(raw_repl[idx]))

# Rebuild entire pack while byte-copying every untouched compressed payload.
out=bytearray();newinc=bytearray();changes=[]
for r in rec:
 i=r['index']; noff=len(out)
 if i in blob_repl:
  blob,dec=blob_repl[i]; compn=len(blob)
  changes.append({'entry':i,'old_comp':r['compressed'],'new_comp':compn,'dec':dec})
 else:
  blob=pack[r['offset']:r['offset']+r['compressed']];dec=r['decompressed'];compn=r['compressed']
 out.extend(blob)
 while len(out)%4: out.append(0)
 newinc.extend(struct.pack('<QIII',noff,dec,compn,r['ident']))
(OUT/'pack.dat').write_bytes(out);(OUT/'pack.inc').write_bytes(newinc)

# Verify replacements and untouched compressed payloads semantically/bytewise.
nrec=parse_pack_inc(bytes(newinc));npack=bytes(out)
for idx,expected in raw_repl.items():
 got,_=lz11_decompress(npack,nrec[idx]['offset']);
 if got!=expected: raise RuntimeError(f'replacement verify failed {idx}')
untouched=0
for r,nr in zip(rec,nrec):
 if r['index'] in blob_repl: continue
 a=pack[r['offset']:r['offset']+r['compressed']]; b=npack[nr['offset']:nr['offset']+nr['compressed']]
 if a!=b: raise RuntimeError('untouched payload changed '+str(r['index']))
 untouched+=1
report={'base_pack_sha256':hashlib.sha256(pack).hexdigest(),'new_pack_sha256':hashlib.sha256(npack).hexdigest(),
        'changed_entries':changes,'changed_count':len(changes),'untouched_payloads_byte_identical':untouched,
        'copy_map':{str(k):v for k,v in COPY.items()},'sai10_entries':SAI10,'menu_check_entries':MENU_CHECK,'event_entries':EVENT,'quit_entries':QUIT,
        'translations':{'New Game':'Yeni Oyun','Continue':'Devam','SAVE':'KAYDET','LOAD':'YÜKLE','English':'İngilizce','Japanese':'Japonca','Move':'Git','Examine':'İncele','Present':'Sun','Talk':'Konuş','CHECK':'İNCELE','Event':'Olay','QUIT / Quit the game?':'ÇIKIŞ / Oyundan çık?'}}
(OUT/'surface_ui_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
