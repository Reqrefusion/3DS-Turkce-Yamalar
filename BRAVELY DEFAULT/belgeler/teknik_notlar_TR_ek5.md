# değişiklikleri

- Kritik paketleme düzeltmesi: LayeredFS paketlerinde yalnız font yama aracı vardı; gerçek `Graphics/UI_en/Font/Font` dosyası paketlenmemişti.
- Türkçe font arşivi artık doğrudan `romfs/Graphics/UI_en/Font/Font` altında hazır olarak geliyor.
- `Ğ ğ İ ı Ş ş` için CFNT CMAP kayıtları binary içinde doğrulandı.
- `Ç ç Ö ö Ü ü` mevcut glyph ve genişlikleri korunuyor.
- Font patch aracı yeniden üretilebilirlik için pakette tutuldu; ancak 'ü kullanmak için ayrıca font komutu çalıştırmak gerekmiyor.
- Font aracındaki yanıltıcı eski glyph-indeksi açıklaması düzeltildi; kaynak glyph'ler CMAP üzerinden dinamik bulunuyor.
