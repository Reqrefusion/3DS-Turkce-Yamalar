#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeus Quest Remastered 3DS (Unity 5.2.4f1) language extractor / patcher.
   Python 3.9+, no third-party packages required.
   Only patch games you have the right to modify.
"""
import argparse, csv, hashlib, io, json, re, struct, sys, zipfile
from collections import Counter
from pathlib import Path

METADATA='romfs/Data/Managed/Metadata/global-metadata.dat'
FONT_ASSET='romfs/Data/sharedassets0.assets'
# Verified ranges of unique IL2CPP string literals in this specific ROM.
LANGS={'EN':(7628,10720),'FR':(10720,13780),'DE':(13780,16861),
       'EL':(16861,19946),'IT':(19946,22924),'ES':(22924,26004)}
FIELDNAMES=['id','meta_index','kaynak_dil','kaynak_metin','turkce','durum','notlar']
UIFIELDS=['id','dosya','path_id','oyun_nesnesi','kaynak_metin','turkce','durum','notlar']
CHARSET='ÇĞİÖŞÜçğıöşü'

def fail(msg):raise ValueError(msg)
def u32(d,p): return struct.unpack_from('<I',d,p)[0]
def i32(d,p): return struct.unpack_from('<i',d,p)[0]
def i64(d,p): return struct.unpack_from('<q',d,p)[0]
def pad4(x): return (x+3)&~3

def metadata_read(blob):
    if u32(blob,0)!=0xfab11baf or u32(blob,4)!=16: fail('Beklenen IL2CPP metadata v16 değil.')
    table,count,data_off,data_size=struct.unpack_from('<IIII',blob,8)
    if count%8 or table!=0xc0 or data_off!=table+count or data_off+data_size>len(blob):fail('Metadata tablosu beklenenden farklı.')
    offsets=[]; out=[]
    for i in range(count//8):
        n,off=struct.unpack_from('<II',blob,table+8*i)
        if off+n>data_size:fail(f'Metadata {i} aralık dışında.')
        s=blob[data_off+off:data_off+off+n]
        try:s=s.decode('utf-8')
        except UnicodeDecodeError:fail(f'Metadata {i} UTF-8 dışı, güvenle değiştirilemiyor.')
        offsets.append((n,off));out.append(s)
    return out,(table,count,data_off,data_size,offsets)

def metadata_rebuild(blob,updates):
    originals,(table,count,data_off,data_size,offs)=metadata_read(blob)
    for i,s in updates.items():
        if not 0<=i<len(originals):fail('Geçersiz metadata index '+str(i))
        if not isinstance(s,str):fail('UTF-8 metin olmalı')
    raw=bytearray(); newidx=[]
    for i,orig in enumerate(originals):
        bs=updates.get(i,orig).encode('utf-8')
        newidx.append((len(bs),len(raw)));raw.extend(bs)
    # Preserve 4-byte alignment of all subsequent tables.
    raw.extend(b'\0'*((4-len(raw)%4)%4));new_len=len(raw)
    delta=new_len-data_size
    out=bytearray(blob[:data_off]);out.extend(raw);out.extend(blob[data_off+data_size:])
    for i,(n,off) in enumerate(newidx):struct.pack_into('<II',out,table+8*i,n,off)
    struct.pack_into('<I',out,0x14,new_len)
    old_end=data_off+data_size
    # Header metadata offsets are pairs (start, byteCount). Shift table starts,
    # except the literal table (0x08) and literal data table (0x10).
    for p in range(0x08,0xc0,8):
        if p in (0x08,0x10):continue
        start=u32(blob,p)
        if start>=old_end and start>0: struct.pack_into('<I',out,p,start+delta)
    chk,_=metadata_read(out)
    for i,v in updates.items():
        if chk[i]!=v:fail(f'Yama doğrulanamadı: metin {i}')
    if len(chk)!=len(originals):fail('Metin sayısı değişti.')
    return bytes(out)

class AssetFile:
    def __init__(self,raw):
        self.raw=raw
        if len(raw)<20:fail('Unity asset kısa')
        self.meta_size,self.total,self.version,self.start=struct.unpack_from('>IIII',raw)
        if self.version!=15 or raw[16]!=0:fail('Yalnızca bu oyundaki Unity asset v15, little-endian destekleniyor.')
        p=20
        p=raw.index(b'\0',p)+1
        p+=4 # platform
        tree=raw[p];p+=1
        if tree: fail('TypeTree bulunan asset desteklenmiyor.')
        n=u32(raw,p);p+=4
        if n>300:fail('Yüksek type sayısı - yanlış dosya?')
        self.types=[]
        for i in range(n):
            cl=i32(raw,p);p+=4
            if cl<0 or cl==114:p+=16
            p+=16;self.types.append(cl)
        self.objects=[];obj_count=u32(raw,p);p+=4
        if obj_count>50000:fail('Çok yüksek nesne sayısı')
        for i in range(obj_count):
            p=pad4(p)
            pid=i64(raw,p)
            off=i32(raw,p+8);size=i32(raw,p+12)
            typ=i32(raw,p+16);cl=struct.unpack_from('<h',raw,p+20)[0]
            if off<0 or size<0 or self.start+off+size>len(raw):fail('Nesne ofseti hatalı')
            self.objects.append({'pid':pid,'off':off,'size':size,'type':typ,'class':cl,'rec':p})
            p+=25
        self.index={o['pid']:o for o in self.objects}
    def object_bytes(self,obj):return self.raw[self.start+obj['off']:self.start+obj['off']+obj['size']]
    def replaced(self,by_id):
        if not by_id:return self.raw
        for pid in by_id:
            if pid not in self.index:fail('Path ID bulunamadı '+str(pid))
        # Rebuild data section, preserve original order and original nonobject padding;
        # always align individual objects to 4 bytes. Object IDs are unchanged.
        targets=sorted(self.objects,key=lambda o:o['off'])
        newdata=bytearray(); cursor=0; rec_updates=[]
        for obj in targets:
            original=self.object_bytes(obj)
            old_gap=self.raw[self.start+cursor:self.start+obj['off']]
            if len(old_gap)>4096:fail('Beklenmeyen nesne aralığı')
            newdata.extend(old_gap)
            newdata.extend(b'\0'*((4-len(newdata)%4)%4))
            offset=len(newdata)
            new=by_id.get(obj['pid'],original)
            newdata.extend(new)
            rec_updates.append((obj['rec'],offset,len(new)))
            cursor=obj['off']+obj['size']
        newdata.extend(self.raw[self.start+cursor:])
        res=bytearray(self.raw[:self.start]);res.extend(newdata)
        struct.pack_into('>I',res,4,len(res))
        for at,off,sz in rec_updates:struct.pack_into('<II',res,at+8,off,sz)
        r=AssetFile(bytes(res))
        for pid,v in by_id.items():
            if r.object_bytes(r.index[pid])!=v: fail('Asset round-trip doğrulaması başarısız')
        return bytes(res)

def unity_string_fields(payload):
    """Scan word-aligned Unity length-prefixed UTF-8 fields (not free binary strings)."""
    for p in range(0,len(payload)-5,4):
        n=u32(payload,p)
        if n<1 or n>min(4000,len(payload)-p-4):continue
        bs=payload[p+4:p+4+n]
        if any(x<32 and x not in (9,10,13) for x in bs):continue
        try:s=bs.decode('utf-8')
        except UnicodeError:continue
        if s and all(c.isprintable() or c in '\n\r\t' for c in s):yield p,s

def scene_ui(raw,filename):
    af=AssetFile(raw);rows=[]
    for obj in af.objects:
        if obj['class']!=114:continue
        dat=af.object_bytes(obj)
        # m_Script == PPtr(fileID 1 or 0, pathID 385), class UnityEngine.UI.Text
        if len(dat)<252 or i64(dat,20)!=385:continue
        if i32(dat,16) not in (0,1):continue
        candidates=[s for offset,s in unity_string_fields(dat) if offset==248]
        if not candidates:continue
        source=candidates[0]
        gameobj=i64(dat,4);gobj=af.index.get(gameobj)
        goname=''
        if gobj and gobj['class']==1:
            names=list(unity_string_fields(af.object_bytes(gobj)))
            if names:goname=names[-1][1]
        rows.append({'id':f'UI:{filename}:{obj["pid"]}', 'dosya':filename,
                     'path_id':str(obj['pid']),'oyun_nesnesi':goname,
                     'kaynak_metin':source,'turkce':'','durum':'bekliyor','notlar':''})
    return rows

def write_csv(path,cols,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore',lineterminator='\r\n')
        wr.writeheader();wr.writerows(rows)

def read_csv(path):
    with open(path,'r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def getzip(path):
    if not path.exists():fail('Oyun arşivi bulunamadı: '+str(path))
    z=zipfile.ZipFile(path)
    if METADATA not in z.namelist():fail('Bu zip Zeus Quest 3DS romfs içermiyor')
    return z

def source_lang_rows(strings,lang):
    a,b=LANGS[lang]
    return [{'id':f'META:{i}','meta_index':str(i),'kaynak_dil':lang,
             'kaynak_metin':strings[i],'turkce':'','durum':'bekliyor','notlar':''}
            for i in range(a,b)]

def bitmap_coverage(z):
    if FONT_ASSET not in z.namelist():return None
    asset=AssetFile(z.read(FONT_ASSET))
    font=next((o for o in asset.objects if o['class']==128),None)
    if not font:return None
    d=asset.object_bytes(font)
    # Verified m_CharacterRects table layout for the game's 'bitmapfont' asset.
    if d[:14]!=b'\x0a\x00\x00\x00bitmapfont':return None
    n=u32(d,52)
    if not 0<n<4096 or 56+44*n>len(d):return None
    codes=[u32(d,56+j*44) for j in range(n)]
    return font,codes

def extract(args):
    dest=Path(args.out)
    with getzip(Path(args.game)) as z:
        strings,_=metadata_read(z.read(METADATA))
        for lang in LANGS:
            write_csv(dest/'ceviriler'/f'{lang}_TR.csv',FIELDNAMES,source_lang_rows(strings,lang))
        print('Metadata dili satırları:',{k:b-a for k,(a,b) in LANGS.items()})
        # Combined file: Each column has its own exact metadata index and ordinal.
        # Blocks differ due to literal deduplication; correspondence IS NOT guaranteed.
        n=max(b-a for a,b in LANGS.values())
        merged=[]
        for ordinal in range(n):
            r={'sira':ordinal+1,'hizalama':'SIRASAL - DOGRULANMAMIS','turkce':''}
            for lang,(start,end) in LANGS.items():
                if start+ordinal<end:
                    r[f'{lang}_index']=start+ordinal;r[lang]=strings[start+ordinal]
                else:r[f'{lang}_index']='';r[lang]=''
            merged.append(r)
        write_csv(dest/'ceviriler'/'DILLER_YAN_YANA_KARSILASTIRMA.csv',
                  ['sira','hizalama',*[x for lang in LANGS for x in (lang+'_index',lang)],'turkce'],merged)
        uimaster=[]
        for name in z.namelist():
            if name.startswith('romfs/Data/') and (name.rsplit('/',1)[-1].startswith('level') or name.endswith('.assets')):
                try:uimaster.extend(scene_ui(z.read(name),name))
                except ValueError:continue
        write_csv(dest/'ceviriler'/'UI_EN_TR.csv',UIFIELDS,uimaster)
        font=bitmap_coverage(z)
        if font:
            obj,glyphs=font;present=set(glyphs)
            fontrows=[{'karakter':c,'unicode':f'U+{ord(c):04X}', 'fontta_var':'EVET' if ord(c) in present else 'HAYIR',
                       'durum':'mevcut' if ord(c) in present else 'yeniden_cizilmeli'} for c in CHARSET]
            write_csv(dest/'font'/'TURKCE_KARAKTER_KONTROL.csv',
                      ['karakter','unicode','fontta_var','durum'],fontrows)
            write_csv(dest/'font'/'MEVCUT_BITMAP_GLYPHS.csv',
                      ['unicode','karakter','codepoint'],[
                      {'unicode':f'U+{c:04X}','karakter':chr(c) if c>=32 and chr(c).isprintable() else '', 'codepoint':c}
                      for c in glyphs])
        summary={'unity':'5.2.4f1','metadata_version':16,'string_literals':len(strings),
                 'languages':{k:b-a for k,(a,b) in LANGS.items()},
                 'ui_entries':len(uimaster), 'font':'bitmapfont',
                 'font_missing': [c for c in CHARSET if font and ord(c) not in font[1]],
                 'note':'UI ve İngilizce script sabitleri ayrı kaynaklarda. Çokdilli karşılaştırma sütunlarının satır eşleştirmesi garanti edilmez.'}
        (dest/'dokuman').mkdir(exist_ok=True,parents=True)
        (dest/'dokuman'/'tespit_ozeti.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        print('UI satırları:',len(uimaster),'font eksik:',summary['font_missing'])
        return summary

def validate_markup(original,new):
    oldtags=re.findall(r'</?\s*[a-zA-Z]+(?:\s+[^>]*)?>',original)
    newtags=re.findall(r'</?\s*[a-zA-Z]+(?:\s+[^>]*)?>',new)
    if sorted(oldtags)!=sorted(newtags): fail('HTML/Unity rich-text etiketleri farklı: '+repr(original[:70]))
    oldfields=re.findall(r'(?<!\{)\{\d+(?::[^{}]*)?\}',original)
    newfields=re.findall(r'(?<!\{)\{\d+(?::[^{}]*)?\}',new)
    if sorted(oldfields)!=sorted(newfields):fail('Sayı yer tutucuları farklı: '+repr(original[:70]))

def ui_rebuild_obj(d,source,new):
    pos=248
    orig_len=u32(d,pos)
    if d[pos+4:pos+4+orig_len].decode('utf8')!=source:fail('UI kaynak metin uyuşmuyor')
    oldend=pad4(pos+4+orig_len)
    bs=new.encode('utf-8')
    out=d[:pos]+struct.pack('<I',len(bs))+bs
    out+=b'\0'*((4-len(out)%4)%4)
    out+=d[oldend:]
    return out

def build(args):
    slot=args.slot.upper()
    if slot not in LANGS:fail('Bilinmeyen dil yuvası: '+slot)
    edits={};warnings=[]
    for row in read_csv(Path(args.csv)):
        new=row.get('turkce','')
        if new is None or not new.strip():continue
        idx=int(row['meta_index']); start,end=LANGS[slot]
        if not start<=idx<end:fail(f'CSV index {idx} seçilen {slot} yuvasında değil')
        if idx in edits and edits[idx][1]!=new:fail(f'CSV tekrarlı ama farklı: {idx}')
        edits[idx]=(row['kaynak_metin'],new)
    ui_edits={}
    if args.ui_csv:
        for row in read_csv(Path(args.ui_csv)):
            new=row.get('turkce','')
            if new is None or not new.strip():continue
            fn=row['dosya'];pid=int(row['path_id']);key=(fn,pid)
            if key in ui_edits:fail('Tekrarlanan UI ID: '+str(key))
            ui_edits[key]=(row['kaynak_metin'],new)
    with getzip(Path(args.game)) as game:
        original=game.read(METADATA);all_strings,_=metadata_read(original)
        patch={};translated={}
        for idx,(source,new) in edits.items():
            if all_strings[idx]!=source:fail(f'Kaynak ZIP değişmiş veya CSV eski: META:{idx}')
            validate_markup(source,new)
            if new!=source:translated[idx]=new
        if translated:patch[METADATA]=metadata_rebuild(original,translated)
        ui_byfile={}
        for (filename,pid),value in ui_edits.items():ui_byfile.setdefault(filename,{})[pid]=value
        for filename,items in ui_byfile.items():
            if filename not in game.namelist():fail('ZIPte UI dosyası yok: '+filename)
            af=AssetFile(game.read(filename));by_id={}
            for pid,(source,new) in items.items():
                obj=af.index.get(pid)
                if not obj or obj['class']!=114:fail('UI path ID bulunamadı')
                d=af.object_bytes(obj)
                if i64(d,20)!=385:fail('UI bileşeni Text değil')
                validate_markup(source,new)
                if new!=source:by_id[pid]=ui_rebuild_obj(d,source,new)
            if by_id:patch[filename]=af.replaced(by_id)
        if not args.no_font:
            # 517 eski glifi koruyup 8 Turkce glif ekler; ETC1A4 3DS texture,
            # Font m_CharacterRects, Unity object tablosu birlikte guncellenir.
            from turkce_font import patch_font_asset
            patch[FONT_ASSET]=patch_font_asset(patch.get(FONT_ASSET,game.read(FONT_ASSET)))[0]
        if not patch:
            print('Henüz çeviri yok ve font yaması kapalı. CSV turkce sütunlarını doldurun.')
            return False
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zout:
            for filename,content in patch.items():zout.writestr(filename,content)
            zout.writestr('README_PATCH.txt',
                ('Zeus Quest Remastered 3DS Türkçe yama dosyaları\n'
                 'Bu zip SADECE degisen dosyalari icerir. Oyun romfs icerisine ayni goreli yollarda\n'
                 'uygulayin veya kendi LayeredFS duzeninize dogru yerlestirin.\n'
                 'Turkce font (Ğ ğ İ ı Ş ş ’ •) varsayilan olarak eklenmistir.\n'
                 'Orijinal dosyalarin yedegini alin. Orijinal oyun dagitilmaz.\n').encode('utf-8'))
        print('Oluşturuldu',out,'metadata yazı',len(translated),'UI yazı',sum(1 for v in ui_edits.values() if v[0]!=v[1]),
              'değişen dosya',len(patch),'Türkçe font', 'DAHIL' if not args.no_font else 'KAPALI')
        return True

def check(args):
    with getzip(Path(args.game)) as z:
        coverage=bitmap_coverage(z)
        if not coverage:fail('Font tablosu tanınmadı')
        supported=set(coverage[1]);allchars=set(CHARSET)
        used=set()
        for filename in args.csv:
            for row in read_csv(Path(filename)):
                s=row.get('turkce','')
                used.update(s)
        missing=sorted(c for c in (used or allchars) if ord(c) not in supported and ord(c)>32)
        print('Orijinal bitmap fontta olmayan karakterler:', ' '.join(f'{x}(U+{ord(x):04X})' for x in missing) or 'YOK')
        print('build komutu varsayılan olarak Ğ ğ İ ı Ş ş ’ • gliflerini ekler.')

def font_build(args):
    from turkce_font import run_patch
    patch=run_patch(args.game)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(FONT_ASSET,patch)
        z.writestr('README_FONT.txt',
                   'bitmapfont: 517 + 8 Turkce glif = 525 karakter.\n'
                   'Bu yamada sadece romfs/Data/sharedassets0.assets degisir.\n'
                   'Kendi romfs katmaninizda ayni dizine kopyalayin.\n'
                   'Gercek 3DS / emulator testi gereklidir.\n')
    print('Türkçe font yaması oluşturuldu:',out)

def main():
    ap=argparse.ArgumentParser(description='Zeus Quest 3DS Unity çeviri aracı')
    sub=ap.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('extract',help='Tüm metinleri ve font kapsamını CSV dışa aktar')
    a.add_argument('--game',required=True,help='Orijinal Zeus Quest Remastered.zip')
    a.add_argument('--out',default='cikti');a.set_defaults(f=extract)
    a=sub.add_parser('build',help='CSV metinlerinden romfs yama ZIP oluştur')
    a.add_argument('--game',required=True);a.add_argument('--csv',required=True)
    a.add_argument('--slot',choices=['en','fr','de','el','it','es'],default='en')
    a.add_argument('--ui-csv',default=None)
    a.add_argument('--no-font',action='store_true',help='Font yamasını pakete ekleme')
    a.add_argument('--out',default='ZeusQuest_TR_LayeredFS.zip');a.set_defaults(f=build)
    a=sub.add_parser('font-check',help='Doldurulmuş CSVlerdeki Türkçe glyph eksiklerini kontrol et')
    a.add_argument('--game',required=True);a.add_argument('--csv',nargs='+',required=True)
    a.set_defaults(f=check)
    a=sub.add_parser('font-build',help='Yalnızca Türkçe font yaması üret')
    a.add_argument('--game',required=True);a.add_argument('--out',default='ZeusQuest_TR_Font_Yamasi.zip')
    a.set_defaults(f=font_build)
    args=ap.parse_args()
    try:args.f(args)
    except (ValueError,KeyError,UnicodeDecodeError,zipfile.BadZipFile,OSError) as e:
        print('HATA:',e,file=sys.stderr);sys.exit(1)

if __name__=='__main__':main()
