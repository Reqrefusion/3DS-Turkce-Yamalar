# Belgelenen hatalar — teknik inceleme

İnceleme tarihi: 5 Kasım 2026

- [Hata bildirimi](https://github.com/Reqrefusion/3DS-Turkce-Yamalar/issues/4)
- [Yayın sayfası](https://gamebanana.com/mods/705559)

## Doğrulanan düzeltmeler

Metin ve komut argümanları ayrı okunur. Eski yöntemde yazı karakteri sanılan sayısal argümanlar değişebiliyordu; komut uzunluklarındaki yanlışlar da metnin ilk harflerini argüman gibi yorumlayabiliyordu. Dönüştürücü artık bütün komut argümanlarını tüketip atladıktan sonra yalnız metin kodlarını yeniden kodlar.

Yerel komut işleyicilerinin incelenmesiyle argüman uzunlukları düzeltildi. Önemli örnekler: 0x76 iki, 0x6E bir, 0x33 beş, 0x60 dört argüman tüketir. 0x69 işleyicisi iki argüman tüketir. 0x7F yerel işleyicisi argümansızdır; HD'deki tek argümanlı kullanımı doğrudan taşınamaz. Bilinen HD çiftleri dosya boyunu koruyan iki yerel boş komuta dönüştürülür.

Sayfa içi koşullu atlamalar (0x35, koşul bit 0x80 kapalı) özgün hedef komutla eşleştirilip Türkçe sayfanın gerçek bayt konumuna taşınır. Paketlenmiş tablo girdilerinde ana sayfa korunur, o sayfanın içindeki hedef konumu yeniden hesaplanır. Gerçek sayfa başlangıçları ve senaryo uzunluğu korunur; hedef taşıyan bazı tablo değerleri bilinçli olarak güncellenir.

Yerel atlama hesabının eksik olması, Türkçe paketteki 1.776 yerel atlamanın 1.077'sinin komut başlangıcına ulaşmamasına neden oluyordu. Diğer bazı yanlış adresler tesadüfen başka bir geçerli komuta denk geliyordu. Toplam 1.274 yerel atlama ve 68 paketlenmiş tablo hedefi taşındı. Üç özgün metin başlangıcı hedefi de ayrıca desteklendi.

## Portekizce referans

Kullanıcının sağladığı Brazilian Portuguese Translation CIA paketi çalışma alanına açılarak karşılaştırıldı. Bu paket ABD sürümüdür (0004000000138F00); Türkçe paket Avrupa sürümüdür (0004000000133300). Program dosyası veya oyun varlıkları bölgeler arasında kopyalanmadı.

Yeni eşleştirme, özgünle eşleştirilen 1.776 Portekizce yerel atlama değerinin tamamını aynen hesaplıyor. 365 paketlenmiş tablo hedefinin 364'ü de eşleşiyor. Portekizce GS1/sc3_2_text tablo girişi 218, sayfa 130'un +2 konumunu seçerken özgün +8 konumunu seçiyor; ikisi de geçerli kontrol başlangıcı olduğundan bu ayrı akış farkı Türkçe pakete kopyalanmadı.

İncelenen komut işleyicileri ve yönlendirme tablosu EUR koduyla aynı. Bütün program dosyasının aynı olduğu iddia edilmiyor. Kanıt adresleri: yönlendirme 0x15DBAC, işleyici tablosu 0x25B2D4, yardımcı atlama tablosu 0x25B4D4. Yardımcı tablo bütün işleyicilerin gerçek argüman tüketimini yansıtmadığı için tek başına kullanılmadı.

## Somut sahne örneği

GS1/sc1_0_text sayfa 78, Maya'nın ablasının telefonunu anlattığı konuşmada 1402/1396/1402 adresleri Türkçe dosyada 1404/1398/1404 olmalıdır. Böylece hidetextbox/0x37/hidetextbox komutlarına ulaşılır. Yanlış adreslerden ikisi satır sonuna ve başka bir komutun argümanına düşüyordu. Aynı sayfanın dış dallanması [22145, 147], avukat kararı sayfasının iki seçenekli dallanması [228, 229] olarak özgün ve Portekizce dosyalarla eşleşir. Sayfa numaraları sıfırdan başlar.

## Depodaki araçlara işlenen korumalar

- Eski ana araç çağrıları yeni girişe yönlendirilir; aktif giriş `aat3ds_tool.py` dosyasıdır.
- Karaktere benzeyen komut argümanları dönüştürülmez.
- Her aktarımda kontrol onarımı, atlama taşıma ve metin koruma denetimi zorunludur.
- Belirsiz veya ters sıralı eşleştirmeler, çözülemeyen hedefler, eksik senaryolar ve bilinmeyen metin kodları hatayla durur.
- Paket ve indeks birlikte oluşturulur; giriş çiftleri işlemden önce doğrulanır.
- Onarım, bütün kontroller bitene kadar geçici klasörde tutulur. Önceki sonuçlar üzerine yazılmaz.
- 25 hedefli kontrol, geçmiş metin bozulmasını ve eksik adres taşımasını yeniden üretip denetler.

## Gerçek dosyalarda sonuçlar

103 senaryoda 3.681.265 metin karakter kodu korunuyor. Depodaki güncel onarım araçları daha önce doğrulanmış senaryo çıktılarıyla birebir aynı sonucu veriyor. 1.776 yerel atlama ve 365 paketlenmiş hedef özgün komut veya metin başlangıcıyla eşleşiyor. 12.938 diyalog dışı paket girdisi, 103 JP kayıt yuvası (boş kayıtlar dâhil) ve mevcut Türkçe code.bin korunuyor.

Bunlar dosya ve kontrol akışı doğrulamalarıdır. Beş bildirimin oyun içinde giderildiği henüz doğrulanmadı. Ekranda kalan yazı, farklı inceleme sıralarında makbuzu edinme, Maya'nın ablasını anlattığı konuşma, döngü ve ilerleme noktaları emülatör veya cihaz üzerinde ayrıca denenmelidir.

## Açık kalan inceleme

Anlamı kesinleşmeyen 10 parametre farkı otomatik geri alınmadı. Olay sırası farklı 27 sayfaya genel parametre kopyalama uygulanmadı; yerel hedef eşleştirmesi bunlardan bağımsız denetlendi. Üçüncü oyunun kısa varyantlarındaki devralınan kuyruk tabloları ayrıca inceleme gerektiriyor. Portekizce pakette de ana dosyayla ham değer farkları bulunduğundan bunlar körlemesine kopyalanmadı.

Ayrıntılı `control_fix_report.json`, girdi/çıktı özetlerini, komut değişikliklerini, yerel hedef eşleştirmelerini ve işlem dışında kalan sayfaları içerir. Tam oyun ve Portekizce ROM verileri depoya eklenmez.
