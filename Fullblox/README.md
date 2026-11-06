# Fullblox Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000163200/` → `sd:/luma/titles/0004000000163200/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/fullblox_tr.csv`.

Araç girişi: `araclar/fullblox_tool.py`. Komutları oyun klasöründe çalıştırın.

CSV kontrol etiketlerini koruyun. Kurulum için yalnız kökteki Title ID ağacı gerekir.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
