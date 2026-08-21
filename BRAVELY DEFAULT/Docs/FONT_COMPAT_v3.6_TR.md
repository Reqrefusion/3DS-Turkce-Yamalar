# Font / Türkçe karakter uyumluluğu — v3.6

## Sorunun kökü

`code.bin` statik taramasında `Graphics/UI$_TL$/Font/Font` yolu ve `Error mbstowcs:%s` dizisi bulundu. Bu, font dosyasının kendisi geniş Unicode CMAP içerse bile bazı metin yollarının locale/çok-baytlı dönüşümden geçebildiğini gösterir. Gerçek 3DS testinde U+011E/U+011F/U+0130/U+0131/U+015E/U+015F karakterlerinin `?` olması bunu doğrulamıştır.

## v3.6 çözümü

Runtime metinlerde altı karakter, oyunun zaten desteklediği ve Türkçe yamada kullanılmayan Latin-1 slotlarına aktarılır:

- `Ğ` → `Ð` (U+00D0)
- `ğ` → `ð` (U+00F0)
- `İ` → `Þ` (U+00DE)
- `ı` → `þ` (U+00FE)
- `Ş` → `Æ` (U+00C6)
- `ş` → `æ` (U+00E6)

Hem `Graphics/UI/Font/Font` hem `Graphics/UI_en/Font/Font` içinde bu altı Latin-1 slotunun glyph bitmapleri gerçek Türkçe glyphlerle değiştirilmiştir. Böylece motor 8-bit/Latin-1 sınırında kalsa bile ekranda Türkçe harf görünür.

Bu, çevirinin anlamını değiştirmez; yalnız oyuna özel bir runtime kodlamasıdır. Araçlarda `turkish_compat_encoding_v36.py` ile tersine çevirme tablosu da bulunur.

Build öncesi yapılandırılmış metin taramasında alias karakterleri 0 idi; bu nedenle mevcut çeviride gerçek `Ð/ð/Þ/þ/Æ/æ` ile çakışma bulunmadı.
