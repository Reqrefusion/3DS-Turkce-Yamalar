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
tools/        MSBT ve arşiv araçları
README_TR.txt Kurulum ve doğrulama bilgileri
CHECKSUMS.txt Önemli dosyaların SHA-256 değerleri

ÇEVİRİ DURUMU
-------------
- 1227 MSBT etiketi denetlendi.
- Kaynakta metin bulunan 1092/1092 girdinin Türkçesi dolu ve REVIEWED olarak işaretli.
- 135 kaynakta boş olan sistem girdisi bilinçli olarak boş bırakıldı.
- MSBT kontrol etiketi uyuşmazlığı: 0
- UTF-16 kodlama hatası: 0
- İngilizce, Almanca, İspanyolca, Fransızca ve İtalyanca sütunları karşılaştırmalı kaynak olarak kullanıldı.
- Özel adlar, Nintendo karakter/adları ve jenerik isimleri korunmuştur.

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
CSV'deki piksel ölçümü alanları önceki bir denetimden kalmadır; 8 kayıt REVIEW,
4 kayıt RISK olarak işaretlidir. Bu klasörde font dosyası ve diğer Avrupa dili
MSBT'leri bulunmadığı için son metin değişikliklerinin piksel genişliği yeniden
hesaplanamamıştır. Bu satırlar gerçek fontla veya cihaz/emülatör görünümüyle
ayrıca kontrol edilmelidir.

DOĞRULAMA
---------
MSBT, dahil edilen şablon ile CSV'den yeniden üretildi. Luma kurulum kopyası ve
CSV, 1227/1227 etikette birebir eşleşiyor. Araç denetiminde boş hedef, kontrol
etiketi veya UTF-16 kodlama hatası yok. Kurulum klasöründeki iki LZ arşivi mevcut
kaynak dosyalardan kopyalanmış ve checksum listesiyle eşleşiyor.

Tam arşiv karşılaştırması için verify_patch.py özgün oyun ROM arşivini ister;
bu klasörde özgün ROM arşivi bulunmadığından o karşılaştırma yeniden çalıştırılamadı.

ÖNEMLİ SINIR
------------
Statik/binary doğrulamalar geçmiştir; ancak burada gerçek bir 3DS üzerinde baştan
sona tam oyun playtest'i yapılamamıştır. Bu nedenle nadir bir ekranın gerçek UI
kutu sınırı veya yalnız çalışma zamanında görülebilen bir davranış için yüzde 100
cihaz garantisi verilemez. Böyle bir taşma görülürse translation/pullblox_tr.csv
ve tools/pullblox_tool.py ile ilgili satır güvenli biçimde düzenlenip yeniden
enjekte edilebilir.
