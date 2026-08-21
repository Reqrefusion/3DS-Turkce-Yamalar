# v3.6 değişiklikleri

- Gerçek 3DS'te `Ğ/ğ/İ/ı/Ş/ş` karakterlerinin `?` olması için Latin-1 uyumluluk kodlaması eklendi.
- Hem ortak `Graphics/UI/Font/Font` hem `Graphics/UI_en/Font/Font` alias glyphleri yamalandı.
- Runtime BTBF ve BCLYT metinleri aynı uzunlukta güvenli kod noktalarına dönüştürüldü; pointer/offset değişmedi.
- code.bin statik analizi belgelendi; code.bin dağıtılmıyor ve code patch yapılmıyor.
- Common.zip 451/451 dosya hash/eşitlik karşılaştırması yapıldı.
- Eksik ID160 Abilink raster occurrence geri kazanıldı ve `Yetenek Bağı` olarak yamalandı.
- `Mesaj`, `Para`, `Büyüler`, `Kaydet`, tutorial ve profil rasterlarında hayalet/taşma/hiza düzeltmeleri yapıldı.
- v3.6 build scripti ve uyumluluk encode/decode aracı Tools'a eklendi.
