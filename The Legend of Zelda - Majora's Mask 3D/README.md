# The Legend of Zelda - Majora's Mask 3D Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `0004000000125600/` → `sd:/luma/titles/0004000000125600/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/translations_v089.csv`.

Araç girişi: `araclar/mm3d_tr_tool_v3.py`. Komutları oyun klasöründe çalıştırın.

İngilizce dil yuvası kullanılır. Grafik/CTXB denetim kayıtları raporlar altındadır. Görsel kaynaklarla font/metin üretimini birbirinden ayırın; oyun içi görünüm ayrıca kontrol edilmelidir.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/KURULUM_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
