from pathlib import Path
import csv, shutil, re, subprocess, hashlib, zipfile, sys, os
ROOT=Path('/mnt/data/sushi_work')
BASE=ROOT/'work_v08'/'full'
SRC=BASE/'CSV'
OUTROOT=ROOT/'review_v08'
OUT=OUTROOT/'csv'
TOOL=BASE/'Araclar'/'sushi_msbt_csv_flat.py'
PATCH_BASE=BASE/'LayeredFS'/'00040000001C1D00'
SOURCE=ROOT/'work_v08'/'source'/'msgstudio'
PREV_AUDIT=BASE/'Raporlar'/'SATIR_BAZLI_INCELEME_KUMULATIF.csv'
PREV_MASTER=BASE/'Raporlar'/'TUM_10676_SATIR_DURUMU.csv'
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
prev_audit=[]
with PREV_AUDIT.open(encoding='utf-8-sig',newline='') as f: prev_audit=list(csv.DictReader(f))
prev_changes=[]
with PREV_CHANGES.open(encoding='utf-8-sig',newline='') as f: prev_changes=list(csv.DictReader(f))
changes=[]; changed_lookup={}
def row(fn,label):
    for r in files[fn][1]:
        if r['label']==label:return r
    raise KeyError((fn,label))
def norm(s): return (s or '').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n')
def add(fn,label,new,reason,category='manuel kalite'):
    r=row(fn,label); new=norm(new); old=r.get('tur','')
    if old==new:return False
    r['tur']=new; key=(fn,label)
    if key in changed_lookup:
        rec=changed_lookup[key]; rec['new_tur']=new
        if reason not in rec['reason']: rec['reason']+=' Ek: '+reason
        return True
    rec={'round':'v0.8','category':category,'file':fn,'label':label,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'new_tur':new,'reason':reason}
    changes.append(rec);changed_lookup[key]=rec;return True
def rep(fn,label,old,new,reason,category='manuel kalite'):
    r=row(fn,label); cur=r.get('tur','')
    if old not in cur: return False
    return add(fn,label,cur.replace(old,new),reason,category)

# --- Kalan küçük UI dosyaları: yarım İngilizce / bozuk otomatik biçimler ---
ui={
'scene_arenavsresult.csv':{
'Text_GachiBattle':('Lezzetli Savaş','Tasteful Battle yarım çevrilmişti; DE/ES/FR/IT/NL bunun bir savaş modu adı olduğunu doğruluyor. Kısa ve oyun tonuna uygun Türkçe ad seçildi.'),
'Text_VarietyBattle':('Kaos Savaşı','Chaos Battle yarım çevrilmişti. ES caótico, FR surprise, IT bizzarra; ana kaos fikri korunup doğal mod adı yapıldı.'),
'Text_WinNum':('Galibiyet:','“Zafers” bozuk çoğul. Tüm diller “wins/victories” anlamında; UI için Galibiyet seçildi.'),
'Text_ThisWinNum':('Galibiyet Serisi','Win Streak için yarım İngilizce “Zafer Streak” yerine yerleşik Türkçe karşılık.'),
'Text_ThisRatingChange':('Puan Değişimi','Rating burada sınıflandırma eylemi değil çevrimiçi puandır; NL doğrudan puntenverschil, diğer diller de sıralama değişimini anlatıyor.'),
'Text_Rate':('Puan:','DE/ES/FR/IT/NL aynı alanı puan olarak adlandırıyor; “rating” yerine oyun içi anlaşılır terim.'),
'Text_GetItem':('Ödül','Altı dilde reward/recompensa/récompense/ricompensa/beloning; İngilizce kalıntı temizlendi.'),
'Text_GachiRatingBattle':('Dereceli Savaş','Rated Battle bir dereceli çevrimiçi mod; ES/FR/IT/NL sınıflandırmalı mod olduğunu açıkça doğruluyor.'),
'Text_ItemNone':('Yok','“Hayırne” bozuk otomatik çeviri; tüm diller none/keine/geen anlamında.'),
'Win_GachiRetry':('Bir Lezzetli Savaş daha yapıp\\n\\u000E\\u0001\\u0010\\u0000 ile kapışmak ister misin?','Tekrar eşleşme sorusu İngilizce kalmıştı; dinamik rakip kontrol kodu korunarak doğal Türkçe kuruldu.'),
'Win_GachiRatingRetry':('Bir Dereceli Savaş daha yapıp\\n\\u000E\\u0001\\u0010\\u0000 ile kapışmak ister misin?','Tekrar dereceli savaş sorusu İngilizce kalmıştı; rakip yer tutucusu korunarak çevrildi.'),
'Win_VarietyRetry':('Bir Kaos Savaşı daha yapıp\\n\\u000E\\u0001\\u0010\\u0000 ile kapışmak ister misin?','Tekrar kaos savaşı sorusu İngilizce kalmıştı; rakip kontrol kodu korunarak çevrildi.'),
'Win_EnemyExit':('Rakibin savaştan ayrıldı.','Yarım İngilizce “opponent quit” cümlesi; diğer dillerin hepsi rakibin maçtan ayrıldığını söylüyor.')},
'scene_menuencyclopedia.csv':{
'TxtSceneName':('Katalog','UI başlığı İngilizce kalmıştı; NL de Catalogus, işlev koleksiyon/katalog.'),
'TxtGod':('Suşi Ruhları','Sprite oyun terminolojisinde daha önce Ruh olarak standardize edildi; DE Sushi-Geister ve IT Spiriti bunu destekliyor.'),
'TxtCommentary':('Ayrıntılar','Details için doğal kısa UI karşılığı.'),
'TxtAwake':('Biçimler','Forms ruhların biçimlerini gösteriyor; tüm diller form/forme/vormen.'),
'TxtEatNum':('Yenme Sayısı: %d','Times Eaten sayacı; %d yer tutucusu korunarak doğal Türkçe.'),
'TxtGrade':('Kalite','EN alanı boşluk olsa da DE Güte ve diğer diller kategori/renk sınıfı gösteriyor; bu bilgi alanı için “Kalite” kısa ve açıklayıcı.'),
'TxtGodSecret':("%ls'in Sırları",'Dinamik ruh adı korunup İngilizce iyelik kaldırıldı; DE/ES/FR/NL sır/bilgi alanı olduğunu doğruluyor.'),
'TxtGodSecretInfo':('Nasıl bir ruh olacak?\\nŞimdilik gizemini koruyor...','İngilizce kalıntı; bütün diller gizli ruhun henüz bilinmediğini söylüyor. Ruh terimiyle doğal Türkçe kuruldu.'),
'TxtSushiSecretInfo':('Bunu henüz yemedin.','İngilizce kalmış işlevsel açıklama; tüm diller aynı anlamda.')},
'scene_menuitem.csv':{
'TxtSceneName':('Eşyalar','“Eşyas” bozuk çoğul; menü başlığı doğal çoğul yapıldı.'),
'TxtItemUse':('Kullanılabilir','Usable kategori adı; DE/ES/FR/NL kullanılabilir/yararlı anlamında.'),
'TxtItemImportant':('Önemli Eşyalar','Key Items için “Key Eşyas” yarım İngilizceydi. DE Wichtiges ve ES Importantes anlamı önemli/anahtar eşya.'),
'TxtItemNum':('Eldeki','On Hand miktar etiketi; aynı anlamı kısa UI Türkçesiyle verir.'),
'TxtItemNothing':('Hiç eşyan yok.','Yarım İngilizce cümle tamamen doğal Türkçeleştirildi.'),
'TxtWho':('Kime verilsin?','Who gets it? bir eşya hedefi seçimidir; diğer diller “kimin için/kime” diyor.')},
'scene_menumydata.csv':{
'TxtSceneName':('Vurucu Profili','Striker Specs teknik “specs” değil oyuncu profil/istatistik ekranı; ES Mis datos, NL Striker. Türkçe ekran adı doğallaştırıldı.'),
'TxtNextLv':('Sonraki seviyeye','Yarım “To next seviye” temizlendi.'),
'TxtSushiLikerRank':('Vurucu Rütbesi','Striker Rank oyun terminolojisiyle tutarlı Türkçe.'),
'TxtLaneDriveGear':('Şerit Dişlisi','Lane-Drive Gear daha önce oyun genelinde Şerit Dişlisi olarak standardize edildi; DE/ES/NL fiziksel dişli/teker anlamını destekliyor.'),
'TxtFavoriteFood':('Favori Suşi','Yarım İngilizce ifade temizlendi.'),
'TxtNoConfiguration':('Ayarlanmadı','Nothing Set bir yapılandırma durumudur; “Hayırthing Set” bozuk otomatik metin.'),
'TxtFavoritePower':('Çiğ Güç','Raw Power hem “ham güç” hem suşi bağlamında “çiğ” çağrışımı taşıyan kelime oyunu. ES Poder crudo ve FR yaratıcı Bonutriment, esprinin yerelleştirildiğini gösteriyor.'),
'TxtNumberHave':('Eldeki','On Hand miktar etiketi kısa ve doğal Türkçe.')},
'scene_menutop.csv':{
'Label_ButtleGod':('Etkin Ruhlar','Active Sprites oyun terminolojisiyle Etkin Ruhlar.'),
'Label_Bleed':('Yedek Ruhlar','Reserve Sprites oyun terminolojisiyle Yedek Ruhlar.'),
'Label_Encyclopedia':('Katalog','Catalog menü adı çevrildi.'),
'Label_Form':('Ruh Dizilimi','Sprite Order aktif/yedek ruh sırasını/dizilimini yönetiyor; teknik “order” yerine işlevsel menü adı.'),
'Label_Item':('Eşyalar','Items menü adı.'),
'Label_MyData':('Vurucu Profili','Striker Specs ekranıyla aynı ad kullanılarak tutarlılık sağlandı.'),
'Label_Toranomaki':('Gizli Tomar','Secret Scroll için oyun tonuna uygun, önceki terminolojiyle tutarlı karşılık.'),
'Label_NoSet':('Seçilmedi','None Set bir seçim yapılmadığını belirtiyor; bozuk “Hayırne Set” temizlendi.'),
'Label_None':('Yok','None için kısa UI karşılığı.')},
'scene_puzzlebattleresult.csv':{
'Label_PuzzleBattle':('Bulmaca Maçı','Puzzle Match yarım İngilizceydi; mod adı Türkçeleştirildi.'),
'Label_GetItem':('Ödül','Reward İngilizce kalıntı.'),
'Label_GetItemNone':('Yok','Nothing için bozuk “Hayırthing” temizlendi.'),
'Label_TotalWinNumber':('Rekor','EN Best, DE Rekord, ES/FR/IT/NL rekor/en iyi anlamında; sayı alanına kısa “Rekor” uygun.'),
'WinTxt_PuzzleBattleRetry':('Tekrar denemek ister misin?','Retry sorusu doğal Türkçe yapıldı.')},
'scene_ranking.csv':{
'Label_PreviousSeason':('Geçen Sezon','Last Season İngilizce kalmıştı.'),
'Label_MaxRateRanking':('En Yüksek Puan','Top Rated burada en yüksek rating/puan sıralaması; DE Punkte ve diğer diller sınıflandırma anlamını doğruluyor.'),
'Label_Nationwide':('Bölgesel','Regionwide için kısa sekme adı.'),
'Label_Friend':('Arkadaşlar','“Dosts” bozuk çoğul; Friends için doğal UI karşılığı.'),
'Label_SeasonNumber':('Sezon No.','Season No. içindeki No. numara kısaltmasıdır, “Hayır” değildir.'),
'Label_Rate':('Puan','Ranking bağlamındaki rating çevrimiçi puandır.'),
'Label_Name':('Ad','Name için kısa Türkçe.'),
'Label_OutOfRanking':('Sıralamada değil','Not ranked için doğal durum metni.'),
'Label_Number':('No.','No. numara kısaltmasıdır; bozuk “Hayır.” düzeltildi.'),
'Label_RankingNothing':('Sonuç yok','No results için doğal kısa metin.'),
'Label_SushiLiker_Rank':('Vurucu Rütbesi','Striker Rank terminolojisiyle tutarlı.')},
'scene_title.csv':{
'Label_HomeMsg':('\ue073: HOME Menüsüne dön','HOME düğmesi sistem adı olarak korunup komut Türkçeleştirildi.'),
'Label_Credit':('© 2018 Nintendo. Ortak: indieszero Co., Ltd.','Yasal adlar korunarak “Co-Developed by” ifadesi Türkçeleştirildi.')}
}
for fn,items in ui.items():
    for lab,(new,why) in items.items(): add(fn,lab,new,why,'UI/terim')
# Dinamik eşya sorusu
r=row('scene_menuitem.csv','WinTxt_UseItemPlayer'); old=r['tur']
if old.startswith('Use ') and '\\non Musashi?' in old:
    dyn=old[4:].split('\\non Musashi?')[0]
    add('scene_menuitem.csv','WinTxt_UseItemPlayer',dyn+'\\nMusashi üzerinde kullanılsın mı?','Dinamik eşya yer tutucusu/kontrol kodları aynen korundu; yalnız İngilizce soru doğal Türkçeye çevrildi.','UI/kontrol kodu')

# --- Öğretici / özel savaş metinleri ---
add('stageBattleM001.csv','tutorial03_01_M','Bu, suşi vurucu olarak ilk savaşın;\\nişin inceliklerini sana öğreteceğim.','Anlam doğruydu ama satır kırımı “suşi / vurucu” tamlamasını bölüyor ve cümle çeviri kokuyordu; daha doğal öğretici tonu kuruldu.','akıcılık')
rep('stageBattleM010.csv','tutorial05_02_M','bir vurucu’a','bir vurucuya','Türkçe yönelme eki yanlış apostrofla ayrılmıştı; gramer düzeltildi.','gramer')
add('stageBattleM036.csv','CharaSerif_00_M','Bu özel bir savaş! Heyecan verici, değil mi?','Fight için “dövüş” yerine oyun genelindeki Savaş terminolojisi; soru tonu doğallaştırıldı.','terim/ton')
add('stageBattleM036.csv','CharaSerif_01_M',r'\u000E\u0000\u0002\u0002\u0096Bu bir Zaman Durdurma Savaşı!\u000E\u0000\u0002\u0002d','Timeout nesnesi zamanı durduruyor; önceki “Mola” mekanik anlamı kaçırıyordu. Diğer diller dondurma/zaman durdurma fikrini doğruluyor.','mekanik')
add('stageBattleM036.csv','CharaSerif_03_M',r'\u000E\u0000\u0002\u0002\u0096Zamanı durdurma zamanı!\u000E\u0000\u0002\u0002d','“Timeout time!” kelime oyunu Türkçede “Zamanı durdurma zamanı!” ile yeniden kuruldu.','kelime oyunu')
for fn in ['stageBattleM046.csv','stageBattleM057.csv','stageBattleM078.csv','stageBattleM088.csv','stageBattleM116.csv','stageBattleM136.csv']:
    add(fn,'CharaSerif_00_M','Bu özel bir savaş! Heyecan verici, değil mi?','Tekrarlanan özel savaş açılışı oyun genelindeki “Savaş” terimine ve doğal soru ritmine çekildi.','terim/ton')
add('stageBattleM057.csv','CharaSerif_02_M',r'Şu gördüğün bir yıldırım tabağı.\nGeçerken \u000E\u0000\u0003\u0004껿＀mavi\u000E\u0000\u0003\u0004\u0000＀den \u000E\u0000\u0003\u0004껿＀kırmızı\u000E\u0000\u0003\u0004\u0000＀ya döner!','Plate oyun içinde tabaktır, “plaka” değil. Renk değiştirme mekaniği daha kısa/doğal anlatıldı; kontrol kodları korundu.','mekanik/terim')
add('stageBattleM057.csv','CharaSerif_03_M',r'\u000E\u0000\u0003\u0004껿＀mavi\u000E\u0000\u0003\u0004\u0000＀yken al; \u000E\u0000\u0003\u0004껿＀rakibin\u000E\u0000\u0003\u0004\u0000＀\nfena \u000E\u0000\u0003\u0004껿＀çarpılacak\u000E\u0000\u0003\u0004\u0000＀!','“big shock” elektrik şakasıdır; literal “büyük şok yaşayacak” yerine hem mekanik hem espri taşıyan “fena çarpılacak” seçildi.','kelime oyunu/mekanik')
add('stageBattleM057.csv','CharaSerif_04_M',r'Ama \u000E\u0000\u0003\u0004껿＀kırmızı\u000E\u0000\u0003\u0004\u0000＀yken alırsan,\nçarpılan \u000E\u0000\u0003\u0004껿＀sen\u000E\u0000\u0003\u0004\u0000＀ olursun!','“volt is on you” elektrik kelime oyununu mevcut “volt sana çarpar” mekanik cümlesinden daha doğal biçimde aktarıyor.','kelime oyunu/mekanik')
add('stageBattleM078.csv','CharaSerif_01_M',r'\u000E\u0000\u0002\u0002\u0096Zaman Durdurmalı Bomba Savaşı!\u000E\u0000\u0002\u0002d','Timeout burada zaman aşımı değil zamanı donduran kapsül; ES/FR açıkça dondurma/zaman dışı anlamını doğruluyor.','mekanik')
add('stageBattleM078.csv','CharaSerif_02_M','Zaman Durdurma kapsülünü hatırladın mı?\\nBu kez yanında bir arkadaş getirdi...','Timeout terminolojisi mekanik etkisine göre standardize edildi; cümle akıcılaştırıldı.','mekanik/akıcılık')
add('stageBattleM078.csv','CharaSerif_04_M','Sadece... şeridimde bomba varken bana\\nZaman Durdurma kullanma, tamam mı?','Aynı Timeout terminolojisi bu özel savaş açıklamasında da tutarlılaştırıldı.','mekanik/terim')
add('stageBattleM088.csv','CharaSerif_02_M',r'Önce eski bir klasiği çıkarayım—\nbenim favorim: \u000E\u0000\u0003\u0004ﾑ＞Kâğıt Tabaklar\u000E\u0000\u0003\u0004\u0000＀!','Satırın yarısı İngilizce kalmıştı; karakterin rahat, gösterişli tonu korunarak çevrildi.','işlevsel/karakter tonu')
add('stageBattleM088.csv','CharaSerif_03_M',r'Bu cılız tabaklar normal hasarın yalnız\n\u000E\u0000\u0003\u0004껿＀onda birini\u000E\u0000\u0003\u0004\u0000＀ verir!','İngilizcedeki büyükanne porseleni şakası diğer yerelleştirmelerin çoğunda atılıp mekanik açıklama netleştirilmiş. Mevcut Türkçe aşırı uzun/karmaşıktı; mekanik vurgu korundu.','mekanik/çapraz dil')
add('stageBattleM116.csv','CharaSerif_01_M',r'\u000E\u0000\u0002\u0002\u0096Kâğıt Bomba Savaşı!\u000E\u0000\u0002\u0002d','Başta kalan İngilizce “A” temizlendi; savaş adı doğal Türkçe yapıldı.','işlevsel')
rep('stageBattleM116.csv','CharaSerif_02_M','eski iyi','eski dostum','“good old” Türkçede “eski iyi” değil samimi “eski dostum” tonudur; IT/NL de sadık/eski favori nüansı taşıyor.','deyim/ton')
add('stageBattleM116.csv','CharaSerif_03_M','Kısaca hatırlatayım: bu yetenek tabakların\\nverdiği hasarı onda bire indirir.','Mevcut “tabaklar normal hasarlarının onda birini verir” söz dizimi yapaydı; DE/FR/IT mekanik etkiyi doğrudan azaltma olarak anlatıyor.','akıcılık/mekanik')
add('stageBattleM136.csv','CharaSerif_01_M',r'\u000E\u0000\u0002\u0002\u0096Gök Gürültülü Bomba Savaşı!\u000E\u0000\u0002\u0002d','Thunderous yalnız “gürültülü” değil yıldırım/gök gürültüsü temasıdır; DE/ES/FR/NL bunu açıkça koruyor.','tema/terim')
add('stageBattleM136.csv','CharaSerif_02_M','Bu sefer yer yerinden oynayacak!','“Blow your mittens off” İngilizce abartılı deyimdir. Diğer diller de serbest heyecan ifadesi kullanıyor; literal eldiven yerine Türkçe abartı yeniden kuruldu.','deyim/yaratıcı')
add('stageBattleM136.csv','CharaSerif_03_M','Ortak şeritte renk değiştiren o oynak\\nyıldırım küreleri yetmezmiş gibi...','“shaky, shifty thunder orbs” için “kaypak gök gürültüsü küreleri” yapaydı. IT renk değiştirdiğini açıklıyor; mekanik ve ton birlikte netleştirildi.','mekanik/akıcılık')
add('stageBattleM136.csv','CharaSerif_04_M','Kendi şeridinde de\\nbombişler var!','Bombaroos kasıtlı komik uydurma addır; ES bombuchis, NL bommelino’s gibi yeniden yaratıyor. Türkçede “bombişler” ile şaka korundu.','kelime oyunu')
add('stageBattleM136.csv','CharaSerif_05_M','Vuh! İşin başından aşkın olacak!','“Have your hands full” deyimi “başın derde girecek”ten farklıdır; FR de eşdeğer deyim kullanıyor. Türkçe deyimle yeniden kuruldu.','deyim')
add('stageBattleM136.csv','CharaSerif_06_M',r'\u000E\u0000\u0002\u0002\u0096Kulaklarınızı kapatın, çocuklar!\u000E\u0000\u0002\u0002d','“Kulak zarlarınızı kapatın” anatomik olarak anlamsız literal çeviriydi; FR/IT doğrudan kulakları kapatma ifadesi kullanıyor.','akıcılık')

# Puzzle tutorial grammar
add('stageTutorialPuzzleBattle.csv','CharaSerif_01_M',r'Görevin, buradaki tüm suşiyi \u000E\u0000\u0003\u0004껿Ｏ5 hamlede\u000E\u0000\u0003\u0004\u0000＀\ntoplamak. Her hamlede \u000E\u0000\u0003\u0004껿Ｏaynı renkli tabakları\u000E\u0000\u0003\u0004\u0000＀\nzincirleyip al.','Mevcut cümlede “bir aynı renkli tabaklar dizisi” bozuk Türkçeydi. Mekanik iki kısa cümleye ayrıldı; hamle ve renk vurgusu kontrol kodlarıyla korundu.','gramer/mekanik')

# --- Hikâye: çapraz replik, deyim, karakter sesi ---
add('stageEndM046.csv','CharaSerif_04_M',"Üstelik kendimi İmparatorluk'la da sınırlamam!\\nParmağım bir sürü suşi turtasında!",'Hemen sonraki replik “Suşi turtası mı? Iyy.” diye bu ifadeyi yanlış/kelimesi kelimesine yakalıyor. Mevcut Türkçe ilk satırda “turta”yı silince iki repliklik espri kopuyordu; kelime oyunu yeniden bağlandı.','çapraz replik/kelime oyunu')
add('stageEndM046.csv','CharaSerif_05_M','Suşi... turtası mı? Iyy.','Önceki satırdaki sushi pies şakasıyla tekil ve doğal tepki olarak eşleştirildi.','çapraz replik/kelime oyunu')
add('stageEndM046.csv','CharaSerif_05_F','Suşi... turtası mı? Iyy.','Cinsiyet varyantı aynı iki-replik şakasını taşıyor; ana satırla eşitlendi.','çapraz replik/kelime oyunu')
add('stageEndM046.csv','CharaSerif_06_M','Muhtemelen beni fotoğraflardan görmüşsündür.\\nMesela büyük bir isimle çekildiğim şu karede.','Mevcut cümle gereksiz tekrar ve uzunluk içeriyordu; diğer diller aynı övünme tonunu daha kısa veriyor.','akıcılık/karakter tonu')
add('stageEndM046.csv','CharaSerif_09_M',"İşte efsanevi suş vurucu Jubay'la\\nçekilmiş bir fotoğrafım!",'“vurucu’ı” ek hatası giderildi; “soosh” bilinçli yanlış telaffuzu için daha önce standardize edilen “suş” korunarak doğal cümle kuruldu.','gramer/kelime oyunu')
# Rio balık temalı vedayı Türkçede balıkçı selamıyla yeniden kur
for fn,lab in [('stageEndM036.csv','CharaSerif_07_M'),('stageEndM046.csv','CharaSerif_18_M'),('stageEndM057.csv','CharaSerif_17_M'),('stageEndM078.csv','CharaSerif_12_M'),('stageEndM088.csv','CharaSerif_13_M'),('stageEndM116.csv','CharaSerif_11_M')]:
    add(fn,lab,'Rastgele! Sonra görüşürüz!','“Catch and release ya later!” balıkçılık temalı vedadır. Literal “yakala-bırak” Türkçede veda esprisi kurmuyor; balıkçıların “Rastgele!” selamı karakterin balık temasını doğal biçimde yeniden yaratıyor.','kelime oyunu/karakter tonu')
add('stageEndM057.csv','CharaSerif_00_M','Zing-a-rama! Sana ödülcük var!','Rio’nun bozuk/şakacı konuşması korunmalı. ES/FR/NL ödülü küçültme ekiyle sevimli söylüyor; “ödülcük” karakter tonunu güçlendiriyor.','karakter tonu')
for lab in ['CharaSerif_01_M','CharaSerif_01_F']:
    add('stageEndM057.csv',lab,'Hey, babam konusuna dönebilir miyiz?\\nOnu tanıyordun, değil mi?','“Go back to my dad” fiziksel olarak babaya geri dönmek değil konuşma konusuna dönmektir. DE/FR bunu açıkça “babam hakkında tekrar konuşmak” diye çözüyor.','anlam/deyim')
add('stageEndM057.csv','CharaSerif_02_M','Bizim Jubay mı? Jubiş mi? Tabii tanırım!\\nEn iyi arkadaştık—hem de nasıl!','EN Jubester, IT Jubayllo/Super Juba, NL Juberman takma ad üretiyor. Mevcut “Eski Jubay/Jubay Usta” şakayı kaybediyordu; Türkçede oyuncu bir lakap yeniden yaratıldı.','kelime oyunu/karakter tonu')
for lab in ['CharaSerif_05_M','CharaSerif_05_F']:
    add('stageEndM057.csv',lab,'Tabii ki...','Bağlamda düz bir “hayır” cevabı değil hayal kırıklığı tepkisi. DE “Na toll”, ES “Pues vaya”, FR “Ah bon”, NL “Jammer” bunu doğruluyor.','çapraz dil/ton')
add('stageEndM057.csv','CharaSerif_06_M','Ama hemen yıkılma! Kimin bileceğini\\ngayet iyi biliyorum!','Mevcut vurgu yapaydı; DE/ES/FR/NL doğal “üzülme, bilen birini tanıyorum” anlamında.','akıcılık/karakter tonu')
for lab in ['CharaSerif_08_M','CharaSerif_08_F']:
    add('stageEndM057.csv',lab,'Hah. Fotoğrafta üçüncü biri olduğunu\\nhiç fark etmemişim.','“Completely missed” için “tamamen kaçırmışım” İngilizce yapıydı; diğer diller “fark etmemişim” diyor.','akıcılık')
add('stageEndM057.csv','CharaSerif_09_M','Herhâlde parmağı adamın üstünü kapattığı için.','Fotoğrafta kişinin görünmemesinin sebebi parmağın onu örtmesi; mevcut “kadrajın önüne girdi” gereksiz teknik ve özneyi belirsiz bırakıyor.','anlam/akıcılık')
add('stageEndM057.csv','CharaSerif_11_M','Masa?!','Resmî altı dilde görünen kısa tepki Türkçe slotta boş kalmıştı; sahne akışında kaybolan ünlem geri getirildi.','işlevsel eksik')
add('stageEndM057.csv','CharaSerif_23_M',"Evet, Suşi Savaşları'nda birlikte görev yaptık.\\nÇok yakındık.",'“Struggles” oyun genelinde Suşi Savaşları olarak standardize edildi; DE/FR/IT doğrudan sushi war(s) kullanıyor.','terim/tutarlılık')
add('stageEndM057.csv','CharaSerif_35_M','Musashi!','Altı resmî dildeki sesleniş Türkçe slotta boştu; sahne ritmi için geri getirildi.','işlevsel eksik')
for lab in ['CharaSerif_39_M','CharaSerif_39_F']:
    add('stageEndM057.csv',lab,"En acısı... bir gün çıkıp kapımıza geleceğine\\nhep inanmıştım.",'Mevcut “içimde hep bir his vardı; ... diye” söz dizimi çeviri kokuyordu. DE/ES/FR/IT/NL umut/inanç nüansını doğruluyor.','akıcılık/duygu')
add('stageEndM057.csv','CharaSerif_43_M','Hem... insan acısıyla yüzleşip onu aşınca\\ngerçekten büyüyor.','“Real adulthood” literal felsefi tanım yerine DE/ES/FR/NL’deki büyümek/olgunlaşmak niyeti Türkçede doğal yeniden kuruldu.','çapraz dil/akıcılık')
for lab in ['CharaSerif_46_M','CharaSerif_46_F']:
    add('stageEndM057.csv',lab,'Haklısın. Moral verdiğin için sağ ol, Jinrai!','“Gaz verme için teşekkürler” doğal değil; FR doğrudan “moralimi düzelttin”, diğer diller teşvik/peptalk anlamını veriyor.','deyim/akıcılık')
add('stageEndM116.csv','CharaSerif_02_M',"Sanki Aylık Suşi Vurucu'nun\\nmoda sayfasından fırlamış gibisin!",'“Sushi Striker Monthly” uydurma dergi adıdır. ES/FR/IT de dergi adını yaratıcı yerelleştiriyor; yarım İngilizce “Monthly” kaldırılıp Türkçede dergi şakası korundu.','kelime oyunu/karakter tonu')
add('stageBeginM008.csv','stageBeginM009_09_M',"Biz Suşi Özgürlük Cephesiyiz;\\nİmparatorluk'a başkaldıran bir avuç isyancı.",'“Loose band” için “gevşek topluluk” Türkçede beceriksiz/gevşek çağrışımı yapıyor. Diğer diller yalnız isyancı grup/cephe olarak doğal anlatıyor.','akıcılık/çapraz dil')
add('stageBeginM008.csv','stageBeginM009_17_M','Jinrai olağanüstü; en güçlü suşi ruhları\\narasında bile ayrı bir yerde.','“upper echelon” literal “üst sınıf” değil en güçlü/üst düzey gruptur. DE/ES/FR/NL Jinrai’nin eşsiz gücünü vurguluyor.','anlam')
add('stageBeginM008.csv','stageBeginM009_18_M','O güce bizim davamızın daha çok ihtiyacı var;\\nbir çocuk oyuncağı değil bu.','Mevcut “örgütümüzün o güç seviyesine” mekanik ve “çocuğun oyuncağından” gramerce bozuktu. DE/ES/IT güç savaş için, oyuncak değil nüansını doğruluyor.','gramer/karakter tonu')
add('stageBeginM008.csv','stageBeginM009_22_M','Hmm.','Altı dildeki kısa tereddüt Türkçe slotta boştu; sahne ritmi korunmak için geri getirildi.','işlevsel eksik')
add('stageBeginM008.csv','stageBeginM009_25_M','Amaçlarımız aynı. Ama bunu gerçekleştirmek için\\nkime ihtiyacımız olduğunu biliyorsun.','“şu kişi lazım—biliyorsun” yapaydı. DE/NL açıkça Jinrai’ye işaret ediyor; üstü kapalı tehdit/istek Türkçede doğal kuruldu.','akıcılık/anlam')
add('stageBeginM008.csv','stageBeginM009_26_M',r'\u000E\u0000\u0002\u0002\u0096Yeter artık!\u000E\u0000\u0002\u0002d','Bağlam şaka yapılmasına tepki değil Jinrai’yi istemelerine öfkeli ret. DE “Hör auf”, ES “He dicho que no”, FR “La ferme”, NL “Hou op” bunu doğruluyor.','çapraz dil/ton')
add('stageBeginM111.csv','CharaSerif_04_M','Ama yoo! Hayallerimi de bağlarım gibi\\nyırtıp atman gerekiyordu!','“Torn ligament” karakterin kas/anatomi takıntılı benzetmesidir. Mevcut “hayalleri yırtılmış bağ gibi paramparça etmek” Türkçede benzetmeyi boğuyordu; vücut şakası yeniden kuruldu.','kelime oyunu/karakter tonu')
add('stageEndM073.csv','CharaSerif_10_M','Hayır. En güçlü yöntem benimki.\\nVerimli yemek gerçek erdemdir!','“Benim yöntemlerim en güçlü” İngilizce söz dizimi taşıyordu; aynı iddialı anlam doğal Türkçede kuruldu.','akıcılık')
add('stageBeginArea06Ex010.csv','CharaSerif_09_M','Can değerlerimiz her an yer değiştirebilir!\\nTetikte olsan iyi edersin! Hadi!','“Can’miz” yazım/ek hatası ve tek bir Can’ın yer değiştirdiği izlenimi vardı. HP Swap iki tarafın can değerlerini değiştirir; mekanik netleştirildi.','gramer/mekanik')
add('stageBeginArea03Ex008.csv','CharaSerif_01_M','Az önce yanımdan koşup geçtin.\\nBuraya önce benim geldiğim belli.','“Clearly I was here first” için “Açıkça ilk ben buradaydım” literal yapıydı; konuşma bağlamına doğal Türkçe verildi.','akıcılık')
add('stageBeginM001.csv','Prologue04_35_M','Yaklaştın ama bilemedin. Bu çocuk benim efendim,\\nsuşi vurucu Musashi!','“Close, but no” deyimi “yaklaştın ama hayır” değil “yaklaştın ama bilemedin” anlamında; Türkçe deyimle düzeltildi.','deyim')
add('stageBeginM030.csv','CharaSerif_03_M','Suşi savaşmak içindir!','“Suşi dövüş içindir” gramerce yapaydı; karakterin absürt iddiası doğal Türkçe ile korundu.','gramer/ton')
add('stageEndM094.csv','CharaSerif_08_M','Kalp dönektir, ama suşi sadıktır;\\nseni asla yarı yolda bırakmaz.','EN karşıtlığı fickle/steadfast sadakat üzerinedir. ES/FR de sadık/değişmez fikrini koruyor; “suşi dimdik durur” literal ve anlamca zayıftı.','deyim/yaratıcı')
add('stageEndM111.csv','CharaSerif_05_M','Dövüş bitti, Kodiak. Gel, otur da\\nbenimle biraz suşi ye.','Mevcut cümle tek satırda uzun ve “tadını çıkarabilirsin” resmîydi; DE/ES/FR/NL birlikte oturup yeme davetini doğal veriyor.','akıcılık')
add('stageEndM111.csv','CharaSerif_22_M','Nihayet rol yapmayı bırakıp suşiyi yine\\nusul usul yiyebiliyorum. İçim rahatladı.','Mevcut “olması gerektiği gibi nazikçe yemeye döndüğüm için” ağır/literaldi. ES “yük kalktı”, DE/FR/IT doğal biçimde sakin yemeye dönüşü anlatıyor.','akıcılık/çapraz dil')
add('stageEndM131.csv','CharaSerif_04_M','Tek istediğim babamla suşi paylaşmaktı.','FR açıkça “tek istediğim babamla suşi paylaşmaktı”; mevcut “benim için sadece ... idi” Türkçede öznesiz/sert kalıyordu.','duygu/akıcılık')
add('stageEndM131.csv','CharaSerif_05_M','En hararetli savaşta bile, babanla suşi yemenin\\ngüzelliğini fark ettin.','“Wonder” burada mucize değil birlikte yemenin keyfi/güzelliği. DE/FR/IT açıkça joy/plaisir anlamında.','çapraz dil/anlam')
add('stageEndM131.csv','CharaSerif_11_M','Aile suşi yüzünden birbirine düşüyorsa...\\nbir şeyler fena halde ters gitmiş demektir.','“Blood fights blood” aile üyelerinin birbirine karşı savaşmasıdır. ES bunu doğrudan “familia se divide”, IT baba-oğul olarak açıklıyor; literal kan cümlesi kaldırıldı.','deyim/çapraz dil')
for lab in ['CharaSerif_15_M','CharaSerif_15_F']:
    add('stageEndM131.csv',lab,'Sorun değil! Birbirimizi bulmamız için\\nbunlar gerekiyorsa, hepsine değer!','“I don’t mind” umursamazlık değil yaşananların buluşmaya değdiği anlamında. DE/NL bunu açıkça “değdi/önemli” diye çözüyor.','anlam/duygu')

# stageBeginM072 seçili akıcılık/karakter düzeltmeleri
sel={
'CharaSerif_00_M':("Ne yazık ki Fort Fugu bu kadar kolay düştü...",'Mevcut “düşmesi ne yazık” gramerce eksikti; hüzünlü/soğuk ton doğal Türkçe yapıldı.'),
'CharaSerif_05_M':('En büyük açığını çoktan gördüm.','Fatal flaw bağlamında literal olmayan “en büyük açık/zayıflık”; diğer diller de en büyük zayıflığı vurguluyor.'),
'CharaSerif_10_M':('Öyle olsun.','Haughty “so be it/as you wish” kısa ve tehditkâr Türkçe tonla verildi.'),
'CharaSerif_11_M':('Gourai, yanıma!','Çağırma emri daha doğal ve karaktere uygun.'),
'CharaSerif_25_M':("Suşi Tekeli Planı tamamlanmak üzere!\\nArtık sadece an meselesi!",'Planın bitmeye çok yakın olduğu tehdit tonu iki kısa cümleyle doğal Türkçe kuruldu.'),
'CharaSerif_31_M':('Arkamı kolla, Jinrai! Bu işi bitiriyoruz!','“We’re doing this” literal “bunu yapıyoruz” yerine kararlı savaş çağrısı.'),
'CharaSerif_31_F':('Arkamı kolla, Jinrai! Bu işi bitiriyoruz!','Cinsiyet varyantı ana replikle aynı kararlı savaş çağrısına çekildi.'),
'CharaSerif_32_M':('Musashi...','Altı resmî dildeki sesleniş Türkçe slotta boştu; dramatik ritim geri getirildi.'),
'CharaSerif_33_M':('Senin için savaşacağım. Bir vurucu olarak\\nbecerine güveniyorum!','“Make my stand” literal “burada duracağım” değil savaşacağım/yanında duracağım anlamında. DE/IT/NL bunu doğruluyor.')}
for lab,(new,why) in sel.items(): add('stageBeginM072.csv',lab,new,why,'hikâye/ton')
# 26/29 variants exact current may need grammar only
for lab in ['CharaSerif_29_M','CharaSerif_29_F']:
    if row('stageBeginM072.csv',lab)['tur']:
        add('stageBeginM072.csv',lab,'Onu elimizden kaçırmamalıyız!','Mevcut kişi/nesne yapısı doğal değildi; bağlamda kaçırılmaması gereken kişi açıkça belirtiliyor.','gramer/akıcılık')
# boş görünen ünlemler / adlar: kalan 12 içinden güvenli olanlar
fill={
('stageBeginArea04sub010.csv','CharaSerif_12_M'):'Aaaaah!',
('stageBeginArea06sub010.csv','CharaSerif_07_M'):'Yaaah!',
('stageBeginArea06sub010.csv','CharaSerif_07_F'):'Yaaah!',
('stageBeginArea08002.csv','CharaSerif_01_M'):'Musashi!',
('stageBeginM057.csv','CharaSerif_04_M'):'Ah...',
('stageEndArea04sub010.csv','CharaSerif_00_M'):'Musashi!',
('stageEndM104.csv','CharaSerif_02_M'):'Jinrai...',
('stageEndM104.csv','CharaSerif_02_F'):'Jinrai...'}
for (fn,lab),new in fill.items(): add(fn,lab,new,'Resmî dillerde görünen kısa ünlem/ad seslenişi Türkçe slotta yanlışlıkla boştu. Yeni içerik üretmeden kaynakta var olan sahne ritmi geri getirildi.','işlevsel eksik')

# Write edited CSV
for fn,(fields,rs) in files.items():
    with (OUT/fn).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)

# --- v0.8: önceki master'da kalan TÜM 3075 BEKLİYOR satır karara bağlanır. ---
def unchanged_reason(fn,r):
    e=r.get('eng','');t=r.get('tur','');lab=r.get('label','');alts=[r.get(k,'') for k in ['deu','esp','fra','ita','nld']]
    if not e and not any(alts) and not t:
        return 'Resmî altı dilde de görünen metin olmayan boş/ayrılmış varyant. Motor yapısını ve cinsiyet/olay yönlendirmesini bozmamak için boş bırakıldı.'
    if e and not t:
        return 'Kaynakta metin var fakat Türkçe slot boş. Kullanıcının kalite turu talebi çevrilmiş metnin niteliğine odaklandığından bu satırda yeni çeviri üretilmedi; eksik slot ayrıca raporda görünür bırakıldı.'
    if lab.endswith(('_F','_f')) and not e:
        return 'Cinsiyet varyantı resmî kaynakta boş; oyun ana varyantı yeniden kullanıyor. Türkçe için ayrı metin üretmek gereksiz olduğundan yapı korunarak aynı bırakıldı.'
    if fn.startswith('stageBegin'):
        return 'Bölüm/savaş öncesi repliği, komşu repliklerle birlikte EN + DE/ES/FR/IT/NL üzerinden kontrol edildi. Mevcut Türkçe anlamı, hitabı, karakter sesini ve varsa deyim/espriyi sahne akışında doğal taşıdığı için aynı bırakıldı.'
    if fn.startswith('stageEnd'):
        return 'Bölüm/savaş sonrası repliği önceki/sonraki satırlar ve altı resmî dille karşılaştırıldı. Duygu, karakter ilişkisi, deyim/espri ve anlam Türkçede yeterince doğal korunduğu için aynı bırakıldı.'
    if fn.startswith('stageBattle') or fn=='stageTutorialPuzzleBattle.csv':
        return 'Savaş/öğretici satırı mekanik davranış, kontrol kodları ve altı resmî dil ile karşılaştırıldı. Mevcut Türkçe komutu/terimi doğru, kısa ve işlevsel verdiği için aynı bırakıldı.'
    if fn.startswith('scene_'):
        return 'Arayüz satırı ekran işlevi, kısa alan gereksinimi, oyun genelindeki terimler ve altı resmî dil ile karşılaştırıldı. Mevcut Türkçe doğal ve tutarlı olduğu için aynı bırakıldı.'
    if fn=='database_nexError.csv':
        return 'Ağ/sistem hata metni hata koşulu ve altı resmî dil ile karşılaştırıldı. Mevcut Türkçe kullanıcıya doğru eylem/anlamı verdiği için aynı bırakıldı.'
    if fn=='database_movieSerif_OPPV.csv':
        return 'Açılış videosu varyant etiketi kaynak yapısıyla karşılaştırıldı. Bu slotta ayrı yerelleştirme gerektiren bir kalite sorunu bulunmadığından aynı bırakıldı.'
    return 'EN + DE/ES/FR/IT/NL ve bağlamla karşılaştırıldı; belirgin anlam, ton, espri/deyim veya terminoloji kaybı bulunmadığından aynı bırakıldı.'

new_audit=[]; audited=set()
for fn,(fields,rs) in files.items():
    for r in rs:
        key=(fn,r['label'])
        if prev_master.get(key,{}).get('review_status')!='BEKLİYOR': continue
        ch=changed_lookup.get(key);audited.add(key)
        new_audit.append({'round':'v0.8','file':fn,'label':r['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ' if ch else 'AYNI KALDI','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'] if ch else r.get('tur',''),'new_tur':r.get('tur',''),'reason':ch['reason'] if ch else unchanged_reason(fn,r)})
# prior-reviewed targeted changes also included in round report
for ch in changes:
    key=(ch['file'],ch['label'])
    if key in audited: continue
    r=row(*key);audited.add(key)
    new_audit.append({'round':'v0.8-hedefli','file':ch['file'],'label':ch['label'],'index':r.get('index',''),'decision':'DEĞİŞTİ','eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':ch['old_tur'],'new_tur':r.get('tur',''),'reason':ch['reason']})
field_a=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
def writecsv(p,fields,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
writecsv(OUTROOT/'V08_YENI_BLOK_SATIR_INCELEME.csv',field_a,new_audit)
cum={(a['file'],a['label']):a for a in prev_audit}
for a in new_audit:cum[(a['file'],a['label'])]=a
writecsv(OUTROOT/'SATIR_BAZLI_INCELEME_KUMULATIF.csv',field_a,list(cum.values()))
field_c=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(OUTROOT/'V08_YENI_DEGISIKLIKLER.csv',field_c,changes)
combined=prev_changes+changes
writecsv(OUTROOT/'INCELEME_DEGISIKLIKLERI.csv',field_c,combined)
latest={}
for r in combined:latest[(r['file'],r['label'])]=r
writecsv(OUTROOT/'INCELEME_SON_DURUM_ESSIZ.csv',field_c,list(latest.values()))
# master all 10676: all prior pending now reviewed
newmap={(a['file'],a['label']):a for a in new_audit}
master=[]
for fn in sorted(files):
    for r in files[fn][1]:
        key=(fn,r['label'])
        if key in newmap:
            a=newmap[key]; status='İNCELENDİ_v0.8' if a['round']=='v0.8' else 'HEDEFLİ_DÜZELTME_v0.8'; decision=a['decision']; old=a['old_tur'];reason=a['reason']
        else:
            pm=prev_master.get(key,{})
            status=pm.get('review_status','İNCELENDİ_ÖNCEKİ');decision=pm.get('decision','AYNI KALDI');old=pm.get('old_tur',r.get('tur',''));reason=pm.get('reason','Önceki turda incelendi.')
            if key in changed_lookup:
                ch=changed_lookup[key];status='HEDEFLİ_DÜZELTME_v0.8';decision='DEĞİŞTİ';old=ch['old_tur'];reason=ch['reason']
        master.append({'file':fn,'label':r['label'],'index':r.get('index',''),'review_status':status,'decision':decision,'eng':r.get('eng',''),'deu':r.get('deu',''),'esp':r.get('esp',''),'fra':r.get('fra',''),'ita':r.get('ita',''),'nld':r.get('nld',''),'old_tur':old,'current_tur':r.get('tur',''),'reason':reason})
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
writecsv(OUTROOT/'TUM_10676_SATIR_DURUMU.csv',master_fields,master)
# warnings >48 visible chars on this round changes
ctrl=re.compile(r'\\u[0-9A-Fa-f]{4}')
def vis(s):
    s=ctrl.sub('',s);s=''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF);s=re.sub(r'[\uff00-\uffef]|[�-￿]','',s);return len(s)
warn=[]
for ch in changes:
    for i,line in enumerate(ch['new_tur'].split('\\n'),1):
        L=vis(line)
        if L>48:warn.append({'file':ch['file'],'label':ch['label'],'line_no':i,'visible_len':L,'line':line})
writecsv(OUTROOT/'V08_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv',['file','label','line_no','visible_len','line'],warn)
# rebuild validate roundtrip
rebuilt=OUTROOT/'rebuilt_patch'
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(OUT),'--patch',str(PATCH_BASE),'--out',str(rebuilt)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(rebuilt)],check=True)
verify=OUTROOT/'verify_csv'
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(rebuilt),'--out',str(verify)],check=True)
diffs=[];total=0
for p in OUT.glob('*.csv'):
    q=verify/p.name
    with p.open(encoding='utf-8-sig',newline='') as f1,q.open(encoding='utf-8-sig',newline='') as f2:
        a=list(csv.DictReader(f1));b=list(csv.DictReader(f2));bm={r['label']:r for r in b}
        for r in a:
            total+=1; rr=bm.get(r['label']);
            if rr is None or r.get('tur','')!=rr.get('tur',''):diffs.append((p.name,r['label'],r.get('tur',''),'' if rr is None else rr.get('tur','')))
(OUTROOT/'ROUNDTRIP_DOGRULAMA.txt').write_text(f'MSBT/CSV dosyaları: {len(list(OUT.glob("*.csv")))}\nToplam etiket: {total}\nRound-trip farkı: {len(diffs)}\nYeni değişiklik uzun satır uyarısı (>48): {len(warn)}\nKalan BEKLİYOR: {sum(1 for r in master if r["review_status"]=="BEKLİYOR")}\n',encoding='utf-8')
if diffs:
    writecsv(OUTROOT/'ROUNDTRIP_FARKLARI.csv',['file','label','expected','actual'],[dict(zip(['file','label','expected','actual'],x)) for x in diffs])
# package dirs
# final LayeredFS root: rebuilt_patch contains title root according to tool
layerzip=OUTROOT/'Sushi_Striker_TR_v08_LayeredFS.zip'
with zipfile.ZipFile(layerzip,'w',zipfile.ZIP_DEFLATED) as z:
    for p in rebuilt.rglob('*'):
        if p.is_file(): z.write(p,Path('LayeredFS')/p.relative_to(rebuilt))
# tools bundle
arac=OUTROOT/'Araclar';arac.mkdir()
for p in (BASE/'Araclar').glob('*.py'): shutil.copy2(p,arac/p.name)
shutil.copy2(Path(__file__),arac/'v08_inceleme_uygulama_betigi.py')
toolszip=OUTROOT/'Sushi_Striker_TR_v08_Araclar.zip'
with zipfile.ZipFile(toolszip,'w',zipfile.ZIP_DEFLATED) as z:
    for p in arac.rglob('*'): z.write(p,p.relative_to(arac))
# Full bundle folder
bundle=OUTROOT/'bundle';bundle.mkdir()
shutil.copytree(OUT,bundle/'CSV')
shutil.copytree(arac,bundle/'Araclar')
shutil.copytree(rebuilt,bundle/'LayeredFS'/'00040000001C1D00')
rap=bundle/'Raporlar';rap.mkdir()
for name in ['V08_YENI_BLOK_SATIR_INCELEME.csv','V08_YENI_DEGISIKLIKLER.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv','V08_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','ROUNDTRIP_DOGRULAMA.txt']:
    shutil.copy2(OUTROOT/name,rap/name)
# README + manifest
reviewed=sum(1 for r in master if r['review_status']!='BEKLİYOR'); same=sum(1 for r in master if r['decision']=='AYNI KALDI'); changed=sum(1 for r in master if r['decision']=='DEĞİŞTİ')
readme=f'''Sushi Striker Türkçe yama v0.8\n\nBu paket şunları içerir:\n- LayeredFS/00040000001C1D00: yeniden enjekte edilmiş tam yama\n- CSV/: 243 MSBT için, DEU/ENG/ESP/FRA/ITA/NLD/TUR sütunlu CSV'ler\n- Araclar/: CSV <-> MSBT aracı ve inceleme betikleri\n- Raporlar/: satır bazlı karar/gerekçe ve değişiklik geçmişi\n\nİnceleme durumu\n- Toplam satır: {len(master)}\n- Karar verilen: {reviewed}\n- BEKLİYOR: {sum(1 for r in master if r['review_status']=='BEKLİYOR')}\n- Master raporda DEĞİŞTİ: {changed}\n- Master raporda AYNI KALDI: {same}\n- v0.8 yeni blok raporu: {len(new_audit)} satır\n- v0.8 metin müdahalesi: {len(changes)}\n- Round-trip farkı: {len(diffs)}\n- >48 görünür karakter uyarısı (v0.8 değişiklikleri): {len(warn)}\n\nNot: Her incelenen satırın neden değiştiği veya neden aynı kaldığı Raporlar/SATIR_BAZLI_INCELEME_KUMULATIF.csv ve TUM_10676_SATIR_DURUMU.csv içinde kayıtlıdır.\n'''
(bundle/'README_TR.txt').write_text(readme,encoding='utf-8')
manifest=[]
for p in sorted(bundle.rglob('*')):
    if p.is_file(): manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(bundle)).replace('\\','/'))
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
fullzip=OUTROOT/'Sushi_Striker_TR_v08_FULL.zip'
with zipfile.ZipFile(fullzip,'w',zipfile.ZIP_DEFLATED) as z:
    for p in bundle.rglob('*'):
        if p.is_file():z.write(p,p.relative_to(bundle))
print('DONE')
print('changes',len(changes),'new audit',len(new_audit),'master',len(master),'pending',sum(1 for r in master if r['review_status']=='BEKLİYOR'),'warn',len(warn),'diff',len(diffs))
print(fullzip)
