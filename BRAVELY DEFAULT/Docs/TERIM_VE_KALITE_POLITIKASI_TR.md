# Terim ve Kalite Politikası

- Bir kavram kullanıcının mevcut `Common_en` çevirisinde karşılığa sahipse UI aynı karşılığı kullanır.
- Aynı İngilizce kelime bağlama göre farklı anlama geliyorsa bağlam ayrılır. Örn. `Slow`: status effect için `Yavaşlat`, message speed için `Yavaş`.
- Özel adlar ve yerleşmiş kısaltmalar otomatik çevrilmez: HP, MP, Normal, Katana ve karakter/yer özel adları bağlama göre korunabilir.
- EventViewer'da tam kaynak string'e bağlı curated override kullanılır; parçalı kelime değişimi yapılmaz.
- Uzun UI metni önce resmi DE/ES/FR/IT geometry donor ile denenir; gerekirse yalnız yatay font boyutu kontrollü küçültülür. Anlam sırf sığdırmak için bozulmaz.
- Dar, tekrarlanan buton alanlarında yalnız anlaşılır ve tutarlı kısaltma kullanılabilir.
- Metin hücresi kullanıcı tarafından zaten Türkçeleştirilmişse normal build onu overwrite etmez; yalnız açık kalite hatası için kaynak-keyed düzeltme uygulanır.
