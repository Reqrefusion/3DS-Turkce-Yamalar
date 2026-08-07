# Pocket Card Jockey (3DS) Türkçe yama aracı

Ana İngilizce metinler bulundu: `romfs/a/0/0/0` GARC arşivinin içindeki 54
şifreli mesaj tablosunda bulunuyor. `.code.bin` metinleri barındırmıyor; oyunun
bu tabloları çözmek için kullandığı rutini barındırıyor. Yama için `.code.bin`
değiştirilmeyecek.

Bu araç yalnızca Python 3 kullanır ve şunları destekler:

- `a/0/0/0` içindeki ana diyalogları UTF-8 CSV'ye çıkarma ve yeniden enjekte etme
- `GARC -> LZ11 -> DARC -> BCLYT` içindeki kısa arayüz yazılarını düzenleme
- Pawn/AMX betiklerine gömülü sabit dizeleri inceleme ve aynı kapasite içinde
  değiştirme

Araç kaynak oyun dosyalarını doğrudan değiştirmez. Yalnızca düzenlenen
arşivleri ayrı bir çıktı klasöründe oluşturur.

## A. Ana diyalog ve oyun metinleri

### Bulunan biçim

- Kaynak arşiv: `romfs/a/0/0/0`
- 54 şifreli mesaj tablosu
- Cinsiyet/karakter varyantlarının aynı olanları birleştirildiğinde 5.810 dolu
  düzenleme satırı
- İngilizce harf içeren 5.727 satır
- Değişken uzunluklu UTF-16 metin desteği; çeviri özgün metinden uzun olabilir

Bazı tablolar iki bölüm içerir. Bunlar erkek/kadın veya benzer konuşma
varyantlarıdır. Aynı metne sahip bölümler CSV'de `section=all` olarak tek satır
halinde gösterilir. Farklı metinler `section=0` ve `section=1` olarak ayrı
satırlardır.

### 1. Mesaj projesini hazırlama

RomFS'ten çıkardığınız `a` klasörü ve `pcj_tr_tool.py` aynı çalışma klasöründe
olsun:

```bash
python3 pcj_tr_tool.py msg-prepare a pcj_message_project
```

Windows'ta komut `py -3` ile başlayabilir. Oluşan önemli dosyalar:

- `pcj_message_project/messages.csv`: 5.810 dolu mesajın tamamı
- `pcj_message_project/messages_latin.csv`: İngilizce harfli 5.727 satır
- `pcj_message_project/extracted/`: yeniden paketleme için çıkarılmış veriler;
  silmeyin veya değiştirmeyin
- `pcj_message_project/message_manifest.json`: biçim ve sayaç bilgileri

CSV dosyaları Excel, LibreOffice Calc ve metin editörleriyle açılabilen UTF-8
biçimindedir. Başlangıç için `messages_latin.csv` kullanılması önerilir.

Bu dağıtımın `message_project` klasörü, gönderdiğiniz `a/0/0/0` için önceden
hazırlanmıştır. Kaynak dosyanız değişmediyse yeniden `msg-prepare` çalıştırmadan
`message_project/messages_latin.csv` dosyasını düzenleyebilirsiniz. Kaynak
sürümü uyuşmazsa oluşturma komutu güvenli biçimde durur; o durumda yukarıdaki
komutla projeyi yeniden hazırlayın.

### 2. CSV'yi çevirme

- `source_text`: özgün metindir; değiştirmeyin.
- `translation`: Türkçe metni buraya yazın.
- `apply`: çevrisi biten satıra `1` yazın. Boş satırlar uygulanmaz.
- `archive`, `member`, `section`, `entry` ve `flags`: teknik alanlardır;
  değiştirmeyin.
- `notes`: çevirmen notları için serbest alandır.

Türkçe karakterleri `ÇĞİÖŞÜçğıöşü` biçiminde doğrudan yazabilirsiniz.
`source_text` içindeki özel gösterimler önemlidir:

- `\n`: oyun içi satır sonu; metnin akışına göre yerini değiştirebilirsiniz.
- `\uXXXX` ve `\0`: oyun değişkenleri, biçimlendirme işaretleri veya özel
  Unicode karakterleridir. Bunların tamamını çeviriye aynı sırada kopyalayın.
- `\\`: gerçek ters eğik çizgidir.

Araç, `\uXXXX` veya `\0` işaretlerinden biri kaybolursa bozuk mesaj üretmemek
için o satırı reddeder. Metin alanının ekrandaki genişliği otomatik büyümez;
uzun Türkçe cümlelerde `\n` kullanın veya ifadeyi kısaltın.

Örnek:

| apply | source_text | translation |
|---:|---|---|
| 1 | `Time Killer` | `Zaman Öldürücü` |

### 3. Çevrilmiş arşivi oluşturma

```bash
python3 pcj_tr_tool.py msg-build \
  a \
  message_project \
  message_project/messages_latin.csv \
  patched
```

Çıktı `patched/0/0/0` olur. Araç kaynak arşivin SHA-256 değerini doğrular,
yalnızca `apply=1` satırlarını uygular, metin tablosunu yeniden şifreler, GARC'ı
yeniden kurar ve sonucu tekrar okuyarak kontrol eder.
Projeyi kendiniz `pcj_message_project` adıyla hazırladıysanız komuttaki iki
`message_project` yolunu bu adla değiştirin.

## B. BCLYT arayüz yazıları

Ana diyaloglardan ayrı olarak menü yerleşimlerinde 658 dolu metin kutusu,
bunların içinde 172 Latin harfli arayüz yazısı bulunmuştur.

### 1. Projeyi hazırlama

```bash
python3 pcj_tr_tool.py prepare a pcj_ui_project
```

Oluşan dosyalar:

- `pcj_ui_project/translations.csv`: bütün dolu BCLYT metin kutuları
- `pcj_ui_project/translations_latin.csv`: Latin harfli arayüz metinleri
- `pcj_ui_project/extracted/`: yeniden paketleme verileri

CSV'de `translation` alanını doldurun ve uygulanacak satıra `apply=1` yazın.
`source_text` ve teknik alanları değiştirmeyin.

### 2. Değişen arşivleri oluşturma

```bash
python3 pcj_tr_tool.py build \
  a \
  pcj_ui_project/extracted \
  pcj_ui_project/translations_latin.csv \
  patched_ui
```

Bazı arayüz yazıları BCLIM görsellerine basılmıştır; bunlar CSV ile çevrilemez
ve görsel düzenleme gerektirir.

## C. Pawn/AMX betikleri

Verilen `pawn` paketindeki 95 AMX dosyası incelendi. Bunların içindeki 833
yüksek güvenli dize geliştirici günlüğü veya iç kimliktir. `dialog*.amx`
dosyaları metnin kendisini değil konuşma akışını ve mesaj kimliklerini yönetir.
Bu nedenle ana Türkçe çeviri için AMX dosyalarını düzenlemeniz gerekmez.

Yine de incelemek için:

```bash
python3 pcj_tr_tool.py amx-prepare pawn pcj_amx_project
```

Seçilen sabit dizeleri yeniden oluşturmak için:

```bash
python3 pcj_tr_tool.py amx-build \
  pawn \
  pcj_amx_project \
  pcj_amx_project/amx_translations.csv \
  patched_pawn
```

AMX adreslerini korumak için bu çeviriler CSV'deki `capacity` değerinden uzun
olamaz. Ana mesaj tablolarında böyle bir kısıtlama yoktur.

## Oyuna yerleştirme

Ana mesaj çıktısını LayeredFS/mod klasöründe şu karşılık gelen yola koyun:

```text
romfs/a/0/0/0
```

BCLYT için üretilen diğer `patched_ui/0/...` dosyalarını da aynı `romfs/a/0/...`
yapısına kopyalayın. Konsol, emülatör ve oyun bölgesine göre üst mod klasörü
değişir; kendi sürümünüzün Title ID'sini kullanın. Özgün dosyaların yedeğini
saklayın.

## Türkçe karakter ve font uyarısı

BCLYT yerleşimleri `cbf_std.bcfnt` sistem fontuna başvuruyor. Ana mesaj çizimi
de oyun ve sistem fontuna bağlıdır. Araç Türkçe UTF-16 karakterleri doğru
saklar; ancak bütün gliflerin görünmesi gerçek konsol/emülatör fontuyla test
edilmelidir. Önce birkaç kısa `ÇĞİÖŞÜçğıöşü` örneğiyle deneme yapın.

## Doğrulama

- 54 mesaj tablosu değişiklik yapılmadan yeniden üretildiğinde bayt bayt aynı
  sonuç verdi.
- Daha uzun `Zaman Öldürücü` örneği şifrelendi, GARC içine yazıldı ve çıktıdan
  tekrar doğru biçimde çözüldü.
- İki bölümlü ortak mesajların her iki varyanta uygulanması doğrulandı.
- 55 GARC arşivinin değişikliksiz yeniden kurulum turu bayt bayt aynı sonuç
  verdi.
- BCLYT içinde Türkçe metin yazma ve geri okuma testi geçti.
- 95 AMX dosyasının compact açma/yeniden kodlama turu bayt bayt aynı sonuç
  verdi.

Yalnızca size ait, yasal olarak çıkarılmış oyun dosyaları üzerinde çalışın;
oyun içeriğini veya yeniden paketlenmiş arşivleri dağıtmayın.

Araç GNU GPL v3 altında sunulur. Açık kaynak atıfları `THIRD_PARTY.md`, tam
lisans koşulları `LICENSE` dosyasındadır.
