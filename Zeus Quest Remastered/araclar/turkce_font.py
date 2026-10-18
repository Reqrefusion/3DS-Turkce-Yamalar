#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zeus Quest 3DS Unity 5.2 bitmapfont'a Türkçe metinlerin ihtiyaç duyduğu altı harf ve iki noktalama glifini ekler.

Sadece Python stdlib. Oyun motorunun ETC1A4_3DS (format 61) bitmap atlasini
kayipsiz 512x512 -> 1024x512 buyutur; 517 mevcut glifi/dokuyu korur;
Türkçe 8 glifi mevcut harf/aksanlardan sentezler, metrikleri ve UV'leri gunceller.
Gercek konsol/emulator testi ayrica gereklidir.
"""
import struct

LETTERS = 'ĞğİıŞş’•'
SRC_W, SRC_H, NEW_W, NEW_H = 512,512,1024,512


def u32(b,p): return struct.unpack_from('<I',b,p)[0]
def fail(msg): raise ValueError('Font yaması: '+msg)


def get_font_chars(font):
    if not font.startswith(b'\x0a\x00\x00\x00bitmapfont'):
        fail('beklenen bitmapfont bulunamadı')
    count=u32(font,52)
    if count!=517:fail('karakter sayısı farklı: '+str(count))
    end=56+count*44
    if end>len(font):fail('karakter tablosu kesilmiş')
    chars={}
    codes=[]
    for j in range(count):
        dat=font[56+44*j:56+44*(j+1)]
        code=u32(dat,0)
        if code in chars:fail('tekrarlı kod noktası')
        chars[code]=dat;codes.append(code)
    if codes!=sorted(codes):fail('karakter tablosu sıralı değil')
    for ch in LETTERS:
        if ord(ch) in chars:fail('zaten Türkçe karakter var: '+ch)
    return chars, font[end:]


def decode_alpha(tex):
    if len(tex)!=76+SRC_W*SRC_H:fail('Texture2D verisi bilinmeyen uzunlukta')
    if (u32(tex,16),u32(tex,20),u32(tex,24),u32(tex,28),u32(tex,72))!=(512,512,262144,61,262144):
        fail('texture2D başlığı beklenenden farklı')
    data=tex[76:]
    fixed_color=b'\x00\x00\x00\x00\x02\xf8\xf8\xf8'
    alpha=bytearray(512*512)
    idx=0
    for ty in range(0,512,8):
        for tx in range(0,512,8):
            for by in range(2):
                for bx in range(2):
                    bit=int.from_bytes(data[idx:idx+8],'little')
                    if data[idx+8:idx+16]!=fixed_color:
                        fail('atlasın bazı ETC1 renk blokları farklı; güvenli yama yapılamıyor')
                    idx+=16
                    for py in range(4):
                        for px in range(4):
                            alpha[(ty+by*4+py)*512+tx+bx*4+px]=(bit>>(4*(px*4+py)))&15
    return alpha


def rect_of(raw, w=512, h=512):
    u,v,uw,vh=struct.unpack_from('<4f',raw,4)
    x=round(u*w); y=round((1-v-vh)*h); rw=round(uw*w);rh=round(vh*h)
    if not (0<=x<=w and 0<=y<=h and 0<=x+rw<=w and 0<=y+rh<=h):
        fail('glif UV sınır dışı')
    return x,y,rw,rh


def patch_font_asset(raw_asset):
    # Local import supports direct CLI execution as well as package import.
    try:
        from zeusquest_tool import AssetFile
    except ImportError:
        from .zeusquest_tool import AssetFile
    af=AssetFile(raw_asset)
    font_objs=[o for o in af.objects if o['class']==128]
    if len(font_objs)!=1:fail('beklenmeyen Font nesne sayısı')
    fobj=font_objs[0]
    font=af.object_bytes(fobj)
    chars,tail=get_font_chars(font)
    tex_objects=[]
    for o in af.objects:
        if o['class']!=28:continue
        d=af.object_bytes(o)
        if d.startswith(b'\x0c\x00\x00\x00bitmapfont_0'):
            tex_objects.append(o)
    if len(tex_objects)!=1:fail('bitmapfont_0 dokusu bulunamadı')
    texobj=tex_objects[0]
    tex=af.object_bytes(texobj)
    alpha=decode_alpha(tex)

    def sprite(ch):
        x,y,w,h=rect_of(chars[ord(ch)])
        return [bytearray(alpha[(y+k)*512+x:(y+k)*512+x+w]) for k in range(h)]

    def src_metrics(ch):
        dat=chars[ord(ch)]
        m=list(struct.unpack_from('<10f',dat,4))
        return m

    def combine(base,mark=None,pos='top',height=8,trim=0):
        rows=sprite(base)
        w=len(rows[0])
        if trim:
            return [r[:] for r in rows[trim:]],w
        result=[bytearray(w) for _ in range(len(rows)+height)]
        base_offset=height if pos=='top' else 0
        for y,row in enumerate(rows):result[y+base_offset][:]=row
        if mark:
            m=sprite(mark)
            if pos=='top':accent=m[:height-1]
            elif pos=='bottom':accent=m[-height:]
            else:fail('aksan konumu')
            mw=len(accent[0]);dx=round((w-mw)/2)
            for y,row in enumerate(accent):
                dy=y if pos=='top' else len(rows)+y
                for mx,v in enumerate(row):
                    px=mx+dx
                    if 0<=px<w and v>result[dy][px]: result[dy][px]=v
        return result,w

    # Türkçe aksanlarının yüksekliği, oyun fontundaki Kiril breve / Ç glifleriyle aynıdır.
    defs={
        'Ğ':('G',*combine('G','˘','top'),+8,8),
        'ğ':('g',*combine('g','˘','top'),+8,8),
        'İ':('I',*combine('I','˙','top'),+8,8),
        'ı':('i',*combine('i',trim=8),-8,-8),
        'Ş':('S',*combine('S','Ç','bottom'),0,8),
        'ş':('s',*combine('s','ç','bottom'),0,8),
        # Aşama 33 Türkçesinin kullandığı iki ek işaret; mevcut gliflerden türetildi.
        '’':("'",sprite("'"),rect_of(chars[ord("'")])[2],0,0),
        '•':('·',sprite('·'),rect_of(chars[ord('·')])[2],0,0),
    }
    # İmal edilmiş yeni glifleri atlasın sağ yarısında 1-px emniyet boşluğu ile yerleştir.
    locations={}
    cursor=532
    for char in LETTERS:
        base,rows,w,topchange,heightchange=defs[char]
        h=len(rows)
        if h!=rect_of(chars[ord(base)])[3]+heightchange:
            fail('aksan yüksekliği uyuşmuyor')
        x=cursor;y=48
        if x+w+2>1024:fail('genişletilmiş atlas doldu')
        locations[char]=(x,y,w,h)
        cursor+=w+8

    # GPU'nun 8x8 Morton değil 2x2 raster bloklardan oluşan ETC1A4_3DS atlası.
    # SOL YARIDAKI ORIJINAL BLOKLAR BYTE-FOR-BYTE AYNEN KOPYALANIR.
    old=tex[76:]
    blank=(b'\x00'*8+b'\x00'*4+b'\x02\xf8\xf8\xf8')*4
    newpix=bytearray(blank*(NEW_W//8)*(NEW_H//8))
    for row in range(NEW_H//8):
        original_slice=old[row*4096:(row+1)*4096]
        newpix[row*8192:row*8192+4096]=original_slice
    for ch in LETTERS:
        x,y,w,h=locations[ch]
        sprite_rows=defs[ch][1]
        for iy,r in enumerate(sprite_rows):
            for ix,value in enumerate(r):
                if not value:continue
                px=x+ix;py=y+iy
                tile=((py//8)*(NEW_W//8)+(px//8))*64
                block=((py%8)//4)*2+((px%8)//4)
                offset=tile+block*16
                index=(px%4)*4+(py%4)
                pos=offset+(index//2)
                if index%2:newpix[pos]=(newpix[pos]&0x0f)|((value&15)<<4)
                else:newpix[pos]=(newpix[pos]&0xf0)|(value&15)

    newtex=bytearray(tex[:76]);newtex.extend(newpix)
    for pos,value in ((16,1024),(24,1024*512),(72,1024*512)):
        struct.pack_into('<I',newtex,pos,value)

    newchars={}
    for code,oldrec in chars.items():
        rec=bytearray(oldrec)
        uv=struct.unpack_from('<4f',rec,4)
        struct.pack_into('<f',rec,4,uv[0]/2.0)
        struct.pack_into('<f',rec,12,uv[2]/2.0)
        newchars[code]=bytes(rec)
    for ch in LETTERS:
        base,rows,w,topchange,heightchange=defs[ch]
        x,y,rw,rh=locations[ch]
        rec=bytearray(chars[ord(base)])
        struct.pack_into('<I',rec,0,ord(ch))
        struct.pack_into('<4f',rec,4,x/1024.0,(512-y-rh)/512.0,rw/1024.0,rh/512.0)
        metrics=src_metrics(base)
        struct.pack_into('<f',rec,4+5*4,metrics[5]+topchange)
        struct.pack_into('<f',rec,4+7*4,metrics[7]-heightchange)
        newchars[ord(ch)]=bytes(rec)
    if len(newchars)!=525:fail('çıktı glif adedi hatalı')
    newfont=bytearray(font[:52]);newfont.extend(struct.pack('<I',525))
    for code in sorted(newchars):newfont.extend(newchars[code])
    newfont.extend(tail)
    newaf=af.replaced({fobj['pid']:bytes(newfont),texobj['pid']:bytes(newtex)})
    checkaf=AssetFile(newaf)
    savedfont=checkaf.object_bytes(checkaf.index[fobj['pid']]); savedtex=checkaf.object_bytes(checkaf.index[texobj['pid']])
    if len(savedfont)!=len(font)+352 or u32(savedfont,52)!=525:fail('çıktı font doğrulaması başarısız')
    if savedtex[76:76+4096]!=old[:4096]:fail('orijinal atlas korunmadı')
    for row in range(64):
        if savedtex[76+row*8192:76+row*8192+4096]!=old[row*4096:row*4096+4096]:
            fail('orijinal atlas blokları bozuldu')
    all_codes=[u32(savedfont,56+i*44) for i in range(525)]
    if all_codes!=sorted(all_codes) or not all(ord(x) in all_codes for x in LETTERS):
        fail('yeni Unicode kodları yanlış')
    for c in LETTERS:
        o=56+44*all_codes.index(ord(c))
        if rect_of(savedfont[o:o+44],1024,512)!=locations[c]:
            fail('yeni glif UV koordinatları hatalı: '+c)
    return newaf,locations,tex,bytes(newtex),font,bytes(newfont)


def run_patch(game_zip):
    import zipfile
    with zipfile.ZipFile(game_zip) as z:
        name='romfs/Data/sharedassets0.assets'
        return patch_font_asset(z.read(name))[0]

if __name__=='__main__':
    import argparse, zipfile
    from pathlib import Path
    a=argparse.ArgumentParser(description='Oyun fontuna 6 Turkce glif ekler')
    a.add_argument('--game',required=True);a.add_argument('--out',default='ZeusQuest_TR_Font_Yamasi.zip')
    args=a.parse_args()
    data=run_patch(args.game)
    with zipfile.ZipFile(args.out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('romfs/Data/sharedassets0.assets',data)
        z.writestr('README_FONT.txt','Unity bitmapfont: Ğ ğ İ ı Ş ş ’ • eklendi. 1024x512 ETC1A4. Gerçek 3DS testi gereklidir.\n')
    print('Yazıldı:',args.out)
