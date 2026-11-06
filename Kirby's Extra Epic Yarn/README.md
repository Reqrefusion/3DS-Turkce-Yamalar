# Kirby's Extra Epic Yarn Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001D1F00/` → `sd:/luma/titles/00040000001D1F00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/Kirby_TR_translated.csv`.

Araç girişi: `araclar/main.py`. Komutları oyun klasöründe çalıştırın.

Kontrol: python araclar/main.py validate. Üretim ve font kontrolü için kendi temiz oyun girdiniz gerekir; araclar/ktl yardımcı pakettir.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
