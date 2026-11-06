# Kirby Planet Robobot Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000183600/` → `sd:/luma/titles/0004000000183600/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/MSBT_CSV/`.

Araç girişi: `araclar/robobo_build.py`. Komutları oyun klasöründe çalıştırın.

TR_Turkish alanlarını düzenleyin. Kaynak şablonlar kaynaklar, font girdileri varliklar/fontlar, üretim çıktıları calisma/uretim altındadır. Kontrol için araclar/robobo_verify.py kullanılır.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `varliklar/`: Font ve görsel çalışma kaynakları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.
- `calisma/`: Ara çıktılar ve çalışma kopyaları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/00_OKU_BENI.md)
- [Kullanım ve teknik notlar 2](belgeler/KURULUM_VE_CALISMA_AKISI.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
