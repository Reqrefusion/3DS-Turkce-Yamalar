# Bloodstained Curse of the Moon Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000001D3C00/` → `sd:/luma/titles/00040000001D3C00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/ttb_translations_tr_v2.csv`.

Araç girişi: `araclar/core/bloodstained_tr_tool.py`. Komutları oyun klasöründe çalıştırın.

TTB tabloları ve grafik metinleri farklı araçlar kullanır. Bazı araştırma betikleri dış çalışma yollarına bağlıdır; klasörün tamamı tek komutla yeniden üretilebilir kabul edilmemelidir.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.
- `calisma/`: Ara çıktılar ve çalışma kopyaları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_PROJECT_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
