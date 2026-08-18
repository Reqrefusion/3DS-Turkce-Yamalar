# Rhythm Heaven Megamix Türkçe — Multilang Project v22

Bu proje bağımsızdır. EN/FR/DE/IT/ES/TR sütunları oyun dosya yapısına göre ayrı TSV dosyalarında tutulur.

## v22

v13-v21 boyunca incelenen 5.247 benzersiz satırın dışında kalan **470 satırın tamamı** bu sürümde tek tek EN/FR/DE/IT/ES ve komşu bağlamla karşılaştırıldı. Böylece proje içindeki **5.717/5.717 satır en az bir kez manuel karşılaştırmalı incelemeden geçti**. Mesaj arşivine enjekte edilen gerçek giriş sayısı 5.715'tir; 2 satır yalnız resmî dil referansıdır.

## Düzenleme

`project/EUENmessage/pajama_sarc/arc/` altındaki ilgili `*.msbt.tsv` dosyasını aç. Sadece `Turkish` sütununu değiştir; `[[TAG]]`, `[[END]]`, `[[PUA]]` kodlarını koru.

## Build

```bash
python build_text.py
python validate_text_v22.py
```

Çıktı: `build/pajama.zlib`.
