# Fire Emblem Awakening Türkçe yama

## Kurulum

Oyununuzun Title ID değeriyle eşleşen kök klasörü `sd:/luma/titles/` içine kopyalayın. Luma3DS ayarlarında **Enable game patching** açık olmalıdır. Mevcut yamanızı önce yedekleyin.

- `000400000009F100/` → `sd:/luma/titles/000400000009F100/`

## Çalışma dosyaları

Düzenleme kaynağı: `ceviri/project_normalized_with_manifest/`.

Araç girişi: `araclar/Language_Tool_V2/fea_lang_tool.py`. Komutları oyun klasöründe çalıştırın.

Normalize edilmiş CSV proje ağacını ve manifestini birlikte koruyun. Font çalışmaları `varliklar/fontlar` altındadır.

Yama üretimi için mevcut Title ID romfs klasörü şablon olarak yeterlidir:

```
python araclar/Build_Helper/rebuild_pass202_patch.py --m 000400000009F100/romfs
```

Üretim sonunda kurulabilir yama doğrudan `000400000009F100/romfs/` altına yazılır. Ara çıktılar varsayılan olarak sistem geçici klasörüne yazılır ve depoda saklanmaz; saklamak için `--out <klasör>` kullanın. Yama klasörüne kurulum yapmadan üretmek için `--no-install`, farklı bir hedef için `--patch-dir` kullanılabilir.

## Klasörler

- `ceviri/`: Düzenlenecek çeviri verileri.
- `araclar/`: Üretim, düzenleme ve doğrulama araçları.
- `varliklar/`: Font ve görsel çalışma kaynakları.
- `belgeler/`: Kullanım ve teknik açıklamalar.

## Açıklamalar

- [Kullanım ve teknik notlar 1](raporlar/CHECKSUMS_SHA256.txt)
- [Kullanım ve teknik notlar 2](belgeler/QUICK_START_TR.txt)
- [Kullanım ve teknik notlar 3](belgeler/README_COMPLETE_BUNDLE_TR.txt)

Kurulum ve çeviri dosyalarının içerikleri klasör düzenlemesi sırasında korunmuştur. Teknik denetim ile gerçek cihazdaki görünüm ayrı değerlendirilmelidir.
