# Mario & Luigi - Dream Team Bros Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `00040000000D9000/` → `sd:/luma/titles/00040000000D9000/`

## Çalışma dosyaları

Düzenleme kaynağı: `kaynaklar/current_patch/tr/fmes/json/`.

Araç girişi: `araclar/fmes_safe_packager.py`. Komutları oyun klasöründe çalıştırın.

FMes/MSBT JSON kayıtlarındaki metin alanlarını düzenleyin; kod, kimlik ve ham veri alanlarını koruyun. Resmî dil referansları kaynaklar/languages altında tutulur.

## Klasörler

- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `kaynaklar/`: Üretimde gereken girdiler ve referanslar.
- `belgeler/`: Kullanım ve teknik açıklamalar.
- `raporlar/`: Denetim ve test kayıtları.

## Açıklamalar

- [Kullanım ve teknik notlar 1](belgeler/kullanim_notlari.md)
- [Kullanım ve teknik notlar 2](belgeler/NAME_LOCALIZATION_GUIDE_TR.md)
- [Kullanım ve teknik notlar 3](belgeler/WORKFLOW_TR.md)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
