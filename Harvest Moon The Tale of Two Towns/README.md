# Harvest Moon The Tale of Two Towns Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `000400000007A300/` → `sd:/luma/titles/000400000007A300/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/mes_data.csv` ve `ceviri/event_mes_data.csv`.

Araç girişi: `araclar/build_final.py`. Komutları oyun klasöründe çalıştırın.

Kaynak ROM ZIP dosyası ve özel karakter haritası kullanılır. Üretimden önce girdileri ve çevirileri yedekleyin; mesaj kapasitesini ve kontrol kodlarını koruyun.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/kullanim_notlari.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
