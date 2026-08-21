# Başlığa Dön / START düğmesi — v3.12

Sorun yazı uzunluğundan ibaret değildi. `Layout/51_ARmovieTXT` içindeki birleşik BCLIM düğmeler eski raster patch'te yeniden çizilirken korunması gereken düğme zemini ve kontrol ikonlarına taşılmıştı.

Özellikle `camera_l_btn4.bclim` texture'ında START göstergesi x=47..94 aralığındadır. v3.12 bu bölgeyi kaynak İngilizce texture'dan byte/piksel olarak aynen korur ve Türkçe metni yalnız sağdaki x=102..208 metin paneline çizer. Sağdaki kamera/R bölgesi de korunur.

`camera_l_btn2.bclim` ve `start2.bclim` de aynı prensiple, kaynak düğme zemini ve ikonları korunarak yeniden yapılmıştır.

Kontrol görseli: `Reports/RETURN_TO_TITLE_BUTTONS_v312.png`.
