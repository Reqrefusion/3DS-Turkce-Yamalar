# Bravely Default TR — v3.7

- `ı` glyph'i artık `i` harfinin aynısından yalnız üstteki nokta bileşeni silinerek oluşturuluyor; U+0131 ve runtime `þ` alias slotu aynı bitmap'i kullanıyor.
- ItemTable'da 247 eşya adı ve 516 eşya açıklaması için Türkçe karşılık eklendi.
- Bravely Second savaş sesi altyazılarındaki 30 İngilizce satır Türkçeleştirildi.
- Açılış/bağlantı öğreticisindeki 8 tam ekran İngilizce BCLIM bilgi sayfası Türkçe raster olarak yeniden çizildi.
- AR işaretiyle ilgili iki 320x240 bilgi görseli Türkçeleştirildi.
- Batı dillerinde ortak kaldığı için önceki EN-vs-FR/DE taramasından kaçan buton/sekme/başlık görselleri `UI_en` ↔ ortak `UI` karşılaştırmasıyla bulundu ve yamalandı.
- BCLYT'lere gerçek CFNT advance ölçümüyle ikinci bir taşma geçişi uygulandı; pane genişliğinin %88'i hedefleniyor ve gerekirse yatay font ölçeği 0.55'e kadar düşebiliyor.

Bu sürüm tam progress build'dir; v3.6'daki Common_en, UI, iki-font uyumluluk kodlaması ve önceki raster düzeltmelerini içerir.
