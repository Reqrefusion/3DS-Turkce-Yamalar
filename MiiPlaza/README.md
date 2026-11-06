# MiiPlaza Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004001000022800/` → `sd:/luma/titles/0004001000022800/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/mii_plaza_base_turkish.csv` ve `ceviri/mii_update_turkish.csv`.

Araç girişi: `araclar/mii_plaza_tr_tool.py`. Komutları oyun klasöründe çalıştırın.

Temel içerik ve güncelleme çevirileri ayrıdır. Güncelleme işlemleri araclar/mii_plaza_update_tr_tool.py ile yapılır.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/KURULUM.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.


[Kullanım açıklaması](belgeler/ARACLAR.txt)
