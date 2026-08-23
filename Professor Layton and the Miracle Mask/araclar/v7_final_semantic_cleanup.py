import csv,json,re,os
from pathlib import Path
root=Path('/mnt/data/Layton_TR_Final_v7')
csvp=root/'ceviri/layton_tr.csv'
jsonlp=root/'ceviri/layton_tr.jsonl'
easy=root/'ceviri/CEVIRI_KOLAY.csv'
report=root/'raporlar/V7_FINAL_SEMANTIK_TEMIZLIK.csv'

with csvp.open(encoding='utf-8-sig',newline='') as f:
    rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)

# Exact word replacements that are unambiguous in the current Turkish text.
word_map={
 'gecelim':'geçelim','hesabi':'hesabı','katildi':'katıldı','bakisi':'bakışı','adimi':'adımı',
 'buyulu':'büyülü','Buyulu':'Büyülü','gurultusunun':'gürültüsünün',
 'secim':'seçim','Secim':'Seçim','secin':'seçin','secici':'seçici','secimin':'seçimin',
 'isletmelerin':'işletmelerin','isletmelerine':'işletmelerine','isletmelerinin':'işletmelerinin','isletmelerini':'işletmelerini',
 'pesindesin':'peşindesin','sahin':'şahin','Sahin':'Şahin','hayatinin':'hayatının','adinin':'adının','kitabin':'kitabın','hanin':'hanın',
 'inis':'iniş','issiz':'ıssız','los':'loş','hakli':'haklı','calindi':'çalındı','calinmis':'çalınmış',
 'Katiliyorum':'Katılıyorum','katiliyorum':'katılıyorum','islecleri':'işleçleri','islerine':'işlerine',
 'kullanin':'kullanın','kirmis':'kırmış','konuşmasini':'konuşmasını','kosa':'koşa','golfcu':'golfçu',
 'kraliceniz':'kraliçeniz','ilestirdiği':'iliştirdiği','ilistirdiği':'iliştirdiği',
 'soyluyordu':'söylüyordu','soyluyorum':'söylüyorum','soyle':'şöyle',
}
# exact word with punctuation safe
word_re=re.compile(r'(?<![\wÇĞİÖŞÜçğıöşüÂÎÛâîû])('+'|'.join(map(re.escape, sorted(word_map,key=len,reverse=True)))+r')(?![\wÇĞİÖŞÜçğıöşüÂÎÛâîû])')

def general(s):
    return word_re.sub(lambda m: word_map[m.group(1)], s)

# row-specific replacements where ASCII homographs or morphology make a blind rule unsafe.
R={}
def add(file,id,*pairs): R.setdefault((file,id),[]).extend(pairs)

# semantic / dialogue fixes
add('02/02_020100.xs','text000010',('yardım işte','yardım iste'))
add('05/05_050420.xs','text000044',('eski olum kapanının her karisini','eski ölüm kapanının her karışını'))
add('40/40_001200.xs','text000101',('bahis konuşu','bahis konusu'))
add('17/17_170010.xs','text000002',("{''}Masked Gentleman{''}","{''}Maskeli Beyefendi{''}"))
add('05/05_050585.xs','text000001',("{''}lost{''}","{''}kayıp{''}"))
add('02/02_020140.xs','text000006',("{''}Doğ{''} Amca","{''}Köpek{''} Amca"))
add('01/01_010210.xs','text000002',('cehremi','çehremi'),(' görünür kil',' görünür kıl'))
add('01/01_010230.xs','text000017',('Şeyahatlerinizde','Seyahatlerinizde'))
add('03/03_030220.xs','text000032',("yasadiğin","yaşadığın"))
add('03/03_030460.xs','text000001',('Başka isiniz','Başka işiniz'))
add('06/06_068080.xs','text000008',('ne isiniz','ne işiniz'))
add('30/30_001050.xs','text000009',('Ne isiniz','Ne işiniz'))
add('03/03_030120.xs','text000014',('isinize','işinize'))
add('05/05_050570.xs','text000004',('tamir islerine','tamir işlerine'))
add('40/40_001000.xs','text000083',('mali islerine','mali işlerine'),('detayları doktu','detayları döktü'))
add('40/40_001200.xs','text000043',('başkalarının islerine','başkalarının işlerine'))
add('40/40_001200.xs','text000037',('babasının\nisini','babasının\nişini'),('babasının isini','babasının işini'))
add('03/03_030480.xs','text000032',('numarasının ise\nyaraması','numarasının işe\nyaraması'),('numarasının ise yaraması','numarasının işe yaraması'))
add('04/04_040130.xs','text000004',('harita olarak ise\nyarayacak','harita olarak işe\nyarayacak'),('harita olarak ise yarayacak','harita olarak işe yarayacak'))
add('40/40_001000.xs','text000077',('bize ise\nyarar','bize işe\nyarar'),('bize ise yarar','bize işe yarar'))
add('50/50_000130.xs','text000007',('sıra söyle olur','sıra şöyle olur'))

# village / town homographs
for k in [('18/18_180150.xs','text000008'),('19/19_190060.xs','text000003')]: add(*k,('koyu','köyü'))
add('20/20_200260.xs','text000004',('Sis koyu','Sis köyü'))
add('02/02_020070.xs','text000008',('bu koyu','bu köyü'),('diplomasi','diploması'))

# carrot endings where stem-final consonant must be ç only without vowel suffix
for k in [('82/82_001000.xs','text000011'),('82/82_001000.xs','text000016'),('82/82_001000.xs','text000150')]: add(*k,('havuc','havuç'))
add('20/20_200200.xs','text000017',('bir sir','bir sır'),('havuclaridir','havuçlarıdır'))
# other secret/glaze rows
for k in [('04/04_040130.xs','text000018'),('05/05_050440.xs','text000001'),('06/06_062090.xs','text000011')]: add(*k,('sir','sır'))
add('81/81_000100.xs','text000073',('Misket Limonlu Sir','Misket Limonlu Sır'))

# katı / katıl / katır homographs
for k in [('02/02_020280.xs','text000004'),('07/07_070220.xs','text000013'),('30/30_008030.xs','text000010'),('40/40_001100.xs','text000043'),('40/40_001500.xs','text000035'),('80/80_000200.xs','text000031')]: add(*k,('kati','katı'))
add('06/06_062150.xs','text000009',('katim','katım'))
add('06/06_068070.xs','text000007',('katin','katın'))
add('07/07_070590.xs','text000007',('katil','katıl'))
add('20/20_200200.xs','text000036',('katirsiniz','katırsınız'))

# karı / kâr / karın / karış homographs
add('05/05_050590.xs','text000023',('kari','kârı'))
for k in [('07/07_071310.xs','text000011'),('07/07_071315.xs','text000005')]: add(*k,('kari','karı'))
for k in [('01/01_010110.xs','text000004'),('03/03_030650.xs','text000030'),('03/03_030650.xs','text000034'),('82/82_000009.xs','text000032')]: add(*k,('karin','karın'))
add('03/03_030090.xs','text000007',('Karisi','Karısı'))
add('05/05_050380.xs','text000026',('karisi','karısı'))
add('05/05_050420.xs','text000044',('karisini','karışını'))
add('05/05_050810.xs','text000022',('karisini','karısını'))
add('07/07_070510.xs','text000010',('Karimin','Karımın'))
add('07/07_070510.xs','text000011',('Karimi','Karımı'))
add('03/03_030100.xs','text000007',('karisin','karışın'))
add('03/03_030484.xs','text000035',('karisan','karışan'))
add('82/82_000009.xs','text000019',('Karin','Karın'))

# sık/şık
add('30/30_008020.xs','text000008',('siklik','şıklık'))
add('81/81_000100.xs','text000177',('siklik','şıklık'),('taşarımının','tasarımının'))
add('30/30_009002.xs','text000010',('sikis','sıkış'))
add('82/82_000007.xs','text000002',('sikisir','sıkışır'))
add('82/82_003040.xs','text000001',('sikkin','sıkkın'),('cani','canı'))

# öl-/oluş- semantic rows
add('19/19_190540.xs','text000001',('olusu','oluşu'))
add('40/40_002000.xs','text000033',('olusu','oluşu'),('barisi','barışı'))
add('05/05_050801.xs','text000026',(' olu ',' ölü '),(' olu.',' ölü.'))

# puzzle/UI specific morphology
add('06/06_060260.xs','text000006',('Kos! Kos!','Koş! Koş!'))
add('50/50_000112.xs','text000002',('Kos','Koş'))
add('07/07_071040.xs','text000008',('üstalasmadan','ustalaşmadan'))
add('07/07_071280.xs','text000005',('sus','süs'))
add('07/07_071232.xs','text000013',('kus','kuş'))
add('81/81_000100.xs','text000196',('Kisin','Kışın'),('mahkum','mahkûm'))

# Ace of Diamonds puzzle
for tid in ['text000002','text000008']:
    add('50/50_000033.xs',tid,('Karo Asi','Karo Ası'))
add('50/50_000033.xs','text000003',("Karo Ası'dir","Karo Ası'dır"))
add('50/50_000033.xs','text000006',('karo asi','karo ası'),('bir sus','bir süs'))

# image/pattern words that affect puzzle clue reading
for file,id,pairs in [
 ('50/50_000091.xs','text000002',[('Onluk','Önlük'),('onluk','önlük')]),
]:
    add(file,id,*pairs)

changes=[]
for r in rows:
    before=r['translation']
    s=general(before)
    for a,b in R.get((r['file'],r['id']),[]):
        s=s.replace(a,b)
    # exact terminal havuc -> havuç (without vowel suffix)
    s=re.sub(r'(?<!\w)havuc(?!\w)', 'havuç', s)
    # buyuluyor etc unambiguous enchant/mesmerise forms
    s=re.sub(r'(?<!\w)buyuluyor(?!\w)','büyülüyor',s)
    if s!=before:
        r['translation']=s
        changes.append((r['file'],r['id'],before,s))

with csvp.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
with jsonlp.open('w',encoding='utf-8') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
# easy format retain all known columns, if existing derive by key and replace translation-ish field
if easy.exists():
    with easy.open(encoding='utf-8-sig',newline='') as f:
        erd=csv.DictReader(f); efields=erd.fieldnames; erows=list(erd)
    d={(r['file'],r['id']):r['translation'] for r in rows}
    transcol=next((c for c in efields if c.lower() in ('translation','ceviri','çeviri','turkce','türkçe')),None)
    if transcol:
        for e in erows:
            k=(e.get('file',''),e.get('id',''))
            if k in d: e[transcol]=d[k]
        with easy.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=efields);w.writeheader();w.writerows(erows)
with report.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['file','id','once','sonra']);w.writerows(changes)
print('changed',len(changes))
print('report',report)
