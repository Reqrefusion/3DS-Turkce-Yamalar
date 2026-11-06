# Pullblox Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000068F00/` → `sd:/luma/titles/0004000000068F00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/pullblox_tr.csv`.

Araç girişi: `araclar/pullblox_tool.py`. Komutları oyun klasöründe çalıştırın.

İngilizce mesaj yuvası hedeflenir. calisma/kurulum_kopyasi yalnız yardımcı çıktı kopyasıdır; kurulumda kökteki Title ID ağacını kullanın.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.
- `calisma/`: Ara çıktılar ve çalışma kopyaları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
