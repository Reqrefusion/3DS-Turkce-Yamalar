#!/usr/bin/env python3
"""Özgün RomFS üzerine doğrulanmış Türkçe kaynakları uygular."""
from __future__ import annotations
import argparse,json,re,tempfile,os,hashlib
from pathlib import Path
import drmario_tool as t
TITLE_ID='000400000013BB00'
MESSAGE_LANGS=['en','en_eu','fr','fr_us','ge','it','ja','sp','sp_us']
GRAPHIC_LANGS=['en','es','fr','ge','it','ja']
PKG=Path(__file__).resolve().parent.parent

def readarc(path):return t.arcv_parse(t.sszl_unpack(path.read_bytes()))
def checked_pack(ar,replacements):
    raw=t.arcv_build(ar,replacements);packed=t.sszl_pack(raw)
    if t.sszl_unpack(packed)!=raw:raise ValueError('SSZL geri açma testi başarısız')
    got={e['name']:e['data'] for e in t.arcv_parse(t.sszl_unpack(packed))['entries']}
    for e in ar['entries']:
        if got[e['name']]!=replacements.get(e['name'],e['data']):raise ValueError('ARCV veri doğrulaması başarısız')
    return packed

def placeholders(s):return re.findall(r'%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?(?:ll|l|h)?[diuoxXfFeEgGaAcsp%]',s)

def build(romfs,out):
    hashes=json.loads((PKG/'ceviri/kaynak_sha256.json').read_text(encoding='utf-8'))
    for rel,digest in hashes.items():
        if hashlib.sha256((romfs/rel).read_bytes()).hexdigest()!=digest:raise ValueError(f'Özgün kaynak uyuşmuyor: {rel}')
    tr=json.loads((PKG/'ceviri/metinler_tr.json').read_text(encoding='utf-8'))
    from metinleri_denetle import main as check_texts
    check_texts()
    reference=readarc(romfs/'message/ms/bin/en/main.lzss')
    ref={e['name']:e for e in reference['entries'] if e['name'] in tr}
    for name,values in tr.items():
        old=t.msbt_texts(ref[name]['data'])
        if len(old)!=len(values):raise ValueError(f'Metin sayısı farklı: {name}')
        for i,(a,b) in enumerate(zip(old,values)):
            if placeholders(a)!=placeholders(b):raise ValueError(f'Değişken işareti farklı: {name}:{i}')
            if any(len(line.strip())==1 and line.strip().isalpha() for line in b.splitlines()):raise ValueError(f'Tek harflik satır: {name}:{i}')
    generated={};counts={}
    for lang in MESSAGE_LANGS:
        rel=Path('message/ms/bin')/lang/'main.lzss';ar=readarc(romfs/rel);repl={}
        for e in ar['entries']:
            name=e['name']
            if name not in tr:continue
            source_labels=t.msbt_labels(ref[name]['data']);target_labels=t.msbt_labels(e['data'])
            label_text={source_labels[i]:s for i,s in enumerate(tr[name])}
            if set(target_labels.values())!=set(label_text):raise ValueError(f'Metin etiketleri uyuşmuyor: {lang}/{name}')
            values=[label_text[target_labels[i]] for i in range(len(tr[name]))]
            new=t.msbt_replace_texts(e['data'],values)
            if t.msbt_texts(new)!=values or t.msbt_labels(new)!=target_labels:raise ValueError('MSBT doğrulaması başarısız')
            repl[name]=new
        if set(repl)!=set(tr):raise ValueError('Eksik MSBT')
        generated[rel]=checked_pack(ar,repl)
        print(f'Metin hazır: {lang}',flush=True)
    for area in ['game','menu']:
        base=PKG/'ceviri/gorseller'/area
        replacements={p.relative_to(base).as_posix():p.read_bytes() for p in base.rglob('*.bflim')}
        images={k:t.bflim_decode_image(b)[0] for k,b in replacements.items()}
        for lang in GRAPHIC_LANGS:
            rel=Path(area)/'2d'/lang/'main.lzss';ar=readarc(romfs/rel)
            if len(ar['entries'])!=1:raise ValueError('Tek SARC bekleniyor')
            ent=ar['entries'][0];sarc=ent['data'];nodes={n['name']:n['data'] for n in t.sarc_parse(sarc)['nodes']};repl={}
            for name,img in images.items():
                if name not in nodes:raise ValueError(f'Görsel eksik: {area}/{lang}/{name}')
                template=nodes[name];target,info=t.bflim_decode_image(template)
                if target.size!=img.size:
                    from PIL import Image
                    # Boş doku yüksekliği değiştiğinde harfleri ezme.
                    glyph=img.crop(img.getbbox());bbox=target.getbbox()
                    scale=min(1,(target.width-4)/glyph.width,(target.height-2)/glyph.height)
                    glyph=glyph.resize((max(1,round(glyph.width*scale)),max(1,round(glyph.height*scale))),Image.Resampling.LANCZOS)
                    im=Image.new('RGBA',target.size)
                    cx=(bbox[0]+bbox[2])/2;cy=(bbox[1]+bbox[3])/2
                    x=max(0,min(target.width-glyph.width,round(cx-glyph.width/2)))
                    y=max(0,min(target.height-glyph.height,round(cy-glyph.height/2)))
                    im.alpha_composite(glyph,(x,y))
                else:im=img
                repl[name]=t.bflim_encode_image(im,template)
            patched=t.sarc_patch_same_size(sarc,repl)
            got={n['name']:n['data'] for n in t.sarc_parse(patched)['nodes']}
            for name,data in nodes.items():
                if got[name]!=repl.get(name,data):raise ValueError(f'SARC doğrulaması başarısız: {name}')
            generated[rel]=checked_pack(ar,{ent['name']:patched})
            print(f'Grafik hazır: {area}/{lang}',flush=True)
        counts[area]=len(replacements)
    # Tüm içerikler üretildikten sonra yalnız bu pakete ait 21 dosyayı yaz.
    dest=out/'luma/titles'/TITLE_ID/'romfs'
    for rel,data in generated.items():
        path=dest/rel;path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:f.write(data);temp=Path(f.name)
        os.replace(temp,path)
    print(f'Hazır: {out}\nMetin: {sum(map(len,tr.values()))}; grafik: {counts}; paket: {len(generated)}')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('romfs');ap.add_argument('cikti');a=ap.parse_args()
    romfs=Path(a.romfs).resolve();out=Path(a.cikti).resolve()
    if out==romfs or out in romfs.parents or romfs in out.parents:raise SystemExit('Kaynak ve çıktı ayrı klasörler olmalı.')
    build(romfs,out)
if __name__=='__main__':main()
