#!/usr/bin/env python3
"""Özgün dokulardan, ölçülü yazı katmanları ile tekrar üretilebilir grafikler."""
from pathlib import Path
import argparse,json,math
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import drmario_tool as t
PKG=Path(__file__).resolve().parent.parent
FONTS=PKG/'araclar/fontlar'
S=4

def label(text,height,maxwidth,style,color=(255,255,255),outline=(51,51,51)):
    fontname='Oyun.ttf' if style=='game' else 'Kalin.ttf' if style=='smallbold' else 'Duz.ttf' if style=='plain' else 'Yuvarlak.otf'
    font=ImageFont.truetype(str(FONTS/fontname),80*S)
    stroke=0 if style=='plain' else (10*S if style=='game' else 6*S if style=='smallbold' else 7*S)
    spacing=6*S
    b=ImageDraw.Draw(Image.new('L',(1,1))).multiline_textbbox((0,0),text,font=font,stroke_width=stroke,spacing=spacing,align='center')
    sz=(math.ceil(b[2]-b[0]+4*S),math.ceil(b[3]-b[1]+4*S))
    mask=Image.new('L',sz);d=ImageDraw.Draw(mask)
    xy=(2*S-b[0],2*S-b[1]);d.multiline_text(xy,text,font=font,fill=255,spacing=spacing,align='center')
    if style=='game':
        # Harflerin hafif farklı eğimleri özgün hareketli başlıklara yaklaşır.
        mask=Image.new('L',(sz[0]+40*S,sz[1]+30*S))
        pen=20*S
        for i,char in enumerate(text):
            cb=font.getbbox(char);advance=font.getlength(char)
            if char!=' ':
                glyph=Image.new('L',(math.ceil(advance)+30*S,110*S))
                ImageDraw.Draw(glyph).text((15*S,0),char,font=font,fill=255)
                glyph=glyph.rotate([3,-4,2,-2,4][i%5],resample=Image.Resampling.BICUBIC)
                mask.paste(glyph,(round(pen)-15*S,0),glyph)
            pen+=advance
        mask=mask.crop(mask.getbbox())
        framed=Image.new('L',(mask.width+2*stroke+8*S,mask.height+2*stroke+8*S))
        framed.paste(mask,(stroke+4*S,stroke+4*S));mask=framed;sz=mask.size
    outer=Image.new('L',sz);ImageDraw.Draw(outer).multiline_text(xy,text,font=font,fill=255,stroke_width=stroke,stroke_fill=255,spacing=spacing,align='center')
    if style=='game':outer=mask.filter(ImageFilter.MaxFilter(2*stroke+1))
    out=Image.new('RGBA',sz,(*outline,255));out.putalpha(outer)
    fill=Image.new('RGBA',sz,(*color,255))
    if style=='game':
        # İki tonlu dolgu ve ince beyaz iç kenar, özgün renk ailesini izler.
        edge=mask.filter(ImageFilter.MaxFilter(11))
        white=Image.new('RGBA',sz,(255,250,231,255));white.putalpha(edge);out.alpha_composite(white)
        pix=fill.load()
        for y in range(sz[1]):
            f=y/max(1,sz[1]-1)
            for x in range(sz[0]):
                hi=max(0,0.7-f)*.75
                pix[x,y]=tuple(round(c+(255-c)*hi) for c in color)+(255,)
    fill.putalpha(mask);out.alpha_composite(fill)
    b=out.getbbox();out=out.crop(b)
    scale=min(height/out.height,maxwidth/out.width)
    out=out.resize((max(1,round(out.width*scale*S)),max(1,round(out.height*scale*S))),Image.Resampling.LANCZOS)
    return out.resize((max(1,round(out.width/S)),max(1,round(out.height/S))),Image.Resampling.LANCZOS)

def insert(img,text,box,style='round',color=(255,255,255),outline=(51,51,51)):
    x0,y0,x1,y1=box
    fg=label(text,y1-y0,x1-x0,style,color,outline)
    img.alpha_composite(fg,(round((x0+x1-fg.width)/2),round((y0+y1-fg.height)/2)))

def clean_gradient(img,box):
    # Yatay düz renkli düğmelerde, aynı satırdaki yazısız renk örnekleri.
    x0,y0,x1,y1=box; px=img.load()
    for y in range(y0,y1):
        candidates=[px[x,y] for x in range(x0,x1) if px[x,y][3]>245]
        # Beyaz yazı ve gri kontur düşük doygunlukludur.
        bg=max(candidates,key=lambda c:max(c[:3])-min(c[:3]))
        for x in range(x0,x1):px[x,y]=bg

def clean_button_center(img,box):
    """Simetrik düğmenin yazı merkezini, iki yandaki temiz piksellerden kurar."""
    x0,y0,x1,y1=box;px=img.load()
    for y in range(y0,y1):
        left=px[x0-2,y];right=px[x1+1,y]
        bg=tuple(round((a+b)/2) for a,b in zip(left,right))
        for x in range(x0,x1):px[x,y]=bg

def render(name,src,text):
    box=src.getbbox();w,h=src.size
    special=any(s in name for s in ['menu_panel_01_btnpic_','menu_panel_07_0_btnpic_1','menu_panel_08_0_btnpic_1','netplay_btnpic_03_','top_binder_vs_scr02_'])
    img=src.copy() if special else Image.new('RGBA',src.size)
    if 'menu_panel_01_btnpic_' in name:
        box=(15,19,97,54);clean_button_center(img,box)
        insert(img,text,(17,20,95,53),'smallbold',(255,255,255),(55,55,55))
        return img,box
    if 'menu_panel_07_' in name or 'menu_panel_08_' in name:
        box=(13,23,148,77);clean_gradient(img,box)
        insert(img,text,(15,25,146,74));return img,box
    if 'netplay_btnpic_03_' in name:
        box=(18,44,w-16,68);clean_gradient(img,box)
        insert(img,text,(20,45,w-18,66));return img,box
    if 'top_binder_vs_scr02_' in name:
        # Bu dokular yerleşimde ayrıca döndürülür; yerel yönü korunur.
        upright=src.transpose(Image.Transpose.ROTATE_90)
        if 'time_2' in name:box=(27,2,159,25)
        else:box=(4,2,upright.width-4,upright.height-2)
        # Etiketin fonu sabit RGBA; desenli sonuç alanı değiştirilmez.
        bg=upright.getpixel((upright.width-2,2))
        ImageDraw.Draw(upright).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=bg)
        insert(upright,text,box,'plain')
        return upright.transpose(Image.Transpose.ROTATE_270),None
    x0,y0,x1,y1=box
    # Kısa çevirileri büyütme; eski yazı merkezini ve yüksekliğini koru.
    maxw=min(w-4,max(x1-x0,w*.87));cx=(x0+x1)/2
    box=(max(2,cx-maxw/2),y0,min(w-2,cx+maxw/2),y1)
    if 'game_font' in name or 'vs_start_font' in name or 'localnet_top_gtxt' in name:
        colors={'game_font_01':(25,121,240),'game_font_02':(15,210,187),'game_font_03':(255,105,15),'game_font_04':(255,174,30),'game_font_05':(255,118,17),'vs_start_font_03':(255,82,24),'vs_start_font_04':(41,118,242),'vs_start_font_08':(15,220,124)}
        color=next((v for k,v in colors.items() if k in name),(255,164,27))
        insert(img,text,box,'game',color,(8,8,8))
    elif 'info_mode' in name:
        color=(255,255,255) if 'f' in Path(name).stem.replace('info','') else (255,222,0)
        if 'info_mode_20.' in name:color=(255,167,0)
        insert(img,text,box,'smallbold',color,(0,0,0))
    elif 'score_panel_line' in name or 'submenu_hiscore' in name:
        color=(0,0,0) if 'line_34' in name else (64,64,64) if 'hiscore' in name else (255,255,255)
        insert(img,text,box,'plain',color)
    elif any(x in name for x in ['t_modetitle','t_ranking','t_join']):
        insert(img,text,box,'round',(255,226,146),(4,4,4))
    else:insert(img,text,box)
    return img,box

def main():
    ap=argparse.ArgumentParser();ap.add_argument('romfs');a=ap.parse_args()
    trans=json.loads((PKG/'ceviri/gorsel_cevirileri.json').read_text(encoding='utf-8'))
    records=[]
    for area in ['game','menu']:
        ar=t.arcv_parse(t.sszl_unpack((Path(a.romfs)/area/'2d/en/main.lzss').read_bytes()))
        nodes={n['name']:n['data'] for n in t.sarc_parse(ar['entries'][0]['data'])['nodes']}
        for key,txt in trans.items():
            if not key.startswith(area+'/'):continue
            name=key[len(area)+1:];b=nodes[name];src,inf=t.bflim_decode_image(b)
            img,box=render(key,src,txt);out=t.bflim_encode_image(img,b)
            p=PKG/'ceviri/gorseller'/key;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(out)
            actual,_=t.bflim_decode_image(out)
            actual.save(PKG/'ceviri/gorsel_onizlemeler'/f'{area}_{Path(name).stem}.png')
            records.append({'dosya':key,'boyut':list(src.size),'ozgun_yazi_siniri':list(src.getbbox()),'yeni_yazi_alani':box})
    (PKG/'ceviri/gorsel_yerlesimleri.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(records)} yazılı doku üretildi.')
if __name__=='__main__':main()
