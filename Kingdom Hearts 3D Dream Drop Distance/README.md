# Kingdom Hearts 3D `message.rbin` Türkçe çeviri aracı

Bu paket, **Nintendo 3DS sürümündeki** `message.rbin` dosyasının içindeki CTD
metinlerini CSV'ye çıkarır ve çevrilen satırları yeni bir RBIN dosyasına geri
enjekte eder. Kaynak oyun dosyası pakete dahil edilmemiştir.

İncelenen dosya:

- RBIN/CRAR sürümü: `1`
- bağlama noktası: `message`
- toplam kayıt: `205`
- CTD dosyası: `202`
- metin satırı: `25.476`
- sıkıştırılmış kayıt: `0`
- SHA-256: `84b46027c9428b40a5f13ba7b46f992445dd7cf5d5ac4daeedb4531165af0e36`

## 1. Üç dili eşleştirilmiş olarak dışarı çıkarma (önerilen)

Python 3.9 veya daha yenisi yeterlidir; ek paket kurulmaz.

```bash
python kh3d_message_tool.py analyze message.rbin
python kh3d_message_tool.py export-aligned message.rbin translations_aligned.csv --target-language fr
```

`translations_aligned.csv` içinde aynı kayıt kimliğine ait üç çeviri yan yana
gelir:

- `source_fr`: Fransızca
- `source_en`: İngilizce
- `source_de`: Almanca
- `translation`: yazacağınız Türkçe metin

Eşleştirme satır sırasına göre değil, aynı `ctd_name + ctd_file_id + message_id`
kimliğine göre yapılır. Arşivde dil dosyaları karışık sırada bulunduğu için araç
her üçlü içindeki dil atamasını birlikte çözer. Böylece örneğin Fransızca
`Saut`, İngilizce `Jump` ve Almanca `Sprung` aynı CSV satırında görünür.

İncelenen arşivden hazırlanan hazır `translations_aligned.csv`, Fransızca hedef
yuvasındaki **7.800 benzersiz kaydı**, 64 CTD grubunda eşleştirir. Bunların
7.677 tanesinde üç dil de vardır. Yerelleştirmelerin içerikleri tamamen birebir
olmadığı için 115 kaydın İngilizce, 18 kaydın Almanca karşılığı yoktur; ilgili
hücre boş bırakılır ve `match_status` bunu açıkça gösterir. Satırlar sıraya göre
kaydırılarak eşleştirilmez.

`cttw000.ctd` içinde aynı Fransızca yuvanın iki bölgesel kopyası vardır. Bu 12
kayıtta `target_variant_count=2` görünür; tek Türkçe hücre enjeksiyon sırasında
iki hedef kopyaya da uygulanır.

Elinizde önceden çıkarılmış `translations_all.csv` varsa, RBIN'i tekrar okumadan
da eşleştirilmiş tablo oluşturabilirsiniz:

```bash
python kh3d_message_tool.py align translations_all.csv translations_aligned.csv --target-language fr
```

Eski, dilleri ayrı satırlarda gösteren dışa aktarma komutları da desteklenir:

```bash
python kh3d_message_tool.py export message.rbin translations_all.csv
python kh3d_message_tool.py export message.rbin translations_fr.csv --language fr
```

Hazır pakette yeni eşleştirilmiş tabloya ek olarak eski biçimdeki
`translations_all.csv` ve `translations_fr.csv` dosyaları da bulunur.

CSV UTF-8 BOM ile yazılır ve Excel/LibreOffice'te açılabilir.
Yalnızca `translation` sütununu düzenleyin. Kaynak metin, kimlik, hedef ve sıra
sütunlarını değiştirmeyin. Eşleştirilmiş CSV'deki `target_rbin_indices`,
`target_rbin_hashes` ve `target_message_indices` alanları enjeksiyon hedefini
güvenli biçimde doğrulamak için kullanılır.

Boş `translation` hücresi, özgün metni aynen korur. Bir metni bilerek tamamen
boşaltmak için hücreye `[[EMPTY]]` yazın.

Metinler UTF-16LE'dir. Bazı satırlar `` benzeri Özel Kullanım Alanı (PUA)
karakterleri içerir; bunlar oyun içi simge veya biçim kodları olabilir.
Çevirdiğiniz satırda bu karakterleri silmeyin ya da değiştirmeyin.

## 2. Çeviriyi geri enjekte etme

Önce her zaman özgün dosyanın yedeğini alın. Çıktıyı ayrı bir dosyaya yazın:

```bash
python kh3d_message_tool.py inject message.rbin translations_aligned.csv message_tr.rbin
```

Araç arşiv hash'lerini, dosya adlarını ve çevrilmemiş CTD kayıtlarını korur;
değişen boyutlara göre RBIN ofsetlerini yeniden hesaplar. CSV'deki bütün
`translation` hücreleri boşsa çıktı özgün RBIN'in birebir kopyasıdır. `inject`
komutu hem yeni eşleştirilmiş CSV'yi hem de eski tek-dilli CSV'leri otomatik
tanır.

## Türkçe font yaması

CTD metinleri UTF-16LE olduğu için araç `ç/Ç`, `ö/Ö`, `ü/Ü`, `ğ/Ğ`, `ş/Ş` ve
`ı/İ` karakterlerinin tamamını kayıpsız yazar. İncelenen özgün `font.rbin`
içindeki Batı dilleri fontlarında `ç/Ç`, `ö/Ö` ve `ü/Ü` zaten bulunur;
`ğ/Ğ`, `ş/Ş` ve `ı/İ` eksiktir.

Paketteki `kh3d_font_tool.py`, eksik altı glifi fontların kendi `G/g`, `S/s`,
`I/i` ve cedilla biçimlerinden üretir. Mevcut Japonca ve sembol glifleri
korunur; yeni glifler boş atlas yuvalarına eklenir.

Önce kapsamı inceleyin, ardından ayrı bir çıktı üretin:

```bash
python kh3d_font_tool.py analyze font.rbin
python kh3d_font_tool.py patch font.rbin font_tr.rbin
```

Yama şu metin fontlarına uygulanır:

- `mesfont.bcfnt`
- `talkfont.bcfnt`
- `cmdfont.bcfnt`
- `helpfont.bcfnt`

`numeral.bcfnt` yalnızca sayı gösterimi, `menufont.bcfnt` Japonca başlık
glifleri ve `iconfont.ctt` simgeler içindir; çevrilen Latin metnini çizmedikleri
için değiştirilmezler.

Üretilen `font_tr.rbin`, oyun dosyalarındaki özgün `font.rbin` yerine
yerleştirilmelidir. `message_tr.rbin` ile `font_tr.rbin` birlikte kullanıldığında
tam Türkçe karakterler görüntülenebilir.

İlk oyun içi denemede şu metni kontrol edin:

```text
Çığ, şüphe, ıslak, İĞÜÖŞ
```

Yama aracı aynı dosyaya ikinci kez uygulandığında yeni kopyalar eklemez.

Font yamasını kullanmadan geçici test yapmak isterseniz altı harfi ASCII
karşılığına çevirebilirsiniz:

```bash
python kh3d_message_tool.py inject message.rbin translations_aligned.csv message_tr.rbin --turkish-ascii
```

## Oyuna yerleştirme

Üretilen `message_tr.rbin`, kullandığınız yasal oyun dökümündeki aynı bölge ve
sürümün `message.rbin` dosyasının yerine geçirilmelidir. Güncelleme/region farkı
varsa dosya yolu ve hash'ler değişebilir. Önce birkaç kısa menü metniyle test
edin; satır uzunlukları 3DS ekranında taşabilir.

3DS imajını çıkarma ve yeniden oluşturma adımları kullanılan yasal döküm ve
mod yükleme yöntemine göre değiştiği için bu paket yalnızca RBIN/CTD katmanını
işler.

## Kaynak ve lisans

RBIN/CTD yapısı OpenKh projesinin araştırma ve kaynak koduna dayanır. Ayrıntı
için `THIRD_PARTY_NOTICES.md` ve `LICENSE-APACHE-2.0`
dosyalarına bakın.
