PULLBLOX TÜRKÇE YAMA
====================

Bu paket, Avrupa Pullblox sürümü için hazırlanmıştır.
Title ID: 0004000000068F00
Yama İngilizce dil slotunu (EURen) Türkçeye çevirir.

KURULUM (Luma3DS LayeredFS)
---------------------------
1. SD kartta Luma3DS oyun yamalarının etkin olduğundan emin olun (Enable game patching).
2. Bu paketteki "luma" klasörünü SD kartın kök dizinine kopyalayın.
3. Sonuçta şu dosyalar bulunmalıdır:

   /luma/titles/0004000000068F00/romfs/EURen/msg/orca.msbt
   /luma/titles/0004000000068F00/romfs/EURen/lyt/Game_U.lz
   /luma/titles/0004000000068F00/romfs/EURen/lyt/Res_U.lz

4. Oyunun İngilizce dil kaynaklarını kullanmasını sağlayın. Avrupa sürümünde yama EURen slotunu değiştirir.
5. Oyunu başlatın.

KALDIRMA
--------
/luma/titles/0004000000068F00 klasörünü silin veya başka bir yere taşıyın.
Yama kayıt dosyanızı değiştirmez; yalnız LayeredFS ile RomFS dosyalarının yerine geçer.

PAKET İÇERİĞİ
--------------
luma/         Kurulabilir LayeredFS yaması
translation/  Beş resmî dil + Türkçe sütunlu CSV
previews/     Türkçeleştirilmiş bitmap yazıların önizlemeleri
reports/      Otomatik doğrulama ve yeniden üretilebilirlik raporları
tools/        MSBT/BCLIM/DARC/LZ11 çıkarma, enjekte etme ve doğrulama araçları
CHECKSUMS.txt Paket içindeki önemli dosyaların SHA-256 değerleri

ÇEVİRİ DURUMU
-------------
- 1227 MSBT etiketi kontrol edildi.
- Kaynakta metin bulunan 1092/1092 girdinin Türkçesi dolu ve REVIEWED olarak işaretli.
- 135 kaynak-boş/sistem girdisi bilinçli olarak boş bırakıldı.
- MSBT özel kontrol kodu uyuşmazlığı: 0
- UTF-16 kodlama hatası: 0
- Oyunun fontunda eksik Türkçe glif: 0
- İngilizce, Almanca, İspanyolca, Fransızca ve İtalyanca metinler karşılaştırmalı kaynak olarak kullanıldı.
- Özel adlar, Nintendo karakter/adları ve kredi isimleri çevrilmeden korunmuştur.

TERİM TUTARLILIĞI
-----------------
Papa Blox       -> Usta Blox
pullout switch  -> çekme düğmesi
manhole         -> geçit
inverted manhole-> ters geçit
reset switch    -> sıfırlama düğmesi
side pull       -> yandan çekiş
QR Code         -> QR Kodu / QR kodu (cümle bağlamına göre)

GÖRSEL YAZILAR
--------------
START!            -> BAŞLA!
CLEAR!            -> TAMAM!
Congratulations!  -> TEBRİKLER!

Değiştirilen BCLIM dosyalarında orijinal genişlik/yükseklik, format, texture veri
uzunluğu ve CLIM header/footer yapısı korunmuştur. DARC içindeki hedef olmayan
varlıklar byte-for-byte aynıdır. LZ11 paketleri açma testiyle doğrulanmıştır.

SIĞMA KONTROLÜ HAKKINDA
-----------------------
Oyun fontunun gerçek glif genişlikleriyle bütün Türkçe metinler yeniden ölçüldü.
Cihaz testinde bazı iki satırlık metinlerin otomatik sarılarak üçüncü satıra taştığı
görüldüğü için doğrulama daha sıkı hale getirildi.

- Resmî dil düzeni 2 satır olan metinlerde Türkçe 3. satıra çıkamaz.
- Bu 2-satır grubunda Türkçe en geniş satır, aynı mesajın resmî dillerindeki en
  geniş satırdan daha geniş olamaz.
- İngilizcesi 1-2 satır olan hiçbir metin Türkçede 3+ satıra çıkamaz.
- Son kontrolde two_line_overflow = 0 ve source_2line_to_3plus = 0.

Uzun tutorial/help metinlerinde satır kırımları piksel genişliğine göre yeniden
dengelendi; sığmayan cümleler anlamı ve kontrol/vurgu kodlarını koruyarak manuel
kısaltıldı. Kalan 8 REVIEW ve 4 RISK yalnız tek satırlık kredi/menü sözcükleridir
(Yönetmen, Kopyala, Yardım, Evet, Hayır, Açık, Kapalı vb.); bunlar 2->3 satır
taşması değildir ve doğal Türkçeyi bozacak yapay kısaltmalar yapılmamıştır.
Ayrıntı: reports/text_qc.json ve reports/translation_audit.json

DOĞRULAMA
---------
Final patch, boş bir klasörde aynı kaynak + aynı araçlar + aynı CSV ile yeniden
üretilmiştir. Üç patch dosyasının SHA-256 değerleri birebir eşleşmiştir.
Ayrıntı: reports/reproducibility.json ve reports/asset_qc.json

ÖNEMLİ SINIR
------------
Statik/binary doğrulamalar geçmiştir; ancak burada gerçek bir 3DS üzerinde baştan
sona tam oyun playtest'i yapılamamıştır. Bu nedenle nadir bir ekranın gerçek UI
kutu sınırı veya yalnız çalışma zamanında görülebilen bir davranış için yüzde 100
cihaz garantisi verilemez. Böyle bir taşma görülürse translation/pullblox_tr.csv
ve tools/pullblox_tool.py ile ilgili satır güvenli biçimde düzenlenip yeniden
enjekte edilebilir.
