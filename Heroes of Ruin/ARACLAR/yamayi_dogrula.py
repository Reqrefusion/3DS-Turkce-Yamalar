from __future__ import annotations
import csv, json, hashlib, sys
from pathlib import Path
from collections import Counter
from hor_formats import parse_strl_file, protected_tokens, blz_decompress
from hor_font_patch import _raw_font, _cmap_codepoints, TURKISH

STRL=['buffs','characterparts','dialogues','names','quests','strings','weapons']

def sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    root=Path(__file__).resolve().parent.parent
    trans=root/'CEVIRI/translation_multilang'
    rom=root/'YAMA_HAZIR/romfs'
    lines=[]
    total=0; blanks=0; token_bad=0; mismatch=0; allchars=set()
    lines.append('Heroes of Ruin Turkce Yama - Dogrulama Raporu')
    lines.append('='*48)
    for base in STRL:
        with (trans/f'{base}.csv').open(encoding='utf-8-sig',newline='') as f: cr=list(csv.DictReader(f))
        jr=json.loads((trans/f'{base}.json').read_text(encoding='utf-8'))['entries']
        if len(cr)!=len(jr): raise SystemExit(f'{base}: CSV/JSON sayi farki')
        for i,(a,b) in enumerate(zip(cr,jr)):
            if a.get('tr','')!=b.get('tr',''): mismatch+=1
            tr=a.get('tr',''); en=a.get('en','')
            if not tr: blanks+=1
            if Counter(protected_tokens(en))!=Counter(protected_tokens(tr)): token_bad+=1
            allchars.update(tr)
        built=parse_strl_file(rom/'_UK'/f'{base}.strl_')
        if len(built)!=len(cr): raise SystemExit(f'{base}: STRL sayi farki')
        text_bad=sum(1 for e,r in zip(built,cr) if e.text!=r['tr'])
        if text_bad: raise SystemExit(f'{base}: STRL metin farki {text_bad}')
        total+=len(cr)
        lines.append(f'{base}: {len(cr)} kayit - OK')

    font_packed=(root/'FONT/demo_font.bcfnt_').read_bytes()
    font_raw=_raw_font(font_packed)
    if blz_decompress(font_packed)!=font_raw: raise SystemExit('Font BLZ round-trip hatasi')
    cps=_cmap_codepoints(font_raw)
    nonascii=sorted(ord(c) for c in allchars if ord(c)>127)
    missing=[cp for cp in nonascii if cp not in cps]
    turk_missing=[ch for ch in TURKISH if ord(ch) not in cps]

    # Hazir klasorlerin ayni dosyalari tasidigini kontrol et.
    luma=root/'YAMA_HAZIR/Luma3DS_SD_KOKUNE_KOPYALA/luma/titles/0004000000074000/romfs'
    emu=root/'YAMA_HAZIR/Azahar_Citra_Mod_Klasorune_Kopyala/romfs'
    ready_diff=0
    for rel in [Path('_UK')/f'{b}.strl_' for b in STRL] + [Path('demo_font.bcfnt_'),Path('demo_font.bcfnt'),Path('UI/demo_font.bcfnt_'),Path('UI/demo_font.bcfnt')]:
        if sha(rom/rel)!=sha(luma/rel) or sha(rom/rel)!=sha(emu/rel): ready_diff+=1

    lines += [
        '',
        f'Toplam Turkce kayit: {total}',
        f'Bos TR satiri: {blanks}',
        f'CSV/JSON TR farki: {mismatch}',
        f'Protected-token uyusmazligi: {token_bad}',
        f'Font CMAP kod noktasi: {len(cps)}',
        f'Turkce glif eksigi: {"".join(turk_missing) if turk_missing else "yok"}',
        'Ceviride kullanilan ASCII-disi kod noktasi: ' + ' '.join(f'U+{x:04X}' for x in nonascii),
        f'Fontta cevirinin ASCII-disi karakter eksigi: {" ".join(f"U+{x:04X}" for x in missing) if missing else "yok"}',
        f'Hazir Luma/Azahar/romfs kopya farki: {ready_diff}',
        '',
        'SONUC: ' + ('BASARILI' if not any([blanks,mismatch,token_bad,missing,turk_missing,ready_diff]) else 'HATA'),
    ]
    text='\n'.join(lines)+'\n'
    print(text,end='')
    (root/'RAPORLAR/yama_dogrulama.txt').write_text(text,encoding='utf-8')
    if 'HATA' in lines[-1]: raise SystemExit(1)

if __name__=='__main__': main()
