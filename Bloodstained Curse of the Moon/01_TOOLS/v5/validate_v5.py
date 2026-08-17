from pathlib import Path
import sys,struct,hashlib,re,zipfile,shutil
from collections import Counter
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import unpack_container,parse_osb,decode_osb_rgba4444,encode_osb_rgba4444,OSB_KEY,TTB_KEY,FONT_KEY,load_ttb,TtbTable,validate_translation
sys.path.insert(0,'/mnt/data/v4work')
from analyze_osb import render_node

ROOT=Path('/mnt/data/bloodstained_tr_v5_complete')
ROM=ROOT/'luma/titles/00040000001D3C00/romfs'
ORIG=Path('/mnt/data/v4work/orig/romfs')
ROOT.mkdir(exist_ok=True)

osb_count=ttb_count=font_count=0
changed_records=0
control_warnings=[]
struct_errors=[]
changed_files=[]
for p in sorted(ROM.iterdir()):
    if not p.is_file(): continue
    op=ORIG/p.name
    if op.exists() and p.read_bytes()!=op.read_bytes(): changed_files.append(p.name)
    if p.suffix=='.ttb':
        t=load_ttb(p); t2=TtbTable(t.build({}))
        assert len(t.records)==len(t2.records)
        for i in range(len(t.records)): assert t.text_for_record(i)==t2.text_for_record(i)
        if op.exists():
            o=load_ttb(op)
            for i in range(min(len(o.records),len(t.records))):
                a=o.text_for_record(i);b=t.text_for_record(i)
                if a!=b:
                    changed_records+=1
                    ws=validate_translation(a,b)
                    if ws: control_warnings.append((p.name,i,ws))
        ttb_count+=1
    elif p.suffix=='.osbctr':
        raw=unpack_container(p,OSB_KEY);h=parse_osb(raw);im=decode_osb_rgba4444(raw)
        assert encode_osb_rgba4444(im)==raw[h[5]:h[5]+h[1]]
        # Correct node-relative vertex pointer bounds.
        for i in range(h[9]):
            base=h[7]+4+i*24
            r=struct.unpack_from('<6I',raw,base)
            a=base+r[2];end=a+r[4]*20
            if not (0<=a<=end<=len(raw)): struct_errors.append((p.name,i,a,end,len(raw)))
        osb_count+=1
    elif p.name=='BMPFont.bfbctr':
        raw=unpack_container(p,FONT_KEY); assert len(raw)>100
        font_count+=1

assert not control_warnings,control_warnings
assert not struct_errors,struct_errors

# Expected full-audit GraphicText00 states.
gt=ROM/'GraphicText00.osbctr'
# We validate visually by rendering focused nodes into preview below; structural checks above cover all 102 nodes.

# Build focused original/v5 comparison.
pairs=[
 ('Sürüm etiketi','GraphicText00.osbctr',14),
 ('Kilitli eylem (orijinal de ??????)','GraphicText00.osbctr',19),
 ('Tuş ayarı kısa etiketi','GraphicText00.osbctr',21),
 ('Koş','GraphicText00.osbctr',58),
 ('Koş komutu','GraphicText00.osbctr',62),
 ('Seçenekler başlığı','Option00.osbctr',37),
 ('Duraklatma başlığı','Pause00.osbctr',29),
]
font=ImageFont.load_default(); rows=[]
for label,fn,node in pairs:
    a=render_node(ORIG/fn,node,4);b=render_node(ROM/fn,node,4)
    W=max(520,a.width+b.width+40);H=max(90,max(a.height,b.height)+34)
    row=Image.new('RGBA',(W,H),(15,15,15,255));d=ImageDraw.Draw(row)
    d.text((4,3),label,fill='white',font=font);d.text((4,17),'ORİJİNAL',fill=(255,210,90),font=font);d.text((W//2,17),'V5',fill=(100,255,150),font=font)
    row.alpha_composite(a,(4,30));row.alpha_composite(b,(W//2,30));rows.append(row)
W=max(x.width for x in rows);H=sum(x.height for x in rows);sheet=Image.new('RGBA',(W,H),(0,0,0,255));y=0
for r in rows:sheet.alpha_composite(r,(0,y));y+=r.height
prev=ROOT/'V5_ORIGINAL_VS_TR.png';sheet.save(prev)

# Full audit report.
report=[]
report.append('Bloodstained: Curse of the Moon (Nintendo 3DS) — Türkçe Yama v5 Tam Tarama')
report.append('Avrupa / CTR-N-BLMP / TitleID 00040000001D3C00')
report.append('')
report.append('DOĞRULAMA')
report.append(f'- Paket dosyası: {len([p for p in ROM.iterdir() if p.is_file()])} RomFS override')
report.append(f'- OSBCTR yapısal + RGBA4444 round-trip: {osb_count}/{osb_count} geçti')
report.append(f'- TTB round-trip: {ttb_count}/{ttb_count} geçti')
report.append(f'- Değişmiş TTB kayıtları (orijinale göre): {changed_records}')
report.append(f'- Kontrol token uyuşmazlığı: {len(control_warnings)}')
report.append(f'- Vertex sınır hatası: {len(struct_errors)}')
report.append('')
report.append('V5 İLE EK DÜZELTİLEN KAÇAKLAR')
report.append('- GraphicText00 node 14: Ver. -> SÜR.')
report.append('- GraphicText00 node 21: KEY CONFIG -> TUŞ AYARI')
report.append('- Option00 node 37: OPTIONS -> AYARLAR (orijinal 7 glif merkezleri korunarak)')
report.append('- Pause00 node 29: PAUSE. -> DURAK. (orijinal 5 glif merkezleri ve nokta korunarak)')
report.append('- Result.ttb: Japonca dışındaki sonuç ekranı yerelleştirme slotları Türkçeye normalize edildi.')
report.append('')
report.append('?????? HAKKINDA')
report.append('- GraphicText00 node 19 orijinal oyunda da tam olarak "??????" grafik kaydıdır.')
report.append('- Ayrı DASH ve COMMAND DASH düğümleri orijinalde node 58 ve 62 olarak bulunur; v5 bunları KOŞ ve KOŞ KOMUTU yapar.')
report.append('- Bu nedenle kilitli durumda görülen ?????? çevrilmemiş İngilizce değildir ve bilerek korunmuştur.')
report.append('')
report.append('OSB GÖRSEL METİN TARAMASI')
report.append('- Orijinal RomFS içindeki 207 OSBCTR atlası temas sayfaları üzerinden tarandı.')
report.append('- Yerelleştirme metni taşıdığı tespit edilen dosyalar: GraphicText00, GraphicText01, GraphicText02_en, Openingext00_en, DemoText00_en, DemoText01_en, DemoText02_en, TutorialText00_en, EndingText00_en, Staffroll_Text00, Start00, Clear00, Thank00, Title00, Option00, Pause00.')
report.append('- TitleLogo / LogoInti_en / Under_InGame00 içindeki oyun ve şirket logoları özel ad/marka olduğu için değiştirilmedi.')
report.append('')
report.append('TTB TARAMASI')
report.append('- Announce, BootReady, BossRush, CommonText, GameOver, Option, PauseMenu, Result, Save, StaffRoll ve Title aktif metin tabloları orijinalle kayıt bazında karşılaştırıldı.')
report.append('- Option.ttb içinde değişmeden kalan Latin diziler yalnız <emoji/Btn...> kontrol tokenlarıdır.')
report.append('- StaffRoll.ttb içinde değişmeden kalan Latin diziler yalnız şirket/oyun özel adları ve telif şirket adlarıdır.')
report.append('- StageSelect.ttb 30 boş kayıttan oluşur.')
report.append('- Item.ttb ve MapCommon.ttb, GAL*GUNVOLT/LOLA/pixel sticker gibi başka Inti oyunlarına ait artık/ortak motor verileri içerir; Bloodstained yerelleştirme ekran metni olarak değiştirilmedi.')
report.append('')
report.append('DEĞİŞTİRİLEN ROMFS DOSYALARI')
for n in changed_files: report.append('- '+n)
(ROOT/'AUDIT_V5_TR.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')

sha=[]
for p in sorted(ROM.iterdir()):
 if p.is_file(): sha.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(ROOT/'SHA256SUMS.txt').write_text('\n'.join(sha)+'\n',encoding='utf-8')

readme='''Bloodstained: Curse of the Moon — Türkçe Yama v5 Tam Tarama\nAvrupa / TitleID 00040000001D3C00\n\nKurulum:\n1. Eski SD:/luma/titles/00040000001D3C00/romfs klasörünü silin.\n2. ZIP içindeki luma klasörünü SD kart köküne kopyalayın.\n3. Luma3DS game patching açık olmalıdır.\n\nv5: v4 sonrası tam OSB/TTB taramasında bulunan KEY CONFIG, OPTIONS ve PAUSE kaçakları düzeltildi. Result.ttb çok dilli slotları Türkçeye normalize edildi. Orijinalde de ?????? olan kilitli eylem göstergesi bilinçli olarak korunur.\n'''
(ROOT/'README_TR.txt').write_text(readme,encoding='utf-8')

zip_path=Path('/mnt/data/bloodstained_tr_v5_complete_layeredfs.zip')
if zip_path.exists():zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(ROOT))
print('files',len([p for p in ROM.iterdir() if p.is_file()]),'osb',osb_count,'ttb',ttb_count,'changed_records',changed_records,'changed_files',len(changed_files))
print('zip',zip_path,zip_path.stat().st_size)
