# code.bin analizi — v3.6

Gönderilen dosya SHA-256: `640d483311b35d3eef050dfc7d7d9dbb3144504d8415ce4560c623185c6b4029`
Boyut: 5709824 bayt.

Önemli statik dizeler:

- `Graphics/UI$_TL$/Font/Font` — 108 doğrudan eşleşme
- `GetCurrentLocale`
- `../../Source/Nintendo3ds/Common/LocaleSetting.hpp`
- `Error mbstowcs:%s`

`$_TL$` oyunun dil tokenıdır; çalışırken boş veya `_en`, `_fr`, `_de`, `_es`, `_it` gibi bir ekle font yolunu seçer. Bu yüzden v3.5'te iki Batı font yolunu yamalamak doğruydu ama U+0100+ karakterlerin `?` olmasını çözmeye yetmedi. `mbstowcs` bulgusu ve gerçek cihaz testi birlikte değerlendirildiğinde v3.6 Latin-1 uyumluluk katmanını kullanır.

`code.bin` patch paketine kopyalanmamıştır; yalnız analiz hash'i ve sonuçları belgelenmiştir. Bu sürüm code patch gerektirmez.
