NEW ART ACADEMY (3DS) — TÜRKÇE YERELLEŞTİRME + FONT KİTİ
========================================================

Bu paket, sağladığınız RomFS arşivindeki İngilizce metinleri çıkarıp Türkçe çeviri sütunu oluşturmak,
çevirileri tekrar oyunun STB dosyalarına yazmak, Türkçe karakterleri destekleyen font yamasını eklemek
ve LayeredFS için RomFS yama klasörü üretmek amacıyla hazırlandı. Orijinal ZIP değiştirilmez.

ÖNEMLİ FONT SONUCU
------------------
Oyunun iki ana CFNA fontu Türkçe glifleri zaten içeriyor:
  fonts/chelseyFont.bcfna   -> Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü = 12/12 mevcut
  fonts/dfhsGothic.bcfna    -> Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü = 12/12 mevcut

Bu nedenle ana STB 1.1 metinlerinde Türkçe karakterler UTF-8 olarak DOĞRUDAN kullanılabilir.

Eski common/materialslibrary-en.stb ise STB 1.0 / tek-bayt Batı Avrupa kodlaması kullanıyor. Bu biçimde
Ğ/ğ/İ/ı/Ş/ş doğrudan kodlanamadığı için kit artık sadeleştirme yapmak yerine font alias yöntemi kullanır:
  Ð -> Ğ
  ð -> ğ
  Ý -> İ
  ÿ -> ı
  Þ -> Ş
  þ -> ş

naa_localizer.py bu altı harfi STB 1.0 içinde uygun CP1252 alias baytlarıyla yazar; aynı build sırasında
chelseyFont ve dfhsGothic içindeki CMAP eşlemeleri mevcut gerçek Türkçe gliflere yönlendirilir. Böylece
çeviri dosyasına normal Türkçe yazarsınız; oyunda da gerçek Türkçe harf görünmesi hedeflenir.

PAKET İÇERİĞİ
--------------
translations_tr.tsv
  Tüm *-en.stb metinleri ile common/credits*.txt kredi satırları. Resmi diller gerçek içerikleriyle yan yana:
  file, id, format, source_en, source_fr, source_de, source_es, source_it, source_nl, source_pt, source_ru,
  tr, source_sha1, notes.
  Çeviriyi yalnızca "tr" sütununa yazın. \n = satır sonu. [f2], [], %s gibi kontrol etiketlerini koruyun.
  RomFS dil kodları: ge=Almanca, sp=İspanyolca, du=Hollandaca, po=Portekizce. Rusça STB'ler UTF-16LE'dir.
  Credits için ayrı resmi dil TXT dosyaları yoktur; common/materialslibrary için Hollandaca/Portekizce/Rusça dosyaları
  RomFS'te bulunmadığından yalnız bu satırlarda ilgili referans hücreleri boş olabilir.

translator_gui.py / 01_ceviri_editorunu_ac.bat
  Üçlü görünüm kullanır: İngilizce kaynak | diğer 7 resmi dil | Türkçe. Diğer diller salt okunur referanstır.
  Python 3 + Tkinter gerekir.

naa_localizer.py
  STB 1.1 UTF-8/UTF-16LE ve STB 1.0 tek-bayt dosyalarını okuyup yazar.
  Varsayılan build artık STB 1.0 için --v100-mode fontmap kullanır ve Türkçe CFNA font yamasını otomatik ekler.

font_tool.py
  Nintendo CFNA içindeki FINF/CMAP tablolarını analiz eder; Türkçe glif kapsamını raporlar ve legacy alias
  eşlemelerini dosya boyutunu değiştirmeden yamalar.

04_fontlari_kontrol_et.bat
  Üzerine romfs.zip sürükleyin. TURKISH_FONT_REPORT.txt oluşturur.

05_sadece_font_yamasi.bat
  Yalnızca iki ana Türkçe font yamasını font_patch_romfs/fonts/ altında üretir.

turkish_fonts/
  Sağladığınız RomFS'ten önceden oluşturulmuş Türkçe alias yamalı iki ana BCFNA fontunun hazır kopyaları.
  Normal 02_yamayi_olustur.bat kullanımında bunları elle kopyalamanız gerekmez; build kaynaktan yeniden üretir.

TURKISH_FONT_REPORT.txt
  Üç CFNA fontunun Türkçe karakter kapsamı. Ana iki font 12/12; eshop.bcfna 0/12.

font_alias_map.tsv
  STB 1.0 için kullanılan Türkçe <-> alias kod noktaları ve CP1252 baytları.

TURKCE_KARAKTER_TESTI.txt
  Ç/Ğ/İ/Ö/Ş/Ü/ç/ğ/ı/ö/ş/ü hızlı test dizisi.

language_files/
  RomFS'teki tüm 8 resmi dil STB dosyalarının kopyaları + credits TXT dosyaları. Toplam 343 dosya.
  Diller: en, fr, ge, sp, it, du, po, ru.

reference_tsv/
  RomFS'te bulunan kaynak TSV tabloları. Ana çeviri kaynağı translations_tr.tsv'dir.

images_to_translate/
  İngilizce yazı/screenshot içeren görseller. Düzenleyip aynı göreli yolla images_edited/ altına koyun.

images_manifest.tsv / images_preview.jpg
  Çevrilecek görsellerin yol listesi ve hızlı önizlemesi.

font_reference/
  Orijinal font/font-bitmap dosyalarının referans kopyaları.

HIZLI KULLANIM
--------------
1) 01_ceviri_editorunu_ac.bat dosyasını çalıştırın
   veya:
     python translator_gui.py translations_tr.tsv

2) "tr" alanlarına NORMAL TÜRKÇE yazın:
     Ç Ğ İ Ö Ş Ü ç ğ ı ö ş ü
   Alias karakterlerini (Ð/ð/Ý/ÿ/Þ/þ) elle yazmayın; STB 1.0 dönüşümünü araç otomatik yapar.

3) images_to_translate içindeki görselleri Türkçeleştirip aynı klasör yapısıyla images_edited içine kaydedin.

4) 02_yamayi_olustur.bat üzerine orijinal romfs.zip dosyanızı sürükleyin.
   Alternatif:
     python naa_localizer.py build romfs.zip translations_tr.tsv --out patch_romfs --images images_edited

5) Çıktı patch_romfs/ altında oluşur. Metin dosyalarının yanında şunlar da otomatik oluşur:
     patch_romfs/fonts/chelseyFont.bcfna
     patch_romfs/fonts/dfhsGothic.bcfna
     patch_romfs/_turkish_font_patch.txt

6) Luma3DS LayeredFS kullanıyorsanız patch_romfs içeriğini genel olarak:
     SD:/luma/titles/<OYUN_TITLE_ID>/romfs/
   altına yerleştirin. Title ID bölge/sürüme göre değişebilir; kit otomatik tahmin etmez.

7) Oyunun dilini İNGİLİZCE seçin. Yama *-en.stb dosyalarını Türkçe içerikle değiştirir.

FONT KONTROL / YALNIZ FONT YAMASI
---------------------------------
Fontları analiz et:
  python font_tool.py analyze romfs.zip --out TURKISH_FONT_REPORT.txt

Yalnız font yaması üret:
  python font_tool.py patch romfs.zip --out font_patch_romfs

Ana build'de font yamasını istemiyorsanız:
  python naa_localizer.py build romfs.zip translations_tr.tsv --out patch_romfs --no-turkish-fonts

STB 1.0 MODLARI
---------------
Varsayılan ve önerilen:
  --v100-mode fontmap
  Gerçek Türkçe karakter için alias baytlarını + CFNA CMAP yamasını birlikte kullanır.

Alternatif:
  --v100-mode transliterate
  Ğ/ğ/İ/ı/Ş/ş -> G/g/I/i/S/s şeklinde sadeleştirir. Font yaması olmadan da çalışır, ama gerçek Türkçe değildir.

  --v100-mode strict
  Kodlanamayan karakter görünce build'i durdurur.

  --v100-mode utf8
  STB 1.0'a deneysel UTF-8 yazar. Oyunun okuyucusunun bunu kabul edeceği garanti edilmez.

DİĞER KOMUTLAR
--------------
STB'leri kontrol et:
  python naa_localizer.py verify romfs.zip

Arşivden yeni çok-dilli boş Türkçe TSV'si üret:
  python naa_localizer.py extract romfs.zip --tsv translations_tr.YENI.tsv
  Bu komut diğer resmi dil sütunlarını da otomatik doldurur.

Dil dosyalarını/görselleri de yeniden paketle:
  python naa_localizer.py extract romfs.zip --tsv translations_tr.YENI.tsv --assets .

Tüm satırlar dolu değilse build'i durdur:
  python naa_localizer.py build romfs.zip translations_tr.tsv --out patch_romfs --require-complete

Kontrol etiketleri değiştiğinde build'i durdur:
  python naa_localizer.py build romfs.zip translations_tr.tsv --out patch_romfs --strict-tags

ESHOP FONT NOTU
---------------
fonts/eshop.bcfna yalnızca 59 karakterlik küçük, fiyat/para odaklı özel bir karakter kümesine sahip ve Türkçe
harf glifleri içermiyor. Kit bu dosyayı zorla değiştirmiyor; ana metin fontları olan chelseyFont ve dfhsGothic
yamalanıyor. Cihaz testinde özellikle eShop/fiyat ekranında Türkçe harf isteyen farklı bir metin yolu tespit
edilirse, eshop atlasına yeni glif çizip yeniden paketleyen ayrı bir genişletme gerekir.

BITMAP FONT NOTU
----------------
RomFS'te 8x8font/titlefont adlı eski Euro bitmap şeritleri de var. Bunlar referans olarak font_reference altında
korundu. Türkçe metin için doğrulanan Unicode CMAP'li ana yol CFNA fontlarıdır. Cihaz üzerinde belirli eski bir
ekranın bu bitmap şeritlerinden metin çizdiği görülürse o ekran ayrıca ele alınmalıdır.

GÖRSEL NOTU
-----------
images_to_translate içinde İngilizce yazı bulunan ekran görüntüleri/görseller vardır. Font yaması bu görsellerin
içine gömülü İngilizce yazıyı değiştirmez; bunları ayrıca düzenlemek gerekir.

TEST / YEDEK
------------
Araç tarafında doğrulananlar:
- İki ana BCFNA fontunda 12/12 Türkçe Unicode glifi mevcut.
- Legacy alias CMAP yaması dosya boyutunu değiştirmeden yeniden okunup doğrulanıyor.
- STB 1.0 testinde "ÇĞİÖŞÜ çğıöşü" girdisi beklenen alias baytlarına dönüştürülüyor.
- Tam build 45 metin dosyası + 2 Türkçe font dosyası oluşturabiliyor.

Son doğrulama gerçek 3DS/uygulama üzerinde yapılmalıdır. Orijinal RomFS/oyun dump'ınızın yedeğini saklayın.


ÇOK DİLLİ TABLO DÜZELTMESİ
---------------------------
Bu sürümde önceki pakette boş bırakılmış diğer dil referans sütunları gerçek RomFS STB içerikleriyle dolduruldu.
Ayrıca Rusça STB 1.1 dosyalarının UTF-16LE kodlaması desteklenir. Yama üretimi yine source_en + tr sütunlarını
kullanır; diğer dil sütunları yalnızca çeviri bağlamı içindir ve build sırasında oyuna yazılmaz.
