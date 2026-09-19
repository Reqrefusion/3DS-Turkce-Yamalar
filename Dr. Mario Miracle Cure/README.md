# Dr. Mario Türkçe Yama

Başlık kimliği: `000400000013BB00`.

Hazır yama için **BASLA.txt** dosyasındaki adımları uygulayın. Python yalnızca çeviriyi düzenlemek ve yamayı yeniden oluşturmak isteyenler içindir. Bu ZIP, oyunun kurulum dosyasını içermez.

## 1. Yama nasıl çalışır?

Luma3DS, oyun bir RomFS dosyası istediğinde SD karttaki aynı adlı değiştirilmiş dosyayı kullanır. Bu yöntemin adı LayeredFS'tir. Oyunun kurulu içeriğini yeniden oluşturmanız gerekmez.

Bu paket dokuz mesaj dili ve altı grafik dili için 21 adet `main.lzss` dosyası içerir. Her dilin kendi kaynak arşivi kullanılır; çeviri dışındaki girdiler korunur. `code.bin` değişmez.

Dosya zinciri şöyledir: `main.lzss` açılır, içindeki ARCV okunur; metinlerde MSBT, grafiklerde SARC içindeki BFLIM dokuları düzenlenir. Sonra ARCV veri blokları konsolun beklediği `0x80` sınırına hizalanır, arşivler gerçek LZSS sıkıştırmasıyla kapatılır ve çıktı tekrar açılarak doğrulanır.

## 2. Hazır yamayı kurma

Gerekenler: bu başlık kimliğine ait oyun, Luma3DS bulunan 3DS/2DS, SD karta erişim ve bu ZIP'in çıkarılmış hali.

1. Oyunu kapatın ve konsolu kapatın.
2. SD karttaki `luma/titles/000400000013BB00` klasörü varsa bilgisayara yedekleyin. Önceki yamayı temiz bir kurulumla değiştirmek için yedekten sonra eski yama klasörünü kaldırın.
3. Paketin **LayeredFS** klasörünü açın; içindeki **luma** klasörünü SD kartın köküne kopyalayın.
4. Örnek tam yol: `SD:/luma/titles/000400000013BB00/romfs/menu/2d/en/main.lzss`.
5. SD kartı takıp SELECT basılıyken konsolu açın. Luma3DS ayarlarında **Enable game patching** seçeneğini etkinleştirin. Ekranda belirtilen kaydet/çık tuşunu kullanın.
6. Oyunu normal şekilde başlatın.

Klasör düzeni ve oyun yaması ayarı için kaynak: [Luma3DS resmî belgeleri](https://github.com/LumaTeam/Luma3DS/wiki/Optional-features).

Bu rehber, yamanın sıfırdan kullanımını anlatır. Konsola Luma3DS kurma işlemi bu paketin parçası değildir. Başlık kimliği farklı olan oyunda klasör adını değiştirerek uyarlama yapmayın; sağlanan dosyalar bu kimlikteki kaynak için hazırlanmıştır.

## 3. Paket içeriği

| Dosya / klasör | İşlev |
| --- | --- |
| `BASLA.txt` | Hazır yama için kısa kurulum |
| `LayeredFS/luma` | SD karta kopyalanacak yama |
| `Gorsel_Karsilastirma.html` | Tarayıcıda çevrimdışı açılan 100 görsel karşılaştırması |
| `ceviri/metinler_tr.json` | 230 düzenlenebilir Türkçe metin |
| `ceviri/metinler_kaynak.json` | İngilizce kaynaklar ve etiketler |
| `ceviri/metin_denetimi.json` | Her metnin özgün/Türkçe karşılığı, satır sayısı ve yaklaşık genişliği |
| `ceviri/gorsel_cevirileri.json` | Görsel metinler |
| `ceviri/gorsel_yerlesimleri.json` | Özgün yazı sınırları ve yeni yazı alanları |
| `ceviri/gorseller` | 116 değiştirilmiş BFLIM; 100 yazılı görsel ve korunan 16 kapsül simgesi |
| `ceviri/gorsel_onizlemeler` | Türkçe PNG önizlemeleri |
| `araclar/fontlar` | Yeniden üretimde kullanılan benzer fontlar ve lisansları |
| `araclar` | Açma, düzenleme, oluşturma ve kontrol araçları |
| `DOGRULAMA.txt` | Yapılan testler ve oynanış testi sınırı |
| `DOSYA_DOGRULAMA_SHA256.txt` | Paket dosyalarının bütünlük özeti |

HTML'deki görseller gerçek oyun ekranı değildir; oyuna verilen doku katmanlarıdır. Dama deseni şeffaf alanı gösterir. İnce sonuç şeritlerinin yerel yönü korunmuştur; bunları oyun yerleşimi döndürür.

## 4. Kendi kaynaklarınızdan yeniden oluşturma

Önce özgün `000400000013BB00 DrMario.zip` arşivini ayrı bir klasöre çıkarın. İçinden `exefs` ve `romfs` klasörleri çıkmalıdır. Aşağıdaki komutlara **romfs klasörünün kendisini** verin. Bu kaynak arşiv yeni yama ZIP'ine dahil değildir.

Bilgisayara Python 3.10 veya üzeri kurun. Paket klasöründe terminal açın. Windows'ta klasörün adres çubuğuna `cmd` yazıp Enter'a basabilirsiniz.

```text
python -m pip install -r araclar/requirements.txt
python araclar/yamayi_olustur.py "D:\Oyun\romfs" "D:\DrMario_Cikti"
```

Windows'ta `python` bulunamıyorsa aynı komutlarda `py -3` kullanın. Linux/macOS'ta gerekirse `python3` kullanın:

```text
python3 -m pip install -r araclar/requirements.txt
python3 araclar/yamayi_olustur.py "/home/kullanici/Oyun/romfs" "/home/kullanici/DrMario_Cikti"
```

Çıktı `DrMario_Cikti/luma/titles/000400000013BB00/romfs/` altında oluşur. Çıktı klasörü kaynak `romfs` klasöründen ayrı olmalıdır.

Araç, kaynağı `ceviri/kaynak_sha256.json` ile kontrol eder. Uyuşmazlıkta hangi dosyanın farklı olduğunu söyler. Kaynak olarak eski yamanın RomFS'ini değil, gönderilen özgün dökümü kullanın. Eksik veya farklı girdileri sessizce atlamaz. Tüm arşivler bellekte oluşturulup doğrulandıktan sonra 21 hedef dosya yazılır; çıktıdaki ilgisiz dosyalar silinmez.

## 5. Metin düzenleme

`ceviri/metinler_tr.json` UTF-8 biçimindedir. Dosya adlarını, dizi sırasını ve giriş sayısını koruyun. `\n` bir satır sonudur; `\n\n` paragraflar arasındaki boş satırdır. `%d` bölüm sayısı, `%ls` oyuncu adı gibi çalışma anında doldurulan alanlardır. Bunları kaldırmayın veya değiştirmeyin. Oyuncu adını ayrı satırda tutun.

Bu pakette çok satırlı 78 giriş, özgün metnin en uzun satırı ve toplam satır sayısı aşılmadan düzenlendi. Kelimeler harflerinden bölünmedi. Kontrol, paket fontuyla karşılaştırmalı genişlik tahmini kullanır; konsolun gerçek yazı ölçümünün yerine geçmez. Kısa düğme etiketlerinde özgün kelimenin harf sayısı tek başına alan sınırı değildir: örneğin `OK` karşılığı `Tamam` olabilir.

Değişiklikten sonra:

```text
python araclar/metinleri_denetle.py
python araclar/yamayi_olustur.py "D:\Oyun\romfs" "D:\DrMario_Cikti"
```

Denetim başarısızsa anlamı koruyarak metni kısaltın; karakteri tek başına alt satıra bırakmayın. Son kontrolü ilgili oyun ekranında yapın.

## 6. Görsel yazıları yeniden üretme

`ceviri/gorsel_cevirileri.json` içindeki karşılıkları düzenleyin. Ardından:

```text
python araclar/gorselleri_olustur.py "D:\Oyun\romfs"
python araclar/yamayi_olustur.py "D:\Oyun\romfs" "D:\DrMario_Cikti"
```

İlk komut 100 yazılı BFLIM'i ve PNG önizlemelerini yeniden üretir. 16 kapsül simgesi hazır BFLIM olarak korunur. İkinci komut bunları oyunun arşivlerine yerleştirir. Paketle gelen HTML, teslim anındaki karşılaştırmadır; sonradan yaptığınız düzenlemeler için PNG önizlemelerine bakın.

Dönüştürücü önce dolgu alanıyla birlikte fiziksel doku yüzeyini döndürür, sonra mantıksal alanı kırpar. Enjeksiyon ters dönüşümü yapar; doku başlığını, biçimini ve dosya boyutunu korur. Farklı dilde doku alanı daha kısaysa boş alanla birlikte harfleri dikey ezmek yerine harf katmanı uygun alana yerleştirilir.

Yazı fontları özgün fontun birebir kopyası değildir. Küçük menülerde yuvarlak, konturlu bir sans serif; oyun başlıklarında renk geçişli, açık iç kenarlı ve koyu dış kenarlı kalın harfler kullanılır. Türkçe harflerin noktaları ve işaretleri yazı sınırına dahildir.

Şeffaf yazı dokuları temiz bir katmandan üretilir. Renkli düğmelerde yazı alanının yatay düz gradyanı aynı satırdaki yazısız renklerden yeniden kurulur. Çerçeve ve yazı alanı dışındaki pikseller korunur. Bu yöntem paketteki belirli düğmeler içindir; başka desenli görselleri otomatik temizleyen genel bir araç değildir.

## 7. Tek bir görseli dışarıda düzenleme

Önce kaynakları açın:

```text
python araclar/tumunu_cikar.py "D:\Oyun\romfs" "D:\DrMario_Acilmis"
```

Desteklenmeyen doku biçimleri ham dosya olarak çıkarılır, PNG üretilmez. Yalnız ham çıkarma için `--png-yok` ekleyebilirsiniz.

Tek görsel için:

```text
python araclar/drmario_tool.py bflim-png "resim.bflim" "resim.png"
python araclar/drmario_tool.py png-bflim "resim.png" "resim.bflim" "resim_yeni.bflim"
```

PNG boyutunu değiştirmeyin. Şablon olarak özgün BFLIM'i kullanın. Çıktıyı `ceviri/gorseller/game/timg/` veya `ceviri/gorseller/menu/timg/` altında aynı dosya adıyla yerleştirin ve yamayı yeniden oluşturun. Bundan sonra `gorselleri_olustur.py` çalıştırırsanız 100 yazılı görsele yaptığınız elle düzenlemelerin üzerine yazar; özel düzenlemelerinizi önce yedekleyin.

Diğer alt komutlar için `python araclar/drmario_tool.py --help` kullanın.

## 8. Doğrulama ve sorun giderme

```text
python -m unittest discover -s araclar -v
python araclar/metinleri_denetle.py
python araclar/paketi_dogrula.py
```

- **Yama görünmüyor:** SD yolunda fazladan `LayeredFS` veya ikinci `luma` klasörü olmadığını, başlık kimliğini ve Enable game patching ayarını kontrol edin.
- **Eski yazılar görünüyor:** Önceki yama klasörünü yedekleyip temiz kurulum yapın. Eski `main.lzss` dosyalarını karıştırmayın.
- **Kaynak uyuşmuyor:** Oluşturucuya özgün `romfs` klasörünü verin. Hazır yamanın klasörünü kaynak olarak kullanmayın.
- **Oyun açılmıyor:** Yama klasörünü geçici olarak çıkarıp oyunu deneyin. Aynı kimlikte başka bir yama varsa bunları ayrı ayrı deneyin.
- **Bir satır hâlâ taşıyor:** Ekranın tamamını, sistem dilini ve görünen metni not edin. Çalışma anındaki font, oyuncu adı ve ekran bağlamı dosya denetiminin dışında kalır.

Gerçek cihaz/emülatör üzerinde oynanış doğrulaması yapılmadı. Özellikle dinamik oyuncu adları, Türkçe gliflerin gerçek fonttaki görünümü, farklı dil yerleşimleri ve animasyon sırasındaki yazılar için oyun içi kontrol gerekir. Menü metinlerinin çevrilmesi, ağ hizmetlerinin çalışacağını garanti etmez.
