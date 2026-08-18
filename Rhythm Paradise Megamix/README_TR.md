# Rhythm Heaven Megamix Türkçe v22 ToolKit

Bu arşiv **tamamen bağımsızdır**; v21 veya daha eski ZIP'lere ihtiyaç duymaz. Çalışan 3DS font/layout tabanı, hazır v22 yaması, EN/FR/DE/IT/ES/TR proje dosyaları, MSBT/SARC aracı, build/doğrulama betikleri ve bütün raporlar içeridedir.

## Hazır kurulum

`ready_patch/README_TR.md` dosyasını oku. Kısaca eski `/luma/titles/000400000018A500` klasörünü tamamen silip `ready_patch/000400000018A500` klasörünü `/luma/titles/` içine kopyala.

## Sıfırdan build

ToolKit kökünde:

```bash
python tools/build_v22.py
```

Çıktı `build_v22/000400000018A500` olur. Script çalışan font/layout tabanını kopyalar, çok dilli projedeki Turkish sütunundan mesaj arşivini üretir ve yalnız `pajama.zlib` değiştiğini doğrular.

## Çeviri düzenleme

`project_multilang/project/EUENmessage/pajama_sarc/arc/` altında oyundaki dosya yapısıyla aynı ayrı TSV'ler bulunur. EN/FR/DE/IT/ES sütunlarını karşılaştır; yalnız `Turkish` sütununu değiştir. `[[TAG]]`, `[[END]]`, `[[PUA]]` kodlarını değiştirme. Ardından `python tools/build_v22.py`.

## v22 manuel kalite kapsamı

Önceki 5.247 benzersiz satırın dışında kalan 470 satırın tamamı bu sürümde tek tek incelendi. Proje toplamı **5.717/5.717 manuel karşılaştırmalı satır**; bunların 5.715'i gerçek MSBT girdisi, 2'si resmî dil referansıdır.

`reports/manual_review_by_file/` altında inceleme raporları yine oyunun mevcut dosya yapısıyla ayrı ayrı tutulur.
