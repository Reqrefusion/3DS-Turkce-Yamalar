from pathlib import Path
import csv, json, re

ROOT=Path('/mnt/data/Layton_TR_Final_v8')
CSV=ROOT/'ceviri/layton_tr.csv'
JSONL=ROOT/'ceviri/layton_tr.jsonl'
EASY=ROOT/'ceviri/CEVIRI_KOLAY.csv'
REPORT=ROOT/'raporlar/V8_SON_IMLA_SEMANTIK_POLISH.csv'

# Only source/context-reviewed forms. Exact-token replacements only.
M={
'yikilisini':'yıkılışını','uzmustu':'üzmüştü','uyarisinda':'uyarısında','ulasin':'ulaşın',
'tuttugumu':'tuttuğumu','tutmus':'tutmuş','suratsiz':'suratsız','sukur':'şükür',
'sovumu':'şovumu','sovu':'şovu','sokusturmus':'sokuşturmuş','sivasan':'sıvasan','sirla':'sırla',
'seranin':'seranın','seffaflasan':'şeffaflaşan','satirlara':'satırlara','sasirmisimdir':'şaşırmışımdır',
'sasirdi':'şaşırdı','sapli':'saplı','sapkin':'sapkın','sallandim':'sallandım','saldirisini':'saldırısını',
'saklayalim':'saklayalım','saklanir':'saklanır','saklandi':'saklandı','saklamistir':'saklamıştır',
'saklamayi':'saklamayı','saklamasini':'saklamasını','sakiz':'sakız','sakinca':'sakınca','sacliydi':'saçlıydı',
'sacina':'saçına','sacin':'saçın','saci':'saçı','porsumus':'pörsümüş','ovustur':'ovuştur','oturmus':'oturmuş',
'operator':'operatör','oluyormus':'oluyormuş','olasin':'olasın','nisanlanmis':'nişanlanmış','masayi':'masayı',
'masasina':'masasına','masali':'masalı','kusurlarinin':'kusurlarının','kusurlarini':'kusurlarını',
'kustahca':'küstahça','kurmussun':'kurmuşsun','kullanmasini':'kullanmasını','kopegine':'köpeğine',
'kopegimi':'köpeğimi','kokmus':'kokmuş','kocasina':'kocasına','kocasi':'kocası','kocanindaki':'koçanındaki',
'kirikligiydi':'kırıklığıydı','kirikligini':'kırıklığını','kesmis':'kesmiş','kazancimi':'kazancımı',
'kazancim':'kazancım','kaslarimi':'kaslarımı','kaslari':'kasları','kasir':'kaşır','kasigi':'kaşığı',
'kasanin':'kasanın','kalmasin':'kalmasın','kalcalarimi':'kalçalarımı','kacinci':'kaçıncı','islemis':'işlemiş',
'isitmaya':'ısıtmaya','isitiriz':'işitiriz','isitirim':'ısıtırım','isit':'ısıt','haksizligin':'haksızlığın',
'gulse':'gülse','giymisti':'giymişti','girmistir':'girmiştir','fistik':'fıstık','fasli':'faslı','esigine':'eşiğine',
'durmustur':'durmuştur','durmasi':'durması','durdugumuz':'durduğumuz','davranisina':'davranışına',
'davranisi':'davranışı','colu':'çölü','civik':'cıvık','citin':'çitin','ciliz':'cılız','cekilisin':'çekilişin',
'cayiri':'çayırı','catisi':'çatısı','canlinin':'canlının','canlilar':'canlılar','canlarim':'canlarım',
'canlaniyor':'canlanıyor','canlanisini':'canlanışını','canlandirmaya':'canlandırmaya','canlandi':'canlandı',
'cabayi':'çabayı','cabami':'çabamı','cabalamaliyim':'çabalamalıyım','bulmasini':'bulmasını','basti':'bastı',
'basmistik':'basmıştık','baski':'baskı','basiniz':'başınız','basindayken':'başındayken','basindadir':'başındadır',
'bahsetmistin':'bahsetmiştin','ayisi':'ayısı','atmasini':'atmasını','atmasi':'atması','astiktan':'aştıktan',
'asmislar':'asmışlar','asmayi':'asmayı','asmaliyiz':'asmalıyız','askini':'aşkını','askin':'aşkın','asinmis':'aşınmış',
'asarim':'asarım','asamayacagimiz':'aşamayacağımız','arkadasiniz':'arkadaşınız','arizali':'arızalı',
'arabasinin':'arabasının','anlatisini':'anlatışını','anlamasini':'anlamasını','amacindan':'amacından','album':'albüm',
'akisina':'akışına','aciyorlar':'açıyorlar','aciyla':'açıyla','acisini':'açısını','acisinda':'acısında',
'acinin':'acının','acinasi':'acınası','acima':'acıma','Venus':'Venüs','Sarkisi':'Şarkısı','Komsulari':'Komşuları',
'Kacisin':'Kaçışın','Canlilik':'Canlılık','Canlari':'Canları','Bekci':'Bekçi','Bahsettigimiz':'Bahsettiğimiz',
'Askimi':'Aşkımı','Amacimiz':'Amacımız','Ahsabin':'Ahşabın','Acini':'Acını','Acinacak':'Acınacak',
# Additional reviewed forms found in final audit
'isletmenize':'işletmenize','isleten':'işleten','isletmenin':'işletmenin','isletmeci':'işletmeci','isletmecisi':'işletmecisi',
'şeyirci':'seyirci','şeyirciler':'seyirciler','şeyircinin':'seyircinin','günesin':'güneşin','Günesin':'Güneşin',
'doğusundadir':'doğusundadır','hakkin':'hakkın','yetis':'yetiş','uzdu':'üzdü','gececegimizse':'geçeceğimizse',
'tedit':'tehdit','unludur':'ünlüdür','kazanilabildigiydi':'kazanılabildiğiydi','görüsundeydi':'görüşündeydi',
'islediğini':'işlediğini',"Angela'dir":"Angela'dır","Dünya'nin":"Dünya'nın",'görüs':'görüş','tabagimizdir':'tabağımızdır',
'yakalayamayacagimizdan':'yakalayamayacağımızdan','Isitici':'Isıtıcı',
}

# phrase-level reviewed fixes (safe and unambiguous in current project)
PHRASES={
'Sesini kis':'Sesini kıs',
'bir iyi yani':'bir iyi yanı',
'İnkar etme':'İnkâr etme',
'yıldız şeyri':'yıldız seyri',
'kis geldi':'kış geldi',
'Soğuk bir kis gününde':'Soğuk bir kış gününde',
}

# Source-reviewed semantic/garbled rows: replace complete translation deliberately.
ROW={
('20/20_209030.xs','text000007'):'<T>Görüşülecek pek çok tanık var.\nOtel resepsiyonuna sormayı dener misin?',
('20/20_209030.xs','text000005'):'<T><M3/2/1>Ve bunlara doyamıyorum!\nSıradan bir sihirbazın çok çok\nüstünde. Ay ile kaşığı kıyaslamak gibi!',
}

# One context-reviewed phrase where exact token alone could be ambiguous.
CONTEXT=[
(('82/82_000009.xs','text000009'),'Sonra kis geldi','Sonra kış geldi'),
(('82/82_000010.xs','text000010'),'Sonra kis geldi','Sonra kış geldi'),
(('82/82_000010.xs','text000012'),'Soğuk bir kis gününde','Soğuk bir kış gününde'),
]

def exact_sub(text, old, new):
    return re.sub(r'(?<![\w])'+re.escape(old)+r'(?![\w])', new, text)

with CSV.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.DictReader(f); fields=reader.fieldnames; rows=list(reader)
changes=[]
for r in rows:
    key=(r['file'],r['id']); before=r['translation']; t=before; reasons=[]
    if key in ROW:
        t=ROW[key]
        reasons.append('Kaynak metne göre bozuk/eksik anlam yeniden çevrildi')
    else:
        for a,b in PHRASES.items():
            nt=t.replace(a,b)
            if nt!=t:
                t=nt; reasons.append(f'İmla/ifade: {a} → {b}')
        for a,b in M.items():
            nt=exact_sub(t,a,b)
            if nt!=t:
                t=nt; reasons.append(f'Türkçe imla/karakter: {a} → {b}')
        for k,a,b in CONTEXT:
            if key==k and a in t:
                t=t.replace(a,b); reasons.append(f'Bağlama göre: {a} → {b}')
    if t!=before:
        r['translation']=t
        changes.append({'file':r['file'],'id':r['id'],'reason':' | '.join(reasons),'before':before,'after':t,'source':r['original']})

with CSV.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
with JSONL.open('w',encoding='utf-8') as f:
    for r in rows: f.write(json.dumps(r,ensure_ascii=False)+'\n')
with EASY.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
REPORT.parent.mkdir(parents=True,exist_ok=True)
with REPORT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','id','reason','before','after','source']); w.writeheader(); w.writerows(changes)
print('changed',len(changes))
print('report',REPORT)
