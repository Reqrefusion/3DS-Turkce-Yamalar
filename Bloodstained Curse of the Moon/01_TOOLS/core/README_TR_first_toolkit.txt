BLOODSTAINED: CURSE OF THE MOON (Nintendo 3DS) - TÜRKÇE ÇEVİRİ KİTİ
====================================================================

Hazırlanan oyun sürümü
----------------------
Kaynak arşivde bulunan CXI:
  00040000001D3C00.00000000 Bloodstained Curse of the Moon (CTR-N-BLMP) (E).cxi

Buna göre bu paket AVRUPA sürümü / TitleID 00040000001D3C00 içindir.
Başka bölge sürümünde dosya yapısı veya metin indeksleri farklı olabilir.

Bu pakette ne hazırlandı?
-------------------------
1) TTB metin formatı çözüldü ve yeniden paketleyen araç hazırlandı.
2) Oyundaki 14 adet TTB dosyasından toplam 4922 kayıt çıkarıldı.
3) İlk oynanabilir Türkçe sürümde 10 TTB dosyasında 130 İngilizce metin çevrildi.
4) <emoji/...> gibi oyun kontrol kodları korunuyor ve araç bunları kontrol ediyor.
5) Metin uzunluğu değişebilir; araç bütün metin ofsetlerini yeniden hesaplıyor.
6) BMPFont.bfbctr içinde Türkçe için gereken şu Unicode karakterleri bulundu:
   ç ğ ı İ ö ş ü Ç Ğ Ö Ş Ü
   Bu yüzden ilk aşamada ayrı bir font yaması gerekmiyor gibi görünüyor.
7) İngilizceye özel 8 OSBCTR grafik atlası PNG olarak çıkarıldı.
8) Araç, düzenlenmiş aynı boyuttaki PNG'yi RGBA4444 + 3DS swizzle ile tekrar OSBCTR'ye
   koyabiliyor. Testte değişiklik yapılmayan atlas birebir aynı OSBCTR dosyasına döndü.

İlk Türkçe yamada çevrilen ana alanlar
--------------------------------------
- Açılış / ilk kurulum / otomatik kayıt uyarıları
- Evet / Hayır
- Boss Rush menüsü
- Game Over menüsü
- Options / tuş ayarları
- Pause menüsü
- Bölüm isimleri ve bölüm numaraları
- Zamanı geri alma açıklamaları
- Sonuç ekranındaki İngilizce etiketler
- Kayıt dosyası kopyalama / silme / üzerine yazma menüleri
- Oyun stili açıklamaları
- Title menüsü

Henüz tamamlanmayan bölüm
-------------------------
Oyunda bazı İngilizce sunum/öykü/eğitim metinleri normal TTB yazısı değil,
*_en.osbctr kaynaklarının içindeki karakter/sprite atlasları ve bunları yerleştiren
nesne/animasyon verileriyle oluşturuluyor. Şu dosyaların atlasları çıkarıldı:
  DemoText00_en.osbctr
  DemoText01_en.osbctr
  DemoText02_en.osbctr
  EndingText00_en.osbctr
  GraphicText02_en.osbctr
  LogoInti_en.osbctr
  Openingext00_en.osbctr
  TutorialText00_en.osbctr

PNG'ler osb_atlases_en klasöründe. LogoInti çeviri gerektirmiyor. Diğerlerinde tam
Türkçe cümle oluşturmak için yalnızca resmi değiştirmek yeterli olmayabilir; sprite
yerleşim/animasyon verisinin de eşlenmesi gerekir. Bu nedenle ilk yama esas olarak
oyunun TTB tabanlı arayüz ve sistem metinlerini kapsıyor.

Item.ttb notu
-------------
Item.ttb tek başına 4068 kayıt içeriyor ve içinde Bloodstained ile ilgisiz görünen,
birden fazla dilde ortak motor/başka oyun kalıntıları bulunuyor. Yanlış veya kullanılmayan
metinleri gereksiz yere değiştirmemek için ilk yamada bunlara dokunulmadı.
MapCommon.ttb içinde de benzer ortak-motor metinleri var. StaffRoll krediler, StageSelect
ise boş metinlerden oluşuyor.

Luma3DS LayeredFS ile kurulum
-----------------------------
Hazır yamanın klasörü:
  LayeredFS/luma/titles/00040000001D3C00/romfs/

1. 3DS SD kartınızın köküne LayeredFS klasöründeki "luma" klasörünü kopyalayın/ birleştirin.
   Sonuç örneği:
   SD:/luma/titles/00040000001D3C00/romfs/Title.ttb
2. Konsolu açarken SELECT tuşuna basılı tutup Luma3DS ayarına girin.
3. "Enable game patching" seçeneğini açık yapın.
4. Bloodstained: Curse of the Moon Avrupa sürümünü başlatın.

İlk testte özellikle şunlara bakın:
- Title menüsünde "Onayla", "Oyun ayarlarını değiştir" gibi Türkçe yazılar çıkıyor mu?
- ç, ğ, ı, İ, ö, ş, ü karakterleri doğru görünüyor mu?
- Uzun metinlerde taşma/kırpılma var mı?
- Save / Game Over / Pause ekranları normal çalışıyor mu?

Çeviriyi düzenleme
------------------
translations_firstpass_tr.csv:
  İlk Türkçe çeviriler doldurulmuştur. "translation_tr" sütununu düzenleyebilirsiniz.

translations_all_template.csv:
  Bütün 4922 TTB kaydını içerir; translation_tr sütunu boştur.

CSV dosyaları UTF-8 BOM ile kaydedildi. Excel/LibreOffice/Notepad++ ile düzenlenebilir.
Metinlerde satır sonları hücre içinde gerçek satır sonu olarak tutulur.

ÇOK ÖNEMLİ:
- <emoji/Decide>, <emoji/Cancel>, <emoji/Start>, <emoji/BtnY> gibi etiketleri silmeyin.
- Varsa %s, %d gibi biçim belirteçlerini değiştirmeyin.
- Metne NUL (\0) karakteri koymayın.
- Orijinal sütununu değiştirmeyin; araç yanlış oyun sürümüne yama uygulanmasını önlemek
  için orijinal metni kontrol eder.

Araç kullanımı
--------------
Python 3 gereklidir. OSB PNG komutları için Pillow gereklidir.

Bütün TTB metinlerini çıkar:
  python bloodstained_tr_tool.py extract-text ROMFS_KLASORU translations.csv

Çeviri CSV'sinden sadece değişen TTB dosyalarını üret:
  python bloodstained_tr_tool.py build ROMFS_KLASORU translations_firstpass_tr.csv CIKTI_ROMFS

TTB yapısını doğrula:
  python bloodstained_tr_tool.py verify-text ROMFS_KLASORU

İngilizce OSBCTR atlaslarını PNG'ye çıkar:
  python bloodstained_tr_tool.py extract-osb ROMFS_KLASORU osb_png

Düzenlenen PNG'yi tekrar bir OSBCTR dosyasına koy:
  python bloodstained_tr_tool.py inject-osb ORIJINAL.osbctr DUZENLENMIS.png YENI.osbctr

OSB görüntü dönüşümünü doğrula:
  python bloodstained_tr_tool.py verify-osb ROMFS_KLASORU

Fontta Türkçe kod noktalarını kontrol et:
  python bloodstained_tr_tool.py font-check ROMFS_KLASORU/BMPFont.bfbctr

Not: inject-osb komutunda PNG'nin genişlik/yüksekliği orijinal atlasla aynı kalmalıdır.

Dosya özeti
-----------
- LayeredFS/                       Hazır ilk Türkçe yama
- translations_firstpass_tr.csv   İlk 130 Türkçe metin + tüm TTB kayıtları
- translations_all_template.csv   Boş tam çeviri şablonu
- bloodstained_tr_tool.py          Çıkarma / yeniden paketleme aracı
- osb_atlases_en/                  İngilizce OSBCTR atlaslarının PNG çıktıları
- TRANSLATION_STATUS.txt           Teknik durum ve dosya sayıları

Bu ilk sürümde metin çevirileri anlam ve ekrana sığma açısından oyun içinde test edilmemiştir.
Ekran görüntüsü alınarak satır taşmaları ve bağlama uymayan terimler ikinci geçişte düzeltilmelidir.
