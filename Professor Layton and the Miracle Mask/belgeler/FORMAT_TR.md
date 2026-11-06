# `lt5_uk.fa` ve XSCR biçim notları

Bu belge araçta uygulanan ikili yapıyı özetler. Alanlar little-endian'dır.

## ROMFS yerleşimi

Professor Layton and the Miracle Mask UK kaynaklarında ana arşiv:

```text
romfs/lt5/arc/lt5_uk.fa
```

Arşivin içindeki metin yolu:

```text
txt/uk/<grup>/<grup>_<kimlik>.xs
```

Kuriimu hata kaydında aynı `lt5_uk.fa` yolu ve içinden çıkarılan `title_a.xa`
örneği belgelenmiştir:
https://github.com/IcySon55/Kuriimu/issues/384

## Level-5 PlainFA

PlainFA'nın küresel bir sihirli imzası yoktur. İlk alan dosya sayısıdır.
Kuriimu'nun bu varyantı tanıma kodu ilk dört baytı `F7 08 00 00` olarak
denetler; little-endian değer `0x08F7`, yani 2.295 kayıttır.

### Başlık — 0x10 bayt

| Ofset | Boyut | Tür | Anlam |
| --- | ---: | --- | --- |
| `0x00` | 4 | `u32` | Dosya sayısı (`lt5_uk.fa`: `0x08F7`) |
| `0x04` | 4 | `u32` | Arşivin toplam boyutu |
| `0x08` | 8 | ham | Ayrılmış alan |

### Kayıt — dosya başına 0x50 bayt

Kayıt tablosu `0x10` konumunda başlar.

| Göreli ofset | Boyut | Tür | Anlam |
| --- | ---: | --- | --- |
| `0x00` | 4 | `u32` | Üye verisinin mutlak dosya ofseti |
| `0x04` | 4 | `u32` | Üye boyutu |
| `0x08` | 8 | ham | Ayrılmış alan |
| `0x10` | 0x40 | CP932 C-string | Arşiv içi yol |

Araç, kayıt ve fiziksel veri sırasını ayrı kavramlar olarak tutar. Yeniden
paketlemede kayıt sırası, ham 0x40 baytlık ad alanı, ayrılmış alanlar, üyeler
arasındaki dolgu baytları ve sonda kalan baytlar korunur. Üye uzarsa sonraki
ofsetler yeniden hesaplanır.

Birincil uygulama kaynakları:

- https://github.com/IcySon55/Kuriimu/blob/master/src/archive/archive_level5/PlainFA.cs
- https://github.com/IcySon55/Kuriimu/blob/master/src/archive/archive_level5/PlainFaSupport.cs
- https://github.com/IcySon55/Kuriimu/blob/master/src/archive/archive_level5/PlainFaManager.cs

## XSCR

### Başlık — 0x14 bayt

| Ofset | Boyut | Tür | Anlam |
| --- | ---: | --- | --- |
| `0x00` | 4 | ASCII | `XSCR` |
| `0x04` | 2 | `u16` | Tablo 0 kayıt sayısı |
| `0x06` | 2 | `u16` | Tablo 0 ofseti / 4 |
| `0x08` | 4 | `u32` | Değişken/komut kayıt sayısı |
| `0x0C` | 4 | `u32` | Değişken/komut tablosu ofseti / 4 |
| `0x10` | 4 | `u32` | Metin tablosu ofseti / 4 |

Üç bölüm Level-5 kabıyla saklanır. Kabın ilk `u32` alanı:

```text
(açılmış_boyut << 3) | yöntem
```

| Yöntem | Sıkıştırma |
| ---: | --- |
| 0 | Yok |
| 1 | LZ10 |
| 2 | Huffman-4 |
| 3 | Huffman-8 |
| 4 | RLE |

Tablo 0 kayıtları 8 bayttır (`i16`, `i16`, `u32`). Komut/değişken tablosu da
8 baytlık (`i32 ident`, `u32 value`) kayıtlardan oluşur. `ident == 0x18`
değerleri açılmış metin tablosundaki CP932 NUL-sonlu dizelere işaret eder.

Araç bytecode komutlarının semantiğini değiştirmeye çalışmaz. Tablo 0 ve
`ident != 0x18` bütün değerler aynen korunur. Değişen metinler özgün metin
blobunun sonuna eklenir ve aynı eski metin ofsetini kullanan bütün `0x18`
kayıtları yeni ofsete yönlendirilir. Bu, Kuriimu'da görülen ardışık metin
bozulmasını önler.

Birincil kaynaklar ve bilinen yazma hataları:

- https://github.com/IcySon55/Kuriimu/tree/master/src/text/text_xs
- https://github.com/IcySon55/Kuriimu/issues/495
- https://github.com/IcySon55/Kuriimu/issues/605

## Kapsam

PlainFA içindeki XS dışı üyeler araç için opaktır; çıkarılabilir, geri
konabilir ve bayt düzeyinde doğrulanabilir. `.xa`/XPCK, font, ses, görüntü ve
model biçimlerini düzenlemek ayrı format eklentileri gerektirir. Bu ayrım
özellikle önemlidir: “tam PlainFA dosya sistemi desteği”, içindeki her özel
dosya biçiminin semantik editörü olduğu anlamına gelmez.
