# Pocket Card Jockey Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000194900/` → `sd:/luma/titles/0004000000194900/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/mesaj_projesi/messages_latin.csv`.

Araç girişi: `araclar/pcj_tr_tool.py`. Komutları oyun klasöründe çalıştırın.

translation alanını düzenleyin, uygulanacak satırda apply alanını etkinleştirin. Aynı klasördeki extracted ağacını ve message_manifest.json dosyasını koruyun.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/kullanim_notlari.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
