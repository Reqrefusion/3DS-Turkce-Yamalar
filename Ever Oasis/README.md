# Ever Oasis Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001A4900/` → `sd:/luma/titles/00040000001A4900/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/main_tr.md`.

Araç girişi: `araclar/oasis_gmsg.py`. Komutları oyun klasöründe çalıştırın.

Üretim: python araclar/oasis_gmsg.py import kaynaklar/main.gmsg ceviri/main_tr.md <cikti.gmsg>. Araç Rozenmad’ın Ever Oasis GMSG çalışmasından uyarlanmıştır.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/kullanim_notlari.md)

## Kaynaklar

- [Kaynak 1](https://github.com/rozenmad/ever_oasis_gmsg)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
