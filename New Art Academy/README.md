# New Art Academy Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000084F00/` → `sd:/luma/titles/0004000000084F00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/translations_tr.tsv`.

Araç girişi: `araclar/proje/naa_localizer.py`. Komutları oyun klasöründe çalıştırın.

İngilizce -en.stb dil dosyaları hedeflenir. Düzenleyici araclar/proje/translator_gui.py dosyasıdır. Çeviri, resim ve font girdileri birlikte korunmalıdır; kaynak arşivi kaynaklar/arsiv altındadır.

## Klasörler

- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.
- `calisma/`: Ara çıktılar ve çalışma kopyaları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/00_OKU_BENI_KURULUM_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
