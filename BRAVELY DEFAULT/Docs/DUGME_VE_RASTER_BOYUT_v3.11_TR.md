# Düğme/raster yazı boyutu — v3.11

v3.10'a kadar BCLYT başlıklarının önemli kısmı resmi EN/DE/FR/ES/IT genişlikleriyle karşılaştırılıyordu; resim içine gömülü BCLIM düğme yazıları ise çoğunlukla yalnız hedef kutuya sığdırılıyordu. Gerçek cihazda bu durum Türkçe yazının kaynak düğmeden daha iri görünmesine yol açtı.

v3.11 iki düzeltme yapar:

1. `Evet/Hayır` gibi BCLYT seçim düğmeleri aynı pane'in beş resmi dildeki en geniş görünür karşılığına göre yatay olarak ölçeklenir. Bu build'de 12 kayıt düzeltildi.
2. ButtonGuide, EventSkip, Düzenle, Hava Gemisi, Mesaj, Hazır/Kaçıyor, Kaydet, Para, Büyüler, Yetenek Bağı ve Savaş Sonuçları gibi raster etiketler orijinal İngilizce kaynak texture'dan yeniden oluşturulur. Türkçe metin kaynak yazının görsel bandı ve yükseklik sınırı içinde çizilir. Dar 128×16 Abilink rasterında yamadaki `Yetenek Bağı` teriminin kısa biçimi `Ytnk. Bağı` kullanılır; normal metin alanlarında tam terim korunur.

Kontrol görüntüsü: `Reports/BUTTON_RASTER_REFINEMENT_v311.png`.
