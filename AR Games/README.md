# AR Games Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004001000022E00/` → `sd:/luma/titles/0004001000022E00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/AR_Games_TR_multilang_translation.csv`.

Araç girişi: `araclar/ar_games_tr_tool.py`. Komutları oyun klasöründe çalıştırın.

EU_English dil yuvası kullanılır. CSV içindeki kontrol etiketlerini koruyun. Temiz RomFS ile validate ve patch alt komutlarını kullanın.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `calisma/`: Ara çıktılar ve çalışma kopyaları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/AR_Games_TR_README.md)
- [Kullanım ve teknik notlar 2](belgeler/README_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
