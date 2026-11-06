# Sushi Striker The Way of Sushido Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001C1D00/` → `sd:/luma/titles/00040000001C1D00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/`.

Araç girişi: `araclar/sushi_msbt_csv_flat.py`. Komutları oyun klasöründe çalıştırın.

MSBT CSV kayıtlarını düzenlerken kontrol kodlarını koruyun. Teknik denetim araclar/msbt_technical_validator.py, font araçları araclar/Font altında bulunur.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
