# Eski araçların incelemesi



Kaynak klasör: `C:/Users/furka/Downloads/AceAtorneyTri/AATri Tools`



Bu klasör diyalog, paket, font, görsel ve ses iş akışları için yararlı dosya biçimi bilgileri içeriyor. İnceleme kod ve dosya karşılaştırmasına dayanır.



## Yararlı yöntemler ve aktarılan özellikler



| Eski araçtaki yöntem | Katkısı | Güncel araçtaki durumu |

| --- | --- | --- |

| Kaynakları imzalarına göre klasörlere ayırma | Görselleri, fontları ve diyalogları kolay bulma | `extract-pack --grouped` içine aktarıldı; dosya yolları ve özetler manifestte tutuluyor. |

| CMAP, CWDH ve texture bilgilerini tek font manifestinde toplama | Karakter → glif → genişlik ilişkisini birlikte inceleme | Font eşleştirmesi araştırması için referans; bütün manifest düzenleme zinciri henüz taşınmadı. |

| BCH içindeki birden çok dokuyu ayrı çıkarma | Tek dosyadaki farklı görsel katmanları düzenleme | Mevcut doku ayrıştırıcısıyla karşılaştırıldı. |

| RGBA8 ve RGB565 dönüştürme | ETC1 dışındaki görselleri de inceleme | Mevcut görsel yardımcı yalnız ETC1/ETC1A4 işliyor; bu ek biçimler için eski kod bir referans. Henüz aktarılmadı. |

| Ses kayıtlarını XML ve dalga dosyası sırasıyla ilişkilendirme | Ses indeksini ve adlarını takip etme | Ses çalışmaları için referans; diyalog düzeltme zincirine eklenmedi. |



Gruplama fikri korunurken yalnız büyük dosyaları diyalog sayan eşik yerine gerçek arşiv tablosu kontrolü kullanıldı. Özgün betikler ve dış çalıştırılabilir dosyalar değiştirilmedi.



## Diyalog araçları



`dialogue_tools/dlgTool2.py`, incelenen komut tablosundan 20 tanımda ayrılıyor. Bir tanım eski tabloda bulunmuyor. Argüman sayısı yanlış olunca metnin ilk harfleri komut argümanı gibi okunabilir veya argümanlar yeni komut sanılabilir.



| Komut | Eski argüman sayısı | Gözden geçirilmiş sayı |

| --- | ---: | ---: |

| 0x4 | 0 | 1 |

| 0x33 | 2 | 5 |

| 0x3a | 2 | 3 |

| 0x4a | 0 | 1 |

| 0x5a | 2 | 1 |

| 0x5c | 0 | 3 |

| 0x5e | tanımsız | 0 |

| 0x60 | 2 | 4 |

| 0x64 | 0 | 1 |

| 0x6e | 2 | 1 |

| 0x70 | 2 | 0 |

| 0x74 | 0 | 2 |

| 0x75 | 0 | 4 |

| 0x76 | 1 | 2 |

| 0x77 | 1 | 2 |

| 0x7b | 0 | 2 |

| 0x7c | 1 | 0 |

| 0x7d | 0 | 1 |

| 0x7e | 0 | 1 |

| 0x7f | 1 | 0 |



Derleyicinin `uni` karakter tablosu `ÇÖÜçöü` harflerini içeriyor; `ĞİŞğış` harflerini doğrudan içermiyor. Kaynakta karşılığı bulunmayan karakterler için hata verilmeden karakter atlanabiliyor. Bu nedenle doğrudan Türkçe Unicode metniyle güvenli bir derleme yolu değil.



`createBin`, sayfa başlangıçlarını yeniden yazıyor; fakat komut etiketlerindeki sayıları ve `do_not_delete` içindeki paketlenmiş hedef değerlerini aynen kopyalıyor. Çeviride metin uzunluğu değişince yerel atlamalar ve paketlenmiş hedeflerin de taşınması gerekiyor. `dlgComp.exe` çağrısı bu betikte hazırlanan ikili dosyayı sıkıştırmak için kullanılıyor; betiğin yazdığı hedefleri yeniden hesapladığına dair bir kaynak kanıtı yok.



Dil arşivi oluşturulurken `offset_list.bin` içindeki eski dosya konumlarına yazılıyor. Yeni sıkıştırılmış kayıt daha büyükse bir sonraki kayıtla çakışmasını engelleyen sınır kontrolü bulunmuyor. Güncel araçlar arşiv tablosunu yeniden oluşturuyor.



## Paket araçları



`packing_tools/packTool.py` iki önemli varsayım taşıyor:



- `compressed` altında karşılığı zaten bulunan dosyaları tekrar sıkıştırmıyor. Kaynak değişmiş olsa da eski önbellek kullanılabiliyor.

- Yeniden paketlerken açılmış boyutu özgün `pack.inc` dosyasından alıyor; değiştirilmiş ham dosyanın gerçek boyutunu yeniden hesaplamıyor.



Mevcut klasörde 58, 6786 ve 9622 diyalog girdilerinin önbellekleri açılıp ham `.dlg` dosyalarıyla karşılaştırıldı; bu üçü şu anda birebir eşleşiyor. Bu kontrol diğer önbellek dosyaları veya gelecekteki düzenlemeler için geçerlilik kanıtı değildir.



Güncel `aat3ds_tool.py` değiştirilmiş girdilerin boyutlarını ve bütün paket konumlarını hesaplayarak `pack.dat` ile `pack.inc` dosyalarını birlikte üretir; iki dosyanın uyumu ayrıca doğrulanır.



## Font ve program kodu araçları



`font_tools/bffnt.py` font tablolarını incelemek için kaynak olabilir. `patch_manifest_tr.py` sabit glif numaraları ve `42_manifest.json` adı kullanır; farklı bir fontta aynı numaraların aynı karakteri temsil ettiği varsayılamaz.



`font_tools/codePatcher.py`, verilen program dosyasını aynı yol üzerinde açıp `0x15B630` konumundan başlayan 131 adet iki baytlık ölçü alanına sabit değerler yazar. Programın kimliğini veya Türkçe profilini doğrulamıyor. Mevcut Türkçe kodla karşılaştırma:



| Harf | Mevcut Türkçe ölçü | Eski aracın yazacağı ölçü |

| --- | ---: | ---: |

| Ç | 12 | 5 |

| Ğ | 12 | 11 |

| İ | 5 | 13 |

| Ö | 12 | 9 |

| Ş | 10 | 5 |

| Ü | 12 | 10 |

| ç | 9 | 10 |

| ğ | 9 | 11 |

| ı | 6 | 10 |

| ö | 10 | 10 |

| ş | 8 | 8 |

| ü | 9 | 10 |



Örneğin `İ` için 5 yerine 13 yazılması, güncel Türkçe çizim ölçülerini bozabilir. Bu betik güncel Türkçe programın üzerine uygulanmamalı. İnceleme sırasında program dosyası değiştirilmedi.



## Görsel ve ses araçları



`picture_tools/BchPngConv2.py` ve `etc1tool.exe`, eski görsel iş akışına ait. `sound_tools/bcsar.py`, düzenlenmiş sesler ve Audacity paketi de ses çalışmaları için ayrı tutulmuş. Bu dosyalar diyalog/olay akışı düzeltmesinin parçası değil; şu incelemede çalıştırılmadılar.



## Kullanılacak yol



Paket ve diyalog üretimi için [güncel araçların kullanımı](TOOLS_TR.md) izlenmelidir. Eski betikler dosya biçimi araştırması için referans olarak korunabilir. Eski komut tablosu, karakter kodlayıcı ve sabit program yaması doğrudan yeni üretim zincirine alınmadı.



Kaynak betik özetleri ve ölçülen karşılaştırmalar `kaynaklar/legacy_tools_audit.json` dosyasındadır. Üçüncü taraf betiklerin tamamı veya çalıştırılabilir dosyaları depoya kopyalanmadı.

