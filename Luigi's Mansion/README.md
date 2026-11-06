# Luigi's Mansion Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001D1A00/` → `sd:/luma/titles/00040000001D1A00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/main.gmsg.csv`.

Araç girişi: `araclar/lm3ds_export_csv.py`. Komutları oyun klasöründe çalıştırın.

Karşılaştırma, sözlük ve kalite tabloları ceviri altında tutulur. Font/kurulum denetimi için araclar/lm3ds_validate_patch.py bulunur.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
