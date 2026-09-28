STREET FIGHTER 3DS TÜRKÇE ÇEVİRİ ARAÇLARI

V7 notu: Bu arşiv beş dilin orijinal ARC kaynaklarını içermez; aşağıdaki
extract-all/build komutları için oyundan alınan ayrı bir kaynak gerekir.
Paketlenmiş altı düzeltilmiş görseli yeniden oluşturmak için bu klasörde
"py bozuk_firca_yazilarini_duzelt.py" komutunu çalıştırabilirsiniz.
Paketlenmiş dört fontu mevcut YAMA üzerinde tekrar güncellemek için
"py font_isaretlerini_yenile.py" komutunu çalıştırabilirsiniz.
Bu iki komut yanında gelen fonts dosyalarını ve Pillow'u kullanır.
V8'de eklenen üç arayüz düzeltmesini tekrar oluşturmak için
"py ek_arayuz_gorsellerini_duzelt.py" komutunu çalıştırın.

Amaç
- _eng, _fre, _ger, _ita, _spa klasörlerindeki aynı ARC dosyalarını eşleştirir.
- Metinleri ARC bazında CSV'ye çıkarır; bütün diller yan yana görünür.
- Her CSV'de sütunlar: arc_entry, gmd, value_index, key, eng, fre, ger, ita, spa, tur.
- Tek bir dev CSV oluşturmaz. Örneğin _GUI/_mes/common.arc -> texts/_GUI/_mes/common.arc.csv olur.
- TEX görsellerini ARC bazında PNG'ye çıkarır. Her varlığın eng/fre/ger/ita/spa ve tur PNG'si yan yana bulunur.
- Geri yazarken mevcut İngilizce ARC dosya adını, klasörünü ve iç giriş adlarını korur. Yeni bir _tur dosya adı icat etmez.
- CSV'lere sürüm alanı eklemez.

Kurulum
1) Python 3 kurulu olmalı.
2) KURULUM.bat çalıştırın. Bu yalnız PNG işlemleri için Pillow kurar.
3) GUI_AC.bat ile grafik arayüzü açabilirsiniz.

Kaynak
- Doğrudan archive.zip seçebilirsiniz.
- Ya da içinde _eng, _fre, _ger, _ita, _spa klasörleri bulunan klasörü seçebilirsiniz.

Çıkarma
GUI'de "Metin + Resim Çıkar" düğmesini kullanın.
Komut satırı:
  py sf4_tr_tool.py extract-all archive.zip workspace

Metin çevirisi
- workspace/texts altındaki CSV'leri açın.
- eng/fre/ger/ita/spa referanstır.
- Yalnız tur sütununu Türkçeye çevirin.
- tur başlangıçta eng ile doldurulur; böylece çevrilmemiş satırlar İngilizce kalır.
- CSV dosyasının satır kimliklerini ve arc_entry/value_index değerlerini değiştirmeyin.

Görsel çevirisi
- workspace/images altında her ARC kendi klasöründedir.
- *.eng.png, *.fre.png, *.ger.png, *.ita.png, *.spa.png referanstır.
- Yalnız *.tur.png dosyalarını düzenleyin.
- Görsel genişliği/yükseklığı değişmemelidir.
- ALPHA türünde beyaz renk + alfa kanalı asıl maskeyi temsil eder.
- assets.csv yalnız eşleştirme bilgisidir; görsel geri yazma için tur.png dosya adı kullanılır.

Geri yazma
GUI'de "Türkçeyi Geri Yaz" düğmesini kullanın.
Komut satırı:
  py sf4_tr_tool.py build archive.zip workspace patched

Çıktı
- patched/_eng altında kaynakla aynı 254 ARC yolu oluşturulur.
- Değişmeyen ARC'ler kaynak byte'larıyla aynen kopyalanır.
- Değişen GMD/TEX öğeleri kendi mevcut ARC dosyasının içine geri enjekte edilir.
- Böylece oyunda İngilizce dil dosyalarının yerine kullanılabilecek, isimleri eşleşen bir set elde edilir.

Kontrol
  py sf4_tr_tool.py check archive.zip

Notlar
- Bu pakette gözlenen TEX yapıları desteklenir: RGBA dokular ve Nintendo 3DS ETC1A4 alfa/maske dokuları.
- Format 12 ETC1A4 dosyalarında renk blokları korunur, PNG düzenlemesi yalnız alpha maskesine geri yazılır.
- İngilizce build sırasında Türkçe GFD font düzeltmesi otomatik uygulanır; ÇçĞğİıÖöŞşÜü ve çeviride kullanılan âîû“ glifleri kapsanır.
- GMD UTF-8 metinleri kayıpsız okunup yeniden yazılır.
- Her zaman orijinal dosyaların yedeğini tutun.
