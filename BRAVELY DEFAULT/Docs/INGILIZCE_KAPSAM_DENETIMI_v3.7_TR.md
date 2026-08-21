# İngilizce kapsam denetimi — v3.7

Önceki denetim yalnız çevrilebilir kısa UI dizeleri ve Batı dilleri arasında farklı rasterları esas alıyordu. Bu iki kör nokta oluşturuyordu:

1. Kaynak İngilizceyle birebir kalan ItemTable ad/açıklamaları çok sayıda olduğu hâlde “özel ad olabilir” kümesinde kalıyordu. v3.7 ItemTable ve DetailInfoItemTable'ı ayrı, kullanıcıya görünür veri olarak ele alır.
2. Tüm Batı dillerinde aynı İngilizce resim kullanılan BCLIM'ler EN↔FR/DE/ES/IT fark taramasında görünmez. v3.7 ayrıca `Graphics/UI_en` ile ortak/Japonca `Graphics/UI` görünür piksel karşılaştırması yapar. Açılış bilgi sayfaları ve AR açıklamaları bu ikinci taramada bulunmuştur.

Bilerek korunabilenler: karakter/yer özel adları, HP/MP/BP/JP/EXP/pg gibi oyun kısaltmaları, StreetPass/Bravely Second gibi ürün/özellik adları ve geliştirici Dummy/test kayıtları.
