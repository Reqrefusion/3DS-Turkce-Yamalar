# Face Raiders Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004001000022D00/` → `sd:/luma/titles/0004001000022D00/`
- `0004001020022D00/` → `sd:/luma/titles/0004001020022D00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/StgFace_all_languages_TR.csv`.

Araç girişi: `araclar/build_working_universal.py`. Komutları oyun klasöründe çalıştırın.

İki Title ID hedefi vardır; cihazınızdaki başlık kimliğiyle eşleşeni kullanın. Temiz CXI/ZIP girdisiyle üretim ve verify_prebuilt.py ile doğrulama yapılır.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_FULL_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
