# Rhythm Paradise Megamix Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `000400000018A500/` → `sd:/luma/titles/000400000018A500/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/proje/project/EUENmessage/pajama_sarc/arc/`.

Araç girişi: `araclar/rhm_tr_text_tool.py`. Komutları oyun klasöründe çalıştırın.

TSV tablolarının Turkish alanlarını düzenleyin; TAG/END/PUA kodlarını koruyun. Hazır mesaj üretim girdileri ceviri/proje/source altındadır. Ana üretim aracı araclar/build_v22.py dosyasıdır.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
