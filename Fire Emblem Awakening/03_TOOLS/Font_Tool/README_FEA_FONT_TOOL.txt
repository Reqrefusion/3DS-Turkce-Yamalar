FEA FONT TOOL
=============

Fire Emblem Awakening .bfnt.lz font dosyalarını komut satırından çıkarır ve
tekrar enjekte eder.

GEREKSİNİMLER
--------------
Python 3.9+
Pillow:
    pip install pillow

Bu pakette fea_font_tool.py ve fea_lang_tool.py birlikte tutulmalıdır.

1) FONTLARI ÇIKAR
-----------------
    python fea_font_tool.py extract fonts.zip font_project

Örnek çıktı:

font_project/
  System/
    metadata.json
    glyphs.csv
    original.bfnt
    page_0.png
    page_1.png
  UI_L/
    glyphs.csv
    page_0.png
  UI_M/
    ...
  UI_S/
    ...
  ank/
    ...
  Debug/
    ...

glyphs.csv alanları:
- index
- codepoint
- char
- page
- x, y
- width, height
- byte10, byte11, byte12
- tail_hex

PNG atlasları düzenlenebilir.
glyphs.csv içindeki Unicode codepoint ve koordinatlar da düzenlenebilir.

NOT:
Bu sürüm glyph satır SAYISINI değiştirmez. Ancak kullanılmayan/placeholder bir
satırın codepoint'ini Türkçe karaktere dönüştürmek mümkündür.

2) GERİ ENJEKTE ET
------------------
    python fea_font_tool.py inject fonts.zip font_project fonts_modified.zip

Araç:
- PNG'yi 3DS tiled L4/L8 atlasına geri çevirir
- glyphs.csv tablosunu BFNT'ye yazar
- BFNT'yi LZ11 sıkıştırır
- Fire Emblem 0x13 wrapper'ını geri ekler
- sonucu tekrar açıp doğrular

3) TÜRKÇE KARAKTER RAPORU
--------------------------
    python fea_font_tool.py turkish-report fonts.zip

Kontrol edilen karakterler:
    Ç Ğ İ Ö Ş Ü ç ğ ı ö ş ü

"YOK":
  Glyph table'da Unicode kodu bulunmuyor.

"BOŞ/PLACEHOLDER":
  Kod var fakat atlas koordinatındaki glyph gerçek çizim değil.

"OK":
  Unicode kodu var ve atlas bölgesinde görünür glyph mevcut.

ÖNEMLİ BULGU
-------------
Verilen font paketinde:
- System, ank ve Debug içinde Ç/ç, Ö/ö, Ü/ü gerçek glyph olarak mevcut.
- Ğ/ğ, İ/ı, Ş/ş eksik.
- UI_L, UI_M ve UI_S'de Latin-1 Türkçe karakter kayıtlarının bir kısmı mevcut
  görünse de atlas karşılıkları 1x1 boş placeholder.

Bu nedenle düzgün Türkçe için yalnız mesaj dosyasına UTF-16LE yazmak yeterli
değil; font atlası + glyph table da patch edilmelidir.
