# Zeus Quest Remastered Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `000400000F70DC00/` → `sd:/luma/titles/000400000F70DC00/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/EN_TR.csv` ve `ceviri/UI_EN_TR.csv`.

Araç girişi: `araclar/ceviri_editoru.py`. Komutları oyun klasöründe çalıştırın.

Font inceleme kayıtları varliklar/fontlar altındadır. Düzenleyici, metin üretimi ve doğrulama başlatıcıları araclar içinde bulunur.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `varliklar/`: Font ve görsel çalışma kaynakları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/README_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.

Yalnız EN/İngilizce metin yuvası Türkçeleştirilir. Dublaj eklenmez. Diğer dillerin konuşma blokları korunur; ortak kullanılan arayüz sahnelerinde bazı sabit yazılar dil değişse de Türkçe kalabilir.
