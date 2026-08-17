from __future__ import annotations
from pathlib import Path
import sys,struct,hashlib,collections,shutil,zipfile,math,os
from PIL import Image,ImageDraw,ImageFont

BASE=Path('/mnt/data/v4work')
KIT=BASE/'kit1'/'bloodstained_tr_kit'
sys.path.insert(0,str(KIT))
from bloodstained_tr_tool import unpack_container,pack_container,parse_osb,decode_osb_rgba4444,encode_osb_rgba4444,OSB_KEY

ORIG=BASE/'orig'/'romfs'/'GraphicText00.osbctr'
V3ROOT=Path('/mnt/data/bloodstained_tr_v4_aligned')
V4=Path('/mnt/data/bloodstained_tr_v5_complete')
TITLE='00040000001D3C00'
ROMOUT=V4/'luma'/'titles'/TITLE/'romfs'
ROMOUT.mkdir(parents=True,exist_ok=True)

# Start with all v3 files, then replace GraphicText00 with a clean rebuild from the original.
v3rom=V3ROOT/'luma'/'titles'/TITLE/'romfs'
for p in v3rom.iterdir():
    if p.is_file(): shutil.copy2(p,ROMOUT/p.name)


def rec(raw,h,i): return list(struct.unpack_from('<6I',raw,h[7]+4+i*24))
def rec_base(h,i): return h[7]+4+i*24
def vertex_abs(h,i,r): return rec_base(h,i)+r[2]
def qoffs(raw,h,i):
    r=rec(raw,h,i); a=vertex_abs(h,i,r)
    return [a+j*80 for j in range(r[4]//4)]
def qvals(raw,o): return [struct.unpack_from('<5f',raw,o+k*20) for k in range(4)]
def qrect(raw,o):
    vs=qvals(raw,o); xs=[v[0] for v in vs];ys=[v[1] for v in vs];us=[v[3] for v in vs];vv=[v[4] for v in vs]
    return (min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv))
def tile_for_quad(atlas,r):
    aw,ah=atlas.size
    x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
    if x1<=x0 or y1<=y0: return None
    return atlas.crop((x0,y0,x1,y1)).resize((8,8),Image.Resampling.NEAREST)
def thash(im): return hashlib.sha1(im.convert('RGBA').tobytes()).hexdigest()

def pack_quad(template_vals,x0,x1,y0,y1,u0,u1,v0,v1):
    xs=[v[0] for v in template_vals];ys=[v[1] for v in template_vals];us=[v[3] for v in template_vals];vs=[v[4] for v in template_vals]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);umin,umax=min(us),max(us);vmin,vmax=min(vs),max(vs)
    out=bytearray()
    for x,y,z,u,v in template_vals:
        nx=x0 if abs(x-xmin)<=abs(x-xmax) else x1
        ny=y0 if abs(y-ymin)<=abs(y-ymax) else y1
        nu=u0 if abs(u-umin)<=abs(u-umax) else u1
        nv=v0 if abs(v-vmin)<=abs(v-vmax) else v1
        out += struct.pack('<5f',nx,ny,z,nu,nv)
    return bytes(out)

# Reliable original labels used only to recover the game's native 8x8 glyphs.
source={
14:'Ver.',15:'PRESS ANY BUTTON',16:'GAME START',17:'BOSS RUSH',18:'OPTIONS',19:'??????',21:'KEY CONFIG',
22:'VIBRATION',23:'HD Rumble',24:'LANGUAGE',25:'COSTUME CHANGE',26:'FILE SELECT',27:'PAUSE',28:'CURSE OF THE MOON',29:'GAME OVER',30:'ZANGETSU',31:'MIRIAM',32:'ALFRED',33:'ZEEBEL',34:'LIFE',35:'LIVES',36:'SCORE',37:'WEAPON',38:'COPY',39:'DELETE',40:'STAGE',41:'NORMAL',42:'NIGHTMARE',43:'ULTIMATE',44:'MODE',45:'CASUAL',46:'VETERAN',47:'STYLE',48:'TIME',49:'NO DATA',50:'END',51:'EXIT GAME',52:'CONTINUE',53:'STYLE CHANGE',54:'MOVE',55:'ATTACK',56:'SUB WEAPON',57:'JUMP',58:'DASH',59:'CHARACTER CHANGE RIGHT',60:'CHARACTER CHANGE LEFT',61:'COMMAND SUB WEAPON',62:'COMMAND DASH',66:'COLOR 1',67:'COLOR 2',68:'COLOR 3',69:'YES',70:'NO',71:'ON',72:'OFF',73:'JAPANESE',74:'ENGLISH',101:'BUTTON CONFIG'}

raw=bytearray(unpack_container(ORIG,OSB_KEY)); h=parse_osb(raw); atlas=decode_osb_rgba4444(raw); aw,ah=atlas.size

# Recover glyph samples and all hashes that represent native text glyphs.
samples=collections.defaultdict(list); text_hashes=set()
for i,text in source.items():
    os_=qoffs(raw,h,i); chars=[c for c in text if c!=' ']
    # Some nodes may contain invisible extras; only use unambiguous nodes for bank extraction.
    if len(os_)!=len(chars):
        continue
    ordered=sorted([(qrect(raw,o),o) for o in os_],key=lambda z:(-round(z[0][3],3),z[0][0]))
    for ch,(r,o) in zip(chars,ordered):
        tile=tile_for_quad(atlas,r)
        if tile is None: continue
        hh=thash(tile); text_hashes.add(hh); samples[ch.upper()].append((hh,r,tile))

# Canonical UV/tile per ASCII glyph = most frequent native sample.
glyph={}
for ch,arr in samples.items():
    cnt=collections.Counter(x[0] for x in arr); best=cnt.most_common(1)[0][0]
    hh,r,tile=next(x for x in arr if x[0]==best)
    glyph[ch]={'tile':tile.copy(),'uv':(r[4],r[5],r[6],r[7]),'hash':hh}

required_ascii=set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?')
# Digits are only needed for color labels; use source-native digit UVs already recovered.
required_native=set('ABCDEFGHIJKLMNOPRSTUVWXYZ')
if not required_native.issubset(glyph):
    raise RuntimeError('Native glyph bank incomplete: '+''.join(sorted(required_native-set(glyph))))

# Add digits from COLOR nodes directly.
for i,text in {66:'COLOR 1',67:'COLOR 2',68:'COLOR 3'}.items():
    os_=qoffs(raw,h,i);chars=[c for c in text if c!=' ']
    ordered=sorted([(qrect(raw,o),o) for o in os_],key=lambda z:z[0][0])
    if len(ordered)==len(chars):
        for ch,(r,o) in zip(chars,ordered):
            if ch.isdigit():
                tile=tile_for_quad(atlas,r); glyph[ch]={'tile':tile.copy(),'uv':(r[4],r[5],r[6],r[7]),'hash':thash(tile)};text_hashes.add(thash(tile))

# Referenced 8x8 cells; free transparent cells are safe homes for Turkish glyphs.
referenced=set()
for i in range(h[9]):
    for o in qoffs(raw,h,i):
        r=qrect(raw,o)
        x0=round(r[4]*aw);x1=round(r[5]*aw);y0=round(r[6]*ah);y1=round(r[7]*ah)
        if x1>x0 and y1>y0:
            for cy in range(max(0,y0//8),min(ah//8,(y1+7)//8)):
                for cx in range(max(0,x0//8),min(aw//8,(x1+7)//8)):
                    referenced.add((cx,cy))
free=[]
for cy in range(ah//8):
    for cx in range(aw//8):
        if (cx,cy) in referenced: continue
        tile=atlas.crop((cx*8,cy*8,cx*8+8,cy*8+8))
        if tile.getbbox() is None: free.append((cx,cy))

# Native pixels are white. Synthesize accents at pixel level so width/stroke match the original font.
def alpha_mask(tile):
    t=tile.convert('RGBA'); return [[t.getpixel((x,y))[3]>0 for x in range(8)] for y in range(8)]
def mask_tile(mask):
    im=Image.new('RGBA',(8,8),(0,0,0,0));px=im.load()
    for y,row in enumerate(mask):
        for x,on in enumerate(row):
            if on: px[x,y]=(255,255,255,255)
    return im

def shifted(base,dy=1):
    m=alpha_mask(glyph[base]['tile']);n=[[False]*8 for _ in range(8)]
    for y in range(8-dy):
        for x in range(8): n[y+dy][x]=m[y][x]
    return n

def make_accent(ch):
    if ch in ('Ş','Ç'):
        base='S' if ch=='Ş' else 'C'; m=alpha_mask(glyph[base]['tile'])
        # compact cedilla in the only free baseline row
        m[7][3]=True; m[7][4]=True
    elif ch=='Ğ':
        m=shifted('G',1); m[0][2]=True;m[0][5]=True;m[0][3]=True;m[0][4]=True
    elif ch=='İ':
        m=shifted('I',1); m[0][3]=True;m[0][4]=True
    elif ch=='Ö':
        m=shifted('O',1); m[0][2]=True;m[0][5]=True
    elif ch=='Ü':
        m=shifted('U',1); m[0][1]=True;m[0][6]=True
    elif ch=='Â':
        m=shifted('A',1); m[0][2]=True;m[0][4]=True;m[0][3]=True
    else: raise KeyError(ch)
    return mask_tile(m)

for ch in ['Ş','Ç','Ğ','İ','Ö','Ü','Â']:
    if not free: raise RuntimeError('No free atlas cell for Turkish glyphs')
    cell=free.pop(0); tile=make_accent(ch)
    x,y=cell[0]*8,cell[1]*8; atlas.paste(tile,(x,y))
    glyph[ch]={'tile':tile,'uv':((x+.02)/aw,(x+7.98)/aw,(y+.02)/ah,(y+7.98)/ah),'hash':thash(tile)}

# New, concise translations. Proper names/legal lines are deliberately untouched.
targets={
14:'SÜR.',15:'BİR TUŞA BAS',16:'BAŞLA',17:'PATRON',18:'AYARLAR',21:'TUŞ AYARI',
22:'TİTREŞİM',23:'HD TİTRE',24:'DİL',25:'KIYAFET DEĞİŞ',26:'DOSYA SEÇ',27:'DURAK',28:'AYIN LANETİ',29:'OYUN SONU',
34:'CAN',35:'HAK',36:'PUAN',37:'SİLAH',38:'KOPYA',39:'SİL',40:'BÖLÜM',41:'NORMAL',42:'KÂBUS',43:'NİHAİ',44:'MOD',45:'RAHAT',46:'USTA',47:'STİL',48:'SÜRE',49:'BOŞ',50:'SON',51:'ÇIKIŞ',52:'DEVAM',53:'STİL DEĞİŞ',
54:'YÖN',55:'SALDIR',56:'ALT SİLAH',57:'ATLA',58:'KOŞ',59:'SAĞ KARAKTER',60:'SOL KARAKTER',61:'ALT SİLAH KOMUTU',62:'KOŞ KOMUTU',
64:'SALDIR',65:'ATLA',66:'RENK 1',67:'RENK 2',68:'RENK 3',69:'EVET',70:'HAYIR',71:'AÇIK',72:'KAPALI',73:'JAPONCA',74:'TÜRKÇE',
101:'TUŞ AYARI'}
for i in range(75,87): targets[i]='YÜKLENİYOR'
targets[87]='HAZIR'
for i in range(88,100): targets[i]='KAYDEDİYOR'
targets[100]='KAYIT'

# Ensure every target char has a native/synthesized tile.
need=set(''.join(targets.values()).replace(' ',''))
missing=need-set(glyph)
if missing: raise RuntimeError('Missing target glyphs: '+repr(sorted(missing)))

# Classify text quads by native glyph hashes. For nodes with mixed icons, this leaves icons intact.
def classify_node(i):
    text=[];other=[]
    for o in qoffs(raw,h,i):
        r=qrect(raw,o); tile=tile_for_quad(atlas,r)
        # Note: atlas now contains new Turkish tiles, but original node refs still point to old cells.
        hh=thash(tile) if tile else ''
        # Native text quads are 8x8 and match any original glyph sample.
        if abs((r[1]-r[0])-8)<.2 and abs((r[3]-r[2])-8)<.2 and hh in text_hashes:
            text.append(o)
        else: other.append(o)
    return text,other

# Because Turkish glyph insertion changed only previously transparent cells, original classification hashes remain valid.
patch_report=[]
for i,text in targets.items():
    text_o,other_o=classify_node(i)
    if not text_o:
        raise RuntimeError(f'node {i}: no native text quads recognized')
    trs=[qrect(raw,o) for o in text_o]
    # Text row metrics and source center, measured from the original English glyphs.
    minx=min(r[0] for r in trs);maxx=max(r[1] for r in trs);miny=min(r[2] for r in trs);maxy=max(r[3] for r in trs)
    center=(minx+maxx)/2; origW=maxx-minx
    # Logical character advance. Keep native 8 px; only tighten when translation would exceed source width.
    n=len(text)
    if n<=1: adv=8.0
    else:
        want=n*8.0
        adv=8.0 if want<=origW+0.01 else max(5.5,(origW-8.0)/(n-1))
    logicalW=8.0 if n==1 else 8.0+(n-1)*adv
    start=center-logicalW/2
    # Use a native text quad as winding/Z template.
    template=qvals(raw,text_o[0])
    new_text=[];cursor=start
    for ch in text:
        if ch!=' ':
            u0,u1,v0,v1=glyph[ch]['uv']; new_text.append(pack_quad(template,cursor,cursor+8,miny,miny+8,u0,u1,v0,v1))
        cursor+=adv
    # Preserve any non-text/icon quads byte-for-byte in their existing geometry/UV.
    preserved=[bytes(raw[o:o+80]) for o in other_o]
    # Keep icon quads first; no overlap with text and draw order is immaterial for these labels.
    vb=b''.join(preserved+new_text)
    # 16-byte align appended vertex buffer.
    while len(raw)%16: raw.append(0)
    new_abs=len(raw); raw.extend(vb)
    base=rec_base(h,i); rel=new_abs-base
    r=rec(raw,h,i)
    struct.pack_into('<I',raw,base+8,rel)
    struct.pack_into('<I',raw,base+16,4*(len(preserved)+len(new_text)))
    struct.pack_into('<I',raw,base+20,6*(len(preserved)+len(new_text)))
    patch_report.append((i,text,len(text_o),len(new_text),len(other_o),origW,logicalW,adv))

# Header post-size grows because new detached vertex blocks were appended.
struct.pack_into('<I',raw,24,len(raw)-h[7])
# Put atlas back after all Turkish glyph cells were written.
h2=parse_osb(raw)
raw[h2[5]:h2[5]+h2[1]]=encode_osb_rgba4444(atlas)
out=ROMOUT/'GraphicText00.osbctr';out.write_bytes(pack_container(bytes(raw),OSB_KEY))

# Structural/roundtrip validation with corrected relative pointer semantics.
vr=unpack_container(out,OSB_KEY);vh=parse_osb(vr);vat=decode_osb_rgba4444(vr)
assert encode_osb_rgba4444(vat)==vr[vh[5]:vh[5]+vh[1]]
for i,text,*_ in patch_report:
    r=rec(vr,vh,i);a=vertex_abs(vh,i,r); assert 0<=a<a+r[4]*20<=len(vr)

# Report and checksums.
lines=['Bloodstained COTM 3DS - v5 GraphicText00 full audit rebuild','',
       'GraphicText00 was rebuilt from the ORIGINAL ROMFS, not from v3.','Native game 8x8 A-Z glyph tiles are reused. Turkish accented glyphs are pixel-derived from those native tiles.','Target labels are centered on the original English node bounds; 8px native advance is preserved unless a longer Turkish label must be tightened to fit.','']
lines.append('node | text | old glyphs -> new glyphs | icons | sourceW -> targetW | advance')
for i,t,oldn,newn,icons,ow,nw,adv in patch_report:
    lines.append(f'{i:3d} | {t} | {oldn}->{newn} | {icons} | {ow:.1f}->{nw:.1f} | {adv:.2f}')
(V4/'ALIGNMENT_REPORT_TR.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
sha=[]
for p in sorted(ROMOUT.iterdir()):
    if p.is_file(): sha.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(V4/'SHA256SUMS.txt').write_text('\n'.join(sha)+'\n',encoding='utf-8')
(V4/'README_TR.txt').write_text('''Bloodstained: Curse of the Moon 3DS Türkçe Yama v5 - Tam Tarama\n\nBu paket v4 dosyalarını temel alır; GraphicText00.osbctr orijinal RomFS'den yeniden oluşturulmuştur.\nAna menü, TUŞ AYARI ve küçük grafik UI etiketleri artık oyunun kendi 8x8 piksel harflerini kullanır.\n\nKurulum:\n1) Eski luma/titles/00040000001D3C00/romfs klasörünü silin.\n2) ZIP içindeki luma klasörünü SD kartın köküne kopyalayın.\n3) Luma3DS game patching açık olmalıdır.\n''',encoding='utf-8')
print('built',out,'size',out.stat().st_size)
print('patched nodes',len(patch_report))
for row in patch_report: print(row)
