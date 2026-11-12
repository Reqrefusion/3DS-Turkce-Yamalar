# Patriots Türkçesi ile Karşılaştırma — Pass243

Tarih: 2026-11-12
Karşılaştırma: Bizim TR (`000400000009F100`, EUR, U slotu) ↔ Patriots Türkçesi (`00040000000A0500`, USA, E slotu).

## 1. Kapsam ve yöntem

- Patriots: 844 dosya / 15.679 kayıt.
- Bizim proje: 854 dosya / 15.817 kayıt; 14.931 dolu TR.
- Eşleştirme: dosya adı + anahtar + sıra. 14.793 satır birebir eşleşti.
- 138 satır Patriots'ta olmayan 10 dosyada; 741 satırda Patriots yalnızca Japonca kalmış.
- Her satır için normalize edilmiş metin, içerik kelime örtüşmesi, uzunluk oranı ve cümle yapısı karşılaştırıldı.

## 2. Sayısal özet

| Durum | Satır |
|---|---:|
| Normalleştirilmiş metin aynı | 3.347 |
| Küçük yazım/üslup farkı | 3.211 |
| Farklı ama benzer anlam | 6.624 |
| Belirgin anlam/üslup farkı | 738 |
| Patriots Japonca bırakmış | 741 |
| Patriots'ta anahtar yok | 138 |
| Patriots bizden kısa | 107 |
| Patriots bizden uzun | 25 |

Ek farklar:

- 3.286 satırda Patriots ASCII Türkçe kullanırken bizde Türkçe karakter var (ç/ğ/ı/ö/ş/ü).
- 9.473 satırda bizim metin `\r\n`, Patriots metni `\n` kullanıyor.
- Patriots'ta 2.495 satırda noktalama sonrası boşluk eksik; bizde 2.253.

## 3. Yapısal/version farkları

Patriots USA, biz EUR sürümüyüz. Bu yüzden bazı farklar çeviri değil, sürüm farkı:

- Patriots'ta olmayan 10 dosya: `Support_S`, `Trial`, `様子_プレイヤー援軍1-4`, `様子_旧マルス1-4`.
- Kayıt sayısı farklı 2 dosya: `System` (biz 102 / Patriots 101), `エンディング` (biz 576 / Patriots 559).
- Doğum yeri kartları: Patriots ABD eyaletleri kullanıyor, biz ülkeler kullanıyoruz:
  - `İtalya` ↔ `Massachusetts`
  - `Monako` ↔ `New Hampshire`
  - `Norveç` ↔ `North Carolina`
  - `Asya` ↔ `Washington, D.C.`
  - `Avrupa` ↔ `West Virginia`

## 4. Terminoloji farkları

Patriots'un yaklaşımı tutarlı değil: bazı yerlerde bizden daha Türkçe, bazı yerlerde İngilizce bırakmış, bazı yerlerde transliterasyon yapmış.

| Kavram | Bizim TR | Patriots | Satır | Not |
|---|---|---|---:|---|
| Exalt | Yüce | Exalt | 76 | Patriots İngilizce bırakmış; biz Türkçeleştirmişiz. |
| Grimleal | Grima Tarikatı | Grimleal | 17 | Patriots İngilizce bırakmış. |
| Outrealm | Öte Âlem | Dış Diyar | 19 | İki farklı Türkçe tercih. |
| Wyvern | Ejder | Wyvern | 70 | Patriots wyvern/dragon ayrımını korumuş; biz "ejder" demişiz. |
| Longfort | Uzunkale | Longfort | 4 | Biz yerelleştirmişiz; Patriots transliterasyon yapmış. |
| Farfort | Uzakkale | Farfort | 1 | Aynı eğilim. |
| Annihilation | İmha | Annihilation | 2 | Patriots şarkı adını çevirmemiş. |
| Black Knight | Kara Şövalye | Black Knight | 6 | Patriots İngilizce bırakmış. |
| Valkyrie | Valkür | Valkyrie | 1 | Patriots İngilizce bırakmış. |
| Tactician | Taktisyen | Stratejist | 11 | İki farklı tercih. |
| Armor Knight | Zırhlı Şövalye | Sövalye | 4 | Biz daha spesifik. |
| Grandmaster | Üstat | Büyük Usta | 1 | İki farklı tercih. |
| Altar | Sunak | Sofra | 1 | İki farklı tercih. |

### Sınıf adları

| Bizim TR | Patriots | Not |
|---|---|---|
| Berserker | Çilgin | Patriots daha Türkçe. |
| Savaşçı | Muharip | Farklı tercih. |
| Keskin Nişancı | Nisanci | Patriots daha kısa. |
| Mirmidon | Kiliç Ustasi | Patriots Türkçeleştirmiş; biz İngilizce/transliterasyon bırakmışız. |
| Kılıç Ustası | Kiliç Üstadi | Aynı anlam, farklı yazım. |
| Kara Pegasus | Karanlik Uçucu | Patriots "pegasus" yerine "uçucu" demiş. |
| Ejder Binicisi | Wyvern Sürücüsü | Patriots wyvern ayrımını korumuş. |
| Ejder Lordu | Wyvern Lordu | Aynı eğilim. |
| Grifon Binicisi | Griffon Sürücüsü | Farklı tercih. |
| Kara Büyücü | Karanlik Büyücü | Farklı tercih. |
| Valkür | Valkyrie | Patriots İngilizce bırakmış. |
| Kara Şövalye | Karanlik Sövalye | Farklı tercih. |
| Büyü Ustası | Sihirbaz | Patriots daha sade. |
| Yıldız Lordu | Kutup Yildizi | Patriots "Star Lord"u "Kutup Yıldızı" yapmış; biz daha literal. |
| KUKLA | DUMMY | Biz Türkçeleştirmişiz; Patriots İngilizce bırakmış. |

### Yer ve bölüm adları

| Bizim TR | Patriots | Not |
|---|---|---|
| Arena Ferox | Ferox Arenasi | Biz İngilizce adı korumuşuz; Patriots çevirmiş. |
| Plegia Kalesi | Plegia Satosu | "Kale" ↔ "Sato". |
| Uzunkale | Longfort | Biz yerelleştirmişiz; Patriots transliterasyon. |
| Uzakkale | Farfort | Aynı. |
| Öte Âlem Kapısı | Dış Diyar Kapisi | Farklı tercih. |
| Ylisstol'un batısında | Ylisstol Batisi | Farklı kısalık. |
| Yan Hikâye 1 | Yan Bölüm 1 | "Hikâye" ↔ "Bölüm". |
| Son Bölüm | Final | Farklı tercih. |

### Skill/menü adları

| Bizim TR | Patriots | Not |
|---|---|---|
| İsabet Oranı +10 | Isabet +10 | Patriots daha kısa. |
| Yetenek +2 | Beceri +2 | Farklı terim. |
| Yetenek | Yatkinlik | Farklı terim. |
| Kilit Açma | Kilit Dokunusu | Farklı tercih. |
| Çifte Vuruş+ | Çift Vurus+ | Aynı anlam. |
| Efekt | Efekt Sesi | Patriots daha açık; biz Pass243'te düzelttik. |
| Morgan (M)/(F) | Morgan (E)/(K) | Patriots Türkçe kısaltma kullanmış; biz Pass243'te düzelttik. |
| Seçenekler | Ayarlar | Farklı tercih. |
| Ara Kayıt | Yer İmi | Bizimki daha standart. |
| Konvoy | Depo | Farklı tercih. |
| Teşvik | Moral | Rally skill'i için farklı tercih. |
| Donat | Kuşan | Equip için farklı tercih. |
| Video Galerisi | Sinema | Farklı tercih. |
| Destek Günlüğü | Destek Kaydi | Farklı tercih. |

## 5. Üslup farkları

Patriots genelde daha literal/kısa; biz daha akıcı ve açıklayıcıyız.

| Satır | Bizim TR | Patriots |
|---|---|---|
| `026.csv` 181 | Kaderin bileğini büktük! | Kaderin kendisini teslim olmaya zorladık! |
| `movie.csv` 6 | İşi bitti. | Onun sonu bu. |
| `E003.csv` 25 | Kardeşimin iyiliği için yaşamaya devam etmeliyim! | Kiz kardesim için yasamaliyim! |
| `E009.csv` 106 | Sırf burada can vermek için ne kadar da yol gelmişsin. | Sonunu görmek için çok yol geldin. |
| `E010.csv` 85 | Hıh... Benim dengim değilsin. | Hmph... Yenildin. |
| `015.csv` 20 | Mümkünse evlere de uğrayıp halkın durumunu öğrenelim. | Mümkünse halkin nasil oldugunu görmek için buradaki evleri de ziyaret etmeliyiz. |
| `026.csv` 149 | İnsanı hayatta hissettiren şey, bir ejderhayı sağlam pataklamaktır! | Bir ejderhanin canina okumak gibisi yok, insana yasadigini hissettiriyor! |

Önemli örnek: `様子_ウード3.csv` 8'de Patriots metni U ile uyuşmuyor; bizim metnimiz U'ya sadık:

- U: "Mother! By the gods, you look ill! Does the heroic blood within you seethe and rage?"
- Biz: "Anne! Tanrılar, hasta görünüyorsun! İçindeki kahraman kanı mı kaynıyor?"
- Patriots: "Anne, hareketlerime yeni isimler buldum! Sence kulağa hoş geliyor mu?"

Bu, Patriots'un her satırda altın standart olmadığını gösterir.

## 6. Eksik/fazla çeviri

- **Patriots bizden kısa (107 satır):** Genelde daha kompakt/literal çeviri; bazılarında bizim ek açıklamamız var.
- **Patriots bizden uzun (26 satır):** Genelde Patriots'un daha açıklayıcı olduğu UI/menu satırları.
- **Patriots Japonca (741 satır):** Çoğu kullanılmayan PCM2/PCF2/PCF3 varyantı; biz bunları Türkçeye çevirmişiz.
- **Patriots'ta anahtar yok (138 satır):** 10 dosya Patriots'ta yok; bizim çevirilerimiz U/F/G/I/S ile doğrulandı.

## 7. Kalite/format farkları

- Patriots 3.286 satırda ASCII Türkçe kullanıyor; bizde Türkçe karakterler var.
- Patriots satır sonlarında `\n`, bizde `\r\n`.
- Patriots'ta noktalama sonrası boşluk eksikliği daha yaygın (`Bu.Bu`, `...`).
- Patriots bazı yerlerde İngilizce bırakmış (`Exalt`, `Grimleal`, `Black Knight`, `Annihilation`, `Valkyrie`).
- Biz bazı yerlerde İngilizce/loanword bıraktık (`Berserker`, `Taguel`, `Manakete`, `Lord`, `General`).
- Patriots ABD sürümü olduğu için doğum yeri kartlarında ABD eyaletleri var; bizde ülkeler var.

## 8. Sonuç

Patriots daha literal, yer yer daha kısa ve bazı sınıf adlarında daha Türkçe; biz daha akıcı, Türkçe karakterli ve konuşma metinlerinde daha eksiksiziz. Patriots bazı yerlerde İngilizce bırakmış, bazı yerlerde bizden daha Türkçe tercih yapmış. Bu yüzden farklar "Patriots daha iyi/kötü" diye tek eksende değerlendirilemez.

Pass243'te Patriots'un daha iyi olduğu üç UI etiketi düzeltildi: `Efekt Sesi`, `Morgan (E)`, `Morgan (K)`. Diğer farklar bilinçli üslup/terminoloji tercihi olarak bırakıldı.

Satır satır incelemek için:

- `raporlar/PASS243_PATRIOTS_NOTABLE.tsv` — 2.250 önemli fark (tüm kısa terim farkları + büyük anlam farkları + Japonca/eksik/kısa/uzun satırlar).
- Tam 14.931 satırlık diff (21,8 MB) gerektiğinde ayrıca üretilebilir.

## 9. Uzunluk/taşma notu

- Piksel bazlı denetim `System.bfnt.lz` glif genişlikleriyle yapıldı.
- Sayfa bazında 400 px üstü ve resmi dil ≤360 px olan **0 satır** kaldı.
- Dikey taşma **0**; sayfa başına en fazla 3 satır (resmi oyun da 3 kullanıyor).
- Pass243'te 42 satırda satır kırma/kısaltma yapıldı.
- 360 px altında kalan 494 satır "sınırda" olarak işaretlendi; normal kutuya sığma ihtimali yüksek olduğu için toplu değiştirilmedi.
