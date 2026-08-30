# Harvest Moon TR FINAL v16 - Width Fit

Bu paket metin düzeltmelerinin yanında resim tabanlı yazıları orijinal sprite/texture boyutlarına göre yeniden kontrol eder.

## Grafik yerleşim düzeltmeleri
- Klavye düğmeleri orijinal yazı yüksekliği ve dikey merkezine göre yeniden çizildi: `B GERİ`, `Y ONAY`, `X SİL`.
- `console_obj_data` içindeki tüm Türkçe resim etiketleri sabit sprite boyutunu değiştirmeden, orijinal yazının dikey metriklerine göre yeniden yerleştirildi.
- Yeni Türkçe yazının orijinalde olmayan bir kenara değmesi/taşması otomatik kontrolde sıfırlandı.
- `Kaydediliyor. Lütfen bekle...` görselinde kaybolan siyah arka plan geri getirildi.
- CEC `Teslim` düğmesindeki düz renkli dikdörtgen yama kaldırılıp ahşap zeminle yumuşak biçimde birleştirildi.
- Diğer değiştirilmiş DARC/BCLIM ve CTPK görsellerinin genişlik/yükseklik/format değerleri orijinalle karşılaştırıldı; görüntü boyutları değiştirilmedi.
- Kısa Türkçe kelimeler (`Başla!`, `Bitiş!` vb.) sırf İngilizceden daha kısa diye gereksiz yere genişletilmedi; yalnız gerçek kesilme/taşma/yerleşim hataları düzeltildi.

## Kurulum
Eski `/luma/titles/000400000007A300/` klasörünü tamamen silin ve paketteki `luma` klasörünü SD kart köküne kopyalayın.


## v16 yatay yerleşim taraması
- Tüm değiştirilen resim yazıları soldan/sağdan taşma ve yatay boşluk açısından tekrar denetlendi.
- Klavye `GERİ / ONAY / SİL` etiketlerinde önceki doğrulanmış yükseklik korunup yalnız yatay doluluk düzeltildi.
- Klavye yazıları orijinal Back/Register/Delete genişliğinin yaklaşık %90'ını hedefler; her iki yanda güvenli piksel boşluğu bırakılır.
- Diğer kısa Türkçe etiketler (ör. `Al`, `Yaz`, `Kış`) sırf İngilizce karşılığı daha geniş diye yapay biçimde uzatılmadı; merkezleme ve sınır güvenliği korundu.
