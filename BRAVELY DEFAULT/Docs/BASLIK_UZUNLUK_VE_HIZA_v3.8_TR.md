# Başlık uzunluğu ve hiza denetimi — v3.8

v3.7'nin genel pane yüzdesi denetimi gerçek cihazdaki başlık/etiket problemini tam temsil etmiyordu. v3.8 aynı `txt1` kaydını İngilizce, Almanca, Fransızca, İspanyolca ve İtalyanca resmi dosyalarda eşleştirir. Her dil için kendi CFNT advance genişliği ve kendi `font_x` değeri kullanılarak gerçek görünür metin genişliği hesaplanır.

Türkçe metin, aynı kaydın **en geniş resmi yerelleştirmesinden** belirgin biçimde genişse ve kendi alanının büyük bölümünü kullanıyorsa yalnız yatay `font_x` küçültülür. Dikey boyut, pane konumu, hizalama ve font glyph'leri değiştirilmez. Böylece bütün UI'yi küçültmek yerine yalnız riskli uzun başlıklar düzeltilir.

Bu build'de düzeltilen kayıt sayısı: **12**.

Örnek riskler: `Arkadaş Menüsü`, `Mızraklar`, `Miğferler`, `İsabet:`, `Kaçınma:`, `Arkadaşlar`, uzun Config/StreetPass başlıkları. Ayrıntılı önce/sonra ölçümleri `Reports/LOCALE_AWARE_TITLE_FIT_v38.json` içindedir.
