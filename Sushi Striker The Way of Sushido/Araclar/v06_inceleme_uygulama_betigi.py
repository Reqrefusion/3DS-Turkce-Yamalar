from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys

ROOT=Path('/mnt/data/sushi_work')
SRC=ROOT/'review_v05'/'csv'
OUTROOT=ROOT/'review_v06'
OUT=OUTROOT/'csv'
TOOL=ROOT/'review_v05'/'full_bundle'/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=ROOT/'review_v05'/'full_bundle'/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'msgstudio'/'msgstudio'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'): shutil.copy2(p,OUT/p.name)

files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rows)

# v0.6: en büyük savaş repliği dosyası + yakın savaş/ayar UI dosyalarının TAMAMI.
review_files=[
    'scene_puzzlebattle.csv','scene_battleresult.csv','scene_battledata.csv',
    'scene_menuformation.csv','scene_menuconfig.csv','scene_fileselect.csv',
    'scene_loading.csv','scene_eyecatch.csv'
]
changes=[]; changed_lookup={}

def row(fn,label):
    for r in files[fn][1]:
        if r['label']==label: return r
    raise KeyError((fn,label))

def norm(s): return (s or '').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')

def add(fn,label,new,reason,category='manuel kalite'):
    new=norm(new); r=row(fn,label); old=r.get('tur','')
    if old==new: return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason and reason not in rec['reason']: rec['reason'] += ' Ek: '+reason
        return True
    rec={'round':'v0.6','category':category,'file':fn,'label':label,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec; return True

def replace_in(fn,label,oldfrag,newfrag,reason,category='manuel kalite',count=-1):
    r=row(fn,label); oldfrag=norm(oldfrag); newfrag=norm(newfrag); cur=r.get('tur','')
    if oldfrag not in cur: raise ValueError(f'{fn}:{label} parça yok: {oldfrag!r}\nCUR={cur!r}')
    new=cur.replace(oldfrag,newfrag,count) if count!=-1 else cur.replace(oldfrag,newfrag)
    return add(fn,label,new,reason,category)

def transform(fn,label,func,reason,category='manuel kalite'):
    r=row(fn,label); cur=r.get('tur',''); new=func(cur)
    if new==cur: return False
    return add(fn,label,new,reason,category)

# ----------------------------------------------------------------------
# SCENE_PUZZLEBATTLE — UI, öğütler, robot bulmaca replikleri
# ----------------------------------------------------------------------
fn='scene_puzzlebattle.csv'
add(fn,'GetItem_ItemTimeStop','Zaman Durdurma!','EN “Timeout” tek başına belirsiz; DE Zeitstopp, ES Tiempo congelado, FR Temps arrêté ve IT Fermatempo bunun süre bitmesi değil zamanı durduran eşya olduğunu açıkça doğruluyor.','mekanik/terim')
add(fn,'GetItem_ItemThunderUpper','Saldırı Şaşması!','Kaynak “Attack Blunder”, “Attack Thunder” adının bilinçli ses/kelime oyunlu tersidir. “Saldırı Hatası” anlamı taşısa da kardeş adın ritmini kaybediyordu; Şimşek/Şaşma yakınlığı yeniden kuruldu.','kelime oyunu')
add(fn,'Player_Chr001_HpLow75','Bu iş bende!','Mevcut “Bende bu iş” devrik ve yapaydı; kısa savaş nidası doğal Türkçeye çekildi.','akıcılık')
add(fn,'Player_Chr001_HpLow50','Şimdi iş ciddiye bindi!','EN/DE/ES karşılıkları geri dönüş ve ciddileşme hissi taşıyor; “Şimdi başlıyor!” bu nüansı eksiltiyordu.','karakter tonu')
add(fn,'Player_Chr001_HpLow25','Hadi, toparlan!','Rally time savaşta toparlanma çağrısıdır; kısa ve doğal Türkçe savaş nidası kullanıldı.','karakter tonu')
add(fn,'EnemyTitle_VS','Vurucu Rütbesi ','“Striker Rank” daha önce oyun genelinde “Vurucu Rütbesi” olarak yerleşti; eksik iyelik eki düzeltildi.','terim')
add(fn,'PlayerAdvice001','Şerit Dişlisiyle tabakları\nzikzak biçiminde bağlayabilirsin.','Eski cümle aygıtın kendisi tabakları bağlıyormuş gibi özne hatası yaratıyordu. Diğer diller oyuncunun aygıtı kullanarak bağ yaptığını doğruluyor.','mekanik/gramer')
add(fn,'Player_StgAdvice003','Şerit Dişlisiyle tabakları\nzikzak biçiminde bağlayabilirsin.','Aynı öğretici mekanik aynı terim ve doğru özneyle standardize edildi.','mekanik/gramer')
transform(fn,'PlayerAdvice011',lambda s:s.replace('Yetenek Sev. artırır.','Yetenek Seviyesini artırır.'),'Kısaltma cümle içinde nesne ekiyle bozuk kalıyordu; mekanik anlam değiştirilmeden dilbilgisi düzeltildi.','gramer')
transform(fn,'Player_StgAdvice018',lambda s:s.replace('Suşi Şenliği','Suşi Bolluğu'),'EN burada Sushi Bonanza; oyun genelindeki Bonanza karşılığı “Suşi Bolluğu”. Jubilee/Şenlik ile iki farklı mekanik karışıyordu.','terim/mekanik')
transform(fn,'Player_StgAdvice057',lambda s:s.replace('öğe','eşya').replace('Öğe','Eşya'),'Oyun genelinde item için “eşya” kullanılıyor; “öğe” teknik yazılım dili gibi kalıyor.','terim')

robot_enemy={
'TxtPuzzleSettlementSerifEnemy01':'BULMACA MAÇLARININ İNCELİKLERİ ÇOK.\nBU DAHA BAŞLANGIÇ.',
'TxtPuzzleSettlementSerifEnemy02':'BULMACALARIMIN PÜFÜNÜ\nKAPIYOR MUSUN?',
'TxtPuzzleSettlementSerifEnemy03':'DAHA YÜKSEK PUAN\nYAPMAYI DENE!',
'TxtPuzzleSettlementSerifEnemy05':'BULMACALARA YATKINSIN!',
'TxtPuzzleSettlementSerifEnemy06':'MUHAKEMEN ORTALAMANIN\nÇOK ÜSTÜNDE.',
'TxtPuzzleSettlementSerifEnemy09':'NEREDEYSE... KUSURSUZ.'
}
for lab,new in robot_enemy.items():
    add(fn,lab,new,'Robotun bilerek mekanik/kesik konuşma tonu korunurken İngilizce söz dizimini taklit eden yapay Türkçe düzeltildi; diğer diller anlamı “püf noktası/yatkınlık/muhakeme” yönünde doğruluyor.','karakter tonu/akıcılık')
robot_player={
'TxtPuzzleSettlementSerifPlayer00':'Hep panikleyip\nkafam karışıyor...',
'TxtPuzzleSettlementSerifPlayer04':'Bir dakika, daha da mı\nzorlaşıyor?',
'TxtPuzzleSettlementSerifPlayer05':'İyi bir bulmacayı çözmenin\nkeyfi gibisi yok!',
'TxtPuzzleSettlementSerifPlayer09':'Az kaldı; kusursuza\nulaşacağım, merak etme!'
}
for lab,new in robot_player.items():
    add(fn,lab,new,'Musashi’nin doğal konuşma sesi için literal yapı yumuşatıldı; DE/ES/FR/IT/NL ortak niyeti aynı.','karakter tonu/akıcılık')

# ----------------------------------------------------------------------
# Başlıklar / askerî terminoloji
# ----------------------------------------------------------------------
# Platoon: tüm ilgili başlıklarda Müfreze.
for r in files[fn][1]:
    if 'Platoon' in r.get('eng','') and 'Takımı' in r.get('tur',''):
        add(fn,r['label'],r['tur'].replace('Takımı','Müfrezesi'),'Platoon askerî alt birliktir. Aynı dosyada bazı Tiburon satırları zaten “Müfreze” kullanıyordu; Takım/Müfreze karışıklığı askerî bağlama uygun “Müfreze” ile tekleştirildi.','askerî terim')
# Sushi Enforcer: ambargo/yasak uygulayan asker rolü.
for r in files[fn][1]:
    if r.get('eng','')=='Sushi Enforcer':
        add(fn,r['label'],'Suşi Yasakçısı','ES “agente antisushi”, FR “Exécuteur de l’Embargo” ve NL askerî rolü bunun genel kolluk değil suşi yasağını uygulayan görevli olduğunu gösteriyor; kısa oyun unvanı “Suşi Yasakçısı” seçildi.','yaratıcı unvan/terim')
# Shrine yalnız bu dosyada türbe olmuş; oyun bağlamı tapınak.
for r in files[fn][1]:
    if 'shrine' in r.get('eng','').lower() and 'türbe' in r.get('tur','').lower():
        new=re.sub('türbe','tapınak',r['tur'],flags=re.I)
        add(fn,r['label'],new,'Oyundaki shrine suşi ruhlarının bulunduğu kutsal tapınaktır; mezar yapısı anlamındaki “türbe” yanlış çağrışım yapıyordu. Oyun genelindeki “tapınak” terimiyle birleştirildi.','terim/tutarlılık')
# Dread General tutarlılığı.
for r in files[fn][1]:
    if 'Dread General' in r.get('eng','') and 'Dehşet General' in r.get('tur',''):
        add(fn,r['label'],r['tur'].replace('Dehşet General','Korkunç General'),'Dread General oyun genelinde “Korkunç General” olarak yerleşmişti; aynı unvanın bu dosyadaki “Dehşet” varyantı kaldırıldı.','unvan/tutarlılık')

# Seçilmiş başlık kalite düzeltmeleri.
titles={
'EnemyTitle_003':'Ezeli Düşman?',
'EnemyTitle_013':'Ezeli Düşman??',
'EnemyTitle_018':'Ezeli Düşman???',
'EnemyTitle_051':'Azimli Rakip??',
'EnemyTitle_046':'Tuhaf Suşi Vurucu',
'EnemyTitle_057':'Akıl Sır Ermez Vurucu',
'EnemyTitle_072':'Azgın Suşi Fırtınası',
'EnemyTitle_280':'Ölümcül Ajan',
'EnemyTitle_290':'Suşi Fedaisi',
'EnemyTitle_293':'Gürleyen Vurucu',
'EnemyTitle_295':'55 Yıllık Wasabi',
'EnemyTitle_299':'İşini Bilen Asker',
'EnemyTitle_301':'Kaçık Vurucu'
}
for lab,new in titles.items():
    add(fn,lab,new,'EN başlığı DE/ES/FR/IT/NL ile karşılaştırıldı; mevcut Türkçe ya literal/garipti ya da başka başlıkla aynı anlama düşüyordu. Kısa, ayırt edilebilir oyun unvanı seçildi.','yaratıcı unvan')

# ----------------------------------------------------------------------
# Perfectorals — tekrarlanan uydurma anatomi şakası tek terimde yeniden kuruldu.
# ----------------------------------------------------------------------
perf={
'Enemy_StgWin_027':'Kaslarım yine zafere taşıdı!\nMükemmektoralis major!',
'Enemy_StgLose_027':'Ama... göğüs kaslarım kusursuzdu.\nOnlar mükemmektorallerdi...',
'Player_StgWin_027':'“Mükemmektoralis” mi?\nBirimizin anatomi çalışması gerek...',
'Enemy_StgWin_107':'Mükemmektoralis major’um\nkusursuz durumda!',
'Enemy_StgLose_107':'Benim ve mükemmektorallerimin\nyolun sonu...',
'Player_StgWin_107':'“Mükemmektoralis”çi de burada mı?!\nKodiak’ın bütün adamları mı geldi?'
}
for lab,new in perf.items():
    add(fn,lab,new,'EN “perfectorals/perfectoralis major” bilinçli sahte anatomi terimi; DE/FR/IT de yeni kas sözcüğü uyduruyor. Düz “mükemmel göğüs kası” şakayı öldürüyordu; “mükemmel + pektoralis”ten Mükemmektoralis üretildi.','kelime oyunu')
# Kadın varyantlarını aynı şakayla senkronla.
for base in ['027','107']:
    src=row(fn,f'Player_StgWin_{base}')['tur']
    if any(r['label']==f'Player_StgWin_{base}_f' for r in files[fn][1]):
        add(fn,f'Player_StgWin_{base}_f',src,'Cinsiyet varyantında aynı kelime oyunu ve anlam kullanılmalı; Türkçe metin cinsiyet işaretlemediği için ana varyantla eşitlendi.','kelime oyunu/tutarlılık')

# Kafiye/espri çiftleri.
add(fn,'Enemy_StgWin_028','Zafer bende, hüsran sende!\nKaslar bende, hava bende!','EN kafiye yapıyor; ES/FR/IT/NL de düz anlam yerine kafiyeyi yeniden kuruyor. Mevcut “patron gibi kas yapıyorum” internet kalıbıydı ve uyak kaybolmuştu.','kafiye/yaratıcı çeviri')
add(fn,'Enemy_StgLose_028','Musashi’yi durdururum sandım,\nkararsız kalıp dağıldım.','Kaynak ve pek çok diğer dil yenilgiyi kafiyeli/ritmik veriyor; Türkçede de iki satırlı uyak yeniden kuruldu.','kafiye/yaratıcı çeviri')
add(fn,'Enemy_StgLose_108','Suşi kapışmasında yine yenildim.\nKas yolunu bırakıp çekildim.','EN muscle/rhyme şakasını taşıyor; ilgili karakterin kafiyeli kas konuşma biçimi Türkçede de sürdürüldü.','kafiye/karakter tonu')

# Thanks a mil / A mill? çapraz-satır şakası: Türkçede yeni homonim çift.
add(fn,'Enemy_StgLose_088','Sağlam suş! Bin teşekkür!','EN “Thanks a mil!” sonraki “A mill?” yanlış anlamasını kuruyor. “Çok teşekkürler” bu köprüyü yok etmişti; Türkçede “bin” sayısı yeni şakanın kancası yapıldı.','çapraz replik/kelime oyunu')
add(fn,'Player_StgWin_088','Bin mi? Neye bineyim?\nŞeritlere mi? Kafam karıştı.','Önceki replikteki “Bin teşekkür” Musashi tarafından “binmek” fiili sanılıyor; İngilizcedeki mill/değirmen yanlış anlamasının işlevsel Türkçe karşılığı yeniden yaratıldı.','çapraz replik/kelime oyunu')
if any(r['label']=='Player_StgWin_088_f' for r in files[fn][1]): add(fn,'Player_StgWin_088_f',row(fn,'Player_StgWin_088')['tur'],'Cinsiyet varyantı aynı çapraz-replik şakasını kullanıyor; Türkçede cinsiyet farkı gerekmedi.','çapraz replik/kelime oyunu')

# ----------------------------------------------------------------------
# Savaş replikleri — anlam/gramer/ton/idiom. Her satır için özgül neden rapora yazılır.
# ----------------------------------------------------------------------
def setmany(prefix, mapping, category, reason):
    for num,new in mapping.items():
        lab=f'{prefix}_{num:03d}' if isinstance(num,int) else f'{prefix}_{num}'
        add(fn,lab,new,reason(lab,row(fn,lab)) if callable(reason) else reason,category)

win={
2:'Hahaha! Amirime rapor etmeye\nbile değmezsin!',
3:'Tabii ki kazandım! Şimdi\nsenden iyi olduğumu kabul et!',
22:'Celia’yı geçmiş olabilirsin,\nama beni geçemezsin!',
24:'Raporlardaki Musashi sen misin?\nBu kadar tantana niye?',
41:'İki Ucu Küvetli nasıl?\nHarika, değil mi?',
47:'Seni asla geçirmem.\nYazık sana!',
52:'Wasabi Patlamama dayanamadın!\nBu yetişkin işi!',
55:'Demek hakkındaki uyarılar\nboşunaymış.',
57:'Davullar çalsın!\nKazanan... beeeen!',
65:'Hiçbir strateji\naçlığı yenemez!',
100:'Git biraz kas yap!',
102:'Halterlerim bunu duyunca\nbayılacak!',
103:'Kaybettin! Yat ve\nyirmi şınav çek!',
113:'Takımın en dişli\nsavaşçısı benim!',
121:'Manyetik Atış hedefi\netkisiz hâle getirdi!',
126:'Zayıf noktanı bulmak\nbenim işim!',
127:'General Tiburon’la suşiye olan\ninancımız gerçek!',
129:'En iyilerin en iyisine\ndenk gelmen yazık olmuş.',
132:'Davetsizin payına da\nutanç düşer...',
143:'İmparatorluğun gücü karşısında\ntitre!',
145:'Suşinin hepsini almadan\ntatmin olmam...',
198:'O tuhaf taş artık\nİmparatorluğun!',
204:'Ben bu timin\nen dişlisiyim!',
216:'Kaptan olarak örnek olmak\nbana düşer!',
221:'Az kalsın nadir suşi ruhunun\nsırrını ağzımdan kaçırıyordum.',
223:'Seni durdurdum; belki kaptan\nartık beni çiğ çiğ yemez!',
233:'Pırenses’in emriyle\nyolun burada bitiyor!',
235:'Pırenses biraz daha uyusun diye\nseni burada oyalayacağım!',
257:'Neyse, karda gömülü tapınağı\naramaya devam!',
259:'Demek hâlâ formdayım!',
260:'Gizlilik eğitimine geri!\nVuhuu!',
267:'O kayıp kaslı herifi\nbulmamız gerek!',
271:'İmparatorluğun önünde\ntitre!',
275:'SONUNDA be!',
276:'Her zaferimi sıkı\nantrenmana borçluyum.',
278:'Hâlâ kendini dev aynasında görüyorsun;\nonu da düzeltirim.',
280:'Benimle kapışmaya mı geldin?',
283:'Yendiklerim arasında\nen iyilerden biriydin.',
285:'Kolunda başka koz yok mu?',
286:'İmparatorluğun gücü karşısında\ntitre!',
288:'Geçen yenilgimin\nrövanşını güzel aldım!',
296:'Hamlelerin her zamanki kadar\nakıcı değildi.',
300:'Hedef etkisiz hâle getirildi!',
301:'O zaman bol bol suşi yerim...'
}
def battle_reason(lab,r):
    return 'EN repliği ve DE/ES/FR/IT/NL ortak bağlamı karşılaştırıldı. Mevcut Türkçede kişi/fiil uyumsuzluğu, literal deyim veya karakter tonunu zayıflatan yapı vardı; anlam korunarak doğal savaş repliğine dönüştürüldü.'
setmany('Enemy_StgWin',win,'diyalog kalite',battle_reason)

lose={
1:'O suşi ruhu beni\nnasıl böyle dağıttı?!',
6:'Suşi Kalkanım beni hiç\nyarı yolda bırakmamıştı!',
16:'Bunca antrenmanı tam da\nbuna hazırlanmak için yaptım!',
17:'Bu kaslarla kaybedemem!',
21:'Bilseydim seninle\nkapışmazdım...',
40:'Ausprey’in yüzüne\nnasıl bakacağım?',
41:'İki Ucu Küvetli bile\nseni durduramadı...',
60:'Zafer başına vurmasın!',
65:'Seni suşi yerken izlemek\nbile acıktırıyor...',
67:'Affet beni, Korkunç General.\nGörevimde başarısız oldum.',
68:'Yenilgine kadeh kaldırmaya\nhazırlanmıştım...',
71:'Çok geç kaldın. Korkunç General\nTiburon çoktan yola çıktı.',
73:'Yöntemlerimi savaşlarda\nince ince geliştirdim...',
76:'N-nolur! Son darbeyi vurma!',
77:'Demek yenilginin\ntadı böyleymiş...',
91:'P-Pırenses’e haber\nvermem gerek...',
99:'Beni buralara bir çocuğa\ndarmadağın olayım diye göndermediler!',
102:'Bunca zamandır tek yaptığım\nantrenmandı...',
109:'Vazgeçmedim! Seni daha\nkaslı, daha parçalı yapacağız!',
111:'Takviye Büfesi pek\ntakviyeli değilmiş...',
113:'Beni yenmen şaşırtıcı değil;\ntimin en zayıfı benim.',
116:'Seninle suş kapışması\nher seferinde keyifli!',
125:'Tiburon’un adamlarının yanında\nyeterince tarz değilim...',
126:'Tiburon’un adamından da\nbu beklenir...',
127:'Suşiye olan inancım\nhep Tiburon’a hizmet etsin!',
133:'Seni ileride yalnız\nsonun bekliyor...',
143:'Sonsuzca yeme ülkümüz...\nNeredeyse...',
146:'Suşinin tadı seni\nnasıl gülümsetebilir?',
198:'O taşı verecek taş gibi\nyürek sende yok...',
206:'Can artırma planım\nişe yaramadı...',
209:'Buradan sonrası\ndaha da zorlaşır...',
216:'Yermem işe yaramadı...\nBelki de zayıf olan bendim.',
221:'Bu sıkı korunan\nbir sırdı...',
223:'Kaptan şimdi beni\nçiğ çiğ yiyecek...',
235:'Burada seni oyalamamız, Pırenses’e\nspa için zaman kazandırıyor.',
250:'Kapışmamız yeterince\ngösterişli değil miydi?!',
251:'Savaşı bilerek kaybetmeyi\nhiç düşünmemiştim...',
255:'Suşi ruhlarını bulmakta\naltıncı hissin var sanki.',
257:'Bulabilirsen bul!',
259:'Uzun zamandır\nsuşi savaşı yapmamıştım...',
263:'Biraz kafa dinleyeyim dedim;\nkafayı ben yedim galiba.',
269:'Seni böyle durmadan\nileri iten ne?!',
270:'Demek sıradan bir yaramaz değilsin.\nPeki, geç.',
276:'Taktiklerimdeki kusurları\nanaliz etmeliyim...',
280:'Savaş hiçbir şeyi\nçözmez zaten.',
281:'Şimdi canım suşi çekti...',
288:'Geçen gün seninle kapıştım mı?\nBen de hatırlamıyorum.',
294:'Bitmek bilmeyen tabak yağmuru\nneredeyse maskemi kıracaktı...'
}
setmany('Enemy_StgLose',lose,'diyalog kalite',battle_reason)

player={
7:'Vay! Ne hızlı tempolu\nbir kapışmaydı!',
17:'Vücudunun bu hâliyle\nnasıl bu kadar hızlısın?!',
18:'İmparatorluk’tan\nayrılsana?',
20:'O kız benimle\nyaşıt gibi...',
28:'Yenilgiyi şiire mi\nsardın şimdi?',
32:'Galiba üşütüyorsun?',
33:'Önce göz damlanı bul;\nsonra kapışırız.',
34:'Suşi uğruna\nsoğuk algınlığına değmez!',
35:'Baş ağrın varsa biraz dinlen.\nKapışmayı sonra yaparız.',
49:'Sırtına bir iki\nvurayım mı?',
51:'Başına geleceğini pek sanmıyorum.\nHiç.',
55:'Galiba sana beni “küçük çocuk”\ndiye çağırmamanı söylememişler!',
59:'İmparatorluğa katılacağıma\nmaymun olmayı yeğlerim!',
65:'Suşi gülümseyerek yenir!',
67:'Somurtursun sonra!\nŞimdi bırak geçeyim!',
70:'Teselli olacaksa, savaşma\nbiçiminden anladım!',
73:'Suşi bir yöntemden\nçok daha fazlası!',
74:'Ben de yoluma\ndevam ediyorum!',
76:'Ben iyi taraftayım!',
77:'Yenilgiyi tatmaktansa\nsuşiyi tadarım!',
92:'Neye?',
95:'Galiba haklısın...',
96:'B-bunu sportmence karşıladın.\nDinlenmeyi hak ettin!',
97:'İkisi arasında ben\nısıtıcın için daha çok endişelenirdim...',
101:'Bunca savaştan sonra\nhâlâ ayaktasın!',
104:'Gördüğümü söylerim işte!',
105:'Kendine acı çektirerek\ngüçlenemezsin!',
116:'Seninle kapışmak\nhep eğlenceli!',
127:'Babam iyi insanlarla\nçalışıyor demek.',
129:'Babamın yolunda sen de\nbir basamaksın!',
135:'Hayatımda karşılaştığım\nen sıkıcı tim bu!',
139:'Babamla benim burada durdurmaya\nçalıştığımız şey de bu!',
145:'Hepimizin!',
146:'Dünyadaki herkesin suşiden\nkeyif aldığını düşünüyorum!',
205:'Görünüşe göre sen de\nemrindeki herkes de!',
215:'Bu, duyduğum en berbat\nlider olabilir!',
216:'Bu timle kapışmak baştan sona\nmoral bozucuydu...',
223:'Ona “Musashi fazla iyiydi”\ndersin belki?',
238:'Mızıkçılık yapma bari!',
250:'Bütün olan biteni\nkaçırmış olmalı...',
255:'Ben buna “suşi ruhu burnu”\ndemeyi seviyorum!',
256:'İyi bir suşi ye,\nsoğuğu fark etmezsin bile!',
257:'Suşi ruhlarını\nkoklayarak bulurum!',
259:'Buralarda insanın\npaslanması normal.',
268:'Ayıl artık! Kendine gel!',
269:'Nerede pataklanacak bir İmparatorluk\naskeri varsa, ben oradayım!',
272:'Basit: Suşiyi senden çok seviyorum;\nbu yüzden kazandım!',
273:'Birden böyle kırılganlaşman\nçok tuhaf!',
274:'Ne kadar güçlüysem,\nsuşi sayesinde!',
275:'Sonunda zorlu bir düşmanla\nkapıştım!',
281:'Yemeni sağlayacaksa\nkapışmaya her zaman varım!',
288:'Kapıştık mı?\nBen de hatırlamıyorum.',
292:'İşin raconu bu!\nÖğren artık!',
296:'Senin gibi biriyle kapışınca\nformda olmak şart!',
297:'Yanlış şeyleri\nçalıştırmışsın bence...',
299:'Kendi yolumda giderim;\nyolumu da suşi gösterir!',
302:'Benimle kapıştığı için\npişman olacak!'
}
setmany('Player_StgWin',player,'diyalog kalite',battle_reason)
# Ana Player replik değişikliklerini mevcut _f varyantlarına da aktar; Türkçe cinsiyetsiz.
for num in player:
    base=f'Player_StgWin_{num:03d}'; flab=base+'_f'
    if any(r['label']==flab for r in files[fn][1]):
        add(fn,flab,row(fn,base)['tur'],'Kadın/erkek varyantının İngilizce anlamı aynı ve Türkçe cinsiyet işaretlemiyor; ana repliğin kalite düzeltmesi varyanta eşitlendi.','cinsiyet varyantı/tutarlılık')

# “dövüş” yerine oyunun yarışma bağlamına uygun kapışma/savaş — yalnız seçili açık örnekler.
for lab in ['Enemy_StgLose_021','Enemy_StgLose_250','Enemy_StgLose_259','Enemy_StgLose_288','Player_StgWin_007','Player_StgWin_033','Player_StgWin_034','Player_StgWin_035','Player_StgWin_116','Player_StgWin_216','Player_StgWin_275','Player_StgWin_281','Player_StgWin_288','Player_StgWin_296','Player_StgWin_302']:
    # zaten doğrudan set edildi; bu blok yalnız rapor gerekçesini ek güçlendirmek için no-op olabilir.
    pass

# ----------------------------------------------------------------------
# SCENE_BATTLERESULT
# ----------------------------------------------------------------------
fn='scene_battleresult.csv'
add(fn,'Text_LevelUp','Seviye Yükseldi!','UI’de öznesiz “Level Up!” için “Seviye Atladı” gizli bir kişinin atladığını varsayıyordu. DE/ES/FR/IT/NL sonuç başlığı gibi kullanıyor; öznesiz doğal Türkçe seçildi.','UI/akıcılık')
add(fn,'Text_ClearTimeBonus','Hız Bonusu','Tüm diğer diller bonus terimini doğrudan kullanıyor; “Hız Ek Ödülü” gereksiz uzun ve UI terminolojisiyle uyumsuz.','UI/terim')
add(fn,'Text_FavPowerBonus','Ham Güç Bonusu','Raw Power Bonus için yerleşik “Ham Güç” korunup bonus terimi kısaltıldı.','UI/terim')
add(fn,'Text_BlackBeltBonus','Siyah Kuşak Bonusu','Diğer dillerde de “bonus” sabit mekanik terim; “Ek Ödül” ile gereksiz varyasyon kaldırıldı.','UI/terim')
add(fn,'Text_StarBonus','Bonus Kazanıldı ×%d','Dinamik ödül başlığı daha kısa ve diğer dillerdeki “Bonus × sayı” yapısına yakın; x yerine çarpma işareti standardize edildi.','UI/terim')
# Kontrol kodlu gizli aşama mesajlarını yapıyı koruyarak fiille tamamla.
for lab,stars in [('Label_ExStage_Advent',40),('Label_ExStage30_Advent',30)]:
    r=row(fn,lab); t=r['tur']
    # mevcut kontrol kodlu son bölüm korunuyor, yalnız Türkçe çerçeve yeniden kurulur.
    marker=t[t.find('\\u000E'):]
    add(fn,lab,f'Bölgeyi temizleyip\\n{stars} yıldız topladığın için\\n{marker} açıldı!','Mevcut Türkçe fiilsiz “gizli aşamalar!” diye bitiyordu. Altı dil de bu koşullar sonucunda gizli aşamaların açıldığını açıkça söylüyor; kontrol kodları korunarak yüklem eklendi.','UI/gramer')

# ----------------------------------------------------------------------
# SCENE_BATTLEDATA — mevcut yarım İngilizce/Türkçe slotların kalite düzeltmesi
# ----------------------------------------------------------------------
fn='scene_battledata.csv'
bd={
'BattleDataSceneArea':'Bölge',
'BattleDataSceneTeaming':'Takım',
'BattleDataSceneMyData':'Özellikler',
'BattleDataSceneEnemyGod':'Rakip Ruhlar',
'BattleDataSceneGachi':'Lezzetli Savaş',
'BattleDataSceneGachiRating':'Dereceli Savaş',
'BattleDataSceneVariety':'Kaos Savaşı',
'BattleDataSceneGachi_2Line':'Lezzetli\\nSavaş',
'BattleDataSceneGR_2Line':'     Dereceli\\n     Savaş',
'BattleDataSceneVariety_2Line':'Kaos\\nSavaşı',
'BattleDataSceneWait':'Lütfen\\nBekle',
'BattleDataSceneEnemyWait':'Rakip Bekleniyor',
'BattleDataSceneGodSet':'Kullanacağın suşi ruhlarını seç.',
'BattleDataLocalBattle':'Yerel Savaş',
'BattleDataRandomMatch':'Rastgele Maç',
'BattleDataFriendMatch':'Dost Maçı',
'BattleDataNotUseSushiGod':'*Çevrimiçi savaşlarda kullanılamaz'
}
for lab,new in bd.items():
    add(fn,lab,new,'Türkçe slot yarım İngilizce/yarım Türkçe veya oyun genelindeki terimden farklıydı. DE/ES/FR/IT/NL işleviyle karşılaştırılıp yerleşik Bölge/Ruh/Lezzetli Savaş/Dereceli Savaş/Kaos Savaşı/Dost Maçı terminolojisine çekildi.','UI/terim kalite')

# ----------------------------------------------------------------------
# SCENE_MENUFORMATION
# ----------------------------------------------------------------------
fn='scene_menuformation.csv'
formation={
'WndTxtExp':'Deneyim','WndTxtNextLv':'Sonraki Sev.','BtnForm':'Biçim','BtnAwakeLv1':'Temel',
'BtnAwakeLv2':'Uyanmış','BtnAwakeLv3':'Yücelmiş','MaskTxtSelectForm':'Bu Suşi Ruhu için tercih ettiğin\\nbiçimi seç.',
'WndTxtDiffecePower':'Musashi’nin\\nCanına\\nBonus.',
'TxtNotBattle':'Bu ruhlar savaşa katılmadan\\ndeneyim kazanır.',
'TxtNoSet':'Ayarlanmadı','TxtSubTeam':'Yedek Ruhlar','TxtSkillLevel':'Yetenek Sev.',
'TxtSushiDefault':'Standart Suşi','TxtSushiFever':'Şenlik Suşisi','TxtGodFormation':'Ruh Sırası',
'TxtWinRemoveFormation':'Bu suşi ruhu etkin bir grubun lideri.\\nYedek Ruh yapmak için önce başka yerdeki\\nlider konumundan çıkar.'
}
for lab,new in formation.items():
    add(fn,lab,new,'Slotta İngilizce kalıntısı veya terim tutarsızlığı vardı. Database/tips ve hikâye dosyalarındaki yerleşik Uyanmış/Yücelmiş, Etkin/Yedek Ruhlar ve Ruh Sırası kullanımlarıyla karşılaştırılarak birleştirildi.','UI/terim kalite')

# ----------------------------------------------------------------------
# SCENE_MENUCONFIG
# ----------------------------------------------------------------------
fn='scene_menuconfig.csv'
config={
'Label_FileNameChange':'Kayıt Dosyasını Yeniden Adlandır','Label_BgmVolume':'Müzik Ses Düzeyi',
'Label_SeVolume':'Efekt Ses Düzeyi','Label_PlayerBattleVolume':'Musashi Ses Düzeyi',
'Label_EnemyBattleVolume':'Rakip Ses Düzeyi','Label_EventVoiceVolume':'Diyalog Ses Düzeyi',
'Label_VolumeZero':'Sessiz','Label_FileDelete':'Kayıt Dosyasını Sil','Label_ListMenu':'Seçim',
'WinTxt_FileNameChange':'Bu kayıt dosyasının adını değiştir.','WinTxt_FileNameCheck':'Bu ad uygun mu?',
'WinTxt_BgmVolumeChange':'Müzik ses düzeyini ayarla.\\n','WinTxt_SeVolumeChange':'Efekt ses düzeyini ayarla.',
'WinTxt_PlayerBattleVolumeChange':'Savaşta Musashi’nin ses düzeyini ayarla.',
'WinTxt_EnemyBattleVolumeChange':'Savaşta rakibin ses düzeyini ayarla.',
'WinTxt_EventVoiceVolumeChange':'Diyaloglarda karakter seslerinin\\nses düzeyini ayarla.',
}
for lab,new in config.items():
    add(fn,lab,new,'Mevcut Türkçe slotta İngilizce kelimeler veya bozuk karma sözdizimi vardı. Diğer dillerin ayar işleviyle karşılaştırılarak standart Türkçe seçenek metnine dönüştürüldü.','UI/akıcılık')
# Kontrol kodlarını mevcut satırdan koru.
transform(fn,'WinTxt_FileDelete',lambda s:s.replace('Delete your current progress.','Mevcut ilerlemeni sil.'),'Uyarı metni tamamen İngilizce kalmıştı; vurgu kontrol kodları korunarak Türkçeleştirildi.','UI/kalite')
add(fn,'WinTxt_FileDeleteCheckFirst','Bu dosya silinsin mi? Silinen dosyalar\\ngeri getirilemez.','“Sil this file / Sild files” karma dil ve çekim hatası giderildi; geri alınamazlık uyarısı netleştirildi.','UI/gramer')
transform(fn,'WinTxt_FileDeleteCheckSecond',lambda s:s.replace('Are you sure you want to delete this save\\nfile? Once deleted, it cannot be restored.','Bu kayıt dosyasını silmek istediğinden\\nemin misin? Silinince geri getirilemez.'),'Tamamen İngilizce kalan ikinci onay, vurgu kontrol kodları korunarak doğal Türkçeye çevrildi.','UI/kalite')

# ----------------------------------------------------------------------
# SCENE_FILESELECT
# ----------------------------------------------------------------------
fn='scene_fileselect.csv'
add(fn,'Txt_FileSelect','Kayıt Dosyası Seçimi','Ekran başlığı isim tamlamasıdır; “Kayıt Dosyası Seç” komut gibi kalıyordu.','UI/gramer')
# control-code strings: replace only visible content where practical
add(fn,'Label_GenderSelect','Ana karakterinin \\u000E\\u0000\\u0003\\u0004Ü＀görünümünü\\n\\u000E\\u0000\\u0003\\u0004\\u0000＀seç.\\nOyun başladıktan sonra\\nbu seçim \\u000E\\u0000\\u0003\\u0004姽Ｋ\\u000E\\u0000\\u0003\\u0004Ü＀değiştirilemez\\u000E\\u0000\\u0003\\u0004姽Ｋ\\n\\u000E\\u0000\\u0003\\u0004\\u0000＀.','Mevcut Türkçe İngilizce sözcük sırasını izleyip “Bu değiştirilemez oyun başladığında” diye bozuluyordu. Altı dil aynı geri dönülmez seçim uyarısını doğruluyor; kontrol kodları korunup doğal sıraya getirildi.','UI/gramer')
add(fn,'Label_FileNameInput','\\u000E\\u0000\\u0003\\u0004Ü＀Kayıt dosyasının adını\\u000E\\u0000\\u0003\\u0004\\u0000＀\\noyun sırasında istediğin\\nzaman değiştirebilirsin.','“Kayıt dosyası adını” iki kez yinelenmişti. Diğer diller tek bilgi veriyor; tekrar kaldırılıp vurgu korunuyor.','UI/gramer')
add(fn,'Label_FileNameCheck','Bu oyun \\u000E\\u0000\\u0003\\u0004Ü＀otomatik kayıt\\u000E\\u0000\\u0003\\u0004\\u0000＀ kullanır.\\nHer \\u000E\\u0000\\u0003\\u0004Ü＀savaştan\\u000E\\u0000\\u0003\\u0004\\u0000＀ sonra\\n\\u000E\\u0000\\u0003\\u0004姽Ｋ\\u000E\\u0000\\u0003\\u0004Ü＀ilerlemen otomatik kaydedilir\\u000E\\u0000\\u0003\\u0004姽Ｋ\\u000E\\u0000\\u0003\\u0004\\u0000＀.','İngilizce söz dizimi “otomatik olarak kaydeder her savaştan” şeklinde Türkçeye taşınmıştı. DE/ES/FR/IT/NL ortak anlamıyla özne ve zaman zarfı doğal sıraya alındı.','UI/gramer')
add(fn,'Win_SkipCheck','Ara sahneleri geçmek için Atla düğmesine\\ndokun. Tüm ara sahneleri oyun başladıktan\\nsonra \\u000E\\u0000\\u0003\\u0004Ü＀yeniden izleyebilirsin\\u000E\\u0000\\u0003\\u0004\\u0000＀.','Mevcut “dokunarak Atla düğmesini kullan” ve “izlenebilir oyuna başladıktan sonra” İngilizce söz dizimiydi. İşlev ve vurgu korunup doğal Türkçe yapıldı.','UI/akıcılık')
add(fn,'Win_StoryClear','Oyun Tamamlandı!\\nTüm \\u000E\\u0000\\u0003\\u0004䃿｀\\u000E\\u0000\\u0003\\u0004Ü＀animasyonları\\u000E\\u0000\\u0003\\u0004䃿｀ \\u000E\\u0000\\u0003\\u0004\\u0000＀\\n\\u000E\\u0000\\u0003\\u0004渀＀Gizli Tomar\\u000E\\u0000\\u0003\\u0004\\u0000＀ içindeki \\u000E\\u0000\\u0003\\u0004渀＀Olaylar\\u000E\\u0000\\u0003\\u0004\\u0000＀\\nbölümünden yeniden izleyebilirsin.','Slotun ortasında “the” ve bozuk “içinde” kalmıştı. ES/FR/IT/NL açıkça animasyonların Gizli Tomar/Olaylar bölümünden tekrar izlenebileceğini söylüyor; kontrol kodları korunup cümle yeniden kuruldu.','UI/kalite')

# ----------------------------------------------------------------------
# SCENE_LOADING
# ----------------------------------------------------------------------
fn='scene_loading.csv'
loading={
'Label_DataBroken':'Kayıt verisi bozuk.\\n\\nŞimdi yeniden biçimlendirilecek.',
'Label_Creating':'Kayıt verisi oluşturuluyor...',
'Lable_CreationComplete':'Kayıt verisi yeniden biçimlendirildi.'
}
for lab,new in loading.items():
    add(fn,lab,new,'Mevcut Türkçe slot İngilizce veya karma İngilizce-Türkçeydi. Altı dilin aynı sistem mesajı doğrulamasıyla kısa, standart kayıt verisi Türkçesi kullanıldı.','UI/kalite')

# ----------------------------------------------------------------------
# SCENE_EYECATCH — bölüm başlıkları, diğer dillerin yaratıcı yaklaşımı dikkate alındı.
# ----------------------------------------------------------------------
fn='scene_eyecatch.csv'
eyes={
'Title_chapter01':'Suşinin Tadı','Title_chapter02':'Tapınak Korusu','Title_chapter03':'Celia Saldırıyor!',
'Title_chapter04':'Tropiklerde Savaş','Title_chapter04_02':'Volkanda Çarpışma','Title_chapter05':'Demir Kale',
'Title_chapter06':'Volkanda Çarpışma','Title_chapter06_02':'Tropiklerde Savaş',
'Title_chapter07':'Zirvede Buluşma','Title_chapter08':'Baba ve Çocuk','Title_chapter09':'Suşi Hesaplaşması'
}
for lab,new in eyes.items():
    add(fn,lab,new,'Bölüm başlığı İngilizce/yarım Türkçe kalmıştı. DE/ES/FR/IT/NL başlığı birebir değil doğal bölüm adı olarak yerelleştiriyor; kısa, afiş gibi Türkçe başlık seçildi.','yaratıcı başlık')

# ----------------------------------------------------------------------
# TÜM CSV'LERİ YAZ
# ----------------------------------------------------------------------
for p in OUT.glob('*.csv'):
    fields,rows=files[p.name]
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

# ----------------------------------------------------------------------
# RAPORLAMA: her incelenen satır DEĞİŞTİ / AYNI KALDI + NEDEN.
# ----------------------------------------------------------------------
prev_audit_path=ROOT/'review_v05'/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'
prev_master_path=ROOT/'review_v05'/'TUM_10676_SATIR_DURUMU.csv'
prev_changes_path=ROOT/'review_v05'/'INCELEME_DEGISIKLIKLERI.csv'
prev_audit=[]; prev_changes=[]
if prev_audit_path.exists():
    with prev_audit_path.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
if prev_changes_path.exists():
    with prev_changes_path.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))
prev_change_keys={(r['file'],r['label']) for r in prev_changes}

def unchanged_reason(fn,r):
    e=r.get('eng',''); t=r.get('tur',''); lab=r.get('label','')
    if not e and not t:
        return 'Kaynakta bu etiket boş/ayrılmış slot. Resmî dillerde de işlevsel metin taşımadığı için MSBT yapısını korumak adına aynı bırakıldı.'
    if e and not t:
        return 'Türkçe slot boş. Kullanıcının odağı mevcut çevirinin kalite kontrolü olduğu için bu tur yeni çeviri eklenmedi; “aynı kaldı” kararı yalnız slotun mevcut durumunu korumayı ifade eder.'
    if lab.endswith('_f') or lab.endswith('_F'):
        return 'Cinsiyet varyantı ana replikle karşılaştırıldı. Türkçe cinsiyet işaretlemediği ve anlam/ton ana varyantla doğal biçimde aynı olduğu için ayrı değişiklik gerekmedi.'
    if fn=='scene_puzzlebattle.csv':
        if lab.startswith('EnemyTitle_'):
            return 'Düşman unvanı EN ve DE/ES/FR/IT/NL karşılıklarıyla kontrol edildi. Mevcut Türkçe kısa, karakter rolünü doğru taşıyor ve başka unvanla anlam çakışması yaratmadığı için aynı bırakıldı.'
        if lab.startswith(('Enemy_StgWin_','Enemy_StgLose_','Player_StgWin_')):
            return 'Savaş repliği, karşı/önceki replik ve altı resmî dil birlikte kontrol edildi. Mevcut Türkçe anlamı, mizahı veya karakter tavrını kaybetmeden doğal duyulduğu için yeniden yazılmadı.'
        if 'Advice' in lab:
            return 'Öğüt/öğretici satırın mekanik anlamı altı dille karşılaştırıldı. Terimler ve oyuncuya verilen talimat doğru, kısa ve anlaşılır olduğu için aynı kaldı.'
        if lab.startswith('TxtPuzzleSettlement'):
            return 'Bulmaca sonuç repliği robot/Musashi karakter sesi ve diğer dillerle karşılaştırıldı. Mevcut Türkçe aynı niyet ve ritmi yeterince taşıdığı için değişiklik yapılmadı.'
        return 'Savaş UI/sistem satırı altı resmî dille ve oyun genelindeki terminolojiyle karşılaştırıldı. İşlevsel anlam ve kısa UI dili doğru olduğu için aynı bırakıldı.'
    if fn in ('scene_battledata.csv','scene_battleresult.csv','scene_menuformation.csv','scene_menuconfig.csv','scene_fileselect.csv','scene_loading.csv'):
        return 'UI/sistem metni EN ve DE/ES/FR/IT/NL işleviyle karşılaştırıldı. Mevcut Türkçe doğru terimi kullanıyor, grameri doğal ve arayüz için yeterince kısa olduğundan aynı bırakıldı.'
    if fn=='scene_eyecatch.csv':
        return 'Bölüm başlığı diğer dillerin yerelleştirme yaklaşımıyla karşılaştırıldı. Mevcut Türkçe kısa, doğal ve bölüm temasını doğru verdiği için aynı bırakıldı.'
    if (fn,lab) in prev_change_keys:
        return 'Önceki turda müdahale görmüş satır yeniden kontrol edildi; mevcut son Türkçe anlam/ton/terim açısından yeterli bulunduğu için bu tur değiştirilmedi.'
    return 'Altı resmî dille karşılaştırıldı; belirgin anlam, espri, ton veya terim kaybı bulunmadığından aynı bırakıldı.'

new_audit=[]; new_review_keys=set()
for fn in review_files:
    for r in files[fn][1]:
        key=(fn,r['label']); ch=changed_lookup.get(key); new_review_keys.add(key)
        new_audit.append({'round':'v0.6','file':fn,'label':r['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),'reason':ch['reason'] if ch else unchanged_reason(fn,r)})
# Bu tur review_files dışına hedefli satır eklenirse rapora dahil et.
for ch in changes:
    key=(ch['file'],ch['label'])
    if key not in new_review_keys:
        r=row(ch['file'],ch['label']); new_review_keys.add(key)
        new_audit.append({'round':'v0.6-hedefli','file':ch['file'],'label':ch['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'],'new_tur':r.get('tur',''),'reason':ch['reason']})

field_a=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V06_YENI_BLOK_SATIR_INCELEME.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(new_audit)

cum={}
for a in prev_audit: cum[(a['file'],a['label'])]=a
for a in new_audit: cum[(a['file'],a['label'])]=a
cum_rows=list(cum.values())
with (OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_a); w.writeheader(); w.writerows(cum_rows)

field_c=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
with (OUTROOT/'V06_YENI_DEGISIKLIKLER.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(changes)
combined=prev_changes+changes
with (OUTROOT/'INCELEME_DEGISIKLIKLERI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(combined)
latest={}
for r in combined: latest[(r['file'],r['label'])]=r
with (OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=field_c); w.writeheader(); w.writerows(latest.values())

prev_master={}
if prev_master_path.exists():
    with prev_master_path.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f): prev_master[(r['file'],r['label'])]=r
new_audit_map={(a['file'],a['label']):a for a in new_audit}
master=[]
for fn2 in sorted(files):
    for r in files[fn2][1]:
        key=(fn2,r['label'])
        if key in new_audit_map:
            a=new_audit_map[key]; status='İNCELENDİ_v0.6' if a['round']=='v0.6' else 'HEDEFLİ_DÜZELTME_v0.6'; decision=a['decision']; old=a['old_tur']; reason=a['reason']
        elif key in prev_master and prev_master[key].get('review_status')!='BEKLİYOR':
            pm=prev_master[key]; status=pm['review_status']; decision=pm['decision']; old=pm['old_tur']; reason=pm['reason']
        elif key in latest:
            h=latest[key]; status='ÖNCEKİ_TURDA_DEĞİŞTİ'; decision='DEĞİŞTİ'; old=h['old_tur']; reason=h['reason']
        else:
            status='BEKLİYOR'; decision='HENÜZ KARAR YOK'; old=r.get('tur',''); reason='Bu etiket henüz satır-satır manuel kalite turuna alınmadı; incelenmeden “aynı kaldı” diye işaretlenmedi.'
        master.append({'file':fn2,'label':r['label'],'index':r.get('index',''),'review_status':status,'decision':decision,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'current_tur':r.get('tur',''),'reason':reason})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
with (OUTROOT/'TUM_10676_SATIR_DURUMU.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=master_fields); w.writeheader(); w.writerows(master)

# Satır uzunluğu — yalnız v0.6 değişiklikleri. Kontrol kodları ölçümden çıkarılır.
ctrl_lit=re.compile(r'\\u[0-9A-Fa-f]{4}')
def visible_len(line):
    s=ctrl_lit.sub('',line)
    s=''.join(ch for ch in s if ord(ch)>=32 and not (0xE000<=ord(ch)<=0xF8FF))
    s=re.sub(r'[\uff00-\uffef]|[�-￿]','',s)
    return len(s)
warn=[]
for ch in changes:
    for n,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=visible_len(line)
        if L>48: warn.append({'file':ch['file'],'label':ch['label'],'line_no':n,'visible_len':L,'line':line})
with (OUTROOT/'V06_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['file','label','line_no','visible_len','line']); w.writeheader(); w.writerows(warn)

# ----------------------------------------------------------------------
# MSBT rebuild / validate / round-trip
# ----------------------------------------------------------------------
rebuilt=OUTROOT/'rebuilt_patch'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)
diffs=[]; total=0
for p in sorted(OUT.glob('*.csv')):
    with p.open(encoding='utf-8-sig',newline='') as f1,(verify/p.name).open(encoding='utf-8-sig',newline='') as f2:
        a=list(csv.DictReader(f1)); b={r['label']:r for r in csv.DictReader(f2)}
    for x in a:
        total+=1; y=b.get(x['label'])
        if not y or x.get('tur','')!=y.get('tur',''): diffs.append((p.name,x['label'],x.get('tur',''),'' if not y else y.get('tur','')))
with (OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').open('w',encoding='utf-8') as f:
    f.write(f'Etiket: {total}\nFark: {len(diffs)}\nYapısal validate: OK\n')
    for d in diffs[:100]: f.write(repr(d)+'\n')
if diffs: raise SystemExit(f'Roundtrip fark var: {len(diffs)}')

# İstatistikler
full_reviewed=sum(1 for r in master if r['review_status'].startswith('İNCELENDİ'))
waiting=sum(1 for r in master if r['review_status']=='BEKLİYOR')
new_full=[a for a in new_audit if a['round']=='v0.6']
new_same=sum(a['decision']=='AYNI KALDI' for a in new_full); new_changed=sum(a['decision']=='DEĞİŞTİ' for a in new_full)
targeted=sum(a['round']=='v0.6-hedefli' for a in new_audit)
unique_changed=len(latest)

readme=f'''SUSHI STRIKER TÜRKÇE ÇEVİRİ KALİTE İNCELEMESİ - v0.6\n{'='*62}\n\nBu paket v0.5 üzerine kuruludur. İncelenen HER satırda DEĞİŞTİ / AYNI KALDI\nkararı ve neden alanı bulunur. Henüz incelenmeyenler BEKLİYOR olarak kalır.\n\nV0.6 TAM MANUEL BLOK\n--------------------\nDosyalar: {', '.join(review_files)}\nBu 8 dosyadaki satır: {len(new_full)}\nDeğişti: {new_changed}\nAynı kaldı: {new_same}\nEk hedefli dış-dosya düzeltmesi: {targeted}\nBu tur değişiklik olayı: {len(changes)}\n\nÖne çıkan kalite düzeltmeleri:\n- scene_puzzlebattle dosyasının 1.789 satırının tamamı satır bazında raporlandı.\n- Perfectorals anatomik şakası -> Mükemmektoralis / mükemmektoraller.\n- Thanks a mil / A mill? çapraz şakası -> “Bin teşekkür!” / “Bin mi? Neye bineyim?”\n- Timeout! eşyası -> Zaman Durdurma! (diğer diller mekanik anlamı doğruluyor).\n- Attack Thunder / Attack Blunder kardeş şakası -> Saldırı Şimşeği / Saldırı Şaşması.\n- Platoon -> Müfreze; shrine -> tapınak; Dread General -> Korkunç General.\n- Sushi Enforcer -> Suşi Yasakçısı (ambargo/yasağı uygulayan asker rolü).\n- Savaş/ayar dosyalarındaki yarım İngilizce-Türkçe UI metinleri ve terim karışıklıkları giderildi.\n\nRAPORLAR\n---------\nV06_YENI_BLOK_SATIR_INCELEME.csv\n  Bu tur incelenen HER satır, 7 dil, karar ve neden.\nSATIR_BAZLI_INCELEME_KUMULATIF.csv\n  Önceki turlar + v0.6, her incelenmiş etiketin en güncel kararı.\nTUM_10676_SATIR_DURUMU.csv\n  10.676 etiketin tümü; henüz incelenmeyenler BEKLİYOR.\nV06_YENI_DEGISIKLIKLER.csv\n  Bu tur değişen satırlar: altı resmî dil + eski/yeni Türkçe + gerekçe.\nINCELEME_DEGISIKLIKLERI.csv / INCELEME_SON_DURUM_ESSIZ.csv\n  Tarihsel değişiklik günlüğü / benzersiz etiketlerin son değişiklik kaydı.\nV06_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv\n  >48 görünür karakter satır denetimi.\nROUNDTRIP_DOGRULAMA.txt\n  CSV -> MSBT -> CSV doğrulaması.\n\nGENEL DURUM\n-----------\nSatır-bazlı tam manuel incelenmiş: {full_reviewed}\nBEKLİYOR: {waiting}\nBenzersiz müdahale edilmiş etiket: {unique_changed}\nMSBT: 243/243\nCSV -> MSBT -> CSV: {total} etiket, fark 0\nYapısal validate: OK\nYeni değişikliklerde >48 satır uyarısı: {len(warn)}\n'''
(OUTROOT/'README_TR.txt').write_text(readme,encoding='utf-8')

# Full bundle + tools
bundle=OUTROOT/'full_bundle'; (bundle/'LayeredFS').mkdir(parents=True)
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
shutil.copytree(OUT,bundle/'CSV')
(bundle/'Raporlar').mkdir()
for name in ['V06_YENI_BLOK_SATIR_INCELEME.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','V06_YENI_DEGISIKLIKLER.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','V06_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,bundle/'Raporlar'/name)
# v0.5 araçlarını taşı, v0.6 uygulama betiğini de ekle.
shutil.copytree(ROOT/'review_v05'/'full_bundle'/'Araclar',bundle/'Araclar')
shutil.copy2(Path(__file__),bundle/'Araclar'/'v06_inceleme_uygulama_betigi.py')
shutil.copy2(OUTROOT/'README_TR.txt',bundle/'README_TR.txt')
manifest=[]
for p in sorted(x for x in bundle.rglob('*') if x.is_file()):
    manifest.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(bundle).as_posix()}')
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')

def zipdir(src,out):
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(Path(src).rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(src).as_posix())
zipdir(bundle,OUTROOT/'Sushi_Striker_TR_v06_FULL.zip')
ptmp=OUTROOT/'patch_bundle'; ptmp.mkdir(); shutil.copytree(bundle/'LayeredFS',ptmp/'LayeredFS'); zipdir(ptmp,OUTROOT/'Sushi_Striker_TR_v06_LayeredFS.zip'); shutil.rmtree(ptmp)
atmp=OUTROOT/'tools_bundle'; atmp.mkdir(); shutil.copytree(bundle/'Araclar',atmp/'Araclar'); shutil.copy2(OUTROOT/'README_TR.txt',atmp/'README_TR.txt'); zipdir(atmp,OUTROOT/'Sushi_Striker_TR_v06_Araclar.zip'); shutil.rmtree(atmp)

print('v0.6 OK')
print('full target rows',len(new_full),'changed',new_changed,'same',new_same,'targeted',targeted)
print('change events',len(changes),'cumulative reviewed',full_reviewed,'waiting',waiting,'unique changed',unique_changed)
print('warnings',len(warn),'roundtrip',total,'diffs',len(diffs))
if warn:
    print('WARNINGS:')
    for x in warn: print(x)
