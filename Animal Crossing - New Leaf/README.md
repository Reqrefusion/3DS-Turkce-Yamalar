# Animal Crossing - New Leaf Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000086400/` → `sd:/luma/titles/0004000000086400/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/`.

Araç girişi: `araclar/build_patch.py`. Komutları oyun klasöründe çalıştırın.

Üretim için kendi oyununuzdan çıkarılmış Script ve Font girdileri gerekir. Komut: python araclar/build_patch.py --script <Script> --translations ceviri --font <Font> --out <cikti>.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
