from pathlib import Path
from PIL import Image, ImageDraw
import shutil, re, hashlib, csv, subprocess, struct

V16=Path('/mnt/data/cs3d_v16/Cave_Story_3D_TR_v16_orijinal_fnt_custom_slot')
BASE=Path('/mnt/data/cs3d_v17')
OUT=BASE/'Cave_Story_3D_TR_v17_bos_atlas_font_fix'
ORIG_FONT=Path('/mnt/data/v10_orig/data')
ORIG_CODE=Path('/mnt/data/exefsinspect/exefs/code.bin')
if BASE.exists(): shutil.rmtree(BASE)
BASE.mkdir(parents=True)
shutil.copytree(V16,OUT)
DATA=OUT/'000400000004D200/romfs/data'
EXEFS=OUT/'000400000004D200/exefs'
R=OUT/'RAPORLAR'; P=OUT/'ONIZLEMELER'; T=OUT/'ARACLAR'

# ---------- parse original BMFont ----------
fnt_orig=(ORIG_FONT/'font_batang.fnt').read_text('latin1')
chars={}; kern=[]
for line in fnt_orig.splitlines():
    if line.startswith('char id='):
        vals={a:int(b) for a,b in re.findall(r'(id|x|y|width|height|xoffset|yoffset|xadvance)=(-?\d+)',line)}
        chars[vals['id']]=vals
    elif line.startswith('kerning '):
        kern.append({a:int(b) for a,b in re.findall(r'(first|second|amount)=(-?\d+)',line)})

def ksig(cid):
    return (
      tuple(sorted((d['first'],d['amount']) for d in kern if d['second']==cid)),
      tuple(sorted((d['second'],d['amount']) for d in kern if d['first']==cid)),
    )

# Turkish char -> (target raw id, base glyph id, new record)
# target IDs chosen so their ORIGINAL kerning signature equals the base glyph signature.
MAP={
 'Ğ':(210,71, dict(x=0,y=80,width=8,height=13,xoffset=0,yoffset=0,xadvance=8)),
 'İ':(205,73, dict(x=10,y=80,width=4,height=13,xoffset=0,yoffset=0,xadvance=4)),
 'Ş':(200,83, dict(x=16,y=80,width=7,height=12,xoffset=-1,yoffset=3,xadvance=6)),
 'ğ':(232,103,dict(x=25,y=80,width=7,height=13,xoffset=0,yoffset=2,xadvance=6)),
 'ı':(161,105,dict(x=34,y=80,width=4,height=10,xoffset=0,yoffset=3,xadvance=4)),
 'ş':(233,115,dict(x=40,y=80,width=6,height=10,xoffset=0,yoffset=5,xadvance=6)),
}

# ---------- build atlas from ORIGINAL, only write into blank y>=80 ----------
orig_img=Image.open(ORIG_FONT/'font_batang_0.tga').convert('RGBA')
img=orig_img.copy()

def crop(cid):
    c=chars[cid]
    return orig_img.crop((c['x'],c['y'],c['x']+c['width'],c['y']+c['height']))

def blank(w,h): return Image.new('RGBA',(w,h),(255,255,255,0))

def put_alpha(dst, alpha, x,y):
    # white RGB, source alpha
    for yy in range(alpha.height):
        for xx in range(alpha.width):
            a=alpha.getpixel((xx,yy))
            if a:
                dst.putpixel((x+xx,y+yy),(255,255,255,a))

# source glyphs
G=crop(71); g=crop(103); I=crop(73); i_g=crop(105); S=crop(83); s=crop(115)
Cced=crop(199).getchannel('A')
cced=crop(231).getchannel('A')
caret=crop(94).getchannel('A')
# 3-row breve: vertically-flipped lower three visible rows of original '^'.
breve8=Image.new('L',(8,3),0)
for dy,srcy in enumerate([5,4,3]):
    for x in range(8): breve8.putpixel((x,dy),caret.getpixel((x,srcy)))
breve7=breve8.crop((1,0,8,3))

custom={}
# Ğ
c=blank(8,13); c.alpha_composite(G,(0,3)); put_alpha(c,breve8,0,0); custom['Ğ']=c
# İ: I body at original screen y=3 + original i dot
c=blank(4,13); c.alpha_composite(I,(0,3)); idot=i_g.getchannel('A').crop((0,1,4,2)); put_alpha(c,idot,0,1); custom['İ']=c
# Ş: exact S body + cedilla alpha copied from original Ç rows 9-10
c=blank(7,12); c.alpha_composite(S,(0,0))
ced=Image.new('L',(7,3),0)
# Ç local x3-4 -> Ş local x3-4, rows9-11
for yy in range(3):
    for xx in range(7):
        sx=xx
        if sx<8: ced.putpixel((xx,yy),Cced.getpixel((sx,9+yy)))
put_alpha(c,ced,0,9); custom['Ş']=c
# ğ: g screen starts y=5; target yoffset2 => local body y=3
c=blank(7,13); c.alpha_composite(g,(0,3)); put_alpha(c,breve7,0,0); custom['ğ']=c
# ı: exact i glyph minus dot; metrics stay i-identical
c=i_g.copy();
for yy in [0,1,2]:
    for xx in range(c.width): c.putpixel((xx,yy),(255,255,255,0))
custom['ı']=c
# ş: exact s body, original ç cedilla style centered under s
c=blank(6,10); c.alpha_composite(s,(0,0))
# copy cedilla rows 7..9, move x3-4 -> x2-3 to center beneath s
for yy in range(3):
    for sx,dx in [(3,2),(4,3)]:
        a=cced.getpixel((sx,7+yy))
        if a: c.putpixel((dx,7+yy),(255,255,255,a))
custom['ş']=c

# verify original area blank at destinations, then paste
for ch,(tid,bid,rec) in MAP.items():
    box=(rec['x'],rec['y'],rec['x']+rec['width'],rec['y']+rec['height'])
    # source is supposed to be totally transparent
    assert orig_img.crop(box).getchannel('A').getbbox() is None,(ch,box)
    img.alpha_composite(custom[ch],(rec['x'],rec['y']))
img.save(DATA/'font_batang_0.tga',format='TGA')

# ---------- patch only six char lines, preserve count/order/kerning ----------
def fmt_char(cid,rec):
    return 'char id={:<3}  x={:<5} y={:<5} width={:<5} height={:<5} xoffset={:<5} yoffset={:<5} xadvance={:<5} page=0  chnl=15\n'.format(
      cid,rec['x'],rec['y'],rec['width'],rec['height'],rec['xoffset'],rec['yoffset'],rec['xadvance'])

lines=fnt_orig.splitlines(True)
changed_lines=[]
for idx,line in enumerate(lines):
    if line.startswith('char id='):
        cid=int(re.search(r'char id=(\d+)',line).group(1))
        for ch,(tid,bid,rec) in MAP.items():
            if cid==tid:
                new=fmt_char(cid,rec)
                assert len(new)==len(line),(cid,len(line),len(new),repr(line),repr(new))
                lines[idx]=new
                changed_lines.append((ch,cid,line.rstrip('\n'),new.rstrip('\n')))
                break
fnt_new=''.join(lines)
(DATA/'font_batang.fnt').write_text(fnt_new,'latin1',newline='')
assert len(fnt_new.encode('latin1'))==len(fnt_orig.encode('latin1'))
# all kerning lines must be byte-identical
orig_k=[x for x in fnt_orig.splitlines() if x.startswith('kerning ')]
new_k=[x for x in fnt_new.splitlines() if x.startswith('kerning ')]
assert orig_k==new_k

# ---------- remap V16 text bytes to V17 target IDs ----------
old_to_new={0xD1:0xD2, 0xA7:0xE8, 0xBF:0xE9}
text_files=list(DATA.rglob('*.sjs'))+list(DATA.glob('credits_text*.txt'))
remap_counts={k:0 for k in old_to_new}
for p in text_files:
    b=bytearray(p.read_bytes())
    for j,v in enumerate(b):
        if v in old_to_new:
            remap_counts[v]+=1; b[j]=old_to_new[v]
    p.write_bytes(b)
# ensure old private IDs gone from text
for old in old_to_new:
    assert sum(p.read_bytes().count(bytes([old])) for p in text_files)==0

# ---------- rebuild ExeFS code from original using V14 translation table and V17 encoding ----------
private={'Ğ':0xD2,'İ':0xCD,'Ş':0xC8,'ğ':0xE8,'ı':0xA1,'ş':0xE9}
def enc(s):
    out=bytearray()
    for ch in s:
        if ch in private: out.append(private[ch])
        else: out.extend(ch.encode('cp1254'))
    return bytes(out)

report14=V16/'RAPORLAR/EXEFS_TURKCE_KARAKTER_VE_KAYIT_UYARISI_V14.tsv'
rows=list(csv.DictReader(report14.open(encoding='utf-8'),delimiter='\t'))
code=bytearray(ORIG_CODE.read_bytes())
patched=[]
for row in rows:
    off=int(row['offset'],16); eng=row['ingilizce']; tr=row['v14_turkce']; slot=int(row['slot_byte'])
    eb=eng.encode('ascii')
    # Some original strings may have punctuation exactly as report; verify the visible prefix.
    if code[off:off+len(eb)]!=eb:
        raise RuntimeError(f'original verify fail {row["offset"]}: {code[off:off+len(eb)]!r} != {eb!r}')
    tb=enc(tr)
    if len(tb)+1>slot: raise RuntimeError(f'slot overflow {row["offset"]} {tr} {len(tb)+1}>{slot}')
    # SAFEST: only overwrite translated bytes + NUL. Never clear the remainder of the slot.
    code[off:off+len(tb)]=tb
    code[off+len(tb)]=0
    patched.append((off,eng,tr,len(tb),slot))
(EXEFS/'code.bin').write_bytes(code)

# IPS generator from original -> code
orig=ORIG_CODE.read_bytes(); new=bytes(code)
def make_ips(a,b,out):
    assert len(a)==len(b)
    recs=[]; i=0
    while i<len(a):
        if a[i]==b[i]: i+=1; continue
        start=i
        while i<len(a) and a[i]!=b[i] and i-start<65535: i+=1
        recs.append((start,b[start:i]))
    o=bytearray(b'PATCH')
    for off,dat in recs:
        o+=off.to_bytes(3,'big')+len(dat).to_bytes(2,'big')+dat
    o+=b'EOF'; out.write_bytes(o)
make_ips(orig,new,OUT/'000400000004D200/code.ips')

# ---------- QA ----------
# parse new fnt
newchars={}
for line in fnt_new.splitlines():
    if line.startswith('char id='):
        vals={a:int(b) for a,b in re.findall(r'(id|x|y|width|height|xoffset|yoffset|xadvance)=(-?\d+)',line)};newchars[vals['id']]=vals
# non-target char records byte-identical
orig_lines={int(re.search(r'char id=(\d+)',l).group(1)):l for l in fnt_orig.splitlines() if l.startswith('char id=')}
new_lines={int(re.search(r'char id=(\d+)',l).group(1)):l for l in fnt_new.splitlines() if l.startswith('char id=')}
target_ids={v[0] for v in MAP.values()}
non_target_diffs=[cid for cid in orig_lines if cid not in target_ids and orig_lines[cid]!=new_lines[cid]]
assert not non_target_diffs
# all base kerning signatures equal target signatures because kerning table untouched and IDs selected accordingly
kerning_match={ch:(ksig(tid)==ksig(bid)) for ch,(tid,bid,rec) in MAP.items()}
assert all(kerning_match.values()),kerning_match
# compare pixels: rows <75 EXACT same
for y in range(75):
    for x in range(256):
        assert orig_img.getpixel((x,y))==img.getpixel((x,y))
# Outside six destination rectangles, ALL pixels exact same
allowed=set()
for ch,(tid,bid,r) in MAP.items():
    for y in range(r['y'],r['y']+r['height']):
        for x in range(r['x'],r['x']+r['width']): allowed.add((x,y))
outside=0
for y in range(128):
    for x in range(256):
        if (x,y) not in allowed and orig_img.getpixel((x,y))!=img.getpixel((x,y)): outside+=1
assert outside==0
# ExeFS critical pointer from V11
ptr=struct.unpack_from('<I',code,0x675BC)[0]
assert ptr==0x001E3228,hex(ptr)
# verify all patched strings decode custom back to expected Turkish
inv={v:k for k,v in private.items()}
def dec_custom(b):
    s='';
    for v in b:
        if v in inv: s+=inv[v]
        else: s+=bytes([v]).decode('cp1254')
    return s
for off,eng,tr,n,slot in patched:
    raw=bytes(code[off:off+n]); assert dec_custom(raw)==tr,(hex(off),dec_custom(raw),tr)

# ---------- own BMFont renderer ----------
def get_kerning(a,b):
    for d in kern:
        if d['first']==a and d['second']==b: return d['amount']
    return 0

def encode_ids(text): return list(enc(text))

def render(text,scale=5,show_guides=False):
    ids=encode_ids(text)
    width=10; prev=None
    for cid in ids:
        if prev is not None: width+=get_kerning(prev,cid)
        width+=newchars[cid]['xadvance']; prev=cid
    h=25
    can=Image.new('RGBA',(max(width+10,20),h),(25,25,30,255))
    d=ImageDraw.Draw(can)
    if show_guides:
        d.line((0,3,can.width,3),fill=(80,80,100,255)); d.line((0,13,can.width,13),fill=(60,90,60,255)); d.line((0,15,can.width,15),fill=(90,60,60,255))
    x=5; prev=None
    for cid in ids:
        if prev is not None: x+=get_kerning(prev,cid)
        c=newchars[cid]
        glyph=img.crop((c['x'],c['y'],c['x']+c['width'],c['y']+c['height']))
        can.alpha_composite(glyph,(x+c['xoffset'],c['yoffset']))
        x+=c['xadvance']; prev=cid
    return can.resize((can.width*scale,can.height*scale),Image.Resampling.NEAREST)

samples=['I İ i ı','S Ş s ş','G Ğ g ğ','İşaret ışığı','değişiklik görüş','Öykü Modu','Başlangıç Noktası']
renders=[render(s,5,True) for s in samples]
w=max(i.width for i in renders); h=sum(i.height for i in renders)+10*(len(renders)-1)
sheet=Image.new('RGB',(w,h),'#111116'); y=0
for rr in renders:
    sheet.paste(rr.convert('RGB'),(0,y)); y+=rr.height+10
sheet.save(P/'FONT_V17_GERCEK_METRIK_RENDER.png')
# glyph detail side by side
pairs=[('G','Ğ'),('g','ğ'),('I','İ'),('i','ı'),('S','Ş'),('s','ş')]
parts=[]
for a,b in pairs:
    rr=render(a+' '+b,12,True); parts.append(rr)
w=max(x.width for x in parts); h=sum(x.height for x in parts)
sh=Image.new('RGB',(w,h),'#111116'); y=0
for rr in parts: sh.paste(rr.convert('RGB'),(0,y)); y+=rr.height
sh.save(P/'FONT_V17_GOVDE_AKSAN_KARSILASTIRMA.png')

# Reports
with (R/'FONT_V17_BYTE_GUVENLIK_QA.txt').open('w',encoding='utf-8') as f:
    f.write('V17 FONT BYTE/ATLAS GUVENLIK QA\n==============================\n')
    f.write(f'Original FNT SHA256: {hashlib.sha256((ORIG_FONT/"font_batang.fnt").read_bytes()).hexdigest()}\n')
    f.write(f'V17 FNT SHA256:      {hashlib.sha256((DATA/"font_batang.fnt").read_bytes()).hexdigest()}\n')
    f.write(f'FNT byte boyu ayni: {len(fnt_orig.encode("latin1"))==len(fnt_new.encode("latin1"))}\n')
    f.write(f'Degisen char satiri: {len(changed_lines)} (beklenen 6)\n')
    f.write(f'Diger 184 char kaydi farki: {len(non_target_diffs)}\n')
    f.write(f'Kerning tablosu byte/metin olarak tamamen ayni: {orig_k==new_k}\n')
    f.write(f'Orijinal glif bolgesi y<75 piksel farki: 0\n')
    f.write(f'Yeni 6 glif kutusu disinda atlas piksel farki: {outside}\n')
    f.write('\nHaritalama / metrik / kerning:\n')
    for ch,(tid,bid,rec) in MAP.items():
        f.write(f'{ch}: byte 0x{tid:02X}, baz={chr(bid)}, adv={rec["xadvance"]}, xoff={rec["xoffset"]}, yoff={rec["yoffset"]}, kerning_imzasi_bazla_ayni={kerning_match[ch]}\n')
    f.write('\nV16->V17 byte remap adetleri:\n')
    for old,n in remap_counts.items(): f.write(f'0x{old:02X}->0x{old_to_new[old]:02X}: {n}\n')

with (R/'FONT_V17_DEGISEN_6_FNT_SATIRI.tsv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,delimiter='\t');w.writerow(['harf','char_id','orijinal_satir','v17_satir'])
    for row in changed_lines:w.writerow(row)

with (R/'EXEFS_V17_GUVENLIK_QA.txt').open('w',encoding='utf-8') as f:
    f.write('V17 EXEFS QA\n============\n')
    f.write(f'Orijinal code SHA256: {hashlib.sha256(orig).hexdigest()}\n')
    f.write(f'V17 code SHA256:      {hashlib.sha256(new).hexdigest()}\n')
    f.write(f'Yamalanan dogrulanmis string: {len(patched)}\n')
    f.write('String slotlarinda kuyruk sifirlama YOK: sadece yeni metin + NUL yazilir.\n')
    f.write(f'Kritik pointer [0x675BC]: 0x{ptr:08X} (beklenen 0x001E3228)\n')

with (R/'QA_V17_OZET.txt').open('w',encoding='utf-8') as f:
    f.write('CAVE STORY 3D TR V17 - BOS ATLAS FONT FIX\n==========================================\n')
    f.write('- V16 font slot-overwrite yontemi kaldirildi.\n')
    f.write('- Font atlasi orijinalden yeniden kuruldu; mevcut tum glifler birebir korundu.\n')
    f.write('- 6 Turkce glif yalniz atlasin tamamen bos y=80 bolgesine eklendi.\n')
    f.write('- .fnt: sadece 6 char kaydi degisti; diger 184 char ve tum kerning satirlari ayni.\n')
    f.write('- Her hedef ID baz harfle ayni orijinal kerning imzasina sahip.\n')
    f.write('- ExeFS orijinal code.bin uzerinden guvenli yeniden uretildi; slot kuyruklari silinmedi.\n')
    f.write('- V16 EVET/HAYIR atlas yerlesimi korundu.\n')

# reproducibility builder copy
builder=(T/'build_v17_blank_atlas_font.py')
builder.write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')

# README
(OUT/'V17_SURUM_NOTLARI.txt').write_text('''Cave Story 3D TR V17 - Bos Atlas Font Fix\n\nBu test surumunde font yeniden tasarlandi:\n- Normal gliflerin hicbir pikseli degistirilmez.\n- 6 Turkce harf atlasin tamamen bos alt bolgesine eklenir.\n- FNT dosyasinda yalniz 6 char kaydi yeni bos atlas koordinatlarina yonlendirilir.\n- Kerning tablosu tamamen orijinaldir.\n- ExeFS string yamasi orijinal code.bin uzerinden yeniden kurulur; slot sonlari sifirlanmaz.\n''',encoding='utf-8')

# include pure-original font A/B diagnostic
ab=OUT/'A_B_TEST_ORIJINAL_FONT';ab.mkdir(exist_ok=True)
shutil.copy2(ORIG_FONT/'font_batang.fnt',ab/'font_batang.fnt')
shutil.copy2(ORIG_FONT/'font_batang_0.tga',ab/'font_batang_0.tga')
(ab/'README.txt').write_text('Bu iki dosya tamamen orijinal oyun fontudur. Yalniz tanisal A/B test icindir; Turkce ozel karakterler dogru gorunmez. Global font kaymasini ayirmak icin kullanilabilir.\n',encoding='utf-8')

# zip + sha
zip_path=Path('/mnt/data/Cave_Story_3D_TR_v17_bos_atlas_font_fix.zip')
if zip_path.exists(): zip_path.unlink()
subprocess.run(['bash','-lc',f'cd {BASE} && zip -qr {zip_path} {OUT.name}'],check=True)
sha=hashlib.sha256(zip_path.read_bytes()).hexdigest()
Path('/mnt/data/Cave_Story_3D_TR_v17_bos_atlas_font_fix.sha256').write_text(f'{sha}  {zip_path.name}\n',encoding='utf-8')
print('OUT',OUT)
print('ZIP',zip_path)
print('SHA',sha)
print('remap',remap_counts)
print('fnt lines',len(changed_lines),'outsidepix',outside,'ptr',hex(ptr))
