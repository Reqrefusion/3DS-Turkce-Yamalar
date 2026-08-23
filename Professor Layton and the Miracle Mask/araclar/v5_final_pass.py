#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, sys, unicodedata
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4

CSV=ROOT/'ceviri'/'layton_tr.csv'
JSONL=ROOT/'ceviri'/'layton_tr.jsonl'
EASY=ROOT/'ceviri'/'CEVIRI_KOLAY.csv'
REPORT_DIR=ROOT/'raporlar'

# v5: yalnız anlamı/biçimi açık olan kesin yazım düzeltmeleri.
WORD_FIX={
    'Esim':'Eşim','esim':'eşim','asina':'aşina','yaniliyordur':'yanılıyordur',
    'yarin':'yarın','Yarin':'Yarın','bosuna':'boşuna','Bosuna':'Boşuna',
    'girisi':'girişi','Girisi':'Girişi','girisini':'girişini','Girisini':'Girişini','girisinde':'girişinde','girisinden':'girişinden',
    'bahsetmis':'bahsetmiş','Bahsetmis':'Bahsetmiş','alin':'alın','Alin':'Alın','alinmis':'alınmış','Alinmis':'Alınmış',
    'hayatin':'hayatın','Hayatin':'Hayatın','aciyorum':'acıyorum','Acıyorum':'Acıyorum',
    'askina':'aşkına','Askina':'Aşkına','asklarindan':'aşklarından','Asklarindan':'Aşklarından',
    'Bahsettiginiz':'Bahsettiğiniz','bahsettiginiz':'bahsettiğiniz','caglar':'çağlar','Caglar':'Çağlar',
    'basliyorsun':'başlıyorsun','Basliyorsun':'Başlıyorsun','saclari':'saçları','Saclari':'Saçları',
    'giyinmis':'giyinmiş','Giyinmis':'Giyinmiş','yuzustu':'yüzüstü','Yuzustu':'Yüzüstü',
    'gececegiz':'geçeceğiz','Gececegiz':'Geçeceğiz','yasadiği':'yaşadığı','Yasadiği':'Yaşadığı',
    'olagandisi':'olağandışı','Olagandisi':'Olağandışı','Aslina':'Aslına','aslina':'aslına',
    'şeyirci':'seyirci','Şeyirci':'Seyirci','şeyircilerin':'seyircilerin','Şeyircilerin':'Seyircilerin','şeyirciye':'seyirciye','Şeyirciye':'Seyirciye',
    'kirikligi':'kırıklığı','Kirikligi':'Kırıklığı','soyluyorum':'söylüyorum','Soyluyorum':'Söylüyorum',
    'basardim':'başardım','Basardim':'Başardım','ucan':'uçan','Ucan':'Uçan','sayısina':'sayısına','Sayısina':'Sayısına',
    'çıkolata':'çikolata','Çıkolata':'Çikolata','çıkolatayi':'çikolatayı','Çıkolatayi':'Çikolatayı','çıkolatanin':'çikolatanın','Çıkolatanin':'Çikolatanın',
    'kocaninda':'koçanında','Kocaninda':'Koçanında','sig':'sığ','Sig':'Sığ','kılıçı':'kılıcı','Kılıçı':'Kılıcı',
    'bastir':'bastır','Bastir':'Bastır','okarinadir':'okarinadır','Okarinadir':'Okarinadır','kostumu':'kostümü','Kostumu':'Kostümü',
    'Isiklar':'Işıklar','isiklar':'ışıklar','Isik':'Işık','isik':'ışık','Isler':'İşler','isler':'işler',
    'Isimiz':'İşimiz','isimiz':'işimiz','Isin':'İşin','isin':'işin','isimi':'işimi','Isimi':'İşimi','isletmek':'işletmek','Isletmek':'İşletmek',
    'cabaliyoruz':'çabalıyoruz','Cabaliyoruz':'Çabalıyoruz','ihtiyaçiniz':'ihtiyacınız','İhtiyaçiniz':'İhtiyacınız',
    'danisin':'danışın','Danisin':'Danışın','aciniz':'açınız','Aciniz':'Açınız','saklanmis':'saklanmış','Saklanmis':'Saklanmış',
    'sandin':'sandın','Sandin':'Sandın','surup':'sürüp','Surup':'Sürüp','basvurusu':'başvurusu','Basvurusu':'Başvurusu',
    'olustu':'oluştu','Olustu':'Oluştu','alacakaranlik':'alacakaranlık','Alacakaranlik':'Alacakaranlık','durugorulu':'duru görülü','Durugorulu':'Duru görülü',
    'yapmasi':'yapması','Yapmasi':'Yapması','bolunmus':'bölünmüş','Bolunmus':'Bölünmüş','taslari':'taşları','Taslari':'Taşları',
    'bulmasina':'bulmasına','Bulmasina':'Bulmasına','sapinda':'sapında','Sapinda':'Sapında',
    'kopegini':'köpeğini','Kopegini':'Köpeğini','kopegini':'köpeğini','kopegini':'köpeğini',
    'sakacilardan':'şakacılardan','Sakacilardan':'Şakacılardan','göçemez':'geçemez','Göçemez':'Geçemez',
    'Asarsan':'Aşarsan','asarsan':'aşarsan','Amac':'Amaç','amac':'amaç','Satranc':'Satranç','satranc':'satranç',
    'Cit':'Çit','cit':'çit','cim':'çim','Cim':'Çim','secimi':'seçimi','Secimi':'Seçimi','kaldir':'kaldır','Kaldir':'Kaldır',
    'Eslesen':'Eşleşen','eslesen':'eşleşen','taslarinin':'taşlarının','Taslarinin':'Taşlarının','dondurmen':'döndürmen','Dondurmen':'Döndürmen',
    'inisini':'inişini','Inisini':'İnişini','holun':'holün','Holun':'Holün',
    'sikisik':'sıkışık','Sikisik':'Sıkışık','basisi':'basışı','Basisi':'Basışı',
    'afis':'afiş','Afis':'Afiş','afislere':'afişlere','Afislere':'Afişlere','asiyorum':'asıyorum','Asiyorum':'Asıyorum',
    'dürüstce':'dürüstçe','Dürüstce':'Dürüstçe','sevinc':'sevinç','Sevinc':'Sevinç',
    'kaldirac':'kaldıraç','Kaldirac':'Kaldıraç','Günes':'Güneş','günes':'güneş',
    'varamayiz':'varamayız','Varamayiz':'Varamayız','ışıklari':'ışıkları','Işıklari':'Işıkları',
    'tasindim':'taşındım','Tasindim':'Taşındım','girmis':'girmiş','Girmis':'Girmiş','kurmus':'kurmuş','Kurmus':'Kurmuş',
    'yaslanmadik':'yaşlanmadık','Yaslanmadik':'Yaşlanmadık','sunun':'şunun','Sunun':'Şunun','Isi':'İşi',
    'üstaca':'ustaca','Üstaca':'Ustaca','pesimden':'peşimden','Pesimden':'Peşimden','sıradisi':'sıra dışı','Sıradisi':'Sıra dışı',
    'üstalikla':'ustalıkla','Üstalikla':'Ustalıkla','ağaçin':'ağacın','Ağaçin':'Ağacın','buzdaginin':'buzdağının','Buzdaginin':'Buzdağının',
    'yarısinin':'yarısının','Yarısinin':'Yarısının','acici':'açıcı','Acici':'Açıcı','Ascotlarin':'Ascotların','ascotlarin':'Ascotların',
    'isiklari':'ışıkları','Isiklari':'Işıkları','cayi':'çayı','Cayi':'Çayı','kirarim':'kırarım','Kirarim':'Kırarım','ucsuz':'uçsuz','Ucsuz':'Uçsuz',
    'saklamis':'saklamış','Saklamis':'Saklamış','esliginde':'eşliğinde','Esliginde':'Eşliğinde','tasinmis':'taşınmış','Tasinmis':'Taşınmış',
    'almasinin':'almasının','Almasinin':'Almasının','isitiyor':'ısıtıyor','Isitiyor':'Isıtıyor','Ledore':'Ledore',
    'halusinojen':'halüsinojen','Halusinojen':'Halüsinojen','ozguveni':'özgüveni','Ozguveni':'Özgüveni','miymis':'miymiş','Miymis':'Miymiş',
    'ağaçi':'ağacı','Ağaçi':'Ağacı','sikisip':'sıkışıp','Sikisip':'Sıkışıp','eslesiyor':'eşleşiyor','Eslesiyor':'Eşleşiyor',
    'kumasi':'kumaşı','Kumasi':'Kumaşı','sandi':'sandı','Sandi':'Sandı','ulasiriz':'ulaşırız','Ulasiriz':'Ulaşırız','yaslanip':'yaslanıp','Yaslanip':'Yaslanıp',
    'fisi':'fişi','Fisi':'Fişi','yaklayacaksiniz':'yakalayacaksınız','Yaklayacaksiniz':'Yakalayacaksınız','yapmasina':'yapmasına','Yapmasina':'Yapmasına',
    'hayatimizi':'hayatımızı','Hayatimizi':'Hayatımızı','yasadiğini':'yaşadığını','Yasadiğini':'Yaşadığını','firca':'fırça','Firca':'Fırça',
    'saklasin':'saklasın','Saklasin':'Saklasın','almasini':'almasını','Almasini':'Almasını','kasli':'kaslı','Kasli':'Kaslı','dolmus':'dolmuş','Dolmus':'Dolmuş',
    'astiriyor':'astırıyor','Astiriyor':'Astırıyor','jonglorlugu':'jonglörlüğü','Jonglorlugu':'Jonglörlüğü','insa':'inşa','Insa':'İnşa',
    'aciyor':'acıyor','Aciyor':'Acıyor','kilik':'kılık','Kilik':'Kılık','üstasi':'ustası','Üstasi':'Ustası','karşilasan':'karşılaşan','Karşilasan':'Karşılaşan',
    'kopekle':'köpekle','Kopekle':'Köpekle','aciyi':'acıyı','Aciyi':'Acıyı','issizligin':'ıssızlığın','Issizligin':'Issızlığın',
    'suratin':'suratın','Suratin':'Suratın','yasadiğim':'yaşadığım','Yasadiğim':'Yaşadığım','canlanir':'canlanır','Canlanir':'Canlanır',
    'birakmasi':'bırakması','Birakmasi':'Bırakması','kılıçın':'kılıcın','Kılıçın':'Kılıcın','şeyirciler':'seyirciler','Şeyirciler':'Seyirciler',
    'olagandışı':'olağandışı',
}


# Son elle taramada güvenle doğrulanan ek imla biçimleri.
WORD_FIX.update({
    'adin':'adın','Adin':'Adın','asiyordum':'asıyordum','Asiyordum':'Asıyordum',
    'afisleri':'afişleri','Afisleri':'Afişleri','askinin':'aşkının','Askinin':'Aşkının',
    'tanrica':'tanrıça','Tanrica':'Tanrıça','basliyormus':'başlıyormuş','Basliyormus':'Başlıyormuş',
    'askim':'aşkım','Askim':'Aşkım','gulunc':'gülünç','Gulunc':'Gülünç','amacini':'amacını','Amacini':'Amacını',
    'secimini':'seçimini','Secimini':'Seçimini','ekana':'ekrana','Ekana':'Ekrana',
    'isinin':'işinin','Isinin':'İşinin','ortusu':'örtüsü','Ortusu':'Örtüsü','buyurken':'büyürken','Buyurken':'Büyürken',
    'yasananlarin':'yaşananların','Yasananlarin':'Yaşananların','yasiyorsa':'yaşıyorsa','Yasiyorsa':'Yaşıyorsa',
    'eglendiricimize':'eğlendiricimize','Eglendiricimize':'Eğlendiricimize','yoldasin':'yoldasın','Yoldasin':'Yoldasın',
    'basariyla':'başarıyla','Basariyla':'Başarıyla','dagilimini':'dağılımını','Dagilimini':'Dağılımını',
    'yarısindaki':'yarısındaki','Yarısindaki':'Yarısındaki','sasirdin':'şaşırdın','Sasirdin':'Şaşırdın',
    'onlugu':'önlüğü','Onlugu':'Önlüğü','fisim':'fişim','Fisim':'Fişim','fis':'fiş','Fis':'Fiş',
    'koymustur':'koymuştur','Koymustur':'Koymuştur','satira':'satıra','Satira':'Satıra','satirin':'satırın','Satirin':'Satırın',
    'satirlari':'satırları','Satirlari':'Satırları','sekli':'şekli','Sekli':'Şekli','sekline':'şekline','Sekline':'Şekline',
    'sigar':'sığar','Sigar':'Sığar','isinir':'ısınır','Isinir':'Isınır','okarinanin':'okarinanın','Okarinanin':'Okarinanın',
    'sakaci':'şakacı','Sakaci':'Şakacı','isletiyor':'işletiyor','Isletiyor':'İşletiyor','isletme':'işletme','Isletme':'İşletme',
    'kapisinin':'kapısının','Kapisinin':'Kapısının','payi':'payı','Payi':'Payı','kuskusuz':'kuşkusuz','Kuskusuz':'Kuşkusuz',
    'ciglik':'çığlık','Ciglik':'Çığlık','kostuk':'koştuk','Kostuk':'Koştuk','kitabi':'kitabı','Kitabi':'Kitabı',
    'vardim':'vardım','Vardim':'Vardım','sonuc':'sonuç','Sonuc':'Sonuç','acar':'açar','Acar':'Açar',
    'donutlari':'donutları','Donutlari':'Donutları','donutlarin':'donutların','Donutlarin':'Donutların',
    'donutlardir':'donutlardır','Donutlardir':'Donutlardır','aynidir':'aynıdır','Aynidir':'Aynıdır',
    'satirla':'satırla','Satirla':'Satırla','seklinde':'şeklinde','Seklinde':'Şeklinde',
    'sekle':'şekle','Sekle':'Şekle','donmusunuz':'dönmüşsünüz','Donmusunuz':'Dönmüşsünüz',
    'donmussunuz':'dönmüşsünüz','Donmussunuz':'Dönmüşsünüz',
    'gordugun':'gördüğün','Gordugun':'Gördüğün','komsulara':'komşulara','Komsulara':'Komşulara',
    'cayim':'çayım','Cayim':'Çayım','kapi':'kapı','Kapi':'Kapı',
})


# İkinci son-tarama: sözlükteki şüpheliler kaynak cümleleriyle doğrulandı.
WORD_FIX.update({
    'isciligi':'işçiliği','Isciligi':'İşçiliği','sakladiğim':'sakladığım','Sakladiğim':'Sakladığım',
    'cabalarina':'çabalarına','Cabalarina':'Çabalarına','arabasina':'arabasına','Arabasina':'Arabasına',
    'cigi':'çığı','Cigi':'Çığı','acinizi':'acınızı','Acinizi':'Acınızı','caglardan':'çağlardan','Caglardan':'Çağlardan',
    'isinlar':'ışınlar','Isinlar':'Işınlar','tasarim':'tasarım','Tasarim':'Tasarım','ic':'iç','Ic':'İç',
    'kullanmasi':'kullanması','Kullanmasi':'Kullanması','cayin':'çayın','Cayin':'Çayın','üstun':'üstün','Üstun':'Üstün',
    'basin':'başın','Basin':'Başın','çalışmasi':'çalışması','Çalışmasi':'Çalışması','olus':'oluş','Olus':'Oluş',
    'asilmis':'asılmış','Asilmis':'Asılmış','sikca':'sıkça','Sikca':'Sıkça','masalin':'masalın','Masalin':'Masalın',
    'basliyorum':'başlıyorum','Basliyorum':'Başlıyorum','sıralari':'sıraları','Sıralari':'Sıraları',
    'baslica':'başlıca','Baslica':'Başlıca','üstaligi':'ustalığı','Üstaligi':'Ustalığı','olcum':'ölçüm','Olcum':'Ölçüm',
    'yazisi':'yazısı','Yazisi':'Yazısı','kalmasini':'kalmasını','Kalmasini':'Kalmasını',
    'canlandirmak':'canlandırmak','Canlandirmak':'Canlandırmak','eslestirip':'eşleştirip','Eslestirip':'Eşleştirip',
    'buzdagindan':'buzdağından','Buzdagindan':'Buzdağından','buzdagi':'buzdağı','Buzdagi':'Buzdağı',
    'komsu':'komşu','Komsu':'Komşu','aklini':'aklını','Aklini':'Aklını','bicimde':'biçimde','Bicimde':'Biçimde',
    'miraslardadir':'miraslardadır','Miraslardadir':'Miraslardadır','deyistirin':'değiştirin','Deyistirin':'Değiştirin',
    'kurus':'kuruş','Kurus':'Kuruş','dondu':'döndü','Dondu':'Döndü','donduğun':'döndüğün','Donduğun':'Döndüğün',
})


# Final bağlam taramasında doğrulanan ek biçimler.
WORD_FIX.update({
    'çokmus':'çökmüş','Çokmus':'Çökmüş','Kirik':'Kırık','kirik':'kırık','kirmissin':'kırmışsın','Kirmissin':'Kırmışsın',
    'hanimi':'hanımı','Hanimi':'Hanımı','isitan':'ısıtan','Isitan':'Isıtan','surece':'sürece','Surece':'Sürece',
    'komsularimiz':'komşularımız','Komsularimiz':'Komşularımız','kiracinin':'kiracının','Kiracinin':'Kiracının',
    'besimize':'beşimize','Besimize':'Beşimize','ismis':'işmiş','Ismis':'İşmiş','pismis':'pişmiş','Pismis':'Pişmiş',
    'sut':'süt','Sut':'Süt','arti':'artı','Arti':'Artı','imkansız':'imkânsız','İmkansız':'İmkânsız',
    'besinci':'beşinci','Besinci':'Beşinci','olumunu':'ölümünü','Olumunu':'Ölümünü','pesinden':'peşinden','Pesinden':'Peşinden',
    'zari':'zarı','Zari':'Zarı','atisini':'atışını','Atisini':'Atışını','susunu':'süsünü','Susunu':'Süsünü',
    'kirilmis':'kırılmış','Kirilmis':'Kırılmış','kirmak':'kırmak','Kirmak':'Kırmak','kirmayi':'kırmayı','Kirmayi':'Kırmayı',
})


# Teslim öncesi son açık imla/anlatım taraması.
WORD_FIX.update({
    'çokmustu':'çökmüştü','Çokmustu':'Çökmüştü','besincisi':'beşincisi','Besincisi':'Beşincisi',
    'hanimin':'hanımın','Hanimin':'Hanımın','mac':'maç','Mac':'Maç','kirikligisin':'kırıklığısın','Kirikligisin':'Kırıklığısın',
    'olumu':'ölümü','Olumu':'Ölümü','nisanci':'nişancı','Nisanci':'Nişancı',
})

# Apostrof ekleri / kalıplar. Yalnız anlamı ve ünlü uyumu açık örnekler.
PHRASE_FIX=[
    (r"\bLayton'in\b","Layton'ın","özel ad eki"),
    (r"\bA'nin\b","A'nın","harf adı eki"),
    (r"\bLedore'lari\b","Ledore'ları","özel ad çoğul eki"),
    (r"\bsuratin asik\b","suratın asık","anlam/imla"),
    (r"\bSharoa'nin\b","Sharoa'nın","özel ad eki"),
    (r"\bLedore'larin\b","Ledore'ların","özel ad çoğul eki"),
    (r"\bDokunmatik Ekran'in\b","Dokunmatik Ekran'ın","özel ad/arayüz eki"),
    (r"\bGerçek Şu ki\b","Gerçek şu ki","yanlış büyük harf"),
    (r"\bBu Şu anlama\b","Bu şu anlama","yanlış büyük harf"),
    (r"\bAllah askina\b","Allah aşkına","imla"),
    (r"\bbas belası\b","baş belası","imla"),
    (r"\bSöyle ki\b","Şöyle ki","bağlaç kalıbı"),
    (r"\bsöyle der\b","şöyle der","anlatım kalıbı"),
    (r"\bSöyle der\b","Şöyle der","anlatım kalıbı"),
    (r"\bsöyle yapalım\b","şöyle yapalım","anlatım kalıbı"),
    (r"\bSöyle yapalım\b","Şöyle yapalım","anlatım kalıbı"),
    (r"\bsöyle düşündüm\b","şöyle düşündüm","anlatım kalıbı"),
    (r"\bSöyle düşündüm\b","Şöyle düşündüm","anlatım kalıbı"),
    (r"\bsöyle diyeceğim\b","şöyle diyeceğim","anlatım kalıbı"),
    (r"\bSöyle diyeyim\b","Şöyle diyeyim","anlatım kalıbı"),
    (r"\bSöyle bakalım\b","Şöyle bakalım","anlatım kalıbı"),
    (r"\bSöyle bir\b","Şöyle bir","anlatım kalıbı"),
    (r"\bsöyle bir\b","şöyle bir","anlatım kalıbı"),
    (r"\bNorwell sürü Şu patikanın\b","Norwell Duvarı şu patikanın","anlam düzeltmesi"),
    (r"\bThe Öne-Stop Shop\b","The One-Stop Shop","İngilizce özel ad bozulmasını geri alma"),
    (r"\bÖne-Stop Shop\b","One-Stop Shop","İngilizce özel ad bozulmasını geri alma"),
    (r"\btek basima\b","tek başıma","imla"),
    (r"\bkendi basima\b","kendi başıma","imla"),
    (r"\bMucizeler Şehri'nde\b","Mucizeler Şehri'nde","koru"),
    (r"\bMaskeli Beyefendi'nden\b","Maskeli Beyefendi'den","özel ad eki"),
    (r"\bgeri donmus\b","geri dönmüş","dönmek fiili bağlamı"),
    (r"\bgeri donmussunuz\b","geri dönmüşsünüz","dönmek fiili bağlamı"),
    (r"\beve donmus\b","eve dönmüş","dönmek fiili bağlamı"),
    (r"\bLondra'ya donmus\b","Londra'ya dönmüş","dönmek fiili bağlamı"),
    (r"\bdeliye donmustur\b","deliye dönmüştür","dönmek fiili bağlamı"),
    (r"\bharabeye donmus\b","harabeye dönmüş","dönmek fiili bağlamı"),
    (r"\bTasa Donmus Kalabalık\b","Taşa Donmuş Kalabalık","başlık imlası/anlamı"),
    (r"\bbesi küçük\b","beşi küçük","sayı bağlamı"),
    (r"\bis birliği\b","iş birliği","imla"),
    (r"\bpamuk seker\b","pamuk şeker","şeker bağlamı"),
    (r"\bseker mısır\b","şeker mısır","şeker bağlamı"),
    (r"\bfazla seker içerir\b","fazla şeker içerir","şeker bağlamı"),
    (r"\bsiz ucu\b","siz üçü","sayı bağlamı"),
    (r"\bUcu de\b","Üçü de","sayı bağlamı"),
    (r"\bucu de\b","üçü de","sayı bağlamı"),
    (r"\bucu birden\b","üçü birden","sayı bağlamı"),
    (r"\bucu yukarı\b","üçü yukarı","sayı bağlamı"),
    (r"\bucu aşağı\b","üçü aşağı","sayı bağlamı"),
    (r"\bEl isciligi\b","El işçiliği","imla"),
    (r"\bKum Cigi\b","Kum Çığı","imla"),
    (r"\bkum cigi\b","kum çığı","imla"),
    (r"\bDus bedeni\b","Duş bedeni","duş bağlamı"),
    (r"\bpesine dus\b","peşine düş","düşmek fiili bağlamı"),
    (r"\bkapis kapis aldı\b","kapış kapış aldı","deyim düzeltmesi"),
    (r"\byapis yapis\b","yapış yapış","imla"),
    (r"\bis arkadaşları\b","iş arkadaşları","imla"),
    (r"\bsu sırayla\b","şu sırayla","işaret sözcüğü"),
    (r"\bkollar, bacaklar, bas, gövde\b","kollar, bacaklar, baş, gövde","baş sözcüğü bağlamı"),
    (r"\bRandall'in\b","Randall'ın","özel ad eki"),
    (r"\bAngela'nin\b","Angela'nın","özel ad eki"),
    (r"\bSirk Müdürü'nun\b","Sirk Müdürü'nün","ünlü uyumu"),
    (r"\bÜstaligi sudur\b","Ustalığı şudur","imla/anlatım"),
    (r"\bnarin bir yani\b","narin bir yanı","anlam/imla"),
    (r"\bsuratın asik\b","suratın asık","asık surat bağlamı"),
    (r"\bgenç asik\b","genç âşık","âşık kişi bağlamı"),
    (r"\b3'un\b","3'ün","sayı eki"),
    (r"\b3'u\b","3'ü","sayı eki"),
    (r"\b4'un\b","4'ün","sayı eki"),
    (r"\b16'nin\b","16'nın","sayı eki"),
    (r"\bamahala\b","ama hâlâ","ayrı yazım/imla"),
    (r"\bgeri don\b","geri dön","dönmek fiili bağlamı"),
    (r"\bise aldı\b","işe aldı","işe almak deyimi"),
    (r"\bTuh, Şansımız\b","Tuh, şansımız","yanlış büyük harf"),
    (r"\bsonra söyle ilerle\b","sonra şöyle ilerle","anlatım kalıbı"),
    (r"\bİyi is çıkardın\b","İyi iş çıkardın","imla"),
    (r"\bGüzel is çıkardın\b","Güzel iş çıkardın","imla"),
    (r"\bharika is çıkardın\b","harika iş çıkardın","imla"),
    (r"\bGenç Üsta Randall\b","Genç Efendi Randall","Master hitabı çeviri kalitesi"),
    (r"\bÜsta Randall\b","Efendi Randall","Master hitabı çeviri kalitesi"),
    (r"\büsta bir retriever\b","usta bir iz sürücü","anlam/çeviri kalitesi"),
    (r"\büsta bir nisanci\b","usta bir nişancı","imla/anlatım"),
]

# Kaynak ve kontrol kodları incelenerek elle çevrilen / düzeltilen kayıtlar.
OVERRIDE={
 ('03/03_030560.xs','text000025'): "<T>Dikkatli olun! Ona boşuna {''}vahşi ve\nkorkutucu Hannibal{''} demiyorlar.",
 ('04/04_040130.xs','text000013'): "<T>Bu sayfayı Rutledge'in {''}Antik\nTarihler{''} kitabından kopyaladım.",
 ('05/05_050680.xs','text000015'): "<T><M4/1/1>Şimdi Müfettiş Grosky... meşgulken,\nşu ipucunu düşünelim: {''}Mucizeye yeni bir\ndönüş.{''}",
 ('05/05_050740.xs','text000003'): "<T>{''}Mucizeye yeni bir dönüş{''}...",
 ('06/06_067605.xs','text000002'): "<T>{''}Tüm kristalleri kırmalısın. Üç deliğe birer\nkaya yerleştir, sonra son kayayı güçlüce\nyukarı doğru it.{''}",
 ('07/07_071150.xs','text000026'): "<T><M6/2/1/45>Bir bakalım...<W> Hikâye, çocuğun {''}pencere\nkenarındaki güneşli bir yerde uykuya\ndalmasıyla{''} bitiyordu.",
 ('07/07_071185.xs','text000015'): "<T>Bu oda, hikâyedeki {''}yeşilliklerle çevrili\ngüzel yer{''} olmasın?",
 ('07/07_071200.xs','text000003'): "<T><M5/1/1/45>Ah, demek {''}yeşilliklerle çevrili güzel yer{''}\nbu odadaki resim çerçevesiymiş.",
 ('20/20_200010.xs','text000001'): "<T>Professor Layton ve Mucize Maskesi'ni\nbeğendiniz mi?",
 ('20/20_200010.xs','text000008'): "<T>Professor Layton ve Mucize Maskesi'nin\ngeri kalanının tadını çıkarın!",
 ('20/20_200020.xs','text000001'): "<T>Professor Layton ve Mucize Maskesi'ni\nbeğendiniz mi?",
 ('20/20_200020.xs','text000004'): "<T>Professor Layton ve Mucize Maskesi'nde\ngörecek daha çok şey var!",
 # Bulmaca yardım metinleri: önceki sürümde İngilizce kalmış olanlar.
 ('52/52_000002.xs','text000000'): 'Go-Kart',
 ('52/52_000002.xs','text000001'): 'Kalemle Dokunmatik Ekran üzerinde cevabını\ndaire içine al. Doğru yaparsan dairenin içinde\ncevabını gösteren bir parmak simgesi belirir.\nBelirmezse tekrar dene.',
 ('52/52_000014.xs','text000000'): 'Üç Renkli Karolar',
 ('52/52_000014.xs','text000001'): 'Dokunmatik Ekran’ın sağındaki karoları alıp\nsoldaki çerçevenin içine, örnek desenle\neşleşecek şekilde yerleştir. Karolar üst üste\ngelebilir.',
 ('52/52_000026.xs','text000000'): 'Kedi Soliteri',
 ('52/52_000026.xs','text000001'): 'Dokunmatik Ekran’da bir kediye basılı tutarak\natlayabileceği kareleri vurgula. Beyaz yavru\nkedilerin üzerinden birer birer atlayıp hepsini\nyok et ve siyah kediyi merkezde bırak.',
 ('52/52_000033.xs','text000001'): 'Uğur böceğinin yönünü değiştirmek için\nDokunmatik Ekran’a dokun.\n\nUğur böceğini o yönde yürütmek için kalemi\nekranda basılı tut.',
 ('52/52_000034.xs','text000001'): 'Tokmağı üst ekranda hareket ettirmek için\nkalemi Dokunmatik Ekran üzerinde kaydır.',
 ('52/52_000034.xs','text000002'): 'Tokmağı bir bloğun yanındaki okun üzerine\ngetirip oku vurgula; sonra Dokunmatik Ekran’a\ndokunarak bloğu o yöne it.\n\nTüm blokları yerlerine oturtabilir misin?',
 ('52/52_000046.xs','text000000'): 'Mağara Duvarı',
 ('52/52_000046.xs','text000001'): 'Üst ekrandaki aydınlık alanı hareket ettirmek\niçin kalemi Dokunmatik Ekran’da kaydır.\n\nLambayı hareket ettir ve duvar resmindeki\nhayvanların sayısını bul.',
 ('52/52_000048.xs','text000000'): 'Sonsuz Koridor Bulmacası',
 ('52/52_000048.xs','text000001'): '[Geçici metin]\n\n[Grafik de geçicidir.]',
 ('52/52_000049.xs','text000000'): 'Anneyi Bul',
 ('52/52_000049.xs','text000001'): 'Üst ekrandaki parmak simgesini hareket\nettirmek için kalemi Dokunmatik Ekran’da\nkaydır.',
 ('52/52_000049.xs','text000003'): 'Simge turuncuya döndüğünde, seçeneği cevabın\nolarak işaretlemek için Dokunmatik Ekran’a\ndokunabilirsin.',
 ('52/52_000050.xs','text000000'): 'Posteri Asalım',
 ('52/52_000050.xs','text000001'): 'Üst ekrandaki posteri döndürmek için eli\nDokunmatik Ekran’daki kaydırma çubuğunda\nkaydır.\n\nEl merkezden ne kadar uzaklaşırsa poster o\nkadar hızlı hareket eder.',
 ('52/52_000051.xs','text000000'): 'İki Hamal',
 ('52/52_000051.xs','text000001'): 'Bagaj parçalarını Dokunmatik Ekran’ın solundan\nhamalların ellerine sürükle, ardından zile dokun.\n\nHamalların ağırlığa nasıl tepki verdiğini üst\nekrandan izle.',
 ('52/52_000052.xs','text000000'): 'Tokoroten Bulmacası',
 ('52/52_000052.xs','text000001'): 'Parçaları yatay ve dikey kaydır. Yalnızca üçlü\nsıralar hâlinde hareket ettirebilirsin.\n\nParçaların desenine dikkat ederek onları\nmerkezde 3 x 3 kare oluşturacak şekilde diz.',
 ('52/52_000055.xs','text000000'): 'Sandığın İçindekiler',
 ('52/52_000055.xs','text000001'): 'Ortadaki bloklara dokunarak onları hareket\nettir; kenardakilere dokunarak döndür.\n\nSandık kapandığında beyaz çıkıntılar ○ ile siyah\ndelikler ● birbirine uyacak şekilde blokları diz.',
}

MUSIC={
 'text000003':'Profesör Layton Teması','text000004':'Mucize Maskesi Teması','text000005':'Bulmacalar Her Yerde',
 'text000006':"Monte d'Or: Karnaval Gecesi",'text000007':'Kuşkular','text000008':'Tehlikeli Şakalar',
 'text000009':'Beyefendinin Teması','text000010':'Amansız Takip','text000011':'Beklenti','text000012':'Yanılsama',
 'text000013':"Monte d'Or: Mucizeler Şehri",'text000014':'Bir Anlık Huzur','text000015':'Sirk Çadırının İçinde',
 'text000016':'Bulmacalar','text000017':'İpucu Arayışı','text000018':'Akrep Kumarhanesi','text000019':'Hipodrom',
 'text000020':'Stansbury: Huzurlu Günler','text000021':'Stansbury: Ay Işıklı Tepe','text000022':'Norwell',
 'text000023':'Akbadain Harabeleri','text000024':'Akbadain Keşfi','text000025':'Harekete Geçme Zamanı!',
 'text000026':'Keder','text000027':'Değerli Anılar','text000028':'Tingly Kasabası','text000029':'Reunion Hanı',
 'text000030':'Descole Teması','text000031':'Kalıcı Bir Hazine','text000032':'Targent Teması','text000033':'Oyuncak Robot',
 'text000034':'Robot Düellosu','text000035':'One-Stop Shop','text000036':'Tavşan Gösterisi','text000037':'Tavşan Sahnede',
 'text000038':'Gizemli Çiçek',
}
for k,v in MUSIC.items(): OVERRIDE[('40/40_001400.xs',k)]=v

# Daha önce kısmen İngilizce kalmış bazı özel ifadeler. Ürün/özel isimler (Magic Fiddle vb.)
# kasıtlı bırakılır; yalnız genel anlatım İngilizcesi çevrilir.
OVERRIDE[('81/81_000300.xs','text000011')]="<T>Bu, adı <CR>Fluffy</CR> olan <CR>sarı bir oyuncak ayı</CR>.\nÇok sevimli değil mi?"


# Son bağlam taramasında kaynak metinle karşılaştırılarak elle düzeltilen kayıtlar.
OVERRIDE.update({
 ('05/05_050100.xs','text000015'): "<T><M1/1/1>Evet, belediyeye gidersen onun\nhüzünlü hikâyesini dinleyebilirsin.",
 ('50/50_000102.xs','text000001'): 'Annenin donutları hangileri?',
 ('50/50_000102.xs','text000002'): 'Üç kişilik bir aile seyyar bir donut dükkânı işletiyor. En çok tutulan ürünleri ünlü Dört Renkli Donut. Şu anda vitrinde 12 donut var ve bunların üçünü ailenin annesi yapmış. Görünüşe göre yalnızca bakarak hangilerinin ona ait olduğunu anlayabilirsin!\n\nAnnenin yaptığı donutları bulabilir misin?\n\nBu arada donutların üzerindeki şeker kaplaması iki tarafta da aynıdır.',
 ('50/50_000102.xs','text000003'): 'Doğru!\n\nAnne, üst sırada soldan ikinci donutu; alt sırada ise en soldaki ve en sağdaki donutları yaptı.\n\nDikkatle bakarsan donutların şeker kaplamalarının az da olsa farklı olduğunu fark edersin. Geriye, birbiriyle aynı şekilde eşleşen ve diğerlerinden ayrılan üç donutluk grubu bulmak kalıyor.',
 ('50/50_000102.xs','text000004'): 'Olmadı.\n\nKim yapmış olursa olsun hepsi aynı derecede lezzetli görünüyor!',
 ('50/50_000102.xs','text000005'): 'On iki donutun boyutu ve şekli aynı, ama aralarındaki farkı anlamanın bir yolu var. Bunun ne olduğunu bulabilir misin?',
 ('50/50_000102.xs','text000006'): 'Tüm donutların boyutu ve şekli aynı; bu yüzden onları yalnızca şeker kaplamalarına bakarak ayırt edebilirsin.\n\nAynı kaplama desenine sahip üç donutu bulmaya çalış.',
 ('50/50_000102.xs','text000007'): 'Donutları ters çevirirsen kaplamaların sırası da değişir.\n\nÖrneğin saat yönünde kahverengi, beyaz, turuncu ve pembe kaplamalı bir donut; ters çevrildiğinde saat yönünde kahverengi, pembe, turuncu ve beyaz kaplamalı donutla aynıdır.\n\nÜçlü grubu ararken bunu aklında tut.',
 ('50/50_000102.xs','text000008'): 'İlk sıraya bak. Üç donutun kaplama sırası aynı, ancak soldan ikinci donutunki farklı. Onu ailenin annesi yapmış.\n\nŞimdi yalnızca onunla eşleşen diğer iki donutu bulman gerekiyor.',
 ('81/81_000004.xs','text000007'): 'Trajik baladım için gereken\nşey <CR>Dusky Stradivarius</CR>!\nMutlaka almalıyım!',
 ('81/81_000010.xs','text000008'): 'Şu <CR>Dusty Tome</CR> da ne?\nİçinde... tarih falan\nvar gibi. Alıyorum!',
 ('81/81_000020.xs','text000038'): 'Bu güneş gibi parlayan <CR>kırmızı\nkeman</CR> <CR>Dusky Stradivarius</CR>\'tur.',
 ('81/81_000020.xs','text000040'): '<CR>Cinocoberry Ring</CR>, bir\n<CR>kırmızı donut</CR>. Onu\nhareket ettiremezsin.',
 ('81/81_000020.xs','text000041'): '<CR>Lime Glaze</CR>,\n<CR>yeşil</CR> kaplamalı\nbir <CR>donuttur</CR>.',
 ('81/81_000020.xs','text000090'): '<CR>Dusty Tome</CR>, entrika\ndolu bir <CR>kırmızı kitaptır</CR>.',
 ('81/81_000100.xs','text000071'): 'Donut',
 ('81/81_000100.xs','text000072'): 'Bu nefis, yumuşacık ve mayhoş donut, misket\nlimonundan çok daha fazla şeker içerir.',
})


OVERRIDE.update({
 ('03/03_030010.xs','text000002'): '<V0020><T>Orada dehşet verici bir manzaraya tanık olduk\n- siviller gözlerimizin önünde taşa dönüştü!</V>',
 ('20/20_200250.xs','text000099'): '<T><M2/1/1>Bu çok rahatlatıcı, Emmy. Ama sanırım\nkendimi savunabilirim.',
 ('81/81_000100.xs','text000079'): 'Üzeri unlanmış bu somun, iç ısıtan bir kase\nİskoç çorbasıyla mükemmel gider.',
})


OVERRIDE.update({
 ('81/81_000000.xs','text000009'): 'İster yeni başlıyor olun ister armonik\nminörlere hâkim olun, burada kaliteli okarineler,\ndavullar ve kemanlar bulacaksınız.',
})

WORD_RE=re.compile(r"(?<![A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû])([A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+)(?![A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû])")
JP_RE=re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')

def apply_word_fix(text:str):
    notes=[]
    def repl(m):
        w=m.group(1); nw=WORD_FIX.get(w,w)
        if nw!=w: notes.append(f'{w}→{nw}')
        return nw
    return WORD_RE.sub(repl,text),notes

def control_codes(s): return base.CTRL_RE.findall(s)

def main():
    adv=base.load_adv(ROOT)
    rows=list(csv.DictReader(CSV.open(encoding='utf-8-sig',newline='')))
    original_v2={}
    p=REPORT_DIR/'orijinal_yedek'/'layton_tr_v2.csv'
    if p.exists():
        for r in csv.DictReader(p.open(encoding='utf-8-sig',newline='')):
            original_v2[(r['file'],r['id'])]=r['translation']
    outmap={}; delta=[]; full=[]; overflow=[]; badcodes=[]; stats=Counter()
    for i,r in enumerate(rows,1):
        key=(r['file'],r['id']); src=r['original']; old=r['translation']; s=old; reasons=[]
        before_codes=control_codes(old)
        if key in OVERRIDE:
            s=OVERRIDE[key]; reasons.append('kaynak metne göre elle çeviri/anlam düzeltmesi'); stats['override']+=1
        s2,wn=apply_word_fix(s)
        if s2!=s:
            s=s2; reasons.append('kesin Türkçe imla düzeltmesi: '+', '.join(wn[:12])+('…' if len(wn)>12 else '')); stats['word_rows']+=1; stats['word_edits']+=len(wn)
        for pat,repl,label in PHRASE_FIX:
            if label=='koru': continue
            ns,c=re.subn(pat,repl,s)
            if c:
                s=ns; reasons.append(label); stats['phrase_edits']+=c
        # Yaygın başlık tutarlılığı
        ns,c=re.subn(r"\{''\}Ancient Histories\{''\}","{''}Antik Tarihler{''}",s)
        if c: s=ns; reasons.append('eser adı tutarlılığı'); stats['title_edits']+=c
        # Blok/blog hatasını yalnız kaynakta block varsa düzelt.
        if re.search(r'\bblocks?\b',src,re.I):
            b=s
            reps={r'\bbloga\b':'bloğa',r'\bblogu\b':'bloğu',r'\bblogun\b':'bloğun',r'\bblogunu\b':'bloğunu',r'\bblogunda\b':'bloğunda',r'\bbloglar\b':'bloklar',r'\bblog\b':'blok',
                  r'\bBloga\b':'Bloğa',r'\bBlogu\b':'Bloğu',r'\bBlogun\b':'Bloğun',r'\bBlogunu\b':'Bloğunu',r'\bBlogunda\b':'Bloğunda',r'\bBloglar\b':'Bloklar',r'\bBlog\b':'Blok'}
            for pat,rp in reps.items(): s=re.sub(pat,rp,s)
            if s!=b: reasons.append('block→blok terimi düzeltildi'); stats['block_rows']+=1
        # "bol" iki ayrı sözcüktür: yalnız kaynak gerçekten divide/cut diyorsa "böl".
        if re.search(r'\b(divid(?:e|ed|ing)?|cut(?:s|ting)?)\b',src,re.I):
            b=s
            s=re.sub(r'\bbol\b','böl',s); s=re.sub(r'\bBol\b','Böl',s)
            if s!=b: reasons.append('divide/cut bağlamında böl fiili')
        # Dön/don: yalnız rotate kaynakta açıkken.
        if re.search(r'\brotate|rotation\b',src,re.I):
            b=s; s=re.sub(r'\bdondurmen\b','döndürmen',s); s=re.sub(r'\bDondurmen\b','Döndürmen',s)
            if s!=b: reasons.append('rotate bağlamında döndür- fiili')
        s=unicodedata.normalize('NFC',s)
        after_codes=control_codes(s)
        if before_codes!=after_codes:
            badcodes.append({'file':r['file'],'id':r['id'],'before':before_codes,'after':after_codes,'candidate':s})
            s=old; reasons=['GÜVENLİK: kontrol kodu dizisi değişeceği için v5 değişikliği uygulanmadı']; stats['reverted']+=1
        # Değişen metinleri kaynak satır düzenine/font genişliğine göre yeniden akıt.
        if s!=old:
            s2,chg,why=v4.wrap_final(src,s,adv)
            if chg:
                # wrap kontrol kodlarını bozarsa kabul etme
                if control_codes(s2)==before_codes:
                    s=s2; reasons.append(why); stats['rewrap']+=1
        px=v4.max_px(s,adv)
        limit=348 if ('<T>' in src or (JP_RE.search(src) and src.count('\n')<=2)) else 399
        if px>limit:
            overflow.append({'file':r['file'],'id':r['id'],'px':px,'limit':limit,'source':src,'translation':s})
        changed=s!=old
        if changed: stats['changed']+=1
        outmap[key]=s; r['translation']=s
        # v5 delta raporu
        if reasons:
            reason='; '.join(reasons)
        elif s==old and JP_RE.search(src) and src==old:
            reason='Kaynakla aynı kalan kısa Japonca ad/konuşmacı/dahili etiket adayı; motor kimliği ve ad eşlemesi riski nedeniyle otomatik değiştirilmedi.'
        elif s==old:
            reason='v4 metni v5 ek kalite taramasında kontrol edildi; güvenli ve gerekli ek değişiklik saptanmadı.'
        else:
            reason='v5 düzenlemesi.'
        delta.append({'sira':i,'file':r['file'],'id':r['id'],'durum':'DEGISTI' if changed else 'DEGISMEDI','neden':reason,'v4':old,'v5':s,'kaynak':src,'v4_max_satir_px':v4.max_px(old,adv),'v5_max_satir_px':px,'limit_px':limit})
        first=original_v2.get(key,old)
        final_status='DEGISTI' if s!=first else 'DEGISMEDI'
        full.append({'sira':i,'file':r['file'],'id':r['id'],'durum':final_status,'neden':reason if changed else ('İlk sürümden değişiklik yok; '+reason),'ilk_yama':first,'final_v5':s,'kaynak':src,'final_max_satir_px':px,'statik_limit_px':limit,'tasma_durumu':'RISK' if px>limit else 'OK'})
    # ana CSV
    with CSV.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']); w.writeheader(); w.writerows(rows)
    # JSONL
    out=[]
    for line in JSONL.read_text(encoding='utf-8').splitlines():
        o=json.loads(line)
        if o.get('kind')=='text': o['translation']=outmap.get((o['file'],o['id']),o.get('translation',''))
        out.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
    JSONL.write_text('\n'.join(out)+'\n',encoding='utf-8')
    # Kolay CSV
    krows=list(csv.DictReader(EASY.open(encoding='utf-8-sig',newline='')))
    for rr in krows:
        k=(rr['file'],rr['id'])
        if k in outmap: rr['turkce']=outmap[k]
    with EASY.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','kaynak_japonca','turkce','durum']); w.writeheader(); w.writerows(krows)
    # raporlar
    rp=REPORT_DIR/'V5_EK_DEGISIKLIK_RAPORU.csv'
    with rp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(delta[0])); w.writeheader(); w.writerows(delta)
    fp=REPORT_DIR/'FINAL_TEK_TEK_KONTROL_RAPORU_V5.csv'
    with fp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(full[0])); w.writeheader(); w.writerows(full)
    op=REPORT_DIR/'V5_TASMA_RISKLERI.csv'
    with op.open('w',encoding='utf-8-sig',newline='') as f:
        fields=['file','id','px','limit','source','translation']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(overflow)
    cp=REPORT_DIR/'V5_KONTROL_KODU_GUVENLIK.json'; cp.write_text(json.dumps(badcodes,ensure_ascii=False,indent=2),encoding='utf-8')
    jp_left=sum(1 for r in rows if r['translation']==r['original'] and JP_RE.search(r['original']))
    en_exact=sum(1 for r in rows if r['translation']==r['original'] and re.search(r'[A-Za-z]',r['original']))
    summary=(
        'LAYTON TÜRKÇE YAMA FINAL v5 — EK KALİTE / TESLİM GEÇİŞİ\n\n'
        f'Toplam kayıt: {len(rows)}\n'
        f'v4 üzerine değişen kayıt: {stats["changed"]}\n'
        f'Elle kaynak karşılaştırmalı düzeltme/çeviri: {stats["override"]}\n'
        f'Kesin imla düzeltmesi: {stats["word_edits"]} işlem / {stats["word_rows"]} kayıt\n'
        f'Kalıp/ek/terim düzeltmesi: {stats["phrase_edits"] + stats["title_edits"]} işlem\n'
        f'Block→blok kaynak bağlamı düzeltmesi: {stats["block_rows"]} kayıt\n'
        f'Yeniden satır dengelenen değişiklik: {stats["rewrap"]}\n'
        f'Kontrol kodu değişimi nedeniyle geri alınan: {stats["reverted"]}\n'
        f'Statik taşma riski: {len(overflow)}\n'
        f'Kaynakla aynı kalan Japonca kayıt: {jp_left} (çoğu kısa ad/konuşmacı/dahili etiket; neden tek-tek raporda)\n'
        f'Kaynakla aynı kalan Latin kayıt: {en_exact} (özel ad, ünlem, ürün/müzik dışı ad vb. dahil)\n\n'
        'v5 ÖZEL DÜZELTMELER\n'
        '- İngilizce kalmış bulmaca yardım metinleri Türkçeleştirildi.\n'
        '- one→öne / sure→süre gibi İngilizce satırlarda oluşmuş yanlış otomatik dönüşümler kaldırıldı.\n'
        '- Müzik galerisi başlıkları Türkçeleştirildi; özel kişi/marka adları korunmuştur.\n'
        '- Türkçe apostrof ekleri, kalan ASCII Türkçe harfleri ve açık imla hataları ek turda temizlendi.\n'
        '- Kontrol kodlarının sırası korunur; statik genişlik testi gerçek nrm font advance değerleriyle yapılır.\n'
        '- Gerçek cihaz/emülatör görsel testi bu ortamda yapılamadığı için yalnız binary/XS/font/statik genişlik doğrulaması yapılabilir.\n'
    )
    (REPORT_DIR/'V5_IYILESTIRME_OZETI.txt').write_text(summary,encoding='utf-8')
    print(json.dumps({'stats':dict(stats),'overflow':len(overflow),'badcodes':len(badcodes),'jp_left':jp_left,'en_exact':en_exact},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
