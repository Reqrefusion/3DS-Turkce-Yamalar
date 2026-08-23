from pathlib import Path
import csv,json,re
ROOT=Path('/mnt/data/Layton_TR_Final_v8')
p=ROOT/'ceviri/layton_tr.csv'
with p.open(encoding='utf-8-sig',newline='') as f:
    rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)

M={
'açılisinda':'açılışında','görünusu':'görünüşü','görüsunuz':'görüşünüz','ihtiyaçı':'ihtiyacı','ihtiyaçım':'ihtiyacım',
'konuşmasina':'konuşmasına','sayısindan':'sayısından','sayısinin':'sayısının','sayısiyla':'sayısıyla','taşarımı':'tasarımı',
'yarısidir':'yarısıdır','yarısina':'yarısına','yarısinda':'yarısında','çalışmasinin':'çalışmasının','çokusu':'çöküşü',
'çözulusunu':'çözülüşünü','çıkisindan':'çıkışından','çıkisini':'çıkışını','çıkisinin':'çıkışının','çıkisiyla':'çıkışıyla',
'çıkmasin':'çıkmasın','çıkmasina':'çıkmasına','çıkolatali':'çikolatalı','üstalasilan':'ustalaşılan','üstalasirsiniz':'ustalaşırsınız',
'üstalasman':'ustalaşman','üstalik':'ustalık','üstalığına':'ustalığına','üstayi':'ustayı','şeyahat':'seyahat',
'şeyahatlerimizde':'seyahatlerimizde','şeyredebilirsin':'seyredebilirsin','şeyredebilirsiniz':'seyredebilirsiniz',
'şeyredersen':'seyredersen','şeyredilmek':'seyredilmek','Görüsu':'Görüşü','Üstalar':'Ustalar',
# suffix-chain misses reviewed against source
'arabuluculugum':'arabuluculuğum','kabartabilmisizdir':'kabartabilmişizdir','coraklikti':'çoraklıktı','mozzarellanin':'mozzarellanın',
'dioramasi':'dioraması','cirakini':'çırağını','aaletlerini':'aletlerini','etkilenmiyormuscasina':'etkilenmiyormuşçasına',
'onyargilarina':'önyargılarına','canimlarimdan':'canımlarımdan','yolmamissindir':'yolmamışsındır','yaniltmacali':'yanıltmacalı',
'buzdaginda':'buzdağında','stogunu':'stoğunu','sualti':'sualtı','coreksizdi':'çöreksizdi','kivranabilirsin':'kıvranabilirsin',
'breakdanscilar':'breakdansçılar','fethedebilirmisim':'fethedebilirmişim','kipirdatisi':'kıpırdatışı','karnini':'karnını','eslik':'eşlik',
'eszamanli':'eşzamanlı','çıkisiyla':'çıkışıyla',
}
# Exact phrase fixes where control tags split a Turkish word or where source gives natural phrasing.
PH=[
('</C>larinda','</C>larında'),
('<CR>üstalasilan\nhareket</C>','<CR>ustalaşılan\nhareket</C>'),
('yercekiminden','yer çekiminden'),
('takma dışını','takma dişini'),
('hayati para','hayatı para'),
('ortaya çıkisiyla','ortaya çıkışıyla'),
('şeyredebilirsin','seyredebilirsin'),
('açıl bir güvenlik','acil bir güvenlik'),
('ayak takimi','ayak takımı'),
]

def sub_exact(t,a,b):
    return re.sub(r'(?<![\w])'+re.escape(a)+r'(?![\w])',b,t)

changes=[]
for r in rows:
    b=r['translation']; t=b; why=[]
    for a,z in PH:
        if a in t:
            t=t.replace(a,z); why.append(f'{a} → {z}')
    for a,z in M.items():
        nt=sub_exact(t,a,z)
        if nt!=t:
            t=nt; why.append(f'{a} → {z}')
    # row-specific wording polish from source
    key=(r['file'],r['id'])
    if key==('40/40_001200.xs','text000063'):
        # false tooth + life + prejudice row
        t=t.replace("Waltham'in\nhayati", "Waltham'ın\nhayatı").replace('takma dışını','takma dişini').replace('onyargilarina','önyargılarına')
    if key==('03/03_030482.xs','text000079'):
        t=t.replace('ortaya çıkışıyla\neşzamanlı','ortaya çıkışıyla\neş zamanlı')
    if key==('82/82_004000.xs','text000006'):
        # Natural Turkish for mastered action; same CR tags retained.
        t=t.replace('<CR>ustalaşılan\nhareket</C>','<CR>öğrenilmiş\nhareket</C>')
    if t!=b:
        r['translation']=t; changes.append({'file':r['file'],'id':r['id'],'reason':'Kaynak karşılaştırmalı ek/imla düzeltmesi: '+' | '.join(why),'before':b,'after':t,'source':r['original']})

for out in [p,ROOT/'ceviri/CEVIRI_KOLAY.csv']:
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (ROOT/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8') as f:
    for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
rep=ROOT/'raporlar/V8_DERIN_EK_IMLA_POLISH.csv'
with rep.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','id','reason','before','after','source']);w.writeheader();w.writerows(changes)
print('changed',len(changes),rep)
