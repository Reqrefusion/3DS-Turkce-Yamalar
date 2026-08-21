# UI taşma ve hiza denetimi — v3.7

BCLYT `txt1` pane genişliği, font X boyutu ve gerçek CFNT advance değerleri birlikte ölçülür. v3.7'de güvenli hedef pane genişliğinin %88'idir. Eski 0.72 minimum ölçek sınırı gerçek cihaz geri bildirimine göre 0.55'e indirildi.

Bu build sırasında küçültülen txt1 kayıtları: **2708**.
Denetimde %92 pane oranını aşan kayıtlar: **2**. Bunlar `Reports/UI_OVERFLOW_AUDIT_v37.json` içinde listelenir; bazıları doğal olarak geniş kredi/URL/özel ekran metni olabilir.

Raster çevirilerde metin sabit görsel alanının içine yeniden fit edilir; tam ekran öğretici ve AR sayfaları ise orijinal İngilizce glyph alanı temizlenip Türkçe paragraflar native 3DS çözünürlüğünde yeniden çizilmiştir.
