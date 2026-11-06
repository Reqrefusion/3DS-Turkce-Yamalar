# WarioWare Gold Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001D1C00/` → `sd:/luma/titles/00040000001D1C00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/`.

Araç girişi: `araclar/msbt_batch_inject.py`. Komutları oyun klasöründe çalıştırın.

Karşılaştırmalı CSV dosyalarında Türkçe hedef alanını düzenleyin. Temiz mesaj/font girdileri kaynaklar altındadır. Denetim: python araclar/verify_package.py.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
