https://gamebanana.com/mods/701527

Yama Avrupa sürümü içindir. 00040000000A8600 dosyasını luma\titles klasörüne atın. Patchleri etkinleştirdiğinizden emin olun. 

# Layton 5 Türkçe yama ve `lt5_uk.fa` aracı

Bu paket Professor Layton and the Miracle Mask'ın iki veri katmanını birlikte
yönetir:

1. ROMFS içindeki `lt5/arc/lt5_uk.fa` Level-5 **PlainFA** arşivi.
2. Bu arşivdeki `txt/uk/.../*.xs` **XSCR** senaryo/metin dosyaları.

Gönderilen `txt.zip`, `lt5_uk.fa` arşivinin tamamı değil; arşivden çıkarılmış
`txt/uk` alt ağacı ile sonradan oluşmuş `.bak`, `.kup`, `org/` ve `tr/`
çalışma dosyalarını içeriyor. Önceki paketin eksik kalan noktası buydu.

## Paketin içeriği

- `arac/layton5_tool.py`: PlainFA ve XSCR için ana uçtan uca araç.
- `arac/layton_xs_tool.py`: XSCR motoru ve eski komutlarla uyumluluk katmanı.
- `hazir_xs/txt/uk/`: Eski KUP çevirilerinden üretilmiş 1.240 doğrulanmış XS.
- `ceviri/layton_tr.csv`: Excel/LibreOffice için UTF-8 çeviri projesi.
- `ceviri/layton_tr.jsonl`: Sürüm kontrolüne uygun ana proje.
- `HIZLI_YAMA.bat` ve `HIZLI_YAMA.sh`: Temiz `lt5_uk.fa` üzerine hazır XS'leri
  koyan yardımcılar.
- `FORMAT_TR.md`: PlainFA ve XSCR ikili biçim notları.
- `raporlar/`: KUP taşıma, XSCR enjeksiyon ve doğrulama sonuçları.

Python 3 dışında bir bağımlılık yoktur.

## En hızlı kullanım

Kendi oyununuzdan alınmış temiz `lt5_uk.fa` dosyasını paketin yanına koyun ve
Windows'ta dosyayı `HIZLI_YAMA.bat` üzerine sürükleyin. Komut satırından aynı
işlem:

```bash
python3 arac/layton5_tool.py fa-replace \
  temiz/lt5_uk.fa \
  hazir_xs \
  cikti/lt5_uk_tr.fa \
  --report cikti/hazir_xs_raporu.json
```

Araç yeni bir arşiv üretir; kaynağın üzerine yazmaz. Çıktıyı oyun tarafından
beklenen adla şu LayeredFS yoluna yerleştirin:

```text
romfs/lt5/arc/lt5_uk.fa
```

Emülatörde oyunun **Open Mod Location / Mod Konumunu Aç** klasöründeki
`romfs/lt5/arc/` ağacını kullanabilirsiniz. Luma3DS'te genel yerleşim
`/luma/titles/<TITLE_ID>/romfs/lt5/arc/lt5_uk.fa` biçimindedir ve game patching
etkin olmalıdır. Oyun bölgesine göre `TITLE_ID` değişir.

## Projeden doğrudan FA üretmek

Hazır XS klasörünü kullanmak yerine JSONL/CSV projesini temiz arşive doğrudan
enjekte edebilirsiniz:

```bash
python3 arac/layton5_tool.py fa-inject-text \
  temiz/lt5_uk.fa \
  ceviri/layton_tr.jsonl \
  cikti/lt5_uk_tr.fa \
  --compression original \
  --encoding-policy turkish-ascii \
  --report cikti/fa_enjeksiyon_raporu.json
```

Bu yol her XS'nin SHA-256 değerini proje kaydıyla karşılaştırır. Yanlış bölgeye,
bozuk eski XS'lere veya farklı oyun sürümüne yanlışlıkla enjeksiyon yapılmasını
engeller. Çıktı arşiv yeniden açılarak kontrol edilir; değiştirilmemiş bütün FA
üyeleri kaynakla SHA-256 düzeyinde karşılaştırılır.

## PlainFA komutları

Arşiv yapısını ve uzantı dağılımını gösterme:

```bash
python3 arac/layton5_tool.py fa-info temiz/lt5_uk.fa --detailed
```

Arşivi ve içindeki bütün `txt/uk/*.xs` dosyalarını doğrulama:

```bash
python3 arac/layton5_tool.py fa-verify \
  temiz/lt5_uk.fa \
  --deep-xs \
  --report fa_dogrulama.json
```

Arşivi güvenli biçimde çıkarma:

```bash
python3 arac/layton5_tool.py fa-extract \
  temiz/lt5_uk.fa \
  lt5_uk_cikarilmis
```

Çıkarma sırasında `.layton5_fa_manifest.json` oluşturulur. Bu manifest kayıt
sırasını, ham dosya adlarını, ayrılmış alanları, fiziksel sıralamayı, aralık
baytlarını ve kaynak SHA-256 değerlerini saklar.

Manifestle yeniden paketleme:

```bash
python3 arac/layton5_tool.py fa-pack \
  lt5_uk_cikarilmis \
  cikti/lt5_uk_yeni.fa \
  --layout preserve
```

Hiçbir dosya değişmediyse `preserve` yerleşimi sentetik test arşivinde
bayt-birebir aynı çıktı verir. `--layout compact`, Kuriimu'ya benzer şekilde
üyeleri kayıt sırasıyla aralıksız yazar.

Bir klasörde bulunan eşleşen üyeleri geri koyma:

```bash
python3 arac/layton5_tool.py fa-replace \
  temiz/lt5_uk.fa \
  degisen_dosyalar \
  cikti/lt5_uk_yeni.fa
```

Manifest olmadan yeni bir PlainFA oluşturma:

```bash
python3 arac/layton5_tool.py fa-create klasor yeni.fa
```

İki arşivi içerik ve fiziksel yerleşim düzeyinde karşılaştırma:

```bash
python3 arac/layton5_tool.py fa-diff \
  temiz/lt5_uk.fa \
  cikti/lt5_uk_tr.fa \
  --report fa_farklari.json
```

## FA içinden çeviri projesi çıkarma

Temiz FA'dan doğrudan CSV veya JSONL oluşturma:

```bash
python3 arac/layton5_tool.py fa-export-text \
  temiz/lt5_uk.fa \
  yeni_ceviri.csv
```

Eski KUP'ları temiz FA içindeki gerçek XS'lerle eşleyerek taşıma:

```bash
python3 arac/layton5_tool.py fa-migrate-kup \
  temiz/lt5_uk.fa \
  eski_kup_klasoru \
  kurtarilan_ceviri.jsonl \
  --report kup_tasima_raporu.json
```

CSV'de yalnız `translation` sütununu değiştirin. `file`, `source_sha256`, `id`,
`offset` ve `original` alanlarını değiştirmeyin. Çok satırlı hücreleri ve
`<T>`, `<W>`, `<M...>`, `<L...>` gibi oyun kontrol kodlarını koruyun.

## Yalnız çıkarılmış XS'lerle çalışma

Eski komutlar ana araç üzerinden de kullanılabilir:

```bash
python3 arac/layton5_tool.py xs export temiz_txt_uk ceviri.csv
python3 arac/layton5_tool.py xs migrate-kup temiz_txt_uk kup_klasoru ceviri.jsonl
python3 arac/layton5_tool.py xs inject \
  temiz_txt_uk ceviri.jsonl yeni_txt_uk \
  --compression original \
  --encoding-policy turkish-ascii
python3 arac/layton5_tool.py xs verify yeni_txt_uk
```

## Neden Kuriimu kaydı bozuluyordu?

XSCR içindeki komut tablosunda `0x18` türündeki değerler metin tablosu
ofsetleridir. Eski Kuriimu yazıcısı uzayan bir metinden sonraki ofsetleri doğru
ve atomik biçimde güncellemiyordu. Bu sorun hem
[Layton 5 için #605](https://github.com/IcySon55/Kuriimu/issues/605) hem de
[genel XS yazıcısı için #495](https://github.com/IcySon55/Kuriimu/issues/495)
olarak raporlanmıştı.

Bu araç özgün XSCR bytecode ve kullanılmayan metin tablosunu korur; yalnız
değişen dizeleri tablo sonuna ekler ve aynı eski ofsete bağlı bütün `0x18`
başvurularını birlikte günceller. Kaynağın Level-5 sıkıştırma yöntemini
(sıkıştırmasız, LZ10, Huffman-4, Huffman-8 veya RLE) bölüm bazında korur.

## Türkçe karakter ve font sınırı

XSCR metinleri CP932/Shift-JIS kullanıyor. Türkçeye özgü harfler bu kodlamada
yoktur. Hazır XS'lerde güvenli `turkish-ascii` ilkesi kullanıldı:

| Türkçe | Oyuna yazılan |
| --- | --- |
| Ç ç | C c |
| Ğ ğ | G g |
| İ ı | I i |
| Ö ö | O o |
| Ş ş | S s |
| Ü ü | U u |

22 dosyada toplam 2.493 karakter dönüştürüldü. `strict` ilkesi desteklenmeyen
karakteri sessizce değiştirmez, hata verir. Gerçek Türkçe harfler için yalnız
font görselini değiştirmek yetmez; oyun fontu ile kullanılmayan CP932 kodları
arasında özel bir eşleme de tasarlanmalıdır. Gerçek `lt5_uk.fa` olmadan font
dosyasının arşiv içindeki yolu ve türü doğrulanamadığı için bu sürüm font
enjeksiyonu yapmaz.

## Gönderilen çevirinin durumu

- 1.240 temiz XS ve 15.689 benzersiz metin doğrulandı.
- 14.657 KUP çevirisi uygulandı.
- KUP/XS kaynak uyuşmazlığı veya eksik kimlik bulunmadı.
- Bozuk XML varlığı içeren `00/00_000020.xs.kup` kontrollü biçimde kurtarıldı.
- 1.240 XS ile oluşturulan büyük PlainFA simülasyonunda hazır-XS ve doğrudan
  proje enjeksiyonu bayt-birebir aynı arşivi üretti.
- 1.240 çevrilmiş XS'nin tamamı FA içinden yeniden açılıp doğrulandı.

Altı çeviride kontrol kodu dizisi orijinalden farklı. Araç bunları raporlar
fakat kasıtlı olabilecekleri için otomatik düzeltmez:

| Dosya | Kimlik | Farkın özeti |
| --- | --- | --- |
| `00/00_002020.xs` | `text000005` | Bir `<W>` eksik |
| `01/01_010180.xs` | `text000005` | `<M5/2/1>` → `<M5/2/1/45>` |
| `04/04_040200.xs` | `text000015` | `<M4/1/1>` → `<M4/1/2>` |
| `09/09_090120.xs` | `text000022` | `<L1.6>` ve `<M5/2/1/45>` eksik |
| `09/09_090160.xs` | `text000009` | `<L1.3>` eksik |
| `09/09_090160.xs` | `text000010` | `<L1.9>` eksik |

## Testler ve önemli sınır

```bash
python3 arac/layton5_tool.py selftest
python3 -m unittest discover -s arac/tests -v
```

PlainFA uygulaması Kuriimu'nun özgün biçim kaynakları, `lt5_uk.fa` ile ilgili
birincil hata kaydı ve sentetik/1.240-XS entegrasyon arşivleri üzerinde
doğrulandı. Gönderilen dosyalar arasında gerçek `lt5_uk.fa` bulunmadığından,
özgün 2.295 girdilik dosyanızda bayt-birebir çıkar/paketle testi henüz
yapılamadı. Dosyayı ayrıca eklerseniz aynı testleri doğrudan onun üzerinde
çalıştırmak son doğrulama adımıdır.
