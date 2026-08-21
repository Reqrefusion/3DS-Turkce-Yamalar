# Brain Train 3DS Türkçe Yama Aracı

Bu araç bu arşivdeki Brain Train 3DS dosyaları için hazırlanmıştır. Python 3 ile çalışır; ek Python paketi gerekmez.

## Ne yapar?

- `msg` altındaki tüm dil klasörlerini tarar ve **her MSBT için tek CSV** üretir. Satırlar etiket/mesaj indeksine göre eşleştirilir; diller yan yana sütunlardır.
- İsterseniz mevcut Türkçe yamanızı `TR_Patch` sütunu olarak CSV'ye ekler.
- CSV'de düzenlediğiniz bir sütunu tekrar MSBT'ye enjekte eder; özgün `LBL1`, `ATR1` ve diğer bölümleri koruyup `TXT2` bölümünü yeniden kurar.
- Dosyanın sıkıştırma türünü otomatik algılar ve çıktıyı aynı türde tekrar sıkıştırır.
- BCFNT fontlarını denetler/onarıp rapor üretir.

## Bu oyun için doğrulanan formatlar

Arşivdeki MSBT ve BCFNT dosyaları Nintendo **LZ11 (`0x11`)** ile sıkıştırılmıştır. Araç ayrıca raw, LZ10 (`0x10`) ve Nintendo RLE (`0x30`) okuyup yazabilir.

MSBT'ler `MsgStdBn`, fontlar `CFNT/BCFNT` yapısındadır. Araç UTF-16 MSBT metinlerini destekler.

## Grafik arayüz

Windows'ta `BAŞLAT.bat` dosyasına çift tıklayın. Alternatif olarak:

```bat
python braintrain_tool.py
```

## 1) Tüm dilleri CSV'ye çıkarma

```bat
python braintrain_tool.py export ^
  --msg-root "...\Brain Train3ds\msg" ^
  --patch-root "...\Türkçe Patch\00040000000B3D00\romfs\msg\EU_English" ^
  --out "csv"
```

Her MSBT için örneğin `main.msbt.csv` oluşur. Sütun düzeni kabaca şöyledir:

`Key, ReferenceIndex, Label, EU_Dutch, EU_English, EU_French, EU_German, EU_Italian, EU_Spanish, US_English, US_French, US_Spanish, TR_Patch`

### Kontrol kodları

Bu oyundaki kontrol etiketlerinin hepsi aynı ikili uzunluk düzenini kullanmadığı için araç tahmin yapmaz. Normal metin okunabilir kalır; güvenli olmayan UTF-16 birimleri kayıpsız token olarak görünür:

- `[[U+000E]]` — MSBT kontrol başlangıcı gibi kontrol birimleri
- `[[U+0001]]` — kontrol kodunun grup/tür/parametre birimleri
- `[[U+E078]]` — private-use ikon/glif karakterleri
- `[[U+FF00]]` — özel sentinel/değerler

**`[[U+....]]` tokenlarını silmeyin veya değiştirmeyin.** Çeviri metnini bunların çevresinde değiştirebilirsiniz. Bu yöntem bu arşivdeki 110 MSBT / 83.250 metin girdisinde byte-for-byte export→import round-trip ile test edilmiştir.

## 2) CSV'yi MSBT'ye geri enjekte etme

Türkçe sütununu mevcut Türkçe patch MSBT'lerinin üstüne yazmak en güvenli yöntemdir:

```bat
python braintrain_tool.py inject ^
  --csv-dir "csv" ^
  --base-msg-dir "...\Türkçe Patch\00040000000B3D00\romfs\msg\EU_English" ^
  --out "yeni_msbt" ^
  --column TR_Patch
```

İsterseniz `EU_English` gibi başka bir sütunu da seçebilirsiniz. Araç ürettiği her MSBT'yi yeniden açarak temel yapısal doğrulama yapar.

## 3) Font onarma

İki mod vardır.

### `safe` — önerilen

Sadece sizin Türkçe yamanızda zaten değiştirilmiş olan fontları onarır. El yapımı Türkçe gliflerinize dokunmadan, aynı fontun 9 özgün dil sürümündeki eksik karakterleri birleştirir. Aynı fontun bazı dillerde hücre/sheet boyutu farklıysa glifi aynı oyun fontundan raster olarak ölçekleyerek ekler. Yamada değişmiş `FINF` varsayılan metrikleri özgün `EU_English` fontundan geri yüklenir.

```bat
python braintrain_tool.py repair-fonts ^
  --mode safe ^
  --msg-root "...\Brain Train3ds\msg" ^
  --patch-font-dir "...\Türkçe Patch\00040000000B3D00\romfs\msg\EU_English" ^
  --out "fixed_fonts_safe" ^
  --report "font_repair_report_safe.csv"
```

Bu arşivde `safe` mod 12 yamalı fontun tamamında Türkçe çekirdek karakterleri (`ÇĞİÖŞÜçğıöşü`) ve tüm dil varyantlarının karakter birleşimini doğruladı.

### `extended` — deneysel/tam set

Tüm fontları işler. Aynı isimli dil varyantlarını birleştirir, **haritalı olduğu halde raster hücresi boş olan glifleri** başka SPARTA fontlarından tamamlar ve Türkçe çekirdek eksikse yakın boyuttaki bir oyuniçi fonttan diakritik/glyph uyarlaması yapar.

```bat
python braintrain_tool.py repair-fonts ^
  --mode extended ^
  --msg-root "...\Brain Train3ds\msg" ^
  --patch-font-dir "...\Türkçe Patch\00040000000B3D00\romfs\msg\EU_English" ^
  --out "fixed_fonts_all" ^
  --report "font_repair_report_all.csv"
```

`extended` mod özellikle `SPARTA2` ve `SPARTA15` içindeki CMAP'te kayıtlı ama gerçekte boş olan çok sayıda Latin glifi de doldurur. Ancak `geometrical_pattern` ve bazı özel amaçlı SPARTA fontları normal metin fontu değildir; bu nedenle oyunda ilk tercih olarak `safe` paketi önerilir. `extended` çıktıyı emülatör/cihaz üzerinde ekran ekran test etmek daha doğrudur.

## 4) Font denetimi

```bat
python braintrain_tool.py audit-fonts ^
  --msg-root "...\Brain Train3ds\msg" ^
  --patch-font-dir "fixed_fonts_safe" ^
  --out "font_audit.csv"
```

Rapor; tüm dil varyantlarının birleşiminden eksikleri, haritalı fakat boş glifleri, Türkçe çekirdek eksiklerini ve `FINF` varsayılanlarının EU English ile eşleşip eşleşmediğini gösterir.

## Notlar

- CSV dosyaları UTF-8 BOM ile yazılır; Excel/LibreOffice Türkçe karakterleri düzgün açar.
- Çeviri sırasında `Key`, `ReferenceIndex` ve `Label` sütunlarını değiştirmeyin.
- Kontrol tokenlarını koruyun.
- Font çıktıları özgün dosyanın sıkıştırma türünü korur.
- Önce `safe` font setiyle test edin; yalnız gerçekten eksik kalan özel bir ekran/font varsa `extended` mod o fontu tamamlamak için kullanılabilir.
