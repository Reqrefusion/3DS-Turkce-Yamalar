# Mario Party - The Top 100 Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001C4D00/` → `sd:/luma/titles/00040000001C4D00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/mp100_translation_complete.csv`.

Araç girişi: `araclar/mp100_tool.py`. Komutları oyun klasöründe çalıştırın.

Metin tablosu ile grafik/font işlemleri ayrı tutulur. Üretim aracı araclar/build_full_patch.py dosyasıdır.

## Klasörler

- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
