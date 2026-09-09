# Araçlar

## `faceraiders_localizer.py`
Ana parser/exporter/enjektör.

Yetenekleri:
- decrypted CXI/NCCH + RomFS okuma
- ZIP içindeki CXI'leri tarama
- MSBT `LBL1` / `TXT2` okuma
- 13 dili yan yana CSV'ye çıkarma
- `%d`, `%ls` vb. placeholder doğrulaması
- Nintendo private-use düğme gliflerini doğrulama
- yaklaşık satır genişliği/fit analizi
- Türkçe sütununu MSBT'ye inject etme

## `build_working_universal.py`
Cihazda çalışan v2 paketinin yeniden üretilebilir builder'ı.
EU English şablonundan tek Türkçe MSBT üretir, 13 dil adı ve iki EUR Title ID altında yazar.

## `verify_prebuilt.py`
LayeredFS içindeki bütün MSBT'leri açar ve Türkçe metinlerin CSV ile birebir aynı olduğunu doğrular.

## `build_translation_csv_internal.py`
İlk çeviri CSV'sini üretirken kullanılan oturum-içi yardımcı scriptin kopyasıdır. Hard-coded çalışma yolları içerir; günlük kullanım için değil, geliştirme geçmişini/iş akışını göstermek için bırakılmıştır.

## `requirements.txt`
Harici paket gerekmediğini belirtir.
