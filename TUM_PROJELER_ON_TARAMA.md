# Tüm 3DS projeleri: ön tarama ve bulgular

Tarih: 2026-11-06

Kapsam: 65 proje klasörü. CSV/TSV sütunları eşleştirilebilen 34 projede otomatik aday taraması yapıldı. Diğer projelerde metinler farklı biçimlerde olabilir; sıfır satır sonucu çeviri olmadığı anlamına gelmez.

Bu belge tam dil incelemesi değildir. Satır sayıları seçilmiş tabloların ham toplamıdır; kaynak, ara çıktı ve tekrar tablolarını içerebilir. Boşluk, kaynakla aynı metin veya etiket farkı otomatik olarak hata sayılmaz. Sayıların her biri ilgili oyunun kaynak ve paketleme yapısıyla doğrulanmalıdır.

## Proje kapsamı

| Proje | Okunan tablo | Ham satır | Bulgular / sonraki işlem |
|---|---:|---:|---|
| Animal Crossing - New Leaf | 3125 | 74,964 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| AR Games | 1 | 354 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Bloodstained Curse of the Moon | 2 | 5,100 | İlk geçiş tablosu Japonca ve başka dil kayıtları da içeriyor; boşluklar etkin İngilizce kapsamından ayrılmalı. TTB tablosunda 178 etkin kayıt için manuel inceleme başladı; 9 hedef satırı ve üretici eşlemeleri düzeltildi, biçim denetimi uyarısız geçti. İkili yeniden üretim için gereken İngilizce kaynak girdi klasörde yok; mevcut ROMFS metinleri Japonca. |
| BRAVELY DEFAULT | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Castlevania Lords of Shadow - Mirror of Fate | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Cave Story 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Detective Pikachu | 27 | 17,653 | Episode 1’deki 1.307/1.307 kayıt kaynak dillerle manuel karşılaştırıldı; toplamda 8.044/17.653 kayıt gözden geçirildi, 2.827 çeviri düzeltildi. Kalan kayıtlar ve diğer bölüm dosyaları sırada. |
| Devilish Brain Training Can you stay focused | 11 | 8,325 | `main.msbt.csv` (686/686), `nou_jintori.msbt.csv` (48/48), `rlx.msbt.csv` (380/380), `etc1.msbt.csv` (1.193/1.193), `etc2.msbt.csv` (605/605), `etc3.msbt.csv` (396/396), `misc.msbt.csv` (421/421) ve `nou.msbt.csv` (1.884 kayıt; metin içeren kayıtlar kaynakla karşılaştırıldı) incelendi; toplam 692 Türkçe satır düzeltildi. Bu sekiz tabloda kontrol etiketi ve yer tutucu denetiminde 0 uyumsuzluk var. `common.msbt.csv` karakter tablosu; diğer 2 metin tablosunun incelemesi sırada. |
| Donkey Kong Country Returns 3D | 1 | 855 | 855 satır kaynakla incelendi, 15 düzeltme üretim CSV’sine aktarıldı. Arşiv yeniden üretildi; 855 metin birebir geri okundu ve paket CRC doğrulaması geçti. Gerçek oyun içi görünüm testi bekliyor. |
| Dr. Mario Miracle Cure | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Dragon Quest VIII - Journey of the Cursed King | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Ever Oasis | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Face Raiders | 2 | 854 | StgFace tablosundaki 244 dolu Türkçe hedefin tamamı kaynak dillerle incelendi, 18 ifade düzeltildi. Yer tutucu/tuş simgesi doğrulaması geçti; araçta iki genişlik inceleme işareti kaldı. CSV ve araçtan üretilen MSBT iki Title ID altındaki 26 dosyaya eşitlendi; cihazda görsel kontrol bekliyor. |
| Fallblox | 1 | 1,639 | ME_ToolHowTo00 düzeltmesine ek olarak yedi event eğitim diyaloğu düzenlendi. CSV ve event.msbt yenilendi; etiketler korundu, satır sınırları aşılmadı ve son derlemede yalnız beş metin değişti. |
| Fire Emblem Awakening | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Fullblox | 1 | 1,841 | Demo_Tlt_02 düzeltildi; CSV ve kurulum MSBT dosyası güncel. 2 satır / 258 px; tablodaki resmî üst sınır 441 px. Dosyada yalnız 1 kayıt değişti. |
| Gravity Falls - Legend of the Gnome Gemulets | 2 | 1,542 | main.csv 373/373 ve dialogue.csv 1.169/1.169 kayıt kaynakla karşılaştırıldı; 37 diyalog düzeltildi. Doğrulama 1.542/1.542 hedefte etiket hatası ve uzunluk uyarısı vermedi. Paketleme için özgün ROMFS gerekiyor. |
| Harvest Moon The Tale of Two Towns | 2 | 29,888 | mes_data.csv 5.242 satır; ilk 144 kayıtta 15 düzeltme. Takvimdeki 60 doğum günü satırı ve menü/yardım/dükkân/kitap alanlarından 29 satır düzeltildi; bankalar geri okundu ve eşitliği doğrulandı. event_mes_data.csv 24.646 kayıt; ilk 31 konum etiketi ve 97–175 aralığındaki festival/ürün adları kontrol edildi, Laney eki, üç tohum ve Pak Choi düzeltildi. 150 seçilmiş diyalog düzeltildi. “evcilin” ve belirsiz “Hala” taramalarında iki tabloda eşleşme kalmadı; çevrilmiş event kayıtlarındaki korunan kontrol kodlarında uyumsuzluk yok. Son grupta beş diyalog düzeltildi; 78 selam kaydındaki boşluk düzenlendi ve tek kısa alan "Hey {#232A}" biçiminde sığdırıldı. 84 event kaydının kapasite/kontrol denetimi, geri okuması ve dört bankanın eşitliği doğrulandı. Kalan kayıtlar incelenecek. |
| Heroes of Ruin | 14 | 13,648 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Hey! Pikmin | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| IRONFALL Invasion | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| James Noir's Hollywood Crimes 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Jewel Master - Atlantis 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Jewel Master - Cradle of Egypt 2 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Kid Icarus Uprising | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Kingdom Hearts 3D Dream Drop Distance | 2 | 15,400 | translations_aligned_en.csv kaynak şablonudur; tr_complete tablosunda karşılıkları dolu. |
| Kirby Planet Robobot | 1 | 2,430 | 30 tablonun 2.430/2.430 kaydı kaynakla karşılaştırıldı ve 311 çeviri düzeltildi; 324 kontrol simgesi denetlendi. 30 MSBT üretildi, bozuk etiket yok, 15/15 Latin font ve QA doğrulaması temiz. Gerçek cihazda görünüm kontrolü bekliyor. |
| Kirby Triple Deluxe | 1 | 1,847 | Kaynaklarla ilk inceleme başladı; arayüz, tutorial ve boss açıklamalarından 17 satır düzeltildi. 23 MSBT, 1.847 satırda CSV ile birebir eşleşiyor; bozuk token yok, Türkçe glifler 10 fontta doğrulandı. Tam dil incelemesi sürüyor. |
| Kirby's Extra Epic Yarn | 2 | 4,476 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Luigi's Mansion | 2 | 4,364 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Luigi's Mansion 2 | 2 | 2,096 | Örnek uyarılar {p} satır sonu sayılarından kaynaklanıyor; değişken kaybı olarak kabul edilmedi. |
| Mahjong Mysteries Ancient Athena | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Mario & Luigi - Dream Team Bros | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Mario & Luigi Superstar Saga + Bowser's Minions | 9 | 7,980 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Mario Party - The Top 100 | 1 | 2,254 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| MiiPlaza | 2 | 26,391 | StreetPass Battle, Panel Parçaları ve StreetPass Quest yardım/menü/Yardımcı Tavşan metinlerinden toplam 118 metin çevrildi. Araç doğrulaması: 12,434 eksik Türkçe; kontrol/placeholder hatası 0. Diğer güncelleme metinleri sırada. |
| Monster Hunter 4 Ultimate | 1 | 45,570 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Murder on the Titanic | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Mystery Case Files - Ravenhearst | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Mystery Murders - Jack the Ripper | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Mystery Murders The Sleeping Palace | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| New Art Academy | 3 | 17,802 | roundtrip_built.tsv yeniden çıkarılmış Türkçe çıktıdır; boş tr sütunu eksik çeviri sayılmaz. |
| Phoenix Wright - Ace Attorney Trilogy | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Pocket Card Jockey | 2 | 6,468 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Pokemon Omega Ruby | 2 | 45,447 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Pokemon Ultra Sun | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Pokemon X | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Pokémon Moon | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Poochy & Yoshi's Woolly World | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Professor Layton and the Miracle Mask | 2 | 31,378 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Pullblox | 1 | 1,227 | Öğretici örneklerinde devrik anlatım var; kontrol sırasını koruyan araç kuralı incelenmeli. Bu geçişte düzenlenmedi. |
| Rhythm Paradise Megamix | 18 | 5,717 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Secret Agent Files Miami | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Secrets of the Titanic 1912-2012 | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Sherlock Holmes - The Mystery of the Frozen City | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Shovel Knight Treasure Trove | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Star Fox 64 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| SUPER STREET FIGHTER Ⅳ 3D EDITION | 76 | 18,416 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Sushi Striker The Way of Sushido | 243 | 10,676 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| The Legend of Zelda - Majora's Mask 3D | 1 | 6,152 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| The Legend of Zelda Ocarina of Time 3D | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Tomodachi Life | 291 | 25,180 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| WarioWare Gold | 51 | 6,037 | Kaynakla tek tek dil karşılaştırması bekliyor. |
| Zero Escape - Virtue's Last Reward | 0 | 0 | Bu taramada eşleştirilen tablo yok; mevcut metin biçimi ve çıkarma aracı incelenecek. |
| Zeus Quest Remastered | 2 | 3,217 | Kaynakla tek tek dil karşılaştırması bekliyor. |

## Bu geçişte doğrulanan düzeltmeler

- Fallblox: “Bir renk seç ve çiz birkaç blok.” → “Bir renk seç ve birkaç blok çiz.” Vurgu grupları taşındı; görünür karakter kümesi ve tek satırın toplam glif genişliği aynı kaldı.
- Fullblox: “Esnetip bloklarını / hareket ettirerek çöz!” → “Bloklarını esneterek / bulmacaları çöz!” Kaynakta olmayan ek eylem kaldırıldı; vurgu grupları ve yazı alanı kontrol edildi.
- İki MSBT yeniden açılarak etiketler ve metinler doğrulandı. Her dosyada yalnız hedeflenen bir kayıt değişti; diğer mesajlar birebir korundu. Cihaz testi yapılmadı.

## İzlenebilirlik

Ham ön tarama ve kaynak sütun envanteri çalışma klasöründeki `tum_projeler_on_tarama.json` ve `tum_projeler_kaynak_envanteri.json` dosyalarında. Bu dosyalar aday listesidir; doğrulanmış hata listesi değildir. İki dil düzeltmesinin önce/sonra metinleri ve kontrolleri `tum_projeler_duzeltmeler/dil_duzeltmeleri.json` dosyasında.

