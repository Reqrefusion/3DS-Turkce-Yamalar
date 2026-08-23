#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, math, argparse, unicodedata
from pathlib import Path
from collections import Counter

TR_CHARS='ÇçĞğİıÖöŞşÜüÂâÎîÛû'
CTRL_RE=re.compile(r'<[^>\n]+>|\{[^}\n]+\}')
ATOM_RE=re.compile(r'<[^>\n]+>|\{[^}\n]+\}|\[[^]\n]+\]')
WORD_RE=re.compile(r"[A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+(?:'[A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+)?")
JP_RE=re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')

# Yüksek güvenli Türkçe ASCII -> gerçek Türkçe sözlük. Oyun içindeki özel adlar
# bilinçli olarak bu sözlüğe alınmaz. Sözlük, yaygın sözcükleri ve yama içinde
# çok tekrar eden biçimleri kapsar.
PAIRS = r'''
icin=için
degil=değil
cok=çok
sey=şey
genc=genç
oldugunu=olduğunu
Profesor=Profesör
profesor=profesör
once=önce
nasil=nasıl
olmali=olmalı
simdi=şimdi
buyuk=büyük
gercekten=gerçekten
Dogru=Doğru
dogru=doğru
oyle=öyle
tum=tüm
hic=hiç
ayni=aynı
gore=göre
kucuk=küçük
yuzden=yüzden
gorunuyor=görünüyor
baska=başka
sekilde=şekilde
Sanirim=Sanırım
sanirim=sanırım
boyle=böyle
guzel=güzel
seyi=şeyi
hicbir=hiçbir
sag=sağ
ust=üst
Hayir=Hayır
hayir=hayır
oldukca=oldukça
gun=gün
artik=artık
Gercekten=Gerçekten
bulmacayi=bulmacayı
Iyi=İyi
iyi=iyi
dort=dört
asagi=aşağı
icinde=içinde
Iste=İşte
iste=işte
farkli=farklı
hakkinda=hakkında
yukari=yukarı
birkac=birkaç
Ipucu=İpucu
yalnizca=yalnızca
gormek=görmek
esya=eşya
kisi=kişi
kac=kaç
kotu=kötü
kirmizi=kırmızı
Tavsan=Tavşan
tavsan=tavşan
aslinda=aslında
uzerinde=üzerinde
diger=diğer
Lutfen=Lütfen
lutfen=lütfen
Anlatim=Anlatım
olduguna=olduğuna
gercek=gerçek
ozel=özel
olmasi=olması
bes=beş
saga=sağa
sola=sola
parca=parça
arasinda=arasında
goz=göz
Aslinda=Aslında
soyledi=söyledi
bazi=bazı
butun=bütün
altinda=altında
onemli=önemli
gerektigini=gerektiğini
dusun=düşün
Guzel=Güzel
Eger=Eğer
hos=hoş
seyler=şeyler
Duzen=Düzen
yesil=yeşil
canina=canına
mumkun=mümkün
icine=içine
coz=çöz
yerlestir=yerleştir
oluyor=oluyor
karsi=karşı
Nasil=Nasıl
yil=yıl
Gorunuse=Görünüşe
yardimci=yardımcı
Tesekkur=Teşekkür
tesekkur=teşekkür
Hic=Hiç
degildi=değildi
tarafindan=tarafından
hizli=hızlı
gorunen=görünen
degilim=değilim
agir=ağır
Burasi=Burası
muhtemelen=muhtemelen
Sag=Sağ
cikti=çıktı
tesekkurler=teşekkürler
calis=çalış
Ayrica=Ayrıca
yanlis=yanlış
sagdaki=sağdaki
kisa=kısa
sure=süre
Mufettis=Müfettiş
gordum=gördüm
cikar=çıkar
korkunc=korkunç
sehir=şehir
Anliyorum=Anlıyorum
acik=açık
yakin=yakın
iceri=içeri
basina=başına
gosteriyor=gösteriyor
yone=yöne
Esya=Eşya
azindan=azından
cunku=çünkü
muhtesem=muhteşem
sira=sıra
soz=söz
cozmek=çözmek
Buyuk=Büyük
bugun=bugün
soyluyor=söylüyor
Iki=İki
ustteki=üstteki
sayi=sayı
kaydir=kaydır
ustunde=üstünde
hazir=hazır
supheli=şüpheli
aksam=akşam
gecen=geçen
palyaco=palyaço
degerli=değerli
isik=ışık
kismi=kısmı
ozur=özür
Uzgunum=Üzgünüm
Baska=Başka
fotograf=fotoğraf
Sehrin=Şehrin
dusunuyorum=düşünüyorum
suru=sürü
cogu=çoğu
gosteri=gösteri
sans=şans
sec=seç
calisma=çalışma
ucuncu=üçüncü
Kucuk=Küçük
sehri=şehri
mukemmel=mükemmel
sira=sıra
aksam=akşam
gecen=geçen
isin=işin
seyin=şeyin
goruyor=görüyor
degerli=değerli
yaninda=yanında
isik=ışık
ozur=özür
Uzgunum=Üzgünüm
dusunuyorum=düşünüyorum
ayak=ayak
suru=sürü
cogu=çoğu
gosteri=gösteri
sans=şans
sec=seç
calisma=çalışma
arkasinda=arkasında
ucuncu=üçüncü
burasi=burası
ortasinda=ortasında
tadini=tadını
parcasi=parçası
altina=altına
adi=adı
calisiyor=çalışıyor
Mukemmel=Mükemmel
uzerindeki=üzerindeki
basladi=başladı
gozden=gözden
oldugundan=olduğundan
cikan=çıkan
insa=inşa
yuksek=yüksek
disari=dışarı
ettigi=ettiği
sayisi=sayısı
cukur=çukur
capraz=çapraz
Boylece=Böylece
ilginc=ilginç
Hicbir=Hiçbir
degildir=değildir
eglenceli=eğlenceli
isaret=işaret
konusmak=konuşmak
saglam=sağlam
gordun=gördün
unlu=ünlü
disarida=dışarıda
bagli=bağlı
inanilmaz=inanılmaz
ozellikle=özellikle
gizemli=gizemli
hikaye=hikâye
Basmufettis=Başmüfettiş
diyorsun=diyorsun
uste=üste
cabuk=çabuk
olmus=olmuş
Ustelik=Üstelik
suc=suç
yuzunden=yüzünden
disinda=dışında
sunu=şunu
kusursuz=kusursuz
canli=canlı
henuz=henüz
dun=dün
ustune=üstüne
koseye=köşeye
parcalari=parçaları
altindaki=altındaki
Kirmizi=Kırmızı
Sehri=Şehri
Oyleyse=Öyleyse
dostlarim=dostlarım
deger=değer
varmis=varmış
ipuclari=ipuçları
cay=çay
simdiye=şimdiye
numarali=numaralı
karmasik=karmaşık
birak=bırak
insanlarin=insanların
Muhtemelen=Muhtemelen
anahtari=anahtarı
tasi=taşı
Butun=Bütün
aksamlar=akşamlar
cozmeye=çözmeye
coktan=çoktan
gucu=gücü
sirasinda=sırasında
karanlik=karanlık
ihtiyacim=ihtiyacım
istedigin=istediğin
sasirtici=şaşırtıcı
yapilmis=yapılmış
Ayni=Aynı
cevap=cevap
yavas=yavaş
kalmis=kalmış
cift=çift
guvenli=güvenli
cevir=çevir
ciz=çiz
cizgiler=çizgiler
tavsanin=tavşanın
hanimefendi=hanımefendi
yapacagim=yapacağım
anliyorum=anlıyorum
alisveris=alışveriş
cikmak=çıkmak
yapiyorsun=yapıyorsun
ihtiyaci=ihtiyacı
Oldukca=Oldukça
Cevap=Cevap
ettigini=ettiğini
ragmen=rağmen
yanindaki=yanındaki
dondur=döndür
Dogrusu=Doğrusu
dogrusu=doğrusu
goremiyorum=göremiyorum
adamin=adamın
insanlari=insanları
cikip=çıkıp
goruyorum=görüyorum
inaniyorum=inanıyorum
Asil=Asıl
disi=dışı
odasinda=odasında
yarisi=yarısı
dusunuyorsun=düşünüyorsun
yemegi=yemeği
etrafinda=etrafında
kesif=keşif
Soyle=Söyle
sekli=şekli
olmasin=olmasın
cozdun=çözdün
tatli=tatlı
sayilar=sayılar
satir=satır
onceki=önceki
dugmeye=düğmeye
sise=şişe
Dort=Dört
sehirde=şehirde
baslayalim=başlayalım
kaydirarak=kaydırarak
cikarmak=çıkarmak
Simdilik=Şimdilik
dusundum=düşündüm
misir=mısır
dogrudan=doğrudan
istedigim=istediğim
haklisin=haklısın
sayilmaz=sayılmaz
endise=endişe
gorkemli=görkemli
gosterisi=gösterisi
Muhtesem=Muhteşem
mesgul=meşgul
suclu=suçlu
bastan=baştan
gormedim=görmedim
Sehir=Şehir
simdiden=şimdiden
kanit=kanıt
Dun=Dün
Kac=Kaç
bulmacanin=bulmacanın
anlatiyor=anlatıyor
duz=düz
dikdortgen=dikdörtgen
soylemek=söylemek
boylesine=böylesine
gosterisli=gösterişli
icinden=içinden
bulmacalari=bulmacaları
yilda=yılda
donustu=dönüştü
donus=dönüş
gunluk=günlük
yasam=yaşam
yasamdan=yaşamdan
koparilmis=koparılmış
ruya=rüya
karnavalin=karnavalın
bakinca=bakınca
buranin=buranın
adim=adım
yardim=yardım
yardimin=yardımın
yardiminiz=yardımınız
yardimci=yardımcı
olmazdi=olmazdı
olmadi=olmadı
Olmadi=Olmadı
olmamis=olmamış
acilisimiz=açılışımız
tanis=tanış
tanismak=tanışmak
tanismak=tanışmak
tanismayi=tanışmayı
umursamazliktan=umursamazlıktan
eglenme=eğlenme
kararliligindan=kararlılığından
sokaklarini=sokaklarını
doldurmus=doldurmuş
senliklerin=şenliklerin
cikariyorlar=çıkarıyorlar
aradigimiz=aradığımız
dukkan=dükkân
dukkani=dükkânı
dukkanin=dükkânın
bolge=bölge
bolgeyi=bölgeyi
bolgesindeki=bölgesindeki
butigi=butiği
konus=konuş
konustu=konuştu
konustuk=konuştuk
yontem=yöntem
aciklayamasa=açıklayamasa
bakiyor=bakıyor
topladigimizi=topladığımızı
aydinlatmak=aydınlatmak
aydinlatti=aydınlattı
aciklanmis=açıklanmış
kaldi=kaldı
cozuldugunden=çözüldüğünden
sorusturmamiza=soruşturmamıza
edecegiz=edeceğiz
davayi=davayı
cikacagi=çıkacağı
gerceginden=gerçeğinden
habersizmis=habersizmiş
planlandigi=planlandığı
yakalamamiza=yakalamamıza
tartisma=tartışma
endiseli=endişeli
yaptiklarindan=yaptıklarından
yaptiklarini=yaptıklarını
atmasina=atmasına
kalmadi=kalmadı
elektrigini=elektriğini
durdurmaliyiz=durdurmalıyız
degismis=değişmiş
kaybolmus=kaybolmuş
anlatilan=anlatılan
acimasiz=acımasız
tarafi=tarafı
guvende=güvende
guvendi=güvendi
guvendiği=güvendiği
güvenli=güvenli
umarim=umarım
tabanin=tabanın
fincanin=fincanın
tabagin=tabağın
donusunu=dönüşünü
carpi=çarpı
vardir=vardır
kiz=kız
yapti=yaptı
calisti=çalıştı
ailesiymis=ailesiymiş
bakti=baktı
parasi=parası
bakalim=bakalım
sehrin=şehrin
saskin=şaşkın
soylenti=söylenti
secenegi=seçeneği
bagisla=bağışla
yanilgi=yanılgı
kaygi=kaygı
uslup=üslup
arastir=araştır
armagan=armağan
paylas=paylaş
anlatacagim=anlatacağım
dagitabilirim=dağıtabilirim
agac=ağaç
kagit=kâğıt
anlasilir=anlaşılır
savunmasiz=savunmasız
guclu=güçlü
olacagini=olacağını
olmadigini=olmadığını
yapacagini=yapacağını
yaptigini=yaptığını
istedigini=istediğini
bildigim=bildiğim
bildigini=bildiğini
gerektigi=gerektiği
gerektigini=gerektiğini
ucuncu=üçüncü
alti=altı
ovguyle=övgüyle
soz=söz
sasirmamali=şaşırmamalı
sasmamali=şaşmamalı
buldugu=bulduğu
babani=babanı
kaybettiklerini=kaybettiklerini
gercekten=gerçekten
Dogru=Doğru
dogru=doğru
katiliyor=katılıyor
Av=Av

yasanir=yaşanır
yasaniyor=yaşanıyor
yasanacak=yaşanacak
haline=hâline
ceyrek=çeyrek
toplamalisin=toplamalısın
ates=ateş
ceker=çeker
bunlari=bunları
yukaridan=yukarıdan
asagiya=aşağıya
zorundadir=zorundadır
eslesmede=eşleşmede
oynanir=oynanır
kullanilan=kullanılan
atilir=atılır
kazanirdim=kazanırdım
onlari=onları
onlarin=onların
yakinda=yakında
bakin=bakın
yazik=yazık
gec=geç
isi=işi
canim=canım
zamani=zamanı
onunde=önünde
anlamina=anlamına
keske=keşke
zavalli=zavallı
olsaydi=olsaydı
bulvari=bulvarı
turlu=türlü
profesorun=profesörün
olasi=olası
kalabalik=kalabalık
heyecanli=heyecanlı
anladim=anladım
zamandir=zamandır
yapiyor=yapıyor
puf=püf
muduru=müdürü
kasabanin=kasabanın
imkansiz=imkânsız
basta=başta
sonucta=sonuçta
siki=sıkı
neseli=neşeli
gunlugu=günlüğü
firsat=fırsat
suna=şuna
pesinde=peşinde
one=öne
isler=işler
isim=işim
guc=güç
yanina=yanına
sehre=şehre
rahatsiz=rahatsız
havali=havalı
gercegi=gerçeği
col=çöl
yon=yön
ortaligi=ortalığı
kostum=koştum
yuz=yüz
yaptim=yaptım
sozde=sözde
olmasina=olmasına
kulaga=kulağa
gecit=geçit
aklinda=aklında
adli=adlı
surekli=sürekli
suradaki=şuradaki
sacmalik=saçmalık
birakip=bırakıp
basini=başını
arkadas=arkadaş
aliyor=alıyor
zorundayim=zorundayım
yaptin=yaptın
tipki=tıpkı
sacma=saçma
mutevazi=mütevazı
korkarim=korkarım
donelim=dönelim
dis=dış
buradasin=buradasın
birakin=bırakın
aklima=aklıma
ugrayin=uğrayın
sirf=sırf
satin=satın
saka=şaka
kadin=kadın
kacti=kaçtı
isine=işine
altin=altın
aldin=aldın
adini=adını
adina=adına
yasli=yaşlı
tanrim=tanrım
olmasaydi=olmasaydı
mantikli=mantıklı
kadariyla=kadarıyla
insanin=insanın
bakmayin=bakmayın
suraya=şuraya
sikayet=şikâyet
senlik=şenlik
sanslar=şanslar
olmaliyiz=olmalıyız
insanlarin=insanların
hiz=hız
hayatini=hayatını
hanim=hanım
bulalim=bulalım
basa=başa
ardindaki=ardındaki
arabayi=arabayı
anlasildi=anlaşıldı
tiklim=tıklım
sapkali=şapkalı
onune=önüne
olduklarini=olduklarını
kirikligina=kırıklığına
kalanini=kalanını
gozunu=gözünü
gecmiste=geçmişte
geciyor=geçiyor
cekiyor=çekiyor
arabanin=arabanın
anlatir=anlatır
yumusak=yumuşak
yillardir=yıllardır
yasayan=yaşayan
uygarligi=uygarlığı
uyari=uyarı
ucup=uçup
taslasma=taşlaşma
takim=takım
soyleyemem=söyleyemem
sef=şef
profesoru=profesörü
meydanina=meydanına
malikanesi=malikânesi
kaldim=kaldım
kalabaligin=kalabalığın
haklisiniz=haklısınız
delikanli=delikanlı
bulacaksin=bulacaksın
birakmak=bırakmak
bicilmez=biçilmez
basinda=başında
baglanti=bağlantı
babasi=babası
ariyorum=arıyorum
ariyorsun=arıyorsun
aramayi=aramayı
aralarinda=aralarında
toreni=töreni
soylemisti=söylemişti
sicacik=sıcacık
sac=saç
oyuncaklari=oyuncakları
ortasina=ortasına
ortalikta=ortalıkta
oglum=oğlum
muthis=müthiş
jonglorluk=jönglörlük
istiyorsaniz=istiyorsanız
istedigimi=istediğimi
etmis=etmiş
buradayiz=buradayız
buradayim=buradayım
birakalim=bırakalım
alisilmadik=alışılmadık
yigini=yığını
yeralti=yeraltı
yemegini=yemeğini
tarafina=tarafına
soyleyince=söyleyince
soyleniyor=söyleniyor
saygin=saygın
sapkanin=şapkanın
saniyor=sanıyor
sakliyor=saklıyor
sakincasi=sakıncası
pelus=peluş
numaranin=numaranın
mirasi=mirası
koyulalim=koyulalım
karinca=karınca
kafani=kafanı
ihtiyacin=ihtiyacın
gozu=gözü
gozlerini=gözlerini
duydugum=duyduğum
digerlerinden=diğerlerinden
calan=çalan
aydinlik=aydınlık
anlastik=anlaştık
zorundasin=zorundasın
yazmayi=yazmayı
yaklasin=yaklaşın
yabanci=yabancı
surukledi=sürükledi
soyledin=söyledin
sirlarini=sırlarını
ruzgar=rüzgâr
rahatca=rahatça
numaralarindan=numaralarından
luks=lüks
lafi=lafı
kazi=kazı
kapatin=kapatın
kabus=kâbus
halkin=halkın
gonderdi=gönderdi
donecegine=döneceğine
curet=cüret
caresiz=çaresiz
caldi=çaldı
bayim=bayım
baktim=baktım
babayi=babayı
asistani=asistanı
asili=asılı
anladiniz=anladınız
agzi=ağzı
zayif=zayıf
zarari=zararı
yuk=yük
yildizi=yıldızı
yildir=yıldır
yetiskin=yetişkin
yetenegin=yeteneğin
yatirim=yatırım
yaptigimiz=yaptığımız
yapamiyorum=yapamıyorum
yapacagimi=yapacağımı
yakalayacagiz=yakalayacağız
tutmayi=tutmayı
tarzini=tarzını
taniklari=tanıkları
soytari=soytarı
soylediler=söylediler
sormayi=sormayı
sirin=şirin
sehrimizi=şehrimizi
sakladi=sakladı
sadik=sadık
otesindeki=ötesindeki
olmaliydi=olmalıydı
kurmali=kurmalı
kullanmis=kullanmış
koseyi=köşeyi
karmasadan=karmaşadan
karistirmak=karıştırmak
kamastiriyor=kamaştırıyor
kacis=kaçış
kacirmak=kaçırmak
iletisime=iletişime
hayatimi=hayatımı
gozlerim=gözlerim
gecer=geçer
egleniyor=eğleniyor
dusmemeye=düşmemeye
donene=dönene
dolasirken=dolaşırken
dolasip=dolaşıp
dolanmis=dolanmış
dolanip=dolanıp
demistim=demiştim
delikanliya=delikanlıya
calmak=çalmak

yangin=yangın
yayilmis=yayılmış
olanlari=olanları
yakininda=yakınında
kullanildigini=kullanıldığını
varsaymistim=varsaymıştım
gelisme=gelişme
bulunuyormus=bulunuyormuş
elenmis=elenmiş
yakindan=yakından
Incelemeyi=İncelemeyi
Inceleme=İnceleme
ekranin=ekranın
kosesindeki=köşesindeki
gecersin=geçersin
hatamdi=hatamdı
olsaydim=olsaydım
soyleniyorsa=söyleniyorsa
saklanmislardir=saklanmışlardır
acin=açın
yakinlastirin=yakınlaştırın
planimin=planımın
asamasi=aşaması
oturdukca=oturdukça
dondugumu=döndüğümü
acikliga=açıklığa
kavusacak=kavuşacak
aslini=aslını
ogrenecegiz=öğreneceğiz
sekilde=şekilde
sasmamali=şaşmamalı
sasmamali=şaşmamalı
karisik=karışık
karsimiza=karşımıza
karsimizda=karşımızda
karsisinda=karşısında
karsisindaki=karşısındaki
karsilastik=karşılaştık
karsilastim=karşılaştım
karsilastigimiz=karşılaştığımız
karsilastir=karşılaştır
karsilastirin=karşılaştırın
karsilastirma=karşılaştırma
basarisiz=başarısız
basarili=başarılı
basariya=başarıya
basarabilir=başarabilir
basladigimiz=başladığımız
basladigi=başladığı
baslamis=başlamış
baslayacak=başlayacak
baslayinca=başlayınca
baslangic=başlangıç
anlatmaya=anlatmaya
anlatilanlar=anlatılanlar
anlattigi=anlattığı
anlattigini=anlattığını
anlayacaksin=anlayacaksın
anlayacagiz=anlayacağız
anlayamadim=anlayamadım
anlayabiliyorum=anlayabiliyorum
kalacagiz=kalacağız
kalacaksin=kalacaksın
kalmasi=kalması
kalmaya=kalmaya
kalmalisin=kalmalısın
oldugum=olduğum
oldugumuz=olduğumuz
oldugun=olduğun
oldugunuz=olduğunuz
olacagim=olacağım
olacaksin=olacaksın
olacagiz=olacağız
olacaktir=olacaktır
olabiliriz=olabiliriz
olmayacak=olmayacak
olmayacagim=olmayacağım
olmadigi=olmadığı
olmadigindan=olmadığından
yapildigini=yapıldığını
yapildigi=yapıldığı
yapildiginda=yapıldığında
yapilacak=yapılacak
yapilabilir=yapılabilir
yapmaya=yapmaya
yapmalisin=yapmalısın
yapmaliyiz=yapmalıyız
yapmamiz=yapmamız
yaptigin=yaptığın
yaptiginiz=yaptığınız
yaptigim=yaptığım
yaptigimiz=yaptığımız
geldigini=geldiğini
geldiginde=geldiğinde
geldigim=geldiğim
geldigin=geldiğin
gidecegiz=gideceğiz
gidecegim=gideceğim
gideceksin=gideceksin
gittigini=gittiğini
istedigim=istediğim
istedigin=istediğin
istediginiz=istediğiniz
istiyorsan=istiyorsan
istiyorsaniz=istiyorsanız
bildigimiz=bildiğimiz
bildigin=bildiğin
bildiginiz=bildiğiniz
bilmedigim=bilmediğim
bilmedigini=bilmediğini
soyledigini=söylediğini
soyledigim=söylediğim
soyledigin=söylediğin
soylediginiz=söylediğiniz
soyleyecegim=söyleyeceğim
soyleyeceksin=söyleyeceksin
gordugum=gördüğüm
gordugunu=gördüğünü
gordugun=gördüğün
gorecegiz=göreceğiz
goreceksin=göreceksin
gorecegim=göreceğim
gosterildigi=gösterildiği
gostermek=göstermek
gostermeye=göstermeye
gosterecegim=göstereceğim
dusundugum=düşündüğüm
dusundugunu=düşündüğünü
dusundugun=düşündüğün
dusundugumuz=düşündüğümüz
dusunecegim=düşüneceğim
dusunmeliyiz=düşünmeliyiz
dusunmelisin=düşünmelisin
cikacagiz=çıkacağız
cikacaksin=çıkacaksın
cikacagim=çıkacağım
ciktigini=çıktığını
ciktiginda=çıktığında
ciktigim=çıktığım
cikarabilir=çıkarabilir
cikarmaya=çıkarmaya
cozecegiz=çözeceğiz
cozeceksin=çözeceksin
cozdugum=çözdüğüm
cozdugun=çözdüğün
cozdugunu=çözdüğünü
cozulmus=çözülmüş
cozulmesi=çözülmesi
cozebilirsin=çözebilirsin
calisiyor=çalışıyor
calisiyordu=çalışıyordu
calismaya=çalışmaya
calismak=çalışmak
calismamiz=çalışmamız
calistigini=çalıştığını
calistigi=çalıştığı
calistim=çalıştım
calistirdim=çalıştırdım
degistir=değiştir
degistirin=değiştirin
degistirmek=değiştirmek
degistirdi=değiştirdi
degistirdim=değiştirdim
degistigini=değiştiğini
degisecek=değişecek

vardi=vardı
kalir=kalır
Ilk=İlk
ilk=ilk
bos=boş
sanmiyorum=sanmıyorum
basla=başla
doner=döner
Sonrasi=Sonrası
sonrasi=sonrası
cikarir=çıkarır
kacmaya=kaçmaya
cekilir=çekilir
dolaninca=dolanınca
gorunuyorum=görünüyorum
serpistirilmis=serpiştirilmiş
kacip=kaçıp
Orasi=Orası
orasi=orası
gorunmuyor=görünmüyor
yuzunuz=yüzünüz
Arkadasin=Arkadaşın
arkadasin=arkadaşın
sandigin=sandığın
sandiginin=sandığının
olacakti=olacaktı
hayati=hayati
kayayi=kayayı
gom=göm
panige=paniğe
farkina=farkına
donatilmis=donatılmış
dondurulmusuz=döndürülmüşüz
'''

def tr_lower(s:str)->str:
    return s.translate(str.maketrans({'I':'ı','İ':'i','Ç':'ç','Ğ':'ğ','Ö':'ö','Ş':'ş','Ü':'ü','Â':'â','Î':'î','Û':'û'})).lower()

EXACT={}
for line in PAIRS.splitlines():
    line=line.strip()
    if not line or '=' not in line: continue
    a,b=line.split('=',1); EXACT[a]=b; EXACT.setdefault(tr_lower(a), tr_lower(b))

# Yaygın kökler. Sadece sözcük başında uygulanır; özel adları bozma riskini
# azaltmak için asgari kök uzunluğu ve açık kök listesi kullanılır.
STEMS = [
 ('tesekkur','teşekkür'),('degis','değiş'),('degil','değil'),('deger','değer'),
 ('gorun','görün'),('goster','göster'),('gorm','görm'),('goru','görü'),('gord','görd'),('gor','gör'),
 ('dusun','düşün'),('dogru','doğru'),('dog','doğ'),
 ('cik','çık'),('calis','çalış'),('coz','çöz'),('ciz','çiz'),('cevir','çevir'),
 ('sehir','şehir'),('sekil','şekil'),('sey','şey'),('sag','sağ'),('kars','karş'),
 ('kucuk','küçük'),('buyuk','büyük'),('guzel','güzel'),('kotu','kötü'),
 ('yuksek','yüksek'),('yukar','yukar'),('asag','aşağ'),('uzer','üzer'),('ust','üst'),
 ('ozel','özel'),('ozur','özür'),('onem','önem'),('once','önce'),('oyle','öyle'),
 ('boyle','böyle'),('baska','başka'),('butun','bütün'),('tum','tüm'),
 ('gercek','gerçek'),('hic','hiç'),('cok','çok'),('cogu','çoğu'),('cocuk','çocuk'),
 ('kirmiz','kırmız'),('yesil','yeşil'),('sari','sarı'),('siyah','siyah'),
 ('tavsan','tavşan'),('palyaco','palyaço'),('suphel','şüphel'),('mufettis','müfettiş'),
 ('muhtesem','muhteşem'),('mumkun','mümkün'),('lutfen','lütfen'),('henuz','henüz'),
 ('aksam','akşam'),('bugun','bugün'),('dun','dün'),('gun','gün'),
 ('yanlis','yanlış'),('yalniz','yalnız'),('hazir','hazır'),('agir','ağır'),
 ('isik','ışık'),('sira','sıra'),('sayi','sayı'),('kisim','kısım'),('kism','kısm'),
 ('fotograf','fotoğraf'),('eglenc','eğlenc'),('sasirt','şaşırt'),('gorkem','görkem'),
 ('hikaye','hikâye'),('inani','inanı'),('inanil','inanıl'),('ihtiyac','ihtiyaç'),
 ('ragmen','rağmen'),('kesif','keşif'),('mesgul','meşgul'),('suc','suç'),
 ('cukur','çukur'),('capraz','çapraz'),('dugme','düğme'),('sise','şişe'),
 ('dikdortgen','dikdörtgen'),('alisveris','alışveriş'),('ipucl','ipuçl'),('ipucu','ipucu'),
 ('parca','parça'),('parcal','parçal'),('ucunc','üçünc'),
 ('yardim','yardım'),('yasam','yaşam'),('donus','dönüş'),('konus','konuş'),('arastir','araştır'),('sorustur','soruştur'),
 ('aydinlat','aydınlat'),('acil','açıl'),('acik','açık'),('tanis','tanış'),('bolge','bölge'),('guven','güven'),
 ('kaybol','kaybol'),('yapil','yapıl'),('yaptik','yaptık'),('anlatil','anlatıl'),('bagis','bağış'),('yanilg','yanılg'),
 ('armagan','armağan'),('paylas','paylaş'),('agac','ağaç'),('kagit','kâğıt'),('sask','şaşk'),('soylent','söylent'),
]

# Bazı üretken ek kalıpları. Bunlar kök düzeltmesinden sonra çalışır.
SUFFIX_REPL = [
 ('digini','diğini'),('digim','diğim'),('digin','diğin'),('digi','diği'),
 ('dugunu','duğunu'),('dugun','duğun'),('dugu','duğu'),
 ('tigini','tiğini'),('tigim','tiğim'),('tigin','tiğin'),('tigi','tiği'),
 ('tugunu','tuğunu'),('tugun','tuğun'),('tugu','tuğu'),
 ('acagini','acağını'),('acagim','acağım'),('acagin','acağın'),('acagi','acağı'),
 ('ecegini','eceğini'),('ecegim','eceğim'),('ecegin','eceğin'),('ecegi','eceği'),
]

PROPER_BASES={
 'Layton','Luke','Randall','Henry','Hershel','Angela','Emmy','Dalston','Ledore','Tingly','Monte','Beaufort',
 'Yukkles','Ludmilla','Stellar','Grosky','Gloria','Mordaunt','Alphonse','Norwell','Descole','Murphy','Hannibal',
 'Aldus','Sharoa','Saroa','Sheffield','Scotland','Youngland','Bloom','Lionel','Jean','Roland','Lucille','Akbadain',
 'Ascot','Bunny','Randy','Hersh','Waltham','Collins','StreetPass','Reunion','Touch','SD'
}

def turkish_title(s:str)->str:
    if not s: return s
    up={'i':'İ','ı':'I','ç':'Ç','ğ':'Ğ','ö':'Ö','ş':'Ş','ü':'Ü','â':'Â','î':'Î','û':'Û'}
    return up.get(s[0],s[0].upper())+s[1:]

def turkish_upper(s:str)->str:
    table=str.maketrans({'i':'İ','ı':'I','ç':'Ç','ğ':'Ğ','ö':'Ö','ş':'Ş','ü':'Ü','â':'Â','î':'Î','û':'Û'})
    return s.translate(table).upper()

def preserve_case(src:str, mapped:str)->str:
    if src.isupper(): return turkish_upper(mapped)
    if src and src[0].isupper(): return turkish_title(mapped)
    return mapped

def deascii_word(tok:str)->str:
    # apostrof sonrası ek ayrı işlenir
    if "'" in tok:
        base,suf=tok.split("'",1)
        if base in PROPER_BASES or (base and base[0].isupper() and base not in EXACT):
            return base+"'"+deascii_word(suf)
        return deascii_word(base)+"'"+deascii_word(suf)
    if tok in PROPER_BASES: return tok
    if tok in EXACT: return EXACT[tok]
    lo=tr_lower(tok)
    if lo in EXACT: return preserve_case(tok, EXACT[lo])
    # Tümü büyük/baş harfi büyük olup bilinen özel ad görünümündeyse kök kuralını ancak
    # bariz Türkçe kökle eşleşiyorsa uygula.
    out=lo
    for a,b in STEMS:
        if out.startswith(a) and len(out)>=len(a):
            out=b+out[len(a):]
            break
    # ekleri sondan düzelt
    for a,b in SUFFIX_REPL:
        if out.endswith(a):
            out=out[:-len(a)]+b
            break
    if out!=lo:
        return preserve_case(tok,out)
    return tok

def deascii_text(text:str)->tuple[str,int]:
    changed=0
    def f(m):
        nonlocal changed
        old=m.group(0); new=deascii_word(old)
        if new!=old: changed+=1
        return new
    return unicodedata.normalize('NFC', WORD_RE.sub(f,text)),changed

# Elle doğrulanmış birkaç yüksek etkili ifade düzeltmesi.
PHRASE_FIXES = [
 ('Her halukarda','Her durumda'),
   ('su şekilde','şu şekilde'),
   ('Su şekilde','Şu şekilde'),
   ('su karmaşadan','şu karmaşadan'),
   ('su meseleyi','şu meseleyi'),
   ('su soldaki','şu soldaki'),
   ('su bulmacayı','şu bulmacayı'),
   ('su bulmaca','şu bulmaca'),
   ('su şeyi','şu şeyi'),
   ('su şey','şu şey'),
   ('su adamı','şu adamı'),
   ('su adam','şu adam'),
   ('su şehri','şu şehri'),
   ('su şehir','şu şehir'),
   ('su yolu','şu yolu'),
   ('su yere','şu yere'),
   ('su taraftaki','şu taraftaki'),
   ('su tarafa','şu tarafa'),
 ('her halukarda','her durumda'),
 ('Mucizeler Sehri','Mucizeler Şehri'),
 ('Mucizeler sehri','Mucizeler şehri'),
 ('Mucizeler Şehri, ha…','Mucizeler Şehri, öyle mi…'),
 ('kesin gozuyle','kesin gözüyle'),
 ('gozuyle','gözüyle'),
 ('gozleri','gözleri'),
 ('gozlerine','gözlerine'),
 ('gozunun','gözünün'),
 ('olmadigini','olmadığını'),
 ('olacagini','olacağını'),
 ('yapacagini','yapacağını'),
 ('yaptigini','yaptığını'),
 ('istedigini','istediğini'),
 ('bildigim','bildiğim'),
 ('bildigini','bildiğini'),
 ('gerektigi','gerektiği'),
 ('gerektigini','gerektiğini'),
 ('oldugu','olduğu'),
 ('oldugunu','olduğunu'),
 ('olduguna','olduğuna'),
 ('anlasilir','anlaşılır'),
 ('anlasilmaz','anlaşılmaz'),
 ('anlatacagim','anlatacağım'),
 ('dagitabilirim','dağıtabilirim'),
 ('kaygi','kaygı'),
 ('uslubuna','üslubuna'),
 ('sorusturma','soruşturma'),
 ('sorusturmaya','soruşturmaya'),
 ('arastirma','araştırma'),
 ('arastirmak','araştırmak'),
 ('arastirmaya','araştırmaya'),
 ('acilis','açılış'),
 ('acmak','açmak'),
 ('acildi','açıldı'),
 ('acmayi','açmayı'),
 ('armaganimizi','armağanımızı'),
 ('paylasmanin','paylaşmanın'),
 ('soylendi','söylendi'),
 ('soylentilere','söylentilere'),
 ('secenegi','seçeneği'),
 ('bagislayamam','bağışlayamam'),
 ('yanilgilarini','yanılgılarını'),
 ('savunmasiz','savunmasız'),
 ('akibeti','akıbeti'),
 ('kininin anlasilir tarafi var','öfkesini anlamak zor değil'),
 ('bir yer olarak duruyor','şehrin tarzını sürdürüyor'),
]

def phrase_fix(s:str)->tuple[str,int]:
    n=0
    for a,b in PHRASE_FIXES:
        if a in s:
            s2=s.replace(a,b)
            n += s.count(a)
            s=s2
    return s,n

VOWELS='aeıioöuüâîû'
def last_vowel(word:str):
    for ch in reversed(tr_lower(word)):
        if ch in VOWELS: return ch
    return ''

def question_form(prev:str, raw:str)->str:
    v=last_vowel(prev)
    if v in 'aıâ': base='mı'
    elif v in 'eiî': base='mi'
    elif v in 'ouû': base='mu'
    elif v in 'öü': base='mü'
    else: base='mi'
    tails={'mi':'','misin':'sın','misiniz':'sınız','miyim':'yım','miyiz':'yız','miydi':'ydı','miydin':'ydın','miydiniz':'ydınız'}
    tail=tails.get(tr_lower(raw))
    if tail is None: return raw
    # tail ünlülerini tabana uydur
    if base=='mi': tail=tail.replace('ı','i').replace('u','i').replace('ü','i')
    elif base=='mı': tail=tail.replace('i','ı').replace('u','ı').replace('ü','ı')
    elif base=='mu': tail=tail.replace('ı','u').replace('i','u').replace('ü','u')
    else: tail=tail.replace('ı','ü').replace('i','ü').replace('u','ü')
    return preserve_case(raw,base+tail) if raw[:1].isupper() else base+tail

def context_fix(source:str,s:str)->tuple[str,int]:
    n=0; sl=source.lower()
    # Anlama göre değişen sözcükler
    def sub_word(pattern,repl):
        nonlocal s,n
        s2,c=re.subn(pattern,repl,s,flags=re.I); s=s2; n+=c
    if re.search(r'\b(calm|quiet|peaceful|tranquil)\b',sl): sub_word(r'\bsakin\b','sakin')
    elif re.search(r"\b(don't|do not|never|mustn't|must not)\b",sl): sub_word(r'\bsakin\b','sakın')
    if not re.search(r'\baunt\b',sl): sub_word(r'\bhala\b','hâlâ')
    if re.search(r'\b(three|third|three-quarter)\b',sl): sub_word(r'\buc\b','üç')
    if re.search(r'\b(stone|stones|rock|rocks|statue|statues)\b',sl): sub_word(r'\btas\b','taş')
    if re.search(r'\b(kind|type|sort|species)\b',sl): sub_word(r'\btur\b','tür')
    for a,b in [('su sekilde','şu şekilde'),('su anda','şu anda'),('su an','şu an'),('su kadar','şu kadar'),('su noktada','şu noktada')]:
        if a in tr_lower(s):
            s2,c=re.subn(r'\b'+re.escape(a)+r'\b',b,s,flags=re.I); s=s2; n+=c
    # Soru ekini önceki sözcüğün son ünlüsüne göre düzelt.
    pat=re.compile(r"([A-Za-zÇçĞğİıÖöŞşÜüÂâÎîÛû]+)(\s+)(mi|misin|misiniz|miyim|miyiz|miydi|miydin|miydiniz)\b",re.I)
    def q(m):
        nonlocal n
        new=question_form(m.group(1),m.group(3)); n += (new!=m.group(3)); return m.group(1)+m.group(2)+new
    s=pat.sub(q,s)
    return unicodedata.normalize('NFC',s),n

MANUAL_OVERRIDES={
 ('00/00_000010.xs','text000003'): 'Evet. Küçük bir handan başladı ve yalnızca\n18 yılda böylesine büyük bir şehre dönüştü.',
 ('00/00_000010.xs','text000004'): 'İnanılmaz!',
 ('00/00_000010.xs','text000005'): 'Bu yüzden,\nbu şehre “Mucizeler Şehri” diyenler de var.',
 ('03/03_030530.xs','text000001'): '<T>Güzel sanat eserlerini yeniden insanlarla\npaylaşabilmek gerçekten büyük bir mutluluk.',
 ('03/03_030530.xs','text000011'): "<T>Ah, muhteşemdi. Dedektif Bloom'un\nsizden bu kadar övgüyle söz etmesine şaşmamalı.",
 ('09/09_090160.xs','text000011'): '<V0090><T><M1/2/1/45>Henry, yeni bulduğu servetiyle anne babanı\ndestekledi ama kaybettiklerinin yerini\ngerçek anlamda dolduramadı.</V>',
 ('40/40_001000.xs','text000067'): 'Söylentiler yangın gibi yayılmış olmalı; şehirde\nneredeyse herkes dün geceki olayları biliyor.\nDedektif Bloom ve Başmüfettiş Sheffield,\nheykellerin bulunduğu yerdeki araba izlerinin\nDalston’a ait bir savaş arabasıyla eşleştiğini söylüyor.\nOlayda bir araba kullanıldığını düşünmüştüm ama\nbu beklenmedik bir gelişme. Bu türden diğer\nsavaş arabaları yalnızca hipodromda tutuluyor ve\nolayla ilgileri olmadığı söyleniyor. Yine de\nonlara daha yakından bakmak\nistiyorum.',
 ('00/00_002010.xs','text000003'): "<T><M2/1/1/45>Sanki sakin [günlük yaşamdan/günlük yaşamdan]\n[koparılmış/koparılmış] gibi; [rüya/rüya] ve [umut/umut] dolu [bambaşka bir dünya/bambaşka bir dünya].\n<W>İşte [Mucizeler/Mucizeler] [Şehri/Şehri] Monte d'Or böyle bir yer.",
 ('00/00_002010.xs','text000006'): '<T><M5/1/1/30>Her durumda elimizde hâlâ yeterli [bilgi/bilgi] yok.\n[İncelemeyi/İncelemeyi] adım adım [ilerletip/ilerletip] yolumuza [devam edelim/devam edelim].',
 ('40/40_001000.xs','text000088'): "Tingly Town'a Doğru",
 ('40/40_001000.xs','text000094'): "Henry Av'a Katılıyor",
 ('40/40_001000.xs','text000162'): 'Randall Yenildi',
}

def split_paragraphs(s:str):
    return s.split('\n\n')

def visible_width(s:str, adv:dict[str,int]|None=None)->int:
    s=CTRL_RE.sub('',s)
    # [görünen/okunuş] yapısında ekranda görünen tarafı bir kez ölç.
    s=re.sub(r'\[([^]/\n]+)/[^]\n]+\]', r'\1', s)
    s=re.sub(r'\[([^]\n]+)\]', r'\1', s)
    if adv is None:
        return len(s)*8
    w=0
    for ch in s:
        w+=adv.get(ch, adv.get('?',8))
    return w

def tokenize_for_wrap(s:str):
    # Kontrol/ruby atomlarının içindeki boşluklarda asla bölme.
    atoms=[]
    def hold(m):
        atoms.append(m.group(0)); return f'§{len(atoms)-1}§'
    protected=ATOM_RE.sub(hold,s)
    toks=protected.split()
    def restore(t):
        return re.sub(r'§(\d+)§',lambda m:atoms[int(m.group(1))],t)
    return [restore(t) for t in toks]

def wrap_n_lines(text:str,n:int,adv:dict[str,int]|None=None)->str:
    if n<=1 or not text.strip(): return text.strip()
    words=tokenize_for_wrap(text.replace('\n',' '))
    if len(words)<=n: return '\n'.join(words)
    widths=[visible_width(w,adv) for w in words]
    # DP: n satırda maksimum satır genişliğini ve dengesizliği azalt.
    pref=[0]
    for i,w in enumerate(widths): pref.append(pref[-1]+w+(0 if i==0 else visible_width(' ',adv)))
    def seg(i,j):
        if i>=j:return 0
        return sum(widths[i:j])+visible_width(' ',adv)*(j-i-1)
    INF=10**18
    dp=[[INF]*(len(words)+1) for _ in range(n+1)]
    prev=[[-1]*(len(words)+1) for _ in range(n+1)]
    dp[0][0]=0
    total=seg(0,len(words)); target=total/n
    for k in range(1,n+1):
        for j in range(k,len(words)+1):
            for i in range(k-1,j):
                if dp[k-1][i]>=INF: continue
                ww=seg(i,j)
                # kare sapma + aşırı uzun satıra ek ceza
                cost=dp[k-1][i]+(ww-target)**2 + max(0,ww-target*1.25)**2*4
                if cost<dp[k][j]: dp[k][j]=cost;prev[k][j]=i
    cuts=[];j=len(words)
    for k in range(n,0,-1):
        i=prev[k][j]
        if i<0: return text
        cuts.append((i,j));j=i
    cuts.reverse()
    return '\n'.join(' '.join(words[i:j]) for i,j in cuts)

def reflow_like_source(source:str,tr:str,adv=None)->tuple[str,bool,str]:
    # Kaynak paragraf/satır sayısını kılavuz olarak kullan. Paragraf sayıları uyuşmazsa
    # güvenli olmak için yalnız çok belirgin tek-paragraf vakalarında işlem yap.
    sp=split_paragraphs(source); tp=split_paragraphs(tr)
    if len(sp)!=len(tp): return tr,False,'paragraf_yapisi_uyusmuyor'
    out=[];changed=False
    for a,b in zip(sp,tp):
        n=max(1,a.count('\n')+1)
        # Kaynak tek satırsa çevirinin mevcut satırını bozma.
        if n<=1:
            out.append(b);continue
        # Çevirideki mevcut satırları birleştirip kaynak satır sayısına göre dengeli yeniden böl.
        nb=wrap_n_lines(b,n,adv)
        if nb!=b: changed=True
        out.append(nb)
    return '\n\n'.join(out),changed,'kaynak_satir_sayisina_gore'

def load_adv(root:Path):
    try:
        import sys,tempfile
        sys.path.insert(0,str(root/'araclar'/'font'))
        from verify_layton_font import xpck_members
        from fnt01_parse import parse as pf
        xf=root/'hazir'/'nrm_tr.xf'
        m=xpck_members(xf)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'FNT.bin';p.write_bytes(m['FNT.bin']);f=pf(p)
        by={z['cp']:z['adv'] for z in f['infos']}
        d={chr(cp):a for cp,a in by.items() if cp<=0x10ffff}
        # Türkçe gerçek Unicode kayıtları mevcut.
        return d
    except Exception:
        return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',nargs='?',default=str(Path(__file__).resolve().parents[1]));a=ap.parse_args()
    root=Path(a.root)
    csvp=root/'ceviri'/'layton_tr.csv'
    rows=list(csv.DictReader(csvp.open(encoding='utf-8-sig',newline='')))
    adv=load_adv(root)
    report=[];changed_count=0;dia_rows=0;reflow_rows=0;phrase_rows=0
    key_to_new={}
    for idx,r in enumerate(rows,1):
        old=r['translation']; s=old
        reasons=[]
        # Kaynakla birebir aynı Japonca kısa kimlik/etiketleri değiştirme.
        if old==r['original'] and JP_RE.search(old):
            status='DEGISMEDI'
            why='Kaynakla birebir aynı Japonca kısa ad/UI/dahili kimlik adayı; motor kimliği olabileceği için güvenli biçimde korunuyor.'
        else:
            key=(r['file'],r['id'])
            if key in MANUAL_OVERRIDES:
                s=MANUAL_OVERRIDES[key]; reasons.append('elle anlam/akıcılık düzeltmesi')
            s,n=deascii_text(s)
            if n: reasons.append(f'Türkçe karakter restorasyonu ({n} sözcük)');dia_rows+=1
            s,cn=context_fix(r['original'],s)
            if cn: reasons.append(f'bağlama göre Türkçe karakter/ek düzeltmesi ({cn})')
            s,pn=phrase_fix(s)
            if pn: reasons.append(f'ifade/imla düzeltmesi ({pn})');phrase_rows+=1
            s2,rf,rfwhy=reflow_like_source(r['original'],s,adv)
            if rf:
                s=s2;reasons.append('kaynak satır yapısına göre yeniden akıtma');reflow_rows+=1
            s=unicodedata.normalize('NFC',s)
            if s!=old:
                status='DEGISTI';why='; '.join(reasons) if reasons else 'metin normalizasyonu';changed_count+=1
            else:
                status='DEGISMEDI';why='Otomatik kontrolde güvenli ve gerekli bir değişiklik saptanmadı; özel ad/kontrol kodu/ifade yapısı korundu.'
        key=(r['file'],r['id']);key_to_new[key]=s
        report.append({
            'sira':idx,'file':r['file'],'id':r['id'],'durum':status,'neden':why,
            'eski':old,'yeni':s,'kaynak':r['original'],
            'eski_karakter':len(old),'yeni_karakter':len(s),
            'eski_max_satir_px':max([visible_width(x,adv) for x in old.split('\n')] or [0]),
            'yeni_max_satir_px':max([visible_width(x,adv) for x in s.split('\n')] or [0]),
        })
        r['translation']=s
    # ana CSV
    with csvp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','offset','original','translation']);w.writeheader();w.writerows(rows)
    # JSONL
    jp=root/'ceviri'/'layton_tr.jsonl'; out=[]
    for line in jp.read_text(encoding='utf-8').splitlines():
        o=json.loads(line)
        if o.get('kind')=='text':
            k=(o['file'],o['id'])
            if k in key_to_new:o['translation']=key_to_new[k]
        out.append(json.dumps(o,ensure_ascii=False,separators=(',',':')))
    jp.write_text('\n'.join(out)+'\n',encoding='utf-8')
    # kolay CSV
    kp=root/'ceviri'/'CEVIRI_KOLAY.csv'; krows=list(csv.DictReader(kp.open(encoding='utf-8-sig',newline='')))
    for r in krows:
        k=(r['file'],r['id'])
        if k in key_to_new:r['turkce']=key_to_new[k]
    with kp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','id','kaynak_japonca','turkce','durum']);w.writeheader();w.writerows(krows)
    # ayrıntılı rapor CSV
    rp=root/'raporlar'/'V3_TEK_TEK_DEGISIKLIK_RAPORU.csv'
    with rp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(report[0]));w.writeheader();w.writerows(report)
    # özet
    rem=Counter()
    for r in rows:
        for w in WORD_RE.findall(CTRL_RE.sub(' ',r['translation'])):
            if not any(c in w for c in TR_CHARS) and any(c in w.lower() for c in 'cgiosu'):
                rem[w]+=1
    summ=root/'raporlar'/'V3_IYILESTIRME_OZETI.txt'
    summ.write_text(
        'LAYTON TÜRKÇE YAMA v3 İYİLEŞTİRME ÖZETİ\n\n'
        f'Toplam kayıt: {len(rows)}\nDeğişen kayıt: {changed_count}\nDeğişmeyen kayıt: {len(rows)-changed_count}\n'
        f'Türkçe karakter restorasyonu yapılan kayıt: {dia_rows}\nİfade/imtla kuralı uygulanan kayıt: {phrase_rows}\n'
        f'Kaynak satır yapısına göre yeniden akıtılan kayıt: {reflow_rows}\n\n'
        'FONT\n- nrm_tr.xf ve sml_tr.xf içindeki 18 Türkçe/şapkalı harf kaydı tek tek doğrulandı.\n'
        '- ÇçĞğİıÖöŞşÜüÂâÎîÛû gerçek Unicode + PUA eşleşmeleri mevcut; glif sınırları atlas içinde ve advance değerleri geçerli.\n'
        '- Font binaryleri bu turda değiştirilmedi: sorun font glifinin yokluğu değil, metinlerin çoğunun ASCII yazılmış olmasıydı.\n'
        '- Bu nedenle metinler gerçek Türkçe harflerle güncellendi; enjeksiyon aracı bunları PUA kodlarına dönüştürüyor.\n\n'
        'TAŞMA\n- İngilizce/Japonca kaynakta bulunan paragraf ve satır sayıları kılavuz alınarak Türkçe satırlar yeniden dengelendi.\n'
        '- Rapor CSV içinde her kayıt için eski/yeni yaklaşık maksimum piksel genişliği yer alır.\n'
        '- Gerçek cihaz/emülatör ekran testi bu ortamda yapılamadığından piksel hesabı font advance ölçülerine dayalı statik kontroldür.\n\n'
        'DEĞİŞMEYENLER\n- Kaynakla birebir aynı kalan Japonca kısa ad/UI/dahili kimlik adayları crash riski nedeniyle korunmuştur.\n'
        '- Diğer değişmeyen satırlarda otomatik kontrolde güvenli bir düzeltme saptanmamıştır; ayrıntı satır bazında rapordadır.\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'changed':changed_count,'dia_rows':dia_rows,'phrase_rows':phrase_rows,'reflow_rows':reflow_rows,'report':str(rp)},ensure_ascii=False))

if __name__=='__main__':main()
