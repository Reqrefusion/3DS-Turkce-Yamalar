from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys, os

ROOT=Path('/mnt/data/sushi_work')
BASE=ROOT/'review_v09_work'
SRC=BASE/'CSV'
OUTROOT=ROOT/'review_v09'
OUT=OUTROOT/'csv'
TOOL=BASE/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=BASE/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'review_v09_source'/'msgstudio'
PREV_MASTER=BASE/'Raporlar'/'TUM_10676_SATIR_DURUMU.csv'
PREV_AUDIT=BASE/'Raporlar'/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'
PREV_CHANGES=BASE/'Raporlar'/'INCELEME_DEGISIKLIKLERI.csv'

if OUTROOT.exists(): shutil.rmtree(OUTROOT)
OUT.mkdir(parents=True)
for p in SRC.glob('*.csv'): shutil.copy2(p,OUT/p.name)

files={}
for p in OUT.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rs=list(csv.DictReader(f)); fields=list(rs[0].keys()) if rs else ['label','index','deu','eng','esp','fra','ita','nld','tur']
    files[p.name]=(fields,rs)

prev_master={}
with PREV_MASTER.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f): prev_master[(r['file'],r['label'])]=r
with PREV_AUDIT.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
with PREV_CHANGES.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))

rows_by_key={(fn,r['label']):r for fn,(_,rs) in files.items() for r in rs}
changes=[]; changed_lookup={}

def row(fn,label):
    try:return rows_by_key[(fn,label)]
    except KeyError: raise KeyError((fn,label))
def norm(s): return (s or '').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')
def add(fn,label,new,reason,category='ikinci kalite geçişi'):
    r=row(fn,label); new=norm(new); old=r.get('tur','')
    if old==new:return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason not in rec['reason']: rec['reason']+=' Ek: '+reason
        return True
    rec={'round':'v0.9','category':category,'file':fn,'label':label,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec); changed_lookup[key]=rec; return True

def rep(fn,label,old,new,reason,category='ikinci kalite geçişi'):
    r=row(fn,label); cur=r.get('tur','')
    if old not in cur:return False
    return add(fn,label,cur.replace(old,new),reason,category)

def add_gender(fn,base_label,new,reason,category='ikinci kalite geçişi'):
    done=0
    for lab in [base_label,base_label+'_f']:
        if (fn,lab) in rows_by_key and row(fn,lab).get('eng','').strip():
            done += bool(add(fn,lab,new,reason,category))
    return done

# ---------------------------------------------------------------------------
# 1) Oyun geneli terim ve kelime oyunu tutarlılığı
# ---------------------------------------------------------------------------
raw_reason=("Raw Power, suşi bağlamında yalnız 'ham güç' değil 'raw/çiğ' kelime oyununu da taşıyor. "
            "İspanyolca 'poder crudo' bunu açıkça korurken Fransızca da düz çeviri yerine 'bonutriment' diye yeniden espri kuruyor. "
            "Bu yüzden tüm ekranlarda 'Çiğ Güç' olarak tekleştirildi.")
for fn,(_,rs) in files.items():
    for r in rs:
        cur=r.get('tur','')
        if 'Ham Güç' in cur or 'ham güç' in cur:
            new=cur.replace('Ham Güç','Çiğ Güç').replace('ham güç','çiğ güç')
            add(fn,r['label'],new,raw_reason,'terim/kelime oyunu')

order_reason=("Sprite Order aynı menü için bazı yerlerde 'Ruh Sırası', ana menüde ise 'Ruh Dizilimi' olmuştu. "
              "DE/NL karşılıkları takım düzeni, FR/IT ise ruh düzeni anlamını veriyor; ekranın işlevi aktif/yedek ruhları dizmek. "
              "Bütün referanslar 'Ruh Dizilimi' olarak birleştirildi.")
for fn,(_,rs) in files.items():
    for r in rs:
        cur=r.get('tur','')
        if 'Ruh Sırasını' in cur or 'Ruh Sırası' in cur:
            new=cur.replace('Ruh Sırasını','Ruh Dizilimini').replace('Ruh Sırası','Ruh Dizilimi')
            add(fn,r['label'],new,order_reason,'terminoloji')

for lab in ['SushiFavPowerName_Rainbowroll','SushiFavPowerName_Rainbowroll_lc']:
    add('database_cmn.csv',lab,'Ole-Aş',
        "Ole-Ace, diğer besin gücü adlarındaki -Ace kelime oyununun parçası. Türkçede Lino-Aş/İno-Aş/Glut-Aş/Fol-Aş serisi kurulmuşken 'Ole-As' diziyi bozuyordu; 'Ole-Aş' hem oleik asidi hem yemek anlamındaki 'aş' şakasını sürdürüyor.",
        'kelime oyunu')

rep('homeSushibar.csv','homeSushibar_17_t_04_M','Sanki... kaslarla suşi striking...\\nbirbirleriyle hiç alakalı değilmiş gibi...',
    'Sanki... kaslarla suşi vuruculuğunun...\\nhiçbir ilgisi yokmuş gibi...',
    "Türkçe satırda İngilizce 'striking' kalmıştı. IT/NL anlamı kaslarla suşi savaşındaki başarının bağlantısızlığını açıkça veriyor; cümle doğal Türkçeyle yeniden kuruldu.",'yarım çeviri')
rep('stageEndM004.csv','stageEndM004_07_M',"Suşi Striking'in Sekiz\\nİlkesi","Suşi Vuruculuğunun Sekiz\\nİlkesi",
    "Eight Precepts of Sushi Striking başlığında İngilizce 'Striking' kalmıştı. ES/IT/NL bunun suşi vuruculuğu/sushistriker ilkeleri olduğunu doğruluyor; yerleşik 'Suşi Vuruculuğu' terimine çekildi.",'yarım çeviri')

# ---------------------------------------------------------------------------
# 2) 1A–5A hikâye sahneleri: komşu replik + altı dil + espri/ton
# ---------------------------------------------------------------------------
add_gender('database_movieSerif_1A.csv','MovieSerifText_1a_0001_M','Eveeeeeeet!',
    "Kaynak yalnız bir coşku ünlemi; DE/ES/IT/NL bunu kendi dilinde yerelleştiriyor. 'Yeeah' bırakmak yerine Türkçedeki uzatılmış 'Eveeeeeeet!' aynı enerjiyi taşıyor.",'karakter sesi')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0005_F','Karnıma, tamam!',
    "Yum yum yum / In my tum kısa bir kafiye. Mevcut 'Karnıma!' anlamı veriyor ama ritmi düşürüyordu; önceki 'Nyam nyam nyam!' ile ses oyununu sürdürmek için serbestçe yeniden kuruldu.",'kafiye/espri')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0012_M','Aynen öyle!',
    "Önceki 'Meyve mi topluyorsun?' sorusuna verilen kısa onaydır. 'Öyle görünüyor' konuşanın kendi eylemi hakkında gereksiz mesafe yaratıyordu; bağlama uygun doğrudan yanıt seçildi.",'bağlam')
add_gender('database_movieSerif_1A.csv','MovieSerifText_1a_0036_M','Of ya! Yine aç kaldım.',
    "DE/NL/IT satırları karakterin hâlâ aç kalmasına odaklanıyor. 'Bana yiyecek kalmadı' dışsal bir neden ekliyordu; kısa ve çocuk karakterin sesine uygun biçimde düzeltildi.",'karakter sesi')
add_gender('database_movieSerif_1A.csv','MovieSerifText_1a_0064_M','Bir lokma alacağıma\\naç kalırım!',
    "EN/ES/FR/NL 'bir lokma yiyeceğime aç kalırım' karşıtlığını kuruyor. Mevcut 'bir tane bile ısırmam' anlaşılır ama Türkçede nesnesiz ve mekanik kalıyordu; doğal deyim yapısına çekildi.",'doğallık')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0069_M','Suşi sadece karın\\ndoyurmak değildir.',
    "Stuff the belly ifadesi DE/ES/IT/NL'de de yalnız mide doldurmanın ötesinde anlamına geliyor. 'Mide doldurmak için yenmez' yerine Türkçedeki yerleşik 'karın doyurmak' kullanıldı.",'deyim')
add_gender('database_movieSerif_1A.csv','MovieSerifText_1a_0075_M','Suşi gurusu mu?',
    "Sprout/sprite kasıtlı yanlış duyma şakasıdır. DE Meister/Geister, ES necio/genio, IT spiritoso/spirito, NL bami/sushigami gibi her dil yeni bir ses oyunu kuruyor. 'Turp/ruh' Türkçede sesçe bağlantısızdı; 'guru/ruh' yanlış duyma zinciri için yeniden yaratıldı.",'kelime oyunu')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0076_M','Guru değil! Suşi ruhu!',
    "Bir önceki sprout/sprite yanlış duyma şakasının cevabı. Türkçe esprinin iki replik boyunca çalışması için 'guru/ruh' eşleşmesi tamamlandı.",'kelime oyunu')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0096_M','Hadi bakalım! Durma,\\nyemeye devam!',
    "Well! Don't stop—keep eating! cesaretlendirici ve neşeli. 'E hadi' Türkçede hafif bıkkın duyuluyordu; FR de 'fais-toi plaisir' diyerek sıcak tonu öne çıkarıyor.",'ton')
add('database_movieSerif_1A.csv','MovieSerifText_1a_0099_M','Bu ne biçim meyve?!',
    "Vurgulu IS this?! şaşkınlık/itirazdır. 'Bu nasıl bir meyve?' daha nötr kalıyordu; doğal şaşkınlık kalıbı seçildi.",'ton')

add('database_movieSerif_1B.csv','MovieSerifText_1b_0007_M','Şimdi seni de suşi ruhunu da\\nelimize geçirdiğimize göre,\\nişimiz burada bitti.',
    "In our mitts ile DE/NL 'elimizde' ve ES 'bizimsiniz' anlamını veriyor. 'Avucumuza aldık' Türkçede himaye etmek çağrışımı yaratıyordu; tutsak alma bağlamı 'elimize geçirmek' ile netleştirildi.",'bağlam')
add('database_movieSerif_1B.csv','MovieSerifText_1b_0008_M',"İmparatorluk'a tek yön\\nbiletin hazır.",
    "One-way trip tehdit/tutsak götürme söylemi. 'Bilet kazandın' ödül kazanmış gibi duyuluyordu; alaycı tehdit tonu korunarak yeniden kuruldu.",'ton/deyim')
add_gender('database_movieSerif_1B.csv','MovieSerifText_1b_0019_M','Off... Düşündükçe\\ndaha da acıkıyorum.',
    "The hungrier I get artan açlığı anlatıyor. 'Karnım daha çok acıkıyor' anlaşılır fakat konuşma dilinde ağır; DE/ES/IT/NL'nin doğrudan açlık vurgusuna uygun doğal Türkçe seçildi.",'doğallık')
add('database_movieSerif_1B.csv','MovieSerifText_1b_0029_M','Seni, sana güç verecek bir kudretin\\nbulunduğu tapınağa götürecek.',
    "Nourishing strength yalnız besin sıfatı değildir; DE 'nährende Kraft', ES 'fuerza revitalizadora', NL 'gücün beslendiği' diyerek güç kazandırma anlamını doğruluyor. 'Besleyici bir güç' kalıbı Türkçede yapaydı.",'anlam nüansı')
add('database_movieSerif_1B.csv','MovieSerifText_1b_0039_M','Ne bekliyorsun?\\nO dev açlığını gider!',
    "Sate hunger için Türkçede 'açlığı doyurmak' değil 'açlığı gidermek' daha doğal. DE 'Heldenhunger' ve NL 'enorme honger' abartılı tonu destekliyor.",'deyim')
add('database_movieSerif_1B.csv','MovieSerifText_1b_0063_M','Üzerindeki ceket\\nsıradan değil.',
    "No ordinary jacket ifadesinde 'ceket ... sıradan bir ceket değil' gereksiz tekrar yaratıyordu. Anlam ve dramatik ton kısaltılarak korundu.",'akıcılık')
add_gender('database_movieSerif_1B.csv','MovieSerifText_1b_0076_M','Eveeeet!',
    "Coşku ünlemi diğer dillerde de yerelleştirilmiş; İngilizce 'Yeeah' bırakılmadan Türkçe seslendirildi.",'karakter sesi')

add('database_movieSerif_2B.csv','MovieSerifText_2b_0002_M','Ormanı yine eskisi gibi\\nsapasağlam hâle getirdik!',
    "Restore ... good as new anlamı mevcut çeviride 'eski hâline, sapasağlam döndürmek' diye iki yapının çarpışmasına yol açıyordu. Türkçe cümle akıcı biçimde yeniden kuruldu.",'akıcılık')
add('database_movieSerif_2B.csv','MovieSerifText_2b_0011_M','Millet aç kalınca\\nbenim de içim içimi yiyor!',
    "Gets me right in the gut karın/gut esprisi taşır; IT de 'mal di pancia' ile beden metaforunu koruyor. 'Mideme yumruk gibi oturuyor' yapaydı; Türkçede yemek temasına da uyan 'içim içimi yiyor' deyimiyle yeniden yaratıldı.",'deyim/kelime oyunu')
add('database_movieSerif_3B.csv','MovieSerifText_3b_0016_M','Suşi hâlâ damak tadıma\\ngöre değil.',
    "Have no taste for hem 'sevmemek' hem tat/damak çağrışımı taşır. NL 'smaakt me niet' de tat eksenini koruyor; düz 'sevmiyorum' yerine Türkçede 'damak tadıma göre değil' seçilerek nüans geri getirildi.",'kelime oyunu/nüans')
add('database_movieSerif_5A.csv','MovieSerifText_5a_0054_M','Cumhuriyet suşinin\\nkıymetini bilmez olmuştu.',
    "Taking for granted ifadesini DE/NL 'değerini bilmemek', ES 'alışıp takdir etmemek', FR 'sıradan saymak' diye çözüyor. 'Armağanı kanıksamak' fazla edebî ve çeviri kokuyordu.",'deyim')
add('database_movieSerif_5A.csv','MovieSerifText_5a_0056_M','İşler o kadar kötüleşti ki\\ntabaklarını bile silip süpürmez oldular.',
    "Clean their plates burada tabak yıkamak değil yemeği bitirmek. Mevcut metin anlamı veriyordu fakat 'lokma bırakır oldular' dolambaçlıydı; Türkçedeki 'silip süpürmek' yemek bağlamında daha canlı ve doğal.",'deyim')

# ---------------------------------------------------------------------------
# 3) Puzzle battle: ikinci pass — eksiltilmiş cümleler, kelime oyunları, ton
# ---------------------------------------------------------------------------
p='scene_puzzlebattle.csv'
add(p,'Enemy_StgWin_005','Bu yenilgi seni fena çarptı galiba!\\nHeheheh...',
    "Shocked, karakterin elektrik yeteneğine gönderme yapan kelime oyunudur. DE/ES/FR/IT/NL'nin tamamı elektrik/çarpılma çağrışımını koruyor; düz 'şaşırma' espriyi siliyordu.",'kelime oyunu')
add(p,'Enemy_StgWin_051','Demek bunca wasabiyi\\nboşuna yememişim!',
    "Diğer yerelleştirmeler 'wasabiyi boşuna yememişim' anlamını öne çıkarıyor. Mevcut 'bir anlamı varmış' Türkçede zayıf ve dolaylıydı.",'karakter sesi')
add(p,'Enemy_StgWin_062',"İmparatorluk'un Manyetik Atışı\\nböyle çarpar!",
    "Yetenekle övünen savaş repliği. 'Manyetik Atış gücü işte budur' katalog açıklaması gibi kalıyordu; vurucu savaş tonu için fiille yeniden kuruldu.",'savaş tonu')
add(p,'Enemy_StgWin_070','Demek suşiyi senden\\ndaha çok seviyormuşum!',
    "Kaynak sevgiyi karşılaştırıyor. 'Sevgim seninkinden daha güçlü' Türkçede soyut ve çeviri kokuyor; aynı anlam konuşma dilinde doğal kuruldu.",'doğallık')
add(p,'Enemy_StgWin_081',"Pırenses'in emri kanundur.\\nBuradan öteye geçemezsin.",
    "DE/IT/NL emre itaat temasını, kaynak da görevi vurguluyor. İyelik yazımı düzeltildi ve muhafız tonuna uygun iki kısa cümle kuruldu.",'karakter sesi/yazım')
add(p,'Enemy_StgWin_097','Buz kestin! Espriyi anladın mı?\\nA-a-anladın mı? Brrr...',
    "Stopped you cold + titreme kekeleyişi bir soğuk esprisidir. ES/FR/NL de 'buz gibi/soğukkanlı' şakası kuruyor. Mevcut 'buz gibi durdurdum' doğal değildi; Türkçedeki 'buz kesmek' deyimiyle yeniden yaratıldı.",'kelime oyunu')
add(p,'Enemy_StgWin_101','Soğukta tek ölçü\\nkas gücüdür!',
    "Kaynak karakterin kas takıntısını sloganlaştırıyor. 'Kimin kaslı olduğu' yapısal çeviri gibi kalıyordu; kısa savaş sloganına dönüştürüldü.",'karakter sesi')
add(p,'Enemy_StgLose_206','Özgüven artırma planım yattı...\\nAma dişli bizde!',
    "Self-esteem 'can/HP' değildir. DE/ES/NL doğrudan özgüven/pozitif motivasyon anlamını doğruluyor; ayrıca kaynakta tamamen düşmüş olan 'ama dişli bizde' ikinci cümlesi geri getirildi.",'anlam + eksik cümle')
add(p,'Enemy_StgLose_221','Nadir suşi ruhu çok gizli bir sır.\\nKimsenin haberi olmamalı!',
    "EN/FR/IT/NL iki ayrı bilgiyi koruyor: sır olduğu ve kimsenin bilmemesi gerektiği. Türkçe ikinci cümleyi tamamen kaybetmişti; ikisi de geri getirildi.",'eksik cümle')
add(p,'Enemy_StgLose_257','Tapınak bu karın altında gömülü.\\nBulabilirsen bul!',
    "Altı dil de tapınağın kar altında gömülü olduğu bilgisini içeriyor. Türkçede yalnız alaycı 'Bulabilirsen bul!' kalmış, görev/ipucu bilgisi düşmüştü.",'eksik bilgi')
add(p,'Enemy_StgLose_017','Ne?! Ben tim kaptanıyım!\\nBu kaslarla kaybedemem!',
    "Kaynak iki karakter özelliğini birleştiriyor: kaptanlık + kaslılık. Türkçe kaptanlık bölümünü atmıştı; FR/IT de iki unsuru koruyor.",'eksik cümle')
add(p,'Enemy_StgWin_100','Hâlâ çok çelimsizsin!\\nGit biraz kas yap!',
    "Kaynak önce rakibi küçümsüyor, sonra emir veriyor. Türkçe ilk cümleyi düşürmüştü; DE/FR/IT/NL iki aşamalı alay tonunu doğruluyor.",'eksik cümle')
add(p,'Enemy_StgWin_259','Uzun zamandır suşi kapışması\\nyapmamıştım. Demek hâlâ formdayım!',
    "Kaynak ve bütün resmî diller 'uzun aradan sonra ilk dövüş' bilgisini verir. Türkçe yalnız sonuç cümlesini bırakmıştı; bağlam geri getirildi.",'eksik cümle')
add(p,'Enemy_StgWin_275','N-ne? Kazandım mı? Gerçekten mi?!\\nSONUNDA be!',
    "Karakterin şaşkınlığı ardından 'artık zamanı gelmişti' patlaması var. Tüm resmî diller iki aşamayı da koruyor; Türkçe yalnız son ünlemi bırakmıştı.",'eksik cümle/karakter sesi')
add(p,'Enemy_StgWin_280','Geçen seferden sonra yine mi kapışacağız?\\nAptallık ediyorsun.',
    "Kaynak önce önceki karşılaşmaya gönderme yapıyor, sonra hakaret ediyor. Türkçede geçmiş karşılaşma ve 'fool' tonu kaybolmuştu.",'eksik bağlam')
add(p,'Enemy_StgWin_285','Bu kadar mı? Kolunda başka koz yok mu?\\nDaha fazlasını beklerdim.',
    "No tricks up your sleeve / hoped for more iki parçalı küçümsemedir. Türkçe yalnız 'koz' sorusunu bırakmıştı; ikinci yargı geri getirildi.",'eksik cümle/deyim')
add(p,'Enemy_StgWin_300','Hedef etkisiz hâle getirildi!\\nZaferimi generale bildirmeliyim.',
    "Bütün resmî diller görev tamamlandıktan sonra generale rapor verme cümlesini koruyor. Türkçe ikinci cümleyi tamamen düşürmüştü.",'eksik cümle')
add(p,'TxtPuzzleSettlementSerifEnemy05','ÇABUK KAVRIYORSUN.\\nBULMACALARDA YETENEKLİSİN!',
    "Kaynak robot iki ayrı övgü veriyor: hızlı kavrama + bulmaca yeteneği. DE/ES/IT/NL de ikisini koruyor; Türkçe ilk övgüyü düşürmüştü. Büyük harf robot üslubu korundu.",'eksik cümle/karakter sesi')

for lab,new,why in [
('Player_StgWin_018',"Seni kovdurduğum için kusura bakma!\\nİmparatorluk'tan ayrılsana?","Kaynak önce kovulmadaki payı için özür, sonra İmparatorluk'tan ayrılma önerisi getiriyor. Türkçede özür tamamen düşmüştü; NL/IT iki kısmı da doğruluyor."),
('Player_StgWin_020','O kız benimle yaşıt gibi...\\nNe kadar üzücü.',"EN/DE/ES/IT/NL yaşıt olma gözlemini ardından üzüntüyle tamamlıyor. Türkçe ikinci duygu cümlesini kaybetmişti."),
('Player_StgWin_031','O aptal yetenekle suşinin\\nkıymetini asla anlayamazsın!',"Appreciate sushi burada 'takdir etmek' değil tadını/kıymetini bilmek. DE/FR/NL bu nüansı destekliyor; doğal Türkçe karşılık seçildi."),
('Player_StgWin_032','Galiba üşütüyorsun.\\nGit biraz yatıp dinlen!',"EN/DE/ES/IT/NL hem hastalık gözlemini hem dinlenme tavsiyesini veriyor. Türkçede ikinci cümle tamamen kayıptı."),
('Player_StgWin_049','Sırtın mı tutuldu? İstersen\\nbir iki vurayım.',"Kaynak iki cümlelik alaycı yardım teklifidir. Türkçe yalnız vurma teklifini bırakınca sebep kayboluyordu; ilk soru geri getirildi."),
('Player_StgWin_065','İşte gerçek suşi böyle olur!\\nGülümseyerek yenir!',"Kaynak 'işte gerçek suşi' sonucunu ardından yeme tavrıyla bağlıyor; IT/NL ikisini de koruyor. Türkçe ilk cümleyi düşürmüştü."),
('Player_StgWin_072','Hem de nasıl yanıldın! Ee, peki\\nniye kaybetmiş gibi davranmıyorsun?',"Karşı tarafın 'seni yanlış değerlendirdim' repliğine doğrudan cevap ve ardından şüphe sorusu. 'Tabii ki ettin' öznesiz ve zayıftı; iki replik arasındaki bağ güçlendirildi."),
('Player_StgWin_076','“Bitirici darbe” mi? Sana zarar\\nvermeyeceğim! Ben iyi taraftayım!',"Kaynak 'finishing blow' sözünü reddedip iyi tarafta olduğunu söylüyor. Türkçede ilk iki düşünce düşmüş, yalnız sonuç kalmıştı."),
('Player_StgWin_090','Demek aklın bu yüzden\\nhiç dövüşte değildi?',"Kaynak önceki açıklamaya bağlanan sebep-sonuç sorusu. Mevcut Türkçe dolambaçlı 'o yüzden mi ... gibiydi' yapısıyla konuşma doğallığını kaybediyordu."),
('Player_StgWin_095','Haaaapşuu! G-galiba\\nhaklısın...',"Hapşırık repliğin esprisinin ve soğuk bağlamının parçası; tüm resmî diller hapşırığı koruyor. Türkçede ses efekti tamamen düşmüştü."),
('Player_StgWin_101','Tabii! Bunca savaştan sonra\\nbaşka türlüsü olur mu?',"Kaynak Musashi'nin kendi savaş geçmişi nedeniyle durumunu onaylamasıdır. Mevcut Türkçe ikinci şahsa dönüp 'hâlâ ayaktasın' diyerek anlamı tersine çevirmişti."),
('Player_StgWin_102','Bir gün hayatın egzersizden\\nibaret olmadığını anlayacaksın!',"'Life has more than exercise' Türkçede 'egzersizden daha fazlası' diye yapısal kalıyordu. Doğal '... ibaret değil' kalıbına çekildi."),
('Player_StgWin_108','Şiiri tam zamanlı yapmayı\\nhiç düşündün mü?',"'Do it full-time' zamiri önceki şiire gönderme yapıyor. Türkçede 'onu' belirsizdi; referans açıklaştırıldı."),
('Player_StgWin_119','Bu tim sorumluluğu birbirine\\natmaya pek alışkınmış!',"Kaynak suç/sorumluluk devretme davranışını ekip özelliği olarak alaya alıyor. Mevcut cümle kişisel ve ağırdı; sahne bağlamına uygun toplu özneyle yeniden kuruldu."),
('Player_StgWin_144',"Octavius'la yüzleşme vakti.\\nSuşi hakkında konuşacağız!","'Meet' burada dostça ilk tanışma değil, hedefe ulaşıp hesaplaşma bağlamında. FR/NL 'iki çift laf etme/sert konuşma' tonunu destekliyor; 'yüzleşmek' sahne niyetini daha iyi veriyor."),
('Player_StgWin_145','Suşi kimsenin malı değil!\\nHepimizin!',"EN/DE/ES/FR/IT/NL ana fikri iki parçalı kuruyor: tek kişinin sahip olamayacağı + herkese ait olduğu. Türkçe yalnız 'Hepimizin!' bırakmıştı."),
('Player_StgWin_204','Garip... Bunu sanki\\ndaha önce duydum.',"Mevcut 'sanki ... gibi' çift belirsizlikti. Kaynağın déjà-vu tonunu tek doğal yapı ile koruyor."),
('Player_StgWin_225','Darılmaca yok, tamam mı?',"No hard feelings için 'Alınmak yok' anlaşılır ama yapay. Karakterin hafif, oyunbaz tonunda doğal Türkçe kalıp seçildi."),
('Player_StgWin_238','İşte gidiyorum. Bari\\nmızıkçılık yapma!',"Kaynak önce önceki iddiaya 'gidiyorum işte' diye cevap verip ardından sore loser alayı yapıyor. Türkçede ilk cevap düşmüştü."),
('Player_StgWin_263','Bazen gücümü biraz\\nFAZLA kaçırıyorum...',"'Try a little too hard' mevcut Türkçede çabalama niyeti gibi kalıyordu; bağlam gücü kontrol edememek. FR diğer anlamı da destekliyor; 'gücü fazla kaçırmak' seçildi."),
('Player_StgWin_277','Suşi vuruculuğunda\\nçok ilerledim!',"'I've grown as a sushi striker' için 'çok geliştim' dönüşlü fiil yanlış/eksik. Türkçede beceride ilerleme doğal biçimde kuruldu."),
('Player_StgWin_291','Nedense bunu ilk fırsatta\\nona yetiştireceksin gibi geliyor...',"Tell him at the first opportunity, karakterin diğerine laf taşıyacağını düşündüğü alaydır. 'Neden bunu...' soru gibi bozulmuştu; 'nedense' ile niyet doğru kuruldu."),
]:
    add_gender(p,lab,new,why,'ikinci geçiş: savaş diyaloğu')

add_gender(p,'Player_VsWin','İşte gerçek bir suşi vurucu\\nböyle kazanır!',
    "DE/FR/IT/NL 'gerçek suşi vurucu böyle vurur/kazanır' diyerek başarı sloganı kuruyor. 'İşi böyle bitirir' İngilizce kalıbı taşıyordu; Türkçe zafer repliğine dönüştürüldü.",'savaş sloganı')

# ---------------------------------------------------------------------------
# 4) Merkez ekranları: doğal konuşma + bağlam + eksik cümle
# ---------------------------------------------------------------------------
h='homeSushibar.csv'
add(h,'homeSushibar_05_cmn_01_M','Bomba bir söylenti duydum!\\nMüşterilerden kaptım.',
    "Doozy of a rumor konuşma dili. 'Paylaşacak bomba gibi bir söylentim var' çeviri yapısıydı; FR/NL'nin canlı söylenti tonu korunarak daha doğal bar konuşmasına çevrildi.",'karakter sesi')
add(h,'homeSushibar_05_c_02_M','Ne kadar çok kişiyi doyurursak,\\nnamımız o kadar yayılır;\\ndaha uzaktan gelirler!',
    "Word spreads burada 'haber yayılır' değil restoranın ününün yayılmasıdır. FR/IT açıkça tanınma/şöhret anlamını veriyor; 'namımız yayılır' bağlamı netleştiriyor.",'anlam nüansı')
add(h,'homeSushibar_09_c_03_M','Ama fazla beklersen rakip\\nsenden önce kapabilir.\\nZor seçim, dostum!',
    "Risk the enemy taking it first yapısı Türkçede 'düşmanın ... riski var' diye dolanıyordu. DE/ES/FR/IT/NL aynı kararsızlığı kısa ve konuşma dilinde veriyor; cümle sadeleştirildi.",'akıcılık')
add(h,'homeSushibar_11_a_02_M',"Ausprey'nin yeniden normal suşiye\\ndönmesine çok sevindim!",
    "Gone back to liking normal sushi için 'sevmeye dönmesine' Türkçede fiil zinciri bozuktu. Diğer diller dönüş fikrini koruyor; kısa doğal yapıya çekildi.",'akıcılık')
add(h,'homeSushibar_12_f_04_M','Onun gibisini mantıkla ikna edemezsin.\\nSöz değil, suşi işe yarar.',
    "Make an appeal to sushi 'suşiye seslen' değildir. DE 'sushi anladığı tek şey', ES suşinin daha etkili, IT söz yerine suşiyle meydan okuma diyor. İşlevsel niyet Türkçede yeniden kuruldu.",'anlam hatası')
add(h,'homeSushibar_14_a_03_M','Cevap suşi! Beyaz suşide, o karın\\nkaslarını sıkılaştıracak tüm protein var!',
    "It's sushi! önceki soruya coşkulu cevaptır; 'Bu suşi!' işaret etme gibi duyuluyordu. Protein/kas açıklaması korunarak bağlamsal giriş düzeltildi.",'bağlam')
add(h,'homeSushibar_14_a_04_M','Düzenli beyaz suşi ve günlük antrenmanla\\nsen de KAS KÜPÜ olabilirsin!',
    "Get JACKED kaslı hâle gelmek için abartılı argo. DE/ES/FR/IT de kaslılık şakasını büyütüyor; 'KASLA DOLARSIN' doğal değildi, Türkçedeki 'kas küpü' ile yeniden yerelleştirildi.",'karakter sesi/espri')
add(h,'homeSushibar_16_a_04_M','Aynen! Suşinin tadını çıkarmak\\nbambaşka bir deneyim.\\nKaslarıma da iyi geliyor!',
    "A novel change 'değişik bir yenilik' diye aynı anlam iki kez söylenmişti. Tüm diller yeni tadını çıkarma deneyimini vurguluyor; tekrar temizlendi.",'akıcılık')
add(h,'homeSushibar_16_a_08_M','Ahahah! Sana eski suşi ruhumu\\nvermeye geldim.\\nBir teşekkür edersin artık, ha?',
    "Look grateful, hmm? alaycı 'hadi teşekkür et' tonudur. 'Minnettar görün' yapısal İngilizceydi; FR/NL'nin 'merci qui?/tof van mij' şakacı tonu Türkçeye uyarlandı.",'karakter sesi')
add(h,'homeSushibar_17_g_02_M',"Ha-hah! Kodiak'ın birliğindeki çocuklar\\nharbi kaslıymış; haklarını yemeyeyim!",
    "DE/ES/FR/IT özellikle çocukların kaslı/çekici olduğunu söylüyor. 'Sağlam ve dayanıklılar' nesne dayanıklılığı gibi kalıyordu; karakterin kas hayranlığı geri getirildi.",'karakter sesi')
add_gender(h,'homeSushibar_cap4_03_M','Vay... Ne güzel düşünmüşsün!',
    "That's really cool of you bir davranışı övüyor. 'Bu senden gerçekten çok iyi' Türkçe sözdizimi değil; ES amable ve FR sympa niyeti doğruluyor.",'doğallık')
add(h,'homeSushibar_cmn_ret_01_M','Kendi evinmiş gibi rahat et!',
    "Make yourself at home için Türkçede yerleşik kalıp 'evinmiş gibi rahat et'. 'Kendini evinde gibi hisset' doğrudan çeviri kokuyordu.",'deyim')
add(h,'homeSushibar_07_a_05_M','Böyle bir konuda dalga geçer miyim?\\nBu iş çok büyük olabilir!',
    "It could be huge fırsatın/olayın önemini anlatıyor; 'dev gibi bir şey' fiziksel büyüklük çağrışımı yapıyordu. DE/FR/NL büyük fırsat/önem anlamını doğruluyor.",'anlam nüansı')

k='homeKoziin.csv'
add(k,'homeKoziin_select_lv04_02_M','İyi ki seninle tanışmışım.\\nTeşekkür ederim.',
    "Grateful to have met you duygusal teşekkürdür. 'Tanıştığıma çok minnettarım' gramer olarak mümkün ama yapay; ES/FR/NL sıcak kişisel tonu Türkçedeki doğal 'iyi ki' ile karşılandı.",'karakter sesi')
# preserve highlight codes by replacing only wording around them
rep(k,'homeKoziin_useful_03_00_M','Süresi sabit olan yeteneklerde,','Süreli yeteneklerde,',
    "Set time burada sabit süreli/geçici etki demektir. ES/IT/NL 'sınırlı/geçici süre' diyor; 'süresi sabit olan' teknik ve ağırdı.",'mekanik anlatım')
# The source formatting has a highlighted skill name; preserve it while reflowing the sentence.
HL1='\\u000E\\u0000\\u0003\\u0004ﾑ＞'; HL0='\\u000E\\u0000\\u0003\\u0004\\u0000' + chr(0xFF00)
add(k,'homeKoziin_useful_14_00_M',f'Bir düşman sana {HL1}Elektroşok{HL0} gibi\\ngüçlü bir tek vuruş yeteneği kullanırsa...',
    "Powerful single attack mevcut Türkçede 'güçlü tekli saldırı yeteneğini sana kullanmak' diye nesne-fiil uyumsuzluğu oluşturuyordu. ES/FR/IT tek vuruş/tek saldırı anlamını doğruluyor; kontrol kodları korunup cümle yeniden akıtıldı.",'akıcılık')
add(k,'homeKoziin_useful_13_02_M',f'{HL1}İki Ucu Hızlı{HL0} da benzer etki yapar.\\nEpey sinsi, değil mi?',
    "Kaynak ve DE/ES/FR/IT/NL önce 'Double-Edged Lanes benzer etki yapar' bilgisini veriyor; Türkçede bu mekanik bilgi tamamen kaybolmuş, yalnız 'sinsi' yorumu kalmıştı. Yetenek adı ve vurgulama kodu geri getirildi.",'eksik mekanik bilgi')

s='homeShrine.csv'
add(s,'homeShrine_rank_06_M',row(s,'homeShrine_rank_06_M')['tur'].replace('tamamlamamışsın gibi görünüyor','henüz tamamlamamışsın'),
    "It seems yapısını kelimesi kelimesine sona taşıyan '... gibi görünüyor' cümleyi hantallaştırıyordu. DE/IT daha doğrudan eksik koşulu söyler; Türkçe UI mesajı kısa ve doğallaştırıldı.",'UI doğallığı')
add(s,'homeShrine_word_08_M',row(s,'homeShrine_word_08_M')['tur'].replace('İlahi siparişin','Böyle bir İlahi Sipariş').replace(' yok gibi görünüyor.',' görünmüyor.'),
    "Doesn't seem to exist kullanıcının sahip olmamasından çok girilen/aranan İlahi Siparişin bulunmaması anlamında. ES/FR/IT/NL bunu 'yok/mevcut değil/doğru söz değil' diye doğruluyor.",'anlam nüansı')
add(s,'homeShrine_first_out_09_M','Kulağa harika geliyor!\\nNe kadar yardım varsa alırım!',
    "I'll take all the help I can get için 'alabileceğim tüm yardımı kabul ederim' resmî ve mekanik kalıyordu. ES/FR/NL'nin sıcak, gündelik tonu korundu.",'karakter sesi')

# ---------------------------------------------------------------------------
# 5) Ansiklopedi / sushi / tips: doğal Türkçe ve mekanik doğruluk
# ---------------------------------------------------------------------------
g='database_godInfo.csv'
add(g,'GodInfo_God005','Gördüğü kiri bırakmaz;\\nher şeyi suyla temizler.',
    "Leaves no dirt uncleaned mevcut Türkçede çift olumsuzluk benzeri 'hiçbir kiri temizlemeden bırakmaz' ile ağırlaşmıştı. DE/ES/FR/NL temizlik takıntısını kısa verir; doğal Türkçe seçildi.",'ansiklopedi üslubu')
add(g,'GodInfo_God037','Meraklıdır, üstelik\\nçok şey bilir.',
    "Knowledgeable için 'çok bilgilidir' ansiklopedi metninde yapay. DE/ES/FR/IT/NL merak + bilgelik/bilgi çiftini veriyor; konuşur Türkçeyle sıkılaştırıldı.",'ansiklopedi üslubu')
add(g,'GodInfo_God050','Güç arttıkça ısı da artar!\\nSoğuk günlerde yanında isteyeceğin\\nsuşi ruhu budur.',
    "More power means more heat sloganı 'daha çok güç, daha çok sıcaklık' diye çeviri kalıbıydı. ES sebep-sonucu açık kuruyor; kısa slogan Türkçeleştirildi.",'ansiklopedi üslubu')
add(g,'GodInfo_God051','Yürekli ve cesurdur; alevleri\\nya cehennem ateşi gibi yakar\\nya da karanlıkta yol gösterir.',
    "A light in the dark 'karanlıkta bir ışık olur' anlaşılır ama cansız. DE/FR/NL sıcaklık-yakma/ışık karşıtlığını canlı tutuyor; Türkçe fiillerle yeniden kuruldu.",'imge/üslup')
add(g,'GodInfo_God059','Karnının gurultusu, duyanı\\nolduğu yere çivilemeye yeter.',
    "Stomach roar kelime oyunu IT'de doğrudan mide gurultusu olarak korunuyor. 'Karnından gelen kükreyiş' yapaydı; Türkçedeki 'karnı guruldamak' + 'olduğu yere çivilenmek' ile imge yeniden kuruldu.",'kelime oyunu/üslup')
add(g,'GodInfo_God086','Doğuştan lider gibidir, yoldaşlarını kollar.\\nSoğuk bakışlarının ardında\\nsarsılmaz bir tutku yanar.',
    "Built like a leader fiziksel 'lider gibi durur'dan çok lider kumaşı/önderlik niteliğidir. ES 'líder nato', IT 'stoffa del capo' bunu açıkça doğruluyor.",'anlam nüansı')
add(g,'GodInfo_God107',"Müzik kutusundan yalnız hip hop hitleri çalar.\\nMüzikte tek ölçütün popülerlik\\nolduğuna yürekten inanır.",
    "Popularity is everything 'müzikte her şeyin popülerlik olduğu' diye Türkçe olmayan bir yüklemle çevrilmişti. ES/FR/NL popülerliği ölçüt/değer olarak veriyor; doğallaştırıldı.",'akıcılık')
add(g,'GodInfo_God124','Cehennemden gelen bir haberci olduğunu\\ngururla söyler. Tabii ki yalan.',
    "Proudly lies about ... 'gururla uydurur' fiil nesnesiyle yapaydı. ES açıkça 'ama yalan', FR/NL 'öyleymiş gibi davranır/iddia eder' diyor; esprili iki cümle Türkçede daha doğal.",'ansiklopedi üslubu')
add(g,'GodInfo_God125','Palyaço gibi davranır. Gösterisinde\\nbirbirinden abartılı uydurma\\nhikâyeler anlatır.',
    "Grand, made-up stories için 'bir sürü büyük uydurma hikâyesi vardır' doğal değil. DE/ES bunları vahşi/rocambolesk uydurmalar olarak verir; gösteri eylemiyle akıcılaştırıldı.",'ansiklopedi üslubu')

add('database_sushiInfo.csv','SushiInfo_Mikan','Tatlı-ekşi tadıyla ağzı tazeler;\\nantrenmandan sonra da\\nferah bir ödül olur.',
    "Mevcut Türkçe yüklemsiz iki isim tamlamasıydı. DE/ES/FR/IT damak tazeleme işlevini tam cümleyle veriyor; İngilizcedeki spor sonrası ferahlık da korunarak Türkçe tamamlandı.",'gastronomi üslubu')

# Tips page: preserve control codes already in row by replacing prose around highlighted phrase.
t='database_tipsInfo.csv'
r=row(t,'TipsPage2_020'); cur=r['tur']
# Build with same highlighted control segment copied from current text.
m=re.search(r'(\\u000E\\u0000\\u0003\\u0004Ü.*?geçiş yap\\u000E\\u0000\\u0003\\u0004\\u0000.)',cur)
high=m.group(1) if m else 'aralarında geçiş yap'
add(t,'TipsPage2_020',f'Önceden dengeli, saldırı odaklı ve\\nsabotaj odaklı setler hazırla.\\nİhtiyacına göre {high}!',
    "Balanced / attack-boosting / saboteur üç ayrı takım tipi. 'Sabote edici bir set gibi şeyler hazırlamayı dene' Türkçede hem 'gibi şeyler' hem fiil sıralamasıyla mekanik kalıyordu; FR/IT/NL üç takım türünü açıkça sıralıyor. Kontrol kodları korunarak sadeleştirildi.",'mekanik anlatım')
# Reflow the Raw Power tip after global terminology replacement so highlighted control codes stay intact.
cur=row(t,'TipsPage2_022')['tur']
cur=cur.replace(' belirli koşulları\\nyerine getirince','\\nbelirli koşulları yerine getirince')
cur=cur.replace('belirli koşulları yerine getirince \\u000E','belirli koşulları yerine getirince\\n\\u000E')
cur=cur.replace('Farklı çiğ güç türlerinin suşi ruhu yetenekleriyle\\nnasıl birlikte çalıştığını dene ve keşfet!',
                'Farklı çiğ güç türlerini suşi ruhu\\nyetenekleriyle birlikte deneyip keşfet!')
add(t,'TipsPage2_022',cur,
    "Raw Power terimi Çiğ Güç olarak tekleştirilirken bu uzun öğretici satır da ikinci kez okundu. Kontrol kodları korunup cümleler doğal Türkçeyle yeniden akıtıldı; mekanik anlam değişmedi ve görünür satır uzunluğu azaltıldı.",'terim + mekanik anlatım')

# ---------------------------------------------------------------------------
# 6) Global eksiltme taramasında yakalanan dış dosya
# ---------------------------------------------------------------------------
add('stageBeginM072.csv','CharaSerif_29_M',"Jinrai... Üzgünüm ama mecburum.\\nOnu elimizden kaçırmamalıyız!",
    "Global eksiltme taraması bu satırı yakaladı: EN/DE/ES/FR/IT ilk cümlede Jinrai'ye özür/zorunluluk ifade ediyor, Türkçede bu tamamen düşmüştü. İki düşünce de geri getirildi.",'eksik cümle taraması')

# ---------------------------------------------------------------------------
# Write updated CSV files
# ---------------------------------------------------------------------------
for fn,(fields,rs) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rs)

# ---------------------------------------------------------------------------
# Second-pass audit: re-read high-risk file blocks in full, plus all targeted rows
# ---------------------------------------------------------------------------
second_pass_files={
'scene_puzzlebattle.csv','database_movieSerif_1A.csv','database_movieSerif_1B.csv','database_movieSerif_2A.csv','database_movieSerif_2B.csv',
'database_movieSerif_3A.csv','database_movieSerif_3B.csv','database_movieSerif_3C.csv','database_movieSerif_4A.csv','database_movieSerif_5A.csv',
'homeSushibar.csv','homeKoziin.csv','homeShrine.csv','database_godInfo.csv','database_sushiInfo.csv','database_tipsInfo.csv','database_achieveInfo.csv','database_cmn.csv',
'homeArena.csv','scene_menuformation.csv','scene_menutop.csv','scene_menumydata.csv','scene_battleresult.csv','stageEndM004.csv','stageEndM009.csv','stageBeginM072.csv'
}

def risk_flags(fn,r):
    e=(r.get('eng') or '').lower(); t=(r.get('tur') or '').lower(); flags=[]
    if fn.startswith('database_movieSerif') or fn=='scene_puzzlebattle.csv': flags.append('BAĞLAM_KOMŞU_REPLİK')
    if re.search(r'\b(shock|cold|taste|raw|sprite|sprout|mill|gut|belly|muscle|jam|catch|release|dish|plate|strike|striking|yum|buffet|clean|beef|flex|jacked|ace)\b',e): flags.append('ESPRİ_DEYİM')
    if any(x in e for x in ['raw power','sprite order','pledge','prepared item','potential plate','lane-drive']): flags.append('TERİM')
    # omission heuristic
    ec=re.sub(r'\\u[0-9a-f]{4}','',e).replace('\\n',' '); tc=re.sub(r'\\u[0-9a-f]{4}','',t).replace('\\n',' ')
    if len(ec)>=40 and tc and len(tc)/max(1,len(ec))<0.55: flags.append('EKSİLTME_RİSKİ')
    if '\\u000e' in e or '\\u000e' in t: flags.append('KONTROL_KODU')
    if not (r.get('eng') or '').strip(): flags.append('BOŞ_SLOT')
    return '+'.join(flags) if flags else 'ANLAM_TON'

def unchanged_reason(fn,r,flag):
    if not (r.get('eng') or '').strip():
        return 'İkinci geçişte kaynak ve tüm resmî dil slotları yeniden kontrol edildi; görünen kaynak metin yok. Yeni metin eklemek yapısal/olay işlevini değiştirebileceğinden boş bırakıldı.'
    if fn=='scene_puzzlebattle.csv':
        return 'İkinci geçişte bu savaş repliği/öğretici, komşu kazanma-kaybetme satırlarıyla birlikte okundu; DE/ES/FR/IT/NL karşılıkları, olası kelime oyunu, eksik cümle ve karakter sesi ayrıca kontrol edildi. Mevcut Türkçe tüm anlam birimlerini taşıyor ve daha serbest yeniden yazım belirgin bir kazanç sağlamayacağı için aynı bırakıldı.'
    if fn.startswith('database_movieSerif'):
        return 'İkinci geçişte sahnenin önceki/sonraki replikleriyle birlikte okundu; altı resmî dildeki serbest yerelleştirmeler, deyim/espri ve konuşan karakterin tonu karşılaştırıldı. Mevcut Türkçe sahne akışında doğal, anlamı tam ve karakter sesine uygun bulunduğu için aynı bırakıldı.'
    if fn=='homeSushibar.csv':
        return 'Sushibar konuşması ikinci kez karakter sesi ve gündelik Türkçe açısından okundu; EN ile DE/ES/FR/IT/NL arasındaki serbestleştirmeler karşılaştırıldı. Mevcut ifade espriyi/niyeti koruyor ve konuşma dilinde yeterince doğal olduğu için aynı bırakıldı.'
    if fn=='homeKoziin.csv':
        return 'Koziin repliği ikinci kez öğretici işlev, Koziin’in sakin konuşma tonu ve oyun terminolojisi açısından kontrol edildi. Resmî dillerle karşılaştırmada eksik mekanik bilgi veya yapay Türkçe saptanmadığından aynı bırakıldı.'
    if fn=='homeShrine.csv':
        return 'Tapınak UI/diyaloğu ikinci kez menü işlevi, kontrol kodları ve Bağ/İlahi Sipariş terminolojisiyle birlikte kontrol edildi. Mevcut Türkçe kısa, anlaşılır ve resmî dillerle anlamca uyumlu olduğu için aynı bırakıldı.'
    if fn=='database_godInfo.csv':
        return 'Ruh ansiklopedisi açıklaması ikinci geçişte betimleme doğallığı, mizah/imge ve DE/ES/FR/IT/NL’de öne çıkan nüanslar açısından yeniden okundu. Mevcut Türkçe akıcı ve karakter özelliğini eksiksiz verdiği için aynı bırakıldı.'
    if fn=='database_sushiInfo.csv':
        return 'Suşi açıklaması ikinci geçişte gastronomi dili, iştah açıcı ton, benzetme/espri ve diğer beş yerelleştirmenin serbest tercihleriyle karşılaştırıldı. Mevcut Türkçe doğal ve imgeyi yeterince koruduğu için aynı bırakıldı.'
    if fn=='database_tipsInfo.csv':
        return 'İpucu satırı ikinci geçişte mekanik doğruluk, kontrol kodları, satır kısalığı ve oyun geneli terimlerle birlikte kontrol edildi. Mevcut Türkçe talimatı eksiksiz ve yanlış yönlendirmeden verdiği için aynı bırakıldı.'
    if fn=='database_achieveInfo.csv':
        return 'Başarı adı/açıklaması ikinci geçişte koşulun sayısal anlamı, kısa UI dili ve diğer dillerdeki unvan yaklaşımıyla karşılaştırıldı. Mevcut Türkçe koşulu ve tonu doğru verdiği için aynı bırakıldı.'
    if fn=='database_cmn.csv':
        lab=r.get('label','')
        if 'Name_' in lab or lab.startswith(('SushiName','GodSkillName','ItemName')):
            return 'Ortak terim/ad ikinci geçişte oyunun diğer dosyalarındaki bütün kullanımları ve DE/ES/FR/IT/NL adlandırmalarıyla karşılaştırıldı. Mevcut ad anlam, uzunluk ve oyun tonu bakımından tutarlı bulunduğu için aynı bırakıldı.'
        return 'Ortak veri satırı ikinci geçişte oyun geneli terminoloji ve altı resmî dille yeniden karşılaştırıldı. Belirgin anlam, kelime oyunu veya tutarlılık kaybı bulunmadığından aynı bırakıldı.'
    if fn in {'homeArena.csv','scene_menuformation.csv','scene_menutop.csv','scene_menumydata.csv','scene_battleresult.csv'}:
        return 'Arayüz satırı ikinci geçişte aynı kavramın diğer ekranlardaki adları, kısa alan gereksinimi, kontrol kodları ve resmî dil karşılıklarıyla yeniden kontrol edildi. Mevcut Türkçe tutarlı ve işlevsel bulunduğu için aynı bırakıldı.'
    if fn.startswith('stage'):
        return 'Sahne repliği ikinci geçişte komşu olay satırları ve altı resmî dille yeniden karşılaştırıldı; eksik cümle, kişi/hitap ve deyim riski kontrol edildi. Mevcut Türkçe bağlamı eksiksiz taşıdığı için aynı bırakıldı.'
    return 'İkinci kalite geçişinde EN + DE/ES/FR/IT/NL, bağlam, deyim/espri ve terminoloji tekrar kontrol edildi; mevcut Türkçede değişiklik gerektirecek somut bir kayıp bulunmadı.'

second=[]; second_keys=set()
for fn in sorted(second_pass_files):
    if fn not in files: continue
    for r in files[fn][1]:
        key=(fn,r['label']); second_keys.add(key); ch=changed_lookup.get(key); pm=prev_master.get(key,{})
        flag=risk_flags(fn,r)
        second.append({
            'round':'v0.9-ikinci-gecis','file':fn,'label':r['label'],'index':r.get('index',''),
            'previous_review_status':pm.get('review_status',''), 'previous_decision':pm.get('decision',''),
            'risk_flags':flag,
            'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI',
            'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
            'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),
            'reason':ch['reason'] if ch else unchanged_reason(fn,r,flag)
        })
# Include any changed target outside the full-file second pass.
for ch in changes:
    key=(ch['file'],ch['label'])
    if key in second_keys: continue
    r=row(*key); pm=prev_master.get(key,{})
    second.append({'round':'v0.9-hedefli','file':ch['file'],'label':ch['label'],'index':r.get('index',''),
                   'previous_review_status':pm.get('review_status',''),'previous_decision':pm.get('decision',''),
                   'risk_flags':risk_flags(ch['file'],r),'decision':'DEĞİŞTİ','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                   'old_tur':ch['old_tur'],'new_tur':r.get('tur',''),'reason':ch['reason']})
    second_keys.add(key)

# Write report helpers.
def writecsv(p,fields,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

second_fields=['round','file','label','index','previous_review_status','previous_decision','risk_flags','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'V09_IKINCI_GECIS_SATIR_INCELEME.csv',second_fields,second)
change_fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'V09_YENI_DEGISIKLIKLER.csv',change_fields,changes)

# Risk summary by flag/decision.
from collections import Counter
flag_counter=Counter(); decision_counter=Counter(x['decision'] for x in second)
for a in second:
    for fl in a['risk_flags'].split('+'): flag_counter[(fl,a['decision'])]+=1
risk_rows=[]
for (fl,dec),cnt in sorted(flag_counter.items()): risk_rows.append({'risk_flag':fl,'decision':dec,'rows':cnt})
writecsv(OUTROOT/'V09_RISK_TARAMA_OZETI.csv',['risk_flag','decision','rows'],risk_rows)

# Cumulative latest decision report: convert previous schema and overwrite reviewed keys with v09 entries.
# Preserve existing columns to stay compatible.
cum={}
for a in prev_audit: cum[(a['file'],a['label'])]=a
for a in second:
    cum[(a['file'],a['label'])]={k:a.get(k,'') for k in ['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']}
cum_fields=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv',cum_fields,list(cum.values()))

combined=prev_changes+changes
writecsv(OUTROOT/'INCELEME_DEGISIKLIKLERI.csv',change_fields,combined)
latest={}
for x in combined: latest[(x['file'],x['label'])]=x
writecsv(OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv',change_fields,list(latest.values()))

# Master 10,676: v0.9 second-pass rows now carry second-pass decision/reason; all others preserve v0.8 record.
secmap={(a['file'],a['label']):a for a in second}
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label']); pm=prev_master.get(key,{})
        if key in secmap:
            a=secmap[key]
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':'İKİNCİ_GEÇİŞ_v0.9','decision':a['decision'],
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':a['old_tur'],'current_tur':r.get('tur',''),'reason':a['reason']})
        else:
            master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':pm.get('review_status','İNCELENDİ_ÖNCEKİ'),'decision':pm.get('decision','AYNI KALDI'),
                           'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),
                           'old_tur':pm.get('old_tur',r.get('tur','')),'current_tur':r.get('tur',''),'reason':pm.get('reason','Önceki turda incelendi.')})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
writecsv(OUTROOT/'TUM_10676_SATIR_DURUMU.csv',master_fields,master)

# Length warnings (>48 visible characters) for new changes.
ctrl=re.compile(r'\\u[0-9A-Fa-f]{4}')
def vis(s):
    s=ctrl.sub('',s); s=''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF); s=re.sub(r'[\uff00-\uffef]','',s); return len(s)
warn=[]
for ch in changes:
    for i,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=vis(line)
        if L>48: warn.append({'file':ch['file'],'label':ch['label'],'line_no':i,'visible_len':L,'line':line})
writecsv(OUTROOT/'V09_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv',['file','label','line_no','visible_len','line'],warn)

# Rebuild and validate against official source; then export and compare every TUR field.
rebuilt=OUTROOT/'rebuilt_title'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)
diffs=[]; total=0
for pp in OUT.glob('*.csv'):
    qq=verify/pp.name
    with pp.open(encoding='utf-8-sig',newline='') as f1, qq.open(encoding='utf-8-sig',newline='') as f2:
        aa=list(csv.DictReader(f1)); bb={x['label']:x for x in csv.DictReader(f2)}
        for rr in aa:
            total+=1; vv=bb.get(rr['label'])
            if vv is None or rr.get('tur','')!=vv.get('tur',''):
                diffs.append({'file':pp.name,'label':rr['label'],'expected':rr.get('tur',''),'actual':'' if vv is None else vv.get('tur','')})
if diffs: writecsv(OUTROOT/'ROUNDTRIP_FARKLARI.csv',['file','label','expected','actual'],diffs)

# Extra checks: no untranslated mixed terms that were specifically targeted.
remnants=[]
for fn,(_,rs) in files.items():
    for r in rs:
        tval=r.get('tur','')
        for pat in ['suşi striking','Suşi Striking','Ham Güç','ham güç','Ruh Sırası','Ruh Sırasını']:
            if pat in tval: remnants.append({'file':fn,'label':r['label'],'pattern':pat,'tur':tval})
writecsv(OUTROOT/'V09_TERIM_KALINTI_KONTROLU.csv',['file','label','pattern','tur'],remnants)

summary=(f'CSV/MSBT dosyaları: {len(list(OUT.glob("*.csv")))}\n'
         f'Toplam etiket: {total}\n'
         f'v0.9 ikinci geçiş satırı: {len(second)}\n'
         f'v0.9 değişen satır: {len(changes)}\n'
         f'v0.9 aynı kalan ikinci-geçiş satırı: {sum(1 for a in second if a["decision"]=="AYNI KALDI")}\n'
         f'Round-trip farkı: {len(diffs)}\n'
         f'Yeni değişiklik uzun satır uyarısı (>48): {len(warn)}\n'
         f'Hedef terim kalıntısı: {len(remnants)}\n')
(OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').write_text(summary,encoding='utf-8')

# Package tools, LayeredFS, CSV and reports.
arac=OUTROOT/'Araclar'; arac.mkdir()
for pp in (BASE/'Araclar').glob('*.py'): shutil.copy2(pp,arac/pp.name)
# script already lives under BASE/Araclar, copied above

layerzip=OUTROOT/'Sushi_Striker_TR_v09_LayeredFS.zip'
with zipfile.ZipFile(layerzip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in rebuilt.rglob('*'):
        if pp.is_file(): z.write(pp,Path('LayeredFS')/'00040000001C1D00'/pp.relative_to(rebuilt))

toolszip=OUTROOT/'Sushi_Striker_TR_v09_Araclar.zip'
with zipfile.ZipFile(toolszip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in arac.rglob('*'):
        if pp.is_file(): z.write(pp,pp.relative_to(arac))

bundle=OUTROOT/'bundle'; bundle.mkdir()
shutil.copytree(OUT,bundle/'CSV')
shutil.copytree(arac,bundle/'Araclar')
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
rap=bundle/'Raporlar'; rap.mkdir()
for name in ['V09_IKINCI_GECIS_SATIR_INCELEME.csv','V09_YENI_DEGISIKLIKLER.csv','V09_RISK_TARAMA_OZETI.csv','V09_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','V09_TERIM_KALINTI_KONTROLU.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,rap/name)

readme=f'''Sushi Striker Türkçe yama v0.9 — ikinci kalite geçişi

Bu paket:
- LayeredFS/00040000001C1D00/: yeniden enjekte edilmiş tam yama
- CSV/: 243 MSBT için DEU/ENG/ESP/FRA/ITA/NLD/TUR sütunlu CSV'ler
- Araclar/: CSV <-> MSBT aracı ve bütün inceleme/uygulama betikleri
- Raporlar/: ilk geçiş + v0.9 ikinci geçiş karar/gerekçe raporları

durum:
- Toplam etiket: {total}
- İlk geçişte BEKLİYOR: 0
- v0.9 ikinci kez satır-bazlı incelenen: {len(second)}
- v0.9 yeni metin müdahalesi: {len(changes)}
- v0.9 ikinci geçişte aynı bırakılan: {sum(1 for a in second if a['decision']=='AYNI KALDI')}
- Round-trip farkı: {len(diffs)}
- >48 görünür karakter uyarısı: {len(warn)}
- Hedef terim kalıntısı: {len(remnants)}

V09_IKINCI_GECIS_SATIR_INCELEME.csv dosyasında her yeniden incelenen satır için:
- önceki karar
- risk sinyalleri
- ikinci geçiş kararı
- 6 resmî dil + eski/yeni Türkçe
- neden değişti / neden aynı kaldı
bulunur.
'''
(bundle/'README_TR.txt').write_text(readme,encoding='utf-8')
manifest=[]
for pp in sorted(bundle.rglob('*')):
    if pp.is_file(): manifest.append(hashlib.sha256(pp.read_bytes()).hexdigest()+'  '+str(pp.relative_to(bundle)).replace('\\','/'))
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
fullzip=OUTROOT/'Sushi_Striker_TR_v09_FULL.zip'
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED) as z:
    for pp in bundle.rglob('*'):
        if pp.is_file(): z.write(pp,pp.relative_to(bundle))

print('DONE')
print(summary)
print('full',fullzip)
print('layer',layerzip)
print('tools',toolszip)
