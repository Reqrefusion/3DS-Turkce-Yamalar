# Kalan İşler / Sonraki Denetimler

 temel menü/UI kısa metinleri, EventViewer başlıkları, Shop replikleri ve Paramater cümle açıklamaları büyük ölçüde temizlendi. Ancak “kaynakla aynı” olmak tek başına çeviri eksikliği kanıtı olmadığı için kalan alanlar bağlama göre incelenmelidir.

1. `Paramater/ItemTable.btb`: kaynakla aynı 874 occurrence'ın çoğu eşya/silah/zırh özel adı. Bunlar kullanıcının mevcut terminolojisiyle tek tek karar verilerek çevrilmeli; kör otomatik çeviri yapılmamalı.
2. `Paramater/DetailInfoItemTable.btb`: sentence-like açıklamalar tamamlandı; kaynakla aynı kalan yaklaşık 348 occurrence çoğunlukla eşya adı.
3. `Battle/MonsterData.btb` ve ability tabloları: canavar/boss/özel yetenek adları için adlandırma politikası gerekiyor.
4. Eski Square Enix Members / network edge-path mesajlarının bir bölümü Japonca/legacy olarak kaynakta duruyor. Oyunda erişilebilir olup olmadığı ayrıca test edilmeli.
5. `Subtitles`: altı doğrudan BTBF tablosundaki 168 kayıt ve altı arşiv BTBF tablosundaki 120 kayıt Türkçe akıcılığı yönünden incelendi; açılış altyazısındaki özne/ek hatası düzeltildi, dosya boyutu ve metin işaretçileri korundu. Kaynak İngilizce altyazılar bu klasörde yok; anlam karşılaştırması bekliyor. `TextTable` ve `DReportTable` tam anlatı denetimi bekliyor. Eşitlik taraması özel adları ve kısa ünlemleri de saydığı için otomatik “eksik” kabul edilmiyor.
 - `UI_TRANSLATIONS` içindeki “Skip this event?” eşlemesi “Bu olayı atlayalım mı?” olarak düzeltildi. Bu İngilizce anahtar etkin ROMFS içinde bulunmadığından runtime dosyasına aktarılmadı.
6. İlk görsel taramadan 65 raster aday henüz insan gözüyle son sınıflandırma bekliyor. Bunların önemli kısmı logo, ikon, sayı, HP/MP veya çevrilmemesi gereken marka/özel terim olabilir.
7. Gerçek 3DS/Azahar üzerinde ekran ekran test: clipping, satır kırılımı, sıra dışı font render'ı ve yalnız koşullu açılan menüler doğrulanmalı.
