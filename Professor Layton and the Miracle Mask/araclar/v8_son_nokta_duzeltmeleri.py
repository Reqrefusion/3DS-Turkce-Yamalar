from pathlib import Path
import csv,json,re
root=Path('/mnt/data/Layton_TR_Final_v8')
csvp=root/'ceviri/layton_tr.csv'
rows=list(csv.DictReader(csvp.open(encoding='utf-8-sig',newline='')))
changes=[]

def change(r,new,reason):
    old=r['translation']
    if old!=new:
        r['translation']=new
        changes.append({'file':r['file'],'id':r['id'],'reason':reason,'before':old,'after':new,'source':r['original']})

for r in rows:
    t=r['translation']
    n=t
    reasons=[]
    # Safe, source-confirmed textual fixes.
    repls=[
        ('söz konuşu','söz konusu','“söz konusu” ifadesindeki yazım hatası düzeltildi.'),
        ('Mucize Beyefendi','Maskeli Beyefendi','Masked Gentleman özel adı resmi/bağlamsal karşılığıyla tutarlılaştırıldı.'),
        ("Londra'nin","Londra'nın",'Türkçe iyelik eki düzeltildi.'),
        ('Isletmenize','İşletmenize','Türkçe İ/ş karakterleri düzeltildi.'),
        ('karmasa','karmaşa','Türkçe ş karakteri düzeltildi.'),
        ('Buradaki mudur benim.','Buradaki müdür benim.','“manager” anlamındaki müdür sözcüğü düzeltildi.'),
    ]
    for a,b,why in repls:
        if a in n:
            n=n.replace(a,b); reasons.append(why)
    # kalip is always the -ip gerund of kalmak in remaining hits.
    if re.search(r'\bkalip\b',n):
        n=re.sub(r'\bkalip\b','kalıp',n); reasons.append('“kalıp” zarf-fiilindeki Türkçe ı düzeltildi.')
    if re.search(r'\bYari\b',n):
        n=re.sub(r'\bYari\b','Yarı',n); reasons.append('“Yarı” sözcüğündeki Türkçe ı düzeltildi.')
    # effort forms; do not touch correct “cabası”.
    effort_patterns=[(r'\bcaba\b','çaba'),(r'\bcabala\b','çabala'),(r'\bcaban\b','çaban')]
    for pat,b in effort_patterns:
        if re.search(pat,n):
            n=re.sub(pat,b,n); reasons.append('“çaba” kökü kaynak bağlamındaki effort anlamına göre düzeltildi.')
    # row-specific natural rewrite preserving the full source meaning.
    if r['file']=='01/01_010335.xs' and r['id']=='text000014':
        n='<T>Peki. Şu sarkık kulaklı yaratıklardan\nbirini al da sahne sanatlarında ustalaşmasını\nsağla. Bunu başarırsan ikisi de kalabilir.'
        reasons.append('“get it to master the dramatic arts” doğal ve eksiksiz Türkçeyle yeniden çevrildi.')
    if n!=t:
        change(r,n,' '.join(dict.fromkeys(reasons)))

fields=['file','id','offset','original','translation']
for out in [root/'ceviri/layton_tr.csv',root/'ceviri/CEVIRI_KOLAY.csv']:
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
with (root/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8',newline='\n') as f:
    for r in rows:
        f.write(json.dumps(r,ensure_ascii=False)+'\n')
rp=root/'raporlar/V8_SON_NOKTA_DUZELTMELERI.csv'
with rp.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','id','reason','before','after','source']); w.writeheader(); w.writerows(changes)
print('changes',len(changes),'report',rp)
