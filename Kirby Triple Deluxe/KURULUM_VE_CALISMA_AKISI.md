# Kirby Triple Deluxe Türkçe v12 — kurulum ve çalışma akışı

## Hazır yamayı kullanma
`01_HAZIR_YAMA/SD_ROOT` içindeki `luma` klasörünü 3DS SD kartının köküne birleştirin. Yama `luma/titles/000400000010C000/romfs/` altındadır.

## v12'de `ı` nasıl düzeltildi?
v10'daki `ı`, küçük `i` bitmapinin üstünü temizleyerek üretiliyordu. Outline/anti-alias satırları yüzünden bazı cihaz ekranlarında üstte çok küçük bir kalıntı görülebiliyordu.

v12'de küçük `i` artık piksel kaynağı değildir. `ı` şu şekilde üretilir:

1. Fontun kendi büyük `I` glifi alınır. Bu glifte nokta yoktur.
2. Normal noktasız küçük harflerden gerçek/dolu **strong x-height** hesaplanır.
3. Büyük `I` glifinin strong x-height üstündeki bütün pikselleri tamamen saydam yapılır.
4. Genişlik/advance bilgisi küçük `i`den alınır.
5. CMAP eşlemesi runtime-safe method-2 tablo içinde korunur.

`CommonStd_OL` zaten Nintendo'nun orijinal `ÇĞİÖŞÜçğıöşü` gliflerinin tamamını içerir. v12 bu fontun orijinal `ı` bitmapini geri yükler ve değiştirmez.

## Görsel kontrol
`06_FONT_ONIZLEMELERI/V12_I_i_dotless_kontrol` altında her normal metin fontu için `I`, `i`, `ı` yan yana PNG bulunur. Üçüncü glif `ı`dır; üstünde nokta bulunmamalıdır.

## Çeviriyi değiştirme
`02_CEVIRI/MSBT_CSV` altındaki 23 CSV'nin `TR_Turkish` sütunlarını düzenleyin. `⟦MSBT:...⟧` ve `⟦U16:...⟧` kontrol belirteçlerini koruyun. Sonra `01_YAMAYI_YENIDEN_OLUSTUR.bat` çalıştırın.

## Fontları temiz kaynaktan yeniden üretme
`04_ARA_DOSYALAR/FONT_ORIJINAL` altında 18 temiz kaynak font bulunur. `06_FONTLARI_SIFIRDAN_TR_PATCHLE.bat` bunları `kirby_font_tr_patch.py` ile yeniden patch'ler ve sonucu `BUILD_OUTPUT/FONT_TR_V12` altında verir.

Bu yeniden üretim yolu test edildi: 18/18 çıktı hazır v12 fontlarıyla bayt-bayt aynıdır.

## Doğrulama
`02_PAKETI_DOGRULA.bat` şunları denetler:
- 23 CSV / 23 MSBT / 1.847 kayıt eşleşmesi,
- bozuk MSBT kontrol tokenı olmaması,
- 10 normal metin fontunda 12 Türkçe karakterin parser ve runtime CMAP erişimi,
- `ı` ile `i` bitmaplerinin farklı olması,
- üretilmiş `ı` için strong x-height üstündeki alpha değerinin kesin olarak 0 olması,
- native Türkçe glifli fontun korunması,
- donor-enjekte fontlarda `ı` bitmapinin büyük `I` tabanlı v12 geometrisiyle eşleşmesi.

Ayrıntılı rapor: `05_RAPORLAR/V12_DOTLESS_I_STRICT_QA.csv`.
