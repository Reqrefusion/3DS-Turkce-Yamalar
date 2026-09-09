# Face Raiders Türkçe Yama — Tam Geliştirici Paketi

Bu arşiv, cihazda çalıştığı doğrulanan Face Raiders Türkçe LayeredFS v2 yamasını; çeviri verilerini, orijinal StgFace MSBT şablonlarını, CSV exporter/enjektör kodunu, yeniden oluşturma aracını ve doğrulama raporlarını birlikte içerir.

## En hızlı kurulum

Sadece yamayı kullanmak istiyorsan:

1. `00_SD_ROOT_READY` klasörünün içeriğini SD kartın köküne kopyala.
2. Sonuç `SD:/luma/titles/...` şeklinde olmalı.
3. Luma3DS ayarlarında `Enable game patching` açık olmalı.
4. Konsolu yeniden başlat ve Face Raiders'ı aç.

Aynı çalışan yamanın yalnızca SD-kökü ZIP'i ayrıca:
`05_PREBUILT/FaceRaiders_TR_SDROOT_ONLY_WORKING.zip`

## Paket yapısı

- `00_SD_ROOT_READY/` — Cihazda çalıştığı doğrulanan hazır LayeredFS yaması.
- `01_TRANSLATION/` — 13 resmî dil yan yana + Türkçe sütunlu CSV, ham export ve Python çeviri haritası.
- `02_TOOLS/` — MSBT/CXI parser, CSV exporter, validator, injector ve universal patch builder.
- `03_SOURCE_MSBT_ORIGINAL/` — Kullanıcının dump'ından çıkarılmış 13 orijinal StgFace dil MSBT'si.
- `04_DOCS/` — Çeviri/fit raporu, teknik notlar ve geliştirme açıklamaları.
- `05_PREBUILT/` — Kuruluma hazır yalnızca-yama ZIP'i.
- `SHA256SUMS.txt` — Paket içindeki dosyaların SHA-256 değerleri.

## Çeviri verisi

`01_TRANSLATION/StgFace_all_languages_TR.csv`:

- 427 hizalanmış MSBT kaydı
- 13 resmî dil sütunu
- 244 dolu Türkçe metin
- satır/uzunluk tahmini
- placeholder kontrolü
- Nintendo PUA/düğme glifi kontrolü
- özel çeviri notları

Fit sonucu: 242 `OK`, 2 `REVIEW` (`Evet` / `Hayır`).

## Çalışan yamayı yeniden üretme

Kendi decrypted Face Raiders CXI dosyanı veya CXI içeren ZIP'i kullan:

```bash
cd 02_TOOLS
python build_working_universal.py /yol/faceraiders.zip ../01_TRANSLATION/StgFace_all_languages_TR.csv ../BUILD_OUT
```

Çıktı:

- `BUILD_OUT/luma/titles/0004001000022D00/...` — EUR Old 3DS
- `BUILD_OUT/luma/titles/0004001020022D00/...` — EUR New 3DS

Script, cihazda çalışan v2 ile aynı yöntemi kullanır: EU English MSBT Türkçeleştirilir ve oyunun 13 StgFace dil dosyası adına kopyalanır. Böylece konsol hangi dil yolunu seçerse seçsin Türkçe yüklenir.

## Mevcut yamayı doğrulama

```bash
cd 02_TOOLS
python verify_prebuilt.py ../01_TRANSLATION/StgFace_all_languages_TR.csv ../00_SD_ROOT_READY
```

Beklenen sonuç:

`OK: 26 MSBT dosyasının Türkçe metinleri CSV ile birebir eşleşiyor.`

26 = 13 dil adı x 2 EUR Title ID.

## Çok-dilli CSV'yi dump'tan yeniden çıkarma

```bash
cd 02_TOOLS
python faceraiders_localizer.py export /yol/faceraiders.zip yeni_export.csv
```

CSV'yi kontrol et:

```bash
python faceraiders_localizer.py validate ../01_TRANSLATION/StgFace_all_languages_TR.csv
```

Tek bir dil yuvasına inject etmek istersen:

```bash
python faceraiders_localizer.py inject /yol/faceraiders.zip ../01_TRANSLATION/StgFace_all_languages_TR.csv ../SINGLE_OUT --base-language EU_English
```

Tam çalışan universal sürüm için `build_working_universal.py` tercih edilir.

## Araç gereksinimleri

- Python 3.10+ önerilir.
- Harici Python paketi gerekmez; standard library yeterlidir.
- `faceraiders_localizer.py` decrypted NCCH/CXI içindeki RomFS'i doğrudan okuyabilir.
- Şifreli CXI'yi decrypt etmez; dump'ın okunabilir/decrypted olması gerekir.
- Cihaz tarafında Luma3DS LayeredFS / game patching gerekir.

## Önemli

Bu pakete tam CXI/ROM dump'ı eklenmemiştir. Yeniden export/build yapmak için kendi dump'ını kullan. Geliştirme/referans amacıyla yalnızca StgFace mesaj şablonları `03_SOURCE_MSBT_ORIGINAL` altında yer alır.
