# v3.5 değişiklikleri

- Gerçek 3DS testinde `Ğ/ğ/İ/ı/Ş/ş` karakterlerinin `?` görünmesi araştırıldı.
- Tam dump'ta `Graphics/UI/Font/Font` adlı ikinci ve yapısal olarak farklı ortak font tespit edildi.
- v3.4'ün yalnız `Graphics/UI_en/Font/Font` dosyasını yamaladığı doğrulandı.
- Ortak 17×17/128×128 font ve İngilizce 14×14/256×256 font birlikte yamalandı.
- Font patch kodu sheet/cell boyutundan bağımsızlaştırıldı.
- `patch_font_layeredfs.py` artık iki fontu birlikte üretir.
- FINF→CMAP aktif zincir doğrulaması ve görünür glyph piksel doğrulaması eklendi.
- LayeredFS paketleri iki hazır font arşivini de doğrudan içerir; ayrıca font patch komutu çalıştırmak gerekmez.
