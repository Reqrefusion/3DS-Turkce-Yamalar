from __future__ import annotations
import csv,re,json,struct,zipfile
from difflib import SequenceMatcher
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LANGS=['EU_English','US_English','EU_French','US_French','EU_German','EU_Italian','EU_Spanish','US_Spanish','JP_Japanese','KR_Korean']
LATIN=LANGS[:8]
CTRL_RE=re.compile(r"\{\{CTRL\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]{4}\|[0-9A-Fa-f]*\}\}")
PH_RE=re.compile(r'<[^>\n]+>')
TOKEN_RE=re.compile(r"\{\{(?:CTRL|U16)\|.*?\}\}")

def cmap_widths(data):
    endian='<' if data[4:6]==b'\xff\xfe' else '>';cmap={};p=0
    while True:
        off=data.find(b'CMAP',p)
        if off<0:break
        p=off+4
        try:
            size=struct.unpack_from(endian+'I',data,off+4)[0];begin,end,method,_r,_n=struct.unpack_from(endian+'HHHHI',data,off+8);q=off+20
            if size<20 or off+size>len(data):continue
            if method==0:
                idx0=struct.unpack_from(endian+'H',data,q)[0]
                for cp in range(begin,end+1):cmap[cp]=idx0+cp-begin
            elif method==1:
                vals=struct.unpack_from(endian+f'{end-begin+1}H',data,q)
                for cp,idx in zip(range(begin,end+1),vals):
                    if idx!=0xffff:cmap[cp]=idx
            elif method==2:
                cnt=struct.unpack_from(endian+'H',data,q)[0];q+=2
                for _ in range(cnt):cp,idx=struct.unpack_from(endian+'HH',data,q);q+=4;cmap[cp]=idx
        except:pass
    idxw={};p=0
    while True:
        off=data.find(b'CWDH',p)
        if off<0:break
        p=off+4
        try:
            size=struct.unpack_from(endian+'I',data,off+4)[0];start,end=struct.unpack_from(endian+'HH',data,off+8);q=off+16
            for idx in range(start,end+1):
                if q+3>off+size:break
                idxw[idx]=data[q+2];q+=3
        except:pass
    return {cp:idxw.get(idx,0) for cp,idx in cmap.items()}

def clean(s):return TOKEN_RE.sub('',s or '')
def width(s,adv):return sum(adv.get(ord(ch),0) for ch in clean(s))
def mw(s,adv):return max([width(x,adv) for x in ((s or '').splitlines() or [''])] or [0])
def group(label):return re.sub(r'\d+','#',label)
def norm(s):
    s=clean(s).lower();s=PH_RE.sub('<var>',s);s=re.sub(r'[^a-z0-9<>]+',' ',s);return ' '.join(s.split())

def main():
    cp=ROOT/'data'/'Kirby_TR_translated.csv';zp=ROOT/'input'/'source.zip'
    with open(cp,encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    with zipfile.ZipFile(zp) as z:
        fs=[cmap_widths(z.read(n)) for n in ('frame/font/GameFont1.bffnt','frame/font/GameFont2.bffnt')]
    cps=set().union(*(set(x) for x in fs));adv={c:max(x.get(c,0) for x in fs) for c in cps}
    caps={};linecaps={}
    for r in rows:
        g=group(r['Label'])
        for l in LATIN:
            if r[l].strip():caps[g]=max(caps.get(g,0),mw(r[l],adv));linecaps[g]=max(linecaps.get(g,0),len(r[l].splitlines()) or 1)
    layout=[]
    for r in rows:
        if not r['Turkish'].strip():continue
        g=group(r['Label']);cap=caps.get(g,0);tw=mw(r['Turkish'],adv)
        layout.append({'Label':r['Label'],'Group':g,'TurkishMaxPx':tw,'ObservedSourceGroupMaxPx':cap,'Ratio':round(tw/cap,4) if cap else 0,'TurkishLines':len(r['Turkish'].splitlines()) or 1,'ObservedSourceGroupMaxLines':linecaps.get(g,0)})
    layout.sort(key=lambda x:(x['Ratio'],x['TurkishMaxPx']),reverse=True)
    with open(ROOT/'reports'/'layout_pixel_audit.csv','w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(layout[0].keys()));w.writeheader();w.writerows(layout)
    presence=[];ctrl=[];ph=[]
    for r in rows:
        pres=[l for l in LANGS if r[l].strip()];absent=[l for l in LANGS if not r[l].strip()]
        if pres and absent:presence.append((r['Label'],pres,absent,bool(r['EU_English'].strip()),r['Turkish']))
        cv={l:tuple(CTRL_RE.findall(r[l])) for l in LANGS}
        if len(set(cv.values()))>1:ctrl.append((r['Label'],cv))
        pv={l:tuple(PH_RE.findall(r[l])) for l in LANGS}
        if len(set(pv.values()))>1:ph.append((r['Label'],pv,r['Turkish']))
    euus=[]
    for r in rows:
        a,b=norm(r['EU_English']),norm(r['US_English'])
        if a!=b:
            sim=SequenceMatcher(None,a,b).ratio() if (a or b) else 1
            euus.append((sim,r['Label'],r['EU_English'],r['US_English'],r['Turkish']))
    euus.sort()
    lines=[]
    lines += ['KIRBY TÜRKÇE - 10 DİL ÇAPRAZ DENETİMİ','='*48,'']
    lines += [f'Toplam etiket: {len(rows)}',f'EU/US İngilizce birebir farklı satır: {len(euus)}',f'Locale boş/dolu yapısı farklı satır: {len(presence)}',f'Locale kontrol-kodu dizisi farklı satır: {len(ctrl)}',f'Locale placeholder sırası/varlığı farklı satır: {len(ph)}','']
    lines += ['KARAR POLİTİKASI','- Hedef ROM Avrupa (E) olduğu için zamanlanmış metin yapısında EU_English kaynak alınır.','- Diğer 9 dil anlam, terim ve belirsizlik kontrolü için kullanılır.','- EU_English boş olan bir zamanlanmış yuvaya başka locale metni taşınmaz.','- Tüm 10 dil klasörüne aynı kanonik Türkçe set enjekte edilir; böylece sistem dili değişse de Türkçe kalır.','- Stilize HOME Menu bannerı yeniden çizilmez; banner.bin byte-byte orijinal tutulur.','']
    lines += ['BOŞ/DOLU LOCALE FARKLARI']
    for label,pres,absent,eu,tr in presence:
        lines.append(f'- {label}: EU_English={"dolu" if eu else "boş"}; dolu={", ".join(pres)}; boş={", ".join(absent)}; TR={tr!r}')
    lines += ['','KONTROL KODU FARKLARI']
    for label,cv in ctrl:
        lines.append(f'- {label}')
        for l,v in cv.items():
            if v:lines.append(f'  {l}: {list(v)}')
    lines += ['','PLACEHOLDER FARKLARI']
    for label,pv,tr in ph:
        lines.append(f'- {label}: TR={tr!r}')
        for l,v in pv.items():
            if v:lines.append(f'  {l}: {list(v)}')
    lines += ['','EU/US ANLAMI EN ÇOK AYRILAN ÖRNEKLER (ilk 40)']
    for sim,label,a,b,tr in euus[:40]:
        lines += [f'- {label} (benzerlik {sim:.2f})',f'  EU: {a!r}',f'  US: {b!r}',f'  TR: {tr!r}']
    lines += ['','PİKSEL GENİŞLİĞİ','- GameFont1 ve GameFont2 CWDH advance değerlerinin karakter başına büyüğü kullanıldı.','- Her etiket ailesi için 8 Latin-kaynak locale içinde gözlenen en geniş satır kapasite referansı kabul edildi.',f'- >%5 kapasite veya satır sayısı uyarısı: {sum(x["Ratio"]>1.05 or (x["ObservedSourceGroupMaxLines"] and x["TurkishLines"]>x["ObservedSourceGroupMaxLines"]) for x in layout)}',f'- En yüksek oran: {layout[0]["Ratio"] if layout else 0:.4f}','', 'Kapasiteye en yakın 30 Türkçe satır:']
    for x in layout[:30]:lines.append(f'- {x["Label"]}: {x["TurkishMaxPx"]}/{x["ObservedSourceGroupMaxPx"]} px ({x["Ratio"]:.3f}), satır {x["TurkishLines"]}/{x["ObservedSourceGroupMaxLines"]}')
    (ROOT/'reports'/'cross_language_audit_v2.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'eu_us_differences':len(euus),'presence_variants':len(presence),'control_variants':len(ctrl),'placeholder_variants':len(ph),'layout_warnings':sum(x['Ratio']>1.05 or (x['ObservedSourceGroupMaxLines'] and x['TurkishLines']>x['ObservedSourceGroupMaxLines']) for x in layout),'max_layout_ratio':layout[0]['Ratio'] if layout else 0},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
