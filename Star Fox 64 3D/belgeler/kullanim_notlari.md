# Çeviri çalışma kuralları

Komutları oyun klasöründe çalıştırın. Ana çeviri kaynağı `ceviri/tr_TR.jsonl` dosyasıdır. Her kayıt tek fiziksel satırdır; normalde yalnız `translation` alanını değiştirin.

## Düzenleme ve kontrol

- Doğal Türkçe ve karakterin konuşma tonunu koruyun.
- `{MSBT:...}` kontrol kodlarını silmeyin, eklemeyin veya sırasını değiştirmeyin.
- Kaynak satır sayısını koruyun. En uzun görünür satır için araç kaynak uzunluğunun üzerine sekiz karakter tolerans uygular.
- Terimler için [terminoloji belgesini](TERMINOLOGY.md) kullanın.

```text
python araclar/validate_translation.py
python araclar/make_review_tsv.py <Resources.zip>
python araclar/import_review_tsv.py review/tr_TR_review.tsv
python araclar/validate_translation.py
```

TSV, düzenleme için üretilen bir görünümdür. Değişiklikleri ana JSONL dosyasına geri aktarın. Kaynak metin ve özgün oyun girdilerini katkı paketine eklemeyin.

Üretim için [üretim rehberine](BUILDING.md), görünüm kontrolü için [test rehberine](TESTING.md) bakın. Yerel doğrulama aracı çalıştırılabilir; bu klasörde otomatik GitHub iş akışı bulunmuyor.

Bu bağımsız bir hayran yerelleştirme projesidir. Star Fox, Nintendo ve ilgili oyun içerikleri hak sahiplerine aittir. Özgün belgede araç kodu için MIT lisansı belirtilmiştir; bu klasörde ayrı lisans dosyası bulunmuyor.
