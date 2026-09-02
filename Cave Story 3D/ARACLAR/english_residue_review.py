#!/usr/bin/env python3
"""english_residue_scanner çıktısını gözden geçirilebilir sınıflara ayırır.
Amaç, birebir kalan İngilizce satırlar içinde gerçekten çevrilmesi gereken cümle/UI
kalıp kalmadığını ayırmaktır. Özel adları, seslenmeleri, ünlemleri ve dahili etiketleri
çeviri hatası saymaz.
"""
from pathlib import Path
import argparse,csv,re
NAMES={
'Quote','Quote!!','Curly Brace','Sue','Kazuma','Kazuma.','Kazuma!','Kazuma: SUUUUE!','Kazuma: Sue?','Sue...','Sue?','...Sue?','Toroko','Toroko...','Toroko!!!',
'Balrog','Balrog.','MISERY!!','Misery','Misery!','Misery.','Itoh','Itoh?','Ma Pignon','King','Hajime','Kakeru','Mick','Nene','Shinobu',
'Booster v0.8','Booster v2.0','NEMESIS','Anatupone','Date Fuyuhiko','Halder','Miakido','Cthulhu','Malco',
'- Kazuma','Sue: Kazuma','Curly Brace.','...K... King...?'
}
INTERNAL={'focus','cemet','jenka','yrotS evaC','"""yrotS evaC""."'}
# Kısa ses/ünlem ifadeleri. Harf tekrarı, sadece ünlem/noktalama veya yaygın kısa ünlemler.
SHORT_UTTER={
'Hey!','Hey.','HEY!!','Heh.','Heh...','Heh heh.','Heh heh...','Hmm?','Hmm...','Ooh!','Ooooh...','Oow...',
'Aah!','Aaahhh!!!','Aaaaahhhh!','Uuuh.','Uuh...','Uuhh...','UUGH!','Nyaa!','Wan...','Nnghh...',
'BWAAAAH!!','WUUUUUUUH!!','NNNNgg!!!','GRRRRAWWR!!!','GRRRRAWWR...','Ooohh...','AAARGH!','Mmm...gulp!',
'ZZZzzz...','ZZZzzz...zzz...','zzz...','Guuh...','Uhh...'
}

def classify(file,text):
    if file=='credit.sjs': return 'KREDİ/ÖZEL_AD'
    if file=='head.sjs' and ('XX: head.tsc' in text or text.startswith('4000:')): return 'DAHİLİ_ETİKET'
    if text in NAMES: return 'ÖZEL_AD'
    if text in INTERNAL or text.strip() in {'"yrotS evaC".','"yrotS evaC".'} or (file=='stage/0.sjs'): return 'DAHİLİ_ETİKET'
    if text in SHORT_UTTER: return 'ÜNLEM/SES'
    if re.fullmatch(r'[A-Za-z]+(?:[.!?]+)?',text) and len(text)<=12 and any(c*3 in text.lower() for c in 'aeiougrwznh'): return 'ÜNLEM/SES'
    # Statue / time-trial character names are proper names.
    if file.endswith('statue.sjs') or file.endswith('tt_statue.sjs'): return 'ÖZEL_AD'
    return 'İNCELE'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('-o','--output',default='english_residue_review.tsv'); a=ap.parse_args()
    rows=[]; review=0; counts={}
    with open(a.input,encoding='utf-8',newline='') as f:
        rd=csv.DictReader(f,delimiter='\t')
        for r in rd:
            file=r['dosya']; text=r['orijinalle_ayni_kalan_metin']; c=classify(file,text)
            counts[c]=counts.get(c,0)+1; review += c=='İNCELE'; rows.append((file,text,c))
    with open(a.output,'w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(['dosya','metin','sinif']); w.writerows(rows)
    print('toplam:',len(rows),'inceleme_gereken:',review,'siniflar:',', '.join(f'{k}={v}' for k,v in sorted(counts.items())))
    if review:
        for r in rows:
            if r[2]=='İNCELE': print('İNCELE',r[0],repr(r[1]))
if __name__=='__main__': main()
