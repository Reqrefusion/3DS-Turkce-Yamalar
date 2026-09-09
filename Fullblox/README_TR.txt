FULLBLOX TÜRKÇE YAMA

Oyun / Title ID
----------------
Fullblox
0004000000163200

Kurulum (Luma3DS LayeredFS)
---------------------------
1. ZIP içindeki "luma" klasörünü SD kartın kök dizinine kopyalayın.
2. Sonuçta şu klasör bulunmalıdır:
   /luma/titles/0004000000163200/romfs/
3. Luma3DS yapılandırmasında "Enable game patching" açık olmalıdır.
4. Yama İngilizce (EURen) dil yuvasını Türkçe ile değiştirir. Oyunu İngilizce dil yuvasıyla çalıştırın.

Yamaya dahil dosyalar
---------------------
- 13 Türkçe MSBT metin dosyası
- Guide_D.lz: MAP -> HARİTA görseli
- Play_U.lz: START -> BAŞLA, CLEAR -> TAMAM görselleri
- Rslt_Base_U.lz: Congratulations -> TEBRİKLER görseli
- translation/fullblox_tr.csv: İngilizce, Almanca, İspanyolca, Fransızca, İtalyanca ve Türkçe yan yana
- tools/: MSBT, FFNT, BFLIM, SARC ve LZ11 çalışma araçları
- reports/: metin / asset / yeniden üretim doğrulama raporları

Çeviri ve teknik notlar
-----------------------
- 1804/1804 gerçek kaynak metin Türkçedir.
- Kontrol kodu uyuşmazlığı: 0
- UTF-16 kodlama hatası: 0
- Eksik Türkçe glif: 0
- İngilizcesi 1-2 satır olup Türkçede 3+ satıra çıkan metin: 0
- İki satırlık kutu taşması: 0
- Tuş ikonuna Türkçe ek yapıştırma / beyaz-siyah render çakışması riski: 0
- Fullblox'un kendi FFNT font metrikleri kullanılmıştır.

Bilinçli tek satır fit istisnaları: Evet, Hayır, Açık, Kapalı, Baykuş ve Köpekbalığı.
Bunlar iki/üç satır taşması değildir; yalnızca resmi dillerdeki en uzun tek satırlık karşılığa göre temkinli piksel karşılaştırmasıdır. Doğal Türkçeyi bozmamak için kısaltılmamıştır.

Tuş komutları
--------------
Fullblox düğme ikonlarını MSBT kontrol kodlarıyla çizer. Türkçe ek, ikonun üstüne bindirilmez. Gereken yerlerde "A tuşuna bas", "B tuşunu basılı tut" türü yapı kullanılır. Böylece Fallblox testinde görülen ikon / apostrof / outline çakışması önlenir.

Görsel asset doğrulaması
------------------------
Fullblox BFLIM/SARC kullanır. START, CLEAR ve MAP grafikleri ETC1A4 olarak korunur.
Sonuç ekranındaki TEBRİKLER grafiği için resmî EURes sonuç şeması kullanılır:
ETC1A4 font + ayrı A4 parlaklık maskesi. EURes ve EURen sonuç layout/animasyonları
aynıdır; fark yalnız yerelleştirilmiş texture adlarıdır. Türkçe sonuç grafiği bu resmî
şemada yeniden üretilir.

Fullblox logosu ve "Fullblox Land" gibi beş resmi dilde de aynı bırakılan özel adlar bilinçli olarak çevrilmemiştir.

Doğrulama
---------
Patch 16 oyun dosyası temiz bir klasörde ikinci kez sıfırdan üretildi. reports/reproducibility.json içinde tüm dosyalarda repro_match=true ve all_match=true olmalıdır.

Not
---
Bu yama ROM / CIA içermez; yalnız LayeredFS üzerinde değiştirilen dosyaları içerir. Kayıt verinizi değiştirmez. Yine de cihaz üzerinde mod/yama kullanmadan önce kayıt yedeği almak iyi bir uygulamadır.

RENKLI METİN / TÜRKÇE FONT DÜZELTMESİ
------------------------------------
Fullblox iki font kaynağı kullanır. Normal metindeki Kurokane fontu Türkçe
karakterleri içerirken, renkli/vurgulu metinde kullanılan Outline fontunun
orijinal karakter haritasında ğ/Ğ, ı/İ ve ş/Ş bulunmaz.

Bu pakette romfs/font/Outline.lz dosyası da yamalanır. Orijinal Outline font
atlasındaki Avrupa sürümünde kullanılmayan altı mevcut Japonca glif yuvası
Ğ/ğ/İ/ı/Ş/ş için yeniden kullanılır. Font dosyası yeni glif indeksiyle büyütülmez;
orijinal 0-334 glif aralığı ve blok yapısı korunur.

Ek QC notu:
- Renkli metindeki Türkçe Outline glifleri mevcut FFNT yuvaları içinde tutulur.
- Küçük ı, küçük i'nin noktası kaldırılmış gerçek küçük-harf gövdesidir; büyük İ ise büyük I + ayrı nokta kullanır.
- Çok satırlı Türkçe metinlerde tolerans kullanılmaz: hiçbir satır aynı mesajdaki resmi dillerin en geniş satırını aşamaz.
