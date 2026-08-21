# Font glyph kalite düzeltmesi — v3.11

Gerçek 3DS geri bildiriminde küçük/altyazı yazısında `ğ` breve işareti ve kuyruğu yeterince seçilmiyordu. Önceki breve birkaç çapraz pikselden oluştuğu için düşük çözünürlükte X/V gibi görünebiliyordu.

v3.11 her iki runtime fontunda (`Graphics/UI/Font/Font`, `Graphics/UI_en/Font/Font`) `ğ/ð` glyph'ini kaynak `g` gövdesinden yeniden kurar. Üst işaret üç satırlık belirgin U-biçimli breve olarak çizilir. Descender pikselleri tam alpha yapılır; 14px küçük fontta alt g halkasının son satırı kapatılarak kuyruğun kesik görünmesi azaltılır. `Ğ/Ð` de aynı breve geometrisini kullanır.

`ı/þ` için kaynak küçük `i` glyph'i her build'de baştan kopyalanır ve yalnız bağlantısız nokta bileşeninin satırları silinir. Gövde taşınmaz, döndürülmez veya aynalanmaz.

Reports klasöründeki `FONT_GLYPHS_COMMON_v311.png` ve `FONT_GLYPHS_UI_EN_v311.png` dosyaları gerçek CFNT bitmaplerinin nearest-neighbor büyütülmüş kontrol görüntüleridir.
